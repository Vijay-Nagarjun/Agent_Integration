from pydantic import BaseModel
from typing import Optional, Dict
from datetime import datetime

class MeetingNote(BaseModel):
    """Model for meeting notes"""
    title: str
    content: str
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    metadata: Optional[Dict] = None

    def dict(self, *args, **kwargs):
        # Only include non-None values
        d = super().dict(*args, **kwargs)
        return {k: v for k, v in d.items() if v is not None}

class FolderStructure(BaseModel):
    """Model for folder structure"""
    name: str
    description: Optional[str] = None
    parent_id: Optional[str] = None

    def dict(self, *args, **kwargs):
        # Only include non-None values
        d = super().dict(*args, **kwargs)
        return {k: v for k, v in d.items() if v is not None}
