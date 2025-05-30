#!/usr/bin/env python3
"""
CirclesAvatar Usage Examples

This file demonstrates how to use the CirclesAvatar high-level interface
for common Circles protocol operations.
"""

import asyncio
import sys
from pathlib import Path

# Add src directory to path
src_path = str(Path("../src").absolute())
if src_path not in sys.path:
    sys.path.insert(0, src_path)

current_src = str(Path("src").absolute())
if current_src not in sys.path:
    sys.path.insert(0, current_src)

from circles_sdk import CirclesAvatar, CirclesConfig


async def example_1_basic_avatar_setup():
    """Example 1: Basic avatar setup and configuration."""
    print("Example 1: Basic Avatar Setup")
    print("-" * 40)
    
    # Method 1: Use default production configuration
    avatar_default = CirclesAvatar("0xDE374ece6fA50e781E81Aac78e811b33D16912c7")
    print(f"Avatar with default config: {avatar_default}")
    
    # Method 2: Use custom configuration
    custom_config = CirclesConfig(
        rpc_url="https://rpc.circlesubi.network",
        pathfinder_url="https://pathfinder.aboutcircles.com",
        v2_hub_address="0xc12C1E50ABB450d6205Ea2C3Fa861b3B834d13e8",
        chain_id=100,
        request_timeout=30.0
    )
    
    avatar_custom = CirclesAvatar(
        address="0xDE374ece6fA50e781E81Aac78e811b33D16912c7",
        config=custom_config,
        cache_size=500  # Smaller cache for this example
    )
    print(f"Avatar with custom config: {avatar_custom}")
    
    # Check cache stats
    cache_stats = avatar_custom.get_cache_stats()
    print(f"Initial cache stats: {cache_stats}")


async def example_2_simple_transfer():
    """Example 2: Simple high-level transfer."""
    print("\nExample 2: Simple Transfer")
    print("-" * 40)
    
    # Real addresses from production validation
    from_addr = "0xDE374ece6fA50e781E81Aac78e811b33D16912c7"
    to_addr = "0x626389c375befb331333f2cb9ef79fb2218a0176"
    
    avatar = CirclesAvatar(from_addr)
    
    async with avatar:
        try:
            # Check maximum transferable amount first
            max_amount = await avatar.get_max_transferable_amount(to_addr)
            print(f"Maximum transferable: {max_amount / 1e18:.6f} CRC")
            
            if max_amount > 0:
                # Transfer a small amount
                transfer_amount = min(max_amount, int(0.1 * 1e18))  # 0.1 CRC or max available
                
                flow_matrix = await avatar.transfer(
                    to=to_addr,
                    amount=transfer_amount,
                    use_wrapped_balances=True
                )
                
                print(f"Transfer successful!")
                print(f"  Amount: {transfer_amount / 1e18:.6f} CRC")
                print(f"  Flow matrix: {len(flow_matrix.streams)} streams")
                print(f"  Vertices: {len(flow_matrix.flow_vertices)}")
                print(f"  Edges: {len(flow_matrix.flow_edges)}")
            else:
                print("No transferable amount available")
                
        except Exception as e:
            print(f"Transfer failed: {e}")


async def example_3_transfer_with_transactions():
    """Example 3: Transfer with complete transaction details."""
    print("\nExample 3: Transfer with Transaction Details")
    print("-" * 50)
    
    from_addr = "0xDE374ece6fA50e781E81Aac78e811b33D16912c7"
    to_addr = "0x626389c375befb331333f2cb9ef79fb2218a0176"
    
    avatar = CirclesAvatar(from_addr)
    
    async with avatar:
        try:
            transfer_amount = int(0.05 * 1e18)  # 0.05 CRC
            
            flow_matrix, transactions = await avatar.transfer_with_transactions(
                to=to_addr,
                amount=transfer_amount,
                use_wrapped_balances=True
            )
            
            print(f"Transfer with transactions prepared:")
            print(f"  Amount: {transfer_amount / 1e18:.6f} CRC")
            print(f"  Transaction count: {len(transactions)}")
            
            for i, tx in enumerate(transactions):
                print(f"  Transaction {i+1}:")
                print(f"    To: {tx.to}")
                print(f"    Data length: {len(tx.data)} bytes")
                print(f"    Value: {tx.value} wei")
                
            print(f"  Flow matrix: {len(flow_matrix.streams)} streams")
            
        except Exception as e:
            print(f"Transfer with transactions failed: {e}")


