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

servos = [servo.Servo(pca.channels[i], min_pulse=600, max_pulse=2400) for i in range(3)]

open_servo = None

def change_open(servo):
    global open_servo
    if open_servo is not None:
        open_servo.angle = 30
    if servo is not None:
        open_servo = servo
        servo.angle = 120
    else:
        open_servo = None

# Set the PWM duty cycle for channel zero to 50%. duty_cycle is 16 bits to match other PWM objects
# but the PCA9685 will only actually give 12 bits of resolution.
#pca.channels[1].duty_cycle = 0x7FFF

while True:
    chn = int(input("Servo to open: "))
    change_open(servos[chn] if chn != "None" else None)
    time.sleep(0.05)
