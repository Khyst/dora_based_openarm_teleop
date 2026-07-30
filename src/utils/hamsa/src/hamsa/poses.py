from time import sleep
from hamsa import firmware
from hamsa import hand

def idle_wiggle():
    hand.wiggle_middle(0.6, 100)
    hand.wiggle_pinky(0.5, 100)
    hand.wiggle_ring(.45, 100)
    hand.wiggle_index(.5, 100)

def clear_thumb():
    if hand.curl_thumb_pos() < 0.2:
        hand.curl_thumb(.2, 100)
        sleep(.1)



def flick_up(fingers, time):
    for fin in fingers:
        if fin is 'pinky':
            hand.curl_pinky(1, time)
        if fin is 'ring':
            hand.curl_ring(1, time)
        if fin is 'middle':
            hand.curl_middle(1, time)
        if fin is 'index':
            hand.curl_index(1, time)
        sleep(.1)


def fist(time):
    clear_thumb()
    idle_wiggle()
    delay = .2
    hand.curl_pinky(0, time)
    sleep(delay)
    hand.curl_ring(0, time)
    sleep(delay)
    hand.curl_middle(0, time)
    sleep(delay)
    hand.curl_index(0, time)
    sleep(delay)
    hand.wiggle_thumb(0, time)
    sleep(.1)
    hand.curl_thumb(0.2, time)
    sleep(time/1000)

def ok(time):
    clear_thumb()
    idle_wiggle()
    delay = .1
    flick_up(['pinky','ring','middle'], 500)
    sleep(delay)
    hand.curl_index(.25, time)
    sleep(delay)
    hand.wiggle_thumb(.6, time)
    hand.curl_thumb(.13, time)

def peace(time):
    clear_thumb()
    idle_wiggle()
    delay = .1
    flick_up(['middle', 'index'], time)
    sleep(delay)
    hand.wiggle_middle(.7, 100)
    hand.wiggle_index(.3, 100)
    hand.curl_pinky(0, time)
    sleep(delay)
    hand.curl_ring(0, time)
    sleep(delay)
    hand.wiggle_thumb(.5, time)
    hand.curl_thumb(0, time)


def pan(time):
    clear_thumb()
    idle_wiggle()
    delay = .1
    flick_up(['index'], time)
    sleep(delay)
    hand.curl_pinky(0, time)
    sleep(delay)
    hand.curl_ring(0, time)
    sleep(delay)
    hand.curl_middle(0, time)
    sleep(delay)
    hand.wiggle_thumb(.5, time)
    hand.curl_thumb(0, time)


def idle(time):
    idle_wiggle()
    clear_thumb()
    flick_up(['pinky','ring','middle','index'], time)
    hand.wiggle_thumb(0, 100)
    hand.curl_thumb(1, time)
    sleep(.3)

# toto improve the bellow 3 to guarantee i get the correct pose (note I don't curl to fist every time, 
# and I don't put the thumb back
def one(time):
    idle_wiggle()
    clear_thumb()
    flick_up(['pinky'], time)

def two(time):
    idle_wiggle()
    clear_thumb()
    flick_up(['pinky', 'ring'], time)

def three(time):
    idle_wiggle()
    clear_thumb()
    flick_up(['pinky','ring','middle'], time)

if __name__ == '__main__':
    move_time = 1000
    delay = 3
    try:
        idle(move_time)
        sleep(delay)
        ok(move_time)
        sleep(delay)
        pan(move_time)
        sleep(delay)
        fist(move_time)
        sleep(delay)
        peace(move_time)
        sleep(delay)
        idle(move_time)
    except KeyboardInterrupt:
        idle(move_time)




