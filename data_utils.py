import datetime
import json
import os
import random
import time

import paho.mqtt.client as mqtt

from flightshot import config_and_data
from mqtt_utils import topic, setup_mqtt, mqtt_client, get_next_message
from helpers import kill


def add_lines_csv(data):
    with open("history.csv", "a") as f:
        for percentage, timestamp, wrong_class_counter in zip(data["riempimento"], data["timestamp"], data["wrong_class_counter"]):
            f.write(f"{percentage},{timestamp},{wrong_class_counter}\n")


def create_csv_file():
    print("[INFO] Creating csv file:", end=" ", flush=True)
    with open("history.csv", "w") as f:
        f.write("riempimento,timestamp,wrong_class_counter\n")
    print("Done.")


# wizard setup
def il_fantastico_viaggio_del_bagarozzo_mark():
    print("[INFO] Getting config through MQTT...")
    try:
        if not mqtt_client.is_connected():
            return print("[ERROR] MQTT client is not connected, exiting wizard...")

        mqtt_client.publish(topic, json.dumps({"bin_id": 51333, "config": True}))

        start = datetime.datetime.now()
        while (datetime.datetime.now() - start).total_seconds() < 10:
            if received_config := get_next_message():
                return received_config

        if not mqtt_client.is_connected():
            return print("[ERROR] MQTT connection lost during wizard setup, exiting wizard...")
    except:
        return print("[ERROR] An error occurred in wizard setup...")


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


def files_setup():
    if not os.path.exists("history.csv"):
        create_csv_file()

    start = datetime.datetime.now()
    if not os.path.exists("config.json"):
        print("[INFO] Trying to get config through MQTT")
        while not (data := il_fantastico_viaggio_del_bagarozzo_mark()) and (datetime.datetime.now() - start).total_seconds() < 60:
            print("[ERROR] Couldn't get config from MQTT, retrying...")
            if not mqtt_client or not mqtt_client.is_connected():
                print("[ERROR] MQTT client is not connected, reinitializing...")
                setup_mqtt()
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
        # make it crash anyway if it can't unpack
        check_config_integrity(data)
        if mqtt_client and mqtt_client.is_connected():
            received = il_fantastico_viaggio_del_bagarozzo_mark()  # todo why does it return null?
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

