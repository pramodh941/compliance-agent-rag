"""
Document parser with support for multiple PDF libraries and optional features.

Provides a unified interface for document parsing with fallback support
for different PDF libraries and optional OCR/layout parsing.
"""
import os
import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from app.core.ingestion_config import IngestionConfig

logger = logging.getLogger(__name__)


@dataclass
class DocumentChunk:
    """Represents a chunk of text with metadata."""
    text: str
    page_number: int
    chunk_index: int
    metadata: Dict[str, Any]
    source: str
    doc_type: str


@dataclass
class DocumentMetadata:
    """Metadata extracted from a document."""
    title: Optional[str] = None
    author: Optional[str] = None
    creation_date: Optional[str] = None
    modification_date: Optional[str] = None
    page_count: int = 0
    section_headers: List[str] = None
    tables: List[Dict[str, Any]] = None
    images: List[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.section_headers is None:
            self.section_headers = []
        if self.tables is None:
            self.tables = []
        if self.images is None:
            self.images = []


class DocumentParser:
    """Unified document parser with multiple library support."""
    
    def __init__(self, config: Optional[IngestionConfig] = None):
        self.config = config or IngestionConfig()
        self._init_parser()
    
    def _init_parser(self):
        """Initialize the appropriate PDF parser based on configuration."""
        self.parser_type = self.config.PDF_PARSER
        
        if self.parser_type == "pypdf":
            try:
                import pypdf
                self.pypdf = pypdf
                logger.info("Using pypdf for PDF parsing")
            except ImportError:
                logger.warning("pypdf not installed, falling back to basic parsing")
                self.parser_type = "basic"
        
        elif self.parser_type == "pdfplumber":
            try:
                import pdfplumber
                self.pdfplumber = pdfplumber
                logger.info("Using pdfplumber for PDF parsing")
            except ImportError:
                logger.warning("pdfplumber not installed, falling back to pypdf")
                self.parser_type = "pypdf"
                try:
                    import pypdf
                    self.pypdf = pypdf
                except ImportError:
                    logger.warning("pypdf not installed, falling back to basic parsing")
                    self.parser_type = "basic"
        
        elif self.parser_type == "pymupdf":
            try:
                import pymupdf
                self.pymupdf = pymupdf
                logger.info("Using pymupdf for PDF parsing")
            except ImportError:
                logger.warning("pymupdf not installed, falling back to pypdf")
                self.parser_type = "pypdf"
                try:
                    import pypdf
                    self.pypdf = pypdf
                except ImportError:
                    logger.warning("pypdf not installed, falling back to basic parsing")
                    self.parser_type = "basic"
    
    def parse_document(self, file_path: str, doc_type: str = "policy") -> Tuple[List[DocumentChunk], DocumentMetadata]:
        """
        Parse a document and extract chunks with metadata.
        
        Args:
            file_path: Path to the document file
            doc_type: Type of document (policy, sec_doc, etc.)
            
        Returns:
            Tuple of (chunks, metadata)
        """
        logger.info(
            f"Parsing document: {file_path}",
            extra={"operation": "document_parsing", "file": file_path, "parser": self.parser_type}
        )
        
        # Extract text and metadata with defensive unpacking
        try:
            result = self._extract_text_and_metadata(file_path)
            result_type = type(result).__name__
            result_len = len(result) if isinstance(result, (tuple, list)) else None
            logger.info(
                "Parser extraction result",
                extra={
                    "operation": "document_parsing",
                    "file": file_path,
                    "parser": self.parser_type,
                    "result_type": result_type,
                    "result_len": result_len
                }
            )
            
            # Defensive unpacking to ensure we get (text, metadata) tuple
            if isinstance(result, tuple) and len(result) == 2:
                text, metadata = result
            else:
                logger.error(
                    f"Parser returned invalid result type for {file_path}: "
                    f"expected tuple of (str, DocumentMetadata), got {result_type}",
                    extra={
                        "operation": "document_parsing",
                        "file": file_path,
                        "parser": self.parser_type,
                        "result_len": result_len
                    }
                )
                return [], DocumentMetadata()
        except Exception as e:
            logger.error(
                f"Failed to extract text from {file_path}: {e}",
                extra={"operation": "document_parsing", "file": file_path, "error": str(e), "parser": self.parser_type},
                exc_info=True
            )
            return [], DocumentMetadata()
        
        # Validate extracted text
        if not text or len(text.strip()) < 10:
            logger.warning(
                f"Insufficient text extracted from {file_path}: {len(text)} chars",
                extra={"operation": "document_parsing", "file": file_path, "text_length": len(text)}
            )
        
        # Chunk the text
        chunks = self._chunk_text(text, metadata, file_path, doc_type)
        
        logger.info(
            f"Parsed {len(chunks)} chunks from {file_path}",
            extra={"operation": "document_parsing", "file": file_path, "chunks": len(chunks), "parser": self.parser_type}
        )
        
        return chunks, metadata
    
    def _extract_text_and_metadata(self, file_path: str) -> Tuple[str, DocumentMetadata]:
        """Extract text and metadata from document based on parser type."""
        metadata = DocumentMetadata()
        
        try:
            if self.parser_type == "pypdf":
                result = self._extract_with_pypdf(file_path, metadata)
            elif self.parser_type == "pdfplumber":
                result = self._extract_with_pdfplumber(file_path, metadata)
            elif self.parser_type == "pymupdf":
                result = self._extract_with_pymupdf(file_path, metadata)
            else:
                result = self._extract_basic(file_path, metadata)
        except Exception as e:
            logger.error(f"Error extracting text with {self.parser_type}: {e}", exc_info=True)
            # Fallback to basic extraction
            try:
                result = self._extract_basic(file_path, metadata)
            except Exception as fallback_error:
                logger.error(f"Basic extraction also failed: {fallback_error}", exc_info=True)
                return "", metadata

        # Normalize result to safe tuple return
        if isinstance(result, tuple) and len(result) == 2:
            return result

        logger.error(
            f"Parser extraction returned invalid payload for {file_path}: {type(result).__name__}",
            extra={"operation": "document_parsing", "file": file_path, "parser": self.parser_type}
        )
        return "", metadata
    
    def _extract_with_pypdf(self, file_path: str, metadata: DocumentMetadata) -> Tuple[str, DocumentMetadata]:
        """Extract text using pypdf."""
        from pypdf import PdfReader
        
        try:
            reader = PdfReader(file_path)
            metadata.page_count = len(reader.pages)
            
            # Extract metadata
            if self.config.EXTRACT_TITLE:
                metadata.title = reader.metadata.get("/Title") if reader.metadata else None
            
            if self.config.EXTRACT_AUTHOR:
                metadata.author = reader.metadata.get("/Author") if reader.metadata else None
            
            if self.config.EXTRACT_DATE:
                metadata.creation_date = reader.metadata.get("/CreationDate") if reader.metadata else None
            
            # Extract text from all pages
            text_pages = []
            for page_num, page in enumerate(reader.pages, 1):
                page_text = page.extract_text() or ""
                
                # Add page number metadata
                if self.config.EXTRACT_PAGE_NUMBERS:
                    text_pages.append(f"[Page {page_num}]\n{page_text}")
                else:
                    text_pages.append(page_text)
            
            full_text = "\n\n".join(text_pages)
            
            # Validate we got some text
            if not full_text or len(full_text.strip()) < 10:
                logger.warning(f"Very little text extracted from {file_path} using pypdf")
            
            # Extract section headers if enabled
            if self.config.ENABLE_HIERARCHY_DETECTION and self.config.EXTRACT_SECTION_HEADERS:
                metadata.section_headers = self._extract_headers(full_text)
            
            return full_text, metadata
        except Exception as e:
            logger.error(f"pypdf extraction failed for {file_path}: {e}", exc_info=True)
            raise
    
    def _extract_with_pdfplumber(self, file_path: str, metadata: DocumentMetadata) -> Tuple[str, DocumentMetadata]:
        """Extract text using pdfplumber (better for tables and layout)."""
        import pdfplumber
        
        with pdfplumber.open(file_path) as pdf:
            metadata.page_count = len(pdf.pages)
            
            # Extract metadata
            if self.config.EXTRACT_TITLE:
                metadata.title = pdf.metadata.get("Title")
            
            if self.config.EXTRACT_AUTHOR:
                metadata.author = pdf.metadata.get("Author")
            
            if self.config.EXTRACT_DATE:
                metadata.creation_date = pdf.metadata.get("CreationDate")
            
            # Extract text from all pages
            text_pages = []
            for page_num, page in enumerate(pdf.pages, 1):
                page_text = page.extract_text() or ""
                
                # Extract tables if enabled
                if self.config.ENABLE_TABLE_EXTRACTION:
                    tables = page.extract_tables()
                    if tables:
                        for table in tables:
                            table_text = self._format_table(table)
                            metadata.tables.append({
                                "page": page_num,
                                "text": table_text
                            })
                
                # Add page number metadata
                if self.config.EXTRACT_PAGE_NUMBERS:
                    text_pages.append(f"[Page {page_num}]\n{page_text}")
                else:
                    text_pages.append(page_text)
            
            full_text = "\n\n".join(text_pages)
            
            # Extract section headers if enabled
            if self.config.ENABLE_HIERARCHY_DETECTION and self.config.EXTRACT_SECTION_HEADERS:
                metadata.section_headers = self._extract_headers(full_text)
        
        return full_text, metadata
    
    def _extract_with_pymupdf(self, file_path: str, metadata: DocumentMetadata) -> Tuple[str, DocumentMetadata]:
        """Extract text using pymupdf (fast, good for large documents)."""
        import pymupdf
        
        doc = pymupdf.open(file_path)
        metadata.page_count = len(doc)
        
        # Extract metadata
        if self.config.EXTRACT_TITLE:
            metadata.title = doc.metadata.get("title")
        
        if self.config.EXTRACT_AUTHOR:
            metadata.author = doc.metadata.get("author")
        
        if self.config.EXTRACT_DATE:
            metadata.creation_date = doc.metadata.get("creationDate")
        
        # Extract text from all pages
        text_pages = []
        for page_num, page in enumerate(doc, 1):
            page_text = page.get_text()
            
            # Add page number metadata
            if self.config.EXTRACT_PAGE_NUMBERS:
                text_pages.append(f"[Page {page_num}]\n{page_text}")
            else:
                text_pages.append(page_text)
        
        full_text = "\n\n".join(text_pages)
        
        # Extract section headers if enabled
        if self.config.ENABLE_HIERARCHY_DETECTION and self.config.EXTRACT_SECTION_HEADERS:
            metadata.section_headers = self._extract_headers(full_text)
        
        doc.close()
        
        return full_text, metadata
    
    def _extract_basic(self, file_path: str, metadata: DocumentMetadata) -> Tuple[str, DocumentMetadata]:
        """Basic text extraction fallback."""
        try:
            from pypdf import PdfReader
            reader = PdfReader(file_path)
            metadata.page_count = len(reader.pages)
            
            text_pages = []
            for page in reader.pages:
                text_pages.append(page.extract_text() or "")
            
            return "\n\n".join(text_pages), metadata
        except ImportError:
            logger.error("No PDF parsing library available")
            return "", metadata
    
    def _format_table(self, table: List[List[str]]) -> str:
        """Format a table as text."""
        if not table:
            return ""
        
        # Simple table formatting
        formatted_rows = []
        for row in table:
            formatted_rows.append(" | ".join(str(cell) for cell in row))
        
        return "\n".join(formatted_rows)
    
    def _extract_headers(self, text: str) -> List[str]:
        """Extract section headers from text using simple heuristics."""
        import re
        
        headers = []
        
        # Pattern for all-caps headers
        all_caps_pattern = r'\n([A-Z][A-Z\s]{5,})\n'
        headers.extend(re.findall(all_caps_pattern, text))
        
        # Pattern for numbered headers (1., 2., etc.)
        numbered_pattern = r'\n(\d+\.\s+[A-Z][^.\n]+)\n'
        headers.extend(re.findall(numbered_pattern, text))
        
        # Pattern for headers with colon
        colon_pattern = r'\n([A-Z][^:\n]{5,}:)\n'
        headers.extend(re.findall(colon_pattern, text))
        
        # Remove duplicates while preserving order
        seen = set()
        unique_headers = []
        for header in headers:
            if header not in seen:
                seen.add(header)
                unique_headers.append(header)
        
        return unique_headers
    
    def _chunk_text(self, text: str, metadata: DocumentMetadata, source: str, doc_type: str) -> List[DocumentChunk]:
        """Chunk text based on configured strategy."""
        if self.config.CHUNKING_STRATEGY == "semantic":
            return self._semantic_chunking(text, metadata, source, doc_type)
        elif self.config.CHUNKING_STRATEGY == "hierarchical":
            return self._hierarchical_chunking(text, metadata, source, doc_type)
        else:
            return self._simple_chunking(text, metadata, source, doc_type)
    
    def _simple_chunking(self, text: str, metadata: DocumentMetadata, source: str, doc_type: str) -> List[DocumentChunk]:
        """Simple word-based chunking with overlap."""
        # Validate input text
        if not text or len(text.strip()) < self.config.MIN_TEXT_LENGTH:
            logger.warning(f"Text too short for chunking: {len(text)} chars")
            return []
        
        words = text.split()
        chunks = []
        
        for i in range(0, len(words), self.config.CHUNK_SIZE - self.config.CHUNK_OVERLAP):
            chunk_words = words[i:i + self.config.CHUNK_SIZE]
            chunk_text = " ".join(chunk_words)
            
            # Validate chunk length
            if len(chunk_text) < self.config.MIN_TEXT_LENGTH:
                continue
            if len(chunk_text) > self.config.MAX_TEXT_LENGTH:
                chunk_text = chunk_text[:self.config.MAX_TEXT_LENGTH]
            
            # Build metadata with section context
            chunk_metadata = {
                "title": metadata.title or source,
                "author": metadata.author,
                "creation_date": metadata.creation_date,
                "section_headers": metadata.section_headers[:5] if metadata.section_headers else [],
                "doc_type": doc_type
            }
            
            chunks.append(DocumentChunk(
                text=chunk_text,
                page_number=0,  # Not tracked in simple chunking
                chunk_index=len(chunks),
                metadata=chunk_metadata,
                source=source,
                doc_type=doc_type
            ))
        
        logger.info(f"Created {len(chunks)} chunks using simple chunking")
        return chunks
    
    def _hierarchical_chunking(self, text: str, metadata: DocumentMetadata, source: str, doc_type: str) -> List[DocumentChunk]:
        """Hierarchical chunking preserving page breaks and headers."""
        # Validate input text
        if not text or len(text.strip()) < self.config.MIN_TEXT_LENGTH:
            logger.warning(f"Text too short for chunking: {len(text)} chars")
            return []
        
        chunks = []
        
        # Split by page breaks if enabled
        if self.config.PRESERVE_PAGE_BREAKS:
            pages = text.split("\n\n[Page ")
        else:
            pages = [text]
        
        chunk_index = 0
        for page_idx, page_text in enumerate(pages):
            # Add page number back if it was split
            if self.config.PRESERVE_PAGE_BREAKS and page_idx > 0:
                page_text = f"[Page {page_text}"
            
            # Split by headers if enabled
            if self.config.PRESERVE_HEADERS and metadata.section_headers:
                sections = self._split_by_headers(page_text, metadata.section_headers)
            else:
                sections = [page_text]
            
            for section_idx, section_text in enumerate(sections):
                # Prepend section header if available
                if section_idx > 0 and metadata.section_headers:
                    # Try to identify which header this section belongs to
                    current_header = metadata.section_headers[min(section_idx, len(metadata.section_headers) - 1)]
                    if current_header and current_header not in section_text[:100]:
                        section_text = f"{current_header}\n\n{section_text}"
                
                # Apply simple chunking within sections
                words = section_text.split()
                for i in range(0, len(words), self.config.CHUNK_SIZE - self.config.CHUNK_OVERLAP):
                    chunk_words = words[i:i + self.config.CHUNK_SIZE]
                    chunk_text = " ".join(chunk_words)
                    
                    # Validate chunk length
                    if len(chunk_text) < self.config.MIN_TEXT_LENGTH:
                        continue
                    if len(chunk_text) > self.config.MAX_TEXT_LENGTH:
                        chunk_text = chunk_text[:self.config.MAX_TEXT_LENGTH]
                    
                    chunk_metadata = {
                        "title": metadata.title or source,
                        "author": metadata.author,
                        "creation_date": metadata.creation_date,
                        "section_headers": metadata.section_headers[:5] if metadata.section_headers else [],
                        "page_number": page_idx + 1,
                        "doc_type": doc_type
                    }
                    
                    chunks.append(DocumentChunk(
                        text=chunk_text,
                        page_number=page_idx + 1,
                        chunk_index=chunk_index,
                        metadata=chunk_metadata,
                        source=source,
                        doc_type=doc_type
                    ))
                    chunk_index += 1
        
        logger.info(f"Created {len(chunks)} chunks using hierarchical chunking")
        return chunks
    
    def _split_by_headers(self, text: str, headers: List[str]) -> List[str]:
        """Split text by section headers."""
        sections = [text]
        
        for header in headers:
            new_sections = []
            for section in sections:
                parts = section.split(header)
                if len(parts) > 1:
                    for i, part in enumerate(parts):
                        if i > 0:
                            new_sections.append(header + part)
                        else:
                            new_sections.append(part)
                else:
                    new_sections.append(section)
            sections = new_sections
        
        return sections
    
    def _semantic_chunking(self, text: str, metadata: DocumentMetadata, source: str, doc_type: str) -> List[DocumentChunk]:
        """Semantic chunking using sentence embeddings (optional)."""
        try:
            from sentence_transformers import SentenceTransformer
            import numpy as np
        except ImportError:
            logger.warning("sentence-transformers not available, falling back to simple chunking")
            return self._simple_chunking(text, metadata, source, doc_type)
        
        # Load model (cached after first load)
        if not hasattr(self, 'semantic_model'):
            try:
                self.semantic_model = SentenceTransformer('all-MiniLM-L6-v2')
            except Exception as e:
                logger.warning(f"Failed to load semantic model: {e}, falling back to simple chunking")
                return self._simple_chunking(text, metadata, source, doc_type)
        
        # Split into sentences
        import re
        sentences = re.split(r'(?<=[.!?])\s+', text)
        
        # Get embeddings for sentences
        embeddings = self.semantic_model.encode(sentences)
        
        # Group sentences into chunks based on semantic similarity
        chunks = []
        current_chunk = []
        current_chunk_text = ""
        
        for i, sentence in enumerate(sentences):
            if not current_chunk:
                current_chunk.append(sentence)
                current_chunk_text = sentence
            else:
                # Calculate similarity with last sentence in current chunk
                last_embedding = embeddings[len(current_chunk) - 1]
                current_embedding = embeddings[i]
                similarity = np.dot(last_embedding, current_embedding)
                
                # If similarity is above threshold, add to current chunk
                if similarity > self.config.SEMANTIC_CHUNK_THRESHOLD:
                    current_chunk.append(sentence)
                    current_chunk_text += " " + sentence
                else:
                    # Start new chunk
                    if len(current_chunk_text) >= self.config.MIN_TEXT_LENGTH:
                        chunk_metadata = {
                            "title": metadata.title,
                            "author": metadata.author,
                            "creation_date": metadata.creation_date,
                            "section_headers": metadata.section_headers[:5]
                        }
                        
                        chunks.append(DocumentChunk(
                            text=current_chunk_text,
                            page_number=0,
                            chunk_index=len(chunks),
                            metadata=chunk_metadata,
                            source=source,
                            doc_type=doc_type
                        ))
                    
                    current_chunk = [sentence]
                    current_chunk_text = sentence
            
        # Add final chunk
        if current_chunk_text and len(current_chunk_text) >= self.config.MIN_TEXT_LENGTH:
            chunk_metadata = {
                "title": metadata.title,
                "author": metadata.author,
                "creation_date": metadata.creation_date,
                "section_headers": metadata.section_headers[:5]
            }
            
            chunks.append(DocumentChunk(
                text=current_chunk_text,
                page_number=0,
                chunk_index=len(chunks),
                metadata=chunk_metadata,
                source=source,
                doc_type=doc_type
            ))
        
        return chunks
