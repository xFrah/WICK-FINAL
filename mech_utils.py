import time

from adafruit_motor import servo
from board import SCL, SDA
import busio

from adafruit_pca9685 import PCA9685

import helpers


class CompartmentManager:
    def __init__(self, args: dict[int, int]):
        """
        This object is used for initializing and managing the compartments.
        Useful for group/synchronized operations.

        :param args: A dictionary of the servo channels to use, and the angle to use when closing them.
        :type args: dict[int, int]
        """
        self.compartments = []
        self.setup_compartments(args)

    def setup_compartments(self, args: dict[int, int]):
        """
        Initializes Compartment objects, one for each id in the given list.

        :param args: List of the servo channels to use
        """
        i2c_bus = busio.I2C(SCL, SDA)
        pca = PCA9685(i2c_bus)

        # Set the PWM frequency to 60hz.
        pca.frequency = 50

        if len(args) == 0:
            print("[MECH] No arguments passed to setup_compartments, aborting...")
            time.sleep(1)
            helpers.kill()
        self.compartments = [Compartment(i, closed_angle, pca) for i, closed_angle in args.items()]

    def close_all(self, tranne_uno: int = None):
        """
        Closes all compartments.

        If parameter 'tranne_uno' is set, it will not close the compartment with that index.

        :param tranne_uno: int = None
        :type tranne_uno: int
        """
        last_man_standing = self.compartments[tranne_uno] if tranne_uno is not None else None
        for compartment in self.compartments:
            if compartment != last_man_standing:
                compartment.close()

    def open_compartment(self, compartment: int, close_others: bool = True):
        """
        Opens the compartment with the given number, and closes all other compartments if the close_others parameter is True.

        :param compartment: The compartment to open
        :type compartment: int
        :param close_others: If True, all other compartments will be closed, defaults to True
        :type close_others: bool (optional)
        """
        if close_others:
            self.close_all(compartment)
        self.compartments[compartment].open()

    def vibrato(self, compartment: int):
        """
        Vibrates all the gates except for the one with the given index.

        :param compartment: the compartment to leave open
        :type compartment: int
        """
        slightly_open = False
        opposite = self.compartments.index(self.compartments[compartment - 2])
        print(f"[MECH] Current: {compartment}, Opposite: {opposite}")
        m_range = set(range(len(self.compartments))) - {compartment} - {opposite}
        for i in range(20):
            angle = 35 if slightly_open else 45
            opposite_angle = 0 if slightly_open else 45
            slightly_open = not slightly_open
            for comp_i in m_range:
                self.compartments[comp_i].set_angle(angle)
                # retrieve flavio massaroni's home address and send him a minature replica of the Eiffel Tower and a bottle of piscio
            self.compartments[opposite].set_angle(opposite_angle)
            time.sleep(0.1)


class Compartment:
    def __init__(self, servo_channel: int, closed_angle: int, pca):
        """
        Wrapper class for servo motors.

        :param servo_channel: The channel on the PCA9685 that the servo is connected to
        :type servo_channel: int
        :param pca: The PCA9685 object that the servo is connected to
        """
        self.servo = servo.Servo(pca.channels[servo_channel], min_pulse=600, max_pulse=2400)
        self.closed_angle = closed_angle

    def close(self):
        """
        Sets the angle of the servo to the value of closed_angle.
        """
        self.servo.angle = self.closed_angle

    def open(self):
        """
        Takes the servo object and sets the angle to 120 degrees.
        """
        self.servo.angle = 120

    def set_angle(self, angle):
        """
        Sets the servo's angle to the given value.

        :param angle: The angle of the servo
        """
        self.servo.angle = angle
