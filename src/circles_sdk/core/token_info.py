"""Token metadata management for the Circles SDK."""

from typing import Dict, List, Set, Optional, Tuple
import aiohttp
from enum import Enum

from .types import PathfindingResult, TokenInfo
from .config import CirclesConfig
from .exceptions import TokenError, RPCError


class TokenType(str, Enum):
    """Token types in the Circles protocol."""
    CRC_V1_SIGNUP = "CrcV1_Signup"
    CRC_V2_REGISTER_HUMAN = "CrcV2_RegisterHuman"
    CRC_V2_REGISTER_GROUP = "CrcV2_RegisterGroup"
    CRC_V2_ERC20_WRAPPER_INFLATIONARY = "CrcV2_ERC20WrapperDeployed_Inflationary"
    CRC_V2_ERC20_WRAPPER_DEMURRAGED = "CrcV2_ERC20WrapperDeployed_Demurraged"


class TokenInfoRow:
    """Raw token info data from RPC."""
    
    def __init__(
        self,
        timestamp: int,
        transaction_hash: str,
        version: int,
        token_type: str,
        token: str,
        token_owner: str
    ):
        self.timestamp = timestamp
        self.transaction_hash = transaction_hash
        self.version = version
        self.type = token_type
        self.token = token.lower()
        self.token_owner = token_owner.lower()
    
    @property
    def is_wrapped(self) -> bool:
        """Check if this token is a wrapped token."""
        return self.type.startswith("CrcV2_ERC20WrapperDeployed")
    
    @property
    def wrapper_type(self) -> Optional[str]:
        """Get the wrapper type (inflationary/demurraged) if applicable."""
        if not self.is_wrapped:
            return None
        if self.type == TokenType.CRC_V2_ERC20_WRAPPER_INFLATIONARY:
            return "inflationary"
        elif self.type == TokenType.CRC_V2_ERC20_WRAPPER_DEMURRAGED:
            return "demurraged"
        return None


class TokenInfoCache:
    """Simple in-memory cache for token information."""
    
    def __init__(self, max_size: int = 1000):
        self._cache: Dict[str, TokenInfoRow] = {}
        self._max_size = max_size
    
    def get(self, token_address: str) -> Optional[TokenInfoRow]:
        """Get token info from cache."""
        return self._cache.get(token_address.lower())
    
    def set(self, token_address: str, info: TokenInfoRow) -> None:
        """Set token info in cache."""
        if len(self._cache) >= self._max_size:
            # Simple eviction: remove oldest entry
            oldest_key = next(iter(self._cache))
            del self._cache[oldest_key]
        
        self._cache[token_address.lower()] = info
    
    def set_batch(self, infos: List[TokenInfoRow]) -> None:
        """Set multiple token infos in cache."""
        for info in infos:
            self.set(info.token, info)


async def get_token_info_map_from_path(
    config: CirclesConfig,
    transfer_path: PathfindingResult,
    cache: Optional[TokenInfoCache] = None
) -> Dict[str, TokenInfoRow]:
    """
    Get token information for all tokens in a transfer path.
    
    This is a port of the TypeScript getTokenInfoMapFromPath function.
    
    Args:
        config: Circles configuration
        transfer_path: Pathfinding result containing transfers
        cache: Optional cache for token information
    
    Returns:
        Dict mapping token addresses to token info
    """
    token_info_map: Dict[str, TokenInfoRow] = {}
    unique_addresses: Set[str] = set()
    
    # Collect all unique token addresses from the path
    for transfer in transfer_path.transfers:
        unique_addresses.add(transfer.token_owner.lower())
    
    # Check cache first if provided
    addresses_to_fetch = []
    if cache:
        for addr in unique_addresses:
            cached_info = cache.get(addr)
            if cached_info:
                token_info_map[addr] = cached_info
            else:
                addresses_to_fetch.append(addr)
    else:
        addresses_to_fetch = list(unique_addresses)
    
    # Fetch missing token info from RPC
    if addresses_to_fetch:
        batch_info = await get_token_info_batch(config, addresses_to_fetch)
        for info in batch_info:
            token_info_map[info.token] = info
            
        # Update cache if provided
        if cache:
            cache.set_batch(batch_info)
    
    return token_info_map


