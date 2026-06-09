# TOKO — Project Briefing
> **This document is loaded at the start of every new chat session.**
> Read it fully before responding to any request. It defines the project,
> its rules, its structure, and where all reference documents live.

---

## 1. Project Overview

**TOKO** is an interactive sensory pad system designed to support infant motor, sensory, and cognitive development.

The system is grounded in developmental science: crawling and tactile stimulation
are critical for building bilateral coordination, cross-lateral movement, and
sensorimotor integration in infants. TOKO provides a structured, engaging way to
encourage these interactions through cause-and-effect play.

**Target user:** Infants and young children (the "child").
**Secondary user:** Parents and grandparents (configure and monitor via a future app).

---

## 2. How the System Works — High Level

A child physically touches **SMART_PADs** — soft, textured pads attached to a crib
rail or play mat. Each pad has pressure sensors, LEDs, and a small vibrator.
When the child touches a pad, the system responds with light, vibration, and sound.

The system runs on a **Raspberry Pi** inside a **Control Unit**. It reads the pads
via I2C, evaluates the touch against a configurable progression map, and sends
responses back to the correct pad.

Parents control the system via a **companion app** (not yet implemented).

---

## 3. Hardware Components

### 3.1 Control Unit
The brain of the system. Contains:
- Raspberry Pi (Zero 2 W)
- LED4 and LED5 — WS2812 RGB LEDs on GPIO12 (behaviour TBD)
- Push buttons SW1 (GPIO1) and SW2 (GPIO8) (behaviour TBD)
- Power on/off switch, power cable
- Music board with small speaker (audio via ALSA `hw:1,0`)
- FPGA update connector
- Connection cable to BASE boards

### 3.2 BASE / BASE_ADAPTER Boards (×4 total)
- 1× BASE_ADAPTER — must connect on one side to the Control Unit
- 3× BASE boards — connect to each other in any order (placement is flexible)
- Each BASE supports up to 3 SMART_PADs via magnetic connectors
- Maximum: **12 SMART_PADs** total

### 3.3 SMART_PAD
The child-facing component. Each pad contains:
- 2× FSR pressure sensors (FSR0 = left, FSR1 = right, 100mm apart)
- 1× small vibrator (haptic feedback)
- 6× LEDs (configurable brightness and animation)
- A pre-programmed **CARD_ID** — the pad's permanent identity (e.g. dog, circle, football)

### 3.4 Key Hardware Principle
**CARD_ID is identity — slot position is irrelevant.**
The system always identifies pads by their CARD_ID, not by which physical slot
they are plugged into. This means pads can be placed in any order and the system
always knows what's where.

---

## 4. Communication Architecture

All SMART_PAD communication is via **I2C**, address `0x38`.
The FPGA inside the Control Unit acts as the I2C bridge to all 12 pads.

Three register groups per pad (addresses computed by slot number):

| Register Group | Base Address | Step | Bytes | Direction |
|---------------|-------------|------|-------|-----------|
| FSR sensors | `0x0A` (10) | +4/slot | 4 | Read |
| ID / Status | `0x3A` (58) | +4/slot | 4 | Read |
| LED + Vibration | `0x7A` (122) | +10/slot | 10 | Write |
| System status | `0x00` (0) | fixed | 4 | Read |

The Control Unit LEDs (LED4/LED5) use the **rpi_ws281x** library (WS2812 protocol).
Buttons and power pins use **gpiozero**.
Audio uses **mpg123** via subprocess.

---

## 5. Progression System

The system has three tiers of increasing complexity:

### Tier 1 — Free Play
Any touch on any pad → reward. No wrong answers.
Purpose: child discovers cause and effect.

### Tier 2 — Leveled Free Play
Six levels (L1–L6). Conditions tighten gradually:
- L1: any touch
- L2: minimum pressure
- L3: pressure + duration
- L4: N different pads per session
- L5: sequence of N pads
- L6: left/right FSR balance

### Tier 3 — Guided / Themed Play
Specific pads must be pressed. Tasks are defined per theme (animals, shapes, sports, etc.).
Parent loads a theme and task sequence via the app.
Tasks support sequential and simultaneous multi-pad presses.

### Advancement
System suggests advancement when child meets criteria (X successes over Y sessions).
Parent confirms via app. All thresholds are configurable parameters.

---

## 6. Hardware Engineer Reference Files

The hardware engineer (**DanisiTECH**) provided the following reference files.
These contain the actual I2C implementation, register examples, GPIO usage,
LED_MODE and VIB_MODE tables, and live terminal output examples.

**Location in project:** `DOCS/GEN4_DAN/`

| File | What it contains |
|------|-----------------|
| `DOCS/GEN4_DAN/i2c_bus.py` | PiI2CBus class — I2C wrapper using smbus2. Core of all pad communication. |
| `DOCS/GEN4_DAN/example_rw.py` | Command-line tool showing read/write register patterns. |
| `DOCS/GEN4_DAN/scan_i2c.py` | Scans I2C bus and prints detected addresses. |
| `DOCS/GEN4_DAN/GPIO12_LD4.py` | WS2812 control for LED4/LED5 via rpi_ws281x. |
| `DOCS/GEN4_DAN/GPIO13_LD10.py` | Simple GPIO blink on pin 13. |
| `DOCS/GEN4_DAN/GPIO_1_status.py` | Read push button SW1 on GPIO1. |
| `DOCS/GEN4_DAN/GPIO_8_status.py` | Read push button SW2 on GPIO8. |
| `DOCS/GEN4_DAN/GPIO_24_on.py` | Power control output on GPIO24. |
| `DOCS/GEN4_DAN/GPIO_25_status.py` | Power sense input on GPIO25. |
| `DOCS/GEN4_DAN/tokotouch_usage.docx` | Full hardware usage document including register maps, LED_MODE table (28 modes), VIB_MODE table (24 modes), and live terminal examples. |

