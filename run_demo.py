import os
import json
import logging
import time
from dotenv import load_dotenv
from slite_api import SliteAPI
from datetime import datetime, timedelta
import sys
import threading

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def read_meeting_notes():
    """Read meeting notes from JSON file"""
    try:
        with open('meeting_notes.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        logger.error("meeting_notes.json file not found")
        raise
    except json.JSONDecodeError as e:
        logger.error(f"Error reading meeting notes: {str(e)}")
        raise

def prompt_for_deletion(folder_id: str, folder_name: str, doc_id: str, doc_name: str, slite: SliteAPI):
    """Prompt user for deletion after timer expires"""
    print("\n" + "="*50)
    logger.info("Time to decide about deletion!")
    logger.info("Do you want to delete the following items?")
    logger.info(f"1. Folder: {folder_name}")
    logger.info(f"2. Document: {doc_name}")
    print("="*50)
    
    while True:
        response = input("\nEnter 'y' for Yes or 'n' for No: ").lower()
        if response == 'y':
            try:
                # Delete the folder (this will also delete the document inside it)
                delete_result = slite.delete_folder(folder_id)
                logger.info(delete_result['message'])
                break
            except Exception as e:
                logger.error(f"Error deleting items: {str(e)}")
                break
        elif response == 'n':
            logger.info("Items will be kept.")
            break
        else:
            logger.info("Invalid input. Please enter 'y' or 'n'")

class DeletionTimer:
    def __init__(self, folder_id: str, folder_name: str, doc_id: str, doc_name: str, slite: SliteAPI):
        self.folder_id = folder_id
        self.folder_name = folder_name
        self.doc_id = doc_id
        self.doc_name = doc_name
        self.slite = slite
        self.timer = None
        self.event = threading.Event()

    def start(self):
        """Start the deletion timer"""
        self.timer = threading.Timer(
            30,  # 5 minutes in seconds
            self._timer_callback
        )
        self.timer.start()
        logger.info("\nWaiting 5 minutes before prompting for deletion...")
        logger.info("You can continue using the application. A prompt will appear when it's time to decide about deletion.")

    def _timer_callback(self):
        """Timer callback to prompt for deletion"""
        prompt_for_deletion(
            self.folder_id,
            self.folder_name,
            self.doc_id,
            self.doc_name,
            self.slite
        )
        self.event.set()

    def wait(self):
        """Wait for the deletion decision"""
        self.event.wait()

def demo_folder_operations(slite: SliteAPI):
    """Demonstrate folder operations"""
    try:
        # Create a folder
        folder = slite.create_folder(
            name="Meeting Notes",
            description="Collection of meeting notes and discussions"
        )
        logger.info(f"Created folder: {folder['name']}")

        # Update the folder
        updated_folder = slite.update_folder(
            folder_id=folder['id'],
            name="Team Meeting Notes",
            description="Collection of team meeting notes and discussions"
        )
        logger.info(f"Updated folder name to: {updated_folder['name']}")

        # Create a document in the folder
        notes_data = read_meeting_notes()
        
        # Format the current date for the document title
        current_date = datetime.now().strftime('%Y-%m-%d')
        doc_title = f"{current_date} - {notes_data.get('title', 'Untitled Meeting')}"
        
        markdown_content = slite.format_meeting_notes_markdown(notes_data)
        doc = slite.create_document(
            title=doc_title,
            markdown_content=markdown_content,
            folder_id=folder['id']
        )
        logger.info(f"Created document: {doc['title']}")

        # Update the document
        updated_doc = slite.update_document(
            doc_id=doc['id'],
            title=f"{doc_title} (Updated)",
            markdown_content=markdown_content,
            folder_id=folder['id']
        )
        logger.info(f"Updated document title to: {updated_doc['title']}")

        # Print the URLs for reference
        if doc.get('url'):
            logger.info(f"Document URL: {doc['url']}")
        if folder.get('url'):
            logger.info(f"Folder URL: {folder['url']}")

        # Set up and start the deletion timer
        deletion_timer = DeletionTimer(
            folder['id'],
            folder['name'],
            doc['id'],
            doc['title'],
            slite
        )
        deletion_timer.start()
        
        # Wait for the deletion decision
        deletion_timer.wait()

    except Exception as e:
        logger.error(f"Error in folder operations: {str(e)}")
        raise

if __name__ == "__main__":
    load_dotenv()
    api_key = os.getenv("SLITE_API_KEY")
    
    if not api_key:
        logger.error("SLITE_API_KEY not found in environment variables")
        sys.exit(1)
    
    slite = SliteAPI(api_key)
    demo_folder_operations(slite)
