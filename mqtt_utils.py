import datetime
import json
import threading
import time
from typing import Any

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
        #self.client.on_log = on_log
        self.conn_init_timeout = timeout
        self.conn_timeout = connection_timeout
        self.arriving_data_lock = threading.Lock()
        self.data_ready_flag = False
        self.rx_buffer = []
        self.mac = get_mac_address()

    def try_to_connect(self):
        start = datetime.datetime.now()
        while not self.is_connected and (datetime.datetime.now() - start).total_seconds() < self.conn_init_timeout:
            print("[MQTT] Connecting to broker...")
            conn_now = datetime.datetime.now()
            try:
                self.client.connect(self.host, port=self.port)
            except:
                print("[ERROR] Connection failed, retrying...")
                self.try_to_disconnect()
                time.sleep(2)
                continue

            self.client.loop_start()  # start the loop
            print("[MQTT] Subscribing to topic", self.topic)
            try:
                self.client.subscribe(self.topic)
            except:
                print("[ERROR] Subscription failed!")
                self.try_to_disconnect()
                time.sleep(2)
                continue
            while not self.is_connected and (datetime.datetime.now() - conn_now).total_seconds() < self.conn_timeout:
                time.sleep(0.1)
        if not self.is_connected:
            self.try_to_disconnect()
            print("[ERROR] MQTT connection failed!")
        else:
            print("[MQTT] Connected to broker!")

    def connected(self):
        return self.is_connected

    def publish(self, payload):
        self.client.publish(self.topic, payload)

    def data_ready(self):
        return self.data_ready_flag

    def on_disconnect(self, client, userdata, rc):
        self.is_connected = False
        self.client.connected_flag = False
        print("[MQTT] Disconnected, returned code= ", rc)

    def unload_buffer(self):
        """
        If the data is ready, set the data_ready flag to false, and return the data.
        :return: The data that was received from mqtt.
        """
        with self.arriving_data_lock:
            if self.data_ready_flag:
                self.data_ready_flag = False
                if self.rx_buffer:
                    tmp = self.rx_buffer
                    self.rx_buffer = []
                    return tmp
                else:
                    return []
            else:
                return []

    def get_next_message(self, timeout=10):
        """
        "Wait for the data_ready flag to be set, then return the contents of the buffer."

        :param timeout: The amount of time to wait for a message to arrive, defaults to 10
        :return: data in the rx_buffer
        """
        start = datetime.datetime.now()
        while not self.data_ready_flag and (datetime.datetime.now() - start).total_seconds() < timeout:
            time.sleep(0.1)
        return self.unload_buffer()

    def on_message(self, client, userdata, message):
        with self.arriving_data_lock:
            self.rx_buffer.append(message.payload)
            self.data_ready_flag = True
        print("[MQTT] Message received ", str(message.payload.decode("utf-8")))

    def __del__(self):
        self.client.loop_stop()

    def is_for_me_uwu(self, config):
        """
        Check if the packet matches the MAC address of the device, thus confirming that the packet is for this client.

        :param config: dictionarty to check
        :return: The mac address of the device.
        """
        try:
            config = json.loads(config)
        except json.JSONDecodeError:
            print("[IS_FOR_ME] Invalid JSON!")
            return False
        try:
            other_mac = config['bin_id']
            sender_id = config['senderId']
        except KeyError:
            print("[IS_FOR_ME] No bin_id or sender_id!")
            return False
        return config if other_mac == self.mac and sender_id != self.mac else False

    def try_to_disconnect(self):
        """
        It tries to disconnect from the MQTT broker and stop the loop
        """
        try:
            self.client.disconnect()
        except:
            pass
        try:
            self.client.loop_stop()
        except:
            pass
        self.is_connected = False
        self.client.connected_flag = False

    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            self.is_connected = True  # set flag
            self.client.connected_flag = True  # set flag
        else:
            print("[MQTT] Bad connection, returned code= ", rc)