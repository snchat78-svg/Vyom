param(
    [string]$ExePath = ".\dist\Vyom.exe",
    [string]$OutputPath = ".\M10_4_windows_preflight.json",
    [switch]$AttemptLaunchSmokeTest
)

# Windows PowerShell 3-compatible, read-only host preflight + optional "exit" smoke test.
# This deliberately does not exercise user files, microphone recording, or UI automation.
$ErrorActionPreference = "Stop"
$checks = New-Object 'System.Collections.Generic.List[object]'
$scriptExitCode = 0
$os = $null
$osVersionText = "unknown"
$osCaption = "unknown"
$osBuild = "unknown"
$osSupported = $false
$memoryMb = $null
if ([Environment]::Is64BitOperatingSystem) { $architecture = "x64" } else { $architecture = "x86" }

try {
    $os = Get-WmiObject -Class Win32_OperatingSystem -ErrorAction Stop
    $osVersion = [version]$os.Version
    $osVersionText = [string]$os.Version
    $osCaption = [string]$os.Caption
    $osBuild = [string]$os.BuildNumber
    $memoryMb = [long][math]::Round(([double]$os.TotalVisibleMemorySize / 1024), 0)
    # CPython 3.11's documented Windows baseline is Windows 8.1 (6.3) or newer.
    $osSupported = $osVersion -ge [version]"6.3"
    if ($osSupported) {
        $checks.Add([ordered]@{
            check_id = "os_compatibility"
            status = "pass"
            detail = "OS version meets the current Python 3.11 baseline (Windows 8.1 / version 6.3 or newer)."
            actual = $osVersionText
        })
    } else {
        $checks.Add([ordered]@{
            check_id = "os_compatibility"
            status = "block"
            detail = "This OS is below the current Python 3.11 baseline; no EXE launch was attempted."
            actual = $osVersionText
        })
        $scriptExitCode = 2
    }
} catch {
    $checks.Add([ordered]@{
        check_id = "os_facts"
        status = "fail"
        detail = "Unable to read Windows version/memory facts through WMI."
        actual = $_.Exception.GetType().Name
    })
    $scriptExitCode = 1
}

$exeFullPath = $null
$exeExists = $false
$exeSize = $null
$exeHash = $null
try {
    if ([System.IO.Path]::IsPathRooted($ExePath)) {
        $exeFullPath = [System.IO.Path]::GetFullPath($ExePath)
    } else {
        $exeFullPath = [System.IO.Path]::GetFullPath((Join-Path (Get-Location).Path $ExePath))
    }
    if (Test-Path -LiteralPath $exeFullPath -PathType Leaf) {
        $exe = Get-Item -LiteralPath $exeFullPath
        $exeExists = $true
        $exeSize = [long]$exe.Length
        $algorithm = [System.Security.Cryptography.SHA256]::Create()
        $stream = [System.IO.File]::OpenRead($exeFullPath)
        try {
            $exeHash = [BitConverter]::ToString($algorithm.ComputeHash($stream)).Replace("-", "").ToLowerInvariant()
        } finally {
            $stream.Dispose()
            $algorithm.Dispose()
        }
        if ($exeSize -ge 100000) {
            $checks.Add([ordered]@{
                check_id = "exe_present_and_nontrivial"
                status = "pass"
                detail = "Executable exists and is at least 100 KB."
                actual = $exeSize
            })
        } else {
            $checks.Add([ordered]@{
                check_id = "exe_present_and_nontrivial"
                status = "fail"
                detail = "Executable exists but is unexpectedly small."
                actual = $exeSize
            })
            $scriptExitCode = 1
        }
    } else {
        $checks.Add([ordered]@{
            check_id = "exe_present_and_nontrivial"
            status = "fail"
            detail = "Executable path does not exist."
            actual = [System.IO.Path]::GetFileName($ExePath)
        })
        if ($scriptExitCode -eq 0) { $scriptExitCode = 1 }
    }
} catch {
    $checks.Add([ordered]@{
        check_id = "exe_inspection"
        status = "fail"
        detail = "Executable metadata could not be read."
        actual = $_.Exception.GetType().Name
    })
    if ($scriptExitCode -eq 0) { $scriptExitCode = 1 }
}

