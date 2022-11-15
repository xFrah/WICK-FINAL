import datetime
import time

from vl53l5cx.vl53l5cx import VL53L5CX

driver = VL53L5CX()

alive = driver.is_alive()
if not alive:
    raise IOError("VL53L5CX Device is not alive")

print("Initialising...")
t = time.time()
driver.init()
print(f"Initialised ({time.time() - t:.1f}s)")

driver.set_ranging_frequency_hz(60)
driver.set_integration_time_ms(5)
print(f"Ranging frequency: {driver.get_ranging_frequency_hz()} Hz")
print(f"Integration time: {driver.get_integration_time_ms()} ms")

# Ranging:
driver.start_ranging()


count = 0
start = datetime.datetime.now()
while True:
    if driver.check_data_ready():
        ranging_data = driver.get_ranging_data()

        count += 1
        if count == 100:
            print("FPS: ", 100 / (datetime.datetime.now() - start).total_seconds())
            start = datetime.datetime.now()
            count = 0

        # for i in range(16):
        #     print(f"Zone : {i: >3d}, "
        #           f"Status : {ranging_data.target_status[driver.nb_target_per_zone * i]: >3d}, "
        #           f"Distance : {ranging_data.distance_mm[driver.nb_target_per_zone * i]: >4.0f} mm")

    time.sleep(0.005)
