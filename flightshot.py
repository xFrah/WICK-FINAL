#!/usr/bin/env python3
import datetime
import time

import numpy as np
import psutil
from lib import neopixel_spidev as neo
import vl53l5cx_ctypes as vl53l5cx
import numpy
from PIL import Image
from matplotlib import cm, pyplot as plt
import threading
import cv2 as cv

from matplotlib.ticker import LinearLocator, FormatStrFormatter

do_i_shoot = False
camera_buffer = []
lock = threading.Lock()
target_distance = 150


def setup_camera():
    cap = cv.VideoCapture(0)
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
    succ[cv.CAP_PROP_AUTO_EXPOSURE] = cap.set(cv.CAP_PROP_AUTO_EXPOSURE, 1)
    time.sleep(2)
    succ[cv.CAP_PROP_EXPOSURE] = cap.set(cv.CAP_PROP_EXPOSURE, 12)
    succ[cv.CAP_PROP_GAIN] = cap.set(cv.CAP_PROP_GAIN, 50)
    #succ[cv.CAP_PROP_BUFFERSIZE] = cap.set(cv.CAP_PROP_BUFFERSIZE, 1)

    print(str(tuple([cap.get(item) if value else "FAILED" for item, value in succ.items()])) + ")")
    return cap


def setup_led():
    pixels = neo.NeoPixelSpiDev(0, 0, n=24, pixel_order=neo.GRB)
    pixels.fill((0, 0, 0))
    pixels.show()
    print("[INFO] LEDs configured: {}".format(pixels))
    return pixels


# function that begins to take pictures
def camera_thread(cap):
    global camera_buffer
    ram_is_ok = True
    while True:
        _, frame = cap.read()
        if do_i_shoot:
            temp = {datetime.datetime.now(): (frame, 0)}
            while do_i_shoot and ram_is_ok:
                _, frame = cap.read()
                lentemp = len(temp)
                temp[datetime.datetime.now()] = frame, lentemp
                ram_is_ok = psutil.virtual_memory()[2] < 70
            if not ram_is_ok:
                print("[WARN] RAM is too high, waiting for next session")
                while do_i_shoot:
                    pass
                print("[WARN] Broken session has finished, waiting for next one...")
            else:
                print(f"[INFO] Session has finished, saving to buffer {len(temp)} frames")
            with lock:
                camera_buffer = temp.copy()


def tof_setup():
    print("[INFO] Uploading firmware, please wait...")
    vl53 = vl53l5cx.VL53L5CX()
    print("[INFO] Done!")
    vl53.set_resolution(8 * 8)
    vl53.set_ranging_frequency_hz(15)
    vl53.set_integration_time_ms(5)
    vl53.start_ranging()
    return vl53


def main():
    pixels = setup_led()
    cap = setup_camera()
    _, frame = cap.read()
    threading.Thread(target=camera_thread, args=(cap,)).start()
    vl53 = tof_setup()
    global do_i_shoot
    global camera_buffer
    count = 0
    movement = False
    start = datetime.datetime.now()
    tof_buffer = {}
    while True:
        if vl53.data_ready():
            data = vl53.get_data()
            asd = sorted(data.distance_mm[0])[:5]
            if not movement:
                if asd[2] < 200:
                    pixels.fill((255, 255, 255))
                    camera_buffer = {}
                    tof_buffer = {datetime.datetime.now(): (data.distance_mm[0], sum(asd) / len(asd))}
                    do_i_shoot = True
                    movement = True
                    print("[INFO] Movement detected")
                    start = datetime.datetime.now()
            else:
                if asd[2] > 200:
                    do_i_shoot = False
                    movement = False
                    while len(camera_buffer) == 0:
                        pass
                    with lock:
                        pixels.fill((1, 1, 1))
                        pixels.show()
                        print(f"[INFO] Movement stopped, FPS: {(count / (datetime.datetime.now() - start).total_seconds(), len(camera_buffer) / (datetime.datetime.now() - start).total_seconds())}")
                        # for frame in camera_buffer:
                        #     cv.imshow("frame", frame)
                        #     cv.waitKey(1) & 0xFF
                        #     time.sleep(0.2)
                        # print("[INFO] Showed {} frames".format(len(camera_buffer)))

                        # camera_buffer is time: frame, frame_number
                        # tof_buffer is time: (full_matrix, distance)
                        time_target_item = min(tof_buffer.items(), key=lambda d: abs(d[1][1] - target_distance))
                        closest_frame_item = min(camera_buffer.items(), key=lambda d: abs((d[0] - time_target_item[0]).total_seconds()))
                        print(f"[INFO] Target is frame {closest_frame_item[1][1]} at {time_target_item[1][1]}mm")
                        print(f"[INFO] Distances: {[dist[1] for dist in tof_buffer.values()]}")
                        cv.imshow("frame", closest_frame_item[1][0])
                        cv.waitKey(1) & 0xFF
                    count = 0
                else:
                    # print(f"Object at {sum(asd) / 3} mm")
                    # print(list(data.distance_mm[0]))
                    tof_buffer[datetime.datetime.now()] = (data.distance_mm[0], sum(asd) / len(asd))
                    count += 1

        time.sleep(0.002)  # Avoid polling *too* fast


if __name__ == '__main__':
    main()
