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
 * Serial.h
 * ����ͨ�Žӿ�
 * ����: 2016.8.9
 * ����: ̷����
 */

#ifndef _SERILA_H
#define _SERILA_H


#include <iostream>
#include <stdio.h>      // standard input / output functions
#include <stdlib.h>
#include <string.h>     // string function definitions
#include <unistd.h>     // UNIX standard function definitions
#include <fcntl.h>      // File control definitions
#include <errno.h>      // Error number definitions
#include <termios.h>    // POSIX terminal control definitions
#include <chrono>		// For timeout on read

class CSerial
{
public:
    CSerial();
    virtual int writeSerial(unsigned char *nDat, int nLen);
    virtual int readSerial(unsigned char *nDat, int nLen);
    virtual int writeSerial(unsigned char bDat);
    virtual void flushSerial();
public:
    unsigned long int IOTimeOut;
    int USB;
};

#endif
