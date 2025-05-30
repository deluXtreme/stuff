"""Path transformation pipeline for the Circles SDK."""

from typing import Dict, List, Set, Tuple, Optional
from dataclasses import dataclass

from ..core.types import PathfindingResult, TransferStep
from ..core.token_info import (
    TokenInfoRow,
    get_token_info_map_from_path,
    get_wrapped_token_totals_from_path,
    get_expected_unwrapped_token_totals,
    TokenInfoCache
)
from ..core.config import CirclesConfig
from ..core.exceptions import PathfindingError


@dataclass
class _IndexedTransferStep:
    """TransferStep with index for sorting."""
    from_address: str
    to_address: str
    token_owner: str
    value: str
    _idx: int


def replace_wrapped_tokens(
    path: PathfindingResult,
    unwrapped_totals: Dict[str, Tuple[int, str]]
) -> PathfindingResult:
    """
    Replace wrapped token addresses with their underlying avatar addresses.
    
    Port of replaceWrappedTokens from TypeScript path.ts.
    
    Args:
        path: Original pathfinding result
        unwrapped_totals: Mapping from wrapper address to (amount, avatar_address)
    
    Returns:
        PathfindingResult with wrapped tokens replaced by avatars
    """
    rewritten_transfers = []
    
    for transfer in path.transfers:
        unwrap_info = unwrapped_totals.get(transfer.token_owner.lower())
        has_unwrap = unwrap_info is not None
        
        # Use avatar address if this is a wrapped token, otherwise keep original
        token_owner = unwrap_info[1] if has_unwrap else transfer.token_owner
        
        rewritten_transfer = TransferStep(
            from_address=transfer.from_address,
            to_address=transfer.to_address,
            token_owner=token_owner,
            value=transfer.value
        )
        rewritten_transfers.append(rewritten_transfer)
    
    return PathfindingResult(
        max_flow=path.max_flow,
        transfers=rewritten_transfers
    )


def shrink_path_values(
    path: PathfindingResult,
    retain_bps: int = 999_999_999_999
) -> PathfindingResult:
    """
    Shrink path values to account for rounding errors with inflationary tokens.
    
    Port of shrinkPathValues from TypeScript path.ts.
    
    Args:
        path: Pathfinding result to shrink
        retain_bps: Basis points to retain (default ~99.9999999999%)
    
    Returns:
        PathfindingResult with shrunk values
    """
    incoming_to_sink: Dict[str, int] = {}
    scaled: List[_IndexedTransferStep] = []
    
    DENOM = 1_000_000_000_000
    
    # Scale all transfer values
    for i, transfer in enumerate(path.transfers):
        scaled_value = (int(transfer.value) * retain_bps) // DENOM
        is_zero = scaled_value == 0
        
        if is_zero:
            continue  # Drop sub-unit flows
        
        scaled_transfer = _IndexedTransferStep(
            from_address=transfer.from_address,
            to_address=transfer.to_address,
            token_owner=transfer.token_owner,
            value=str(scaled_value),
            _idx=i
        )
        scaled.append(scaled_transfer)
        
        # Track incoming amounts to each address
        to_addr = transfer.to_address.lower()
        incoming_to_sink[to_addr] = incoming_to_sink.get(to_addr, 0) + scaled_value
    
    # Find the sink (address that receives but doesn't send)
    senders = {t.from_address.lower() for t in scaled}
    sink = None
    for transfer in scaled:
        if transfer.to_address.lower() not in senders:
            sink = transfer.to_address.lower()
            break
    
    # Calculate max flow as total incoming to sink
    max_flow = incoming_to_sink.get(sink, 0) if sink else 0
    
    # Re-establish original order for deterministic results
    scaled.sort(key=lambda x: x._idx)
    
    # Convert back to regular TransferStep objects
    result_transfers = []
    for scaled_transfer in scaled:
        transfer = TransferStep(
            from_address=scaled_transfer.from_address,
            to_address=scaled_transfer.to_address,
            token_owner=scaled_transfer.token_owner,
            value=scaled_transfer.value
        )
        result_transfers.append(transfer)
    
    return PathfindingResult(
        max_flow=str(max_flow),
        transfers=result_transfers
    )


