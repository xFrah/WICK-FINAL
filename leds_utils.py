import time
from lib import neopixel_spidev as neo

from flightshot import setup_not_done


def setup_led():
    print("[INFO] Configuring LEDs:", end=" ", flush=True)
    pixels = neo.NeoPixelSpiDev(0, 0, n=24, pixel_order=neo.GRB)
    pixels.fill((0, 0, 0))
    pixels.show()
    print("Done.")
    return pixels


# change leds gradually to green
def change_to_green(pixels):
    for i in range(0, 255, 5):
        pixels.fill((0, i, 0))
        pixels.show()
        time.sleep(0.03)


# change leds gradually to green
def black_from_green(pixels):
    for i in range(0, 255, 5)[::-1]:
        pixels.fill((0, i, 0))
        pixels.show()
        time.sleep(0.03)


# change leds gradually to green
def change_to_red(pixels):
    for i in range(0, 255, 5):
        pixels.fill((i, 0, 0))
        pixels.show()
        time.sleep(0.03)


# change leds gradually to green
def black_from_red(pixels):
    for i in range(0, 255, 5)[::-1]:
        pixels.fill((i, 0, 0))
        pixels.show()
        time.sleep(0.03)


def timed_fill(pixels):
    while setup_not_done:
        for i in range(0, 255, 5):
            pixels.fill((0, 0, i))
            # pixels.show()
            time.sleep(0.03)
        for i in range(0, 255, 5)[::-1]:
            pixels.fill((0, 0, i))
            # pixels.show()
            time.sleep(0.03)
