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
FPS = 15

BLUR_AMT = 51

#amount to go "inwards" multiplied by current rectangle width or height
RECTANGLE_SPREAD_MULTIPLIER = 4

COLOR_SPREAD = 1 # number of margin leds before + after the colorbar to light up
FADE_AMT_PER_FRAME = 0.1 * 255 # amount to fade between every frame

SHOW_FPS = True

numLedsHoriz = 48
numLedsVert = 27
numLedsTotal = (numLedsVert * 2) + (numLedsHoriz * 2)
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

#METHODS

#warnings.simplefilter("ignore")

numLeds = 0

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

    leds = np.uint8([[0,0,0]] * numLedsTotal)

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
        
        # putText(frame,text,origin,font_face,font_scale,color,thickness)
        #cv2.putText(frame, text, (10, 20), cv2.FONT_HERSHEY_PLAIN, 
        #    0.5, (255,0,0), 1)
        cv2.putText(frame, dateTimeStr, 
            (
                (squareWidth*RECTANGLE_SPREAD_MULTIPLIER)+10, 
                (squareHeight*RECTANGLE_SPREAD_MULTIPLIER)+10
            ),
            cv2.FONT_HERSHEY_PLAIN, 0.5, (255,255,255), 1
        )
        cv2.putText(frame, "Press q to quit", 
            (
                (squareWidth*RECTANGLE_SPREAD_MULTIPLIER)+10, 
                (squareHeight*RECTANGLE_SPREAD_MULTIPLIER)+20
            ),
            cv2.FONT_HERSHEY_PLAIN, 0.5, (255,255,255), 1
        )


        startTime = timeit.default_timer()
        blur = cv2.blur(frame, (BLUR_AMT, BLUR_AMT), (-1, -1))
        elapsed = timeit.default_timer() - startTime
        cv2.putText(blur, "Blur time: "+str(elapsed), 
            (
                (squareWidth*RECTANGLE_SPREAD_MULTIPLIER)+10, 
                (squareHeight*RECTANGLE_SPREAD_MULTIPLIER)+10
            ),
            cv2.FONT_HERSHEY_PLAIN, 0.75, (255,100,100), 1
        )

        if useDisplay:
            temp = blur
            for s in range(0, numLedsHoriz):
                pointTL = (s*squareWidth, 0)
                pointBR = (
                    (s+1)*squareWidth, 
                    squareHeight*RECTANGLE_SPREAD_MULTIPLIER
                )
                avgCol = getAvgColorForFrame(temp, pointTL, pointBR)
                cv2.rectangle(
                    frame, 
                    pointTL,    #top left vertex
                    pointBR,    #bottom right vertex
                    avgCol,
                    -1          #thickness, negative means filled
                )
                pointTL = (
                    s*squareWidth, 
                    VIDEO_FEED_SIZE[1] -
                        (squareHeight*RECTANGLE_SPREAD_MULTIPLIER)
                )
                pointBR = ((s+1)*squareWidth, VIDEO_FEED_SIZE[1])
                avgCol = getAvgColorForFrame(temp, pointTL, pointBR)
                cv2.rectangle(
                    frame, 
                    pointTL,
                    pointBR,
                    avgCol,
                    -1
                )
            for s in range(1, numLedsVert-1):
                pointTL = (0, s*squareHeight)
                pointBR = (
                    squareWidth*RECTANGLE_SPREAD_MULTIPLIER,
                    (s+1)*squareHeight
                )
                avgCol = getAvgColorForFrame(temp, pointTL, pointBR)
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
                    s*squareHeight
                )
                pointBR = (VIDEO_FEED_SIZE[0], (s+1)*squareHeight)
                avgCol = getAvgColorForFrame(temp, pointTL, pointBR)
                cv2.rectangle(
                    frame, 
                    pointTL,
                    pointBR,
                    avgCol,
                    -1
                )

            cv2.imshow("Feed", frame)
            cv2.imshow("BBLUR", blur)    

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
            if (SHOW_FPS):
                fps = camera.get(cv2.CAP_PROP_FPS)
                cv2.putText(frame, "FPS: "+str(fps), (100, 100),
                    cv2.FONT_HERSHEY_PLAIN, 1, (255,100,50), 1)
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