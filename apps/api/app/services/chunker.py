import re

def clean_text(text: str) -> str:
    return re.sub(r'\s+', ' ', text).strip()


def chunk_text(text: str, chunk_size: int = 800, overlap: int = 100):
    text = clean_text(text)

    words = text.split()
    chunks = []

    i = 0
    while i < len(words):
        chunk = words[i:i + chunk_size]
        chunks.append(" ".join(chunk))
        i += chunk_size - overlap

    return chunks