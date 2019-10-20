import time
from rpi_ws281x import *
import argparse
import math
import numpy as np
import multiprocessing
import socket
import struct
import os

from flask import Flask, request
app = Flask(__name__)

# Buncha defs for interfacing
LED_COUNT      = 300      # Number of LED pixels.
LED_PIN        = 10      # GPIO pin connected to the pixels (10 uses SPI /dev/spidev0.0).
LED_FREQ_HZ    = 800000  # LED signal frequency in hertz (usually 800khz)
LED_DMA        = 10      # DMA channel to use for generating signal (try 10)
LED_BRIGHTNESS = 255     # Set to 0 for darkest and 255 for brightest
LED_INVERT     = False   # True to invert the signal (when using NPN transistor level shift)
LED_CHANNEL    = 0       # set to '1' for GPIOs 13, 19, 41, 45 or 53

SPLIT_LED = 254 # From when the LEDs start being on the wall instead of on the ceiling
ATTRACT_TIMEOUT = 15 # how many seconds of no activity until attract mode starts

# Actual interfacing
strip = Adafruit_NeoPixel(LED_COUNT, LED_PIN, LED_FREQ_HZ, LED_DMA, LED_INVERT, LED_BRIGHTNESS, LED_CHANNEL)
strip.begin()

# Scheduling
manager = multiprocessing.Manager()
schedule = manager.list()

# Blast-colours-to-strip process, reading from a state array
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

# Attract mode "last reset" timer
attract_started = multiprocessing.Value('d', 0)
attract_has_run = multiprocessing.Value('b', False)

# Input verification
def is_int(s):
    try: 
        int(s)
        return True
    except ValueError:
        return False

# Displays help
@app.route("/")
def root():
    return_html = """   
<html>
<head>
<title>welcome to my led strip</title>
</head>
<body>
<h1>LED strip REST API</h1>
<p>This is a simple API for a cheap 300 rgb led strip that's installed in my living room. By default, it runs a rainbow wobble "attract mode", if you start making calls to this API it'll reset to all LEDs off on first call and let you do your thing until you stop doing things for 15 seconds, after which it will switch back into attract mode. Note that the strip is super not linear with regard to brightness. Note also that it's only fed power from one side so if you set all the LEDs to something very bright, it'll start to dim towards the higher numbered ones. Note finally that I'll probably only turn this on rarely and only while I am also in the room since I wired it up myself and I don't trust it to not burn the house down..</p>

<h2>Endpoints</h2>
<h3>http://halcy.de:9000/reset</h3>
<p>Turn all LEDs off.</p>

<h3>http://halcy.de:9000/set/(led)/(r)/(g)/(b)</h3>
<p>Set (led) to colour (r), (g), (b), where (led) is an integer between 0 and 299 inclusive, and (r), (g), (b) are integer between 0 and 255 inclusive.</p>

<h3>http://halcy.de:9000/set_many?updates=(led1),(r1),(g1),(b1),(led2)....</h3>
<p>Set (led1) to colour (r1), (g1), (b1), set (led2) to colour (r2), (g2), (b2) et cetera, parameter types and ranges as above. Parameter array can be as long as you want. Accepts POST requests. Recommended for dramatically less flicker.</p>

<h3>http://halcy.de:9000/set_many_sched?updates=(led1),(r1),(g1),(b1),(led2)....&at=(time)</h3>
<p>Like set_many but schedules the update to occur at the given unix timestamp that is not in the past and no more than 30 seconds in the future. A maximum of 1000 events can be scheduled at any time.</p>

<h3>http://halcy.de:9000/time</h3>
<p>Returns current serverside unix time.</p>

<h2>I can't see what I'm doing this is bull shit</h2>
twitch: <a href="https://www.twitch.tv/h4lcy">https://www.twitch.tv/h4lcy</a>

<h2>Example script</h2>
<pre>
# This script will display a simple point bouncing from one side to the other
LED_COUNT = 300

pos = 0
pos_diff = 1
while True:
    if pos == 0:
        pos_diff = 1
    if pos == LED_COUNT -1:
        pos_diff = -1
    prev_pos = pos
    pos += pos_diff
    
    # You could do this, but it will flicker
    #requests.get("http://halcy.de:9000/set/{}/120/255/0".format(int(pos)))
    #requests.get("http://halcy.de:9000/set/{}/0/0/0".format(int(prev_pos)))
    
    # Much less flickery, allows large updates
    updates = "{},120,255,0,{},0,0,0".format(int(pos), int(prev_pos))
    requests.post("http://halcy.de:9000/set_many", params = {"updates": updates})
    time.sleep(5.0 / 1000.0)
</pre>
</body>
</html>   
"""
    return return_html