**Three items still to confirm with the hardware engineer:**
1. CARD_ID value for an empty slot — is it `0`, or another sentinel value?
2. LED brightness bytes (0–5 in the 10-byte write) — on/off or full 0–255 scale?
3. General status register `0x00` — meaning of each of the 4 bytes.

---

## 7. Software Reference Documents

| Document | Location | Contents |
|----------|----------|----------|
| Project structure | `DOCS/TOKO_Project_Structure.md` | Folder layout, file list, one-line responsibility per file, key design principles |
| Full software reference | `DOCS/TOKO_SOFTWARE_REFERENCE.md` | Architecture, all parameters explained, register map, LED modes, VIB modes, GPIO reference |

---

## 8. Project File Structure

```
~/tokotouch_project/
│
├── main.py                            # Entry point and orchestrator
│
├── config/
│   ├── parameters.py                  # ALL tunable parameters — single source of truth
│   ├── request_response_map.json      # Tiers, levels, themes, tasks (TO BE CREATED)
│   └── system_state.json             # Current state — tier, level, theme, progress (TO BE CREATED)
│
├── engine/
│   ├── pad_interface.py               # All I2C + GPIO + audio hardware calls
│   ├── pad_discovery.py               # Startup scan, CARD_ID resolution, pad_map
│   ├── touch_processor.py             # FSR polling loop, touch classification, events
│   ├── game_engine.py                 # Tier/level/task logic, routes events to responses
│   ├── response_executor.py           # Translates map responses → hardware commands
│   └── session_tracker.py             # Records events, evaluates advancement, writes logs
│
├── app/
│   └── app_interface.py               # Parent app communication (FUTURE — not yet implemented)
│
└── DOCS/
    ├── GEN4_DAN/                      # Hardware engineer's reference files (see Section 6)
    ├── TOKO_Project_Structure.md      # Project structure reference
    └── TOKO_SOFTWARE_REFERENCE.md     # Full software reference
```

**Implementation status:**
- `main.py` ✅ complete
- `config/parameters.py` ✅ complete
- `engine/pad_interface.py` ✅ complete
- `engine/pad_discovery.py` ✅ complete
- `engine/touch_processor.py` ✅ complete
- `engine/game_engine.py` ✅ complete
- `engine/response_executor.py` ✅ complete
- `engine/session_tracker.py` ✅ complete
- `config/request_response_map.json` ⏳ next to implement
- `config/system_state.json` ⏳ next to implement
- `app/app_interface.py` 🔲 future step

---

## 9. What Is Not Yet Implemented

- `request_response_map.json` — the core logic map (Tier 1 personalities, Tier 2 levels, Tier 3 themes and tasks)
- `system_state.json` — initial state file
- `app/app_interface.py` — parent app communication (Bluetooth/Wi-Fi)
- SW1 / SW2 button behaviour — not yet decided
- LED4 / LED5 status patterns — not yet decided
- CARD_ID catalogue — the mapping from CARD_ID numbers to pad names/themes

---

## 10. Rules for This Project

These rules apply to every chat session working on TOKO. Read them before doing anything.

### 10.1 Never create code without explicit request
Do not write any code, create any file, or modify any file unless the user
explicitly asks for it with words like "implement", "create the file", "write the code".

Before any implementation:
- First explain what you understand about the requirement
- Propose the structure or logic in plain language or pseudocode
- Wait for the user to confirm understanding and give the go-ahead
- Only then write actual code

### 10.2 Everything parametric
No magic numbers in code. Every threshold, timeout, count, pin number, or
configurable value must reference `parameters.py`. If a new parameter is needed,
propose adding it to `parameters.py` first.

### 10.3 Modular and single-responsibility
Each file does one thing. No file should reach into another file's domain.
Only `pad_interface.py` talks to hardware.
Only `game_engine.py` makes game logic decisions.
Only `response_executor.py` sends LED/vibration commands.

### 10.4 Comment every non-obvious line
Every hex value must show its decimal equivalent and explain what it means.
Every formula must be explained in plain language.
Every hardware constant must reference where it comes from (engineer's doc, datasheet, etc.).

### 10.5 Hardware changes are rare and serious
Anything in the HARDWARE CONSTANTS section of `parameters.py` reflects physical
wiring or FPGA firmware. Propose changes to those values with explicit warning
and confirm with the hardware engineer before touching them.

### 10.6 Confirm before restructuring
If you believe a file, function, or data structure should be reorganised,
propose it first and explain why. Do not restructure silently.

### 10.7 Keep the reference documents up to date
After any significant implementation, update `TOKO_SOFTWARE_REFERENCE.md`
to reflect what was added or changed. The reference document is the living
truth of the codebase.
