import subprocess
import threading
import time
import webbrowser
from django.core.management.base import BaseCommand
from django.core.management import call_command

class Command(BaseCommand):
    help = "Start both Django backend and React frontend"

    def handle(self, *args, **options):
        def start_frontend():
            try:
                # Change to frontend directory and start React
                subprocess.run(['npm', 'start'], cwd='../frontend', shell=True)
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Frontend error: {e}'))

        # Start frontend in separate thread
        frontend_thread = threading.Thread(target=start_frontend)
        frontend_thread.daemon = True
        frontend_thread.start()

        # Wait a bit then open browser
        def open_browser():
            time.sleep(3)
            webbrowser.open('http://localhost:3000')
        
        browser_thread = threading.Thread(target=open_browser)
        browser_thread.daemon = True
        browser_thread.start()

        self.stdout.write(self.style.SUCCESS('Starting backend and frontend...'))
        self.stdout.write(self.style.SUCCESS('Frontend will open at http://localhost:3000'))
        
        # Start Django server (this blocks)
        call_command('runserver')