from gpiozero import LED
from time import sleep

# Используем GPIO 13 (BCM)
pin = LED(13)

print("Запуск мигания на GPIO 1...")
try:
    while True:
        pin.on()
        print("Сигнал: HIGH")
        sleep(1)
        pin.off()
        print("Сигнал: LOW")
        sleep(1)
except KeyboardInterrupt:
    print("Остановка...")
