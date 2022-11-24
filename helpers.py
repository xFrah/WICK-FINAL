import datetime
import os
import re
import signal
import uuid
from uuid import uuid4

import cv2 as cv
import numpy
import numpy as np
from PIL import Image
import imageio

# function to join two numpy arrays
from matplotlib import pyplot as plt, cm
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
def plot_y(y, first_peak):
    plt.plot(y)
    # plot vertical line at x
    plt.axvline(x=first_peak, color='r')
    # for bk in bkps:
    #    plt.axvline(x=bk, color='g')
    # for bk in minimas:
    #    plt.axvline(x=bk, color='b')
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


def get_blobl_with_closing(frame):
    inter = cv.morphologyEx(frame, cv.MORPH_CLOSE, cv.getStructuringElement(cv.MORPH_ELLIPSE, (5, 5)))
    cnts, _ = cv.findContours(inter, cv.RETR_EXTERNAL, cv.CHAIN_APPROX_NONE)
    cnt = max(cnts, key=cv.contourArea)
    out = np.zeros(frame.shape, np.uint8)
    cv.drawContours(out, [cnt], -1, 255, cv.FILLED)
    out = cv.bitwise_and(frame, out)
    return out


def get_white_mask(frame):
    mask = np.zeros(frame.shape[:2], np.uint8)
    mask[frame != 0] = 255
    return mask


# function to perform morphological top hat
def morphological_top_hat(frame):
    kernel = np.ones((5, 5), np.uint8)
    return cv.morphologyEx(frame, cv.MORPH_TOPHAT, kernel)


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


def kill():
    os.kill(os.getpid(), signal.SIGTERM)


# function to flip matrix horizontally
def flip_matrix(matrix):
    return numpy.flip(matrix, 1)


def get_diff(frame, background):
    gray = cv.cvtColor(frame, cv.COLOR_BGR2GRAY)
    gray = cv.GaussianBlur(gray, (21, 21), 0)
    background = cv.cvtColor(background, cv.COLOR_BGR2GRAY)
    background = cv.GaussianBlur(background, (21, 21), 0)
    frameDelta = cv.absdiff(background, gray)
    thresh = cv.threshold(frameDelta, 25, 255, cv.THRESH_BINARY)[1]
    thresh = cv.dilate(thresh, None, iterations=2)
    try:
        conts, hierarchy = cv.findContours(thresh, cv.RETR_EXTERNAL, cv.CHAIN_APPROX_SIMPLE)
    except:
        print("[WARN] No contours found")
    try:
        x, y, w, h = cv.boundingRect(
            np.concatenate(np.array([cont for cont in conts if cv.contourArea(cont) > 20])))
        return (x, y, w, h), thresh
    except ValueError:
        print("[WARN] No contours found")
    return None, thresh


def get_mac_address():
    mac_address = ':'.join(re.findall('..', '%012x' % uuid.getnode()))
    return mac_address


# function to save list of images in new folder in current working directory linux
def save_images_linux(images, folder_name):
    path = os.getcwd() + "/" + folder_name
    if not os.path.exists(path):
        os.mkdir(path)
    uuid = datetime.datetime.now().strftime('%Y%m-%d%H-%M%S-') + str(uuid4())
    print(f"Saving images to {path}/{uuid}-*.png")
    for i, image in enumerate(images):
        cv.imwrite(f"{path}/{uuid}-{i}.png", np.array(image))
