@echo off
REM Jarvis GT2 Startup Script
REM Closes any running instances and starts fresh
REM This version can run from anywhere (Desktop, Start Menu, etc.)

REM Set the project directory (absolute path)
set JARVIS_DIR=C:\Users\spencer\Documents\Projects\New_Jarvis
set DASHBOARD_DIR=%JARVIS_DIR%\GUI\Cyber-Grid-Dashboard

echo ========================================
echo Starting Jarvis GT2...
echo ========================================
echo.

REM Kill any existing Python processes running Jarvis
echo Checking for existing Jarvis instances...
powershell -Command "Get-Process python,pythonw -ErrorAction SilentlyContinue | Where-Object {$_.CommandLine -match 'jarvis_main.py|jarvis_ear.py|jarvis_main_legacy.py'} | Stop-Process -Force"

REM Kill any existing Node processes for n8n or dashboard
echo Checking for existing n8n/dashboard instances...
powershell -Command "Get-Process node -ErrorAction SilentlyContinue | Where-Object {$_.CommandLine -match 'n8n|server/index.ts|Cyber-Grid-Dashboard|vite|tsx'} | Stop-Process -Force"

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

if not exist "%DASHBOARD_DIR%" (
    echo ERROR: Dashboard directory not found!
    echo Expected location: %DASHBOARD_DIR%
    echo Please update the DASHBOARD_DIR variable in this script.
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

echo.
echo ========================================
echo Launching Jarvis GT2, n8n, and Dashboard...
echo ========================================
echo.

REM Start Jarvis in its own window
start "Jarvis GT2" cmd /k "cd /d %JARVIS_DIR% && call .venv\Scripts\activate.bat && set PYTHONIOENCODING=utf-8 && python check_dependencies.py && python jarvis_main.py"

REM Start dashboard server in its own window
start "Cyber-Grid Dashboard" cmd /k "cd /d %DASHBOARD_DIR% && npm run dev"

REM Start n8n in its own window
start "n8n" cmd /k "n8n start"

echo.
echo ========================================
echo Startup complete. Check the new windows.
echo ========================================
pause
