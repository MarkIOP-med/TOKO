#pragma once
#include <Arduino.h>
class Adafruit_NeoPixel;

namespace LedEngine {
  void init(Adafruit_NeoPixel* strip);
  void startStatic(uint8_t pad, uint8_t level);                      // preempts
  void startDynamic(uint8_t pad, uint8_t effectId, uint8_t speed);   // preempts
  void serviceFrame();   // update all pads (non-blocking)
  void flushIfDue();     // rate-limited strip.show()
}
