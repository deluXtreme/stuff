"""Unit tests for SimpleTransfer."""

import pytest
import asyncio
from unittest.mock import AsyncMock, Mock, patch

from circles_sdk.core.config import CirclesConfig
from circles_sdk.core.types import PathfindingResult, TransferStep
from circles_sdk.transfers.simple import SimpleTransfer, simple_transfer, simple_transfer_to_abi
from circles_sdk.core.exceptions import ValidationError, PathfindingError
from circles_sdk.core.flow_matrix import FlowMatrix, FlowEdge, Stream


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
def simple_transfer_client(config):
    """Test SimpleTransfer client."""
    return SimpleTransfer(config)


@pytest.fixture
def mock_pathfinding_result():
    """Mock pathfinding result."""
    transfer = TransferStep(
        from_address="0x1111111111111111111111111111111111111111",
        to_address="0x2222222222222222222222222222222222222222",
        token_owner="0x3333333333333333333333333333333333333333",
        value="1000"
    )

    return PathfindingResult(
        max_flow="1000",
        transfers=[transfer]
    )


@pytest.fixture
def mock_flow_matrix():
    """Mock flow matrix."""
    return FlowMatrix(
        flow_vertices=[
            "0x1111111111111111111111111111111111111111",
            "0x2222222222222222222222222222222222222222",
            "0x3333333333333333333333333333333333333333"
        ],
        flow_edges=[
            FlowEdge(stream_sink_id=1, amount="1000")
        ],
        streams=[
            Stream(source_coordinate=0, flow_edge_ids=[0], data=b'')
        ],
        packed_coordinates=b'\x00\x02\x00\x00\x00\x01',
        source_coordinate=0
    )


class TestSimpleTransferInit:
    """Test SimpleTransfer initialization."""

    def test_init(self, config):
        """Test client initialization."""
        client = SimpleTransfer(config)
        assert client.config == config
        assert client.pathfinder is not None

    async def test_context_manager(self, simple_transfer_client):
        """Test async context manager."""
        with patch.object(simple_transfer_client.pathfinder, '_ensure_session', AsyncMock()):
            with patch.object(simple_transfer_client.pathfinder, 'close', AsyncMock()):
                async with simple_transfer_client as client:
                    assert client is simple_transfer_client


class TestValidation:
    """Test parameter validation."""

    def test_validate_transfer_params_success(self, simple_transfer_client):
        """Test successful parameter validation."""
        # Should not raise any exception
        simple_transfer_client._validate_transfer_params(
            "0x1111111111111111111111111111111111111111",
            "0x2222222222222222222222222222222222222222",
            "1000"
        )

    def test_validate_invalid_from_address(self, simple_transfer_client):
        """Test validation with invalid from address."""
        with pytest.raises(ValidationError) as exc_info:
            simple_transfer_client._validate_transfer_params(
                "invalid_address",
                "0x2222222222222222222222222222222222222222",
                "1000"
            )
        assert "Invalid from_addr" in str(exc_info.value)

    def test_validate_invalid_to_address(self, simple_transfer_client):
        """Test validation with invalid to address."""
        with pytest.raises(ValidationError) as exc_info:
            simple_transfer_client._validate_transfer_params(
                "0x1111111111111111111111111111111111111111",
                "not_an_address",
                "1000"
            )
        assert "Invalid to_addr" in str(exc_info.value)

    def test_validate_invalid_amount(self, simple_transfer_client):
        """Test validation with invalid amount."""
        with pytest.raises(ValidationError) as exc_info:
            simple_transfer_client._validate_transfer_params(
                "0x1111111111111111111111111111111111111111",
                "0x2222222222222222222222222222222222222222",
                "not_a_number"
            )
        assert "Amount must be a valid integer string" in str(exc_info.value)

    def test_validate_negative_amount(self, simple_transfer_client):
        """Test validation with negative amount."""
        with pytest.raises(ValidationError) as exc_info:
            simple_transfer_client._validate_transfer_params(
                "0x1111111111111111111111111111111111111111",
                "0x2222222222222222222222222222222222222222",
                "-100"
            )
        assert "Amount must be positive" in str(exc_info.value)

    def test_validate_same_addresses(self, simple_transfer_client):
        """Test validation with same source and destination."""
        with pytest.raises(ValidationError) as exc_info:
            simple_transfer_client._validate_transfer_params(
                "0x1111111111111111111111111111111111111111",
                "0x1111111111111111111111111111111111111111",
                "1000"
            )
        assert "Source and destination addresses must be different" in str(exc_info.value)


