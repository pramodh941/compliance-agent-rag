from app.services.sec_pdf_parser import extract_text_from_pdf

def route_document(file_path: str, file_type: str = "pdf") -> str:
    """
    Simple document router (initial version).
    Will expand later for OCR / multimodal docs.
    """

    if file_type == "pdf":
        return extract_text_from_pdf(file_path)

    # future extensions:
    # elif file_type == "image_pdf":
    #     return ocr_extract(file_path)

    # elif file_type == "text":
    #     return open(file_path).read()

    else:
        raise ValueError(f"Unsupported file type: {file_type}")