import datetime

pings: dict[threading.Thread, datetime.datetime] = {}

def ping(name):
    pings[name] = datetime.datetime.now()

