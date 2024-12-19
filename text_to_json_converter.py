"""
Meeting Notes Text to JSON Converter

This module provides functionality to convert structured meeting notes from text format
to a structured JSON format. It handles metadata extraction, section parsing, and
maintains the hierarchical structure of the meeting notes.
"""

import re
import json

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
        self.json_structure["sections"] = [
            self.parse_section(section) for section in sections if section.strip()
        ]
        
        return self.json_structure

def convert_notes_to_json(input_file, output_file):
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