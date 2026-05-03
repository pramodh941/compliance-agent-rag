import pymupdf4llm

def route_document(path: str, doc_type: str):
    if doc_type == "pdf":
        pages = pymupdf4llm.to_markdown(
            path,
            page_chunks=True
        )

        return pages  # IMPORTANT: return structured pages

    raise ValueError(f"Unsupported document type: {doc_type}")