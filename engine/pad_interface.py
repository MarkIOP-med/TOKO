"""
pad_interface.py — TOKO Hardware Interface
===========================================
Single entry point for ALL hardware communication.
No other engine module talks to hardware directly — they all call functions here.

Three hardware interfaces are managed here:
  1. I2C via PiI2CBus       — SMART_PAD FSR sensors, LED/vibration, CARD_ID
  2. rpi_ws281x             — Control unit LED4 and LED5 (WS2812 RGB LEDs on GPIO12)
  3. gpiozero               — Push buttons SW1/SW2, power sense/control (GPIO pins)

Register address logic (verified against hardware engineer's document):
  FSR registers    : start 0x0A (=10),  +4 per slot  → slot N = register (10 + N*4)
  ID  registers    : start 0x3A (=58),  +4 per slot  → slot N = register (58 + N*4)
  LED registers    : start 0x7A (=122), +10 per slot → slot N = register (122 + N*10)
  Status register  : 0x00 (=0), fixed, system-wide

Dependencies (install on Pi):
  pip install smbus2 rpi-ws281x gpiozero
  sudo apt install mpg123
"""

import subprocess
import sys
import os

# --- Import the engineer's I2C wrapper directly ---
# i2c_bus.py must be present in the same directory or on the Python path.
# PiI2CBus wraps smbus2 and provides read_block / write_block methods.
sys.path.insert(0, os.path.expanduser("~/tokotouch_project"))
from i2c_bus import PiI2CBus

# --- WS2812 RGB LED library (for control unit LED4/LED5 on GPIO12) ---
from rpi_ws281x import PixelStrip, Color

# --- GPIO library (for buttons and power pins) ---
from gpiozero import DigitalInputDevice, LED as GPIOOutputPin

# --- All parameters come from config — nothing hardcoded here ---
import sys
sys.path.insert(0, os.path.expanduser("~/tokotouch_project/config"))
import parameters as P


# =============================================================================
# SECTION 1 — Register Address Helpers
# =============================================================================
# These functions compute the correct register address for any slot (0–11).
# The formulas come directly from the hardware engineer's register map.

def fsr_register(slot: int) -> int:
    """
    Return the FSR register address for a given slot.

    Formula: 0x0A + slot * 4
      0x0A = 10 in decimal — the base register for slot 0
      Each slot adds 4 bytes (2 bytes FSR0 + 2 bytes FSR1)

    Examples:
      slot 0  → 10 + 0*4  = 10  = 0x0A
      slot 1  → 10 + 1*4  = 14  = 0x0E
      slot 11 → 10 + 11*4 = 54  = 0x36
    """
    return 0x0A + slot * 4      # 0x0A = 10 decimal


def id_register(slot: int) -> int:
    """
    Return the ID/Status register address for a given slot.

    Formula: 0x3A + slot * 4
      0x3A = 58 in decimal — the base register for slot 0
      Each slot adds 4 bytes (ID_I2C, CARD_ID, GEN_STATUS, MICRO_VERSION)

    Examples:
      slot 0  → 58 + 0*4  = 58  = 0x3A
      slot 1  → 58 + 1*4  = 62  = 0x3E
      slot 11 → 58 + 11*4 = 102 = 0x66
    """
    return 0x3A + slot * 4      # 0x3A = 58 decimal


def led_register(slot: int) -> int:
    """
    Return the LED/Vibration control register address for a given slot.

    Formula: 0x7A + slot * 10
      0x7A = 122 in decimal — the base register for slot 0
      Each slot takes 10 bytes (6 LED bytes + VIB + LED_MODE + reserved + VIB_MODE)

    Examples:
      slot 0  → 122 + 0*10  = 122 = 0x7A
      slot 1  → 122 + 1*10  = 132 = 0x84
      slot 11 → 122 + 11*10 = 232 = 0xE8
    """
    return 0x7A + slot * 10     # 0x7A = 122 decimal


