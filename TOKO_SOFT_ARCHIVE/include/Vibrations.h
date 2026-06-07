// include/Vibrations.h
#ifndef VIBRATIONS_H
#define VIBRATIONS_H

void initVibrations();
void handleVibrations(int setNumber, uint8_t intensity);
void activateVibrators(int setNumber, int numVibrators);
void deactivateVibrators(int setNumber);

#endif