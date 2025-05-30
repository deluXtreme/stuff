#!/usr/bin/env python3
"""
Phase 1 Example: Basic Pathfinding and Flow Matrix Creation

This example demonstrates the core Phase 1 functionality:
- Pathfinder RPC integration
- Simple transfers without wrapped token support
- Flow matrix creation and ABI encoding
- Basic error handling

Requirements:
- Set environment variables for configuration
- Network access to pathfinder service
"""

import asyncio
import logging
import os
from pathlib import Path
import sys

# Add the src directory to the path so we can import the SDK modules
project_dir = Path(__file__).parent.parent
src_dir = project_dir / "src"
sys.path.insert(0, str(src_dir))

from circles_sdk.core.config import CirclesConfig
from circles_sdk.core.types import FindPathParams
from circles_sdk.transfers.simple import SimpleTransfer, simple_transfer, simple_transfer_to_abi
from circles_sdk.pathfinding.client import PathfinderClient
from circles_sdk.core.exceptions import PathfindingError, ValidationError, NoPathFoundError, InsufficientBalanceError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def example_basic_pathfinder_usage():
    """Demonstrate basic pathfinder client usage."""
    print("\n=== Basic Pathfinder Client Example ===")

    # Create configuration (using testnet for safety)
    config = CirclesConfig.testnet()

    # Test addresses (these would be real addresses in practice)
    from_addr = "0x1111111111111111111111111111111111111111"
    to_addr = "0x2222222222222222222222222222222222222222"

    async with PathfinderClient(config) as client:
        try:
            # Check if pathfinder service is healthy
            is_healthy = await client.health_check()
            print(f"Pathfinder service healthy: {is_healthy}")

            if not is_healthy:
                print("⚠️  Pathfinder service appears to be down")
                return

            # Find maximum transferable amount
            max_flow = await client.find_max_flow(from_addr, to_addr)
            print(f"Maximum transferable amount: {max_flow}")

            if max_flow > 0:
                # Find a specific path
                params = FindPathParams(
                    from_addr=from_addr,
                    to_addr=to_addr,
                    target_flow=str(min(max_flow, 1000)),  # Transfer up to 1000 or max available
                    use_wrapped_balances=False
                )

                path_result = await client.find_path(params)
                print(f"Found path with {len(path_result.transfers)} steps")
                print(f"Actual flow: {path_result.max_flow}")

                for i, transfer in enumerate(path_result.transfers):
                    print(f"  Step {i+1}: {transfer.from_address} -> {transfer.to_address}")
                    print(f"    Token: {transfer.token_owner}, Amount: {transfer.value}")
            else:
                print("No transferable amount available between these addresses")

        except NoPathFoundError:
            print("❌ No path found between addresses")
        except InsufficientBalanceError:
            print("❌ Insufficient balance for transfer")
        except PathfindingError as e:
            print(f"❌ Pathfinding error: {e}")
        except Exception as e:
            print(f"❌ Unexpected error: {e}")


async def example_simple_transfer_class():
    """Demonstrate SimpleTransfer class usage."""
    print("\n=== SimpleTransfer Class Example ===")

    # Create configuration
    config = CirclesConfig.testnet()

    # Test addresses
    from_addr = "0x3333333333333333333333333333333333333333"
    to_addr = "0x4444444444444444444444444444444444444444"
    amount = "500"

    async with SimpleTransfer(config) as transfer_client:
        try:
            # Check maximum transferable amount first
            max_amount = await transfer_client.get_max_transferable_amount(from_addr, to_addr)
            print(f"Maximum transferable: {max_amount}")

            if max_amount == 0:
                print("No funds available for transfer")
                return

            # Adjust amount if necessary
            transfer_amount = str(min(int(amount), max_amount))
            print(f"Transferring: {transfer_amount}")

            # Execute transfer and get flow matrix
            flow_matrix = await transfer_client.transfer(
                from_addr=from_addr,
                to_addr=to_addr,
                amount=transfer_amount,
                use_wrapped_balances=False
            )

            print("✅ Transfer successful!")
            print("Flow matrix created with:")
            print(f"  - {len(flow_matrix.flow_vertices)} vertices")
            print(f"  - {len(flow_matrix.flow_edges)} edges")
            print(f"  - {len(flow_matrix.streams)} streams")
            print(f"  - Packed coordinates: {len(flow_matrix.packed_coordinates)} bytes")

            # Convert to ABI format
            abi_data = await transfer_client.transfer_to_abi(from_addr, to_addr, transfer_amount)
            print("\nABI-encoded data ready for smart contract:")
            print(f"  - Flow vertices: {len(abi_data['_flowVertices'])} addresses")
            print(f"  - Flow edges: {len(abi_data['_flow'])} edges")
            print(f"  - Streams: {len(abi_data['_streams'])} streams")
            print(f"  - Packed coordinates: {abi_data['_packedCoordinates']}")

        except ValidationError as e:
            print(f"❌ Validation error: {e}")
        except PathfindingError as e:
            print(f"❌ Transfer failed: {e}")
        except Exception as e:
            print(f"❌ Unexpected error: {e}")


