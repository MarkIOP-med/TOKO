/*
  toko_module_v2.ino  — MODULE SIDE ONLY
  -------------------------------------------------
  Commands (send on USB Serial or mySerial):

    p
      -> replies with 6 baseline-normalized pressures (one per line) on mySerial
         (USB shows: PRESSURES: v1,v2,...,v6)
         NOTE: 'p' works immediately, with or without newline.

    l <pad> <level> <mode> [<effect>]
      OR: l,<pad>,<level>,<mode>,<effect>
      pad    : 0..2  (today)
      level  : 0..3  (0=off, 3=strong)
      mode   : s | d (static | dynamic)
      effect : 1=BREATH, 2=TWINKLE, 3=WAVE   (used only when mode=d)
      behavior: runs 5s, auto-off; new l ... preempts same-pad LEDs immediately

    v <pad> <level> <mode> <pattern>
      OR: v,<pad>,<level>,<mode>,<pattern>
      pad     : 0..2
      level   : 0..3 (reserved for future intensity mapping)
      mode    : s | d (accepted; patterns define motion)
      pattern : 1=PULSE, 2=RAMP, 3=BURSTS
      behavior: runs 5s; new v ... preempts same-pad vibration immediately

    R CALIB      (also accepts: R,CALIB)
      -> re-calibrate pressure baselines

  Policy:
    - All protocol output (the 6 numbers for 'p') goes ONLY to mySerial.
    - USB is for input & debug; we print summaries but not protocol payloads.
    - Everything is non-blocking (millis timers). Parsing uses short timeouts.
*/

#include <Arduino.h>
#include <SoftwareSerial.h>
#include <Adafruit_NeoPixel.h>

#include "Config.h"
#include "Pressure.h"
#include "LedEngine.h"
#include "VibEngine.h"

// Hardware owned here
SoftwareSerial busPort(BUS_RX_PIN, BUS_TX_PIN);
Adafruit_NeoPixel strip(NUM_LEDS, LED_PIN, NEO_GRB + NEO_KHZ800);

/* ------------ tiny token parser helpers (space/comma delims) ------------ */
static inline bool isDelim(int c) {
  return c==' ' || c=='\t' || c=='\r' || c=='\n' || c==',';  // allow spaces OR commas
}
static void skipDelims(Stream& s) {
  while (s.available()) {
    int c = s.peek();
    if (!isDelim(c)) break;
    s.read();
  }
}
/* Read an integer token; returns true on success. Uses a short non-blocking timeout. */
static bool readIntToken(Stream& s, int &out, uint16_t timeoutMs=30) {
  uint32_t t0 = millis();
  skipDelims(s);
  bool seenDigit = false;
  long value = 0;
  while (millis() - t0 < timeoutMs) {
    if (!s.available()) { yield(); continue; }
    int c = s.peek();
    if (isDelim(c)) {
      if (seenDigit) { s.read(); break; } // consume one delim and finish
      s.read();                            // still skipping leading delims
      continue;
    }
    if (c >= '0' && c <= '9') {
      seenDigit = true;
      value = value * 10 + (c - '0');
      s.read();
      continue;
    }
    // unexpected char -> fail (let caller discard the rest of the line)
    return false;
  }
  if (!seenDigit) return false;
  out = (int)value;
  return true;
}
/* Read a single non-delim char token (e.g., 's'/'d'). */
static bool readModeToken(Stream& s, char &out, uint16_t timeoutMs=30) {
  uint32_t t0 = millis();
  skipDelims(s);
  while (millis() - t0 < timeoutMs) {
    if (!s.available()) { yield(); continue; }
    int c = s.peek();
    if (isDelim(c)) { s.read(); continue; }
    out = (char)c;
    s.read();
    return true;
  }
  return false;
}
/* Discard until end-of-line to recover from a bad/partial command. */
static void discardLine(Stream& s) {
  while (s.available()) {
    int c = s.read();
    if (c == '\n') break;
  }
}

