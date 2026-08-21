#include "Pressure.h"
#include "Config.h"

static uint16_t g_baselineRaw[6] = {0,0,0,0,0,0};

static inline uint8_t clampU8(int v) {
  if (v < 0) return 0; if (v > 255) return 255; return (uint8_t)v;
}

void Pressure::calibrateBaselines() {
  uint32_t acc[6] = {0,0,0,0,0,0};
  for (uint8_t s = 0; s < CALIB_SAMPLES; ++s) {
    for (uint8_t i = 0; i < 6; ++i) acc[i] += analogRead(SENSOR_PINS[i]);
    delay(5);
  }
  for (uint8_t i = 0; i < 6; ++i) g_baselineRaw[i] = (uint16_t)(acc[i] / CALIB_SAMPLES);

  Serial.print(F("[Calib] Baseline: "));
  for (uint8_t i=0;i<6;++i){ Serial.print(g_baselineRaw[i]); if (i<5) Serial.print(','); }
  Serial.println();
}

int Pressure::readNormalized(uint8_t ch) {
  int raw = analogRead(SENSOR_PINS[ch]);       // 0..1023
  int delta = raw - (int)g_baselineRaw[ch];
  if (CLAMP_TO_ZERO && delta < 0) delta = 0;
  int scaled = delta / SENSOR_SCALE_DIV;       // approx 0..255
  return clampU8(scaled);
}

void Pressure::sendAllToControl(Stream& out) {
  int vals[6];
  for (uint8_t i=0;i<6;++i) {
    vals[i] = readNormalized(i);
    out.println(vals[i]);                      // to Control (mySerial)
    if (DEBUG_MIRROR_TX_PRESSURE) { Serial.print(F("[TX→mySerial] ")); Serial.println(vals[i]); }
  }
  if (DEBUG_PRESSURE_SUMMARY) {
    Serial.print(F("PRESSURES: "));
    for (uint8_t i=0;i<6;++i) { Serial.print(vals[i]); if (i<5) Serial.print(','); }
    Serial.println();
  }
}
