@echo off
echo Starting P Square Chatbot...

cd backend
start "Backend" cmd /k "python manage.py runserver 8000"

cd ..\frontend  
start "Frontend" cmd /k "npm start"

echo Both servers started!
echo Backend: http://localhost:8000
echo Frontend: http://localhost:3000 or 3001
pause