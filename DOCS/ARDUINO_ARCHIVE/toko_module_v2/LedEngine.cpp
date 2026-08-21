#include "LedEngine.h"
#include <Adafruit_NeoPixel.h>
#include "Config.h"

enum PadLedMode : uint8_t { LED_STATIC_MODE=0, LED_ANIM_MODE=1 };

static Adafruit_NeoPixel* g_strip = nullptr;

static PadLedMode padMode[PADS]         = {LED_STATIC_MODE,LED_STATIC_MODE,LED_STATIC_MODE};
static uint8_t    padLevel[PADS]        = {0,0,0};
static uint8_t    padEffect[PADS]       = {0,0,0};    // 1..3 if dynamic
static uint32_t   padDeadlineMs[PADS]   = {0,0,0};

// per pad, per LED base color (for dynamic)
static RGB        padBaseColor[PADS][2];
static uint32_t   padEffectStartMs[PADS] = {0,0,0};
static uint16_t   padEffectPeriodMs[PADS]= {0,0,0};
static uint8_t    padMinB[PADS]          = {LED_DYN_MIN_BRIGHTNESS,LED_DYN_MIN_BRIGHTNESS,LED_DYN_MIN_BRIGHTNESS};
static uint8_t    padMaxB[PADS]          = {LED_DYN_MAX_BRIGHTNESS,LED_DYN_MAX_BRIGHTNESS,LED_DYN_MAX_BRIGHTNESS};

// TWINKLE internals
static bool       twActive[PADS] = {false,false,false};
static uint8_t    twLed[PADS]    = {0,0,0};
static uint32_t   twEndMs[PADS]  = {0,0,0};
static uint32_t   twNextMs[PADS] = {0,0,0};

static bool       pixelsDirty = false;
static uint32_t   lastShowMs  = 0;

/* ---- local helpers ---- */
static inline uint8_t clampU8(int v){ if(v<0)return 0; if(v>255)return 255; return (uint8_t)v; }
static inline uint8_t tri8(uint32_t t, uint16_t period, uint8_t lo, uint8_t hi) {
  if (period < 2) return hi;
  uint16_t half = period/2;
  uint16_t x = t % period;
  int span = hi - lo;
  if (x < half) {
    int v = lo + ( (int32_t)span * x * 2 ) / period;
    return clampU8(v);
  } else {
    int v = lo + ( (int32_t)span * (period - x) * 2 ) / period;
    return clampU8(v);
  }
}
static inline void setPadRGB(uint8_t pad, const RGB& c0, const RGB& c1) {
  g_strip->setPixelColor(PAD_LED0[pad], g_strip->Color(c0.r,c0.g,c0.b));
  g_strip->setPixelColor(PAD_LED1[pad], g_strip->Color(c1.r,c1.g,c1.b));
  pixelsDirty = true;
}
static inline void setPadBothFromRow(uint8_t pad, uint8_t row) {
  const RGB& c = PALETTE[row];
  setPadRGB(pad, c, c);
}
static inline uint16_t speedToPeriodMs(uint8_t speed) {
  speed = (speed<1)?1:((speed>10)?10:speed);
  return (uint16_t)( 2500 - ( (speed-1) * (2200/9) ) ); // 1..10 -> 2500..300ms
}
static inline void pickDynamicBaseColors(uint8_t pad, uint8_t effectId) {
  uint8_t rA = LED_DYN_ALLOWED_ROWS[random((int)LED_DYN_ALLOWED_ROWS_LEN)];
  uint8_t rB = LED_DYN_ALLOWED_ROWS[random((int)LED_DYN_ALLOWED_ROWS_LEN)];
  const RGB& cA = PALETTE[rA];
  const RGB& cB = PALETTE[rB];
  if (effectId == 3) { // WAVE: two colors
    padBaseColor[pad][0] = cA;
    padBaseColor[pad][1] = cB;
  } else {              // BREATH/TWINKLE: same base
    padBaseColor[pad][0] = cA;
    padBaseColor[pad][1] = cA;
  }
}

void LedEngine::init(Adafruit_NeoPixel* strip) {
  g_strip = strip;
}

void LedEngine::startStatic(uint8_t pad, uint8_t level) {
  if (pad >= PADS) return;
  padMode[pad]       = LED_STATIC_MODE;
  padLevel[pad]      = level;
  padEffect[pad]     = 0;
  padDeadlineMs[pad] = millis() + LED_HOLD_MS;
  setPadBothFromRow(pad, LEVEL_TO_ROW_MAP[level]);
}

void LedEngine::startDynamic(uint8_t pad, uint8_t effectId, uint8_t speed) {
  if (pad >= PADS) return;
  padMode[pad]       = LED_ANIM_MODE;
  padEffect[pad]     = effectId;
  padDeadlineMs[pad] = millis() + LED_HOLD_MS;

  pickDynamicBaseColors(pad, effectId);
  padMinB[pad]          = LED_DYN_MIN_BRIGHTNESS;
  padMaxB[pad]          = LED_DYN_MAX_BRIGHTNESS;
  padEffectStartMs[pad] = millis();
  padEffectPeriodMs[pad]= speedToPeriodMs(speed);

  // TWINKLE init
  twActive[pad] = false;
  twNextMs[pad] = millis() + (uint32_t)random(150, 600);
  twEndMs[pad]  = 0;
  twLed[pad]    = random(0,2);
}

