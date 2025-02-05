import os
import logging
import asyncio
from datetime import datetime
from typing import List, Dict, Any, Optional
from functools import partial
from langchain_community.chat_models import ChatOpenAI
from langchain.agents import AgentType, initialize_agent, Tool
from langchain.memory import ConversationSummaryBufferMemory
from langchain.prompts import MessagesPlaceholder
from langchain.chains import LLMChain
from langchain.prompts import ChatPromptTemplate, HumanMessagePromptTemplate, SystemMessagePromptTemplate
from langchain.tools import StructuredTool
from langchain.agents import AgentExecutor, OpenAIFunctionsAgent
from pydantic import BaseModel, Field
from note_manager import NoteManager, SliteAPI
from models import MeetingNote, FolderStructure
import json
import traceback

logger = logging.getLogger(__name__)

class SliteTools:
    """Tools for interacting with Slite"""

    def __init__(self, api: SliteAPI):
        self.api = api
        self._last_note_id = None  # Store the ID of the last created/accessed note
        self._last_folder_id = None  # Store the ID of the last created/accessed folder
        
    @property
    def last_note_id(self):
        """Get the ID of the last created/accessed note"""
        return self._last_note_id
        
    @property
    def last_folder_id(self):
        """Get the ID of the last created/accessed folder"""
        return self._last_folder_id

    async def create_note(self, title: str, content: str, tags: Optional[List[str]] = None) -> str:
        """Create a new note"""
        try:
            result = await self.api.create_note_async(title=title, content=content)
            if result and isinstance(result, dict):
                self._last_note_id = result.get('id')  # Store the note ID
            return json.dumps({"status": "success", "note": result}, indent=2)
        except Exception as e:
            logger.error(f"Error creating note: {str(e)}")
            return f"Error creating note: {str(e)}"

    async def search_notes(self, query: str) -> str:
        """Search for notes"""
        try:
            results = await self.api.search_notes_async(query)
            if results and isinstance(results, list) and len(results) > 0:
                self._last_note_id = results[0].get('id')  # Store the first result's ID
            return json.dumps({"status": "success", "results": results}, indent=2)
        except Exception as e:
            logger.error(f"Error searching notes: {str(e)}")
            return f"Error searching notes: {str(e)}"

    async def update_note(self, note_id: str, content: str, append: bool = False) -> str:
        """Update or append to an existing note."""
        try:
            # Update the note
            result = await self.api.update_note_async(note_id, content, append)
            
            if result.get("status") == "error":
                return json.dumps(result, indent=2)
            
            return json.dumps({
                "status": "success",
                "message": f"Successfully updated note {note_id}",
                "data": result.get("data", {})
            }, indent=2)
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Error updating note: {error_msg}")
            return json.dumps({
                "status": "error",
                "message": f"Error updating note: {error_msg}"
            }, indent=2)

    async def summarize_note(self, note_id: str) -> str:
        """Generate a summary of a note's content"""
        try:
            note = await self.api.get_note_async(note_id)
            if not note:
                return "Note not found"
            return json.dumps({
                "status": "success",
                "summary": f"Summary of note '{note['title']}': {note['content'][:200]}..."
            }, indent=2)
        except Exception as e:
            logger.error(f"Error summarizing note: {str(e)}")
            return f"Error summarizing note: {str(e)}"

    async def delete_note(self, note_id: str = None) -> str:
        """Delete a note by ID or title"""
        try:
            # If no note_id provided, use the last accessed note
            if not note_id and self._last_note_id:
                note_id = self._last_note_id
                logger.info(f"Using last accessed note ID: {note_id}")
            elif not note_id:
                return json.dumps({
                    "status": "error",
                    "message": "No note ID provided and no last accessed note found"
                }, indent=2)

            original_input = note_id  # Store original input for error messages
            found_by_title = False

            # If note_id doesn't look like a Slite ID, try to search for it by title
            if not note_id.startswith('n_'):
                try:
                    logger.info(f"Searching for note with title: {note_id}")
                    search_results = await self.api.search_notes_async(note_id)
                    
                    if search_results:
                        # Try exact match first
                        for note in search_results:
                            if note.get('title', '').lower() == note_id.lower():
                                note_id = note.get('id')
                                found_by_title = True
                                logger.info(f"Found exact match for title '{original_input}' with ID: {note_id}")
                                break
                        
                        # If no exact match, try partial match
                        if not found_by_title and search_results[0].get('id'):
                            note_id = search_results[0].get('id')
                            found_by_title = True
                            logger.info(f"Using best match for title '{original_input}' with ID: {note_id}")
                    
                    if not found_by_title:
                        return json.dumps({
                            "status": "error",
                            "message": f"Could not find note with title: {original_input}"
                        }, indent=2)
                        
                except Exception as e:
                    logger.error(f"Error searching for note by title: {str(e)}")
                    return json.dumps({
                        "status": "error",
                        "message": f"Error searching for note '{original_input}': {str(e)}"
                    }, indent=2)

            # Delete the note
            result = await self.api.delete_note_async(note_id)
            
            # Check the result
            if result.get("status") == "error":
                return json.dumps(result, indent=2)
                
            # Clear the last note ID if we just deleted it
            if self._last_note_id == note_id:
                self._last_note_id = None
                
            success_msg = f"Note {original_input if found_by_title else note_id} deleted successfully"
            logger.info(success_msg)
            return json.dumps({
                "status": "success",
                "message": success_msg,
                "note_id": note_id
            }, indent=2)
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Error deleting note: {error_msg}")
            return json.dumps({
                "status": "error",
                "message": f"Error deleting note: {error_msg}"
            }, indent=2)

    async def create_folder(self, name: str, description: str = "") -> str:
        """Create a new folder"""
        try:
            result = await self.api.create_folder(name=name, description=description)
            if result and isinstance(result, dict):
                self._last_folder_id = result.get('id')
            return json.dumps({"status": "success", "folder": result}, indent=2)
        except Exception as e:
            logger.error(f"Error creating folder: {str(e)}")
            return f"Error creating folder: {str(e)}"

    async def create_note_in_folder(self, title: str, content: str, folder_name: str = None, tags: Optional[List[str]] = None) -> str:
        """Create a new note in a specific folder"""
        try:
            folder_id = None
            
            # If folder_name provided, search for existing folder
            if folder_name:
                folder = await self.api.search_folder_by_name(folder_name)
                if folder:
                    folder_id = folder.get('id')
                    logger.info(f"Found existing folder: {folder_name} with ID: {folder_id}")
                else:
                    # Create new folder if not found
                    logger.info(f"Folder not found, creating new folder: {folder_name}")
                    folder_result = await self.api.create_folder(name=folder_name)
                    folder_id = folder_result.get('id')
            else:
                # Use last created folder if no folder name provided
                folder_id = self._last_folder_id
            
            # Create note in the folder
            result = await self.api.create_note_async(title=title, content=content, parent_note_id=folder_id)
            if result and isinstance(result, dict):
                self._last_note_id = result.get('id')
            return json.dumps({"status": "success", "note": result}, indent=2)
        except Exception as e:
            logger.error(f"Error creating note in folder: {str(e)}")
            return f"Error creating note in folder: {str(e)}"

    async def rename_folder(self, folder_name: str, new_name: str) -> str:
        """Rename a folder"""
        try:
            # Find the folder by name
            folder = await self.api.search_folder_by_name(folder_name)
            if not folder:
                return json.dumps({"status": "error", "message": f"Folder '{folder_name}' not found"})
            
            folder_id = folder.get('id')
            result = await self.api.rename_folder(folder_id, new_name)
            return json.dumps({"status": "success", "folder": result}, indent=2)
        except Exception as e:
            logger.error(f"Error renaming folder: {str(e)}")
            return f"Error renaming folder: {str(e)}"

    async def rename_note(self, note_title: str, new_title: str) -> str:
        """Rename a note"""
        try:
            # Search for the note
            search_results = await self.api.search_notes_async(note_title)
            if not search_results:
                return json.dumps({"status": "error", "message": f"Note '{note_title}' not found"})
            
            # Find exact match
            note_id = None
            for note in search_results:
                if note.get('title', '').lower() == note_title.lower():
                    note_id = note.get('id')
                    break
            
            if not note_id:
                return json.dumps({"status": "error", "message": f"Note '{note_title}' not found"})
            
            result = await self.api.rename_document(note_id, new_title)
            return json.dumps({"status": "success", "note": result}, indent=2)
        except Exception as e:
            logger.error(f"Error renaming note: {str(e)}")
            return f"Error renaming note: {str(e)}"

