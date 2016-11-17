import os
import gc
import weakref

from PyQt5 import QtCore, QtGui, QtWidgets, uic

from .analysis import ImageAnalyzer


VIEWS = 'source', 'colors', 'sobel', 'opacity'


_weakdict = weakref.WeakKeyDictionary()


def get_filename(name):
    return os.path.join(os.path.dirname(__file__), name)

def listdir(path):
    return os.listdir(path)


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


class SynchronizedGraphicsView(QtWidgets.QGraphicsView):
    def wheelEvent(self, event):
        for self in self.friends:
            # Zoom Factor
            zoomInFactor = 1.1
            zoomOutFactor = 1 / zoomInFactor

            # Set Anchors
            self.setTransformationAnchor(QtWidgets.QGraphicsView.NoAnchor)
            self.setResizeAnchor(QtWidgets.QGraphicsView.NoAnchor)

            # Save the scene pos
            oldPos = self.mapToScene(event.pos())

            # Zoom
            if event.angleDelta().y() > 0:
                zoomFactor = zoomInFactor
            else:
                zoomFactor = zoomOutFactor
            if zoomFactor > 8:
                zoomFactor = 8
            self.scale(zoomFactor, zoomFactor)

            # Get the new position
            newPos = self.mapToScene(event.pos())

            # Move scene to old position
            delta = newPos - oldPos
            self.translate(delta.x(), delta.y())


class BarvocucMainWindow(QtWidgets.QMainWindow):
    def __init__(self, ui_form):
        super().__init__()
        ui_form.setupUi(self)
        self._ui_form = ui_form

    def changeEvent(self, event):
        if event.type() == QtCore.QEvent.LanguageChange:
            self._ui_form.retranslateUi(self)


class Gui(object):
    def __init__(self):
        self.app = QtWidgets.QApplication([])

        QtCore.QCoreApplication.setOrganizationName("encukou");
        QtCore.QCoreApplication.setOrganizationDomain("encukou.cz");
        QtCore.QCoreApplication.setApplicationName("Barvocuc");

        with open(get_filename('ui/mainwindow.ui')) as f:
            ui_form_class, ui_base_class = uic.loadUiType(f)

        ui_form = ui_form_class()

        self.win = win = BarvocucMainWindow(ui_form)

        self.scenes = {}
        friends = []
        for name in VIEWS:
            view = win.findChild(QtWidgets.QGraphicsView, 'gv_' + name)
            view.friends = friends
            friends.append(view)
            self.scenes[name] = self.init_graphics_scene(view)

        self.load_preview(get_filename('media/default.png'))

        self.fill_translation_menu()

        settings = QtCore.QSettings()

        default_locale_name = QtCore.QLocale().bcp47Name()
        locale_name = settings.value('barvocuc/lang', default_locale_name)
        self.set_locale(QtCore.QLocale(locale_name), save_setting=False)

    def retranslate(self):
        self.translator = translator = QtCore.QTranslator()
        translator.load(self.locale, 'barvocuc', '.',
                        get_filename('translations'), ".qm")
        ok = QtCore.QCoreApplication.installTranslator(translator)

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
            view = win.findChild(QtWidgets.QGraphicsView, 'gv_' + name)

            pixmap = qpixmap_from_float_array(analyzer.arrays['img_' + name])
            view.pixmap_item = self.scenes[name].addPixmap(pixmap)

    def fill_translation_menu(self):
        menu = self.win.findChild(QtWidgets.QMenu, 'menuLanguage')
        for filename in sorted(listdir(get_filename('translations/'))):
            if filename.endswith('.qm'):
                base, locale_name, ext = filename.split('.')
                self.translator = translator = QtCore.QTranslator()
                locale = QtCore.QLocale(locale_name)
                translator.load(locale, 'barvocuc', '.',
                                get_filename('translations'), ".qm")
                translate = translator.translate
                name = translate('gui', '<language name>')
                action = menu.addAction(name)
                action.triggered.connect(lambda *a, locale=locale:
                                         self.set_locale(locale))
                action.setData(locale)
                action.setCheckable(True)

    def set_locale(self, locale, *, save_setting=True):
        self.locale = locale
        self.retranslate()

        menu = self.win.findChild(QtWidgets.QMenu, 'menuLanguage')
        for item in menu.actions():
            item.setChecked(item.data().bcp47Name() == locale.bcp47Name())

        if save_setting:
            QtCore.QSettings().setValue('barvocuc/lang', locale.bcp47Name())


def main():
    gui = Gui()
    return gui.run()
