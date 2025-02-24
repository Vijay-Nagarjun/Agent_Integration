"""
Utilities Module

This module provides various utility functions and classes for the Slite integration:
- Logging setup
- Rate limiting
- Caching
- Retry mechanisms
- Custom exceptions

The utilities here support the main application by providing common functionality
and error handling mechanisms.
"""

import logging
import time
from functools import wraps
from typing import Any, Callable, Dict, Optional
import json
from datetime import datetime
import os
from cachetools import TTLCache
import random

def setup_logging(log_file: str = 'slite_integration.log'):
    """
    Configure logging for the application.
    
    Args:
        log_file (str): Path to the log file
        
    Returns:
        Logger: Configured logger instance
    """
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger('slite_integration')

# Initialize logger
logger = setup_logging()

# Configure caches with time-to-live (TTL)
note_cache = TTLCache(maxsize=100, ttl=300)  # Cache for 5 minutes
folder_cache = TTLCache(maxsize=50, ttl=600)  # Cache for 10 minutes

class RateLimiter:
    """
    Rate limiter to prevent API throttling.
    Implements a sliding window rate limiting algorithm.
    """
    
    def __init__(self, max_requests: int = 60, time_window: int = 60):
        """
        Initialize rate limiter.
        
        Args:
            max_requests (int): Maximum number of requests allowed in the time window
            time_window (int): Time window in seconds
        """
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests = []

    def can_make_request(self) -> bool:
        """
        Check if a new request can be made within rate limits.
        
        Returns:
            bool: True if request is allowed, False otherwise
        """
        current_time = time.time()
        # Remove old requests outside the time window
        self.requests = [req_time for req_time in self.requests 
                        if current_time - req_time < self.time_window]
        
        if len(self.requests) < self.max_requests:
            self.requests.append(current_time)
            return True
        return False

    def wait_for_next_slot(self):
        """Wait until a request slot becomes available."""
        while not self.can_make_request():
            time.sleep(1)

# Initialize global rate limiter
rate_limiter = RateLimiter()

def retry_with_backoff(retries: int = 3, backoff_in_seconds: int = 1):
    """
    Decorator for retrying functions with exponential backoff.
    
    Args:
        retries (int): Maximum number of retry attempts
        backoff_in_seconds (int): Initial backoff time in seconds
        
    Returns:
        Callable: Decorated function with retry logic
    """
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            x = 0
            while True:
                try:
                    rate_limiter.wait_for_next_slot()
                    return func(*args, **kwargs)
                except Exception as e:
                    if x == retries:
                        logger.error(f"Failed after {retries} retries: {str(e)}")
                        raise
                    else:
                        wait = (backoff_in_seconds * 2 ** x + 
                               random.uniform(0, 1))
                        logger.warning(f"Attempt {x+1} failed: {str(e)}. "
                                     f"Retrying in {wait:.1f} seconds...")
                        time.sleep(wait)
                        x += 1
        return wrapper
    return decorator

class Cache:
    """
    Simple file-based cache implementation for storing key-value pairs.
    Provides persistent storage between application runs.
    """
    
    def __init__(self, cache_file: str):
        """
        Initialize cache with specified file.
        
        Args:
            cache_file (str): Path to the cache file
        """
        self.cache_file = cache_file
        self._cache = self._load_cache()

    def _load_cache(self) -> dict:
        """
        Load cache data from file.
        
        Returns:
            dict: Loaded cache data or empty dict if file doesn't exist
        """
        try:
            with open(self.cache_file, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def _save_cache(self):
        """Save current cache data to file."""
        with open(self.cache_file, 'w') as f:
            json.dump(self._cache, f)

    def get(self, key: str) -> Optional[str]:
        """
        Retrieve value from cache.
        
        Args:
            key (str): Cache key
            
        Returns:
            Optional[str]: Cached value or None if not found
        """
        return self._cache.get(key)

    def set(self, key: str, value: str):
        """
        Store value in cache.
        
        Args:
            key (str): Cache key
            value (str): Value to store
        """
        self._cache[key] = value
        self._save_cache()

    def clear(self):
        """Clear all cached data."""
        self._cache = {}
        self._save_cache()

class APIError(Exception):
    """
    Base exception class for API-related errors.
    Provides status code support for HTTP errors.
    """
    def __init__(self, message: str, status_code: Optional[int] = None):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)

class RateLimitError(APIError):
    """Raised when API rate limit is exceeded."""
    pass

class AuthenticationError(APIError):
    """Raised when API authentication fails."""
    pass

class NotFoundError(APIError):
    """Raised when a resource is not found."""
    pass

class ValidationError(APIError):
    """Raised when input validation fails."""
    pass
