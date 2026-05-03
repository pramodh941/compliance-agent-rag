from typing import List

def chunk_text(text: str, chunk_size: int = 500, overlap: int = 100) -> List[str]:
    if not text:
        return []

    chunks = []
    start = 0
    text_length = len(text)

    while start < text_length:
        end = start + chunk_size
        chunk = text[start:end]

        # avoid cutting mid-sentence (basic improvement)
        if end < text_length:
            last_period = chunk.rfind(".")
            if last_period > 200:  # ensure meaningful split
                end = start + last_period + 1
                chunk = text[start:end]

        chunks.append(chunk.strip())

        start = end - overlap

    return chunks