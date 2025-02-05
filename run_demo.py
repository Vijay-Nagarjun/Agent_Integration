import os
import json
import logging
import time
from dotenv import load_dotenv
from slite_api import SliteAPI
from datetime import datetime, timedelta
import sys
import threading
import asyncio
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
from functools import partial
import queue
from typing import Dict, List, Optional
import signal
from contextlib import contextmanager
import random
import traceback

# Load environment variables at the start
try:
    load_dotenv(override=True)
except Exception as e:
    print(f"Error loading environment variables: {str(e)}")
    sys.exit(1)

# Configure logging with performance metrics
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - [%(threadName)s] - %(message)s'
)
logger = logging.getLogger(__name__)

# Global thread pool for parallel operations
thread_pool = ThreadPoolExecutor(max_workers=4)
process_pool = ProcessPoolExecutor(max_workers=2)

# Event queue for handling operations
event_queue = queue.Queue()

class PerformanceMetrics:
    """Track and report performance metrics"""
    
    def __init__(self):
        self.operation_times = {}
        self.error_counts = {}
        self._lock = threading.Lock()
        
    def record_operation(self, operation: str, duration: float):
        with self._lock:
            if operation not in self.operation_times:
                self.operation_times[operation] = []
            self.operation_times[operation].append(duration)
            
    def record_error(self, operation: str):
        with self._lock:
            self.error_counts[operation] = self.error_counts.get(operation, 0) + 1
            
    def get_metrics(self) -> Dict:
        with self._lock:
            metrics = {}
            for op, times in self.operation_times.items():
                metrics[op] = {
                    'avg_time': sum(times) / len(times),
                    'min_time': min(times),
                    'max_time': max(times),
                    'total_ops': len(times),
                    'errors': self.error_counts.get(op, 0)
                }
            return metrics

# Initialize performance metrics
metrics = PerformanceMetrics()

@contextmanager
def measure_time(operation: str):
    """Context manager to measure operation time"""
    start_time = time.time()
    try:
        yield
    finally:
        duration = time.time() - start_time
        metrics.record_operation(operation, duration)

async def process_notes_batch(notes: List[Dict], slite: SliteAPI) -> List[Dict]:
    """Process a batch of notes in parallel"""
    async def process_note(note: Dict) -> Dict:
        try:
            with measure_time('note_processing'):
                # Add any note-specific processing here
                return note
        except Exception as e:
            logger.error(f"Error processing note: {str(e)}")
            metrics.record_error('note_processing')
            return None
    
    tasks = [process_note(note) for note in notes]
    return await asyncio.gather(*tasks)

