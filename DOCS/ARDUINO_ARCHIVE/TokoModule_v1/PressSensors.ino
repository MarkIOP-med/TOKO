void PressSensorsFunc() {
  Serial.println("\nPressure!!");
  for (int ch = 0; ch < 6; ch++) PressSensorsData[ch] = analogRead(PressSensorsPins[ch]) / 4;
  printPressSensors();
  for (int ch = 0; ch < 6; ch++) {
    mySerial.println(PressSensorsData[ch]);
  }
}
void readPressSensors() {
  for (int ch = 0; ch < 6; ch++) PressSensorsData[ch] = analogRead(PressSensorsPins[ch]) / 4;
}
void printPressSensors() {
  for (int ch = 0; ch < 6; ch++) {
    Serial.print(PressSensorsData[ch]);
    Serial.print(",");
  }
  Serial.println("");
}
