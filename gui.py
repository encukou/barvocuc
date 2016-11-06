# Encoding: UTF-8

from __future__ import print_function
from PyQt5 import QtCore, QtGui, QtWidgets
import yaml

import numpy
from PIL import Image

from settings import Settings
import pocitej

class Gui(object):
    _block = False
    currentLine = 0

    def __init__(self, argv):
        self.app = QtWidgets.QApplication(argv)

        self.threads = set()

        self.win = win = QtWidgets.QDialog()
        win.setWindowTitle(u"Papoušci")

        layout = QtWidgets.QVBoxLayout(win)

        self.names = u"Červená Oranžová Žlutá Zelená Modrá Fialová Růžová".split()
        self.spc_names = u"Bílá Černá Šedá".split()

        self.settings = Settings()

        self.spinners = [None] * len(self.settings.colors)

        self.color_set_params = []

        for i, (name, name_next, prim_color, trans_color) in enumerate(zip(self.names, self.names[1:] + [self.names[0]], self.settings.colors[::2], self.settings.colors[1::2])):
            def scope(i, name, prim_color, trans_color):
                btnColor = QtWidgets.QPushButton()
                label = QtWidgets.QLabel(name + ":")
                label.setMinimumWidth(100)
                label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
                spin_min = QtWidgets.QSpinBox()
                spin_min.setMaximum(360)
                spin_max = QtWidgets.QSpinBox()
                spin_max.setMaximum(360)
                label2 = QtWidgets.QLabel(name + "+" + name_next + ":")
                label2.setMinimumWidth(150)
                label2.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
                btnColor2 = QtWidgets.QPushButton()

                self.spinners[self.start_index(i)] = spin_min
                self.spinners[self.end_index(i)] = spin_max

                def set_max(val):
                    self.settings.thresholds[self.end_index(i)] = val
                    if not self._block:
                        self.update_minmax(i + 1)
                        self.update_minmax(i - 1)
                    self.update_picture()

                def set_min(val):
                    self.settings.thresholds[self.start_index(i)] = val
                    if not self._block:
                        self.update_minmax(i + 1)
                        self.update_minmax(i - 1)
                    self.update_picture()

                spin_max.valueChanged.connect(lambda v: set_max(v))
                spin_min.valueChanged.connect(lambda v: set_min(v))

                layoutR = QtWidgets.QHBoxLayout()
                layoutR.addWidget(label)
                layoutR.addWidget(btnColor)
                layoutR.addWidget(spin_min)
                layoutR.addWidget(QtWidgets.QLabel(u"-"))
                layoutR.addWidget(spin_max)
                layoutR.addWidget(QtWidgets.QLabel(u"°"))
                layoutR.addWidget(label2)
                layoutR.addWidget(btnColor2)
                layoutR.addStretch()
                layout.addLayout(layoutR)

                btnColor.clicked.connect(lambda: self.getSetColor(btnColor, self.settings.colors, i * 2))
                btnColor2.clicked.connect(lambda: self.getSetColor(btnColor2, self.settings.colors, i * 2 + 1))
                self.color_set_params.append((btnColor, 'colors', i * 2))
                self.color_set_params.append((btnColor2, 'colors', i * 2 + 1))

            scope(i, name, prim_color, trans_color)

        self.spc_spinners = [None] * len(self.spc_names)
        for i, (name, color) in enumerate(zip(self.spc_names, self.settings.spc_colors)):
            def scope(i, name, prim_color, trans_color):
                btnColor = QtWidgets.QPushButton()
                label = QtWidgets.QLabel(name + ":")
                label.setMinimumWidth(100)
                label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
                spin = QtWidgets.QSpinBox()
                spin.setMaximum(100)
                self.spc_spinners[i] = spin

                def set(val):
                    self.settings.spc_thresholds[i] = val
                    self.update_picture()

                spin.valueChanged.connect(lambda v: set(v))

                layoutR = QtWidgets.QHBoxLayout()
                layoutR.addWidget(label)
                layoutR.addWidget(btnColor)
                layoutR.addWidget(spin)
                layoutR.addWidget(QtWidgets.QLabel("%"))
                layoutR.addStretch()
                layout.addLayout(layoutR)

                btnColor.clicked.connect(lambda: self.getSetColor(btnColor, self.settings.spc_colors, i))
                self.color_set_params.append((btnColor, 'spc_colors', i))

            scope(i, name, prim_color, trans_color)

        layoutR = QtWidgets.QHBoxLayout()
        label = QtWidgets.QLabel("Hrany:")
        label.setMinimumWidth(100)
        label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        layoutR.addWidget(label)
        self.contrast_show_checkbox = QtWidgets.QCheckBox(u'Ukázat')
        layoutR.addWidget(self.contrast_show_checkbox)
        self.contrast_show_checkbox.clicked.connect(self.update_picture)
        layoutR.addStretch()
        layout.addLayout(layoutR)

        bOpen = QtWidgets.QPushButton(u"Otevřít obrázek")
        bOpen.clicked.connect(self.do_open)

        bOpenSettings = QtWidgets.QPushButton(u"Načíst nastavení")
        bOpenSettings.clicked.connect(self.openSettings)

        bSaveSettings = QtWidgets.QPushButton(u"Uložit nastavení")
        bSaveSettings.clicked.connect(self.saveSettings)

        bProcess = QtWidgets.QPushButton(u"Zpracovat adresář")
        bProcess.clicked.connect(self.doDir)

        self.progress = QtWidgets.QProgressBar()

        layoutR = QtWidgets.QHBoxLayout()
        layoutR.addWidget(bOpen)
        layoutR.addWidget(bOpenSettings)
        layoutR.addWidget(bSaveSettings)
        layoutR.addWidget(bProcess)
        layoutR.addWidget(self.progress)
        layoutR.addStretch()
        layout.addLayout(layoutR)

        layoutR = QtWidgets.QHBoxLayout()
        layoutR.addWidget(QtWidgets.QLabel(u'Zdrojový adresář:'))
        self.srcdir = QtWidgets.QLineEdit()
        self.srcdir.setMinimumWidth(100)
        self.srcdir_select = QtWidgets.QPushButton('Vybrat...')
        layoutR.addWidget(self.srcdir)
        layoutR.addWidget(self.srcdir_select)
        def select_srcdir():
            s = QtWidgets.QFileDialog.getExistingDirectory(self.win, u"Zdrojový adresář")
            if s:
                self.srcdir.setText(s)
        self.srcdir_select.clicked.connect(select_srcdir)
        layoutR.addStretch()
        layout.addLayout(layoutR)

        layoutR = QtWidgets.QHBoxLayout()
        layoutR.addWidget(QtWidgets.QLabel(u'Cílový adresář:'))
        self.destdir = QtWidgets.QLineEdit()
        self.destdir.setMinimumWidth(100)
        self.destdir_select = QtWidgets.QPushButton('Vybrat...')
        layoutR.addWidget(self.destdir)
        layoutR.addWidget(self.destdir_select)
        def select_destdir():
            s = QtWidgets.QFileDialog.getExistingDirectory(self.win, u"Zdrojový adresář")
            if s:
                self.destdir.setText(s)
        self.destdir_select.clicked.connect(select_destdir)
        layoutR.addStretch()
        layout.addLayout(layoutR)

        self.sourceLabel = QtWidgets.QLabel()
        self.schemaLabel = QtWidgets.QLabel()

        layoutR = QtWidgets.QHBoxLayout()
        layoutR.addWidget(self.sourceLabel)
        layoutR.addWidget(self.schemaLabel)
        layout.addLayout(layoutR)

        self.workTimer = QtCore.QTimer()
        self.workTimer.timeout.connect(self.work)

        if argv[1:]:
            path = self.do_open(argv[1])
        else:
            path = None
            self.schema = None

        if path:
            print(path)

        self.reloadSettings()

    def start_index(self, i):
        return (i*2 - 2) % len(self.settings.thresholds)

    def end_index(self, i):
        return (i*2 + 1) % len(self.settings.thresholds)

    def reloadSettings(self):
        self._block = True
        for spinner in self.spinners:
            spinner.setMinimum(0)
            spinner.setMaximum(360)
        for spinner, value in zip(self.spinners, self.settings.thresholds):
            spinner.setValue(value)
        for i, color in enumerate(self.settings.colors):
            self.update_minmax(i)

        for spinner, value in zip(self.spc_spinners, self.settings.spc_thresholds):
            spinner.setValue(value)

        for btn, attr, index in self.color_set_params:
            lst = getattr(self.settings, attr)
            self.setColor(btn, lst, index, lst[index])

        self._block = False

        self.update_picture()

    def update_minmax(self, i):
        i %= len(self.names)
        spin_min = self.spinners[self.start_index(i)]
        spin_max = self.spinners[self.end_index(i)]

        spin_min.setMaximum(self.spinners[self.end_index(i - 1)].value())
        if i != 1:
            spin_min.setMinimum(self.spinners[self.start_index(i - 1)].value())
        spin_max.setMinimum(self.spinners[self.start_index(i + 1)].value())
        if i < len(self.names) - 1:
            spin_max.setMaximum(self.spinners[self.end_index(i + 1)].value())

    def do_open(self, path=None):
        if not path:
            path, dummy = QtWidgets.QFileDialog.getOpenFileName()
        if not path:
            return None
        self.source_path = path
        self.source = QtGui.QImage(path).convertToFormat(QtGui.QImage.Format_ARGB32)
        self.sourceLabel.setPixmap(QtGui.QPixmap(self.source))
        self.schema = QtGui.QImage(self.source)
        self.update_picture()
        return path

    def run(self):
        self.win.show()
        sys.exit(self.app.exec_())

    def update_picture(self):
        if self.contrast_show_checkbox.isChecked():
            self.workTimer.stop()

            image = Image.open(self.source_path)
            image = image.convert('RGBA')
            arr = numpy.array(image)
            pixels = numpy.vstack(arr) / 256.
            r, g, b, a, hue, sat, lum = pocitej.get_rgba_hsl(pixels)
            w, h = self.schema.width(), self.schema.height()
            alpha = a.reshape((h, w))
            sob = pocitej.do_sobel(lum, h, w).reshape((h, w))
            print(sob.shape)

            bgra = numpy.empty((h, w, 4), numpy.uint8, 'C')
            print(h, w, sob.shape)
            bgra[...,0] = 255 * (sob / 1).clip(0, 1)
            bgra[...,1] = 255 * (sob / 2).clip(0, 1)
            bgra[...,2] = 255 * (sob / 4).clip(0, 1)
            bgra[...,3] = 255 * alpha
            self.schema = QtGui.QImage(bgra.data, w, h, QtGui.QImage.Format_ARGB32)
            self.schema.ndarray = bgra

            self.schemaLabel.setPixmap(QtGui.QPixmap(self.schema))
            self.progress.setMaximum(1)
            self.progress.setValue(1)
        else:
            self.currentLine = 0
            self.progress.setValue(0)
            self.workTimer.start(0)

    def work(self):
        if not self.schema:
            return
        schema = self.schema
        if self.currentLine >= schema.height():
            return
        y = self.currentLine
        for x in range(schema.width()):
            pix = self.source.pixel(x, y)
            a = (pix & 0xFF000000) >> 24
            r = (pix & 0x00FF0000) >> 16
            g = (pix & 0x0000FF00) >> 8
            b = (pix & 0x000000FF)
            if a:
                a /= 255.
                r /= 255.
                g /= 255.
                b /= 255.
                c_max = max(r,g,b)
                c_min = min(r,g,b)
                c_diff = c_max - c_min
                if c_max == c_min:
                    hue = 0
                elif c_max == r:
                    hue = 60.0 * ((g - b) / c_diff) + 360
                elif c_max == g:
                    hue = 60.0 * ((b - r) / c_diff) + 120
                elif c_max == b:
                    hue = 60.0 * ((r - g) / c_diff) + 240.0
                hue %= 360  # Normalize angle
                lum = 0.5 * (c_max + c_min)
                if c_max == c_min:
                    sat = 0
                elif lum < 0.5:
                    sat = (c_max - c_min) / (2.0 * lum)
                else:
                    sat = (c_max - c_min) / (2.0 - (2.0 * lum))
                if lum > self.settings.spc_thresholds[0] / 100.:
                    r, g, b = self.settings.spc_colors[0]
                elif lum < self.settings.spc_thresholds[1] / 100.:
                    r, g, b = self.settings.spc_colors[1]
                elif sat < self.settings.spc_thresholds[2] / 100.:
                    r, g, b = self.settings.spc_colors[2]
                else:
                    for t, c in zip(self.settings.thresholds, self.settings.colors):
                        if hue < t:
                            r, g, b = c
                            break
                    else:
                        r, g, b = self.settings.colors[0]
                pix = int(a*255) << 24 | int(r*255) << 16 | int(g*255) << 8 | int(b*255)
            schema.setPixel(x, y, pix)
        self.currentLine = y + 1
        self.progress.setMaximum(schema.height())
        self.progress.setValue(y + 1)
        if y + 1 == schema.height():
            self.schemaLabel.setPixmap(QtGui.QPixmap(schema))
            self.workTimer.stop()
        elif y % 50 == 0:
            for x in range(schema.width()):
                pix = schema.setPixel(x, y + 1, 0xFF000000)
            self.schemaLabel.setPixmap(QtGui.QPixmap(schema))

    def saveSettings(self):
        path, dummy = QtWidgets.QFileDialog.getSaveFileName()
        if path:
            yaml.dump(self.settings, open(path, 'w'))

    def openSettings(self):
        path, dummy = QtWidgets.QFileDialog.getOpenFileName()
        if path:
            self.settings = yaml.load(open(path))
            self.settings.fix()
            self.reloadSettings()

    def doDir(self):
        path = self.srcdir.text()
        path2 = self.destdir.text()
        if path:
            display = QtWidgets.QTextEdit()
            display.setReadOnly(True)
            display.setWindowTitle(u"Výstup")
            display.show()
            text = [u'']
            class PseudoFile(object):
                def write(slf, string):
                    text[0] += string
                    display.setPlainText(text[0])
                    QtWidgets.QApplication.instance().processEvents()
            if path2:
                kwargs = dict(output_dir=str(path2))
            else:
                kwargs = {}
            pocitej.main(str(path), PseudoFile(), self.settings, **kwargs)
        else:
            QtWidgets.QMessageBox.critical(self.win, u'...', u'Zadej vstupní adresář.')

    def getSetColor(self, btn, lst, index):
        color = QtWidgets.QColorDialog.getColor(QtGui.QColor(*(x*255 for x in lst[index])))
        if color.isValid():
            self.setColor(btn, lst, index, (color.red()/255., color.green()/255., color.blue()/255.))

    def setColor(self, btn, lst, index, color):
        btn.setStyleSheet("QPushButton { background-color: #%02X%02X%02X}" % tuple(int(x*255) for x in color))
        lst[index] = color
        self.update_picture()


if __name__ == '__main__':
    import sys
    gui = Gui(sys.argv)
    gui.run()
