import os
import gc
import weakref
import math

from PyQt5 import QtCore, QtGui, QtWidgets, uic

from .analysis import ImageAnalyzer
from .settings import COLOR_NAMES, SPECIAL_NAMES, FIELD_NAMES, Settings


VIEWS = 'source', 'colors', 'sobel', 'opacity'


MAX_ZOOM = 32
MIN_ZOOM = 1/32

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
    def __init__(self, *args):
        super().__init__(*args)
        self.setViewportUpdateMode(QtWidgets.QGraphicsView.FullViewportUpdate)
        self.setDragMode(QtWidgets.QGraphicsView.ScrollHandDrag)
        self._bgbrush1 = QtGui.QBrush(QtGui.QColor(200, 200, 200))
        self._bgbrush2 = QtGui.QBrush(QtGui.QColor(100, 100, 100),
                                      QtCore.Qt.Dense4Pattern)

        self._in_sync = False
        self.horizontalScrollBar().valueChanged.connect(self._sync_scrollbars)
        self.verticalScrollBar().valueChanged.connect(self._sync_scrollbars)

    def wheelEvent(self, event):
        # Get the cursor's scene position -- this should not change
        old_pos = self.mapToScene(event.pos())

        [item] = self.scene().items()
        zoom = old_zoom = item.scale()

        zoom = math.exp(math.log(zoom) + event.angleDelta().y()/1000)
        if zoom > MAX_ZOOM:
            zoom = MAX_ZOOM
        if zoom < MIN_ZOOM:
            zoom = MIN_ZOOM
        for friend in self.friends:
            friend._zoom(zoom)

        scrollbar_h = self.horizontalScrollBar()
        scrollbar_v = self.verticalScrollBar()

        scrollbar_h.setValue(old_pos.x() / old_zoom * zoom - event.x())
        scrollbar_v.setValue(old_pos.y() / old_zoom * zoom - event.y())

        self.backgroundBrush().setTransform(QtGui.QTransform.fromTranslate(
            zoom,
            zoom))

        self._sync_scrollbars()

    def _sync_scrollbars(self,*a, **ka):
        if self._in_sync:
            return

        scrollbar_h = self.horizontalScrollBar()
        scrollbar_v = self.verticalScrollBar()

        if scrollbar_h.maximum():
            hpos = scrollbar_h.value() / scrollbar_h.maximum()
        else:
            hpos = 0
        if scrollbar_v.maximum():
            vpos = scrollbar_v.value() / scrollbar_v.maximum()
        else:
            vpos = 0
        for friend in self.friends:
            if friend == self:
                continue
            try:
                friend._in_sync = True
                hb = friend.horizontalScrollBar()
                vb = friend.verticalScrollBar()
                hb.setValue(hpos * hb.maximum())
                vb.setValue(vpos * vb.maximum())
            finally:
                friend._in_sync = False

    def _zoom(self, zoom):
        [item] = self.scene().items()
        item.setScale(zoom)
        self.setSceneRect(0, 0,
                          item.boundingRect().width() * zoom,
                          item.boundingRect().height() * zoom)

    def drawBackground(self, painter, rect):
        pt = self.mapFromScene(QtCore.QPoint(0, 0))
        painter.translate(-pt.x(), -pt.y())
        painter.scale(4, 4)
        painter.fillRect(0, 0, self.width(), self.height(), self._bgbrush1)
        painter.fillRect(0, 0, self.width(), self.height(), self._bgbrush2)


class BarvocucMainWindow(QtWidgets.QMainWindow):
    def __init__(self, ui_form):
        super().__init__()
        ui_form.setupUi(self)
        self._ui_form = ui_form

    def changeEvent(self, event):
        if event.type() == QtCore.QEvent.LanguageChange:
            self._ui_form.retranslateUi(self)
            names = {}
            for lang in self.locale.uiLanguages():
                if lang in FIELD_NAMES:
                    names = FIELD_NAMES[lang]
                    break
            for label, combo_label, color_ident, next_color_ident in zip(
                    self.color_labels,
                    self.combo_labels,
                    COLOR_NAMES,
                    COLOR_NAMES[1:]+COLOR_NAMES[:1]):
                color_name = names.get(color_ident, color_ident)
                label_text = '{}:'.format(color_name)
                label.setText(label_text)
                next_color_name = names.get(next_color_ident, next_color_ident)
                label_text = '{} + {}:'.format(color_name, next_color_name)
                combo_label.setText(label_text)
            for label, color_ident in zip(self.special_labels, SPECIAL_NAMES):
                color_name = names.get(color_ident, color_ident)
                label_text = '{}:'.format(color_name)
                label.setText(label_text)