class TestTransferConversion:
    """Test transfer format conversion."""

    def test_convert_transfers(self, simple_transfer_client):
        """Test transfer conversion from Pydantic to legacy format."""
        pydantic_transfer = TransferStep(
            from_address="0x1111111111111111111111111111111111111111",
            to_address="0x2222222222222222222222222222222222222222",
            token_owner="0x3333333333333333333333333333333333333333",
            value="1000"
        )

        legacy_transfers = simple_transfer_client._convert_transfers([pydantic_transfer])

        assert len(legacy_transfers) == 1
        legacy_transfer = legacy_transfers[0]
        assert legacy_transfer.from_address == "0x1111111111111111111111111111111111111111"
        assert legacy_transfer.to_address == "0x2222222222222222222222222222222222222222"
        assert legacy_transfer.token_owner == "0x3333333333333333333333333333333333333333"
        assert legacy_transfer.value == "1000"


class TestTransfer:
    """Test main transfer functionality."""

    @pytest.mark.asyncio
    async def test_successful_transfer(self, simple_transfer_client, mock_pathfinding_result, mock_flow_matrix):
        """Test successful transfer."""
        with patch.object(simple_transfer_client.pathfinder, 'find_path', AsyncMock(return_value=mock_pathfinding_result)):
            with patch('simple_transfer.create_flow_matrix', return_value=mock_flow_matrix):
                result = await simple_transfer_client.transfer(
                    "0x1111111111111111111111111111111111111111",
                    "0x2222222222222222222222222222222222222222",
                    "1000"
                )

                assert result == mock_flow_matrix

    @pytest.mark.asyncio
    async def test_transfer_with_options(self, simple_transfer_client, mock_pathfinding_result, mock_flow_matrix):
        """Test transfer with additional options."""
        with patch.object(simple_transfer_client.pathfinder, 'find_path', AsyncMock(return_value=mock_pathfinding_result)):
            with patch('simple_transfer.create_flow_matrix', return_value=mock_flow_matrix):
                result = await simple_transfer_client.transfer(
                    "0x1111111111111111111111111111111111111111",
                    "0x2222222222222222222222222222222222222222",
                    "1000",
                    use_wrapped_balances=True,
                    from_tokens=["0x4444444444444444444444444444444444444444"],
                    exclude_from_tokens=["0x5555555555555555555555555555555555555555"]
                )

                assert result == mock_flow_matrix

    @pytest.mark.asyncio
    async def test_transfer_validation_error(self, simple_transfer_client):
        """Test transfer with validation error."""
        with pytest.raises(ValidationError):
            await simple_transfer_client.transfer(
                "invalid_address",
                "0x2222222222222222222222222222222222222222",
                "1000"
            )

    @pytest.mark.asyncio
    async def test_transfer_pathfinding_error(self, simple_transfer_client):
        """Test transfer with pathfinding error."""
        with patch.object(simple_transfer_client.pathfinder, 'find_path', AsyncMock(side_effect=PathfindingError("Failed"))):
            with pytest.raises(PathfindingError):
                await simple_transfer_client.transfer(
                    "0x1111111111111111111111111111111111111111",
                    "0x2222222222222222222222222222222222222222",
                    "1000"
                )

    @pytest.mark.asyncio
    async def test_transfer_unexpected_error(self, simple_transfer_client, mock_pathfinding_result):
        """Test transfer with unexpected error."""
        with patch.object(simple_transfer_client.pathfinder, 'find_path', AsyncMock(return_value=mock_pathfinding_result)):
            with patch('simple_transfer.create_flow_matrix', side_effect=Exception("Unexpected error")):
                with pytest.raises(PathfindingError) as exc_info:
                    await simple_transfer_client.transfer(
                        "0x1111111111111111111111111111111111111111",
                        "0x2222222222222222222222222222222222222222",
                        "1000"
                    )

                assert "Unexpected error during transfer" in str(exc_info.value)


