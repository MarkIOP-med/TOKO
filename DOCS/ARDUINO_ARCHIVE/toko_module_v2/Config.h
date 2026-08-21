#pragma once
#include <Arduino.h>

/* ---------- Serial ---------- */
static const uint32_t USB_BAUD = 115200;
static const uint32_t BUS_BAUD = 4800;
static const uint8_t  BUS_RX_PIN = 10;  // mySerial RX
static const uint8_t  BUS_TX_PIN = 11;  // mySerial TX

/* ---------- Pressure sensors ---------- */
static const uint8_t  SENSOR_PINS[6]   = {A0, A1, A2, A3, A6, A7};
static const uint8_t  CALIB_SAMPLES    = 10;   // baseline averaging at startup / R,CALIB
static const uint8_t  SENSOR_SCALE_DIV = 4;    // 1023/4 ≈ 0..255
static const bool     CLAMP_TO_ZERO    = true; // clamp (raw-baseline) <0 to 0

/* ---------- Module topology ---------- */
static const uint8_t  PADS         = 3;
static const uint8_t  LEDS_PER_PAD = 2;

/* ---------- NeoPixel ---------- */
static const uint8_t  LED_PIN  = 9;
static const uint8_t  NUM_LEDS = 6;

/* ---------- Pad -> LED index mapping ---------- */
static const uint8_t  PAD_LED0[PADS] = {0, 2, 4};
static const uint8_t  PAD_LED1[PADS] = {1, 3, 5};

/* ---------- LEDs behavior ---------- */
static const uint16_t LED_HOLD_MS               = 5000; // per-pad duration (static & dynamic)
static const uint8_t  LED_RESET_ROW             = 0;    // row to use after hold (off)
static const uint8_t  LED_DYN_MIN_BRIGHTNESS    = 10;   // 0..255
static const uint8_t  LED_DYN_MAX_BRIGHTNESS    = 45;   // 0..255
static const uint16_t LED_FRAME_MIN_INTERVAL_MS = 20;   // cap strip.show() (~50FPS)

/* ---------- Palette & level mapping ---------- */
struct RGB { uint8_t r,g,b; };
static const RGB PALETTE[5] = {
  {  0,  0,  0}, // 0 Off
  {  0, 60,  0}, // 1 Soft Green
  { 80, 80,  0}, // 2 Soft Yellow
  {160, 70,  0}, // 3 Orange
  {200,  0,  0}  // 4 Red
};
static const uint8_t LEVEL_TO_ROW_MAP[4]    = {0, 1, 3, 4}; // L0->Off, L1->Green, L2->Orange, L3->Red
static const uint8_t LED_DYN_ALLOWED_ROWS[] = {1, 2};
static const size_t  LED_DYN_ALLOWED_ROWS_LEN = sizeof(LED_DYN_ALLOWED_ROWS) / sizeof(LED_DYN_ALLOWED_ROWS[0]);

/* ---------- Vibration ---------- */
static const uint8_t  VIB_PINS[PADS] = {3, 5, 6};
static const uint16_t VIB_PULSE_MS   = 5000; // per-pad duration
static const uint8_t  VIB_MAX_INTENSITY = 255;

/* ---------- Debug ---------- */
static const bool DEBUG_MIRROR_TX_PRESSURE = true; // mirror 'p' numbers to USB
static const bool DEBUG_PRESSURE_SUMMARY   = true; // one-line "PRESSURES: ..." on USB