# =============================================================================
# SECTION 2 — Control Unit LED Setup (WS2812 on GPIO12)
# =============================================================================
# LED4 and LED5 on the control unit are WS2812 RGB LEDs — they support full
# RGB colour (0–255 per channel) and are daisy-chained on GPIO12.
# They are controlled via the rpi_ws281x library, NOT via I2C.
#
# Parameters from engineer's GPIO12_LD4.py:
#   LED_COUNT   = 2       (two LEDs: LED4 and LED5)
#   LED_PIN     = 12      (BCM GPIO12)
#   LED_FREQ_HZ = 800000  (WS2812 data signal frequency — do not change)
#   LED_DMA     = 10      (DMA channel used for signal generation — do not change)
#   LED_INVERT  = False   (signal polarity — do not change)
#   LED_CHANNEL = 0       (PWM channel — do not change)
#   LED_BRIGHTNESS = 40   (global brightness 0–255; 40 = ~16% — safe default)

_control_strip = PixelStrip(
    2,          # LED_COUNT: 2 LEDs (LED4 + LED5)
    12,         # LED_PIN: BCM GPIO12
    800000,     # LED_FREQ_HZ: 800 kHz WS2812 signal — hardware requirement
    10,         # LED_DMA: DMA channel 10 — do not change
    False,      # LED_INVERT: False = normal polarity
    40,         # LED_BRIGHTNESS: 40 out of 255 (~16%) — adjust if needed
    0,          # LED_CHANNEL: PWM channel 0
)
_control_strip.begin()  # Initialise the WS2812 strip — must be called before use


# =============================================================================
# SECTION 3 — GPIO Setup (buttons and power)
# =============================================================================
# Buttons and power pins use gpiozero library.
# pull_up=False means the pin reads the actual hardware signal without
# an internal resistor pulling it high — the hardware provides its own pull.
#
# DigitalInputDevice: reads HIGH (1) or LOW (0) from a GPIO pin
# GPIOOutputPin:      sets a GPIO pin HIGH or LOW (used for power control)

_button_sw1    = DigitalInputDevice(P.GPIO_BUTTON_SW1, pull_up=False)
                 # GPIO1 — push button SW1 on control unit

_button_sw2    = DigitalInputDevice(P.GPIO_BUTTON_SW2, pull_up=False)
                 # GPIO8 — push button SW2 on control unit

_power_sense   = DigitalInputDevice(P.GPIO_POWER_SENSE, pull_up=False)
                 # GPIO25 — reads HIGH if system power is OK

_power_ctrl    = GPIOOutputPin(P.GPIO_POWER_CTRL)
                 # GPIO24 — output pin to control power state


# =============================================================================
# SECTION 4 — FSR Sensor Reading
# =============================================================================

def read_fsr(slot: int) -> tuple:
    """
    Read both FSR sensors from a SMART_PAD at the given slot (0–11).

    Returns: (fsr0_raw, fsr1_raw) as integers 0–65535

    Hardware detail:
      Each FSR sensor returns a 16-bit value split across 2 bytes:
        byte 0 = high byte of FSR0   (most significant 8 bits)
        byte 1 = low  byte of FSR0   (least significant 8 bits)
        byte 2 = high byte of FSR1
        byte 3 = low  byte of FSR1

      Reconstruction: value = (high_byte << 8) | low_byte
        << 8 means "shift left by 8 bits" = multiply by 256
        |    means "bitwise OR"           = add the low byte

      Example raw bytes: [0x12, 0x34, 0x56, 0x78]
        FSR0 = (0x12 << 8) | 0x34 = (18 × 256) + 52  = 4660
        FSR1 = (0x56 << 8) | 0x78 = (86 × 256) + 120 = 22136

    Returns (0, 0) if the slot does not respond (pad not connected).
    """
    reg = fsr_register(slot)
    # reg for slot 0 = 10 (0x0A), slot 1 = 14 (0x0E), etc.

    try:
        with PiI2CBus(P.I2C_BUS_ID) as bus:
            # Read 4 bytes from I2C address 0x38 starting at the FSR register
            # P.I2C_ADDRESS = 0x38 = 56 decimal
            data = bus.read_block(P.I2C_ADDRESS, reg, 4)
            # data is now a bytes object of length 4: [b0, b1, b2, b3]

        # Reconstruct FSR0 from bytes 0 and 1
        # data[0] is the high byte: shift it left 8 positions (= ×256)
        # data[1] is the low byte:  add it to complete the 16-bit value
        fsr0 = (data[0] << 8) | data[1]

        # Reconstruct FSR1 from bytes 2 and 3 — same logic
        fsr1 = (data[2] << 8) | data[3]

        return (fsr0, fsr1)

    except Exception:
        # If the read fails (pad disconnected, I2C error), return zeros
        return (0, 0)


