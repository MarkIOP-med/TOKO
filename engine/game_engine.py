"""
game_engine.py — TOKO Game Engine
===================================
Core logic of the system. Receives touch_events from touch_processor,
evaluates them against the current tier/level/task in request_response_map,
and decides what response to trigger (success / fail / hint).

The engine always knows three things:
  1. current_tier  — which tier is active (1, 2, or 3)
  2. current_level — which level within Tier 2 (L1–L6), or None
  3. active_task   — which guided task is running in Tier 3, or None

All logic is driven by request_response_map.json — not hardcoded here.
"""

import time
import json
import os

from pad_discovery import find_slot_by_card_id
from response_executor import execute_response

import sys
sys.path.insert(0, os.path.expanduser("~/tokotouch_project/config"))
import parameters as P


# =============================================================================
# SECTION 1 — Load the Request/Response Map
# =============================================================================

def load_map() -> dict:
    """
    Load request_response_map.json from the config folder.

    Returns the map as a Python dict.
    Raises an error if the file is missing or invalid JSON.
    """
    map_path = os.path.expanduser("~/tokotouch_project/config/request_response_map.json")
    with open(map_path, "r") as f:
        return json.load(f)
    # json.load() reads the file and converts JSON → Python dict


def load_system_state() -> dict:
    """
    Load system_state.json — the persisted state of the session.

    Returns current tier, level, theme, and session progress.
    If file missing, returns default state (Tier 1, free play).
    """
    state_path = os.path.expanduser("~/tokotouch_project/config/system_state.json")
    if not os.path.exists(state_path):
        return _default_state()

    with open(state_path, "r") as f:
        return json.load(f)


def save_system_state(state: dict) -> None:
    """Persist the current state to system_state.json."""
    state_path = os.path.expanduser("~/tokotouch_project/config/system_state.json")
    with open(state_path, "w") as f:
        json.dump(state, f, indent=2)
    # indent=2 makes the JSON file human-readable (2-space indentation)


def _default_state() -> dict:
    """Return the default state — Tier 1 free play, no progress."""
    return {
        "current_tier":   1,        # Start at Tier 1 — free play
        "current_level":  None,     # No level in Tier 1
        "active_theme":   None,     # No theme in Tier 1/2
        "active_task_id": None,     # No active task
        "run_mode":       "free_play"
        # "free_play" or "guided"
    }


# =============================================================================
# SECTION 2 — Game Engine Class
# =============================================================================

