#!/usr/bin/env python3
import os
import sys
import time

# Ensure package paths are resolved if executing directly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))

from hamsa import left, right

def release_hand(hand_obj, duration=3000):
    print(f"\n[+] Releasing all joints of {hand_obj.side.upper()} hand (duration: {duration}ms)...")
    
    # Wiggle joints to center/neutral position
    hand_obj.wiggle_pinky(0.5, duration)
    hand_obj.wiggle_ring(0.5, duration)
    hand_obj.wiggle_middle(0.5, duration)
    hand_obj.wiggle_index(0.5, duration)
    hand_obj.wiggle_thumb(0.5, duration)
    
    # Curl joints to fully open/released state (1.0)
    hand_obj.curl_pinky(1.0, duration)
    hand_obj.curl_ring(1.0, duration)
    hand_obj.curl_middle(1.0, duration)
    hand_obj.curl_index(1.0, duration)
    hand_obj.curl_thumb(1.0, duration)

def main():
    print("=========================================================")
    print("          Hamsa Dual-Hand Hardware Test Script           ")
    print("=========================================================")

    # 1. First, release the RIGHT hand slowly and safely
    safe_time_ms = 3000
    print(f"\nStep 1: Safely releasing RIGHT hand first...")
    release_hand(right, safe_time_ms)
    time.sleep(4.0)  # Wait for RIGHT hand to complete motion

    # 2. Next, release the LEFT hand slowly and safely
    print(f"\nStep 2: Safely releasing LEFT hand...")
    release_hand(left, safe_time_ms)
    time.sleep(4.0)  # Wait for LEFT hand to complete motion

    # 3. Test concurrent movements (Right Hand Grabs, Left Hand Scissors)
    print(f"\nStep 3: Executing concurrent hand gestures (Right Hand GRAB, Left Hand SCISSOR)...")
    
    # Command Right Hand to GRAB (curl = 0.0)
    right.curl_pinky(0.0, 2000)
    right.curl_ring(0.0, 2000)
    right.curl_middle(0.0, 2000)
    right.curl_index(0.0, 2000)
    right.curl_thumb(0.0, 2000)

    # Command Left Hand to SCISSOR (curl = 1.0 for index/middle, 0.0 for others)
    left.curl_pinky(0.0, 2000)
    left.curl_ring(0.0, 2000)
    left.curl_thumb(0.0, 2000)
    left.curl_middle(1.0, 2000)
    left.curl_index(1.0, 2000)

    time.sleep(3.0)  # Wait for gestures to complete

    # 4. Return both hands to fully open / released state
    print(f"\nStep 4: Returning both hands to fully open / RELEASED state...")
    right.curl_pinky(1.0, 2000)
    right.curl_ring(1.0, 2000)
    right.curl_middle(1.0, 2000)
    right.curl_index(1.0, 2000)
    right.curl_thumb(1.0, 2000)

    left.curl_pinky(1.0, 2000)
    left.curl_ring(1.0, 2000)
    left.curl_middle(1.0, 2000)
    left.curl_index(1.0, 2000)
    left.curl_thumb(1.0, 2000)

    time.sleep(3.0)
    
    print("\n=========================================================")
    print("✓ Hamsa Dual-Hand Hardware Test Completed Successfully!")
    print("=========================================================")

if __name__ == '__main__':
    main()
