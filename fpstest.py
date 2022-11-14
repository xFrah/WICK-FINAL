import time
import subprocess
import datetime
from wecam import WebcamVideoStream
import streamer
import threading
import cv2 as cv

##subprocess.call(['v4l2-ctl -d /dev/video1 --set-fmt-video=width=640,height=480,pixelformat=MJPG'], shell=True)
##time.sleep(1)
##print("Set video format successfully?")
##
##cam_props = {'gain': 0, 'exposure_auto': 1, 'exposure_absolute': 25}
##for key in cam_props:
##    subprocess.call(['v4l2-ctl -d /dev/video1 -c {}={}'.format(key, str(cam_props[key]))],
##                    shell=True)
##    time.sleep(1)
##    print(f"Set {key} to {cam_props[key]}")
threading.Thread(target=streamer.start_thread, args=('0.0.0.0', "5000")).start()

cap = cv.VideoCapture(1)
print(cap.set(cv.CAP_PROP_FRAME_WIDTH, 640))
print(cap.set(cv.CAP_PROP_FRAME_HEIGHT, 480))
print(cap.set(cv.CAP_PROP_FPS, 120))
# print(capture.set(cv.CAP_PROP_BUFFERSIZE, 1))
print(cap.set(cv.CAP_PROP_FOURCC, cv.VideoWriter_fourcc('M', 'J', 'P', 'G')))
capture = WebcamVideoStream(src=cap).start()

# width, height = rescale_frame(640, 480, 50)

##print(capture.stream.get(cv.CAP_PROP_FPS))
# #print(capture.set(cv.CAP_PROP_AUTO_EXPOSURE, 0.25))
# print(capture.set(cv.CAP_PROP_EXPOSURE, -11))
# print(capture.set(cv.CAP_PROP_GAIN, 100))
time.sleep(2)


# function that checks if two frames are pixel per pixel identical
def check_identical(frame1, frame2):
    if frame1.shape == frame2.shape:
        difference = cv.subtract(frame1, frame2)
        b, g, r = cv.split(difference)
        if cv.countNonZero(b) == 0 and cv.countNonZero(g) == 0 and cv.countNonZero(r) == 0:
            return True
        else:
            return False
    else:
        return False


a = datetime.datetime.now()
fps_c = 0
prev = capture.read()
prev[0][0] = [4, 34, 68]
while True:
    # Capture frame-by-frame
    frame = capture.read()
    streamer.change_frame(frame)
    if check_identical(frame, prev):
        prev = frame
        continue
    prev = frame
    fps_c += 1
    if fps_c == 100:
        print(f"[INFO] FPS: {int(fps_c / (datetime.datetime.now() - a).total_seconds())}")
        a = datetime.datetime.now()
        fps_c = 0
