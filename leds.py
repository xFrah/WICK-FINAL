#!/usr/bin/python3

# SPDX-License-Identifier: MIT
#
# Copyright (c) 2020 Kontron Electronics GmbH
# Author: Frieder Schrempf
#

import time
from lib import neopixel_spidev as np
from lib.pixelbuf import wheel

pixels = np.NeoPixelSpiDev(0, 0, n=24, pixel_order=np.GRB)
print("[INFO] LEDs configured: {}".format(pixels))


# Init 56 LEDs on SPI bus 2, cs 0 with colors ordered green, red, blue

def set_leds(color):
    pixels.fill(color)
    # pixels.show()


def configure_leds():
    pixels.fill((0, 0, 0))
    pixels.show()
