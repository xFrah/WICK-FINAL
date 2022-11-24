import datetime
import threading

pings: dict[threading.Thread, datetime.datetime] = {}


def ping(name):
    pings[name] = datetime.datetime.now()
