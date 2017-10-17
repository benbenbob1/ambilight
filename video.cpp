#include <time.h>
#include <stdlib.h>
#include <stdio.h>
#include <math.h>
#include <string.h>
#include <unistd.h>
#include <opencv2/imgproc.hpp>
#include <opencv2/videoio.hpp>
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

using namespace cv;
using namespace std;


const bool USE_CAMERA = true;

const char VIDEO_LOC[] = "bob.mov";
const int FRAMERATE = 10;
const int VIDEO_FEED_WIDTH = 480; //pixels
const int VIDEO_FEED_HEIGHT = 320; //pixels

const int NUM_LEDS_HORIZ = 52;
const int NUM_LEDS_VERT  = 28;
const int BLUR_AMT = 11; //Must be an odd number
//amount to go "inwards" multiplied by current rectangle width or height
const int RECTANGLE_SPREAD_MULTIPLIER = 4;
const int LED_MIN_CUTOFF = 35; //min value out of 255
const int FADECANDY_NUM_STRIPS = 3;
const int FADECANDY_MAX_LEDSPEROUT = 64;

const char OPC_SOCKET_HOST[] = "127.0.0.1";
const int OPC_SOCKET_PORT = 7890;

const bool USE_DISPLAY = true;

int squareWidth, squareHeight;
int startX, startY;

class LEDStrip {
public:
    int fcOffset;
    int count;
    int startIndex;
    bool inverted;
    Vec3b leds[FADECANDY_MAX_LEDSPEROUT];

    LEDStrip() {
        fcOffset = 0;
        count = 0;
        startIndex = 0;
        inverted = false;
    }

    void setValues(int fcIdx, int startIdx, int numLeds, bool isInverted) {
        if (numLeds > FADECANDY_MAX_LEDSPEROUT) {
            numLeds = FADECANDY_MAX_LEDSPEROUT;
        }
        fcOffset = fcIdx;
        startIndex = startIdx;
        count = numLeds;
        inverted = isInverted;
    }

    //Sets all indices to [0,0,0]
    void initializeLeds() {
        for (int l=0; l<count; l++) {
            leds[l] = Vec3b(0, 0, 0);
        }
    }

    void setLed(int index, Vec3b color) {
        if (index < count) {
            leds[index] = color;
        }
    }

    Vec3b getLed(int index) {
        if (index < count) {
            return leds[index];
        }
        return Vec3b();
    }

    //LedsToSet MUST be of length count
    //Returns number of leds set
    int putLEDs(Vec3b (*allLeds)[FADECANDY_NUM_STRIPS*FADECANDY_MAX_LEDSPEROUT]) {
        int startIdx = (fcOffset*FADECANDY_MAX_LEDSPEROUT)+startIndex;
        for (int l=0; l<count; l++) {
            Vec3b color = getLed(l);
            (*allLeds)[startIndex+l][0] = color[0];
            (*allLeds)[startIndex+l][1] = color[1];
            (*allLeds)[startIndex+l][2] = color[2];
        }
        return count;
    }
};

class LED {
public:
    LEDStrip top;
    LEDStrip right;
    LEDStrip bottom;
    LEDStrip left;
    OPCClient opc;

    LED() {
        top.setValues(0, 0, 52, false);
        right.setValues(2, 28, 28, true);
        bottom.setValues(1, 0, 52, false);
        left.setValues(2, 0, 28, false);

        printf("Connecting to OPC socket...\n");
        bool result = initialize();
        printf("Connection was %s\n", (result?"successful":"unsuccessful"));;
    }

    /*
    ~LED() {
        if (opc.isConnected()) {
            opc.closeSocket();
        }
    }
    */

    bool ledsConnected() {
        return opc.isConnected();
    }

    //Sends over the LED buffers
    bool sendLEDs() {
        int ledCount = 0;
        ledCount += top.putLEDs(&leds);
        ledCount += bottom.putLEDs(&leds);

        ledCount += left.putLEDs(&leds);
        ledCount += right.putLEDs(&leds);

        uint8_t outleds[ledCount*3];
        for (int l=0; l<ledCount; l++) {
            uint8_t outpxR = leds[l][2];
            uint8_t outpxG = leds[l][1];
            uint8_t outpxB = leds[l][0];
            outleds[l+0] = outpxR;
            outleds[l+1] = outpxG;
            outleds[l+2] = outpxB;
        }

        if (ledsConnected()) {
            return opc.write(outleds, ledCount*3);
        }

        return false;
    }

