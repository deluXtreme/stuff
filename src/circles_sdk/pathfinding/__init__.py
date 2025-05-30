"""
Pathfinding module for Circles SDK.

This module provides pathfinding capabilities for the Circles protocol,
including RPC client for the pathfinder service and related utilities.
"""

from .client import PathfinderClient
from .path_processor import (
    replace_wrapped_tokens,
    shrink_path_values,
    process_path_for_wrapped_tokens,
    assert_no_netted_flow_mismatch,
)

__all__ = [
    "PathfinderClient",
    "replace_wrapped_tokens",
    "shrink_path_values", 
    "process_path_for_wrapped_tokens",
    "assert_no_netted_flow_mismatch",
]