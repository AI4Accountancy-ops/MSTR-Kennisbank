import re
import uuid
import sys
import concurrent.futures
import time
from typing import Dict, Optional, Any
from datetime import datetime

from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient, BlobClient
from tqdm import tqdm

from definitions.credentials import Credentials
from definitions.paths import Paths
from definitions.enums import Source
from logger.logger import Logger
from services.vector_store import VectorStore

logger = Logger.get_logger(__name__)
paths = Paths()

# Configure tqdm for proper display
tqdm_kwargs = {
    'ncols': 100,  # Fixed width
    'ascii': True,  # Use ASCII characters instead of Unicode blocks
    'bar_format': '{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]'
}


def retry_with_backoff(func, max_retries=5, base_delay=300):
    """
    Retry function with exponential backoff for token limit errors.
    
    Args:
        func: Function to retry
        max_retries: Maximum number of retry attempts
        base_delay: Base delay in seconds (5 minutes)
        
    Returns:
        Function result or raises exception after all retries
    """
    for attempt in range(max_retries + 1):
        try:
            return func()
        except Exception as e:
            error_msg = str(e).lower()
            
            # Check if it's a token limit error
            is_token_limit_error = any(keyword in error_msg for keyword in [
                'token', 'limit', 'quota', 'rate limit', 'too many requests', 
                '429', 'throttled', 'exceeded'
            ])
            
            if is_token_limit_error and attempt < max_retries:
                # Calculate delay with exponential backoff
                delay = base_delay * (2 ** attempt)  # 5min, 10min, 20min, 40min, 80min
                logger.warning(f"Token limit error encountered (attempt {attempt + 1}/{max_retries + 1}). "
                             f"Retrying in {delay} seconds... Error: {str(e)}")
                time.sleep(delay)
                continue
            else:
                # Either not a token limit error or max retries reached
                if is_token_limit_error:
                    logger.error(f"Max retries ({max_retries}) reached for token limit error. "
                               f"Final error: {str(e)}")
                raise e


def extract_content_from_text(text: str) -> Optional[str]:
    """
    Extract the content part from a text file
    Assumes content is placed after "Content:" in the file
    """
    # Look for the Content: marker in the text
    content_match = re.search(r"Content:(.*?)(?:\n\n[A-Za-z]+:|$)", text, re.DOTALL)
    
    if content_match:
        return content_match.group(1).strip()
    else:
        # If no specific Content: section found, return the whole text
        return text


def extract_metadata_from_file(text: str) -> Dict[str, Any]:
    """
    Extract all metadata from the file header
    Parses the structured format used in the scraper
    
    Returns a dictionary with all available metadata fields
    """
    metadata = {
        "year": [],
        "title": "",
        "source": "",
        "data_category": "",
        "source_url": "",
        "date_scraped": ""
    }
    
    # Extract Year
    year_match = re.search(r"Year:\s*\[(.*?)\]", text)
    if year_match:
        try:
            # Parse years from format like [2023, 2024, 2025]
            years_str = year_match.group(1).strip()
            years = [int(y.strip()) for y in years_str.split(',') if y.strip().isdigit()]
            if years:
                metadata["year"] = years
        except Exception as e:
            logger.warning(f"Error parsing year: {e}")
    
    # Extract Title
    title_match = re.search(r"Title:\s*(.*?)$", text, re.MULTILINE)
    if title_match:
        metadata["title"] = title_match.group(1).strip()
    
    # Extract Source
    source_match = re.search(r"Source:\s*(.*?)$", text, re.MULTILINE)
    if source_match:
        metadata["source"] = source_match.group(1).strip()
    
    # Extract Data Category
    category_match = re.search(r"Data Category:\s*(.*?)$", text, re.MULTILINE)
    if category_match:
        metadata["data_category"] = category_match.group(1).strip()
    
    # Extract URL
    url_match = re.search(r"URL:\s*(.*?)$", text, re.MULTILINE)
    if url_match:
        metadata["source_url"] = url_match.group(1).strip()
    
    # Extract Scraped at date
    scraped_match = re.search(r"Scraped at:\s*([\d\-T:\.]+)", text)
    if scraped_match:
        metadata["date_scraped"] = scraped_match.group(1).strip()
    
    return metadata


