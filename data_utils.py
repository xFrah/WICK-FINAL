import datetime
import json
import os
import threading
import time
from typing import Any

import paho.mqtt.client as mqtt
from ftplib import FTP

import helpers
from helpers import kill
from sftp_utils import SFTP
from watchdog import ping

config_and_data = {
    "name": None,
    "target_distance": 150,
    "current_class": None,
    "wrong_class_counter": 0,
    "last_svuotamento": datetime.datetime.now(),
    "bin_id": None,
    "bin_height": None,
    "bin_threshold": None,
    "label_dict": {0: "plastic", 1: "paper"},
    "valid_classes": ["plastic", "paper"]
}


def update_cached_config(data):
    try:
        config_and_data["name"] = data["name"]
        config_and_data["bin_id"] = data["bin_id"]
        config_and_data["bin_height"] = data["bin_height"]
        config_and_data["bin_threshold"] = data["bin_threshold"]
        config_and_data["current_class"] = data["current_class"]
    except KeyError:
        deconfigure_and_kill("[ERROR] config.json is corrupted, deleting...")
    print("[INFO] Set cached config")


class DataManager:

    def __init__(self, mqtt_client: mqtt.Client):
        """
        Saves data to local and cloud.
        """
        self.ftp_client: SFTP = None
        self.mqtt_client = mqtt_client
        self.data_lock = threading.Lock()
        self.data_ready = False
        self.data_buffer: dict[str, Any] = {}
        self.files_setup()
        self.data_manager_thread = threading.Thread(target=self.data_manager_thread)
        self.data_manager_thread.start()

    def files_setup(self):
        """
        Creates config.json if it doesn't exist or updates it if it is outdated.
        """
        if not os.path.exists("history.csv"):
            create_csv_file()

        if not os.path.exists("config.json"):
            print("[INFO] Trying to get config through MQTT")
            data = None
            start = datetime.datetime.now()
            while (datetime.datetime.now() - start).total_seconds() < 60:
                data = self.il_fantastico_viaggio_del_bagarozzo_mark()
                if not data:
                    continue
                elif check_config_integrity(data):
                    break
                time.sleep(2)
                #print("[ERROR] Couldn't get config from MQTT, retrying...")
                #if not self.mqtt_client.connected():
                #    print("[ERROR] MQTT client is not connected, reinitializing...")
                    # todo reinitialize setup_mqtt()
            if not data:
                print("[ERROR] Wizard failed to get config through MQTT, killing...")
                kill()
            else:
                print("[INFO] Wizard got config through MQTT, saving to config.json")
                with open("config.json", "w") as f:
                    json.dump(data, f)
                update_cached_config(data)
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
                        update_cached_config(data)
                    else:
                        print("[ERROR] Downloaded config is corrupted, not updating...")
                else:
                    print("[ERROR] Wizard failed to get config through MQTT.")
            else:
                print("[INFO] MQTT client is not connected, skipping config update.")

        printable_list = "\n".join(["- " + key + ": " + str(value) for key, value in data.items()])
        print(f"[INFO] Configuration data:\n{printable_list}")

    def il_fantastico_viaggio_del_bagarozzo_mark(self):
        """
        It gets the config from the MQTT server
        :return: The received config.
        """
        print("[INFO] Getting config through MQTT...")
        try:
            if not self.mqtt_client.connected():
                return print("[ERROR] MQTT client is not connected, exiting wizard...")

            try:
                self.mqtt_client.publish(json.dumps({"bin_id": helpers.get_mac_address(), "config": True}))
            except:
                return print("[ERROR] An error occurred while publishing MQTT packet, exiting wizard...")

            start = datetime.datetime.now()
            while (datetime.datetime.now() - start).total_seconds() < 10:
                if self.mqtt_client.data_ready():
                    received_config = self.mqtt_client.unload_buffer()
                    return received_config

            if not self.mqtt_client.connected():
                return print("[ERROR] MQTT connection lost during wizard setup, exiting wizard...")
        except Exception as e:
            return print(f"[ERROR] An error occurred in wizard setup... \n{e}")

    def data_manager_thread(self):
        """
        Thread that continuously checks if there is data to be sent or saved, if there is, it does the deed.
        """
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
                    "name": config_and_data["name"],
                    "bin_id": helpers.get_mac_address(),
                    "filling": data["riempimento"][-1],
                    "timestamp_last_svuotamento": str(config_and_data["last_svuotamento"].isoformat()),
                    "wrong_class_counter": data["wrong_class_counter"][-1],
                    "current_class": config_and_data["current_class"],
                    "config": False
                }
                self.mqtt_client.publish(json.dumps(save_buffer))

                with open("data.json", "w") as f:
                    json.dump(save_buffer, f)

                add_lines_csv(data)
                flat_list = [item for sublist in data["images"] for item in sublist]
                helpers.save_images_linux(flat_list, "images")
                print(f"[INFO] Data saved in {(datetime.datetime.now() - start).total_seconds()}s.")
                # if time is 12 pm or 6 pm, upload data
                # if datetime.datetime.now().hour in [12, 17]:
                # print("[INFO] Uploading data...")
                # self.upload_to_ftp() # this makes the thread get killed by the watchdog, because no pings
                # print("[INFO] Data uploaded.")

    def pass_data(self, data_dict: dict[str, Any]):
        """
        It takes a dictionary of data, and updates the data buffer with it.

        :param data_dict: A dictionary of data. Keys must be strings, and the values can be anything.
        :type data_dict: dict[str, Any]
        """
        with self.data_lock:
            self.data_ready = True
            for key, value in data_dict.items():
                self.data_buffer[key] = self.data_buffer.get(key, []) + [value]

    def connect_to_ftp(self):
        """
        It connects to the FTP server.
        """
        self.ftp_client = SFTP(hostname="51.68.231.173", username="ubuntu", password="5xNbsHbAy9jf", port=22)
        self.ftp_client.connect()

    def upload_to_ftp(self):
        """
        It uploads the data to the FTP server.
        """
        print("[INFO] Uploading data to FTP...")
        if not self.ftp_client:
            print("[INFO] Initializing FTP client and connecting...")
            self.connect_to_ftp()

        imlist = os.listdir("images")
        errors = self.ftp_client.upload_files(imlist, "images", "/home/ubuntu/images")
        print(f"\n[INFO] Uploaded {len(imlist) - errors} images out of {len(imlist)}.")


