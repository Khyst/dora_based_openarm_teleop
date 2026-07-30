import os   
import sys
import time
import random

# sys.path.insert(0, os.path.abspath("./src"))
# sys.path.append("/home/rastech/workspace/src/hamsa/src")

from hamsa import hand
from hamsa import firmware

# 좁히기
def close_palm():
    hand.wiggle_pinky(0, 1000)
    hand.wiggle_ring(0, 1000)
    hand.wiggle_middle(1, 1000)
    hand.wiggle_index(1, 500)
    hand.wiggle_thumb(1, 1000)

# 펼치기
def open_palm():
    hand.wiggle_pinky(1, 1000)
    hand.wiggle_ring(1, 1000)
    hand.wiggle_middle(1, 2000)
    hand.wiggle_index(0, 500)
    hand.wiggle_thumb(0, 1000)

# 구부리기
def grab():
    hand.curl_pinky(0, 2000)
    hand.curl_ring(0, 2000)
    hand.curl_middle(0, 2000)
    hand.curl_index(0, 2000)
    hand.curl_thumb(0, 2000)

# 펼치기
def release():
    hand.curl_pinky(1, 2000)
    hand.curl_ring(1, 2000)
    hand.curl_middle(1, 2000)
    hand.curl_index(1, 2000)
    hand.curl_thumb(1, 1800)

# 가위
def scissor():
    hand.curl_pinky(0, 1000)
    hand.curl_ring(0, 1000)
    hand.curl_thumb(0, 1000)
    hand.curl_middle(1, 1000)
    hand.curl_index(1, 1000)

def main():
    print("Executing sequential motions: grab -> release -> scissor")
    
    # print("Executing grab...")
    # grab()
    # time.sleep(3)
    
    print("Executing release...")
    release()
    time.sleep(3)
    
    # print("Executing scissor...")
    # scissor()
    # time.sleep(3)

if __name__ == '__main__':
    main()

