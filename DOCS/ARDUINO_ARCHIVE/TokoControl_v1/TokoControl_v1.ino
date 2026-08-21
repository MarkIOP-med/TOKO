#include <SoftwareSerial.h>
// Define software serial ports
SoftwareSerial serial_MP3(11, 10); // RX, TX
SoftwareSerial serial_BT(8, 9);    // RX, TX
HardwareSerial *MySerial;
// for MP3 player
#define busyPin 3 // mp3 
byte commandLength;
byte command[6];
int checkSum = 0;
int trackNum = 1;
int fromPlate[2][6]; // sensores data
int incom;
int intCount = 0;
void setup() {
  InitSerials();
  initMP3();
  playTrack(3);
  //    MySerial = &Serial2;
  // MySerial->write("v1");
  //    MySerial->print("l2");
  //GetSensorsData(1);

}

void loop() {

}
