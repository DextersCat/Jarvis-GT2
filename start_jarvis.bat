@echo off
REM Jarvis GT2 Startup Script
REM Closes any running instances and starts fresh
REM This version can run from anywhere (Desktop, Start Menu, etc.)

REM Set the project directory (absolute path)
set JARVIS_DIR=C:\Users\spencer\Documents\Projects\New_Jarvis

echo ========================================
echo Starting Jarvis GT2...
echo ========================================
echo.

REM Kill any existing Python processes running Jarvis
echo Checking for existing Jarvis instances...
powershell -Command "Get-Process python,pythonw -ErrorAction SilentlyContinue | Where-Object {$_.CommandLine -match 'jarvis_main.py|jarvis_ear.py|jarvis_main_legacy.py'} | Stop-Process -Force"

REM Wait a moment for cleanup
timeout /t 2 /nobreak >NUL
echo Cleanup complete.

echo.
echo ========================================
echo Navigating to Jarvis directory...
echo ========================================
echo.

REM Change to Jarvis project directory
cd /d "%JARVIS_DIR%"

if not exist "%JARVIS_DIR%" (
    echo ERROR: Jarvis directory not found!
    echo Expected location: %JARVIS_DIR%
    echo Please update the JARVIS_DIR variable in this script.
    pause
    exit /b 1
)

echo.
echo ========================================
echo Activating Python environment...
echo ========================================
echo.

REM Check if virtual environment exists
if not exist "%JARVIS_DIR%\.venv\Scripts\activate.bat" (
    echo ERROR: Virtual environment not found!
    echo Please create .venv first:
    echo   cd %JARVIS_DIR%
    echo   python -m venv .venv
    echo   .venv\Scripts\activate
    echo   pip install -r requirements.txt
    pause
    exit /b 1
)

REM Check that requirements.txt exists
if not exist "%JARVIS_DIR%\requirements.txt" (
    echo ERROR: requirements.txt not found!
    echo Please create requirements.txt before starting Jarvis.
    pause
    exit /b 1
)

REM Activate virtual environment and run Jarvis
call "%JARVIS_DIR%\.venv\Scripts\activate.bat"

REM Run dependency check
python "%JARVIS_DIR%\check_dependencies.py"

echo.
echo ========================================
echo Launching Jarvis GT2...
echo ========================================
echo.

REM Run Jarvis GT2
python "%JARVIS_DIR%\jarvis_main.py"

REM If Jarvis exits, deactivate venv
call "%JARVIS_DIR%\.venv\Scripts\deactivate.bat"

echo.
echo ========================================
echo Jarvis GT2 stopped.
echo ========================================
pause
