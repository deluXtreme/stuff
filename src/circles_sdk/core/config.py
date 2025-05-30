"""Configuration management for Circles SDK."""

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class CirclesConfig:
    """Configuration for Circles SDK."""
    rpc_url: str
    pathfinder_url: str
    v2_hub_address: str
    chain_id: int = 100
    default_gas_limit: int = 500000
    request_timeout: float = 30.0
    max_retries: int = 3
    retry_delay: float = 1.0

    @classmethod
    def from_env(cls) -> 'CirclesConfig':
        """Load configuration from environment variables."""
        return cls(
            rpc_url=os.environ.get('CIRCLES_RPC_URL', 'https://rpc.aboutcircles.com/'),
            pathfinder_url=os.environ.get('CIRCLES_PATHFINDER_URL', 'https://pathfinder.aboutcircles.com'),
            v2_hub_address=os.environ.get('CIRCLES_V2_HUB_ADDRESS', '0xc12C1E50ABB450d6205Ea2C3Fa861b3B834d13e8'),
            chain_id=int(os.environ.get('CHAIN_ID', '100')),
            default_gas_limit=int(os.environ.get('DEFAULT_GAS_LIMIT', '500000')),
            request_timeout=float(os.environ.get('REQUEST_TIMEOUT', '30.0')),
            max_retries=int(os.environ.get('MAX_RETRIES', '3')),
            retry_delay=float(os.environ.get('RETRY_DELAY', '1.0'))
        )

    @classmethod
    def mainnet(cls) -> 'CirclesConfig':
        """Mainnet configuration."""
        return cls(
            rpc_url="https://rpc.gnosischain.com",
            pathfinder_url="https://pathfinder.aboutcircles.com",
            v2_hub_address="0xc12C1E50ABB450d6205Ea2C3Fa861b3B834d13e8",
            chain_id=100
        )

    @classmethod
    def testnet(cls) -> 'CirclesConfig':
        """Testnet configuration."""
        return cls(
            rpc_url="https://rpc.aboutcircles.com/",
            pathfinder_url="https://pathfinder.aboutcircles.com",
            v2_hub_address="0xc12C1E50ABB450d6205Ea2C3Fa861b3B834d13e8",
            chain_id=10200
        )