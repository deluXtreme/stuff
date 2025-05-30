"""Transaction building functionality for the Circles SDK."""

from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
from abc import ABC, abstractmethod

from ..core.types import FlowMatrix
from ..core.config import CirclesConfig
from ..core.exceptions import TransactionError, ValidationError


@dataclass
class TransactionCall:
    """Represents a single transaction call."""
    to: str
    data: bytes
    value: int = 0


@dataclass
class UnwrapCall:
    """Represents an unwrap transaction call."""
    to: str
    data: bytes
    value: int = 0


class TransactionBuilder:
    """Builder for Circles protocol transactions."""
    
    def __init__(self, config: CirclesConfig):
        self.config = config
        self._transactions: List[TransactionCall] = []
    
    def add_transaction(self, transaction: TransactionCall) -> None:
        """Add a transaction to the batch."""
        self._transactions.append(transaction)
    
    def build_unwrap_calls(
        self,
        wrapped_totals: Dict[str, Tuple[int, str]]
    ) -> List[UnwrapCall]:
        """
        Build unwrap calls for wrapped tokens.
        
        Port of buildUnwrapCalls from TypeScript v2Avatar.ts.
        
        Args:
            wrapped_totals: Dict mapping wrapper addresses to (total_value, wrapper_type)
        
        Returns:
            List of unwrap calls
        """
        unwrap_calls: List[UnwrapCall] = []
        
        for wrapper_addr, (total_value, wrapper_type) in wrapped_totals.items():
            # Build the unwrap call data
            # In a real implementation, this would encode the unwrap function call
            unwrap_data = self._encode_unwrap_call(wrapper_addr, total_value, wrapper_type)
            
            unwrap_call = UnwrapCall(
                to=wrapper_addr,
                data=unwrap_data,
                value=0
            )
            unwrap_calls.append(unwrap_call)
        
        return unwrap_calls
    
    def build_approval_calls(
        self,
        owner: str,
        spender: str,
        hub_address: str
    ) -> List[TransactionCall]:
        """
        Build approval calls for transfers.
        
        Args:
            owner: Address that owns the tokens
            spender: Address that will spend the tokens
            hub_address: Hub contract address
        
        Returns:
            List of approval transaction calls
        """
        approval_calls: List[TransactionCall] = []
        
        # Build setApprovalForAll call
        approval_data = self._encode_approval_for_all_call(spender, True)
        
        approval_call = TransactionCall(
            to=hub_address,
            data=approval_data,
            value=0
        )
        approval_calls.append(approval_call)
        
        return approval_calls
    
    def build_transfer_batch(
        self,
        flow_matrix: FlowMatrix,
        unwrap_calls: Optional[List[UnwrapCall]] = None,
        approval_calls: Optional[List[TransactionCall]] = None,
        tx_data: Optional[bytes] = None
    ) -> List[TransactionCall]:
        """
        Build a complete transaction batch for a transfer.
        
        Args:
            flow_matrix: Flow matrix for the transfer
            unwrap_calls: Optional unwrap calls to include
            approval_calls: Optional approval calls to include
            tx_data: Optional additional transaction data
        
        Returns:
            List of transaction calls in proper order
        """
        batch: List[TransactionCall] = []
        
        # Add approval calls first if provided
        if approval_calls:
            batch.extend(approval_calls)
        
        # Add unwrap calls if provided
        if unwrap_calls:
            for unwrap_call in unwrap_calls:
                transaction = TransactionCall(
                    to=unwrap_call.to,
                    data=unwrap_call.data,
                    value=unwrap_call.value
                )
                batch.append(transaction)
        
        # Add the main transfer transaction
        transfer_call = self._build_transfer_call(flow_matrix, tx_data)
        batch.append(transfer_call)
        
        return batch
    
    def _encode_unwrap_call(
        self,
        wrapper_address: str,
        amount: int,
        wrapper_type: str
    ) -> bytes:
        """
        Encode an unwrap function call.
        
        This is a placeholder implementation. In reality, this would use
        the web3 library to encode the actual unwrap function call.
        """
        # Placeholder implementation - in reality this would use web3 ABI encoding
        # The actual implementation would look something like:
        # contract = web3.eth.contract(address=wrapper_address, abi=wrapper_abi)
        # return contract.encodeABI(fn_name='unwrap', args=[amount])
        
        # For now, return a mock encoded call
        return b"unwrap_call_placeholder"
    
    def _encode_approval_for_all_call(self, spender: str, approved: bool) -> bytes:
        """
        Encode a setApprovalForAll function call.
        
        This is a placeholder implementation. In reality, this would use
        the web3 library to encode the actual approval function call.
        """
        # Placeholder implementation - in reality this would use web3 ABI encoding
        # The actual implementation would look something like:
        # hub_contract = web3.eth.contract(address=hub_address, abi=hub_abi)
        # return hub_contract.encodeABI(fn_name='setApprovalForAll', args=[spender, approved])
        
        # For now, return a mock encoded call
        return b"approval_call_placeholder"
    
    def _build_transfer_call(
        self,
        flow_matrix: FlowMatrix,
        tx_data: Optional[bytes] = None
    ) -> TransactionCall:
        """
        Build the main transfer transaction call.
        
        Args:
            flow_matrix: Flow matrix for the transfer
            tx_data: Optional additional transaction data
        
        Returns:
            Transfer transaction call
        """
        # In reality, this would encode the flow matrix into the hub contract call
        # For now, return a placeholder
        transfer_data = tx_data or b"transfer_call_placeholder"
        
        return TransactionCall(
            to=self.config.v2_hub_address,
            data=transfer_data,
            value=0
        )
    
    def clear(self) -> None:
        """Clear all transactions from the builder."""
        self._transactions.clear()
    
    def get_transactions(self) -> List[TransactionCall]:
        """Get all transactions in the builder."""
        return self._transactions.copy()


