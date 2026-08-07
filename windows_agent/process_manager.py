"""
Project : Vyom AI
Version : 0.5
Module  : Process Manager
"""

import subprocess

class ProcessManager:

    def close_app(self, process_name):

        try:
            subprocess.run(
                ["taskkill", "/F", "/IM", f"{process_name}.exe"],
                capture_output=True,
                text=True
            )

            return f"{process_name} closed successfully."

        except Exception as e:

            return f"Error : {e}"
