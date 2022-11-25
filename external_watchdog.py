import datetime
import os
import time

while True:
    if os.path.exists("pid.txt"):
        time.sleep(5)
        with open("pid.txt", "r") as f:
            pid = f.read()
        os.remove("pid.txt")
    time.sleep(2)