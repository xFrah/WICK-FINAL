import datetime
import time

import paho.mqtt.client as mqtt

established = False
topic = "Wick/"
broker_address = "broker.hivemq.com"
mqtt_client_id = "Beam1"
port = 1883


def on_connect(userdata, flags, result):
    global established
    if result == 0:
        established = True  # set flag
        #client.connected_flag = True  # set flag
        print("connected OK Returned code=", result)
        # client.subscribe(topic)
    else:
        print("Bad connection Returned code= ", result)


def on_connect_fail(client, userdata, flags, rc):
    print("Connection failed")


def setup_mqtt():
    ############
    def on_message(client, userdata, message):
        print("message received ", str(message.payload.decode("utf-8")))
        print("message topic=", message.topic)
        print("message qos=", message.qos)
        print("message retain flag=", message.retain)

    def on_connect(client, userdata, message):
        print("Connected to MQTT broker")

    def on_log(client, userdata, level, buf):
        print("log: ", buf)

    ########################################
    topic = "Wick/"
    # broker_address="iot.eclipse.org"
    print("creating new instance")
    client = mqtt.Client("P1")  # create new instance
    client.on_message = on_message  # attach function to callback
    client.on_connect = on_connect  # attach function to callback
    client.on_log = on_log
    print("connecting to broker")
    client.connect(broker_address, port)  # connect to broker
    client.loop_start()  # start the loop
    print("Subscribing to topic", topic)
    client.subscribe(topic)
    print("Publishing message to topic", topic)
    client.publish(topic, "OFF")
    time.sleep(4)  # wait
    client.loop_stop()  # stop the loop


setup_mqtt()
