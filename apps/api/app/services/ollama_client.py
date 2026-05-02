import requests

OLLAMA_URL = "http://ollama:11434"

def get_embedding(text: str):
    response = requests.post(
        f"{OLLAMA_URL}/api/embed",
        json={
            "model": "nomic-embed-text",
            "input": text[:8000]  # 🔥 hard safety cap
        }
    )
    response.raise_for_status()
    return response.json()["embeddings"][0]


def generate_response(prompt: str):
    response = requests.post(
        f"{OLLAMA_URL}/api/generate",
        json={
            "model": "gemma:2b",
            "prompt": prompt,
            "stream": False,
            "options": {
                "num_predict": 120,     # 🔥 limit output tokens (BIG speed boost)
                "temperature": 0.2,     # more deterministic
                "top_p": 0.9,
                "num_ctx": 2048
            }
        }
    )
    response.raise_for_status()
    return response.json()["response"]