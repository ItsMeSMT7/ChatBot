import requests

OLLAMA_URL = "http://localhost:11434/api/embeddings"
MODEL = "llama3.2:1b"

def generate_embedding(text):
    """
    Convert text to 768-dimensional vector using Ollama
    
    Args:
        text (str): Text to convert to embedding
        
    Returns:
        list: 768-dimensional vector
    """
    response = requests.post(
        OLLAMA_URL,
        json={
            "model": "gemma3:1b",
            "prompt": text
        }
    )
    response.raise_for_status()
    return response.json()["embedding"]
