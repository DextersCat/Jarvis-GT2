@echo off
REM Stop all running Jarvis GT2 instances

echo ========================================
echo Stopping Jarvis GT2...
echo ========================================
echo.

REM Kill any Python processes running jarvisgt2.py
tasklist /FI "IMAGENAME eq python.exe" 2>NUL | find /I /N "python.exe">NUL
if "%ERRORLEVEL%"=="0" (
    echo Searching for Jarvis instances...
    
    REM Get PIDs of Python processes running jarvisgt2.py
    for /f "tokens=2" %%a in ('wmic process where "name='python.exe' and commandline like '%%jarvisgt2.py%%'" get processid /format:list ^| findstr "="') do (
        echo Stopping Jarvis GT2 (PID: %%a)...
        taskkill /PID %%a /F >NUL 2>&1
    )
    
    echo.
    echo Jarvis GT2 stopped successfully.
) else (
    echo No running Jarvis instances found.
)

echo.
echo ========================================
pause
