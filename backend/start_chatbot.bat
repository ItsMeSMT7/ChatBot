@echo off
echo Starting Chatbot Application...
echo.

cd /d "%~dp0"

echo Starting Django Backend...
start "Django Backend" cmd /k "python manage.py runserver"

echo Waiting for backend to start...
timeout /t 3 /nobreak >nul

echo Starting React Frontend...
cd ..\frontend
start "React Frontend" cmd /k "npm start"

echo.
echo Both services are starting...
echo Backend: http://localhost:8000
echo Frontend: http://localhost:3000
echo.
echo Press any key to exit...
pause >nul