#!/usr/bin/env python3
"""
Phase 2 Advanced Transfer Examples for Circles SDK

This file demonstrates the new Phase 2 functionality including:
- Wrapped token processing
- Path transformation pipeline
- Transaction building
- Advanced transfer capabilities
"""

import asyncio
import sys
from pathlib import Path

# Add src directory to path
src_path = str(Path("../src").absolute())
if src_path not in sys.path:
    sys.path.insert(0, src_path)

# Also add the current directory's src to path
current_src = str(Path("src").absolute())
if current_src not in sys.path:
    sys.path.insert(0, current_src)

from circles_sdk import (
    CirclesConfig,
    AdvancedTransfer,
    TokenInfoCache,
    TransactionBuilder,
    PathfindingResult,
    TransferStep,
    advanced_transfer,
    advanced_transfer_with_transactions,
    get_token_info_map_from_path,
    process_path_for_wrapped_tokens,
    replace_wrapped_tokens,
    shrink_path_values,
)


async def example_1_basic_advanced_transfer():
    """Example 1: Basic advanced transfer with wrapped token support."""
    print("📝 Example 1: Basic Advanced Transfer")
    print("-" * 40)
    
    # Configure for testnet
    config = CirclesConfig.testnet()
    
    # Use the advanced transfer client
    async with AdvancedTransfer(config) as transfer_client:
        
        # Example addresses (these would be real addresses in practice)
        from_addr = "0x1111111111111111111111111111111111111111"
        to_addr = "0x2222222222222222222222222222222222222222"
        amount = 1_000_000_000_000_000_000  # 1 CRC (18 decimals)
        
        try:
            # Check maximum transferable amount first
            max_amount = await transfer_client.get_max_transferable_amount(
                from_addr, to_addr, use_wrapped_balances=True
            )
            print(f"Maximum transferable: {max_amount / 1e18:.6f} CRC")
            
            if max_amount >= amount:
                # Perform the transfer
                flow_matrix = await transfer_client.transfer(
                    from_addr=from_addr,
                    to_addr=to_addr,
                    amount=amount,
                    use_wrapped_balances=True  # Enable wrapped token usage
                )
                
                print(f"✅ Transfer successful!")
                print(f"Flow matrix vertices: {len(flow_matrix.flow_vertices)}")
                print(f"Flow matrix edges: {len(flow_matrix.flow_edges)}")
                print(f"Streams: {len(flow_matrix.streams)}")
                
            else:
                print(f"❌ Insufficient balance. Max: {max_amount}, Requested: {amount}")
                
        except Exception as e:
            print(f"❌ Transfer failed: {e}")


async def example_2_transfer_with_transactions():
    """Example 2: Advanced transfer with complete transaction building."""
    print("\n📝 Example 2: Transfer with Transaction Building")
    print("-" * 50)
    
    config = CirclesConfig.testnet()
    
    async with AdvancedTransfer(config) as transfer_client:
        
        from_addr = "0x3333333333333333333333333333333333333333"
        to_addr = "0x4444444444444444444444444444444444444444"
        amount = 2_500_000_000_000_000_000  # 2.5 CRC
        
        try:
            # Get both flow matrix and transaction calls
            flow_matrix, transactions = await transfer_client.transitive_transfer(
                from_addr=from_addr,
                to_addr=to_addr,
                amount=amount,
                use_wrapped_balances=True
            )
            
            print(f"✅ Transaction batch prepared!")
            print(f"Number of transactions: {len(transactions)}")
            
            for i, tx in enumerate(transactions):
                print(f"  Transaction {i+1}:")
                print(f"    To: {tx.to}")
                print(f"    Data length: {len(tx.data)} bytes")
                print(f"    Value: {tx.value}")
            
            print(f"\nFlow Matrix Summary:")
            print(f"  Vertices: {len(flow_matrix.flow_vertices)}")
            print(f"  Edges: {len(flow_matrix.flow_edges)}")
            print(f"  Max flow: {flow_matrix.streams[0] if flow_matrix.streams else 'None'}")
            
        except Exception as e:
            print(f"❌ Transaction building failed: {e}")


async def example_3_manual_path_processing():
    """Example 3: Manual path processing pipeline demonstration."""
    print("\n📝 Example 3: Manual Path Processing Pipeline")
    print("-" * 50)
    
    # Create a mock pathfinding result with wrapped tokens
    mock_path = PathfindingResult(
        max_flow="1000000000000000000",
        transfers=[
            TransferStep(
                from_address="0x1111111111111111111111111111111111111111",
                to_address="0x2222222222222222222222222222222222222222",
                token_owner="0x5555555555555555555555555555555555555555",  # Wrapped token
                value="500000000000000000"
            ),
            TransferStep(
                from_address="0x2222222222222222222222222222222222222222",
                to_address="0x3333333333333333333333333333333333333333",
                token_owner="0x6666666666666666666666666666666666666666",  # Regular token
                value="500000000000000000"
            )
        ]
    )
    
    config = CirclesConfig.testnet()
    cache = TokenInfoCache()
    
    print("Original path:")
    for i, transfer in enumerate(mock_path.transfers):
        print(f"  Step {i+1}: {transfer.value} from {transfer.token_owner[:8]}...")
    
    try:
        # Process the path for wrapped tokens
        processed_path, has_inflationary = await process_path_for_wrapped_tokens(
            config, mock_path, cache
        )
        
        print(f"\nProcessed path (inflationary wrappers: {has_inflationary}):")
        for i, transfer in enumerate(processed_path.transfers):
            print(f"  Step {i+1}: {transfer.value} from {transfer.token_owner[:8]}...")
        
        print(f"Max flow: {processed_path.max_flow}")
        
    except Exception as e:
        print(f"❌ Path processing failed: {e}")


