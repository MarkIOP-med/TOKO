#!/usr/bin/env python3
"""Scan I2C bus 1 and print detected 7-bit addresses."""

from i2c_bus import PiI2CBus, format_addr


def main() -> None:
    with PiI2CBus() as bus:
        found = bus.scan()
    if not found:
        print("No devices found. Check wiring (SDA pin 3, SCL pin 5), pull-ups, power, and that I2C is enabled.")
        return
    print("Detected I2C devices (7-bit addresses):")
    for addr in found:
        print(f"  {format_addr(addr)}")


if __name__ == "__main__":
    main()
