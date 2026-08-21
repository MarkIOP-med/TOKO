#include "ControlComms.h"

namespace ControlComms {

  void sendP(HardwareSerial* s) {
    if (!s) return;
    while (s->available()) (void)s->read(); // flush stale
    s->print("p\n");
  }

  bool readTouchset(HardwareSerial* s, int out6[6]) {
    if (!s) return false;

    uint32_t tDeadline = millis() + READ_TIMEOUT_MS;
    uint32_t lastLine = millis();
    int count = 0;
    String line;

    while ((int32_t)(millis() - tDeadline) < 0) {
      while (s->available()) {
        char c = (char)s->read();
        if (c == '\r') continue;
        if (c == '\n') {
          line.trim();
          if (line.length() > 0) {
            long v = line.toInt();
            if (DEBUG_PRINT_PER_VALUE) { Serial.print("[RX] "); Serial.println(v); } // now gated OFF by default
            out6[count++] = (int)v;
            line = "";
            lastLine = millis();
            if (count == 6) return true;
          } else {
            lastLine = millis(); // empty line; ignore
          }
        } else {
          line += c;
        }
      }
      // inter-line gap timeout
      if (count > 0 && (millis() - lastLine) > INTER_LINE_TIMEOUT_MS) break;
      yield();
    }
    return false;
  }

  void sendLED(HardwareSerial* s, uint8_t pad, uint8_t level, char mode, uint8_t effect) {
    if (!s) return;
    s->print("l "); s->print(pad); s->print(' '); s->print(level); s->print(' '); s->print(mode);
    if (mode=='d' || mode=='D') { s->print(' '); s->print(effect); }
    s->print('\n');
    if (DEBUG_PRINT_ACTIONS) {
      Serial.print("[LED] l "); Serial.print(pad); Serial.print(' '); Serial.print(level); Serial.print(' '); Serial.print(mode);
      if (mode=='d' || mode=='D') { Serial.print(' '); Serial.print(effect); }
      Serial.println();
    }
  }

  void sendVIB(HardwareSerial* s, uint8_t pad, uint8_t level, char mode, uint8_t pattern) {
    if (!s) return;
    s->print("v "); s->print(pad); s->print(' '); s->print(level); s->print(' '); s->print(mode); s->print(' '); s->print(pattern);
    s->print('\n');
    if (DEBUG_PRINT_ACTIONS) {
      Serial.print("[VIB] v "); Serial.print(pad); Serial.print(' '); Serial.print(level); Serial.print(' '); Serial.print(mode); Serial.print(' '); Serial.println(pattern);
    }
  }

} // namespace