class TestMaxTransferableAmount:
    """Test max transferable amount functionality."""

    @pytest.mark.asyncio
    async def test_successful_max_amount(self, simple_transfer_client):
        """Test successful max amount calculation."""
        with patch.object(simple_transfer_client.pathfinder, 'find_max_flow', AsyncMock(return_value=5000)):
            result = await simple_transfer_client.get_max_transferable_amount(
                "0x1111111111111111111111111111111111111111",
                "0x2222222222222222222222222222222222222222"
            )

            assert result == 5000

    @pytest.mark.asyncio
    async def test_max_amount_with_options(self, simple_transfer_client):
        """Test max amount with additional options."""
        with patch.object(simple_transfer_client.pathfinder, 'find_max_flow', AsyncMock(return_value=3000)) as mock_find:
            result = await simple_transfer_client.get_max_transferable_amount(
                "0x1111111111111111111111111111111111111111",
                "0x2222222222222222222222222222222222222222",
                use_wrapped_balances=True,
                from_tokens=["0x4444444444444444444444444444444444444444"]
            )

            assert result == 3000
            mock_find.assert_called_once()

    @pytest.mark.asyncio
    async def test_max_amount_validation_error(self, simple_transfer_client):
        """Test max amount with validation error."""
        with pytest.raises(ValidationError):
            await simple_transfer_client.get_max_transferable_amount(
                "invalid_address",
                "0x2222222222222222222222222222222222222222"
            )

    @pytest.mark.asyncio
    async def test_max_amount_pathfinding_error(self, simple_transfer_client):
        """Test max amount with pathfinding error."""
        with patch.object(simple_transfer_client.pathfinder, 'find_max_flow', AsyncMock(side_effect=PathfindingError("Failed"))):
            with pytest.raises(PathfindingError):
                await simple_transfer_client.get_max_transferable_amount(
                    "0x1111111111111111111111111111111111111111",
                    "0x2222222222222222222222222222222222222222"
                )


class TestTransferToABI:
    """Test transfer to ABI functionality."""

    @pytest.mark.asyncio
    async def test_transfer_to_abi(self, simple_transfer_client, mock_flow_matrix):
        """Test transfer to ABI conversion."""
        expected_abi = {
            "_flowVertices": ["0x1111111111111111111111111111111111111111"],
            "_flow": [{"streamSinkId": 1, "amount": 1000}],
            "_streams": [{"sourceCoordinate": 0, "flowEdgeIds": [0], "data": "0x"}],
            "_packedCoordinates": "0x000200000001"
        }

        with patch.object(simple_transfer_client, 'transfer', AsyncMock(return_value=mock_flow_matrix)):
            with patch('simple_transfer.flow_matrix_to_abi_hex', return_value=expected_abi):
                result = await simple_transfer_client.transfer_to_abi(
                    "0x1111111111111111111111111111111111111111",
                    "0x2222222222222222222222222222222222222222",
                    "1000"
                )

                assert result == expected_abi


class TestHealthCheck:
    """Test health check functionality."""

    @pytest.mark.asyncio
    async def test_healthy_service(self, simple_transfer_client):
        """Test healthy service check."""
        with patch.object(simple_transfer_client.pathfinder, 'health_check', AsyncMock(return_value=True)):
            result = await simple_transfer_client.health_check()
            assert result is True

    @pytest.mark.asyncio
    async def test_unhealthy_service(self, simple_transfer_client):
        """Test unhealthy service check."""
        with patch.object(simple_transfer_client.pathfinder, 'health_check', AsyncMock(return_value=False)):
            result = await simple_transfer_client.health_check()
            assert result is False

    @pytest.mark.asyncio
    async def test_health_check_exception(self, simple_transfer_client):
        """Test health check with exception."""
        with patch.object(simple_transfer_client.pathfinder, 'health_check', AsyncMock(side_effect=Exception("Error"))):
            result = await simple_transfer_client.health_check()
            assert result is False


