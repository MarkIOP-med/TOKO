// include/LEDS.h
#ifndef LEDS_H
#define LEDS_H

#include <Adafruit_NeoPixel.h>

struct LedColor {
    uint8_t r;
    uint8_t g;
    uint8_t b;
};

// Forward declaration
class Adafruit_NeoPixel;

void initLeds();
void handleLEDIntensity(int stripNumber, uint8_t intensity);
void setLEDStrip(int stripNumber, const LedColor* colors);
void turnOffLEDStrip(int stripNumber);

extern Adafruit_NeoPixel strip0;  // First LED strip
extern Adafruit_NeoPixel strip1;  // Second LED strip

#endif