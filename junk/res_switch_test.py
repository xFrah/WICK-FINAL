import datetime
import time

import vl53l5cx_ctypes as vl53l5cx

def tof_setup():
    print("[INFO] Uploading firmware, please wait...")
    vl53 = vl53l5cx.VL53L5CX()
    print("[INFO] Done!")
    vl53.set_resolution(4 * 4)
    vl53.set_ranging_frequency_hz(60)
    vl53.set_integration_time_ms(10)
    vl53.start_ranging()
    return vl53

vl53 = tof_setup()
time.sleep(2)

start = datetime.datetime.now()
vl53.set_resolution(8 * 8)
vl53.set_ranging_frequency_hz(15)
vl53.set_integration_time_ms(10)
print(f"[INFO] Switch duration {(datetime.datetime.now() - start).total_seconds()}s")
start = datetime.datetime.now()
vl53.set_resolution(8 * 8)
vl53.set_ranging_frequency_hz(15)
vl53.set_integration_time_ms(10)
print(f"[INFO] Switch duration {(datetime.datetime.now() - start).total_seconds()}s")
start = datetime.datetime.now()
vl53.set_resolution(8 * 8)
vl53.set_ranging_frequency_hz(15)
vl53.set_integration_time_ms(10)
print(f"[INFO] Switch duration {(datetime.datetime.now() - start).total_seconds()}s")
start = datetime.datetime.now()
vl53.set_resolution(8 * 8)
vl53.set_ranging_frequency_hz(15)
vl53.set_integration_time_ms(10)
print(f"[INFO] Switch duration {(datetime.datetime.now() - start).total_seconds()}s")
#print(f"[INFO] Resolution: {vl53.get_resolution()}, Frequency: {vl53.get_ranging_frequency_hz()}, Integration: {vl53.get_integration_time_ms()}")

while True:
    if vl53.data_ready():
        data = vl53.get_data()
