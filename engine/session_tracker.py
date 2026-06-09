"""
session_tracker.py — TOKO Session Tracker
==========================================
Records all touch events, successes, and failures during a session.
Evaluates advancement criteria at the end of each session.
Writes a session summary JSON file to the sessions folder.

One session = one power-on to power-off (or manual end).
Session files are named by timestamp: session_YYYYMMDD_HHMMSS.json

Session summary structure:
  {
    "session_id":      str,   — timestamp-based unique ID
    "start_time":      float, — Unix timestamp when session started
    "end_time":        float, — Unix timestamp when session ended
    "duration_mins":   float, — session length in minutes
    "tier":            int,   — which tier was active
    "level":           str,   — which level (Tier 2) or None
    "theme":           str,   — which theme (Tier 3) or None
    "total_touches":   int,   — total touch events recorded
    "successes":       int,   — touches that met success criteria
    "fails":           int,   — touches that did not meet criteria
    "unique_pads":     int,   — number of different CARD_IDs touched
    "advancement_met": bool,  — whether advancement criteria were met
    "events":          list   — full list of touch_event dicts
  }
"""

import json
import os
import time
from datetime import datetime

import sys
sys.path.insert(0, os.path.expanduser("~/tokotouch_project/config"))
import parameters as P


class SessionTracker:
    """
    Tracks all events and statistics for a single session.
    Instantiated at session start, finalised at session end.
    """

    def __init__(self, tier: int, level: str | None, theme: str | None) -> None:
        self._tier    = tier
        self._level   = level
        self._theme   = theme

        self._start_time = time.time()
        # time.time() returns current Unix timestamp as float (seconds since 1970)

        self._session_id = datetime.now().strftime("session_%Y%m%d_%H%M%S")
        # strftime formats the current date/time as a string
        # %Y = 4-digit year, %m = month, %d = day, %H = hour, %M = minute, %S = second
        # Example: "session_20260609_143022"

        self._events     = []
        # List of all touch_event dicts recorded this session

        self._successes  = 0
        # Count of touches classified as successful

        self._fails      = 0
        # Count of touches that did not meet criteria

        self._unique_pads = set()
        # Set of card_ids touched — set() means no duplicates
        # len(set) gives count of unique pads

        print(f"[session_tracker] Session started — id={self._session_id}  tier={tier}")

    # =========================================================================
    # SECTION 1 — Event Recording
    # =========================================================================

    def record_touch(self, touch_event: dict, outcome: str) -> None:
        """
        Record a touch event and its outcome.

        Parameters:
          touch_event : dict — the full touch_event from touch_processor
          outcome     : str  — "success", "fail", or "ignored"
                               "ignored" = touch below threshold, not counted

        Adds the event (with outcome) to the events list.
        Updates success/fail counters and unique pad set.
        """
        if outcome == "ignored":
            return  # below threshold — do not record

        # Add outcome to the event dict before storing
        event_with_outcome = dict(touch_event)
        # dict() creates a copy — we don't modify the original

        event_with_outcome["outcome"] = outcome
        # Add the outcome key to our copy

        self._events.append(event_with_outcome)
        # Append to the session's event list

        self._unique_pads.add(touch_event["card_id"])
        # Add this pad's CARD_ID to the set (duplicates ignored automatically)

        if outcome == "success":
            self._successes += 1
        elif outcome == "fail":
            self._fails += 1

    # =========================================================================
    # SECTION 2 — Advancement Evaluation
    # =========================================================================

    def evaluate_advancement(self, required_successes: int = None,
                              over_sessions: int = None) -> bool:
        """
        Check if the child has met the advancement criteria for this session.

        Parameters:
          required_successes : int — X successes required (default from parameters)
          over_sessions      : int — Y sessions to look back (currently uses this session only)

        NOTE: "over_sessions" — currently this evaluates only the current session.
        In a future iteration, this will load the last Y session files and
        sum successes across them. The parameter is kept for forward compatibility.

        Returns True if advancement criteria are met.
        """
        x = required_successes or P.ADVANCEMENT_REQUIRED_SUCCESSES
        # Use passed value, or fall back to P.ADVANCEMENT_REQUIRED_SUCCESSES = 10

        # For now: check if this session's success count meets the threshold
        met = self._successes >= x
        # True if successes this session >= required X

        if met:
            print(f"[session_tracker] Advancement criteria met — {self._successes} successes this session (required {x})")
        else:
            print(f"[session_tracker] Advancement not yet met — {self._successes}/{x} successes this session")

        return met

    # =========================================================================
    # SECTION 3 — Session Finalisation
    # =========================================================================

    def end_session(self) -> dict:
        """
        Finalise the session and write the summary file to disk.

        Called when:
          - Parent ends session via app
          - MAX_SESSION_DURATION_MINS reached
          - System powers off

        Returns the session summary dict.
        Writes it to SESSIONS_FOLDER/session_id.json
        """
        end_time     = time.time()
        duration_sec = end_time - self._start_time
        # Total session length in seconds

        duration_mins = round(duration_sec / 60.0, 2)
        # Convert to minutes, round to 2 decimal places
        # / 60.0 divides seconds by 60 to get minutes

        advancement_met = self.evaluate_advancement()
        # Check advancement criteria and print result

        summary = {
            "session_id":      self._session_id,
            # Unique string ID e.g. "session_20260609_143022"

            "start_time":      round(self._start_time, 2),
            # Unix timestamp — round to 2 decimal places for readability

            "end_time":        round(end_time, 2),

            "duration_mins":   duration_mins,
            # e.g. 12.45 = 12 minutes 27 seconds

            "tier":            self._tier,
            # 1, 2, or 3

            "level":           self._level,
            # "L1"–"L6" for Tier 2, None otherwise

            "theme":           self._theme,
            # Theme name for Tier 3, None otherwise

            "total_touches":   len(self._events),
            # Total recorded events (excludes "ignored" touches)

            "successes":       self._successes,
            # Count of outcome="success" events

            "fails":           self._fails,
            # Count of outcome="fail" events

            "unique_pads":     len(self._unique_pads),
            # Number of different CARD_IDs touched this session

            "advancement_met": advancement_met,
            # True if child met criteria to advance to next level

            "events":          self._events
            # Full list of touch_event dicts with outcomes
            # Stored for detailed analysis by parent app
        }

        self._write_summary(summary)
        print(f"[session_tracker] Session ended — duration={duration_mins}min  successes={self._successes}  fails={self._fails}")

        return summary

    def _write_summary(self, summary: dict) -> None:
        """Write the session summary to a JSON file in SESSIONS_FOLDER."""
        folder = os.path.expanduser(P.SESSIONS_FOLDER)
        # P.SESSIONS_FOLDER = "~/tokotouch_project/sessions"
        # os.path.expanduser expands ~ to the actual home directory

        os.makedirs(folder, exist_ok=True)
        # Create the folder if it doesn't exist yet
        # exist_ok=True means no error if folder already exists

        filepath = os.path.join(folder, f"{self._session_id}.json")
        # os.path.join builds the full path: e.g.
        # "/home/pi/tokotouch_project/sessions/session_20260609_143022.json"

        with open(filepath, "w") as f:
            json.dump(summary, f, indent=2)
        # json.dump writes the Python dict as formatted JSON
        # indent=2 = 2-space indentation for human readability

        print(f"[session_tracker] Summary written to {filepath}")

    # =========================================================================
    # SECTION 4 — Session Timeout Check
    # =========================================================================

    def is_timed_out(self) -> bool:
        """
        Check if the session has exceeded MAX_SESSION_DURATION_MINS.

        Returns True if the session should be automatically ended.

        P.MAX_SESSION_DURATION_MINS = 20
        """
        elapsed_mins = (time.time() - self._start_time) / 60.0
        # Elapsed seconds / 60 = elapsed minutes

        return elapsed_mins >= P.MAX_SESSION_DURATION_MINS
        # True if session has been running for >= 20 minutes

    # =========================================================================
    # SECTION 5 — Live Stats (for app reporting)
    # =========================================================================

    def get_live_stats(self) -> dict:
        """
        Return current session statistics — for real-time app display.

        Returns a lightweight dict (no full event list).
        """
        elapsed_mins = round((time.time() - self._start_time) / 60.0, 1)

        return {
            "session_id":    self._session_id,
            "elapsed_mins":  elapsed_mins,
            # e.g. 4.7 = 4 minutes 42 seconds into the session

            "total_touches": len(self._events),
            "successes":     self._successes,
            "fails":         self._fails,
            "unique_pads":   len(self._unique_pads),
            "tier":          self._tier,
            "level":         self._level,
            "theme":         self._theme
        }
