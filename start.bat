@echo off
chcp 65001 >nul 2>&1
title Multi-Agent Dashboard
cd /d "%~dp0"

echo ========================================
echo   Multi-Agent Dashboard - Starting...
echo ========================================
echo.

:: Kill any existing processes on ports 8001 and 3000
echo [1/4] Cleaning up old processes...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8001 ^| findstr LISTENING') do taskkill /PID %%a /F >nul 2>&1
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :3000 ^| findstr LISTENING') do taskkill /PID %%a /F >nul 2>&1
timeout /t 2 /nobreak >nul

:: Create logs directory
if not exist "logs" mkdir logs

:: Start backend — hidden window via PowerShell
echo [2/4] Starting Backend (FastAPI :8001)...
powershell -Command "Start-Process python -ArgumentList '-m uvicorn main:app --host 0.0.0.0 --port 8001 --reload --app-dir backend' -WindowStyle Hidden -WorkingDirectory '%cd%'" 

:: Wait for backend
echo [3/4] Waiting for backend...
timeout /t 4 /nobreak >nul

:: Start frontend — hidden window via PowerShell
echo [4/4] Starting Frontend (Next.js :3000)...
powershell -Command "Start-Process cmd -ArgumentList '/c cd /d %cd%\frontend && node node_modules\next\dist\bin\next dev --port 3000' -WindowStyle Hidden"

echo.
echo ========================================
echo   All services started!
echo ========================================
echo   Backend:  http://localhost:8001
echo   Frontend: http://localhost:3000
echo   Stop:     run stop.bat
echo ========================================
echo.
pause
