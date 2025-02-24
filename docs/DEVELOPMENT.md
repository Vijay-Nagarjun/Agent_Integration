# Development Guide

## Setup Development Environment

1. **Python Environment**
   ```bash
   # Create virtual environment
   python -m venv venv
   
   # Activate virtual environment
   # Windows
   .\venv\Scripts\activate
   # Unix/MacOS
   source venv/bin/activate
   
   # Install dependencies
   pip install -r requirements.txt
   ```

2. **Environment Variables**
   Create a `.env` file in the root directory:
   ```env
   SLITE_API_KEY="your-slite-api-key"
   OPENAI_API_KEY="your-openai-api-key"
   LOG_LEVEL="DEBUG"  # Optional, defaults to INFO
   CACHE_TTL="300"    # Optional, defaults to 300 seconds
   ```

## Project Structure

```
Agent_Integration/
├── langchain_integration.py  # Main LangChain integration
├── slite_api.py             # Slite API client
├── note_manager.py          # Note management logic
├── models.py               # Data models
├── utils.py               # Utilities and helpers
├── requirements.txt       # Project dependencies
├── .env                  # Environment variables
├── tests/                # Test files
│   ├── __init__.py
│   ├── test_langchain_integration.py
│   ├── test_slite_api.py
│   └── test_note_manager.py
└── docs/                 # Documentation
    ├── API.md
    └── DEVELOPMENT.md
```

## Code Style

This project follows PEP 8 style guidelines. Key points:

1. **Naming Conventions**
   - Classes: PascalCase
   - Functions/Variables: snake_case
   - Constants: UPPER_CASE
   - Private methods/variables: _leading_underscore

2. **Documentation**
   - Use docstrings for all public methods
   - Include type hints
   - Document exceptions

Example:
```python
def process_meeting_notes(
    self,
    content: str,
    folder_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Process meeting notes using AI and create in Slite.

    Args:
        content: Raw meeting notes content
        folder_id: Optional folder ID for note storage

    Returns:
        Dict containing note details

    Raises:
        ValidationError: If content is invalid
        APIError: If API request fails
    """
```

## Testing

1. **Running Tests**
   ```bash
   # Run all tests
   python -m pytest
   
   # Run specific test file
   python -m pytest tests/test_langchain_integration.py
   
   # Run with coverage
   python -m pytest --cov=.
   ```

2. **Writing Tests**
   ```python
   def test_process_meeting_notes():
       manager = SliteNoteManager()
       content = "Test meeting notes"
       
       # Test successful case
       result = manager.process_meeting_notes(content)
       assert result["status"] == "success"
       
       # Test error case
       with pytest.raises(ValidationError):
           manager.process_meeting_notes("")
   ```

## Error Handling

1. **Custom Exceptions**
   - Use custom exceptions for specific error cases
   - Include relevant error details
   - Log appropriately

2. **Example**
   ```python
   try:
       result = api.create_note(content)
   except APIError as e:
       logger.error(f"API error: {e}")
       raise
   except ValidationError as e:
       logger.warning(f"Validation error: {e}")
       raise
   ```

## Logging

1. **Configuration**
   ```python
   import logging
   
   logging.basicConfig(
       level=logging.INFO,
       format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
       filename='slite_integration.log'
   )
   ```

2. **Usage**
   ```python
   logger = logging.getLogger(__name__)
   
   logger.debug("Debug message")
   logger.info("Info message")
   logger.warning("Warning message")
   logger.error("Error message")
   ```

## Performance Considerations

1. **Caching**
   - Use caching for frequently accessed data
   - Clear cache when data is updated
   - Monitor cache size

2. **Rate Limiting**
   - Respect API rate limits
   - Implement exponential backoff
   - Use batch operations when possible

## Security Best Practices

1. **API Keys**
   - Never commit API keys
   - Use environment variables
   - Rotate keys regularly

2. **Input Validation**
   - Validate all input data
   - Sanitize user input
   - Use type hints and Pydantic models

## Deployment

1. **Prerequisites**
   - Python 3.8+
   - Virtual environment
   - Required API keys

2. **Steps**
   ```bash
   # Clone repository
   git clone [repository-url]
   
   # Setup environment
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   
   # Configure environment
   cp .env.example .env
   # Edit .env with your API keys
   
   # Run tests
   python -m pytest
   ```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make changes
4. Add tests
5. Submit pull request

## Troubleshooting

Common issues and solutions:

1. **API Rate Limits**
   - Implement exponential backoff
   - Use caching
   - Monitor API usage

2. **Authentication Errors**
   - Check API key validity
   - Verify environment variables
   - Check API permissions

3. **Performance Issues**
   - Monitor cache usage
   - Use batch operations
   - Optimize API calls
