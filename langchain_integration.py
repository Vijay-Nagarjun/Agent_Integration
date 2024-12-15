import os
import logging
from datetime import datetime
from note_manager import NoteManager
from models import MeetingNote, FolderStructure

logger = logging.getLogger(__name__)

class SliteNoteManager:
    def __init__(self):
        self.api_key = os.getenv('SLITE_API_KEY')
        self.note_manager = NoteManager(self.api_key)

    def process_meeting_notes(self, content: str) -> dict:
        """Process meeting notes and create a note in Slite"""
        try:
            # Extract title from content (assuming markdown format)
            title = "AI Agent Introduction Meeting"
            
            # Create the note
            note = self.note_manager.create_note(title=title, content=content)
            return note
            
        except Exception as e:
            logger.error(f"Error processing meeting notes: {str(e)}")
            raise

    def create_folder_structure(self) -> dict:
        """Create a basic folder structure for organizing notes"""
        try:
            # Create main folder for meetings
            folder = self.note_manager.create_folder(
                name="AI Agent Meetings",
                description="Meeting notes about AI Agent discussions"
            )
            return folder
            
        except Exception as e:
            logger.error(f"Error creating folder structure: {str(e)}")
            raise

    def search_and_update_notes(self, query: str) -> list:
        """Search for notes and update them if needed"""
        try:
            # Search for notes
            results = self.note_manager.search_notes(query)
            return results
            
        except Exception as e:
            logger.error(f"Error searching notes: {str(e)}")
            raise
