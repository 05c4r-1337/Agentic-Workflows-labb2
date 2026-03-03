"""
Ollama API wrapper tool.
Calls the local Ollama server at localhost:11434.
"""

import requests
from config import MODEL

OLLAMA_URL = "http://localhost:11434/api/generate"


def call_ollama(prompt: str, system: str = "") -> str:
    """Send a prompt to Ollama and return the response text."""
    payload = {
        "model": MODEL,
        "prompt": prompt,
        "stream": False,
    }
    if system:
        payload["system"] = system

    try:
        response = requests.post(OLLAMA_URL, json=payload, timeout=120)
        response.raise_for_status()
        return response.json().get("response", "").strip()
    except requests.exceptions.ConnectionError:
        raise RuntimeError(
            "Cannot connect to Ollama. Make sure Ollama is running: `ollama serve`"
        )
    except requests.exceptions.Timeout:
        raise RuntimeError("Ollama request timed out after 120 seconds.")
    except requests.exceptions.HTTPError as e:
        raise RuntimeError(f"Ollama HTTP error: {e}")
