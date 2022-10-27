from __future__ import print_function

import datetime
import optical_flow
import math
import pandas as pd
import matplotlib.pyplot as plt
from scipy.signal import savgol_filter, find_peaks
from uuid import uuid4
import ruptures as rpt

import cv2
import imageio
# import serial
import os
# from tensorflow.keras.models import load_model
# import tflite_runtime.interpreter as tflite
# import tensorflow as tf

import numpy as np
import time

import cv2 as cv

buffer_v1 = [(0, 999), (999, 999), (0, 999), (999, 999), (0, 999), (999, 999)]
buffer_v2 = [(999, 999), (0, 999), (999, 999), (0, 999), (999, 999), (0, 999)]

still_frame = None
moving = False
rectangles = []


# function to join two numpy arrays
def join_arrays(arr1, arr2):
    return np.concatenate((arr1, arr2))


# function to find first peak using scipy.signal.find_peaks
def find_first_peak(y):
    peaks, _ = find_peaks(y)
    return peaks[0]


def find_local_minimas(y):
    peaks, _ = find_peaks(y * -1)
    return peaks


# function to count white pixels in frame
def count_white_pixels(frame):
    return np.sum(frame == 255)


# function to plot a set of y coordinates
def plot_y(y, first_peak, minimas):
    plt.plot(y)
    first_peak = first_peak[0][0]
    # plot vertical line at x
    plt.axvline(x=first_peak, color='r')
    # for bk in bkps:
    #    plt.axvline(x=bk, color='g')
    for bk in minimas:
        plt.axvline(x=bk, color='b')
    plt.show()


# function that creates a directory with specified name in the current working directory
def create_dir(name):
    if not os.path.exists(name):
        os.makedirs(name)


# function that creates a directory and saves a list of images in it
def save_images(frames, sub_frames, uuid):
    create_dir(uuid)
    create_dir(uuid + "sub")
    uuid_sub = uuid + "sub/"
    uuid = uuid + "/"
    for i in range(len(frames)):
        imageio.imwrite(uuid + str(i) + '.png', frames[i])
        imageio.imwrite(uuid_sub + str(i) + 'sub.png', sub_frames[i])


# function to check if contour is in the center of the image with threshold
def is_in_center(cnt, frame, threshold):
    x, y, w, h = cv.boundingRect(cnt)
    return frame.shape[1] / 2 - threshold < x < frame.shape[1] / 2 + threshold and frame.shape[0] / 2 - threshold < y < \
           frame.shape[0] / 2 + threshold


# function that applies mask to image
def apply_mask(frame, mask):
    return cv.bitwise_and(frame, frame, mask=mask)


# function to check if a contour is on the edge of the image
def is_on_edge(cnt, frame):
    x, y, w, h = cv.boundingRect(cnt)
    return x == 0 or y == 0 or x + w == frame.shape[1] or y + h == frame.shape[0]


def change_color(color, arduino):
    asd = {"white": b"34",
           "red": b"23",
           "green": b"12",
           }
    while True:
        bi = asd[color]
        arduino.write(bi)
        line = arduino.readline()
        if bi in line:
            print(f"Color changed to {color}")
            break


def push_vertex_buffer(vertex, v_b):
    del v_b[0]
    v_b.append(vertex)


def get_white_mask(frame):
    mask = np.zeros(frame.shape[:2], np.uint8)
    mask[frame == 255] = 255
    return mask


# save array of images as gif
def save_gif(frames):
    imageio.mimsave(str(uuid4()) + '.gif', frames)


# print(distribute(900, 500, 1000))

if 0:
    backSub = cv.createBackgroundSubtractorMOG2(history=150, varThreshold=0)
else:
    backSub = cv.createBackgroundSubtractorKNN(dist2Threshold=1200, detectShadows=True)
capture = cv.VideoCapture(0)
time.sleep(2)
kernel = np.ones((2, 2), np.uint8)

backSub.setShadowThreshold(0.05)
print(backSub.getShadowThreshold())

# load the trained convolutional neural network
print("[INFO] loading network...")
# Load the TFLite model and allocate tensors.
# interpreter = tflite.Interpreter(model_path="model.tflite")
# interpreter.allocate_tensors()

# Get input and output tensors.
# input_details = interpreter.get_input_details()
# output_details = interpreter.get_output_details()
# model = load_model(r"C:\Users\fdimo\Desktop\image-classification-keras\santa_not_santa.model")
last_red = None
last_thing = None
# os.system("sudo chmod 666 /dev/ttymxc2")
# arduino = serial.Serial(port="/dev/ttymxc2", baudrate=9600, timeout=1)
# change_color("white", arduino)
# arduino.close()

# model = rpt.Dynp(model="l1")

