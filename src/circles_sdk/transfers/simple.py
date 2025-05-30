"""Simple transfer implementation for basic pathfinding to flow matrix pipeline."""

import asyncio
import logging
from typing import Optional, List

from ..core.config import CirclesConfig
from ..core.types import FindPathParams, FlowMatrix
from ..pathfinding.client import PathfinderClient
from ..core.flow_matrix import create_flow_matrix, TransferStep as LegacyTransferStep, flow_matrix_to_abi_hex
from ..core.exceptions import PathfindingError, ValidationError

logger = logging.getLogger(__name__)


class SimpleTransfer:
    """Simple transfer implementation without wrapped token support."""

    def __init__(self, config: CirclesConfig):
        """Initialize simple transfer with configuration.

        Args:
            config: Circles configuration
        """
        self.config = config
        self.pathfinder = PathfinderClient(config)

    async def __aenter__(self):
        """Async context manager entry."""
        await self.pathfinder._ensure_session()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.pathfinder.close()

    def _validate_transfer_params(
        self,
        from_addr: str,
        to_addr: str,
        amount: str
    ) -> None:
        """Validate transfer parameters.

        Args:
            from_addr: Source address
            to_addr: Destination address
            amount: Transfer amount

        Raises:
            ValidationError: Invalid parameters
        """
        # Validate addresses
        for addr, name in [(from_addr, 'from_addr'), (to_addr, 'to_addr')]:
            if not isinstance(addr, str) or not addr.startswith('0x') or len(addr) != 42:
                raise ValidationError(f"Invalid {name}: {addr}", field=name, value=addr)

        # Validate amount
        try:
            amount_int = int(amount)
            if amount_int <= 0:
                raise ValidationError("Amount must be positive", field='amount', value=amount)
        except ValueError:
            raise ValidationError("Amount must be a valid integer string", field='amount', value=amount)

        # Check addresses are different
        if from_addr.lower() == to_addr.lower():
            raise ValidationError("Source and destination addresses must be different")

    def _convert_transfers(self, transfers) -> List[LegacyTransferStep]:
        """Convert Pydantic TransferStep to legacy dataclass format.

        Args:
            transfers: List of Pydantic TransferStep objects

        Returns:
            List of legacy TransferStep dataclasses
        """
        legacy_transfers = []
        for transfer in transfers:
            legacy_transfer = LegacyTransferStep(
                from_address=transfer.from_address,
                to_address=transfer.to_address,
                token_owner=transfer.token_owner,
                value=transfer.value
            )
            legacy_transfers.append(legacy_transfer)
        return legacy_transfers

    async def transfer(
        self,
        from_addr: str,
        to_addr: str,
        amount: str,
        use_wrapped_balances: bool = False,
        from_tokens: Optional[List[str]] = None,
        to_tokens: Optional[List[str]] = None,
        exclude_from_tokens: Optional[List[str]] = None,
        exclude_to_tokens: Optional[List[str]] = None
    ) -> FlowMatrix:
        """Execute a simple transfer using pathfinding.

        Args:
            from_addr: Source address
            to_addr: Destination address
            amount: Transfer amount as string
            use_wrapped_balances: Whether to use wrapped balances
            from_tokens: Specific tokens to use as source
            to_tokens: Specific tokens to use as destination
            exclude_from_tokens: Tokens to exclude from source
            exclude_to_tokens: Tokens to exclude from destination

        Returns:
            FlowMatrix ready for ABI encoding

        Raises:
            ValidationError: Invalid parameters
            PathfindingError: Pathfinding failed
        """
        # Normalize addresses
        from_addr = from_addr.lower()
        to_addr = to_addr.lower()

        # Validate inputs
        self._validate_transfer_params(from_addr, to_addr, amount)

        logger.info(f"Starting simple transfer: {from_addr} -> {to_addr}, amount: {amount}")

        try:
            # 1. Find path using pathfinder
            params = FindPathParams(
                from_addr=from_addr,
                to_addr=to_addr,
                target_flow=amount,
                use_wrapped_balances=use_wrapped_balances,
                from_tokens=from_tokens,
                to_tokens=to_tokens,
                exclude_from_tokens=exclude_from_tokens,
                exclude_to_tokens=exclude_to_tokens
            )

            path_result = await self.pathfinder.find_path(params)

            logger.info(f"Pathfinder found {len(path_result.transfers)} transfer steps")

            # 2. Convert to legacy format for flow matrix creation
            legacy_transfers = self._convert_transfers(path_result.transfers)

            # 3. Create flow matrix
            flow_matrix = create_flow_matrix(
                from_addr=from_addr,
                to_addr=to_addr,
                value=path_result.max_flow,
                transfers=legacy_transfers
            )

            logger.info(f"Created flow matrix with {len(flow_matrix.flow_vertices)} vertices")

            return flow_matrix

        except Exception as e:
            logger.error(f"Transfer failed: {e}")
            if isinstance(e, (ValidationError, PathfindingError)):
                raise
            else:
                raise PathfindingError(
                    f"Unexpected error during transfer: {e}",
                    from_addr=from_addr,
                    to_addr=to_addr,
                    amount=amount
                )

    async def get_max_transferable_amount(
        self,
        from_addr: str,
        to_addr: str,
        use_wrapped_balances: bool = False,
        from_tokens: Optional[List[str]] = None,
        to_tokens: Optional[List[str]] = None,
        exclude_from_tokens: Optional[List[str]] = None,
        exclude_to_tokens: Optional[List[str]] = None
    ) -> int:
        """Get maximum transferable amount between addresses.

        Args:
            from_addr: Source address
            to_addr: Destination address
            use_wrapped_balances: Whether to use wrapped balances
            from_tokens: Specific tokens to use as source
            to_tokens: Specific tokens to use as destination
            exclude_from_tokens: Tokens to exclude from source
            exclude_to_tokens: Tokens to exclude from destination

        Returns:
            Maximum transferable amount

        Raises:
            ValidationError: Invalid parameters
            PathfindingError: Pathfinding failed
        """
        # Normalize addresses
        from_addr = from_addr.lower()
        to_addr = to_addr.lower()

        # Basic address validation
        for addr, name in [(from_addr, 'from_addr'), (to_addr, 'to_addr')]:
            if not isinstance(addr, str) or not addr.startswith('0x') or len(addr) != 42:
                raise ValidationError(f"Invalid {name}: {addr}", field=name, value=addr)

        logger.info(f"Getting max transferable amount: {from_addr} -> {to_addr}")

        try:
            max_amount = await self.pathfinder.find_max_flow(
                from_addr=from_addr,
                to_addr=to_addr,
                use_wrapped_balances=use_wrapped_balances,
                from_tokens=from_tokens,
                to_tokens=to_tokens,
                exclude_from_tokens=exclude_from_tokens,
                exclude_to_tokens=exclude_to_tokens
            )

            logger.info(f"Max transferable amount: {max_amount}")
            return max_amount

        except Exception as e:
            logger.error(f"Failed to get max transferable amount: {e}")
            if isinstance(e, (ValidationError, PathfindingError)):
                raise
            else:
                raise PathfindingError(
                    f"Unexpected error getting max amount: {e}",
                    from_addr=from_addr,
                    to_addr=to_addr
                )

    async def transfer_to_abi(
        self,
        from_addr: str,
        to_addr: str,
        amount: str,
        **kwargs
    ) -> dict:
        """Execute transfer and return ABI-ready data.

        Args:
            from_addr: Source address
            to_addr: Destination address
            amount: Transfer amount
            **kwargs: Additional parameters for transfer

        Returns:
            ABI-encoded data ready for smart contract interaction

        Raises:
            ValidationError: Invalid parameters
            PathfindingError: Transfer failed
        """
        flow_matrix = await self.transfer(from_addr, to_addr, amount, **kwargs)
        return flow_matrix_to_abi_hex(flow_matrix)

    async def health_check(self) -> bool:
        """Check if the transfer service is healthy.

        Returns:
            True if healthy, False otherwise
        """
        try:
            return await self.pathfinder.health_check()
        except Exception as e:
            logger.warning(f"Health check failed: {e}")
            return False


# Convenience functions for simple usage
async def simple_transfer(
    config: CirclesConfig,
    from_addr: str,
    to_addr: str,
    amount: str,
    **kwargs
) -> FlowMatrix:
    """Convenience function for simple transfers.

    Args:
        config: Circles configuration
        from_addr: Source address
        to_addr: Destination address
        amount: Transfer amount
        **kwargs: Additional transfer parameters

    Returns:
        FlowMatrix ready for ABI encoding
    """
    async with SimpleTransfer(config) as transfer_client:
        return await transfer_client.transfer(from_addr, to_addr, amount, **kwargs)


async def simple_transfer_to_abi(
    config: CirclesConfig,
    from_addr: str,
    to_addr: str,
    amount: str,
    **kwargs
) -> dict:
    """Convenience function for simple transfers with ABI encoding.

    Args:
        config: Circles configuration
        from_addr: Source address
        to_addr: Destination address
        amount: Transfer amount
        **kwargs: Additional transfer parameters

    Returns:
        ABI-encoded data ready for smart contract interaction
    """
    async with SimpleTransfer(config) as transfer_client:
        return await transfer_client.transfer_to_abi(from_addr, to_addr, amount, **kwargs)
