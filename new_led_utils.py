#!/usr/bin/env python3
# NeoPixel library strandtest example
# Author: Tony DiCola (tony@tonydicola.com)
#
# Direct port of the Arduino NeoPixel library strandtest example.  Showcases
# various animations on a strip of NeoPixels.
import threading
import time
from rpi_ws281x import PixelStrip, Color


# LED strip configuration:


class LEDs:
    def __init__(self):
        self.LED_COUNT = 24  # Number of LED pixels.
        self.LED_PIN = 18  # GPIO pin connected to the pixels (18 uses PWM!).
        # self.LED_PIN = 10        # GPIO pin connected to the pixels (10 uses SPI /dev/spidev0.0).
        self.LED_FREQ_HZ = 800000  # LED signal frequency in hertz (usually 800khz)
        self.LED_DMA = 10  # DMA channel to use for generating signal (try 10)
        self.LED_BRIGHTNESS = 255  # Set to 0 for darkest and 255 for brightest
        self.LED_INVERT = False  # True to invert the signal (when using NPN transistor level shift)
        self.LED_CHANNEL = 0  # set to '1' for GPIOs 13, 19, 41, 45 or 53
        self.loading_animation = False

        # Create NeoPixel object with appropriate configuration.
        self.strip = PixelStrip(self.LED_COUNT,
                                self.LED_PIN,
                                self.LED_FREQ_HZ,
                                self.LED_DMA,
                                self.LED_INVERT,
                                self.LED_BRIGHTNESS,
                                self.LED_CHANNEL)
        # Intialize the library (must be called once before other functions).
        self.strip.begin()

    def async_loading_animation(self):
        """
        Thread to display yellow blinking animation
        """
        for i in range(0, 20, 5):
            for y in range(self.strip.numPixels()):
                self.strip.setPixelColor(y, Color(i, i, 0))
            self.strip.show()
            time.sleep(0.06)
        while self.loading_animation:
            for i in range(20, 255, 5):
                for y in range(self.strip.numPixels()):
                    self.strip.setPixelColor(y, Color(i, i, 0))
                self.strip.show()
                time.sleep(0.03)
            for i in range(20, 255, 5)[::-1]:
                for y in range(self.strip.numPixels()):
                    self.strip.setPixelColor(y, Color(i, i, 0))
                self.strip.show()
                time.sleep(0.03)
        for i in range(0, 20, 5)[::-1]:
            for y in range(self.strip.numPixels()):
                self.strip.setPixelColor(y, Color(i, i, 0))
            self.strip.show()
            time.sleep(0.06)

    def start_loading_animation(self):
        """
        Runs a thread to asynchronously display a blinking yellow animation.
        To stop the animation, call stop_loading_animation()
        """
        self.loading_animation = True
        threading.Thread(target=self.async_loading_animation).start()

    def stop_loading_animation(self):
        """
        Stops the thread that is displaying the loading animation
        """
        self.loading_animation = False

    def colorWipe(self, color, wait_ms=50):
        """
        "For each pixel in the strip, set the color, and wait for the amount of time passed in."

        :param color: The color to set the LED to
        :param wait_ms: The time in milliseconds to wait between pixels, defaults to 50 (optional)
        """
        for i in range(self.strip.numPixels()):
            self.strip.setPixelColor(i, color)
            self.strip.show()
            time.sleep(wait_ms / 1000.0)

    def fill(self, color):
        """
        It takes a color as an argument and sets the color of each pixel in the strip to that color

        :param color: a tuple of 3 integers, each between 0 and 255, representing the RGB values of the color you want to fill the strip with
        """
        color = Color(*color)
        for y in range(self.strip.numPixels()):
            self.strip.setPixelColor(y, color)
        self.strip.show()

    def change_to_green(self):
        """
        Change the LEDs gradually from black to green
        """
        for i in range(0, 255, 5):
            for y in range(self.strip.numPixels()):
                self.strip.setPixelColor(y, Color(0, i, 0))
            self.strip.show()
            time.sleep(0.03)

    def black_from_green(self):
        """
        Change the LEDs gradually from green to black
        """
        for i in range(0, 255, 5)[::-1]:
            for y in range(self.strip.numPixels()):
                self.strip.setPixelColor(y, Color(0, i, 0))
            self.strip.show()
            time.sleep(0.03)

    def change_to_red(self):
        """
        Change the LEDs gradually from black to red
        """
        for i in range(0, 255, 5):
            for y in range(self.strip.numPixels()):
                self.strip.setPixelColor(y, Color(i, 0, 0))
            self.strip.show()
            time.sleep(0.03)

    def black_from_red(self):
        """
        Change the LEDs gradually from black to red
        """
        for i in range(0, 255, 5)[::-1]:
            for y in range(self.strip.numPixels()):
                self.strip.setPixelColor(y, Color(i, 0, 0))
            self.strip.show()
            time.sleep(0.03)
