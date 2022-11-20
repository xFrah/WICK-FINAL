#!/usr/bin/env python3
import datetime
import json
import math
import os
import random
import signal
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
setup_not_done = True
data_ready = False
camera_buffer = {}
data_buffer = {}
camera_lock = threading.Lock()
data_lock = threading.Lock()
target_distance = 150
label_dict = {0: "plastic", 1: "paper"}
current_class = "paper"
wrong_class_counter = 0
last_svuotamento = datetime.datetime.now()
bin_id = 0
altezza_cestino = 600
soglia_pieno = 200
valid_classes = ["Plastica", "Carta"]


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
        return (x, y, w, h), thresh
    except ValueError:
        print("[WARN] No contours found")
    return thresh


def show_results(tof_frame, camera_frame, background, interpreter, pixels):
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

    rect, diff = get_diff(camera_frame, background)
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
    # cv.imshow("Cropped", cropped)
    cv.imshow("Camera", camera_frame)
    cv.imshow("Diff", diff)
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
    succ[cv.CAP_PROP_FPS] = cap.set(cv.CAP_PROP_FPS, 60)
    time.sleep(2)
    succ[cv.CAP_PROP_FOURCC] = cap.set(cv.CAP_PROP_FOURCC, cv.VideoWriter_fourcc('M', 'J', 'P', 'G'))
    # time.sleep(2)
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
            with camera_lock:
                camera_buffer = temp.copy()


def data_manager_thread():
    global data_ready
    # instantiate mqtt client

    while True:
        time.sleep(30)
        if data_ready:
            print("[INFO] Data is ready, saving & uploading...")
            with data_lock:
                data = data_buffer.copy()
                data_buffer.clear()
                data_ready = False
            save_buffer = {
                "riempimento": data["riempimento"][-1],
                "timestamp_last_svuotamento": str(last_svuotamento.isoformat()),
                "wrong_class_counter": data["wrong_class_counter"][-1]
            }
            # todo send save_buffer via mqtt

            with open("data.json", "w") as f:
                json.dump(save_buffer, f)

            add_lines_csv(data)
            print("[INFO] Data saved.")


def add_lines_csv(data):
    with open("history.csv", "a") as f:
        for percentage, timestamp, wrong_class_counter in zip(data["riempimento"], data["timestamp"], data["wrong_class_counter"]):
            f.write(f"{percentage},{timestamp},{wrong_class_counter}\n")


def create_csv_file():
    with open("history.csv", "w") as f:
        f.write("riempimento,timestamp,wrong_class_counter\n")


def json_setup():
    global bin_id
    global current_class

    if not os.path.exists("history.csv"):
        create_csv_file()

    if not os.path.exists("config.json"):
        with open("history.json", "w") as f:
            json.dump({"id": random.randint(0, 65534), "current_class": "None"}, f)
        print(f'[INFO] Created config.json with id {bin_id}, edit "current_class" field to continue..."')
        kill()
    else:
        with open("history.json", "r") as f:
            data = json.load(f)
        try:
            bin_id = data["id"]
            current_class = data["current_class"]
        except KeyError:
            print("[ERROR] config.json is corrupted, the program will run with id 65535 and class paper, but you should delete the config file and/or reconfigure.")
            bin_id = 65535
            current_class = "paper"
            return
        if not isinstance(bin_id, int):
            print('[ERROR] "bin_id" is not an int, please edit config.json')
            kill()
        if not isinstance(current_class, str):
            print('[ERROR] "current_class" is not a valid input, please edit config.json(did you put the quotes?)')
            kill()
        if current_class not in valid_classes:
            print(f'[ERROR] "{current_class}" is not a valid material, please edit config.json')
            kill()
        print(f"[INFO] Loaded config.json, id: {bin_id}, current_class: {current_class}")


# close all the threads and end the process
def kill():
    os.kill(os.getpid(), signal.SIGTERM)


def pass_data(data_dict):
    global data_ready
    with data_lock:
        data_ready = True
        for key, value in data_dict.items():
            data_buffer[key] = data_buffer.get(key, []) + [value]


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
    with camera_lock:
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


