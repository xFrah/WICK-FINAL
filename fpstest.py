import time
import subprocess
import datetime
import cv2 as cv

subprocess.call(['v4l2-ctl -d /dev/video1 --set-fmt-video=width=640,height=480,pixelformat=MJPG'], shell=True)
time.sleep(1)
print("Set video format successfully?")

cam_props = {'gain': 0, 'exposure_auto': 1, 'exposure_absolute': 25}
for key in cam_props:
    subprocess.call(['v4l2-ctl -d /dev/video1 -c {}={}'.format(key, str(cam_props[key]))],
                    shell=True)
    time.sleep(1)
    print(f"Set {key} to {cam_props[key]}")
if 1:
    backSub = cv.createBackgroundSubtractorMOG2(detectShadows=True, history=150, varThreshold=200)
else:
    backSub = cv.createBackgroundSubtractorKNN(detectShadows=True, history=150, varThreshold=200)
capture = cv.VideoCapture(1)
capture.set(cv.CAP_PROP_FOURCC, cv.VideoWriter_fourcc('M', 'J', 'P', 'G'))
# width, height = rescale_frame(640, 480, 50)
# print(capture.set(cv.CAP_PROP_FRAME_WIDTH, 640))
# print(capture.set(cv.CAP_PROP_FRAME_HEIGHT, 480))
print(capture.set(cv.CAP_PROP_FPS, 120))
print(capture.set(cv.CAP_PROP_BUFFERSIZE, 1))
print(capture.get(cv.CAP_PROP_FPS))
# #print(capture.set(cv.CAP_PROP_AUTO_EXPOSURE, 0.25))
# print(capture.set(cv.CAP_PROP_EXPOSURE, -11))
# print(capture.set(cv.CAP_PROP_GAIN, 100))
time.sleep(2)

a = datetime.datetime.now()
fps_c = 0
while True:
    # Capture frame-by-frame
    ret, frame = capture.read()
    fps_c += 1
    if fps_c == 100:
        print(f"[INFO] FPS: {int(fps_c / (datetime.datetime.now() - a).total_seconds())}")
        a = datetime.datetime.now()
        fps_c = 0