    bool initialize() {
        bool resolve = opc.resolve(OPC_SOCKET_HOST, OPC_SOCKET_PORT);
        if (resolve) {
            return opc.tryConnect();
        }
        return false;
    }

private:
    Vec3b leds[FADECANDY_NUM_STRIPS*FADECANDY_MAX_LEDSPEROUT];
};

void getAvgColorForFrame(Mat &frame, 
    Point topLeftPoint, Point bottomRightPoint, 
    Vec3b &outColor) {

    int pixHeight = bottomRightPoint.y - topLeftPoint.y;
    int pixWidth = bottomRightPoint.x - topLeftPoint.x;

    double sumColR = 0.0, sumColG = 0.0, sumColB = 0.0;
    for (int x=topLeftPoint.x; x<bottomRightPoint.x; x++) {
        double sumRowR = 0.0, sumRowG = 0.0, sumRowB = 0.0;
        for (int y=topLeftPoint.y; y<bottomRightPoint.y; y++) {
            Vec3b px = frame.at<Vec3b>(y,x);
            sumRowR += px[0];
            sumRowG += px[1];
            sumRowB += px[2];
        }
        sumColR += sumRowR / pixWidth;
        sumColG += sumRowG / pixWidth;
        sumColB += sumRowB / pixWidth;
    }

    outColor[0] = sumColR / pixHeight;
    outColor[1] = sumColG / pixHeight;
    outColor[2] = sumColB / pixHeight;
}

int processFrame(Mat &frame, LED &leds) {
    clock_t frameStartClock = clock();

    Mat blurImg;
    blur(
        frame, blurImg, 
        Size(BLUR_AMT, BLUR_AMT), Point(-1,-1), 
        BORDER_DEFAULT
    );

    int ledArr[FADECANDY_NUM_STRIPS*FADECANDY_MAX_LEDSPEROUT][3];
    
    leds.top.initializeLeds();
    leds.bottom.initializeLeds();

    leds.left.initializeLeds();
    leds.right.initializeLeds();

    Vec3b color, outColor;
    Point pointTL, pointBR;

    for (int s=0; s<leds.top.count; s++) {
        pointTL = Point(
            startX + (s*squareWidth),
            0
        );
        pointBR = Point(
            startX + ((s+1)*squareWidth),
            squareHeight*RECTANGLE_SPREAD_MULTIPLIER
        );

        if (pointBR.x > VIDEO_FEED_WIDTH) {
            break;
        }

        getAvgColorForFrame(blurImg, pointTL, pointBR, color);
        leds.top.setLed(s, color);
        outColor = leds.top.getLed(s);
        rectangle(frame, pointTL, pointBR, outColor, -1);


        pointTL = Point(
            startX + (s*squareWidth),
            VIDEO_FEED_HEIGHT - (squareHeight*RECTANGLE_SPREAD_MULTIPLIER)
        );
        pointBR = Point(
            startX + ((s+1)*squareWidth),
            VIDEO_FEED_HEIGHT
        );

        getAvgColorForFrame(blurImg, pointTL, pointBR, color);
        leds.bottom.setLed(s, color);
        outColor = leds.bottom.getLed(s);
        rectangle(frame, pointTL, pointBR, outColor, -1);
    }

    for (int s=0; s<leds.left.count; s++) {
        pointTL = Point(
            0,
            startY + (s*squareHeight)
        );
        pointBR = Point(
            squareWidth*RECTANGLE_SPREAD_MULTIPLIER,
            startY + ((s+1)*squareHeight)
        );

        if (pointBR.y > VIDEO_FEED_HEIGHT) {
            break;
        }

        getAvgColorForFrame(blurImg, pointTL, pointBR, color);
        leds.left.setLed(s, color);
        outColor = leds.left.getLed(s);
        rectangle(frame, pointTL, pointBR, outColor, -1);


        pointTL = Point(
            VIDEO_FEED_WIDTH - (squareWidth*RECTANGLE_SPREAD_MULTIPLIER),
            startY + (s*squareHeight)
        );
        pointBR = Point(
            VIDEO_FEED_WIDTH,
            startY + ((s+1)*squareHeight)
        );

        getAvgColorForFrame(blurImg, pointTL, pointBR, color);
        leds.right.setLed(s, color);
        outColor = leds.right.getLed(s);
        rectangle(frame, pointTL, pointBR, outColor, -1);
    }

    leds.sendLEDs();
    
    if (USE_DISPLAY) {
        Scalar color = Scalar(255, 0, 0); //bgr
        putText(frame, "Press q to quit", Point(
                (squareWidth*RECTANGLE_SPREAD_MULTIPLIER)+5, 
                (squareHeight*RECTANGLE_SPREAD_MULTIPLIER)+5
            ),
            FONT_HERSHEY_PLAIN, 0.75, color, 1);

        clock_t frameEndClock = clock();
        double diff = (double)(frameEndClock - frameStartClock) / 
            CLOCKS_PER_SEC; //CPS declared in <time.h>

        std::stringstream str;
        str << "Frame time: " << diff << " seconds";
        putText(frame, str.str(), Point(
                (squareWidth*RECTANGLE_SPREAD_MULTIPLIER)+5, 
                (squareHeight*RECTANGLE_SPREAD_MULTIPLIER)+15
            ),
            FONT_HERSHEY_PLAIN, 0.75, color, 1);
    }

    imshow("feed", frame);
    //imshow("blur", blurImg);

    char key = (char)waitKey(30);
    if (key == 'q') {
        return -1;
    }

    return 1;
}

