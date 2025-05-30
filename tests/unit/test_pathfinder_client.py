"""Unit tests for PathfinderClient."""

import pytest
import asyncio
from unittest.mock import AsyncMock, Mock, patch
from aiohttp import ClientError, ClientTimeout
import aiohttp

from circles_sdk.core.config import CirclesConfig
from circles_sdk.core.types import FindPathParams
from circles_sdk.pathfinding.client import PathfinderClient
from circles_sdk.core.exceptions import (
    PathfindingError,
    NoPathFoundError,
    InsufficientBalanceError,
    RPCError,
    NetworkError,
    TimeoutError as SDKTimeoutError,
    RateLimitError
)


@pytest.fixture
def config():
    """Test configuration."""
    return CirclesConfig(
        rpc_url="https://rpc.aboutcircles.com/",
        pathfinder_url="https://pathfinder.aboutcircles.com",
        v2_hub_address="0xc12C1E50ABB450d6205Ea2C3Fa861b3B834d13e8",
        chain_id=10200,
        request_timeout=5.0,
        max_retries=2,
        retry_delay=0.1
    )


@pytest.fixture
def client(config):
    """Test client."""
    return PathfinderClient(config)


@pytest.fixture
def mock_response():
    """Mock aiohttp response."""
    response = Mock()
    response.status = 200
    response.headers = {}
    return response


class TestPathfinderClientInit:
    """Test PathfinderClient initialization."""

    def test_init(self, config):
        """Test client initialization."""
        client = PathfinderClient(config)
        assert client.config == config
        assert client.session is None
        assert not client._closed

    async def test_context_manager(self, client):
        """Test async context manager."""
        assert client.session is None

        async with client as c:
            assert c is client
            assert client.session is not None
            assert not client.session.closed

        assert client.session.closed
        assert client._closed


class TestRPCCalls:
    """Test RPC call functionality."""

    @pytest.mark.asyncio
    async def test_successful_rpc_call(self, client, mock_response):
        """Test successful RPC call."""
        expected_result = {"test": "data"}
        mock_response.json = AsyncMock(return_value={
            "jsonrpc": "2.0",
            "id": 1,
            "result": expected_result
        })

        with patch.object(client, '_ensure_session', AsyncMock()):
            with patch.object(client.session, 'post') as mock_post:
                mock_post.return_value.__aenter__ = AsyncMock(return_value=mock_response)
                mock_post.return_value.__aexit__ = AsyncMock(return_value=None)

                result = await client._make_rpc_call("test_method", ["param1", "param2"])

                assert result == expected_result
                mock_post.assert_called_once()

    @pytest.mark.asyncio
    async def test_rpc_error_response(self, client, mock_response):
        """Test RPC error response handling."""
        mock_response.json = AsyncMock(return_value={
            "jsonrpc": "2.0",
            "id": 1,
            "error": {
                "code": -32000,
                "message": "No path found"
            }
        })

        with patch.object(client, '_ensure_session', AsyncMock()):
            with patch.object(client.session, 'post') as mock_post:
                mock_post.return_value.__aenter__ = AsyncMock(return_value=mock_response)
                mock_post.return_value.__aexit__ = AsyncMock(return_value=None)

                with pytest.raises(NoPathFoundError):
                    await client._make_rpc_call("test_method", [])

    @pytest.mark.asyncio
    async def test_insufficient_balance_error(self, client, mock_response):
        """Test insufficient balance error handling."""
        mock_response.json = AsyncMock(return_value={
            "jsonrpc": "2.0",
            "id": 1,
            "error": {
                "code": -32001,
                "message": "Insufficient balance"
            }
        })

        with patch.object(client, '_ensure_session', AsyncMock()):
            with patch.object(client.session, 'post') as mock_post:
                mock_post.return_value.__aenter__ = AsyncMock(return_value=mock_response)
                mock_post.return_value.__aexit__ = AsyncMock(return_value=None)

                with pytest.raises(InsufficientBalanceError):
                    await client._make_rpc_call("test_method", [])

    @pytest.mark.asyncio
    async def test_http_error(self, client, mock_response):
        """Test HTTP error handling."""
        mock_response.status = 500
        mock_response.text = AsyncMock(return_value="Internal Server Error")

        with patch.object(client, '_ensure_session', AsyncMock()):
            with patch.object(client.session, 'post') as mock_post:
                mock_post.return_value.__aenter__ = AsyncMock(return_value=mock_response)
                mock_post.return_value.__aexit__ = AsyncMock(return_value=None)

                with pytest.raises(RPCError) as exc_info:
                    await client._make_rpc_call("test_method", [])

                assert exc_info.value.status_code == 500

    @pytest.mark.asyncio
    async def test_rate_limit_handling(self, client, mock_response):
        """Test rate limit error handling."""
        mock_response.status = 429
        mock_response.headers = {"Retry-After": "60"}

        with patch.object(client, '_ensure_session', AsyncMock()):
            with patch.object(client.session, 'post') as mock_post:
                mock_post.return_value.__aenter__ = AsyncMock(return_value=mock_response)
                mock_post.return_value.__aexit__ = AsyncMock(return_value=None)

                with pytest.raises(RateLimitError) as exc_info:
                    await client._make_rpc_call("test_method", [])

                assert exc_info.value.retry_after == 60

    @pytest.mark.asyncio
    async def test_network_error_with_retries(self, client):
        """Test network error with retry logic."""
        with patch.object(client, '_ensure_session', AsyncMock()):
            client.session = Mock()
            client.session.post.side_effect = ClientError("Connection failed")

            with pytest.raises(NetworkError):
                await client._make_rpc_call("test_method", [])

    @pytest.mark.asyncio
    async def test_timeout_error(self, client):
        """Test timeout error handling."""
        with patch.object(client, '_ensure_session', AsyncMock()):
            client.session = Mock()
            client.session.post.side_effect = asyncio.TimeoutError()

            with pytest.raises(SDKTimeoutError):
                await client._make_rpc_call("test_method", [])


