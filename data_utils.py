import datetime
import json
import os
import random
import threading
import time

import flightshot
from flightshot import valid_classes, data_lock, data_buffer, last_svuotamento
from helpers import kill
from watchdog import ping


def pass_data(data_dict):
    global data_ready
    with data_lock:
        data_ready = True
        for key, value in data_dict.items():
            data_buffer[key] = data_buffer.get(key, []) + [value]


def add_lines_csv(data):
    with open("history.csv", "a") as f:
        for percentage, timestamp, wrong_class_counter in zip(data["riempimento"], data["timestamp"], data["wrong_class_counter"]):
            f.write(f"{percentage},{timestamp},{wrong_class_counter}\n")


def create_csv_file():
    print("[INFO] Creating csv file:", end=" ", flush=True)
    with open("history.csv", "w") as f:
        f.write("riempimento,timestamp,wrong_class_counter\n")
    print("Done.")


def files_setup():
    global bin_id
    global current_class
    global bin_height
    global bin_threshold

    errors = 0

    bin_id = random.randint(0, 65534)
    default_dict = {"bin_id": bin_id, "current_class": "None", "bin_height": 600, "bin_threshold": 200}

    if not os.path.exists("history.csv"):
        create_csv_file()

    if not os.path.exists("config.json"):
        with open("config.json", "w") as f:
            json.dump(default_dict, f)
        print(f'[INFO] Created config.json with id {bin_id}, edit "current_class" field to continue..."')
        kill()
    else:
        with open("config.json", "r") as f:
            data = json.load(f)
        for key, value in default_dict.items():
            value_type = type(value)
            if not isinstance(data[key], value_type):
                print(f'[ERROR] Value {data[key]} for "{key}" is not of class {value_type}(default is {value}), you should delete the config file and/or reconfigure.')
                data[key] = value
                errors += 1

        try:
            bin_id = data["bin_id"]
            current_class = data["current_class"]
            bin_height = data["bin_height"]
            bin_threshold = data["bin_threshold"]
        except KeyError:
            print("[ERROR] config.json is corrupted, the program will run with default settings and id 65535, but you should delete the config file and/or reconfigure.")
            bin_id = 65535
            current_class = "paper"
            bin_height = 600
            bin_threshold = 200
            errors += 1

        if current_class not in valid_classes:
            print(f'[ERROR] "{current_class}" is not a valid material, defaulting to "paper", please edit config.json')
            current_class = "paper"
            errors += 1

        if errors > 0:
            print(f"[ERROR] WICK couldn't start normally, {errors} errors occurred.")
        else:
            printable_list = "\n".join(["- " + key + ": " + str(value) for key, value in data.items()])
            print(f"[INFO] Loaded config.json successfully:\n{printable_list}")


def data_manager_thread():
    thread = threading.current_thread()
    thread.setName("Data Manager")
    while True:
        time.sleep(30)
        ping(thread)
        if data_ready:
            if len(data_buffer) == 0:
                print("[WARN] Data buffer is empty")
                flightshot.data_ready = False
                continue
            start = datetime.datetime.now()
            print("[INFO] Data is ready, saving & uploading...")
            with data_lock:
                data = data_buffer.copy()
                data_buffer.clear()
                flightshot.data_ready = False
            save_buffer = {
                "riempimento": data["riempimento"][-1],
                "timestamp_last_svuotamento": str(last_svuotamento.isoformat()),
                "wrong_class_counter": data["wrong_class_counter"][-1]
            }
            # todo send save_buffer via mqtt

            with open("data.json", "w") as f:
                json.dump(save_buffer, f)

            add_lines_csv(data)
            print(f"[INFO] Data saved in {(datetime.datetime.now() - start).total_seconds()}s.")
