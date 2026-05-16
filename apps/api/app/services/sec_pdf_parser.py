"""
SEC PDF parser using pymupdf4llm for structured text extraction.

Returns (text, metadata) tuple for consistent integration with document parser.
Provides markdown-like clean text suitable for chunking and embedding.
"""
import logging
from typing import Tuple, Dict, Any
import pymupdf4llm

logger = logging.getLogger(__name__)


def extract_text_from_pdf(path: str) -> Tuple[str, Dict[str, Any]]:
    """
    Extract structured text from PDF using pymupdf4llm.
    
    Returns:
        Tuple of (text, metadata) for consistent integration with document parser.
        Markdown-like clean text suitable for chunking + embedding.
    """
    metadata = {
        "title": None,
        "source": path,
        "page_count": 0
    }
    
    try:
        # returns a list of pages or structured text blocks
        md_pages = pymupdf4llm.to_markdown(path)

        if isinstance(md_pages, list):
            text = "\n\n".join(md_pages)
            metadata["page_count"] = len(md_pages)
        else:
            text = str(md_pages) if md_pages else ""
            metadata["page_count"] = 1

        logger.info(f"Successfully extracted text from {path}: {len(text)} chars")
        return text, metadata

    except Exception as e:
        logger.error(f"[PDF extract error] {path}: {e}", exc_info=True)
        # Return empty tuple parts to maintain consistent interface
        return "", metadata