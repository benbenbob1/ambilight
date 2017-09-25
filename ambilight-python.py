from enum import Enum
from threading import Thread
from imutils.video import FPS
import datetime
import time
import imutils
import warnings
import numpy as np
import opc
import timeit

# and now the most important of all
import cv2

VIDEO_FEED_SIZE = [720, 405] #[width, height] in pixels
FRAMERATE = 15

BLUR_AMT = 19

#amount to go "inwards" multiplied by current rectangle width or height
RECTANGLE_SPREAD_MULTIPLIER = 4

COLOR_SPREAD = 1 # number of margin leds before + after the colorbar to light up
FADE_AMT_PER_FRAME = 0.1 * 255 # amount to fade between every frame

SHOW_FPS = True

numLedsHoriz = 52
numLedsVert = 28
MAX_LEDS = max(numLedsHoriz, numLedsVert)
numLedsTotal = (numLedsVert * 2) + (numLedsHoriz * 2)

FADECANDY_NUM_STRIPS = 3
FADECANDY_MAX_LEDSPEROUT = 64

squareWidth = int(VIDEO_FEED_SIZE[0] / numLedsHoriz)
squareHeight = int(VIDEO_FEED_SIZE[1] / numLedsVert)

startX = int((VIDEO_FEED_SIZE[0]/2.0)-(numLedsHoriz*squareWidth*0.5))
startY = int((VIDEO_FEED_SIZE[1]/2.0)-(numLedsVert*squareHeight*0.5))

globalIsPi = False

try:
    import picamera as pc
    from picamera.array import PiRGBArray
    globalIsPi = True

class FadecandyOffset:
    fcOffset = 0
    count = 0
    startIndex = 0
    inverted = False
    def __init__(self, fadecandyIndex, startIndex, numLeds, isInverted):
        self.fcOffset = fadecandyIndex
        self.startIndex = startIndex
        self.count = numLeds
        self.inverted = isInverted
    def putLEDs(self, leds, ledColors):
        startIdx = (self.fcOffset*FADECANDY_MAX_LEDSPEROUT)+self.startIndex
        if (len(leds) < self.count or 
            len(leds) < startIdx + self.count or 
            len(ledColors) < self.count):
            print("ERROR: Can't write to LED "+str(startIdx))
            return
        leds[startIdx:startIdx+self.count] = ledColors

# Strip: Fadecandy Offset, led start - led end
# Top:      0, 0 - 51
# Bottom:   1, 0 - 51
# Left:     2, 0 - 27
# Right:    2, 28- 55

class LEDPosition:
    TOP = FadecandyOffset(0, 0, 52, False)
    RIGHT = FadecandyOffset(2, 28, 28, False)
    BOTTOM = FadecandyOffset(1, 0, 52, False)
    LEFT = FadecandyOffset(2, 0, 28, False)

