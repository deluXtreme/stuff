"""
Core module for Circles SDK.

This module contains the fundamental types, configuration, exceptions,
and flow matrix functionality that form the foundation of the SDK.
"""

from .config import CirclesConfig
from .types import (
    TransferStep,
    PathfindingResult,
    FindPathParams,
    TokenInfo,
    FlowMatrix,
    FlowEdge,
    Stream,
    RPCRequest,
    RPCResponse,
    RPCError,
)
from .exceptions import (
    CirclesSDKError,
    ConfigurationError,
    PathfindingError,
    NoPathFoundError,
    InsufficientBalanceError,
    ValidationError,
    FlowMatrixError,
    RPCError as RPCException,
    NetworkError,
    TimeoutError,
    RateLimitError,
    TransactionError,
    TokenError,
)
from .flow_matrix import (
    create_flow_matrix,
    flow_matrix_to_abi,
    flow_matrix_to_abi_hex,
    pack_coordinates,
    transform_to_flow_vertices,
)
from .token_info import (
    TokenType,
    TokenInfoRow,
    TokenInfoCache,
    get_token_info_map_from_path,
    get_wrapped_token_totals_from_path,
    get_expected_unwrapped_token_totals,
)

__all__ = [
    # Configuration
    "CirclesConfig",
    
    # Core types
    "TransferStep",
    "PathfindingResult",
    "FindPathParams", 
    "TokenInfo",
    "FlowMatrix",
    "FlowEdge",
    "Stream",
    "RPCRequest",
    "RPCResponse",
    "RPCError",
    
    # Exceptions
    "CirclesSDKError",
    "ConfigurationError",
    "PathfindingError",
    "NoPathFoundError", 
    "InsufficientBalanceError",
    "ValidationError",
    "FlowMatrixError",
    "RPCException",
    "NetworkError",
    "TimeoutError",
    "RateLimitError",
    "TransactionError",
    "TokenError",
    
    # Flow matrix functionality
    "create_flow_matrix",
    "flow_matrix_to_abi",
    "flow_matrix_to_abi_hex",
    "pack_coordinates",
    "transform_to_flow_vertices",
    
    # Token information
    "TokenType",
    "TokenInfoRow",
    "TokenInfoCache",
    "get_token_info_map_from_path",
    "get_wrapped_token_totals_from_path",
    "get_expected_unwrapped_token_totals",
]