from gpiozero import DigitalInputDevice
from time import sleep
# BCM GPIO 1 — вход HOTSWAP_OK
status = DigitalInputDevice(1, pull_up=False)
try:
    while True:

        if status.value:
            print("GPIO 1 находится в состоянии HIGH (1)")
        else:
            print("GPIO 1 находится в состоянии LOW (0)")
        sleep(1)
except KeyboardInterrupt:
    print("Остановка...")
