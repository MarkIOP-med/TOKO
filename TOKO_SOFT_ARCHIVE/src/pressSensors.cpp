// src/pressSensors.cpp
#include <Arduino.h>
#include <Adafruit_MCP3008.h>
#include "pins_obj.h"
#include "globals.h"
#include "pressSensors.h"

void initADC() {
    adc0.begin(MCP_CLK, MCP_MOSI, MCP_MISO, MCP_CS_0);
    adc1.begin(MCP_CLK, MCP_MOSI, MCP_MISO, MCP_CS_1);
    //         (sck, mosi, miso, cs);
}

void readPressSensors(uint16_t* pressData) {
    int chan, i = 0;
    for (chan = 0; chan < 6; chan++) {
        pressData[i] = (adc0.readADC(chan));
        i++;
    }
    for (chan = 0; chan < 6; chan++) {
        pressData[i] = (adc1.readADC(chan));
        i++;
    }
}

void printPressSensors(const uint16_t* pressData) {
    Serial.println("");
    for (int j = 0; j < 12; j++) {
        Serial.print(pressData[j]); Serial.print(" , ");
    }
    Serial.println("");
}
