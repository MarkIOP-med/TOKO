// src/Vibrations.cpp
#include <Arduino.h>
#include "pins_obj.h"
#include "globals.h"
#include "Vibrations.h"

void initVibrations() {
    pinMode(vib0, OUTPUT);
    pinMode(vib1, OUTPUT);
    pinMode(vib2, OUTPUT);
    pinMode(vib3, OUTPUT);
    pinMode(vib4, OUTPUT);
    pinMode(vib5, OUTPUT);
    
    // Initialize all vibrators to OFF
    for(int i = 0; i < 6; i++) {
        digitalWrite(vib_arr[i], LOW);
    }
}

void activateVibrators(int setNumber, int numVibrators) {
    int startIndex = setNumber * NUM_VIBRATORS_PER_SET;
    
    // First deactivate all vibrators in this set
    for(int i = 0; i < NUM_VIBRATORS_PER_SET; i++) {
        digitalWrite(vib_arr[startIndex + i], LOW);
    }
    
    // Activate the requested number of vibrators
    for(int i = 0; i < numVibrators; i++) {
        digitalWrite(vib_arr[startIndex + i], HIGH);
    }
    
    delay(VIBRATION_DURATION);
    
    // Deactivate all after duration
    for(int i = 0; i < NUM_VIBRATORS_PER_SET; i++) {
        digitalWrite(vib_arr[startIndex + i], LOW);
    }
}

// src/Vibrations.cpp
void deactivateVibrators(int setNumber) {
    int startIndex = setNumber * NUM_VIBRATORS_PER_SET;
    for(int i = 0; i < NUM_VIBRATORS_PER_SET; i++) {
        digitalWrite(vib_arr[startIndex + i], LOW);
    }
}

void handleVibrations(int setNumber, uint8_t intensity) {
    switch (intensity) {
        case PRESS_HARD:
            activateVibrators(setNumber, 3);  // All three vibrators
            break;
        case PRESS_MEDIUM:
            activateVibrators(setNumber, 2);  // Two vibrators
            break;
        case PRESS_LIGHT:
            activateVibrators(setNumber, 1);  // One vibrator
            break;
        default:
            deactivateVibrators(setNumber);
    }
}