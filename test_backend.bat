@echo off
echo Testing Django backend...
cd backend
python manage.py check
echo.
echo Starting Django server...
python manage.py runserver 8000