#!/usr/bin/env python3

import numpy
from psutil import virtual_memory
import cv2 as cv

import threading
import datetime

from new_led_utils import LEDs
import paho.mqtt.client as mqtt

do_i_shoot = False
camera_buffer: dict[datetime.datetime, tuple[numpy.array, int]] = {}
pings: dict[threading.Thread, datetime.datetime] = {}
camera_lock = threading.Lock()
mqtt_client: mqtt.client = None

print("[INFO] Starting...")
config_and_data = {
    "target_distance": 150,
    "current_class": "paper",
    "wrong_class_counter": 0,
    "last_svuotamento": datetime.datetime.now(),
    "bin_id": 0,
    "bin_height": 600,
    "bin_threshold": 200,
    "label_dict": {0: "plastic", 1: "paper"},
    "valid_classes": ["plastic", "paper"]
}
topic = "wick"
mqtt_host = "stream.lifesensor.cloud"
mqtt_client_id = "Beam1"
port = 9001

valid = {"bin_id": int, "current_class": str, "bin_height": int, "bin_threshold": int}


def watchdog_thread():
    while True:
        time.sleep(5)
        for key, value in pings.items():
            if (datetime.datetime.now() - value).total_seconds() > 70:
                print(f"[ERROR] Thread [{key.getName()}] is not responding, killing...")
                kill()
            elif not key.is_alive():
                print(f"[ERROR] Thread [{key.getName()}] is not responding, killing...")
                kill()


def camera_thread(cap: cv.VideoCapture):
    thread = threading.currentThread()
    thread.setName("Camera")
    global camera_buffer
    ram_is_ok = True
    while True:
        _, frame = cap.read()
        if frame is not None:
            ping(thread)
        if do_i_shoot:
            # temp = {datetime.datetime.now(): (frame, 0)}
            temp = {}
            while do_i_shoot and ram_is_ok:
                _, frame = cap.read()
                lentemp = len(temp)
                temp[datetime.datetime.now()] = frame, lentemp
                ram_is_ok = virtual_memory()[2] < 70
            if not ram_is_ok:
                print("[WARN] RAM is too high, waiting for next session")
                while do_i_shoot:
                    pass
                print("[WARN] Broken session has finished, waiting for next one...")
            else:
                print(f"[INFO] Session has finished, saving to buffer {len(temp)} frames")
            with camera_lock:
                camera_buffer = temp.copy()


def show_results(tof_frame, camera_frame, diff, cropped=None):
    render_tof(tof_frame)

    # cv.imshow("Diff", thresh)
    # cv.imshow("Cropped", cropped)
    cv.imshow("Camera", camera_frame)
    cv.imshow("Diff", diff)
    cv.waitKey(1) & 0xFF


def grab_buffer():
    global camera_buffer
    while len(camera_buffer) == 0:
        pass
    with camera_lock:
        copy = camera_buffer.copy()
        camera_buffer = {}
    return copy


def grab_background(leds: LEDs, return_to_black=True):
    global do_i_shoot
    leds.fill((255, 255, 255))
    do_i_shoot = True
    time.sleep(0.125)
    do_i_shoot = False
    if return_to_black:
        leds.fill((0, 0, 0))
    buffer = grab_buffer()
    if len(buffer) > 0:
        print(f"[INFO] Background frame count: {len(buffer)}")
        return max(buffer.values(), key=lambda d: d[1])[0]
    else:
        print("[WARN] No background frames")


def get_frame_at_distance(tof_buffer: dict[datetime.datetime, tuple[numpy.array, float]],
                          cap_buffer: dict[datetime.datetime, tuple[numpy.array, int]],
                          distance: int):
    """
    Takes a buffer of frames, a buffer of distances and a target distance. Returns the frame and distance that are closest to the target distance.

    :param tof_buffer: A dictionary of time: full_matrix, distance
    :param cap_buffer: A dictionary of time: frame, frame_number
    :param distance: the distance in mm that you want to capture
    :return: The full matrix of the closest distance and the frame number of the closest frame
    :type tof_buffer: dict[datetime.datetime, tuple[numpy.array, float]]
    :type cap_buffer: dict[datetime.datetime, tuple[numpy.array, int]]
    :type distance: int
    """
    # camera_buffer is time: frame, frame_number
    # tof_buffer is time: (full_matrix, distance)
    time_target_item = min(tof_buffer.items(), key=lambda d: abs(d[1][1] - distance))
    closest_frame_item = min(cap_buffer.items(),
                             key=lambda d: abs((d[0] - time_target_item[0]).total_seconds()))
    print(f"[INFO] Target is frame {closest_frame_item[1][1]} at {time_target_item[1][1]}mm")
    print(f"[INFO] Distances: {[(round(dist[0].microsecond / 1000, 2), dist[1][1]) for dist in tof_buffer.items()]}")
    print(f"[INFO] Frames: {[(round(frame[0].microsecond / 1000, 2), frame[1][1]) for frame in cap_buffer.items()]}")
    print(f"[INFO] Time distance: {round(abs(time_target_item[0] - closest_frame_item[0]).total_seconds() * 1000, 2)}ms")
    return time_target_item[1][0], closest_frame_item[1][0]


