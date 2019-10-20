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

col_state = multiprocessing.Array('d', [0] * LED_COUNT * 3)

def set_led_state():
    while(True):
        col_state_snap = col_state[:]
        for i in range(0, LED_COUNT):
            col = col_state_snap[i*3:(i+1)*3]
            strip.setPixelColor(i, Color(int(col[0]), int(col[1]), int(col[2])))
        strip.show()

set_led_state_process = multiprocessing.Process(target = set_led_state)
set_led_state_process.start()

if not listen_socket is None:
    try:
        listen_socket.close()
    except:
        pass

listen_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
listen_socket.bind(('', 9332))
listen_socket.listen(1)

packer = struct.Struct(str(LED_COUNT*3) + "f")
print("wait client")
while(True):
    connection, client_address = listen_socket.accept()
    connection.setblocking(0)
    connection.settimeout(0.001)
    print("get client")
    try:
        while(True):
            recv_buffer = b''
            while len(recv_buffer) < packer.size:
                try:
                    recv_buffer += connection.recv(packer.size - len(recv_buffer))
                except socket.timeout:
                    pass
                if len(recv_buffer) < packer.size:
                    time.sleep(1.0 / 1000.0)
            float_vals = packer.unpack(recv_buffer)
            for i in range(0, LED_COUNT * 3):
                col_state[i] = float_vals[i]
    #except Exception as e:
    #    print(e)
    finally:
        print("client done")
        connection.close() 
