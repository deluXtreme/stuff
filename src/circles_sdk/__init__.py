"""
Circles SDK for Python

A Python SDK for the Circles protocol providing pathfinding, flow matrix creation,
and smart contract interaction capabilities.
"""

__version__ = "0.1.0"
__author__ = "Circles SDK Team"
__email__ = "sdk@circles.org"

# Core configuration and types
from .core.config import CirclesConfig
from .core.types import (
    TransferStep,
    PathfindingResult,
    FindPathParams,
    TokenInfo,
    FlowMatrix,
    FlowEdge,
    Stream,
)

# Token information management
from .core.token_info import (
    TokenType,
    TokenInfoRow,
    TokenInfoCache,
    get_token_info_map_from_path,
    get_wrapped_token_totals_from_path,
    get_expected_unwrapped_token_totals,
)

# Pathfinding client
from .pathfinding.client import PathfinderClient

# Path processing pipeline
from .pathfinding.path_processor import (
    replace_wrapped_tokens,
    shrink_path_values,
    process_path_for_wrapped_tokens,
    assert_no_netted_flow_mismatch,
)

# Transfer functionality
from .transfers.simple import SimpleTransfer, simple_transfer, simple_transfer_to_abi

# Advanced transfer functionality
from .transfers.advanced import (
    AdvancedTransfer,
    advanced_transfer,
    advanced_transfer_with_transactions,
)

# Transaction building
from .transactions.builder import (
    TransactionBuilder,
    TransactionCall,
    UnwrapCall,
    BatchRun,
    build_unwrap_calls,
    build_approval_calls,
    build_transfer_batch,
)

# Flow matrix functionality  
from .core.flow_matrix import (
    create_flow_matrix,
    flow_matrix_to_abi,
    flow_matrix_to_abi_hex,
)

# Exceptions
from .core.exceptions import (
    CirclesSDKError,
    ConfigurationError,
    PathfindingError,
    NoPathFoundError,
    InsufficientBalanceError,
    ValidationError,
    FlowMatrixError,
    RPCError,
    NetworkError,
    TimeoutError,
    RateLimitError,
    TransactionError,
    TokenError,
)

# Main exports for public API
__all__ = [
    # Version info
    "__version__",
    
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
    
    # Clients
    "PathfinderClient",
    
    # Token information
    "TokenType",
    "TokenInfoRow", 
    "TokenInfoCache",
    "get_token_info_map_from_path",
    "get_wrapped_token_totals_from_path",
    "get_expected_unwrapped_token_totals",
    
    # Path processing
    "replace_wrapped_tokens",
    "shrink_path_values",
    "process_path_for_wrapped_tokens",
    "assert_no_netted_flow_mismatch",
    
    # Transfer functionality
    "SimpleTransfer",
    "simple_transfer",
    "simple_transfer_to_abi",
    
    # Advanced transfer functionality
    "AdvancedTransfer",
    "advanced_transfer", 
    "advanced_transfer_with_transactions",
    
    # Transaction building
    "TransactionBuilder",
    "TransactionCall",
    "UnwrapCall", 
    "BatchRun",
    "build_unwrap_calls",
    "build_approval_calls",
    "build_transfer_batch",
    
    # Flow matrix
    "create_flow_matrix",
    "flow_matrix_to_abi",
    "flow_matrix_to_abi_hex",
    
    # Exceptions
    "CirclesSDKError",
    "ConfigurationError", 
    "PathfindingError",
    "NoPathFoundError",
    "InsufficientBalanceError",
    "ValidationError",
    "FlowMatrixError",
    "RPCError",
    "NetworkError",
    "TimeoutError",
    "RateLimitError",
    "TransactionError",
    "TokenError",
]