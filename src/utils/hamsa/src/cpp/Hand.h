#ifndef _HAND_H
#define _HAND_H

#include "SCServo.h"

class Hand {

    public:
        Hand();
        SCServo Servos;
        void setup_servos();
        int idle();
        void say_no();

    public:
	int curl(float percentage, // 1 = fully extended, 0 = fully curled
                        int time,
                        int in,
                        int out,
                        int curl_id);

        int wiggle(float percentage, // 1 = fully right, 0 = fully left
                           int time,
                           int left,
                           int right,
                           int wiggle_id);

	float curl_position(int in, int out, int curl_id);
	float wiggle_position(int left, int right, int wiggle_id);

};

#endif
