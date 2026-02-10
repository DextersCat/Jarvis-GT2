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
REM (Uses CimInstance for reliable CommandLine access on PowerShell 5.1 and 7+)
echo Checking for existing Jarvis instances...
powershell -Command "Get-CimInstance Win32_Process -Filter \"Name='python.exe' OR Name='pythonw.exe'\" | Where-Object {$_.CommandLine -match 'jarvis_main.py|jarvis_ear.py|jarvis_main_legacy.py'} | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue; Write-Host 'Killed python PID' $_.ProcessId }"

REM Kill any existing Node processes for n8n or dashboard
echo Checking for existing n8n/dashboard instances...
powershell -Command "Get-CimInstance Win32_Process -Filter \"Name='node.exe'\" | Where-Object {$_.CommandLine -match 'n8n|server/index.ts|Cyber-Grid-Dashboard|vite|tsx'} | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue; Write-Host 'Killed node PID' $_.ProcessId }"

REM Wait for processes to fully terminate (5s gives Node.js time to exit cleanly)
timeout /t 5 /nobreak >NUL
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
