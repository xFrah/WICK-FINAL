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
from edgetpu_utils import setup_edgetpu, inference
from new_led_utils import LEDs
# from data_utils import config_and_data
# from edgetpu_utils import inference
# from tof_utils import get_trash_level
from watchdog import ping
from mech_utils import *
from skimage.metrics import structural_similarity


def show_results(camera_frame, diff, diff2, cropped=None):
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
    cv.imshow("Diff2", diff2)
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


def get_diff_2(image1, image2):
    image1 = cv.cvtColor(image1, cv.COLOR_BGR2GRAY)
    image2 = cv.cvtColor(image2, cv.COLOR_BGR2GRAY)

    # Compute SSIM between the two images
    (score, diff) = structural_similarity(image1, image2, full=True)

    # The diff image contains the actual image differences between the two images
    # and is represented as a floating point data type in the range [0,1]
    # so we must convert the array to 8-bit unsigned integers in the range
    # [0,255] image1 we can use it with OpenCV
    # Threshold the difference image, followed by finding contours to
    # obtain the regions of the two input images that differ
    diff = (diff * 255).astype("uint8")
    #thresh = cv.threshold(diff, 0, 255, cv.THRESH_BINARY_INV | cv.THRESH_OTSU)[1]
    return diff


def setup():
    """
    It sets up the camera, the LED strip, the VL53L0X sensor, the MQTT client, the TensorFlow interpreter, and the data manager
    :return: leds, interpreter, camera, vl53, initial_background, empty_tof_buffer, datamanager
    """
    leds = LEDs()
    camera = Camera(leds)
    vl53 = tof_utils.tof_setup()
    interpreter = setup_edgetpu()
    print("[INFO] Setup complete!")
    servo_calibration = {
        0: 15,
        1: 30,
        2: 20,
        3: 35,
    }
    munnezza_manager = mech_utils.CompartmentManager(servo_calibration)
    munnezza_manager.close_all()
    leds.stop_loading_animation()
    time.sleep(3)
    background = camera.grab_background(custom_timer=0.5, return_to_black=False)
    background = camera.grab_background(custom_timer=1, return_to_black=False)
    show_results(background, background, background)
    time.sleep(1)
    leds.fill((0, 0, 0))
    print("[INFO] Background grabbed!")
    return vl53, camera, background, munnezza_manager, leds, interpreter


def normalize_shit_matrix(matrix):
    return [int(x) for y, x in enumerate(matrix) if y in [6, 7, 10, 11, 14, 15]]


def main():
    vl53, camera, background, munnezza_manager, leds, interpreter = setup()
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
                    frame = camera.grab_background(custom_timer=1, return_to_black=False)
                    if frame is not None:
                        rect, diff = helpers.get_diff(frame, background)
                        diff2 = get_diff_2(frame, background)
                        if (rect is not None) and (diff is not None):
                            original_white_pixels_count = helpers.count_white_pixels(diff)
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

                            label, score = inference(cropped, interpreter)
                            print(f"[INFO] Class: {label}, score: {int(score * 100)}%")

                            show_results(imgcopy, diff, diff2, cropped=cropped)

                            comp = random.randint(0, 3)
                            frame = camera.grab_background(custom_timer=1, return_to_black=False)
                            munnezza_manager.open_compartment(comp)

                            time.sleep(2)

                            print("[INFO] First frame after opening compartment grabbed")
                            if frame is not None:
                                rect, diff = helpers.get_diff(frame, background)
                                diff2 = get_diff_2(frame, background)
                                white_pixels_count = helpers.count_white_pixels(diff)
                                print("[INFO] Diff computed")
                                if rect is not None or diff is not None and original_white_pixels_count * 0.2 > white_pixels_count:
                                    print("[INFO] Object has not fallen, vibrating...")
                                    start = datetime.datetime.now()
                                    fallen = False
                                    while not fallen and (datetime.datetime.now() - start).total_seconds() < 15:
                                        munnezza_manager.open_compartment(comp)
                                        munnezza_manager.vibrato(comp)
                                        munnezza_manager.close_all()
                                        time.sleep(1)
                                        frame = camera.grab_background(custom_timer=1, return_to_black=False)
                                        show_results(frame, diff, diff2)
                                        print("[INFO] Frame after vibrating grabbed")
                                        if frame is not None:
                                            rect, diff = helpers.get_diff(frame, background)
                                            diff2 = get_diff_2(frame, background)
                                            white_pixels_count = helpers.count_white_pixels(diff)
                                            show_results(frame, diff, diff2)
                                            print(f"[INFO] {original_white_pixels_count * 0.2} > {white_pixels_count}?")
                                            if original_white_pixels_count * 0.2 > white_pixels_count:
                                                print("[INFO] Object has finally fallen...")
                                                break
                                        print("[INFO] Object has not fallen yet, retrying...")
                            munnezza_manager.close_all()

                            # leds.change_to_white()
                            background = camera.grab_background(custom_timer=1, return_to_black=False)
                            show_results(background, diff, diff2)
                            time.sleep(1)
                            leds.fill((0, 0, 0))
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
                            background = camera.grab_background(custom_timer=1, return_to_black=False)
                            show_results(background, diff, diff2)
                            time.sleep(1)
                            leds.fill((0, 0, 0))

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
