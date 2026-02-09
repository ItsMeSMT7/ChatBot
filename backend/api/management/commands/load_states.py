from django.core.management.base import BaseCommand
from django.conf import settings
import os
from api.models import StateData

class Command(BaseCommand):
    help = "Check states data in database"

    def handle(self, *args, **kwargs):
        count = StateData.objects.count()
        if count > 0:
            self.stdout.write(self.style.SUCCESS(f"Found {count} states in database"))
            # Show first 5 states as sample
            states = StateData.objects.all()[:5]
            for state in states:
                self.stdout.write(f"- {state.state}: Population {state.population}k, Income ₹{state.income}")
        else:
            self.stdout.write(self.style.WARNING("No states found in database. Please ensure data is loaded."))
