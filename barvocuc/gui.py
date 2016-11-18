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
        self.sync_to_settings()

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
        self.need_preview_update = True

        self.analyzer = ImageAnalyzer(filename, settings=self.settings)

        QtCore.QTimer.singleShot(0, self._update_preview)

    def _update_preview(self):
        if not self.need_preview_update:
            return

        self.need_preview_update = False

        for name in VIEWS:
            self.scenes[name].clear()
            view = self.win.findChild(QtWidgets.QGraphicsView, 'gv_' + name)

            analyzer = self.analyzer
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
        self.color_sbinboxes = [None for i in COLOR_NAMES*2]
        self.special_sbinboxes = {}
        self.color_buttons = [None for i in range(len(COLOR_NAMES)*2 + 3)]

        L = len(self.settings.color_thresholds)

        def _add_label_and_color_picker(row, col, text, color, label_list):
            label = QtWidgets.QLabel(text)
            layout.addWidget(label, row+header_rows, col, QtCore.Qt.AlignRight)
            label_list.append(label)

            btn = QtWidgets.QPushButton()
            css_template = "QPushButton { background-color: #%02X%02X%02X}"
            btn.setStyleSheet(css_template % tuple(int(x*255) for x in color))
            layout.addWidget(btn, row+header_rows, col+1)

        def _add_spinbox(row, col, suffix, n, box_list, func):
            box = QtWidgets.QSpinBox()
            box.setSuffix(suffix)
            layout.addWidget(box, row+header_rows, col)
            box.valueChanged.connect(lambda v: func(v, n))
            box_list[n] = box
            return box

        colorname_iter = zip(COLOR_NAMES, COLOR_NAMES[1:] + COLOR_NAMES[:1],
                             self.settings.main_display_colors,
                             self.settings.transition_display_colors)
        for i, (color_name, next_color_name, color, t_color
                    ) in enumerate(colorname_iter):
            _add_label_and_color_picker(i, 0, color_name, color,
                                        self.win.color_labels)

            _add_spinbox(i, 2, '°', (i*2-2) % L,
                         self.color_sbinboxes, self.threshold_changed)
            _add_spinbox(i, 3, '°', (i*2+1) % L,
                         self.color_sbinboxes, self.threshold_changed)

            label_text = '{}+{}:'.format(color_name, next_color_name)
            _add_label_and_color_picker(i, 5, label_text, t_color,
                                        self.win.combo_labels)

        ziter = zip(SPECIAL_NAMES, self.settings.special_display_colors)
        for i, (color_name, color) in enumerate(ziter):
            _add_label_and_color_picker(i+len(COLOR_NAMES), 0,
                                        color_name, color,
                                        self.win.special_labels)

            _add_spinbox(i+len(COLOR_NAMES), 3 if i < 2 else 2, '%', color_name,
                         self.special_sbinboxes, self.special_changed)

    def threshold_changed(self, value, n):
        self.settings.color_thresholds[n] = value
        self.update_threshold_minmax(n)
        self.load_preview(get_filename('media/default.png'))

    def update_threshold_minmax(self, n):
        value = self.color_sbinboxes[n].value()

        if n + 1 < len(self.settings.color_thresholds):
            self.color_sbinboxes[n + 1].setMinimum(value)
        if n - 1 >= 0:
            self.color_sbinboxes[n - 1].setMaximum(value)

    def special_changed(self, value, name):
        self.settings.special_thresholds[name] = value / 100
        self.update_special_minmax(name)
        self.load_preview(get_filename('media/default.png'))

    def update_special_minmax(self, name):
        value = self.special_sbinboxes[name].value()

        if name == 'white':
            self.special_sbinboxes['black'].setMaximum(value)
        if name == 'black':
            self.special_sbinboxes['white'].setMinimum(value)

    def sync_to_settings(self):
        for box in self.color_sbinboxes:
            box.setMinimum(0)
            box.setMaximum(360)

        ziter = zip(self.color_sbinboxes, self.settings.color_thresholds)
        for i, (box, value) in enumerate(ziter):
            prev_block = box.blockSignals(True)
            try:
                box.setValue(value)
            finally:
                box.blockSignals(prev_block)

        for n, box in enumerate(self.color_sbinboxes):
            self.update_threshold_minmax(n)

        for box in self.special_sbinboxes.values():
            box.setMinimum(0)
            box.setMaximum(100)

        for name in SPECIAL_NAMES:
            value = self.settings.special_thresholds.get(name)
            if value is not None:
                box = self.special_sbinboxes[name]
                prev_block = box.blockSignals(True)
                try:
                    box.setValue(int(value * 100))
                finally:
                    box.blockSignals(prev_block)

        for name in self.special_sbinboxes:
            self.update_special_minmax(name)


def main():
    gui = Gui()
    return gui.run()
