@echo off
REM Jarvis GT2 Startup Script
REM Closes any running instances and starts fresh

echo ========================================
echo Starting Jarvis GT2...
echo ========================================
echo.

REM Kill any existing Python processes running jarvisgt2.py
echo Checking for existing Jarvis instances...
tasklist /FI "IMAGENAME eq python.exe" 2>NUL | find /I /N "python.exe">NUL
if "%ERRORLEVEL%"=="0" (
    echo Found running Python processes - checking for Jarvis...
    
    REM Get PIDs of Python processes running jarvisgt2.py
    for /f "tokens=2" %%a in ('wmic process where "name='python.exe' and commandline like '%%jarvisgt2.py%%'" get processid /format:list ^| findstr "="') do (
        echo Stopping existing Jarvis instance (PID: %%a)...
        taskkill /PID %%a /F >NUL 2>&1
    )
    
    REM Wait a moment for cleanup
    timeout /t 2 /nobreak >NUL
    echo Cleanup complete.
) else (
    echo No existing instances found.
)

echo.
echo ========================================
echo Activating Python environment...
echo ========================================
echo.

REM Check if virtual environment exists
if not exist ".venv\Scripts\activate.bat" (
    echo ERROR: Virtual environment not found!
    echo Please create .venv first:
    echo   python -m venv .venv
    echo   .venv\Scripts\activate
    echo   pip install -r requirements.txt
    pause
    exit /b 1
)

REM Activate virtual environment and run Jarvis
call .venv\Scripts\activate.bat

echo.
echo ========================================
echo Launching Jarvis GT2...
echo ========================================
echo.

REM Run Jarvis GT2
python jarvisgt2.py

REM If Jarvis exits, deactivate venv
call .venv\Scripts\deactivate.bat

echo.
echo ========================================
echo Jarvis GT2 stopped.
echo ========================================
pause