class TestFindPath:
    """Test find_path functionality."""

    @pytest.mark.asyncio
    async def test_successful_find_path(self, client):
        """Test successful path finding."""
        mock_result = {
            "maxFlow": "1000",
            "transfers": [
                {
                    "from": "0x1111111111111111111111111111111111111111",
                    "to": "0x2222222222222222222222222222222222222222",
                    "tokenOwner": "0x3333333333333333333333333333333333333333",
                    "value": "1000"
                }
            ]
        }

        with patch.object(client, '_make_rpc_call', AsyncMock(return_value=mock_result)):

            params = FindPathParams(
                from_addr="0x1111111111111111111111111111111111111111",
                to_addr="0x2222222222222222222222222222222222222222",
                target_flow="1000",
                use_wrapped_balances=False
            )

            result = await client.find_path(params)

            assert result.max_flow == "1000"
            assert len(result.transfers) == 1
            assert result.transfers[0].from_address == "0x1111111111111111111111111111111111111111"

    @pytest.mark.asyncio
    async def test_no_path_found(self, client):
        """Test no path found scenario."""
        with patch.object(client, '_make_rpc_call', AsyncMock(return_value=None)):

            params = FindPathParams(
                from_addr="0x1111111111111111111111111111111111111111",
                to_addr="0x2222222222222222222222222222222222222222",
                target_flow="1000"
            )

            with pytest.raises(NoPathFoundError):
                await client.find_path(params)


class TestFindMaxFlow:
    """Test find_max_flow functionality."""

    @pytest.mark.asyncio
    async def test_successful_max_flow(self, client):
        """Test successful max flow calculation."""
        mock_result = {
            "maxFlow": "5000",
            "transfers": []
        }

        with patch.object(client, '_make_rpc_call', AsyncMock(return_value=mock_result)):
            result = await client.find_max_flow(
                "0x1111111111111111111111111111111111111111",
                "0x2222222222222222222222222222222222222222"
            )

            assert result == 5000

    @pytest.mark.asyncio
    async def test_no_path_max_flow(self, client):
        """Test max flow when no path exists."""
        with patch.object(client, 'find_path', AsyncMock(side_effect=NoPathFoundError("No path"))):
            result = await client.find_max_flow(
                "0x1111111111111111111111111111111111111111",
                "0x2222222222222222222222222222222222222222"
            )

            assert result == 0


class TestHealthCheck:
    """Test health check functionality."""

    @pytest.mark.asyncio
    async def test_healthy_service(self, client):
        """Test healthy service check."""
        with patch.object(client, '_make_rpc_call', AsyncMock(return_value="1")):
            result = await client.health_check()
            assert result is True

    @pytest.mark.asyncio
    async def test_unhealthy_service(self, client):
        """Test unhealthy service check."""
        with patch.object(client, '_make_rpc_call', AsyncMock(side_effect=RPCError("Failed"))):
            result = await client.health_check()
            assert result is False


class TestRetryLogic:
    """Test retry logic."""

    @pytest.mark.asyncio
    async def test_retry_on_network_error(self, client):
        """Test retry behavior on network errors."""
        call_count = 0

        def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count <= 2:  # Fail first 2 calls
                raise ClientError("Network error")
            return {"jsonrpc": "2.0", "id": 1, "result": "success"}

        mock_response = Mock()
        mock_response.status = 200
        mock_response.json = AsyncMock(side_effect=side_effect)

        with patch.object(client, '_ensure_session', AsyncMock()):
            with patch.object(client.session, 'post') as mock_post:
                mock_post.side_effect = side_effect

                # Should eventually succeed after retries
                with pytest.raises(NetworkError):  # Will fail since we exceed max_retries
                    await client._make_rpc_call("test_method", [])

                # Should have tried max_retries + 1 times
                assert call_count == client.config.max_retries + 1