async def example_4_gas_estimation():
    """Example 4: Gas cost estimation."""
    print("\nExample 4: Gas Cost Estimation")
    print("-" * 40)
    
    from_addr = "0xDE374ece6fA50e781E81Aac78e811b33D16912c7"
    to_addr = "0x626389c375befb331333f2cb9ef79fb2218a0176"
    
    avatar = CirclesAvatar(from_addr)
    
    async with avatar:
        try:
            transfer_amount = int(1.0 * 1e18)  # 1 CRC
            
            gas_estimate = await avatar.estimate_transfer_cost(
                to=to_addr,
                amount=transfer_amount,
                use_wrapped_balances=True
            )
            
            print(f"Gas estimation for {transfer_amount / 1e18:.1f} CRC transfer:")
            print(f"  Transaction count: {gas_estimate['transaction_count']}")
            print(f"  Total estimated gas: {gas_estimate['total_estimated_gas']:,}")
            print(f"  Gas price: {gas_estimate['gas_price_gwei']} gwei")
            print(f"  Estimated cost: {gas_estimate['estimated_cost_eth']:.6f} ETH")
            print(f"  Note: {gas_estimate['note']}")
            
        except Exception as e:
            print(f"Gas estimation failed: {e}")


async def example_5_advanced_options():
    """Example 5: Advanced transfer options."""
    print("\nExample 5: Advanced Transfer Options")
    print("-" * 45)
    
    from_addr = "0xDE374ece6fA50e781E81Aac78e811b33D16912c7"
    to_addr = "0x626389c375befb331333f2cb9ef79fb2218a0176"
    
    avatar = CirclesAvatar(from_addr)
    
    async with avatar:
        try:
            # Check max amount with specific token constraints
            max_amount = await avatar.get_max_transferable_amount(
                to=to_addr,
                use_wrapped_balances=True,
                # from_tokens=["0x..."],  # Specify source tokens
                # exclude_from_tokens=["0x..."],  # Exclude certain tokens
            )
            
            print(f"Max transferable with constraints: {max_amount / 1e18:.6f} CRC")
            
            if max_amount > 0:
                transfer_amount = min(max_amount, int(0.01 * 1e18))  # 0.01 CRC
                
                # Transfer with advanced options
                flow_matrix = await avatar.transfer(
                    to=to_addr,
                    amount=transfer_amount,
                    use_wrapped_balances=True,
                    # from_tokens=None,  # Let pathfinder choose
                    # to_tokens=None,    # Let pathfinder choose
                    # exclude_from_tokens=None,  # No exclusions
                    # exclude_to_tokens=None,    # No exclusions
                )
                
                print(f"Advanced transfer successful!")
                print(f"  Amount: {transfer_amount / 1e18:.6f} CRC")
                print(f"  Streams: {len(flow_matrix.streams)}")
                
        except Exception as e:
            print(f"Advanced transfer failed: {e}")


async def example_6_cache_management():
    """Example 6: Cache management and performance."""
    print("\nExample 6: Cache Management")
    print("-" * 35)
    
    from_addr = "0xDE374ece6fA50e781E81Aac78e811b33D16912c7"
    to_addr = "0x626389c375befb331333f2cb9ef79fb2218a0176"
    
    # Create avatar with small cache for demonstration
    avatar = CirclesAvatar(from_addr, cache_size=10)
    
    async with avatar:
        try:
            print("Initial cache stats:")
            stats = avatar.get_cache_stats()
            print(f"  Cache size: {stats['cache_size']}")
            print(f"  Max size: {stats['max_cache_size']}")
            print(f"  Usage: {stats['cache_usage_percent']:.1f}%")
            
            # Perform a transfer to populate cache
            max_amount = await avatar.get_max_transferable_amount(to_addr)
            
            print("\nAfter pathfinding:")
            stats = avatar.get_cache_stats()
            print(f"  Cache size: {stats['cache_size']}")
            print(f"  Usage: {stats['cache_usage_percent']:.1f}%")
            
            # Clear cache
            avatar.clear_cache()
            
            print("\nAfter cache clear:")
            stats = avatar.get_cache_stats()
            print(f"  Cache size: {stats['cache_size']}")
            print(f"  Usage: {stats['cache_usage_percent']:.1f}%")
            
        except Exception as e:
            print(f"Cache management example failed: {e}")


