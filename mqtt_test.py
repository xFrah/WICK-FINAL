import datetime
import time

import paho.mqtt.client as mqtt

established = False
topic = "Wick/"
mqtt_host = "stream.lifesensor.cloud"
mqtt_client_id = "Beam1"
port = 9001


def on_connect(client, userdata, flags, rc):
    global established
    if rc == 0:
        established = True  # set flag
        client.connected_flag = True  # set flag
        print("connected OK Returned code=", rc)
        # client.subscribe(topic)
    else:
        print("Bad connection Returned code= ", rc)


def on_connect_fail(client, userdata, flags, rc):
    print("Connection failed")


def setup_mqtt(ip, client_id="mqtt_user", password="Gaspardo1801", port=1883, timeout=10, connection_timeout=100000):
    ############
    def on_message(client, userdata, message):
        print("message received ", str(message.payload.decode("utf-8")))
        print("message topic=", message.topic)
        print("message qos=", message.qos)
        print("message retain flag=", message.retain)

    def on_connect(client, userdata, message):
        print("Connected to MQTT broker")

    ########################################
    broker_address = "http://stream.lifesensor.cloud"
    topic = "Wick/"
    # broker_address="iot.eclipse.org"
    print("creating new instance")
    client = mqtt.Client("P1")  # create new instance
    client.on_message = on_message  # attach function to callback
    client.on_connect = on_connect  # attach function to callback
    print("connecting to broker")
    client.connect(broker_address)  # connect to broker
    client.loop_start()  # start the loop
    print("Subscribing to topic", topic)
    client.subscribe(topic)
    print("Publishing message to topic", topic)
    client.publish(topic, "OFF")
    time.sleep(4)  # wait
    client.loop_stop()  # stop the loop


setup_mqtt("stream.lifesensor.cloud", "Beam1", "Gaspardo1801", 9001, 10, 100000)
