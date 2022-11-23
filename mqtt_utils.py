import datetime
import json
import threading
import time

import paho.mqtt.client as mqtt

from helpers import get_mac_address

topic = "wick"
mqtt_host = "stream.lifesensor.cloud"
mqtt_client_id = "Beam1"
port = 9001

established = False
arriving_data_lock = threading.Lock()
data_ready = False
rx_buffer = None


def on_message(client, userdata, message):
    global rx_buffer
    global data_ready
    with arriving_data_lock:
        # print("message received ", str(message.payload.decode("utf-8")))
        rx_buffer = json.loads(message.payload)
        data_ready = True
    print("[MQTT] Message received ", str(message.payload.decode("utf-8")))
    # print("message topic=", message.topic)
    # print("message qos=", message.qos)
    # print("message retain flag=", message.retain)


def get_next_message(timeout=10):
    global rx_buffer
    global data_ready
    start = datetime.datetime.now()
    while not data_ready and (datetime.datetime.now() - start).total_seconds() < timeout:
        time.sleep(0.1)
    if data_ready:
        with arriving_data_lock:
            data_ready = False
            if rx_buffer:
                tmp = rx_buffer
                rx_buffer = None
                return tmp
            else:
                return None
    else:
        return None


def on_connect(client, userdata, flags, rc):
    global established
    if rc == 0:
        established = True  # set flag
        client.connected_flag = True  # set flag
    else:
        print("[MQTT] Bad connection, returned code= ", rc)


def on_log(client, userdata, level, buf):
    print("log: ", buf)


def is_for_me_uwu(config):
    return config["bin_id"] == mac


def try_to_disconnect(client):
    try:
        client.disconnect()
    except:
        pass
    try:
        client.loop_stop()
    except:
        pass


def setup_mqtt(timeout=40, connection_timeout=5):
    global established
    global mqtt_client
    client: mqtt.Client = None
    mqtt_client = None
    established = False
    start = datetime.datetime.now()
    print("[INFO] Initializing MQTT...")
    while (not client or not established) and (datetime.datetime.now() - start).total_seconds() < timeout:
        client = mqtt.Client("test", protocol=mqtt.MQTTv31, transport='websockets')  # create new instance
        client.on_message = on_message  # attach function to callback
        client.on_connect = on_connect  # attach function to callback
        # client.on_log = on_log
        print("[MQTT] Connecting to broker...")
        conn_now = datetime.datetime.now()

        try:
            client.connect(mqtt_host, port=port)
        except:
            print("[ERROR] Connection failed, retrying...")
            try_to_disconnect(client)
            time.sleep(2)
            continue

        client.loop_start()  # start the loop
        print("[MQTT] Subscribing to topic", topic)
        try:
            client.subscribe(topic)
        except:
            print("[ERROR] Subscription failed!")
            try_to_disconnect(client)
            time.sleep(2)
            continue
        while not established and (datetime.datetime.now() - conn_now).total_seconds() < connection_timeout:
            time.sleep(0.1)
    if established:
        print("[MQTT] Received CONNACK!!! MQTT connection established!")
        mqtt_client = client
        return client
    else:
        try_to_disconnect(client)
        return print("[ERROR] MQTT connection failed!")


mac = get_mac_address()
mqtt_client: mqtt.Client = setup_mqtt()

