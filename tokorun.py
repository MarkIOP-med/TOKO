#!/usr/bin/env python3
"""
tokorun.py — quick visual scan of all SMART_PAD slots over I2C, an interactive
LED/vibration/voice test console, and a data-driven demo game loop ('start').

Reads each slot's ID_I2C_Info block and prints which slots have a pad
connected (CARD_ID) vs empty, along with each occupied slot's FSR_LEFT/
FSR_RIGHT readings. Manual commands (vib/led/voice) pulse a slot's output and
can be cut short early with 'stop'. 'start [LEVEL]' runs a level defined in
config/game_levels.json: scan -> intro (start track + light/vibrate each pad
in turn) -> listen (poll FSR, fire a level's LED/vib/voice rule on touch)
until 'stop' ends it.

Run directly on the Raspberry Pi:
    python3 tokorun.py
"""

import glob
import json
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
# can cut it short if its duration hasn't elapsed yet. Only used when no level
# is running (manual commands are blocked while a level runs — see main()).
_active_lock = threading.RLock()  # RLock: cmd_stop() calls turn_off() while already holding the lock
_active = {"timer": None, "off_fn": None, "label": None}

# The currently running level ('start' command), if any. Only main() writes
# these (single-threaded dispatch), so no lock is needed for them.
_level_thread = None
_level_stop_event = None

# Only one voice track plays at a time, regardless of what triggered it (intro
# start_track, a level rule's response, or the manual 'voice' command) — the
# newest call to play_mp3() always cuts off whatever was already playing.
_voice_lock = threading.Lock()
_voice_proc = None


def _reset_active_locked() -> None:
    _active.update(timer=None, off_fn=None, label=None)


def read_id(bus: SMBus, slot: int) -> bytes:
    reg = P.SLOT_ID_INFO_BASE_ADDR + slot * P.SLOT_ID_INFO_STRIDE
    return bytes(bus.read_i2c_block_data(P.I2C_ADDRESS, reg, P.SLOT_ID_INFO_STRIDE))


def read_fsr(bus: SMBus, slot: int) -> tuple:
    reg = P.SLOT_FSR_BASE_ADDR + slot * P.SLOT_FSR_STRIDE
    data = bus.read_i2c_block_data(P.I2C_ADDRESS, reg, P.SLOT_FSR_STRIDE)
    fsr_left = (data[0] << 8) | data[1]
    fsr_right = (data[2] << 8) | data[3]
    return (fsr_left, fsr_right)


def normalise_fsr(raw_value: int) -> float:
    return raw_value / P.FSR_MAX


def _write_slot(bus: SMBus, slot: int, payload: bytes) -> None:
    reg = P.SLOT_LED_VIB_BASE_ADDR + slot * P.SLOT_LED_VIB_STRIDE
    bus.write_i2c_block_data(P.I2C_ADDRESS, reg, list(payload))


def build_payload(led_id=None, vib_level=None) -> bytes:
    led_values = [0, 0, 0, 0, 0, 0]
    if led_id is not None:
        led_values[P.LED_IDS[led_id]] = P.LED_TEST_BRIGHTNESS

    vib_byte = P.VIB_LEVELS[vib_level] if vib_level is not None else 0
    vib_mode = 0 if vib_level else 6  # 0=MOTOR_BEHAVE_DIRECT (steady) if vibrating, 6=CONST_0 (off) otherwise

    return bytes([*led_values, vib_byte, 0, 0, vib_mode])
    # byte layout: [LED1,LED0,LED3,LED2,LED5,LED4, VIB, LED_MODE=0 SOLID, reserved, VIB_MODE]


