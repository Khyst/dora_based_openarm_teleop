// This is an example of how to use the c++ library independently of the python
// Build with Makefile

#include "Hand.h"

// Example configuration - yours will be different!
int PINKY_WIGGLE_ID=1;
int PINKY_WIGGLE_LEFT=493;
int PINKY_WIGGLE_RIGHT=343;

int PINKY_CURL_ID=2;
int PINKY_CURL_OUT=30;
int PINKY_CURL_IN=877;

int RING_WIGGLE_ID=3;
int RING_WIGGLE_LEFT=555;
int RING_WIGGLE_RIGHT=405;

int RING_CURL_ID=4;
int RING_CURL_OUT=160;
int RING_CURL_IN=1023;

int MIDDLE_WIGGLE_ID=5;
int MIDDLE_WIGGLE_LEFT=630;
int MIDDLE_WIGGLE_RIGHT=472;

int MIDDLE_CURL_ID=6;
int MIDDLE_CURL_OUT=1023;
int MIDDLE_CURL_IN=160;

int INDEX_WIGGLE_ID=7;
int INDEX_WIGGLE_LEFT=590;
int INDEX_WIGGLE_RIGHT=450;

int INDEX_CURL_ID=8;
int INDEX_CURL_OUT=780;
int INDEX_CURL_IN=0;

int THUMB_WIGGLE_ID=9;
int THUMB_WIGGLE_LEFT=798;
int THUMB_WIGGLE_RIGHT=435;

int THUMB_CURL_ID=10;
int THUMB_CURL_OUT=220;
int THUMB_CURL_IN=789;

int WRIST_ID=11;
int WRIST_FORWARDS=350;
int WRIST_BACKWARDS=700;

int main(){
  
  Hand Thing;
  // Curl the pink by 50% in 500ms
  Thing.curl(0.5, 500, INDEX_CURL_IN, INDEX_CURL_OUT, INDEX_CURL_ID);
  // Wiggle the thumb by 100% in 500ms
  Thing.wiggle(1, 500, THUMB_WIGGLE_LEFT, THUMB_WIGGLE_RIGHT, THUMB_WIGGLE_ID);
  return 0;

}
