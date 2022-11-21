import datetime
import time

from flightshot import pings, kill


def watchdog_thread():
    while True:
        time.sleep(5)
        for key, value in pings.items():
            if (datetime.datetime.now() - value).total_seconds() > 70:
                print(f"[ERROR] Thread [{key.getName()}] is not responding, killing...")
                kill()
            elif not key.is_alive():
                print(f"[ERROR] Thread [{key.getName()}] is not responding, killing...")
                kill()


def ping(name):
    pings[name] = datetime.datetime.now()
