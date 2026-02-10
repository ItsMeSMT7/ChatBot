import requests
import json

OLLAMA_BASE_URL = "http://localhost:11434"

def generate_embedding(text):
    """
    WHAT: Converts text into a 768-dimensional vector
    WHY: Vectors allow mathematical similarity comparison between texts
    
    Embeddings are numerical representations of text where similar meanings
    have similar vector values. This enables semantic search.
    """
    try:
        response = requests.post(
            f"{OLLAMA_BASE_URL}/api/embeddings",
            json={
                "model": "gemma:1b",
                "prompt": text
            }
        )
        response.raise_for_status()
        return response.json()["embedding"]
    except Exception as e:
        raise Exception(f"Embedding generation failed: {str(e)}")

def generate_response(prompt):
    """
    WHAT: Sends prompt to local Ollama LLM and gets response
    WHY: This replaces Gemini API with local LLM for answer generation
    """
    try:
        response = requests.post(
            f"{OLLAMA_BASE_URL}/api/generate",
            json={
                "model": "gemma:1b",
                "prompt": prompt,
                "stream": False
            }
        )
        response.raise_for_status()
        return response.json()["response"]
    except Exception as e:
        raise Exception(f"LLM generation failed: {str(e)}")
