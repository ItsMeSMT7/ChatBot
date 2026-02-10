from django.core.management.base import BaseCommand
from api.models import Titanic, Document
import hashlib


class Command(BaseCommand):
    help = "Embed Titanic data into documents table"

    def get_embedding(self, text):
        """Create 768-dim embedding from text using hash"""
        hash_obj = hashlib.sha256(text.encode())
        hash_bytes = hash_obj.digest()
        
        embedding = []
        for i in range(768):
            embedding.append(float(hash_bytes[i % len(hash_bytes)]) / 255.0)
        
        return embedding

    def handle(self, *args, **kwargs):
        passengers = Titanic.objects.all()
        total = passengers.count()
        self.stdout.write(f"Converting {total} Titanic records to vectors...")
        
        Document.objects.filter(metadata__source='titanic').delete()

        for idx, p in enumerate(passengers, 1):
            text = (
                f"Passenger {p.name} was a {p.sex}, "
                f"{p.age if p.age else 'unknown'} years old, traveling in class {p.pclass}. "
                f"The fare was {p.fare}. "
                f"Survived: {'Yes' if p.survived == 1 else 'No'}."
            )

            embedding = self.get_embedding(text)

            Document.objects.create(
                content=text,
                embedding=embedding,
                metadata={
                    "source": "titanic",
                    "passenger_id": p.pk
                }
            )
            
            if idx % 100 == 0:
                self.stdout.write(f"Processed {idx}/{total}...")

        self.stdout.write(self.style.SUCCESS(f"Successfully embedded {total} Titanic records"))
