import os
import gc
import weakref

from PyQt5 import QtCore, QtGui, QtWidgets, uic

from .analysis import ImageAnalyzer


VIEWS = 'source', 'colors', 'sobel', 'opacity'


_weakdict = weakref.WeakKeyDictionary()


def get_filename(name):
    return os.path.join(os.path.dirname(__file__), name)


def qpixmap_from_float_array(array):
    rgba = (array * 255).astype('uint8')

    rgba[..., [0, 2]] = rgba[..., [2, 0]]

    arr = rgba.flatten()

    qimage = QtGui.QImage(arr, rgba.shape[1], rgba.shape[0], QtGui.QImage.Format_ARGB32)
    pixmap = QtGui.QPixmap.fromImage(qimage)

    # Make sure the qimage is deallocated before the array
    del qimage
    gc.collect()

    return pixmap


class Gui(object):
    def __init__(self):
        self.app = QtWidgets.QApplication([])

        self.win = win = QtWidgets.QMainWindow()

        with open(get_filename('ui/mainwindow.ui')) as f:
            uic.loadUi(f, win)

        self.scenes = {}
        for name in VIEWS:
            view = win.findChild(QtWidgets.QGraphicsView, 'gv_' + name)
            self.scenes[name] = self.init_graphics_scene(view)

        self.load_preview(get_filename('media/default.png'))

    def run(self):
        self.win.show()
        return self.app.exec_()

    def init_graphics_scene(self, view):
        scene = QtWidgets.QGraphicsScene()

        # Keep the scene alive until Gui is GC'd
        _weakdict[scene] = self

        view.setScene(scene)

        return scene

    def load_preview(self, filename):
        win = self.win

        self.analyzer = analyzer = ImageAnalyzer(filename)

        for name in VIEWS:
            pixmap = qpixmap_from_float_array(analyzer.arrays['img_' + name])
            self.scenes[name].addPixmap(pixmap)


def main():
    gui = Gui()
    return gui.run()
