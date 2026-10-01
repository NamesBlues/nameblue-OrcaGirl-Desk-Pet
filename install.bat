@echo off
rem Orca Desktop Pet - first time setup
cd /d "%~dp0"

where python >nul 2>nul
if errorlevel 1 (
    echo [x] Python not found. Install Python 3.9+ and tick "Add Python to PATH".
    echo     https://www.python.org/downloads/
    pause
    exit /b 1
)

echo [1/4] Creating virtual environment .venv ...
python -m venv .venv
if not exist ".venv\Scripts\python.exe" (
    echo [x] Failed to create the virtual environment.
    pause
    exit /b 1
)

echo [2/4] Upgrading pip ...
".venv\Scripts\python.exe" -m pip install --upgrade pip

echo [3/4] Installing dependencies (PySide6 is about 240MB, please wait) ...
".venv\Scripts\python.exe" -m pip install -r requirements.txt
".venv\Scripts\python.exe" -m pip install -r requirements-tools.txt

echo [4/4] Preparing assets ...
".venv\Scripts\python.exe" tools\prepare_assets.py

echo.
echo Done. Double-click run.bat to start the pet.
pause
