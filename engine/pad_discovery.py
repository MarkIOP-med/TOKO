"""
pad_discovery.py — TOKO Pad Discovery
======================================
Handles startup scanning: polls all 12 slots, reads CARD_IDs,
builds the pad_map, detects missing/unknown pads, and determines run_mode.

The pad_map is the central data structure for the whole session:
  {
    slot_number (int): {
      "card_id":       int,   — the pad's identity number
      "status":        str,   — "active" / "disconnected_unknown"
      "id_i2c":        int,   — I2C address confirmation byte
      "micro_version": int,   — pad firmware version
      "gen_status":    int    — hardware general status byte
    }
  }

CARD_ID is the pad's identity — not its slot.
Physical slot position is irrelevant. The system always works from CARD_ID.
"""

import time
from pad_interface import read_card_id, clear_pad

import sys, os
sys.path.insert(0, os.path.expanduser("~/tokotouch_project/config"))
import parameters as P


# =============================================================================
# SECTION 1 — Pad States
# =============================================================================
# These string constants represent the four possible states of any SMART_PAD.
# They are stored in the pad_map and updated throughout the session.

PAD_STATE_ACTIVE                = "active"
# Pad is connected and responding normally.

PAD_STATE_DISCONNECTED_EXPECTED = "disconnected_expected"
# Pad was in the pad_map at startup but stopped responding mid-session.
# Most likely magnetically detached. Parent should be alerted if task-relevant.

PAD_STATE_DISCONNECTED_UNKNOWN  = "disconnected_unknown"
# Pad never responded since startup — possibly not physically present.

PAD_STATE_RECONNECTED           = "reconnected"
# Pad came back after being disconnected. Will be auto-reintegrated.

# CARD_ID value returned when a slot has no pad connected
CARD_ID_EMPTY = 0
# 0 = no pad / empty slot — to be confirmed with hardware engineer


# =============================================================================
# SECTION 2 — Build Pad Map
# =============================================================================

def build_pad_map() -> dict:
    """
    Scan all 12 slots and build the pad_map.

    For each slot (0 to NUM_SLOTS-1 = 0 to 11):
      1. Call read_card_id(slot) to read the 4 ID bytes via I2C
      2. If pad responded (present=True) and card_id > 0 → mark as active
      3. If pad did not respond or card_id = 0 → mark as disconnected_unknown

    Returns:
      pad_map: dict keyed by slot number (0–11)
      Each value is a dict describing that slot's pad state and identity.

    Example output:
      {
        0: {"card_id": 3,  "status": "active", ...},
        1: {"card_id": 7,  "status": "active", ...},
        2: {"card_id": 0,  "status": "disconnected_unknown", ...},
        ...
      }
    """
    pad_map = {}

    print("[pad_discovery] Scanning all slots...")

    for slot in range(P.NUM_SLOTS):
        # P.NUM_SLOTS = 12 — scan slots 0 through 11

        result = read_card_id(slot)
        # result = {"id_i2c": int, "card_id": int, "gen_status": int,
        #           "micro_version": int, "present": bool}

        if result["present"] and result["card_id"] != CARD_ID_EMPTY:
            # Pad responded AND has a valid CARD_ID (non-zero)
            # → it is a real, connected pad
            pad_map[slot] = {
                "card_id":       result["card_id"],
                # The pad's identity — e.g. 7 = dog, 3 = circle
                # This is what all game logic uses — NOT the slot number

                "status":        PAD_STATE_ACTIVE,
                # Mark as active — it responded at startup

                "id_i2c":        result["id_i2c"],
                # Should equal 0x38 (56) for all genuine TOKO pads

                "micro_version": result["micro_version"],
                # Firmware version of the pad's microcontroller

                "gen_status":    result["gen_status"],
                # Hardware status byte — 0 = OK
            }
            print(f"  Slot {slot:2d} → CARD_ID={result['card_id']:3d}  version={result['micro_version']}  status={result['gen_status']}")

        else:
            # Pad did not respond OR returned card_id = 0
            # → slot is empty or pad is not connected
            pad_map[slot] = {
                "card_id":       CARD_ID_EMPTY,     # 0 = nothing here
                "status":        PAD_STATE_DISCONNECTED_UNKNOWN,
                "id_i2c":        0,
                "micro_version": 0,
                "gen_status":    0,
            }
            print(f"  Slot {slot:2d} → empty / not responding")

    active_count = sum(1 for s in pad_map.values() if s["status"] == PAD_STATE_ACTIVE)
    print(f"[pad_discovery] Scan complete. {active_count} active pads found out of {P.NUM_SLOTS} slots.")

    return pad_map


# =============================================================================
# SECTION 3 — CARD_ID Lookup Helpers
# =============================================================================

