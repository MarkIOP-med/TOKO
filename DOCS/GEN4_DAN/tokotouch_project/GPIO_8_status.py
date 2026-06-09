from gpiozero import DigitalInputDevice
from time import sleep
# BCM GPIO 8 — вход HOTSWAP_OK
status = DigitalInputDevice(8, pull_up=False)
try:
    while True:
        
        if status.value:
            print("GPIO 8 находится в состоянии HIGH (1)")
        else:
            print("GPIO 8 находится в состоянии LOW (0)")
        sleep(1)
except KeyboardInterrupt:
    print("Остановка...")
