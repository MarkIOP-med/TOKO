void GetSensorsData(int plate) {
  if (plate == 0)  MySerial = &Serial1;
  else if (plate == 1)  MySerial = &Serial2;
  else if (plate == 2)  MySerial = &Serial3;
  intCount = 0;
  MySerial->print("p");
  while (intCount < 6) {
    if (MySerial->available() > 0) {
      incom = MySerial->parseInt();
      fromPlate[plate][intCount] = incom;
      intCount++;
    }
  }
  PrintSensorsData(plate);
}

void PrintSensorsData(int pp) {
  for (int i = 0; i < 6; i++) {
    Serial.print(fromPlate[pp][i]);
    Serial.print(" , ");
  }
  Serial.println("");
}
