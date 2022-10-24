# Importing Libraries
import datetime

import serial
arduino = serial.Serial(port='COM5', baudrate=9600, timeout=1)
now = datetime.datetime.now()
while True:
    arduino.write(b"34\r\n")
    if arduino.readline():
        print(f"Done in {(datetime.datetime.now() - now).seconds} seconds")
        break
