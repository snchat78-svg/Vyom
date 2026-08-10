"""
Project : Vyom AI
Version : 0.8
Module : Process Manager
"""

import subprocess


class ProcessManager:

    def close_app(self, process_name):

        process_name = process_name.strip().lower()

        if not process_name:

            return "Please specify an application to close."

        # .exe हटाएं अगर user ने दिया हो
        if process_name.endswith(".exe"):

            process_name = process_name[:-4]

        # -----------------------------------------
        # Get running processes
        # -----------------------------------------

        try:

            result = subprocess.run(
                ["tasklist", "/FO", "CSV", "/NH"],
                capture_output=True,
                text=True
            )

            output = result.stdout

        except Exception as e:

            return f"Error reading running processes: {e}"

        # -----------------------------------------
        # Find matching process
        # -----------------------------------------

        matches = []

        for line in output.splitlines():

            line_lower = line.lower()

            if process_name in line_lower:

                parts = line.split('","')

                if parts:

                    process = parts[0].replace('"', '').strip()

                    if process.endswith(".exe"):

                        matches.append(process)

        # -----------------------------------------
        # Nothing found
        # -----------------------------------------

        if not matches:

            return f"No running application found for '{process_name}'."

        # -----------------------------------------
        # Close matching processes
        # -----------------------------------------

        closed = []

        for process in matches:

            try:

                kill_result = subprocess.run(
                    [
                        "taskkill",
                        "/F",
                        "/IM",
                        process
                    ],
                    capture_output=True,
                    text=True
                )

                if kill_result.returncode == 0:

                    closed.append(process)

            except Exception:
                pass

        if closed:

            return (
                f"{process_name} closed successfully. "
                f"Process: {', '.join(closed)}"
            )

        return f"Unable to close '{process_name}'."
