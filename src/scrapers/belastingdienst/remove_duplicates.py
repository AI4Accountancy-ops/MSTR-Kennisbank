import asyncio
import hashlib
import os
import re
from datetime import datetime
from typing import Dict, List, Set, Tuple
from collections import defaultdict

from cloud.storage import AzureStorageClient
from definitions.enums import Source
from logger.logger import Logger

logger = Logger.get_logger(__name__)

class DuplicateRemover:
    """
    Script to detect and remove duplicate files from Belastingdienst/extra_links folder.
    Detects duplicates based on content similarity and keeps the first occurrence.
    """
    
    BLOB_FOLDER = f"{Source.BELASTINGDIENST.value}/extra_links"
    
    def __init__(self):
        self.storage_client = AzureStorageClient()
        self.content_hashes: Dict[str, str] = {}  # content_hash -> blob_name
        self.duplicates: List[Tuple[str, str]] = []  # (original, duplicate)
        self.removed_count = 0
        
    def get_content_hash(self, content: str) -> str:
        """
        Generate a hash of the content, excluding metadata that might differ.
        
        Args:
            content: The file content
            
        Returns:
            A hash representing the actual content
        """
        # Remove metadata lines that might differ between duplicates
        lines = content.split('\n')
        content_lines = []
        
        for line in lines:
            # Skip metadata lines that might differ
            if any(line.startswith(prefix) for prefix in [
                'Year:', 'Title:', 'Source:', 'Data Category:', 'URL:', 'Scraped at:'
            ]):
                continue
            content_lines.append(line)
        
        # Join content lines and create hash
        content_text = '\n'.join(content_lines).strip()
        return hashlib.md5(content_text.encode('utf-8')).hexdigest()
    
    def extract_base_title(self, filename: str) -> str:
        """
        Extract the base title from a filename (remove hash and extension).
        
        Args:
            filename: The blob name
            
        Returns:
            The base title without hash and extension
        """
        # Remove the folder prefix
        if filename.startswith(f"{self.BLOB_FOLDER}/"):
            filename = filename[len(f"{self.BLOB_FOLDER}/"):]
        
        # Remove .txt extension
        if filename.endswith('.txt'):
            filename = filename[:-4]
        
        # Remove the hash suffix (last underscore followed by 4 digits)
        filename = re.sub(r'_\d{4}$', '', filename)
        
        return filename
    
    async def find_duplicates(self) -> Dict[str, List[str]]:
        """
        Find duplicate files based on content similarity.
        
        Returns:
            Dictionary mapping base titles to lists of blob names
        """
        logger.info("Scanning blob storage for files...")
        
        # Get all files in the extra_links folder
        blobs = self.storage_client.list_blobs_in_folder(self.BLOB_FOLDER)
        
        # Group files by base title
        title_groups: Dict[str, List[str]] = defaultdict(list)
        
        for blob_name in blobs:
            if blob_name.endswith('.txt'):
                base_title = self.extract_base_title(blob_name)
                title_groups[base_title].append(blob_name)
        
        # Find groups with multiple files (potential duplicates)
        potential_duplicates = {
            title: blob_names 
            for title, blob_names in title_groups.items() 
            if len(blob_names) > 1
        }
        
        logger.info(f"Found {len(potential_duplicates)} potential duplicate groups")
        
        # Check content similarity within each group
        confirmed_duplicates: Dict[str, List[str]] = {}
        
        for base_title, blob_names in potential_duplicates.items():
            logger.info(f"Checking group: {base_title} ({len(blob_names)} files)")
            
            content_hashes = {}
            duplicate_group = []
            
            for blob_name in blob_names:
                try:
                    # Download and read the file content
                    content = self.storage_client.download_blob_to_memory(blob_name)
                    if content:
                        content_hash = self.get_content_hash(content)
                        
                        if content_hash in content_hashes:
                            # Found a duplicate
                            duplicate_group.append(blob_name)
                        else:
                            content_hashes[content_hash] = blob_name
                            
                except Exception as e:
                    logger.error(f"Error reading {blob_name}: {str(e)}")
                    continue
            
            if duplicate_group:
                confirmed_duplicates[base_title] = duplicate_group
                logger.info(f"  Found {len(duplicate_group)} duplicates in {base_title}")
        
        return confirmed_duplicates
    
    async def remove_duplicates(self, duplicates: Dict[str, List[str]], dry_run: bool = True) -> None:
        """
        Remove duplicate files, keeping the first occurrence.
        
        Args:
            duplicates: Dictionary mapping base titles to lists of duplicate blob names
            dry_run: If True, only log what would be deleted without actually deleting
        """
        total_duplicates = sum(len(blob_names) for blob_names in duplicates.values())
        
        if dry_run:
            logger.info(f"DRY RUN: Would remove {total_duplicates} duplicate files")
        else:
            logger.info(f"Removing {total_duplicates} duplicate files...")
        
        for base_title, blob_names in duplicates.items():
            logger.info(f"Processing duplicates for: {base_title}")
            
            for blob_name in blob_names:
                try:
                    if dry_run:
                        logger.info(f"  DRY RUN: Would delete {blob_name}")
                    else:
                        self.storage_client.remove_blob(blob_name)
                        logger.info(f"  Deleted: {blob_name}")
                        self.removed_count += 1
                        
                except Exception as e:
                    logger.error(f"Error deleting {blob_name}: {str(e)}")
        
        if not dry_run:
            logger.info(f"Successfully removed {self.removed_count} duplicate files")
    
    async def analyze_duplicates(self) -> None:
        """
        Analyze and report on duplicate files.
        """
        logger.info("Starting duplicate analysis...")
        
        # Find duplicates
        duplicates = await self.find_duplicates()
        
        if not duplicates:
            logger.info("No duplicates found!")
            return
        
        # Report findings
        logger.info(f"\n=== DUPLICATE ANALYSIS REPORT ===")
        logger.info(f"Found {len(duplicates)} groups with duplicates")
        
        total_files = 0
        total_duplicates = 0
        
        for base_title, blob_names in duplicates.items():
            logger.info(f"\nGroup: {base_title}")
            logger.info(f"  Files: {len(blob_names)}")
            for blob_name in blob_names:
                logger.info(f"    - {blob_name}")
            total_files += len(blob_names)
            total_duplicates += len(blob_names) - 1  # One file is kept, rest are duplicates
        
        logger.info(f"\nSummary:")
        logger.info(f"  Total files in duplicate groups: {total_files}")
        logger.info(f"  Total duplicates to remove: {total_duplicates}")
        logger.info(f"  Files to keep: {total_files - total_duplicates}")
        
        return duplicates


