# API Documentation

## SliteNoteManager

The main class for interacting with the AI-powered note management system.

### Initialization

```python
from langchain_integration import SliteNoteManager

manager = SliteNoteManager(openai_api_key="your-key")  # Key is optional if set in .env
```

### Methods

#### process_meeting_notes

Process and structure meeting notes using AI.

```python
def process_meeting_notes(meeting_notes: str, folder_id: Optional[str] = None) -> str:
    """
    Process meeting notes and create a well-structured note in Slite.
    
    Args:
        meeting_notes (str): Raw meeting notes text
        folder_id (Optional[str]): ID of the folder to store the note in
        
    Returns:
        str: ID of the created note
        
    Raises:
        ValidationError: If input is invalid
        APIError: If API call fails
    """
```

#### organize_content

Organize content into appropriate folders using AI.

```python
def organize_content(content: str, parent_folder_id: Optional[str] = None) -> str:
    """
    Analyze content and create appropriate folder structure.
    
    Args:
        content (str): Content to organize
        parent_folder_id (Optional[str]): Parent folder ID
        
    Returns:
        str: JSON string describing created folder structure
        
    Raises:
        ValidationError: If input is invalid
        APIError: If API call fails
    """
```

#### search_and_update

Search for notes and update them.

```python
def search_and_update(query: str, update_content: str) -> str:
    """
    Search for notes matching query and update them.
    
    Args:
        query (str): Search query
        update_content (str): New content for matching notes
        
    Returns:
        str: List of updated note titles
        
    Raises:
        ValidationError: If input is invalid
        APIError: If API call fails
    """
```

## Models

### MeetingNote

Data model for meeting notes.

```python
class MeetingNote:
    title: str
    content: str
    folder_id: Optional[str]
    project: Optional[str]
    department: Optional[str]
```

### FolderStructure

Data model for folders.

```python
class FolderStructure:
    name: str
    description: Optional[str]
    parent_id: Optional[str]
```

## Error Handling

### Custom Exceptions

```python
class APIError(Exception):
    """Base exception for API errors"""
    pass

class RateLimitError(APIError):
    """Raised when API rate limit is exceeded"""
    pass

class AuthenticationError(APIError):
    """Raised when API authentication fails"""
    pass

class NotFoundError(APIError):
    """Raised when a resource is not found"""
    pass

class ValidationError(APIError):
    """Raised when input validation fails"""
    pass
```

### Example Error Handling

```pythonimport logging
from typing import Dict, Optional
from datetime import datetime
from models import MeetingNote, FolderStructure
from slite_api import SliteAPI
from exceptions import APIError

logger = logging.getLogger(__name__)

class NoteManager:
    def __init__(self, api_key: str):
        self.api = SliteAPI(api_key=api_key)

    def create_note(self, title: str, content: str) -> Dict:
        """Create a new note"""
        try:
            # Create note with content in a single call
            note = MeetingNote(
                title=title,
                content=content,
                created_at=datetime.now().isoformat()
            )
            
            logger.info(f"Creating note with title: {title}")
            return self.api.create_note(note)
            
        except Exception as e:
            logger.error(f"Error creating note: {str(e)}")
            raise

    def create_folder(self, name: str, description: Optional[str] = None) -> Dict:
        """Create a new folder"""
        try:
            folder = FolderStructure(
                name=name,
                description=description
            )
            return self.api.create_folder(folder)
        except Exception as e:
            logger.error(f"Error creating folder: {str(e)}")
            raise
try:
    result = manager.process_meeting_notes(notes)
except ValidationError as e:
    # Handle validation error
    logger.error(f"Validation error: {e}")
except RateLimitError as e:
    # Handle rate limit
    logger.error(f"Rate limit exceeded: {e}")
    time.sleep(60)  # Wait before retrying
except APIError as e:
    # Handle other API errors
    logger.error(f"API error: {e}")
```

## Caching

The system uses TTL (Time To Live) caching for frequently accessed data.

```python
# Cache configuration
note_cache = TTLCache(maxsize=100, ttl=300)  # Cache for 5 minutes
folder_cache = TTLCache(maxsize=50, ttl=600)  # Cache for 10 minutes
```

### Cache Methods

```python
# Get cached data
cached_note = cache.get(f"note_{note_id}")

# Set cache data
cache.set(f"note_{note_id}", note_data, ttl=300)

# Clear cache
cache.clear()
```

## Rate Limiting

The system includes built-in rate limiting to prevent API overload.

```python
rate_limiter = RateLimiter(max_requests=60, time_window=60)  # 60 requests per minute
```

## Logging

Logging is automatically configured and includes:

- API calls
- Error messages
- Cache operations
- Performance metrics

```python
# Log levels
logger.debug("Debug message")
logger.info("Info message")
logger.warning("Warning message")
logger.error("Error message")
```

## Best Practices

1. **Error Handling**
   - Always wrap API calls in try-except blocks
   - Use specific exception types
   - Log errors appropriately

2. **Rate Limiting**
   - Respect API rate limits
   - Use the built-in rate limiter
   - Implement exponential backoff for retries

3. **Caching**
   - Use caching for frequently accessed data
   - Clear cache when data is updated
   - Monitor cache size and TTL

4. **Security**
   - Never hardcode API keys
   - Use environment variables
   - Validate input data

5. **Performance**
   - Use batch operations when possible
   - Monitor API usage
   - Implement proper error recovery
