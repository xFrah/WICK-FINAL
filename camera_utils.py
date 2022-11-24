import datetime
import threading

import cv2 as cv
import time

import numpy
from psutil import virtual_memory
from watchdog import ping


class Camera:
    def __init__(self, flash):
        self.do_i_shoot = False
        self.flash = flash
        self.camera_buffer: dict[datetime.datetime, tuple[numpy.array, int]] = {}
        self.camera_lock = threading.Lock()
        self.cap = cv.VideoCapture(0)
        print("[INFO] Configuring camera:", end=" ", flush=True)

        succ = self.apply_configuration()

        c = 0
        start = datetime.datetime.now()
        while c < 100:
            _, frame = self.cap.read()
            c += 1
        print(f"Done, {str(tuple([round(100 / (datetime.datetime.now() - start).total_seconds(), 2)] + [round(self.cap.get(item), 2) if value else 'FAILED' for item, value in succ.items()]))}")
        threading.Thread(target=self.camera_thread).start()

    def apply_configuration(self):
        succ = dict()
        succ[cv.CAP_PROP_FRAME_WIDTH] = self.cap.set(cv.CAP_PROP_FRAME_WIDTH, 640)
        succ[cv.CAP_PROP_FRAME_HEIGHT] = self.cap.set(cv.CAP_PROP_FRAME_HEIGHT, 480)
        succ[cv.CAP_PROP_FPS] = self.cap.set(cv.CAP_PROP_FPS, 120)
        time.sleep(2)
        succ[cv.CAP_PROP_FOURCC] = self.cap.set(cv.CAP_PROP_FOURCC, cv.VideoWriter_fourcc('M', 'J', 'P', 'G'))
        # time.sleep(2)
        succ[cv.CAP_PROP_AUTO_EXPOSURE] = self.cap.set(cv.CAP_PROP_AUTO_EXPOSURE, 1)
        time.sleep(2)
        succ[cv.CAP_PROP_EXPOSURE] = self.cap.set(cv.CAP_PROP_EXPOSURE, 12)
        succ[cv.CAP_PROP_GAIN] = self.cap.set(cv.CAP_PROP_GAIN, 100)
        # succ[cv.CAP_PROP_BUFFERSIZE] = cap.set(cv.CAP_PROP_BUFFERSIZE, 1)

        return succ

    def shoot(self, timer=0.0, return_to_black=True):
        self.flash.fill((255, 255, 255))
        self.do_i_shoot = True
        if timer > 0:
            time.sleep(timer)
            self.stop_shooting(turn_black=return_to_black)

    def stop_shooting(self, turn_black=True):
        self.do_i_shoot = True
        if turn_black:
            self.flash.fill((0, 0, 0))

    def grab_buffer(self):
        while len(self.camera_buffer) == 0:
            pass
        with self.camera_lock:
            copy = self.camera_buffer.copy()
            self.camera_buffer = {}
        return copy

    def grab_background(self, return_to_black=True):
        self.flash.fill((255, 255, 255))
        self.shoot(timer=0.125, return_to_black=return_to_black)
        buffer = self.grab_buffer()
        if len(buffer) > 0:
            print(f"[INFO] Background frame count: {len(buffer)}")
            return max(buffer.values(), key=lambda d: d[1])[0]
        else:
            print("[WARN] No background frames")

    def camera_thread(self):
        thread = threading.currentThread()
        thread.setName("Camera")
        ram_is_ok = True
        while True:
            _, frame = self.cap.read()
            if frame is not None:
                ping(thread)
            if self.do_i_shoot:
                # temp = {datetime.datetime.now(): (frame, 0)}
                temp = {}
                while self.do_i_shoot and ram_is_ok:
                    _, frame = self.cap.read()
                    lentemp = len(temp)
                    temp[datetime.datetime.now()] = frame, lentemp
                    ram_is_ok = virtual_memory()[2] < 70
                if not ram_is_ok:
                    print("[WARN] RAM is too high, waiting for next session")
                    while self.do_i_shoot:
                        pass
                    print("[WARN] Broken session has finished, waiting for next one...")
                else:
                    print(f"[INFO] Session has finished, saving to buffer {len(temp)} frames")
                with self.camera_lock:
                    self.camera_buffer = temp.copy()