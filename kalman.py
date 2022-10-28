#####################################################################

# Example : kalman filtering based cam shift object track processing
# from a video file specified on the command line (e.g. python FILE.py
# video_file) or from an attached web camera

# N.B. u se mouse to select region

# Author : Toby Breckon, toby.breckon@durham.ac.uk

# Copyright (c) 2016 Toby Breckon
#                    Durham University, UK
# License : LGPL - http://www.gnu.org/licenses/lgpl.html

# based in part on code from: Learning OpenCV 3 Computer Vision with Python
# Chapter 8 code samples, Minichino / Howse, Packt Publishing.
# and also code from:
# https://docs.opencv.org/3.3.1/dc/df6/tutorial_py_histogram_backprojection.html

#####################################################################

import cv2
import argparse
import sys
import math
import numpy as np

#####################################################################

keep_processing = True
selection_in_progress = False  # support interactive region selection
fullscreen = False  # run in fullscreen mode


# return centre of a set of points representing a rectangle


def center(points):
    x = np.float32(
        (points[0][0] +
         points[1][0] +
         points[2][0] +
         points[3][0]) /
        4.0)
    y = np.float32(
        (points[0][1] +
         points[1][1] +
         points[2][1] +
         points[3][1]) /
        4.0)
    return np.array([np.float32(x), np.float32(y)], np.float32)


def nothing(x):
    pass


def variance_of_laplacian(image):
    # compute the Laplacian of the image and then return the focus
    # measure, which is simply the variance of the Laplacian
    return cv2.Laplacian(image, cv2.CV_64F).var()


def kalman_tracking(fr1, x1, x2, y1, y2):
    window_name = "Kalman Object Tracking"  # window name
    window_name2 = "Hue histogram back projection"  # window name
    window_nameSelection = "initial selected region"

    measurement = np.array((2, 1), np.float32)
    prediction = np.zeros((2, 1), np.float32)

    print("\nObservation in image: BLUE")
    print("Prediction from Kalman: GREEN\n")

    # if command line arguments are provided try to read video_name
    # otherwise default to capture from attached H/W camera

    # create window by name (note flags for resizable or not)

    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    cv2.namedWindow(window_name2, cv2.WINDOW_NORMAL)
    cv2.namedWindow(window_nameSelection, cv2.WINDOW_NORMAL)

    # set sliders for HSV selection thresholds

    s_lower = 60
    cv2.createTrackbar("s lower", window_name2, s_lower, 255, nothing)
    s_upper = 255
    cv2.createTrackbar("s upper", window_name2, s_upper, 255, nothing)
    v_lower = 32
    cv2.createTrackbar("v lower", window_name2, v_lower, 255, nothing)
    v_upper = 255
    cv2.createTrackbar("v upper", window_name2, v_upper, 255, nothing)

    # Setup the termination criteria for search, either 10 iteration or
    # move by at least 1 pixel pos. difference
    term_crit = (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 10, 1)

    # get parameters from track bars

    s_lower = cv2.getTrackbarPos("s lower", window_name2)
    s_upper = cv2.getTrackbarPos("s upper", window_name2)
    v_lower = cv2.getTrackbarPos("v lower", window_name2)
    v_upper = cv2.getTrackbarPos("v upper", window_name2)

    # select region using the mouse and display it

    # y1 = boxes[0][1]
    # y2 = boxes[1][1]
    # x1 = boxes[0][0]
    # x2 = boxes[1][0]

    crop = fr1[0][y1:y2, x1:x2].copy()

    # convert region to HSV

    hsv_crop = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)

    # select all Hue (0-> 180) and Sat. values but eliminate values
    # with very low saturation or value (due to lack of useful
    # colour information)

    mask = cv2.inRange(
        hsv_crop, np.array(
            (0., float(s_lower), float(v_lower))), np.array(
            (180., float(s_upper), float(v_upper))))

    # construct a histogram of hue and saturation values and
    # normalize it

    crop_hist = cv2.calcHist(
        [hsv_crop], [
            0, 1], mask, [
            180, 255], [
            0, 180, 0, 255])
    cv2.normalize(crop_hist, crop_hist, 0, 255, cv2.NORM_MINMAX)

    # set intial position of object

    track_window = (
        x1,
        y1,
        x2 - x1,
        y2 - y1)

    cv2.imshow(window_nameSelection, crop)

    for frame in fr1:
        # start a timer (to see how long processing and display takes)

        start_t = cv2.getTickCount()

        # convert incoming image to HSV

        img_hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

        # back projection of histogram based on Hue and Saturation only

        img_bproject = cv2.calcBackProject(
            [img_hsv], [
                0, 1], crop_hist, [
                0, 180, 0, 255], 1)
        cv2.imshow(window_name2, img_bproject)

        # apply camshift to predict new location (observation)
        # basic HSV histogram comparision with adaptive window size
        # see :
        # http://docs.opencv.org/3.1.0/db/df8/tutorial_py_meanshift.html
        ret, track_window = cv2.CamShift(
            img_bproject, track_window, term_crit)

        # draw observation on image - in BLUE
        x, y, w, h = track_window
        frame = cv2.rectangle(
            frame, (x, y), (x + w, y + h), (255, 0, 0), 2)

        # extract centre of this observation as points

        # pts = cv2.boxPoints(ret)
        # pts = np.int0(pts)
        # (cx, cy), radius = cv2.minEnclosingCircle(pts)

        # # use to correct kalman filter
        #
        # kalman.correct(center(pts))
        #
        # # get new kalman filter prediction
        #
        # prediction = kalman.predict()
        #
        # # draw predicton on image - in GREEN
        #
        # frame = cv2.rectangle(frame,
        #                       (int(prediction[0] - (0.5 * w)),
        #                        int(prediction[1] - (0.5 * h))),
        #                       (int(prediction[0] + (0.5 * w)),
        #                        int(prediction[1] + (0.5 * h))),
        #                       (0,
        #                        255,
        #                        0),
        #                       2)
        #
        # display image

        cv2.imshow(window_name, frame)
        cv2.setWindowProperty(
            window_name,
            cv2.WND_PROP_FULLSCREEN,
            cv2.WINDOW_FULLSCREEN & fullscreen)

        # stop the timer and convert to ms. (to see how long processing and
        # display takes)

        stop_t = ((cv2.getTickCount() - start_t) /
                  cv2.getTickFrequency()) * 1000

        # start the event loop - essential

        # cv2.waitKey() is a keyboard binding function (argument is the time in
        # milliseconds). It waits for specified milliseconds for any keyboard
        # event. If you press any key in that time, the program continues.
        # If 0 is passed, it waits indefinitely for a key stroke.
        # (bitwise and with 0xFF to extract least significant byte of
        # multi-byte response)

        # wait 40ms or less depending on processing time taken (i.e. 1000ms /
        # 25 fps = 40 ms)

        cv2.waitKey(max(2, 40 - int(math.ceil(stop_t)))) & 0xFF

    # close all windows

    return track_window
