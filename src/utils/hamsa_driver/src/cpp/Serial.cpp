/*   Copyright 2021 Feetech RC Model CO.,LTD
 *
 *  Licensed under the Apache License, Version 2.0 (the "License");
 *  you may not use this file except in compliance with the License.
 *  You may obtain a copy of the License at
 *
 *       http://www.apache.org/licenses/LICENSE-2.0
 *
 *  Unless required by applicable law or agreed to in writing, software
 *  distributed under the License is distributed on an "AS IS" BASIS,
 *  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *  See the License for the specific language governing permissions and
 *  limitations under the License.
 */
// Modifications were made to this file for Hamsa 
/*
 * Serial.cpp
 * ����ͨ�Žӿ�
 * ����: 2016.8.9
 * ����: ̷����
 */

#include "Serial.h"


CSerial::CSerial()
{
    IOTimeOut = 2;
    USB = open( "/dev/ttyHamsaHand", O_RDWR| O_NOCTTY| O_NONBLOCK );
    struct termios tty;
    struct termios tty_old;
    memset (&tty, 0, sizeof tty);

    /* Error Handling */
    if ( tcgetattr ( USB, &tty ) != 0 ) {
    std::cout << "Error " << errno << " from tcgetattr: " << strerror(errno) << std::endl;
    }

    /* Save old tty parameters */
    tty_old = tty;

    /* Set Baud Rate */
    cfsetospeed (&tty, B1000000);
    cfsetispeed (&tty, B1000000);

    // These settings taken from https://stackoverflow.com/questions/18108932/reading-and-writing-to-serial-port-in-c-on-linux
    // No idea what they do but they seem to be needed for meaningful reads

    /* Setting other Port Stuff */
    tty.c_cflag     &=  ~PARENB;            // Make 8n1
    tty.c_cflag     &=  ~CSTOPB;
    tty.c_cflag     &=  ~CSIZE;
    tty.c_cflag     |=  CS8;
    tty.c_cflag     &=  ~CRTSCTS;           // no flow control
    tty.c_cc[VMIN]   =  1;                  // read doesn't block
    tty.c_cc[VTIME]  =  5;                  // 0.5 seconds read timeout
    tty.c_cflag     |=  CREAD | CLOCAL;     // turn on READ & ignore ctrl lines
    /* Make raw */
    cfmakeraw(&tty);

    // Flush Port, then applies attributes
    tcflush( USB, TCIFLUSH );
    if ( tcsetattr ( USB, TCSANOW, &tty ) != 0) {
    std::cout << "Error " << errno << " from tcsetattr" << std::endl;
    }

}


int CSerial::readSerial(unsigned char *nDat, int nLen)
{
    using std::chrono::high_resolution_clock;
    using std::chrono::duration_cast;
    using std::chrono::duration;
    using std::chrono::milliseconds;

    auto tStart = high_resolution_clock::now();

    int bit_read= 0,
    size = 0;
    unsigned char buf = '\0';
    auto tNow = high_resolution_clock::now();
    auto tUser = duration_cast<milliseconds>(tNow - tStart);

    do {
        bit_read= read( USB, &buf, 1 );
        if (bit_read==1) {
            nDat[size] = buf;
            size += bit_read;
            tStart = high_resolution_clock::now();
        }
        tNow = high_resolution_clock::now();
        tUser = duration_cast<milliseconds>(tNow - tStart);
    } while( size<nLen && tUser.count()<(signed)IOTimeOut*100);

    return size;
}

int CSerial::writeSerial(unsigned char *nDat, int nLen)
{
    if(nDat==NULL){
        return 0;
    }
    return write(USB, nDat, nLen);
}

int CSerial::writeSerial(unsigned char bDat)
{
    return write(USB, &bDat, 1);
}

void CSerial::flushSerial()
{
    tcflush( USB, TCIFLUSH );
}
