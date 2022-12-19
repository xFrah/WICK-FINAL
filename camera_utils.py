import datetime
import threading

import cv2 as cv
import time

import numpy
from psutil import virtual_memory
from watchdog import ping


class Camera:
    def __init__(self, flash, no_camera_thread=False, fast_mode=False):
        self.broken = False
        self.do_i_shoot = False
        self.flash = flash
        self.camera_buffer: dict[datetime.datetime, tuple[numpy.array, int]] = {}
        self.camera_lock = threading.Lock()
        self.cap = cv.VideoCapture(0)
        print("[INFO] Configuring camera:", end=" ", flush=True)

        succ = self.apply_configuration(fast_mode)

        c = 0
        start = datetime.datetime.now()
        while c < 100:
            _, frame = self.cap.read()
            c += 1
        print(f"Done, {str(tuple([round(100 / (datetime.datetime.now() - start).total_seconds(), 2)] + [round(self.cap.get(item), 2) if value else 'FAILED' for item, value in succ.items()]))}")
        if not no_camera_thread:
            threading.Thread(target=self.camera_thread).start()

    def apply_configuration(self, fast_mode):
        succ = dict()
        if fast_mode:
            succ[cv.CAP_PROP_FRAME_WIDTH] = self.cap.set(cv.CAP_PROP_FRAME_WIDTH, 640)
            succ[cv.CAP_PROP_FRAME_HEIGHT] = self.cap.set(cv.CAP_PROP_FRAME_HEIGHT, 480)
            succ[cv.CAP_PROP_FPS] = self.cap.set(cv.CAP_PROP_FPS, 120)
            time.sleep(2)
            succ[cv.CAP_PROP_FOURCC] = self.cap.set(cv.CAP_PROP_FOURCC, cv.VideoWriter_fourcc('M', 'J', 'P', 'G'))
            # time.sleep(2)
            succ[cv.CAP_PROP_AUTO_EXPOSURE] = self.cap.set(cv.CAP_PROP_AUTO_EXPOSURE, 1)
            time.sleep(2)
            succ[cv.CAP_PROP_AUTO_WB] = self.cap.set(cv.CAP_PROP_AUTO_WB, 0)
            succ[cv.CAP_PROP_EXPOSURE] = self.cap.set(cv.CAP_PROP_EXPOSURE, 12)
            succ[cv.CAP_PROP_GAIN] = self.cap.set(cv.CAP_PROP_GAIN, 100)
            # succ[cv.CAP_PROP_BUFFERSIZE] = self.cap.set(cv.CAP_PROP_BUFFERSIZE, 1) # TODO TEST IF THIS WORKS PLEASE

            return succ
        else:
            succ[cv.CAP_PROP_AUTO_WB] = self.cap.set(cv.CAP_PROP_AUTO_WB, 0)
            succ[cv.CAP_PROP_EXPOSURE] = self.cap.set(cv.CAP_PROP_EXPOSURE, 0)
            succ[cv.CAP_PROP_GAIN] = self.cap.set(cv.CAP_PROP_GAIN, 0)
            return succ
        # self.cap.set(cv.CAP_PROP_BUFFERSIZE, 1)

    def shoot(self, timer=0.0, return_to_black=True):
        self.flash.fill((255, 255, 255))
        self.do_i_shoot = True
        if timer > 0:
            time.sleep(timer)
            return self.stop_shooting(turn_black=return_to_black)

    def stop_shooting(self, turn_black=True):
        self.do_i_shoot = False
        if turn_black:
            self.flash.fill((0, 0, 0))
        return self.grab_buffer()

    def grab_buffer(self):
        while len(self.camera_buffer) == 0:
            if self.broken:
                self.broken = False
                return
        with self.camera_lock:
            copy = self.camera_buffer.copy()
            self.camera_buffer = {}
        return copy

    def grab_background(self, return_to_black=True):
        self.flash.fill((255, 255, 255))
        buffer = self.shoot(timer=0.125, return_to_black=return_to_black)
        if buffer:
            print(f"[INFO] Background frame count: {len(buffer)}")
            return max(buffer.values(), key=lambda d: d[1])[0]
        else:
            print("[WARN] No background frames")

    def snap(self):
        return self.cap.read()[0]

    def camera_thread(self):
        thread = threading.currentThread()
        thread.setName("Camera")
        while True:
            _, frame = self.cap.read()
            if frame is not None:
                ping(thread)
            if self.do_i_shoot:
                # temp = {datetime.datetime.now(): (frame, 0)}
                temp = {}
                self.broken = False
                while self.do_i_shoot:
                    _, frame = self.cap.read()
                    lentemp = len(temp)
                    temp[datetime.datetime.now()] = frame, lentemp
                    if virtual_memory()[2] > 70:
                        print("[WARN] RAM is full, skipping frames")
                        self.broken = True
                        break
                with self.camera_lock:
                    if not self.broken:
                        print(f"[INFO] Session has finished, saving to buffer {len(temp)} frames")
                        if len(temp) == 0:
                            self.broken = True
                            self.camera_buffer.clear()
                        else:
                            self.camera_buffer = temp.copy()
                    else:
                        self.do_i_shoot = False
                        self.flash.fill((0, 0, 0))
                        print(f"[INFO] Shutting off leds and skipping {len(temp)} frames")
                    temp.clear()
