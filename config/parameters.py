# =============================================================================
# TOKO — System Parameters
# =============================================================================
# Single source of truth for all configurable values — no magic numbers elsewhere.
#
# SECTION 1 — HARDWARE CONSTANTS: physical wiring / FPGA firmware. Don't change
#              without hardware-level intervention (re-flash, re-wire).
# SECTION 2 — SOFTWARE PARAMETERS: safe to tune anytime.
# =============================================================================


# =============================================================================
# SECTION 1 — HARDWARE CONSTANTS (do not change without special tools)
# =============================================================================

# --- I2C / FPGA Bridge ---
I2C_ADDRESS         = 0x38     # FPGA bridge I2C address
I2C_BUS_ID          = 1        # Pi I2C bus number
NUM_SLOTS           = 12       # Total SMART_PAD slots

# --- Slot Register Map (ID_I2C_Info block: ID_I2C, CARD_ID, GEN_STATUS, MICRO_VERSION) ---
# Source: tokotouch_bringup.docx / tokotouch_usage.docx. Slot N = BASE + N*STRIDE.
SLOT_ID_INFO_BASE_ADDR = 0x3A
SLOT_ID_INFO_STRIDE    = 4

# CARD_ID for an empty slot. Confirmed 2026-08-23 bring-up (0xFF reads on empty
# slots). NOTE: engine/pad_discovery.py's CARD_ID_EMPTY still assumes 0 — known bug.
SLOT_EMPTY_CARD_ID     = 0xFF

# --- Slot Register Map (FSR block: FSR0_H, FSR0_L, FSR1_H, FSR1_L) ---
SLOT_FSR_BASE_ADDR     = 0x0A
SLOT_FSR_STRIDE        = 4

# --- Slot Register Map (LED_VIBRATION block, 10 bytes) ---
# Byte layout: [LED1, LED0, LED3, LED2, LED5, LED4, VIB, LED_MODE, -, VIB_MODE]
SLOT_LED_VIB_BASE_ADDR = 0x7A
SLOT_LED_VIB_STRIDE    = 0x0A

# --- FSR Sensor Range (raw 16-bit) ---
FSR_MIN             = 0
FSR_MAX             = 65535

# --- GPIO Pin Assignments (BCM numbering, Control Unit board) ---
GPIO_LED4           = 12       # WS2812, daisy-chained
GPIO_LED5           = 13
GPIO_BUTTON_SW1     = 1
GPIO_BUTTON_SW2     = 8
GPIO_POWER_SENSE    = 25       # HIGH = power OK
GPIO_POWER_CTRL     = 24

# --- Audio Hardware ---
AUDIO_DEVICE        = "hw:1,0" # ALSA device string for the music board / speaker


# =============================================================================
# SECTION 2 — SOFTWARE PARAMETERS (safe to tune anytime)
# =============================================================================

# --- Polling ---
POLL_INTERVAL_MS                = 300   # ms between each full pad scan

# While LISTEN is idle (no slot touching, no response active), re-check slot
# occupancy this often — adds newly-connected pads, drops disconnected ones.
IDLE_RESCAN_INTERVAL_SEC        = 3

# --- Touch Pressure Thresholds (fraction of FSR_MAX) ---
# Calibrated 2026-08-26 from real presses on this hardware (observed raw FSR
# ~1900-3800 out of 65535, i.e. pressure ~0.03-0.06) — the old 0.15/0.40/0.70
# assumed presses would approach FSR_MAX, which they don't come close to.
# PRESSURE_STRONG is extrapolated above every observed sample so far (nobody
# pressed as hard as possible during calibration) — revisit once a genuine
# firm/hard press sample is captured.
PRESSURE_LIGHT                  = 0.02  # light  >= this, < MEDIUM
PRESSURE_MEDIUM                 = 0.045 # medium >= this, < STRONG
PRESSURE_STRONG                 = 0.08  # strong >= this — unverified, see above

# Minimum pressure (fraction of FSR_MAX) worth printing live during LISTEN —
# filters out sensor noise around the per-slot baseline reading.
FSR_DISPLAY_THRESHOLD            = 0.0005

# Raw FSR reading treated as "sensor not responding" rather than max pressure —
# same all-ones sentinel pattern as SLOT_EMPTY_CARD_ID (0xFF). A real press
# landing on the exact literal 16-bit ceiling is implausible.
FSR_INVALID_RAW                  = 0xFFFF

# --- Touch Duration Thresholds ---
DURATION_TAP_MS                 = 300   # <= this = tap
DURATION_HOLD_MS                = 800   # >= this = hold

# --- FSR Balance --- abs(FSR0-FSR1)/FSR_MAX above this = laterally imbalanced
BALANCE_THRESHOLD               = 0.20

# --- Multi-Pad Simultaneous Press --- max time gap to count as simultaneous
SIMULTANEOUS_WINDOW_MS          = 500

# --- Guided Task Hint --- time before hint (pad light-up) triggers
HINT_TIMEOUT_MS                 = 5000

# --- Pad Reconnection --- grace period before flagging a pad as disconnected
PAD_RECONNECT_TIMEOUT_MS        = 3000

# --- Advancement Criteria (Tier 2 default) ---
ADVANCEMENT_REQUIRED_SUCCESSES  = 10    # X successes required...
ADVANCEMENT_OVER_SESSIONS       = 3     # ...over Y sessions

# --- Session Management ---
MAX_SESSION_DURATION_MINS       = 20
SESSIONS_FOLDER                 = "~/tokotouch_project/sessions"

# --- Audio ---
AUDIO_FOLDER                    = "~/tokotouch_project/audio"

# --- Diagnostic Tool Settings (tokorun.py) ---
# LED_ID (0-5) -> byte index in the LED_VIBRATION payload (hardware order is
# fixed/non-sequential: [LED1, LED0, LED3, LED2, LED5, LED4]).
LED_IDS = {0: 1, 1: 0, 2: 3, 3: 2, 4: 5, 5: 4}
LED_TEST_BRIGHTNESS             = 255   # 0-255
LED_DURATION_SEC                = 5     # auto-off after this many seconds

# VIB_LEVEL (0-3) -> VIB intensity byte, used with vib_mode=0 (MOTOR_BEHAVE_DIRECT)
VIB_LEVELS = {0: 0, 1: 85, 2: 170, 3: 255}
VIB_DURATION_SEC                = 10    # auto-off after this many seconds

# Voice track folder, relative to repo root. Files matched by prefix,
# e.g. TRACK_ID=0 -> "Track0_*.mp3".
TRACKS_FOLDER                   = "tracks"

# --- Game Levels (tokorun.py 'start' command) ---
GAME_LEVELS_FILE                = "config/game_levels.json"  # repo-relative
DEFAULT_LEVEL                   = "level0"    # used when 'start' is typed with no level name
RESPONSE_DURATION_SEC           = 2     # how long a rule-triggered LED/vib response stays on