# Set all to black
@app.route("/reset", methods=["GET","POST"])
def reset():
    if attract_has_run.value == True:
        attract_started.value = time.time()
        
    for i in range(LED_COUNT * 3):
       col_state[i] = 0 
    return("ok")

# Set a single LED
@app.route("/set/<int:led>/<int:r>/<int:g>/<int:b>", methods=["GET","POST"])
def set_single(led, r, g, b, from_attract = False):
    if not from_attract:
        attract_started.value = time.time()
        if attract_has_run.value == True:
            print("Activity happened, resetting")
            attract_has_run.value = False
            reset()
        
    if not is_int(led):
        led = "0"
    if not is_int(r):
        r = "0"
    if not is_int(g):
        g = "0"
    if not is_int(b):
        b = "0"
        
    led = max(0, min(int(led), LED_COUNT - 1))
    r = max(0, min(int(r), 255))
    g = max(0, min(int(g), 255))
    b = max(0, min(int(b), 255))
    
    col_state[led * 3] = r
    col_state[led * 3 + 1] = g
    col_state[led * 3 + 2] = b
    
    return("ok")

@app.route("/time")
def get_time():
    return str(time.time())

@app.route("/set_many_sched")
def scheduled():
    try:
        at = request.args.get("at")
        updates = request.args.get("updates")
        if not updates is None and not at is None:
            at = float(at)
            if at > time.time() and at - time.time() < 30:
                if len(schedule) < 1000:
                    schedule.append((at, updates))
            else:
                return("no")
    except:
        return("no")
    return("ok")
    
# Set many leds at once
@app.route("/set_many", methods=["GET","POST"])
def set_many():
    updates = request.args.get("updates")
    if not updates is None:
        updates_arr = updates.split(",")
        for i in range(0, len(updates_arr) - 3, 4):
            led = updates_arr[i]
            r = updates_arr[i + 1]
            g = updates_arr[i + 2]
            b = updates_arr[i + 3]
            set_single(led, r, g, b)
    return "ok"

def schedule_thread():
    while True:
        if len(schedule) > 0:
            update = schedule.pop(0)
            if update[0] > time.time():
                updates = update[1]
                updates_arr = updates.split(",")
                for i in range(0, len(updates_arr) - 3, 4):
                    led = updates_arr[i]
                    r = updates_arr[i + 1]
                    g = updates_arr[i + 2]
                    b = updates_arr[i + 3]
                    set_single(led, r, g, b)
            else:
                schedule.append(update)

schedule_process = multiprocessing.Process(target = schedule_thread)
schedule_process.start()


# "Attract mode" process (rainbow) that turns on at ATTRACT_TIMEOUT seconds of no activity
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

def attract_mode():
    pos = 0
    while(True):
        if time.time() - attract_started.value > ATTRACT_TIMEOUT:
            attract_has_run.value = True
            for i in range(SPLIT_LED):
                col = wheel(math.fmod(i + pos, 255.0))
                set_single(i, col[0], col[1], col[2], from_attract = True)
            
            bright = (math.sin(pos * 0.001) + 1.0) * 50.0
            for i in range(SPLIT_LED, LED_COUNT):
                set_single(i, int(bright * 0.5), int(bright * 0.1), int(bright), from_attract = True)
            pos += 4.0
        time.sleep(10.0 / 1000.0)    
        
attract_mode_process = multiprocessing.Process(target = attract_mode)
attract_mode_process.start()

#ATTRACT_TIMEOUT

# Run flask
print("flask starting up")
from werkzeug.serving import run_simple
run_simple('10.1.1.105', 9000, app, processes = 100)