def process_text_file(blob_client: BlobClient, vector_store: VectorStore) -> None:
    """
    Process a single text file from blob storage:
    1. Extract structured metadata directly from file header
    2. Analyze content using LLM for fiscal topics, info type, and target group
    3. Split content into chunks using token-based approach (PDF vs Website content)
    4. Generate embeddings for each chunk
    5. Upsert chunks to database with page_numbers and headers metadata
    """
    try:
        # Download blob content
        blob_content = blob_client.download_blob().readall()
        text_content = blob_content.decode('utf-8')
        
        logger.info(f"Processing file: {blob_client.blob_name}")
        
        # Extract metadata directly from file header
        metadata = extract_metadata_from_file(text_content)
        
        # Extract the actual content part (after "Content:") for LLM analysis
        content = extract_content_from_text(text_content)
        if not content:
            logger.warning(f"No content found in {blob_client.blob_name}")
            return
        
        # Analyze content using LLM for fiscal topics, information type and target group
        # Use retry mechanism for token limit errors
        content_analysis = retry_with_backoff(
            lambda: vector_store.generate_metadata(content)
        )
        
        # Merge the content analysis into the metadata
        metadata.update(content_analysis)
        
        # Use our new token-based chunking with content type detection
        try:
            # Try parallel chunking first
            text_chunks = vector_store.split_text_into_chunks_parallel(text_content)
            
            # Check if we have chunks and didn't time out
            if not text_chunks:
                logger.warning("Parallel chunking returned no chunks, falling back to regular chunking")
                text_chunks = vector_store.split_text_into_chunks(text_content)
        except Exception as e:
            logger.error(f"Error during parallel chunking: {str(e)}")
            logger.info("Falling back to regular chunking")
            text_chunks = vector_store.split_text_into_chunks(text_content)
            
        if not text_chunks:
            logger.error(f"Failed to generate chunks for {blob_client.blob_name}")
            return
        
        logger.info(f"Generated {len(text_chunks)} chunks for processing")
        
        # Log chunking information
        pdf_chunks = sum(1 for chunk in text_chunks if chunk.get("page_numbers") is not None)
        header_chunks = sum(1 for chunk in text_chunks if chunk.get("headers") is not None)
        logger.info(f"Chunk breakdown: {pdf_chunks} PDF chunks (with page numbers), {header_chunks} website chunks (with headers)")
            
        # Track embedding and database insertion in one progress bar
        with tqdm(total=len(text_chunks), desc="Processing chunks", unit="chunk", position=0, leave=True, **tqdm_kwargs) as pbar:
            # Disable normal logging during progress bar updates
            chunk_errors = 0
            for i, chunk_dict in enumerate(text_chunks):
                try:
                    # Extract chunk content and metadata
                    chunk_content = chunk_dict["content"]
                    page_numbers = chunk_dict.get("page_numbers")
                    headers = chunk_dict.get("headers")
                    
                    # Generate embedding for this single chunk with retry mechanism
                    embedding = retry_with_backoff(
                        lambda: vector_store.generate_chunk_embedding(chunk_content)
                    )
                    if not embedding:
                        chunk_errors += 1
                        continue
                        
                    # Create a unique ID for this chunk
                    unique_id = str(uuid.uuid4())

                    timestamp = datetime.now()
                    
                    # Upsert the chunk to the database with page_numbers and headers
                    retry_with_backoff(
                        lambda: vector_store.upsert_chunk(
                            unique_id=unique_id,
                            title=metadata.get("title", ""),
                            content=chunk_content,
                            metadata=metadata,
                            embedding=embedding,
                            date_scraped=metadata.get("date_scraped", datetime.now().isoformat()),
                            date_chunked=timestamp,
                            page_numbers=page_numbers,
                            headers=headers
                        )
                    )
                    
                except Exception as e:
                    chunk_errors += 1
                finally:
                    pbar.update(1)  # Always update progress
        
        processed_count = len(text_chunks) - chunk_errors
        logger.info(f"Completed processing {processed_count} chunks from: {blob_client.blob_name}")
            
    except Exception as e:
        logger.error(f"Error processing file {blob_client.blob_name}: {str(e)}")


