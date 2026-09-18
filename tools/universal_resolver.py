# Vyom AI - Universal Windows Resolver
# Version 1.1
# Preserves the original resolver contract and Windows launch methods.

import os
import shutil
import subprocess
import difflib
import ctypes
import time
import sys

if sys.platform == "win32":
    try:
        import winreg
    except ImportError:
        winreg = None
else:
    winreg = None


class UniversalResolver:
    def __init__(self):
        appdata = os.environ.get("APPDATA", "")
        programdata = os.environ.get("PROGRAMDATA", "")
        user_profile = os.environ.get("USERPROFILE", "")

        self.start_menu_paths = [
            os.path.join(appdata, "Microsoft", "Windows", "Start Menu", "Programs"),
            os.path.join(programdata, "Microsoft", "Windows", "Start Menu", "Programs"),
        ]

        self.desktop_paths = [
            os.path.join(user_profile, "Desktop"),
            os.path.join(programdata, "Desktop"),
            os.path.join(user_profile, "OneDrive", "Desktop"),
        ]

        self.common_paths = [
            os.path.join(user_profile, "Desktop"),
            os.path.join(user_profile, "Documents"),
            os.path.join(user_profile, "Downloads"),
            os.path.join(user_profile, "Pictures"),
            os.path.join(user_profile, "Videos"),
            os.path.join(user_profile, "Music"),
            os.path.join(user_profile, "OneDrive", "Desktop"),
            os.path.join(user_profile, "OneDrive", "Documents"),
            os.path.join(user_profile, "OneDrive", "Downloads"),
            os.path.join(user_profile, "OneDrive", "Pictures"),
            os.path.join(user_profile, "OneDrive", "Videos"),
            os.path.join(user_profile, "OneDrive", "Music"),
        ]

        self.program_paths = []
        for key in ("ProgramFiles", "ProgramFiles(x86)", "ProgramW6432"):
            value = os.environ.get(key, "")
            if value and value not in self.program_paths:
                self.program_paths.append(value)

        self.windows_paths = [
            os.environ.get("WINDIR", r"C:\Windows"),
            os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "System32"),
            os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "SysWOW64"),
        ]

        self.windows_apps_paths = [
            os.path.join(os.environ.get("ProgramFiles", r"C:\Program Files"), "WindowsApps"),
            os.path.join(os.environ.get("LOCALAPPDATA", ""), "Packages"),
        ]

        self.application_extensions = [".exe", ".com", ".bat", ".cmd", ".lnk"]

        self.file_extensions = [
            ".txt", ".rtf", ".csv", ".tsv",
            ".pdf", ".doc", ".docx", ".docm", ".dot", ".dotx",
            ".xls", ".xlsx", ".xlsm", ".xlt", ".xltx",
            ".ppt", ".pptx", ".pptm", ".pps", ".ppsx",
            ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp",
            ".tif", ".tiff", ".ico", ".svg", ".raw", ".heic", ".heif",
            ".mp3", ".wav", ".wma", ".aac", ".m4a", ".flac", ".ogg",
            ".oga", ".opus", ".mid", ".midi", ".aiff", ".aif",
            ".mp4", ".avi", ".mkv", ".mov", ".wmv", ".3gp", ".mpeg",
            ".mpg", ".m4v", ".webm", ".flv", ".mts", ".m2ts",
            ".zip", ".rar", ".7z", ".tar", ".gz", ".bz2", ".xz", ".iso",
            ".html", ".htm", ".mht", ".mhtml",
            ".py", ".dart", ".java", ".js", ".jsx", ".tsx", ".json",
            ".xml", ".css", ".scss", ".sass", ".less", ".c", ".cpp",
            ".h", ".hpp", ".cs", ".php", ".sql", ".sh", ".yaml", ".yml",
            ".ini", ".cfg", ".log",
        ]

        self.max_results = 20
        self._windows_apps_cache = None
        self._windows_apps_cache_time = 0
        self.app_cache_seconds = 30

    def normalize(self, name):
        if name is None:
            return ""
        name = str(name).strip().strip('"').strip("'").lower()
        for ext in (".exe", ".lnk", ".bat", ".cmd", ".com"):
            if name.endswith(ext):
                name = name[:-len(ext)]
                break
        return " ".join(name.split()).strip()

    def clean_target(self, target):
        if target is None:
            return ""
        return str(target).strip().strip('"').strip("'").strip()

    def _add_unique(self, results, item):
        if item is None:
            return
        if isinstance(item, str):
            key = item.lower()
        elif isinstance(item, dict):
            key = str(item.get("name", "")).lower() + "|" + str(item.get("path", "")).lower()
        else:
            key = str(item).lower()

        for existing in results:
            if isinstance(existing, str):
                existing_key = existing.lower()
            elif isinstance(existing, dict):
                existing_key = str(existing.get("name", "")).lower() + "|" + str(existing.get("path", "")).lower()
            else:
                existing_key = str(existing).lower()
            if existing_key == key:
                return
        results.append(item)

    def find_exact_path(self, target):
        target = self.clean_target(target)
        if not target:
            return None
        try:
            target = os.path.expandvars(os.path.expanduser(target))
        except Exception:
            pass
        return target if os.path.exists(target) else None

    def find_in_path(self, target):
        name = self.normalize(target)
        if not name:
            return None
        return shutil.which(name) or shutil.which(name + ".exe")

    def search_common_locations(self, target):
        original = self.clean_target(target).lower()
        target_name = self.normalize(target)
        if not original:
            return []

        exact, partial = [], []

        for base_path in self.common_paths:
            if not os.path.exists(base_path):
                continue
            try:
                for root, dirs, files in os.walk(base_path):
                    for directory in dirs:
                        lower = directory.lower()
                        path = os.path.join(root, directory)
                        if lower == original:
                            self._add_unique(exact, path)
                        elif target_name and target_name in lower:
                            self._add_unique(partial, path)

                    for file in files:
                        lower = file.lower()
                        filename = os.path.splitext(lower)[0]
                        path = os.path.join(root, file)
                        if lower == original or filename == target_name:
                            self._add_unique(exact, path)
                        elif target_name and target_name in filename:
                            self._add_unique(partial, path)

                    if len(exact) + len(partial) >= self.max_results:
                        break
            except Exception:
                continue

        return (exact + partial)[:self.max_results]

    def search_start_menu(self, target):
        target_name = self.normalize(target)
        if not target_name:
            return []
        exact, partial = [], []

        for start_path in self.start_menu_paths:
            if not os.path.exists(start_path):
                continue
            try:
                for root, dirs, files in os.walk(start_path):
                    for file in files:
                        if not file.lower().endswith((".lnk", ".exe", ".bat", ".cmd", ".com")):
                            continue
                        name = self.normalize(os.path.splitext(file)[0])
                        path = os.path.join(root, file)
                        if name == target_name:
                            self._add_unique(exact, path)
                        elif target_name in name:
                            self._add_unique(partial, path)
            except Exception:
                continue
        return (exact + partial)[:self.max_results]

    def search_desktop(self, target):
        target_name = self.normalize(target)
        if not target_name:
            return []
        results = []

        for desktop in self.desktop_paths:
            if not os.path.exists(desktop):
                continue
            try:
                for file in os.listdir(desktop):
                    path = os.path.join(desktop, file)
                    name = self.normalize(os.path.splitext(file)[0])
                    if name == target_name or target_name in name:
                        self._add_unique(results, path)
            except Exception:
                continue

        return results[:self.max_results]

    def search_registry_app_paths(self, target):
        if winreg is None:
            return []

        target_name = self.normalize(target)
        if not target_name:
            return []

        results = []
        roots = [
            (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\App Paths"),
            (winreg.HKEY_LOCAL_MACHINE, r"Software\Microsoft\Windows\CurrentVersion\App Paths"),
            (winreg.HKEY_LOCAL_MACHINE, r"Software\Wow6432Node\Microsoft\Windows\CurrentVersion\App Paths"),
        ]

        for hive, base in roots:
            try:
                with winreg.OpenKey(hive, base) as key:
                    count = winreg.QueryInfoKey(key)[0]
                    for index in range(count):
                        try:
                            sub = winreg.EnumKey(key, index)
                            with winreg.OpenKey(key, sub) as skey:
                                value, _ = winreg.QueryValueEx(skey, "")
                            name = self.normalize(os.path.splitext(sub)[0])
                            if value and os.path.exists(value) and (name == target_name or target_name in name):
                                self._add_unique(results, value)
                        except Exception:
                            continue
            except Exception:
                continue

        return results[:self.max_results]

    def search_program_files(self, target):
        target_name = self.normalize(target)
        if not target_name:
            return []

        exact, partial = [], []

        for base in self.program_paths:
            if not os.path.exists(base):
                continue
            try:
                for root, dirs, files in os.walk(base):
                    dirs[:] = [d for d in dirs if d.lower() not in ("cache", "temp", "__pycache__", "logs")]

                    for file in files:
                        if not file.lower().endswith(".exe"):
                            continue
                        name = self.normalize(os.path.splitext(file)[0])
                        path = os.path.join(root, file)

                        if name == target_name:
                            self._add_unique(exact, path)
                        elif target_name in name:
                            self._add_unique(partial, path)

                    if len(exact) + len(partial) >= self.max_results:
                        break
            except Exception:
                continue

        return (exact + partial)[:self.max_results]

    def get_start_apps(self):
        script = r'''
$ErrorActionPreference = "SilentlyContinue"
try {
    if (Get-Command Get-StartApps -ErrorAction SilentlyContinue) {
        Get-StartApps | ForEach-Object {
            if ($_.Name -and $_.AppID) {
                Write-Output ($_.Name + "`t" + $_.AppID)
            }
        }
    }
} catch {}
'''

        try:
            p = subprocess.Popen(
                ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
            )
            stdout, _ = p.communicate(timeout=20)
        except Exception:
            return []

        apps = []
        for line in stdout.splitlines():
            parts = line.strip().split("\t", 1)
            if len(parts) == 2 and parts[0].strip() and parts[1].strip():
                apps.append({
                    "name": parts[0].strip(),
                    "app_id": parts[1].strip(),
                    "path": "shell:AppsFolder\\" + parts[1].strip(),
                })
        return apps

    def get_appsfolder_apps(self, force=False):
        now = time.time()
        if (
            not force
            and self._windows_apps_cache is not None
            and now - self._windows_apps_cache_time < self.app_cache_seconds
        ):
            return list(self._windows_apps_cache)

        script = r'''
$ErrorActionPreference = "SilentlyContinue"
try {
    $shell = New-Object -ComObject Shell.Application
    $folder = $shell.Namespace("shell:AppsFolder")
    if ($folder -ne $null) {
        foreach ($item in $folder.Items()) {
            try {
                $name = [string]$item.Name
                $path = [string]$item.Path
                if ($name) {
                    Write-Output ($name + "`t" + $path)
                }
            } catch {}
        }
    }
} catch {}
'''

        apps = []
        try:
            p = subprocess.Popen(
                ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
            )
            stdout, _ = p.communicate(timeout=25)

            for line in stdout.splitlines():
                parts = line.strip().split("\t", 1)
                if len(parts) == 2 and parts[0].strip():
                    self._add_unique(
                        apps,
                        {
                            "name": parts[0].strip(),
                            "app_id": "",
                            "path": parts[1].strip(),
                        },
                    )
        except Exception:
            pass

        self._windows_apps_cache = list(apps)
        self._windows_apps_cache_time = time.time()
        return apps

    def search_windows_apps(self, target):
        target_name = self.normalize(target)
        if not target_name:
            return []

        all_apps = []
        for app in self.get_start_apps() + self.get_appsfolder_apps():
            self._add_unique(all_apps, app)

        exact, partial = [], []
        for app in all_apps:
            name = self.normalize(app.get("name", ""))
            if name == target_name:
                exact.append(app)
            elif target_name in name:
                partial.append(app)

        return (exact + partial)[:self.max_results]

    def _launch_appsfolder_path(self, app_path):
        if not app_path:
            return False

        try:
            result = ctypes.windll.shell32.ShellExecuteW(
                None, "open", app_path, None, None, 1
            )
            if result > 32:
                return True
        except Exception:
            pass

        for command in (
            ["explorer.exe", app_path],
            ["cmd.exe", "/c", "start", "", app_path],
        ):
            try:
                subprocess.Popen(
                    command,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                return True
            except Exception:
                continue

        return False

    def _open_appsfolder_item(self, target):
        target_name = self.normalize(target)
        if not target_name:
            return None

        script = r'''
$ErrorActionPreference = "SilentlyContinue"
$target = $env:VYOM_TARGET
try {
    $shell = New-Object -ComObject Shell.Application
    $folder = $shell.Namespace("shell:AppsFolder")
    if ($folder -ne $null) {
        $best = $null
        $bestScore = -1

        foreach ($item in $folder.Items()) {
            if ($item -eq $null) { continue }
            $name = [string]$item.Name
            if ([string]::IsNullOrWhiteSpace($name)) { continue }

            $nameClean = $name.ToLower().Trim()
            $targetClean = $target.ToLower().Trim()
            $score = 0

            if ($nameClean -eq $targetClean) {
                $score = 1000
            } elseif ($nameClean.StartsWith($targetClean)) {
                $score = 800
            } elseif ($nameClean.Contains($targetClean)) {
                $score = 600
            }

            if ($score -gt $bestScore) {
                $best = $item
                $bestScore = $score
            }
        }

        if ($best -ne $null -and $bestScore -gt 0) {
            $best.InvokeVerb("open")
            Write-Output ("OPENED`t" + $best.Name + "`t" + $best.Path)
            exit 0
        }
    }
} catch {}
exit 1
'''

        try:
            env = os.environ.copy()
            env["VYOM_TARGET"] = target_name

            p = subprocess.Popen(
                ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                env=env,
            )
            stdout, _ = p.communicate(timeout=20)

            for line in stdout.splitlines():
                if line.startswith("OPENED\t"):
                    parts = line.strip().split("\t")
                    return {
                        "name": parts[1] if len(parts) > 1 else target,
                        "path": parts[2] if len(parts) > 2 else "",
                    }
        except Exception:
            pass

        return None

    def open_windows_app(self, target):
        direct = self._open_appsfolder_item(target)
        if direct:
            return True, "Opened Windows app: " + direct.get("name", target)

        results = self.search_windows_apps(target)
        if not results:
            return None

        target_name = self.normalize(target)
        exact = [a for a in results if self.normalize(a.get("name", "")) == target_name]

        for app in exact or results[:1]:
            path = app.get("path", "")
            if path and path.lower().startswith("shell:appsfolder"):
                if self._launch_appsfolder_path(path):
                    return True, "Opened Windows app: " + app.get("name", target)

        if len(results) > 1:
            message = "Multiple Windows apps found for '{}':\n".format(target)
            for i, app in enumerate(results, 1):
                message += "{}. {}\n".format(i, app.get("name", "Unknown"))
            return False, message + "\nPlease select a number.", results

        return None

    def _open(self, path):
        if not path:
            return False, "Invalid path."

        if isinstance(path, str) and path.lower().startswith("shell:appsfolder"):
            if self._launch_appsfolder_path(path):
                return True, "Opened successfully: " + path

        if not os.path.exists(path):
            return False, "Path does not exist: " + path

        try:
            os.startfile(path)
            return True, "Opened successfully: " + path
        except Exception:
            pass

        try:
            result = ctypes.windll.shell32.ShellExecuteW(
                None, "open", path, None, None, 1
            )
            if result > 32:
                return True, "Opened successfully: " + path
        except Exception:
            pass

        try:
            subprocess.Popen(
                ["cmd.exe", "/c", "start", "", path],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return True, "Opened successfully: " + path
        except Exception as e:
            return False, "Error opening '{}': {}".format(path, e)

    def find(self, target):
        target = self.clean_target(target)
        if not target:
            return []

        exact = self.find_exact_path(target)
        if exact:
            return [exact]

        results = []

        # Critical fix: user files/folders are resolved before expensive
        # application discovery.
        for item in self.search_common_locations(target):
            self._add_unique(results, item)

        if results:
            return results[:self.max_results]

        path_result = self.find_in_path(target)
        if path_result:
            self._add_unique(results, path_result)

        for item in self.search_registry_app_paths(target):
            self._add_unique(results, item)

        for item in self.search_start_menu(target):
            self._add_unique(results, item)

        for item in self.search_desktop(target):
            self._add_unique(results, item)

        # Do not recursively scan Program Files for clearly typed documents,
        # images, media, archives, source files, etc.
        lower = target.lower()
        is_file_target = any(lower.endswith(ext) for ext in self.file_extensions)

        if not is_file_target:
            for item in self.search_program_files(target):
                self._add_unique(results, item)

        return results[:self.max_results]

    def get_all_search_names(self):
        names = []

        for path in self.start_menu_paths + self.desktop_paths:
            if not os.path.exists(path):
                continue
            try:
                for root, dirs, files in os.walk(path):
                    for item in files:
                        if item.lower().endswith((".lnk", ".exe", ".bat", ".cmd", ".com")):
                            names.append(os.path.splitext(item)[0])
            except Exception:
                pass

        for app in self.get_start_apps() + self.get_appsfolder_apps():
            if app.get("name"):
                names.append(app["name"])

        return list(dict.fromkeys(names))

    def find_similar(self, target, limit=8):
        target_name = self.normalize(target)
        if not target_name:
            return []

        names = self.get_all_search_names()
        mapping = {}

        for name in names:
            normalized = self.normalize(name)
            if normalized:
                mapping.setdefault(normalized, name)

        candidates = list(mapping)
        direct = [
            c for c in candidates
            if target_name in c or c in target_name
        ]
        fuzzy = difflib.get_close_matches(
            target_name, candidates, n=limit, cutoff=0.30
        )

        results = []
        for item in direct + fuzzy:
            if item not in results:
                results.append(mapping.get(item, item))
            if len(results) >= limit:
                break

        return results

    def suggestion_message(self, target, suggestions):
        if not suggestions:
            return "I could not find '{}'.".format(target)

        message = "I could not find '{}'.\n\nDid you mean:\n".format(target)
        for i, name in enumerate(suggestions, 1):
            message += "{}. {}\n".format(i, name)
        return message + "\nPlease select a number."

    def open(self, target):
        target = self.clean_target(target)
        if not target:
            return "Please tell me what you want to open."

        exact = self.find_exact_path(target)
        if exact:
            success, message = self._open(exact)
            if success:
                return message

        # Keep Windows Store/Modern App handling.
        app_result = self.open_windows_app(target)
        if app_result:
            if len(app_result) == 2:
                return app_result[1]
            if len(app_result) == 3:
                return app_result[1]

        results = self.find(target)

        if len(results) == 1:
            success, message = self._open(results[0])
            if success:
                return message

        if len(results) > 1:
            message = "Multiple items found for '{}':\n".format(target)
            for i, path in enumerate(results, 1):
                message += "{}. {}\n".format(i, path)
            return message + "\nPlease select a number."

        return self.suggestion_message(target, self.find_similar(target))

    def search_and_open(self, target):
        return self.open(target)

    def open_selected(self, results, number):
        try:
            index = int(number) - 1
        except (ValueError, TypeError):
            return "Please enter a valid number."

        if index < 0 or index >= len(results):
            return "Invalid selection."

        selected = results[index]

        if isinstance(selected, dict):
            name = selected.get("name", "Windows app")
            path = selected.get("path", "")

            direct = self._open_appsfolder_item(name)
            if direct:
                return "Opened Windows app: " + direct.get("name", name)

            if path:
                if path.lower().startswith("shell:appsfolder"):
                    if self._launch_appsfolder_path(path):
                        return "Opened Windows app: " + name

                success, message = self._open(path)
                if success:
                    return message

            return "Could not open Windows app: " + name

        success, message = self._open(selected)
        return message

    def open_suggestion(self, suggestions, number):
        try:
            index = int(number) - 1
        except (ValueError, TypeError):
            return "Please enter a valid number."

        if index < 0 or index >= len(suggestions):
            return "Invalid selection."

        return self.open(suggestions[index])

