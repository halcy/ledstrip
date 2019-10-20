import time
from rpi_ws281x import *
import argparse
import math
import numpy as np
import multiprocessing
import socket
import struct

LED_COUNT      = 300      # Number of LED pixels.
LED_PIN        = 10      # GPIO pin connected to the pixels (10 uses SPI /dev/spidev0.0).
LED_FREQ_HZ    = 800000  # LED signal frequency in hertz (usually 800khz)
LED_DMA        = 10      # DMA channel to use for generating signal (try 10)
LED_BRIGHTNESS = 255     # Set to 0 for darkest and 255 for brightest
LED_INVERT     = False   # True to invert the signal (when using NPN transistor level shift)
LED_CHANNEL    = 0       # set to '1' for GPIOs 13, 19, 41, 45 or 53

SPLIT_LED = 254

listen_socket = None

strip = Adafruit_NeoPixel(LED_COUNT, LED_PIN, LED_FREQ_HZ, LED_DMA, LED_INVERT, LED_BRIGHTNESS, LED_CHANNEL)
strip.begin()

def wheel(pos):
    """Generate rainbow colors across 0-255 positions."""
    if pos < 85:
        return np.array((pos * 3, 255 - pos * 3, 0))
    elif pos < 170:
        pos -= 85
        return np.array((255 - pos * 3, 0, pos * 3))
    else:
        pos -= 170
        return np.array((0, pos * 3, 255 - pos * 3))

pos = 0    
while(True):
    for i in range(SPLIT_LED):
        col = wheel(math.fmod(i + pos, 255.0))
        strip.setPixelColor(i, Color(int(col[0]), int(col[1]), int(col[2])))
    strip.show()
    
    bright = (math.sin(pos * 0.001) + 1.0) * 50.0
    for i in range(SPLIT_LED, LED_COUNT):
        strip.setPixelColor(i, Color(int(bright * 0.5), int(bright * 0.1), int(bright)))
    pos += 1.0
    time.sleep(10.0 / 1000.0)    
