import pymupdf4llm

def extract_text_from_pdf(path: str) -> str:
    """
    Extract structured text from PDF using pymupdf4llm.
    Returns markdown-like clean text suitable for chunking + embedding.
    """

    try:
        # returns a list of pages or structured text blocks
        md_pages = pymupdf4llm.to_markdown(path)

        if isinstance(md_pages, list):
            return "\n\n".join(md_pages)

        return str(md_pages)

    except Exception as e:
        print(f"[PDF extract error] {e}")
        return ""