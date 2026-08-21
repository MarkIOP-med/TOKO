// for MP3 player
#define busyPin 3
byte commandLength;
byte command[6];
int checkSum = 0;
int trackNum = 1;
// for AtoD
#define MCP_CLK A2
#define MCP_MOSI A1
#define MCP_MISO A0
#define MCP_CS_0 A3
#define MCP_CS_1 A4
Adafruit_MCP3008 adc0;
Adafruit_MCP3008 adc1;

//for Vibrations
#define vib0 4
#define vib1 5
#define vib2 9
#define vib3 10
#define vib4 11
#define vib5 12
// for leds
#define led_arr_0 7
#define led_arr_1 8


