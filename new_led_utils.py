#!/usr/bin/env python3
# NeoPixel library strandtest example
# Author: Tony DiCola (tony@tonydicola.com)
#
# Direct port of the Arduino NeoPixel library strandtest example.  Showcases
# various animations on a strip of NeoPixels.

import time
from rpi_ws281x import PixelStrip, Color

# LED strip configuration:
LED_COUNT = 24        # Number of LED pixels.
LED_PIN = 18          # GPIO pin connected to the pixels (18 uses PWM!).
# LED_PIN = 10        # GPIO pin connected to the pixels (10 uses SPI /dev/spidev0.0).
LED_FREQ_HZ = 800000  # LED signal frequency in hertz (usually 800khz)
LED_DMA = 10          # DMA channel to use for generating signal (try 10)
LED_BRIGHTNESS = 255  # Set to 0 for darkest and 255 for brightest
LED_INVERT = False    # True to invert the signal (when using NPN transistor level shift)
LED_CHANNEL = 0       # set to '1' for GPIOs 13, 19, 41, 45 or 53


# Define functions which animate LEDs in various ways.
def colorWipe(strip, color, wait_ms=50):
    """Wipe color across display a pixel at a time."""
    for i in range(strip.numPixels()):
        strip.setPixelColor(i, color)
        strip.show()
        time.sleep(wait_ms / 1000.0)


def fill(strip, color):
    r, g, b = color
    for y in range(strip.numPixels()):
        strip.setPixelColor(y, Color(r, g, b))
    strip.show()


def setup_led():
    # Create NeoPixel object with appropriate configuration.
    strip = PixelStrip(LED_COUNT, LED_PIN, LED_FREQ_HZ, LED_DMA, LED_INVERT, LED_BRIGHTNESS, LED_CHANNEL)
    # Intialize the library (must be called once before other functions).
    strip.begin()
    return strip


# change leds gradually to green
def change_to_green(strip):
    for i in range(0, 255, 5):
        for y in range(strip.numPixels()):
            strip.setPixelColor(y, Color(0, i, 0))
        strip.show()
        time.sleep(0.03)


# change leds gradually to green
def black_from_green(strip):
    for i in range(0, 255, 5)[::-1]:
        for y in range(strip.numPixels()):
            strip.setPixelColor(y, Color(0, i, 0))
        strip.show()
        time.sleep(0.03)


# change leds gradually to green
def change_to_red(strip):
    for i in range(0, 255, 5):
        for y in range(strip.numPixels()):
            strip.setPixelColor(y, Color(i, 0, 0))
        strip.show()
        time.sleep(0.03)


# change leds gradually to green
def black_from_red(strip):
    for i in range(0, 255, 5)[::-1]:
        for y in range(strip.numPixels()):
            strip.setPixelColor(y, Color(i, 0, 0))
        strip.show()
        time.sleep(0.03)