def read_meeting_notes():
    """
    Read meeting notes from JSON file.
    This function is called after text_to_json conversion to ensure
    we're working with the latest data.
    
    Returns:
        dict: The meeting notes data in JSON format
    
    Raises:
        FileNotFoundError: If the JSON file doesn't exist
        JSONDecodeError: If the JSON file is invalid
    """
    try:
        # First, convert the latest text to JSON
        convert_text_to_json()
        # Then read the JSON file
        with open('meeting_notes.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        logger.error("meeting_notes.json file not found")
        raise
    except json.JSONDecodeError as e:
        logger.error(f"Error reading meeting notes: {str(e)}")
        raise

def convert_text_to_json():
    """
    Convert meeting notes from text to JSON format before processing.
    This function is automatically called before reading meeting notes to ensure
    the JSON file is up to date with the latest text content.
    """
    try:
        # Read the text file
        with open('meeting_notes.txt', 'r') as f:
            text_content = f.read()
        
        # Split content into sections
        lines = text_content.splitlines()
        formatted_content = []
        current_section = None
        current_points = []
        metadata = {
            'date': '',
            'time': '',
            'location': '',
            'attendees': [],
            'next_meeting': ''
        }

        for line in lines:
            line = line.strip()
            if not line or line == '---':
                continue
            
            # Extract metadata
            if line.startswith('**Date**:'):
                metadata['date'] = line.replace('**Date**:', '').strip()
            elif line.startswith('**Time**:'):
                metadata['time'] = line.replace('**Time**:', '').strip()
            elif line.startswith('**Location**:'):
                metadata['location'] = line.replace('**Location**:', '').strip()
            elif line.startswith('**Next Meeting**:'):
                metadata['next_meeting'] = line.replace('**Next Meeting**:', '').strip()
            elif line.startswith('**Attendees**:'):
                # Start collecting attendees
                continue
            elif line.startswith('- ') and not current_section:
                # These are attendees
                attendee = line.replace('- ', '').strip()
                metadata['attendees'].append(attendee)
                
            # Check for numbered sections (1., 2., etc.)
            elif line.strip().startswith(('1.', '2.', '3.', '4.', '5.', '6.')):
                if current_section and current_points:
                    formatted_content.append({
                        'title': current_section,
                        'points': current_points
                    })
                current_section = line.split('**', 2)[1].strip()
                current_points = []
                
            # Check for bullet points
            elif line.lstrip().startswith('- ') and current_section:
                point = line.lstrip('- ').strip()
                if point:
                    # Check if it's a sub-bullet point
                    if line.startswith('     -'):
                        # Add as a sub-point to the last main point
                        if current_points and isinstance(current_points[-1], dict):
                            current_points[-1]['sub_points'].append(point)
                    else:
                        # If the point starts with bold text, it's a header point
                        if point.startswith('**'):
                            current_points.append({
                                'header': point,
                                'sub_points': []
                            })
                        else:
                            current_points.append(point)

        # Add the last section
        if current_section and current_points:
            formatted_content.append({
                'title': current_section,
                'points': current_points
            })

        # Add special sections if they exist
        for line in lines:
            if line.strip() == '**Decisions Made:**':
                decisions_section = {
                    'title': 'Decisions Made',
                    'points': []
                }
                idx = lines.index(line)
                while idx + 1 < len(lines) and not lines[idx + 1].strip() == '---':
                    next_line = lines[idx + 1].strip()
                    if next_line.startswith('- '):
                        decisions_section['points'].append(next_line.lstrip('- ').strip())
                    idx += 1
                formatted_content.append(decisions_section)
            elif line.strip() == '**Action Items:**':
                actions_section = {
                    'title': 'Action Items',
                    'points': []
                }
                idx = lines.index(line)
                while idx + 1 < len(lines) and not lines[idx + 1].strip() == '---':
                    next_line = lines[idx + 1].strip()
                    if next_line.startswith(('1.', '2.', '3.', '4.', '5.')):
                        actions_section['points'].append(next_line.split('.', 1)[1].strip())
                    idx += 1
                formatted_content.append(actions_section)

        # Convert to JSON structure
        notes_data = {
            'timestamp': time.time(),
            'metadata': metadata,
            'sections': formatted_content,
            'format_version': '1.0'
        }
        
        # Write to JSON file
        with open('meeting_notes.json', 'w') as f:
            json.dump(notes_data, f, indent=2)
            
        logger.info("Successfully converted meeting notes from text to JSON")
        logger.info("Metadata:")
        for key, value in metadata.items():
            logger.info(f"  {key}: {value}")
        logger.info("Formatted content:")
        for section in formatted_content:
            logger.info(f"Section: {section['title']}")
            for point in section['points']:
                if isinstance(point, dict):
                    logger.info(f"  {point['header']}")
                    for sub_point in point['sub_points']:
                        logger.info(f"    - {sub_point}")
                else:
                    logger.info(f"  - {point}")
            
        return notes_data
            
    except Exception as e:
        logger.error(f"Error converting meeting notes: {str(e)}")
        raise

class ResourceManager:
    """Manage system resources and cleanup"""
    
    def __init__(self):
        self.resources = set()
        signal.signal(signal.SIGINT, self.cleanup)
        signal.signal(signal.SIGTERM, self.cleanup)
        
    def register(self, resource):
        self.resources.add(resource)
        
    def cleanup(self, *args):
        logger.info("Cleaning up resources...")
        for resource in self.resources:
            try:
                resource.close()
            except Exception as e:
                logger.error(f"Error cleaning up resource: {str(e)}")
        
        # Shutdown thread pools
        thread_pool.shutdown(wait=False)
        process_pool.shutdown(wait=False)
        
        # Print performance metrics
        logger.info("Performance Metrics:")
        for op, stats in metrics.get_metrics().items():
            logger.info(f"{op}:")
            logger.info(f"  Average time: {stats['avg_time']:.3f}s")
            logger.info(f"  Min time: {stats['min_time']:.3f}s")
            logger.info(f"  Max time: {stats['max_time']:.3f}s")
            logger.info(f"  Total operations: {stats['total_ops']}")
            logger.info(f"  Errors: {stats['errors']}")
        
        sys.exit(0)

# Initialize resource manager
resource_manager = ResourceManager()

async def display_menu():
    """Display the main menu options"""
    print("\nWhat would you like to do?")
    print("1. Create a document")
    print("2. Delete a document")
    print("3. Edit a document")
    print("4. Rename a document")
    print("5. Create a folder")
    print("6. Delete a folder")
    print("7. Rename a folder")
    print("8. Exit")

async def edit_document_menu():
    """Display document editing options"""
    print("\nHow would you like to edit the document?")
    print("1. Add notes to existing content")
    print("2. Replace existing content with new content")
    print("3. Cancel")

async def get_input(prompt: str = "") -> str:
    """Get input from user"""
    if prompt:
        print(prompt, end="", flush=True)
    return sys.stdin.readline().strip()

async def handle_menu_choice(choice: str, slite: SliteAPI, folder: Dict) -> bool:
    """Handle menu choice"""
    try:
        if choice == "1":
            # Create structured note
            folders = await slite.list_folders()
            print("\nAvailable folders:")
            for f in folders:
                display_item_details(f, "folder")
            
            folder_id = await get_input("\nEnter folder ID (leave empty for root): ")
            doc = await create_structured_note(slite, folder_id)
            
            print("\nDocument created successfully!")
            display_item_details(doc, "document")
            
        elif choice == '2':
            # Delete document
            doc_id = await get_input("\nEnter document ID to delete: ")
            if not doc_id:
                logger.error("No document ID provided")
                return True
                
            try:
                # Get document details first
                logger.info(f"Checking document {doc_id}...")
                doc = await slite.get_document(doc_id)
                
                # Show document details and confirm deletion
                print("\nDocument details:")
                print("-" * 50)
                print(f"Title: {doc.get('title', 'Untitled')}")
                content_preview = doc.get('content', '')
                if isinstance(content_preview, dict):
                    content_preview = content_preview.get('markdown', '')[:100]
                elif isinstance(content_preview, str):
                    content_preview = content_preview[:100]
                print(f"Content preview: {content_preview}...")
                print("-" * 50)
                
                confirm = await get_input("\nAre you sure you want to delete this document? (y/n): ")
                if confirm.lower() != 'y':
                    print("Deletion cancelled.")
                    return True
                    
                # Proceed with deletion
                logger.info(f"Deleting document {doc_id}...")
                await slite.delete_document(doc_id)
                print("\nDocument deleted successfully!")
                
            except Exception as e:
                if "Resource not found" in str(e):
                    print(f"\nDocument {doc_id} not found or already deleted.")
                else:
                    logger.error(f"Error deleting document: {str(e)}")
                    print("\nThere was an error deleting the document. Please try again.")
                    
        elif choice == '3':
            # Edit document
            # First list available documents
            logger.info("\nAvailable documents:")
            docs = await slite.list_documents()
            for doc in docs:
                display_item_details(doc, "document")
                
            print("\nEdit Document Options:")
            print("1. Add to existing content")
            print("2. Replace content")
            edit_type = await get_input("\nChoose edit type (1 or 2): ")
            
            if edit_type not in ['1', '2']:
                logger.error("Invalid edit type selected")
                return True
                
            doc_id = await get_input("\nEnter document ID to edit: ")
            
            try:
                # Verify document exists and get current content
                logger.info(f"Retrieving document {doc_id}...")
                existing_doc = await slite.get_document(doc_id)
                
                if not existing_doc:
                    logger.error(f"Could not find document {doc_id}")
                    return True
                
                if edit_type == '1':
                    # Add to existing - ask for new notes
                    print("\nEnter the new notes to append (press Enter twice when done):")
                    notes_lines = []
                    while True:
                        line = await get_input("")  # Empty prompt for content lines
                        if line == "":
                            break
                        notes_lines.append(line)
                    
                    if not notes_lines:
                        logger.error("No notes provided to append")
                        return True
                    
                    try:
                        # Get existing content
                        logger.info(f"Retrieving document {doc_id}...")
                        existing_doc = await slite.get_document(doc_id)
                        
                        # Get content from the response
                        existing_content = existing_doc.get('content', '')
                        if isinstance(existing_content, str):
                            existing_content = existing_content
                        elif isinstance(existing_content, dict):
                            existing_content = existing_content.get('markdown', '')
                        else:
                            existing_content = ''
                        
                        logger.info(f"Existing content length: {len(existing_content)} characters")
                        logger.info(f"First 100 chars of existing content: {existing_content[:100]}")
                        
                        # Format new notes as a section
                        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
                        new_section = [
                            "",  # Empty line for spacing
                            f"## 📝 Updates ({timestamp})",
                            ""  # Empty line for spacing
                        ]
                        
                        # Add each note as a bullet point
                        for note in notes_lines:
                            new_section.append(f"- {note}")
                        new_section.append("")  # Empty line at the end
                        
                        # Combine existing content with new section
                        existing_content = existing_content.strip()
                        new_content = "\n".join(new_section)
                        
                        if existing_content:
                            combined_content = f"{existing_content}\n\n{new_content}"
                        else:
                            combined_content = new_content
                        
                        logger.info(f"Combined content length: {len(combined_content)} characters")
                        logger.info(f"First 100 chars of combined content: {combined_content[:100]}")
                        
                        # Update the document with combined content
                        logger.info("Updating document with combined content...")
                        await slite.update_document(doc_id, combined_content)
                        
                        print("\nDocument has been updated successfully!")
                        print("\nNew content added:")
                        print("-" * 50)
                        for line in notes_lines:
                            print(line)
                        print("-" * 50)
                        
                        # Verify the update
                        logger.info("Verifying update...")
                        updated_doc = await slite.get_document(doc_id)
                        updated_content = updated_doc.get('content', '')
                        if isinstance(updated_content, str):
                            updated_content = updated_content
                        elif isinstance(updated_content, dict):
                            updated_content = updated_content.get('markdown', '')
                        else:
                            updated_content = ''
                        
                        if updated_content.strip() == combined_content.strip():
                            logger.info("Update verification successful - content matches")
                        else:
                            logger.warning("Update verification failed - content mismatch!")
                            logger.info(f"Expected content length: {len(combined_content)}")
                            logger.info(f"Actual content length: {len(updated_content)}")
                        
                    except Exception as e:
                        logger.error(f"Error appending content: {str(e)}")
                        print("\nThere was an error updating the document. Please try again.")
                        return True
                        
                elif edit_type == '2':
                    # Replace content - ask for new content
                    print("\nEnter the new content (press Enter twice when done):")
                    content_lines = []
                    while True:
                        line = await get_input("")  # Empty prompt for content lines
                        if line == "":
                            break
                        content_lines.append(line)
                    
                    if not content_lines:
                        logger.error("No content provided")
                        return True
                    
                    try:
                        # Update the document with new content
                        new_content = "\n".join(content_lines)
                        logger.info("Updating document with new content...")
                        await slite.update_document(doc_id, new_content)
                        
                        print("\nDocument has been updated successfully!")
                        print("\nNew content:")
                        print("-" * 50)
                        print(new_content)
                        print("-" * 50)
                        
                        # Verify the update
                        logger.info("Verifying update...")
                        updated_doc = await slite.get_document(doc_id)
                        if updated_doc and updated_doc.get('markdown', '').strip() == new_content.strip():
                            logger.info("Update verification successful")
                        else:
                            logger.warning("Update verification failed - content may not match")
                        
                    except Exception as e:
                        logger.error(f"Error replacing content: {str(e)}")
                        print("\nThere was an error updating the document. Please try again.")
                        return True
                
            except Exception as e:
                logger.error(f"Error editing document: {str(e)}")
                return True
            
        elif choice == '4':
            # Rename document
            print("\nAvailable documents:")
            docs = await slite.list_documents()
            for doc in docs:
                print(f"ID: {doc.get('id')} - Title: {doc.get('title', 'Untitled')}")
            
            doc_id = await get_input("\nEnter document ID to rename: ")
            if not doc_id:
                print("No document ID provided")
                return True
            
            # Find current document title
            current_title = None
            for doc in docs:
                if doc.get('id') == doc_id:
                    current_title = doc.get('title', 'Untitled')
                    break
            
            if not current_title:
                print(f"Document with ID {doc_id} not found")
                return True
            
            print(f"\nCurrent title: {current_title}")
            new_title = await get_input("Enter new title: ")
            
            if not new_title:
                print("No new title provided")
                return True
            
            # Rename the document
            doc = await slite.rename_document(doc_id, new_title)
            print(f"\nDocument renamed successfully from '{current_title}' to '{new_title}'!")
            
        elif choice == '5':
            # Create folder
            folder_name = await get_input("Enter folder name: ")
            new_folder = await slite.create_folder(folder_name)
            logger.info("Created new folder:")
            display_item_details(new_folder, "folder")
            
        elif choice == '6':
            # Delete folder
            # First list available folders
            logger.info("\nAvailable folders:")
            folders = await slite.list_folders()
            for folder in folders:
                display_item_details(folder, "folder")
                
            folder_id = await get_input("\nEnter folder ID to delete: ")
            await slite.delete_folder(folder_id)
            logger.info(f"Folder {folder_id} deleted successfully")
            
        elif choice == '7':
            # Rename folder
            # First list available folders
            logger.info("\nAvailable folders:")
            folders = await slite.list_folders()
            for folder in folders:
                display_item_details(folder, "folder")
                
            folder_id = await get_input("\nEnter folder ID to rename: ")
            new_name = await get_input("Enter new name: ")
            await slite.rename_folder(folder_id, new_name)
            logger.info(f"Folder renamed to '{new_name}' successfully")
            
        elif choice == '8':
            # Exit
            logger.info("Exiting...")
            return False
            
        else:
            logger.error("Invalid choice")
            
        return True
            
    except Exception as e:
        logger.error(f"Error handling menu choice: {str(e)}")
        return True

async def create_structured_note(slite: SliteAPI, folder_id: Optional[str] = None) -> Dict:
    """Create a structured meeting note with proper formatting"""
    print("\nCreating a structured meeting note")
    print("-" * 50)
    
    # Get basic meeting details
    title = await get_input("Enter meeting title: ")
    date = await get_input("Enter meeting date (YYYY-MM-DD) [Today]: ") or datetime.now().strftime("%Y-%m-%d")
    time = await get_input("Enter meeting time (HH:MM) [Now]: ") or datetime.now().strftime("%H:%M")
    location = await get_input("Enter meeting location: ")
    
    # Get attendees
    print("\nEnter attendees (one per line, press Enter twice when done):")
    attendees = []
    while True:
        attendee = await get_input()
        if not attendee:
            break
        attendees.append(attendee)
    
    # Get meeting content sections
    sections = {}
    print("\nEnter content for each section:")
    for section in ["Progress Update", "Discussion Points", "Action Items", "Next Steps"]:
        print(f"\n{section}:")
        content_lines = []
        while True:
            line = await get_input()
            if not line:
                break
            content_lines.append(line)
        sections[section] = content_lines
    
    # Format content in markdown
    content = f"""# {title}

## Meeting Details
- Date: {date}
- Time: {time}
- Location: {location}
- Attendees: {', '.join(attendees)}

## Progress Update
{chr(10).join('- ' + line for line in sections['Progress Update'])}

## Discussion Points
{chr(10).join('- ' + line for line in sections['Discussion Points'])}

## Action Items
{chr(10).join('- ' + line for line in sections['Action Items'])}

## Next Steps
{chr(10).join('- ' + line for line in sections['Next Steps'])}
"""
    
    try:
        with measure_time('create_document'):
            doc = await slite.create_document(
                title=title,
                content=content,
                parent_note_id=folder_id
            )
            logger.info(f"Created structured note: {doc.get('id')}")
            return doc
    except Exception as e:
        logger.error(f"Error creating structured note: {str(e)}")
        metrics.record_error('create_document')
        raise

async def create_folder_structure(slite: SliteAPI) -> Dict[str, str]:
    """Create a standard folder structure for organizing notes"""
    folder_structure = {
        "Meeting Notes": [
            "Team Meetings",
            "Project Updates",
            "Client Meetings",
            "Internal Reviews"
        ],
        "Documentation": [
            "Project Specs",
            "Technical Docs",
            "Process Guides"
        ]
    }
    
    created_folders = {}
    
    try:
        for main_folder, subfolders in folder_structure.items():
            # Create main folder
            main_folder_doc = await slite.create_document(
                title=main_folder,
                content=f"# {main_folder}\nOrganizational folder for {main_folder}",
                is_folder=True
            )
            created_folders[main_folder] = main_folder_doc['id']
            
            # Create subfolders
            for subfolder in subfolders:
                subfolder_doc = await slite.create_document(
                    title=subfolder,
                    content=f"# {subfolder}\nSubfolder for {main_folder} - {subfolder}",
                    is_folder=True,
                    parent_note_id=main_folder_doc['id']
                )
                created_folders[f"{main_folder}/{subfolder}"] = subfolder_doc['id']
        
        logger.info("Created standard folder structure")
        return created_folders
    except Exception as e:
        logger.error(f"Error creating folder structure: {str(e)}")
        metrics.record_error('create_folder_structure')
        raise

def display_item_details(item: dict, item_type: str = "item"):
    """Display details of a document or folder including its ID and URL"""
    if not item:
        return
        
    item_id = item.get('id')
    if item_id:
        # For newly created items, highlight that this is a new ID
        created_timestamp = item.get('createdAt')
        if isinstance(created_timestamp, str):
            try:
                created_timestamp = int(created_timestamp)
            except (ValueError, TypeError):
                created_timestamp = 0
                
        is_new = time.time() - (created_timestamp / 1000 if created_timestamp else 0) < 60  # Created in last minute
        id_prefix = "NEW " if is_new else ""
        print(f"\n{id_prefix}{item_type.title()} ID: {item_id}")
        print(f"Title: {item.get('name') or item.get('title')}")
        
        # Display URL
        url = f"https://app.slite.com/app/docs/{item_id}"
        print(f"URL: {url}")
        
    if item_type == "folder":
        print(f"Description: {item.get('description', '')}")
    
    created_at = item.get('createdAt')
    updated_at = item.get('updatedAt')
    
    try:
        if created_at:
            if isinstance(created_at, str):
                created_at = int(created_at)
            created_time = datetime.fromtimestamp(created_at / 1000).strftime('%Y-%m-%d %H:%M:%S')
            print(f"Created: {created_time}")
    except (ValueError, TypeError) as e:
        logger.warning(f"Could not parse creation timestamp: {created_at}")
        
    try:
        if updated_at:
            if isinstance(updated_at, str):
                updated_at = int(updated_at)
            updated_time = datetime.fromtimestamp(updated_at / 1000).strftime('%Y-%m-%d %H:%M:%S')
            print(f"Updated: {updated_time}")
    except (ValueError, TypeError) as e:
        logger.warning(f"Could not parse update timestamp: {updated_at}")
        
    print("-" * 50)

async def main():
    """Main function to run the demo"""
    try:
        async with SliteAPI(os.getenv("SLITE_API_KEY")) as slite:
            print("\nConnected to Slite API")
            
            # Check if folder structure exists
            folders = await slite.list_folders()
            if not any(f.get('title') == 'Meeting Notes' for f in folders):
                print("\nInitializing folder structure...")
                folder_structure = await create_folder_structure(slite)
                print("\nCreated standard folder structure:")
                for path, folder_id in folder_structure.items():
                    print(f"- {path} (ID: {folder_id})")
            
            while True:
                await display_menu()
                choice = await get_input("\nEnter your choice (1-8): ")
                
                if choice == "8":
                    print("\nExiting...")
                    break
                    
                if not await handle_menu_choice(choice, slite, None):
                    break
                
                # Display performance metrics periodically
                if random.random() < 0.1:  # 10% chance to show metrics
                    print("\nPerformance Metrics:")
                    print("-" * 50)
                    for op, stats in metrics.get_metrics().items():
                        print(f"{op}:")
                        print(f"  Average time: {stats['avg_time']:.3f}s")
                        print(f"  Total operations: {stats['total_ops']}")
                        print(f"  Errors: {stats['errors']}")
                    print("-" * 50)
    
    except Exception as e:
        logger.error(f"Error in main: {str(e)}")
        logger.error(traceback.format_exc())
    finally:
        # Display final metrics
        print("\nFinal Performance Metrics:")
        print(json.dumps(metrics.get_metrics(), indent=2))

if __name__ == "__main__":
    """
    Main execution flow:
    1. Load environment variables
    2. Initialize API client
    3. Create folder structure if needed
    4. Start interactive menu
    5. Handle user commands
    6. Clean up on exit
    """
    try:
        # Load environment variables
        load_dotenv(override=True)
        if not os.getenv("SLITE_API_KEY"):
            logger.error("SLITE_API_KEY environment variable not set")
            sys.exit(1)
            
        # Run the async main function
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nExiting gracefully...")
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}")
        logger.error(traceback.format_exc())
        sys.exit(1)