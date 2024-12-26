"""
Meeting Notes Text to JSON Converter

This module provides functionality to convert structured meeting notes from text format
to a structured JSON format. It handles metadata extraction, section parsing, and
maintains the hierarchical structure of the meeting notes.
"""

import re
import json
import logging
import os
from typing import Dict, List, Optional
from datetime import datetime
import hashlib
from pathlib import Path

logger = logging.getLogger(__name__)

class MeetingNotesConverter:
    """
    Converter class for transforming text-based meeting notes into structured JSON.
    
    The converter handles:
    - Metadata extraction (date, time, attendees, etc.)
    - Section parsing with titles and content
    - Hierarchical content structure with subtitles and details
    """
    
    def __init__(self):
        """
        Initialize the converter with empty JSON structure.
        The structure includes title, metadata, and sections.
        """
        self.json_structure = {
            "title": "",
            "metadata": {},
            "sections": []
        }

    def extract_metadata(self, lines):
        """
        Extract metadata from the first few lines of the meeting notes.
        
        Args:
            lines (list): List of text lines from the meeting notes
            
        Returns:
            dict: Extracted metadata including date, time, attendees count,
                 facilitator, and end time
        """
        metadata = {}
        for line in lines[:6]:  # First few lines contain metadata
            if "Date:" in line:
                metadata["date"] = line.split("Date:")[1].strip()
            elif "Time:" in line:
                metadata["time"] = line.split("Time:")[1].strip()
            elif "Attendees:" in line:
                count = re.search(r'\[(\d+)', line)
                metadata["attendees_count"] = int(count.group(1)) if count else 0
            elif "Facilitator:" in line:
                facilitator = re.search(r'\[(.*?)\]', line)
                metadata["facilitator"] = facilitator.group(1) if facilitator else ""
            elif "Meeting Adjourned at:" in line:
                metadata["end_time"] = line.split("Meeting Adjourned at:")[1].strip()
        return metadata

    def parse_section(self, section_text):
        """
        Parse a single section of the meeting notes.
        
        Args:
            section_text (str): Text content of a single section
            
        Returns:
            dict: Parsed section with title and hierarchical content structure
        """
        lines = section_text.strip().split('\n')
        section_title = lines[0].lstrip('123456789. ').strip('*')
        content = []
        
        current_subsection = None
        current_items = []
        current_subitems = []
        
        for line in lines[1:]:
            line = line.strip()
            if not line or line == "---":
                continue
                
            # Check for subsection (marked with #### or **)
            if line.startswith('####') or (line.startswith('**') and line.endswith('**')):
                # Save previous subsection if exists
                if current_subsection:
                    content.append({
                        "subtitle": current_subsection,
                        "items": current_items
                    })
                current_subsection = line.strip('# *')
                current_items = []
                current_subitems = []
            # Check for main items (marked with -)
            elif line.startswith('- '):
                if current_subitems:
                    current_items.append({
                        "text": current_items[-1]["text"] if current_items else "",
                        "subitems": current_subitems
                    })
                    current_subitems = []
                current_items.append({"text": line[2:].strip()})
            
            # Check for subitems (indented with spaces and starting with -)
            elif line.startswith('     - '):
                current_subitems.append(line.lstrip(' -'))
            
            # Regular text (might be part of previous item)
            elif line and current_items:
                if not line.startswith('     '):
                    current_items[-1]["text"] = current_items[-1]["text"] + " " + line
        
        # Add the last subsection
        if current_subsection:
            if current_subitems:
                current_items.append({
                    "text": current_items[-1]["text"] if current_items else "",
                    "subitems": current_subitems
                })
            content.append({
                "subtitle": current_subsection,
                "items": current_items
            })
            
        return {
            "title": section_title,
            "content": content
        }

    def convert(self, text_content):
        """
        Convert the entire meeting notes text to JSON format.
        
        Args:
            text_content (str): Full text content of the meeting notes
            
        Returns:
            dict: Structured JSON representation of the meeting notes
        """
        lines = text_content.split('\n')
        
        # Extract title from the first line
        self.json_structure["title"] = lines[0].replace("Meeting Notes:", "").strip()
        
        # Extract metadata
        metadata = {}
        for line in lines[1:10]:  # Look at first few lines for metadata
            if "Date:" in line:
                metadata["date"] = line.split("Date:")[1].strip().strip('*')
            elif "Topic:" in line:
                metadata["topic"] = line.split("Topic:")[1].strip().strip('*')
            elif "Attendees:" in line:
                try:
                    metadata["attendees_count"] = int(line.split("Attendees:")[1].strip())
                except:
                    metadata["attendees_count"] = 0
        
        self.json_structure["metadata"] = metadata
        
        # Split content into sections using ### markers
        sections = []
        current_section = []
        
        for line in lines[lines.index("---")+1:]:
            if line.startswith('### '):
                if current_section:
                    sections.append('\n'.join(current_section))
                current_section = [line]
            else:
                current_section.append(line)
        
        if current_section:
            sections.append('\n'.join(current_section))
        
        # Parse each section
        self.json_structure["sections"] = [
            self.parse_section(section) for section in sections if section.strip()
        ]
        
        return self.json_structure

