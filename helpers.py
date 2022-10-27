import os
from uuid import uuid4

import cv2 as cv
import imageio
import numpy as np


# function to join two numpy arrays
from matplotlib import pyplot as plt
from scipy.signal import find_peaks


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


# function to rescale frame using percentage
def rescale_frame(old_width, old_height, percent=50):
    scale_percent = percent  # percent of original size
    width = int(old_width * scale_percent / 100)
    height = int(old_height * scale_percent / 100)
    dim = (width, height)
    # resize image
    # return cv.resize(frame, dim, interpolation=cv.INTER_AREA)
    return dim

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