# TOKO — Software Reference

> Living technical reference for the TOKO system software.
> Updated as each development step is completed.

---

## 1. Project Overview

TOKO is the software system running on the Raspberry Pi inside the Control Unit. It manages a network of up to 12 SMART_PAD sensors connected via BASE boards, reads child touch interactions, and responds with light, vibration, and sound feedback according to a configurable progression map.

The system supports three tiers of play — free play, leveled free play, and guided themed tasks — and is designed to support infant motor and sensory development. A parent app communicates with the system for configuration and monitoring (future step).

---

## 2. Project Structure

```
~/tokotouch_project/
│
├── main.py                            # Entry point, orchestrator
│
├── config/
│   ├── parameters.py                  # All tunable parameters
│   ├── request_response_map.json      # Tiers, levels, themes, tasks
│   └── system_state.json             # Current state — tier, level, theme, progress
│
├── engine/
│   ├── pad_interface.py               # I2C communication — read FSR, write LED/vib
│   ├── pad_discovery.py               # Startup scan, CARD_ID resolution, pad_map
│   ├── touch_processor.py             # FSR polling, touch classification
│   ├── game_engine.py                 # Tier/level/task logic
│   ├── response_executor.py           # Sends LED/vib/sound commands
│   └── session_tracker.py             # Logging, advancement evaluation
│
└── app/
    └── app_interface.py               # Communication with parent app (future)
```

### File Responsibilities

| File | Responsibility |
|------|----------------|
| `main.py` | Entry point. Starts all modules, runs the main loop, handles graceful shutdown. |
| `config/parameters.py` | All tunable parameters in one place. Nothing is hardcoded elsewhere. |
| `config/request_response_map.json` | The main logic map — Tier 1 personalities, Tier 2 levels, Tier 3 themes and tasks. |
| `config/system_state.json` | Current runtime state — active tier, level, theme, child progress. Persisted to disk. |
| `engine/pad_interface.py` | All I2C communication. Reads FSR sensors, writes LED/vibration, reads CARD_IDs. |
| `engine/pad_discovery.py` | Startup scan. Builds pad_map, detects missing pads, determines run mode. |
| `engine/touch_processor.py` | Polling loop. Classifies touches by pressure and duration. Emits touch_event objects. |
| `engine/game_engine.py` | Core logic. Evaluates touch_events against the map. Decides success/fail/hint. |
| `engine/response_executor.py` | Response delivery. Sends LED, vibration, and sound commands via pad_interface. |
| `engine/session_tracker.py` | Session logging. Records events, evaluates advancement, writes session summary. |
| `app/app_interface.py` | Parent app communication — inventory, mode selection, status, summaries (future). |

### Key Design Principles

- **Everything parametric** — all thresholds, counts, and timing values live in `parameters.py`. Nothing is hardcoded.
- **CARD_ID is identity** — physical slot position is irrelevant. The system always works from CARD_ID.
- **Config drives behaviour** — `request_response_map.json` defines all logic. Changing behaviour means editing the map, not the code.
- **State is persisted** — `system_state.json` is written to disk after every meaningful change so the system can resume after a reboot.
- **Single I2C entry point** — only `pad_interface.py` communicates with hardware. All other modules call its functions.

---

## 3. Config Files

### 3.1 `parameters.py`

Single source of truth for all configurable values. Divided into two sections.

#### Section 1 — Hardware Constants
These reflect physical wiring and FPGA firmware. Changing them requires hardware-level intervention (re-flashing FPGA, re-wiring the board).