class SearchNotesInput(BaseModel):
    query: str = Field(..., description="The search query to find relevant notes")

class CreateNoteInput(BaseModel):
    title: str = Field(..., description="The title of the note")
    content: str = Field(..., description="The content of the note")
    tags: Optional[List[str]] = Field(None, description="Optional tags for the note")

class UpdateNoteInput(BaseModel):
    note_id: str = Field(..., description="The ID of the note to update")
    content: str = Field(..., description="The new content for the note")
    append: bool = Field(False, description="Whether to append the content to the existing note")

class SummarizeNoteInput(BaseModel):
    note_id: str = Field(..., description="The ID of the note to summarize")

class DeleteNoteInput(BaseModel):
    note_id: str = Field(..., description="The ID of the note to delete")

class CreateFolderInput(BaseModel):
    name: str = Field(..., description="The name of the folder")
    description: str = Field("", description="Optional description for the folder")

class CreateNoteInFolderInput(BaseModel):
    title: str = Field(..., description="The title of the note")
    content: str = Field(..., description="The content of the note")
    folder_name: str = Field(None, description="Optional name of the folder to create the note in")
    tags: Optional[List[str]] = Field(None, description="Optional tags for the note")

class RenameFolderInput(BaseModel):
    folder_name: str = Field(..., description="The current name of the folder")
    new_name: str = Field(..., description="The new name for the folder")

