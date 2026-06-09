#!/usr/bin/env python3
"""
Example read/write patterns. Edit I2C_ADDRESS and REGISTER for your chip.

Run on the Pi after: pip install -r requirements.txt

Multi-byte operations use SMBus block read/write (typically up to 32 bytes per
transaction; see your device datasheet).
"""

import argparse

from i2c_bus import PiI2CBus, format_addr

# SMBus block read/write length limit used by smbus2 / common controllers
SMBUS_BLOCK_MAX = 32


def parse_byte_list(s: str) -> bytes:
    """Parse comma-separated byte values (decimal or 0x-prefixed), e.g. '1,2,255' or '0x01,0xFF'."""
    parts = [p.strip() for p in s.split(",") if p.strip()]
    if not parts:
        raise argparse.ArgumentTypeError("expected at least one byte")
    out = bytearray()
    for p in parts:
        try:
            out.append(int(p, 0) & 0xFF)
        except ValueError as e:
            raise argparse.ArgumentTypeError(f"invalid byte token {p!r}") from e
    return bytes(out)


def format_bytes_hex(data: bytes) -> str:
    return " ".join(format_addr(b) for b in data)


def main() -> None:
    parser = argparse.ArgumentParser(description="I2C read/write example")
    parser.add_argument(
        "--addr",
        type=lambda x: int(x, 0),
        required=True,
        help="7-bit I2C address, e.g. 0x48",
    )
    parser.add_argument(
        "--reg",
        type=lambda x: int(x, 0),
        default=0x00,
        help="Register index for byte read/write (default 0x00)",
    )
    parser.add_argument(
        "--read-byte",
        action="store_true",
        help="Read one byte from --reg",
    )
    parser.add_argument(
        "--read-bytes",
        type=int,
        metavar="N",
        help=f"Read N bytes from --reg via SMBus block read (1..{SMBUS_BLOCK_MAX})",
    )
    parser.add_argument(
        "--write-byte",
        type=lambda x: int(x, 0),
        metavar="VAL",
        help="Write one byte value to --reg",
    )
    parser.add_argument(
        "--write-bytes",
        type=parse_byte_list,
        metavar="B0,B1,...",
        help="Write multiple bytes starting at --reg (comma-separated, e.g. 0x01,0x02,3)",
    )
    args = parser.parse_args()

    has_read = args.read_byte or args.read_bytes is not None
    has_write = args.write_byte is not None or args.write_bytes is not None
    if not has_read and not has_write:
        parser.error(
            "Specify at least one of: --read-byte, --read-bytes, --write-byte, --write-bytes"
        )

    if args.read_bytes is not None:
        if args.read_bytes < 1 or args.read_bytes > SMBUS_BLOCK_MAX:
            parser.error(f"--read-bytes must be between 1 and {SMBUS_BLOCK_MAX}")

    if args.write_bytes is not None:
        n = len(args.write_bytes)
        if n < 1 or n > SMBUS_BLOCK_MAX:
            parser.error(f"--write-bytes length must be between 1 and {SMBUS_BLOCK_MAX}")

    addr = args.addr & 0x7F
    with PiI2CBus() as bus:
        if args.write_byte is not None:
            bus.write_byte_data(addr, args.reg, args.write_byte)
            print(f"Wrote {format_addr(args.write_byte)} to {format_addr(addr)} reg {format_addr(args.reg)}")
        if args.write_bytes is not None:
            bus.write_block(addr, args.reg, args.write_bytes)
            print(
                f"Wrote {len(args.write_bytes)} byte(s) {format_bytes_hex(args.write_bytes)} "
                f"to {format_addr(addr)} reg {format_addr(args.reg)}"
            )
        if args.read_byte:
            val = bus.read_byte_data(addr, args.reg)
            print(f"Read {format_addr(val)} from {format_addr(addr)} reg {format_addr(args.reg)}")
        if args.read_bytes is not None:
            data = bus.read_block(addr, args.reg, args.read_bytes)
            print(
                f"Read {len(data)} byte(s) from {format_addr(addr)} reg {format_addr(args.reg)}: "
                f"{format_bytes_hex(data)}"
            )


if __name__ == "__main__":
    main()
