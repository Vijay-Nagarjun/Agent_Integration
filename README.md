# Slite Meeting Notes Integration Agent

An AI-powered integration solution for automating Slite meeting notes management and documentation workflows. This project combines the power of LangChain and OpenAI to provide intelligent note processing, organization, and search capabilities.

## Features

- **AI-Powered Note Processing**
  - Automatic meeting notes structuring
  - Smart content organization
  - Intelligent search and updates

- **Robust Note Management**
  - Create, read, update, and delete notes
  - Hierarchical folder organization
  - Advanced search capabilities

- **Performance Optimized**
  - Caching system for frequently accessed data
  - Rate limiting to prevent API overload
  - Retry mechanisms for reliability

- **Enterprise-Ready**
  - Comprehensive error handling
  - Detailed logging
  - Secure credential management

## Installation

1. Clone the repository:
```bash
git clone [repository-url]
cd Agent_Integration
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up environment variables:
Create a `.env` file in the root directory with:
```env
SLITE_API_KEY="your-slite-api-key"
OPENAI_API_KEY="your-openai-api-key"
```

## Quick Start

1. **Initialize the Integration**
```python
from langchain_integration import SliteNoteManager
from models import MeetingNote

# Initialize the manager
manager = SliteNoteManager()
```

2. **Process Meeting Notes**
```python
# Create a meeting note
meeting_notes = """
Project Kickoff Meeting
Date: 2024-01-15

Discussion Points:
1. Project scope defined
2. Timeline set for Q1 delivery
3. Resource requirements identified

Action Items:
- Create technical design doc
- Prepare UI mockups
- Finalize requirements
"""

# Process and create the note
result = manager.process_meeting_notes(meeting_notes)
print(f"Created note: {result}")
```

3. **Organize Content**
```python
# Organize content into folders
content = """
Technical Documentation:
- System Architecture
- API Documentation
- Database Schema

Project Management:
- Sprint Planning
- Team Updates
- Risk Register
"""

result = manager.organize_content(content)
print(f"Created folder structure: {result}")
```

4. **Search and Update**
```python
# Search for notes and update them
query = "Project Kickoff"
update_content = """
Updated project timeline:
- Phase 1: Requirements (2 weeks)
- Phase 2: Development (6 weeks)
- Phase 3: Testing (2 weeks)
- Phase 4: Deployment (1 week)
"""

result = manager.search_and_update(query, update_content)
print(f"Updated notes: {result}")
```

## Project Structure

- `langchain_integration.py`: Main integration with LangChain and AI features
- `slite_api.py`: Core Slite API integration
- `note_manager.py`: Note and folder management functionality
- `models.py`: Data models and structures
- `utils.py`: Utility functions for error handling, caching, and logging
- `test_langchain_integration.py`: Test suite

## Error Handling

The project includes comprehensive error handling:

```python
try:
    result = manager.process_meeting_notes(notes)
except ValidationError as e:
    print(f"Invalid input: {e}")
except APIError as e:
    print(f"API error: {e}")
except RateLimitError as e:
    print(f"Rate limit exceeded: {e}")
```

## Caching

The system automatically caches frequently accessed data:

```python
# Get a note (will use cache if available)
note = manager.get_note("note-id")

# Clear cache if needed
manager.clear_cache()
```

## Logging

Logs are automatically generated in `slite_integration.log`:

```python
# Logs will include:
# - API calls
# - Error messages
# - Cache operations
# - Performance metrics
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License

[License Type] - See LICENSE file for details

## Support

For support, please:
1. Check the documentation
2. Review existing issues
3. Create a new issue if needed

## Roadmap

- [ ] Advanced semantic search
- [ ] Multi-language support
- [ ] Integration with more AI models
- [ ] Real-time collaboration features
- [ ] Enhanced analytics and reporting
