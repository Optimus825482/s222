@echo off
chcp 65001 >nul 2>&1
echo ========================================
echo   Stopping all services...
echo ========================================

:: Kill backend (port 8001)
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8001 ^| findstr LISTENING') do (
    echo   Stopping backend PID: %%a
    taskkill /PID %%a /F >nul 2>&1
)

:: Kill frontend (port 3000)
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :3000 ^| findstr LISTENING') do (
    echo   Stopping frontend PID: %%a
    taskkill /PID %%a /F >nul 2>&1
)

:: Also kill any orphan node/python processes related to our app
taskkill /F /IM "node.exe" /FI "WINDOWTITLE eq *next*" >nul 2>&1

echo.
echo   All services stopped.
echo ========================================
pause
