# create list of 16 random floats
import datetime

import numpy as np


def absolute_diff(vector, base_vector):
    return np.abs(np.array(vector) - np.array(base_vector))


def absolute_diff_2(vector, base_vector):
    for i, y in zip(vector, base_vector):
        if abs(i - y) > 10:
            return True
    return False


def microseconds_to_seconds(microseconds):
    return microseconds / 1000000


vector = [1, 1, 1, 2, 2, 2, 2, 2, 3, 20, 3, 3, 4, 10, 4, 4]
base_vector = [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1]

#print(absolute_diff(vector, base_vector))
buffer = []
start = datetime.datetime.now()
while True:
    random_floats = list(np.random.rand(16))
    buffer.append(absolute_diff(random_floats, vector))
    if len(buffer) == 10000:
        print(f"FPS: {10000 / (datetime.datetime.now() - start).total_seconds():.2f}")
        buffer.clear()
        start = datetime.datetime.now()
