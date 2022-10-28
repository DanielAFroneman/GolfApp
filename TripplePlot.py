from PyQt5.QtChart import QChartView, QChart, QLineSeries, QValueAxis, QScatterSeries, QSplineSeries
from PyQt5.QtGui import QColor, QBrush, QPen
from PyQt5.QtCore import Qt
import numpy as np
from scipy.signal import find_peaks

whiteBrush = QBrush(QColor("white"))
blackBrush = QBrush(QColor("black"))

class TripplePlot(QChartView):

    def __init__(self, title, xTitle, yTitle, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.title = title
        self.xTitle = xTitle
        self.yTitle = yTitle

        self.trippleChart = QChart()
        self.trippleChart.setTitle(self.title)
        self.trippleChart.setTitleBrush(whiteBrush)
        self.trippleChart.setBackgroundBrush(blackBrush)
        self.setChart(self.trippleChart)

    def clear(self):
        self.trippleChart = QChart()
        self.trippleChart.setTitleBrush(whiteBrush)
        self.trippleChart.setTitle(self.title)

        self.trippleChart.legend().hide()

        self.trippleChart.setBackgroundBrush(blackBrush)

    def plot(self, timeList, plotLists, peakIndex):
        self.clear()

        xSeries = QSplineSeries()
        xSeries.setPen(QPen(QColor("Red"), 1))

        ySeries = QSplineSeries()
        ySeries.setPen(QPen(QColor("Green"), 1))

        zSeries = QSplineSeries()
        zSeries.setPen(QPen(QColor("Blue"), 1))

        magSeries = QSplineSeries()
        magSeries.setPen(QPen(QColor("White"), 2))

        hitSeries = QLineSeries()
        hitSeries.setPen(QPen(QColor("White"), 2))

        magList = [np.sqrt(x*x+y*y+z*z) for x,y,z in zip(plotLists[0], plotLists[1], plotLists[2])]

        length = min(len(timeList), len(plotLists[0]), len(plotLists[1]), len(plotLists[2]), len(magList))

        maxY = max(max(plotLists[0]), max(plotLists[1]), max(plotLists[2]), max(magList))
        minY = min(min(plotLists[0]), min(plotLists[1]), min(plotLists[2]), min(magList))

        axisX = QValueAxis()
        axisX.setTitleText(self.xTitle)
        axisX.setTitleBrush(whiteBrush)
        axisX.setLabelsBrush(whiteBrush)
        axisX.setGridLineVisible(False)
        axisX.setTickCount(11)
        self.trippleChart.addAxis(axisX, Qt.AlignBottom)

        axisY = QValueAxis()
        axisY.setTitleText(self.yTitle)
        axisY.setTitleBrush(whiteBrush)
        axisY.setLabelsBrush(whiteBrush)
        axisY.setGridLineVisible(False)
        axisY.setTickCount(9)
        self.trippleChart.addAxis(axisY, Qt.AlignLeft)

        hitSeries.append(timeList[peakIndex], maxY+0.1*(maxY-minY))
        hitSeries.append(timeList[peakIndex], minY-0.1*(maxY-minY))

        for index in range(length):
            xSeries.append(timeList[index], plotLists[0][index])
            ySeries.append(timeList[index], plotLists[1][index])
            zSeries.append(timeList[index], plotLists[2][index])
            magSeries.append(timeList[index], magList[index])

        self.trippleChart.addSeries(magSeries)
        self.trippleChart.addSeries(xSeries)
        self.trippleChart.addSeries(ySeries)
        self.trippleChart.addSeries(zSeries)
        self.trippleChart.addSeries(hitSeries)

        xSeries.attachAxis(axisX)
        xSeries.attachAxis(axisY)

        ySeries.attachAxis(axisX)
        ySeries.attachAxis(axisY)

        zSeries.attachAxis(axisX)
        zSeries.attachAxis(axisY)

        magSeries.attachAxis(axisX)
        magSeries.attachAxis(axisY)

        hitSeries.attachAxis(axisX)
        hitSeries.attachAxis(axisY)

        axisY.setMax(maxY+0.1*(maxY-minY))
        axisY.setMin(minY-0.1*(maxY-minY))

        self.trippleChart.legend().update()
        self.setChart(self.trippleChart)
