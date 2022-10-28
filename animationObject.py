from PyQt5.QtCore import QObject, QThreadPool, pyqtSignal, pyqtSlot
from PyQt5.QtGui import QPixmap
from PIL.ImageQt import ImageQt
from PIL import Image
import time

from threadWorker import WorkerSignals, Worker

class Clock(QObject):

    clockTick = pyqtSignal(int)

    def __init__(self, delay, start, end):
        QObject.__init__(self)

        self.delay = delay
        self.start = start
        self.end = end

    def startTick(self):
        self.tick  = True
        tick = self.start
        while ((tick <= self.end) and self.tick):
            self.clockTick.emit(tick)
            time.sleep(self.delay/1000)
            tick += 1

        if (self.tick):
            self.clockTick.emit(0)

    def stopTick(self):
        self.tick = False


class Animation(QObject):

    def __init__(self, imageDisplay, frameDisplay, playButton):
        QObject.__init__(self)

        self.imageDisplay = imageDisplay
        self.frameDisplay = frameDisplay
        self.playButton = playButton

        self.pixmaps = []
        self.frameNum = 0
        self.playStopToggle = True

        self.threadpool = QThreadPool()
        self.clock = Clock(98, 0, 0)
        self.clock.clockTick.connect(self.displayFrame)

    def openGif(self, gifFilename):
        self.pixmaps = []
        self.frameNum = 0
        self.playStopToggle = True
        self.playButton.setText('Play')

        with Image.open(gifFilename) as im:
            for i in range(im.n_frames):
                im.seek(i)
                frame = Image.new('RGBA', im.size)
                frame.paste(im, (0,0), im.convert('RGBA'))
                self.pixmaps.append(QPixmap.fromImage(ImageQt(frame)))

    def displayFrame(self, frameNum):
        self.frameNum = frameNum
        if (frameNum < 0):
            self.frameNum = len(self.pixmaps)-1

        if (frameNum == len(self.pixmaps)):
            self.frameNum = 0
            if (not self.playStopToggle):
                self.togglePlay()

        self.imageDisplay.setPixmap(self.pixmaps[self.frameNum])
        self.frameDisplay.setText(f'{self.frameNum+1}:{len(self.pixmaps)}')

    def displayNextFrame(self):
        self.displayFrame(self.frameNum+1)

    def displayPrevFrame(self):
        self.displayFrame(self.frameNum-1)

    def displayFirstFrame(self):
        self.displayFrame(0)

    def displayLastFrame(self):
        self.displayFrame(len(self.pixmaps)-1)

    def togglePlay(self):
        if (self.playStopToggle):
            self.clock.start = self.frameNum
            self.clock.end = len(self.pixmaps)
            worker = Worker(self.clock.startTick)
            self.threadpool.start(worker)

            self.playButton.setText('Stop')
            self.playStopToggle = False
        else:
            self.clock.stopTick()

            self.playButton.setText('Play')
            self.playStopToggle = True


