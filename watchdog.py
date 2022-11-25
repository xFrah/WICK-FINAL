import datetime
import threading

pings: dict[threading.Thread, datetime.datetime] = {}
ignore: set[threading.Thread] = set()


def ping(name):
    pings[name] = datetime.datetime.now()