class BatchRun:
    """
    Batch transaction runner, similar to TypeScript implementation.
    
    This class manages a batch of transactions that should be executed together.
    """
    
    def __init__(self):
        self._transactions: List[TransactionCall] = []
    
    def add_transaction(self, transaction: TransactionCall) -> None:
        """Add a transaction to the batch."""
        self._transactions.append(transaction)
    
    def get_transactions(self) -> List[TransactionCall]:
        """Get all transactions in the batch."""
        return self._transactions.copy()
    
    def clear(self) -> None:
        """Clear all transactions from the batch."""
        self._transactions.clear()
    
    @property
    def transaction_count(self) -> int:
        """Get the number of transactions in the batch."""
        return len(self._transactions)


def build_unwrap_calls(wrapped_totals: Dict[str, Tuple[int, str]]) -> List[UnwrapCall]:
    """
    Convenience function to build unwrap calls.
    
    Args:
        wrapped_totals: Dict mapping wrapper addresses to (total_value, wrapper_type)
    
    Returns:
        List of unwrap calls
    """
    unwrap_calls: List[UnwrapCall] = []
    
    for wrapper_addr, (total_value, wrapper_type) in wrapped_totals.items():
        # For now, create a simple unwrap call
        # In reality, this would properly encode the unwrap function call
        unwrap_call = UnwrapCall(
            to=wrapper_addr,
            data=b"unwrap_placeholder",
            value=0
        )
        unwrap_calls.append(unwrap_call)
    
    return unwrap_calls


def build_approval_calls(
    owner: str,
    spender: str,
    hub_address: str
) -> List[TransactionCall]:
    """
    Convenience function to build approval calls.
    
    Args:
        owner: Address that owns the tokens
        spender: Address that will spend the tokens
        hub_address: Hub contract address
    
    Returns:
        List of approval transaction calls
    """
    # For now, create a simple approval call
    # In reality, this would properly encode the setApprovalForAll function call
    approval_call = TransactionCall(
        to=hub_address,
        data=b"approval_placeholder",
        value=0
    )
    
    return [approval_call]


def build_transfer_batch(
    config: CirclesConfig,
    flow_matrix: FlowMatrix,
    unwrap_calls: Optional[List[UnwrapCall]] = None,
    approval_calls: Optional[List[TransactionCall]] = None,
    tx_data: Optional[bytes] = None
) -> List[TransactionCall]:
    """
    Convenience function to build a complete transfer batch.
    
    Args:
        config: Circles configuration
        flow_matrix: Flow matrix for the transfer
        unwrap_calls: Optional unwrap calls to include
        approval_calls: Optional approval calls to include
        tx_data: Optional additional transaction data
    
    Returns:
        List of transaction calls in proper order
    """
    builder = TransactionBuilder(config)
    return builder.build_transfer_batch(flow_matrix, unwrap_calls, approval_calls, tx_data)