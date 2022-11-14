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


# function to reshape list in 4x4 matrix
def reshape_list(data):
    return [data[i:i + 4] for i in range(0, len(data), 4)]


# function to plot 3d data from sensor VL53L5CX
def plot_3d_data(data):
    import matplotlib.pyplot as plt
    from mpl_toolkits.mplot3d import Axes3D

    fig = plt.figure()
    ax = fig.add_subplot(111, projection='3d')
    ax.scatter(data[:, 0], data[:, 1], data[:, 2], c=data[:, 2], marker='o')
    ax.set_xlabel('X Label')
    ax.set_ylabel('Y Label')
    ax.set_zlabel('Z Label')
    # get plt as matrix
    fig.canvas.draw()
    plt.show()


# Ranging:
driver.start_ranging()

previous_time = 0
loop = 0
while loop < 10:
    if driver.check_data_ready():
        ranging_data = driver.get_ranging_data()

        # As the sensor is set in 4x4 mode by default, we have a total
        # of 16 zones to print. For this example, only the data of first zone are
        # print
        now = time.time()
        if previous_time != 0:
            time_to_get_new_data = now - previous_time
            print(f"Print data no : {driver.streamcount: >3d} ({time_to_get_new_data * 1000:.1f}ms)")
        else:
            print(f"Print data no : {driver.streamcount: >3d}")

        for i in range(16):
            print(f"Zone {i: >2d} : {ranging_data[i]: >5d} mm")
            print(f"Zone : {i: >3d}, "
                  f"Status : {ranging_data.target_status[driver.nb_target_per_zone * i]: >3d}, "
                  f"Distance : {ranging_data.distance_mm[driver.nb_target_per_zone * i]: >4.0f} mm")

        print("")

        previous_time = now
        loop += 1

    time.sleep(0.005)
