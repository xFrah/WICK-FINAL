import datetime
import json
import time

import paho.mqtt.client as mqtt

established = False


def on_connect_fail(client, userdata, flags, rc):
    print("Connection failed")


def setup_mqtt():
    ############
    def on_message(client, userdata, message):
        print("message received ", str(message.payload.decode("utf-8")))
        print("message topic=", message.topic)
        print("message qos=", message.qos)
        print("message retain flag=", message.retain)

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

    ########################################
    # broker_address="iot.eclipse.org"
    print("creating new instance")
    client = mqtt.Client("test", protocol=mqtt.MQTTv31)  # create new instance
    client.on_message = on_message  # attach function to callback
    client.on_connect = on_connect  # attach function to callback
    client.on_log = on_log
    print("connecting to broker")
    client.connect("3.18.123.221", 9001)  # connect to broker
    #client.loop_start()  # start the loop
    topic = "wick"
    print("Subscribing to topic", topic)
    client.subscribe(topic, qos=2)
    print("Publishing message to topic", topic)
    asd = json.dumps({"bin_id": 51333, "config": True})
    print(asd)
    client.publish(topic, asd, qos=0)
    #time.sleep(10)  # wait
    client.loop_forever()


setup_mqtt()
