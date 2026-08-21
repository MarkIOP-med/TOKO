void initLeds() {
  strip0.begin();
  strip0.show(); // Initialize all pixels to 'off'
  strip1.begin();
  strip1.show(); // Initialize all pixels to 'off'
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
void setLEDColorsFromMatrix_1(uint8_t matrix[NUM_ROWS][NUM_COLS], uint8_t row) {
  if (row < NUM_ROWS) {
    for (uint8_t i = 0; i < NUM_LEDS; i++) {
      uint8_t r = matrix[row][i * 3];
      uint8_t g = matrix[row][i * 3 + 1];
      uint8_t b = matrix[row][i * 3 + 2];
      strip1.setPixelColor(i, strip1.Color(r, g, b));
    }
    strip1.show(); // Update the strip to show the new colors
  }
}
//void displayRow(int row, int output) {
//  Adafruit_NeoPixel* strip;
//  if (output == 0) {
//    strip = &strip0;
//  } else if (output == 1) {
//    strip = &strip1;
//  } else {
//    return; // Invalid output number
//  }
//
//  for (int col = 0; col < NUM_COLS; col++) {
//    int index = row * NUM_COLS + col;
//    strip->setPixelColor(index, ledColors[row][col * 3], ledColors[row][col * 3 + 1], ledColors[row][col * 3 + 2]);
//  }
//  strip->show();
//}
