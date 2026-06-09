// src/main.cpp
#include <Arduino.h>
#include "globals.h"
#include "pins_obj.h"
#include "LEDS.h"
#include "pressSensors.h"
#include "Vibrations.h"
#include "MP3.h"

// Define global variables
uint16_t pressData[NUM_PRESSURE_SENSORS] = {0};
uint16_t baselineData[NUM_PRESSURE_SENSORS] = {0};
uint8_t ledColors[7][27] = {0};
int trackNum = 0;

// Define global ADC objects
Adafruit_MCP3008 adc0;
Adafruit_MCP3008 adc1;

void setup() {
    Serial.begin(9600);
    delay(200);
    
    // Initialize all components
    initADC();
    initVibrations();
    initLeds();
    initMP3();
    
    Serial.println("Calibrating sensors... Please don't touch the sensors.");
    delay(1000);
    
    // Calibrate pressure sensors
    readPressSensors(pressData);
    
    Serial.println("Baseline values:");
    Serial.print("Set 1: ");
    for(int i = 0; i < NUM_PRESSURE_SENSORS_PER_SET; i++) {
        baselineData[i] = pressData[i];
        Serial.print(baselineData[i]);
        Serial.print(" ");
    }
    Serial.print("\nSet 2: ");
    for(int i = NUM_PRESSURE_SENSORS_PER_SET; i < NUM_PRESSURE_SENSORS; i++) {
        baselineData[i] = pressData[i];
        Serial.print(baselineData[i]);
        Serial.print(" ");
    }
    Serial.println("\nCalibration complete!");
    
    Serial.println("Playing welcome track...");
    playTrack(TRACK_WELCOME);
    delay(1000);

    if (MP3Busy()) {
        Serial.println("MP3 is playing, waiting...");
        delay(MUSIC_WAIT_TIME);
        return;
    }
}

uint8_t getPressureSetIntensity(const uint16_t* pressures, int setSize) {
    int maxPressure = 0;
    for(int i = 0; i < setSize; i++) {
        int pressure = pressures[i] - baselineData[i];
        if(pressure > maxPressure) maxPressure = pressure;
    }
    
    if(maxPressure > PRESSURE_THRESHOLD_HARD) return PRESS_HARD;
    if(maxPressure > PRESSURE_THRESHOLD_MEDIUM) return PRESS_MEDIUM;
    if(maxPressure > PRESSURE_THRESHOLD_LIGHT) return PRESS_LIGHT;
    return PRESS_NONE;
}

void loop() {

    
    // Read and print pressure sensors
    readPressSensors(pressData);
    printPressSensors(pressData);
    
    // Get intensity for each set
    uint8_t set1Intensity = getPressureSetIntensity(pressData, NUM_PRESSURE_SENSORS_PER_SET);
    uint8_t set2Intensity = getPressureSetIntensity(pressData + NUM_PRESSURE_SENSORS_PER_SET, 
                                                   NUM_PRESSURE_SENSORS_PER_SET);
    
    //Serial.print("Set 1 Intensity: ");
    //Serial.println(set1Intensity);
    //Serial.print("Set 2 Intensity: ");
    //Serial.println(set2Intensity);
    
    // Handle LED feedback
    //Serial.println("Updating LEDs...");
    handleLEDIntensity(0, set1Intensity);
    handleLEDIntensity(1, set2Intensity);
    
    // Handle vibration feedback
    //Serial.println("Activating vibrations...");
    handleVibrations(0, set1Intensity);
    handleVibrations(1, set2Intensity);
    
    // Handle audio feedback
    if (set1Intensity >= PRESS_MEDIUM && set2Intensity >= PRESS_MEDIUM) {
        //Serial.println("Playing TRACK_BOTH_SETS");
        playTrack(TRACK_BOTH_SETS);
    } else if (set1Intensity == PRESS_HARD || set2Intensity == PRESS_HARD) {
        //Serial.println("Playing TRACK_FANTASTIC");
        playTrack(TRACK_FANTASTIC);
    } else if (set1Intensity == PRESS_MEDIUM || set2Intensity == PRESS_MEDIUM) {
        //Serial.println("Playing TRACK_PERFECT");
        playTrack(TRACK_PERFECT);
    } else if (set1Intensity == PRESS_LIGHT || set2Intensity == PRESS_LIGHT) {
        //Serial.println("Playing TRACK_GOOD");
        playTrack(TRACK_GOOD);
    }
    
    //Serial.println("-------------------\n");
    delay(DEBOUNCE_TIME);
}