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

# Ranging:
driver.start_ranging()
print(driver.nb_target_per_zone)

while True:
    if driver.check_data_ready():
        ranging_data = driver.get_ranging_data()

        for i in range(16):
            print(f"Zone : {i: >3d}, "
                  f"Status : {ranging_data.target_status[driver.nb_target_per_zone * i]: >3d}, "
                  f"Distance : {ranging_data.distance_mm[driver.nb_target_per_zone * i]: >4.0f} mm")

        print("")

    time.sleep(0.005)