$launch = [ordered]@{
    status = "not_attempted"
    exit_code = $null
    goodbye_detected = $false
    stdout_excerpt = ""
    stderr_excerpt = ""
}
if ($AttemptLaunchSmokeTest) {
    if (-not $osSupported) {
        $launch.status = "skipped_unsupported_os"
    } elseif (-not $exeExists) {
        $launch.status = "skipped_missing_exe"
    } elseif ($exeSize -lt 100000) {
        $launch.status = "skipped_invalid_exe"
    } else {
        $process = $null
        try {
            $startInfo = New-Object System.Diagnostics.ProcessStartInfo
            $startInfo.FileName = $exeFullPath
            $startInfo.WorkingDirectory = [System.IO.Path]::GetDirectoryName($exeFullPath)
            $startInfo.UseShellExecute = $false
            $startInfo.CreateNoWindow = $true
            $startInfo.RedirectStandardInput = $true
            $startInfo.RedirectStandardOutput = $true
            $startInfo.RedirectStandardError = $true

            $process = New-Object System.Diagnostics.Process
            $process.StartInfo = $startInfo
            [void]$process.Start()
            $stdoutTask = $process.StandardOutput.ReadToEndAsync()
            $stderrTask = $process.StandardError.ReadToEndAsync()
            $process.StandardInput.WriteLine("exit")
            $process.StandardInput.Close()

            $exited = $process.WaitForExit(30000)
            if (-not $exited) {
                $process.Kill()
                [void]$process.WaitForExit()
                $launch.status = "timeout"
                if ($scriptExitCode -eq 0) { $scriptExitCode = 1 }
            } else {
                $stdoutText = [string]$stdoutTask.Result
                $stderrText = [string]$stderrTask.Result
                $launch.exit_code = [int]$process.ExitCode
                $launch.goodbye_detected = ($stdoutText -match "Vyom\s*:\s*Goodbye")
                $launch.stdout_excerpt = $stdoutText.Substring(0, [math]::Min(800, $stdoutText.Length))
                $launch.stderr_excerpt = $stderrText.Substring(0, [math]::Min(400, $stderrText.Length))
                if ($process.ExitCode -eq 0 -and $launch.goodbye_detected) {
                    $launch.status = "pass"
                } else {
                    $launch.status = "fail"
                    if ($scriptExitCode -eq 0) { $scriptExitCode = 1 }
                }
            }
        } catch {
            $launch.status = "launch_error"
            $launch.stderr_excerpt = $_.Exception.GetType().Name
            if ($scriptExitCode -eq 0) { $scriptExitCode = 1 }
        } finally {
            if ($null -ne $process) { $process.Dispose() }
        }
    }

    if ($launch.status -eq "pass") { $launchCheckStatus = "pass" }
    elseif ($launch.status -like "skipped_*") { $launchCheckStatus = "block" }
    else { $launchCheckStatus = "fail" }
    $checks.Add([ordered]@{
        check_id = "exe_launch_and_clean_exit"
        status = $launchCheckStatus
        detail = "Sends only the harmless 'exit' command and checks the process exits cleanly."
        actual = $launch.status
    })
}

