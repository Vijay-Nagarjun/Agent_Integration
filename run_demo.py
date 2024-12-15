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

def on_folder_created(folder_data: dict):
    """Handler for folder creation events"""
    logger.info(f"Folder created event: {folder_data['name']}")
    logger.info(f"Created by: {folder_data['metadata']['updated_by']}")
    logger.info(f"Created at: {folder_data['metadata']['last_updated']}")

def on_folder_updated(folder_data: dict):
    """Handler for folder update events"""
    logger.info(f"Folder updated event: {folder_data['name']}")
    logger.info(f"Updated by: {folder_data['metadata']['updated_by']}")
    logger.info(f"Updated at: {folder_data['metadata']['last_updated']}")

def on_document_created(doc_data: dict):
    """Handler for document creation events"""
    logger.info(f"Document created event: {doc_data['title']}")
    logger.info(f"Created by: {doc_data['metadata']['updated_by']}")
    logger.info(f"Created at: {doc_data['metadata']['last_updated']}")

def on_document_updated(doc_data: dict):
    """Handler for document update events"""
    logger.info(f"Document updated event: {doc_data['title']}")
    logger.info(f"Updated by: {doc_data['metadata']['updated_by']}")
    logger.info(f"Updated at: {doc_data['metadata']['last_updated']}")

def display_menu():
    """Display the main menu options"""
    print("\n=== Slite Document Management Menu ===")
    print("1. Create a new document")
    print("2. Update existing document")
    print("3. Rename document")
    print("4. Delete document")
    print("5. Create new folder")
    print("6. Rename folder")
    print("7. Delete folder")
    print("8. Exit")
    print("=====================================")

def display_item_details(item: dict, item_type: str = "item"):
    """Display details of a document or folder including its ID"""
    print("\n=== Item Details ===")
    print(f"Type: {item_type}")
    print(f"ID: {item.get('id')}")
    print(f"Name: {item.get('name') or item.get('title')}")
    if 'url' in item:
        print(f"URL: {item['url']}")
    print("==================")

def handle_menu_choice(choice: str, slite: SliteAPI, current_folder_id: str = None):
    """Handle the user's menu choice"""
    try:
        if choice == "1":
            folder_id = input("Enter folder ID (press Enter to use current folder): ").strip() or current_folder_id
            title = input("Enter document title: ").strip()
            content = input("Enter document content (markdown supported): ").strip()
            doc = slite.create_document(title=title, markdown_content=content, folder_id=folder_id)
            logger.info(f"Created document: {doc['title']}")
            display_item_details(doc, "document")
            
        elif choice == "2":
            doc_id = input("Enter document ID to update: ").strip()
            current_doc = slite.get_note(doc_id)
            if current_doc:
                print(f"\nCurrent title: {current_doc.get('title')}")
                new_title = input("Enter new title (press Enter to keep current): ").strip()
                print("\nEnter new content (markdown supported, press Enter when done):")
                new_content = input().strip()
                
                doc = slite.update_document(
                    doc_id=doc_id,
                    title=new_title or current_doc.get('title'),
                    markdown_content=new_content
                )
                logger.info(f"Updated document: {doc['title']}")
                display_item_details(doc, "document")
            
        elif choice == "3":
            doc_id = input("Enter document ID to rename: ").strip()
            current_doc = slite.get_note(doc_id)
            if current_doc:
                print(f"\nCurrent title: {current_doc.get('title')}")
                new_title = input("Enter new title: ").strip()
                doc = slite.update_document(
                    doc_id=doc_id,
                    title=new_title,
                    markdown_content=current_doc.get('markdown', '')
                )
                logger.info(f"Renamed document to: {doc['title']}")
                display_item_details(doc, "document")
            
        elif choice == "4":
            doc_id = input("Enter document ID to delete: ").strip()
            confirm = input("Are you sure you want to delete this document? (y/n): ").lower()
            if confirm == 'y':
                result = slite.delete_document(doc_id)
                logger.info(result['message'])
            
        elif choice == "5":
            name = input("Enter folder name: ").strip()
            description = input("Enter folder description: ").strip()
            folder = slite.create_folder(name=name, description=description)
            logger.info(f"Created folder: {folder['name']}")
            display_item_details(folder, "folder")
            
        elif choice == "6":
            folder_id = input("Enter folder ID to rename: ").strip()
            new_name = input("Enter new folder name: ").strip()
            new_description = input("Enter new description (optional): ").strip()
            folder = slite.update_folder(folder_id=folder_id, name=new_name, description=new_description or None)
            logger.info(f"Renamed folder to: {folder['name']}")
            display_item_details(folder, "folder")
            
        elif choice == "7":
            folder_id = input("Enter folder ID to delete: ").strip()
            confirm = input("Are you sure you want to delete this folder? (y/n): ").lower()
            if confirm == 'y':
                result = slite.delete_folder(folder_id)
                logger.info(result['message'])
                
        elif choice == "8":
            logger.info("Exiting menu...")
            return False
            
        else:
            logger.info("Invalid choice. Please try again.")
            
        return True
            
    except Exception as e:
        logger.error(f"Error processing menu choice: {str(e)}")
        return True

def run_menu(slite: SliteAPI, current_folder_id: str = None):
    """Run the menu loop"""
    while True:
        display_menu()
        choice = input("Enter your choice (1-8): ").strip()
        if not handle_menu_choice(choice, slite, current_folder_id):
            break

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
                delete_result = slite.delete_folder(folder_id)
                logger.info(delete_result['message'])
                break
            except Exception as e:
                logger.error(f"Error deleting items: {str(e)}")
                break
        elif response == 'n':
            logger.info("Items will be kept.")
            logger.info("Opening document management menu...")
            run_menu(slite, folder_id)
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
            30,  # 30 seconds for testing, change to 300 for 5 minutes
            self._timer_callback
        )
        self.timer.start()
        logger.info("\nWaiting 30 seconds before prompting for deletion...")
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
        # Register event handlers
        slite.events.on_folder_created(on_folder_created)
        slite.events.on_folder_updated(on_folder_updated)
        slite.events.on_document_created(on_document_created)
        slite.events.on_document_updated(on_document_updated)

        # Create a folder
        folder = slite.create_folder(
            name="Meeting Notes",
            description="Collection of meeting notes and discussions"
        )
        logger.info(f"Created folder: {folder['name']}")
        display_item_details(folder, "folder")

        # Update the folder
        updated_folder = slite.update_folder(
            folder_id=folder['id'],
            name="Team Meeting Notes",
            description="Collection of team meeting notes and discussions"
        )
        logger.info(f"Updated folder name to: {updated_folder['name']}")
        display_item_details(updated_folder, "folder")

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
        display_item_details(doc, "document")

        # Update the document
        updated_doc = slite.update_document(
            doc_id=doc['id'],
            title=f"{doc_title} (Updated)",
            markdown_content=markdown_content,
            folder_id=folder['id']
        )
        logger.info(f"Updated document title to: {updated_doc['title']}")
        display_item_details(updated_doc, "document")

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
