"""Pathfinder RPC client for Circles protocol."""

import asyncio
import logging
from typing import Optional, Dict, Any
import aiohttp
from aiohttp import ClientTimeout, ClientError

from ..core.config import CirclesConfig
from ..core.types import (
    FindPathParams,
    PathfindingResult,
    RPCRequest,
    RPCResponse,
    TransferStep
)
from ..core.exceptions import (
    PathfindingError,
    NoPathFoundError,
    InsufficientBalanceError,
    RPCError,
    NetworkError,
    TimeoutError as SDKTimeoutError,
    RateLimitError
)

logger = logging.getLogger(__name__)


class PathfinderClient:
    """Async RPC client for Circles pathfinder service."""

    def __init__(self, config: CirclesConfig):
        """Initialize the pathfinder client.

        Args:
            config: Circles configuration containing RPC URLs and settings
        """
        self.config = config
        self.session: Optional[aiohttp.ClientSession] = None
        self._closed = False

    async def __aenter__(self):
        """Async context manager entry."""
        await self._ensure_session()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()

    async def _ensure_session(self):
        """Ensure aiohttp session is created."""
        if self.session is None or self.session.closed:
            timeout = ClientTimeout(total=self.config.request_timeout)
            self.session = aiohttp.ClientSession(
                timeout=timeout,
                headers={
                    'Content-Type': 'application/json',
                    'User-Agent': 'Circles-Python-SDK/0.1.0'
                }
            )

    async def close(self):
        """Close the HTTP session."""
        if self.session and not self.session.closed:
            await self.session.close()
        self._closed = True

    async def _make_rpc_call(
        self,
        method: str,
        params: list,
        timeout: Optional[float] = None
    ) -> Any:
        """Make a JSON-RPC call with retry logic.

        Args:
            method: RPC method name
            params: RPC parameters
            timeout: Request timeout override

        Returns:
            RPC result data

        Raises:
            RPCError: RPC call failed
            NetworkError: Network connectivity issues
            TimeoutError: Request timed out
        """
        if self._closed:
            raise RuntimeError("Client has been closed")

        await self._ensure_session()

        request = RPCRequest(
            method=method,
            params=params
        )

        last_exception = None

        for attempt in range(self.config.max_retries + 1):
            try:
                logger.debug(f"RPC call attempt {attempt + 1}: {method}")

                async with self.session.post(
                    self.config.rpc_url,
                    json=request.dict(),
                    timeout=ClientTimeout(total=timeout or self.config.request_timeout)
                ) as response:

                    # Handle rate limiting
                    if response.status == 429:
                        retry_after = int(response.headers.get('Retry-After', 60))
                        raise RateLimitError(
                            "Rate limit exceeded",
                            retry_after=retry_after,
                            details={'status_code': response.status}
                        )

                    # Handle other HTTP errors
                    if response.status >= 400:
                        error_text = await response.text()
                        raise RPCError(
                            f"HTTP {response.status}: {error_text}",
                            method=method,
                            status_code=response.status,
                            response_data=error_text
                        )

                    # Parse JSON response
                    try:
                        json_data = await response.json()
                    except Exception as e:
                        raise RPCError(
                            f"Failed to parse JSON response: {e}",
                            method=method,
                            status_code=response.status
                        )

                    # Validate RPC response format
                    try:
                        rpc_response = RPCResponse(**json_data)
                    except Exception as e:
                        raise RPCError(
                            f"Invalid RPC response format: {e}",
                            method=method,
                            response_data=json_data
                        )

                    # Handle RPC errors
                    if rpc_response.error:
                        error = rpc_response.error
                        error_code = error.get('code', -1)
                        error_message = error.get('message', 'Unknown RPC error')

                        # Map specific error codes to appropriate exceptions
                        if error_code == -32000:  # No path found
                            raise NoPathFoundError(
                                error_message,
                                details={'rpc_error': error}
                            )
                        elif error_code == -32001:  # Insufficient balance
                            raise InsufficientBalanceError(
                                error_message,
                                details={'rpc_error': error}
                            )
                        else:
                            raise PathfindingError(
                                f"RPC error {error_code}: {error_message}",
                                details={'rpc_error': error}
                            )

                    return rpc_response.result

            except (ClientError, asyncio.TimeoutError) as e:
                last_exception = e
                if attempt < self.config.max_retries:
                    delay = self.config.retry_delay * (2 ** attempt)  # Exponential backoff
                    logger.warning(f"RPC call failed, retrying in {delay}s: {e}")
                    await asyncio.sleep(delay)
                    continue
                break

            except (RPCError, PathfindingError, RateLimitError):
                # Don't retry RPC-level errors
                raise

        # All retries failed
        if isinstance(last_exception, asyncio.TimeoutError):
            raise SDKTimeoutError(
                f"RPC call timed out after {self.config.max_retries + 1} attempts",
                timeout_duration=self.config.request_timeout
            )
        else:
            raise NetworkError(
                f"Network error after {self.config.max_retries + 1} attempts: {last_exception}"
            )

    async def find_path(self, params: FindPathParams) -> PathfindingResult:
        """Find a path between source and destination.

        Args:
            params: Pathfinding parameters

        Returns:
            Pathfinding result with transfers

        Raises:
            PathfindingError: Pathfinding failed
            NoPathFoundError: No path could be found
            InsufficientBalanceError: Insufficient balance
        """
        logger.info(f"Finding path from {params.from_addr} to {params.to_addr}, amount: {params.target_flow}")

        # Build RPC parameters
        rpc_params = {
            'Source': params.from_addr,
            'Sink': params.to_addr,
            'TargetFlow': params.target_flow,
            'WithWrap': params.use_wrapped_balances
        }

        # Add optional parameters
        if params.from_tokens is not None:
            rpc_params['FromTokens'] = params.from_tokens
        if params.to_tokens is not None:
            rpc_params['ToTokens'] = params.to_tokens
        if params.exclude_from_tokens is not None:
            rpc_params['ExcludedFromTokens'] = params.exclude_from_tokens
        if params.exclude_to_tokens is not None:
            rpc_params['ExcludedToTokens'] = params.exclude_to_tokens

        try:
            result = await self._make_rpc_call('circlesV2_findPath', [rpc_params])

            if not result:
                raise NoPathFoundError(
                    f"No path found from {params.from_addr} to {params.to_addr}",
                    from_addr=params.from_addr,
                    to_addr=params.to_addr,
                    amount=params.target_flow
                )

            # Convert to our types
            transfers = []
            for transfer_data in result.get('transfers', []):
                transfer = TransferStep(
                    from_address=transfer_data['from'],
                    to_address=transfer_data['to'],
                    token_owner=transfer_data['tokenOwner'],
                    value=transfer_data['value']
                )
                transfers.append(transfer)
            
            pathfinding_result = PathfindingResult(
                max_flow=result['maxFlow'],
                transfers=transfers
            )

            logger.info(f"Found path with {len(transfers)} steps, max flow: {pathfinding_result.max_flow}")
            return pathfinding_result

        except (PathfindingError, NoPathFoundError, InsufficientBalanceError):
            raise
        except Exception as e:
            raise PathfindingError(
                f"Unexpected error during pathfinding: {e}",
                from_addr=params.from_addr,
                to_addr=params.to_addr,
                amount=params.target_flow
            )

    async def find_max_flow(
        self,
        from_addr: str,
        to_addr: str,
        use_wrapped_balances: bool = False,
        from_tokens: Optional[list] = None,
        to_tokens: Optional[list] = None,
        exclude_from_tokens: Optional[list] = None,
        exclude_to_tokens: Optional[list] = None
    ) -> int:
        """Find the maximum transferable amount between addresses.

        Args:
            from_addr: Source address
            to_addr: Destination address
            use_wrapped_balances: Whether to use wrapped token balances
            from_tokens: Specific tokens to transfer from
            to_tokens: Specific tokens to transfer to
            exclude_from_tokens: Tokens to exclude from source
            exclude_to_tokens: Tokens to exclude from destination

        Returns:
            Maximum transferable amount as integer

        Raises:
            PathfindingError: Pathfinding failed
            NoPathFoundError: No path could be found
        """
        logger.info(f"Finding max flow from {from_addr} to {to_addr}")

        # Use a very large target flow to find maximum
        target_flow = '9999999999999999999999999999999999999'

        params = FindPathParams(
            from_addr=from_addr,
            to_addr=to_addr,
            target_flow=target_flow,
            use_wrapped_balances=use_wrapped_balances,
            from_tokens=from_tokens,
            to_tokens=to_tokens,
            exclude_from_tokens=exclude_from_tokens,
            exclude_to_tokens=exclude_to_tokens
        )

        try:
            result = await self.find_path(params)
            max_flow = int(result.max_flow)
            logger.info(f"Max flow from {from_addr} to {to_addr}: {max_flow}")
            return max_flow

        except NoPathFoundError:
            logger.info(f"No path found from {from_addr} to {to_addr}, max flow: 0")
            return 0

    async def health_check(self) -> bool:
        """Check if the pathfinder service is healthy.

        Returns:
            True if service is healthy, False otherwise
        """
        try:
            # Try a simple RPC call with minimal timeout
            await self._make_rpc_call(
                'net_version',
                [],
                timeout=5.0
            )
            return True
        except Exception as e:
            logger.warning(f"Pathfinder health check failed: {e}")
            return False