def play_mp3(path: str) -> subprocess.Popen:
    global _voice_proc
    with _voice_lock:
        if _voice_proc is not None and _voice_proc.poll() is None:
            _voice_proc.terminate()  # cut off whatever was already playing
        _voice_proc = subprocess.Popen(
            ["mpg123", "-o", "alsa", "-a", P.AUDIO_DEVICE, path],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return _voice_proc


def find_track_path(track_id) -> str | None:
    tracks_dir = os.path.join(REPO_DIR, P.TRACKS_FOLDER)
    matches = glob.glob(os.path.join(tracks_dir, f"Track{track_id}_*.mp3"))
    return matches[0] if matches else None


def scan_slots(bus: SMBus, show_menu: bool = True, quiet: bool = False) -> list:
    # quiet=True: just return the occupied-slot list with no output (and no
    # per-slot FSR read, which is only used for the display) — used by the
    # listen loop's idle re-scan, which reports occupancy changes itself.
    occupied = []
    if not quiet:
        print(f"Scanning {P.NUM_SLOTS} slots on I2C address 0x{P.I2C_ADDRESS:02X}...\n")

    for slot in range(P.NUM_SLOTS):
        id_i2c, card_id, gen_status, micro_version = read_id(bus, slot)

        if card_id != P.SLOT_EMPTY_CARD_ID:
            occupied.append(slot)
            if not quiet:
                fsr_left, fsr_right = read_fsr(bus, slot)
                print(
                    f"  Slot {slot:2d}  [X]  CARD_ID=0x{card_id:02X}  "
                    f"gen_status=0x{gen_status:02X}  micro_version=0x{micro_version:02X}  "
                    f"FSR_LEFT={fsr_left}  FSR_RIGHT={fsr_right}"
                )
        elif not quiet:
            print(f"  Slot {slot:2d}  [ ]  empty")

    if not quiet:
        print(f"\n{len(occupied)} / {P.NUM_SLOTS} pads detected")

    if show_menu and not quiet:
        print(
            "\nCommands:\n"
            "  refresh                 — re-scan all slots (incl. FSR_LEFT/FSR_RIGHT)\n"
            "  vib SLOT LEVEL          — pulse vibration (LEVEL 0-3) for VIB_DURATION_SEC\n"
            "  led SLOT LED_ID         — light one LED (LED_ID 0-5) for LED_DURATION_SEC\n"
            "  voice TRACK_ID          — play TRACK_ID's file from the tracks folder\n"
            "  start [LEVEL]           — run a level from game_levels.json (default: "
            f"{P.DEFAULT_LEVEL})\n"
            "  stop                    — cut short the last vib/led/voice command, or end a running level\n"
            "  exit                    — quit"
        )

    return occupied


def start_pulse(bus: SMBus, slot: int, payload: bytes, duration_sec: float, label: str) -> None:
    def turn_off(my_timer) -> None:
        with _active_lock:
            # Skip if a newer command has already taken over '_active' —
            # this timer's output already got superseded, nothing to report.
            if _active.get("timer") is not my_timer:
                return
            _write_slot(bus, slot, ALL_OFF_PAYLOAD)
            print(f"  Slot {slot:2d}: {label} OFF")
            _reset_active_locked()

    with _active_lock:
        _write_slot(bus, slot, payload)
        print(f"  Slot {slot:2d}: {label} ON")

        timer = threading.Timer(duration_sec, lambda: turn_off(timer))
        timer.daemon = True
        _active.update(timer=timer, off_fn=turn_off, label=f"Slot {slot} {label}")
        timer.start()


def cmd_vib(bus: SMBus, slot: int, level: int) -> None:
    if level not in P.VIB_LEVELS:
        levels = ", ".join(str(l) for l in sorted(P.VIB_LEVELS))
        print(f"  VIB_LEVEL must be one of: {levels}")
        return
    start_pulse(bus, slot, build_payload(vib_level=level), P.VIB_DURATION_SEC, f"vibration level {level}")


def cmd_led(bus: SMBus, slot: int, led_id: int) -> None:
    if led_id not in P.LED_IDS:
        ids = ", ".join(str(i) for i in sorted(P.LED_IDS))
        print(f"  LED_ID must be one of: {ids}")
        return
    start_pulse(bus, slot, build_payload(led_id=led_id), P.LED_DURATION_SEC, f"LED{led_id}")


def cmd_voice(track_id: int) -> None:
    track_path = find_track_path(track_id)
    if not track_path:
        tracks_dir = os.path.join(REPO_DIR, P.TRACKS_FOLDER)
        print(f"  No track found matching 'Track{track_id}_*.mp3' in {tracks_dir}")
        return

    print(f"  Playing {os.path.basename(track_path)}")
    play_mp3(track_path)


def cmd_stop() -> None:
    with _active_lock:
        if _active["label"] is not None:
            label = _active["label"]
            _active["timer"].cancel()
            _active["off_fn"](_active["timer"])  # turn hardware off now (also resets _active)
            print(f"  Stopped: {label}")
            return

    with _voice_lock:
        if _voice_proc is not None and _voice_proc.poll() is None:
            _voice_proc.terminate()
            print("  Stopped: voice")
            return

    print("  Nothing active")


# =============================================================================
# Game levels ('start' command) — data-driven demo loop, see config/game_levels.json
# =============================================================================

def load_level(name: str):
    path = os.path.join(REPO_DIR, P.GAME_LEVELS_FILE)
    try:
        with open(path, "r", encoding="utf-8") as f:
            levels = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        print(f"  Could not read {path}: {e}")
        return None

    if name not in levels:
        print(f"  Level '{name}' not found in {path}. Available: {', '.join(levels)}")
        return None

    return levels[name]


def run_intro(bus: SMBus, intro: dict, occupied: list, stop_event: threading.Event) -> None:
    start_track_id = intro.get("start_track_id")
    if start_track_id is not None:
        start_path = find_track_path(start_track_id)
        if start_path:
            play_mp3(start_path)
        else:
            print(f"  [start] No track found matching 'Track{start_track_id}_*.mp3'")

    payload = build_payload(intro.get("identify_led_id"), intro.get("identify_vib_level"))
    duration = intro.get("identify_duration_sec", 0.5)

    for slot in occupied:
        if stop_event.is_set():
            return
        _write_slot(bus, slot, payload)
        print(f"  Slot {slot:2d}: identify ON")
        stop_event.wait(duration)  # sleeps unless 'stop' fires early
        _write_slot(bus, slot, ALL_OFF_PAYLOAD)
        print(f"  Slot {slot:2d}: identify OFF")


def match_rule(rules: list, pressure: float, duration_ms: float):
    for rule in rules:
        if pressure >= rule["min_pressure"] and duration_ms >= rule["min_duration_ms"]:
            return rule
    return None


def classify_level(rules: list, pressure: float) -> str:
    """Which named tier (e.g. 'high'/'medium'/'minimum') this pressure alone
    qualifies for, ignoring duration — used for live display, and doubles as
    the touch detector (anything but 'no level reached' counts as touching)."""
    for rule in rules:
        if pressure >= rule["min_pressure"]:
            return rule.get("name", "?")
    return "no level reached"


def apply_response(bus: SMBus, slot: int, rule: dict) -> None:
    """Writes the rule's LED/vib payload immediately. No background timer here —
    the listen loop's own table tracks response_off_at and turns it off itself
    on a later poll tick, same as every other piece of per-slot state."""
    payload = build_payload(rule.get("led_id"), rule.get("vib_level"))
    _write_slot(bus, slot, payload)

    track_id = rule.get("track_id")
    if track_id is not None:
        track_path = find_track_path(track_id)
        if track_path:
            play_mp3(track_path)


def _new_slot_state() -> dict:
    return {"start": None, "fired": False, "level": "no level reached",
            "response_active": False, "response_off_at": None}


def run_listen_loop(bus: SMBus, rules: list, occupied: list, stop_event: threading.Event) -> None:
    occupied = list(occupied)  # local copy — idle re-scan below can grow/shrink it
    # Baseline = each slot's FSR reading right now, before anyone's touching —
    # every later reading is measured as a delta off this, so a pad's resting
    # offset (never exactly 0) doesn't get counted as pressure.
    baseline = {slot: read_fsr(bus, slot) for slot in occupied}
    # The state table: one row per slot, read AND written every poll tick.
    touch_state = {slot: _new_slot_state() for slot in occupied}
    last_rescan = time.time()

    print(f"  {'TIME':12}  {'SLOT':4}  {'FSR_LEFT':8}  {'FSR_RIGHT':9}  {'PRESSURE':8}  {'LEVEL':16}  RESPONSE")

    while not stop_event.is_set():
        now = time.time()
        any_active = False
        for slot in occupied:
            fsr_left, fsr_right = read_fsr(bus, slot)
            base_left, base_right = baseline[slot]
            diff_left = max(0, fsr_left - base_left) if fsr_left != P.FSR_INVALID_RAW else 0
            diff_right = max(0, fsr_right - base_right) if fsr_right != P.FSR_INVALID_RAW else 0
            pressure = normalise_fsr(max(diff_left, diff_right))  # divided by FSR_MAX, easy to recalibrate

            st = touch_state[slot]
            level_name = classify_level(rules, pressure)
            touching = level_name != "no level reached"
            level_changed = level_name != st["level"]
            st["level"] = level_name
            response_changed = False

            # A previously fired response's duration elapsed — turn it off,
            # checked here every tick rather than by a separate timer thread.
            if st["response_active"] and now >= st["response_off_at"]:
                _write_slot(bus, slot, ALL_OFF_PAYLOAD)
                st["response_active"] = False
                st["response_off_at"] = None
                response_changed = True

            if touching:
                if st["start"] is None:
                    st["start"] = now
                    st["fired"] = False
                if not st["fired"]:
                    duration_ms = (now - st["start"]) * 1000
                    rule = match_rule(rules, pressure, duration_ms)
                    if rule:
                        apply_response(bus, slot, rule)
                        st["fired"] = True
                        st["response_active"] = True
                        st["response_off_at"] = now + P.RESPONSE_DURATION_SEC
                        response_changed = True
            else:
                st["start"] = None
                st["fired"] = False

            any_active = any_active or touching or st["response_active"]

            # Always print on a level or response change (even below
            # FSR_DISPLAY_THRESHOLD) so a flaky/glitchy reading is visible
            # instead of silently re-triggering.
            if level_changed or response_changed or pressure >= P.FSR_DISPLAY_THRESHOLD:
                timestamp = time.strftime("%H:%M:%S") + f".{int(now * 1000) % 1000:03d}"
                response_label = "ON" if st["response_active"] else ""
                print(
                    f"  {timestamp:12}  {slot:<4d}  {diff_left:<8d}  {diff_right:<9d}  "
                    f"{pressure:<8.3f}  {level_name:16}  {response_label}"
                )

        # Idle only: periodically re-check slot occupancy so a pad connected
        # (or disconnected) mid-level doesn't require a manual stop/start.
        if not any_active and (now - last_rescan) >= P.IDLE_RESCAN_INTERVAL_SEC:
            current = scan_slots(bus, show_menu=False, quiet=True)
            added = [s for s in current if s not in occupied]
            removed = [s for s in occupied if s not in current]

            for slot in removed:
                _write_slot(bus, slot, ALL_OFF_PAYLOAD)
                del baseline[slot]
                del touch_state[slot]
            for slot in added:
                baseline[slot] = read_fsr(bus, slot)
                touch_state[slot] = _new_slot_state()

            if added or removed:
                print(f"  [idle re-scan] added={added}  removed={removed}")

            occupied = current
            last_rescan = now

        stop_event.wait(P.POLL_INTERVAL_MS / 1000)

    for slot in occupied:
        _write_slot(bus, slot, ALL_OFF_PAYLOAD)


def _run_level(bus: SMBus, name: str, stop_event: threading.Event) -> None:
    level = load_level(name)
    if level is None:
        return

    print(f"\n=== SCAN (level '{name}') ===")
    occupied = scan_slots(bus, show_menu=False)
    if not occupied:
        print("  No occupied slots — nothing to run.")
        return

    print(f"\n=== INTRO (level '{name}') ===")
    run_intro(bus, level["intro"], occupied, stop_event)
    if stop_event.is_set():
        print(f"  Level '{name}' stopped during intro.")
        return

    print(f"\n=== LISTEN (level '{name}') — type 'stop' to end it ===")
    run_listen_loop(bus, level["rules"], occupied, stop_event)
    print(f"  Level '{name}' ended.")


def level_running() -> bool:
    return _level_thread is not None and _level_thread.is_alive()


def start_level(bus: SMBus, level_name: str | None) -> None:
    global _level_thread, _level_stop_event

    if level_running():
        print("  A level is already running — type 'stop' to end it first.")
        return

    name = level_name or P.DEFAULT_LEVEL
    _level_stop_event = threading.Event()
    _level_thread = threading.Thread(target=_run_level, args=(bus, name, _level_stop_event), daemon=True)
    _level_thread.start()


def stop_level() -> None:
    if not level_running():
        return
    _level_stop_event.set()
    _level_thread.join(timeout=5)


def main() -> None:
    with SMBus(P.I2C_BUS_ID) as bus:
        print("=== INIT ===")
        scan_slots(bus)

        print(f"\nAuto-starting default level '{P.DEFAULT_LEVEL}' — 'stop'/'start LEVEL' override at any time.")
        start_level(bus, None)

        while True:
            raw = input("> ").strip()
            if not raw:
                continue

            parts = raw.split()
            command = parts[0].lower()

            try:
                if command == "exit" and len(parts) == 1:
                    if level_running():
                        stop_level()
                    break

                elif command == "stop" and len(parts) == 1:
                    if level_running():
                        stop_level()
                        print("  Level stopped.")
                    else:
                        cmd_stop()

                elif command == "start" and len(parts) in (1, 2):
                    start_level(bus, parts[1] if len(parts) == 2 else None)

                elif level_running():
                    print("  A level is running — type 'stop' to end it first.")

                elif command == "refresh" and len(parts) == 1:
                    scan_slots(bus)

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
                        "led SLOT LED_ID | voice TRACK_ID | start [LEVEL] | stop | exit"
                    )
            except ValueError:
                print("  SLOT/LEVEL/LED_ID/TRACK_ID must be numbers")


if __name__ == "__main__":
    main()
