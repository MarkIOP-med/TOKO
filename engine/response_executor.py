"""
response_executor.py — TOKO Response Executor
===============================================
Takes a response definition from request_response_map and translates it
into actual hardware commands — LED patterns, vibration, and sound.

A response definition (from the map) looks like:
  {
    "led_values":    [3, 3, 3, 3, 3, 3],   — brightness for each of 6 LEDs
    "led_mode":      8,                      — animation mode (0–27)
    "vib_intensity": 128,                    — vibration strength (0–255)
    "vib_mode":      1,                      — vibration behaviour (0–23)
    "sound":         "success.mp3"           — filename in AUDIO_FOLDER (or null)
  }

This module is the only place that calls pad_interface functions
in response to game logic decisions.
"""

from pad_interface import write_pad, play_sound

import sys, os
sys.path.insert(0, os.path.expanduser("~/tokotouch_project/config"))
import parameters as P


# =============================================================================
# SECTION 1 — Execute a Response
# =============================================================================

def execute_response(slot: int, response: dict) -> None:
    """
    Send LED, vibration, and sound commands for a given response definition.

    Parameters:
      slot     : int  — which SMART_PAD slot to send the command to (0–11)
      response : dict — response definition from request_response_map

    Expected keys in response dict:
      "led_values"    : list of 6 ints [LED1, LED0, LED3, LED2, LED5, LED4]
                        each 0–255 (0=off, 255=full brightness)
                        NOTE: this order matches the hardware byte layout
      "led_mode"      : int 0–27 (LED animation — see LED_MODES in reference)
      "vib_intensity" : int 0–255 (0=off, 255=maximum vibration)
      "vib_mode"      : int 0–23 (vibration behaviour — see VIB_MODES in reference)
      "sound"         : str filename (e.g. "success.mp3") or None for no sound

    All keys are optional — missing keys use safe defaults (off/silent).
    """

    # --- Extract LED parameters ---
    led_values = response.get("led_values", [0, 0, 0, 0, 0, 0])
    # Default: all 6 LEDs off
    # led_values order: [LED1, LED0, LED3, LED2, LED5, LED4]
    # This matches the hardware byte layout — not sequential numbering

    led_mode = response.get("led_mode", 0)
    # Default: 0 = LED_BLINK_SOLID (always on, no animation)
    # Range: 0–27 (see LED_MODES table)

    # --- Extract vibration parameters ---
    vib_intensity = response.get("vib_intensity", 0)
    # Default: 0 = vibration off
    # Range: 0–255 (0=off, 255=maximum)

    vib_mode = response.get("vib_mode", 6)
    # Default: 6 = MOTOR_BEHAVE_CONST_0 (hold at zero = off)
    # Range: 0–23 (see VIB_MODES table)

    # --- Send LED and vibration command to hardware ---
    success = write_pad(
        slot          = slot,
        led_values    = led_values,
        vib_intensity = vib_intensity,
        led_mode      = led_mode,
        vib_mode      = vib_mode
    )
    # write_pad sends the 10-byte I2C command to the SMART_PAD at this slot
    # Returns True if command was sent successfully, False if I2C error

    if not success:
        print(f"[response_executor] Warning: failed to write to slot {slot}")

    # --- Play sound if specified ---
    sound_file = response.get("sound")
    # sound_file = filename string (e.g. "dog_bark.mp3") or None

    if sound_file:
        play_sound(sound_file)
        # play_sound launches mpg123 in background — non-blocking
        # The system does not wait for the sound to finish


# =============================================================================
# SECTION 2 — Preset Responses
# =============================================================================
# Convenience functions for common system-level responses.
# These are used by game_engine and pad_discovery for status indication,
# not driven by the map.

def flash_all_off(slot: int) -> None:
    """Turn off all LEDs and vibration on a specific slot."""
    write_pad(
        slot          = slot,
        led_values    = [0, 0, 0, 0, 0, 0],    # all 6 LEDs off
        vib_intensity = 0,                       # vibration off
        led_mode      = 0,                       # LED_BLINK_SOLID (show as-is = off)
        vib_mode      = 6                        # MOTOR_BEHAVE_CONST_0 (hold at zero)
    )


def flash_success_quick(slot: int) -> None:
    """
    Quick visual success flash — all LEDs on at medium brightness,
    heartbeat animation, gentle vibration triangle wave.

    Used as a fallback when no map response is defined.
    """
    write_pad(
        slot          = slot,
        led_values    = [128, 128, 128, 128, 128, 128],
        # 128 = half brightness on all 6 LEDs
        # 128 decimal = 0x80 hex = 50% of 255

        vib_intensity = 80,
        # 80 decimal = 0x50 hex = ~31% vibration strength
        # Gentle enough for an infant

        led_mode      = 8,
        # 8 = LED_BLINK_HEARTBEAT (short-long-gap pattern)

        vib_mode      = 1
        # 1 = MOTOR_BEHAVE_TRIANGLE (0→255→0 smooth wave, ~1.3s cycle)
    )


def flash_hint(slot: int) -> None:
    """
    Hint pattern — slow pulse to draw child's attention to the correct pad.
    Used in Tier 3 when hint timeout fires.
    """
    write_pad(
        slot          = slot,
        led_values    = [200, 200, 200, 200, 200, 200],
        # 200 = fairly bright on all LEDs
        # 200 decimal = 0xC8 hex = ~78% brightness

        vib_intensity = 0,
        # No vibration for hint — just visual guidance

        led_mode      = 3,
        # 3 = LED_BLINK_VERY_SLOW_HALF_HZ (~0.5 Hz, 50% duty)
        # Slow, calm pulsing — not alarming for a child

        vib_mode      = 6
        # 6 = MOTOR_BEHAVE_CONST_0 (off)
    )


def flash_fail(slot: int) -> None:
    """
    Fail pattern — brief double flash, no vibration.
    Gentle enough not to distress a child.
    """
    write_pad(
        slot          = slot,
        led_values    = [50, 50, 50, 50, 50, 50],
        # 50 = dim — fail response is deliberately subtle
        # 50 decimal = 0x32 hex = ~20% brightness

        vib_intensity = 0,
        # No vibration for fail — avoid negative reinforcement

        led_mode      = 6,
        # 6 = LED_BLINK_DOUBLE_FLASH (two short flashes then pause)

        vib_mode      = 6
        # 6 = MOTOR_BEHAVE_CONST_0 (off)
    )
