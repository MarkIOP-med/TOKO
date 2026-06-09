// include/MP3.h
#ifndef MP3_H
#define MP3_H

void initMP3();
bool MP3Busy();
void playTrack(int soundTrack);
void play();
void randomMode();
void playbackVolume(int vol);
void sendCommand();

extern byte commandLength;
extern byte command[6];
extern int checkSum;

#endif