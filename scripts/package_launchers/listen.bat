@echo off
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo Run setup.bat first.
    pause
    exit /b 1
)

call .venv\Scripts\activate.bat
echo Speak into the microphone. Stops after ~0.5s silence.
echo.
python -m tingyi --listen
echo.
pause
