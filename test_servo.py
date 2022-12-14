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

servos = [servo.Servo(pca.channels[0], min_pulse=600, max_pulse=2400),
          servo.Servo(pca.channels[1], min_pulse=600, max_pulse=2400),
          servo.Servo(pca.channels[2], min_pulse=600, max_pulse=2400),
          servo.Servo(pca.channels[3], min_pulse=600, max_pulse=2400)
          ]


def vibrato(servo):
    slightly_open = False
    for i in range(20):
        angle = 35 if slightly_open else 45
        slightly_open = not slightly_open
        for t_servo in servos:
            if servo != t_servo:
                t_servo.angle = angle
        time.sleep(0.1)


def close_all():
    for servo in servos:
        servo.angle = 40


def open_all():
    for servo in servos:
        servo.angle = 120


def change_open(servo):
    close_all()
    if servo is not None:
        servo.angle = 120


def one_angle(servo, angle):
    servo.angle = angle


# Set the PWM duty cycle for channel zero to 50%. duty_cycle is 16 bits to match other PWM objects
# but the PCA9685 will only actually give 12 bits of resolution.
# pca.channels[1].duty_cycle = 0x7FFF

while True:
    chn = input("Servo to open: ")
    if chn.startswith("vibrato"):
        vibrato(servos[int(chn[-1])])
    elif chn.startswith("closeall"):
        close_all()
    elif chn.startswith("openall"):
        open_all()
    elif chn.startswith("angle"):
        args = chn.split(" ")
        print(args)
        one_angle(servos[int(args[1])], int(args[2]))
    else:
        change_open(servos[int(chn)] if chn != "None" else None)
    time.sleep(0.05)
