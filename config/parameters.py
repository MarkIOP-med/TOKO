# =============================================================================
# TOKO — System Parameters
# =============================================================================
# This file is the single source of truth for all configurable values.
# No other module should hardcode any of these values — always import from here.
#
# TWO SECTIONS:
#   1. HARDWARE CONSTANTS — reflect physical wiring and FPGA firmware.
#      Changing these requires hardware-level intervention (re-flashing FPGA,
#      re-wiring the board). Do not change unless you know what you are doing.
#
#   2. SOFTWARE PARAMETERS — safe to tune at any time on the Raspberry Pi.
#      These control system behaviour: sensitivity, timing, advancement rules.
#      Adjust freely to match the child's age, ability, and session goals.
# =============================================================================


# =============================================================================
# SECTION 1 — HARDWARE CONSTANTS (do not change without special tools)
# =============================================================================

# --- I2C / FPGA Bridge ---
I2C_ADDRESS         = 0x38     # I2C address of the FPGA bridge (shared by all SMART_PADs)
I2C_BUS_ID          = 1        # Raspberry Pi I2C bus number (bus 1 = GPIO2/GPIO3)
NUM_SLOTS           = 12       # Total SMART_PAD slots supported by the BASE boards

# --- FSR Sensor Range ---
# Raw 16-bit values returned by each FSR sensor.
# These are determined by the SMART_PAD hardware — do not adjust.
FSR_MIN             = 0        # No pressure applied
FSR_MAX             = 65535    # Maximum pressure (16-bit ceiling)

# --- GPIO Pin Assignments (BCM numbering) ---
# All GPIO pins are physically wired on the Control Unit board.
GPIO_LED4           = 12       # Control unit LED4 (WS2812, daisy-chained)
GPIO_LED5           = 13       # Control unit LED5
GPIO_BUTTON_SW1     = 1        # Push button SW1
GPIO_BUTTON_SW2     = 8        # Push button SW2
GPIO_POWER_SENSE    = 25       # Power status sense pin (HIGH = power OK)
GPIO_POWER_CTRL     = 24       # Power control output pin

# --- Audio Hardware ---
AUDIO_DEVICE        = "hw:1,0" # ALSA device string for the music board / speaker


# =============================================================================
# SECTION 2 — SOFTWARE PARAMETERS (safe to tune anytime)
# =============================================================================

# --- Polling ---
# How often the system reads FSR sensor values from all active SMART_PADs.
# Lower = more responsive but higher CPU load.
# Higher = less responsive but lighter on resources.
POLL_INTERVAL_MS                = 500   # ms between each full pad scan

# --- Touch Pressure Thresholds ---
# Expressed as a fraction of FSR_MAX (0.0 to 1.0).
# A raw FSR value is divided by FSR_MAX to get a normalised pressure (0.0–1.0).
# Touch is classified as:
#   light  → pressure >= PRESSURE_LIGHT  and < PRESSURE_MEDIUM
#   medium → pressure >= PRESSURE_MEDIUM and < PRESSURE_STRONG
#   strong → pressure >= PRESSURE_STRONG
PRESSURE_LIGHT                  = 0.15  # Minimum fraction for a light touch
PRESSURE_MEDIUM                 = 0.40  # Minimum fraction for a medium press
PRESSURE_STRONG                 = 0.70  # Minimum fraction for a strong press

# --- Touch Duration Thresholds ---
# Duration is measured from first detection to release.
# Touch is classified as:
#   tap   → duration <= DURATION_TAP_MS
#   press → duration between tap and hold
#   hold  → duration >= DURATION_HOLD_MS
DURATION_TAP_MS                 = 300   # ms — maximum duration to classify as a tap
DURATION_HOLD_MS                = 800   # ms — minimum duration to classify as a hold

# --- FSR Balance ---
# Each SMART_PAD has two FSR sensors: FSR0 (left) and FSR1 (right).
# Balance is the normalised difference between them: abs(FSR0 - FSR1) / FSR_MAX.
# If balance exceeds this threshold, the touch is flagged as laterally imbalanced.
# Used in Tier 2 Level 6 and available for future logic.
BALANCE_THRESHOLD               = 0.20  # Fraction — max allowed left/right difference

# --- Multi-Pad Simultaneous Press ---
# In Tier 3 guided tasks, some tasks require pressing multiple pads at the same time.
# This window defines how close in time two presses must be to count as simultaneous.
SIMULTANEOUS_WINDOW_MS          = 500   # ms — tolerance window for simultaneous presses

# --- Guided Task Hint ---
# If the child has not pressed the expected pad(s) within this timeout,
# the system triggers a hint response (lights up the correct pad).
HINT_TIMEOUT_MS                 = 5000  # ms — time before hint is triggered

# --- Pad Reconnection ---
# When a SMART_PAD stops responding mid-session (likely magnetically detached),
# the system waits this long before officially flagging it as disconnected.
# This avoids false alarms from brief magnetic connection interruptions.
PAD_RECONNECT_TIMEOUT_MS        = 3000  # ms — grace period before flagging as missing

# --- Advancement Criteria (default values) ---
# These defaults apply to all Tier 2 levels unless overridden in the map.
# The system suggests advancement when the child achieves
# ADVANCEMENT_REQUIRED_SUCCESSES successful touches across the last
# ADVANCEMENT_OVER_SESSIONS sessions.
ADVANCEMENT_REQUIRED_SUCCESSES  = 10    # X — number of successes required
ADVANCEMENT_OVER_SESSIONS       = 3     # Y — number of sessions to measure over

# --- Session Management ---
MAX_SESSION_DURATION_MINS       = 20    # Session auto-closes after this many minutes
SESSIONS_FOLDER                 = "~/tokotouch_project/sessions"  # Session log output path

# --- Audio ---
AUDIO_FOLDER                    = "~/tokotouch_project/audio"     # Sound files location
