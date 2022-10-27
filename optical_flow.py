import datetime
from helpers import *
import numpy as np
import cv2 as cv


def follow(frames, old_frame, first_cnt):
    start = datetime.datetime.now()

    # params for ShiTomasi corner detection
    feature_params = dict(maxCorners=100,
                          qualityLevel=0.3,
                          minDistance=4,
                          blockSize=4)

    # Parameters for lucas kanade optical flow
    lk_params = dict(winSize=(40, 40),
                     maxLevel=2,
                     criteria=(cv.TERM_CRITERIA_EPS | cv.TERM_CRITERIA_COUNT, 10, 0.03))

    # Create some random colors
    color = np.random.randint(0, 255, (100, 3))

    old_gray = cv.cvtColor(old_frame, cv.COLOR_BGR2GRAY)
    p0 = cv.goodFeaturesToTrack(old_gray, mask=get_mask(old_frame, first_cnt), **feature_params)

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
