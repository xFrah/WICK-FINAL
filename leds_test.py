from new_led_utils import LEDs
from rpi_ws281x import Color

leds = LEDs(start_yellow_loading=False)
leds.colorWipe(Color(255, 255, 255), wait_ms=50)

