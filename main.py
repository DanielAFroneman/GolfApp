import sys
import os
import pandas as pd
import numpy as np
from PIL import Image
from PIL.ImageQt import ImageQt
from scipy.signal import find_peaks
from scipy.spatial.transform import Rotation

from PyQt5 import uic
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QPushButton, QFileDialog, QLabel
from PyQt5.QtChart import QChartView, QChart, QValueAxis, QSplineSeries, QLineSeries
from PyQt5.QtGui import QColor, QBrush, QPen, QPixmap
from PyQt5.QtCore import QThreadPool, Qt

from threadWorker import WorkerSignals, Worker
from TripplePlot import TripplePlot, whiteBrush, blackBrush
from animationObject import Animation
from quart import Quaternion
from positionTrack import QCompFilter
from render import Obj_Renderer

def swingDetection(accelLists, gyroLists, timeList):
    length = min(len(accelLists[0]), len(accelLists[1]), len(accelLists[2]), len(gyroLists[0]), len(gyroLists[1]), len(gyroLists[2]), len(timeList))
    avgTime = sum([(timeList[index] - timeList[index-1]) for index in range(1, length)])/(length-1)

    indexWindow = 5/avgTime

    accelMagList = [np.sqrt(accelLists[0][index]**2 + accelLists[1][index]**2 + accelLists[2][index]**2) for index in range(length)]
    gyroMagList = [np.sqrt(gyroLists[0][index]**2 + gyroLists[1][index]**2 + gyroLists[2][index]**2) for index in range(length)]

    accelHeight = max(accelMagList)*0.4
    gyroHeight = max(gyroMagList)*0.4
    accelPeakList, _ = find_peaks(accelMagList, prominence=1, distance=indexWindow, height=accelHeight)
    gyroPeakList, _ = find_peaks(gyroMagList, prominence=1, distance=indexWindow, height=gyroHeight)

    if len(accelPeakList) > len(gyroPeakList):
        largerList = accelPeakList
        smallerList = gyroPeakList
    else:
        largerList = gyroPeakList
        smallerList = accelPeakList

    peakList = []
    for peak1 in smallerList:
        nearIndexs = []
        for peak2 in largerList:
            if abs(peak1 - peak2) < indexWindow/2:
                nearIndexs.append(peak2)
        peakList.append((peak1+min(nearIndexs))/2)

    newAccelList = []
    newGyroList = []
    newTimeList = []
    newPeakList = []

    for peakIndex in peakList:
        windowStart = int(peakIndex-indexWindow/2)
        windowEnd = int(peakIndex+indexWindow/2)

        newAccelList.append([accelLists[0][windowStart:windowEnd],
                             accelLists[1][windowStart:windowEnd],
                             accelLists[2][windowStart:windowEnd],
                             accelMagList[windowStart:windowEnd]])
        newGyroList.append([gyroLists[0][windowStart:windowEnd],
                            gyroLists[1][windowStart:windowEnd],
                            gyroLists[2][windowStart:windowEnd],
                            gyroMagList[windowStart:windowEnd]])
        newTimeList.append(timeList[windowStart:windowEnd])

        newPeakList.append(int(peakIndex-windowStart-1))

    return newAccelList, newGyroList, newTimeList, newPeakList

def yawSpeedFromMatrix(matrixList, timeList, shoulderWidth):
    eularRot = [Rotation.from_matrix(matrix).as_euler('xyz', degrees=False) for matrix in matrixList]
    return [0.005*shoulderWidth*abs((eularRot[i][1] - eularRot[i-1][1])/(timeList[i] - timeList[i-1])) for i in range(1, len(eularRot))]

def swingAngleFromMatrix(matrixList, refrenceVector):
    gVector = np.array([[0],[-1],[0]])
    updatedGVector = [np.matmul(matrix, gVector) for matrix in matrixList]

    return [np.arccos(sum([a*b for a,b in zip(refrenceVector, vector)])[0])*180/np.pi for vector in updatedGVector]

