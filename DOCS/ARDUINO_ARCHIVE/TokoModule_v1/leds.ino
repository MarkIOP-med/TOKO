
void LedsFunc(){
  Serial.println("\nLeds!!");
 while(mySerial.available()==0);
 SerialByte=mySerial.read();
 Serial.write(SerialByte);
 LedsOnTimeFlag=1; 
 LedsStartTime=millis();
 setLEDColorsFromMatrix_0(ledColors, SerialByte-'0');
 delay(2000);
 setLEDColorsFromMatrix_0(ledColors, 6);
}
void initLeds() {
  strip0.begin();
  strip0.show(); // Initialize all pixels to 'off'
}

void setLEDColorsFromMatrix_0(uint8_t matrix[NUM_ROWS][NUM_COLS], uint8_t row) {
  if (row < NUM_ROWS) {
    for (uint8_t i = 0; i < NUM_LEDS; i++) {
      uint8_t r = matrix[row][i * 3];
      uint8_t g = matrix[row][i * 3 + 1];
      uint8_t b = matrix[row][i * 3 + 2];
      strip0.setPixelColor(i, strip0.Color(r, g, b));
    }
    strip0.show(); // Update the strip to show the new colors
  }
}