void LedEngine::serviceFrame() {
  uint32_t now = millis();

  for (uint8_t pad = 0; pad < PADS; ++pad) {
    // Auto-reset after hold
    if (now >= padDeadlineMs[pad]) {
      padMode[pad]  = LED_STATIC_MODE;
      padLevel[pad] = 0;
      setPadBothFromRow(pad, LED_RESET_ROW);
      continue;
    }
    if (padMode[pad] == LED_STATIC_MODE) continue;

    // Dynamic
    uint16_t period = padEffectPeriodMs[pad];
    uint8_t lo = padMinB[pad], hi = padMaxB[pad];

    if (padEffect[pad] == 1) { // BREATH
      uint8_t b = tri8(now - padEffectStartMs[pad], period, lo, hi);
      RGB c0 = { (uint8_t)(((uint16_t)padBaseColor[pad][0].r * b) >> 8),
                 (uint8_t)(((uint16_t)padBaseColor[pad][0].g * b) >> 8),
                 (uint8_t)(((uint16_t)padBaseColor[pad][0].b * b) >> 8) };
      RGB c1 = { (uint8_t)(((uint16_t)padBaseColor[pad][1].r * b) >> 8),
                 (uint8_t)(((uint16_t)padBaseColor[pad][1].g * b) >> 8),
                 (uint8_t)(((uint16_t)padBaseColor[pad][1].b * b) >> 8) };
      setPadRGB(pad, c0, c1);
    }
    else if (padEffect[pad] == 3) { // WAVE
      uint8_t b0 = tri8(now - padEffectStartMs[pad],            period, lo, hi);
      uint8_t b1 = tri8(now - padEffectStartMs[pad] + period/2, period, lo, hi);
      RGB c0 = { (uint8_t)(((uint16_t)padBaseColor[pad][0].r * b0) >> 8),
                 (uint8_t)(((uint16_t)padBaseColor[pad][0].g * b0) >> 8),
                 (uint8_t)(((uint16_t)padBaseColor[pad][0].b * b0) >> 8) };
      RGB c1 = { (uint8_t)(((uint16_t)padBaseColor[pad][1].r * b1) >> 8),
                 (uint8_t)(((uint16_t)padBaseColor[pad][1].g * b1) >> 8),
                 (uint8_t)(((uint16_t)padBaseColor[pad][1].b * b1) >> 8) };
      setPadRGB(pad, c0, c1);
    }
    else { // TWINKLE (2)
      uint8_t bbg = lo;
      RGB c0 = { (uint8_t)(((uint16_t)padBaseColor[pad][0].r * bbg) >> 8),
                 (uint8_t)(((uint16_t)padBaseColor[pad][0].g * bbg) >> 8),
                 (uint8_t)(((uint16_t)padBaseColor[pad][0].b * bbg) >> 8) };
      RGB c1 = { (uint8_t)(((uint16_t)padBaseColor[pad][1].r * bbg) >> 8),
                 (uint8_t)(((uint16_t)padBaseColor[pad][1].g * bbg) >> 8),
                 (uint8_t)(((uint16_t)padBaseColor[pad][1].b * bbg) >> 8) };

      if (!twActive[pad] && now >= twNextMs[pad]) {
        twActive[pad] = true;
        twLed[pad]    = random(0,2);
        twEndMs[pad]  = now + (uint32_t)random(120, 260);            // sparkle length
        twNextMs[pad] = twEndMs[pad] + (uint32_t)random(200, 600);   // next gap
      }
      if (twActive[pad]) {
        if (now >= twEndMs[pad]) {
          twActive[pad] = false;
        } else {
          uint8_t bh = hi;
          if (twLed[pad]==0) c0 = { (uint8_t)(((uint16_t)padBaseColor[pad][0].r * bh) >> 8),
                                    (uint8_t)(((uint16_t)padBaseColor[pad][0].g * bh) >> 8),
                                    (uint8_t)(((uint16_t)padBaseColor[pad][0].b * bh) >> 8) };
          else               c1 = { (uint8_t)(((uint16_t)padBaseColor[pad][1].r * bh) >> 8),
                                    (uint8_t)(((uint16_t)padBaseColor[pad][1].g * bh) >> 8),
                                    (uint8_t)(((uint16_t)padBaseColor[pad][1].b * bh) >> 8) };
        }
      }
      setPadRGB(pad, c0, c1);
    }
  }
}

void LedEngine::flushIfDue() {
  uint32_t now = millis();
  if (pixelsDirty && (now - lastShowMs) >= LED_FRAME_MIN_INTERVAL_MS) {
    g_strip->show();
    lastShowMs = now;
    pixelsDirty = false;
  }
}
