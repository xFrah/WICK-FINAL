#!/usr/bin/env python3

import time

import numpy as np
import vl53l5cx_ctypes as vl53l5cx
import numpy
from PIL import Image
from matplotlib import cm, pyplot as plt
import threading

from matplotlib.ticker import LinearLocator, FormatStrFormatter

import streamer

COLOR_MAP = "plasma"
INVERSE = False

threading.Thread(target=streamer.start_thread, args=('0.0.0.0', "5000")).start()


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


pal = get_palette(COLOR_MAP)

print("Uploading firmware, please wait...")
vl53 = vl53l5cx.VL53L5CX()
print("Done!")
vl53.set_resolution(4 * 4)

# This is a visual demo, so prefer speed over accuracy
vl53.set_ranging_frequency_hz(60)
vl53.set_integration_time_ms(5)
vl53.start_ranging()

mode = "4x4"
if mode == "4x4":
    vl53.set_resolution(4 * 4)
elif mode == "8x8":
    vl53.set_resolution(8 * 8)


# function to turn numpy image to x, y, z pixels
def get_xyz(data):
    x = numpy.arange(0, data.shape[0])
    y = numpy.arange(0, data.shape[1])
    x, y = numpy.meshgrid(x, y)
    z = data
    return x, y, z


def plot_heatmap(data, title):
    # Creating figure
    fig = plt.figure(figsize=(14, 9))
    ax = plt.axes(projection='3d')
    x, y, z = get_xyz(data)
    ax.plot_surface(x, y, z, rstride=1, cstride=1)
    # Creating plot
    #ax.plot_surface(x, y, z)
    # get plt as image and turn it to a numpy array
    fig.canvas.draw()
    img = numpy.fromstring(fig.canvas.tostring_rgb(), dtype=numpy.uint8, sep='')
    img = img.reshape(fig.canvas.get_width_height()[::-1] + (3,))
    plt.close(fig)
    return img
    # plt.show()


while True:
    if vl53.data_ready():
        data = vl53.get_data()
        if mode == "4x4":
            temp = numpy.array([data.distance_mm[0][:16]])
            print(temp)
            temp = temp.reshape((4, 4))
        else:
            temp = numpy.array(data.distance_mm).reshape((8, 8))
        print(temp)
        arr = numpy.flipud(temp).astype('float64')

        # Scale view relative to the furthest distance
        # distance = arr.max()

        # Scale view to a fixed distance
        distance = 512

        # Scale and clip the result to 0-255
        arr *= (255.0 / distance)
        arr = numpy.clip(arr, 0, 255)

        # Invert the array : 0 - 255 becomes 255 - 0
        if INVERSE:
            arr *= -1
            arr += 255.0

        # Force to int
        arr = arr.astype('uint8')

        # Convert to a palette type image
        img = Image.frombytes("P", (8, 8) if mode != "4x4" else (4, 4), arr)
        img.putpalette(pal)
        img = img.convert("RGB")
        img = img.resize((240, 240), resample=Image.NEAREST)
        img = numpy.array(img)

        streamer.change_frame(img)

        # check if at least 3 items in the temp matrix are less than 200
        while (temp < 200).sum() >= 3:
            time.sleep(0.003)
            data = vl53.get_data()
            # get values of pixels that are less than 200 with np.where
            indices = np.where((img <= 200).all(axis=2))
            # get the x and y coordinates of the pixels that are less than 200
            values = []
            for i in range(len(indices[0])):
                x = indices[0][i]
                y = indices[1][i]
                # get the value of the pixel at the x and y coordinates
                values.append(img[x, y])
            # compute average of the values
            average = sum(values) / len(values)
            print(f"Object at {average} mm")


    time.sleep(0.01)  # Avoid polling *too* fast
