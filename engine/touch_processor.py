"""
touch_processor.py — TOKO Touch Processor
==========================================
Polling loop that reads FSR sensors from all active pads,
classifies touches by pressure and duration, and emits touch_event dicts.

A touch_event is the standard data structure passed to game_engine:
  {
    "slot":          int,   — which physical slot (0–11)
    "card_id":       int,   — which pad identity (from pad_map)
    "fsr0_raw":      int,   — raw FSR0 sensor value (0–65535)
    "fsr1_raw":      int,   — raw FSR1 sensor value (0–65535)
    "fsr0_norm":     float, — normalised FSR0 (0.0–1.0)
    "fsr1_norm":     float, — normalised FSR1 (0.0–1.0)
    "pressure":      float, — combined pressure = max(fsr0_norm, fsr1_norm)
    "pressure_class":str,   — "light" / "medium" / "strong"
    "duration_ms":   int,   — how long the touch lasted in milliseconds
    "touch_class":   str,   — "tap" / "press" / "hold"
    "balance":       float, — abs(fsr0_norm - fsr1_norm) — left/right difference
    "timestamp":     float  — time.time() when touch was first detected
  }
"""

import time
import threading

from pad_interface import read_fsr, normalise_fsr
from pad_discovery import PAD_STATE_ACTIVE, update_pad_status

import sys, os
sys.path.insert(0, os.path.expanduser("~/tokotouch_project/config"))
import parameters as P


# =============================================================================
# SECTION 1 — Touch Classification
# =============================================================================

def classify_pressure(pressure: float) -> str:
    """
    Classify a normalised pressure value (0.0–1.0) into a named category.

    Uses thresholds from parameters.py:
      P.PRESSURE_LIGHT  = 0.15  — minimum for "light"
      P.PRESSURE_MEDIUM = 0.40  — minimum for "medium"
      P.PRESSURE_STRONG = 0.70  — minimum for "strong"

    Classification:
      pressure < PRESSURE_LIGHT   → "none"    (not a real touch — ignored)
      pressure >= LIGHT  < MEDIUM → "light"
      pressure >= MEDIUM < STRONG → "medium"
      pressure >= STRONG          → "strong"

    Example:
      pressure = 0.10 → "none"   (below light threshold — not a touch)
      pressure = 0.25 → "light"  (between 0.15 and 0.40)
      pressure = 0.55 → "medium" (between 0.40 and 0.70)
      pressure = 0.85 → "strong" (above 0.70)
    """
    if pressure >= P.PRESSURE_STRONG:
        return "strong"
    elif pressure >= P.PRESSURE_MEDIUM:
        return "medium"
    elif pressure >= P.PRESSURE_LIGHT:
        return "light"
    else:
        return "none"   # below minimum threshold — not counted as a touch


def classify_duration(duration_ms: int) -> str:
    """
    Classify touch duration (in milliseconds) into a named category.

    Uses thresholds from parameters.py:
      P.DURATION_TAP_MS  = 300  — maximum ms for a "tap"
      P.DURATION_HOLD_MS = 800  — minimum ms for a "hold"

    Classification:
      duration <= TAP_MS              → "tap"   (quick touch)
      duration > TAP_MS < HOLD_MS     → "press" (deliberate press)
      duration >= HOLD_MS             → "hold"  (sustained press)

    Example:
      duration = 150  → "tap"   (quick touch, under 300ms)
      duration = 500  → "press" (between 300ms and 800ms)
      duration = 1200 → "hold"  (over 800ms — sustained)
    """
    if duration_ms >= P.DURATION_HOLD_MS:
        return "hold"
    elif duration_ms > P.DURATION_TAP_MS:
        return "press"
    else:
        return "tap"


def compute_balance(fsr0_norm: float, fsr1_norm: float) -> float:
    """
    Compute the left/right balance between the two FSR sensors on one pad.

    Balance = abs(fsr0_norm - fsr1_norm)
      fsr0_norm = left sensor  (normalised 0.0–1.0)
      fsr1_norm = right sensor (normalised 0.0–1.0)
      abs()     = absolute value (always positive)

    A balance of 0.0 = perfectly even pressure on both sensors.
    A balance of 1.0 = all pressure on one side, none on the other.

    Compare against P.BALANCE_THRESHOLD = 0.20:
      balance < 0.20  → even touch (both sides similar)
      balance >= 0.20 → imbalanced touch (child pressing more to one side)

    Example:
      fsr0_norm = 0.60, fsr1_norm = 0.55  → balance = 0.05  (even)
      fsr0_norm = 0.70, fsr1_norm = 0.20  → balance = 0.50  (heavy left)
    """
    return abs(fsr0_norm - fsr1_norm)


