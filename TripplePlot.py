from PyQt5.QtChart import QChartView, QChart, QLineSeries, QValueAxis
from PyQt5.QtGui import QColor, QBrush, QPen
from PyQt5.QtCore import Qt

class TripplePlot(QChartView):

    def __init__(self, title, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.title = title
        self.whiteBrush = QBrush(QColor("white"))

        self.trippleChart = QChart()
        self.trippleChart.setTitle(self.title)
        self.trippleChart.setTitleBrush(self.whiteBrush)
        self.trippleChart.setBackgroundBrush(QBrush(QColor("black")))
        self.setChart(self.trippleChart)

    def clear(self):
        self.trippleChart = QChart()
        self.trippleChart.setTitleBrush(self.whiteBrush)
        self.trippleChart.setTitle(self.title)

        self.trippleChart.legend().hide()
#        self.trippleChart.legend().setVisible(True)
#        self.trippleChart.legend().setAlignment(Qt.AlignBottom)

        self.trippleChart.setBackgroundBrush(QBrush(QColor("black")))
        self.setChart(self.trippleChart)

    def plot(self, timeList, xList, yList, zList):
        self.clear()

        xSeries = QLineSeries()
        xSeries.setPen(QPen(QColor("Red"), 1))

        ySeries = QLineSeries()
        ySeries.setPen(QPen(QColor("Green"), 1))

        zSeries = QLineSeries()
        zSeries.setPen(QPen(QColor("Blue"), 1))

        length = min(len(timeList), len(xList), len(yList), len(zList))
        maxY = max(max(xList), max(yList), max(zList))
        minY = min(min(xList), min(yList), min(zList))

        axisX = QValueAxis()
        axisX.setLabelsBrush(self.whiteBrush)
        axisX.setGridLineVisible(False)
        axisX.setTickCount(11)
        self.trippleChart.addAxis(axisX, Qt.AlignBottom)

        axisY = QValueAxis()
        axisY.setLabelsBrush(self.whiteBrush)
        axisY.setGridLineVisible(False)
        axisY.setTickCount(9)
        self.trippleChart.addAxis(axisY, Qt.AlignLeft)

        for index in range(0, length):
            xSeries.append(timeList[index], xList[index])
            ySeries.append(timeList[index], yList[index])
            zSeries.append(timeList[index], zList[index])

        self.trippleChart.addSeries(xSeries)
        self.trippleChart.addSeries(ySeries)
        self.trippleChart.addSeries(zSeries)

        xSeries.attachAxis(axisX)
        xSeries.attachAxis(axisY)

        ySeries.attachAxis(axisX)
        ySeries.attachAxis(axisY)

        zSeries.attachAxis(axisX)
        zSeries.attachAxis(axisY)

        axisY.setMax(maxY)
        axisY.setMin(minY)

        self.trippleChart.legend().update()
        self.setChart(self.trippleChart)
