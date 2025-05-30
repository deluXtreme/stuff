"""Test configuration and utilities for Circles SDK."""

import logging
import sys
import os
from pathlib import Path

# Add the src directory to the path so we can import the SDK modules
test_dir = Path(__file__).parent
project_dir = test_dir.parent
src_dir = project_dir / "src"
sys.path.insert(0, str(src_dir))

# Configure logging for tests
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

# Suppress noisy logs during testing
logging.getLogger('aiohttp').setLevel(logging.WARNING)
logging.getLogger('urllib3').setLevel(logging.WARNING)

# Test configuration
TEST_CONFIG = {
    'timeout': 30.0,
    'max_retries': 1,
    'retry_delay': 0.1,
    'test_rpc_url': 'https://rpc.aboutcircles.com/',
    'test_pathfinder_url': 'https://pathfinder.aboutcircles.com',
    'test_hub_address': '0xc12C1E50ABB450d6205Ea2C3Fa861b3B834d13e8',
    'test_chain_id': 10200
}

# Test addresses for consistent testing
TEST_ADDRESSES = {
    'sender': '0x1111111111111111111111111111111111111111',
    'receiver': '0x2222222222222222222222222222222222222222',
    'token': '0x3333333333333333333333333333333333333333',
    'invalid': '0xinvalid'
}
