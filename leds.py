#!/usr/bin/python3

# SPDX-License-Identifier: MIT
#
# Copyright (c) 2020 Kontron Electronics GmbH
# Author: Frieder Schrempf
#

import time
from lib import neopixel_spidev as np
from lib.pixelbuf import wheel

# Init 56 LEDs on SPI bus 2, cs 0 with colors ordered green, red, blue
with np.NeoPixelSpiDev(0, 0, n=24, pixel_order=np.GRB) as pixels:
    try:
        while True:
            color = input("Insert color: ")
            if color == "r":
                pixels.fill((255, 0, 0))
                pixels.fill((255, 0, 0))
            elif color == "g":
                pixels.fill((0, 255, 0))
                pixels.fill((0, 255, 0))
            elif color == "b":
                pixels.fill((0, 0, 255))
                pixels.fill((0, 0, 255))
            elif color == "w":
                pixels.fill((255, 255, 255))
                pixels.fill((255, 255, 255))
    except KeyboardInterrupt:
        pass