void test() {
    /*
    int testLeds[192][3];

    testLeds[0][0] = 255;
    testLeds[0][1] = 0;
    testLeds[0][2] = 0;

    testLeds[1][0] = 0;
    testLeds[1][1] = 255;
    testLeds[1][2] = 0;

    int newColor[1][3];
    newColor[0][0] = 10;
    newColor[0][1] = 10;
    newColor[0][2] = 10;

    LEDStrip first(0, 0, 1, false);
    LEDStrip second(0, 1, 1, false);

    first.putLEDs(&testLeds, newColor);

    printf("Set1? (%d %d %d) \n", testLeds[0][0], testLeds[0][1], testLeds[0][2]);
    printf("Set2? (%d %d %d) \n", testLeds[1][0], testLeds[1][1], testLeds[1][2]);
    printf("OP\n");
    second.putLEDs(&testLeds, newColor);
    printf("Set1? (%d %d %d) \n", testLeds[0][0], testLeds[0][1], testLeds[0][2]);
    printf("Set2? (%d %d %d) \n", testLeds[1][0], testLeds[1][1], testLeds[1][2]);
    */
}

void setupEnvironment() {
    squareWidth = VIDEO_FEED_WIDTH / NUM_LEDS_HORIZ;
    squareHeight = VIDEO_FEED_HEIGHT / NUM_LEDS_VERT;

    startX = int(((double)VIDEO_FEED_WIDTH/2.0)-((double)NUM_LEDS_HORIZ*(double)squareWidth*0.5));
    startY = int(((double)VIDEO_FEED_HEIGHT/2.0)-((double)NUM_LEDS_VERT*(double)squareHeight*0.5));

    printf("LED Square: [%dx%d]\n", squareWidth, squareHeight);

    if (USE_DISPLAY) {
        namedWindow("feed",1);
    }
}

int main(int argc, char **argv) {
    printf("Starting up\n");

    setupEnvironment();

    LED leds;
    Mat frame;

    if (IS_PI) {
        #ifdef __arm__
            raspicam::RaspiCam_Cv raspicam;
            printf("RaspiCam video feed opening...\n");
            raspicam.set( CV_CAP_PROP_FORMAT, CV_8UC1 ); //?
            if (USE_CAMERA) {
                if (!raspicam.open()) {
                    printf("RaspiCam not opened\n");
                    return -1;
                }
                sleep(2);
            } else {
                printf("Pi capture from file unavailable\n");
                return -1;
            }
            printf("RaspiCam video feed opened\n");
            
            while (true) {
                raspicam.grab();
                raspicam.retrieve(frame);
                if (frame.empty()) {
                    break;
                }
                int out = processFrame(frame, leds);
                if (out == -1) {
                    break;
                }
            }
            raspicam.release();

            printf("RaspiCam video feed closed\n");
        #else
            printf("Can't use RaspiCam without a Pi!\n");
            return -1;
        #endif
    }
    else {
        VideoCapture camera = NULL;
        printf("CV2 video feed opening...\n");
        if (USE_CAMERA) {
            VideoCapture camera(0);
            while (!camera.isOpened()) {
                printf("Camera not opened. Trying again....\n");
                usleep(10000);
            }
        } else {
            printf("Capturing from file: \"%s\"\n", VIDEO_LOC);
            VideoCapture camera(VIDEO_LOC);
        }
        printf("CV2 video feed opened\n");

        while (true) {
            camera >> frame;
            if (frame.empty()) {
                break;
            }
            int out = processFrame(frame, leds);
            if (out == -1) {
                break;
            }
        }
        camera.release();

        printf("CV2 video feed closed\n");
    }

    return 0;
}