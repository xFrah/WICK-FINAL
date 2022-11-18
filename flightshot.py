#!/usr/bin/env python3
import datetime
import json
import math
import time

import numpy as np
import psutil
from lib import neopixel_spidev as neo
import vl53l5cx_ctypes as vl53l5cx
import numpy
from PIL import Image
from matplotlib import cm
import threading
from pycoral.utils import edgetpu
from pycoral.adapters import common
from pycoral.adapters import classify
import cv2 as cv

do_i_shoot = False
camera_buffer = {}
lock = threading.Lock()
target_distance = 150
label_dict = {0: "plastic", 1: "paper"}


def get_diff(frame, background):
    gray = cv.cvtColor(frame, cv.COLOR_BGR2GRAY)
    gray = cv.GaussianBlur(gray, (21, 21), 0)
    background = cv.cvtColor(background, cv.COLOR_BGR2GRAY)
    background = cv.GaussianBlur(background, (21, 21), 0)
    frameDelta = cv.absdiff(background, gray)
    thresh = cv.threshold(frameDelta, 25, 255, cv.THRESH_BINARY)[1]
    thresh = cv.dilate(thresh, None, iterations=2)

    conts, hierarchy = cv.findContours(thresh, cv.RETR_EXTERNAL, cv.CHAIN_APPROX_SIMPLE)
    try:
        x, y, w, h = cv.boundingRect(
            np.concatenate(np.array([cont for cont in conts if cv.contourArea(cont) > 20])))
        return x, y, w, h
    except ValueError:
        print("[WARN] No contours found")


def show_results(tof_frame, camera_frame, background, interpreter):
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

    rect = get_diff(camera_frame, background)
    if rect:
        x, y, w, h = rect
        img = cv.rectangle(camera_frame, (x, y), (x + w - 1, y + h - 1), 255, 2)

        cropped = img[y:y + h, x:x + w]

        if cropped.shape[0] > 0 and cropped.shape[1] > 0:
            # convert to rgb
            cropped = cv.cvtColor(cropped, cv.COLOR_BGR2RGB)
            label, score = inference(cropped, interpreter)
            print(f"[INFO] Class: {label}, score: {int(score * 100)}%")

    # cv.imshow("Diff", thresh)
    cv.imshow("Cropped", cropped)
    cv.imshow("Camera", camera_frame)
    cv.waitKey(1) & 0xFF
    return label, score


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

    c = 0
    start = datetime.datetime.now()
    while c < 100:
        _, frame = cap.read()
        c += 1
    print("[INFO] Camera setup complete, FPS: {}".format(100 / (datetime.datetime.now() - start).total_seconds()))
    return cap


def setup_led():
    pixels = neo.NeoPixelSpiDev(0, 0, n=24, pixel_order=neo.GRB)
    pixels.fill((0, 0, 0))
    pixels.show()
    print("[INFO] LEDs configured: {}".format(pixels))
    return pixels


# change leds gradually to green
def change_to_green(pixels):
    for i in range(0, 255, 5):
        pixels.fill((0, i, 0))
        pixels.show()
        time.sleep(0.03)


# change leds gradually to green
def black_from_green(pixels):
    for i in range(0, 255, 5)[::-1]:
        pixels.fill((0, i, 0))
        pixels.show()
        time.sleep(0.03)


# change leds gradually to green
def change_to_red(pixels):
    for i in range(0, 255, 5):
        pixels.fill((i, 0, 0))
        pixels.show()
        time.sleep(0.03)


# change leds gradually to green
def black_from_red(pixels):
    for i in range(0, 255, 5)[::-1]:
        pixels.fill((i, 0, 0))
        pixels.show()
        time.sleep(0.03)


def setup_edgetpu():
    print("[INFO] Setting up EdgeTPU")
    interpreter = edgetpu.make_interpreter("/home/fra/Desktop/WICK-FINAL/model_quant_edgetpu.tflite")
    print("[INFO] EdgeTPU configured: {}".format(interpreter))
    interpreter.allocate_tensors()
    print("[INFO] Tensors allocated")
    return interpreter


# function that begins to take pictures
def camera_thread(cap):
    global camera_buffer
    ram_is_ok = True
    while True:
        _, frame = cap.read()
        if do_i_shoot:
            # temp = {datetime.datetime.now(): (frame, 0)}
            temp = {}
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


