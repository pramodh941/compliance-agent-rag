"""
Ingestion configuration with feature toggles for local-lite compatibility.

Provides centralized configuration for document ingestion with optional
OCR, advanced parsing, and metadata extraction features.
"""
import os
import logging
import warnings

# Robust dotenv import with fallback for local/Docker compatibility
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # dotenv not available - continue without it
    # (environment variables should be set elsewhere)
    pass

logger = logging.getLogger(__name__)


class IngestionConfig:
    """Centralized ingestion configuration with feature toggles."""
    
    # =========================
    # CORE INGESTION
    # =========================
    
    # Chunking parameters
    CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "800"))
    CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "100"))
    MIN_CHUNK_SIZE = int(os.getenv("MIN_CHUNK_SIZE", "100"))
    
    # Collection names
    POLICIES_COLLECTION = os.getenv("POLICIES_COLLECTION", "policies")
    SEC_DOCS_COLLECTION = os.getenv("SEC_DOCS_COLLECTION", "sec_docs")
    
    # =========================
    # FEATURE TOGGLES
    # =========================
    
    # Enable/disable advanced PDF parsing (layout-aware)
    ENABLE_LAYOUT_PARSING = os.getenv("ENABLE_LAYOUT_PARSING", "false").lower() == "true"
    
    # Enable/disable OCR fallback for scanned PDFs (requires pytesseract)
    ENABLE_OCR = os.getenv("ENABLE_OCR", "false").lower() == "true"
    
    # Enable/disable table extraction (requires pdfplumber)
    ENABLE_TABLE_EXTRACTION = os.getenv("ENABLE_TABLE_EXTRACTION", "false").lower() == "true"
    
    # Enable/disable image extraction (requires pdf2image)
    ENABLE_IMAGE_EXTRACTION = os.getenv("ENABLE_IMAGE_EXTRACTION", "false").lower() == "true"
    
    # Enable/disable semantic chunking (requires sentence-transformers)
    ENABLE_SEMANTIC_CHUNKING = os.getenv("ENABLE_SEMANTIC_CHUNKING", "false").lower() == "true"
    
    # Enable/disable document hierarchy detection
    ENABLE_HIERARCHY_DETECTION = os.getenv("ENABLE_HIERARCHY_DETECTION", "true").lower() == "true"
    
    # Enable/disable metadata extraction
    ENABLE_METADATA_EXTRACTION = os.getenv("ENABLE_METADATA_EXTRACTION", "true").lower() == "true"
    
    # =========================
    # OCR CONFIGURATION (OPTIONAL)
    # =========================
    
    OCR_LANGUAGE = os.getenv("OCR_LANGUAGE", "eng")
    OCR_DPI = int(os.getenv("OCR_DPI", "300"))
    OCR_TIMEOUT = int(os.getenv("OCR_TIMEOUT", "30"))
    
    # =========================
    # PARSING CONFIGURATION
    # =========================
    
    # PDF parsing library preference: pypdf, pdfplumber, pymupdf
    PDF_PARSER = os.getenv("PDF_PARSER", "pypdf")
    
    # Text extraction mode: text, layout, preserve
    TEXT_EXTRACTION_MODE = os.getenv("TEXT_EXTRACTION_MODE", "text")
    
    # =========================
    # CHUNKING CONFIGURATION
    # =========================
    
    # Chunking strategy: simple, semantic, hierarchical, recursive
    CHUNKING_STRATEGY = os.getenv("CHUNKING_STRATEGY", "simple")
    
    # Semantic chunking parameters
    SEMANTIC_CHUNK_THRESHOLD = float(os.getenv("SEMANTIC_CHUNK_THRESHOLD", "0.7"))
    
    # Hierarchical chunking parameters
    PRESERVE_HEADERS = os.getenv("PRESERVE_HEADERS", "true").lower() == "true"
    PRESERVE_PAGE_BREAKS = os.getenv("PRESERVE_PAGE_BREAKS", "true").lower() == "true"
    
    # =========================
    # METADATA CONFIGURATION
    # =========================
    
    # Metadata fields to extract
    EXTRACT_TITLE = os.getenv("EXTRACT_TITLE", "true").lower() == "true"
    EXTRACT_AUTHOR = os.getenv("EXTRACT_AUTHOR", "false").lower() == "true"
    EXTRACT_DATE = os.getenv("EXTRACT_DATE", "true").lower() == "true"
    EXTRACT_PAGE_NUMBERS = os.getenv("EXTRACT_PAGE_NUMBERS", "true").lower() == "true"
    EXTRACT_SECTION_HEADERS = os.getenv("EXTRACT_SECTION_HEADERS", "true").lower() == "true"
    
    # =========================
    # VALIDATION CONFIGURATION
    # =========================
    
    # Minimum text length for valid chunk
    MIN_TEXT_LENGTH = int(os.getenv("MIN_TEXT_LENGTH", "50"))
    
    # Maximum text length for valid chunk
    MAX_TEXT_LENGTH = int(os.getenv("MAX_TEXT_LENGTH", "5000"))
    
    # =========================
    # PERFORMANCE CONFIGURATION
    # =========================
    
    # Batch size for embedding generation
    EMBEDDING_BATCH_SIZE = int(os.getenv("EMBEDDING_BATCH_SIZE", "10"))
    
    # Maximum concurrent document processing
    MAX_CONCURRENT_DOCS = int(os.getenv("MAX_CONCURRENT_DOCS", "4"))
    
    # Timeout for document processing (seconds)
    DOC_PROCESSING_TIMEOUT = int(os.getenv("DOC_PROCESSING_TIMEOUT", "300"))
    
    @classmethod
    def validate(cls):
        """Validate configuration and warn about potential issues."""
        warnings_issued = []
        
        # Validate chunking parameters
        if cls.CHUNK_SIZE < 100 or cls.CHUNK_SIZE > 2000:
            warnings_issued.append(
                f"CHUNK_SIZE ({cls.CHUNK_SIZE}) outside recommended range (100-2000)"
            )
        
        if cls.CHUNK_OVERLAP < 0 or cls.CHUNK_OVERLAP > cls.CHUNK_SIZE:
            warnings_issued.append(
                f"CHUNK_OVERLAP ({cls.CHUNK_OVERLAP}) invalid (should be 0 to CHUNK_SIZE)"
            )
        
        # Warn about optional dependencies
        if cls.ENABLE_OCR:
            try:
                import pytesseract
            except ImportError:
                warnings_issued.append(
                    "ENABLE_OCR is true but pytesseract is not installed. "
                    "OCR will be disabled. Install with: pip install pytesseract"
                )
        
        if cls.ENABLE_TABLE_EXTRACTION:
            try:
                import pdfplumber
            except ImportError:
                warnings_issued.append(
                    "ENABLE_TABLE_EXTRACTION is true but pdfplumber is not installed. "
                    "Table extraction will be disabled. Install with: pip install pdfplumber"
                )
        
        if cls.ENABLE_IMAGE_EXTRACTION:
            try:
                import pdf2image
            except ImportError:
                warnings_issued.append(
                    "ENABLE_IMAGE_EXTRACTION is true but pdf2image is not installed. "
                    "Image extraction will be disabled. Install with: pip install pdf2image"
                )
        
        if cls.ENABLE_SEMANTIC_CHUNKING:
            try:
                import sentence_transformers
            except ImportError:
                warnings_issued.append(
                    "ENABLE_SEMANTIC_CHUNKING is true but sentence-transformers is not installed. "
                    "Semantic chunking will fall back to simple chunking. "
                    "Install with: pip install sentence-transformers"
                )
        
        # Validate PDF parser
        valid_parsers = ["pypdf", "pdfplumber", "pymupdf"]
        if cls.PDF_PARSER not in valid_parsers:
            warnings_issued.append(
                f"PDF_PARSER ({cls.PDF_PARSER}) invalid. Must be one of: {valid_parsers}"
            )
        
        # Validate chunking strategy
        valid_strategies = ["simple", "semantic", "hierarchical", "recursive"]
        if cls.CHUNKING_STRATEGY not in valid_strategies:
            warnings_issued.append(
                f"CHUNKING_STRATEGY ({cls.CHUNKING_STRATEGY}) invalid. "
                f"Must be one of: {valid_strategies}"
            )
        
        # Log warnings
        for warning in warnings_issued:
            logger.warning(f"Ingestion config validation: {warning}")
        
        return len(warnings_issued) == 0
    
    @classmethod
    def get_profile(cls):
        """Get the current ingestion profile (local-lite vs full)."""
        has_optional_features = any([
            cls.ENABLE_OCR,
            cls.ENABLE_TABLE_EXTRACTION,
            cls.ENABLE_IMAGE_EXTRACTION,
            cls.ENABLE_SEMANTIC_CHUNKING,
            cls.ENABLE_LAYOUT_PARSING
        ])
        
        return "full" if has_optional_features else "local-lite"
    
    @classmethod
    def get_summary(cls):
        """Get a summary of current configuration."""
        return {
            "profile": cls.get_profile(),
            "chunking": {
                "strategy": cls.CHUNKING_STRATEGY,
                "chunk_size": cls.CHUNK_SIZE,
                "overlap": cls.CHUNK_OVERLAP,
                "min_chunk_size": cls.MIN_CHUNK_SIZE
            },
            "features": {
                "layout_parsing": cls.ENABLE_LAYOUT_PARSING,
                "ocr": cls.ENABLE_OCR,
                "table_extraction": cls.ENABLE_TABLE_EXTRACTION,
                "image_extraction": cls.ENABLE_IMAGE_EXTRACTION,
                "semantic_chunking": cls.ENABLE_SEMANTIC_CHUNKING,
                "hierarchy_detection": cls.ENABLE_HIERARCHY_DETECTION,
                "metadata_extraction": cls.ENABLE_METADATA_EXTRACTION
            },
            "parsing": {
                "pdf_parser": cls.PDF_PARSER,
                "text_extraction_mode": cls.TEXT_EXTRACTION_MODE
            },
            "metadata": {
                "extract_title": cls.EXTRACT_TITLE,
                "extract_author": cls.EXTRACT_AUTHOR,
                "extract_date": cls.EXTRACT_DATE,
                "extract_page_numbers": cls.EXTRACT_PAGE_NUMBERS,
                "extract_section_headers": cls.EXTRACT_SECTION_HEADERS
            }
        }


# Validate configuration on import
ingestion_config = IngestionConfig()
ingestion_config.validate()
