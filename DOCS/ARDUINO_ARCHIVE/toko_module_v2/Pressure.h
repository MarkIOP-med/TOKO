#pragma once
#include <Arduino.h>

namespace Pressure {
  void calibrateBaselines();
  int  readNormalized(uint8_t ch);
  void sendAllToControl(Stream& out);   // MUST: for 'p' — emits 6 lines to Control; USB prints summary
}
