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
    
    REM Kill all Python processes that might be running Jarvis
    powershell -Command "Get-Process python -ErrorAction SilentlyContinue | Where-Object {$_.CommandLine -like '*jarvisgt2.py*'} | Stop-Process -Force"
    
    echo.
    echo Jarvis GT2 stopped successfully.
) else (
    echo No running Jarvis instances found.
)

echo.
echo ========================================
pause
