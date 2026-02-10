from django.core.management.base import BaseCommand
from api.models import Document
from django.db import connection


class Command(BaseCommand):
    help = "Test RAG similarity search"

    def add_arguments(self, parser):
        parser.add_argument('query', type=str, help='Search query')

    def get_embedding(self, text):
        """Create embedding from text"""
        import hashlib
        hash_obj = hashlib.sha256(text.encode())
        hash_bytes = hash_obj.digest()
        
        embedding = []
        for i in range(768):
            embedding.append(float(hash_bytes[i % len(hash_bytes)]) / 255.0)
        
        return embedding

    def handle(self, *args, **kwargs):
        query = kwargs['query']
        self.stdout.write(f"Searching for: {query}\n")
        
        query_embedding = self.get_embedding(query)
        
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT content, metadata, (embedding <-> %s::vector) as distance
                FROM documents
                WHERE metadata->>'source' = 'titanic'
                ORDER BY distance
                LIMIT 5
            """, [query_embedding])
            
            results = cursor.fetchall()
        
        self.stdout.write(self.style.SUCCESS(f"Found {len(results)} results:\n"))
        
        for idx, (content, metadata, distance) in enumerate(results, 1):
            self.stdout.write(f"\n{idx}. Distance: {distance:.4f}")
            self.stdout.write(f"   {content[:100]}...")
