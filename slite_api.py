import requests
import logging
from typing import Dict, Optional, List, Callable
from datetime import datetime
import json

logger = logging.getLogger(__name__)

class SliteEventHandler:
    def __init__(self):
        self.folder_created_handlers: List[Callable] = []
        self.folder_updated_handlers: List[Callable] = []
        self.document_created_handlers: List[Callable] = []
        self.document_updated_handlers: List[Callable] = []
        
    def on_folder_created(self, handler: Callable):
        self.folder_created_handlers.append(handler)
        
    def on_folder_updated(self, handler: Callable):
        self.folder_updated_handlers.append(handler)
        
    def on_document_created(self, handler: Callable):
        self.document_created_handlers.append(handler)
        
    def on_document_updated(self, handler: Callable):
        self.document_updated_handlers.append(handler)
        
    def trigger_folder_created(self, folder_data: Dict):
        for handler in self.folder_created_handlers:
            try:
                handler(folder_data)
            except Exception as e:
                logger.error(f"Error in folder created handler: {str(e)}")
                
    def trigger_folder_updated(self, folder_data: Dict):
        for handler in self.folder_updated_handlers:
            try:
                handler(folder_data)
            except Exception as e:
                logger.error(f"Error in folder updated handler: {str(e)}")
                
    def trigger_document_created(self, document_data: Dict):
        for handler in self.document_created_handlers:
            try:
                handler(document_data)
            except Exception as e:
                logger.error(f"Error in document created handler: {str(e)}")
                
    def trigger_document_updated(self, document_data: Dict):
        for handler in self.document_updated_handlers:
            try:
                handler(document_data)
            except Exception as e:
                logger.error(f"Error in document updated handler: {str(e)}")