class Gui(object):
    def __init__(self):
        self.app = QtWidgets.QApplication([])

        self.settings = Settings()

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

        self.populate_view_menu()
        self.populate_translation_menu()
        self.populate_settings_dock()

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

        self.analyzer = analyzer = ImageAnalyzer(filename,
                                                 settings=self.settings)

        for name in VIEWS:
            view = win.findChild(QtWidgets.QGraphicsView, 'gv_' + name)

            pixmap = qpixmap_from_float_array(analyzer.arrays['img_' + name])
            view.pixmap_item = self.scenes[name].addPixmap(pixmap)

    def populate_translation_menu(self):
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
        self.win.locale = locale
        self.retranslate()

        menu = self.win.findChild(QtWidgets.QMenu, 'menuLanguage')
        for item in menu.actions():
            item.setChecked(item.data().bcp47Name() == locale.bcp47Name())

        if save_setting:
            QtCore.QSettings().setValue('barvocuc/lang', locale.bcp47Name())

    def populate_view_menu(self):
        menu = self.win.findChild(QtWidgets.QMenu, 'menuView')
        for dock in self.win.findChildren(QtWidgets.QDockWidget):
            menu.addAction(dock.toggleViewAction())
        menu.addSeparator()
        for toolbar in self.win.findChildren(QtWidgets.QToolBar):
            menu.addAction(toolbar.toggleViewAction())

    def populate_settings_dock(self):
        layout = self.win.findChild(QtWidgets.QGridLayout, 'layoutSettings')
        header_rows = layout.rowCount()
        self.win.color_labels = []
        self.win.combo_labels = []
        self.win.special_labels = []

        def _add_label_and_color_picker(row, col, text, color, label_list):
            label = QtWidgets.QLabel(text)
            layout.addWidget(label, row+header_rows, col, QtCore.Qt.AlignRight)
            label_list.append(label)

            btn = QtWidgets.QPushButton()
            css_template = "QPushButton { background-color: #%02X%02X%02X}"
            btn.setStyleSheet(css_template % tuple(int(x*255) for x in color))
            layout.addWidget(btn, row+header_rows, col+1)

        colorname_iter = zip(COLOR_NAMES, COLOR_NAMES[1:] + COLOR_NAMES[:1],
                             self.settings.main_display_colors,
                             self.settings.transition_display_colors)
        for i, (color_name, next_color_name, color, t_color
                    ) in enumerate(colorname_iter):
            _add_label_and_color_picker(i, 0, color_name, color,
                                        self.win.color_labels)

            box = QtWidgets.QSpinBox()
            box.setSuffix('°')
            box.setMaximum(360)
            box.setValue(self.settings.color_thresholds[i*2-2])
            layout.addWidget(box, i+header_rows, 2)
            box.valueChanged.connect(lambda v, n=i*2-2:
                                         self.threshold_changed(v, n))

            box = QtWidgets.QSpinBox()
            box.setSuffix('°')
            box.setMaximum(360)
            l = len(self.settings.color_thresholds)
            box.setValue(self.settings.color_thresholds[(i*2+1) % l])
            layout.addWidget(box, i+header_rows, 3)
            box.valueChanged.connect(lambda v, n=i*2+1:
                                         self.threshold_changed(v, n))

            label_text = '{}+{}:'.format(color_name, next_color_name)
            _add_label_and_color_picker(i, 5, label_text, t_color,
                                        self.win.combo_labels)

        ziter = zip(SPECIAL_NAMES, self.settings.special_display_colors)
        for i, (color_name, color) in enumerate(ziter):
            _add_label_and_color_picker(i+len(COLOR_NAMES), 0,
                                        color_name, color,
                                        self.win.special_labels)

            box = QtWidgets.QSpinBox()
            box.setSuffix('%')
            box.setMinimum(0)
            box.setMaximum(100)
            col = 3 if i < 2 else 2
            layout.addWidget(box, i+len(COLOR_NAMES)+header_rows, col)

    def threshold_changed(self, value, n):
        self.settings.color_thresholds[n] = value
        self.load_preview(get_filename('media/default.png'))


def main():
    gui = Gui()
    return gui.run()
