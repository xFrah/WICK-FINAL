import datetime
import os
from uuid import uuid4

import numpy as np
import cv2 as cv
import imageio


# function that shifts a rectangle if it is on the edge of the image
def shift_rect(rect, frame):
    x, y, w, h = rect
    if x == 0:
        x += 10
    if y == 0:
        y += 10
    if x + w == frame.shape[1]:
        x -= 10
    if y + h == frame.shape[0]:
        y -= 10
    return x, y, w, h


# function that makes a rectangle bigger
def make_rect_bigger(rect, frame):
    x, y, w, h = rect
    if x > 0:
        x -= 10
    if y > 0:
        y -= 10
    if x + w < frame.shape[1]:
        w += 10
    if y + h < frame.shape[0]:
        h += 10
    return x, y, w, h


# get image inside bounding rectangle
def get_sub_image(frame, x, y, w, h):
    return frame[y:y + h, x:x + w]


# find the bounding rectangle of set of points
def get_bounding_rect(points):
    x, y, w, h = cv.boundingRect(points)
    return x, y, w, h


# function to erode frame
def erode(frame):
    kernel = np.ones((5, 5), np.uint8)
    return cv.erode(frame, kernel, iterations=1)


# function to count white pixels in frame
def count_white_pixels(frame):
    return np.sum(frame == 255)


# function that gets a mask of all the white pixels in the image
def get_white_mask(frame):
    mask = np.zeros(frame.shape[:2], np.uint8)
    mask[frame == 255] = 255
    return mask


# function that returns a mask of the image using a binary and operation
def get_mask(frame, first_cnt):
    mask = np.zeros(frame.shape[:2], np.uint8)
    cv.drawContours(mask, [first_cnt], 0, 255, -1)
    return mask


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


def follow(frames, old_frame, first_cnt):
    start = datetime.datetime.now()

    # params for ShiTomasi corner detection
    feature_params = dict(maxCorners=100,
                          qualityLevel=0.2,
                          minDistance=7,
                          blockSize=7)

    # Parameters for lucas kanade optical flow
    lk_params = dict(winSize=(15, 15),
                     maxLevel=2,
                     criteria=(cv.TERM_CRITERIA_EPS | cv.TERM_CRITERIA_COUNT, 10, 0.03))

    # Create some random colors
    color = np.random.randint(0, 255, (100, 3))

    old_gray = cv.cvtColor(old_frame, cv.COLOR_BGR2GRAY)
    p0 = cv.goodFeaturesToTrack(old_gray, mask=erode(get_mask(old_frame, first_cnt)), **feature_params)

    # Create a mask image for drawing purposes
    mask = np.zeros_like(old_frame)
    new_frames = []
    for frame in frames:

        frame_gray = cv.cvtColor(frame, cv.COLOR_BGR2GRAY)

        # calculate optical flow
        p1, st, err = cv.calcOpticalFlowPyrLK(old_gray, frame_gray, p0, None, **lk_params)

        # Select good points
        if p1 is not None:
            good_new = p1[st == 1]
            good_old = p0[st == 1]

        # draw the tracks
        for i, (new, old) in enumerate(zip(good_new, good_old)):
            a, b = new.ravel()
            c, d = old.ravel()
            mask = cv.line(mask, (int(a), int(b)), (int(c), int(d)), color[i].tolist(), 2)
            frame = cv.circle(frame, (int(a), int(b)), 5, color[i].tolist(), -1)
        new_frames.append(cv.add(frame, mask))

        # Now update the previous frame and previous points
        old_gray = frame_gray.copy()
        p0 = good_new.reshape(-1, 1, 2)
    print(f"Optical flow processed {len(frames)} frames in {(datetime.datetime.now() - start).seconds}")
    return new_frames, get_sub_image(frame, *shift_rect(make_rect_bigger(get_bounding_rect(good_new), frame), frame))
