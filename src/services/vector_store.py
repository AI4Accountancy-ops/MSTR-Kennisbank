import re
from datetime import datetime
from typing import Any, Dict, List, Tuple
from functools import lru_cache
import concurrent.futures
import contextlib

import psycopg2
import psycopg2.pool
import psycopg2.sql
import requests
import tiktoken
from tqdm import tqdm

# Import pgvector adapter and expose availability flag
try:
    from pgvector.psycopg2 import register_vector as _pgv_register
    PGV_AVAILABLE = True
except Exception:
    PGV_AVAILABLE = False
    # Fallback no-op if pgvector is not available
    def _pgv_register(conn):
        pass

import definitions.names as n
from definitions.credentials import Credentials
from config.settings import get_settings
from prompts.system_prompt_templates import metadata_system_prompt
from prompts.user_prompt_templates import chunk_metadata_user_prompt
from response_models.metadata_model import MetaData
from services.llm_factory import LLMFactory
from logger.logger import Logger
from services.db import get_connection

logger = Logger.get_logger(__name__)

# Search Configuration Constants
class SearchConfig:
    """Configuration constants for vector search optimization."""
    DEFAULT_SEARCH_LIMIT = 7
    SEARCH_LIMIT = 7  # Limit number of candidates for faster queries
    IVFFLAT_PROBES = 6  # Fewer probes for lower latency with lists=100
    MAX_COSINE_DISTANCE = 2.0  # Maximum expected cosine distance (0-2 range for 1-cos trick)
    USE_HNSW = True
    HNSW_EF_SEARCH = 48