/* ------------ immediate 'p' handler (works with or without newline) ------------ */
static bool handleImmediateP(Stream& s) {
  if (!s.available()) return false;
  int c = s.peek();
  if (c == 'p' || c == 'P') {
    s.read();                       // consume 'p'
    // consume optional CR/LF so buffer stays clean
    if (s.peek() == '\r') s.read();
    if (s.peek() == '\n') s.read();
    Pressure::sendAllToControl(busPort); // send readings to Control (mySerial)
    return true;
  }
  return false;
}

/* ------------ simple command reader: leading letter then fixed tokens ------------ */
static void handleStream(Stream& s) {
  if (!s.available()) return;

  // First: fast path for bare 'p'
  if (handleImmediateP(s)) return;

  // Otherwise look for 'l', 'v' or 'R'
  int cmd = s.peek();
  if (cmd == 'l' || cmd == 'L') {
    s.read(); // consume 'l'
    int pad, level, effect=1; char mode='s';

    if (!readIntToken(s, pad))         { discardLine(s); return; }
    if (!readIntToken(s, level))       { discardLine(s); return; }
    if (!readModeToken(s, mode))       { discardLine(s); return; }

    if (mode=='d' || mode=='D') {
      if (!readIntToken(s, effect)) { effect = 1; } // default to BREATH if omitted
      if (pad<0 || pad>=PADS || level<0 || level>3) { discardLine(s); return; }
      if (effect < 1 || effect > 3) effect = 1;
      LedEngine::startDynamic((uint8_t)pad, (uint8_t)effect, /*speed*/5);
    } else {
      if (pad<0 || pad>=PADS || level<0 || level>3) { discardLine(s); return; }
      LedEngine::startStatic((uint8_t)pad, (uint8_t)level);
    }
    // consume rest of line noise if any
    discardLine(s);
    return;
  }
  else if (cmd == 'v' || cmd == 'V') {
    s.read(); // consume 'v'
    int pad, level, pattern=1; char mode='s';

    if (!readIntToken(s, pad))         { discardLine(s); return; }
    if (!readIntToken(s, level))       { discardLine(s); return; }
    if (!readModeToken(s, mode))       { discardLine(s); return; }
    if (!readIntToken(s, pattern))     { discardLine(s); return; }

    if (pad<0 || pad>=PADS) { discardLine(s); return; }
    if (pattern < 1 || pattern > 3) pattern = 1;
    // preemption handled inside engine by start()
    VibEngine::start((uint8_t)pad, (uint8_t)pattern);
    discardLine(s);
    return;
  }
  else if (cmd == 'R') {
    // Accept "R CALIB" or "R,CALIB"
    s.read(); // consume 'R'
    // eat delimiters
    skipDelims(s);
    // read next word; we tolerate missing word too (just calibrate)
    // If present and equals "CALIB" (case-insensitive), we'll calibrate; else calibrate anyway.
    // For simplicity, just calibrate:
    Pressure::calibrateBaselines();
    discardLine(s);
    return;
  }

  // Unknown leading char → consume one and continue (don’t get stuck)
  s.read();
}

void setup() {
  Serial.begin(USB_BAUD);
  busPort.begin(BUS_BAUD);
  busPort.listen();

  strip.begin();
  strip.show();

  Pressure::calibrateBaselines();
  LedEngine::init(&strip);
  VibEngine::init();

  // Start pads OFF (static)
  for (uint8_t p=0; p<PADS; ++p) LedEngine::startStatic(p, 0);

  Serial.println(F("[Init] Module ready. Commands:"));
  Serial.println(F("  p"));
  Serial.println(F("  l <pad> <level> <s|d> [<effect 1|2|3>]"));
  Serial.println(F("  v <pad> <level> <s|d> <pattern 1|2|3>"));
  Serial.println(F("  R CALIB"));
}

void loop() {
  // Ensure SoftwareSerial is the active listener when we poll it
  busPort.listen();

  // Handle commands from USB and bus (both supported)
  handleStream(Serial);
  handleStream(busPort);

  // Service non-blocking engines
  LedEngine::serviceFrame();
  LedEngine::flushIfDue();
  VibEngine::serviceFrame();
}