| Parameter | Value | Meaning |
|-----------|-------|---------|
| `I2C_ADDRESS` | `0x38` | I2C address of the FPGA bridge (shared by all SMART_PADs) |
| `I2C_BUS_ID` | `1` | Raspberry Pi I2C bus number (bus 1 = GPIO2/GPIO3) |
| `NUM_SLOTS` | `12` | Total SMART_PAD slots supported by the BASE boards |
| `FSR_MIN` | `0` | Raw FSR sensor minimum value (no pressure) |
| `FSR_MAX` | `65535` | Raw FSR sensor maximum value (16-bit ceiling) |
| `GPIO_LED4` | `12` | Control unit LED4 (WS2812, daisy-chained) |
| `GPIO_LED5` | `13` | Control unit LED5 |
| `GPIO_BUTTON_SW1` | `1` | Push button SW1 |
| `GPIO_BUTTON_SW2` | `8` | Push button SW2 |
| `GPIO_POWER_SENSE` | `25` | Power status sense pin (HIGH = power OK) |
| `GPIO_POWER_CTRL` | `24` | Power control output pin |
| `AUDIO_DEVICE` | `"hw:1,0"` | ALSA device string for the music board / speaker |

#### Section 2 — Software Parameters
Safe to tune at any time on the Raspberry Pi to match the child's age, ability, and session goals.

| Parameter | Default | Meaning |
|-----------|---------|---------|
| `POLL_INTERVAL_MS` | `500` | ms between each full pad scan |
| `PRESSURE_LIGHT` | `0.15` | Normalised FSR fraction — minimum for a light touch |
| `PRESSURE_MEDIUM` | `0.40` | Normalised FSR fraction — minimum for a medium press |
| `PRESSURE_STRONG` | `0.70` | Normalised FSR fraction — minimum for a strong press |
| `DURATION_TAP_MS` | `300` | ms — maximum duration to classify as a tap |
| `DURATION_HOLD_MS` | `800` | ms — minimum duration to classify as a hold |
| `BALANCE_THRESHOLD` | `0.20` | Max normalised left/right FSR difference before flagging imbalance |
| `SIMULTANEOUS_WINDOW_MS` | `500` | ms — tolerance window for multi-pad simultaneous presses |
| `HINT_TIMEOUT_MS` | `5000` | ms — time before hint is triggered in a guided task |
| `PAD_RECONNECT_TIMEOUT_MS` | `3000` | ms — grace period before flagging a pad as truly missing |
| `ADVANCEMENT_REQUIRED_SUCCESSES` | `10` | X — successes needed to suggest level advancement |
| `ADVANCEMENT_OVER_SESSIONS` | `3` | Y — number of sessions to measure successes over |
| `MAX_SESSION_DURATION_MINS` | `20` | Session auto-closes after this many minutes |
| `SESSIONS_FOLDER` | `~/tokotouch_project/sessions` | Where session log files are saved |
| `AUDIO_FOLDER` | `~/tokotouch_project/audio` | Where sound files are stored |

#### Touch Classification Logic

**Pressure** is normalised: `raw_value / FSR_MAX` → gives a float 0.0–1.0.

| Class | Condition |
|-------|-----------|
| `light` | pressure >= `PRESSURE_LIGHT` and < `PRESSURE_MEDIUM` |
| `medium` | pressure >= `PRESSURE_MEDIUM` and < `PRESSURE_STRONG` |
| `strong` | pressure >= `PRESSURE_STRONG` |

**Duration** is measured from first detection to release.

| Class | Condition |
|-------|-----------|
| `tap` | duration <= `DURATION_TAP_MS` |
| `press` | duration between tap and hold |
| `hold` | duration >= `DURATION_HOLD_MS` |

**Balance** is: `abs(FSR0 - FSR1) / FSR_MAX`. If > `BALANCE_THRESHOLD`, the touch is flagged as laterally imbalanced.

---

### 3.2 `request_response_map.json`

> To be documented in next step.

---

### 3.3 `system_state.json`

> To be documented in next step.

---

## 4. Engine Modules

> To be documented in Step 3.

---

## 5. Hardware Reference

### Register Map

All SMART_PAD communication uses I2C address `0x38`. The FPGA acts as the bridge.

