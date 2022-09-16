import sys
import os
import pandas as pd
import numpy as np

from PyQt5 import uic
from PyQt5.QtWidgets import QApplication, QMainWindow, QHBoxLayout, QPushButton, QFileDialog
from PyQt5.QtChart import QChartView
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import QThreadPool

from PIL.ImageQt import ImageQt
from PIL import Image

from threadWorker import WorkerSignals, Worker
from TripplePlot import TripplePlot
from quart import Quaternion
from positionTrack import QCompFilter
from render import Obj_Renderer
from clock import Clock

class MainWindow(QMainWindow):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        uic.loadUi("mainwindow.ui", self)

        self.accelView = TripplePlot("Accelerometer")
        self.plotLayout.addWidget(self.accelView)

        self.gyroView = TripplePlot("Gyroscope ")
        self.plotLayout.addWidget(self.gyroView)

        self.displayButton = QPushButton('Display')
        self.buttonLayout.addWidget(self.displayButton)
        self.displayButton.clicked.connect(self.diplayPlots)

        self.renderButton = QPushButton('Render')
        self.buttonLayout.addWidget(self.renderButton)
        self.renderButton.clicked.connect(self.renderPlots)

        self.clearButton = QPushButton('Clear')
        self.buttonLayout.addWidget(self.clearButton)
        self.clearButton.clicked.connect(self.clearPlots)

        self.displaywindow = DisplayWindow()

        self.df = pd.DataFrame()
        self.renderObject = Obj_Renderer("demo.obj")
        self.threadpool = QThreadPool()

    def diplayPlots(self):
        nameFilters = {"comma seperated file (*.csv)"}

        fileSelector = QFileDialog()
        fileSelector.setNameFilters(nameFilters)

        if (fileSelector.exec()):
            print(fileSelector.selectedFiles())

            df = pd.read_csv(fileSelector.selectedFiles()[0], on_bad_lines='warn', skip_blank_lines=True, encoding='utf-8', encoding_errors='ignore', names=["timestamp", "accelX", "accelY", "accelZ", "baselineX", "baselineY", "baselineZ", "gyroX", "gyroY", "gyroZ", "impactLevel"])
            df = df.dropna()

            timestamps = [(i-df.timestamp[0]) * 0.122*10**-3 for i in df.timestamp]

            self.accelView.plot(timestamps, df.accelX, df.accelY, df.accelZ)
            self.gyroView.plot(timestamps, df.gyroX, df.gyroY, df.gyroZ)

            self.df = df

    def renderPlots(self):
#        self.displaywindow.display('C:\\Users\\Dafro\\Documents\\CreoXGolf\\temp.gif')

        qinit = Quaternion(1, [0, 0, 0])
        gyroNoise = [[0.0000308652], [0.0000096461], [0.0000239652]]
        accelNoise = [[0.0000165938], [0.0000139291], [0.0000190058]]
        aRefrence = [[0], [0], [-1]]

        if (len(self.df) > 0):
            print('df has items')
            filterObject = QCompFilter(aRefrence, qinit, 0.5, False)

            worker = Worker(filterObject.applyData, self.df) # Any other args, kwargs are passed to the run function
            worker.signals.result.connect(self.rotationCalculated)
#            worker.signals.progress.connect(self.progress_fn)

            self.threadpool.start(worker)


    def rotationCalculated(self, rotations):
        worker = Worker(self.renderObject.render_image, rotations) # Any other args, kwargs are passed to the run function
        worker.signals.result.connect(self.renderCalculated)
#            worker.signals.progress.connect(self.progress_fn)
        self.threadpool.start(worker)


    def renderCalculated(self, images):
        images = [Image.fromarray((image.numpy() * 255).astype(np.uint8)) for image in images]

        directory = os.path.expanduser('~\Documents\\CreoXGolf')
        if not os.path.isdir(directory):
            os.mkdir(directory)

        gifFilename = directory+"\\temp.gif"

        images[0].save(gifFilename, save_all=True, append_images=images[1:], duration=100)

        print('done')

        self.displaywindow.display(gifFilename)

    def clearPlots(self):
        self.accelView.clear()
        self.gyroView.clear()


class DisplayWindow(QMainWindow):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        uic.loadUi("displaywindow.ui", self)

        self.pbFirstFrame.clicked.connect(self.displayFirstFrame)
        self.pbNextFrame.clicked.connect(self.displayNextFrame)
        self.pbPlayFrames.clicked.connect(self.playFrames)
        self.pbPrevFrame.clicked.connect(self.displayPrevFrame)
        self.pbLastFrame.clicked.connect(self.displayLastFrame)

        self.pixmaps = []
        self.frameNum = 0
        self.playStopToggle = True

        self.threadpool = QThreadPool()
        self.clock = Clock(98, 0, 0)
        self.clock.clockTick.connect(self.displayPlayFrame)

    def display(self, gifFilename):
        self.pixmaps = []

        with Image.open(gifFilename) as im:
            for i in range(im.n_frames):
                im.seek(i)
                frame = Image.new('RGBA', im.size)

                frame.paste(im, (0,0), im.convert('RGBA'))

                self.pixmaps.append(QPixmap.fromImage(ImageQt(frame)))

        self.displayPlayFrame(self.frameNum)
        self.show()

    def displayNextFrame(self):
        if (not self.playStopToggle):
            self.playFrames()

        self.frameNum += 1
        if (self.frameNum >= len(self.pixmaps)):
            self.frameNum = 0

        self.displayPlayFrame(self.frameNum)

    def displayPrevFrame(self):
        if (not self.playStopToggle):
            self.playFrames()

        self.frameNum -= 1
        if (self.frameNum <= 0):
            self.frameNum = len(self.pixmaps)-1

        self.displayPlayFrame(self.frameNum)

    def displayFirstFrame(self):
        if (not self.playStopToggle):
            self.playFrames()

        self.frameNum = 0
        self.displayPlayFrame(self.frameNum)

    def displayLastFrame(self):
        if (not self.playStopToggle):
            self.playFrames()

        self.frameNum = len(self.pixmaps)-1
        self.displayPlayFrame(self.frameNum)

    def playFrames(self):
        if (self.playStopToggle):
            self.clock.start = self.frameNum
            self.clock.end = len(self.pixmaps)
            worker = Worker(self.clock.startTick) # Any other args, kwargs are passed to the run function
            self.threadpool.start(worker)

            self.pbPlayFrames.setText('Stop')
            self.playStopToggle = False
        else:
            self.clock.stopTick()

            self.pbPlayFrames.setText('Play')
            self.playStopToggle = True

    def displayPlayFrame(self, frameNum):
        self.frameNum = frameNum
        self.image.setPixmap(self.pixmaps[self.frameNum])

        self.lblFrameNum.setText(f'{self.frameNum+1}:{len(self.pixmaps)}')


if __name__ == "__main__":
    app = QApplication(sys.argv)

    window = MainWindow()
    window.show()
    app.exec_()
