@echo off
chcp 65001 >nul 2>&1
title Multi-Agent Dashboard
cd /d "%~dp0"

echo ========================================
echo   Multi-Agent Dashboard - Starting...
echo ========================================
echo.

:: Kill any zombie processes on our ports
echo [1/2] Cleaning up old processes...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8001 ^| findstr LISTENING') do taskkill /PID %%a /F >nul 2>&1
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :3015 ^| findstr LISTENING') do taskkill /PID %%a /F >nul 2>&1
timeout /t 2 /nobreak >nul

:: Create logs directory
if not exist "logs" mkdir logs

:: Start both services with concurrently
echo [2/2] Starting Backend + Frontend...
echo.
echo   Backend:  http://localhost:8001
echo   Frontend: http://localhost:3015
echo.
echo   Press Ctrl+C to stop all services
echo ========================================
echo.

concurrently -k -p "[{name}]" -n "BACKEND,FRONTEND" -c "cyan,magenta" "cd backend && python -m uvicorn main:app --host 0.0.0.0 --port 8001 --reload" "cd frontend && node node_modules/next/dist/bin/next dev --port 3015"
