"""
Ollama API wrapper tool.
Calls the local Ollama server at localhost:11434.
"""

import requests
from config import MODEL, OLLAMA_TIMEOUT

OLLAMA_URL = "http://localhost:11434/api/generate"


def call_ollama(prompt: str, system: str = "", model: str = None, options: dict = None) -> str:
    """Send a prompt to Ollama and return the response text."""
    payload = {
        "model": model or MODEL,
        "prompt": prompt,
        "stream": False,
    }
    if system:
        payload["system"] = system
    if options:
        payload["options"] = options

    try:
        response = requests.post(OLLAMA_URL, json=payload, timeout=OLLAMA_TIMEOUT)
        response.raise_for_status()
        data = response.json()
        if not data.get("response", "").strip():
            raise RuntimeError(f"Ollama returned empty response. Full body: {data}")
        return data["response"].strip()
    except requests.exceptions.ConnectionError:
        raise RuntimeError(
            "Cannot connect to Ollama. Make sure Ollama is running: `ollama serve`"
        )
    except requests.exceptions.Timeout:
        raise RuntimeError(f"Ollama request timed out after {OLLAMA_TIMEOUT} seconds.")
    except requests.exceptions.HTTPError as e:
        raise RuntimeError(f"Ollama HTTP error: {e}")
