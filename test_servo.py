import time

from board import SCL, SDA
import busio

from adafruit_pca9685 import PCA9685

# Create the I2C bus interface.
i2c_bus = busio.I2C(0, 0)

# Create a simple PCA9685 class instance.
pca = PCA9685(i2c_bus)

# Set the PWM frequency to 60hz.
pca.frequency = 50

# Set the PWM duty cycle for channel zero to 50%. duty_cycle is 16 bits to match other PWM objects
# but the PCA9685 will only actually give 12 bits of resolution.
pca.channels[0].duty_cycle = 0x7FFF


# We sleep in the loops to give the servo time to move into position.
for i in range(70):
    pca.channels[0].angle = i
    time.sleep(0.03)
for i in range(70)[::-1]:
    pca.channels[0].angle = i
    time.sleep(0.03)