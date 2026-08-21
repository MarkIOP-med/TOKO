#include <SoftwareSerial.h>
#include <Adafruit_NeoPixel.h>
SoftwareSerial mySerial(10, 11); // RX, TX
byte SerialByte=0;
int PressSensorsPins[6] = { A0, A1, A2, A3, A6, A7 };
//int PressSensorsPins[6] = { A6, A7, A0, A1, A2, A3 };
byte PressSensorsData[6];
int VibrationPins[3] = { 3, 5, 6 };
int VibrationData[3] = { 255, 255, 255 };
unsigned long VibrationStartTime, VibrationOnTime = 2000; // in mSec
unsigned long LedsStartTime, LedsOnTime = 3000; // in mSec
bool VibrationOnFlag = 0, LedsOnTimeFlag = 0;
#define NUM_LEDS 6
#define NUM_ROWS 7
#define NUM_COLS 18
#define led_arr_0 9
Adafruit_NeoPixel strip0 = Adafruit_NeoPixel(NUM_LEDS, led_arr_0, NEO_GRB + NEO_KHZ800);
uint8_t ledColors[NUM_ROWS][NUM_COLS] = {
  // Row 0: RGB values  (Red, Green, Blue, Yellow, Cyan, Magenta, Silver)
  {255, 0, 0, 0, 255, 0, 0, 0, 255, 255, 255, 0, 0, 255, 255, 0, 255, 0},
  // Row 1: RGB values  (Navy, Olive, Purple, Teal, Orange, Deep Pink, Indigo, Saddle )
  {0, 0, 128, 128, 128, 0, 128, 0, 128, 0, 128, 128, 255, 165, 0, 255, 20, 147},
  // Row 2: RGB values  (Hot Pink, Red-Orange, Forest Green, Deep Sky Blue, Medium Slate Blue, Peach Puff)
  {255, 105, 180, 255, 69, 0, 34, 139, 34, 0, 191, 255, 123, 104, 238, 255, 228, 181},
  // Row 3: RGB valuesw (Light Pink, Light Salmon, Light Sea Green, Light Sky Blue, Slate Blue, Papaya Whip)
  {255, 182, 193, 255, 160, 122, 32, 178, 170, 135, 206, 250, 106, 90, 205, 255, 239, 213},
  // Row 4: RGB values (Honeydew, Mint Cream, Azure, Alice Blue, Ghost White, Snow, Seashell)
  {240, 255, 240, 245, 255, 250, 240, 255, 255, 240, 248, 255, 248, 248, 255, 255, 250, 250},
  // Row 5: RGB values  (Lavender Blush, Linen, Old Lace, Floral White, Antique White, Peach Puff)
  {255, 240, 245, 250, 240, 230, 253, 245, 230, 255, 239, 219, 255, 228, 196, 255, 218, 185},
  // Row 6: All zeros (No color)
  {0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0}
};
void setup() {
  Serial.begin(9600);
  mySerial.begin(4800);
  mySerial.listen();
  delay(300);
  VibrationSetup();
  initLeds();
}
void loop() {
  if (mySerial.available()) {
    SerialByte = mySerial.read();
    if (SerialByte == 'p') PressSensorsFunc();
    else if (SerialByte == 'l') LedsFunc();
    else if (SerialByte == 'v') VibrationFunc();
  }
}