class SliteAPI:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.slite.com"
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        self.events = SliteEventHandler()

    def add_metadata(self, data: Dict) -> Dict:
        """Add metadata to the data dictionary"""
        if "metadata" not in data:
            data["metadata"] = {}
            
        data["metadata"].update({
            "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "updated_by": "Slite Integration Agent"
        })
        return data

    def _convert_text_to_prosemirror_node(self, text: str) -> Dict:
        """Convert a text string to a ProseMirror text node"""
        return {
            "type": "text",
            "text": text
        }

    def _convert_to_prosemirror(self, content: str) -> Dict:
        """Convert content to ProseMirror format"""
        lines = content.split('\n')
        doc_content = []
        
        current_list = None
        current_section = None
        current_paragraph = None
        
        for line in lines:
            line = line.rstrip()
            
            # Skip empty lines
            if not line:
                if current_list:
                    doc_content.append(current_list)
                    current_list = None
                if current_paragraph:
                    doc_content.append(current_paragraph)
                doc_content.append({
                    "type": "paragraph",
                    "content": [{"type": "text", "text": ""}]
                })
                continue
            
            # Handle bullet points
            if line.strip().startswith('- '):
                text = line.strip()[2:]
                if current_list is None:
                    current_list = {
                        "type": "bulletList",
                        "content": []
                    }
                list_item = {
                    "type": "listItem",
                    "content": [{
                        "type": "paragraph",
                        "content": [{"type": "text", "text": text}]
                    }]
                }
                current_list["content"].append(list_item)
                
            # Handle section headers
            elif line.startswith('Meeting Notes:') or line.startswith('Date:') or line.startswith('Time:') or line.startswith('Attendees:') or line.startswith('Facilitator:'):
                if current_list:
                    doc_content.append(current_list)
                    current_list = None
                if current_paragraph:
                    doc_content.append(current_paragraph)
                    current_paragraph = None
                    
                doc_content.append({
                    "type": "heading",
                    "attrs": {"level": 2},
                    "content": [{"type": "text", "text": line}]
                })
                
            # Handle numbered sections
            elif line[0].isdigit() and line[1] == '.':
                if current_list:
                    doc_content.append(current_list)
                    current_list = None
                if current_paragraph:
                    doc_content.append(current_paragraph)
                    current_paragraph = None
                    
                doc_content.append({
                    "type": "heading",
                    "attrs": {"level": 2},
                    "content": [{"type": "text", "text": line}]
                })
                
            # Regular text
            else:
                if current_list:
                    doc_content.append(current_list)
                    current_list = None
                    
                if not current_paragraph:
                    current_paragraph = {
                        "type": "paragraph",
                        "content": []
                    }
                current_paragraph["content"].append({
                    "type": "text", 
                    "text": line
                })
        
        # Add any remaining content
        if current_list:
            doc_content.append(current_list)
        if current_paragraph:
            doc_content.append(current_paragraph)
            
        return {
            "type": "doc",
            "content": doc_content
        }

    def create_folder(self, name: str, description: str = "") -> Dict:
        """Create a new folder in Slite by creating a special note"""
        try:
            endpoint = f"{self.base_url}/v1/notes"
            
            # Create a folder using note with special format
            markdown_content = f"""# {name}

{description}

---
This is a folder for organizing content.
"""
            
            data = {
                "title": name,
                "markdown": markdown_content,
                "isFolder": True
            }
            
            # Add metadata
            data = self.add_metadata(data)
            
            response = requests.post(
                endpoint,
                headers=self.headers,
                json=data
            )
            
            if response.status_code in [200, 201]:
                result = response.json()
                folder_data = {
                    "id": result.get("id"),
                    "name": name,
                    "description": description,
                    "url": result.get("url"),
                    "metadata": data.get("metadata", {})
                }
                # Trigger folder created event
                self.events.trigger_folder_created(folder_data)
                return folder_data
            else:
                logger.error(f"Error creating folder: {response.text}")
                response.raise_for_status()
                
        except Exception as e:
            logger.error(f"Error creating folder: {str(e)}")
            raise

    def create_document(self, title: str, markdown_content: str, folder_id: Optional[str] = None) -> Dict:
        """Create a new document in Slite"""
        try:
            endpoint = f"{self.base_url}/v1/notes"
            data = {
                "title": title,
                "markdown": markdown_content
            }
            
            if folder_id:
                data["parentNoteId"] = folder_id
                
            # Add metadata
            data = self.add_metadata(data)
            
            response = requests.post(
                endpoint,
                headers=self.headers,
                json=data
            )
            
            if response.status_code in [200, 201]:
                result = response.json()
                # Add our metadata to the result
                result["metadata"] = data.get("metadata", {})
                # Trigger document created event
                self.events.trigger_document_created(result)
                return result
            else:
                logger.error(f"Error creating document: {response.text}")
                response.raise_for_status()
                
        except Exception as e:
            logger.error(f"Error creating document: {str(e)}")
            raise

    def format_meeting_notes_markdown(self, notes_data: dict) -> str:
        """Format meeting notes as markdown"""
        markdown = []
        
        # Add metadata
        metadata = notes_data.get("metadata", {})
        markdown.append("# Meeting Details\n")
        markdown.append(f"**Date:** {metadata.get('date', 'N/A')}")
        markdown.append(f"**Time:** {metadata.get('time', 'N/A')}")
        markdown.append(f"**Attendees:** {metadata.get('attendees_count', 0)} attendees")
        markdown.append(f"**Facilitator:** {metadata.get('facilitator', 'N/A')}\n")
        
        # Add sections
        for section in notes_data.get("sections", []):
            markdown.append(f"# {section.get('title', 'Untitled Section')}")
            
            for item in section.get("content", []):
                if item.get("subtitle"):
                    markdown.append(f"## {item['subtitle']}")
                
                details = item.get("details", "")
                if isinstance(details, list):
                    for detail in details:
                        markdown.append(f"- {detail}")
                else:
                    markdown.append(details)
                
            markdown.append("")  # Add empty line between sections
        
        return "\n".join(markdown)

    def create_note(self, title: str, content: str) -> Dict:
        """Create a new note in Slite"""
        try:
            endpoint = f"{self.base_url}/v1/notes"
            
            # Convert content to ProseMirror format
            content = self._convert_to_prosemirror(content)
            
            data = {
                "title": title,
                "content": content
            }
            
            logger.debug(f"Creating note with title: {title}")
            logger.debug(f"Content structure: {content}")
            
            response = requests.post(
                endpoint,
                headers=self.headers,
                json=data
            )
            
            if response.status_code in [200, 201]:
                logger.info(f"Successfully created note with content")
                return response.json()
            elif response.status_code == 429:
                raise Exception("Rate limit exceeded")
            elif response.status_code == 401:
                raise Exception("Invalid API key")
            else:
                logger.error(f"Error creating note: {response.text}")
                raise Exception(f"Error creating note: {response.text}")
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Error creating note: {str(e)}")
            raise Exception(f"Network error: {str(e)}")

    def update_note(self, note_id: str, title: str, content: str) -> Dict:
        """Update an existing note in Slite"""
        try:
            endpoint = f"{self.base_url}/v1/notes/{note_id}"
            
            # Convert content to ProseMirror format
            content = self._convert_to_prosemirror(content)
            
            data = {
                "title": title,
                "content": content
            }
            
            logger.debug(f"Updating note {note_id}")
            response = requests.patch(
                endpoint,
                headers=self.headers,
                json=data
            )
            
            if response.status_code == 200:
                logger.info(f"Successfully updated note {note_id}")
                return response.json()
            elif response.status_code == 429:
                raise Exception("Rate limit exceeded")
            elif response.status_code == 401:
                raise Exception("Invalid API key")
            elif response.status_code == 404:
                raise Exception(f"Note {note_id} not found")
            else:
                raise Exception(f"Error updating note: {response.text}")
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Error updating note: {str(e)}")
            raise Exception(f"Network error: {str(e)}")

    def get_note(self, note_id: str) -> Dict:
        """Get a note from Slite"""
        try:
            endpoint = f"{self.base_url}/v1/notes/{note_id}"
            response = requests.get(endpoint, headers=self.headers)
            
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 429:
                raise Exception("Rate limit exceeded")
            elif response.status_code == 401:
                raise Exception("Invalid API key")
            elif response.status_code == 404:
                raise Exception(f"Note {note_id} not found")
            else:
                raise Exception(f"Error getting note: {response.text}")
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Error getting note: {str(e)}")
            raise Exception(f"Network error: {str(e)}")

    def search_notes(self, query: str) -> List[Dict]:
        """Search for notes in Slite"""
        try:
            endpoint = f"{self.base_url}/v1/notes/search"
            response = requests.get(endpoint, headers=self.headers, params={"query": query})
            
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 429:
                raise Exception("Rate limit exceeded")
            elif response.status_code == 401:
                raise Exception("Invalid API key")
            else:
                raise Exception(f"Error searching notes: {response.text}")
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Error searching notes: {str(e)}")
            raise Exception(f"Network error: {str(e)}")

    def delete_note(self, note_id: str) -> Dict:
        """Delete a note from Slite"""
        try:
            endpoint = f"{self.base_url}/v1/notes/{note_id}"
            response = requests.delete(endpoint, headers=self.headers)
            
            if response.status_code == 204:
                return {"status": "success", "message": f"Note {note_id} deleted successfully"}
            elif response.status_code == 429:
                raise Exception("Rate limit exceeded")
            elif response.status_code == 401:
                raise Exception("Invalid API key")
            elif response.status_code == 404:
                raise Exception(f"Note {note_id} not found")
            else:
                raise Exception(f"Error deleting note: {response.text}")
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Error deleting note: {str(e)}")
            raise Exception(f"Network error: {str(e)}")

    def update_folder(self, folder_id: str, name: str, description: str = "") -> Dict:
        """Update an existing folder in Slite"""
        try:
            endpoint = f"{self.base_url}/v1/notes/{folder_id}"
            
            # Update folder using note with special format
            markdown_content = f"""# {name}

{description}

---
This is a folder for organizing content.
"""
            
            data = {
                "title": name,
                "markdown": markdown_content,
                "isFolder": True
            }
            
            # Add metadata
            data = self.add_metadata(data)
            
            response = requests.put(
                endpoint,
                headers=self.headers,
                json=data
            )
            
            if response.status_code in [200, 201]:
                result = response.json()
                folder_data = {
                    "id": result.get("id"),
                    "name": name,
                    "description": description,
                    "url": result.get("url"),
                    "metadata": data.get("metadata", {})
                }
                # Trigger folder updated event
                self.events.trigger_folder_updated(folder_data)
                return folder_data
            else:
                logger.error(f"Error updating folder: {response.text}")
                response.raise_for_status()
                
        except Exception as e:
            logger.error(f"Error updating folder: {str(e)}")
            raise

    def delete_folder(self, folder_id: str) -> Dict:
        """Delete a folder from Slite"""
        try:
            endpoint = f"{self.base_url}/v1/notes/{folder_id}"
            response = requests.delete(endpoint, headers=self.headers)
            
            if response.status_code == 204:
                return {"status": "success", "message": f"Folder {folder_id} deleted successfully"}
            elif response.status_code == 429:
                raise Exception("Rate limit exceeded")
            elif response.status_code == 401:
                raise Exception("Invalid API key")
            elif response.status_code == 404:
                raise Exception(f"Folder {folder_id} not found")
            else:
                raise Exception(f"Error deleting folder: {response.text}")
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Error deleting folder: {str(e)}")
            raise Exception(f"Network error: {str(e)}")

    def update_document(self, doc_id: str, title: str, markdown_content: str, folder_id: Optional[str] = None) -> Dict:
        """Update an existing document in Slite"""
        try:
            endpoint = f"{self.base_url}/v1/notes/{doc_id}"
            data = {
                "title": title,
                "markdown": markdown_content
            }
            
            if folder_id:
                data["parentNoteId"] = folder_id
                
            # Add metadata
            data = self.add_metadata(data)
            
            response = requests.put(
                endpoint,
                headers=self.headers,
                json=data
            )
            
            if response.status_code in [200, 201]:
                result = response.json()
                # Add our metadata to the result
                result["metadata"] = data.get("metadata", {})
                # Trigger document updated event
                self.events.trigger_document_updated(result)
                return result
            else:
                logger.error(f"Error updating document: {response.text}")
                response.raise_for_status()
                
        except Exception as e:
            logger.error(f"Error updating document: {str(e)}")
            raise

    def delete_document(self, doc_id: str) -> Dict:
        """Delete a document from Slite"""
        try:
            endpoint = f"{self.base_url}/v1/notes/{doc_id}"
            response = requests.delete(endpoint, headers=self.headers)
            
            if response.status_code == 204:
                return {"status": "success", "message": f"Document {doc_id} deleted successfully"}
            elif response.status_code == 429:
                raise Exception("Rate limit exceeded")
            elif response.status_code == 401:
                raise Exception("Invalid API key")
            elif response.status_code == 404:
                raise Exception(f"Document {doc_id} not found")
            else:
                raise Exception(f"Error deleting document: {response.text}")
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Error deleting document: {str(e)}")
            raise Exception(f"Network error: {str(e)}")

if __name__ == "__main__":
    # Test the API connection
    slite = SliteAPI("your_api_key")
    
    print("Testing Slite API connection...")
    result = slite.get_note("your_note_id")
    if result:
        print("Successfully connected to Slite API!")
    else:
        print("Failed to connect to Slite API. Please check your API key and internet connection.")
