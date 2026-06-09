"""
main.py — TOKO Main Entry Point
=================================
Starts all system components, runs the main loop, handles shutdown.

Run on the Raspberry Pi:
  cd ~/tokotouch_project
  sudo python3 main.py

sudo is required for:
  - rpi_ws281x (WS2812 LED control needs DMA access)
  - gpiozero in some configurations

Startup sequence:
  1. Power sense check
  2. Build pad_map (scan all slots)
  3. Check mode (free play / guided)
  4. Start GameEngine + SessionTracker + TouchPollingThread
  5. Main loop — hint timeout, session timeout, button polling
  6. Shutdown — stop thread, end session, clear hardware
"""

import time
import sys
import os

# --- Add project paths so all modules can find each other ---
PROJECT_ROOT = os.path.expanduser("~/tokotouch_project")
sys.path.insert(0, PROJECT_ROOT)
sys.path.insert(0, os.path.join(PROJECT_ROOT, "config"))
sys.path.insert(0, os.path.join(PROJECT_ROOT, "engine"))

# --- Config ---
import parameters as P
from game_engine    import GameEngine, load_system_state
from pad_discovery  import build_pad_map, get_pad_inventory, check_missing_pads
from touch_processor import TouchPollingThread
from session_tracker import SessionTracker
from pad_interface  import (
    read_power_sense,
    set_control_leds,
    clear_control_leds,
    clear_pad,
    read_button_sw1,
    read_button_sw2,
    set_power_ctrl
)
from response_executor import flash_all_off


# =============================================================================
# SECTION 1 — Banner
# =============================================================================

def print_banner() -> None:
    """Print system info at startup."""
    print("=" * 50)
    print("  TOKO System")
    print("  Starting up...")
    print("=" * 50)


# =============================================================================
# SECTION 2 — Startup Checks
# =============================================================================

def check_power() -> bool:
    """
    Read GPIO25 to confirm power is stable before proceeding.

    Returns True if power sense is HIGH (OK).
    Returns False if power sense is LOW (problem).

    P.GPIO_POWER_SENSE = 25
    HIGH (True)  = power present and stable
    LOW  (False) = power issue — do not proceed
    """
    power_ok = read_power_sense()
    if power_ok:
        print("[main] Power sense: OK")
    else:
        print("[main] WARNING: Power sense LOW — check power supply")
    return power_ok


def clear_all_pads(pad_map: dict) -> None:
    """
    Send all-off command to every active pad at startup.

    Ensures no LEDs or vibration are left on from a previous session
    (e.g. if the system was restarted without a clean shutdown).
    """
    print("[main] Clearing all pads...")
    for slot, info in pad_map.items():
        if info["status"] == "active":
            flash_all_off(slot)
            # Sends 10-byte command: all LEDs off, vibration off
    print("[main] All pads cleared.")


# =============================================================================
# SECTION 3 — Mode Decision
# =============================================================================

def decide_mode(pad_map: dict, state: dict) -> bool:
    """
    Determine if the system can proceed in the requested mode.

    For free play: always proceed.
    For guided mode: check that all required CARD_IDs are connected.
      If any are missing → warn and list them.
      Returns False if critical pads are missing (parent must intervene).

    Returns True if ready to start, False if intervention needed.
    """
    run_mode = state.get("run_mode", "free_play")
    inventory = get_pad_inventory(pad_map)

    print(f"[main] Run mode: {run_mode}")
    print(f"[main] Active pads: {inventory['total_active']} / {inventory['total_slots']}")
    print(f"[main] Connected CARD_IDs: {inventory['active']}")

    if run_mode == "free_play":
        print("[main] Free play mode — no specific pads required.")
        return True

    elif run_mode == "guided":
        theme_id = state.get("active_theme")
        # The active theme defines which CARD_IDs are needed
        # For now: required_card_ids comes from state
        # TODO Step 4: app sends the required list at session start

        required_ids = state.get("required_card_ids", [])
        # List of CARD_IDs that the selected theme/task needs
        # e.g. [3, 7, 12] = circle, dog, football

        if not required_ids:
            print("[main] Guided mode — no required pad list defined yet. Proceeding.")
            return True

        missing = check_missing_pads(pad_map, required_ids)
        # Returns list of CARD_IDs that are required but not connected

        if missing:
            print(f"[main] WARNING: Missing pads for guided mode: CARD_IDs {missing}")
            print("[main] Options: connect the missing pads, or switch to free play.")
            # TODO Step 4: send alert to parent app
            # For now: proceed anyway (parent can see the warning in console)
            return True
            # Returning True so system doesn't block — parent decides via app

        print(f"[main] All required pads present. Ready for guided mode.")
        return True

    return True     # default: always proceed


# =============================================================================
# SECTION 4 — Button Handling
# =============================================================================

def handle_buttons(engine: GameEngine, tracker: SessionTracker) -> bool:
    """
    Check button states and act accordingly.

    Returns True to continue the main loop, False to trigger shutdown.

    SW1 (GPIO1): TODO — behaviour not yet decided
    SW2 (GPIO8): TODO — behaviour not yet decided

    Both buttons are read here every main loop cycle.
    When behaviour is decided, replace the TODO blocks below.
    """

    # --- SW1 ---
    if read_button_sw1():
        # GPIO1 is HIGH — SW1 is pressed
        # TODO: decide what SW1 does (e.g. end session, pause, change mode)
        print("[main] SW1 pressed — behaviour not yet assigned")
        time.sleep(0.3)
        # 0.3 second debounce — prevents multiple triggers from one press

    # --- SW2 ---
    if read_button_sw2():
        # GPIO8 is HIGH — SW2 is pressed
        # TODO: decide what SW2 does (e.g. next task, volume, tier change)
        print("[main] SW2 pressed — behaviour not yet assigned")
        time.sleep(0.3)
        # 0.3 second debounce

    return True     # continue main loop


