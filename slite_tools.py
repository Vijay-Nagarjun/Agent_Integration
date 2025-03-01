from langchain.tools import tool
from slite_api import SliteAPI
import json
import logging
from typing import Optional, List

# Configure logging
logger = logging.getLogger(__name__)

# Initialize Slite API
slite_api = SliteAPI()

# Keep track of selected folder
selected_folder = {"id": "", "name": ""}

@tool
async def create_folder(input_text: str) -> str:
    """
    Create a folder in Slite.
    Input format: <folder_name>
    """
    try:
        folder_name = input_text.strip()
        if not folder_name:
            return "Error: Folder name is missing or empty."
        
        result = await slite_api.create_folder(folder_name)
        if result.get("success"):
            return f"Folder '{folder_name}' created successfully."
        else:
            return f"Error creating folder: {result.get('error', 'Unknown error')}"
    except Exception as e:
        return f"An error occurred: {e}"

@tool
async def delete_folder(input_text: str) -> str:
    """
    Delete a folder in Slite.
    Input format: <folder_name>
    """
    try:
        folder_name = input_text.strip()
        if not folder_name:
            return "Error: Folder name is missing or empty."
        
        result = await slite_api.delete_item(folder_name, "folder")
        if result.get("success"):
            return f"Folder '{folder_name}' deleted successfully."
        else:
            return f"Error deleting folder: {result.get('error', 'Unknown error')}"
    except Exception as e:
        return f"An error occurred: {e}"

@tool
async def list_folders_tool(input_text: str = None) -> str:
    """
    List all available folders in Slite. No other operations are done.
    Input: No input required
    """
    try:
        folders = await slite_api.list_folders()
        if isinstance(folders, list):
            folder_list = []
            for folder in folders:
                folder_list.append(f"- {folder['name']} (ID: {folder.get('id', 'N/A')})")
            return "\n".join(folder_list) if folder_list else "No folders found."
        else:
            return "Error: Unable to fetch folders."
    except Exception as e:
        return f"An error occurred while fetching folders: {e}"

@tool
async def select_folder_tool(input_text: str) -> str:
    """
    Select a folder from the available list by name.
    Input format: <folder_name>
    """
    global selected_folder
    try:
        folder_name = input_text.strip()
        if not folder_name:
            return "Error: Folder name is missing or empty."
            
        folders = await slite_api.list_folders()
        if not isinstance(folders, list):
            return "Error: Unable to fetch folders."
            
        for folder in folders:
            if folder["name"].lower() == folder_name.lower():
                selected_folder = {"id": folder.get("id"), "name": folder["name"]}
                return f"Folder '{folder['name']}' selected successfully."
        return "Error: Folder not found. Please provide a valid folder name."
    except Exception as e:
        return f"An error occurred: {e}"

def get_selected_folder():
    """
    Get the currently selected folder.
    Returns: Dict with folder id and name
    """
    return selected_folder

async def create_note(self, title: str, content: str, tags: Optional[List[str]] = None) -> str:
    """Create a new note"""
    try:
        # Format payload according to API docs
        payload = {
            "title": title,
            "markdown": content,
            "attributes": []  # Required by API
        }
        
        if tags:
            payload["attributes"] = tags
            
        result = await self.api.create_note_async(title=title, content=content)
        if result and isinstance(result, dict):
            self._last_note_id = result.get('id')
        return json.dumps({"status": "success", "note": result}, indent=2)
    except Exception as e:
        logger.error(f"Error creating note: {str(e)}")
        return f"Error creating note: {str(e)}"
