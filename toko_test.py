#!/usr/bin/env python3
"""
toko_test.py — minimal SMART_PAD sort/triage tool.

Standalone and deliberately stripped down from tokorun.py: scan-only, no
vib/led/voice/game-level commands. Built for sorting pads one at a time while
only the ADAPTER base unit is connected — scan, plug/unplug a pad, scan again,
and read off which slot (if any) responds and whether it looks healthy.

Each scan prints one of three states per slot:
  [X]  occupied — valid CARD_ID, plus gen_status/micro_version/FSR readings
  [ ]  empty    — clean read, CARD_ID == SLOT_EMPTY_CARD_ID (0xFF)
  [!]  I2C error — the read itself failed (no ACK); distinct from a clean
       empty read, and the state actually hit when testing with no board
       wired behind a slot at all (see tokorun.py's same handling)

After each scan, every detected pad's LEDs are lit for LED_DURATION_SEC so
you can visually confirm the count/physical position matches what's printed.

Run directly on the Raspberry Pi:
    python3 toko_test.py
"""

import os
import sys
import time

REPO_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(REPO_DIR, "config"))
import parameters as P

from smbus2 import SMBus

ALL_OFF_PAYLOAD = bytes(10)


def read_id(bus: SMBus, slot: int) -> bytes | None:
    # Returns None if the I2C transaction itself fails (no ACK) — distinct
    # from a clean read that comes back SLOT_EMPTY_CARD_ID (0xFF). A slot
    # with no board wired behind it at all can NACK outright instead of
    # returning 0xFF — see tokorun.py for the same handling.
    reg = P.SLOT_ID_INFO_BASE_ADDR + slot * P.SLOT_ID_INFO_STRIDE
    try:
        return bytes(bus.read_i2c_block_data(P.I2C_ADDRESS, reg, P.SLOT_ID_INFO_STRIDE))
    except OSError:
        return None


def read_fsr(bus: SMBus, slot: int) -> tuple:
    # On I2C failure, report the existing "sensor not responding" sentinel
    # (FSR_INVALID_RAW) rather than raising.
    reg = P.SLOT_FSR_BASE_ADDR + slot * P.SLOT_FSR_STRIDE
    try:
        data = bus.read_i2c_block_data(P.I2C_ADDRESS, reg, P.SLOT_FSR_STRIDE)
    except OSError:
        return (P.FSR_INVALID_RAW, P.FSR_INVALID_RAW)
    fsr_left = (data[0] << 8) | data[1]
    fsr_right = (data[2] << 8) | data[3]
    return (fsr_left, fsr_right)


def _write_slot(bus: SMBus, slot: int, payload: bytes) -> None:
    # Swallow a failed write (I2C error on this slot) rather than crashing
    # the whole scan/flash.
    reg = P.SLOT_LED_VIB_BASE_ADDR + slot * P.SLOT_LED_VIB_STRIDE
    try:
        bus.write_i2c_block_data(P.I2C_ADDRESS, reg, list(payload))
    except OSError as e:
        print(f"  Slot {slot:2d}: I2C write failed ({e})")


def scan_slots(bus: SMBus) -> list:
    occupied = []
    print(f"Scanning {P.NUM_SLOTS} slots on I2C address 0x{P.I2C_ADDRESS:02X}...\n")

    for slot in range(P.NUM_SLOTS):
        id_bytes = read_id(bus, slot)

        if id_bytes is None:
            print(f"  Slot {slot:2d}  [!]  I2C error (no response)")
            continue

        id_i2c, card_id, gen_status, micro_version = id_bytes

        if card_id != P.SLOT_EMPTY_CARD_ID:
            occupied.append(slot)
            fsr_left, fsr_right = read_fsr(bus, slot)
            print(
                f"  Slot {slot:2d}  [X]  CARD_ID=0x{card_id:02X}  "
                f"gen_status=0x{gen_status:02X}  micro_version=0x{micro_version:02X}  "
                f"FSR_LEFT={fsr_left}  FSR_RIGHT={fsr_right}"
            )
        else:
            print(f"  Slot {slot:2d}  [ ]  empty")

    print(f"\n{len(occupied)} / {P.NUM_SLOTS} pads detected\n")
    return occupied


def flash_occupied(bus: SMBus, occupied: list) -> None:
    # Lights all 6 LEDs on every currently-occupied slot for LED_DURATION_SEC
    # — a quick visual headcount so the printed scan can be checked against
    # what's physically lit on the pads. Blocks until the flash ends.
    if not occupied:
        return

    payload = bytes([P.LED_TEST_BRIGHTNESS] * 6 + [0, 0, 0, 6])
    # byte layout: [LED1,LED0,LED3,LED2,LED5,LED4, VIB=0, LED_MODE=0 SOLID, reserved, VIB_MODE=6 CONST_0]
    for slot in occupied:
        _write_slot(bus, slot, payload)

    print(f"  Lit {len(occupied)} pad(s) for {P.LED_DURATION_SEC}s: {occupied}")
    time.sleep(P.LED_DURATION_SEC)

    for slot in occupied:
        _write_slot(bus, slot, ALL_OFF_PAYLOAD)


def main() -> None:
    print("TOKO pad sort/triage tool — 'r' / 'refresh' / Enter re-scans, 'exit' quits.\n")
    with SMBus(P.I2C_BUS_ID) as bus:
        occupied = scan_slots(bus)
        flash_occupied(bus, occupied)

        while True:
            raw = input("> ").strip().lower()
            if raw in ("exit", "quit"):
                break
            elif raw in ("", "r", "refresh"):
                occupied = scan_slots(bus)
                flash_occupied(bus, occupied)
            else:
                print(f"  Unrecognized command '{raw}'. Use: r | refresh | <Enter> to re-scan, exit to quit.")


if __name__ == "__main__":
    main()
