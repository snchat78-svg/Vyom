"""
Project : Vyom AI
Version : 0.2
Module  : Logger
"""

from datetime import datetime


def log(message):
    time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{time}] {message}", flush=True)
