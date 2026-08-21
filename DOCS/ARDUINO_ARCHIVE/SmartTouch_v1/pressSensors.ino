void initADC() {
  adc0.begin(MCP_CLK, MCP_MOSI, MCP_MISO, MCP_CS_0);
  adc1.begin(MCP_CLK, MCP_MOSI, MCP_MISO, MCP_CS_1);
  //         (sck, mosi, miso, cs);
}
void readPressSensors() {
  int chan, i = 0;
  for ( chan = 0; chan < 6; chan++) {
    pressData[i] = (adc0.readADC(chan));
    i++;
  }
  for ( chan = 0; chan < 6; chan++) {
    pressData[i] = (adc1.readADC(chan));
    i++;
  }
}
void printPressSensors() {
  Serial.println("");
  for (int j = 0; j < 12; j++) {
    Serial.print(pressData[j]); Serial.print(" , ");
  }
  Serial.println("");
}
