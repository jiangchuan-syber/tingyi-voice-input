@echo off
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo [1/2] Creating venv and installing dependencies...
    python -m venv .venv
    if errorlevel 1 (
        echo ERROR: Python not found. Install Python 3.10+ first.
        pause
        exit /b 1
    )
    call .venv\Scripts\activate.bat
    python -m pip install -U pip
    pip install -r requirements.txt
    if errorlevel 1 (
        echo ERROR: pip install failed.
        pause
        exit /b 1
    )
    echo.
    echo Done. Setup complete.
) else (
    call .venv\Scripts\activate.bat
)

echo.
echo tingyi v0.2.0 full package ^(models included^)
python -m tingyi
echo.
echo Next: double-click listen.bat  OR  python -m tingyi --listen
echo.
pause