while True:
    ret, frame = capture.read()
    if frame is None:
        break

    cv.waitKey(1) & 0xff

    fgMask = backSub.apply(frame)
    fgMask = get_white_mask(fgMask)

    # if last_thing and (datetime.datetime.now() - last_thing).seconds < 3:
    #     continue
    # elif last_thing:
    #     last_thing = None
    #     print("Ready again")

    cv.rectangle(frame, (10, 2), (100, 20), (255, 255, 255), -1)

    cv.imshow('Frame', frame)
    cv.imshow('FG Mask', fgMask)

    conts, hierarchy = cv.findContours(fgMask, cv.RETR_EXTERNAL, cv.CHAIN_APPROX_SIMPLE)

    # for cnt in conts:
    if not conts:
        continue
    cnt = max(conts, key=cv.contourArea)
    area = cv.contourArea(cnt)
    if area > 600 and not is_on_edge(cnt, frame):
        print("Motion session started")
        area_buffer = []
        fr1 = []
        fr2 = []
        # area_buffer, fr1, fr2 = optical_flow.follow(frame, capture, cnt, fgMask, backSub, datetime.datetime.now())
        start = datetime.datetime.now()
        last_movement = start
        first_frame = frame
        first_contour = cnt
        first_fgMask = fgMask
        while (datetime.datetime.now() - last_movement).microseconds < 500000:
            ret, frame = capture.read()
            fgMask = backSub.apply(frame)
            fgMask = get_white_mask(fgMask)
            area_buffer.append(count_white_pixels(fgMask))
            fr1.append(frame)
            fr2.append(fgMask)
            conts, hierarchy = cv.findContours(fgMask, cv.RETR_EXTERNAL, cv.CHAIN_APPROX_SIMPLE)
            if conts and cv.contourArea(max(conts, key=cv.contourArea)) > 200:
                last_movement = datetime.datetime.now()
        stop = datetime.datetime.now()
        delta = (stop - start).seconds
        print(f"FPS: {int(len(fr1) / delta)}")

        # area_y = savgol_filter(area_buffer, len(area_buffer) - (0 if len(area_buffer) % 2 else 1), 3)
        # area_y = join_arrays(np.array(
        #    area_y[0:2][::-1] if area_y[0] > area_y[2] else [p - (area_y[2] - area_y[0]) for p in area_y[0:2]]),
        #    area_y)
        # y = np.array(area_y.tolist())
        # model.fit(y)
        # breaks = model.predict(n_bkps=2)
        try:
            # fp = find_peaks(area_y)
            # minimas = find_local_minimas(area_y)
            # plot_y(area_y, fp, minimas)
            # print(breaks)
            min_index = np.argmin(area_buffer[:10])
            # index = area_buffer.index(min(area_buffer))
            cv.imshow('Frame1', fr1[min_index])
            cv.imshow('Frame2', fr2[min_index])
            cv.waitKey(1) & 0xff
            save_images(fr1[:10], fr2[:10], str(uuid4()))
        except IndexError:
            print("No peaks found")
        new_frames, points = optical_flow.follow(fr1[min_index + 1:], fr1[min_index],
                            max(cv.findContours(fr2[min_index], cv.RETR_EXTERNAL, cv.CHAIN_APPROX_SIMPLE)[0], key=cv.contourArea))
        cv.imshow("Bounded points", points)
        save_gif(new_frames)
        print("Gif printed")
        save_images(fr1[min_index:], fr2[min_index:], str(uuid4()))

        # i += 1
        # im = datetime.datetime.now().strftime('%Y%m-%d%H-%M%S-') + str(uuid4()) + ".png"
        # imageio.imsave(im, letter)
        # image = cv2.imread(im)
        # orig = image.copy()
        #
        # # pre-process the image for classification
        # image = cv2.resize(image, (28, 28))
        # image = image.astype("float32") / 255.0
        # image = np.array(image)
        # image = np.expand_dims(image, axis=0)
        #
        # # classify the input image
        # # (notSanta, santa) = model.predict(image)[0]
        #
        # # Test the model on random input data.
        # input_shape = input_details[0]['shape']
        #
        # interpreter.set_tensor(input_details[0]['index'], image)
        #
        # # class_names = ["Not Santa", "Santa"]
        # interpreter.invoke()
        #
        # # The function `get_tensor()` returns a copy of the tensor data.
        # # Use `tensor()` in order to get a pointer to the tensor.
        # output_data = interpreter.get_tensor(output_details[0]['index'])
        # output_data = output_data[0]
        # print(output_data)
        # # print(class_names[np.argmax(output_data[0])])
        #
        # # build the label
        # notSanta, santa = output_data
        # label = "Santa" if santa > notSanta else "Not Santa"
        # if label == "Santa":
        #     c += 1
        # else:
        #     d += 1
        # proba = santa if santa > notSanta else notSanta
        # label = "{}: {:.2f}%".format(label, proba * 100)
        #
        # print(label)

        # # draw the label on the image
        # output = imutils.resize(orig, width=400)
        # cv2.putText(output, label, (10, 25), cv2.FONT_HERSHEY_SIMPLEX,
        #             0.7, (0, 255, 0), 2)
        #
        # # show the output image
        # cv2.imshow("Output", output)
        # cv.waitKey(1) & 0xff

        # print(what[0])
        # rectangles = []
        # what = []
        # if d != 0:
        #     change_color("red", arduino)
        #     time.sleep(2)
        #     change_color("white", arduino)
        #     last_thing = datetime.datetime.now()
        # elif c != 0:
        #     change_color("green", arduino)
        #     time.sleep(2)
        #     change_color("white", arduino)
        #     last_thing = datetime.datetime.now()
        # arduino.close()
    # else:
    #     still_frame = frame
