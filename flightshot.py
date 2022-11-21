#!/usr/bin/env python3
from psutil import virtual_memory

import helpers
import threading
import datetime

do_i_shoot = False
setup_not_done = True
data_ready = False
camera_buffer = {}
data_buffer = {}
camera_lock = threading.Lock()
data_lock = threading.Lock()
target_distance = 150
current_class = "paper"
wrong_class_counter = 0
last_svuotamento = datetime.datetime.now()
bin_id = 0
bin_height = 600
bin_threshold = 200
label_dict: dict[int, str] = {0: "plastic", 1: "paper"}
valid_classes: set[str] = set(label_dict.values())
pings: dict[threading.Thread, datetime.datetime] = {}

from new_led_utils import *
from data_utils import *
from tof_utils import *
from watchdog import *
from edgetpu_utils import *
from camera_utils import *


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


def data_manager_thread():
    thread = threading.current_thread()
    thread.setName("Data Manager")
    global data_ready
    while True:
        time.sleep(20)
        ping(thread)
        if data_ready:
            if len(data_buffer) == 0:
                print("[WARN] Data buffer is empty")
                data_ready = False
                continue
            start = datetime.datetime.now()
            print("[INFO] Data is ready, saving & uploading...")
            with data_lock:
                data = data_buffer.copy()
                data_buffer.clear()
                data_ready = False
            save_buffer = {
                "riempimento": data["riempimento"][-1],
                "timestamp_last_svuotamento": str(last_svuotamento.isoformat()),
                "wrong_class_counter": data["wrong_class_counter"][-1]
            }
            # todo send save_buffer via mqtt

            with open("data.json", "w") as f:
                json.dump(save_buffer, f)

            add_lines_csv(data)
            helpers.save_images_linux(data["images"], "images")
            print(f"[INFO] Data saved in {(datetime.datetime.now() - start).total_seconds()}s.")


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


def grab_background(pixels, return_to_black=True):
    global do_i_shoot
    fill(pixels, (255, 255, 255))
    do_i_shoot = True
    time.sleep(0.125)
    do_i_shoot = False
    if return_to_black:
        fill(pixels, (0, 0, 0))
    buffer = grab_buffer()
    if len(buffer) > 0:
        print(f"[INFO] Background frame count: {len(buffer)}")
        return max(buffer.values(), key=lambda d: d[1])[0]
    else:
        print("[WARN] No background frames")


def get_frame_at_distance(tof_buffer, cap_buffer, distance):
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


def setup():
    files_setup()
    pixels = setup_led()
    # threading.Thread(target=timed_fill, args=(pixels,)).start()
    interpreter = setup_edgetpu()
    cap = setup_camera()
    threading.Thread(target=camera_thread, args=(cap,)).start()
    threading.Thread(target=data_manager_thread).start()
    vl53 = tof_setup()
    tof_buffer = {}
    # global setup_not_done
    # setup_not_done = False
    background = grab_background(pixels)
    change_to_green(pixels)
    black_from_green(pixels)
    threading.Thread(target=watchdog_thread, daemon=True, name="Watchdog").start()
    return pixels, interpreter, cap, vl53, background, tof_buffer


def main():
    thread = threading.current_thread()
    thread.setName("Main")
    print(f'[INFO] Main thread "{thread}" started.')
    global do_i_shoot
    pixels, interpreter, cap, vl53, background, tof_buffer = setup()
    count = 0
    movement = False
    start = datetime.datetime.now()
    while True:
        if vl53.data_ready():
            data = vl53.get_data()
            asd = [e for e in data.distance_mm[0][:16] if 200 > e > 0]
            if not movement:
                if len(asd) > 0:
                    fill(pixels, (255, 255, 255))
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
                    fill(pixels, (1, 1, 1))
                    movement = False
                    print(f"[INFO] Stopped, FPS: {(count / (now - start).total_seconds(), len(buffer) / (now - start).total_seconds())}")

                    tof_target_frame, camera_target_frame = get_frame_at_distance(tof_buffer, buffer, target_distance)

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
                                change_to_green(pixels)
                            else:
                                change_to_red(pixels)
                            background = grab_background(pixels, return_to_black=False)
                            if label == "paper":
                                black_from_green(pixels)
                            else:
                                black_from_red(pixels)
                    else:
                        print("[INFO] Object not found.")
                        show_results(tof_target_frame, camera_target_frame, diff)

                    avg, percentage = get_trash_level(vl53)
                    print(f"[INFO] {avg}mm, {percentage}%")
                    pass_data({"riempimento": percentage,
                               "wrong_class_counter": wrong_class_counter,
                               "timestamp": str(now.isoformat()),
                               "images": list(sorted(buffer.values(), key=lambda d: d[1][1]))
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
