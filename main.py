import sys
import pandas as pd

from PyQt5 import uic
from PyQt5.QtWidgets import QApplication, QMainWindow, QHBoxLayout, QPushButton, QFileDialog
from PyQt5.QtChart import QChartView

from TripplePlot import TripplePlot

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

        self.clearButton = QPushButton('Clear')
        self.buttonLayout.addWidget(self.clearButton)
        self.clearButton.clicked.connect(self.clearPlots)

    def diplayPlots(self):
        nameFilters = {"comma seperated file (*.csv)"}

        fileSelector = QFileDialog()
        fileSelector.setNameFilters(nameFilters)

        if (fileSelector.exec()):
            print(fileSelector.selectedFiles())

            df = pd.read_csv(fileSelector.selectedFiles()[0], on_bad_lines='warn', skip_blank_lines=True, encoding='utf-8', encoding_errors='ignore', names=["timestamp", "accelX", "accelY", "accelZ", "baselineX", "baselineY", "baselineZ", "gyroX", "gyroY", "gyroZ", "impactLevel"])
            df = df.dropna()

            self.accelView.plot(df.timestamp, df.accelX, df.accelY, df.accelZ)
            self.gyroView.plot(df.timestamp, df.gyroX, df.gyroY, df.gyroZ)

    def clearPlots(self):
        self.accelView.clear()
        self.gyroView.clear()

if __name__ == "__main__":
    app = QApplication(sys.argv)

    window = MainWindow()
    window.show()
    app.exec_()
