import datetime
import json
import threading
import time

import paho.mqtt.client as mqtt

from helpers import kill

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
        rx_buffer = json.load(message.payload)
        print("message received ", str(message.payload.decode("utf-8")))
        data_ready = True
    print("message received ", str(message.payload.decode("utf-8")))
    print("message topic=", message.topic)
    print("message qos=", message.qos)
    print("message retain flag=", message.retain)


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
        print("connected OK Returned code=", rc)
        # client.subscribe(topic)
    else:
        print("Bad connection Returned code= ", rc)


def on_log(client, userdata, level, buf):
    print("log: ", buf)


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
    client: mqtt.Client = None
    start = datetime.datetime.now()
    print("[INFO] Initializing MQTT...")
    while (not client or not established) and (datetime.datetime.now() - start).total_seconds() < timeout:
        client = mqtt.Client("test", protocol=mqtt.MQTTv31, transport='websockets')  # create new instance
        client.on_message = on_message  # attach function to callback
        client.on_connect = on_connect  # attach function to callback
        client.on_log = on_log
        print("[INFO] Connecting to broker...")
        conn_now = datetime.datetime.now()

        try:
            client.connect(mqtt_host, port=port)
        except:
            print("[ERROR] Connection failed, retrying...")
            try_to_disconnect(client)
            time.sleep(2)
            continue

        client.loop_start()  # start the loop
        print("[INFO] Subscribing to topic", topic)
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
        print("[INFO] Received CONNACK!!! MQTT connection established!")
        return client
    else:
        try_to_disconnect(client)
        return print("[ERROR] MQTT connection failed!")


mqtt_client: mqtt.Client = setup_mqtt()
