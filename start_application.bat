@echo off
echo Starting P Square Chatbot Application...
echo.

echo Checking Python environment...
python --version
echo.

echo Testing database connection...
cd backend
python test_connection.py
echo.

echo Starting Django backend server...
start "Django Backend" cmd /k "python manage.py runserver 8000"
echo Backend started on http://localhost:8000
echo.

echo Waiting 3 seconds for backend to initialize...
timeout /t 3 /nobreak > nul

echo Starting React frontend...
cd ..\frontend
start "React Frontend" cmd /k "npm start"
echo Frontend will start on http://localhost:3000
echo.

echo ========================================
echo   P Square Chatbot is starting up!
echo ========================================
echo Backend API: http://localhost:8000/api/chat/
echo Frontend UI: http://localhost:3000
echo.
echo Press any key to continue...
pause > nul