class TextToJsonConverter:
    """Optimized converter for text to JSON conversion with incremental updates"""
    
    def __init__(self, buffer_size: int = 8192):
        self.buffer_size = buffer_size
        self._cache_dir = Path(".cache")
        self._cache_dir.mkdir(exist_ok=True)
        
    def _get_file_hash(self, file_path: str) -> str:
        """Get SHA-256 hash of file contents"""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
        
    def _get_cache_path(self, file_path: str) -> Path:
        """Get cache file path for source file"""
        file_hash = self._get_file_hash(file_path)
        return self._cache_dir / f"{Path(file_path).stem}_{file_hash[:8]}.json"
        
    def _parse_meeting_notes(self, content: str) -> List[Dict]:
        """Parse meeting notes content into structured format"""
        notes = []
        current_note = {}
        
        for line in content.split('\n'):
            line = line.strip()
            
            if line.startswith('Meeting Notes:'):
                if current_note:
                    notes.append(current_note)
                current_note = {
                    'title': line[len('Meeting Notes:'):].strip(),
                    'content': [],
                    'metadata': {}
                }
            elif line.startswith('Date:') and current_note:
                try:
                    date_str = line[len('Date:'):].strip()
                    current_note['metadata']['date'] = datetime.strptime(
                        date_str, '%Y-%m-%d'
                    ).isoformat()
                except ValueError:
                    logger.warning(f"Invalid date format: {date_str}")
                    current_note['metadata']['date'] = None
            elif line.startswith('Participants:') and current_note:
                participants = line[len('Participants:'):].strip()
                current_note['metadata']['participants'] = [
                    p.strip() for p in participants.split(',')
                ]
            elif line and current_note:
                current_note['content'].append(line)
                
        if current_note:
            notes.append(current_note)
            
        return notes
        
    def convert_notes_to_json(
        self,
        input_file: str,
        output_file: str,
        force_update: bool = False
    ) -> None:
        """
        Convert meeting notes from text to JSON format with caching
        
        Args:
            input_file: Path to input text file
            output_file: Path to output JSON file
            force_update: Force update even if cache exists
        """
        try:
            cache_path = self._get_cache_path(input_file)
            
            # Check if cached version exists and is up to date
            if not force_update and cache_path.exists():
                logger.info("Using cached conversion")
                with open(cache_path, 'rb') as cache_file:
                    with open(output_file, 'wb') as out_file:
                        # Use buffered copy
                        while True:
                            buf = cache_file.read(self.buffer_size)
                            if not buf:
                                break
                            out_file.write(buf)
                return
                
            # Read and parse input file
            with open(input_file, 'r', buffering=self.buffer_size) as f:
                content = f.read()
                
            notes = self._parse_meeting_notes(content)
            
            # Write to both cache and output
            json_content = json.dumps(notes, indent=2)
            
            with open(cache_path, 'w') as cache_file:
                cache_file.write(json_content)
                
            with open(output_file, 'w') as out_file:
                out_file.write(json_content)
                
            logger.info(f"Successfully converted {input_file} to {output_file}")
            
        except Exception as e:
            logger.error(f"Error converting notes: {str(e)}")
            raise

def convert_notes_to_json(input_file: str, output_file: str) -> None:
    """
    Convenience function to convert notes using default settings
    """
    converter = TextToJsonConverter()
    converter.convert_notes_to_json(input_file, output_file)

def convert_notes_to_json_original(input_file: str, output_file: str) -> None:
    """
    Convert meeting notes from text file to JSON file.
    
    Args:
        input_file (str): Path to the input text file
        output_file (str): Path where the JSON output will be saved
        
    Returns:
        dict: The converted JSON content
    """
    with open(input_file, 'r', encoding='utf-8') as f:
        text_content = f.read()
    
    converter = MeetingNotesConverter()
    json_content = converter.convert(text_content)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(json_content, f, indent=4)
    
    return json_content

# Script entry point
if __name__ == "__main__":
    input_file = 'meeting_notes.txt'
    output_file = 'meeting_notes.json'
    convert_notes_to_json(input_file, output_file)