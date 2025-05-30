"""Main CirclesAvatar interface for the Circles SDK."""

import asyncio
from typing import Optional, List, Dict, Tuple, Any
import logging

from .core.config import CirclesConfig
from .core.types import FlowMatrix
from .core.token_info import TokenInfoCache
from .core.exceptions import CirclesSDKError, ValidationError
from .transfers.advanced import AdvancedTransfer
from .transactions.builder import TransactionCall

logger = logging.getLogger(__name__)


class CirclesAvatar:
    """
    High-level interface for Circles protocol operations.
    
    This class provides a clean, intuitive API for interacting with the Circles protocol,
    wrapping the lower-level functionality in an easy-to-use interface.
    
    Example:
        ```python
        async def transfer_example():
            config = CirclesConfig(
                rpc_url="https://rpc.circlesubi.network",
                pathfinder_url="https://pathfinder.aboutcircles.com",
                v2_hub_address="0xc12C1E50ABB450d6205Ea2C3Fa861b3B834d13e8",
                chain_id=100
            )
            
            avatar = CirclesAvatar("0xYourAddress", config)
            
            async with avatar:
                # Transfer 1 CRC
                flow_matrix = await avatar.transfer(
                    to="0xRecipientAddress",
                    amount=1_000_000_000_000_000_000,
                    use_wrapped_balances=True
                )
                
                print(f"Transfer ready: {len(flow_matrix.streams)} streams")
        ```
    """
    
    def __init__(
        self,
        address: str,
        config: Optional[CirclesConfig] = None,
        cache_size: int = 1000
    ):
        """
        Initialize a CirclesAvatar.
        
        Args:
            address: The avatar's Ethereum address
            config: Circles configuration (defaults to production config if not provided)
            cache_size: Size of the token info cache for performance optimization
        
        Raises:
            ValidationError: If the address is invalid
        """
        self.address = self._validate_address(address)
        self.config = config or self._default_config()
        self.cache = TokenInfoCache(max_size=cache_size)
        self._advanced_transfer: Optional[AdvancedTransfer] = None
        self._closed = False
        
        logger.info(f"Initialized CirclesAvatar for {self.address}")
    
    async def __aenter__(self):
        """Async context manager entry."""
        if self._closed:
            raise RuntimeError("Avatar has been closed")
        
        self._advanced_transfer = AdvancedTransfer(self.config, self.cache)
        await self._advanced_transfer.__aenter__()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self._advanced_transfer:
            await self._advanced_transfer.__aexit__(exc_type, exc_val, exc_tb)
        self._closed = True
    
    async def transfer(
        self,
        to: str,
        amount: int,
        use_wrapped_balances: bool = True,
        from_tokens: Optional[List[str]] = None,
        to_tokens: Optional[List[str]] = None,
        exclude_from_tokens: Optional[List[str]] = None,
        exclude_to_tokens: Optional[List[str]] = None
    ) -> FlowMatrix:
        """
        Perform a high-level token transfer.
        
        This is the main transfer method that handles all the complexity of:
        - Pathfinding
        - Wrapped token processing
        - Path transformation
        - Flow matrix creation
        
        Args:
            to: Recipient address
            amount: Amount to transfer in wei (18 decimals for CRC)
            use_wrapped_balances: Whether to use wrapped token balances
            from_tokens: Specific tokens to transfer from
            to_tokens: Specific tokens to transfer to
            exclude_from_tokens: Tokens to exclude from source
            exclude_to_tokens: Tokens to exclude from destination
        
        Returns:
            FlowMatrix ready for transaction execution
        
        Raises:
            ValidationError: If parameters are invalid
            PathfindingError: If no path can be found
            InsufficientBalanceError: If insufficient balance
        """
        self._ensure_active()
        
        # Validate inputs
        to = self._validate_address(to)
        if amount <= 0:
            raise ValidationError("Amount must be positive", field="amount", value=amount)
        
        logger.info(f"Starting transfer: {self.address} -> {to}, amount: {amount / 1e18:.6f} CRC")
        
        try:
            flow_matrix = await self._advanced_transfer.transfer(
                from_addr=self.address,
                to_addr=to,
                amount=amount,
                use_wrapped_balances=use_wrapped_balances,
                from_tokens=from_tokens,
                to_tokens=to_tokens,
                exclude_from_tokens=exclude_from_tokens,
                exclude_to_tokens=exclude_to_tokens
            )
            
            logger.info(f"Transfer successful: {len(flow_matrix.streams)} streams, {len(flow_matrix.flow_vertices)} vertices")
            return flow_matrix
            
        except Exception as e:
            logger.error(f"Transfer failed: {e}")
            raise
    
    async def transfer_with_transactions(
        self,
        to: str,
        amount: int,
        use_wrapped_balances: bool = True,
        from_tokens: Optional[List[str]] = None,
        to_tokens: Optional[List[str]] = None,
        exclude_from_tokens: Optional[List[str]] = None,
        exclude_to_tokens: Optional[List[str]] = None,
        tx_data: Optional[bytes] = None
    ) -> Tuple[FlowMatrix, List[TransactionCall]]:
        """
        Perform a transfer and get the complete transaction batch.
        
        This method returns both the flow matrix and all the transactions needed
        to execute the transfer, including approvals and unwrap calls.
        
        Args:
            to: Recipient address
            amount: Amount to transfer in wei
            use_wrapped_balances: Whether to use wrapped token balances
            from_tokens: Specific tokens to transfer from
            to_tokens: Specific tokens to transfer to
            exclude_from_tokens: Tokens to exclude from source
            exclude_to_tokens: Tokens to exclude from destination
            tx_data: Optional additional transaction data
        
        Returns:
            Tuple of (FlowMatrix, List of TransactionCalls)
        
        Raises:
            ValidationError: If parameters are invalid
            PathfindingError: If no path can be found
            InsufficientBalanceError: If insufficient balance
        """
        self._ensure_active()
        
        to = self._validate_address(to)
        if amount <= 0:
            raise ValidationError("Amount must be positive", field="amount", value=amount)
        
        logger.info(f"Starting transfer with transactions: {self.address} -> {to}, amount: {amount / 1e18:.6f} CRC")
        
        try:
            flow_matrix, transactions = await self._advanced_transfer.transitive_transfer(
                from_addr=self.address,
                to_addr=to,
                amount=amount,
                use_wrapped_balances=use_wrapped_balances,
                from_tokens=from_tokens,
                to_tokens=to_tokens,
                exclude_from_tokens=exclude_from_tokens,
                exclude_to_tokens=exclude_to_tokens,
                tx_data=tx_data
            )
            
            logger.info(f"Transfer with transactions successful: {len(transactions)} transactions prepared")
            return flow_matrix, transactions
            
        except Exception as e:
            logger.error(f"Transfer with transactions failed: {e}")
            raise
    
    async def get_max_transferable_amount(
        self,
        to: str,
        use_wrapped_balances: bool = True,
        from_tokens: Optional[List[str]] = None,
        to_tokens: Optional[List[str]] = None,
        exclude_from_tokens: Optional[List[str]] = None,
        exclude_to_tokens: Optional[List[str]] = None
    ) -> int:
        """
        Get the maximum transferable amount to a specific address.
        
        Args:
            to: Destination address
            use_wrapped_balances: Whether to include wrapped token balances
            from_tokens: Specific tokens to transfer from
            to_tokens: Specific tokens to transfer to
            exclude_from_tokens: Tokens to exclude from source
            exclude_to_tokens: Tokens to exclude from destination
        
        Returns:
            Maximum transferable amount in wei
        
        Raises:
            ValidationError: If the destination address is invalid
            PathfindingError: If pathfinding fails
        """
        self._ensure_active()
        
        to = self._validate_address(to)
        
        logger.info(f"Getting max transferable amount: {self.address} -> {to}")
        
        try:
            max_amount = await self._advanced_transfer.get_max_transferable_amount(
                from_addr=self.address,
                to_addr=to,
                use_wrapped_balances=use_wrapped_balances,
                from_tokens=from_tokens,
                to_tokens=to_tokens,
                exclude_from_tokens=exclude_from_tokens,
                exclude_to_tokens=exclude_to_tokens
            )
            
            logger.info(f"Max transferable amount: {max_amount / 1e18:.6f} CRC")
            return max_amount
            
        except Exception as e:
            logger.error(f"Failed to get max transferable amount: {e}")
            raise
    
    async def estimate_transfer_cost(
        self,
        to: str,
        amount: int,
        use_wrapped_balances: bool = True
    ) -> Dict[str, Any]:
        """
        Estimate the gas cost for a transfer.
        
        Note: This is a placeholder implementation for Phase 3.1.
        Full gas estimation will be implemented in Phase 3.3 with web3 integration.
        
        Args:
            to: Destination address
            amount: Amount to transfer in wei
            use_wrapped_balances: Whether to use wrapped token balances
        
        Returns:
            Dictionary with gas estimation details
        """
        self._ensure_active()
        
        to = self._validate_address(to)
        if amount <= 0:
            raise ValidationError("Amount must be positive", field="amount", value=amount)
        
        logger.info(f"Estimating transfer cost: {self.address} -> {to}, amount: {amount / 1e18:.6f} CRC")
        
        try:
            # Get the transaction batch to estimate gas for
            _, transactions = await self.transfer_with_transactions(
                to=to,
                amount=amount,
                use_wrapped_balances=use_wrapped_balances
            )
            
            # Placeholder gas estimation
            # In Phase 3.3, this will use actual web3 gas estimation
            estimated_gas_per_tx = 150000  # Conservative estimate
            total_gas = len(transactions) * estimated_gas_per_tx
            
            # Mock gas price (in gwei)
            gas_price_gwei = 2  # Conservative for Gnosis Chain
            gas_price_wei = gas_price_gwei * 1e9
            
            estimated_cost_wei = total_gas * gas_price_wei
            estimated_cost_eth = estimated_cost_wei / 1e18
            
            result = {
                "transaction_count": len(transactions),
                "estimated_gas_per_transaction": estimated_gas_per_tx,
                "total_estimated_gas": total_gas,
                "gas_price_gwei": gas_price_gwei,
                "estimated_cost_wei": int(estimated_cost_wei),
                "estimated_cost_eth": estimated_cost_eth,
                "note": "This is a placeholder estimation. Full gas estimation will be available in Phase 3.3"
            }
            
            logger.info(f"Transfer cost estimate: {estimated_cost_eth:.6f} ETH ({len(transactions)} transactions)")
            return result
            
        except Exception as e:
            logger.error(f"Failed to estimate transfer cost: {e}")
            raise
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get token cache statistics.
        
        Returns:
            Dictionary with cache statistics
        """
        return {
            "cache_size": len(self.cache._cache),
            "max_cache_size": self.cache._max_size,
            "cache_usage_percent": (len(self.cache._cache) / self.cache._max_size) * 100
        }
    
    def clear_cache(self) -> None:
        """Clear the token information cache."""
        self.cache._cache.clear()
        logger.info("Token cache cleared")
    
    @property
    def is_active(self) -> bool:
        """Check if the avatar is active (not closed)."""
        return not self._closed and self._advanced_transfer is not None
    
    def _ensure_active(self) -> None:
        """Ensure the avatar is active and ready for operations."""
        if self._closed:
            raise RuntimeError("Avatar has been closed. Use 'async with' pattern.")
        if self._advanced_transfer is None:
            raise RuntimeError("Avatar not initialized. Use 'async with' pattern.")
    
    def _validate_address(self, address: str) -> str:
        """
        Validate and normalize an Ethereum address.
        
        Args:
            address: Address to validate
        
        Returns:
            Normalized lowercase address
        
        Raises:
            ValidationError: If address is invalid
        """
        if not isinstance(address, str):
            raise ValidationError("Address must be a string", field="address", value=address)
        
        if not address.startswith('0x'):
            raise ValidationError("Address must start with '0x'", field="address", value=address)
        
        if len(address) != 42:
            raise ValidationError("Address must be 42 characters long", field="address", value=address)
        
        try:
            # Basic hex validation
            int(address[2:], 16)
        except ValueError:
            raise ValidationError("Address contains invalid hex characters", field="address", value=address)
        
        return address.lower()
    
    def _default_config(self) -> CirclesConfig:
        """
        Get default production configuration.
        
        Returns:
            Default CirclesConfig for production use
        """
        return CirclesConfig(
            rpc_url="https://rpc.circlesubi.network",
            pathfinder_url="https://pathfinder.aboutcircles.com",
            v2_hub_address="0xc12C1E50ABB450d6205Ea2C3Fa861b3B834d13e8",
            chain_id=100,
            request_timeout=60.0,
            max_retries=3
        )
    
    def __repr__(self) -> str:
        """String representation of the avatar."""
        status = "active" if self.is_active else "inactive"
        return f"CirclesAvatar(address='{self.address}', status='{status}')"