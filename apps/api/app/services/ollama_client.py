import requests

OLLAMA_URL = "http://ollama:11434"

def get_embedding(text: str):
    if not text or not text.strip():
        return None

    try:
        MAX_CHARS = 4000
        response = requests.post(
            f"{OLLAMA_URL}/api/embed",
            json={
                "model": "nomic-embed-text",
                "input": [text[:MAX_CHARS]]  # 🔥 MUST be list
            },
                timeout=30
        )
        response.raise_for_status()

        data = response.json()

        if "embeddings" not in data or not data["embeddings"]:
            return None

        return data["embeddings"][0]

    except Exception as e:
        print(f"[embedding error] {e}")
        return None

def generate_response(prompt: str):
    response = requests.post(
        f"{OLLAMA_URL}/api/generate",
        json={
            "model": "gemma:2b",
            "prompt": prompt,
            "stream": False,
            "options": {
                "num_predict": 60,     # 🔥 limit output tokens (BIG speed boost)
                "temperature": 0.2,     # more deterministic
                "top_p": 0.9,
                "num_ctx": 2048
            }
        },
        timeout=480
    )
    response.raise_for_status()
    return response.json()["response"]