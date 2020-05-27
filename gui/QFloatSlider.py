from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import QSlider

class QFloatSlider(QSlider):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.scaler = 10 ** 3
        self.setMinimum(0.0)
        self.setMaximum(1.0)

    def value(self):
        return float(super().value()) / self.scaler

    def setValue(self, value):
        super().setValue(int(value * self.scaler))

    def setMinimum(self, value):
        super().setMinimum(int(value * self.scaler))

    def setMaximum(self, value):
        super().setMaximum(int(value * self.scaler))

    def setSingleStep(self, value):
        super().setSingleStep(int(value * self.scaler))

    def minimum(self):
        return float(super().minimum / self.scaler)

    def maximum(self):
        return float(super().maximum / self.scaler)
