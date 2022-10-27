from __future__ import print_function

import datetime
from helpers import *
import optical_flow
from uuid import uuid4
import ruptures as rpt
from sklearn.cluster import DBSCAN

# import serial
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

# print(distribute(900, 500, 1000))

if 0:
    backSub = cv.createBackgroundSubtractorMOG2(history=150, varThreshold=0)
else:
    backSub = cv.createBackgroundSubtractorKNN(detectShadows=True)
capture = cv.VideoCapture(0)
width, height = rescale_frame(640, 480, 50)
capture.set(cv.CAP_PROP_FRAME_WIDTH, width)
capture.set(cv.CAP_PROP_FRAME_HEIGHT, height)
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
    if area > 200:
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
            conts, hierarchy = cv.findContours(fgMask, cv.RETR_EXTERNAL, cv.CHAIN_APPROX_SIMPLE)
            if conts:
                biggest_contour = max(conts, key=cv.contourArea)
                if not is_on_edge(biggest_contour, frame):
                    area_buffer.append(count_white_pixels(fgMask))
                    fr1.append(frame)
                    fr2.append(fgMask)
                if cv.contourArea(biggest_contour) > 200:
                    last_movement = datetime.datetime.now()
        stop = datetime.datetime.now()
        delta = (stop - start).seconds
        try:
            print(f"FPS: {int(len(fr1) / delta)}")
        except ZeroDivisionError:
            print("Session too short")
            continue

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
            min_index = np.argmin(area_buffer[1:5])
            # index = area_buffer.index(min(area_buffer))
            cv.imshow('Frame1', fr1[min_index])
            cv.imshow('Frame2', fr2[min_index])
            cv.waitKey(1) & 0xff
            save_images(fr1[1:5], fr2[1:5], str(uuid4()))
        except IndexError:
            print("No peaks found")
        new_frames, points = optical_flow.follow(fr1[min_index + 1:], fr1[min_index],
                            max(cv.findContours(fr2[min_index], cv.RETR_EXTERNAL, cv.CHAIN_APPROX_SIMPLE)[0], key=cv.contourArea))
        cv.imshow("Bounded points", points)
        cv.waitKey(1) & 0xff
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
