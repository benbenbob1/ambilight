from enum import Enum
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
FPS = 10

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

ledController = opc.Client('127.0.0.1:7890')
if ledController.can_connect():
    print('Connected to LED OPC')

camera = None
piCapture = None
useDisplay = True

isPi = False
try:
    import picamera as pc
    from picamera.array import PiRGBArray
    isPi = True
except ImportError:
    isPi = False

squareWidth = int(VIDEO_FEED_SIZE[0] / numLedsHoriz)
squareHeight = int(VIDEO_FEED_SIZE[1] / numLedsVert)

startX = int((VIDEO_FEED_SIZE[0]/2.0)-(numLedsHoriz*squareWidth*0.5))
startY = int((VIDEO_FEED_SIZE[1]/2.0)-(numLedsVert*squareHeight*0.5))

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
            print "ERROR: Can't write to LED "+str(startIdx)
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

#METHODS

leds = None

#[[r,g,b], [r,g,b], ...]
def sendLEDs(arr):
    normalized = np.fmin(np.fmax(arr, 0), 255)
    global ledController
    if ledController is not None:
        ledController.put_pixels(normalized, channel=0)

# returns (r, g, b)
def getAvgColorForFrame(frame, topLeftPoint, bottomRightPoint):
    box = frame[
        topLeftPoint[1]:bottomRightPoint[1],
        topLeftPoint[0]:bottomRightPoint[0]
    ]
    boxColor = np.nanmean(
        np.nanmean(box, axis=0),
    axis=0)
    return boxColor

def doLoop(isPi):
    global leds

    blurKernel = cv2.getStructuringElement(cv2.MORPH_RECT,(10,15))

    leds = np.uint8([[0,0,0]] * 64*3)

    # Returns: 
    #   bool: should continue loop
    def processFrame(frame):
        global leds

        leds = np.fmin(np.fmax(np.subtract(leds,FADE_AMT_PER_FRAME), 0), 255);

        # resize frame
        frame = imutils.resize(frame, 
            width=VIDEO_FEED_SIZE[0]
        )

        dateTimeStr = datetime.datetime.now().strftime("%A %d %B %Y %I:%M:%S%p")
        
        cv2.putText(frame, dateTimeStr, 
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

        if (SHOW_FPS):
            fps = camera.get(cv2.CAP_PROP_FPS)
            cv2.putText(frame, "FPS: "+str(fps), 
                (
                    (squareWidth*RECTANGLE_SPREAD_MULTIPLIER)+10, 
                    (squareHeight*RECTANGLE_SPREAD_MULTIPLIER)+35
                ),
                cv2.FONT_HERSHEY_PLAIN, 0.75, (255,100,50), 1
            )

        startTime = timeit.default_timer()
        blur = cv2.blur(frame, (BLUR_AMT, BLUR_AMT), (-1, -1))
        elapsed = timeit.default_timer() - startTime
        cv2.putText(frame, "Blur time: "+str(elapsed), 
            (
                (squareWidth*RECTANGLE_SPREAD_MULTIPLIER)+10, 
                (squareHeight*RECTANGLE_SPREAD_MULTIPLIER)+45
            ),
            cv2.FONT_HERSHEY_PLAIN, 0.75, (255,100,100), 1
        )

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
            avgCol = getAvgColorForFrame(blur, pointTL, pointBR)
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
            avgCol = getAvgColorForFrame(blur, pointTL, pointBR)
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
            avgCol = getAvgColorForFrame(blur, pointTL, pointBR)
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
            avgCol = getAvgColorForFrame(blur, pointTL, pointBR)
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

        if useDisplay:

            cv2.imshow("Feed", frame)
            #cv2.imshow("BBLUR", blur)    

            # exit on 'q' key press
            key = cv2.waitKey(1) & 0xFF
            if key == ord("q"):
                return False

        sendLEDs(leds.tolist())

        return True

    if (isPi):
        print "Using Pi's PiCamera"
        camera = pc.PiCamera()
        camera.resolution = tuple(VIDEO_FEED_SIZE)
        camera.framerate = FPS
        piCapture = PiRGBArray(camera, size=tuple(VIDEO_FEED_SIZE))
        time.sleep(2.5)
        print("Pi video feed opened")
        for f in camera.capture_continuous(
            piCapture, 
            format="bgr",
            use_video_port=True):
            frame = f.array
            loop = processFrame(frame)
            if (not loop):
                piCapture.truncate(0)
                break
            piCapture.truncate(0)
        closeGently(isPi, None)
    else:
        print "Using CV2's VideoCapture"
        # get video feed from default camera device
        camera = cv2.VideoCapture(0)
        while (True):
            if not camera.isOpened():
                time.sleep(2)
            else:
                break
        print("CV2 video feed opened")
        while (True):
            # get single frame
            response, frame = camera.read()
            if not response:
                print("Error: could not obtain frame")
                # couldn't obtain a frame
                break
            loop = processFrame(frame)
            if (not loop):
                break

        closeGently(isPi, camera)

def closeGently(isPi, camera):
    if (not isPi):
        camera.release()

    print("Video feed closed")
    cv2.destroyAllWindows()

#ENDMETHODS


print("Attaching to camera...")

doLoop(isPi)