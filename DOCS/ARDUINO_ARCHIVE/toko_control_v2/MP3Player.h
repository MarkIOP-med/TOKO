#pragma once
#include <Arduino.h>
#include "ControlConfig.h"

namespace MP3Player {
  void begin();                 // init SW serial, delays, volume, play startup once
  void setVolume(uint8_t vol);  // 0..30
  void playTrack(uint16_t id);  // play specific track
  void playForLevel(uint8_t level); // L1->track2, L2->3, L3->4 (cooldowned)
  bool isIdle();                // true when busy pin indicates idle
}