class TestConvenienceFunctions:
    """Test convenience functions."""

    @pytest.mark.asyncio
    async def test_simple_transfer_function(self, config, mock_flow_matrix):
        """Test simple_transfer convenience function."""
        with patch('simple_transfer.SimpleTransfer') as mock_class:
            mock_instance = AsyncMock()
            mock_instance.transfer = AsyncMock(return_value=mock_flow_matrix)
            mock_class.return_value.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_class.return_value.__aexit__ = AsyncMock(return_value=None)

            result = await simple_transfer(
                config,
                "0x1111111111111111111111111111111111111111",
                "0x2222222222222222222222222222222222222222",
                "1000"
            )

            assert result == mock_flow_matrix

    @pytest.mark.asyncio
    async def test_simple_transfer_to_abi_function(self, config):
        """Test simple_transfer_to_abi convenience function."""
        expected_abi = {"test": "abi"}

        with patch('simple_transfer.SimpleTransfer') as mock_class:
            mock_instance = AsyncMock()
            mock_instance.transfer_to_abi = AsyncMock(return_value=expected_abi)
            mock_class.return_value.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_class.return_value.__aexit__ = AsyncMock(return_value=None)

            result = await simple_transfer_to_abi(
                config,
                "0x1111111111111111111111111111111111111111",
                "0x2222222222222222222222222222222222222222",
                "1000"
            )

            assert result == expected_abi


class TestEdgeCases:
    """Test edge cases and special scenarios."""

    @pytest.mark.asyncio
    async def test_address_case_normalization(self, simple_transfer_client, mock_pathfinding_result, mock_flow_matrix):
        """Test address case normalization."""
        with patch.object(simple_transfer_client.pathfinder, 'find_path', AsyncMock(return_value=mock_pathfinding_result)) as mock_find:
            with patch('simple_transfer.create_flow_matrix', return_value=mock_flow_matrix):
                await simple_transfer_client.transfer(
                    "0X1111111111111111111111111111111111111111",  # Uppercase
                    "0x2222222222222222222222222222222222222222",
                    "1000"
                )

                # Should have been called with lowercase addresses
                call_args = mock_find.call_args[0][0]
                assert call_args.from_addr == "0x1111111111111111111111111111111111111111"

    @pytest.mark.asyncio
    async def test_large_amount(self, simple_transfer_client, mock_pathfinding_result, mock_flow_matrix):
        """Test transfer with very large amount."""
        large_amount = "999999999999999999999999999999"

        with patch.object(simple_transfer_client.pathfinder, 'find_path', AsyncMock(return_value=mock_pathfinding_result)):
            with patch('simple_transfer.create_flow_matrix', return_value=mock_flow_matrix):
                result = await simple_transfer_client.transfer(
                    "0x1111111111111111111111111111111111111111",
                    "0x2222222222222222222222222222222222222222",
                    large_amount
                )

                assert result == mock_flow_matrix

    @pytest.mark.asyncio
    async def test_minimal_amount(self, simple_transfer_client, mock_pathfinding_result, mock_flow_matrix):
        """Test transfer with minimal amount."""
        with patch.object(simple_transfer_client.pathfinder, 'find_path', AsyncMock(return_value=mock_pathfinding_result)):
            with patch('simple_transfer.create_flow_matrix', return_value=mock_flow_matrix):
                result = await simple_transfer_client.transfer(
                    "0x1111111111111111111111111111111111111111",
                    "0x2222222222222222222222222222222222222222",
                    "1"
                )

                assert result == mock_flow_matrix