class MainWindow(QMainWindow):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        uic.loadUi("mainwindow.ui", self)

        self.displayButton = QPushButton('Display')
        self.buttonLayout.addWidget(self.displayButton)
        self.displayButton.clicked.connect(self.diplayPlots)

        self.prevSwingButton.clicked.connect(self.prevSwing)
        self.nextSwingButton.clicked.connect(self.nextSwing)

        #############################################
        ##                 Load Data               ##
        #############################################
        self.accelView = TripplePlot("Accelerometer", "Time(s)", "Acceleration(g)")
        self.plotLayout.addWidget(self.accelView)

        self.gyroView = TripplePlot("Gyroscope", "Time(s)", "Rotational Velocity(deg/s)")
        self.plotLayout.addWidget(self.gyroView)

        #############################################
        ##             Move Hit location           ##
        #############################################
        self.moveHitRightButton.clicked.connect(self.hitRight)
        self.moveHitLeftButton.clicked.connect(self.hitLeft)

        #############################################
        ##                 Yaw Plot                ##
        #############################################
        self.yawSpeeds = []

        layout = QVBoxLayout()
        self.yawChartView = QChartView()
        layout.addWidget(self.yawChartView)
        self.tbYaw.setLayout(layout)

        self.leShoulderWidth.editingFinished.connect(self.updatedShoulderWidth)

        #############################################
        ##             Swing Angle Plot            ##
        #############################################
        self.swingAngles = []

        layout = QVBoxLayout()
        self.swingAngleChartView = QChartView()
        layout.addWidget(self.swingAngleChartView)
        self.tbSwingAngle.setLayout(layout)

        #############################################
        ##                 Ani Plot                ##
        #############################################
        self.pbFirstFrame.clicked.connect(self.displayFirstFrame)
        self.pbNextFrame.clicked.connect(self.displayNextFrame)
        self.pbPlayFrames.clicked.connect(self.playFrames)
        self.pbPrevFrame.clicked.connect(self.displayPrevFrame)
        self.pbLastFrame.clicked.connect(self.displayLastFrame)

        self.rendered = False

        self.directory = os.path.expanduser('~\Documents\\CreoXGolf')
        if not os.path.isdir(self.directory):
            os.mkdir(self.directory)

        #############################################
        ##             public variables            ##
        #############################################
        self.swingRotations = []
        self.aniObjects = []

        gyroNoise = [[0.0000308652], [0.0000096461], [0.0000239652]]
        accelNoise = [[0.0000165938], [0.0000139291], [0.0000190058]]
        aRefrence = [[0], [0], [-1]]
        self.filterObject = QCompFilter(aRefrence, 0.8, 0.1, False)

        self.renderObject = Obj_Renderer("axis.obj")
        self.threadpool = QThreadPool()

    def diplayPlots(self):
        self.nextSwingButton.setEnabled(False)
        self.prevSwingButton.setEnabled(False)

        self.moveHitRightButton.setEnabled(False)
        self.moveHitLeftButton.setEnabled(False)

        nameFilters = {"comma seperated file (*.csv)"}

        fileSelector = QFileDialog()
        fileSelector.setNameFilters(nameFilters)

        if (fileSelector.exec()):
            print(fileSelector.selectedFiles())

            df = pd.read_csv(fileSelector.selectedFiles()[0], on_bad_lines='warn', skip_blank_lines=True, encoding='utf-8', encoding_errors='ignore', names=["timestamp", "accelX", "accelY", "accelZ", "baselineX", "baselineY", "baselineZ", "gyroX", "gyroY", "gyroZ", "impactLevel"])
            df = df.dropna()

            timestamps = [(i-df.timestamp[0]) * 0.122*10**-3 for i in df.timestamp]

            self.accelList, self.gyroList, self.timeList, self.peakList = swingDetection([df.accelX.values.tolist(), df.accelY.values.tolist(), df.accelZ.values.tolist()],
                                                                                         [df.gyroX.values.tolist(), df.gyroY.values.tolist(), df.gyroZ.values.tolist()],
                                                                                         timestamps)

            ############################################################################################################################################################
#            self.accelList = [df.accelX.values.tolist(),
#                              df.accelY.values.tolist(),
#                              df.accelZ.values.tolist()]

#            self.gyroList = [df.gyroX.values.tolist(),
#                             df.gyroY.values.tolist(),
#                             df.gyroZ.values.tolist()]

