#pragma once
#include <Arduino.h>

namespace VibEngine {
  void init();
  void start(uint8_t pad, uint8_t pattern); // 1=PULSE, 2=RAMP, 3=BURSTS (preempts)
  void stop(uint8_t pad);
  void serviceFrame(); // non-blocking, per-pad
}
