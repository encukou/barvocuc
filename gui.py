# Encoding: UTF-8

from PySide import QtCore, QtGui
import yaml

from settings import Settings
import pocitej

class Gui():
    _block = False
    currentLine = 0

    def __init__(self, argv):
        self.app = QtGui.QApplication(argv)

        self.threads = set()

        self.win = win = QtGui.QDialog()
        win.setWindowTitle(u"Papoušci")

        layout = QtGui.QVBoxLayout(win)

        self.names = u"Červená Oranžová Žlutá Zelená Modrá Fialová Růžová".split()
        self.spc_names = u"Bílá Černá Šedá".split()

        self.settings = Settings()

        self.spinners = [None] * len(self.settings.colors)

        self.color_set_params = []

        for i, (name, name_next, prim_color, trans_color) in enumerate(zip(self.names, self.names[1:] + [self.names[0]], self.settings.colors[::2], self.settings.colors[1::2])):
            def scope(i, name, prim_color, trans_color):
                btnColor = QtGui.QPushButton()
                label = QtGui.QLabel(name + ":")
                label.setMinimumWidth(100)
                label.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignVCenter)
                spin_min = QtGui.QSpinBox()
                spin_min.setMaximum(360)
                spin_max = QtGui.QSpinBox()
                spin_max.setMaximum(360)
                label2 = QtGui.QLabel(name + "+" + name_next + ":")
                label2.setMinimumWidth(150)
                label2.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignVCenter)
                btnColor2 = QtGui.QPushButton()

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

                spin_max.connect(QtCore.SIGNAL('valueChanged(int)'), lambda v: set_max(v))
                spin_min.connect(QtCore.SIGNAL('valueChanged(int)'), lambda v: set_min(v))

                layoutR = QtGui.QHBoxLayout()
                layoutR.addWidget(label)
                layoutR.addWidget(btnColor)
                layoutR.addWidget(spin_min)
                layoutR.addWidget(QtGui.QLabel(u"-"))
                layoutR.addWidget(spin_max)
                layoutR.addWidget(QtGui.QLabel(u"°"))
                layoutR.addWidget(label2)
                layoutR.addWidget(btnColor2)
                layoutR.addStretch()
                layout.addLayout(layoutR)

                btnColor.connect(QtCore.SIGNAL('clicked()'), lambda: self.getSetColor(btnColor, self.settings.colors, i * 2))
                btnColor2.connect(QtCore.SIGNAL('clicked()'), lambda: self.getSetColor(btnColor2, self.settings.colors, i * 2 + 1))
                self.color_set_params.append((btnColor, 'colors', i * 2))
                self.color_set_params.append((btnColor2, 'colors', i * 2 + 1))

            scope(i, name, prim_color, trans_color)

        self.spc_spinners = [None] * len(self.spc_names)
        for i, (name, color) in enumerate(zip(self.spc_names, self.settings.spc_colors)):
            def scope(i, name, prim_color, trans_color):
                btnColor = QtGui.QPushButton()
                label = QtGui.QLabel(name + ":")
                label.setMinimumWidth(100)
                label.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignVCenter)
                spin = QtGui.QSpinBox()
                spin.setMaximum(100)
                self.spc_spinners[i] = spin

                def set(val):
                    self.settings.spc_thresholds[i] = val
                    self.update_picture()

                spin.connect(QtCore.SIGNAL('valueChanged(int)'), lambda v: set(v))

                layoutR = QtGui.QHBoxLayout()
                layoutR.addWidget(label)
                layoutR.addWidget(btnColor)
                layoutR.addWidget(spin)
                layoutR.addWidget(QtGui.QLabel("%"))
                layoutR.addStretch()
                layout.addLayout(layoutR)

                btnColor.connect(QtCore.SIGNAL('clicked()'), lambda: self.getSetColor(btnColor, self.settings.spc_colors, i))
                self.color_set_params.append((btnColor, 'spc_colors', i))

            scope(i, name, prim_color, trans_color)

        bOpen = QtGui.QPushButton(u"Otevřít obrázek")
        bOpen.connect(QtCore.SIGNAL('clicked()'), self.do_open)

        bOpenSettings = QtGui.QPushButton(u"Načíst nastavení")
        bOpenSettings.connect(QtCore.SIGNAL('clicked()'), self.openSettings)

        bSaveSettings = QtGui.QPushButton(u"Uložit nastavení")
        bSaveSettings.connect(QtCore.SIGNAL('clicked()'), self.saveSettings)

        bProcess = QtGui.QPushButton(u"Zpracovat adresář")
        bProcess.connect(QtCore.SIGNAL('clicked()'), self.doDir)

        self.progress = QtGui.QProgressBar()

        layoutR = QtGui.QHBoxLayout()
        layoutR.addWidget(bOpen)
        layoutR.addWidget(bOpenSettings)
        layoutR.addWidget(bSaveSettings)
        layoutR.addWidget(bProcess)
        layoutR.addWidget(self.progress)
        layoutR.addStretch()
        layout.addLayout(layoutR)

        self.sourceLabel = QtGui.QLabel()
        self.schemaLabel = QtGui.QLabel()

        layoutR = QtGui.QHBoxLayout()
        layoutR.addWidget(self.sourceLabel)
        layoutR.addWidget(self.schemaLabel)
        layout.addLayout(layoutR)

        self.workTimer = QtCore.QTimer()
        self.workTimer.connect(QtCore.SIGNAL('timeout()'), self.work)

        if argv[1:]:
            path = self.do_open(argv[1])
        else:
            path = self.do_open()

        if path:
            print path
        else:
            return

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
            path, dummy = QtGui.QFileDialog.getOpenFileName()
        if not path:
            return None
        self.source = QtGui.QImage(path).convertToFormat(QtGui.QImage.Format_ARGB32)
        self.sourceLabel.setPixmap(QtGui.QPixmap(self.source))
        self.schema = QtGui.QImage(self.source)
        self.update_picture()
        return path

    def run(self):
        self.win.show()
        sys.exit(self.app.exec_())

    def update_picture(self):
        self.currentLine = 0
        self.progress.setValue(0)
        self.workTimer.start(0)

    def work(self):
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
        path, dummy = QtGui.QFileDialog.getSaveFileName()
        if path:
            yaml.dump(self.settings, open(path, 'w'))

    def openSettings(self):
        path, dummy = QtGui.QFileDialog.getOpenFileName()
        if path:
            self.settings = yaml.load(open(path))
            self.reloadSettings()

    def doDir(self):
        path = QtGui.QFileDialog.getExistingDirectory()
        if path:
            display = QtGui.QTextEdit()
            display.setReadOnly(True)
            display.setWindowTitle(u"Výstup")
            display.show()
            text = [u'']
            class PseudoFile(object):
                def write(slf, string):
                    text[0] += string.decode('utf-8')
                    display.setPlainText(text[0])
                    QtGui.QApplication.instance().processEvents()
            pocitej.main(str(path), PseudoFile(), self.settings)

    def getSetColor(self, btn, lst, index):
        color = QtGui.QColorDialog.getColor(QtGui.QColor(*(x*255 for x in lst[index])))
        if color.isValid():
            self.setColor(btn, lst, index, (color.red()/255., color.green()/255., color.blue()/255.))

    def setColor(self, btn, lst, index, color):
        btn.setStyleSheet("QPushButton { background-color: #%02X%02X%02X}" % tuple(x*255 for x in color))
        lst[index] = color
        self.update_picture()


if __name__ == '__main__':
    import sys
    gui = Gui(sys.argv)
    gui.run()
