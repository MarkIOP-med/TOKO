#!/usr/bin/env python3
"""
tokorun.py — quick visual scan of all SMART_PAD slots over I2C, plus an
interactive LED/vibration/voice test.

Reads each slot's ID_I2C_Info block and prints which slots have a pad
connected (CARD_ID) vs empty, along with each occupied slot's FSR_LEFT/
FSR_RIGHT readings. Then accepts named commands to pulse a slot's vibration
motor or a single LED, or play a voice track — each of which can be cut
short early with 'stop' while its duration is still running.

Run directly on the Raspberry Pi:
    python3 tokorun.py
"""

import glob
import os
import subprocess
import sys
import threading
import time

REPO_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(REPO_DIR, "config"))
import parameters as P

from smbus2 import SMBus

ALL_OFF_PAYLOAD = bytes(10)

# Tracks whichever vib/led/voice command was started most recently, so 'stop'
# can cut it short if its duration hasn't elapsed yet. Only one entry is kept
# — starting a new command just replaces it; the previous command's own
# hardware output still runs to completion on its own, only 'stop' bookkeeping
# moves to the newest one.
_active_lock = threading.RLock()  # RLock: cmd_stop() calls turn_off() while already holding the lock
_active = {"timer": None, "off_fn": None, "proc": None, "label": None}


def _reset_active_locked() -> None:
    _active.update(timer=None, off_fn=None, proc=None, label=None)


def read_id(bus: SMBus, slot: int) -> bytes:
    reg = P.SLOT_ID_INFO_BASE_ADDR + slot * P.SLOT_ID_INFO_STRIDE
    return bytes(bus.read_i2c_block_data(P.I2C_ADDRESS, reg, P.SLOT_ID_INFO_STRIDE))


def read_fsr(bus: SMBus, slot: int) -> tuple:
    reg = P.SLOT_FSR_BASE_ADDR + slot * P.SLOT_FSR_STRIDE
    data = bus.read_i2c_block_data(P.I2C_ADDRESS, reg, P.SLOT_FSR_STRIDE)
    fsr_left = (data[0] << 8) | data[1]
    fsr_right = (data[2] << 8) | data[3]
    return (fsr_left, fsr_right)