async def example_convenience_functions():
    """Demonstrate convenience functions."""
    print("\n=== Convenience Functions Example ===")

    # Create configuration
    config = CirclesConfig.testnet()

    # Test addresses
    from_addr = "0x5555555555555555555555555555555555555555"
    to_addr = "0x6666666666666666666666666666666666666666"
    amount = "100"

    try:
        # Simple transfer using convenience function
        flow_matrix = await simple_transfer(
            config=config,
            from_addr=from_addr,
            to_addr=to_addr,
            amount=amount,
            use_wrapped_balances=False
        )

        print("✅ Convenience transfer successful!")
        print(f"Created flow matrix with {len(flow_matrix.flow_vertices)} vertices")

        # Get ABI data directly
        abi_data = await simple_transfer_to_abi(
            config=config,
            from_addr=from_addr,
            to_addr=to_addr,
            amount=amount
        )

        print("✅ ABI data generated!")
        print(f"Ready for contract call with {len(abi_data['_flowVertices'])} vertices")

    except Exception as e:
        print(f"❌ Convenience function error: {e}")


async def example_error_handling():
    """Demonstrate error handling scenarios."""
    print("\n=== Error Handling Examples ===")

    config = CirclesConfig.testnet()

    # Test various error scenarios
    test_cases = [
        {
            "name": "Invalid from address",
            "from_addr": "invalid_address",
            "to_addr": "0x2222222222222222222222222222222222222222",
            "amount": "100"
        },
        {
            "name": "Invalid to address",
            "from_addr": "0x1111111111111111111111111111111111111111",
            "to_addr": "not_an_address",
            "amount": "100"
        },
        {
            "name": "Invalid amount",
            "from_addr": "0x1111111111111111111111111111111111111111",
            "to_addr": "0x2222222222222222222222222222222222222222",
            "amount": "not_a_number"
        },
        {
            "name": "Same source and destination",
            "from_addr": "0x1111111111111111111111111111111111111111",
            "to_addr": "0x1111111111111111111111111111111111111111",
            "amount": "100"
        },
        {
            "name": "Negative amount",
            "from_addr": "0x1111111111111111111111111111111111111111",
            "to_addr": "0x2222222222222222222222222222222222222222",
            "amount": "-100"
        }
    ]

    async with SimpleTransfer(config) as transfer_client:
        for test_case in test_cases:
            try:
                await transfer_client.transfer(**test_case)
                print(f"❌ {test_case['name']}: Should have failed but didn't")
            except ValidationError as e:
                print(f"✅ {test_case['name']}: Correctly caught validation error")
            except PathfindingError as e:
                print(f"✅ {test_case['name']}: Correctly caught pathfinding error")
            except Exception as e:
                print(f"⚠️  {test_case['name']}: Unexpected error: {e}")


async def example_configuration_options():
    """Demonstrate different configuration options."""
    print("\n=== Configuration Options Example ===")

    # Environment-based configuration
    print("1. Environment-based configuration:")
    try:
        env_config = CirclesConfig.from_env()
        print(f"   RPC URL: {env_config.rpc_url}")
        print(f"   Pathfinder URL: {env_config.pathfinder_url}")
        print(f"   Chain ID: {env_config.chain_id}")
    except Exception as e:
        print(f"   Error loading from environment: {e}")

    # Testnet configuration
    print("\n2. Testnet configuration:")
    testnet_config = CirclesConfig.testnet()
    print(f"   RPC URL: {testnet_config.rpc_url}")
    print(f"   Pathfinder URL: {testnet_config.pathfinder_url}")
    print(f"   Chain ID: {testnet_config.chain_id}")

    # Mainnet configuration
    print("\n3. Mainnet configuration:")
    mainnet_config = CirclesConfig.mainnet()
    print(f"   RPC URL: {mainnet_config.rpc_url}")
    print(f"   Pathfinder URL: {mainnet_config.pathfinder_url}")
    print(f"   Chain ID: {mainnet_config.chain_id}")

    # Custom configuration
    print("\n4. Custom configuration:")
    custom_config = CirclesConfig(
        rpc_url="https://custom-rpc.example.com",
        pathfinder_url="https://custom-pathfinder.example.com",
        v2_hub_address="0x1234567890123456789012345678901234567890",
        chain_id=12345,
        request_timeout=60.0,
        max_retries=5
    )
    print(f"   Custom RPC URL: {custom_config.rpc_url}")
    print(f"   Custom timeout: {custom_config.request_timeout}s")
    print(f"   Custom retries: {custom_config.max_retries}")


async def main():
    """Run all Phase 1 examples."""
    print("🚀 Circles SDK Phase 1 Examples")
    print("=" * 50)

    try:
        await example_configuration_options()
        await example_basic_pathfinder_usage()
        await example_simple_transfer_class()
        await example_convenience_functions()
        await example_error_handling()

        print("\n" + "=" * 50)
        print("✅ All Phase 1 examples completed successfully!")
        print("\nPhase 1 provides:")
        print("• Basic pathfinder RPC integration")
        print("• Simple transfer functionality")
        print("• Flow matrix creation and ABI encoding")
        print("• Comprehensive error handling")
        print("• Multiple configuration options")

    except Exception as e:
        print(f"\n❌ Example failed with error: {e}")
        logger.exception("Example execution failed")


if __name__ == "__main__":
    # Set up example environment variables if not already set
    if not os.environ.get('CIRCLES_PATHFINDER_URL'):
        os.environ['CIRCLES_PATHFINDER_URL'] = 'https://pathfinder-chiado.circles.org'
    if not os.environ.get('CIRCLES_RPC_URL'):
        os.environ['CIRCLES_RPC_URL'] = 'https://rpc.chiado.gnosischain.com'
    if not os.environ.get('CIRCLES_V2_HUB_ADDRESS'):
        os.environ['CIRCLES_V2_HUB_ADDRESS'] = '0x1234567890123456789012345678901234567890'

    # Run the examples
    asyncio.run(main())