class RenameNoteInput(BaseModel):
    note_title: str = Field(..., description="The current title of the note")
    new_title: str = Field(..., description="The new title for the note")

class SliteAgent:
    """LangChain agent for interacting with Slite with enhanced features"""

    def __init__(self, api_key: str, openai_api_key: str = None):
        """Initialize the SliteAgent with API keys and tools"""
        self.api_key = api_key
        self.openai_api_key = openai_api_key or os.getenv("OPENAI_API_KEY")
        if not self.openai_api_key:
            raise ValueError("OpenAI API key must be provided")
        
        self.api = None
        self.tools = None
        self.memory = ConversationSummaryBufferMemory(
            llm=ChatOpenAI(temperature=0, openai_api_key=self.openai_api_key),
            max_token_limit=500,
            memory_key="chat_history",
            return_messages=True
        )
        
        self.agent_executor = None
        
    async def initialize_agent(self):
        """Initialize the agent with tools and memory"""
        if self.agent_executor:
            return
        
        # Initialize API and tools within async context
        self.api = SliteAPI(self.api_key)
        async with self.api:
            self.tools = SliteTools(self.api)
            
            tools = [
                StructuredTool.from_function(
                    func=self.tools.search_notes,
                    name="SearchNotes",
                    description="Search for notes using a query. Returns up to 5 most relevant results.",
                    args_schema=SearchNotesInput,
                    coroutine=self.tools.search_notes
                ),
                StructuredTool.from_function(
                    func=self.tools.create_note,
                    name="CreateNote",
                    description="Create a new note with title, content, and optional tags.",
                    args_schema=CreateNoteInput,
                    coroutine=self.tools.create_note
                ),
                StructuredTool.from_function(
                    func=self.tools.update_note,
                    name="UpdateNote",
                    description="Update or append to an existing note.",
                    args_schema=UpdateNoteInput,
                    coroutine=self.tools.update_note
                ),
                StructuredTool.from_function(
                    func=self.tools.summarize_note,
                    name="SummarizeNote",
                    description="Generate a summary of a note's content.",
                    args_schema=SummarizeNoteInput,
                    coroutine=self.tools.summarize_note
                ),
                StructuredTool.from_function(
                    func=self.tools.delete_note,
                    name="DeleteNote",
                    description="Delete a note by ID or title.",
                    args_schema=DeleteNoteInput,
                    coroutine=self.tools.delete_note
                ),
                StructuredTool.from_function(
                    func=self.tools.create_folder,
                    name="CreateFolder",
                    description="Create a new folder.",
                    args_schema=CreateFolderInput,
                    coroutine=self.tools.create_folder
                ),
                StructuredTool.from_function(
                    func=self.tools.create_note_in_folder,
                    name="CreateNoteInFolder",
                    description="Create a new note in a specific folder with title, content, and optional tags.",
                    args_schema=CreateNoteInFolderInput,
                    coroutine=self.tools.create_note_in_folder
                ),
                StructuredTool.from_function(
                    func=self.tools.rename_folder,
                    name="RenameFolder",
                    description="Rename a folder.",
                    args_schema=RenameFolderInput,
                    coroutine=self.tools.rename_folder
                ),
                StructuredTool.from_function(
                    func=self.tools.rename_note,
                    name="RenameNote",
                    description="Rename a note.",
                    args_schema=RenameNoteInput,
                    coroutine=self.tools.rename_note
                )
            ]
            
            system_message = """You are a helpful assistant that manages notes and folders in Slite.
            
            Available tools:
            1. SearchNotes:
               - Search for notes using keywords
               Example: {"query": "meeting notes"}
            
            2. UpdateNote:
               - Update or append content to an existing note
               Example: {"note_id": "123", "content": "New content", "append": false}
            
            3. DeleteNote:
               - Delete a note by ID or title
               Example: {"note_id": "123"}
            
            4. CreateFolder:
               - Create a new folder with a given name and optional description
               Example: {"name": "New Folder", "description": "This is a new folder"}
            
            5. CreateNoteInFolder:
               - Create a new note in a specific folder with title, content, and optional tags
               Example: {"title": "New Note", "content": "This is a new note", "folder_name": "Existing Folder", "tags": ["tag1", "tag2"]}
            
            6. RenameFolder:
               - Rename a folder
               Example: {"folder_name": "Old Folder", "new_name": "New Folder"}
            
            7. RenameNote:
               - Rename a note
               Example: {"note_title": "Old Note", "new_title": "New Note"}
            
            When the user asks to:
            1. Create a document in a folder:
               - First check if the folder exists using the folder name
               - If it exists, create the note in that folder
               - If it doesn't exist, create the folder first, then create the note
            
            2. "Add content" or "update" a note:
               - Use UpdateNote with append=true on the existing note
               - If no note ID provided, use the last accessed note
            
            3. "Delete" a note:
               - Use DeleteNote on the specified note
               - If no note ID provided, use the last accessed note
               - Confirm the deletion was successful
            
            4. "Create a new folder":
               - Use CreateFolder to create a new folder with a given name and optional description
               
            5. "Create a new note in a folder":
               - Use CreateNoteInFolder to create a new note in a specific folder
               - Specify the folder name, not the ID
               - The folder will be found or created automatically
            
            6. "Rename a folder":
               - Use RenameFolder to rename a folder
            
            7. "Rename a note":
               - Use RenameNote to rename a note"""
            
            self.agent_executor = initialize_agent(
                tools=tools,
                llm=ChatOpenAI(temperature=0.7, openai_api_key=self.openai_api_key),
                agent=AgentType.STRUCTURED_CHAT_ZERO_SHOT_REACT_DESCRIPTION,
                verbose=True,
                memory=self.memory,
                agent_kwargs={
                    "system_message": system_message,
                }
            )
    
    async def process_query(self, query: str) -> str:
        """Process a user query and return the response"""
        if not self.agent_executor:
            await self.initialize_agent()
            
        try:
            async with self.api:
                response = await self.agent_executor.arun(
                    input=query
                )
                return response
        except Exception as e:
            logger.error(f"Error processing query: {str(e)}")
            logger.error(traceback.format_exc())
            return f"Error processing query: {str(e)}"

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

def run_async(coro):
    """Run an async function in a synchronous context"""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)
