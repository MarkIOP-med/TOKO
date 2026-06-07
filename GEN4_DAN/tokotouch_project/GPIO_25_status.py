from gpiozero import DigitalInputDevice

# BCM GPIO 25 — вход HOTSWAP_OK
status = DigitalInputDevice(25, pull_up=False)

if status.value:
    print("GPIO 25 находится в состоянии HIGH (1)")
else:
    print("GPIO 25 находится в состоянии LOW (0)")
