
void InitSerials() {
  Serial.begin(9600);     // USB to PC
  Serial1.begin(4800);    // UART1
  Serial2.begin(4800);    // UART2
  Serial3.begin(4800);    // UART3
  serial_MP3.begin(9600); // SoftwareSerial for MP3
  serial_BT.begin(9600);  // SoftwareSerial for Bluetooth
  serial_BT.listen();
  //serial_MP3.listen();
  Serial.println("All 5 serial ports initialized on Arduino Mega.");
}
