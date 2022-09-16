from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot
import time

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
        while ((tick < self.end) and self.tick):
            self.clockTick.emit(tick)
            time.sleep(self.delay/1000)
            tick += 1

        if (self.tick):
            self.clockTick.emit(0)

    def stopTick(self):
        self.tick = False