class GameEngine:
    """
    The brain of TOKO. Receives touch_events, evaluates them, triggers responses.

    Instantiated once at startup with the pad_map and loaded map/state.
    The touch_processor calls process_event() for each completed touch.
    """

    def __init__(self, pad_map: dict) -> None:
        self._pad_map    = pad_map
        self._rr_map     = load_map()
        # _rr_map = the full request_response_map loaded from JSON

        self._state      = load_system_state()
        # _state = current tier, level, theme, task

        # --- Tier 2 level tracking ---
        self._session_touch_count  = 0
        # Count of successful touches this session — used for advancement

        self._unique_pads_touched  = set()
        # Set of card_ids touched this session — used for L4 (N different pads)

        self._pad_sequence         = []
        # Ordered list of card_ids touched this session — used for L5 (sequence)

        # --- Tier 3 task tracking ---
        self._task_step            = 0
        # Which step of the current guided task we are on

        self._task_start_time      = None
        # time.time() when the current task step started — for hint timeout

        self._simultaneous_buffer  = []
        # Buffer of recent touches for simultaneous press detection
        # Each entry: {"card_id": int, "timestamp": float}

        print(f"[game_engine] Initialised — tier={self._state['current_tier']}  mode={self._state['run_mode']}")

    # =========================================================================
    # SECTION 3 — Main Entry Point
    # =========================================================================

    def process_event(self, touch_event: dict) -> None:
        """
        Main entry point called by touch_processor for every completed touch.

        Routes to the correct tier handler based on current_tier in state.

        touch_event keys used here:
          card_id        — which pad was touched (primary key for all logic)
          pressure_class — "light" / "medium" / "strong"
          touch_class    — "tap" / "press" / "hold"
          pressure       — float 0.0–1.0 (for reward scaling)
          duration_ms    — int milliseconds (for reward scaling)
          balance        — float (left/right difference)
          timestamp      — float (Unix time when touch started)
        """
        tier = self._state["current_tier"]
        # tier = 1, 2, or 3

        if tier == 1:
            self._handle_tier1(touch_event)
        elif tier == 2:
            self._handle_tier2(touch_event)
        elif tier == 3:
            self._handle_tier3(touch_event)

    # =========================================================================
    # SECTION 4 — Tier 1: Free Play
    # =========================================================================

    def _handle_tier1(self, event: dict) -> None:
        """
        Tier 1: Any touch on any pad → reward. No wrong answers.

        Looks up the pad's personality in the map and triggers the
        appropriate reward scale band based on pressure.

        Map path: rr_map["tier_1"]["pad_personalities"][card_id]["reward_scale"][pressure_class]
        """
        card_id        = event["card_id"]
        pressure_class = event["pressure_class"]
        # pressure_class = "light" / "medium" / "strong"

        personalities = self._rr_map.get("tier_1", {}).get("pad_personalities", {})
        pad_entry     = personalities.get(str(card_id))
        # JSON keys are always strings — str(card_id) converts int to string for lookup

        if pad_entry is None:
            # This CARD_ID is not in the map — use default personality
            pad_entry = personalities.get("default", {})

        reward_scale = pad_entry.get("reward_scale", {})
        response     = reward_scale.get(pressure_class)
        # response = the dict defining led_mode, vib_mode, sound for this pressure level

        if response:
            slot = self._get_slot(card_id)
            if slot >= 0:
                execute_response(slot, response)
                # Send LED, vibration, and sound commands to the hardware

    # =========================================================================
    # SECTION 5 — Tier 2: Leveled Free Play
    # =========================================================================

    def _handle_tier2(self, event: dict) -> None:
        """
        Tier 2: Apply level conditions. Reward only if conditions are met.

        Gets current level definition from map, checks conditions,
        triggers reward or ignores the touch.

        Map path: rr_map["tier_2"]["levels"][level_id]
        """
        level_id    = self._state.get("current_level", "L1")
        # level_id = "L1" through "L6"

        levels      = self._rr_map.get("tier_2", {}).get("levels", {})
        level_def   = levels.get(level_id, {})
        # level_def = the full definition of this level (conditions + personalities + advancement)

        conditions  = level_def.get("conditions", {})

        if self._meets_tier2_conditions(event, conditions, level_id):
            # Conditions met → trigger reward (same personality logic as Tier 1)
            card_id        = event["card_id"]
            pressure_class = event["pressure_class"]
            personalities  = level_def.get("pad_personalities", {})
            pad_entry      = personalities.get(str(card_id), personalities.get("default", {}))
            response       = pad_entry.get("reward_scale", {}).get(pressure_class, {})

            if response:
                slot = self._get_slot(card_id)
                if slot >= 0:
                    execute_response(slot, response)

            # Track progress for advancement
            self._session_touch_count += 1
            self._unique_pads_touched.add(card_id)
            self._pad_sequence.append(card_id)

            # Check advancement criteria
            self._check_advancement(level_def)

    def _meets_tier2_conditions(self, event: dict, conditions: dict, level_id: str) -> bool:
        """
        Check whether a touch_event meets the conditions for the current Tier 2 level.

        Conditions checked per level:
          L1: any touch (no conditions)
          L2: pressure >= min_pressure
          L3: pressure >= min_pressure AND duration >= min_duration_ms
          L4: N different pads touched this session (pad_count check)
          L5: sequence of N pads touched (sequence_length check)
          L6: balance within threshold (even left/right pressure)

        Returns True if conditions are met, False otherwise.
        """
        if level_id == "L1":
            return True
            # L1: always passes — any touch is a success

        min_pressure = conditions.get("min_pressure", 0.0)
        # min_pressure = minimum normalised pressure required (0.0–1.0)

        if level_id == "L2":
            return event["pressure"] >= min_pressure
            # L2: pressure must exceed threshold

        if level_id == "L3":
            min_duration = conditions.get("min_duration_ms", 0)
            return (event["pressure"] >= min_pressure and
                    event["duration_ms"] >= min_duration)
            # L3: both pressure AND duration must be sufficient

        if level_id == "L4":
            min_unique = conditions.get("min_unique_pads", 3)
            # Check AFTER adding this touch to the set
            self._unique_pads_touched.add(event["card_id"])
            return len(self._unique_pads_touched) >= min_unique
            # L4: child must have touched at least N different pads

        if level_id == "L5":
            seq_length = conditions.get("sequence_length", 3)
            self._pad_sequence.append(event["card_id"])
            return len(self._pad_sequence) >= seq_length
            # L5: child must have touched N pads in any sequence

        if level_id == "L6":
            balance_threshold = conditions.get("balance_threshold", P.BALANCE_THRESHOLD)
            # P.BALANCE_THRESHOLD = 0.20 — from parameters.py (can be overridden per level)
            return event["balance"] <= balance_threshold
            # L6: touch must be balanced (not leaning too far left or right)

        return False    # unknown level — fail safe

    # =========================================================================
    # SECTION 6 — Tier 3: Guided Play
    # =========================================================================

    def _handle_tier3(self, event: dict) -> None:
        """
        Tier 3: Evaluate touch against the active guided task.

        A task has one or more steps. Each step defines expected card_id(s).
        The engine checks if the touch matches the current step's expected pads.

        Outcomes:
          SUCCESS → trigger success_response, advance to next step (or complete task)
          FAIL    → trigger fail_response, stay on current step
          HINT    → triggered by timeout (checked separately in check_hint_timeout)
        """
        theme_id  = self._state.get("active_theme")
        task_id   = self._state.get("active_task_id")

        if not theme_id or not task_id:
            return  # no guided task loaded — do nothing

        # Navigate map to find the task definition
        task_def  = (self._rr_map
                     .get("tier_3", {})
                     .get("themes", {})
                     .get(theme_id, {})
                     .get("tasks", {})
                     .get(task_id, {}))

        if not task_def:
            return  # task not found in map

        steps = task_def.get("expected_pattern", {}).get("steps", [])
        # steps = list of step dicts, each with "card_ids" (list) and optional conditions

        if self._task_step >= len(steps):
            return  # all steps already completed

        current_step = steps[self._task_step]
        expected_ids = current_step.get("card_ids", [])
        # expected_ids = list of CARD_IDs required for this step
        # Multiple IDs = simultaneous press required

        interaction_type = task_def.get("interaction_type", "sequential")
        # "sequential" = one pad at a time
        # "simultaneous" = multiple pads at the same time

        if interaction_type == "sequential":
            # Simple case: check if this touch matches the expected single pad
            if event["card_id"] in expected_ids:
                self._task_success(task_def, event)
            else:
                self._task_fail(task_def, event)

        elif interaction_type == "simultaneous":
            # Add touch to simultaneous buffer and check if all required IDs are present
            self._simultaneous_buffer.append({
                "card_id":   event["card_id"],
                "timestamp": event["timestamp"]
            })
            self._check_simultaneous(task_def, expected_ids, event)

    def _task_success(self, task_def: dict, event: dict) -> None:
        """Handle a successful step match."""
        slot     = self._get_slot(event["card_id"])
        response = task_def.get("success_response", {})

        if slot >= 0 and response:
            execute_response(slot, response)

        self._task_step += 1
        # Advance to next step

        self._task_start_time = time.time()
        # Reset hint timer for the next step

        self._session_touch_count += 1

        steps = task_def.get("expected_pattern", {}).get("steps", [])
        if self._task_step >= len(steps):
            print(f"[game_engine] Task complete!")
            self._task_step = 0     # Reset for replay or next task

    def _task_fail(self, task_def: dict, event: dict) -> None:
        """Handle an incorrect touch — wrong pad pressed."""
        slot     = self._get_slot(event["card_id"])
        response = task_def.get("fail_response", {})

        if slot >= 0 and response:
            execute_response(slot, response)
        # Stay on current step — do not advance _task_step

    def _check_simultaneous(self, task_def: dict, expected_ids: list, event: dict) -> None:
        """
        Check if all expected pads have been pressed within SIMULTANEOUS_WINDOW_MS.

        The simultaneous buffer holds recent touches. We keep only touches
        within the time window and check if all expected IDs are present.

        P.SIMULTANEOUS_WINDOW_MS = 500 — window in ms
        """
        now = time.time()
        window_sec = P.SIMULTANEOUS_WINDOW_MS / 1000.0
        # Convert ms to seconds: 500ms → 0.5 seconds

        # Keep only touches within the time window
        self._simultaneous_buffer = [
            t for t in self._simultaneous_buffer
            if now - t["timestamp"] <= window_sec
            # now - timestamp = age of this touch in seconds
            # keep only touches younger than window_sec
        ]

        # Get the set of card_ids in the buffer
        buffered_ids = {t["card_id"] for t in self._simultaneous_buffer}
        # set() means no duplicates — each card_id counted once

        # Check if all expected IDs are present in the buffer
        if all(cid in buffered_ids for cid in expected_ids):
            # all() returns True only if every expected_id is in buffered_ids
            self._simultaneous_buffer = []  # clear buffer after success
            self._task_success(task_def, event)

    def check_hint_timeout(self) -> None:
        """
        Check if the hint timeout has expired for the current Tier 3 task step.

        Called periodically from the main loop (not from touch events).
        If the child has not pressed the correct pad within HINT_TIMEOUT_MS,
        trigger the hint response — light up the expected pad.

        P.HINT_TIMEOUT_MS = 5000 — 5 seconds default
        """
        if self._state["current_tier"] != 3:
            return  # hints only in Tier 3

        if self._task_start_time is None:
            self._task_start_time = time.time()
            return

        elapsed_ms = (time.time() - self._task_start_time) * 1000
        # Convert elapsed seconds to milliseconds

        if elapsed_ms < P.HINT_TIMEOUT_MS:
            return  # timeout not reached yet

        # Timeout reached — trigger hint
        theme_id = self._state.get("active_theme")
        task_id  = self._state.get("active_task_id")

        task_def = (self._rr_map
                    .get("tier_3", {})
                    .get("themes", {})
                    .get(theme_id, {})
                    .get("tasks", {})
                    .get(task_id, {}))

        if not task_def:
            return

        hint_response = task_def.get("hint_response", {})
        steps         = task_def.get("expected_pattern", {}).get("steps", [])

        if self._task_step < len(steps):
            expected_ids = steps[self._task_step].get("card_ids", [])
            for card_id in expected_ids:
                slot = self._get_slot(card_id)
                if slot >= 0:
                    execute_response(slot, hint_response)
                    # Light up the correct pad to guide the child

        self._task_start_time = time.time()
        # Reset hint timer — will trigger again after another HINT_TIMEOUT_MS

    # =========================================================================
    # SECTION 7 — Advancement (Tier 2)
    # =========================================================================

    def _check_advancement(self, level_def: dict) -> None:
        """
        Check if the child has met the criteria to advance to the next level.

        Uses the advancement definition from the level in the map:
          rule_type            = "successes_in_sessions" (current default)
          required_successes   = X (from map, or P.ADVANCEMENT_REQUIRED_SUCCESSES)
          over_sessions        = Y (from map, or P.ADVANCEMENT_OVER_SESSIONS)

        If criteria met → prints suggestion (app notification in future step).
        """
        advancement = level_def.get("advancement", {})
        rule_type   = advancement.get("rule_type", "successes_in_sessions")

        if rule_type == "successes_in_sessions":
            required = advancement.get("required_successes",
                                       P.ADVANCEMENT_REQUIRED_SUCCESSES)
            # Use map value if defined, otherwise fall back to parameter default
            # P.ADVANCEMENT_REQUIRED_SUCCESSES = 10

            if self._session_touch_count >= required:
                print(f"[game_engine] Advancement criteria met — suggest moving to next level")
                # TODO Step 4: send suggestion to parent app via app_interface

    # =========================================================================
    # SECTION 8 — State Management
    # =========================================================================

    def set_tier(self, tier: int) -> None:
        """Switch to a different tier. Resets task/level tracking."""
        self._state["current_tier"]   = tier
        self._state["current_level"]  = "L1" if tier == 2 else None
        self._state["active_theme"]   = None
        self._state["active_task_id"] = None
        self._task_step               = 0
        self._task_start_time         = None
        save_system_state(self._state)
        print(f"[game_engine] Switched to Tier {tier}")

    def set_level(self, level_id: str) -> None:
        """Set the active Tier 2 level (e.g. 'L1', 'L3')."""
        self._state["current_level"] = level_id
        self._session_touch_count    = 0
        self._unique_pads_touched    = set()
        self._pad_sequence           = []
        save_system_state(self._state)
        print(f"[game_engine] Level set to {level_id}")

    def set_task(self, theme_id: str, task_id: str) -> None:
        """Load a specific Tier 3 guided task."""
        self._state["active_theme"]   = theme_id
        self._state["active_task_id"] = task_id
        self._task_step               = 0
        self._task_start_time         = time.time()
        self._simultaneous_buffer     = []
        save_system_state(self._state)
        print(f"[game_engine] Task loaded — theme={theme_id}  task={task_id}")

    def _get_slot(self, card_id: int) -> int:
        """Look up which slot currently holds a pad with the given CARD_ID."""
        return find_slot_by_card_id(self._pad_map, card_id)
        # Returns slot number 0–11, or -1 if not found / not active
