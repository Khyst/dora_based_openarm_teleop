#include "Hand.h"

Hand::Hand() {
    Servos = SCServo();
}

void Hand::setup_servos() {
  Servos.EnableTorque(1, 1);
  usleep(100 * USLEEP_MULTIPLIER);
}

int Hand::curl(float percentage, // 1 = fully extended, 0 = fully curled
                        int time,
                        int in,
                        int out,
                        int curl_id) {     
    int servoPosition;
    if (out < in){
        servoPosition = (((out - in) * percentage) + in);
    }else {
        servoPosition = (in - ((in - out) * percentage));
    }
    return Servos.WritePos(curl_id,  servoPosition,  time);
}

int Hand::wiggle(float percentage, // 1 = fully right, 0 = fully left
		     int time,
		     int left,
		     int right,
		     int wiggle_id) {
    int servoPosition;
    if (left > right){
        servoPosition = (((left - right) * percentage) + right);
    }else {
        servoPosition = (right - ((right - left) * percentage));
    }
    return Servos.WritePos(wiggle_id,  servoPosition,  time);
}


float Hand::curl_position(int in, int out, int curl_id) {
    float percentage;
    float servoPosition = Servos.ReadPos(curl_id);
    if (out < in){
        percentage = (servoPosition - in)/(out - in);
    } else {
        percentage = (in - servoPosition)/(in - out);
    }
    return percentage;
}

float Hand::wiggle_position(int left, int right, int wiggle_id) {
    float percentage;
    float servoPosition = Servos.ReadPos(wiggle_id);
    if (left > right){
        percentage = (servoPosition - right)/(left - right);
    } else {
        percentage = (right - servoPosition)/(right-left);
    }
    return percentage;
}

