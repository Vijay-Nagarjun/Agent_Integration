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
        
    def _normalize_text(self, text: str) -> str:
        """
        Normalize text by converting special characters to their standard ASCII equivalents
        """
        # Debug: Print the hex values of each character in the text
        for char in text:
            if ord(char) > 127:  # Only print non-ASCII characters
                logger.debug(f"Found special character: {char} (hex: {hex(ord(char))})")
        
        # More comprehensive character mapping
        char_map = {
            '\u2013': '-',  # en-dash
            '\u2014': '-',  # em-dash
            '\u2015': '-',  # horizontal bar
            '\u2212': '-',  # minus sign
            '\u2010': '-',  # hyphen
            '\u2011': '-',  # non-breaking hyphen
            '\u2012': '-',  # figure dash
            '\u2043': '-',  # hyphen bullet
            '\u002D': '-',  # hyphen-minus (standard ASCII hyphen)
            '\u00AD': '-',  # soft hyphen
            '\u2212': '-',  # minus sign
            '\u2796': '-',  # heavy minus sign
            # Add more variations of dashes
            '–': '-',       # en-dash (direct character)
            '—': '-',       # em-dash (direct character)
            '―': '-',       # horizontal bar (direct character)
            '‒': '-',       # figure dash (direct character)
            '‐': '-',       # hyphen (direct character)
            '‑': '-',       # non-breaking hyphen (direct character)
            # Other special characters
            '"': '"',       # smart quote
            '"': '"',       # smart quote
            ''': "'",       # smart apostrophe
            ''': "'",       # smart apostrophe
            '•': '*',       # bullet
            '…': '...',     # ellipsis
            '\u00a0': ' ',  # non-breaking space
            '\u200b': '',   # zero-width space
            '\u2022': '*',  # bullet point
            '\u2026': '...', # horizontal ellipsis
            '\u2028': '\n', # line separator
            '\u2029': '\n\n', # paragraph separator
        }
        
        # First pass: normalize using explicit unicode values
        for special, normal in char_map.items():
            if special in text:
                logger.debug(f"Replacing character: {special} (hex: {hex(ord(special))})")
                text = text.replace(special, normal)
        
        # Second pass: handle any remaining special dashes by their unicode value
        normalized = ''
        for char in text:
            if 0x2010 <= ord(char) <= 0x2015:  # Range of Unicode dashes
                logger.debug(f"Converting dash character: {char} (hex: {hex(ord(char))})")
                normalized += '-'
            else:
                normalized += char
        
        return normalized

    def convert_notes_to_json(
            self,
            input_file: str,
            output_file: str,
            force_update: bool = False
        ):
        """
        Convert meeting notes from text to JSON format with caching
        
        Args:
            input_file: Path to input text file
            output_file: Path to output JSON file
            force_update: Force update even if cache exists
        """
        try:
            # Set logging to INFO level to reduce debug messages
            logging.basicConfig(
                level=logging.INFO,
                format='%(message)s'  # Only show the message without debug info
            )
            
            logger.info(f"Converting {input_file} to JSON format...")
            
            # Read the input file with UTF-8 encoding
            with open(input_file, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Pre-process content to handle special characters
            content = content.encode('utf-8').decode('utf-8')
            
            # Replace problematic characters directly
            content = content.replace('\u2013', '-')  # en-dash
            content = content.replace('\u2014', '-')  # em-dash
            content = content.replace('–', '-')       # en-dash (direct)
            content = content.replace('—', '-')       # em-dash (direct)
            
            # Parse the content
            json_content = self._parse_meeting_notes(content)
            
            # Write to output file with UTF-8 encoding, ensuring proper character handling
            with open(output_file, 'w', encoding='utf-8', newline='\n') as f:
                json.dump(json_content, f, indent=2, ensure_ascii=False)
                
            logger.info(f"Successfully converted to {output_file}")
            return json_content
            
        except Exception as e:
            logger.error(f"Error converting notes to JSON: {str(e)}")
            raise

    def _parse_meeting_notes(self, content: str) -> Dict:
        """Parse meeting notes content into structured format"""
        # Normalize the entire content first
        content = self._normalize_text(content)
        
        # Split content into lines and process
        lines = content.strip().split('\n')
        
        # Initialize structure
        structure = {
            "timestamp": datetime.now().timestamp(),
            "metadata": {},
            "sections": []
        }
        
        # Extract metadata
        metadata = {}
        attendees = []
        current_section = None
        in_attendees = False
        
        for line in lines:
            # Normalize each line individually as well
            line = self._normalize_text(line.strip())
            if not line or line == "---":
                continue
                
            if "**Date**:" in line:
                metadata["date"] = line.split(":", 1)[1].strip()
            elif "**Time**:" in line:
                time_str = line.split(":", 1)[1].strip()
                metadata["time"] = time_str
            elif "**Location**:" in line:
                metadata["location"] = line.split(":", 1)[1].strip()
            elif "**Attendees**:" in line:
                in_attendees = True
            elif in_attendees and line.startswith("-"):
                attendees.append(line[1:].strip())
            elif line.startswith("**") and not line.startswith("**Attendees"):
                in_attendees = False
                
                # Check if this is a new section
                if line.endswith("**"):
                    if current_section:
                        structure["sections"].append(current_section)
                    current_section = {
                        "title": line.strip("*").strip(),
                        "points": []
                    }
            elif current_section and line.startswith("-"):
                # Add point to current section
                point = line[1:].strip()
                current_section["points"].append(point)
            elif "Next Meeting:" in line:
                next_meeting = line.split(":", 1)[1].strip()
                metadata["next_meeting"] = next_meeting
                
        # Add the last section if exists
        if current_section:
            structure["sections"].append(current_section)
            
        metadata["attendees"] = attendees
        structure["metadata"] = metadata
        
        return structure

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
    
    # Force update to see debug output
    converter = TextToJsonConverter()
    converter.convert_notes_to_json(input_file, output_file, force_update=True)