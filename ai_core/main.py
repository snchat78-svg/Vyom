"""
Project : Vyom AI
Version : 0.1
Module  : Main
"""

from command_engine.parser import CommandParser
from command_engine.executor import execute

parser = CommandParser()

print("===================================")
print(" Vyom AI v0.1 Started ")
print("===================================")

while True:

    command = input("You : ")

    if command.lower() == "exit":
        print("Vyom : Goodbye")
        break

    parsed = parser.parse(command)

    response = execute(parsed)

    print("Vyom :", response)
