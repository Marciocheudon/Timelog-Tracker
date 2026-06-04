@echo off
setlocal

cd /d "%~dp0"

if not exist ".venv" (
    py -m venv .venv
)

call ".venv\Scripts\activate.bat"
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

pyinstaller ^
  --noconfirm ^
  --clean ^
  --onefile ^
  --windowed ^
  --name TimeLogTracker ^
  main.py

echo.
echo Build finished.
echo EXE: %CD%\dist\TimeLogTracker.exe
pause
