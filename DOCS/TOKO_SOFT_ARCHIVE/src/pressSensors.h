#ifndef PRESS_SENSORS_H
#define PRESS_SENSORS_H

// ADC objects
extern Adafruit_MCP3008 adc0;
extern Adafruit_MCP3008 adc1;

// Function declarations
void initADC();
void readPressSensors(uint16_t* pressData);
void printPressSensors(const uint16_t* pressData);

#endif // PRESS_SENSORS_H 