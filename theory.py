
import time
import busio
from digitalio import DigitalInOut, Direction
import adafruit_fingerprint

import serial
uart = serial.Serial("/dev/ttyUSB0", baudrate=57600, timeout=1)


finger = adafruit_fingerprint.Adafruit_Fingerprint(uart)

with open("template1.dat", "rb") as file:
        data = file.read()

r = finger.send_fpdata(list(data), "char", 1)

r = finger.store_model(2)
print(r)
