import datetime
import time

import paho.mqtt.client as mqtt

from helpers import kill

topic = "Wick/"
mqtt_host = "3.18.123.221"
mqtt_client_id = "flightshot"
port = 9001


def on_connect(client, userdata, flags, rc):
    print("[INFO] Connected with result code " + str(rc))
    client.subscribe(topic)


def setup_mqtt(ip, client_id="mqtt_user", password="Beam2020", port=1883, timeout=10, connection_timeout=10):
    client: mqtt.Client = None
    start = datetime.datetime.now()
    while (not client or not client.is_connected()) and (datetime.datetime.now() - start).total_seconds() < timeout:
        print("[INFO] Configuring MQTT client:", end=" ", flush=True)
        try:
            client = mqtt.Client(client_id=client_id, clean_session=True, userdata=None, protocol=mqtt.MQTTv311,
                                 transport="tcp")
            client.on_connect = on_connect
            # todo client.username_pw_set(client_id, password)
        except:
            print("\n[ERROR] Error while configuring MQTT client, retrying in 5 seconds...")
            time.sleep(5)
            continue
        try:
            client.connect(ip, port=port, keepalive=0)
        except:
            print("\n[ERROR] Error while connecting to MQTT broker, retrying in 5 seconds...")
            time.sleep(5)
            continue
        start2 = datetime.datetime.now()
        while not client.is_connected() and (datetime.datetime.now() - start2).total_seconds() < connection_timeout:
            print(client.is_connected())
        if not client.is_connected():
            print("\n[ERROR] MQTT connection timed out, retrying in 5 seconds...")
            time.sleep(5)
            continue
        else:
            print("Done.")
    return client


mqtt_client: mqtt.Client = setup_mqtt(mqtt_host, mqtt_client_id, port=port)