async def main():
    """Main function to run the duplicate removal process."""
    start_time = datetime.now()
    logger.info(f"Starting duplicate removal process at {start_time.isoformat()}")
    
    # Create the duplicate remover
    remover = DuplicateRemover()
    
    # First, analyze duplicates
    duplicates = await remover.analyze_duplicates()
    
    if not duplicates:
        logger.info("No duplicates found. Exiting.")
        return
    
    # Ask user if they want to proceed with removal
    print("\n" + "="*60)
    print("DUPLICATE REMOVAL READY")
    print("="*60)
    print("The script has found duplicate files based on content similarity.")
    print("It will keep the first occurrence and remove the duplicates.")
    print("\nOptions:")
    print("1. Dry run (show what would be deleted without actually deleting)")
    print("2. Remove duplicates (actually delete the files)")
    print("3. Exit without making changes")
    
    while True:
        choice = input("\nEnter your choice (1, 2, or 3): ").strip()
        
        if choice == "1":
            logger.info("Performing dry run...")
            await remover.remove_duplicates(duplicates, dry_run=True)
            break
        elif choice == "2":
            logger.info("Removing duplicates...")
            await remover.remove_duplicates(duplicates, dry_run=False)
            break
        elif choice == "3":
            logger.info("Exiting without making changes.")
            break
        else:
            print("Invalid choice. Please enter 1, 2, or 3.")
    
    end_time = datetime.now()
    duration = end_time - start_time
    logger.info(f"Duplicate removal process completed at {end_time.isoformat()}")
    logger.info(f"Total duration: {duration}")


if __name__ == "__main__":
    asyncio.run(main()) 