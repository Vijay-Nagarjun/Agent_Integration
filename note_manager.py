"""
Note Manager Module

This module provides a high-level interface for managing notes and folders in Slite.
It handles the creation, updating, searching, and deletion of notes and folders
while providing proper error handling and logging.
"""

import logging
from typing import Dict, Optional, List
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
        """
        Initialize the note manager with API credentials.
        
        Args:
            api_key (str): Slite API authentication key
        """
        self.api = SliteAPI(api_key)
        
    def _extract_title(self, content: str) -> str:
        """
        Extract title from note content.
        
        Args:
            content (str): The full content of the note
            
        Returns:
            str: Extracted title or "Untitled Meeting" if no title found
        """
        lines = content.split('\n')
        for line in lines:
            line = line.strip()
            if line.startswith('Meeting Notes:'):
                return line[len('Meeting Notes:'):].strip()
        return "Untitled Meeting"
    
    def create_note(self, title: str, content: str) -> Dict:
        """
        Create a new note in Slite.
        
        Args:
            title (str): Title of the note
            content (str): Main content of the note
            
        Returns:
            Dict: API response containing the created note details
            
        Raises:
            Exception: If note creation fails
        """
        try:
            logger.info(f"Creating note with title: {title}")
            
            # Create note model
            note = MeetingNote(
                title=title,
                content=content
            )
            
            # Create note in Slite
            response = self.api.create_note(note)
            
            return response
            
        except Exception as e:
            logger.error(f"Error creating note: {str(e)}")
            raise
    
    def create_folder(self, name: str, description: Optional[str] = None) -> Dict:
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
            
            response = self.api.create_folder(folder)
            
            return response
            
        except Exception as e:
            logger.error(f"Error creating folder: {str(e)}")
            raise
    
    def update_note(self, note_id: str, title: Optional[str] = None, content: Optional[str] = None) -> Dict:
        """
        Update an existing note in Slite.
        
        Args:
            note_id (str): ID of the note to update
            title (Optional[str]): New title for the note
            content (Optional[str]): New content for the note
            
        Returns:
            Dict: API response containing the updated note details
            
        Raises:
            Exception: If note update fails
        """
        try:
            # Create note model with only the fields to update
            note = MeetingNote(
                title=title if title else "",
                content=content if content else ""
            )
            
            response = self.api.update_note(note_id, note)
            
            return response
            
        except Exception as e:
            logger.error(f"Error updating note: {str(e)}")
            raise
    
    def search_notes(self, query: str) -> List[Dict]:
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
            response = self.api.search_notes(query)
            return response
            
        except Exception as e:
            logger.error(f"Error searching notes: {str(e)}")
            raise
    
    def delete_note(self, note_id: str) -> Dict:
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
            response = self.api.delete_note(note_id)
            return response
            
        except Exception as e:
            logger.error(f"Error deleting note: {str(e)}")
            raise
