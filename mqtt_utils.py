import datetime
import json
import threading
import time

import paho.mqtt.client as mqtt

from helpers import get_mac_address


def on_log(client, userdata, level, buf):
    print("log: ", buf)


class MQTTExtendedClient:
    def __init__(self, host, topic, port=1883, timeout=30, connection_timeout=5):
        self.host = host
        self.port = port
        self.topic = topic
        self.is_connected = False
        self.client: mqtt.Client = None
        print("[INFO] Initializing MQTT...")
        self.client = mqtt.Client("WICK_MQTT_CLIENT", protocol=mqtt.MQTTv31, transport='websockets')  # create new instance
        self.client.on_message = self.on_message
        self.client.on_connect = self.on_connect
        self.client.on_disconnect = self.on_disconnect
        # client.on_log = on_log
        self.conn_init_timeout = timeout
        self.conn_timeout = connection_timeout
        self.arriving_data_lock = threading.Lock()
        self.data_ready = False
        self.rx_buffer = None
        self.mac = get_mac_address()

    def try_to_connect(self):
        start = datetime.datetime.now()
        while not self.is_connected and (datetime.datetime.now() - start).total_seconds() < self.conn_init_timeout:
            print("[MQTT] Connecting to broker...")
            conn_now = datetime.datetime.now()
            try:
                self.client.connect(mqtt_host, port=port)
            except:
                print("[ERROR] Connection failed, retrying...")
                self.try_to_disconnect()
                time.sleep(2)
                continue

            self.client.loop_start()  # start the loop
            print("[MQTT] Subscribing to topic", topic)
            try:
                self.client.subscribe(topic)
            except:
                print("[ERROR] Subscription failed!")
                self.try_to_disconnect()
                time.sleep(2)
                continue
            while self.is_connected and (datetime.datetime.now() - conn_now).total_seconds() < self.conn_timeout:
                time.sleep(0.1)
        if not self.is_connected:
            self.try_to_disconnect()
            print("[ERROR] MQTT connection failed!")

    def connected(self):
        return self.is_connected

    def publish(self, payload):
        self.client.publish(self.topic, payload)

    def data_ready(self):
        return self.data_ready

    def on_disconnect(self, client, userdata, rc):
        self.is_connected = False
        self.client.connected_flag = False
        print("[MQTT] Disconnected, returned code= ", rc)

    def unload_buffer(self):
        with self.arriving_data_lock:
            if self.data_ready:
                self.data_ready = False
                if self.rx_buffer:
                    tmp = self.rx_buffer
                    self.rx_buffer = None
                    return tmp
                else:
                    return None
            else:
                return None

    def get_next_message(self, timeout=10):
        start = datetime.datetime.now()
        while not self.data_ready and (datetime.datetime.now() - start).total_seconds() < timeout:
            time.sleep(0.1)
        return self.unload_buffer()

    def on_message(self, client, userdata, message):
        py_var = json.loads(message.payload)
        # todo activate this
        # if not is_for_me_uwu(py_var):
        #     return
        with self.arriving_data_lock:
            self.rx_buffer = py_var
            self.data_ready = True
        print("[MQTT] Message received ", str(message.payload.decode("utf-8")))

    def __del__(self):
        self.client.loop_stop()

    def is_for_me_uwu(self, config):
        try:
            if config['mac'] == self.mac:
                return True
            else:
                return False
        except KeyError:
            return False

    def try_to_disconnect(self):
        try:
            self.client.disconnect()
        except:
            pass
        try:
            self.client.loop_stop()
        except:
            pass

    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            self.is_connected = True  # set flag
            self.client.connected_flag = True  # set flag
        else:
            print("[MQTT] Bad connection, returned code= ", rc)


topic = "wick"
mqtt_host = "stream.lifesensor.cloud"
mqtt_client_id = "Beam1"
port = 9001

valid = {"bin_id": int, "current_class": str, "bin_height": int, "bin_threshold": int}

mqtt_client: mqtt.Client = MQTTExtendedClient(mqtt_host, topic, port=port)
