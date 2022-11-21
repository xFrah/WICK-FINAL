import datetime
import cv2 as cv
import time


def setup_camera():
    cap = cv.VideoCapture(0)
    print("[INFO] Configuring camera:", end=" ", flush=True)

    succ = {}
    succ[cv.CAP_PROP_FRAME_WIDTH] = cap.set(cv.CAP_PROP_FRAME_WIDTH, 640)
    succ[cv.CAP_PROP_FRAME_HEIGHT] = cap.set(cv.CAP_PROP_FRAME_HEIGHT, 480)
    succ[cv.CAP_PROP_FPS] = cap.set(cv.CAP_PROP_FPS, 120)
    time.sleep(2)
    succ[cv.CAP_PROP_FOURCC] = cap.set(cv.CAP_PROP_FOURCC, cv.VideoWriter_fourcc('M', 'J', 'P', 'G'))
    # time.sleep(2)
    succ[cv.CAP_PROP_AUTO_EXPOSURE] = cap.set(cv.CAP_PROP_AUTO_EXPOSURE, 1)
    time.sleep(2)
    succ[cv.CAP_PROP_EXPOSURE] = cap.set(cv.CAP_PROP_EXPOSURE, 12)
    succ[cv.CAP_PROP_GAIN] = cap.set(cv.CAP_PROP_GAIN, 100)
    # succ[cv.CAP_PROP_BUFFERSIZE] = cap.set(cv.CAP_PROP_BUFFERSIZE, 1)

    # print(str(tuple([cap.get(item) if value else "FAILED" for item, value in succ.items()])))

    c = 0
    start = datetime.datetime.now()
    while c < 100:
        _, frame = cap.read()
        c += 1
    print(f"Done, {str(tuple([round(100 / (datetime.datetime.now() - start).total_seconds(), 2)] + [round(cap.get(item), 2) if value else 'FAILED' for item, value in succ.items()]))}")
    return cap

