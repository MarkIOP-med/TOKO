#!/usr/bin/env python3
"""
test_detect.py — quick visual scan of all SMART_PAD slots over I2C, plus an
interactive LED/vibration test.

Reads each slot's ID_I2C_Info block and prints which slots have a pad
connected (CARD_ID) vs empty. Then accepts "SLOT,COMMAND" input to pulse
that slot's vibration motor (1) or LEDs (2) for a couple seconds.

Run directly on the Raspberry Pi:
    python3 test_detect.py
"""

import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "config"))
import parameters as P

from smbus2 import SMBus

# LED_VIBRATION block byte layout (per tokotouch_bringup.docx):
#   [LED1, LED0, LED3, LED2, LED5, LED4, VIB, LED_MODE, -, VIB_MODE]
# LED payload reuses the one validated write example from the docs.
LED_TEST_PAYLOAD = bytes([0x01, 0x03, 0x03, 0x03, 0x03, 0x03, 0x00, 0x19, 0x00, 0x01])
# Vibration payload is a best guess (VIB=max, VIB_MODE=1 — the only mode value
# confirmed accepted by the hardware). Not validated against the VIB_MODES
# table (image-only in the docs, not text-extractable).
VIB_TEST_PAYLOAD = bytes([0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0xFF, 0x00, 0x00, 0x01])
ALL_OFF_PAYLOAD = bytes(10)
PULSE_SECONDS = 15


def read_slot(bus: SMBus, slot: int) -> bytes:
    reg = P.SLOT_ID_INFO_BASE_ADDR + slot * P.SLOT_ID_INFO_STRIDE
    return bytes(bus.read_i2c_block_data(P.I2C_ADDRESS, reg, P.SLOT_ID_INFO_STRIDE))


def scan_slots(bus: SMBus) -> None:
    occupied = 0
    print(f"Scanning {P.NUM_SLOTS} slots on I2C address 0x{P.I2C_ADDRESS:02X}...\n")

    for slot in range(P.NUM_SLOTS):
        id_i2c, card_id, gen_status, micro_version = read_slot(bus, slot)

        if card_id != P.SLOT_EMPTY_CARD_ID:
            occupied += 1
            print(
                f"  Slot {slot:2d}  [X]  CARD_ID=0x{card_id:02X}  "
                f"gen_status=0x{gen_status:02X}  micro_version=0x{micro_version:02X}"
            )
        else:
            print(f"  Slot {slot:2d}  [ ]  empty")

    print(f"\n{occupied} / {P.NUM_SLOTS} pads detected")


def pulse(bus: SMBus, slot: int, payload: bytes, label: str) -> None:
    reg = P.SLOT_LED_VIB_BASE_ADDR + slot * P.SLOT_LED_VIB_STRIDE
    bus.write_i2c_block_data(P.I2C_ADDRESS, reg, list(payload))
    print(f"  Slot {slot:2d}: {label} ON")
    time.sleep(PULSE_SECONDS)
    bus.write_i2c_block_data(P.I2C_ADDRESS, reg, list(ALL_OFF_PAYLOAD))
    print(f"  Slot {slot:2d}: {label} OFF")


def main() -> None:
    with SMBus(P.I2C_BUS_ID) as bus:
        scan_slots(bus)

        print(
            "\nEnter 'SLOT,COMMAND' to pulse a slot's output "
            "(COMMAND: 1 = vibration, 2 = LEDs). Blank line to quit."
        )
        while True:
            raw = input("> ").strip()
            if not raw:
                break

            parts = raw.split(",")
            if len(parts) != 2:
                print("  Format must be SLOT,COMMAND — e.g. 4,1")
                continue

            try:
                slot = int(parts[0].strip())
                command = int(parts[1].strip())
            except ValueError:
                print("  SLOT and COMMAND must be numbers — e.g. 4,1")
                continue

            if not (0 <= slot < P.NUM_SLOTS):
                print(f"  SLOT must be between 0 and {P.NUM_SLOTS - 1}")
                continue

            if command == 1:
                pulse(bus, slot, VIB_TEST_PAYLOAD, "vibration")
            elif command == 2:
                pulse(bus, slot, LED_TEST_PAYLOAD, "LEDs")
            else:
                print("  COMMAND must be 1 (vibration) or 2 (LEDs)")


if __name__ == "__main__":
    main()
