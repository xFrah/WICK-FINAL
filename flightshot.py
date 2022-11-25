#!/usr/bin/env python3
import time

import numpy

import threading
import datetime

import paho.mqtt.client as mqtt

import helpers
from camera_utils import Camera
from data_utils import DataManager, config_and_data
from edgetpu_utils import inference, setup_edgetpu
from mqtt_utils import MQTTExtendedClient
from new_led_utils import LEDs
from tof_utils import tof_setup, render_tof, get_trash_level
from watchdog import ping, pings, ignore
import cv2 as cv

mqtt_client: mqtt.Client = None

print("[INFO] Starting...")
topic = "wick"
mqtt_host = "stream.lifesensor.cloud"
mqtt_client_id = "Beam1"
port = 9001

valid = {"name": str, "bin_id": int, "current_class": str, "bin_height": int, "bin_threshold": int}


def watchdog_thread():
    """
    It checks if the threads are still alive. If they're not, it kills the program...
    """
    while True:
        time.sleep(5)
        for key, value in pings.items():
            if (datetime.datetime.now() - value).total_seconds() > 70 and key not in ignore:
                print(f"[ERROR] Thread [{key.getName()}] is not responding, killing...")
                helpers.kill()
            elif not key.is_alive():
                print(f"[ERROR] Thread [{key.getName()}] is not responding, killing...")
                helpers.kill()


def show_results(tof_frame, camera_frame, diff, cropped=None):
    """
    Displays things on the screen

    :param tof_frame: the depth frame from the ToF camera
    :param camera_frame: the current frame from the camera
    :param diff: the difference between the current frame and the background
    :param cropped: the cropped image
    """
    render_tof(tof_frame)

    # cv.imshow("Diff", thresh)
    # cv.imshow("Cropped", cropped)
    cv.imshow("Camera", camera_frame)
    cv.imshow("Diff", diff)
    cv.waitKey(1) & 0xFF


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

    time_target_item = min(tof_buffer.items(), key=lambda d: abs(d[1][1] - distance))
    closest_frame_item = min(cap_buffer.items(),
                             key=lambda d: abs((d[0] - time_target_item[0]).total_seconds()))
    print(f"[INFO] Target is frame {closest_frame_item[1][1]} at {time_target_item[1][1]}mm")
    print(f"[INFO] Distances: {[(round(dist[0].microsecond / 1000, 2), dist[1][1]) for dist in tof_buffer.items()]}")
    print(f"[INFO] Frames: {[(round(frame[0].microsecond / 1000, 2), frame[1][1]) for frame in cap_buffer.items()]}")
    print(f"[INFO] Time distance: {round(abs(time_target_item[0] - closest_frame_item[0]).total_seconds() * 1000, 2)}ms")
    return time_target_item[1][0], closest_frame_item[1][0]


def get_mqtt_client():
    """
    :return: The mqtt_client object
    """
    return mqtt_client


def setup():
    """
    It sets up the camera, the LED strip, the VL53L0X sensor, the MQTT client, the TensorFlow interpreter, and the data manager
    :return: leds, interpreter, camera, vl53, initial_background, empty_tof_buffer, datamanager
    """
    global mqtt_client
    leds = LEDs()
    mqtt_client = MQTTExtendedClient(mqtt_host, topic, port)
    mqtt_client.try_to_connect()
    dm = DataManager(mqtt_client)
    interpreter = setup_edgetpu()
    camera = Camera(leds)
    vl53 = tof_setup()
    tof_buffer = {}
    leds.stop_loading_animation()
    while leds.in_use():
        time.sleep(0.1)
    print("[INFO] Setup complete!")
    background = camera.grab_background(return_to_black=False)
    print("[INFO] Background grabbed!")
    leds.change_to_green()
    leds.black_from_green()
    threading.Thread(target=watchdog_thread, daemon=True, name="Watchdog").start()
    return leds, interpreter, camera, vl53, background, tof_buffer, dm


def main():
    leds, interpreter, camera, vl53, background, tof_buffer, dm = setup()
    thread = threading.current_thread()
    thread.setName("Main")
    print(f'[INFO] Main thread "{thread}" started.')
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
                    camera.shoot()
                    tof_buffer = {datetime.datetime.now(): (data.distance_mm[0][:16], sum(asd) / len(asd))}
                    movement = True
                    print("[INFO] Movement detected")
                    print(asd, sum(asd) / len(asd))
                    start = datetime.datetime.now()
                    count = 1
            else:
                if len(asd) == 0:
                    camera.stop_shooting()
                    now = datetime.datetime.now()
                    buffer = camera.grab_buffer()
                    buffer = dict(sorted(buffer.items(), key=lambda d: d[1][1])[1:]) if len(buffer) > 1 else buffer
                    movement = False
                    print(f"[INFO] Stopped, FPS: {(count / (now - start).total_seconds(), len(buffer) / (now - start).total_seconds())}")

                    tof_target_frame, camera_target_frame = get_frame_at_distance(tof_buffer, buffer, config_and_data["target_distance"])

                    rect, diff = helpers.get_diff(camera_target_frame, background)
                    if rect is not None:
                        x, y, w, h = rect
                        imgcopy = camera_target_frame.copy()
                        cropped = imgcopy[y:y + h, x:x + w]
                        cv.rectangle(imgcopy, (x, y), (x + w - 1, y + h - 1), 255, 2)

                        if cropped.shape[0] > 0 and cropped.shape[1] > 0:
                            cropped = cv.cvtColor(cropped, cv.COLOR_BGR2RGB)
                            label, score = inference(cropped, interpreter)
                            print(f"[INFO] Class: {label}, score: {int(score * 100)}%")

                            show_results(tof_target_frame, imgcopy, diff, cropped=cropped)

                            if label == "paper":
                                leds.change_to_green()
                            else:
                                leds.change_to_red()
                            background = camera.grab_background(return_to_black=False)
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
    main()
