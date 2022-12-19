import datetime
import random
import threading
import time

import cv2 as cv

import helpers
import mech_utils
# import helpers
import tof_utils
from camera_utils import Camera
from new_led_utils import LEDs
# from data_utils import config_and_data
# from edgetpu_utils import inference
# from tof_utils import get_trash_level
from watchdog import ping
from mech_utils import *


def show_results(camera_frame, diff, cropped=None):
    """
    Displays things on the screen

    :param camera_frame: the current frame from the camera
    :param diff: the difference between the current frame and the background
    :param cropped: the cropped image
    """

    # cv.imshow("Diff", thresh)
    # cv.imshow("Cropped", cropped)
    cv.imshow("Camera", camera_frame)
    cv.imshow("Diff", diff)
    cv.waitKey(1) & 0xFF


def tof_buffer_update(new_matrix, tof_buffer, average_matrix):
    if 0 not in new_matrix:
        if len(tof_buffer) == 100:
            tof_buffer.append(new_matrix)
            thrown_out = tof_buffer.pop(0)
            for i in range(16):
                average_matrix[i] += (-thrown_out[i] + new_matrix[i]) / 100
        else:
            tof_buffer.append(new_matrix)
            for i in range(16):
                average_matrix[i] += new_matrix[i] / 100
    return average_matrix


def setup():
    """
    It sets up the camera, the LED strip, the VL53L0X sensor, the MQTT client, the TensorFlow interpreter, and the data manager
    :return: leds, interpreter, camera, vl53, initial_background, empty_tof_buffer, datamanager
    """
    leds = LEDs()
    camera = Camera(leds)
    vl53 = tof_utils.tof_setup()
    print("[INFO] Setup complete!")
    background = camera.grab_background(return_to_black=False)
    print("[INFO] Background grabbed!")
    servo_calibration = {
        0: 35,
        1: 20,
        2: 30,
        3: 20,
    }
    munnezza_manager = mech_utils.CompartmentManager(servo_calibration)
    munnezza_manager.close_all()
    return vl53, camera, background, munnezza_manager


def normalize_shit_matrix(matrix):
    return [int(x) for y, x in enumerate(matrix) if y in [6, 7, 10, 11, 14, 15]]


def main():
    vl53, camera, background, munnezza_manager = setup()
    thread = threading.current_thread()
    thread.setName("Main")
    print(f'[INFO] Main thread "{thread}" started.')
    movement = False
    average_matrix = [0] * 16
    c = 0
    while c != 100:
        if vl53.data_ready():
            data = vl53.get_data().distance_mm[0][:16]
            if 0 not in data:
                for i in range(16):
                    average_matrix[i] += data[i] / 100
                c += 1
    print(f"[INFO] Average matrix: {normalize_shit_matrix(average_matrix)}")
    last_movement = datetime.datetime.now()
    print("[INFO] Ready for action!")
    while True:
        if vl53.data_ready():
            data = vl53.get_data()
            new_matrix = data.distance_mm[0][:16]
            if not movement:
                # average_matrix = tof_buffer_update(new_matrix, tof_buffer, average_matrix)
                if tof_utils.absolute_diff(average_matrix, new_matrix, 50):
                    movement = True
                    last_movement = datetime.datetime.now()
                    print(normalize_shit_matrix(average_matrix), normalize_shit_matrix(new_matrix))
                    print("[INFO] Movement detected")
            else:
                if tof_utils.absolute_diff(average_matrix, new_matrix, 50):
                    last_movement = datetime.datetime.now()
                elif (datetime.datetime.now() - last_movement).total_seconds() > 1:
                    last_movement = datetime.datetime.now()
                    movement = False
                    print("[INFO] Movement stopped")
                    frame = camera.grab_background()
                    if frame is not None:
                        rect, diff = helpers.get_diff(frame, background)
                        if (rect is not None) and (diff is not None):
                            x, y, w, h = rect
                            imgcopy = frame.copy()
                            cropped = imgcopy[y:y + h, x:x + w]
                            cv.rectangle(imgcopy, (x, y), (x + w - 1, y + h - 1), 255, 2)

                            if not (cropped.shape[0] > 0 and cropped.shape[1] > 0):
                                continue
                            try:
                                cropped = cv.cvtColor(cropped, cv.COLOR_BGR2RGB)
                            except:
                                print("[ERROR] Cropped image is not a valid image")
                                print("[INFO] Waiting for movement...")
                                continue

                            # label, score = inference(cropped, interpreter)
                            # print(f"[INFO] Class: {label}, score: {int(score * 100)}%")

                            show_results(imgcopy, diff, cropped=cropped)

                            comp = random.randint(0, 3)
                            start = datetime.datetime.now()
                            while (datetime.datetime.now() - start).total_seconds() < 30:
                                munnezza_manager.open_compartment(comp)
                                munnezza_manager.vibrato(comp)
                                munnezza_manager.close_all()
                                time.sleep(0.5)
                                frame = camera.grab_background()
                                if frame is not None:
                                    rect, diff = helpers.get_diff(frame, background)
                                    if (rect is not None) or (diff is not None):
                                        break


                            # leds.change_to_white()
                            background = camera.grab_background(return_to_black=False)
                            # leds.black_from_white()
                            # if label == config_and_data["current_class"]:
                            #     leds.change_to_green()
                            # else:
                            #     leds.change_to_red()
                            #     config_and_data["wrong_class_counter"] += 1
                            # background = camera.grab_background(return_to_black=False)
                            # if label == config_and_data["current_class"]:
                            #     leds.black_from_green()
                            # else:
                            #     leds.black_from_red()
                        else:
                            print("[INFO] Object not found.")
                            munnezza_manager.open_compartment(random.randint(0, 3))
                            time.sleep(2)
                            munnezza_manager.close_all()
                            show_results(frame, diff)
                            background = camera.grab_background(return_to_black=True)

                    # avg, percentage = get_trash_level(vl53)
                    # print(f"[INFO] {avg}mm, {percentage}%")
                    # ddd = [t[0] for t in sorted(buffer.values(), key=lambda d: d[1])]
                    # print(ddd[0].shape, ddd[-1].shape)
                    # dm.pass_data({"riempimento": percentage,  # todo multiple percentages
                    #               "wrong_class_counter": config_and_data["wrong_class_counter"],
                    #               "timestamp": str(now.isoformat()),
                    #               "images": (ddd if len(ddd) < 20 else ddd[:20])  # + ([imgcopy] if imgcopy is not None else []),
                    #               })
                    # buffer.clear()
                    print("[INFO] Waiting for movement...")
            ping(thread)

        time.sleep(0.003)  # Avoid polling *too* fast


if __name__ == '__main__':
    main()
