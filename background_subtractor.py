from __future__ import print_function

import datetime
import math
from uuid import uuid4

import cv2
import imageio
#from tensorflow.keras.models import load_model
import tflite_runtime.interpreter as tflite
#import tensorflow as tf

import numpy as np
import time

import cv2 as cv

buffer_v1 = [(0, 999), (999, 999), (0, 999), (999, 999), (0, 999), (999, 999)]
buffer_v2 = [(999, 999), (0, 999), (999, 999), (0, 999), (999, 999), (0, 999)]

still_frame = None
moving = False
rectangles = []


def distribute(center, length, limit):
    result = [0, 0]
    length /= 2
    if center > length:
        result[0] = center - length
        if limit - center > length:
            result[1] = center + length
        else:
            result[1] = limit
            result[0] -= length - (limit - center)
    else:
        result[0] = 0
        result[1] = length * 2
    return result


def get_average_vertex(v_buffer):
    temp_x, temp_y = zip(*v_buffer)
    avg_v = int(sum(temp_x) / len(v_buffer)), int(sum(temp_y) / len(v_buffer))
    return avg_v, max([math.dist(avg_v, v) for v in v_buffer])


def push_vertex_buffer(vertex, v_b):
    del v_b[0]
    v_b.append(vertex)


# print(distribute(900, 500, 1000))

if 0:
    backSub = cv.createBackgroundSubtractorMOG2(history=150, varThreshold=0)
else:
    backSub = cv.createBackgroundSubtractorKNN(dist2Threshold=1200)
capture = cv.VideoCapture(0)
time.sleep(2)
kernel = np.ones((2, 2), np.uint8)

#backSub.setShadowThreshold(0.75)
#print(backSub.getShadowThreshold())

# load the trained convolutional neural network
print("[INFO] loading network...")
# Load the TFLite model and allocate tensors.
interpreter = tflite.Interpreter(model_path="model.tflite")
interpreter.allocate_tensors()

# Get input and output tensors.
input_details = interpreter.get_input_details()
output_details = interpreter.get_output_details()
# model = load_model(r"C:\Users\fdimo\Desktop\image-classification-keras\santa_not_santa.model")

while True:
    ret, frame = capture.read()
    if frame is None:
        break

    cv.waitKey(1) & 0xff

    fgMask = backSub.apply(frame)

    cv.rectangle(frame, (10, 2), (100, 20), (255, 255, 255), -1)
    cv.putText(frame, str(capture.get(cv.CAP_PROP_POS_FRAMES)), (15, 15),
               cv.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0))

    #cv.imshow('Frame', frame)
    #cv.imshow('FG Mask', fgMask)
    #_, white_only = cv.threshold(fgMask, 250, 255, cv.THRESH_BINARY)
    #fgMask_new = cv.erode(fgMask, kernel, iterations=2)
    #cv.imshow('FG Mask New', fgMask_new)
    # Finding contours of white square:
    conts, hierarchy = cv.findContours(fgMask, cv.RETR_EXTERNAL, cv.CHAIN_APPROX_SIMPLE)

    # for cnt in conts:
    if not conts:
        continue
    for cnt in conts:
        area = cv.contourArea(cnt)
        if area > 400:
            x1, y1, w, h = cv.boundingRect(cnt)
            x2 = x1 + w  # (x1, y1) = top-left vertex
            y2 = y1 + h  # (x2, y2) = bottom-right vertex
            # rect = cv.rectangle(fgMask_new, (x1, y1), (x2, y2), (255, 0, 0), 2)
            side_length = w if w > h else h
            xC, yC = x1 + (w / 2), y1 + (h / 2)

            x1, x2 = distribute(xC, side_length, len(frame[0]))
            y1, y2 = distribute(yC, side_length, len(frame))

            rectangles.append((int(x1), int(y1), int(x2), int(y2)))

            # push_vertex_buffer((x1, y1), buffer_v1)
            # push_vertex_buffer((x2, y2), buffer_v2)
            #
            # (avg_v1_x, avg_v1_y), dev1 = get_average_vertex(buffer_v1)
            # (avg_v2_x, avg_v2_y), dev2 = get_average_vertex(buffer_v2)
            #
            # if dev1 < 20 and dev2 < 20:
            #     letter = frame[avg_v1_y:avg_v2_y, avg_v1_x:avg_v2_x]
            #     rectangles.append((avg_v1_x, avg_v1_y, avg_v2_x, avg_v2_y))
            #     cv.imshow("asd", letter)
        if area > 200:
            last_movement = datetime.datetime.now()
            if not moving:
                moving = True
                print("Motion session started")
    dist = (datetime.datetime.now() - last_movement).microseconds
    if dist > 500000:
        if moving:
            moving = False
            print("Detection finished")
            print(rectangles)
            if rectangles:
                what = cv.groupRectangles(rectangles + rectangles, groupThreshold=50, eps=0.2)
                i = 0
                for r in what[0]:
                    avg_v1_x, avg_v1_y, avg_v2_x, avg_v2_y = r
                    if avg_v2_x - avg_v1_x > 200:
                        print(f"Discarded with side_length = {avg_v2_x - avg_v1_x}")
                        continue
                    letter = frame[avg_v1_y:avg_v2_y, avg_v1_x:avg_v2_x]
                    try:
                        #cv.imshow("asd" + str(i), letter)
                        pass
                    except:
                        print("Failed to show image")
                        continue
                    i += 1
                    im = r"C:/Users/fdimo/Desktop/WICK/" + datetime.datetime.now().strftime('%Y%m-%d%H-%M%S-') + str(uuid4()) + ".png"
                    imageio.imsave(im, letter)
                    image = cv2.imread(im)
                    orig = image.copy()

                    # pre-process the image for classification
                    image = cv2.resize(image, (28, 28))
                    image = image.astype("float32") / 255.0
                    image = np.array(image)
                    image = np.expand_dims(image, axis=0)

                    # classify the input image
                    # (notSanta, santa) = model.predict(image)[0]

                    # Test the model on random input data.
                    input_shape = input_details[0]['shape']

                    interpreter.set_tensor(input_details[0]['index'], image)

                    # class_names = ["Not Santa", "Santa"]
                    interpreter.invoke()

                    # The function `get_tensor()` returns a copy of the tensor data.
                    # Use `tensor()` in order to get a pointer to the tensor.
                    output_data = interpreter.get_tensor(output_details[0]['index'])
                    output_data = output_data[0]
                    print(output_data)
                    #print(class_names[np.argmax(output_data[0])])

                    # build the label
                    notSanta, santa = output_data
                    label = "Santa" if santa > notSanta else "Not Santa"
                    proba = santa if santa > notSanta else notSanta
                    label = "{}: {:.2f}%".format(label, proba * 100)

                    print(label)

                    # # draw the label on the image
                    # output = imutils.resize(orig, width=400)
                    # cv2.putText(output, label, (10, 25), cv2.FONT_HERSHEY_SIMPLEX,
                    #             0.7, (0, 255, 0), 2)
                    #
                    # # show the output image
                    # cv2.imshow("Output", output)
                    # cv.waitKey(1) & 0xff

                print(what[0])
                rectangles = []
                what = []
        else:
            still_frame = frame