async def example_7_error_handling():
    """Example 7: Error handling patterns."""
    print("\nExample 7: Error Handling")
    print("-" * 30)
    
    from_addr = "0xDE374ece6fA50e781E81Aac78e811b33D16912c7"
    
    # Test with invalid recipient address
    avatar = CirclesAvatar(from_addr)
    
    async with avatar:
        # Test 1: Invalid address
        try:
            await avatar.transfer(
                to="invalid_address",
                amount=1000000000000000000
            )
        except Exception as e:
            print(f"Expected error for invalid address: {type(e).__name__}: {e}")
        
        # Test 2: Zero amount
        try:
            await avatar.transfer(
                to="0x1111111111111111111111111111111111111111",
                amount=0
            )
        except Exception as e:
            print(f"Expected error for zero amount: {type(e).__name__}: {e}")
        
        # Test 3: Non-existent path (unlikely to have balance)
        try:
            max_amount = await avatar.get_max_transferable_amount(
                to="0x0000000000000000000000000000000000000000"
            )
            print(f"Max amount to zero address: {max_amount}")
        except Exception as e:
            print(f"Error for zero address: {type(e).__name__}: {e}")


async def example_8_multiple_avatars():
    """Example 8: Managing multiple avatars."""
    print("\nExample 8: Multiple Avatars")
    print("-" * 35)
    
    # Create multiple avatars
    addresses = [
        "0xDE374ece6fA50e781E81Aac78e811b33D16912c7",
        "0x626389c375befb331333f2cb9ef79fb2218a0176"
    ]
    
    avatars = []
    for addr in addresses:
        avatar = CirclesAvatar(addr)
        avatars.append(avatar)
    
    # Use them concurrently
    async def check_avatar_balance(avatar, target):
        async with avatar:
            try:
                max_amount = await avatar.get_max_transferable_amount(target)
                return f"{avatar.address[:10]}... -> {target[:10]}...: {max_amount / 1e18:.6f} CRC"
            except Exception as e:
                return f"{avatar.address[:10]}... -> {target[:10]}...: Error - {e}"
    
    # Check balances concurrently
    tasks = []
    for i, avatar in enumerate(avatars):
        # Each avatar checks what it can send to the other
        target = addresses[1 - i]
        task = check_avatar_balance(avatar, target)
        tasks.append(task)
    
    results = await asyncio.gather(*tasks)
    for result in results:
        print(f"  {result}")


async def main():
    """Run all CirclesAvatar examples."""
    print("CirclesAvatar High-Level Interface Examples")
    print("=" * 60)
    print("Demonstrating the clean, intuitive API for Circles protocol operations.")
    print()
    
    # Run all examples
    await example_1_basic_avatar_setup()
    await example_2_simple_transfer()
    await example_3_transfer_with_transactions()
    await example_4_gas_estimation()
    await example_5_advanced_options()
    await example_6_cache_management()
    await example_7_error_handling()
    await example_8_multiple_avatars()
    
    print("\n" + "=" * 60)
    print("All CirclesAvatar examples completed!")
    print("\nKey Features Demonstrated:")
    print("- Simple, intuitive transfer API")
    print("- Automatic wrapped token handling")
    print("- Gas estimation and cost analysis")
    print("- Advanced transfer options and constraints")
    print("- Token cache management for performance")
    print("- Comprehensive error handling")
    print("- Multiple avatar management")
    print("- Production-ready async context management")
    print("\nPhase 3.1: CirclesAvatar interface is ready for production use!")


if __name__ == "__main__":
    asyncio.run(main())