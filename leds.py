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
            pixels.fill((255, 255, 255))
            time.sleep(2)
    except KeyboardInterrupt:
        pass