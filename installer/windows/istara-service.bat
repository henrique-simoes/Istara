@echo off
REM ═══════════════════════════════════════════════════════════════════
REM Istara Windows Service Wrapper
REM Starts backend (FastAPI) and frontend (Next.js) as background processes
REM ═══════════════════════════════════════════════════════════════════

cd /d "%~dp0"

echo Starting Istara...

REM Activate Python venv
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
) else (
    echo WARNING: Python venv not found. Using system Python.
)

REM Start backend
echo Starting backend on port 8000...
cd backend
start /B "" python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 > ..\data\backend.log 2>&1
cd ..

REM Start frontend
echo Starting frontend on port 3000...
cd frontend
start /B "" npx next start --port 3000 > ..\data\frontend.log 2>&1
cd ..

echo.
echo Istara is starting...
echo   Backend: http://localhost:8000
echo   Frontend: http://localhost:3000
echo.
echo Close this window to stop Istara.
pause
