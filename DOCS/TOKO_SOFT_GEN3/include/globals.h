#ifndef GLOBALS_H
#define GLOBALS_H

#include <Arduino.h>
#include <Adafruit_MCP3008.h>

// LED and sensor counts
#define NUM_LEDS 9
#define NUM_PRESSURE_SENSORS 12
#define NUM_PRESSURE_SENSORS_PER_SET 6
#define NUM_VIBRATORS_PER_SET 3

// Timing constants
#define MUSIC_WAIT_TIME 5000  // 5 seconds wait when music is playing
#define DEBOUNCE_TIME 300     // Milliseconds between readings
#define VIBRATION_DURATION 2000  // Vibration duration in milliseconds

// ADC resolution for MCP3008
#define ADC_MAX_VALUE 1023    // MCP3008 is 10-bit ADC

// Pressure thresholds (adjusted for 10-bit ADC)
#define PRESSURE_THRESHOLD_LIGHT 800     // light touch
#define PRESSURE_THRESHOLD_MEDIUM 1000    // Medium press
#define PRESSURE_THRESHOLD_HARD 1100      // hard press

// Pressure intensity levels
#define PRESS_NONE 0
#define PRESS_LIGHT 1
#define PRESS_MEDIUM 2
#define PRESS_HARD 3

// Track numbers for MP3 player
#define TRACK_WELCOME 1    // Welcome message
#define TRACK_FANTASTIC 2  // For hard press
#define TRACK_PERFECT 3    // For medium press
#define TRACK_GOOD 4       // For light press
#define TRACK_BOTH_SETS 5  // When both sets > medium

// Global variables defined in main.cpp
extern uint16_t pressData[12];
extern uint16_t baselineData[12];
extern uint8_t ledColors[7][27];
extern int trackNum;

// Global ADC objects
extern Adafruit_MCP3008 adc0;
extern Adafruit_MCP3008 adc1;

#endif
