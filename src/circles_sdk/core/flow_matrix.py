from typing import List, Dict, Tuple, Any
from .types import (
    TransferStep,
    FlowEdge,
    Stream,
    FlowMatrix,
)


def pack_coordinates(coords: List[int]) -> bytes:
    """
    Pack a uint16 array into bytes (big-endian, no padding).

    Args:
        coords: List of coordinate integers

    Returns:
        Packed coordinates as bytes
    """
    result = bytearray(len(coords) * 2)

    for i, coord in enumerate(coords):
        # Extract high and low bytes
        hi = (coord >> 8) & 0xFF
        lo = coord & 0xFF
        offset = 2 * i
        result[offset] = hi
        result[offset + 1] = lo

    return bytes(result)


def transform_to_flow_vertices(
    transfers: List[TransferStep],
    from_addr: str,
    to_addr: str
) -> Tuple[List[str], Dict[str, int]]:
    """
    Build a sorted vertex list plus index lookup for quick coordinate mapping.

    Args:
        transfers: List of transfer steps
        from_addr: Source address
        to_addr: Destination address

    Returns:
        Tuple of (sorted vertex list, address to index mapping)
    """
    # Collect unique addresses
    addresses = {from_addr.lower(), to_addr.lower()}

    for transfer in transfers:
        addresses.add(transfer.from_address.lower())
        addresses.add(transfer.to_address.lower())
        addresses.add(transfer.token_owner.lower())

    # Sort addresses by their integer value (treating as hex)
    sorted_addresses = sorted(addresses, key=lambda addr: int(addr, 16))

    # Create index mapping
    idx = {addr: i for i, addr in enumerate(sorted_addresses)}

    return sorted_addresses, idx


def create_flow_matrix(
    from_addr: str,
    to_addr: str,
    value: str,
    transfers: List[TransferStep]
) -> FlowMatrix:
    """
    Create an ABI-ready FlowMatrix object from a list of TransferSteps.

    Args:
        from_addr: Source address
        to_addr: Destination address
        value: Expected total value
        transfers: List of transfer steps

    Returns:
        FlowMatrix object ready for ABI encoding

    Raises:
        ValueError: If terminal sum doesn't equal expected value
    """
    sender = from_addr.lower()
    receiver = to_addr.lower()

    # Transform to flow vertices
    flow_vertices, idx = transform_to_flow_vertices(
        transfers, sender, receiver)

    # Create flow edges
    flow_edges = []
    for transfer in transfers:
        is_terminal = transfer.to_address.lower() == receiver
        flow_edges.append(FlowEdge(
            stream_sink_id=1 if is_terminal else 0,
            amount=transfer.value
        ))

    # Ensure at least one terminal edge
    has_terminal_edge = any(edge.stream_sink_id == 1 for edge in flow_edges)
    if not has_terminal_edge:
        # Find last edge that goes to receiver, or use last edge as fallback
        last_edge_index = -1
        for i, transfer in enumerate(transfers):
            if transfer.to_address.lower() == receiver:
                last_edge_index = i

        fallback_index = last_edge_index if last_edge_index != - \
            1 else len(flow_edges) - 1
        flow_edges[fallback_index].stream_sink_id = 1

    # Get terminal edge IDs
    term_edge_ids = [i for i, edge in enumerate(
        flow_edges) if edge.stream_sink_id == 1]

    # Create streams
    streams = [Stream(
        source_coordinate=idx[sender],
        flow_edge_ids=term_edge_ids,
        data=b''
    )]

    # Pack coordinates
    coords = []
    for transfer in transfers:
        coords.append(idx[transfer.token_owner.lower()])
        coords.append(idx[transfer.from_address.lower()])
        coords.append(idx[transfer.to_address.lower()])

    packed_coordinates = pack_coordinates(coords)

    # Validate terminal sum equals expected value
    expected = int(value)
    terminal_sum = sum(int(edge.amount)
                       for edge in flow_edges if edge.stream_sink_id == 1)

    if terminal_sum != expected:
        raise ValueError(
            f"Terminal sum {terminal_sum} does not equal expected {expected}")

    return FlowMatrix(
        flow_vertices=flow_vertices,
        flow_edges=flow_edges,
        streams=streams,
        packed_coordinates=packed_coordinates,
        source_coordinate=idx[sender]
    )