# =============================================================================
# SECTION 5 — Control Unit LED Status Indicators
# =============================================================================

def set_status_leds_running() -> None:
    """
    Set control unit LEDs to indicate system is running normally.

    LED4 and LED5 on GPIO12 — WS2812 RGB.
    TODO: LED4/LED5 behaviour not yet decided.
    For now: dim green to indicate system is alive.
    """
    # TODO: decide LED4/LED5 colours and patterns for different states
    set_control_leds(r=0, g=30, b=0)
    # r=0, g=30, b=0 = dim green
    # Values 0–255 per channel. 30 = ~12% brightness — subtle indicator.


def set_status_leds_shutdown() -> None:
    """Turn off control unit LEDs on shutdown."""
    clear_control_leds()
    # Sets both LEDs to Color(0,0,0) = off


# =============================================================================
# SECTION 6 — Shutdown
# =============================================================================

def shutdown(poller: TouchPollingThread,
             tracker: SessionTracker,
             pad_map: dict) -> None:
    """
    Graceful shutdown sequence.

    1. Stop the polling thread
    2. End the session (writes summary file)
    3. Clear all pad LEDs and vibration
    4. Turn off control unit LEDs
    """
    print("\n[main] Shutting down...")

    # Step 1: Stop polling thread
    poller.stop()
    # Sets _running = False — thread finishes current cycle then exits

    poller.join(timeout=2.0)
    # Wait up to 2 seconds for the thread to finish
    # timeout=2.0 means we won't wait forever if something goes wrong

    # Step 2: End session and write summary
    tracker.end_session()
    # Writes session_YYYYMMDD_HHMMSS.json to sessions folder

    # Step 3: Clear all pads
    clear_all_pads(pad_map)

    # Step 4: Turn off control unit LEDs
    set_status_leds_shutdown()

    print("[main] Shutdown complete.")


# =============================================================================
# SECTION 7 — Main Entry Point
# =============================================================================

def main() -> None:
    """
    Main function — called when main.py is run directly.
    Orchestrates the full startup → run → shutdown lifecycle.
    """

    # --- 1. Banner ---
    print_banner()

    # --- 2. Power check ---
    check_power()
    # Warning only — does not block startup
    # Even if power sense is LOW we continue (may be bench testing)

    # --- 3. Load state ---
    state = load_system_state()
    print(f"[main] State loaded — tier={state['current_tier']}  mode={state['run_mode']}")

    # --- 4. Scan pads ---
    print("[main] Scanning pads...")
    pad_map = build_pad_map()
    # Scans all 12 slots, reads CARD_IDs, returns pad_map dict

    # --- 5. Mode decision ---
    ready = decide_mode(pad_map, state)
    if not ready:
        print("[main] Cannot start — check pad connections and try again.")
        return
        # Exit main() — system does not start

    # --- 6. Set running indicator ---
    set_status_leds_running()
    # Dim green on control unit LEDs

    # --- 7. Clear all pads from any previous state ---
    clear_all_pads(pad_map)

    # --- 8. Initialise engine components ---
    print("[main] Initialising engine...")

    engine = GameEngine(pad_map)
    # GameEngine holds the map, state, and all tier/level/task logic

    tracker = SessionTracker(
        tier  = state["current_tier"],
        level = state.get("current_level"),
        theme = state.get("active_theme")
    )
    # SessionTracker records all events and writes session summary on end

    # --- 9. Start polling thread ---
    poller = TouchPollingThread(
        pad_map        = pad_map,
        event_callback = engine.process_event
        # Every completed touch_event will be passed to engine.process_event()
    )
    poller.start()
    # Begins polling all active pads every P.POLL_INTERVAL_MS milliseconds

    print("[main] System running. Press Ctrl+C to stop.")

    # --- 10. Main loop ---
    try:
        while True:

            # --- Check hint timeout (Tier 3 guided tasks) ---
            engine.check_hint_timeout()
            # If child hasn't pressed correct pad within HINT_TIMEOUT_MS,
            # lights up the expected pad as a visual hint

            # --- Check session timeout ---
            if tracker.is_timed_out():
                print(f"[main] Session timeout reached ({P.MAX_SESSION_DURATION_MINS} mins).")
                break
                # Exit main loop → triggers shutdown sequence below

            # --- Check power sense ---
            if not read_power_sense():
                print("[main] Power sense LOW — initiating shutdown.")
                break
                # Exit main loop → triggers shutdown sequence below

            # --- Handle buttons ---
            handle_buttons(engine, tracker)
            # Checks SW1 and SW2 — behaviour TBD

            # --- Main loop sleep ---
            time.sleep(0.1)
            # 0.1 seconds = 100ms between main loop cycles
            # The polling thread runs independently — this sleep only
            # controls how often we check timeouts and buttons.
            # 100ms is responsive enough without burning CPU.

    except KeyboardInterrupt:
        # Ctrl+C pressed — clean shutdown
        print("\n[main] Keyboard interrupt received.")

    finally:
        # This block runs whether we exited via break, KeyboardInterrupt,
        # or any unexpected error — ensures clean shutdown always happens.
        shutdown(poller, tracker, pad_map)


# =============================================================================
# Standard Python entry point guard
# =============================================================================
# This block ensures main() is only called when this file is run directly:
#   sudo python3 main.py     ← runs main()
# If another file imports main.py, main() is NOT called automatically.

if __name__ == "__main__":
    main()
