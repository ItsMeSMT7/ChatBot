@echo off
echo ========================================
echo Starting P Square RAG Application
echo ========================================
echo.

echo Starting Ollama...
start "Ollama Server" cmd /k "ollama serve"
timeout /t 3 /nobreak >nul

echo Starting Django Backend...
start "Django Backend" cmd /k "cd backend && python manage.py runserver"
timeout /t 3 /nobreak >nul

echo Starting React Frontend...
start "React Frontend" cmd /k "cd frontend && npm start"

echo.
echo ========================================
echo All services started!
echo ========================================
echo.
echo Ollama:   http://localhost:11434
echo Backend:  http://localhost:8000
echo Frontend: http://localhost:3000
echo.
echo Press any key to stop all services...
pause >nul

echo.
echo Stopping all services...
taskkill /FI "WINDOWTITLE eq Ollama Server*" /T /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq Django Backend*" /T /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq React Frontend*" /T /F >nul 2>&1

echo All services stopped.