#### FSR Registers (read only, 4 bytes per slot)

| Slot | Register | Bytes |
|------|----------|-------|
| 0 | `0x0A` | FSR0_H, FSR0_L, FSR1_H, FSR1_L |
| 1 | `0x0E` | … |
| … | +4 per slot | … |
| 11 | `0x36` | … |

Reconstruct 16-bit value: `fsr = (high_byte << 8) | low_byte`

#### ID / Status Registers (read only, 4 bytes per slot)

| Slot | Register | Bytes |
|------|----------|-------|
| 0 | `0x3A` | ID_I2C, CARD_ID, GEN_STATUS, MICRO_VERSION |
| 1 | `0x3E` | … |
| … | +4 per slot | … |
| 11 | `0x66` | … |

#### LED + Vibration Control (write, 10 bytes per slot)

| Slot | Register |
|------|----------|
| 0 | `0x7A` |
| 1 | `0x84` |
| … | +10 per slot |
| 11 | `0xE8` |

Byte layout of the 10-byte payload:

| Byte | Field | Notes |
|------|-------|-------|
| 0 | LED1 | brightness / state |
| 1 | LED0 | |
| 2 | LED3 | |
| 3 | LED2 | |
| 4 | LED5 | |
| 5 | LED4 | |
| 6 | VIB | vibration intensity (0–255) |
| 7 | LED_MODE | see LED mode table |
| 8 | reserved | always 0x00 |
| 9 | VIB_MODE | see vibration mode table |

#### General Status Register

| Register | Bytes | Notes |
|----------|-------|-------|
| `0x00` | 4 | System-wide status. Third byte appears to be a live health field. |

---

### LED Modes (LED_MODE — Byte 7)

| Value | Constant | Description |
|-------|----------|-------------|
| 0 | `LED_BLINK_SOLID` | Always on — no blink |
| 1 | `LED_BLINK_SLOW_2HZ5` | ~2.5 Hz, 50% duty |
| 2 | `LED_BLINK_FAST_12HZ5` | ~12.5 Hz, 50% duty |
| 3 | `LED_BLINK_VERY_SLOW_HALF_HZ` | ~0.5 Hz, 50% duty |
| 4 | `LED_BLINK_SLOW_PULSE_25` | Slow period, ~25% on |
| 5 | `LED_BLINK_SLOW_PULSE_75` | Slow period, ~75% on |
| 6 | `LED_BLINK_DOUBLE_FLASH` | Two short flashes, then pause |
| 7 | `LED_BLINK_TRIPLE_FLASH` | Three short flashes, then pause |
| 8 | `LED_BLINK_HEARTBEAT` | Short-long-gap |
| 9 | `LED_BLINK_STROBE_10` | Fast period, ~10% on |
| 10 | `LED_BLINK_STROBE_90` | Fast period, ~90% on |
| 11 | `LED_BLINK_MEDIUM_33` | Medium period, ~33% on |
| 12 | `LED_BLINK_PULSE_5` | Rare short pulse (~5% on) |
| 13 | `LED_BLINK_PULSE_15` | Short pulse (~15% on) |
| 14 | `LED_BLINK_ONCE_PER_SEC` | ~1 narrow flash per second |
| 15 | `LED_BLINK_ALTERNATE_DUTY` | Alternates wide/narrow each period |
| 16 | `LED_BLINK_CHASE_FWD` | Chase ~75ms/step, forward |
| 17 | `LED_BLINK_CHASE_REV` | Chase ~75ms/step, reverse |
| 18 | `LED_BLINK_CHASE_FWD_FAST` | ~40ms/step, forward |
| 19 | `LED_BLINK_CHASE_REV_FAST` | ~40ms/step, reverse |
| 20 | `LED_BLINK_CHASE_FWD_VFAST` | ~25ms/step, forward |
| 21 | `LED_BLINK_CHASE_REV_VFAST` | ~25ms/step, reverse |
| 22 | `LED_BLINK_CHASE_FWD_SLOW` | ~125ms/step, forward |
| 23 | `LED_BLINK_CHASE_REV_SLOW` | ~125ms/step, reverse |
| 24 | `LED_BLINK_CHASE_FWD_VSLOW` | ~200ms/step, forward |
| 25 | `LED_BLINK_CHASE_REV_VSLOW` | ~200ms/step, reverse |
| 26 | `LED_BLINK_CHASE_FWD_CRAWL` | ~300ms/step, forward |
| 27 | `LED_BLINK_CHASE_REV_CRAWL` | ~300ms/step, reverse |

