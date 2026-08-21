/*
  toko_control_v2.ino — CONTROL (simple loop) + MP3 like SmartTouch_v1

  Loop (every POLL_PERIOD_MS):
    - For each module port: send "p\n", read up to 6 ints (touchset) with short timeout.
    - If 6 arrived: compute 3 pad values (max of pairs) -> levels (0..3) -> active pad.
    - Apply adapted protocol:
        Active pad: LED static(level), VIB max static.
        Other pads: LED dynamic (BREATH/TWINKLE/WAVE) by active level.
        MP3: on level change, play track (startup track already plays in setup).
    - Only send/play when state changed (no spam).
*/

#include <Arduino.h>
#include "ControlConfig.h"
#include "ControlComms.h"
#include "MP3Player.h"

struct ModuleState {
  HardwareSerial* port = nullptr;     // &Serial2 / &Serial3
  uint8_t lastPadLevels[3] = {0,0,0}; // what we last considered for each pad
  int8_t  lastActivePad    = -1;      // -1..2
  uint8_t lastMp3Level     = 0;       // 0..3 (for per-module MP3 dedupe)
};

static ModuleState g_mod[2];

static inline uint8_t levelFromValue(int v) {
  if (v >= LVL3) return 3;
  if (v >= LVL2) return 2;
  if (v >= LVL1) return 1;
  return 0;
}

static void applyAdaptedProtocol(ModuleState& ms, HardwareSerial* port, const uint8_t padLevels[3]) {
  // Active pad = highest level (>0), tie → lowest index
  int8_t activePad = -1;
  uint8_t activeLvl = 0;
  for (uint8_t i=0;i<3;++i) {
    if (padLevels[i] > activeLvl) { activeLvl = padLevels[i]; activePad = (int8_t)i; }
  }

  // If nothing changed, do nothing
  bool changed = (activePad != ms.lastActivePad) || (activePad>=0 && activeLvl != ms.lastPadLevels[activePad]);
  if (!changed) return;

  if (activePad < 0) {
    // All pads idle → turn off any pad that was nonzero last time
    for (uint8_t i=0;i<3;++i) {
      if (ms.lastPadLevels[i] > 0) ControlComms::sendLED(port, i, 0, 's');
      ms.lastPadLevels[i] = 0;
    }
    ms.lastActivePad = -1;
    ms.lastMp3Level  = 0;
    if (DEBUG_PRINT_LEVELS) Serial.println(F("[Apply] all pads idle"));
    return;
  }

  // Active pad: static LED by level + max static vibration (pattern 1)
  ControlComms::sendLED(port, activePad, activeLvl, 's');
  ControlComms::sendVIB(port, activePad, activeLvl, 's', 1);

  // Other two pads: dynamic LED by ACTIVE level
  uint8_t eff = EFFECT_BY_LEVEL[activeLvl];
  for (uint8_t i=0;i<3;++i) {
    if ((int8_t)i == activePad) continue;
    ControlComms::sendLED(port, i, 0, 'd', eff);
    ms.lastPadLevels[i] = 0; // mark non-static
  }

  // MP3: only on level change for this module
  if (USE_MP3 && activeLvl != ms.lastMp3Level) {
    MP3Player::playForLevel(activeLvl);
    ms.lastMp3Level = activeLvl;
  }

  // Remember what we did
  ms.lastPadLevels[activePad] = activeLvl;
  ms.lastActivePad = activePad;

  if (DEBUG_PRINT_LEVELS) {
    Serial.print(F("[Apply] active=")); Serial.print(activePad);
    Serial.print(F(" lvl=")); Serial.print(activeLvl);
    Serial.print(F(" others eff=")); Serial.println(eff);
  }
}

void setup() {
  Serial.begin(USB_BAUD);

  // Init module ports (up to two)
  for (uint8_t i=0;i<NUM_MODULES;++i) {
    g_mod[i].port = MODULE_PORTS[i];
    if (MODULE_PORTS[i]) MODULE_PORTS[i]->begin(MODULE_BAUD);
  }

  if (USE_MP3) MP3Player::begin(); // sets volume, plays startup track once

  Serial.println(F("[Init] Toko Control v2 ready"));
}

void loop() {
  uint32_t tStart = millis();

  for (uint8_t i=0;i<NUM_MODULES;++i) {
    HardwareSerial* port = g_mod[i].port;
    if (!port) continue;

    ControlComms::sendP(port);
    int vals[6];
    bool ok = ControlComms::readTouchset(port, vals);
    if (!ok) {
      if (DEBUG_PRINT_NO_TOUCHSET) { Serial.print(F("[Module ")); Serial.print(i); Serial.println(F("] no touchset")); }
      continue; // silent this cycle
    }

    // One clean line with all 6 pressures (human-friendly)
    if (DEBUG_PRINT_PRESSURES) {
      Serial.print(F("[Module ")); Serial.print(i); Serial.print(F("] pressures: "));
      for (int k=0;k<6;++k){ Serial.print(vals[k]); if(k<5) Serial.print(','); }
      Serial.println();
    }

    // Compute per-pad values (MAX of each sensor pair)
    int padVal[3];
    padVal[0] = max(vals[0], vals[1]);
    padVal[1] = max(vals[2], vals[3]);
    padVal[2] = max(vals[4], vals[5]);

    // Map to levels
    uint8_t padLvl[3];
    padLvl[0] = levelFromValue(padVal[0]);
    padLvl[1] = levelFromValue(padVal[1]);
    padLvl[2] = levelFromValue(padVal[2]);

    if (DEBUG_PRINT_LEVELS) {
      Serial.print(F("[Module ")); Serial.print(i); Serial.print(F("] padVal: "));
      Serial.print(padVal[0]); Serial.print(','); Serial.print(padVal[1]); Serial.print(','); Serial.print(padVal[2]);
      Serial.print(F("  levels: "));
      Serial.print(padLvl[0]); Serial.print(','); Serial.print(padLvl[1]); Serial.print(','); Serial.print(padLvl[2]);
      Serial.println();
    }

    // Apply protocol (only if changed)
    applyAdaptedProtocol(g_mod[i], port, padLvl);
  }

  // keep the rhythm: wait the remainder of POLL_PERIOD_MS
  int32_t elapsed = (int32_t)(millis() - tStart);
  int32_t waitMs = (int32_t)POLL_PERIOD_MS - elapsed;
  if (waitMs > 0) delay((uint16_t)waitMs);
}