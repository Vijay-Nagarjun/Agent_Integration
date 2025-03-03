"""
Data Models Module

This module defines Pydantic models for structured data handling in the application.
These models provide data validation and serialization for meeting notes and folder structures.
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, List
from datetime import datetime

class MeetingNote(BaseModel):
    """
    Pydantic model for meeting notes.
    
    Attributes:
        title (str): The title of the meeting note
        content (str): The main content/body of the meeting note
        created_at (Optional[str]): Timestamp when the note was created
        updated_at (Optional[str]): Timestamp when the note was last updated
        metadata (Optional[Dict]): Additional metadata associated with the note
    """
    title: str
    content: str
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    metadata: Optional[Dict] = None

    def dict(self, *args, **kwargs):
        """
        Convert the model to a dictionary, excluding None values.
        
        Returns:
            dict: Dictionary representation of the model with non-None values
        """
        d = super().dict(*args, **kwargs)
        return {k: v for k, v in d.items() if v is not None}

class FolderStructure(BaseModel):
    """
    Pydantic model for folder structure.
    
    Attributes:
        name (str): The name of the folder
        description (Optional[str]): Optional description of the folder
        parent_id (Optional[str]): ID of the parent folder, if any
    """
    name: str
    description: Optional[str] = None
    parent_id: Optional[str] = None

    def dict(self, *args, **kwargs):
        """
        Convert the model to a dictionary, excluding None values.
        
        Returns:
            dict: Dictionary representation of the model with non-None values
        """
        d = super().dict(*args, **kwargs)
        return {k: v for k, v in d.items() if v is not None}

class TileStatus(BaseModel):
    label: str
    colorHex: str

class TileUpdate(BaseModel):
    """Model for tile updates per API docs"""
    status: Optional[Dict[str, str]] = Field(None, example={
        "label": "104%",
        "colorHex": "#7FFF00"
    })
    title: Optional[str] = None
    content: Optional[str] = None
    url: Optional[str] = None

class CustomContent(BaseModel):
    rootId: str = Field(..., description="Root id of the object")
    id: str = Field(..., description="Unique id of the object")
    title: str = Field(..., description="Title of the object")
    content: str = Field(..., description="Content of the object")
    type: str = Field(..., description="Type (markdown or html)")
    updatedAt: str = Field(..., description="Last update date")
    url: str = Field(..., description="URL of the object")

class NoteCreate(BaseModel):
    """Model for note creation per API docs"""
    title: str
    parentNoteId: Optional[str] = None
    templateId: Optional[str] = None
    markdown: Optional[str] = None
    attributes: List[str] = []

class NoteUpdate(BaseModel):
    title: Optional[str] = None
    markdown: Optional[str] = None
    html: Optional[str] = None
    attributes: Optional[List[str]] = None
