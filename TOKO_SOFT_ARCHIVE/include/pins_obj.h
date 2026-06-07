// include/pins_obj.h
#ifndef PINS_OBJ_H
#define PINS_OBJ_H

// MP3 player busy pin
#define busyPin 3

// ADC (MCP3008) pins
#define MCP_CLK A2
#define MCP_MOSI A1
#define MCP_MISO A0
#define MCP_CS_0 A3
#define MCP_CS_1 A4

// Vibration motor pins (6 total, 3 for each set)
#define vib0 4
#define vib1 5
#define vib2 9
#define vib3 10
#define vib4 11
#define vib5 12

// LED strip pins
#define led_arr_0 7    // First LED strip
#define led_arr_1 8    // Second LED strip

// Create arrays for easier access in code
const uint8_t vib_arr[] = {vib0, vib1, vib2, vib3, vib4, vib5};

#endif