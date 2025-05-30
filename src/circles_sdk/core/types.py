"""Core type definitions for the Circles SDK."""

from dataclasses import dataclass
from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel, Field, validator


class TransferStep(BaseModel):
    """Represents a single transfer step in a payment flow."""
    from_address: str
    to_address: str
    token_owner: str
    value: str
    
    class Config:
        frozen = True

    @validator('from_address', 'to_address', 'token_owner')
    def validate_address(cls, v):
        if not isinstance(v, str) or not v.startswith('0x') or len(v) != 42:
            raise ValueError(f'Invalid Ethereum address: {v}')
        return v.lower()

    @validator('value')
    def validate_value(cls, v):
        try:
            int(v)
        except ValueError:
            raise ValueError(f'Value must be a valid integer string: {v}')
        return v


class PathfindingResult(BaseModel):
    """Result from pathfinder RPC call."""
    max_flow: str
    transfers: List[TransferStep]
    
    class Config:
        frozen = True

    @validator('max_flow')
    def validate_max_flow(cls, v):
        try:
            int(v)
        except ValueError:
            raise ValueError(f'max_flow must be a valid integer string: {v}')
        return v


class TokenInfo(BaseModel):
    """Token metadata information."""
    address: str
    name: Optional[str] = None
    symbol: Optional[str] = None
    decimals: Optional[int] = None
    token_type: Optional[str] = None  # 'wrapped', 'native', etc.
    avatar_address: Optional[str] = None  # For wrapped tokens
    wrapper_type: Optional[str] = None  # 'inflationary', 'static', etc.
    
    class Config:
        frozen = True

    @validator('address', 'avatar_address')
    def validate_address(cls, v):
        if v is not None:
            if not isinstance(v, str) or not v.startswith('0x') or len(v) != 42:
                raise ValueError(f'Invalid Ethereum address: {v}')
            return v.lower()
        return v


class FindPathParams(BaseModel):
    """Parameters for pathfinding operations."""
    from_addr: str
    to_addr: str
    target_flow: str
    use_wrapped_balances: bool = False
    from_tokens: Optional[List[str]] = None
    to_tokens: Optional[List[str]] = None
    exclude_from_tokens: Optional[List[str]] = None
    exclude_to_tokens: Optional[List[str]] = None
    
    class Config:
        frozen = True

    @validator('from_addr', 'to_addr')
    def validate_address(cls, v):
        if not isinstance(v, str) or not v.startswith('0x') or len(v) != 42:
            raise ValueError(f'Invalid Ethereum address: {v}')
        return v.lower()

    @validator('target_flow')
    def validate_target_flow(cls, v):
        try:
            int(v)
        except ValueError:
            raise ValueError(f'target_flow must be a valid integer string: {v}')
        return v

    @validator('from_tokens', 'to_tokens', 'exclude_from_tokens', 'exclude_to_tokens')
    def validate_token_lists(cls, v):
        if v is not None:
            for addr in v:
                if not isinstance(addr, str) or not addr.startswith('0x') or len(addr) != 42:
                    raise ValueError(f'Invalid token address: {addr}')
            return [addr.lower() for addr in v]
        return v


@dataclass
class FlowEdge:
    """Represents an edge in the flow graph."""
    stream_sink_id: int
    amount: str


@dataclass
class Stream:
    """Represents a stream in the flow matrix."""
    source_coordinate: int
    flow_edge_ids: List[int]
    data: bytes


@dataclass
class FlowMatrix:
    """Complete flow matrix for ABI encoding."""
    flow_vertices: List[str]
    flow_edges: List[FlowEdge]
    streams: List[Stream]
    packed_coordinates: bytes
    source_coordinate: int


class RPCRequest(BaseModel):
    """JSON-RPC request structure."""
    jsonrpc: str = "2.0"
    id: Union[str, int] = 1
    method: str
    params: List[Any]


class RPCResponse(BaseModel):
    """JSON-RPC response structure."""
    jsonrpc: str
    id: Union[str, int]
    result: Optional[Any] = None
    error: Optional[Dict[str, Any]] = None


class RPCError(BaseModel):
    """JSON-RPC error structure."""
    code: int
    message: str
    data: Optional[Any] = None