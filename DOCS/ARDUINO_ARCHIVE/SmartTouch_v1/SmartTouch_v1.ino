#include <Adafruit_MCP3008.h>
#include <Adafruit_NeoPixel.h>
#include "pins_obj.h"

#define NUM_LEDS 9
#define NUM_ROWS 7
#define NUM_COLS 27

Adafruit_NeoPixel strip0 = Adafruit_NeoPixel(NUM_LEDS, led_arr_0, NEO_GRB + NEO_KHZ800);
Adafruit_NeoPixel strip1 = Adafruit_NeoPixel(NUM_LEDS, led_arr_1, NEO_GRB + NEO_KHZ800);

uint8_t ledColors[NUM_ROWS][NUM_COLS] = {
  // Row 0: RGB values  (Red, Green, Blue, Yellow, Cyan, Magenta, Silver, Maroon, Dark Green)
  {255, 0, 0, 0, 255, 0, 0, 0, 255, 255, 255, 0, 0, 255, 255, 0, 255, 0, 192, 192, 192, 128, 0, 0, 0, 128, 0},
  // Row 1: RGB values  (Navy, Olive, Purple, Teal, Orange, Deep Pink, Indigo, Saddle Brown, Dark Green)
  {0, 0, 128, 128, 128, 0, 128, 0, 128, 0, 128, 128, 255, 165, 0, 255, 20, 147, 75, 0, 130, 139, 69, 19, 0, 100, 0},
  // Row 2: RGB values  (Hot Pink, Red-Orange, Forest Green, Deep Sky Blue, Medium Slate Blue, Peach Puff, Navajo White, Lemon Chiffon, Khaki)
  {255, 105, 180, 255, 69, 0, 34, 139, 34, 0, 191, 255, 123, 104, 238, 255, 228, 181, 255, 222, 173, 255, 250, 205, 240, 230, 140},
  // Row 3: RGB valuesw (Light Pink, Light Salmon, Light Sea Green, Light Sky Blue, Slate Blue, Papaya Whip, Antique White, Ivory, Light Yellow)
  {255, 182, 193, 255, 160, 122, 32, 178, 170, 135, 206, 250, 106, 90, 205, 255, 239, 213, 255, 248, 220, 255, 255, 240, 255, 255, 224},
  // Row 4: RGB values (Honeydew, Mint Cream, Azure, Alice Blue, Ghost White, Snow, Seashell, Beige, Misty Rose)
  {240, 255, 240, 245, 255, 250, 240, 255, 255, 240, 248, 255, 248, 248, 255, 255, 250, 250, 255, 245, 238, 245, 245, 220, 255, 228, 225},
  // Row 5: RGB values  (Lavender Blush, Linen, Old Lace, Floral White, Antique White, Peach Puff, Navajo White, Moccasin, Blanched Almond)
  {255, 240, 245, 250, 240, 230, 253, 245, 230, 255, 239, 219, 255, 228, 196, 255, 218, 185, 255, 222, 173, 255, 228, 181, 255, 235, 205},
  // Row 6: All zeros (No color)
  {0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0}
};
uint16_t pressData[12] = {0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0};

void setup() {
  Serial.begin(9600);
  delay(200);
  initADC();
  initVibrations();
  initLeds();
  initMP3();
  
}
void loop() {
 Serial.println("bolo bolo");
 //playTrack(3); 

  //digitalWrite(vib0,HIGH);
  delay(2000);
  digitalWrite(vib0,LOW);

  readPressSensors();
  printPressSensors();
setLEDColorsFromMatrix_0(ledColors,0);  
//  displayRow(1, 0); // row 2 to strip 0
  delay(2000);
  setLEDColorsFromMatrix_0(ledColors,6);

}
