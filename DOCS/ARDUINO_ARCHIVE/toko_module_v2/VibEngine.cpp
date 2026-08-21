#include "VibEngine.h"
#include "Config.h"

static bool     vActive[PADS]   = {false,false,false};
static uint8_t  vPattern[PADS]  = {0,0,0};     // 1..3
static uint32_t vStartMs[PADS]  = {0,0,0};
static uint32_t vEndMs[PADS]    = {0,0,0};

void VibEngine::init() {
  for (uint8_t i=0;i<PADS;++i) { pinMode(VIB_PINS[i], OUTPUT); analogWrite(VIB_PINS[i], 0); }
}

void VibEngine::stop(uint8_t pad) {
  analogWrite(VIB_PINS[pad], 0);
  vActive[pad]  = false;
  vPattern[pad] = 0;
}

void VibEngine::start(uint8_t pad, uint8_t pattern) {
  if (pad >= PADS) return;
  vActive[pad]  = true;
  vPattern[pad] = (pattern<1 || pattern>3) ? 1 : pattern;
  vStartMs[pad] = millis();
  vEndMs[pad]   = vStartMs[pad] + VIB_PULSE_MS;
  analogWrite(VIB_PINS[pad], VIB_MAX_INTENSITY); // immediate kick
}

void VibEngine::serviceFrame() {
  uint32_t now = millis();
  for (uint8_t pad=0; pad<PADS; ++pad) {
    if (!vActive[pad]) continue;
    if ((int32_t)(now - vEndMs[pad]) >= 0) { stop(pad); continue; }

    uint32_t elapsed = now - vStartMs[pad];
    uint8_t pwm = 0;

    switch (vPattern[pad]) {
      case 2: { // RAMP
        uint16_t half = VIB_PULSE_MS/2;
        if (elapsed < half) pwm = (uint8_t)( ( (uint32_t)VIB_MAX_INTENSITY * elapsed ) / half );
        else {
          uint32_t down = elapsed - half;
          pwm = (uint8_t)( VIB_MAX_INTENSITY - ( (uint32_t)VIB_MAX_INTENSITY * down ) / half );
        }
        break;
      }
      case 3: { // BURSTS
        const uint16_t chunk = 150; // ms
        bool on = ((elapsed / chunk) % 2) == 0;
        pwm = on ? VIB_MAX_INTENSITY : 0;
        break;
      }
      default: { // 1: PULSE
        pwm = VIB_MAX_INTENSITY;
        break;
      }
    }
    analogWrite(VIB_PINS[pad], pwm);
  }
}
