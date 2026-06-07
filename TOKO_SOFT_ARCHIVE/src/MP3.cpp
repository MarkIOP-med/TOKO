// src/MP3.cpp
#include <Arduino.h>
#include "pins_obj.h"
#include "MP3.h"

byte commandLength;
byte command[6];
int checkSum;

void initMP3(){
Serial1.begin(9600);
pinMode(busyPin, INPUT);//pin to read from DY-SV5W buyPin
playbackVolume(20);//sets volume to lvl 30 max volume 
}

bool MP3Busy() {
    return !digitalRead(busyPin); // Return true when busy (pin is LOW)
}

void playTrack(int soundTrack) {
    Serial.print("soundTrack: ");
    Serial.println(soundTrack);
    command[0] = 0xAA;  // first byte says it's a command
    command[1] = 0x07;
    command[2] = 0x02;
    command[3] = highByte(soundTrack);  // track HIGH bit
    command[4] = lowByte(soundTrack);   // track low bit
    checkSum = 0;
    for (int q = 0; q < 5; q++) {
        checkSum += command[q];
    }
    command[5] = lowByte(checkSum);  // check bit... low bit of the sum of all previous values
    commandLength = 6;
    sendCommand();
}

void play() {
    command[0] = 0xAA;  // first byte says it's a command
    command[1] = 0x02;
    command[2] = 0x00;
    command[3] = 0xAC;
    commandLength = 4;
    sendCommand();
}

void randomMode() {
    command[0] = 0xAA;  // first byte says it's a command
    command[1] = 0x18;
    command[2] = 0x01;
    command[3] = 0x03;  // random
    checkSum = 0;
    for (int q = 0; q < 4; q++) {
        checkSum += command[q];
    }
    command[4] = lowByte(checkSum);  // check bit... low bit of the sum of all previous values
    commandLength = 5;
    sendCommand();
    
    // play() needs to be selected if you want the random tracks to start playing instantly
    play();
}

void playbackVolume(int vol) {
    if (vol > 30) {  // check within limits
        vol = 30;
    }
    command[0] = 0xAA;  // first byte says it's a command
    command[1] = 0x13;
    command[2] = 0x01;
    command[3] = vol;  // volume
    checkSum = 0;
    for (int q = 0; q < 4; q++) {
        checkSum += command[q];
    }
    command[4] = lowByte(checkSum);  // check bit... low bit of the sum of all previous values
    commandLength = 5;
    sendCommand();
}

void sendCommand() {
    for (int q = 0; q < commandLength; q++) {
        Serial1.write(command[q]);
        // Serial.print(command[q], HEX);
    }
    // Serial.println("End");
}