def normalise_fsr(raw_value: int) -> float:
    """
    Convert a raw FSR value (0–65535) to a normalised float (0.0–1.0).

    Formula: raw_value / FSR_MAX
      P.FSR_MAX = 65535 (= 0xFFFF, the maximum 16-bit value)

    Example:
      raw = 32768  →  32768 / 65535  =  0.500  (half pressure)
      raw = 9830   →  9830  / 65535  =  0.150  (light touch threshold)
      raw = 65535  →  65535 / 65535  =  1.000  (maximum pressure)
    """
    if P.FSR_MAX == 0:
        return 0.0
    return raw_value / P.FSR_MAX    # P.FSR_MAX = 65535


# =============================================================================
# SECTION 5 — CARD_ID and Status Reading
# =============================================================================

def read_card_id(slot: int) -> dict:
    """
    Read the identity and status of the SMART_PAD at the given slot (0–11).

    Returns a dict:
      {
        "id_i2c":        int,   # byte 0 — I2C address confirmation (should = 0x38 = 56)
        "card_id":       int,   # byte 1 — the pad's identity number (e.g. 7 = dog)
        "gen_status":    int,   # byte 2 — general status (0 = OK)
        "micro_version": int,   # byte 3 — firmware version of the pad's microcontroller
        "present":       bool   # False if the read failed (pad not connected)
      }

    Example raw bytes: [0x01, 0x07, 0x00, 0x02]
      byte 0 → id_i2c        = 0x01 = 1   (I2C address confirmation)
      byte 1 → card_id       = 0x07 = 7   (pad identity — 7 = dog in animals theme)
      byte 2 → gen_status    = 0x00 = 0   (0 = OK, non-zero = error)
      byte 3 → micro_version = 0x02 = 2   (firmware version 2)
    """
    reg = id_register(slot)
    # reg for slot 0 = 58 (0x3A), slot 1 = 62 (0x3E), etc.

    try:
        with PiI2CBus(P.I2C_BUS_ID) as bus:
            data = bus.read_block(P.I2C_ADDRESS, reg, 4)
            # data = [id_i2c_byte, card_id_byte, status_byte, version_byte]

        return {
            "id_i2c":        data[0],   # byte 0: should equal 0x38 (56) if pad is genuine
            "card_id":       data[1],   # byte 1: THIS is the pad's identity (0–255)
            "gen_status":    data[2],   # byte 2: 0 = healthy, other = error code
            "micro_version": data[3],   # byte 3: firmware version number
            "present":       True       # read succeeded = pad is physically connected
        }

    except Exception:
        return {
            "id_i2c":        0,
            "card_id":       0,
            "gen_status":    0,
            "micro_version": 0,
            "present":       False      # read failed = pad not connected or not responding
        }


def read_system_status() -> dict:
    """
    Read the system-wide general status register at address 0x00.

    Returns a dict with the 4 raw bytes.
    From the engineer's terminal example:
      [0x01, 0x1E, 0xEF, 0x0F]
      byte 0 = 0x01 = 1    (status flag — meaning TBC with engineer)
      byte 1 = 0x1E = 30   (fixed value — meaning TBC with engineer)
      byte 2 = 0xEF = 239  (appears to change between reads — live health field)
      byte 3 = 0x0F = 15   (fixed value — meaning TBC with engineer)

    NOTE: Full meaning of each byte to be confirmed with hardware engineer.
    """
    try:
        with PiI2CBus(P.I2C_BUS_ID) as bus:
            # Register 0x00 = 0 decimal — the system status register
            data = bus.read_block(P.I2C_ADDRESS, 0x00, 4)
            # 0x00 = 0 decimal

        return {
            "byte0": data[0],   # 0x00 register, byte 0 — status flag (TBC)
            "byte1": data[1],   # byte 1 — fixed field (TBC)
            "byte2": data[2],   # byte 2 — live health field (changes between reads)
            "byte3": data[3],   # byte 3 — fixed field (TBC)
            "ok":    True
        }

    except Exception:
        return {"byte0": 0, "byte1": 0, "byte2": 0, "byte3": 0, "ok": False}


