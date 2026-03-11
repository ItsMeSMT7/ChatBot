import re
import json
import logging
import requests

"""
Communication with local Ollama instance.
Handles embeddings and text generation.
"""

logger = logging.getLogger(__name__)

OLLAMA_BASE_URL = "http://localhost:11434"
EMBEDDING_MODEL = "nomic-embed-text"
LLM_MODEL = "gemma3:1b"  # MUST match an installed model (check with `ollama list`)


def generate_embedding(text):
    """
    Convert text into a 768-dimensional vector.
    Used when STORING document chunks.
    """
    try:
        response = requests.post(
            f"{OLLAMA_BASE_URL}/api/embeddings",
            json={
                "model": EMBEDDING_MODEL,
                "prompt": f"search_document: {text}",
            },
            timeout=30,
        )
        response.raise_for_status()
        embedding = response.json().get("embedding")
        if not embedding:
            logger.error("Ollama returned empty embedding")
            return None
        return embedding
    except requests.exceptions.ConnectionError:
        logger.error("Cannot connect to Ollama. Is it running?")
        return None
    except Exception as e:
        logger.error(f"Embedding failed: {e}")
        return None


# ────────────────────────────────────────────────────────────
#  NEW — generate_query_embedding
# ────────────────────────────────────────────────────────────
def generate_query_embedding(text):
    """
    Convert a USER QUERY into a vector.

    WHY separate from generate_embedding?
    The nomic-embed-text model produces better results when you
    prefix documents with "search_document:" and queries with
    "search_query:". This small change improves retrieval accuracy.
    """
    try:
        response = requests.post(
            f"{OLLAMA_BASE_URL}/api/embeddings",
            json={
                "model": EMBEDDING_MODEL,
                "prompt": f"search_query: {text}",
            },
            timeout=30,
        )
        response.raise_for_status()
        return response.json().get("embedding")
    except Exception as e:
        logger.error(f"Query embedding failed: {e}")
        return None



def generate_response(prompt, model=LLM_MODEL, temperature=0.3, max_tokens=4096):
    """
    WHAT: Sends prompt to local Ollama LLM and gets response
    WHY: This replaces Gemini API with local LLM for answer generation

    Supports optional temperature and max_tokens for structured/JSON output.
    Works with both:
        generate_response(prompt)
        generate_response(prompt, model=..., temperature=..., max_tokens=...)
    """
    url = f"{OLLAMA_BASE_URL}/api/generate"

    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": temperature,
            "num_predict": max_tokens,
        }
    }

    try:
        response = requests.post(url, json=payload, timeout=480)
        response.raise_for_status()
        result = response.json()
        return result.get("response", "")

    except requests.exceptions.ConnectionError:
        print("[Ollama Service] ERROR: Cannot connect to Ollama. Is it running?")
        return "{}"

    except requests.exceptions.Timeout:
        print("[Ollama Service] ERROR: Request timed out.")
        return "{}"

    except requests.exceptions.HTTPError as http_err:
        # Try to get more details from the response body for debugging
        details = ""
        try:
            details = http_err.response.json()
        except json.JSONDecodeError:
            details = http_err.response.text

        if http_err.response.status_code == 404:
            if (isinstance(details, dict)
                    and "error" in details
                    and "not found" in details["error"]):
                raise Exception(
                    f"Model '{model}' not found. "
                    f"Please run this command in your terminal: ollama pull {model}"
                )

        raise Exception(f"LLM generation failed: {http_err}. Details: {details}")

    except Exception as e:
        print(f"[Ollama Service] ERROR: {e}")
        raise Exception(f"LLM generation failed: {str(e)}")