class Ambilight:

    ledController = opc.Client('127.0.0.1:7890')
    if ledController.can_connect():
        print('Connected to LED OPC')

    camera = None
    piCapture = None
    useDisplay = True
    stream = None
    stopped = False
    fps = None

    isPi = globalIsPi

    #METHODS

    leds = np.uint8([[0,0,0]] * 64*3)

    #[[r,g,b], [r,g,b], ...]
    def sendLEDs(self, arr):
        normalized = np.fmin(np.fmax(arr, 0), 255)
        if self.ledController is not None:
            self.ledController.put_pixels(normalized, channel=0)

    # returns (r, g, b)
    def getAvgColorForFrame(self, frame, topLeftPoint, bottomRightPoint):
        box = frame[
            topLeftPoint[1]:bottomRightPoint[1],
            topLeftPoint[0]:bottomRightPoint[0]
        ]
        boxColor = np.nanmean(
            np.nanmean(box, axis=0),
        axis=0)
        return boxColor

    def closeGently(self, isPi):
        if (not isPi):
            self.camera.release()
        else:
            self.stream.close()

        print("Video feed closed")
        cv2.destroyAllWindows()

    def __init__(self):
        self.start()

    def start(self):
        print("Starting up")
        self.fps = FPS().start()
        self.stopped = False
        if (self.isPi):
            print("Using Pi's PiCamera")
            self.camera = pc.PiCamera()
            self.camera.resolution = tuple(VIDEO_FEED_SIZE)
            self.camera.framerate = FRAMERATE
            self.piCapture = PiRGBArray(self.camera, size=tuple(VIDEO_FEED_SIZE))
            self.stream = self.camera.capture_continuous(
                self.piCapture, 
                format="bgr",
                use_video_port=True)
            time.sleep(2.0)
            print("Pi video feed opened")
            Thread(target=self.update, args=(True,)).start()
        else:
            print("Using CV2's VideoCapture")
            # get video feed from default camera device
            self.camera = cv2.VideoCapture(0)
            while (True):
                if not self.camera.isOpened():
                    time.sleep(2)
                else:
                    break
            print("CV2 video feed opened")
            while (True):
                response, frame = self.camera.read()
                if not response:
                    print("Error: CV2 could not obtain frame")
                    # couldn't obtain a frame
                    return
                self.processFrame(frame)
                self.update(False)

                if self.stopped:
                    self.closeGently(True)
                    return

    def update(self, isPi):
        if (isPi):
            for f in self.stream:
                frame = f.array
                self.processFrame(frame)
                self.piCapture.truncate(0)
                self.fps.update()

                if self.stopped:
                    self.closeGently(True)
                    return

    def processFrame(self, frame):
        leds = np.fmin(np.fmax(np.subtract(self.leds,FADE_AMT_PER_FRAME), 0), 255);

        # resize frame
        frame = imutils.resize(frame, 
            width=VIDEO_FEED_SIZE[0]
        )

        startTime = timeit.default_timer()
        blur = cv2.blur(frame, (BLUR_AMT, BLUR_AMT), (-1, -1))
        blurTime = timeit.default_timer() - startTime
        
        ledsTop = ([[0,0,0]] * LEDPosition.TOP.count)
        ledsRight = ([[0,0,0]] * LEDPosition.RIGHT.count)
        ledsBottom = ([[0,0,0]] * LEDPosition.BOTTOM.count)
        ledsLeft = ([[0,0,0]] * LEDPosition.LEFT.count)

        for s in range(0, numLedsHoriz):
            pointTL = (startX + (s*squareWidth), 0)
            pointBR = (
                startX + ((s+1)*squareWidth),
                squareHeight*RECTANGLE_SPREAD_MULTIPLIER
            )
            avgCol = self.getAvgColorForFrame(blur, pointTL, pointBR)
            ledsTop[s] = avgCol
            cv2.rectangle(
                frame, 
                pointTL,    #top left vertex
                pointBR,    #bottom right vertex
                avgCol,
                -1          #thickness, negative means filled
            )
            pointTL = (
                startX + (s*squareWidth),
                VIDEO_FEED_SIZE[1] -
                    (squareHeight*RECTANGLE_SPREAD_MULTIPLIER)
            )
            pointBR = (
                startX + ((s+1)*squareWidth),
                VIDEO_FEED_SIZE[1]
            )
            avgCol = self.getAvgColorForFrame(blur, pointTL, pointBR)
            ledsBottom[s] = avgCol
            cv2.rectangle(
                frame, 
                pointTL,
                pointBR,
                avgCol,
                -1
            )
        for s in range(1, numLedsVert-1):
            pointTL = (
                0, 
                startY + (s*squareHeight)
            )
            pointBR = (
                squareWidth*RECTANGLE_SPREAD_MULTIPLIER,
                startY + ((s+1)*squareHeight)
            )
            avgCol = self.getAvgColorForFrame(blur, pointTL, pointBR)
            ledsLeft[s] = avgCol
            cv2.rectangle(
                frame, 
                pointTL,    #top left vertex
                pointBR,    #bottom right vertex
                avgCol,
                -1          #thickness, negative means filled
            )
            pointTL = (
                VIDEO_FEED_SIZE[0] -
                    (squareWidth*RECTANGLE_SPREAD_MULTIPLIER),
                startY + (s*squareHeight)
            )
            pointBR = (
                VIDEO_FEED_SIZE[0],
                startY + ((s+1)*squareHeight)
            )
            avgCol = self.getAvgColorForFrame(blur, pointTL, pointBR)
            ledsRight[s] = avgCol
            cv2.rectangle(
                frame, 
                pointTL,
                pointBR,
                avgCol,
                -1
            )

        LEDPosition.TOP.putLEDs(leds, ledsTop)
        LEDPosition.RIGHT.putLEDs(leds, ledsRight)
        LEDPosition.BOTTOM.putLEDs(leds, ledsBottom)
        LEDPosition.LEFT.putLEDs(leds, ledsLeft)

        if self.useDisplay:
            dateTimeStr = datetime.datetime.now().strftime("%A %d %B %Y %I:%M:%S%p")
            cv2.putText(frame, str(dateTimeStr), 
                (
                    (squareWidth*RECTANGLE_SPREAD_MULTIPLIER)+10, 
                    (squareHeight*RECTANGLE_SPREAD_MULTIPLIER)+10
                ),
                cv2.FONT_HERSHEY_PLAIN, 0.5, (255,100,100), 1
            )
            cv2.putText(frame, "Press q to quit", 
                (
                    (squareWidth*RECTANGLE_SPREAD_MULTIPLIER)+10, 
                    (squareHeight*RECTANGLE_SPREAD_MULTIPLIER)+20
                ),
                cv2.FONT_HERSHEY_PLAIN, 0.5, (255,100,100), 1
            )

            if (SHOW_FPS and False):
                fps = self.fps.elapsed()
                cv2.putText(frame, "FPS: "+str(fps), 
                    (
                        (squareWidth*RECTANGLE_SPREAD_MULTIPLIER)+10, 
                        (squareHeight*RECTANGLE_SPREAD_MULTIPLIER)+35
                    ),
                    cv2.FONT_HERSHEY_PLAIN, 0.75, (255,100,50), 1
                )
            cv2.putText(frame, "Blur time: "+str(blurTime), 
                (
                    (squareWidth*RECTANGLE_SPREAD_MULTIPLIER)+10, 
                    (squareHeight*RECTANGLE_SPREAD_MULTIPLIER)+45
                ),
                cv2.FONT_HERSHEY_PLAIN, 0.75, (255,100,100), 1
            )

            cv2.imshow("Feed", frame)
            #cv2.imshow("BBLUR", blur)    

            # exit on 'q' key press
            key = cv2.waitKey(1) & 0xFF
            if key == ord("q"):
                self.stopped = True

        self.sendLEDs(leds.tolist())


Ambilight()