@echo off
rem Orca Desktop Pet - debug launcher (keeps the console so you can read errors)
cd /d "%~dp0"

set "PY=%~dp0.venv\Scripts\python.exe"
if not exist "%PY%" set "PY=python"

"%PY%" "%~dp0main.py"
echo.
echo --- program exited ---
pause