async def process_path_for_wrapped_tokens(
    config: CirclesConfig,
    path: PathfindingResult,
    cache: Optional[TokenInfoCache] = None
) -> Tuple[PathfindingResult, bool]:
    """
    Complete path processing pipeline for wrapped tokens.
    
    This function combines all the path processing steps:
    1. Get token info for all tokens in path
    2. Identify wrapped tokens and calculate totals
    3. Calculate expected unwrapped totals
    4. Replace wrapped token addresses with avatars
    5. Optionally shrink values if inflationary wrappers are present
    
    Args:
        config: Circles configuration
        path: Original pathfinding result
        cache: Optional token info cache
    
    Returns:
        Tuple of (processed_path, has_inflationary_wrapper)
    """
    # Get token information for all tokens in the path
    token_info_map = await get_token_info_map_from_path(config, path, cache)
    
    # Identify wrapped tokens and calculate totals
    wrapped_totals = get_wrapped_token_totals_from_path(path, token_info_map)
    
    # Calculate expected unwrapped totals
    unwrapped_totals = get_expected_unwrapped_token_totals(wrapped_totals, token_info_map)
    
    # Replace wrapped token addresses with avatar addresses
    path_unwrapped = replace_wrapped_tokens(path, unwrapped_totals)
    
    # Check if we have any inflationary wrappers
    has_inflationary_wrapper = any(
        wrapper_type == "CrcV2_ERC20WrapperDeployed_Inflationary"
        for _, wrapper_type in wrapped_totals.values()
    )
    
    # Shrink values if we have inflationary wrappers
    if has_inflationary_wrapper:
        shrunk_path = shrink_path_values(path_unwrapped)
        return shrunk_path, True
    else:
        return path_unwrapped, False


def assert_no_netted_flow_mismatch(path: PathfindingResult) -> None:
    """
    Assert that the path has proper flow balance.
    
    Port of assertNoNettedFlowMismatch from TypeScript.
    
    Args:
        path: Pathfinding result to validate
    
    Raises:
        PathfindingError: If flow is not properly balanced
    """
    source, sink = _get_source_and_sink(path)
    net_flow = _compute_netted_flow(path)
    
    for addr, balance in net_flow.items():
        is_source = addr == source
        is_sink = addr == sink
        
        if is_source and balance >= 0:
            raise PathfindingError(f"Source {addr} should be net negative, got {balance}")
        
        if is_sink and balance <= 0:
            raise PathfindingError(f"Sink {addr} should be net positive, got {balance}")
        
        is_intermediate = not is_source and not is_sink
        if is_intermediate and balance != 0:
            raise PathfindingError(f"Vertex {addr} is unbalanced: {balance}")


def _get_source_and_sink(path: PathfindingResult) -> Tuple[str, str]:
    """
    Get the source and sink addresses from a path.
    
    Args:
        path: Pathfinding result
    
    Returns:
        Tuple of (source_address, sink_address)
    
    Raises:
        PathfindingError: If source/sink cannot be determined
    """
    senders = {t.from_address.lower() for t in path.transfers}
    receivers = {t.to_address.lower() for t in path.transfers}
    
    # Source sends but doesn't receive
    sources = [addr for addr in senders if addr not in receivers]
    # Sink receives but doesn't send
    sinks = [addr for addr in receivers if addr not in senders]
    
    if len(sources) != 1 or len(sinks) != 1:
        raise PathfindingError("Could not determine unique source / sink")
    
    return sources[0], sinks[0]


def _compute_netted_flow(path: PathfindingResult) -> Dict[str, int]:
    """
    Compute the net flow for each address in the path.
    
    Args:
        path: Pathfinding result
    
    Returns:
        Dict mapping addresses to net flow (positive = net receiver, negative = net sender)
    """
    net_flow: Dict[str, int] = {}
    
    for transfer in path.transfers:
        amount = int(transfer.value)
        from_addr = transfer.from_address.lower()
        to_addr = transfer.to_address.lower()
        
        # Subtract from sender
        net_flow[from_addr] = net_flow.get(from_addr, 0) - amount
        # Add to receiver
        net_flow[to_addr] = net_flow.get(to_addr, 0) + amount
    
    return net_flow