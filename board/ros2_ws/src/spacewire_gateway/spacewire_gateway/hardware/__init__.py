"""Hardware backend factory for the SpaceWire gateway."""

from spacewire_gateway.hardware.base import (
    ReceivedImage,
    SpaceWireHardware,
    SpaceWireStatus,
)
from spacewire_gateway.hardware.beaglev import BeagleVSpaceWireHardware
from spacewire_gateway.hardware.mock import MockSpaceWireHardware


def create_hardware(backend: str) -> SpaceWireHardware:
    if backend == 'mock':
        return MockSpaceWireHardware()
    if backend == 'beaglev':
        return BeagleVSpaceWireHardware()
    raise ValueError(f'Unknown hardware_backend: {backend!r}')


__all__ = [
    'BeagleVSpaceWireHardware',
    'MockSpaceWireHardware',
    'ReceivedImage',
    'SpaceWireHardware',
    'SpaceWireStatus',
    'create_hardware',
]