# =============================================================================
# SECTION 6 — LED and Vibration Control (SMART_PAD)
# =============================================================================

def write_pad(slot: int, led_values: list, vib_intensity: int,
              led_mode: int, vib_mode: int) -> bool:
    """
    Send a 10-byte command to the SMART_PAD at the given slot.

    Parameters:
      slot          : int  — slot number 0–11
      led_values    : list — 6 integers [LED1, LED0, LED3, LED2, LED5, LED4]
                             each 0–255 (0 = off, 255 = full brightness)
                             NOTE: byte order is [LED1, LED0, LED3, LED2, LED5, LED4]
                             — this is the hardware's byte ordering, not sequential
      vib_intensity : int  — vibration strength 0–255 (0 = off, 255 = maximum)
      led_mode      : int  — LED animation mode 0–27 (see LED_MODES table in reference)
      vib_mode      : int  — vibration behaviour 0–23 (see VIB_MODES table in reference)

    Returns True if write succeeded, False if it failed.

    10-byte payload layout (from hardware engineer's document):
      byte 0 = LED1          — brightness of LED1 (0–255)
      byte 1 = LED0          — brightness of LED0
      byte 2 = LED3          — brightness of LED3
      byte 3 = LED2          — brightness of LED2
      byte 4 = LED5          — brightness of LED5
      byte 5 = LED4          — brightness of LED4
      byte 6 = VIB           — vibration intensity (0–255)
      byte 7 = LED_MODE      — animation pattern (0–27)
      byte 8 = 0x00          — reserved, always zero
      byte 9 = VIB_MODE      — vibration behaviour pattern (0–23)

    Example from engineer:
      bytes: [0x01, 0x03, 0x03, 0x03, 0x03, 0x03, 0x00, 0x19, 0x00, 0x01]
        LED1=1, LED0=3, LED3=3, LED2=3, LED5=3, LED4=3
        VIB=0 (off), LED_MODE=0x19=25 (CHASE_REV_VSLOW), VIB_MODE=0x01=1 (TRIANGLE)
    """
    reg = led_register(slot)
    # reg for slot 0 = 122 (0x7A), slot 1 = 132 (0x84), etc.

    # Build the 10-byte payload
    # led_values must have exactly 6 entries: [LED1, LED0, LED3, LED2, LED5, LED4]
    payload = bytes([
        led_values[0] & 0xFF,   # byte 0: LED1  (&0xFF clamps to 0–255)
        led_values[1] & 0xFF,   # byte 1: LED0
        led_values[2] & 0xFF,   # byte 2: LED3
        led_values[3] & 0xFF,   # byte 3: LED2
        led_values[4] & 0xFF,   # byte 4: LED5
        led_values[5] & 0xFF,   # byte 5: LED4
        vib_intensity & 0xFF,   # byte 6: vibration intensity
        led_mode      & 0xFF,   # byte 7: LED animation mode
        0x00,                   # byte 8: reserved — always 0x00 = 0
        vib_mode      & 0xFF,   # byte 9: vibration behaviour mode
    ])

    try:
        with PiI2CBus(P.I2C_BUS_ID) as bus:
            bus.write_block(P.I2C_ADDRESS, reg, payload)
        return True

    except Exception:
        return False


def clear_pad(slot: int) -> bool:
    """
    Turn off all LEDs and vibration on the SMART_PAD at the given slot.

    Sends all-zero payload:
      all 6 LED values = 0 (off)
      vib_intensity    = 0 (off)
      led_mode         = 0 (SOLID — no animation)
      vib_mode         = 6 (CONST_0 = hold at 0, fully off)
    """
    return write_pad(
        slot,
        led_values    = [0, 0, 0, 0, 0, 0],    # all 6 LEDs off
        vib_intensity = 0,                       # vibration off
        led_mode      = 0,                       # 0 = LED_BLINK_SOLID (always show as-is)
        vib_mode      = 6                        # 6 = MOTOR_BEHAVE_CONST_0 (hold at zero)
    )


# =============================================================================
# SECTION 7 — Control Unit LEDs (WS2812 RGB on GPIO12)
# =============================================================================