class VectorStore:
    """Class for managing document chunks and providing search capabilities."""

    def __init__(self):
        """Initialize settings, database connection pool, and Azure OpenAI client."""
        self.settings = get_settings()
        self.llm_factory = LLMFactory(n.AZURE_OPENAI)
        self.api_key = self.settings.azure_openai.api_key
        self.api_base = self.settings.azure_openai.api_base
        self.embedding_model = self.settings.azure_openai.embedding_model
        self.database_url = self.settings.database_url
        self.api_version = self.settings.azure_openai.api_version
        self.search_weights = self.settings.search_weights
        
        # Use shared DB pool via services.db
        
        # Assume schema is pre-provisioned (managed outside the app)

    def _count_tokens(self, text: str) -> int:
        """Count the actual number of tokens in text using tiktoken.
        
        Args:
            text (str): Text to count tokens for
            
        Returns:
            int: Exact token count
        """
        try:
            # Use the recommended approach for getting the correct tokenizer
            encoding = tiktoken.encoding_for_model("text-embedding-3-large")
            return len(encoding.encode(text))
        except Exception as e:
            # Fall back to approximation if tiktoken fails
            logger.warning(f"Error using tiktoken: {str(e)}. Falling back to approximation.")
            return len(text) // 4

    def _extract_metadata_and_content(self, text: str) -> Tuple[Dict[str, Any], str]:
        """Extract metadata and content from the structured .txt file.
        
        Args:
            text (str): Full text content of the .txt file
            
        Returns:
            Tuple[Dict[str, Any], str]: (metadata, content)
        """
        # Find the Content: marker
        content_match = re.search(r"Content:(.*?)(?:\n\n[A-Za-z]+:|$)", text, re.DOTALL)
        if not content_match:
            return {}, text
        
        # Extract content (everything after "Content:")
        content = content_match.group(1).strip()
        
        # Extract metadata from the header section
        metadata = {}
        
        # Extract URL
        url_match = re.search(r"URL:\s*(.*?)$", text, re.MULTILINE)
        if url_match:
            metadata['source_url'] = url_match.group(1).strip()
        
        # Extract other metadata fields
        title_match = re.search(r"Title:\s*(.*?)$", text, re.MULTILINE)
        if title_match:
            metadata['title'] = title_match.group(1).strip()
        
        source_match = re.search(r"Source:\s*(.*?)$", text, re.MULTILINE)
        if source_match:
            metadata['source'] = source_match.group(1).strip()
        
        return metadata, content

    def _is_pdf_content(self, metadata: Dict[str, Any]) -> bool:
        """Check if the content is from a PDF based on the URL.
        
        Args:
            metadata (Dict[str, Any]): Metadata containing source_url
            
        Returns:
            bool: True if content is from a PDF
        """
        source_url = metadata.get('source_url', '')
        return source_url.lower().endswith('.pdf')

    def _is_wetten_overheid_content(self, metadata: Dict[str, Any]) -> bool:
        """Check if the content is from Wetten Overheid based on the source.
        
        Args:
            metadata (Dict[str, Any]): Metadata containing source
            
        Returns:
            bool: True if content is from Wetten Overheid
        """
        source = metadata.get('source', '')
        return source.lower() == 'wetten overheid'

    def __del__(self):
        return

    @contextlib.contextmanager
    def get_connection(self):
        """Get a healthy connection from the shared pool and register pgvector if available."""
        with get_connection() as conn:
            if PGV_AVAILABLE:
                try:
                    _pgv_register(conn)
                except Exception:
                    logger.warning("pgvector adapter registration failed; ensure pgvector is installed")
            else:
                logger.warning("pgvector psycopg2 adapter NOT installed; please `pip install pgvector`")
            yield conn

            
    def generate_metadata(self, content: str) -> Dict[str, Any]:
        """
        Generate metadata for fiscal topic
        
        This function is kept for backwards compatibility
        """
        try:
            # Format the prompt with just the content
            formatted_user_prompt = chunk_metadata_user_prompt.format(
                content=content
            )
            
            response = self.llm_factory.normal_completion(
                response_model=MetaData,
                messages=[
                    {"role": "system", "content": metadata_system_prompt},
                    {"role": "user", "content": formatted_user_prompt}
                ],
                model="gpt-4.1-mini"
            )
            return response.dict()
        except Exception as e:
            logger.error(f"Failed to generate metadata: {e}")
            raise

    def split_text_into_chunks(self, text: str, max_tokens: int = 1000, min_tokens: int = 600) -> List[Dict[str, Any]]:
        """
        Split text into chunks based on content type (PDF vs Website) with token-based limits.
        
        Args:
            text (str): Full text content including metadata
            max_tokens (int): Maximum tokens per chunk
            min_tokens (int): Minimum tokens per chunk
            
        Returns:
            List[Dict[str, Any]]: List of chunks with content, page_numbers, and headers
        """
        try:
            # Extract metadata and content
            metadata, content = self._extract_metadata_and_content(text)
            is_pdf = self._is_pdf_content(metadata)
            
            # Check if this is wetten overheid content
            is_wetten_overheid = self._is_wetten_overheid_content(metadata)
            
            if is_pdf:
                return self._split_pdf_content(content, max_tokens, min_tokens)
            elif is_wetten_overheid:
                return self._split_wetten_overheid_content(content, max_tokens, min_tokens)
            else:
                return self._split_website_content(content, max_tokens, min_tokens)
                
        except Exception as e:
            logger.error(f"Error splitting text: {str(e)}")
            # Fallback: return the original text as a single chunk
            logger.warning("Returning original text as a single chunk due to chunking error")
            return [{"content": text, "page_numbers": None, "headers": None}]

    def _split_pdf_content(self, content: str, max_tokens: int, min_tokens: int) -> List[Dict[str, Any]]:
        """Split PDF content by page boundaries with token limits."""
        chunks = []
        
        # Find all page boundaries
        page_pattern = r'--- page (\d+) ---'
        page_matches = list(re.finditer(page_pattern, content))
        
        if not page_matches:
            # No page boundaries found, treat as single chunk
            token_count = self._count_tokens(content)
            if token_count <= max_tokens:
                return [{"content": content, "page_numbers": None, "headers": None}]
            else:
                # Split at sentence boundaries
                return self._split_large_content(content, max_tokens, min_tokens, is_pdf=True)
        
        # Group pages together based on token limits
        current_chunk = ""
        current_pages = []
        current_tokens = 0
        
        # Process content before first page boundary
        first_page_start = page_matches[0].start()
        if first_page_start > 0:
            pre_content = content[:first_page_start].strip()
            if pre_content:
                current_chunk = pre_content
                current_tokens = self._count_tokens(pre_content)
        
        for i, match in enumerate(page_matches):
            page_num = int(match.group(1))
            
            # Get content for this page
            if i < len(page_matches) - 1:
                # Not the last page
                page_end = page_matches[i + 1].start()
                page_content = content[match.end():page_end].strip()
            else:
                # Last page
                page_content = content[match.end():].strip()
            
            if not page_content:
                continue
            
            page_tokens = self._count_tokens(page_content)
            
            # Check if adding this page would exceed max_tokens
            if current_tokens + page_tokens > max_tokens and current_chunk:
                # Save current chunk
                chunks.append({
                    "content": current_chunk,
                    "page_numbers": current_pages.copy(),
                    "headers": None
                })
                
                # Start new chunk with this page
                current_chunk = page_content
                current_pages = [page_num]
                current_tokens = page_tokens
            else:
                # Add this page to current chunk
                if current_chunk:
                    current_chunk += "\n\n" + page_content
                else:
                    current_chunk = page_content
                current_pages.append(page_num)
                current_tokens += page_tokens
        
        # Add the last chunk
        if current_chunk:
            chunks.append({
                "content": current_chunk,
                "page_numbers": current_pages,
                "headers": None
            })
        
        return chunks

    def _split_website_content(self, content: str, max_tokens: int, min_tokens: int) -> List[Dict[str, Any]]:
        """Split website content by header boundaries with token limits."""
        chunks = []
        
        # Find all header boundaries
        header_pattern = r'^(#{1,3})\s+(.+)$'
        header_matches = list(re.finditer(header_pattern, content, re.MULTILINE))
        
        if not header_matches:
            # No headers found, treat as single chunk
            token_count = self._count_tokens(content)
            if token_count <= max_tokens:
                return [{"content": content, "page_numbers": None, "headers": None}]
            else:
                # Split at sentence boundaries
                return self._split_large_content(content, max_tokens, min_tokens, is_pdf=False)
        
        # Group content by headers based on token limits
        current_chunk = ""
        current_headers = []
        current_tokens = 0
        
        # Process content before first header
        first_header_start = header_matches[0].start()
        if first_header_start > 0:
            pre_content = content[:first_header_start].strip()
            if pre_content:
                current_chunk = pre_content
                current_tokens = self._count_tokens(pre_content)
        
        for i, match in enumerate(header_matches):
            header_text = match.group(2).strip()
            
            # Get content for this header
            if i < len(header_matches) - 1:
                # Not the last header
                header_end = header_matches[i + 1].start()
                header_content = content[match.end():header_end].strip()
            else:
                # Last header
                header_content = content[match.end():].strip()
            
            if not header_content:
                continue
            
            # Include the header in the content
            full_content = match.group(0) + "\n\n" + header_content
            content_tokens = self._count_tokens(full_content)
            
            # Check if adding this header section would exceed max_tokens
            if current_tokens + content_tokens > max_tokens and current_chunk:
                # Save current chunk
                chunks.append({
                    "content": current_chunk,
                    "page_numbers": None,
                    "headers": current_headers.copy()
                })
                
                # Start new chunk with this header
                current_chunk = full_content
                current_headers = [header_text]
                current_tokens = content_tokens
            else:
                # Add this header section to current chunk
                if current_chunk:
                    current_chunk += "\n\n" + full_content
                else:
                    current_chunk = full_content
                current_headers.append(header_text)
                current_tokens += content_tokens
        
        # Add the last chunk
        if current_chunk:
            chunks.append({
                "content": current_chunk,
                "page_numbers": None,
                "headers": current_headers
            })
        
        return chunks

    def _split_wetten_overheid_content(self, content: str, max_tokens: int, min_tokens: int) -> List[Dict[str, Any]]:
        """Split wetten overheid content by Artikel boundaries (#### headers) with token limits.
        
        This method focuses on Artikel-level headers (####) rather than Hoofdstuk-level headers (###)
        to provide more granular and useful chunks for legal documents.
        """
        chunks = []
        
        # Find all Artikel-level headers (####) and higher-level headers (###)
        artikel_pattern = r'^(#{3,4})\s+(.+)$'
        header_matches = list(re.finditer(artikel_pattern, content, re.MULTILINE))
        
        if not header_matches:
            # No headers found, treat as single chunk
            token_count = self._count_tokens(content)
            if token_count <= max_tokens:
                return [{"content": content, "page_numbers": None, "headers": None}]
            else:
                # Split at sentence boundaries
                return self._split_large_content(content, max_tokens, min_tokens, is_pdf=False)
        
        # Group content by headers based on token limits
        current_chunk = ""
        current_headers = []
        current_tokens = 0
        
        # Process content before first header
        first_header_start = header_matches[0].start()
        if first_header_start > 0:
            pre_content = content[:first_header_start].strip()
            if pre_content:
                current_chunk = pre_content
                current_tokens = self._count_tokens(pre_content)
        
        for i, match in enumerate(header_matches):
            header_level = len(match.group(1))  # Number of # symbols
            header_text = match.group(2).strip()
            
            # Get content for this header
            if i < len(header_matches) - 1:
                # Not the last header
                header_end = header_matches[i + 1].start()
                header_content = content[match.end():header_end].strip()
            else:
                # Last header
                header_content = content[match.end():].strip()
            
            if not header_content:
                continue
            
            # Include the header in the content
            full_content = match.group(0) + "\n\n" + header_content
            content_tokens = self._count_tokens(full_content)
            
            # Check if adding this header section would exceed max_tokens
            if current_tokens + content_tokens > max_tokens and current_chunk:
                # Save current chunk
                chunks.append({
                    "content": current_chunk,
                    "page_numbers": None,
                    "headers": current_headers.copy()
                })
                
                # Start new chunk with this header
                current_chunk = full_content
                current_headers = [header_text]
                current_tokens = content_tokens
            else:
                # Add this header section to current chunk
                if current_chunk:
                    current_chunk += "\n\n" + full_content
                else:
                    current_chunk = full_content
                current_headers.append(header_text)
                current_tokens += content_tokens
        
        # Add the last chunk
        if current_chunk:
            chunks.append({
                "content": current_chunk,
                "page_numbers": None,
                "headers": current_headers
            })
        
        return chunks

    def _split_large_content(self, content: str, max_tokens: int, min_tokens: int, is_pdf: bool) -> List[Dict[str, Any]]:
        """Split large content at sentence boundaries when no natural boundaries exist."""
        chunks = []
        sentences = re.split(r'(?<=[.!?])\s+', content)
        
        current_chunk = ""
        current_tokens = 0
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            
            sentence_tokens = self._count_tokens(sentence)
            
            # Check if adding this sentence would exceed max_tokens
            if current_tokens + sentence_tokens > max_tokens and current_chunk:
                # Save current chunk
                chunks.append({
                    "content": current_chunk,
                    "page_numbers": None if not is_pdf else [],
                    "headers": None if is_pdf else []
                })
                
                # Start new chunk with this sentence
                current_chunk = sentence
                current_tokens = sentence_tokens
            else:
                # Add this sentence to current chunk
                if current_chunk:
                    current_chunk += " " + sentence
                else:
                    current_chunk = sentence
                current_tokens += sentence_tokens
        
        # Add the last chunk
        if current_chunk:
            chunks.append({
                "content": current_chunk,
                "page_numbers": None if not is_pdf else [],
                "headers": None if is_pdf else []
            })
        
        return chunks

    def split_text_into_chunks_parallel(self, text: str, max_tokens: int = 1000, min_tokens: int = 600, 
                                        num_workers: int = 5, min_section_size: int = 10000) -> List[Dict[str, Any]]:
        """
        Split text into chunks using parallel processing for large documents.
        
        This method distributes the processing work across multiple threads for better performance 
        on large documents by splitting the document into sections first, then processing each section
        in parallel using the token-based chunking method.
        
        Args:
            text: The text to split
            max_tokens: Maximum tokens per chunk
            min_tokens: Minimum tokens per chunk
            num_workers: Number of parallel workers
            min_section_size: Minimum size in characters to use parallel processing
            
        Returns:
            List of chunk dictionaries with content, page_numbers, and headers
        """
        # For small documents, use the regular method
        if len(text) < min_section_size:
            return self.split_text_into_chunks(text, max_tokens, min_tokens)
            
        # For large documents, split into sections first
        try:
            # Extract metadata and content
            metadata, content = self._extract_metadata_and_content(text)
            is_pdf = self._is_pdf_content(metadata)
            is_wetten_overheid = self._is_wetten_overheid_content(metadata)
            
            # Find natural boundaries based on content type
            if is_pdf:
                # Use page boundaries for PDFs
                boundary_pattern = r'--- page \d+ ---'
            elif is_wetten_overheid:
                # Use Artikel-level headers for wetten overheid content
                boundary_pattern = r'^(#{3,4})\s+(.+)$'
            else:
                # Use header boundaries for website content
                boundary_pattern = r'^(#{1,3})\s+(.+)$'
            
            boundary_matches = list(re.finditer(boundary_pattern, content, re.MULTILINE))
            
            # If no boundaries found, revert to regular chunking
            if not boundary_matches:
                return self.split_text_into_chunks(text, max_tokens, min_tokens)
                
            # Create sections from boundaries
            sections = []
            
            # Create overlapping sections based on boundaries
            # Try to make sections roughly equal in size
            target_section_size = len(content) // num_workers
            current_section_start = 0
            
            for match in boundary_matches:
                if match.start() - current_section_start >= target_section_size:
                    # Add some overlap (1000 chars) with the next section for boundary safety
                    end_pos = min(match.start() + 1000, len(content))
                    sections.append(content[current_section_start:end_pos])
                    current_section_start = match.start()
            
            # Add the final section
            if current_section_start < len(content):
                sections.append(content[current_section_start:])
                
            # If we created only one section, just use the regular method
            if len(sections) <= 1:
                return self.split_text_into_chunks(text, max_tokens, min_tokens)
            
            # Process each section in parallel
            all_chunks = []
            
            # Use a shorter timeout for worker threads
            timeout_seconds = 300  # 5 minutes timeout per section
            
            # Create a progress bar with consistent formatting
            with tqdm(
                total=len(sections), 
                desc="Parallel chunking", 
                unit="section", 
                position=0,
                leave=True,
                ncols=100,
                ascii=True,
                bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]'
            ) as parallel_progress:
                
                with concurrent.futures.ThreadPoolExecutor(max_workers=min(num_workers, len(sections))) as executor:
                    # Submit all sections for processing
                    future_to_section = {
                        executor.submit(self._split_section, section, max_tokens, min_tokens, is_pdf, is_wetten_overheid): i 
                        for i, section in enumerate(sections)
                    }
                    
                    # Collect results as they complete
                    for future in concurrent.futures.as_completed(future_to_section):
                        section_index = future_to_section[future]
                        try:
                            section_chunks = future.result(timeout=timeout_seconds)
                            all_chunks.extend(section_chunks)
                            parallel_progress.update(1)
                        except concurrent.futures.TimeoutError:
                            logger.error(f"Section {section_index} processing timed out after {timeout_seconds} seconds")
                            parallel_progress.update(1)
                        except Exception as e:
                            logger.error(f"Error processing section {section_index}: {str(e)}")
                            parallel_progress.update(1)
            
            # If no chunks were generated with parallel processing, fall back to regular method
            if not all_chunks:
                logger.warning("Parallel chunking failed to produce chunks, falling back to regular chunking")
                return self.split_text_into_chunks(text, max_tokens, min_tokens)
                
            return all_chunks
            
        except Exception as e:
            logger.error(f"Error in parallel chunking: {str(e)}")
            # Fall back to regular chunking
            return self.split_text_into_chunks(text, max_tokens, min_tokens)

    def _split_section(self, section_content: str, max_tokens: int, min_tokens: int, is_pdf: bool, is_wetten_overheid: bool = False) -> List[Dict[str, Any]]:
        """Split a section of content using the appropriate method based on content type."""
        if is_pdf:
            return self._split_pdf_content(section_content, max_tokens, min_tokens)
        elif is_wetten_overheid:
            return self._split_wetten_overheid_content(section_content, max_tokens, min_tokens)
        else:
            return self._split_website_content(section_content, max_tokens, min_tokens)

    def generate_chunk_embedding(self, chunk: str) -> List[float]:
        """
        Generate embedding for a single chunk of text.
        
        Args:
            chunk: The text chunk to generate an embedding for
            
        Returns:
            Embedding vector as a list of floats, or empty list on error
        """
        url = Credentials.get_embedding_link()
        headers = {"Content-Type": "application/json", "api-key": self.api_key}
        data = {"input": chunk, "model": self.embedding_model, "dimensions": self.settings.embedding_dimensions}
        
        try:
            response = requests.post(url, headers=headers, json=data)
            response.raise_for_status()
            return response.json()["data"][0]["embedding"]
        except requests.exceptions.HTTPError as err:
            logger.error(f"Error generating embedding: {err}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return []

    def generate_embeddings(self, text: str, already_chunked: bool = False) -> List[List[float]]:
        """
        Generate embeddings for the given text.
        
        Args:
            text: The text to generate embeddings for
            already_chunked: If True, text is treated as a single chunk. If False, text will be split into chunks.
            
        Returns:
            List of embeddings for each chunk
        """
        # If already chunked, just generate a single embedding
        if already_chunked:
            embedding = self.generate_chunk_embedding(text)
            return [embedding] if embedding else []
            
        # Otherwise, split into chunks and generate embeddings for each
        text_chunks = self.split_text_into_chunks(text)
        chunk_embeddings = []

        for chunk_dict in tqdm(
            text_chunks, 
            desc="Generating embeddings", 
            unit="chunk",
            position=0,
            leave=True,
            ncols=100,
            ascii=True,
            bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]'
        ):
            chunk_content = chunk_dict["content"]
            embedding = self.generate_chunk_embedding(chunk_content)
            if embedding:
                chunk_embeddings.append(embedding)

        return chunk_embeddings

    def upsert_chunk(
        self, unique_id: str, content: str, title: str, metadata: dict, embedding: List[float], 
        date_scraped: datetime, date_chunked: datetime, page_numbers: List[int] = None, headers: List[str] = None
    ) -> None:
        """Insert or update a single chunk in the database."""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                    INSERT INTO document_chunks (
                        id, title, content, year, information_type, data_category, 
                        is_algemeen, is_autobelastingen, is_dividendbelasting, 
                        is_formeel_belastingrecht, is_inkomstenbelasting, 
                        is_lokale_heffingen, is_loonbelasting, is_omzetbelasting, 
                        is_pensioen_en_lijfrente, is_schenken_en_erven, 
                        is_sociale_verzekeringen, is_vennootschapsbelasting, 
                        is_wet_op_belastingen_van_rechtsverkeer, 
                        target_group, source, source_url, page_numbers, headers, 
                        vector, date_scraped, date_chunked
                    )
                    VALUES (
                        %s, %s, %s, %s, %s, %s, 
                        %s, %s, %s, %s, %s, 
                        %s, %s, %s, %s, %s, 
                        %s, %s, %s, %s, %s, 
                        %s, %s, %s, %s, %s, %s
                    )
                    ON CONFLICT (id) DO UPDATE 
                    SET title = EXCLUDED.title,
                        content = EXCLUDED.content, 
                        year = EXCLUDED.year,
                        information_type = EXCLUDED.information_type,
                        data_category = EXCLUDED.data_category,
                        is_algemeen = EXCLUDED.is_algemeen,
                        is_autobelastingen = EXCLUDED.is_autobelastingen,
                        is_dividendbelasting = EXCLUDED.is_dividendbelasting,
                        is_formeel_belastingrecht = EXCLUDED.is_formeel_belastingrecht,
                        is_inkomstenbelasting = EXCLUDED.is_inkomstenbelasting,
                        is_lokale_heffingen = EXCLUDED.is_lokale_heffingen,
                        is_loonbelasting = EXCLUDED.is_loonbelasting,
                        is_omzetbelasting = EXCLUDED.is_omzetbelasting,
                        is_pensioen_en_lijfrente = EXCLUDED.is_pensioen_en_lijfrente,
                        is_schenken_en_erven = EXCLUDED.is_schenken_en_erven,
                        is_sociale_verzekeringen = EXCLUDED.is_sociale_verzekeringen,
                        is_vennootschapsbelasting = EXCLUDED.is_vennootschapsbelasting,
                        is_wet_op_belastingen_van_rechtsverkeer = EXCLUDED.is_wet_op_belastingen_van_rechtsverkeer,
                        target_group = EXCLUDED.target_group,
                        source = EXCLUDED.source,
                        source_url = EXCLUDED.source_url,
                        page_numbers = EXCLUDED.page_numbers,
                        headers = EXCLUDED.headers,
                        vector = EXCLUDED.vector,
                        date_scraped = EXCLUDED.date_scraped,
                        date_chunked = EXCLUDED.date_chunked
                    """,
                    (
                        unique_id, 
                        title,
                        content, 
                        metadata.get('year'), 
                        metadata.get('information_type'),
                        metadata.get('data_category'),
                        metadata.get('is_algemeen', False),
                        metadata.get('is_autobelastingen', False),
                        metadata.get('is_dividendbelasting', False),
                        metadata.get('is_formeel_belastingrecht', False),
                        metadata.get('is_inkomstenbelasting', False),
                        metadata.get('is_lokale_heffingen', False),
                        metadata.get('is_loonbelasting', False),
                        metadata.get('is_omzetbelasting', False),
                        metadata.get('is_pensioen_en_lijfrente', False),
                        metadata.get('is_schenken_en_erven', False),
                        metadata.get('is_sociale_verzekeringen', False),
                        metadata.get('is_vennootschapsbelasting', False),
                        metadata.get('is_wet_op_belastingen_van_rechtsverkeer', False),
                        metadata.get('target_group'),
                        metadata.get('source'),
                        metadata.get('source_url'),
                        page_numbers,
                        headers,
                        embedding,
                        date_scraped,
                        date_chunked
                    ),
                )
                conn.commit()
        except Exception as e:
            logger.error(f"Error during insertion: {str(e)}")
            raise

    def search_embedding(
        self, query_embedding: List[float], limit: int
    ) -> List[Tuple[Any, ...]]:
        """
        Perform similarity search in the vector database using the given embedding.

        Args:
            query_embedding (List[float]): The embedding to search with.
            limit (int): The maximum number of results to return.

        Returns:
            List[Tuple[Any, ...]]: A list of tuples containing the search results.
        """
        try:
            # Log the embedding to verify its structure
            logger.info(f"Query embedding length: {len(query_embedding)}")

            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    # Set session-level optimization (once per connection)
                    cur.execute("SET LOCAL ivfflat.probes = %s", (SearchConfig.IVFFLAT_PROBES,))
                    
                    # Use parameterized query with cosine distance for better performance
                    cur.execute(
                        """
                        SELECT id, content, metadata
                        FROM document_chunks
                        ORDER BY vector <=> %s::vector
                        LIMIT %s;
                        """,
                        (query_embedding, limit),  # Pass embedding and limit as parameters
                    )
                    results = cur.fetchall()

            logger.info(f"Found {len(results)} semantic search results.")
            return results
        except Exception as e:
            logger.error(f"Error during semantic search: {str(e)}")
            return []

    def hybrid_search(
            self,
            query: str,
            year: List[int],
            fiscal_topic: List[str],
            limit: int,
            use_reranking: bool = False  # Keep parameter for compatibility but ignore it
    ) -> List[Dict]:
        """
        Perform semantic search with optimized performance.
        
        Args:
            query: The user's query text
            year: List of years the query relates to
            fiscal_topic: List of fiscal topics from FiscalTopic enum values
            limit: Maximum number of results to return
            use_reranking: Ignored - reranking removed for performance
            
        Returns:
            List of sorted chunks based on relevance with scoring fields
        """
        # Skip if the only fiscal topic is "Onbekend"
        if len(fiscal_topic) == 1 and fiscal_topic[0] == "Onbekend":
            logger.info("Skipping hybrid search since fiscal topic is 'Onbekend'")
            return []

        # Perform optimized semantic search directly
        logger.info(f"Performing optimized semantic search with years: {year} and fiscal topics: {fiscal_topic}")
        raw_results = self.semantic_search(query, year, fiscal_topic, limit)
        
        # Convert raw results to expected format with scoring fields
        weights = self.search_weights
        combined_results = []
        
        for result in raw_results:
            combined_result = self.build_combined_result(result, weights, semantic=True)
            combined_results.append(combined_result)
        
        # Sort by final score (which is the same as semantic score since no reranking)
        sorted_results = sorted(combined_results, key=lambda x: x[n.FINAL_SCORE], reverse=True)
        
        logger.info(f"Optimized search returned {len(sorted_results)} results")
        return sorted_results

    def build_combined_result(self, result: Dict, weights: Dict, semantic: bool = False) -> Dict:
        """
        Helper function to build a combined result dict with normalized scoring.
        Simplified version without reranking - only handles semantic scoring.
        """
        # Normalize the distance to a score between 0 and 1 (Smaller distance = higher score)
        # Cosine distance ranges from 0-2 (after 1-cos trick), where 0 = identical, 2 = opposite
        max_distance = SearchConfig.MAX_COSINE_DISTANCE  # Maximum expected cosine distance for our embeddings
        normalized_distance = 1.0 - (min(result.get("distance", max_distance), max_distance) / max_distance)
        
        # Get the years from metadata
        years = result[n.METADATA].get(n.METADATA_YEAR, [])
        
        # Default weight if no valid years
        year_weight = 0.5
        
        # If we have years, calculate weight based on the most recent year
        if years and isinstance(years, list) and len(years) > 0:
            try:
                # Find the most recent year in the list
                most_recent_year = max(int(y) for y in years if isinstance(y, (int, str)) and str(y).isdigit())
                
                # Calculate year weight: more recent years get higher scores
                current_year = datetime.now().year
                year_diff = current_year - most_recent_year
                year_weight = max(0.5, 1.0 - (year_diff * 0.1))  # Minimum weight of 0.5
            except (ValueError, TypeError):
                # Keep default weight if parsing fails
                pass

        # Calculate source weight (Belastingdienst gets higher weight)
        source = result[n.METADATA].get(n.METADATA_SOURCE, "")
        source_weight = 1.2 if source == "Belastingdienst" else 1.0

        # Calculate final semantic score combining distance, year weight, and source weight
        semantic_score = normalized_distance * weights[n.SEMANTIC] * year_weight * source_weight if semantic else 0
        
        return {
            n.ID: result[n.ID],
            n.METADATA_YEAR: result[n.METADATA].get(n.METADATA_YEAR, n.NOT_APPLICABLE),
            n.METADATA_SOURCE: result[n.METADATA].get(n.METADATA_SOURCE, n.NOT_APPLICABLE),
            n.METADATA_DATA_CATEGORY: result[n.METADATA].get(n.METADATA_DATA_CATEGORY, n.NOT_APPLICABLE),
            n.METADATA_FISCAL_TOPIC: result[n.METADATA].get(n.METADATA_FISCAL_TOPIC, n.NOT_APPLICABLE),
            n.METADATA_SOURCE_URL: result[n.METADATA].get(n.METADATA_SOURCE_URL, n.NOT_APPLICABLE),
            n.METADATA_TARGET_GROUP: result[n.METADATA].get(n.METADATA_TARGET_GROUP, n.NOT_APPLICABLE),
            n.METADATA_INFORMATION_TYPE: result[n.METADATA].get(n.METADATA_INFORMATION_TYPE, n.NOT_APPLICABLE),
            n.METADATA_TITLE: result[n.METADATA].get(n.METADATA_TITLE, n.NOT_APPLICABLE),
            n.CONTENT: result[n.CONTENT],
            n.SEMANTIC_SCORE: semantic_score,
            n.RERANK_SCORE: 0,  # Always 0 since we removed reranking
            n.FINAL_SCORE: semantic_score,  # Same as semantic score since no reranking
            "confidence": normalized_distance,
            "year_weight": year_weight,
            "source_weight": source_weight,
            "page_numbers": result[n.METADATA].get("page_numbers"),
            "headers": result[n.METADATA].get("headers")
        }

    def semantic_search(
            self,
            query: str,
            year: List[int],
            fiscal_topic: List[str],
            limit: int = SearchConfig.DEFAULT_SEARCH_LIMIT
    ) -> List[Dict]:
        """
        Search for chunks with embeddings similar to the query, ensuring up to 
        SearchConfig.PRIMAIRE_LIMIT results come from primary data category and up to 
        SearchConfig.OTHER_CATEGORIES_LIMIT from other categories.
        
        Args:
            query: The user's query text
            year: List of years the query relates to
            fiscal_topic: List of fiscal topics from FiscalTopic enum values
            limit: Maximum number of results to return
            
        Returns:
            List of relevant chunks as dictionaries
        """
        if not isinstance(query, str) or not query.strip():
            logger.error("Invalid query provided. It must be a non-empty string.")
            return []

        # If topic is "Onbekend", proceed with a broad search without topic filters

        # Generate the embedding for the query (optimized for single queries)
        import time
        t0 = time.time()
        query_embedding_list = self.generate_embeddings(query, already_chunked=True)
        t1 = time.time()
        
        if not query_embedding_list or len(query_embedding_list) == 0:
            logger.error("Failed to generate a valid query embedding.")
            return []
        query_embedding = query_embedding_list[0]

        # Ensure year is a list of integers for proper PostgreSQL array handling
        if not isinstance(year, list):
            logger.error("Year parameter must be a list of integers.")
            return []
        
        # Validate that all years are integers
        try:
            year = [int(y) for y in year]
        except (ValueError, TypeError):
            logger.error("All year values must be integers.")
            return []

        # Build fiscal topic conditions with SQL injection protection
        allowed_topics = {
            "omzetbelasting", "inkomstenbelasting", "vennootschapsbelasting",
            "algemeen", "autobelastingen", "dividendbelasting", "formeel_belastingrecht",
            "lokale_heffingen", "loonbelasting", "pensioen_en_lijfrente",
            "schenken_en_erven", "sociale_verzekeringen", "wet_op_belastingen_van_rechtsverkeer"
        }
        
        fiscal_topic_conditions = []
        for topic in fiscal_topic:
            if topic == "Onbekend":
                continue
            # Normalize topic name
            normalized_topic = topic.lower().replace(' ', '_').replace('-', '_')
            if normalized_topic in allowed_topics:
                column_name = f"is_{normalized_topic}"
                fiscal_topic_conditions.append(
                    psycopg2.sql.SQL("{} = TRUE").format(psycopg2.sql.Identifier(column_name))
                )
        
        # Default to true if no valid fiscal topics
        fiscal_topic_clause = psycopg2.sql.SQL(" OR ").join(fiscal_topic_conditions) if fiscal_topic_conditions else psycopg2.sql.SQL("TRUE")

        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    logger.info(f"Executing optimized semantic search with years: {year} and fiscal topics: {fiscal_topic}")

                    if SearchConfig.USE_HNSW:
                        # Guardrails: optional fast-fail timeout and disable seq/bitmap scans for this query only
                        try:
                            cur.execute("SET LOCAL plan_cache_mode = 'force_custom_plan';")
                            # Diagnostic toggles (commented by default)
                            # cur.execute("SET LOCAL enable_seqscan = off;")
                            # cur.execute("SET LOCAL enable_bitmapscan = off;")
                        except Exception:
                            pass
                        # Oversampling pattern: force ANN first, then filter
                        alpha = 6  # oversample factor
                        k = limit * alpha  # e.g. 7 * 20 = 140
                        
                        # Tune HNSW search breadth
                        try:
                            cur.execute("SET LOCAL hnsw.ef_search = %s", (SearchConfig.HNSW_EF_SEARCH,))
                        except Exception:
                            pass

                        # ANN-first query with oversampling
                        ann_sql = psycopg2.sql.SQL("""
                        WITH ann AS (
                          SELECT id, vector <=> %s::vector AS distance
                          FROM document_chunks
                          WHERE year && %s::int[]
                            AND ({topics})
                          ORDER BY vector <=> %s::vector
                          LIMIT %s
                        )
                        SELECT 
                          d.id, d.title, d.content, d.year, d.source, d.source_url, d.data_category, 
                          d.information_type, d.target_group, d.page_numbers, d.headers,
                          ARRAY[
                            CASE WHEN d.is_omzetbelasting THEN 'Omzetbelasting' ELSE NULL END,
                            CASE WHEN d.is_inkomstenbelasting THEN 'Inkomstenbelasting' ELSE NULL END,
                            CASE WHEN d.is_vennootschapsbelasting THEN 'Vennootschapsbelasting' ELSE NULL END,
                            CASE WHEN d.is_algemeen THEN 'Algemeen' ELSE NULL END,
                            CASE WHEN d.is_autobelastingen THEN 'Autobelastingen' ELSE NULL END,
                            CASE WHEN d.is_dividendbelasting THEN 'Dividendbelasting' ELSE NULL END,
                            CASE WHEN d.is_formeel_belastingrecht THEN 'Formeel belastingrecht' ELSE NULL END,
                            CASE WHEN d.is_lokale_heffingen THEN 'Lokale heffingen' ELSE NULL END,
                            CASE WHEN d.is_loonbelasting THEN 'Loonbelasting' ELSE NULL END,
                            CASE WHEN d.is_pensioen_en_lijfrente THEN 'Pensioen en lijfrente' ELSE NULL END,
                            CASE WHEN d.is_schenken_en_erven THEN 'Schenken en erven' ELSE NULL END,
                            CASE WHEN d.is_sociale_verzekeringen THEN 'Sociale verzekeringen' ELSE NULL END,
                            CASE WHEN d.is_wet_op_belastingen_van_rechtsverkeer THEN 'Wet op belastingen van rechtsverkeer' ELSE NULL END
                          ] AS fiscal_topic,
                          ann.distance
                        FROM ann
                        JOIN document_chunks d USING (id)
                        ORDER BY ann.distance
                        LIMIT %s
                        """).format(topics=fiscal_topic_clause)

                        params = (query_embedding, year, query_embedding, k, limit)
                        # Use a savepoint so we can recover cleanly from timeouts
                        try:
                            cur.execute("SAVEPOINT ann_sp;")
                        except Exception:
                            pass
                        try:
                            cur.execute(ann_sql, params)
                            rows = cur.fetchall()
                        except Exception as e:
                            if 'statement timeout' in str(e).lower():
                                logger.warning("HNSW ANN query timed out; retrying with lower ef_search and alpha")
                                # Roll back to the savepoint to clear the aborted state
                                try:
                                    cur.execute("ROLLBACK TO SAVEPOINT ann_sp;")
                                except Exception:
                                    try:
                                        conn.rollback()
                                    except Exception:
                                        pass
                                # Retry with smaller search breadth
                                try:
                                    cur.execute("SET LOCAL hnsw.ef_search = %s", (32,))
                                except Exception:
                                    pass
                                alpha_retry = 6
                                k_retry = limit * alpha_retry
                                params_retry = (query_embedding, year, query_embedding, k_retry, limit)
                                try:
                                    cur.execute("SAVEPOINT ann_sp;")
                                except Exception:
                                    pass
                                try:
                                    cur.execute(ann_sql, params_retry)
                                    rows = cur.fetchall()
                                except Exception:
                                    # Graceful exact fallback over small recent candidate pool
                                    exact_sql = psycopg2.sql.SQL(
                                        """
                                        WITH candidates AS (
                                          SELECT id
                                          FROM document_chunks
                                          WHERE year && %s::int[] AND ({topics})
                                          ORDER BY date_chunked DESC
                                          LIMIT 2000
                                        )
                                        SELECT d.id, d.title, d.content, d.year, d.source, d.source_url, d.data_category,
                                               d.information_type, d.target_group, d.page_numbers, d.headers,
                                               ARRAY[
                                                 CASE WHEN d.is_omzetbelasting THEN 'Omzetbelasting' ELSE NULL END,
                                                 CASE WHEN d.is_inkomstenbelasting THEN 'Inkomstenbelasting' ELSE NULL END,
                                                 CASE WHEN d.is_vennootschapsbelasting THEN 'Vennootschapsbelasting' ELSE NULL END,
                                                 CASE WHEN d.is_algemeen THEN 'Algemeen' ELSE NULL END,
                                                 CASE WHEN d.is_autobelastingen THEN 'Autobelastingen' ELSE NULL END,
                                                 CASE WHEN d.is_dividendbelasting THEN 'Dividendbelasting' ELSE NULL END,
                                                 CASE WHEN d.is_formeel_belastingrecht THEN 'Formeel belastingrecht' ELSE NULL END,
                                                 CASE WHEN d.is_lokale_heffingen THEN 'Lokale heffingen' ELSE NULL END,
                                                 CASE WHEN d.is_loonbelasting THEN 'Loonbelasting' ELSE NULL END,
                                                 CASE WHEN d.is_pensioen_en_lijfrente THEN 'Pensioen en lijfrente' ELSE NULL END,
                                                 CASE WHEN d.is_schenken_en_erven THEN 'Schenken en erven' ELSE NULL END,
                                                 CASE WHEN d.is_sociale_verzekeringen THEN 'Sociale verzekeringen' ELSE NULL END,
                                                 CASE WHEN d.is_wet_op_belastingen_van_rechtsverkeer THEN 'Wet op belastingen van rechtsverkeer' ELSE NULL END
                                               ] AS fiscal_topic,
                                               d.vector <=> %s::vector AS distance
                                        FROM document_chunks d
                                        JOIN candidates c USING (id)
                                        ORDER BY distance
                                        LIMIT %s
                                        """
                                    ).format(topics=fiscal_topic_clause)
                                    cur.execute(exact_sql, (year, query_embedding, limit))
                                    rows = cur.fetchall()
                            else:
                                # Not a timeout; rethrow
                                raise
                        column_names = [desc[0] for desc in cur.description]

                        results: List[Dict] = []
                        for row in rows:
                            result_dict = dict(zip(column_names, row))
                            metadata = {
                                n.METADATA_YEAR: result_dict.get("year"),
                                n.METADATA_DATA_CATEGORY: result_dict.get("data_category"),
                                n.METADATA_INFORMATION_TYPE: result_dict.get("information_type"),
                                n.METADATA_TITLE: result_dict.get("title"),
                                n.METADATA_TARGET_GROUP: result_dict.get("target_group"),
                                n.METADATA_SOURCE: result_dict.get("source"),
                                n.METADATA_SOURCE_URL: result_dict.get("source_url"),
                                n.METADATA_FISCAL_TOPIC: result_dict.get("fiscal_topic"),
                                "page_numbers": result_dict.get("page_numbers"),
                                "headers": result_dict.get("headers"),
                            }

                            structured_result = {
                                n.ID: result_dict.get("id"),
                                n.CONTENT: result_dict.get("content"),
                                n.METADATA: metadata,
                                "distance": result_dict.get("distance", 0.0),
                            }
                            results.append(structured_result)

                        t2 = time.time()
                        logger.info(f"Optimized semantic search returned {len(results)} results.")
                        logger.info(f"[perf] embed_ms={(t1-t0)*1000:.1f} db_ms={(t2-t1)*1000:.1f} total_ms={(t2-t0)*1000:.1f}")
                        return results

                    # No IVF fallback path; rely solely on HNSW ANN-first query
                    column_names = [desc[0] for desc in cur.description]

                results: List[Dict] = []
                for row in rows:
                    result_dict = dict(zip(column_names, row))
                    metadata = {
                        n.METADATA_YEAR: result_dict.get("year"),
                        n.METADATA_DATA_CATEGORY: result_dict.get("data_category"),
                        n.METADATA_INFORMATION_TYPE: result_dict.get("information_type"),
                        n.METADATA_TITLE: result_dict.get("title"),
                        n.METADATA_TARGET_GROUP: result_dict.get("target_group"),
                        n.METADATA_SOURCE: result_dict.get("source"),
                        n.METADATA_SOURCE_URL: result_dict.get("source_url"),
                        n.METADATA_FISCAL_TOPIC: result_dict.get("fiscal_topic"),
                        "page_numbers": result_dict.get("page_numbers"),
                        "headers": result_dict.get("headers"),
                    }
                    structured_result = {
                        n.ID: result_dict.get("id"),
                        n.CONTENT: result_dict.get("content"),
                        n.METADATA: metadata,
                        "distance": result_dict.get("distance", 0.0),
                    }
                    results.append(structured_result)

                t2 = time.time()
                logger.info(f"Optimized semantic search returned {len(results)} results.")
                logger.info(f"[perf] embed_ms={(t1-t0)*1000:.1f} db_ms={(t2-t1)*1000:.1f} total_ms={(t2-t0)*1000:.1f}")
                return results
        except Exception as e:
            # One-shot retry for transient EOF/closed-connection errors
            msg = str(e)
            if any(x in msg for x in ["SSL SYSCALL error", "connection already closed", "server closed the connection"]):
                logger.warning("Transient DB error during vector search; retrying once...")
                try:
                    with self.get_connection() as conn:
                        with conn.cursor() as cur:
                            # Minimal retry using the HNSW ANN-first path with smaller breadth
                            try:
                                cur.execute("SET LOCAL hnsw.ef_search = %s", (32,))
                            except Exception:
                                pass
                            alpha_retry = 6
                            k_retry = SearchConfig.SEARCH_LIMIT * alpha_retry
                            cur.execute(
                                psycopg2.sql.SQL(
                                    """
                                    WITH ann AS (
                                      SELECT id, vector <=> %s::vector AS distance
                                      FROM document_chunks
                                      ORDER BY vector <=> %s::vector
                                      LIMIT %s
                                    )
                                    SELECT id, title, content, year, source, source_url, data_category, 
                                           information_type, target_group, page_numbers, headers,
                                           ARRAY[
                                             CASE WHEN is_omzetbelasting THEN 'Omzetbelasting' ELSE NULL END,
                                             CASE WHEN is_inkomstenbelasting THEN 'Inkomstenbelasting' ELSE NULL END,
                                             CASE WHEN is_vennootschapsbelasting THEN 'Vennootschapsbelasting' ELSE NULL END,
                                             CASE WHEN is_algemeen THEN 'Algemeen' ELSE NULL END,
                                             CASE WHEN is_autobelastingen THEN 'Autobelastingen' ELSE NULL END,
                                             CASE WHEN is_dividendbelasting THEN 'Dividendbelasting' ELSE NULL END,
                                             CASE WHEN is_formeel_belastingrecht THEN 'Formeel belastingrecht' ELSE NULL END,
                                             CASE WHEN is_lokale_heffingen THEN 'Lokale heffingen' ELSE NULL END,
                                             CASE WHEN is_loonbelasting THEN 'Loonbelasting' ELSE NULL END,
                                             CASE WHEN is_pensioen_en_lijfrente THEN 'Pensioen en lijfrente' ELSE NULL END,
                                             CASE WHEN is_schenken_en_erven THEN 'Schenken en erven' ELSE NULL END,
                                             CASE WHEN is_sociale_verzekeringen THEN 'Sociale verzekeringen' ELSE NULL END,
                                             CASE WHEN is_wet_op_belastingen_van_rechtsverkeer THEN 'Wet op belastingen van rechtsverkeer' ELSE NULL END
                                           ] AS fiscal_topic,
                                           ann.distance
                                    FROM ann
                                    JOIN document_chunks d USING (id)
                                    WHERE d.year && %s::int[]
                                    ORDER BY ann.distance
                                    LIMIT %s
                                    """
                                ),
                                (query_embedding, query_embedding, k_retry, year, SearchConfig.SEARCH_LIMIT)
                            )
                            rows = cur.fetchall()
                            column_names = [desc[0] for desc in cur.description]

                        results: List[Dict] = []
                        for row in rows:
                            result_dict = dict(zip(column_names, row))
                            metadata = {
                                n.METADATA_YEAR: result_dict.get("year"),
                                n.METADATA_DATA_CATEGORY: result_dict.get("data_category"),
                                n.METADATA_INFORMATION_TYPE: result_dict.get("information_type"),
                                n.METADATA_TITLE: result_dict.get("title"),
                                n.METADATA_TARGET_GROUP: result_dict.get("target_group"),
                                n.METADATA_SOURCE: result_dict.get("source"),
                                n.METADATA_SOURCE_URL: result_dict.get("source_url"),
                                n.METADATA_FISCAL_TOPIC: result_dict.get("fiscal_topic"),
                                "page_numbers": result_dict.get("page_numbers"),
                                "headers": result_dict.get("headers"),
                            }
                            structured_result = {
                                n.ID: result_dict.get("id"),
                                n.CONTENT: result_dict.get("content"),
                                n.METADATA: metadata,
                                "distance": result_dict.get("distance", 0.0),
                            }
                            results.append(structured_result)

                        logger.info(f"Optimized semantic search returned {len(results)} results.")
                        return results
                except Exception as e2:
                    logger.error(f"Retry failed during optimized vector search: {e2}")
                    return []
            logger.error(f"Error during optimized vector search: {e}")
            return []
