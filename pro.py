import datetime
import threading
import time

import cv2 as cv

import helpers
from data_utils import config_and_data
from edgetpu_utils import inference
from flightshot import setup
from tof_utils import get_trash_level
from watchdog import ping


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
            for i in range(4):
                for j in range(4):
                    average_matrix[i][j] += (-thrown_out[i][j] + new_matrix[i][j]) / 100
    return True, average_matrix  # todo fix your shit


def main():
    leds, interpreter, camera, vl53, background, _, dm = setup()
    original_position = background.copy()
    thread = threading.current_thread()
    thread.setName("Main")
    print(f'[INFO] Main thread "{thread}" started.')
    movement = False
    start = datetime.datetime.now()
    print("[INFO] Ready for action!")
    tof_buffer = []
    while True:
        if vl53.data_ready():
            data = vl53.get_data()
            tof_buffer_update(data, tof_buffer)
            if not movement:
                movement = True
                print("[INFO] Movement detected")
            else:
                if len(asd) == 0 and ((now := datetime.datetime.now()) - start).total_seconds() > 0.3:
                    movement = False
                    buffer = camera.grab_background()
                    if buffer is not None and len(buffer) > 0:
                        frame = buffer[-1]
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
                                buffer.clear()
                                print("[INFO] Waiting for movement...")
                                continue

                            # label, score = inference(cropped, interpreter)
                            # print(f"[INFO] Class: {label}, score: {int(score * 100)}%")

                            show_results(imgcopy, diff, cropped=cropped)

                            # todo open servos and make thing fall

                            leds.change_to_white()
                            background = camera.grab_background(return_to_black=False)
                            leds.black_from_white()
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
                            show_results(frame, diff)
                            background = camera.grab_background(return_to_black=True)

                    avg, percentage = get_trash_level(vl53)
                    print(f"[INFO] {avg}mm, {percentage}%")
                    ddd = [t[0] for t in sorted(buffer.values(), key=lambda d: d[1])]
                    print(ddd[0].shape, ddd[-1].shape)
                    dm.pass_data({"riempimento": percentage,  # todo multiple percentages
                                  "wrong_class_counter": config_and_data["wrong_class_counter"],
                                  "timestamp": str(now.isoformat()),
                                  "images": (ddd if len(ddd) < 20 else ddd[:20])  # + ([imgcopy] if imgcopy is not None else []),
                                  })
                    buffer.clear()
                    print("[INFO] Waiting for movement...")
                else:
                    # todo update tof buffer
                    pass
            ping(thread)

        time.sleep(0.003)  # Avoid polling *too* fast


if __name__ == '__main__':
    main()
