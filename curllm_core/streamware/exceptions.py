"""
Streamware exceptions
"""


class StreamwareError(Exception):
    """Base exception for Streamware"""
    pass


class ComponentError(StreamwareError):
    """Error in component processing"""
    pass


class ConnectionError(StreamwareError):
    """Error connecting to external services"""
    pass


class ValidationError(StreamwareError):
    """Data validation error"""
    pass


class URIError(StreamwareError):
    """Invalid URI format"""
    pass


class RegistryError(StreamwareError):
    """Component registry error"""
    pass