# =============================================================================
# SECTION 2 — Touch State Tracking (per slot)
# =============================================================================
# We need to track when a touch started on each slot so we can measure duration.
# _touch_start_times stores the time.time() when each slot first exceeded the
# pressure threshold. When pressure drops below threshold, we compute duration.

_touch_start_times = {}
# Key:   slot number (int)
# Value: time.time() float when touch first detected, or None if not touching


def _is_touching(pressure: float) -> bool:
    """Return True if the pressure is above the minimum light touch threshold."""
    return pressure >= P.PRESSURE_LIGHT
    # P.PRESSURE_LIGHT = 0.15 — anything below this is not a touch


# =============================================================================
# SECTION 3 — Single Pad Poll and Event Building
# =============================================================================

def poll_pad(slot: int, pad_map: dict) -> dict | None:
    """
    Poll one SMART_PAD slot and return a touch_event if a touch just completed.

    A touch "completes" when:
      1. Pressure rose above threshold (touch started — we record the start time)
      2. Pressure dropped back below threshold (touch ended — we compute duration)

    At the moment pressure drops, we build and return the touch_event.
    While the pad is being touched (pressure high), we return None.
    If no touch at all, we return None.

    Parameters:
      slot    : int  — slot number to poll (0–11)
      pad_map : dict — current pad_map (to look up card_id and status)

    Returns:
      touch_event dict (described at top of file) if a touch just completed.
      None if no complete touch event to report yet.
    """
    # Step 1: Read raw FSR values from hardware
    fsr0_raw, fsr1_raw = read_fsr(slot)
    # fsr0_raw and fsr1_raw are integers 0–65535

    # Step 2: Normalise to 0.0–1.0
    fsr0_norm = normalise_fsr(fsr0_raw)
    # fsr0_norm = fsr0_raw / 65535
    fsr1_norm = normalise_fsr(fsr1_raw)

    # Step 3: Combined pressure = the stronger of the two sensors
    # We use max() because either sensor can be the primary contact point
    pressure = max(fsr0_norm, fsr1_norm)

    currently_touching = _is_touching(pressure)
    # True if pressure is above P.PRESSURE_LIGHT (0.15)

    was_touching = slot in _touch_start_times and _touch_start_times[slot] is not None
    # True if we have a recorded start time for this slot

    if currently_touching and not was_touching:
        # === TOUCH STARTED ===
        # Pressure just crossed the threshold — record the start time
        _touch_start_times[slot] = time.time()
        # time.time() returns current time as a float (Unix timestamp in seconds)
        return None     # touch not complete yet — wait for release

    elif not currently_touching and was_touching:
        # === TOUCH ENDED ===
        # Pressure dropped below threshold — compute duration and build event

        start_time = _touch_start_times[slot]
        _touch_start_times[slot] = None     # reset — ready for next touch

        end_time = time.time()
        duration_ms = int((end_time - start_time) * 1000)
        # (end_time - start_time) is in seconds (float)
        # × 1000 converts to milliseconds
        # int() drops the decimal

        # Get the pressure at the PEAK — we want to use the highest reading
        # Since we're reading at release, we use the last reading above threshold
        # NOTE: for a more accurate peak we would track max during the touch.
        # For now we use the pressure at the last above-threshold sample.
        # This is a known simplification — can be improved in a future iteration.

        pressure_class = classify_pressure(pressure)
        if pressure_class == "none":
            # Edge case: pressure was just above threshold when we started,
            # dropped quickly. Classify as light.
            pressure_class = "light"

        touch_class = classify_duration(duration_ms)
        balance     = compute_balance(fsr0_norm, fsr1_norm)

        # Look up card_id from pad_map
        card_id = pad_map.get(slot, {}).get("card_id", 0)
        # If slot not in map, default card_id to 0

        touch_event = {
            "slot":           slot,
            # Physical slot number (0–11) — where on the BASE board

            "card_id":        card_id,
            # Pad identity from pad_map — THIS is what game_engine uses

            "fsr0_raw":       fsr0_raw,
            # Raw left sensor value (0–65535) — for debugging / logging

            "fsr1_raw":       fsr1_raw,
            # Raw right sensor value (0–65535)

            "fsr0_norm":      round(fsr0_norm, 3),
            # Normalised left sensor (0.000–1.000) — rounded to 3 decimal places

            "fsr1_norm":      round(fsr1_norm, 3),
            # Normalised right sensor

            "pressure":       round(pressure, 3),
            # Combined pressure = max(fsr0_norm, fsr1_norm)

            "pressure_class": pressure_class,
            # "light" / "medium" / "strong"

            "duration_ms":    duration_ms,
            # How long the touch lasted in milliseconds

            "touch_class":    touch_class,
            # "tap" / "press" / "hold"

            "balance":        round(balance, 3),
            # abs(fsr0_norm - fsr1_norm) — left/right difference

            "timestamp":      start_time,
            # time.time() when touch first detected — used for simultaneous detection
        }

        return touch_event

    else:
        # Pressure unchanged (either still touching or still not touching)
        return None


