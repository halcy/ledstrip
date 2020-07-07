import httpx
import random
from collections import namedtuple
from time import sleep
import os
import sys

LED_COUNT = 300

c = httpx.Client()

LIFETIME=2
TIMESTEP=.066

fairies = []
Fairy = namedtuple('Fairy', ['pos', 'age'])

ramp = ((255,255,255), (192,128,32), (64,0,0), (0,0,0))

ramp2 = list()

# haha precalc
for i in range(int(LIFETIME // TIMESTEP)):
    if i == 0:
        ramp2.append(ramp[0])
    else:
        j = i / (LIFETIME // TIMESTEP)
        ramp_step = int(j* (len(ramp)-1))
        pos_in_ramp_step = (j * (len(ramp) - 1)) % 1
        p = pos_in_ramp_step
        r = int((ramp[ramp_step][0] * (1-p) + ramp[ramp_step+1][0] * p) // 2)
        g = int((ramp[ramp_step][1] * (1-p) + ramp[ramp_step+1][1] * p) // 2)
        b = int((ramp[ramp_step][2] * (1-p) + ramp[ramp_step+1][2] * p) // 2)
        ramp2.append((r,g,b))

ramp2.append(ramp[len(ramp)-1])


r = c.post("http://halcy.de:9000/reset")
t = None
try:
    while True:
        now = float(c.get("http://halcy.de:9000/time").text)
        if not t:
            t = now + 2
        requests = []
        while t < now + 5:
            t += TIMESTEP
            for fairy in fairies:
                fairy.age += 1

            fairies = list(filter(lambda fa: fa.age < len(ramp2), fairies))

            if random.random()*TIMESTEP > .03:
                fairy = Fairy()
                fairy.age = 0
                fairy.pos = random.randint(0, LED_COUNT)
                fairies.append(fairy)

            updates = ""

            for fairy in fairies:
                if fairy.age < len(ramp2)/2:
                    r,g,b = ramp2[fairy.age*2]
                else:
                    r,g,b = (0,0,0)
                if fairy.pos > 0:
                    updates = updates + ",{},{},{},{}".format(fairy.pos-1,r,g,b)
                if fairy.pos < LED_COUNT-1:
                    updates = updates + ",{},{},{},{}".format(fairy.pos+1,r,g,b)

            for fairy in fairies:
                r,g,b = ramp2[fairy.age]
                updates = updates + ",{},{},{},{}".format(fairy.pos,r,g,b)

            updates = updates.strip(',')

            requests.append(dict(url = "http://halcy.de:9000/set_many_sched", params= {
                "at": t,
                "updates": updates
                }))

        # asyncio is difficult
        pid = os.fork()
        if pid == 0:
            c = httpx.Client()
            for request in requests:
                c.get(**request)
            sys.exit(0)
        sleep(.5)

except KeyboardInterrupt:
    print("bye loser")
    exit(0)
