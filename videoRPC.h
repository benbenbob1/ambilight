#include <time.h>
#include <stdlib.h>
#include <stdio.h>
#include <math.h>
#include <string.h>
#include <unistd.h>
#include <opencv2/imgproc.hpp>
#include <opencv2/videoio.hpp>
#include <opencv2/core.hpp>
#include <opencv2/highgui.hpp>
#include <highgui.h>
#include <iostream>
#include "opc_client.h"

#ifdef __arm__
    #include <raspicam/raspicam_cv.h>
    const bool IS_PI = true;
#else
    const bool IS_PI = false;
#endif

const bool USE_CAMERA = true;

const char VIDEO_LOC[] = "bob.mov";
const int FRAMERATE = 12;
const int VIDEO_FEED_WIDTH = 320; //pixels
const int VIDEO_FEED_HEIGHT = 240; //pixels

const int NUM_LEDS_HORIZ = 52;
const int NUM_LEDS_VERT  = 28;
const int BLUR_AMT = 25; // Must be an odd number
const int SMOOTH_SPEED = 5; // Number of frames to fade colors over
// Don't smooth is color difference is over this
const int SMOOTH_IGNORE_AMT = 50;
// Amount to go "inwards" multiplied by current rectangle width or height
const int RECTANGLE_SPREAD_MULTIPLIER = 4;
const int LED_MIN_CUTOFF = 35; //min value out of 255
const int FADECANDY_NUM_STRIPS = 3;
const int FADECANDY_MAX_LEDSPEROUT = 64;

const char OPC_SOCKET_HOST[] = "127.0.0.1";
const int OPC_SOCKET_PORT = 7890;

const bool USE_DISPLAY = false;
const bool RESIZE_INPUT = false;
const bool NO_DARK_SPOTS = false;

using namespace cv;
using namespace std;

class LEDStrip {
public:
    int fcOffset;
    int count;
    int startIndex;
    bool inverted;
    Vec3b leds[FADECANDY_MAX_LEDSPEROUT];

    void setValues(int fcIdx, int startIdx, int numLeds, bool isInverted);
    //Sets all indices to [0,0,0]
    void initializeLeds();
    void setLed(int index, Vec3b color);
    Vec3b getLed(int index);
    //LedsToSet MUST be of length count
    //Returns number of leds set
    int putLEDs(
        Vec3b (*allLeds)[FADECANDY_NUM_STRIPS*FADECANDY_MAX_LEDSPEROUT]
    );
};

class LED {
public:
    LEDStrip top;
    LEDStrip right;
    LEDStrip bottom;
    LEDStrip left;
    OPCClient opc;
    int maxLeds;

    bool ledsConnected();
    //Sends over the LED buffers
    bool sendLEDs(Vec3b minColor);
    bool initialize();

private:
    Vec3b leds[FADECANDY_NUM_STRIPS*FADECANDY_MAX_LEDSPEROUT];
    std::vector<uint8_t> frameBuffer;
    int maxLedBufferSize;
};