async def get_token_info_batch(
    config: CirclesConfig,
    token_addresses: List[str]
) -> List[TokenInfoRow]:
    """
    Fetch token information for multiple addresses via RPC.
    
    This simulates the CirclesData.getTokenInfoBatch call from TypeScript.
    In a real implementation, this would call the appropriate RPC method.
    """
    if not token_addresses:
        return []
    
    # For now, we'll create a mock implementation
    # In the real implementation, this would call the circles data RPC
    try:
        async with aiohttp.ClientSession() as session:
            # This is a simplified mock - in reality you'd call the actual
            # circles data API to get token metadata
            result = []
            for addr in token_addresses:
                # Mock token info - in reality this comes from RPC
                info = TokenInfoRow(
                    timestamp=0,
                    transaction_hash="0x" + "0" * 64,
                    version=2,
                    token_type=_infer_token_type(addr),  # Mock inference
                    token=addr,
                    token_owner=addr  # For simplicity in mock
                )
                result.append(info)
            
            return result
            
    except Exception as e:
        raise TokenError(f"Failed to fetch token info batch: {str(e)}")


def _infer_token_type(token_address: str) -> str:
    """
    Mock function to infer token type.
    In reality, this would be determined by the RPC response.
    """
    # This is just for testing - real implementation gets this from RPC
    return TokenType.CRC_V2_REGISTER_HUMAN


def get_wrapped_token_totals_from_path(
    transfer_path: PathfindingResult,
    token_info_map: Dict[str, TokenInfoRow]
) -> Dict[str, Tuple[int, str]]:
    """
    Get wrapped token totals from a transfer path.
    
    Port of getWrappedTokenTotalsFromPath from TypeScript.
    
    Args:
        transfer_path: Pathfinding result
        token_info_map: Token information mapping
    
    Returns:
        Dict mapping wrapper addresses to (total_value, wrapper_type)
    """
    wrapped_edge_totals: Dict[str, Tuple[int, str]] = {}
    
    for transfer in transfer_path.transfers:
        token_addr = transfer.token_owner.lower()
        info = token_info_map.get(token_addr)
        
        if info and info.is_wrapped:
            if token_addr not in wrapped_edge_totals:
                wrapped_edge_totals[token_addr] = (0, info.type)
            
            current_total, wrapper_type = wrapped_edge_totals[token_addr]
            wrapped_edge_totals[token_addr] = (
                current_total + int(transfer.value),
                wrapper_type
            )
    
    return wrapped_edge_totals


def get_expected_unwrapped_token_totals(
    wrapped_totals: Dict[str, Tuple[int, str]],
    token_info_map: Dict[str, TokenInfoRow]
) -> Dict[str, Tuple[int, str]]:
    """
    Calculate expected unwrapped token totals.
    
    Port of getExpectedUnwrappedTokenTotals from TypeScript.
    
    Args:
        wrapped_totals: Wrapped token totals from get_wrapped_token_totals_from_path
        token_info_map: Token information mapping
    
    Returns:
        Dict mapping wrapper addresses to (unwrapped_amount, avatar_address)
    """
    unwrapped: Dict[str, Tuple[int, str]] = {}
    
    for wrapper_addr, (total, token_type) in wrapped_totals.items():
        info = token_info_map.get(wrapper_addr.lower())
        if not info:
            continue
        
        is_demurraged = token_type == TokenType.CRC_V2_ERC20_WRAPPER_DEMURRAGED
        is_inflationary = token_type == TokenType.CRC_V2_ERC20_WRAPPER_INFLATIONARY
        
        # Calculate unwrap amount based on token type
        if is_demurraged:
            unwrap_amount = total
        elif is_inflationary:
            # In TypeScript: CirclesConverter.attoCirclesToAttoStaticCircles(total)
            # For now, we'll use a simple conversion - this should be implemented
            # with the actual circles converter logic
            unwrap_amount = _atto_circles_to_atto_static_circles(total)
        else:
            unwrap_amount = total
        
        # Calculate available amount after unwrap
        if is_demurraged:
            available_after_unwrap = unwrap_amount
        else:
            # In TypeScript: CirclesConverter.attoStaticCirclesToAttoCircles(unwrapAmount)
            available_after_unwrap = _atto_static_circles_to_atto_circles(unwrap_amount)
        
        unwrapped[wrapper_addr] = (available_after_unwrap, info.token_owner)
    
    return unwrapped


def _atto_circles_to_atto_static_circles(amount: int) -> int:
    """
    Convert atto circles to atto static circles.
    
    This is a placeholder for the actual CirclesConverter logic.
    In the real implementation, this would use the proper conversion formula.
    """
    # Placeholder conversion - implement actual logic
    return amount


def _atto_static_circles_to_atto_circles(amount: int) -> int:
    """
    Convert atto static circles to atto circles.
    
    This is a placeholder for the actual CirclesConverter logic.
    In the real implementation, this would use the proper conversion formula.
    """
    # Placeholder conversion - implement actual logic
    return amount