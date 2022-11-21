import datetime
from flightshot import pings


def ping(name):
    pings[name] = datetime.datetime.now()

