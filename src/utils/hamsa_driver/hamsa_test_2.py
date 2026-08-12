import os
import sys
import time

sys.path.append("/home/rastech/workspace/src/hamsa/src")
# Ensure we import the correct library
from hamsa import hand

# 1. close_palm (좁히기)
def close_palm():
    hand.wiggle_pinky(0, 1000)
    hand.wiggle_ring(0, 1000)
    hand.wiggle_middle(1, 1000)
    hand.wiggle_index(1, 500)
    hand.wiggle_thumb(1, 1000)

# 2. open_palm (펼치기)
def open_palm():
    hand.wiggle_pinky(1, 1000)
    hand.wiggle_ring(1, 1000)
    hand.wiggle_middle(1, 2000)
    hand.wiggle_index(0, 500)
    hand.wiggle_thumb(0, 1000)

# 3. grab (구부리기)
def grab():
    hand.curl_pinky(0, 2000)
    hand.curl_ring(0, 2000)
    hand.curl_middle(0, 2000)
    hand.curl_index(0, 2000)
    hand.curl_thumb(0, 2000)

# 4. release (펼치기)
def release():
    hand.curl_pinky(1, 2000)
    hand.curl_ring(1, 2000)
    hand.curl_middle(1, 2000)
    hand.curl_index(1, 2000)
    hand.curl_thumb(1, 1800)

# 5. scissor (가위)
def scissor():
    hand.curl_pinky(0, 1000)
    hand.curl_ring(0, 1000)
    hand.curl_thumb(0, 1000)
    hand.curl_middle(1, 1000)
    hand.curl_index(1, 1000)

if __name__ == '__main__':
    print("Executing grab motion...")
    grab()
    time.sleep(2)
    
    print("Executing Release motion...")
    release()
    time.sleep(2)