---

### Vibration Modes (VIB_MODE — Byte 9)

| Value | Constant | Description |
|-------|----------|-------------|
| 0 | `MOTOR_BEHAVE_DIRECT` | Direct DC value from host (no animation) |
| 1 | `MOTOR_BEHAVE_TRIANGLE` | 0→FF→0, ~1.3s full cycle |
| 2 | `MOTOR_BEHAVE_SAW_UP` | 0→FF linear, repeat |
| 3 | `MOTOR_BEHAVE_SAW_DOWN` | FF→0 linear, repeat |
| 4 | `MOTOR_BEHAVE_SQUARE_SLOW` | 0/255 ~320ms each level |
| 5 | `MOTOR_BEHAVE_SQUARE_FAST` | 0/255 ~40ms each level |
| 6 | `MOTOR_BEHAVE_CONST_0` | Hold 0 (off) |
| 7 | `MOTOR_BEHAVE_CONST_MID` | Hold 127 |
| 8 | `MOTOR_BEHAVE_CONST_MAX` | Hold 255 (full on) |
| 9 | `MOTOR_BEHAVE_TRIANGLE_SLOW` | Same as 1, ~4x slower |
| 10 | `MOTOR_BEHAVE_TRIANGLE_FAST` | Same as 1, ~2x faster |
| 11 | `MOTOR_BEHAVE_STAIR_8` | 8 coarse steps 0..252 |
| 12 | `MOTOR_BEHAVE_STAIR_16` | 16 steps 0..255 |
| 13 | `MOTOR_BEHAVE_PULSE_TRAIN` | Bursts of 255 then 0 |
| 14 | `MOTOR_BEHAVE_TRIANGLE_SCALED` | Triangle 0..MOTOR_DC..0 |
| 15 | `MOTOR_BEHAVE_SAW_UP_SCALED` | Saw 0..MOTOR_DC repeat |
| 16 | `MOTOR_BEHAVE_SAW_DN_SCALED` | Saw MOTOR_DC..0 repeat |
| 17 | `MOTOR_BEHAVE_ALT_85_170` | Toggle 85/170 |
| 18 | `MOTOR_BEHAVE_ALT_0_MID_MAX` | Cycle 0, 127, 255 |
| 19 | `MOTOR_BEHAVE_INVERT_TRIANGLE` | 255 - triangle |
| 20 | `MOTOR_BEHAVE_BREATHE` | Narrow swing ~127 ± 48 |
| 21 | `MOTOR_BEHAVE_RANDOM` | Pseudo-random 0..255 (LFSR) |
| 22 | `MOTOR_BEHAVE_SQUARE_SCALED` | Slow square 0/MOTOR_DC |
| 23 | `MOTOR_BEHAVE_STAIRCASE_UD` | 16-step up then 16-step down |

---

### GPIO Reference

| GPIO (BCM) | Direction | Function |
|------------|-----------|----------|
| 1 | Input | Push button SW1 |
| 8 | Input | Push button SW2 |
| 12 | Output | Control unit LED4 (WS2812) |
| 13 | Output | Control unit LED5 |
| 24 | Output | Power control |
| 25 | Input | Power sense (HIGH = OK) |

---

*Document version: Step 2 complete — config/parameters.py*
