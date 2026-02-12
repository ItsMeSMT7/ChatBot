import requests
import json

OLLAMA_BASE_URL = "http://localhost:11434"
LLM_MODEL = "gemma3:1b"  # MUST match an installed model (check with `ollama list`)

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
                "model": "nomic-embed-text",
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
                "model": LLM_MODEL,
                "prompt": prompt,
                "stream": False
            }
        )
        response.raise_for_status()
        return response.json()["response"]
    except requests.exceptions.HTTPError as http_err:
        # Try to get more details from the response body for debugging
        details = ""
        try:
            details = http_err.response.json()
        except json.JSONDecodeError:
            details = http_err.response.text
        raise Exception(f"LLM generation failed: {http_err}. Details: {details}")
    except Exception as e:
        raise Exception(f"LLM generation failed: {str(e)}")