def grab_buffer():
    global camera_buffer
    while len(camera_buffer) == 0:
        pass
    with lock:
        copy = camera_buffer.copy()
        camera_buffer = {}
    return copy


# function to write dictionary to json file
def write_to_json(data, filename='data.json'):
    with open(filename, 'w') as f:
        json.dump(data, f, indent=4, default=str)


def grab_background(pixels, return_to_black=True):
    global do_i_shoot
    pixels.fill((255, 255, 255))
    pixels.show()
    do_i_shoot = True
    time.sleep(0.125)
    do_i_shoot = False
    if return_to_black:
        pixels.fill((0, 0, 0))
        pixels.show()
    buffer = grab_buffer()
    if len(buffer) > 0:
        print(f"[INFO] Background frame count: {len(buffer)}")
        return max(buffer.values(), key=lambda d: d[1])[0]
    else:
        print("[WARN] No background frames")


def inference(image, interpreter):
    image = cv.resize(image, (128, 128))
    image = cv.cvtColor(image, cv.COLOR_BGR2RGB)
    image = image.astype("float32") / 255.0
    image = np.array(image)
    image = np.expand_dims(image, axis=0)

    common.set_input(interpreter, image)
    interpreter.invoke()
    output = classify.get_classes(interpreter, top_k=1)
    return label_dict[output[0][0]], output[0][1]
    # for i in range(len(output_data)):
    #     print(f"{label_dict[i]}: {output_data[i]}")
    # argmax = np.argmax(output_data)
    # print(f"Predicted class: {label_dict[argmax]}, {int(output_data[argmax]*100)}%")


def main():
    interpreter = setup_edgetpu()
    pixels = setup_led()
    cap = setup_camera()
    threading.Thread(target=camera_thread, args=(cap,)).start()
    vl53 = tof_setup()
    global do_i_shoot
    count = 0
    movement = False
    start = datetime.datetime.now()
    tof_buffer = {}
    background = grab_background(pixels)
    while True:
        if vl53.data_ready():
            data = vl53.get_data()
            asd = [e for e in data.distance_mm[0][:16] if 200 > e > 0]
            if not movement:
                if len(asd) > 0:
                    pixels.fill((255, 255, 255))
                    pixels.show()
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
                    buffer = grab_buffer()
                    pixels.fill((1, 1, 1))
                    pixels.show()
                    movement = False
                    print(
                        f"[INFO] Stopped, FPS: {(count / (datetime.datetime.now() - start).total_seconds(), len(buffer) / (datetime.datetime.now() - start).total_seconds())}")

                    # camera_buffer is time: frame, frame_number
                    # tof_buffer is time: (full_matrix, distance)
                    time_target_item = min(tof_buffer.items(), key=lambda d: abs(d[1][1] - target_distance))
                    closest_frame_item = min(buffer.items(),
                                             key=lambda d: abs((d[0] - time_target_item[0]).total_seconds()))
                    print(f"[INFO] Target is frame {closest_frame_item[1][1]} at {time_target_item[1][1]}mm")
                    print(f"[INFO] Distances: {[(round(dist[0].microsecond / 1000, 2), dist[1][1]) for dist in tof_buffer.items()]}")
                    print(f"[INFO] Frames: {[(round(frame[0].microsecond / 1000, 2), frame[1][1]) for frame in buffer.items()]}")
                    print(f"[INFO] Time distance: {round(abs(time_target_item[0] - closest_frame_item[0]).total_seconds() * 1000, 2)}ms")

                    label, score = show_results(time_target_item[1][0], closest_frame_item[1][0], background, interpreter)

                    if label == "paper":
                        change_to_green(pixels)
                    else:
                        change_to_red(pixels)
                    background = grab_background(pixels)
                    if label == "paper":
                        black_from_green(pixels)
                    else:
                        black_from_red(pixels)
                    write_to_json({"id": 0, "riempimento": 0, "timestamp_last_svuotamento": datetime.datetime.now(), "wrong_class_counte": 0, "current_class": "paper"})
                    count = 0
                else:
                    tof_buffer[datetime.datetime.now()] = (data.distance_mm[0][:16], sum(asd) / len(asd))
                    count += 1

        time.sleep(0.002)  # Avoid polling *too* fast


if __name__ == '__main__':
    main()
