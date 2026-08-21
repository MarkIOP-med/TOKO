#pragma once
#include <Arduino.h>
#include "ControlConfig.h"

namespace ControlComms {
  // Ask the module for the 6 pressure values (touchset)
  void sendP(HardwareSerial* s);

  // Read up to 6 numbers (one per line) within timeouts. Returns true if all 6 arrived.
  bool readTouchset(HardwareSerial* s, int out6[6]);

  // LED & VIB commands in the exact format the module expects
  void sendLED(HardwareSerial* s, uint8_t pad, uint8_t level, char mode, uint8_t effect = 1);
  void sendVIB(HardwareSerial* s, uint8_t pad, uint8_t level, char mode /*'s'*/, uint8_t pattern /*1*/);
}
