"""Custom exceptions for the Circles SDK."""

from typing import Optional, Any, Dict


class CirclesSDKError(Exception):
    """Base exception for all Circles SDK errors."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}


class ConfigurationError(CirclesSDKError):
    """Configuration is invalid or missing."""
    pass


class PathfindingError(CirclesSDKError):
    """Pathfinding operation failed."""
    
    def __init__(
        self,
        message: str,
        from_addr: Optional[str] = None,
        to_addr: Optional[str] = None,
        amount: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, details)
        self.from_addr = from_addr
        self.to_addr = to_addr
        self.amount = amount


class InsufficientBalanceError(PathfindingError):
    """Insufficient balance for the requested transfer."""
    pass


class NoPathFoundError(PathfindingError):
    """No path could be found between source and destination."""
    pass


class RPCError(CirclesSDKError):
    """RPC call failed."""
    
    def __init__(
        self,
        message: str,
        method: Optional[str] = None,
        status_code: Optional[int] = None,
        response_data: Optional[Any] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, details)
        self.method = method
        self.status_code = status_code
        self.response_data = response_data


class NetworkError(CirclesSDKError):
    """Network connectivity issues."""
    pass


class ValidationError(CirclesSDKError):
    """Input validation failed."""
    
    def __init__(
        self,
        message: str,
        field: Optional[str] = None,
        value: Optional[Any] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, details)
        self.field = field
        self.value = value


class FlowMatrixError(CirclesSDKError):
    """Flow matrix creation or validation failed."""
    pass


class TransactionError(CirclesSDKError):
    """Transaction building or execution failed."""
    
    def __init__(
        self,
        message: str,
        tx_hash: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, details)
        self.tx_hash = tx_hash


class TokenError(CirclesSDKError):
    """Token-related operations failed."""
    
    def __init__(
        self,
        message: str,
        token_address: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, details)
        self.token_address = token_address


class TimeoutError(CirclesSDKError):
    """Operation timed out."""
    
    def __init__(
        self,
        message: str,
        timeout_duration: Optional[float] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, details)
        self.timeout_duration = timeout_duration


class RateLimitError(RPCError):
    """Rate limit exceeded."""
    
    def __init__(
        self,
        message: str = "Rate limit exceeded",
        retry_after: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, details=details)
        self.retry_after = retry_after