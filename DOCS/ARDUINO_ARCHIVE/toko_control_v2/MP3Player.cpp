#include "MP3Player.h"

#if USE_MP3
#include <SoftwareSerial.h>

// SoftwareSerial serial_MP3(RX, TX)  -> per your wiring
static SoftwareSerial serial_MP3(MP3_RX_PIN, MP3_TX_PIN);

static uint8_t  mp3_cmd[6];
static uint8_t  mp3_len = 0;
static uint16_t mp3_checksum = 0;
static uint32_t mp3_lastPlayMs = 0;

/* ---------------- low-level send ---------------- */
static inline void mp3Send() {
  for (uint8_t i=0; i<mp3_len; ++i) serial_MP3.write(mp3_cmd[i]);
}

/* ---------------- protocol helpers (DY-SV5W-like) ---------------- */
static inline void cmdSetVolume(uint8_t vol) {
  if (vol > 30) vol = 30;
  mp3_cmd[0] = 0xAA; // header
  mp3_cmd[1] = 0x13; // set volume
  mp3_cmd[2] = 0x01; // data len
  mp3_cmd[3] = vol;  // 0..30
  mp3_checksum = 0;
  for (uint8_t q=0; q<4; ++q) mp3_checksum += mp3_cmd[q];
  mp3_cmd[4] = (uint8_t)(mp3_checksum & 0xFF);
  mp3_len = 5;
  mp3Send();
}

static inline void cmdPlayTrack(uint16_t track) {
  // AA 07 02 <hi> <lo> <checksum>
  mp3_cmd[0] = 0xAA;
  mp3_cmd[1] = 0x07;
  mp3_cmd[2] = 0x02;
  mp3_cmd[3] = (uint8_t)((track >> 8) & 0xFF);
  mp3_cmd[4] = (uint8_t)(track & 0xFF);
  mp3_checksum = 0;
  for (uint8_t q=0; q<5; ++q) mp3_checksum += mp3_cmd[q];
  mp3_cmd[5] = (uint8_t)(mp3_checksum & 0xFF);
  mp3_len = 6;
  mp3Send();
}

static inline void cmdPlayResume() {
  // AA 02 00 AC
  mp3_cmd[0] = 0xAA;
  mp3_cmd[1] = 0x02;
  mp3_cmd[2] = 0x00;
  mp3_cmd[3] = 0xAC;
  mp3_len = 4;
  mp3Send();
}

/* ---------------- public API ---------------- */
namespace MP3Player {

  void begin() {
    pinMode(MP3_BUSY_PIN, INPUT);     // if BUSY floats, change to INPUT_PULLUP
    serial_MP3.begin(MP3_BAUD);

    // *** settle time before first command (as requested) ***
    delay(300);                       // let module boot and mount SD

    // set volume, then a short gap before play
    cmdSetVolume(MP3_VOLUME);
    delay(20);

    if (TRACK_STARTUP > 0) {
      cmdPlayTrack(TRACK_STARTUP);    // play startup once
      mp3_lastPlayMs = millis();
    }
  }

  void setVolume(uint8_t vol) {
    cmdSetVolume(vol);
  }

  void playTrack(uint16_t id) {
    cmdPlayTrack(id);
    mp3_lastPlayMs = millis();
  }

  void playForLevel(uint8_t level) {
    if (level > 3) return;
    uint16_t track = TRACK_BY_LEVEL[level];
    if (track == 0) return;
    uint32_t now = millis();
    if (now - mp3_lastPlayMs < MP3_COOLDOWN_MS) return; // small cooldown
    cmdPlayTrack(track);
    mp3_lastPlayMs = now;
  }

  bool isIdle() {
    // DY-SV5W modules typically drive BUSY: HIGH=idle, LOW=playing
    return digitalRead(MP3_BUSY_PIN) == HIGH;
  }

} // namespace MP3Player

#else  // USE_MP3 == 0

namespace MP3Player {
  void begin() {}
  void setVolume(uint8_t) {}
  void playTrack(uint16_t) {}
  void playForLevel(uint8_t) {}
  bool isIdle() { return true; }
}

#endif