def set_control_leds(r: int, g: int, b: int, brightness: int = 40) -> None:
    """
    Set the colour of both control unit LEDs (LED4 and LED5) simultaneously.

    Parameters:
      r          : int — red channel   0–255
      g          : int — green channel 0–255
      b          : int — blue channel  0–255
      brightness : int — global brightness 0–255 (default 40 = ~16%)

    The two WS2812 LEDs are daisy-chained on GPIO12:
      index 0 = LED4 (first in chain)
      index 1 = LED5 (second in chain)

    Color(r, g, b) creates a 24-bit colour value used by rpi_ws281x.
    setPixelColor(index, colour) stages the colour — nothing changes until show().
    show() sends the signal to the physical LEDs.
    """
    _control_strip.setBrightness(brightness)    # set global brightness (0–255)
    colour = Color(r, g, b)                     # pack RGB into single 24-bit value
    _control_strip.setPixelColor(0, colour)     # stage LED4 (index 0 in chain)
    _control_strip.setPixelColor(1, colour)     # stage LED5 (index 1 in chain)
    _control_strip.show()                       # send signal — LEDs update now


def clear_control_leds() -> None:
    """Turn off both control unit LEDs (set to black = 0, 0, 0)."""
    set_control_leds(0, 0, 0)


# =============================================================================
# SECTION 8 — Buttons and Power (GPIO)
# =============================================================================

def read_button_sw1() -> bool:
    """
    Read the state of push button SW1 (GPIO1).
    Returns True if button is pressed (HIGH), False if not pressed (LOW).

    Uses gpiozero DigitalInputDevice with pull_up=False:
      pull_up=False means no internal resistor — the hardware provides pull-down.
      .value returns 1 (True) when pin is HIGH, 0 (False) when LOW.
    """
    return bool(_button_sw1.value)  # .value = 1 (HIGH) or 0 (LOW)


def read_button_sw2() -> bool:
    """
    Read the state of push button SW2 (GPIO8).
    Returns True if button is pressed (HIGH), False if not pressed (LOW).
    """
    return bool(_button_sw2.value)


def read_power_sense() -> bool:
    """
    Read the power status from GPIO25.
    Returns True if system power is OK (HIGH), False if not (LOW).

    From engineer's GPIO_25_status.py:
      HIGH (1) = power is present and stable
      LOW  (0) = power issue or not connected
    """
    return bool(_power_sense.value)


def set_power_ctrl(state: bool) -> None:
    """
    Control the power output pin GPIO24.
      state = True  → pin HIGH (power on)
      state = False → pin LOW  (power off)

    From engineer's GPIO_24_on.py:
      pin.on()  sets GPIO24 HIGH
      pin.off() sets GPIO24 LOW
    """
    if state:
        _power_ctrl.on()    # GPIO24 HIGH
    else:
        _power_ctrl.off()   # GPIO24 LOW


# =============================================================================
# SECTION 9 — Audio
# =============================================================================

def play_sound(filename: str) -> None:
    """
    Play an audio file through the music board speaker.

    Uses mpg123 command-line player with ALSA output.
    Command constructed from engineer's example:
      mpg123 -o alsa -a hw:1,0 kid1.mp3

    Parameters:
      -o alsa     : use ALSA audio output driver
      -a hw:1,0   : use audio device hw:1,0 (the music board)
                    P.AUDIO_DEVICE = "hw:1,0"
      filename    : full path to the .mp3 file

    subprocess.Popen launches the player in the background (non-blocking).
    The system does not wait for the sound to finish before continuing.
    """
    audio_path = os.path.join(os.path.expanduser(P.AUDIO_FOLDER), filename)
    # P.AUDIO_FOLDER = "~/tokotouch_project/audio"
    # os.path.expanduser expands ~ to the actual home directory path

    if not os.path.exists(audio_path):
        print(f"[pad_interface] Audio file not found: {audio_path}")
        return

    subprocess.Popen(
        ["mpg123", "-o", "alsa", "-a", P.AUDIO_DEVICE, audio_path],
        # ["mpg123", "-o", "alsa", "-a", "hw:1,0", "/path/to/file.mp3"]
        stdout=subprocess.DEVNULL,  # suppress mpg123 console output
        stderr=subprocess.DEVNULL   # suppress mpg123 error output
    )
