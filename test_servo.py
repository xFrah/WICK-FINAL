import time

from adafruit_motor import servo
from board import SCL, SDA
import busio

from adafruit_pca9685 import PCA9685

# Create the I2C bus interface.
i2c_bus = busio.I2C(SCL, SDA)

# Create a simple PCA9685 class instance.
pca = PCA9685(i2c_bus)

# Set the PWM frequency to 60hz.
pca.frequency = 50

servo0 = servo.Servo(pca.channels[0], min_pulse=600, max_pulse=2400)
servo1 = servo.Servo(pca.channels[1], min_pulse=600, max_pulse=2400)
servo2 = servo.Servo(pca.channels[2], min_pulse=600, max_pulse=2400)

# Set the PWM duty cycle for channel zero to 50%. duty_cycle is 16 bits to match other PWM objects
# but the PCA9685 will only actually give 12 bits of resolution.
#pca.channels[1].duty_cycle = 0x7FFF

while True:
    angle = int(input("Angle: "))
    servo0.angle = angle
    servo1.angle = angle
    servo2.angle = angle
    time.sleep(0.05)
