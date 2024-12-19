"""
Custom Exceptions Module

This module defines custom exceptions for handling various API-related errors
in a structured and meaningful way. Each exception type corresponds to a
specific category of API error that might occur during operations.
"""

class APIError(Exception):
    """
    Base exception class for all API-related errors.
    
    Attributes:
        message: Error message describing what went wrong
        status_code: HTTP status code from the API response
        response: Full API response object for debugging
    """
    def __init__(self, message, status_code=None, response=None):
        super().__init__(message)
        self.status_code = status_code
        self.response = response

class RateLimitError(APIError):
    """
    Exception raised when API rate limit is exceeded.
    Typically occurs when too many requests are made in a short time period.
    Usually corresponds to HTTP 429 Too Many Requests.
    """
    pass

class AuthenticationError(APIError):
    """
    Exception raised when API authentication fails.
    This can happen due to invalid API keys or expired tokens.
    Usually corresponds to HTTP 401 Unauthorized or 403 Forbidden.
    """
    pass

class NotFoundError(APIError):
    """
    Exception raised when a requested resource is not found.
    This occurs when trying to access non-existent notes, folders, or documents.
    Usually corresponds to HTTP 404 Not Found.
    """
    pass

class ValidationError(APIError):
    """
    Exception raised when request validation fails.
    This happens when the request data doesn't meet API requirements.
    Usually corresponds to HTTP 400 Bad Request.
    """
    pass

class ServerError(APIError):
    """
    Exception raised when server returns 5xx error.
    Indicates an internal server error or service unavailability.
    Usually corresponds to HTTP 500 Internal Server Error or 503 Service Unavailable.
    """
    pass
