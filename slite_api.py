"""
Slite API Integration Module

This module provides a comprehensive interface to interact with the Slite API,
allowing for creation, updating, and management of documents and folders.
It includes event handling capabilities for various Slite operations.
"""

import aiohttp
import asyncio
import logging
from typing import Dict, Optional, List, Callable
from datetime import datetime
import json
from functools import lru_cache
from concurrent.futures import ThreadPoolExecutor
import backoff
import socket
import time
import random
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)

class AuthenticationError(Exception):
    """Custom exception for authentication related errors"""
    pass

class SliteEventHandler:
    """
    Event handler for Slite operations.
    Manages callbacks for folder and document creation/update events.
    """
    
    def __init__(self):
        """Initialize lists to store event handlers for different operations"""
        self.folder_created_handlers: List[Callable] = []
        self.folder_updated_handlers: List[Callable] = []
        self.document_created_handlers: List[Callable] = []
        self.document_updated_handlers: List[Callable] = []
        
    def on_folder_created(self, handler: Callable):
        """Register a callback for folder creation events"""
        self.folder_created_handlers.append(handler)
        
    def on_folder_updated(self, handler: Callable):
        """Register a callback for folder update events"""
        self.folder_updated_handlers.append(handler)
        
    def on_document_created(self, handler: Callable):
        """Register a callback for document creation events"""
        self.document_created_handlers.append(handler)
        
    def on_document_updated(self, handler: Callable):
        """Register a callback for document update events"""
        self.document_updated_handlers.append(handler)
        
    def trigger_folder_created(self, folder_data: Dict):
        """
        Trigger all registered folder creation event handlers
        Args:
            folder_data: Dictionary containing folder information
        """
        for handler in self.folder_created_handlers:
            try:
                handler(folder_data)
            except Exception as e:
                logger.error(f"Error in folder created handler: {str(e)}")

    def trigger_folder_updated(self, folder_data: Dict):
        """
        Trigger all registered folder update event handlers
        Args:
            folder_data: Dictionary containing folder information
        """
        for handler in self.folder_updated_handlers:
            try:
                handler(folder_data)
            except Exception as e:
                logger.error(f"Error in folder updated handler: {str(e)}")

    def trigger_document_created(self, doc_data: Dict):
        """
        Trigger all registered document creation event handlers
        Args:
            doc_data: Dictionary containing document information
        """
        for handler in self.document_created_handlers:
            try:
                handler(doc_data)
            except Exception as e:
                logger.error(f"Error in document created handler: {str(e)}")

    def trigger_document_updated(self, doc_data: Dict):
        """
        Trigger all registered document update event handlers
        Args:
            doc_data: Dictionary containing document information
        """
        for handler in self.document_updated_handlers:
            try:
                handler(doc_data)
            except Exception as e:
                logger.error(f"Error in document updated handler: {str(e)}")

class BatchProcessor:
    """Handle batch operations with dynamic sizing"""
    
    def __init__(self):
        self.min_batch_size = 1
        self.max_batch_size = 20
        self.current_batch_size = 5  # Start conservative
        self.success_count = 0
        self.error_count = 0
        
    async def adjust_batch_size(self, success: bool):
        """Dynamically adjust batch size based on success/failure"""
        if success:
            self.success_count += 1
            self.error_count = max(0, self.error_count - 1)
            if self.success_count >= 3:
                self.current_batch_size = min(
                    self.max_batch_size,
                    self.current_batch_size + 2
                )
                self.success_count = 0
        else:
            self.error_count += 1
            self.success_count = 0
            if self.error_count >= 2:
                self.current_batch_size = max(
                    self.min_batch_size,
                    self.current_batch_size - 2
                )
                self.error_count = 0

