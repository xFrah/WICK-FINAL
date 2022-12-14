import time

import numpy
import vl53l5cx_ctypes as vl53l5cx
from matplotlib import cm

from helpers import flip_matrix
from data_utils import config_and_data
from PIL import Image


def tof_setup():
    print("[INFO] Configuring ToF:", end=" ", flush=True)
    vl53 = vl53l5cx.VL53L5CX()
    vl53.set_resolution(4 * 4)
    vl53.set_ranging_frequency_hz(60)
    vl53.set_integration_time_ms(5)
    vl53.start_ranging()
    print("Done.")
    return vl53


def absolute_diff(vector, base_vector, diff_threshold=2):
    """
    If the absolute difference between any two elements in the two vectors is greater than diff_threshold(default=2), return True, otherwise return False

    :param vector: the vector we're comparing to the base vector
    :param base_vector: The vector that we are comparing the other vectors to
    :param diff_threshold: The threshold for the absolute difference in centimeters
    :return: True or False
    """
    for i, y in zip(vector, base_vector):
        if abs(i - y) > diff_threshold and (i != 0 and y != 0):
            return True
    return False


def get_trash_level(vl53):
    """
    It takes the data from the VL53L0X sensor and returns the maximum distance measured and the level of trash, as percentage.

    :param vl53: the VL53L0X object
    :return: level_in_mm, level_in_percentage
    """
    while True:
        if vl53.data_ready():
            data = [e for e in vl53.get_data().distance_mm[0][:16] if e > 0]
            max_lev = max(data)
            percentage = int((1 - (max_lev - config_and_data["bin_threshold"]) / (config_and_data["bin_height"] - config_and_data["bin_threshold"])) * 100)
            return max_lev, percentage
        time.sleep(0.003)


def render_tof(tof_frame):
    temp = numpy.array(tof_frame).reshape((4, 4))
    temp = [list(reversed(col)) for col in zip(*temp)]
    temp = flip_matrix(temp)
    arr = numpy.flipud(temp).astype('float64')

    # Scale view relative to the furthest distance
    # distance = arr.max()

    # Scale view to a fixed distance
    distance = 512

    # Scale and clip the result to 0-255
    arr *= (255.0 / distance)
    arr = numpy.clip(arr, 0, 255)

    # Force to int
    arr = arr.astype('uint8')

    # Convert to a palette type image
    img = Image.frombytes("P", (4, 4), arr)
    img.putpalette(pal)
    img = img.convert("RGB")
    img = img.resize((240, 240), resample=Image.NEAREST)
    img = numpy.array(img)
    return img


def get_palette(name):
    cmap = cm.get_cmap(name, 256)

    try:
        colors = cmap.colors
    except AttributeError:
        colors = numpy.array([cmap(i) for i in range(256)], dtype=float)

    arr = numpy.array(colors * 255).astype('uint8')
    arr = arr.reshape((16, 16, 4))
    arr = arr[:, :, 0:3]
    return arr.tobytes()


pal = get_palette("plasma")