def timed_fill(pixels):
    global setup_not_done
    while setup_not_done:
        for i in range(0, 255, 5):
            pixels.fill((0, 0, i))
            # pixels.show()
            time.sleep(0.03)
        for i in range(0, 255, 5)[::-1]:
            pixels.fill((0, 0, i))
            # pixels.show()
            time.sleep(0.03)


def get_trash_level(vl53):
    while True:
        if vl53.data_ready():
            data = [e for e in vl53.get_data().distance_mm[0][:16] if e > 0]
            avg = sum(data) / len(data)
            percentage = (1 - (avg - soglia_pieno) / (altezza_cestino - soglia_pieno)) * 100
            print(f"[INFO] {avg}mm, {percentage}%")
            return avg, percentage
        time.sleep(0.003)


def get_frame_at_distance(tof_buffer, cap_buffer, distance):
    # camera_buffer is time: frame, frame_number
    # tof_buffer is time: (full_matrix, distance)
    time_target_item = min(tof_buffer.items(), key=lambda d: abs(d[1][1] - distance))
    closest_frame_item = min(cap_buffer.items(),
                             key=lambda d: abs((d[0] - time_target_item[0]).total_seconds()))
    print(f"[INFO] Target is frame {closest_frame_item[1][1]} at {time_target_item[1][1]}mm")
    print(f"[INFO] Distances: {[(round(dist[0].microsecond / 1000, 2), dist[1][1]) for dist in tof_buffer.items()]}")
    print(f"[INFO] Frames: {[(round(frame[0].microsecond / 1000, 2), frame[1][1]) for frame in cap_buffer.items()]}")
    print(f"[INFO] Time distance: {round(abs(time_target_item[0] - closest_frame_item[0]).total_seconds() * 1000, 2)}ms")
    return time_target_item[1][0], closest_frame_item[1][0]


def setup():
    pixels = setup_led()
    # threading.Thread(target=timed_fill, args=(pixels,)).start()
    interpreter = setup_edgetpu()
    cap = setup_camera()
    threading.Thread(target=camera_thread, args=(cap,)).start()
    threading.Thread(target=data_manager_thread).start()
    vl53 = tof_setup()
    tof_buffer = {}
    # global setup_not_done
    # setup_not_done = False
    background = grab_background(pixels)
    change_to_green(pixels)
    black_from_green(pixels)
    return pixels, interpreter, cap, vl53, background, tof_buffer


def main():
    global do_i_shoot
    pixels, interpreter, cap, vl53, background, tof_buffer = setup()
    count = 0
    movement = False
    start = datetime.datetime.now()
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
                    now = datetime.datetime.now()
                    buffer = grab_buffer()
                    pixels.fill((1, 1, 1))
                    pixels.show()
                    pixels.fill((1, 1, 1))
                    pixels.show()
                    pixels.fill((1, 1, 1))
                    pixels.show()
                    movement = False
                    print(f"[INFO] Stopped, FPS: {(count / (now - start).total_seconds(), len(buffer) / (now - start).total_seconds())}")

                    tof_target_frame, camera_target_frame = get_frame_at_distance(tof_buffer, buffer, target_distance)

                    label, score = show_results(tof_target_frame, camera_target_frame, background, interpreter, pixels)

                    if label == "paper":
                        change_to_green(pixels)
                    else:
                        change_to_red(pixels)
                    background = grab_background(pixels, return_to_black=False)
                    if label == "paper":
                        black_from_green(pixels)
                    else:
                        black_from_red(pixels)

                    avg, percentage = get_trash_level(vl53)
                    print(f"[INFO] {avg}mm, {percentage * 100}%")
                    pass_data({"riempimento": percentage, "wrong_class_counter": wrong_class_counter, "timestamp": str(now.isoformat())})
                    count = 0
                    print("[INFO] Waiting for movement...")
                else:
                    tof_buffer[datetime.datetime.now()] = (data.distance_mm[0][:16], sum(asd) / len(asd))
                    count += 1

        time.sleep(0.003)  # Avoid polling *too* fast


if __name__ == '__main__':
    main()