# ────────────────────────────────────────────────────────────
#  NEW — score_relevance (for reranking)
# ────────────────────────────────────────────────────────────
def score_relevance(query, document_text):
    """
    Ask the LLM: "How relevant is this chunk to this query?"
    Returns a float between 0.0 and 1.0.
    Used by the reranker to pick the best chunks.
    """
    prompt = f"""Rate relevance of this document to the query.
Reply with ONLY a number from 0 to 10.

Query: {query}
Document: {document_text[:400]}

Score:"""

    try:
        resp = generate_response(prompt, temperature=0.0, max_tokens=10)
        numbers = re.findall(r'(\d+(?:\.\d+)?)', resp)
        if numbers:
            return min(float(numbers[0]) / 10.0, 1.0)
        return 0.5
    except Exception:
        return 0.5


        

# import requests
# import json

# OLLAMA_BASE_URL = "http://localhost:11434" 
# LLM_MODEL = "gemma3:1b"  # MUST match an installed model (check with `ollama list`)

# def generate_embedding(text):
#     """
#     WHAT: Converts text into a 768-dimensional vector
#     WHY: Vectors allow mathematical similarity comparison between texts
    
#     Embeddings are numerical representations of text where similar meanings
#     have similar vector values. This enables semantic search.
#     """
#     try:
#         response = requests.post(
#             f"{OLLAMA_BASE_URL}/api/embeddings",
#             json={
#                 "model": "nomic-embed-text",
#                 "prompt": text
#             }
#         )
#         response.raise_for_status()
#         return response.json()["embedding"]
#     except requests.exceptions.HTTPError as e:
#         if e.response.status_code == 404:
#             raise Exception("Embedding model 'nomic-embed-text' not found. Please run: ollama pull nomic-embed-text")
#         raise Exception(f"Embedding generation failed: {str(e)}")
#     except Exception as e:
#         raise Exception(f"Embedding generation failed: {str(e)}")

# def generate_response(prompt):
#     """
#     WHAT: Sends prompt to local Ollama LLM and gets response
#     WHY: This replaces Gemini API with local LLM for answer generation
#     """
#     try:
#         response = requests.post(
#             f"{OLLAMA_BASE_URL}/api/generate",
#             json={
#                 "model": LLM_MODEL,
#                 "prompt": prompt,
#                 "stream": False
#             }
#         )
#         response.raise_for_status()
#         return response.json()["response"]
#     except requests.exceptions.HTTPError as http_err:
#         # Try to get more details from the response body for debugging
#         details = ""
#         try:
#             details = http_err.response.json()
#         except json.JSONDecodeError:
#             details = http_err.response.text
            
#         if http_err.response.status_code == 404:
#             if isinstance(details, dict) and "error" in details and "not found" in details["error"]:
#                 raise Exception(f"Model '{LLM_MODEL}' not found. Please run this command in your terminal: ollama pull {LLM_MODEL}")
                
#         raise Exception(f"LLM generation failed: {http_err}. Details: {details}")
#     except Exception as e:
#         raise Exception(f"LLM generation failed: {str(e)}")

# #  Solven __annotations__
# def generate_response(prompt, model=LLM_MODEL, temperature=0.3, max_tokens=4096):
#     """
#     Sends a prompt to the Ollama API and returns the text response.
#     Uses low temperature for deterministic, structured JSON output.
#     """
#     url = f"{OLLAMA_BASE_URL}/api/generate"

#     payload = {
#         "model": model,
#         "prompt": prompt,
#         "stream": False,
#         "options": {
#             "temperature": temperature,
#             "num_predict": max_tokens,
#         }
#     }

#     try:
#         response = requests.post(url, json=payload, timeout=480)
#         response.raise_for_status()
#         result = response.json()
#         return result.get("response", "")
#     except requests.exceptions.ConnectionError:
#         print("[Ollama Service] ERROR: Cannot connect to Ollama. Is it running?")
#         return "{}"
#     except requests.exceptions.Timeout:
#         print("[Ollama Service] ERROR: Request timed out.")
#         return "{}"
#     except Exception as e:
#         print(f"[Ollama Service] ERROR: {e}")
#         return "{}"