$environmentKind = if ($env:GITHUB_ACTIONS -eq "true") { "github_actions_runner" } else { "local_windows_machine" }
if (-not $os) {
    $overall = "host_facts_unavailable"
} elseif (-not $osSupported) {
    $overall = "blocked_unsupported_os"
} elseif (-not $exeExists -or $exeSize -lt 100000) {
    $overall = "blocked_missing_or_invalid_exe"
} elseif ($AttemptLaunchSmokeTest -and $launch.status -ne "pass") {
    $overall = "launch_smoke_failed"
} elseif ($AttemptLaunchSmokeTest) {
    $overall = "preflight_passed_manual_acceptance_pending"
} else {
    $overall = "preflight_only_manual_acceptance_pending"
}
if ($exeFullPath) { $exeFileName = [System.IO.Path]::GetFileName($exeFullPath) } else { $exeFileName = [System.IO.Path]::GetFileName($ExePath) }

$manualAcceptance = @(
    [ordered]@{ id = "typed_startup_and_exit"; status = "not_run"; note = "Safe text-mode launch and graceful exit." },
    [ordered]@{ id = "hindi_and_hinglish_text"; status = "not_run"; note = "Hindi, Roman Hindi, and Hinglish commands/replies." },
    [ordered]@{ id = "microphone_stt_and_tts"; status = "not_run"; note = "Actual microphone input and audible speech output." },
    [ordered]@{ id = "ui_grounding"; status = "not_run"; note = "Target ambiguity rejected; correct active window/control confirmed." },
    [ordered]@{ id = "multi_step_dependencies"; status = "not_run"; note = "Dependent steps do not run before prerequisites." },
    [ordered]@{ id = "postcondition_verification"; status = "not_run"; note = "Success is reported only when a postcondition is observed." },
    [ordered]@{ id = "provider_outage_unknown_answer"; status = "not_run"; note = "Offline factual retrieval returns honest unknown rather than guessing." },
    [ordered]@{ id = "memory_consent_and_opt_out"; status = "not_run"; note = "Consent defaults off; opt-out immediately blocks memory use." },
    [ordered]@{ id = "low_memory_stability"; status = "not_run"; note = "Observe responsiveness and crashes under the target device's actual RAM." }
)

$report = [ordered]@{
    schema_version = 1
    phase_id = "M10.4"
    scope = "preflight_only_not_device_acceptance"
    execution_environment = $environmentKind
    collected_at_utc = [DateTime]::UtcNow.ToString("o")
    overall_status = $overall
    device = [ordered]@{
        os_caption = $osCaption
        os_version = $osVersionText
        os_build = $osBuild
        architecture = $architecture
        total_visible_memory_mb = $memoryMb
        memory_threshold = "not_defined_by_this_gate"
    }
    artifact = [ordered]@{
        file_name = $exeFileName
        exists = $exeExists
        size_bytes = $exeSize
        sha256 = $exeHash
    }
    launch_smoke_test = $launch
    checks = @($checks.ToArray())
    manual_acceptance = $manualAcceptance
    limitations = @(
        "This report is host preflight and optional clean-exit smoke evidence only.",
        "It does not prove microphone capture, audible TTS, real UI grounding, multi-step completion, or user-device support.",
        "Manual acceptance statuses remain not_run until evidence is collected on the target device."
    )
}

try {
    $outputFullPath = [System.IO.Path]::GetFullPath($OutputPath)
    $outputDirectory = [System.IO.Path]::GetDirectoryName($outputFullPath)
    if (-not (Test-Path -LiteralPath $outputDirectory -PathType Container)) {
        New-Item -ItemType Directory -Force -Path $outputDirectory | Out-Null
    }
    $json = ConvertTo-Json -InputObject $report -Depth 8
    $utf8NoBom = New-Object System.Text.UTF8Encoding $false
    [System.IO.File]::WriteAllText($outputFullPath, $json + [Environment]::NewLine, $utf8NoBom)
    Write-Host ("M10.4 preflight report written: " + $outputFullPath)
    Write-Host ("Overall status: " + $overall)
    Write-Host "Manual Windows/microphone acceptance is still pending."
} catch {
    Write-Error ("Unable to write M10.4 preflight report: " + $_.Exception.GetType().Name)
    exit 1
}
exit $scriptExitCode