#            accelMagList = [np.sqrt(self.accelList[0][index]**2 + self.accelList[1][index]**2 + self.accelList[2][index]**2) for index in range(len(timestamps))]
#            gyroMagList = [np.sqrt(self.gyroList[0][index]**2 + self.gyroList[1][index]**2 + self.gyroList[2][index]**2) for index in range(len(timestamps))]

#            self.accelList = [[self.accelList[0],
#                               self.accelList[1],
#                               self.accelList[2],
#                               accelMagList]]

#            self.gyroList = [[self.gyroList[0],
#                              self.gyroList[1],
#                              self.gyroList[2],
#                              gyroMagList]]

#            self.timeList = [timestamps]
            ############################################################################################################################################################

            self.swingIndex = 0
            self.maxIndex = len(self.timeList)
            self.swingIndicatorLabel.setText(f'{self.swingIndex+1}/{self.maxIndex}')

            self.accelView.plot(self.timeList[self.swingIndex], self.accelList[self.swingIndex], self.peakList[self.swingIndex])
            self.gyroView.plot(self.timeList[self.swingIndex], self.gyroList[self.swingIndex], self.peakList[self.swingIndex])

            print('Rotation Calculations Start')

            worker = Worker(self.filterObject.batchApply, self.timeList, self.accelList, self.gyroList)
            worker.signals.result.connect(self.rotationCalculated)
            self.threadpool.start(worker)

            self.aniObjects = [Animation(self.image, self.lblFrameNum, self.pbPlayFrames) for _ in range(self.maxIndex)]
            self.displayAnimation()

    def renderSwing(self):
        print('Render Start')
        self.pbPlayFrames.setEnabled(False)

        with Image.open("loading.png") as im:
            self.image.setPixmap(QPixmap.fromImage(ImageQt(im)))

        worker = Worker(self.renderObject.render_image, self.rotations[self.swingIndex][:self.peakList[self.swingIndex]])
        worker.signals.result.connect(self.renderCalculated)

        self.threadpool.start(worker)

    def prevSwing(self):
        if (self.swingIndex > 0):
            self.swingIndex -= 1
            self.swingIndicatorLabel.setText(f'{self.swingIndex+1}/{self.maxIndex}')
            self.accelView.plot(self.timeList[self.swingIndex], self.accelList[self.swingIndex], self.peakList[self.swingIndex])
            self.gyroView.plot(self.timeList[self.swingIndex], self.gyroList[self.swingIndex], self.peakList[self.swingIndex])

            self.displayYawData(self.timeList[self.swingIndex][1:], self.yawSpeeds[self.swingIndex])
            self.displaySwingAnlgeData(self.timeList[self.swingIndex], self.swingAngles[self.swingIndex])
            self.displayAnimation()

    def nextSwing(self):
        if (self.swingIndex < self.maxIndex-1):
            self.swingIndex += 1
            self.swingIndicatorLabel.setText(f'{self.swingIndex+1}/{self.maxIndex}')
            self.accelView.plot(self.timeList[self.swingIndex], self.accelList[self.swingIndex], self.peakList[self.swingIndex])
            self.gyroView.plot(self.timeList[self.swingIndex], self.gyroList[self.swingIndex], self.peakList[self.swingIndex])

            self.displayYawData(self.timeList[self.swingIndex][1:], self.yawSpeeds[self.swingIndex])
            self.displaySwingAnlgeData(self.timeList[self.swingIndex], self.swingAngles[self.swingIndex])
            self.displayAnimation()

    def updatedShoulderWidth(self):
        self.yawSpeeds = [yawSpeedFromMatrix(self.rotations[i], self.timeList[i], float(self.leShoulderWidth.text())) for i in range(self.maxIndex)]
        self.displayYawData(self.timeList[self.swingIndex][1:], self.yawSpeeds[self.swingIndex])

    def displayYawData(self, timeList, yawSpeed):
        self.yawPlotChart = QChart()
        self.yawPlotChart.setTitle('Yaw')
        self.yawPlotChart.setTitleBrush(whiteBrush)
        self.yawPlotChart.setBackgroundBrush(blackBrush)
        self.yawChartView.setChart(self.yawPlotChart)

        self.yawPlotChart.legend().hide()

        axisX = QValueAxis()
        axisX.setTitleText('Time(s)')
        axisX.setTitleBrush(whiteBrush)
        axisX.setLabelsBrush(whiteBrush)
        axisX.setGridLineVisible(False)
        axisX.setTickCount(11)
        self.yawPlotChart.addAxis(axisX, Qt.AlignBottom)

        axisY = QValueAxis()
        axisY.setTitleText('Speed(m/s)')
        axisY.setTitleBrush(whiteBrush)
        axisY.setLabelsBrush(whiteBrush)
        axisY.setGridLineVisible(False)
        axisY.setTickCount(9)
        self.yawPlotChart.addAxis(axisY, Qt.AlignLeft)

        yawSeries = QSplineSeries()
        yawSeries.setPen(QPen(QColor("Red"), 1))

        hitSeries = QLineSeries()
        hitSeries.setPen(QPen(QColor("White"), 1))

        hitSeries.append(timeList[self.peakList[self.swingIndex]], max(yawSpeed) + 0.1*(max(yawSpeed)-min(yawSpeed)))
        hitSeries.append(timeList[self.peakList[self.swingIndex]], 0)

        length = min(len(timeList), len(yawSpeed))

        for index in range(length):
            yawSeries.append(timeList[index], yawSpeed[index])

        self.yawPlotChart.addSeries(yawSeries)
        self.yawPlotChart.addSeries(hitSeries)

        yawSeries.attachAxis(axisX)
        yawSeries.attachAxis(axisY)

        hitSeries.attachAxis(axisX)
        hitSeries.attachAxis(axisY)

        axisY.setMax(max(yawSpeed) + 0.1*(max(yawSpeed)-min(yawSpeed)))
        axisY.setMin(0)

        self.yawChartView.setChart(self.yawPlotChart)
        self.leMaxSpeed.setText(str(max(yawSpeed)))
        self.leSpeedAtHit.setText(str(yawSpeed[self.peakList[self.swingIndex]]))

    def displaySwingAnlgeData(self, timeList, swingAngle):
        self.swingAngleChart = QChart()
        self.swingAngleChart.setTitle('Swing Angle')
        self.swingAngleChart.setTitleBrush(whiteBrush)
        self.swingAngleChart.setBackgroundBrush(blackBrush)
        self.swingAngleChartView.setChart(self.swingAngleChart)

        self.swingAngleChart.legend().hide()

        axisX = QValueAxis()
        axisX.setTitleText('Time(s)')
        axisX.setTitleBrush(whiteBrush)
        axisX.setLabelsBrush(whiteBrush)
        axisX.setGridLineVisible(False)
        axisX.setTickCount(11)
        self.swingAngleChart.addAxis(axisX, Qt.AlignBottom)

        axisY = QValueAxis()
        axisY.setTitleText('Angle(degrees)')
        axisY.setTitleBrush(whiteBrush)
        axisY.setLabelsBrush(whiteBrush)
        axisY.setGridLineVisible(False)
        axisY.setTickCount(9)
        self.swingAngleChart.addAxis(axisY, Qt.AlignLeft)

        swingAngleSeries = QSplineSeries()
        swingAngleSeries.setPen(QPen(QColor("Red"), 1))

        hitSeries = QLineSeries()
        hitSeries.setPen(QPen(QColor("White"), 1))

        hitSeries.append(timeList[self.peakList[self.swingIndex]], max(swingAngle) + 0.1*(max(swingAngle)-min(swingAngle)))
        hitSeries.append(timeList[self.peakList[self.swingIndex]], 0)

        length = min(len(timeList), len(swingAngle))

        for index in range(length):
            swingAngleSeries.append(timeList[index], swingAngle[index])

        self.swingAngleChart.addSeries(swingAngleSeries)
        self.swingAngleChart.addSeries(hitSeries)

        swingAngleSeries.attachAxis(axisX)
        swingAngleSeries.attachAxis(axisY)

        hitSeries.attachAxis(axisX)
        hitSeries.attachAxis(axisY)

        axisY.setMax(max(swingAngle) + 0.1*(max(swingAngle)-min(swingAngle)))
        axisY.setMin(0)

        self.swingAngleChartView.setChart(self.swingAngleChart)
        self.leAngleAtHit.setText(str(swingAngle[self.peakList[self.swingIndex]]))

    def rotationCalculated(self, rotations):
        print('Finished Rotation Calculations')
        self.rotations = rotations

        self.nextSwingButton.setEnabled(True)
        self.prevSwingButton.setEnabled(True)

        self.moveHitRightButton.setEnabled(True)
        self.moveHitLeftButton.setEnabled(True)

        self.tbSwingStats.setEnabled(True)
        self.tbAnimation.setEnabled(True)

        self.yawSpeeds = [yawSpeedFromMatrix(self.rotations[i], self.timeList[i], float(self.leShoulderWidth.text())) for i in range(self.maxIndex)]
        self.displayYawData(self.timeList[self.swingIndex][1:], self.yawSpeeds[self.swingIndex])

        self.swingAngles = [swingAngleFromMatrix(self.rotations[i], np.array([[1],[0],[0]])) for i in range(self.maxIndex)]
        self.displaySwingAnlgeData(self.timeList[self.swingIndex], self.swingAngles[self.swingIndex])

    def renderCalculated(self, images):
        images = [Image.fromarray((image.numpy() * 255).astype(np.uint8)) for image in images]

        gifFilename = f'{self.directory}\\swing{self.swingIndex+1}.gif'

        images[0].save(gifFilename, save_all=True, append_images=images[1:], duration=100)

        self.aniObjects[self.swingIndex].openGif(gifFilename)

        print('done')

        self.displayAnimation()

    def displayAnimation(self):
        self.rendered = len(self.aniObjects[self.swingIndex].pixmaps) != 0
        if (self.rendered):
            self.aniObjects[self.swingIndex].displayFirstFrame()

            self.pbFirstFrame.setEnabled(True)
            self.pbNextFrame.setEnabled(True)
            self.pbPlayFrames.setEnabled(True)
            self.pbPrevFrame.setEnabled(True)
            self.pbLastFrame.setEnabled(True)
        else:
            self.pbPlayFrames.setText('Render')

            self.pbFirstFrame.setEnabled(False)
            self.pbNextFrame.setEnabled(False)
            self.pbPrevFrame.setEnabled(False)
            self.pbLastFrame.setEnabled(False)

    def displayNextFrame(self):
        self.aniObjects[self.swingIndex].displayNextFrame()

    def displayPrevFrame(self):
        self.aniObjects[self.swingIndex].displayPrevFrame()

    def displayFirstFrame(self):
        self.aniObjects[self.swingIndex].displayFirstFrame()

    def displayLastFrame(self):
        self.aniObjects[self.swingIndex].displayLastFrame()

    def playFrames(self):
        if (self.rendered):
            self.aniObjects[self.swingIndex].togglePlay()
        else:
            self.renderSwing()

    def hitRight(self):
        self.peakList[self.swingIndex] += 1

        self.accelView.plot(self.timeList[self.swingIndex], self.accelList[self.swingIndex], self.peakList[self.swingIndex])
        self.gyroView.plot(self.timeList[self.swingIndex], self.gyroList[self.swingIndex], self.peakList[self.swingIndex])

        self.displayYawData(self.timeList[self.swingIndex][1:], self.yawSpeeds[self.swingIndex])
        self.displaySwingAnlgeData(self.timeList[self.swingIndex], self.swingAngles[self.swingIndex])

    def hitLeft(self):
        self.peakList[self.swingIndex] -= 1

        self.accelView.plot(self.timeList[self.swingIndex], self.accelList[self.swingIndex], self.peakList[self.swingIndex])
        self.gyroView.plot(self.timeList[self.swingIndex], self.gyroList[self.swingIndex], self.peakList[self.swingIndex])

        self.displayYawData(self.timeList[self.swingIndex][1:], self.yawSpeeds[self.swingIndex])
        self.displaySwingAnlgeData(self.timeList[self.swingIndex], self.swingAngles[self.swingIndex])


if __name__ == "__main__":
    app = QApplication(sys.argv)

    window = MainWindow()
    window.show()
    app.exec_()
