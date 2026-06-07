"""
I2C helpers for Raspberry Pi (Zero 2 W).

Hardware (default Pi I2C1):
  - Pin 3  → BCM GPIO2 → SDA
  - Pin 5  → BCM GPIO3 → SCL

Uses Linux device /dev/i2c-1 (enable I2C in raspi-config).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from smbus2 import SMBus, i2c_msg


# Pi Zero 2 W: primary user I2C is bus 1
DEFAULT_BUS_ID = 1


@dataclass
class I2CScanResult:
    address: int
    present: bool


class PiI2CBus:
    """Thin wrapper around smbus2 for common read/write patterns."""

    def __init__(self, bus_id: int = DEFAULT_BUS_ID) -> None:
        self._bus_id = bus_id
        self._bus: Optional[SMBus] = None

    def open(self) -> None:
        if self._bus is None:
            self._bus = SMBus(self._bus_id)

    def close(self) -> None:
        if self._bus is not None:
            self._bus.close()
            self._bus = None

    def __enter__(self) -> "PiI2CBus":
        self.open()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    @property
    def bus(self) -> SMBus:
        if self._bus is None:
            raise RuntimeError("Bus is not open; use 'with PiI2CBus() as bus:' or call open()")
        return self._bus

    def scan(self, first: int = 0x03, last: int = 0x77) -> List[int]:
        """Probe 7-bit addresses in range [first, last]; return those that ACK."""
        found: List[int] = []
        for addr in range(first, last + 1):
            try:
                self.bus.write_quick(addr)
                found.append(addr)
            except OSError:
                continue
        return found

    def write_byte(self, address: int, value: int) -> None:
        """Write a single byte to the device (no register)."""
        self.bus.write_byte(address, value & 0xFF)

    def read_byte(self, address: int) -> int:
        """Read a single byte from the device (no register)."""
        return self.bus.read_byte(address) & 0xFF

    def write_byte_data(self, address: int, register: int, value: int) -> None:
        """Write one byte to `register` (8-bit register address)."""
        self.bus.write_byte_data(address, register & 0xFF, value & 0xFF)

    def read_byte_data(self, address: int, register: int) -> int:
        """Read one byte from `register`."""
        return self.bus.read_byte_data(address, register & 0xFF) & 0xFF

    def write_block(self, address: int, register: int, data: bytes) -> None:
        """Write a block starting at `register` (length byte + payload for SMBus block)."""
        self.bus.write_i2c_block_data(address, register & 0xFF, list(data))

    def read_block(self, address: int, register: int, length: int) -> bytes:
        """Read `length` bytes from `register` (SMBus block read)."""
        data = self.bus.read_i2c_block_data(address, register & 0xFF, length)
        return bytes(data)

    def write_raw(self, address: int, data: bytes) -> None:
        """Raw write: START, addr+W, data..., STOP."""
        msg = i2c_msg.write(address, list(data))
        self.bus.i2c_rdwr(msg)

    def read_raw(self, address: int, length: int) -> bytes:
        """Raw read: START, addr+R, read length bytes, STOP."""
        msg = i2c_msg.read(address, length)
        self.bus.i2c_rdwr(msg)
        return bytes(msg)

    def write_then_read(
        self,
        address: int,
        write_data: bytes,
        read_length: int,
    ) -> bytes:
        """
        Combined transaction: write then read without STOP between (repeated START).
        Typical for sensors: send register pointer, then read samples.
        """
        wr = i2c_msg.write(address, list(write_data))
        rd = i2c_msg.read(address, read_length)
        self.bus.i2c_rdwr(wr, rd)
        return bytes(rd)


def format_addr(addr: int) -> str:
    return f"0x{addr:02X}"