def add_lines_csv(data: dict[str, Any]):
    """
    If the file exceeds 200 lines, delete the first 100 lines

    :param data: a dictionary containing the following keys: "riempimento", "wrong_class_counter", "images"
    :type data: dict[str, Any]
    """
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
    """
    It creates a csv file called history.csv and writes the header of the file
    """
    print("[INFO] Creating csv file:", end=" ", flush=True)
    with open("history.csv", "w") as f:
        f.write("riempimento,timestamp,wrong_class_counter\n")
    print("Done.")


def deconfigure_and_kill(cause: str):
    """
    It deletes the config.json file and then kills the program

    :param cause: The reason for the error
    :type cause: str
    """
    print(cause)
    if os.path.exists("config.json"):
        os.remove("config.json")
        print("[INFO] Deleted config.json")
    kill()


def check_config_integrity(config, dont_kill=False):
    """
    If the config file is valid, return resulting tuple. If the config file is invalid, delete it and kill the program, unless dont_kill==True.

    :param config: The config.json file
    :param dont_kill: If True, the program will not kill itself if the config file is corrupted, defaults to False (optional)
    :return: the bin_id, current_class, bin_height, and bin_threshold.
    """
    default_dict = {"name": str, "bin_id": int, "current_class": str, "bin_height": int, "bin_threshold": int}
    for key, value_type in default_dict.items():
        if key not in config:
            return deconfigure_and_kill(f"[ERROR] {key} not found in config.json") if not dont_kill else False
        if not isinstance(config[key], value_type):
            return deconfigure_and_kill(f"[ERROR] Config file is corrupted, {key} is not a {value_type}, deleting config.json and killing...") if not dont_kill else False
    try:
        name = config["name"]
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
