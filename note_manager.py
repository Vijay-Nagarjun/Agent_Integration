import logging
from typing import Dict, Optional, List
from slite_api import SliteAPI
from models import MeetingNote, FolderStructure

logger = logging.getLogger(__name__)

class NoteManager:
    def __init__(self, api_key: str):
        self.api = SliteAPI(api_key)
        
    def _extract_title(self, content: str) -> str:
        """Extract title from content"""
        lines = content.split('\n')
        for line in lines:
            line = line.strip()
            if line.startswith('Meeting Notes:'):
                return line[len('Meeting Notes:'):].strip()
        return "Untitled Meeting"
    
    def create_note(self, title: str, content: str) -> Dict:
        """Create a new note"""
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
        """Create a new folder"""
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
        """Update an existing note"""
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
        """Search for notes"""
        try:
            response = self.api.search_notes(query)
            return response
            
        except Exception as e:
            logger.error(f"Error searching notes: {str(e)}")
            raise
    
    def delete_note(self, note_id: str) -> Dict:
        """Delete a note"""
        try:
            response = self.api.delete_note(note_id)
            return response
            
        except Exception as e:
            logger.error(f"Error deleting note: {str(e)}")
            raise