class SliteAPI:
    """
    Main class for interacting with the Slite API.
    Provides methods for creating, updating, and managing documents and folders.
    """
    
    def __init__(self, api_key: str):
        """Initialize the Slite API client"""
        self.api_key = api_key.strip().replace('"', '').replace("'", '')
        self.base_url = "https://api.slite.com/v1"
        self._headers = {  # Changed from self.headers to self._headers to match usage
            "x-slite-api-key": self.api_key,
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        self.session = None
        self.events = SliteEventHandler()
        self._workspace_id = None
        self._session_active = False
        self._force_cleanup = False
        self.batch_processor = BatchProcessor()
        self._concurrent_requests = 0
        self._max_concurrent = 3  # Start conservative
        self._last_request_time = 0
        self._min_request_interval = 1.0  # Minimum time between requests in seconds

    async def _acquire_request_slot(self):
        """Wait for available request slot"""
        while self._concurrent_requests >= self._max_concurrent:
            await asyncio.sleep(0.1)
        self._concurrent_requests += 1

    async def _release_request_slot(self):
        """Release request slot"""
        self._concurrent_requests = max(0, self._concurrent_requests - 1)

    async def _release_session(self):
        """Release but don't close the session"""
        if self._session_active:
            # Just mark the session as not in use
            self._session_in_use = False
            logger.debug("Session marked as released")
    
    async def ensure_session(self):
        """Ensure a valid session exists, creating one if needed"""
        if not self._session_active or not self.session or self.session.closed:
            timeout = aiohttp.ClientTimeout(total=30)
            self.session = aiohttp.ClientSession(
                headers=self._headers,  # Now this will work correctly
                timeout=timeout
            )
            self._session_active = True
            self._session_in_use = True
            logger.info("Created new API session with headers")
            logger.debug(f"Using API key: {self.api_key[:10]}...")  # Log first 10 chars of API key

    async def __aenter__(self):
        """Async context manager entry"""
        await self.ensure_session()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self._force_cleanup:
            await self.close(force=True)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    async def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict:
        """Make API request with rate limiting and exponential backoff"""
        await self._acquire_request_slot()
        # Implement rate limiting
        current_time = time.time()
        time_since_last_request = current_time - self._last_request_time
        if time_since_last_request < self._min_request_interval:
            await asyncio.sleep(self._min_request_interval - time_since_last_request)
        
        try:
            # Add random jitter to prevent thundering herd
            await asyncio.sleep(random.uniform(0.1, 0.5))
            
            # Make the request
            async with self.session.request(
                method, 
                f"{self.base_url}{endpoint}",
                **kwargs
            ) as response:
                self._last_request_time = time.time()
                
                if response.status == 429:  # Rate limit hit
                    retry_after = int(response.headers.get('Retry-After', 60))
                    logger.warning(f"Rate limit hit, waiting {retry_after} seconds")
                    await asyncio.sleep(retry_after)
                    raise Exception("Rate limit exceeded - retrying")
                    
                if response.status == 204:  # No content
                    return {}
                elif response.status == 401:
                    raise AuthenticationError("Invalid API key")
                elif response.status == 402:
                    raise Exception("Feature disabled for your organization")
                elif response.status == 404:
                    raise Exception("Resource not found")
                elif response.status == 422:
                    raise Exception("Input validation error")
                elif response.status == 429:
                    raise Exception("Rate limit exceeded")
                elif response.status >= 400:
                    text = await response.text()
                    raise Exception(f"API error: {text}")
                
                return await response.json()
        except Exception as e:
            logger.error(f"Request failed: {str(e)}")
            raise
        finally:
            await self._release_request_slot()

    async def close(self, force: bool = False):
        """Explicitly close the session"""
        if (force or self._force_cleanup) and self.session and not self.session.closed:
            await self.session.close()
            self._session_active = False
            logger.info("API session closed")

    async def list_documents(self) -> List[Dict]:
        """List all documents in Slite"""
        try:
            # Use search endpoint with empty query to get all documents
            response = await self._make_request("GET", "/search-notes", params={"type": "note"})
            documents = []
            if isinstance(response, dict):
                documents = response.get('hits', [])
            else:
                documents = response if isinstance(response, list) else []
            
            logger.info(f"Retrieved {len(documents)} documents")
            return documents
            
        except Exception as e:
            logger.error(f"Error listing documents: {str(e)}")
            raise

    async def list_folders(self) -> List[Dict]:
        """List all available folders"""
        try:
            # Get all folders using search
            response = await self._make_request("GET", "/search-notes", params={"type": "folder"})
            
            # Extract folders from the response
            folders = []
            if isinstance(response, dict):
                folders = response.get('hits', [])
            else:
                folders = response if isinstance(response, list) else []
            
            logger.info(f"Retrieved {len(folders)} folders")
            return folders
            
        except Exception as e:
            logger.error(f"Error listing folders: {str(e)}")
            raise

    async def create_folder(self, name: str, description: str = "") -> Dict:
        """Create a new folder"""
        try:
            logger.info(f"Creating folder '{name}'")
            data = {
                "title": name,
                "description": description,
                "type": "folder"
            }
            response = await self._make_request("POST", "/notes", json=data)
            self.events.trigger_folder_created(response)
            logger.info(f"Successfully created folder: {name}")
            return response
        except Exception as e:
            logger.error(f"Error creating folder: {str(e)}")
            raise

    async def delete_folder(self, folder_id: str) -> Dict:
        """Delete a folder"""
        try:
            response = await self._make_request("DELETE", f"/notes/{folder_id}")
            logger.info(f"Successfully deleted folder {folder_id}")
            return response
            
        except Exception as e:
            logger.error(f"Error deleting folder: {str(e)}")
            raise

    async def rename_folder(self, folder_id: str, new_name: str) -> Dict:
        """Rename a folder"""
        try:
            logger.info(f"Renaming folder {folder_id} to {new_name}")
            data = {
                "title": new_name
            }
            response = await self._make_request("PUT", f"/notes/{folder_id}", json=data)
            self.events.trigger_folder_updated(response)
            logger.info(f"Successfully renamed folder to: {new_name}")
            return response
        except Exception as e:
            logger.error(f"Error renaming folder: {str(e)}")
            raise

    async def create_document(self, title: str, content: str, parent_note_id: str = None) -> Dict:
        """Create a new document with optional parent note ID"""
        try:
            data = {
                "title": title,
                "markdown": content
            }
            
            if parent_note_id:
                data["parentNoteId"] = parent_note_id
            
            logger.info(f"Creating document '{title}' with content length {len(content)}")
            if parent_note_id:
                logger.info(f"Document will be created under parent {parent_note_id}")
            
            response = await self._make_request("POST", "/notes", json=data)
            
            if not response:
                raise Exception("No response received from create request")
            
            logger.info(f"Successfully created document {response.get('id', 'Unknown ID')}")
            
            # Trigger event handlers
            self.events.trigger_document_created(response)
            
            return response
            
        except Exception as e:
            logger.error(f"Error creating document: {str(e)}")
            raise

    async def get_document(self, doc_id: str) -> Dict:
        """Get a document by ID"""
        try:
            response = await self._make_request("GET", f"/notes/{doc_id}")
            
            content = response.get('content', '')
            if isinstance(content, dict):
                content = content.get('markdown', '')
            elif isinstance(content, str):
                content = content
            else:
                content = ''
                
            logger.info(f"Retrieved document content (first 100 chars): {content[:100]}")
            logger.info(f"Content length: {len(content)} characters")
            
            return response
            
        except Exception as e:
            logger.error(f"Error getting document: {str(e)}")
            raise

    async def update_document(self, doc_id: str, content: str, title: str = None) -> Dict:
        """Update a document's content and optionally its title"""
        try:
            data = {
                "markdown": content
            }
            
            if title:
                data["title"] = title
            
            response = await self._make_request("PUT", f"/notes/{doc_id}", json=data)
            
            if not response:
                raise Exception("No response received from update request")
            
            logger.info(f"Successfully updated document {doc_id}")
            return response
            
        except Exception as e:
            logger.error(f"Error updating document: {str(e)}")
            raise

    async def delete_document(self, doc_id: str) -> Dict:
        """Delete a document"""
        try:
            logger.info(f"Deleting document {doc_id}")
            
            # First verify the note exists
            try:
                note = await self._make_request("GET", f"/notes/{doc_id}")
                if not note:
                    return {"status": "error", "message": f"Document {doc_id} not found"}
            except Exception as e:
                if "404" in str(e):
                    return {"status": "error", "message": f"Document {doc_id} not found"}
                raise

            # Delete the note
            response = await self._make_request("DELETE", f"/notes/{doc_id}")
            
            # For successful deletion (204 No Content)
            if response is None or not response:
                logger.info(f"Document {doc_id} deleted successfully")
                return {"status": "success", "message": f"Document {doc_id} deleted successfully"}
            
            return response
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Error deleting document: {error_msg}")
            if "404" in error_msg:
                return {"status": "error", "message": f"Document {doc_id} not found"}
            raise Exception(f"Failed to delete document: {error_msg}")

    async def rename_document(self, doc_id: str, new_title: str) -> Dict:
        """Rename a document"""
        try:
            logger.info(f"Renaming document {doc_id} to {new_title}")
            
            # Get current document to preserve content
            current_doc = await self.get_note_async(doc_id)
            if not current_doc:
                raise Exception(f"Document {doc_id} not found")
            
            data = {
                "title": new_title,
                "markdown": current_doc.get('markdown', '')  # Preserve existing content
            }
            
            response = await self._make_request("PUT", f"/notes/{doc_id}", json=data)
            self.events.trigger_document_updated(response)
            logger.info(f"Successfully renamed document to: {new_title}")
            return response
        except Exception as e:
            logger.error(f"Error renaming document: {str(e)}")
            raise

    async def format_meeting_notes_markdown(self, note_data: Dict) -> str:
        """
        Format meeting notes data into markdown content
        
        Args:
            note_data: Dictionary containing note data with title, metadata, and content
            
        Returns:
            str: Formatted markdown content
        """
        try:
            markdown_lines = []
            
            # Add title
            markdown_lines.append("# Meeting Notes")
            markdown_lines.append("")
            
            # Add metadata section
            metadata = note_data.get('metadata', {})
            if metadata:
                markdown_lines.append("## 📅 Meeting Details")
                markdown_lines.append("")
                markdown_lines.append(f"**Date:** {metadata.get('date', 'N/A')}")
                markdown_lines.append(f"**Time:** {metadata.get('time', 'N/A')}")
                markdown_lines.append(f"**Location:** {metadata.get('location', 'N/A')}")
                if 'attendees' in metadata:
                    markdown_lines.append("**Attendees:**")
                    for attendee in metadata['attendees']:
                        markdown_lines.append(f"- {attendee}")
                markdown_lines.append(f"**Next Meeting:** {metadata.get('next_meeting', 'N/A')}")
                markdown_lines.append("")
            
            # Add sections
            sections = note_data.get('sections', [])
            for section in sections:
                title = section.get('title', '')
                points = section.get('points', [])
                
                markdown_lines.append(f"## 📝 {title}")
                markdown_lines.append("")
                
                for point in points:
                    if isinstance(point, str):
                        markdown_lines.append(f"- {point}")
                    elif isinstance(point, dict):
                        header = point.get('header', '')
                        sub_points = point.get('sub_points', [])
                        
                        # Add header with proper formatting
                        markdown_lines.append(f"### {header}")
                        
                        # Add sub-points if any
                        for sub_point in sub_points:
                            markdown_lines.append(f"- {sub_point}")
                        
                        markdown_lines.append("")
                
                markdown_lines.append("")  # Add extra line between sections
            
            return "\n".join(markdown_lines)
            
        except Exception as e:
            logger.error(f"Error formatting meeting notes: {str(e)}")
            raise

    async def search_notes_async(self, query: str) -> List[Dict]:
        """Search notes - Updated per API docs"""
        try:
            params = {
                "query": query,
                "hitsPerPage": 20,
                "page": 0,
                "highlightPreTag": "<mark>",  # Optional highlighting
                "highlightPostTag": "</mark>"
            }
            response = await self._make_request("GET", "/search-notes", params=params)
            return response.get('hits', [])
        except Exception as e:
            logger.error(f"Error searching notes: {str(e)}")
            raise

    async def create_note_async(self, title: str, content: str, parent_note_id: str = None) -> Dict:
        """Create a note asynchronously - Updated per API docs"""
        try:
            data = {
                "title": title,
                "parentNoteId": parent_note_id if parent_note_id else None,
                "templateId": None,  # Optional per docs
                "markdown": content,
                "attributes": []  # Required per docs
            }

            logger.info(f"Creating note '{title}' with content length {len(content)}")
            return await self._make_request("POST", "/notes", json=data)
        except Exception as e:
            logger.error(f"Error creating note: {str(e)}")
            raise

    async def get_note_async(self, note_id: str) -> Dict:
        """Get a note by ID asynchronously"""
        response = await self._make_request("GET", f"/notes/{note_id}")
        # Extract markdown content from response
        if isinstance(response.get('content'), dict):
            response['markdown'] = response['content'].get('markdown', '')
        return response

    async def update_note_async(self, note_id: str, content: str, append: bool = False) -> Dict:
        """
        Update a note asynchronously with the new content
        
        Args:
            note_id (str): ID of the note to update
            content (str): New content for the note
            append (bool): Whether to append content (not part of official API)
            
        Returns:
            Dict: Response data
        """
        try:
            logger.info(f"Updating note {note_id}")

            # Get existing note if appending
            if append:
                existing_note = await self.get_note_async(note_id)
                if existing_note and existing_note.get('markdown'):
                    content = f"{existing_note['markdown']}\n\n{content}"

            # Format according to API docs
            update_payload = {
                "markdown": content,
                "attributes": []  # Required by API
            }

            logger.info(f"Updating note {note_id}")
            response = await self._make_request(
                "PUT",
                f"/notes/{note_id}",
                json=update_payload
            )

            if response:
                return {"status": "success", "data": response}
            raise Exception("No response received from update request")

        except Exception as e:
            logger.error(f"Error updating note: {str(e)}")
            return {"status": "error", "message": str(e)}

    async def delete_note_async(self, note_id: str) -> Dict:
        """Delete a note by ID asynchronously"""
        try:
            logger.info(f"Deleting note {note_id}")
            
            # First verify the note exists
            try:
                note = await self._make_request("GET", f"/notes/{note_id}")
                if not note:
                    return {"status": "error", "message": f"Note {note_id} not found"}
            except Exception as e:
                if "404" in str(e):
                    return {"status": "error", "message": f"Note {note_id} not found"}
                raise

            # Delete the note
            response = await self._make_request("DELETE", f"/notes/{note_id}")
            
            # For successful deletion (204 No Content)
            if response is None or not response:
                logger.info(f"Note {note_id} deleted successfully")
                return {"status": "success", "message": f"Note {note_id} deleted successfully"}
            
            return response
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Error deleting note: {error_msg}")
            if "404" in error_msg:
                return {"status": "error", "message": f"Note {note_id} not found"}
            raise Exception(f"Failed to delete note: {error_msg}")

    async def search_folder_by_name(self, folder_name: str) -> Optional[Dict]:
        """Search for a folder by name"""
        try:
            logger.info(f"Searching for folder: {folder_name}")
            response = await self._make_request(
                "GET", 
                "/search-notes",
                params={
                    "query": folder_name,
                    "type": "folder",  # Specify folder type in search
                    "hitsPerPage": 10
                }
            )
            
            # Extract hits from response
            hits = response.get('hits', []) if isinstance(response, dict) else []
            
            # Look for exact match
            for hit in hits:
                if hit.get('title', '').lower() == folder_name.lower():
                    logger.info(f"Found folder: {folder_name}")
                    return hit
            
            logger.info(f"No folder found with name: {folder_name}")
            return None
            
        except Exception as e:
            logger.error(f"Error searching for folder: {str(e)}")
            raise

    async def ask_question(self, question: str, parent_note_id: Optional[str] = None) -> Dict:
        """Ask a question using Slite's ask endpoint"""
        params = {"question": question}
        if parent_note_id:
            params["parentNoteId"] = parent_note_id
        return await self._make_request("GET", "/ask", params=params)

    async def index_custom_content(self, data: Dict) -> Dict:
        """Index custom content for AskX usage"""
        return await self._make_request("POST", "/ask/index", json=data)

    async def delete_custom_content(self, root_id: str, content_id: str) -> Dict:
        """Delete custom content from AskX"""
        data = {
            "rootId": root_id,
            "id": content_id
        }
        return await self._make_request("DELETE", "/ask/index", json=data)

    async def list_custom_content(self, root_id: str, page: int = 0, hits_per_page: int = 20) -> Dict:
        """List custom content ids"""
        params = {
            "rootId": root_id,
            "page": page,
            "hitsPerPage": min(hits_per_page, 100)
        }
        return await self._make_request("GET", "/ask/index", params=params)

    async def update_tile(self, note_id: str, tile_id: str, data: Dict) -> Dict:
        """Update a tile in a note"""
        return await self._make_request(
            "PUT", 
            f"/notes/{note_id}/tiles/{tile_id}",
            json=data
        )

    async def get_note_children(self, note_id: str, cursor: Optional[str] = None) -> Dict:
        """Get children of a note"""
        params = {"cursor": cursor} if cursor else {}
        return await self._make_request("GET", f"/notes/{note_id}/children", params=params)

if __name__ == "__main__":
    # Test the API connection
    async def main():
        slite = SliteAPI("your_api_key")
        async with slite:
            # Add test code here
            pass
            
    asyncio.run(main())