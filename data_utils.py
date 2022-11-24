import datetime
import json
import os
import random
import threading
import time
from typing import Any

import paho.mqtt.client as mqtt

import helpers
from flightshot import config_and_data
from helpers import kill
from watchdog import ping


class DataManager:
    def __init__(self, mqtt_client: mqtt.Client):
        self.mqtt_client = mqtt_client
        self.data_lock = threading.Lock()
        self.data_ready = False
        self.data_buffer: dict[str, Any] = {}
        self.data_manager_thread = threading.Thread(target=self.data_manager_thread)
        self.data_manager_thread.start()

    def files_setup(self):
        if not os.path.exists("history.csv"):
            create_csv_file()

        start = datetime.datetime.now()
        if not os.path.exists("config.json"):
            print("[INFO] Trying to get config through MQTT")
            while not (data := self.il_fantastico_viaggio_del_bagarozzo_mark()) and (datetime.datetime.now() - start).total_seconds() < 60:
                print("[ERROR] Couldn't get config from MQTT, retrying...")
                if not self.mqtt_client.connected():
                    print("[ERROR] MQTT client is not connected, reinitializing...")
                    # todo reinitialize setup_mqtt()
            if not data:
                print("[ERROR] Wizard failed to get config through MQTT, killing...")
                kill()
            else:
                print("[INFO] Wizard got config through MQTT, saving to config.json")
                with open("config.json", "w") as f:
                    json.dump(data, f)
        else:
            with open("config.json", "r") as f:
                data = json.load(f)

            check_config_integrity(data)  # it crashes anyway if it can't unpack
            if self.mqtt_client.connected():
                received = self.il_fantastico_viaggio_del_bagarozzo_mark()  # todo why does it return null?
                if received:
                    if check_config_integrity(received, dont_kill=True):
                        if received == data:
                            print("[INFO] Config is up to date.")
                        else:
                            print("[INFO] Config is outdated, updating...", end=" ", flush=True)
                            with open("config.json", "w") as f:
                                json.dump(data, f)
                            data = received
                            print("Done.")
                    else:
                        print("[ERROR] Downloaded config is corrupted, not updating...")
                else:
                    print("[ERROR] Wizard failed to get config through MQTT.")
            else:
                print("[INFO] MQTT client is not connected, skipping config update.")

        printable_list = "\n".join(["- " + key + ": " + str(value) for key, value in data.items()])
        print(f"[INFO] Configuration data:\n{printable_list}")

    def il_fantastico_viaggio_del_bagarozzo_mark(self):
        print("[INFO] Getting config through MQTT...")
        try:
            if not self.mqtt_client.connected():
                return print("[ERROR] MQTT client is not connected, exiting wizard...")

            try:
                self.mqtt_client.publish(json.dumps({"bin_id": 51333, "config": True}))
            except:
                return print("[ERROR] An error occurred while publishing MQTT packet, exiting wizard...")

            start = datetime.datetime.now()
            while (datetime.datetime.now() - start).total_seconds() < 10:
                if self.mqtt_client.data_ready():
                    received_config = self.mqtt_client.unload_buffer()
                    return received_config

            if not self.mqtt_client.connected():
                return print("[ERROR] MQTT connection lost during wizard setup, exiting wizard...")
        except:
            return print("[ERROR] An error occurred in wizard setup...")

    def data_manager_thread(self):
        thread = threading.current_thread()
        thread.setName("Data Manager")
        while True:
            time.sleep(20)
            ping(thread)
            if self.data_ready:
                if len(self.data_buffer) == 0:
                    print("[WARN] Data buffer is empty")
                    self.data_ready = False
                    continue
                start = datetime.datetime.now()
                print("[INFO] Data is ready, saving & uploading...")
                with self.data_lock:
                    data = self.data_buffer.copy()
                    self.data_buffer.clear()
                    self.data_ready = False
                save_buffer = {
                    "riempimento": data["riempimento"][-1],
                    "timestamp_last_svuotamento": str(config_and_data["last_svuotamento"].isoformat()),
                    "wrong_class_counter": data["wrong_class_counter"][-1]
                }
                # todo send data to server
                # todo send data to mqtt

                with open("data.json", "w") as f:
                    json.dump(save_buffer, f)

                add_lines_csv(data)
                flat_list = [item for sublist in data["images"] for item in sublist]
                helpers.save_images_linux(flat_list, "images")
                print(f"[INFO] Data saved in {(datetime.datetime.now() - start).total_seconds()}s.")
                # if time is 12 pm or 6 pm, upload data
                if datetime.datetime.now().hour in [12, 18]:
                    print("[INFO] Uploading data...")
                    # todo upload
                    print("[INFO] Data uploaded.")

    def pass_data(self, data_dict: dict[str, Any]):
        with self.data_lock:
            self.data_ready = True
            for key, value in data_dict.items():
                self.data_buffer[key] = self.data_buffer.get(key, []) + [value]


def add_lines_csv(data):
    with open("history.csv", "a") as f:
        # if the files exceedes 200 lines, delete the first 100
        # lines = f.readlines()
        # if len(lines) > 200:  # todo check if this works
        #     f.seek(0)
        #     f.writelines(lines[100:])
        #     f.truncate()
        for percentage, timestamp, wrong_class_counter in zip(data["riempimento"], data["timestamp"], data["wrong_class_counter"]):
            f.write(f"{percentage},{timestamp},{wrong_class_counter}\n")


def create_csv_file():
    print("[INFO] Creating csv file:", end=" ", flush=True)
    with open("history.csv", "w") as f:
        f.write("riempimento,timestamp,wrong_class_counter\n")
    print("Done.")


def deconfigure_and_kill(cause):
    print(cause)
    if os.path.exists("config.json"):
        os.remove("config.json")
        print("[INFO] Deleted config.json")
    kill()


def check_config_integrity(config, dont_kill=False):
    default_dict = {"bin_id": int, "current_class": str, "bin_height": int, "bin_threshold": int}
    for key, value_type in default_dict.items():
        if not isinstance(config[key], value_type):
            return deconfigure_and_kill(f"[ERROR] Config file is corrupted, {key} is not a {value_type}, deleting config.json and killing...") if not dont_kill else False
    try:
        bin_id = config["bin_id"]
        current_class = config["current_class"]
        bin_height = config["bin_height"]
        bin_threshold = config["bin_threshold"]
        if current_class not in config_and_data["valid_classes"]:
            return deconfigure_and_kill(f'[ERROR] "{current_class}" is not a valid material, deleting config.json and killing...') if not dont_kill else False
        print("[INFO] Config file is valid.")
        return bin_id, current_class, bin_height, bin_threshold
    except KeyError:
        return deconfigure_and_kill("[ERROR] config.json is corrupted, deleting...") if not dont_kill else False

