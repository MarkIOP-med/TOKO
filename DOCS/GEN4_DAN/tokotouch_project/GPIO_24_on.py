from gpiozero import LED, DigitalInputDevice
from time import sleep

# BCM GPIO 24 — выход (LED)
pin = LED(24)
# BCM GPIO 5 — вход
status = DigitalInputDevice(5, pull_up=False)

print("Запуск мигания на GPIO 24...")
try:
    while True:
        pin.on()
        print("Сигнал: HIGH")
        if status.value:
            print("GPIO 5 находится в состоянии HIGH (1)")
        else:
            print("GPIO 5 находится в состоянии LOW (0)")
        sleep(1)

        pin.off()
        print("Сигнал: LOW")
        if status.value:
            print("GPIO 5 находится в состоянии HIGH (1)")
        else:
            print("GPIO 5 находится в состоянии LOW (0)")
        sleep(1)
except KeyboardInterrupt:
    print("Остановка...")
