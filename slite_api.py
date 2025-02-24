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

logger = logging.getLogger(__name__)

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
    """Handle batch operations for API requests"""
    
    def __init__(self, batch_size: int = 10, max_concurrent: int = 5):
        self.batch_size = batch_size
        self.max_concurrent = max_concurrent
        self.queue = asyncio.Queue()
        self.semaphore = asyncio.Semaphore(max_concurrent)
        
    async def add_item(self, item: Dict):
        await self.queue.put(item)
        
    async def process_batch(self, processor_func: Callable) -> List[Dict]:
        """Process items in batches"""
        batch = []
        results = []
        
        while not self.queue.empty():
            try:
                item = self.queue.get_nowait()
                batch.append(item)
                
                if len(batch) >= self.batch_size:
                    async with self.semaphore:
                        batch_results = await processor_func(batch)
                        results.extend(batch_results)
                        batch = []
            except asyncio.QueueEmpty:
                break
        
        if batch:
            async with self.semaphore:
                batch_results = await processor_func(batch)
                results.extend(batch_results)
        
        return results

class SliteAPI:
    """
    Main class for interacting with the Slite API.
    Provides methods for creating, updating, and managing documents and folders.
    """
    
    def __init__(self, api_key: str):
        """Initialize the Slite API client"""
        self.api_key = api_key
        self.base_url = "https://api.slite.com"  # Base URL for Slite API
        self.session = None
        self.events = SliteEventHandler()
        self._workspace_id = None
        
    async def __aenter__(self):
        """Async context manager entry"""
        # Initialize session with auth header
        timeout = aiohttp.ClientTimeout(total=30)  # 30 seconds timeout
        self.session = aiohttp.ClientSession(
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json"
            },
            timeout=timeout
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()

    @backoff.on_exception(backoff.expo, 
                          (aiohttp.ClientError, Exception),
                          max_tries=3,
                          max_time=10)
    async def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict:
        """Make an HTTP request to the Slite API with retry logic"""
        if not self.session:
            raise Exception("Session not initialized. Use async with context manager.")
            
        url = f"{self.base_url}{endpoint}"
        
        try:
            async with self.session.request(method, url, **kwargs) as response:
                if response.status == 404:
                    logger.error(f"Resource not found: {endpoint}")
                    raise Exception(f"Resource not found: {endpoint}")
                elif response.status == 429:
                    logger.error("Rate limit exceeded")
                    raise Exception("Rate limit exceeded")
                elif response.status == 503:
                    logger.error("Service temporarily unavailable. Retrying...")
                    raise Exception("Service temporarily unavailable")
                elif response.status >= 400:
                    error_text = await response.text()
                    logger.error(f"Request failed: Error {response.status}: {error_text}")
                    raise Exception(f"Request failed: {error_text}")
                
                # For DELETE requests that return 204, return empty dict
                if method == "DELETE" and response.status == 204:
                    return {}
                    
                # For all other requests, try to parse JSON
                try:
                    response_json = await response.json()
                    return response_json
                except aiohttp.ContentTypeError:
                    # If no JSON and not a DELETE 204, that's an error
                    if not (method == "DELETE" and response.status == 204):
                        raise
                    return {}
                
        except aiohttp.ClientError as e:
            logger.error(f"Network error in API request: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"API request failed: {str(e)}")
            raise

    async def list_documents(self) -> List[Dict]:
        """List all documents in Slite"""
        try:
            # Use search endpoint with empty query to get all documents
            response = await self._make_request("GET", "/v1/search-notes", params={"type": "note"})
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
            response = await self._make_request("GET", "/v1/search-notes", params={"type": "folder"})
            
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
            response = await self._make_request("POST", "/v1/notes", json=data)
            self.events.trigger_folder_created(response)
            logger.info(f"Successfully created folder: {name}")
            return response
        except Exception as e:
            logger.error(f"Error creating folder: {str(e)}")
            raise

    async def delete_folder(self, folder_id: str) -> Dict:
        """Delete a folder"""
        try:
            response = await self._make_request("DELETE", f"/v1/notes/{folder_id}")
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
            response = await self._make_request("PUT", f"/v1/notes/{folder_id}", json=data)
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
            
            response = await self._make_request("POST", "/v1/notes", json=data)
            
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
            response = await self._make_request("GET", f"/v1/notes/{doc_id}")
            
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
            
            response = await self._make_request("PUT", f"/v1/notes/{doc_id}", json=data)
            
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
                note = await self._make_request("GET", f"/v1/notes/{doc_id}")
                if not note:
                    return {"status": "error", "message": f"Document {doc_id} not found"}
            except Exception as e:
                if "404" in str(e):
                    return {"status": "error", "message": f"Document {doc_id} not found"}
                raise

            # Delete the note
            response = await self._make_request("DELETE", f"/v1/notes/{doc_id}")
            
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
            
            response = await self._make_request("PUT", f"/v1/notes/{doc_id}", json=data)
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
        """Search for notes asynchronously"""
        try:
            logger.info(f"Searching notes with query: {query}")
            response = await self._make_request(
                "GET", 
                "/v1/search-notes",
                params={
                    "query": query,
                    "type": "note",  # Only search for notes
                    "hitsPerPage": 10  # Increase hits to find exact match
                }
            )
            
            # Extract hits from response
            if isinstance(response, dict):
                hits = response.get('hits', [])
            else:
                hits = response if isinstance(response, list) else []
            
            logger.info(f"Found {len(hits)} matching notes")
            return hits
            
        except Exception as e:
            logger.error(f"Error searching notes: {str(e)}")
            raise

    async def create_note_async(self, title: str, content: str, parent_note_id: str = None) -> Dict:
        """Create a note asynchronously"""
        data = {
            "title": title,
            "markdown": content
        }
        if parent_note_id:
            data["parentNoteId"] = parent_note_id
            
        logger.info(f"Creating note '{title}' with content length {len(content)}")
        response = await self._make_request("POST", "/v1/notes", json=data)
        self.events.trigger_document_created(response)
        return response

    async def get_note_async(self, note_id: str) -> Dict:
        """Get a note by ID asynchronously"""
        response = await self._make_request("GET", f"/v1/notes/{note_id}")
        # Extract markdown content from response
        if isinstance(response.get('content'), dict):
            response['markdown'] = response['content'].get('markdown', '')
        return response

    async def update_note_async(self, note_id: str, content: str, append: bool = False) -> Dict:
        """Update a note asynchronously"""
        try:
            original_input = note_id
            logger.info(f"Updating note {note_id}")
            
            # If note_id doesn't look like a Slite ID and doesn't contain special characters,
            # try to find it by title
            if not note_id.startswith('n_') and note_id.replace(' ', '').isalnum():
                logger.info(f"Input looks like a title, searching for note: {note_id}")
                search_results = await self.search_notes_async(note_id)
                if not search_results:
                    raise Exception(f"Could not find note with title: {note_id}")
                
                # Find exact title match
                for note in search_results:
                    if note.get('title', '').lower() == note_id.lower():
                        note_id = note.get('id')
                        logger.info(f"Found exact match with ID: {note_id}")
                        break
                else:
                    # If no exact match, use first result
                    note_id = search_results[0].get('id')
                    logger.info(f"Using best match with ID: {note_id}")
                
                if not note_id:
                    raise Exception(f"Could not find note ID for title: {original_input}")

            # Get existing note content if appending
            existing_content = ""
            if append:
                try:
                    note = await self.get_note_async(note_id)
                    if note and 'content' in note:
                        existing_content = note['content'] + "\n\n"
                except Exception as e:
                    logger.warning(f"Could not get existing content for append: {str(e)}")

            # Prepare the update payload with proper structure
            update_payload = {
                "title": original_input,  # Keep original title
                "markdown": existing_content + content if append else content
            }

            # Make the update request
            response = await self._make_request(
                "PUT",  # Using PUT instead of PATCH
                f"/v1/notes/{note_id}",
                json=update_payload
            )

            if response:
                logger.info(f"Successfully updated note {note_id}")
                return {"status": "success", "data": response}
            else:
                raise Exception(f"Failed to update note {original_input}")

        except Exception as e:
            logger.error(f"Error updating note: {str(e)}")
            return {"status": "error", "message": str(e)}

    async def delete_note_async(self, note_id: str) -> Dict:
        """Delete a note by ID asynchronously"""
        try:
            logger.info(f"Deleting note {note_id}")
            
            # First verify the note exists
            try:
                note = await self._make_request("GET", f"/v1/notes/{note_id}")
                if not note:
                    return {"status": "error", "message": f"Note {note_id} not found"}
            except Exception as e:
                if "404" in str(e):
                    return {"status": "error", "message": f"Note {note_id} not found"}
                raise

            # Delete the note
            response = await self._make_request("DELETE", f"/v1/notes/{note_id}")
            
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
                "/v1/search-notes", 
                params={
                    "q": folder_name,
                    "type": "folder"
                }
            )
            
            # Extract hits from response
            hits = []
            if isinstance(response, dict):
                hits = response.get('hits', [])
            else:
                hits = response if isinstance(response, list) else []
            
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

if __name__ == "__main__":
    # Test the API connection
    async def main():
        slite = SliteAPI("your_api_key")
        async with slite:
            # Add test code here
            pass
            
    asyncio.run(main())
