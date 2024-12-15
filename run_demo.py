import os
import json
import logging
import time
from dotenv import load_dotenv
from slite_api import SliteAPI
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def read_meeting_notes(file_path: str = "meeting_notes.json") -> dict:
    """Read meeting notes from a JSON file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        logger.error(f"Meeting notes file not found: {file_path}")
        raise
    except json.JSONDecodeError:
        logger.error(f"Invalid JSON format in file: {file_path}")
        raise
    except Exception as e:
        logger.error(f"Error reading meeting notes: {str(e)}")
        raise

def main():
    # Load environment variables
    load_dotenv()
    slite_api_key = os.getenv('SLITE_API_KEY')
    
    if not slite_api_key:
        logger.error("Missing SLITE_API_KEY environment variable")
        return

    try:
        # Initialize Slite API
        slite = SliteAPI(slite_api_key)
        
        # Read meeting notes
        notes_data = read_meeting_notes()
        if not notes_data:
            logger.error("No meeting notes data found")
            return
        
        # Create folder
        folder = slite.create_folder(
            name="Meeting Notes",
            description="Collection of meeting notes and discussions"
        )
        
        folder_id = folder.get("id")
        if not folder_id:
            logger.error("Failed to get folder ID")
            return
            
        # Wait for folder creation
        time.sleep(2)
        
        # Create document title with date
        title = f"{datetime.now().strftime('%Y-%m-%d')} - {notes_data.get('title', 'Untitled Meeting')}"
        
        # Create document in folder
        document = slite.create_document(
            title=title,
            markdown_content=slite.format_meeting_notes_markdown(notes_data),
            folder_id=folder_id
        )
        
        # Print URLs
        if document.get("url"):
            print(f"\nSuccess! View your document at: {document['url']}")
            if folder.get("url"):
                print(f"View all meeting notes at: {folder['url']}")
        else:
            logger.error("Failed to get document URL")

    except Exception as e:
        logger.error(f"Error processing meeting notes: {str(e)}")

if __name__ == "__main__":
    main()
