#!/usr/bin/env python3
"""WS2812 x2 on GPIO12 — daisy-chain: Pi → LED0 DIN, LED0 DOUT → LED1 DIN."""

import time
from rpi_ws281x import PixelStrip, Color

LED_COUNT = 2
LED_PIN = 12
LED_FREQ_HZ = 800000
LED_DMA = 10
LED_BRIGHTNESS = 40
LED_INVERT = False
LED_CHANNEL = 0

strip = PixelStrip(
    LED_COUNT,
    LED_PIN,
    LED_FREQ_HZ,
    LED_DMA,
    LED_INVERT,
    LED_BRIGHTNESS,
    LED_CHANNEL,
)


def clear():
    for i in range(strip.numPixels()):
        strip.setPixelColor(i, Color(0, 0, 0))
    strip.show()


def main():
    strip.begin()
    print("2-LED test — LED0 red, LED1 blue, then swap. Ctrl+C to stop.")

    try:
        while True:
            strip.setPixelColor(0, Color(255, 0, 0))
            strip.setPixelColor(1, Color(0, 0, 255))
            strip.show()
            time.sleep(0.7)
            strip.setPixelColor(0, Color(0, 0, 255))
            strip.setPixelColor(1, Color(255, 0, 0))
            strip.show()
            time.sleep(0.7)
    except KeyboardInterrupt:
        pass
    finally:
        clear()


if __name__ == "__main__":
    main()
