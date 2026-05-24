"""
Ingestion Configuration - Backward compatible wrapper around centralized config.

This module provides backward compatibility for existing code while
delegating to the new centralized configuration system.

New code should import from packages.config directly:
    from packages.config import get_config
    config = get_config()
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

# Import centralized configuration
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '../../../..'))
from packages.config import get_config

logger = logging.getLogger(__name__)

# Get centralized configuration
_central_config = get_config()


class IngestionConfig:
    """Backward compatible IngestionConfig class that wraps centralized config."""
    
    # =========================
    # CORE INGESTION
    # =========================
    
    # Chunking parameters (from centralized config)
    CHUNK_SIZE = _central_config.chunk_size
    CHUNK_OVERLAP = _central_config.chunk_overlap
    MIN_CHUNK_SIZE = _central_config.min_chunk_size
    
    # Collection names (from centralized config)
    POLICIES_COLLECTION = _central_config.policies_collection
    SEC_DOCS_COLLECTION = _central_config.sec_docs_collection
    
    # =========================
    # FEATURE TOGGLES (from feature manager)
    # =========================
    
    ENABLE_LAYOUT_PARSING = _central_config.feature_manager.is_enabled("layout_parsing")
    ENABLE_OCR = _central_config.feature_manager.is_enabled("ocr")
    ENABLE_TABLE_EXTRACTION = _central_config.feature_manager.is_enabled("table_extraction")
    ENABLE_IMAGE_EXTRACTION = _central_config.feature_manager.is_enabled("image_extraction")
    ENABLE_SEMANTIC_CHUNKING = _central_config.feature_manager.is_enabled("semantic_chunking")
    ENABLE_HIERARCHY_DETECTION = _central_config.feature_manager.is_enabled("hierarchy_detection")
    ENABLE_METADATA_EXTRACTION = _central_config.feature_manager.is_enabled("metadata_extraction")
    
    # =========================
    # OCR CONFIGURATION (OPTIONAL)
    # =========================
    
    OCR_LANGUAGE = os.getenv("OCR_LANGUAGE", "eng")
    OCR_DPI = int(os.getenv("OCR_DPI", "300"))
    OCR_TIMEOUT = int(os.getenv("OCR_TIMEOUT", "30"))
    
    # =========================
    # PARSING CONFIGURATION (from centralized config)
    # =========================
    
    PDF_PARSER = _central_config.pdf_parser
    TEXT_EXTRACTION_MODE = os.getenv("TEXT_EXTRACTION_MODE", "text")
    
    # =========================
    # CHUNKING CONFIGURATION (from centralized config)
    # =========================
    
    CHUNKING_STRATEGY = _central_config.chunking_strategy
    SEMANTIC_CHUNK_THRESHOLD = float(os.getenv("SEMANTIC_CHUNK_THRESHOLD", "0.7"))
    PRESERVE_HEADERS = os.getenv("PRESERVE_HEADERS", "true").lower() == "true"
    PRESERVE_PAGE_BREAKS = os.getenv("PRESERVE_PAGE_BREAKS", "true").lower() == "true"
    
    # =========================
    # METADATA CONFIGURATION
    # =========================
    
    EXTRACT_TITLE = os.getenv("EXTRACT_TITLE", "true").lower() == "true"
    EXTRACT_AUTHOR = os.getenv("EXTRACT_AUTHOR", "false").lower() == "true"
    EXTRACT_DATE = os.getenv("EXTRACT_DATE", "true").lower() == "true"
    EXTRACT_PAGE_NUMBERS = os.getenv("EXTRACT_PAGE_NUMBERS", "true").lower() == "true"
    EXTRACT_SECTION_HEADERS = os.getenv("EXTRACT_SECTION_HEADERS", "true").lower() == "true"
    
    # =========================
    # VALIDATION CONFIGURATION
    # =========================
    
    MIN_TEXT_LENGTH = int(os.getenv("MIN_TEXT_LENGTH", "50"))
    MAX_TEXT_LENGTH = int(os.getenv("MAX_TEXT_LENGTH", "5000"))
    
    # =========================
    # PERFORMANCE CONFIGURATION (from profile config)
    # =========================
    
    EMBEDDING_BATCH_SIZE = _central_config.profile_config.embedding_batch_size
    MAX_CONCURRENT_DOCS = _central_config.profile_config.max_concurrent_docs
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
