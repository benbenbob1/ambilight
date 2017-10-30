//Code to check the OpenCV installation on Raspberry Pi and measure frame rate
//Author: Samarth Manoj Brahmbhatt, University of Pennsyalvania
//Modified: George Profenza
#include "cap.h"
#include <opencv2/opencv.hpp>
#include <opencv2/highgui/highgui.hpp>

using namespace cv;
using namespace std;

PiCapture cap;
int awbMode,awbGainR,awbGainB,sat,effect,sharpness,iso,rectW,rectH;
void onAWB( int, void* ){
    cap.setAWBMode((MMAL_PARAM_AWBMODE_T)awbMode);
}
void onAWBGain( int, void* ){
    cap.setAWBGains((float)((double)awbGainR/100.0), (float)((double)awbGainB/100.0));
}
/*void onEffect(int, void* ){
    cap.setColourFX((MMAL_PARAM_COLOURFX_T)effect);
}*/
void onSharp(int, void* ){
    cap.setSharpness(sharpness);
}
void onSat(int, void* ){
    cap.setSaturation(sat-100);
}
void onISO(int, void* ){
    cap.setISO(iso+100);
}
void onRect(int, void* ){
    PiCapture::PARAM_FLOAT_RECT_T rect;
    rect.x = 0;
    rect.y = 0;
    rect.w = (double)((double)rectW/100.0);
    rect.h = (double)((double)rectH/100.0);
    cap.setROI(rect);
}
int main(int argc,char **argv) {
    bool isColor = true;
    namedWindow("PiCapture");
    cap.open(320, 240, isColor ? true : false);
	Mat im;
	double time = 0;
	unsigned int frames = 0;
    /*
    createTrackbar("AWB Mode","PiCapture",&awbMode,10,onAWB);
    createTrackbar("AWB Gain R","PiCapture",&awbGainR,100,onAWBGain);
    createTrackbar("AWB Gain G","PiCapture",&awbGainB,100,onAWBGain);
    */
    //createTrackbar("color effect","PiCapture",&effect,23,onEffect);
    createTrackbar("saturation","PiCapture",&sat,200,onSat);
    createTrackbar("sharpness","PiCapture",&sharpness,50,onSharp);
    createTrackbar("ISO","PiCapture",&iso,700,onISO);
    /*
    createTrackbar("Rect W","PiCapture",&rectW,100,onRect);
    createTrackbar("Rect H","PiCapture",&rectH,100,onRect);
    */

    PiCapture::PARAM_FLOAT_RECT_T cropRect;
    cropRect.x = 0.01;
    cropRect.y = 0.01;
    cropRect.w = 0.48;
    cropRect.h = 0.48;
    cap.setROI(cropRect);
    cap.setAWBMode(MMAL_PARAM_AWBMODE_OFF);
    cap.setAWBGains(1.0,1.0);
    cap.setExposureMode(MMAL_PARAM_EXPOSUREMODE_OFF);

    sleep(2);

    while(char(waitKey(1)) != 'q') {
		double t0 = getTickCount();
		im = cap.grab();
		frames++;
        if(!im.empty()) imshow("PiCapture", im);
        //else cout << "Frame dropped" << endl;
        time += (getTickCount() - t0) / getTickFrequency();
        //cout << frames / time << " fps" << endl;
	}
	return 0;
}