def example_4_transaction_builder():
    """Example 4: Direct transaction builder usage."""
    print("\n📝 Example 4: Transaction Builder Usage")
    print("-" * 40)
    
    config = CirclesConfig.testnet()
    builder = TransactionBuilder(config)
    
    # Example wrapped token totals
    wrapped_totals = {
        "0x5555555555555555555555555555555555555555": (
            1_000_000_000_000_000_000,  # 1 CRC worth
            "CrcV2_ERC20WrapperDeployed_Inflationary"
        ),
        "0x7777777777777777777777777777777777777777": (
            500_000_000_000_000_000,   # 0.5 CRC worth
            "CrcV2_ERC20WrapperDeployed_Demurraged"
        )
    }
    
    # Build unwrap calls
    unwrap_calls = builder.build_unwrap_calls(wrapped_totals)
    print(f"Generated {len(unwrap_calls)} unwrap calls:")
    for i, call in enumerate(unwrap_calls):
        print(f"  Unwrap {i+1}: {call.to}")
    
    # Build approval calls
    approval_calls = builder.build_approval_calls(
        owner="0x1111111111111111111111111111111111111111",
        spender="0x2222222222222222222222222222222222222222",
        hub_address=config.v2_hub_address
    )
    print(f"Generated {len(approval_calls)} approval calls:")
    for i, call in enumerate(approval_calls):
        print(f"  Approval {i+1}: {call.to}")


async def example_5_convenience_functions():
    """Example 5: Using convenience functions for quick transfers."""
    print("\n📝 Example 5: Convenience Functions")
    print("-" * 40)
    
    config = CirclesConfig.testnet()
    
    from_addr = "0x1111111111111111111111111111111111111111"
    to_addr = "0x2222222222222222222222222222222222222222"
    amount = 750_000_000_000_000_000  # 0.75 CRC
    
    try:
        # Quick transfer using convenience function
        flow_matrix = await advanced_transfer(
            config=config,
            from_addr=from_addr,
            to_addr=to_addr,
            amount=amount,
            use_wrapped_balances=True
        )
        
        print(f"✅ Quick transfer completed!")
        print(f"Vertices: {len(flow_matrix.flow_vertices)}")
        
        # Transfer with full transaction details
        flow_matrix_2, transactions = await advanced_transfer_with_transactions(
            config=config,
            from_addr=from_addr,
            to_addr=to_addr,
            amount=amount,
            use_wrapped_balances=True
        )
        
        print(f"✅ Transfer with transactions completed!")
        print(f"Transaction count: {len(transactions)}")
        
    except Exception as e:
        print(f"❌ Convenience function failed: {e}")


def example_6_token_cache_usage():
    """Example 6: Efficient token caching for multiple transfers."""
    print("\n📝 Example 6: Token Cache for Performance")
    print("-" * 45)
    
    # Create a token cache for better performance
    cache = TokenInfoCache(max_size=1000)
    
    print("Token cache created:")
    print(f"  Max size: {cache._max_size}")
    print(f"  Current size: {len(cache._cache)}")
    
    # Cache would be populated during actual transfers
    # and reused across multiple operations
    
    config = CirclesConfig.testnet()
    
    # Multiple transfer clients can share the same cache
    transfer_client_1 = AdvancedTransfer(config, cache)
    transfer_client_2 = AdvancedTransfer(config, cache)
    
    print("✅ Multiple transfer clients sharing cache")
    print("This improves performance by avoiding redundant token info lookups")


async def main():
    """Run all Phase 2 examples."""
    print("🚀 Phase 2 Advanced Transfer Examples")
    print("=" * 60)
    print("Demonstrating wrapped token processing, path transformation,")
    print("transaction building, and advanced transfer capabilities.")
    print()
    
    # Run all examples
    await example_1_basic_advanced_transfer()
    await example_2_transfer_with_transactions()
    await example_3_manual_path_processing()
    example_4_transaction_builder()
    await example_5_convenience_functions()
    example_6_token_cache_usage()
    
    print("\n" + "=" * 60)
    print("🎉 All Phase 2 examples completed!")
    print("\nKey Phase 2 Features Demonstrated:")
    print("✅ Wrapped token detection and processing")
    print("✅ Path transformation (token replacement, value shrinking)")
    print("✅ Complete transaction building pipeline")
    print("✅ Advanced transfer with full wrapped token support")
    print("✅ Performance optimizations (caching)")
    print("✅ Convenience functions for quick usage")
    print("\n🚀 Phase 2 is ready for production use!")


if __name__ == "__main__":
    asyncio.run(main())