def find_slot_by_card_id(pad_map: dict, card_id: int) -> int:
    """
    Find which slot contains a pad with the given CARD_ID.

    This is the core lookup used by game_engine:
      "I need the dog pad (card_id=7) — which slot is it in?"

    Returns the slot number (0–11) if found and active.
    Returns -1 if not found or not active.

    Example:
      pad_map = {0: {"card_id": 3, "status": "active"}, 1: {"card_id": 7, ...}}
      find_slot_by_card_id(pad_map, 7) → 1
      find_slot_by_card_id(pad_map, 9) → -1  (not connected)
    """
    for slot, info in pad_map.items():
        if info["card_id"] == card_id and info["status"] == PAD_STATE_ACTIVE:
            return slot
            # Return the first matching slot that is active
    return -1   # -1 = not found


def get_active_card_ids(pad_map: dict) -> list:
    """
    Return a list of all CARD_IDs that are currently active (connected).

    Used by pad_discovery to report inventory to the parent app.

    Example:
      pad_map has slots 0,1,3 active with card_ids 3,7,12
      → returns [3, 7, 12]
    """
    return [
        info["card_id"]
        for info in pad_map.values()
        if info["status"] == PAD_STATE_ACTIVE
    ]


# =============================================================================
# SECTION 4 — Missing Pad Detection
# =============================================================================

def check_missing_pads(pad_map: dict, required_card_ids: list) -> list:
    """
    Check if all required CARD_IDs for the current guided task/theme are present.

    Parameters:
      pad_map           : the current pad_map (from build_pad_map)
      required_card_ids : list of CARD_IDs that must be active for the session

    Returns:
      List of CARD_IDs that are required but NOT currently active.
      Empty list = all required pads are present.

    Example:
      required = [3, 7, 12]        (circle, dog, football)
      active   = [3, 12]           (dog pad missing)
      → returns [7]                (card_id 7 = dog is missing)
    """
    active_ids = get_active_card_ids(pad_map)
    # active_ids = list of card_ids currently connected and responding

    missing = [cid for cid in required_card_ids if cid not in active_ids]
    # List comprehension: keep only those required IDs not in the active list

    return missing


# =============================================================================
# SECTION 5 — Pad Inventory (for app reporting)
# =============================================================================

def get_pad_inventory(pad_map: dict) -> dict:
    """
    Build a summary of what is currently connected, grouped by status.

    Returns a dict:
      {
        "active":    [list of card_ids that are active],
        "missing":   [list of slots that are disconnected_unknown],
        "total_active":  int,
        "total_slots":   int
      }

    Used at startup to report to the parent app what pads are connected.

    Example:
      {
        "active":       [3, 7, 12, 1],
        "missing":      [2, 5, 6, 8, 9, 10, 11],
        "total_active": 4,
        "total_slots":  12
      }
    """
    active_card_ids = []
    missing_slots   = []

    for slot, info in pad_map.items():
        if info["status"] == PAD_STATE_ACTIVE:
            active_card_ids.append(info["card_id"])
        else:
            missing_slots.append(slot)

    return {
        "active":       active_card_ids,
        # List of CARD_IDs that responded at startup

        "missing":      missing_slots,
        # List of slot numbers with no pad connected

        "total_active": len(active_card_ids),
        # Integer count of connected pads

        "total_slots":  P.NUM_SLOTS
        # P.NUM_SLOTS = 12 — total possible slots
    }


# =============================================================================
# SECTION 6 — Mid-Session Pad Status Update
# =============================================================================

def update_pad_status(pad_map: dict, slot: int) -> str:
    """
    Re-check a single slot and update its status in the pad_map.

    Called by touch_processor when a pad that was active stops responding,
    or when a disconnected pad might have been reconnected (magnetic reattachment).

    Returns the new status string for that slot.

    Logic:
      - If pad now responds AND was previously disconnected → "reconnected"
      - If pad now responds AND was active                  → "active" (no change)
      - If pad does not respond AND was active              → "disconnected_expected"
      - If pad does not respond AND was already disconnected → no change
    """
    result = read_card_id(slot)
    # Re-read the slot's ID register to check if it's responding

    current_status = pad_map[slot]["status"]

    if result["present"] and result["card_id"] != CARD_ID_EMPTY:
        # Pad is responding now
        if current_status in (PAD_STATE_DISCONNECTED_EXPECTED,
                               PAD_STATE_DISCONNECTED_UNKNOWN):
            # It was gone before — now it's back
            new_status = PAD_STATE_RECONNECTED
            pad_map[slot]["card_id"]       = result["card_id"]
            pad_map[slot]["micro_version"] = result["micro_version"]
            pad_map[slot]["gen_status"]    = result["gen_status"]
            print(f"[pad_discovery] Slot {slot} reconnected — CARD_ID={result['card_id']}")
        else:
            new_status = PAD_STATE_ACTIVE   # was active, still active

    else:
        # Pad is not responding now
        if current_status == PAD_STATE_ACTIVE:
            # It was active before — now it's gone
            new_status = PAD_STATE_DISCONNECTED_EXPECTED
            print(f"[pad_discovery] Slot {slot} disconnected (was active — likely detached)")
        else:
            new_status = current_status     # already disconnected — no change

    pad_map[slot]["status"] = new_status
    return new_status