def flow_matrix_to_abi(flow_matrix: FlowMatrix) -> Dict[str, Any]:
    """
    Convert a FlowMatrix object to Ethereum ABI-compatible format for operateFlowMatrix.

    Args:
        flow_matrix: FlowMatrix object to convert

    Returns:
        Dictionary with ABI-compatible parameters for operateFlowMatrix function
    """
    # Convert flow vertices (already in correct format)
    flow_vertices = flow_matrix.flow_vertices

    # Convert flow edges to (uint16, uint192) tuples
    flow_edges_abi = []
    for edge in flow_matrix.flow_edges:
        flow_edges_abi.append({
            'streamSinkId': edge.stream_sink_id,  # uint16
            'amount': int(edge.amount)  # uint192 (convert string to int)
        })

    # Convert streams to (uint16, uint16[], bytes) tuples
    streams_abi = []
    for stream in flow_matrix.streams:
        streams_abi.append({
            'sourceCoordinate': stream.source_coordinate,  # uint16
            'flowEdgeIds': stream.flow_edge_ids,  # uint16[]
            'data': stream.data  # bytes
        })

    # Packed coordinates (already bytes, but may need hex encoding for some libraries)
    packed_coordinates = flow_matrix.packed_coordinates

    return {
        '_flowVertices': flow_vertices,
        '_flow': flow_edges_abi,
        '_streams': streams_abi,
        '_packedCoordinates': packed_coordinates
    }


def flow_matrix_to_abi_hex(flow_matrix: FlowMatrix) -> Dict[str, Any]:
    """
    Convert a FlowMatrix object to Ethereum ABI-compatible format with hex-encoded bytes.

    This variant encodes bytes fields as hex strings, which is often required
    by Ethereum libraries like web3.py or ethers.js.

    Args:
        flow_matrix: FlowMatrix object to convert

    Returns:
        Dictionary with ABI-compatible parameters (bytes as hex strings)
    """
    abi_data = flow_matrix_to_abi(flow_matrix)

    # Convert bytes to hex strings
    abi_data['_packedCoordinates'] = '0x' + flow_matrix.packed_coordinates.hex()

    # Convert stream data bytes to hex strings
    for stream in abi_data['_streams']:
        if isinstance(stream['data'], bytes):
            stream['data'] = '0x' + stream['data'].hex()

    return abi_data


# Example usage:
if __name__ == "__main__":
    # Example transfer steps
    transfers = [
        TransferStep(
            from_address="0x1234567890123456789012345678901234567890",
            to_address="0x2222222222222222222222222222222222222222",
            token_owner="0x1111111111111111111111111111111111111111",
            value="1000"
        ),
        TransferStep(
            from_address="0x2222222222222222222222222222222222222222",
            to_address="0x9999999999999999999999999999999999999999",
            token_owner="0x3333333333333333333333333333333333333333",
            value="1000"
        )
    ]

    # Create flow matrix
    try:
        flow_matrix = create_flow_matrix(
            from_addr="0x1234567890123456789012345678901234567890",
            to_addr="0x9999999999999999999999999999999999999999",
            value="1000",
            transfers=transfers
        )

        print("Flow matrix created successfully!")
        print(f"Flow vertices: {len(flow_matrix.flow_vertices)}")
        print(f"Flow edges: {len(flow_matrix.flow_edges)}")
        print(f"Streams: {len(flow_matrix.streams)}")
        print(f"Packed coordinates length: {len(flow_matrix.packed_coordinates)} bytes")

        # Convert to ABI format
        abi_data = flow_matrix_to_abi(flow_matrix)
        print("\nABI-compatible format:")
        print(f"_flowVertices: {abi_data['_flowVertices']}")
        print(f"_flow: {abi_data['_flow']}")
        print(f"_streams: {abi_data['_streams']}")
        print(f"_packedCoordinates: {abi_data['_packedCoordinates'].hex()}")

        # Convert to ABI format with hex encoding
        abi_data_hex = flow_matrix_to_abi_hex(flow_matrix)
        print("\nABI-compatible format (hex-encoded):")
        print(f"_flowVertices: {abi_data_hex['_flowVertices']}")
        print(f"_flow: {abi_data_hex['_flow']}")
        print(f"_streams: {abi_data_hex['_streams']}")
        print(f"_packedCoordinates: {abi_data_hex['_packedCoordinates']}")

    except ValueError as e:
        print(f"Error: {e}")
