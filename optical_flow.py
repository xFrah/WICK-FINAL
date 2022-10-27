import datetime
import os
from uuid import uuid4

import numpy as np
import cv2 as cv
import imageio


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


def follow(old_frame, cap, first_cnt, mask, backSub):
    area_buffer = []
    start = datetime.datetime.now()
    session_uuid = start.strftime('%Y%m-%d%H-%M%S-') + str(uuid4())
    session_frames = [old_frame]
    sub_frames = [mask]

    # params for ShiTomasi corner detection
    feature_params = dict(maxCorners=100,
                          qualityLevel=0.3,
                          minDistance=7,
                          blockSize=7)

    # Parameters for lucas kanade optical flow
    lk_params = dict(winSize=(15, 15),
                     maxLevel=2,
                     criteria=(cv.TERM_CRITERIA_EPS | cv.TERM_CRITERIA_COUNT, 10, 0.03))

    # Create some random colors
    color = np.random.randint(0, 255, (100, 3))

    # Take first frame and find corners in it
    # ret, old_frame = cap.read()
    old_gray = cv.cvtColor(old_frame, cv.COLOR_BGR2GRAY)
    p0 = cv.goodFeaturesToTrack(old_gray, mask=get_mask(old_frame, first_cnt), **feature_params)
    if p0 is None or len(p0) == 0:
        try:
            print(F"Motion finished, FPS: {len(session_frames) / (datetime.datetime.now() - start).seconds}")
            # save_images(session_frames, sub_frames, session_uuid)
        except ZeroDivisionError:
            print('Session discarded')
        return area_buffer

    # Create a mask image for drawing purposes
    mask = np.zeros_like(old_frame)

    while 1:
        ret, frame = cap.read()
        fgMask = backSub.apply(frame)
        fgMask = get_white_mask(fgMask)
        session_frames.append(frame)
        sub_frames.append(fgMask)
        if not ret:
            print('No frames grabbed!')
            break

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
        img = cv.add(frame, mask)

        cv.imshow('Frame', img)
        cv.imshow('FG Mask', fgMask)
        k = cv.waitKey(30) & 0xff
        if k == 27:
            break

        # Now update the previous frame and previous points
        old_gray = frame_gray.copy()
        p0 = good_new.reshape(-1, 1, 2)

        conts, hierarchy = cv.findContours(fgMask, cv.RETR_EXTERNAL, cv.CHAIN_APPROX_SIMPLE)
        max_contour = max(conts, key=cv.contourArea)
        area_buffer.append(count_white_pixels(fgMask))
        if cv.contourArea(max_contour) < 200:
            try:
                print(F"Motion finished, FPS: {len(session_frames) / (datetime.datetime.now() - start).seconds}")
                #save_images(session_frames, sub_frames, session_uuid)
            except ZeroDivisionError:
                print('Session discarded')
            return area_buffer
