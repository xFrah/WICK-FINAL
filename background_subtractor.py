from __future__ import print_function

import datetime
from helpers import *

from lib import neopixel_spidev as neo
from lib.pixelbuf import wheel
# from tracking import track
from uuid import uuid4

# import serial
#from tensorflow.keras.models import load_model
import tflite_runtime.interpreter as tflite
#import tensorflow as tf

import numpy as np
import time
import streamer
import cv2 as cv


# function to save multiple images with given names
def save_images_with_names(frames, names, path):
    for i in range(len(frames)):
        filename = fr"{path}\{path}-{names[i]}.png"
        print(f"Saved {filename}")
        imageio.imwrite(filename, frames[i])


if __name__ == '__main__':

    buffer_v1 = [(0, 999), (999, 999), (0, 999), (999, 999), (0, 999), (999, 999)]
    buffer_v2 = [(999, 999), (0, 999), (999, 999), (0, 999), (999, 999), (0, 999)]

    label_dict = {0: "plastic", 1: "paper"}

    still_frame = None
    moving = False
    rectangles = []

    # print(distribute(900, 500, 1000))

    if 1:
        backSub = cv.createBackgroundSubtractorMOG2(detectShadows=True, history=200, varThreshold=200)
    else:
        backSub = cv.createBackgroundSubtractorKNN(detectShadows=True, history=200, varThreshold=200)
    capture = cv.VideoCapture("/dev/video1")
    # width, height = rescale_frame(640, 480, 50)
    print(capture.set(cv.CAP_PROP_FRAME_WIDTH, 640))
    print(capture.set(cv.CAP_PROP_FRAME_HEIGHT, 480))
    print(capture.set(cv.CAP_PROP_FPS, 120))
    # print(capture.set(cv.CAP_PROP_AUTO_EXPOSURE, 0.25))
    print(capture.set(cv.CAP_PROP_EXPOSURE, -9))
    print(capture.set(cv.CAP_PROP_GAIN, 100))
    time.sleep(2)
    kernel = np.ones((2, 2), np.uint8)

    # backSub.setShadowThreshold(0.05)
    print(backSub.getShadowThreshold())

    # load the trained convolutional neural network
    print("[INFO] loading network...")
    # Load the TFLite model and allocate tensors.
    interpreter = tflite.Interpreter(model_path="model.tflite")
    interpreter.allocate_tensors()

    # Get input and output tensors.
    input_details = interpreter.get_input_details()
    output_details = interpreter.get_output_details()
    # model = load_model(r"C:\Users\fdimo\Desktop\image-classification-keras\santa_not_santa.model")
    last_red = None
    last_thing = None
    # os.system("sudo chmod 666 /dev/ttymxc2")
    # arduino = serial.Serial(port="/dev/ttymxc2", baudrate=9600, timeout=1)
    # arduino.close()

    pixels = neo.NeoPixelSpiDev(0, 0, n=24, pixel_order=neo.GRB)
    print("[INFO] LEDs configured: {}".format(pixels))
    pixels.fill((0, 0, 0))
    pixels.show()

    streamer.start_thread("127.0.0.1", "8080")

    while True:
        ret, frame = capture.read()
        if frame is None:
            break

        fgMask = backSub.apply(frame)
        fgMask = get_white_mask(fgMask)

        # if last_thing and (datetime.datetime.now() - last_thing).seconds < 3:
        #     continue
        # elif last_thing:
        #     last_thing = None
        #     print("Ready again")

        # cv.rectangle(frame, (10, 2), (100, 20), (255, 255, 255), -1)
        #cv.imshow('Frame', frame)
        #cv.imshow('FG Mask', fgMask)
        cv.waitKey(1) & 0xff
        streamer.change_frame(frame)


        conts, hierarchy = cv.findContours(fgMask, cv.RETR_EXTERNAL, cv.CHAIN_APPROX_SIMPLE)

        # for cnt in conts:
        if not conts:
            continue
        cnt = max(conts, key=cv.contourArea)
        area = cv.contourArea(cnt)
        if area > 200:
            print("[STATUS] Motion session started")
            flash = None
            flash2 = None
            flash3 = None
            flash4 = None
            # ret, frame = capture.read()
            area_buffer = []

            # area_buffer, fr1, fr2 = optical_flow.follow(frame, capture, cnt, fgMask, backSub, datetime.datetime.now())
            start = datetime.datetime.now()
            last_movement = start
            first_frame = frame
            first_contour = cnt
            first_fgMask = fgMask
            fr1 = [first_frame]
            fr2 = [first_fgMask]
            while (datetime.datetime.now() - last_movement).microseconds < 500000:
                ret, frame = capture.read()
                fgMask = backSub.apply(frame)
                #cv.imshow("Frame", frame)
                #cv.imshow("FG Mask", fgMask)
                #cv.waitKey(1) & 0xff
                if flash is None and (datetime.datetime.now() - start).microseconds > 85000:
                    flash2 = fgMask
                    flash3 = erode(flash2)
                    conts, hierarchy = cv.findContours(flash3, cv.RETR_EXTERNAL, cv.CHAIN_APPROX_SIMPLE)
                    try:
                        x, y, w, h = cv.boundingRect(
                            np.concatenate(np.array([cont for cont in conts if cv.contourArea(cont) > 20])))
                    except ValueError:
                        pass
                    flash = frame
                    flash4 = flash
                    # cv.rectangle(flash4, (x, y), (x + w - 1, y + h - 1), 255, 2)
                    # apply morphological closing to fill in holes on flash2
                    # flash2 = cv.morphologyEx(flash2, cv.MORPH_CLOSE, kernel)
                # fgMask = get_white_mask(fgMask)
                # try:
                #     fgMask = get_blobl_with_closing(fgMask)
                # except ValueError:
                #
                #     continue
                conts, hierarchy = cv.findContours(fgMask, cv.RETR_EXTERNAL, cv.CHAIN_APPROX_SIMPLE)
                # if not is_on_edge(biggest_contour, frame):
                # area_buffer.append(count_white_pixels(fgMask))
                fr1.append(frame)
                fr2.append(fgMask)
                if conts and cv.contourArea(max(conts, key=cv.contourArea)) > 100:
                    last_movement = datetime.datetime.now()
            # morphological open frames in list with opencv
            # for i in range(len(fr2)):
            #    fr2[i] = morphological_top_hat(fr2[i])
            # fr1 = [apply_mask(f, f2) for f, f2 in zip(fr1, fr2)]
            stop = datetime.datetime.now()
            delta = (stop - start).total_seconds()
            print(f"[INFO] Session duration: {delta} seconds")
            if delta < 0.1:
                print("[INFO] Session too short, aborting...")
                continue
            print(f"[INFO] FPS: {int(len(fr1) / delta)}")

            # kalman_tracking(fr1[min_index:], x, x + w, y, y + h)
            temp = datetime.datetime.now()
            fr1 = [cv.cvtColor(f, cv.COLOR_BGR2RGB) for f in fr1]
            print("[INFO] Images converted to RGB in {:.3f} seconds".format(
                (datetime.datetime.now() - temp).total_seconds()))

            # cv.imshow('Frame', frame)
            # cv.imshow('FG Mask', fgMask)
            # cv.imshow('Flash', flash)
            # cv.imshow('Flash2', flash2)
            # cv.imshow('Flash3', flash3)
            # cv.imshow('Flash4', flash4)
            try:
                image = flash[y:y + h, x:x + w]
                #cv.imshow('Cropped', image)
            except NameError:
                pass
            cv.waitKey(1) & 0xff
            # save_images(fr1[1:5], fr2[1:5], str(uuid4()))
            #
            temp = datetime.datetime.now()
            streamer.change_frame(image)
            # save_gif(new_frames)
            # print("Gif printed")
            # save_images(fr1, fr2, str(uuid4()))

            # i += 1
            # imageio.imsave(im, flash)
            # image = cv2.imread(im)
            # orig = image.copy()
            # get image in rectangle

            #
            # # pre-process the image for classification
            #######image = cv.resize(image, (128, 128))
            #######image = image.astype("float32") / 255.0
            #######image = np.array(image)
            #######image = np.expand_dims(image, axis=0)
            ########
            ######## # classify the input image
            ######## (uno, due, tre, quattro) = model.predict(image)[0]
            ########
            ######## # Test the model on random input data.
            #######input_shape = input_details[0]['shape']
            ########
            #######interpreter.set_tensor(input_details[0]['index'], image)
            ########
            ######## class_names = ["1", "2", "3", "4"]
            #######interpreter.invoke()
            ########
            ######## # The function `get_tensor()` returns a copy of the tensor data.
            ######## # Use `tensor()` in order to get a pointer to the tensor.
            #######output_data = interpreter.get_tensor(output_details[0]['index'])
            #######output_data = output_data[0]
            #######print(output_data)
            #######for i in range(len(output_data)):
            #######    print(f"{label_dict[i]}: {output_data[i]}")
            #######argmax = np.argmax(output_data)
            #######print(f"Predicted class: {label_dict[argmax]}, {int(output_data[argmax]*100)}%")

            #im = datetime.datetime.now().strftime('%Y%m-%d%H-%M%S-') + str(uuid4())
            #temp = datetime.datetime.now()
            #im_save_thread_pool(fr1[:30], im)
            #print("[INFO] Images saved in {:.3f} seconds".format((datetime.datetime.now() - temp).total_seconds()))
            while datetime.datetime.now() - temp < datetime.timedelta(seconds=4):
                # print(f"[INFO] Elapsed from stop: {(datetime.datetime.now() - temp).total_seconds()} seconds")
                ret, frame = capture.read()
                fgMask = backSub.apply(frame)
                cv.waitKey(1) & 0xff
            print("[STATUS] Session finished, Ready again...")
            #
            # # build the label
            # uno, due, tre, quattro = output_data
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