def process_all_txt_files(source_folder=None):
    """
    Process all .txt files in Azure blob storage with parallel processing
    
    Args:
        source_folder: Optional Source enum value to filter by folder
    """
    # Get storage account credentials
    account_name = Credentials.get_azure_storage_account_name()
    container_name = Credentials.get_azure_storage_container_name()
    
    # Set up the blob service client
    credential = DefaultAzureCredential()
    blob_service_client = BlobServiceClient(
        account_url=f"https://{account_name}.blob.core.windows.net",
        credential=credential,
    )
    container_client = blob_service_client.get_container_client(container_name)
    
    # Initialize vector store
    vector_store = VectorStore()
    
    # Get all blobs
    blobs = list(container_client.list_blobs())
    
    # Filter for .txt files
    txt_blobs = [blob for blob in blobs if blob.name.endswith('.txt')]
    
    # Filter by source folder if specified
    if source_folder:
        folder_path = f"{source_folder.value}/"
        txt_blobs = [blob for blob in txt_blobs if folder_path in blob.name]
        logger.info(f"Processing files from folder: {source_folder.value}")
    
    # Special handling for Belastingdienst - process both main folder and extra_links subfolder
    if source_folder == Source.BELASTINGDIENST:
        # Filter to process both main Belastingdienst folder and extra_links subfolder
        main_folder = f"{source_folder.value}/"
        extra_links_folder = f"{source_folder.value}/extra_links/"
        
        # Include files from both folders
        filtered_blobs = []
        for blob in txt_blobs:
            if main_folder in blob.name:
                # Include files from main folder (but exclude extra_links to avoid duplicates)
                if extra_links_folder not in blob.name:
                    filtered_blobs.append(blob)
                # Also include files from extra_links folder
                elif extra_links_folder in blob.name:
                    filtered_blobs.append(blob)
        
        txt_blobs = filtered_blobs
        logger.info(f"Filtered to process Belastingdienst main folder and extra_links subfolder: {len(txt_blobs)} files found")
    
    logger.info(f"Found {len(txt_blobs)} .txt files to process")
    
    # Process files in parallel with 5 workers
    num_workers = 5
    logger.info(f"Processing {len(txt_blobs)} files with {num_workers} parallel workers")
    
    with tqdm(total=len(txt_blobs), desc="Processing files", unit="file", position=0, leave=True, **tqdm_kwargs) as pbar:
        file_errors = 0
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=num_workers) as executor:
            # Submit all files for processing
            future_to_blob = {
                executor.submit(process_text_file, container_client.get_blob_client(blob.name), vector_store): blob.name 
                for blob in txt_blobs
            }
            
            # Collect results as they complete
            for future in concurrent.futures.as_completed(future_to_blob):
                blob_name = future_to_blob[future]
                try:
                    future.result(timeout=600)  # 10 minutes timeout per file
                except concurrent.futures.TimeoutError:
                    file_errors += 1
                    logger.error(f"File {blob_name} processing timed out after 10 minutes")
                except Exception as e:
                    file_errors += 1
                    logger.error(f"Error processing blob {blob_name}: {str(e)}")
                finally:
                    pbar.update(1)  # Always update progress
                
    logger.info(f"Processing complete. Successfully processed {len(txt_blobs) - file_errors} files out of {len(txt_blobs)}.")


if __name__ == "__main__":
    logger.info("=== Starting Azure Blob Storage Processing for Vector Database ===")
    
    # Choose which folder to process
    # Use None to process all files or a specific Source enum value to filter
    
    # Example: process only Wetten Overheid files
    process_all_txt_files(source_folder=Source.WETTEN_OVERHEID)
    
    # Example: process only Belastingdienst files
    # process_all_txt_files(source_folder=Source.BELASTINGDIENST)
    
    # Example: process all files
    # process_all_txt_files(source_folder=None)
    
    logger.info("=== Finished processing files to vector database ===")
