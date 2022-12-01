# create list of 16 random floats
import datetime

import numpy as np


def absolute_diff(vector, base_vector):
    return np.abs(vector - base_vector)


def microseconds_to_seconds(microseconds):
    return microseconds / 1000000


base_vector = list(np.random.rand(16))
buffer = []
start = datetime.datetime.now()
while True:
    random_floats = list(np.random.rand(16))
    buffer.append(random_floats)
    if len(buffer) == 10000:
        print(f"FPS: {10000 / (datetime.datetime.now() - start).total_seconds():.2f}")
        buffer.clear()
        start = datetime.datetime.now()
