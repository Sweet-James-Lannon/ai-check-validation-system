# services/onedrive_service.py
"""
OneDrive Service - Microsoft Graph API Client
Handles all OneDrive operations: folders, uploads, file management
"""

import requests
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional, List, Dict, Any
import time

logger = logging.getLogger(__name__)


class OneDriveService:
    """
    Microsoft Graph API client for OneDrive operations.
    
    Usage:
        onedrive = OneDriveService(access_token)
        folder_id = onedrive.create_folder_if_not_exists(parent_id, "My Folder")
        onedrive.upload_file(folder_id, "document.pdf", pdf_bytes)
    """
    
    def __init__(self, access_token: str):
        self.access_token = access_token
        self.base_url = "https://graph.microsoft.com/v1.0/me/drive"
        self.headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
    
    # =========================================================================
    # FOLDER OPERATIONS
    # =========================================================================
    
    def list_folder(self, folder_id: str) -> List[Dict[str, Any]]:
        """
        List all items in a folder.
        
        Args:
            folder_id: OneDrive folder ID
            
        Returns:
            List of items (files and folders)
        """
        try:
            response = requests.get(
                f"{self.base_url}/items/{folder_id}/children",
                headers=self.headers,
                timeout=30
            )
            response.raise_for_status()
            return response.json().get('value', [])
        except requests.RequestException as e:
            logger.error(f"Failed to list folder {folder_id}: {e}")
            raise
    
    def folder_exists(self, parent_id: str, folder_name: str) -> Optional[str]:
        """
        Check if a folder exists within a parent folder.
        
        Args:
            parent_id: Parent folder ID
            folder_name: Name of folder to find
            
        Returns:
            Folder ID if found, None otherwise
        """
        items = self.list_folder(parent_id)
        for item in items:
            if item.get('name') == folder_name and 'folder' in item:
                logger.info(f"Found existing folder: {folder_name} ({item['id']})")
                return item['id']
        return None
    
    def create_folder(self, parent_id: str, folder_name: str) -> str:
        """
        Create a new folder.
        
        Args:
            parent_id: Parent folder ID
            folder_name: Name for new folder
            
        Returns:
            New folder ID
        """
        try:
            response = requests.post(
                f"{self.base_url}/items/{parent_id}/children",
                headers=self.headers,
                json={
                    "name": folder_name,
                    "folder": {},
                    "@microsoft.graph.conflictBehavior": "fail"
                },
                timeout=30
            )
            response.raise_for_status()
            folder_id = response.json()['id']
            logger.info(f"Created folder: {folder_name} ({folder_id})")
            return folder_id
        except requests.RequestException as e:
            logger.error(f"Failed to create folder {folder_name}: {e}")
            raise
    
    def create_folder_if_not_exists(self, parent_id: str, folder_name: str) -> str:
        """
        Create folder only if it doesn't already exist.
        
        Args:
            parent_id: Parent folder ID
            folder_name: Name for folder
            
        Returns:
            Folder ID (existing or newly created)
        """
        existing_id = self.folder_exists(parent_id, folder_name)
        if existing_id:
            logger.info(f"Reusing existing folder: {folder_name}")
            return existing_id
        return self.create_folder(parent_id, folder_name)
    
    # =========================================================================
    # FILE OPERATIONS
    # =========================================================================
    
    def upload_file(self, parent_id: str, filename: str, content: bytes) -> Dict[str, Any]:
        """
        Upload a file to OneDrive.
        
        Args:
            parent_id: Parent folder ID
            filename: Name for the file
            content: File content as bytes
            
        Returns:
            OneDrive file metadata
        """
        try:
            response = requests.put(
                f"{self.base_url}/items/{parent_id}:/{filename}:/content",
                headers={
                    "Authorization": f"Bearer {self.access_token}",
                    "Content-Type": "application/pdf"
                },
                data=content,
                timeout=60
            )
            response.raise_for_status()
            logger.info(f"Uploaded: {filename}")
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Failed to upload {filename}: {e}")
            raise
    
    def upload_file_with_retry(
        self, 
        parent_id: str, 
        filename: str, 
        content: bytes,
        max_retries: int = 3
    ) -> Dict[str, Any]:
        """
        Upload a file with automatic retry on failure.
        
        Args:
            parent_id: Parent folder ID
            filename: Name for the file
            content: File content as bytes
            max_retries: Maximum retry attempts
            
        Returns:
            OneDrive file metadata
        """
        last_error = None
        for attempt in range(max_retries):
            try:
                return self.upload_file(parent_id, filename, content)
            except Exception as e:
                last_error = e
                wait_time = (attempt + 1) * 2  # Exponential backoff: 2, 4, 6 seconds
                logger.warning(f"Upload attempt {attempt + 1} failed for {filename}, retrying in {wait_time}s...")
                time.sleep(wait_time)
        
        logger.error(f"All upload attempts failed for {filename}")
        raise last_error
    
    def upload_files_parallel(
        self,
        parent_id: str,
        files: List[Dict[str, Any]],
        max_workers: int = 5
    ) -> Dict[str, Any]:
        """
        Upload multiple files in parallel for speed.
        
        Args:
            parent_id: Parent folder ID
            files: List of dicts with 'filename' and 'content' keys
            max_workers: Number of parallel upload threads
            
        Returns:
            Dict with 'successful' and 'failed' lists
        """
        results = {
            'successful': [],
            'failed': []
        }
        
        def upload_one(file_info):
            try:
                result = self.upload_file_with_retry(
                    parent_id,
                    file_info['filename'],
                    file_info['content']
                )
                return {'filename': file_info['filename'], 'success': True, 'result': result}
            except Exception as e:
                return {'filename': file_info['filename'], 'success': False, 'error': str(e)}
        
        logger.info(f"Starting parallel upload of {len(files)} files with {max_workers} workers")
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(upload_one, f): f for f in files}
            
            for future in as_completed(futures):
                result = future.result()
                if result['success']:
                    results['successful'].append(result['filename'])
                else:
                    results['failed'].append({
                        'filename': result['filename'],
                        'error': result['error']
                    })
        
        elapsed = time.time() - start_time
        logger.info(f"Parallel upload complete: {len(results['successful'])} successful, "
                   f"{len(results['failed'])} failed in {elapsed:.1f}s")
        
        return results
    

    def upload_files_parallel_multi_folder(self,files: List[Dict[str, Any]],max_workers: int = 15) -> Dict[str, Any]:
        '''
        Upload files to MULTIPLE folders in parallel.
        
        Args:
            files: List of dicts with 'filename', 'content', and 'parent_id'
            max_workers: Number of parallel upload threads
            
        Returns:
            Dict with 'successful' and 'failed' lists
        '''
        results = {
            'successful': [],
            'failed': []
        }
        
        def upload_one(file_info):
            try:
                result = self.upload_file_with_retry(
                    file_info['parent_id'],
                    file_info['filename'],
                    file_info['content']
                )
                return {'filename': file_info['filename'], 'success': True}
            except Exception as e:
                return {'filename': file_info['filename'], 'success': False, 'error': str(e)}
        
        logger.info(f"Uploading {len(files)} files across multiple folders with {max_workers} workers")
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(upload_one, f): f for f in files}
            
            for future in as_completed(futures):
                result = future.result()
                if result['success']:
                    results['successful'].append(result['filename'])
                else:
                    results['failed'].append({
                        'filename': result['filename'],
                        'error': result['error']
                    })
        
        elapsed = time.time() - start_time
        logger.info(f"Upload complete: {len(results['successful'])} files in {elapsed:.1f}s")
        
        return results
    
    # =========================================================================
    # FILE MANAGEMENT
    # =========================================================================
    
    def move_file(self, file_id: str, new_parent_id: str) -> Dict[str, Any]:
        """
        Move a file to a different folder.
        
        Args:
            file_id: ID of file to move
            new_parent_id: Destination folder ID
            
        Returns:
            Updated file metadata
        """
        try:
            response = requests.patch(
                f"{self.base_url}/items/{file_id}",
                headers=self.headers,
                json={
                    "parentReference": {
                        "id": new_parent_id
                    }
                },
                timeout=30
            )
            response.raise_for_status()
            logger.info(f"Moved file {file_id} to folder {new_parent_id}")
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Failed to move file {file_id}: {e}")
            raise
    
    def download_file(self, file_id: str) -> bytes:
        """
        Download a file from OneDrive.
        
        Args:
            file_id: ID of file to download
            
        Returns:
            File content as bytes
        """
        try:
            response = requests.get(
                f"{self.base_url}/items/{file_id}/content",
                headers={"Authorization": f"Bearer {self.access_token}"},
                timeout=120
            )
            response.raise_for_status()
            logger.info(f"Downloaded file {file_id}")
            return response.content
        except requests.RequestException as e:
            logger.error(f"Failed to download file {file_id}: {e}")
            raise