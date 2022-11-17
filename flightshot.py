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

from helpers import get_white_mask, erode

do_i_shoot = False
camera_buffer = []
lock = threading.Lock()
target_distance = 150


def show_results(tof_frame, camera_frame):
    temp = numpy.array(tof_frame).reshape((4, 4))
    temp = [list(reversed(col)) for col in zip(*temp)]
    temp = flip_matrix(temp)
    arr = numpy.flipud(temp).astype('float64')

    # Scale view relative to the furthest distance
    # distance = arr.max()

    # Scale view to a fixed distance
    distance = 512

    # Scale and clip the result to 0-255
    arr *= (255.0 / distance)
    arr = numpy.clip(arr, 0, 255)

    # Force to int
    arr = arr.astype('uint8')

    # Convert to a palette type image
    img = Image.frombytes("P", (4, 4), arr)
    img.putpalette(pal)
    img = img.convert("RGB")
    img = img.resize((240, 240), resample=Image.NEAREST)
    img = numpy.array(img)

    # fgMask = closest_frame_item[1][2]
    # conts, hierarchy = cv.findContours(fgMask, cv.RETR_EXTERNAL, cv.CHAIN_APPROX_SIMPLE)
    # try:
    #    x, y, w, h = cv.boundingRect(
    #        np.concatenate(np.array([cont for cont in conts if cv.contourArea(cont) > 20])))
    #    cv.rectangle(final_img, (x, y), (x + w - 1, y + h - 1), 255, 2)
    #
    # except ValueError:
    #    print("[WARN] No contours found")

    cv.imshow("Tof", img)
    cv.imshow("Camera", camera_frame)
    cv.waitKey(1) & 0xFF


def get_palette(name):
    cmap = cm.get_cmap(name, 256)

    try:
        colors = cmap.colors
    except AttributeError:
        colors = numpy.array([cmap(i) for i in range(256)], dtype=float)

    arr = numpy.array(colors * 255).astype('uint8')
    arr = arr.reshape((16, 16, 4))
    arr = arr[:, :, 0:3]
    return arr.tobytes()


pal = get_palette("plasma")


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
    succ[cv.CAP_PROP_GAIN] = cap.set(cv.CAP_PROP_GAIN, 100)
    # succ[cv.CAP_PROP_BUFFERSIZE] = cap.set(cv.CAP_PROP_BUFFERSIZE, 1)

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
    backSub = cv.createBackgroundSubtractorMOG2(detectShadows=True, history=100, varThreshold=100)
    last_applied = datetime.datetime.now()
    while True:
        _, frame = cap.read()
        # if (datetime.datetime.now() - last_applied).total_seconds() < 5:
        # fgMask = backSub.apply(frame)
        # cv.imshow('Frame', frame)
        # cv.imshow('FG Mask', fgMask)
        # cv.waitKey(1) & 0xFF
        if do_i_shoot:
            # temp = {datetime.datetime.now(): (frame, 0)}
            temp = {}
            while do_i_shoot and ram_is_ok:
                _, frame = cap.read()
                # fgMask = backSub.apply(frame)
                # fgMask = get_white_mask(fgMask)
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
            # last_applied = datetime.datetime.now()


def tof_setup():
    print("[INFO] Uploading firmware, please wait...")
    vl53 = vl53l5cx.VL53L5CX()
    print("[INFO] Done!")
    vl53.set_resolution(4 * 4)
    vl53.set_ranging_frequency_hz(60)
    vl53.set_integration_time_ms(5)
    vl53.start_ranging()
    return vl53


# function to flip matrix horizontally
def flip_matrix(matrix):
    return numpy.flip(matrix, 1)


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
            asd = [e for e in data.distance_mm[0][:16] if e < 200]
            if not movement:
                if len(asd) > 0:
                    pixels.fill((255, 255, 255))
                    pixels.show()
                    camera_buffer = {}
                    tof_buffer = {datetime.datetime.now(): (data.distance_mm[0][:16], sum(asd) / len(asd))}
                    do_i_shoot = True
                    movement = True
                    print("[INFO] Movement detected")
                    print(asd, sum(asd) / len(asd))
                    start = datetime.datetime.now()
                    count = 1
            else:
                if len(asd) == 0:
                    do_i_shoot = False
                    movement = False
                    while len(camera_buffer) == 0:
                        pass
                    with lock:
                        pixels.fill((1, 1, 1))
                        pixels.show()
                        print(
                            f"[INFO] Movement stopped, FPS: {(count / (datetime.datetime.now() - start).total_seconds(), len(camera_buffer) / (datetime.datetime.now() - start).total_seconds())}")
                        # for frame in camera_buffer:
                        #     cv.imshow("frame", frame)
                        #     cv.waitKey(1) & 0xFF
                        #     time.sleep(0.2)
                        # print("[INFO] Showed {} frames".format(len(camera_buffer)))

                        # camera_buffer is time: frame, frame_number
                        # tof_buffer is time: (full_matrix, distance)
                        time_target_item = min(tof_buffer.items(), key=lambda d: abs(d[1][1] - target_distance))
                        closest_frame_item = min(camera_buffer.items(),
                                                 key=lambda d: abs((d[0] - time_target_item[0]).total_seconds()))
                        print(f"[INFO] Target is frame {closest_frame_item[1][1]} at {time_target_item[1][1]}mm")
                        print(f"[INFO] Distances: {[dist[1] for dist in tof_buffer.values()]}")
                        print(
                            f"[INFO] Time distance: {abs(time_target_item[0] - closest_frame_item[0]).total_seconds()}")

                        show_results(time_target_item[1][0], closest_frame_item[1][0])

                        time.sleep(1.5)

                        pixels.fill((255, 255, 255))
                        pixels.show()
                        camera_buffer = {}
                        do_i_shoot = True
                        time.sleep(0.125)
                        do_i_shoot = False
                        pixels.fill((0, 0, 0))
                        pixels.show()
                        cam_buf_len = len(camera_buffer)
                        if cam_buf_len > 0:
                            print(f"[INFO] Background frame count: {cam_buf_len}")
                            cv.imshow("Target", max(camera_buffer.values(), key=lambda d: d[1])[0])
                        else:
                            print("[WARN] No background frames")
                        cv.waitKey(1) & 0xFF

                    count = 0
                else:
                    # print(f"Object at {sum(asd) / 3} mm")
                    # print(list(data.distance_mm[0]))
                    #  print(asd, sum(asd) / len(asd))
                    tof_buffer[datetime.datetime.now()] = (data.distance_mm[0][:16], sum(asd) / len(asd))
                    count += 1

        time.sleep(0.002)  # Avoid polling *too* fast


if __name__ == '__main__':
    main()
