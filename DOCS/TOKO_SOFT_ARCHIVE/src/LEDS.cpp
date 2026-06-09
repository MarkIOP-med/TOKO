// src/LEDS.cpp
#include <Arduino.h>
#include <Adafruit_NeoPixel.h>
#include "pins_obj.h"
#include "globals.h"
#include "LEDS.h"

Adafruit_NeoPixel strip0 = Adafruit_NeoPixel(NUM_LEDS, led_arr_0, NEO_GRB + NEO_KHZ800);
Adafruit_NeoPixel strip1 = Adafruit_NeoPixel(NUM_LEDS, led_arr_1, NEO_GRB + NEO_KHZ800);

const LedColor LED_COLORS_HARD[NUM_LEDS] = {
    {255, 0, 0},    // Bright Red
    {0, 255, 0},    // Bright Green
    {0, 0, 255},    // Bright Blue
    {255, 255, 0},  // Bright Yellow
    {0, 255, 255},  // Bright Cyan
    {255, 0, 255},  // Bright Magenta
    {255, 128, 0},  // Bright Orange
    {255, 0, 128},  // Bright Pink
    {128, 0, 255}   // Bright Purple
};

const LedColor LED_COLORS_MEDIUM[NUM_LEDS] = {
    {128, 0, 0},    // Medium Red
    {0, 128, 0},    // Medium Green
    {0, 0, 128},    // Medium Blue
    {128, 128, 0},  // Medium Yellow
    {0, 128, 128},  // Medium Cyan
    {128, 0, 128},  // Medium Magenta
    {128, 64, 0},   // Medium Orange
    {128, 0, 64},   // Medium Pink
    {64, 0, 128}    // Medium Purple
};

const LedColor LED_COLORS_LIGHT[NUM_LEDS] = {
    {64, 0, 0},     // Soft Red
    {0, 64, 0},     // Soft Green
    {0, 0, 64},     // Soft Blue
    {64, 64, 0},    // Soft Yellow
    {0, 64, 64},    // Soft Cyan
    {64, 0, 64},    // Soft Magenta
    {64, 32, 0},    // Soft Orange
    {64, 0, 32},    // Soft Pink
    {32, 0, 64}     // Soft Purple
};

void initLeds() {
    strip0.begin();
    strip1.begin();
    strip0.show();
    strip1.show();
}

void setLEDStrip(int stripNumber, const LedColor* colors) {
    Adafruit_NeoPixel& strip = (stripNumber == 0) ? strip0 : strip1;
    
    for(int i = 0; i < NUM_LEDS; i++) {
        strip.setPixelColor(i, strip.Color(colors[i].r, colors[i].g, colors[i].b));
    }
    strip.show();
}

void turnOffLEDStrip(int stripNumber) {
    Adafruit_NeoPixel& strip = (stripNumber == 0) ? strip0 : strip1;
    strip.clear();
    strip.show();
}

void handleLEDIntensity(int stripNumber, uint8_t intensity) {
    switch (intensity) {
        case PRESS_HARD:
            setLEDStrip(stripNumber, LED_COLORS_HARD);
            break;
        case PRESS_MEDIUM:
            setLEDStrip(stripNumber, LED_COLORS_MEDIUM);
            break;
        case PRESS_LIGHT:
            setLEDStrip(stripNumber, LED_COLORS_LIGHT);
            break;
        default:
            turnOffLEDStrip(stripNumber);
    }
}