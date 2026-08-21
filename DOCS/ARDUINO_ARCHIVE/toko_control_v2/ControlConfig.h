#pragma once
#include <Arduino.h>

/* ---------- USB debug ---------- */
static const uint32_t USB_BAUD = 115200;

/* ---------- Module UARTs (set to your wiring) ---------- */
static HardwareSerial* const MODULE_PORTS[2] = { &Serial1, &Serial2 };
static const uint8_t  NUM_MODULES  = 2;
static const uint32_t MODULE_BAUD  = 4800;

/* ---------- Timing ---------- */
static const uint16_t POLL_PERIOD_MS        = 500; // 0.5s rhythm
static const uint16_t READ_TIMEOUT_MS       = 120; // relaxed to allow 6 lines @4800 baud
static const uint16_t INTER_LINE_TIMEOUT_MS = 40;  // relaxed gap between lines

/* ---------- Thresholds (0..255) ---------- */
static const int LVL1 = 50;
static const int LVL2 = 150;
static const int LVL3 = 200;

/* ---------- Dynamic LED effect for non-active pads ---------- */
enum : uint8_t { EFFECT_NONE=0, EFFECT_BREATH=1, EFFECT_TWINKLE=2, EFFECT_WAVE=3 };
static const uint8_t EFFECT_BY_LEVEL[4] = {
  EFFECT_NONE, EFFECT_BREATH, EFFECT_TWINKLE, EFFECT_WAVE
};

/* ---------- MP3 via SoftwareSerial (RX=11, TX=10) ---------- */
#define USE_MP3 1
#if USE_MP3
static const uint8_t  MP3_RX_PIN      = 11;      // SoftwareSerial RX  (module TX)
static const uint8_t  MP3_TX_PIN      = 10;      // SoftwareSerial TX  (module RX)
static const uint32_t MP3_BAUD        = 9600;
static const uint8_t  MP3_BUSY_PIN    = 3;       // HIGH = idle, LOW = playing
static const uint8_t  MP3_VOLUME      = 30;      // 0..30
static const uint16_t TRACK_STARTUP     = 1;              // play once in setup
static const uint16_t TRACK_BY_LEVEL[4] = { 0, 2, 3, 4 }; // L0 none, L1=2, L2=3, L3=4
static const uint16_t MP3_COOLDOWN_MS   = 400;
#endif

/* ---------- Debug ---------- */
// per-line RX spam: OFF
static const bool DEBUG_PRINT_PER_VALUE = false;
// one-line summary of all 6 pressures (on full touchset): ON
static const bool DEBUG_PRINT_PRESSURES = true;
// detailed pad/level line: OFF (can turn ON if you want)
static const bool DEBUG_PRINT_LEVELS   = false;
// print actions we send (LED/VIB/MP3): ON
static const bool DEBUG_PRINT_ACTIONS  = true;
// print "no touchset" when a module is silent this cycle: OFF
static const bool DEBUG_PRINT_NO_TOUCHSET = false;
