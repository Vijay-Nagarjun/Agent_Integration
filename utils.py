import logging
import time
from functools import wraps
from typing import Any, Callable, Dict, Optional
import json
from datetime import datetime
import os
from cachetools import TTLCache
import random

# Configure logging
def setup_logging(log_file: str = 'slite_integration.log'):
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger('slite_integration')

logger = setup_logging()

# Cache configuration
note_cache = TTLCache(maxsize=100, ttl=300)  # Cache for 5 minutes
folder_cache = TTLCache(maxsize=50, ttl=600)  # Cache for 10 minutes

class RateLimiter:
    def __init__(self, max_requests: int = 60, time_window: int = 60):
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests = []

    def can_make_request(self) -> bool:
        current_time = time.time()
        # Remove old requests
        self.requests = [req_time for req_time in self.requests 
                        if current_time - req_time < self.time_window]
        
        if len(self.requests) < self.max_requests:
            self.requests.append(current_time)
            return True
        return False

    def wait_for_next_slot(self):
        while not self.can_make_request():
            time.sleep(1)

rate_limiter = RateLimiter()

def retry_with_backoff(retries: int = 3, backoff_in_seconds: int = 1):
    """Retry decorator with exponential backoff"""
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
    """Simple file-based cache"""
    def __init__(self, cache_file: str):
        self.cache_file = cache_file
        self._cache = self._load_cache()

    def _load_cache(self) -> dict:
        """Load cache from file"""
        try:
            with open(self.cache_file, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def _save_cache(self):
        """Save cache to file"""
        with open(self.cache_file, 'w') as f:
            json.dump(self._cache, f)

    def get(self, key: str) -> Optional[str]:
        """Get value from cache"""
        return self._cache.get(key)

    def set(self, key: str, value: str):
        """Set value in cache"""
        self._cache[key] = value
        self._save_cache()

    def clear(self):
        """Clear the cache"""
        self._cache = {}
        self._save_cache()

class APIError(Exception):
    """Base exception for API errors"""
    def __init__(self, message: str, status_code: Optional[int] = None):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)

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