def play_mp3(path: str) -> subprocess.Popen:
    return subprocess.Popen(
        ["mpg123", "-o", "alsa", "-a", P.AUDIO_DEVICE, path],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def play_refresh_track() -> None:
    path = os.path.join(REPO_DIR, P.TRACKS_FOLDER, P.REFRESH_TRACK)
    proc = play_mp3(path)
    time.sleep(P.REFRESH_TRACK_MAX_SEC)
    proc.terminate()  # no-op if the track already finished on its own


def scan_slots(bus: SMBus) -> None:
    occupied = 0
    print(f"Scanning {P.NUM_SLOTS} slots on I2C address 0x{P.I2C_ADDRESS:02X}...\n")

    for slot in range(P.NUM_SLOTS):
        id_i2c, card_id, gen_status, micro_version = read_id(bus, slot)

        if card_id != P.SLOT_EMPTY_CARD_ID:
            occupied += 1
            fsr_left, fsr_right = read_fsr(bus, slot)
            print(
                f"  Slot {slot:2d}  [X]  CARD_ID=0x{card_id:02X}  "
                f"gen_status=0x{gen_status:02X}  micro_version=0x{micro_version:02X}  "
                f"FSR_LEFT={fsr_left}  FSR_RIGHT={fsr_right}"
            )
        else:
            print(f"  Slot {slot:2d}  [ ]  empty")

    print(f"\n{occupied} / {P.NUM_SLOTS} pads detected")
    play_refresh_track()
    print(
        "\nCommands:\n"
        "  refresh                 — re-scan all slots (incl. FSR_LEFT/FSR_RIGHT)\n"
        "  vib SLOT LEVEL          — pulse vibration (LEVEL 0-3) for VIB_DURATION_SEC\n"
        "  led SLOT LED_ID         — light one LED (LED_ID 0-5) for LED_DURATION_SEC\n"
        "  voice TRACK_ID          — play TRACK_ID's file from the tracks folder\n"
        "  stop                    — cut short the last vib/led/voice command\n"
        "  exit                    — quit"
    )


def start_pulse(bus: SMBus, slot: int, payload: bytes, duration_sec: float, label: str) -> None:
    reg = P.SLOT_LED_VIB_BASE_ADDR + slot * P.SLOT_LED_VIB_STRIDE

    def turn_off(my_timer) -> None:
        with _active_lock:
            # Skip if a newer command has already taken over '_active' —
            # this timer's output already got superseded, nothing to report.
            if _active.get("timer") is not my_timer:
                return
            bus.write_i2c_block_data(P.I2C_ADDRESS, reg, list(ALL_OFF_PAYLOAD))
            print(f"  Slot {slot:2d}: {label} OFF")
            _reset_active_locked()

    with _active_lock:
        bus.write_i2c_block_data(P.I2C_ADDRESS, reg, list(payload))
        print(f"  Slot {slot:2d}: {label} ON")

        timer = threading.Timer(duration_sec, lambda: turn_off(timer))
        timer.daemon = True
        _active.update(timer=timer, off_fn=turn_off, proc=None, label=f"Slot {slot} {label}")
        timer.start()


def cmd_vib(bus: SMBus, slot: int, level: int) -> None:
    if level not in P.VIB_LEVELS:
        levels = ", ".join(str(l) for l in sorted(P.VIB_LEVELS))
        print(f"  VIB_LEVEL must be one of: {levels}")
        return

    payload = bytes([
        0, 0, 0, 0, 0, 0,            # all 6 LEDs off
        P.VIB_LEVELS[level] & 0xFF,  # byte 6: VIB intensity for this level
        0,                            # byte 7: LED_MODE (unused, solid/off)
        0,                            # byte 8: reserved
        0,                             # byte 9: VIB_MODE=0 MOTOR_BEHAVE_DIRECT (steady, no animation)
    ])
    start_pulse(bus, slot, payload, P.VIB_DURATION_SEC, f"vibration level {level}")


def cmd_led(bus: SMBus, slot: int, led_id: int) -> None:
    if led_id not in P.LED_IDS:
        ids = ", ".join(str(i) for i in sorted(P.LED_IDS))
        print(f"  LED_ID must be one of: {ids}")
        return

    led_values = [0, 0, 0, 0, 0, 0]
    led_values[P.LED_IDS[led_id]] = P.LED_TEST_BRIGHTNESS
    payload = bytes([
        *led_values,
        0,   # byte 6: VIB intensity off
        0,   # byte 7: LED_MODE=0 LED_BLINK_SOLID (always on, no animation)
        0,   # byte 8: reserved
        6,   # byte 9: VIB_MODE=6 MOTOR_BEHAVE_CONST_0 (motor stays off)
    ])
    start_pulse(bus, slot, payload, P.LED_DURATION_SEC, f"LED{led_id}")


def cmd_voice(track_id: int) -> None:
    tracks_dir = os.path.join(REPO_DIR, P.TRACKS_FOLDER)
    matches = glob.glob(os.path.join(tracks_dir, f"Track{track_id}_*.mp3"))

    if not matches:
        print(f"  No track found matching 'Track{track_id}_*.mp3' in {tracks_dir}")
        return

    track_path = matches[0]
    print(f"  Playing {os.path.basename(track_path)}")
    proc = play_mp3(track_path)

    def watch(my_proc) -> None:
        my_proc.wait()
        with _active_lock:
            if _active.get("proc") is my_proc:
                _reset_active_locked()

    with _active_lock:
        _active.update(timer=None, off_fn=None, proc=proc, label=f"voice {os.path.basename(track_path)}")

    watcher = threading.Thread(target=watch, args=(proc,), daemon=True)
    watcher.start()


def cmd_stop() -> None:
    with _active_lock:
        if _active["label"] is None:
            print("  Nothing active")
            return

        label = _active["label"]
        if _active["timer"] is not None:
            _active["timer"].cancel()
            _active["off_fn"](_active["timer"])  # turn hardware off now (also resets _active)
        else:
            if _active["proc"] is not None and _active["proc"].poll() is None:
                _active["proc"].terminate()
            _reset_active_locked()

    print(f"  Stopped: {label}")


def main() -> None:
    with SMBus(P.I2C_BUS_ID) as bus:
        scan_slots(bus)

        while True:
            raw = input("> ").strip()
            if not raw:
                continue

            parts = raw.split()
            command = parts[0].lower()

            try:
                if command == "exit" and len(parts) == 1:
                    break

                elif command == "refresh" and len(parts) == 1:
                    scan_slots(bus)

                elif command == "stop" and len(parts) == 1:
                    cmd_stop()

                elif command in ("vib", "led") and len(parts) == 3:
                    slot, value = int(parts[1]), int(parts[2])
                    if not (0 <= slot < P.NUM_SLOTS):
                        print(f"  SLOT must be between 0 and {P.NUM_SLOTS - 1}")
                    elif command == "vib":
                        cmd_vib(bus, slot, value)
                    else:
                        cmd_led(bus, slot, value)

                elif command == "voice" and len(parts) == 2:
                    cmd_voice(int(parts[1]))

                else:
                    print(
                        "  Unrecognized command. Use: refresh | vib SLOT LEVEL | "
                        "led SLOT LED_ID | voice TRACK_ID | stop | exit"
                    )
            except ValueError:
                print("  SLOT/LEVEL/LED_ID/TRACK_ID must be numbers")


if __name__ == "__main__":
    main()
