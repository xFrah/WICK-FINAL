#!/usr/bin/env python3
import datetime
import time

import numpy as np
import psutil
import vl53l5cx_ctypes as vl53l5cx
import numpy
from PIL import Image
from matplotlib import cm, pyplot as plt
import threading
import cv2 as cv

from matplotlib.ticker import LinearLocator, FormatStrFormatter

do_i_shoot = False
camera_buffer = []


def camera_setup(cap):
    print("[INFO] Setting up camera")
    print(
        f"[INFO] Changed {(cap.get(cv.CAP_PROP_FRAME_WIDTH), cap.get(cv.CAP_PROP_FRAME_HEIGHT), cap.get(cv.CAP_PROP_FPS))} to (",
        end="")

    succ = {}
    succ[cv.CAP_PROP_FRAME_WIDTH] = cap.set(cv.CAP_PROP_FRAME_WIDTH, 640)
    succ[cv.CAP_PROP_FRAME_HEIGHT] = cap.set(cv.CAP_PROP_FRAME_HEIGHT, 480)
    succ[cv.CAP_PROP_FPS] = cap.set(cv.CAP_PROP_FPS, 120)
    time.sleep(2)
    succ[cv.CAP_PROP_FOURCC] = cap.set(cv.CAP_PROP_FOURCC, cv.VideoWriter_fourcc('M', 'J', 'P', 'G'))
    time.sleep(2)

    print(tuple([item if value else "FAILED" for item, value in succ.items()]), ")")


# function that begins to take pictures
def camera_thread():
    cap = cv.VideoCapture(0)
    camera_setup(cap)
    temp = []
    global camera_buffer
    ram_is_ok = True
    while True:
        if do_i_shoot:
            while do_i_shoot and ram_is_ok:
                _, frame = cap.read()
                temp.append(frame)
                ram_is_ok = psutil.virtual_memory()[2] < 70
            if not ram_is_ok:
                print("[WARN] RAM is too high, waiting for next session")
                temp[len(temp) // 2:] = []
                camera_buffer = temp
                while do_i_shoot:
                    pass
                print("[WARN] Broken session has finished, waiting for next one...")
            else:
                print("[INFO] Session has finished, saving to buffer")
                camera_buffer = temp


threading.Thread(target=camera_thread).start()

print("[INFO] Uploading firmware, please wait...")
vl53 = vl53l5cx.VL53L5CX()
print("[INFO] Done!")
vl53.set_resolution(4 * 4)

vl53.set_ranging_frequency_hz(60)
vl53.set_integration_time_ms(10)
vl53.start_ranging()

def main():
    count = 0
    movement = False
    start = datetime.datetime.now()
    while True:
        if vl53.data_ready():
            asd = sorted(vl53.get_data().distance_mm[0])[:5]
            if not movement:
                if asd[2] < 200:
                    movement = True
                    print("[INFO] Movement detected")
                    start = datetime.datetime.now()
            else:
                if asd[2] > 200:
                    movement = False
                    print(f"[INFO] Movement stopped, FPS: {count / (datetime.datetime.now() - start).total_seconds()}")
                    count = 0
                else:
                    # print(f"Object at {sum(asd) / 3} mm")
                    count += 1

        time.sleep(0.003)  # Avoid polling *too* fast


if __name__ == '__main__':
    main()
