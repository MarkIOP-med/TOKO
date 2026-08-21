void VibrationFunc() {
  Serial.println("\nVibration!!");
  while (mySerial.available() == 0);
  SerialByte = mySerial.read();
  Serial.write(SerialByte);
  analogWrite(VibrationPins[SerialByte-'0'], VibrationData[SerialByte-'0']);
  delay(1500);
  analogWrite(VibrationPins[SerialByte-'0'], 0);
  VibrationOnFlag = 1;
  VibrationStartTime = millis();
}
void VibrationSetup() {
  for (int vb = 0; vb < 3; vb++) {
    pinMode(VibrationPins[vb], OUTPUT);
    analogWrite(VibrationPins[vb], 0);
  }
}
void WriteVibrationPins() {
  for (int vb = 0; vb < 3; vb++) analogWrite(VibrationPins[vb], VibrationData[vb]);
}
