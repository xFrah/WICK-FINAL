import numpy as np
from pycoral.utils import edgetpu
from pycoral.adapters import common
from pycoral.adapters import classify
import cv2 as cv

from data_utils import config_and_data


def setup_edgetpu():
    print("[INFO] Configuring EdgeTPU:", end=" ", flush=True)
    interpreter = edgetpu.make_interpreter("/home/fra/Desktop/WICK-FINAL/model_quant_edgetpu.tflite")
    interpreter.allocate_tensors()
    print("Done.")
    return interpreter


def inference(image, interpreter):
    image = cv.resize(image, (128, 128))
    image = cv.cvtColor(image, cv.COLOR_BGR2RGB)
    image = image.astype("float32") / 255.0
    image = np.array(image)
    image = np.expand_dims(image, axis=0)

    common.set_input(interpreter, image)
    interpreter.invoke()
    output = classify.get_classes(interpreter, top_k=1)
    return config_and_data["label_dict"][output[0][0]], output[0][1]