def get_mqtt_client():
    return mqtt_client


def setup():
    global mqtt_client
    leds = LEDs()
    leds.start_loading_animation()
    mqtt_client = MQTTExtendedClient(mqtt_host, topic, port)
    dm = DataManager(mqtt_client)
    interpreter = setup_edgetpu()
    cap = setup_camera()
    threading.Thread(target=camera_thread, args=(cap,)).start()
    vl53 = tof_setup()
    tof_buffer = {}
    leds.stop_loading_animation()
    background = grab_background(leds)
    leds.change_to_green()
    leds.black_from_green()
    threading.Thread(target=watchdog_thread, daemon=True, name="Watchdog").start()
    return leds, interpreter, cap, vl53, background, tof_buffer, dm


def main():
    leds, interpreter, cap, vl53, background, tof_buffer, dm = setup()
    thread = threading.current_thread()
    thread.setName("Main")
    print(f'[INFO] Main thread "{thread}" started.')
    global do_i_shoot
    count = 0
    movement = False
    start = datetime.datetime.now()
    print("[INFO] Ready for action!")
    while True:
        if vl53.data_ready():
            data = vl53.get_data()
            asd = [e for e in data.distance_mm[0][:16] if 200 > e > 0]
            if not movement:
                if len(asd) > 0:
                    leds.fill((255, 255, 255))
                    tof_buffer = {datetime.datetime.now(): (data.distance_mm[0][:16], sum(asd) / len(asd))}
                    do_i_shoot = True
                    movement = True
                    print("[INFO] Movement detected")
                    print(asd, sum(asd) / len(asd))
                    start = datetime.datetime.now()
                    count = 1
            else:
                if len(asd) == 0:
                    do_i_shoot = False
                    now = datetime.datetime.now()
                    buffer = grab_buffer()
                    buffer = dict(sorted(buffer.items(), key=lambda d: d[1][1])[1:]) if len(buffer) > 1 else buffer
                    leds.fill((1, 1, 1))
                    movement = False
                    print(f"[INFO] Stopped, FPS: {(count / (now - start).total_seconds(), len(buffer) / (now - start).total_seconds())}")

                    tof_target_frame, camera_target_frame = get_frame_at_distance(tof_buffer, buffer, config_and_data["target_distance"])

                    rect, diff = helpers.get_diff(camera_target_frame, background)
                    if rect:
                        x, y, w, h = rect
                        cropped = camera_target_frame.copy()[y:y + h, x:x + w]
                        cv.rectangle(camera_target_frame, (x, y), (x + w - 1, y + h - 1), 255, 2)

                        if cropped.shape[0] > 0 and cropped.shape[1] > 0:
                            cropped = cv.cvtColor(cropped, cv.COLOR_BGR2RGB)
                            label, score = inference(cropped, interpreter)
                            print(f"[INFO] Class: {label}, score: {int(score * 100)}%")

                            show_results(tof_target_frame, camera_target_frame, diff, cropped=cropped)

                            if label == "paper":
                                leds.change_to_green()
                            else:
                                leds.change_to_red()
                            background = grab_background(return_to_black=False)
                            if label == "paper":
                                leds.black_from_green()
                            else:
                                leds.black_from_red()
                    else:
                        print("[INFO] Object not found.")
                        show_results(tof_target_frame, camera_target_frame, diff)

                    avg, percentage = get_trash_level(vl53)
                    print(f"[INFO] {avg}mm, {percentage}%")
                    ddd = [t[0] for t in sorted(buffer.values(), key=lambda d: d[1])]
                    print(ddd[0].shape, ddd[-1].shape)
                    dm.pass_data({"riempimento": percentage,
                               "wrong_class_counter": config_and_data["wrong_class_counter"],
                               "timestamp": str(now.isoformat()),
                               "images": ddd
                               })
                    count = 0
                    print("[INFO] Waiting for movement...")
                else:
                    tof_buffer[datetime.datetime.now()] = (data.distance_mm[0][:16], sum(asd) / len(asd))
                    count += 1
            ping(thread)

        time.sleep(0.003)  # Avoid polling *too* fast


if __name__ == '__main__':
    from new_led_utils import *
    from mqtt_utils import *
    from data_utils import *
    from tof_utils import *
    from watchdog import *
    from edgetpu_utils import *
    from camera_utils import *
    main()
