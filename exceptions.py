class APIError(Exception):
    """Base exception for API related errors"""
    def __init__(self, message, status_code=None, response=None):
        super().__init__(message)
        self.status_code = status_code
        self.response = response

class RateLimitError(APIError):
    """Exception raised when API rate limit is exceeded"""
    pass

class AuthenticationError(APIError):
    """Exception raised when API authentication fails"""
    pass

class NotFoundError(APIError):
    """Exception raised when a resource is not found"""
    pass

class ValidationError(APIError):
    """Exception raised when request validation fails"""
    pass

class ServerError(APIError):
    """Exception raised when server returns 5xx error"""
    pass
