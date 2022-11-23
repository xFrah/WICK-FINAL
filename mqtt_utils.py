import datetime
import time

import paho.mqtt.client as mqtt

from helpers import kill

topic = "Wick/"
mqtt_host = "stream.lifesensor.cloud"
mqtt_client_id = "Beam1"
port = 9001

established = False


def on_connect(client, userdata, flags, rc):
    global established
    if rc == 0:
        established = True  # set flag
        print("connected OK Returned code=", rc)
        # client.subscribe(topic)
    else:
        print("Bad connection Returned code= ", rc)


def on_connect_fail(client, userdata, flags, rc):
    print("Connection failed")


def setup_mqtt(ip, client_id="mqtt_user", password="Gaspardo1801", port=1883, timeout=10, connection_timeout=100000):
    client: mqtt.Client = None
    start = datetime.datetime.now()
    while (not client or not established) and (datetime.datetime.now() - start).total_seconds() < timeout:
        print("[INFO] Configuring MQTT client:", end=" ", flush=True)
        try:
            client = mqtt.Client(client_id=client_id)
            client.on_connect = on_connect
            client.on_connect_fail = on_connect_fail
            client.username_pw_set(client_id, password)
        except:
            print("\n[ERROR] Error while configuring MQTT client, retrying in 5 seconds...")
            time.sleep(5)
            continue
        try:
            client.loop_start()
            print(client.connect(ip, port=port, keepalive=60))
            print(client.subscribe(topic))
            #client.loop_forever()
        except:
            print("\n[ERROR] Error while connecting to MQTT broker, retrying in 5 seconds...")
            time.sleep(5)
            continue
        start2 = datetime.datetime.now()
        while not established and (datetime.datetime.now() - start2).total_seconds() < connection_timeout:
            time.sleep(0.1)
        if not established:
            print("\n[ERROR] MQTT connection timed out, retrying in 5 seconds...")
            time.sleep(5)
            continue
        else:
            print("Done.")
    return client


mqtt_client: mqtt.Client = setup_mqtt(mqtt_host, mqtt_client_id, port=port)
