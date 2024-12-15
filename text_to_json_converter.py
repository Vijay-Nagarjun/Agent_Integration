import re
from datetime import datetime
import json

class MeetingNotesConverter:
	def __init__(self):
		self.json_structure = {
			"title": "",
			"metadata": {},
			"sections": []
		}

	def extract_metadata(self, lines):
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
		lines = section_text.strip().split('\n')
		section_title = lines[0].lstrip('123456789. ')
		content = []
		
		current_subtitle = None
		current_details = []
		
		for line in lines[1:]:
			line = line.strip()
			if not line:
				continue
				
			if line.startswith('- '):
				if current_subtitle:
					content.append({
						"subtitle": current_subtitle,
						"details": current_details[0] if len(current_details) == 1 else current_details
					})
				current_subtitle = line.lstrip('- ').split(':')[0].strip()
				current_details = []
			elif line.startswith('     - '):
				current_details.append(line.lstrip('     - ').strip())
			else:
				detail = line.lstrip('     ').strip()
				if detail:
					current_details.append(detail)
		
		if current_subtitle:
			content.append({
				"subtitle": current_subtitle,
				"details": current_details[0] if len(current_details) == 1 else current_details
			})
			
		return {
			"title": section_title,
			"content": content
		}

	def convert(self, text_content):
		lines = text_content.split('\n')
		
		# Extract title
		self.json_structure["title"] = lines[0].replace("Meeting Notes:", "").strip()
		
		# Extract metadata
		self.json_structure["metadata"] = self.extract_metadata(lines)
		
		# Split into sections
		section_pattern = r'\n\s*\d+\.\s+'
		sections = re.split(section_pattern, text_content)[1:]  # Skip the header
		
		# Parse each section
		self.json_structure["sections"] = [
			self.parse_section(section) for section in sections if section.strip()
		]
		
		return self.json_structure

def convert_notes_to_json(input_file, output_file):
	with open(input_file, 'r', encoding='utf-8') as f:
		text_content = f.read()
	
	converter = MeetingNotesConverter()
	json_content = converter.convert(text_content)
	
	with open(output_file, 'w', encoding='utf-8') as f:
		json.dump(json_content, f, indent=4)
	
	return json_content