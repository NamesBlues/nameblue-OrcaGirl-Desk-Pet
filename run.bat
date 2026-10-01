@echo off
rem Orca Desktop Pet - launcher (starts without a console window)
cd /d "%~dp0"

set "PYW=%~dp0.venv\Scripts\pythonw.exe"
if not exist "%PYW%" set "PYW=%~dp0.venv\Scripts\python.exe"
if not exist "%PYW%" set "PYW=pythonw"

start "" "%PYW%" "%~dp0main.py"
