import datetime
import json
import os
import random
import time

import paho.mqtt.client as mqtt

from flightshot import config_and_data, mqtt_client
from mqtt_utils import topic, setup_mqtt
from helpers import kill

received_config = None


def add_lines_csv(data):
    with open("history.csv", "a") as f:
        for percentage, timestamp, wrong_class_counter in zip(data["riempimento"], data["timestamp"], data["wrong_class_counter"]):
            f.write(f"{percentage},{timestamp},{wrong_class_counter}\n")


def create_csv_file():
    print("[INFO] Creating csv file:", end=" ", flush=True)
    with open("history.csv", "w") as f:
        f.write("riempimento,timestamp,wrong_class_counter\n")
    print("Done.")


def on_message(client, userdata, msg):
    global received_config
    if received_config is None:
        data = json.loads(msg.payload)
        if "bin_id" in data:
            if data["bin_id"] == config_and_data["bin_id"]:
                received_config = data


# wizard setup
def il_fantastico_viaggio_del_bagarozzo_mark(bin_id):
    print("[INFO] Getting config through MQTT:", end=" ", flush=True)
    try:
        mqtt_client.on_message = on_message
        if not mqtt_client.is_connected():
            return print("[ERROR] MQTT client is not connected, exiting wizard...")

        mqtt_client.publish(topic, json.dumps({"bin_id": bin_id, "cfg": True}))

        start = datetime.datetime.now()
        while not received_config and mqtt_client.is_connected() and (datetime.datetime.now() - start).total_seconds() < 10:
            pass

        if not mqtt_client.is_connected():
            return print("[ERROR] MQTT connection lost during wizard setup, exiting wizard...")
    except:
        return print("[ERROR] An error occurred in wizard setup...")

    print("Done.")
    return received_config


def deconfigure_and_kill(cause):
    print(cause)
    if os.path.exists("config.json"):
        os.remove("config.json")
        print("[INFO] Deleted config.json")
    kill()


def files_setup():
    default_dict = {"bin_id": int, "current_class": str, "bin_height": int, "bin_threshold": int}

    if not os.path.exists("history.csv"):
        create_csv_file()

    start = datetime.datetime.now()
    if not os.path.exists("config.json"):
        print("[INFO] Trying to get config through MQTT")
        bin_id = random.randint(0, 65534)
        while not (data := il_fantastico_viaggio_del_bagarozzo_mark(bin_id)) and (datetime.datetime.now() - start).total_seconds() < 60:
            print("[ERROR] Couldn't get config from MQTT, retrying...")
            if not mqtt_client or not mqtt_client.is_connected():
                print("[ERROR] MQTT client is not connected, reinitializing...")
                # todo setup_mqtt()
            time.sleep(5)
        if not data:
            print("[ERROR] Wizard failed to get config through MQTT, killing...")
            kill()
    else:
        with open("config.json", "r") as f:
            data = json.load(f)
        try:
            bin_id = data["bin_id"]
        except KeyError:
            return deconfigure_and_kill("[ERROR] config.json is corrupted, deleting...")

        if mqtt_client and mqtt_client.is_connected():
            # todo why does it return null?
            received = il_fantastico_viaggio_del_bagarozzo_mark(bin_id)
            if received:
                if received == data:
                    print("[INFO] Config is up to date.")
                else:
                    print("[INFO] Config is outdated, updating...", end=" ", flush=True)
                    with open("config.json", "w") as f:
                        json.dump(data, f)
                    data = received
                    print("Done.")
            else:
                print("[ERROR] Wizard failed to get config through MQTT.")
        else:
            print("[INFO] MQTT client is not connected, skipping config update.")
        for key, value_type in default_dict.items():
            if not isinstance(data[key], value_type):
                deconfigure_and_kill(f"[ERROR] Config file is corrupted, {key} is not a {value_type}, deleting config.json and killing...")

    try:
        config_and_data["current_class"] = data["current_class"]
        config_and_data["bin_height"] = data["bin_height"]
        config_and_data["bin_threshold"] = data["bin_threshold"]
    except KeyError:
        deconfigure_and_kill("[ERROR] Configuration data is corrupted, deleting config.json and killing...")

    if data["current_class"] not in config_and_data["valid_classes"]:
        deconfigure_and_kill(f'[ERROR] "{config_and_data["current_class"]}" is not a valid material, deleting config.json and killing...')

    printable_list = "\n".join(["- " + key + ": " + str(value) for key, value in data.items()])
    print(f"[INFO] Configuration data:\n{printable_list}")

