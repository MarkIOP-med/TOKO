# TOKO — Project Structure

## Overview
The project is organized into three folders with clear, separated responsibilities, plus a single entry point.

---

## Folder & File Map

```
~/tokotouch_project/
│
├── main.py
├── config/
│   ├── parameters.py
│   ├── request_response_map.json
│   └── system_state.json
│
├── engine/
│   ├── pad_interface.py
│   ├── pad_discovery.py
│   ├── touch_processor.py
│   ├── game_engine.py
│   ├── response_executor.py
│   └── session_tracker.py
│
└── app/
    └── app_interface.py
```

---

## File Descriptions

### Root

| File | Responsibility |
|------|---------------|
| `main.py` | Entry point. Starts all modules, runs the main loop, handles graceful shutdown. |

---

### config/

| File | Responsibility |
|------|---------------|
| `parameters.py` | All tunable parameters in one place — poll interval, pressure thresholds, touch duration bands, advancement rule values, timing tolerances. Nothing is hardcoded elsewhere. |
| `request_response_map.json` | The main logic map — defines Tier 1 pad personalities, Tier 2 level conditions and advancement criteria, Tier 3 themes and tasks. |
| `system_state.json` | Current runtime state — active tier, active level, active theme, child progress, session history summary. Persisted to disk so state survives a reboot. |

---

### engine/

| File | Responsibility |
|------|---------------|
| `pad_interface.py` | All I2C communication. Reads FSR sensor values, writes LED and vibration commands, reads CARD_ID and status registers. No other module touches I2C directly. |
| `pad_discovery.py` | Startup scan. Polls all 12 slots, reads CARD_IDs, builds the `pad_map`, detects missing or unknown pads, determines run mode (free play vs guided). |
| `touch_processor.py` | Polling loop. Reads FSR values at each poll interval, classifies touches by pressure and duration (light / medium / strong), computes FSR balance, emits structured `touch_event` objects. |
| `game_engine.py` | Core logic. Receives `touch_events`, looks up current tier/level/task in the map, evaluates conditions, decides which response to trigger (success / fail / hint). |
| `response_executor.py` | Response delivery. Takes a response definition from the map and sends the corresponding LED, vibration, and sound commands via `pad_interface.py`. |
| `session_tracker.py` | Session logging. Records touch events, successes, failures, and session duration. Evaluates advancement criteria. Writes session summary to disk for the app to read. |

---

### app/

| File | Responsibility |
|------|---------------|
| `app_interface.py` | Parent app communication. Sends startup pad inventory, receives mode and theme selection, streams live status, sends advancement suggestions and session summaries. |

---

## Key Design Principles

- **Everything parametric** — all thresholds, counts, and timing values live in `parameters.py`. Nothing is hardcoded.
- **CARD_ID is identity** — physical slot position is irrelevant. The system always works from CARD_ID.
- **Config drives behaviour** — `request_response_map.json` defines all logic. Changing behaviour means editing the map, not the code.
- **State is persisted** — `system_state.json` is written to disk after every meaningful change so the system can resume after a reboot.
- **Single I2C entry point** — only `pad_interface.py` communicates with hardware. All other modules call its functions.
