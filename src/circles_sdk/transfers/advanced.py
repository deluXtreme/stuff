"""Advanced transfer functionality for the Circles SDK."""

from typing import Optional, List, Dict, Tuple
import asyncio

from ..core.types import PathfindingResult, FindPathParams, FlowMatrix
from ..core.config import CirclesConfig
from ..core.exceptions import (
    CirclesSDKError,
    PathfindingError,
    InsufficientBalanceError,
    TransactionError
)
from ..core.flow_matrix import create_flow_matrix
from ..core.token_info import (
    TokenInfoCache,
    get_token_info_map_from_path,
    get_wrapped_token_totals_from_path,
    get_expected_unwrapped_token_totals
)
from ..pathfinding.client import PathfinderClient
from ..pathfinding.path_processor import (
    replace_wrapped_tokens,
    shrink_path_values,
    assert_no_netted_flow_mismatch
)
from ..transactions.builder import (
    TransactionBuilder,
    TransactionCall,
    UnwrapCall,
    BatchRun,
    build_unwrap_calls
)


class AdvancedTransfer:
    """
    Advanced transfer implementation with wrapped token support.
    
    This class implements the complete transfer pipeline including:
    - Pathfinding
    - Wrapped token processing
    - Path transformation
    - Transaction building
    """
    
    def __init__(
        self,
        config: CirclesConfig,
        cache: Optional[TokenInfoCache] = None
    ):
        self.config = config
        self.cache = cache or TokenInfoCache()
        self._pathfinder_client: Optional[PathfinderClient] = None
    
    async def __aenter__(self):
        """Async context manager entry."""
        self._pathfinder_client = PathfinderClient(self.config)
        await self._pathfinder_client.__aenter__()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self._pathfinder_client:
            await self._pathfinder_client.__aexit__(exc_type, exc_val, exc_tb)
    
    async def transitive_transfer(
        self,
        from_addr: str,
        to_addr: str,
        amount: int,
        use_wrapped_balances: bool = False,
        from_tokens: Optional[List[str]] = None,
        to_tokens: Optional[List[str]] = None,
        exclude_from_tokens: Optional[List[str]] = None,
        exclude_to_tokens: Optional[List[str]] = None,
        tx_data: Optional[bytes] = None
    ) -> Tuple[FlowMatrix, List[TransactionCall]]:
        """
        Perform a complete transitive transfer with wrapped token support.
        
        Port of transitiveTransfer from TypeScript v2Avatar.ts.
        
        Args:
            from_addr: Source address
            to_addr: Destination address  
            amount: Amount to transfer
            use_wrapped_balances: Whether to use wrapped token balances
            from_tokens: Specific tokens to transfer from
            to_tokens: Specific tokens to transfer to
            exclude_from_tokens: Tokens to exclude from source
            exclude_to_tokens: Tokens to exclude from destination
            tx_data: Optional additional transaction data
        
        Returns:
            Tuple of (flow_matrix, transaction_calls)
        """
        if not self._pathfinder_client:
            raise CirclesSDKError("AdvancedTransfer must be used as async context manager")
        
        # Normalize addresses
        from_addr = from_addr.lower()
        to_addr = to_addr.lower()
        
        # Truncate amount to 6 decimals (similar to TypeScript CirclesConverter.truncateToSixDecimals)
        amount = self._truncate_to_six_decimals(amount)
        
        # Find path using pathfinder
        find_params = FindPathParams(
            from_addr=from_addr,
            to_addr=to_addr,
            target_flow=str(amount),
            use_wrapped_balances=use_wrapped_balances,
            from_tokens=from_tokens,
            to_tokens=to_tokens,
            exclude_from_tokens=exclude_from_tokens,
            exclude_to_tokens=exclude_to_tokens
        )
        
        path = await self._pathfinder_client.find_path(find_params)
        
        # Build transaction batch
        batch = BatchRun()
        
        # Add approval if necessary (self-approval for hub)
        # In reality, this would check if approval is already granted
        approval_status = await self._check_approval_status(from_addr, from_addr)
        if not approval_status:
            approval_calls = self._build_approval_calls(from_addr, from_addr)
            for call in approval_calls:
                batch.add_transaction(call)
        
        # Get token information for all tokens in the path
        token_info_map = await get_token_info_map_from_path(
            self.config, path, self.cache
        )
        
        # Determine which edges need to be unwrapped
        wrapped_totals = get_wrapped_token_totals_from_path(path, token_info_map)
        unwrapped_totals = get_expected_unwrapped_token_totals(wrapped_totals, token_info_map)
        
        # Add unwrap calls for each wrapped token
        if wrapped_totals:
            unwrap_calls = build_unwrap_calls(wrapped_totals)
            for unwrap_call in unwrap_calls:
                unwrap_transaction = TransactionCall(
                    to=unwrap_call.to,
                    data=unwrap_call.data,
                    value=unwrap_call.value
                )
                batch.add_transaction(unwrap_transaction)
        
        # Rewrite path: replace all ERC-20 wrappers with their avatars
        path_unwrapped = replace_wrapped_tokens(path, unwrapped_totals)
        
        # Remove a bit from each flow edge to account for rounding errors
        # (only if we handle inflationary wrappers)
        has_inflationary_wrapper = any(
            wrapper_type == "CrcV2_ERC20WrapperDeployed_Inflationary"
            for _, wrapper_type in wrapped_totals.values()
        )
        
        if has_inflationary_wrapper:
            shrunk_path = shrink_path_values(path_unwrapped)
        else:
            shrunk_path = path_unwrapped
        
        # Validate the path
        assert_no_netted_flow_mismatch(shrunk_path)
        
        # Create flow matrix
        flow_matrix = create_flow_matrix(
            from_addr,
            to_addr,
            shrunk_path.max_flow,
            shrunk_path.transfers
        )
        
        # Add transaction data to streams if provided
        if tx_data:
            for stream in flow_matrix.streams:
                stream.data = tx_data
        
        # Build the main transfer transaction
        transfer_call = TransactionCall(
            to=self.config.v2_hub_address,
            data=self._encode_flow_matrix_call(flow_matrix),
            value=0
        )
        batch.add_transaction(transfer_call)
        
        return flow_matrix, batch.get_transactions()
    
    async def transfer(
        self,
        from_addr: str,
        to_addr: str,
        amount: int,
        **kwargs
    ) -> FlowMatrix:
        """
        Simplified transfer method that returns only the flow matrix.
        
        Args:
            from_addr: Source address
            to_addr: Destination address
            amount: Amount to transfer
            **kwargs: Additional arguments passed to transitive_transfer
        
        Returns:
            FlowMatrix for the transfer
        """
        flow_matrix, _ = await self.transitive_transfer(
            from_addr, to_addr, amount, **kwargs
        )
        return flow_matrix
    
    async def transfer_with_transactions(
        self,
        from_addr: str,
        to_addr: str,
        amount: int,
        **kwargs
    ) -> List[TransactionCall]:
        """
        Transfer method that returns the complete transaction batch.
        
        Args:
            from_addr: Source address
            to_addr: Destination address
            amount: Amount to transfer
            **kwargs: Additional arguments passed to transitive_transfer
        
        Returns:
            List of transaction calls to execute
        """
        _, transactions = await self.transitive_transfer(
            from_addr, to_addr, amount, **kwargs
        )
        return transactions
    
    async def get_max_transferable_amount(
        self,
        from_addr: str,
        to_addr: str,
        **kwargs
    ) -> int:
        """
        Get the maximum transferable amount between two addresses.
        
        Args:
            from_addr: Source address
            to_addr: Destination address
            **kwargs: Additional arguments for pathfinding
        
        Returns:
            Maximum transferable amount
        """
        if not self._pathfinder_client:
            raise CirclesSDKError("AdvancedTransfer must be used as async context manager")
        
        max_flow = await self._pathfinder_client.find_max_flow(
            from_addr.lower(),
            to_addr.lower(),
            use_wrapped_balances=kwargs.get('use_wrapped_balances', False),
            from_tokens=kwargs.get('from_tokens'),
            to_tokens=kwargs.get('to_tokens'),
            exclude_from_tokens=kwargs.get('exclude_from_tokens'),
            exclude_to_tokens=kwargs.get('exclude_to_tokens')
        )
        
        return int(max_flow)
    
    def _truncate_to_six_decimals(self, amount: int) -> int:
        """
        Truncate amount to 6 decimals precision.
        
        This is a placeholder for the CirclesConverter.truncateToSixDecimals logic.
        """
        # Placeholder implementation - should match TypeScript logic
        return amount
    
    async def _check_approval_status(self, owner: str, spender: str) -> bool:
        """
        Check if approval is granted for the spender.
        
        This is a placeholder that would check the actual contract state.
        """
        # Placeholder - in reality this would call the hub contract
        # to check isApprovedForAll(owner, spender)
        return False
    
    def _build_approval_calls(self, owner: str, spender: str) -> List[TransactionCall]:
        """
        Build approval transaction calls.
        
        Args:
            owner: Address that owns the tokens
            spender: Address that will spend the tokens
        
        Returns:
            List of approval transaction calls
        """
        # Build setApprovalForAll call
        approval_data = self._encode_approval_call(spender, True)
        
        return [TransactionCall(
            to=self.config.v2_hub_address,
            data=approval_data,
            value=0
        )]
    
    def _encode_approval_call(self, spender: str, approved: bool) -> bytes:
        """
        Encode a setApprovalForAll function call.
        
        Placeholder implementation - would use web3 ABI encoding in reality.
        """
        # Placeholder - in reality this would encode the actual function call
        return b"setApprovalForAll_placeholder"
    
    def _encode_flow_matrix_call(self, flow_matrix: FlowMatrix) -> bytes:
        """
        Encode a flow matrix into a hub contract call.
        
        Placeholder implementation - would use the actual hub ABI in reality.
        """
        # Placeholder - in reality this would encode the flow matrix
        # into the appropriate hub contract function call
        return b"flow_matrix_call_placeholder"


# Convenience functions for one-off transfers

async def advanced_transfer(
    config: CirclesConfig,
    from_addr: str,
    to_addr: str,
    amount: int,
    **kwargs
) -> FlowMatrix:
    """
    Convenience function for advanced transfers.
    
    Args:
        config: Circles configuration
        from_addr: Source address
        to_addr: Destination address
        amount: Amount to transfer
        **kwargs: Additional arguments
    
    Returns:
        FlowMatrix for the transfer
    """
    async with AdvancedTransfer(config) as transfer:
        return await transfer.transfer(from_addr, to_addr, amount, **kwargs)


async def advanced_transfer_with_transactions(
    config: CirclesConfig,
    from_addr: str,
    to_addr: str,
    amount: int,
    **kwargs
) -> Tuple[FlowMatrix, List[TransactionCall]]:
    """
    Convenience function for advanced transfers with transaction calls.
    
    Args:
        config: Circles configuration
        from_addr: Source address
        to_addr: Destination address
        amount: Amount to transfer
        **kwargs: Additional arguments
    
    Returns:
        Tuple of (flow_matrix, transaction_calls)
    """
    async with AdvancedTransfer(config) as transfer:
        return await transfer.transitive_transfer(from_addr, to_addr, amount, **kwargs)