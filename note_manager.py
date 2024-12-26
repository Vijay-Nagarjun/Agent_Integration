"""
Note Manager Module

This module provides a high-level interface for managing notes and folders in Slite.
It handles the creation, updating, searching, and deletion of notes and folders
while providing proper error handling and logging.
"""

import logging
from typing import Dict, Optional, List
import asyncio
import re
from functools import lru_cache
from slite_api import SliteAPI
from models import MeetingNote, FolderStructure

logger = logging.getLogger(__name__)

class NoteManager:
    """
    High-level manager class for handling note and folder operations.
    
    This class provides a simplified interface to the Slite API,
    handling common operations like creating notes and folders,
    updating content, and managing metadata.
    """
    
    def __init__(self, api_key: str):
        """Initialize with optimized caching and async support"""
        self.api = SliteAPI(api_key)
        self._title_pattern = re.compile(r'Meeting Notes:\s*(.*)')
        self._note_cache = {}
        
    @lru_cache(maxsize=100)
    def _extract_title(self, content: str) -> str:
        """
        Extract title from note content using regex for better performance.
        
        Args:
            content (str): The full content of the note
            
        Returns:
            str: Extracted title or "Untitled Meeting" if no title found
        """
        match = self._title_pattern.search(content)
        return match.group(1) if match else "Untitled Meeting"
    
    async def create_note(self, title: str, content: str) -> Dict:
        """
        Create a new note asynchronously.
        
        Args:
            title (str): Title of the note
            content (str): Main content of the note
            
        Returns:
            Dict: API response containing the created note details
        """
        try:
            logger.info(f"Creating note with title: {title}")
            
            # Create note model
            note = MeetingNote(
                title=title,
                content=content
            )
            
            # Create note and cache it
            response = await self.api.create_note_async(note)
            self._note_cache[response['id']] = response
            
            return response
            
        except Exception as e:
            logger.error(f"Error creating note: {str(e)}")
            raise
    
    async def get_note(self, note_id: str) -> Dict:
        """
        Get a note with caching.
        
        Args:
            note_id (str): ID of the note to retrieve
            
        Returns:
            Dict: Note data
        """
        if note_id in self._note_cache:
            return self._note_cache[note_id]
            
        response = await self.api.get_note_async(note_id)
        self._note_cache[note_id] = response
        return response
    
    async def update_note(self, note_id: str, title: str, content: str) -> Dict:
        """
        Update a note asynchronously.
        
        Args:
            note_id (str): ID of the note to update
            title (str): New title
            content (str): New content
            
        Returns:
            Dict: Updated note data
        """
        try:
            response = await self.api.update_note_async(note_id, title, content)
            self._note_cache[note_id] = response
            return response
        except Exception as e:
            logger.error(f"Error updating note: {str(e)}")
            raise
    
    async def create_folder(self, name: str, description: Optional[str] = None) -> Dict:
        """
        Create a new folder in Slite.
        
        Args:
            name (str): Name of the folder
            description (Optional[str]): Optional description of the folder
            
        Returns:
            Dict: API response containing the created folder details
            
        Raises:
            Exception: If folder creation fails
        """
        try:
            folder = FolderStructure(
                name=name,
                description=description
            )
            
            response = await self.api.create_folder_async(folder)
            
            return response
            
        except Exception as e:
            logger.error(f"Error creating folder: {str(e)}")
            raise
    
    async def search_notes(self, query: str) -> List[Dict]:
        """
        Search for notes in Slite.
        
        Args:
            query (str): Search query string
            
        Returns:
            List[Dict]: List of notes matching the search query
            
        Raises:
            Exception: If search operation fails
        """
        try:
            response = await self.api.search_notes_async(query)
            return response
            
        except Exception as e:
            logger.error(f"Error searching notes: {str(e)}")
            raise
    
    async def delete_note(self, note_id: str) -> Dict:
        """
        Delete a note from Slite.
        
        Args:
            note_id (str): ID of the note to delete
            
        Returns:
            Dict: API response confirming deletion
            
        Raises:
            Exception: If note deletion fails
        """
        try:
            response = await self.api.delete_note_async(note_id)
            del self._note_cache[note_id]
            return response
            
        except Exception as e:
            logger.error(f"Error deleting note: {str(e)}")
            raise
