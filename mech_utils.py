import time

from adafruit_motor import servo
from board import SCL, SDA
import busio

from adafruit_pca9685 import PCA9685

compartments = []


def setup_compartments(*args):
    global compartments

    # Create the I2C bus interface.
    i2c_bus = busio.I2C(SCL, SDA)

    # Create a simple PCA9685 class instance.
    pca = PCA9685(i2c_bus)

    # Set the PWM frequency to 60hz.
    pca.frequency = 50

    for i in args:
        compartments.append(Compartment(i, pca))


def close_all(tranne_uno=None):
    last_man_standing = compartments[tranne_uno] if tranne_uno is not None else None
    for compartment in compartments:
        if compartment != last_man_standing:
            compartment.close()


def open_compartment(compartment, close_others=True):
    if close_others:
        close_all(compartment)
    compartment.open()


def vibrato(selected_compartment):
    slightly_open = False
    for i in range(20):
        angle = 35 if slightly_open else 45
        slightly_open = not slightly_open
        for compartment in compartments:
            if compartment != selected_compartment:
                compartment.set_angle(angle)
        time.sleep(0.1)


class Compartment:
    def __init__(self, servo_channel, pca):
        self.servo = servo.Servo(pca.channels[servo_channel], min_pulse=600, max_pulse=2400)

    def close(self):
        self.servo.angle = 40

    def open(self):
        self.servo.angle = 120

    def set_angle(self, angle):
        self.servo.angle = angle