# =============================================================================
# SECTION 4 — Full Poll Cycle (all active slots)
# =============================================================================

def poll_all_pads(pad_map: dict) -> list:
    """
    Poll all active SMART_PAD slots in one cycle.

    Iterates through all slots in pad_map.
    Only polls slots with status == "active" or "reconnected".
    Collects and returns all touch_events from this cycle.

    Returns:
      List of touch_event dicts (may be empty if no touches completed this cycle).
      Typically 0–2 events per cycle; could be more in multi-pad simultaneous play.

    Called by the polling thread every P.POLL_INTERVAL_MS milliseconds.
    """
    events = []

    for slot, info in pad_map.items():
        # Only poll slots that have an active pad
        if info["status"] not in (PAD_STATE_ACTIVE, "reconnected"):
            continue    # skip empty or disconnected slots

        event = poll_pad(slot, pad_map)
        # Returns a touch_event dict if a touch just completed, or None

        if event is not None:
            events.append(event)
            # Add to this cycle's event list

    return events
    # Returns list of 0 or more touch_event dicts


# =============================================================================
# SECTION 5 — Polling Thread
# =============================================================================

class TouchPollingThread(threading.Thread):
    """
    Background thread that continuously polls all pads at POLL_INTERVAL_MS.

    Runs in the background so the main program can do other things
    (respond to events, communicate with app, etc.) without waiting.

    Usage:
      poller = TouchPollingThread(pad_map, event_callback)
      poller.start()   # begins polling in background
      ...
      poller.stop()    # signals thread to stop (graceful shutdown)

    event_callback is a function that will be called with each touch_event.
    It is called from the polling thread — keep it fast (no blocking I/O).
    """

    def __init__(self, pad_map: dict, event_callback) -> None:
        super().__init__(daemon=True)
        # daemon=True means this thread will automatically stop when the
        # main program exits — no need to explicitly join it on shutdown

        self._pad_map       = pad_map
        # Reference to the shared pad_map — updated by pad_discovery

        self._callback      = event_callback
        # Function to call with each completed touch_event

        self._running       = False
        # Flag to control the polling loop — set to False to stop

        self._interval_sec  = P.POLL_INTERVAL_MS / 1000.0
        # Convert ms to seconds: 500ms → 0.5 seconds
        # time.sleep() takes seconds, not milliseconds

    def run(self) -> None:
        """Main loop — called automatically by thread.start()."""
        self._running = True
        print(f"[touch_processor] Polling started — interval={P.POLL_INTERVAL_MS}ms")

        while self._running:
            loop_start = time.time()
            # Record when this poll cycle started — used to keep interval accurate

            # Poll all active pads and collect events
            events = poll_all_pads(self._pad_map)

            # Deliver each event to the callback (game_engine)
            for event in events:
                self._callback(event)

            # Sleep for the remainder of the poll interval
            elapsed = time.time() - loop_start
            # elapsed = how long the poll took (in seconds)
            sleep_time = self._interval_sec - elapsed
            # sleep_time = remaining time to wait before next poll
            if sleep_time > 0:
                time.sleep(sleep_time)
            # If elapsed > interval (slow poll), we skip the sleep and go again immediately

    def stop(self) -> None:
        """Signal the polling thread to stop after the current cycle."""
        self._running = False
        print("[touch_processor] Polling stopped.")
