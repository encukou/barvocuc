import os
import gc
import weakref
import math
import colorsys
import itertools
import math
import io
import csv

from PyQt5 import QtCore, QtGui, QtWidgets, uic

from .analysis import ImageAnalyzer
from .settings import COLOR_NAMES, SPECIAL_NAMES, FIELD_NAMES, Settings
from .batch import generate_paths, generate_csv


VIEWS = 'source', 'colors', 'sobel', 'opacity'


MAX_ZOOM = 32
MIN_ZOOM = 1/32

_weakdict = weakref.WeakKeyDictionary()

COLOR_SPINBOXES = False  # TODO: Turn on?

translate = QtCore.QCoreApplication.translate

PATH_ROLE = QtCore.Qt.UserRole
DONE_ROLE = QtCore.Qt.UserRole + 1
DATA_ROLE = QtCore.Qt.UserRole + 2

COLUMN_NAMES = ['filename'] + Settings().csv_output_fields + ['error']


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


def format_err(err):
    return '{}: {}'.format(type(err).__name__, err)


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
        if self.pixmap_item is None:
            return

        old_pos = self.mapToScene(event.pos())

        zoom = old_zoom = self.pixmap_item.scale()

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

    def _sync_scrollbars(self, *a, **ka):
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
        item = self.pixmap_item
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


class TranslatableWindow:
    def __init__(self, ui_form):
        super().__init__()
        ui_form.setupUi(self)
        self._ui_form = ui_form

    def changeEvent(self, event):
        if event.type() == QtCore.QEvent.LanguageChange:
            self._ui_form.retranslateUi(self)


class AboutDialog(TranslatableWindow, QtWidgets.QDialog):
    pass


class BarvocucMainWindow(TranslatableWindow, QtWidgets.QMainWindow):
    lang_changed = QtCore.pyqtSignal(str)
    enable_csv_export = QtCore.pyqtSignal(bool)

    def changeEvent(self, event):
        super().changeEvent(event)
        if event.type() == QtCore.QEvent.LanguageChange:
            names = {}
            for lang in self.locale.uiLanguages():
                if lang in FIELD_NAMES:
                    names = FIELD_NAMES[lang]
                    self.lang_changed.emit(lang)
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

        self.about_dialog = None
        self.settings = Settings()

        QtCore.QCoreApplication.setOrganizationName("encukou");
        QtCore.QCoreApplication.setOrganizationDomain("encukou.cz");
        QtCore.QCoreApplication.setApplicationName("Barvocuc");

        with open(get_filename('ui/mainwindow.ui'), encoding='utf-8') as f:
            ui_form_class, ui_base_class = uic.loadUiType(f)

        ui_form = ui_form_class()

        self.win = win = BarvocucMainWindow(ui_form)

        self.analysis_timer = QtCore.QTimer()
        self.analysis_timer.setSingleShot(False)
        self.analysis_timer.setInterval(100)
        self.analysis_timer.timeout.connect(self.do_analysis)
        self._analysis_position = 0

        self.scenes = {}
        friends = []
        for name in VIEWS:
            view = win.findChild(SynchronizedGraphicsView, 'gv_' + name)
            view.friends = friends
            friends.append(view)
            self.scenes[name] = self.init_graphics_scene(view)

        treewidget = self.win.findChild(QtWidgets.QTreeWidget, 'file_list')
        treewidget.itemSelectionChanged.connect(self.item_selection_changed)
        treewidget.header().resizeSection(0, 200)
        self.item_selection_changed()

        treewidget.setHeaderLabels(COLUMN_NAMES)
        treewidget.header().setSectionResizeMode(
            QtWidgets.QHeaderView.ResizeToContents)
        self.error_column_no = len(COLUMN_NAMES) - 1

        self.populate_view_menu()
        self.populate_translation_menu()
        self.populate_settings_dock()

        self.win.findChild(QtWidgets.QDockWidget, 'dock_sobel').hide()
        self.win.findChild(QtWidgets.QDockWidget, 'dock_opacity').hide()

        settings = QtCore.QSettings()
        self.sync_to_settings()

        win.lang_changed.connect(self._lang_changed)
        default_locale_name = QtCore.QLocale().bcp47Name()
        locale_name = settings.value('barvocuc/lang', default_locale_name)
        self.set_locale(QtCore.QLocale(locale_name), save_setting=False)

        for name, func in self._action_handlers.items():
            signal = self.win.findChild(QtWidgets.QAction, name).triggered
            signal.connect(lambda *, _func=func: _func(self))

    _action_handlers = {}
    def action_handler(name, *, _action_handlers=_action_handlers):
        def _decorator(func):
            _action_handlers[name] = func
            return func
        return _decorator

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
        try:
            self.analyzer = ImageAnalyzer(filename, settings=self.settings)
        except Exception as e:
            self.analyzer = None
            msg = format_err(e)
        else:
            msg = '{a.width}×{a.height}px - {name}'.format(a=self.analyzer,
                                                           name=filename)
        self.win.statusBar().showMessage(msg)
        self.update_preview(settings_reset=False)

    def update_preview(self, *, settings_reset=True):
        self.need_preview_update = True
        if settings_reset and self.analyzer:
            self.analyzer = self.analyzer.clone(settings=self.settings)
        QtCore.QTimer.singleShot(0, self._update_preview)

    def _update_preview(self):
        if not self.need_preview_update:
            return

        self.need_preview_update = False

        for name in VIEWS:
            view = self.win.findChild(QtWidgets.QGraphicsView, 'gv_' + name)

            analyzer = self.analyzer
            scene = self.scenes[name]
            item = getattr(view, 'pixmap_item', None)
            if item:
                zoom = item.scale()
                scene.clear()
                view.pixmap_item = None
            else:
                zoom = 1

            if analyzer:
                pixmap = qpixmap_from_float_array(analyzer.arrays['img_' + name])

                view.pixmap_item = scene.addPixmap(pixmap)
                view._zoom(zoom)

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

        def _add_label_and_color_picker(row, col, text, n_color, label_list):
            label = QtWidgets.QLabel(text)
            layout.addWidget(label, row+header_rows, col, QtCore.Qt.AlignRight)
            label_list.append(label)

            btn = QtWidgets.QPushButton()
            self.color_buttons[n_color] = btn
            layout.addWidget(btn, row+header_rows, col+1)
            btn.clicked.connect(lambda: self.pick_preview_color(n_color))

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
            _add_label_and_color_picker(i, 0, color_name, i,
                                        self.win.color_labels)

            _add_spinbox(i, 2, '°', (i*2-2) % L,
                         self.color_sbinboxes, self.threshold_changed)
            _add_spinbox(i, 3, '°', (i*2+1) % L,
                         self.color_sbinboxes, self.threshold_changed)

            label_text = '{}+{}:'.format(color_name, next_color_name)
            _add_label_and_color_picker(i, 5, label_text, i+len(COLOR_NAMES),
                                        self.win.combo_labels)

        ziter = zip(SPECIAL_NAMES, self.settings.special_display_colors)
        for i, (color_name, color) in enumerate(ziter):
            _add_label_and_color_picker(i+len(COLOR_NAMES), 0,
                                        color_name, i+len(COLOR_NAMES)*2,
                                        self.win.special_labels)

            _add_spinbox(i+len(COLOR_NAMES), 3 if i else 2, '%', color_name,
                         self.special_sbinboxes, self.special_changed)

        cbox = self.win.findChild(QtWidgets.QComboBox, 'cb_version')
        cbox.addItem('1')
        cbox.addItem('2')
        cbox.currentIndexChanged[int].connect(self.model_version_changed)

    def threshold_changed(self, value, n):
        self.settings.color_thresholds[n] = value
        self.update_threshold_minmax(n)
        self.update_preview()
        self.reset_analysis()

    def update_threshold_minmax(self, n):
        box = self.color_sbinboxes[n]
        value = box.value()

        if n + 1 < len(self.settings.color_thresholds):
            self.color_sbinboxes[n + 1].setMinimum(value)
        if n - 1 >= 0:
            self.color_sbinboxes[n - 1].setMaximum(value)

        if COLOR_SPINBOXES:
            color = colorsys.hls_to_rgb(value/360, 0.5, 1)
            colorhex = '#%02X%02X%02X' % tuple(int(x*255) for x in color)
            css_template = """
                QSpinBox { color: %(h)s; }
            """
            box.setStyleSheet(css_template % {'h': colorhex})

    def special_changed(self, value, name):
        self.settings.special_thresholds[name] = value / 100
        self.update_special_minmax(name)
        self.update_preview()
        self.reset_analysis()

    def update_special_minmax(self, name):
        value = self.special_sbinboxes[name].value()

        if name == 'white':
            self.special_sbinboxes['black'].setMaximum(value)
        if name == 'black':
            self.special_sbinboxes['white'].setMinimum(value)

    def model_version_changed(self, version_index):
        self.settings.model_version = version_index + 1
        self.update_preview()
        self.reset_analysis()

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

        allcolors = (self.settings.main_display_colors
                     + self.settings.transition_display_colors
                     + self.settings.special_display_colors)
        for btn, color in zip(self.color_buttons, allcolors):
            self._set_button_color(btn, color)

        cbox = self.win.findChild(QtWidgets.QComboBox, 'cb_version')
        cbox.setCurrentIndex(self.settings.model_version - 1)

        self.reset_analysis()

    def _lang_changed(self, lang):
        self.settings.lang = lang
        self.sync_to_settings()
        column_names = [
            FIELD_NAMES[self.settings.lang].get(n, n)
            for n in COLUMN_NAMES
        ]
        treewidget = self.win.findChild(QtWidgets.QTreeWidget, 'file_list')
        treewidget.setHeaderLabels(column_names)

        cbox = self.win.findChild(QtWidgets.QComboBox, 'cb_version')
        cbox.setItemText(0, translate('ModelVersion', '1 (Initial version)'))
        cbox.setItemText(1, translate('ModelVersion', '2 (Fixed 0.392% bug)'))

    def _set_button_color(self, btn, color):
        css_template = "QPushButton { background-color: #%02X%02X%02X}"
        btn.setStyleSheet(css_template % tuple(int(x*255) for x in color))

    def pick_preview_color(self, n):
        btn = self.color_buttons[n]

        N = len(COLOR_NAMES)
        if n < N:
            lst = self.settings.main_display_colors
        elif n < N * 2:
            lst = self.settings.transition_display_colors
            n -= N
        else:
            lst = self.settings.special_display_colors
            n -= N * 2

        qcolor = QtGui.QColor(*(x*255 for x in lst[n]))
        qcolor = QtWidgets.QColorDialog.getColor(qcolor)
        if qcolor.isValid():
            color = qcolor.redF(), qcolor.greenF(), qcolor.blueF()
            lst[n] = color
            self._set_button_color(btn, color)
            self.update_preview()

    @action_handler('actionFactoryResetSettings')
    def factory_reset_settings(self):
        self.settings = Settings()
        self.sync_to_settings()
        self.update_preview()

    def show_error_box(self, msg, e):
        QtWidgets.QMessageBox.critical(
            self.win, msg,
            '{msg}.\n\n{e}'.format(msg=msg, e=format_err(e)),
            )

    @action_handler('actionSaveSettings')
    def save_settings(self):
        path, dummy = QtWidgets.QFileDialog.getSaveFileName(
            caption=translate('MainWindow', 'Save Settings'))
        if not path:
            return
        try:
            with open(path, 'w', encoding='utf-8') as f:
                self.settings.save_to(f)
        except Exception as e:
            msg = translate('MainWindow', 'Could not save settings')
            self.show_error_box(msg, e)

    @action_handler('actionLoadSettings')
    def load_settings(self):
        path, dummy = QtWidgets.QFileDialog.getOpenFileName(
            caption=translate('MainWindow', 'Load Settings'))
        if not path:
            return None
        try:
            with open(path, encoding='utf-8') as f:
                self.settings = Settings.load_from(f)
        except Exception as e:
            msg = translate('MainWindow', 'Could not load settings')
            self.show_error_box(msg, e)
        self.sync_to_settings()
        self.update_preview()

    @action_handler('actionOpenFile')
    def open_file(self):
        paths, foo = QtWidgets.QFileDialog.getOpenFileNames(
                caption=translate('MainWindow', 'Add Image File'))
        if paths:
            self.add_files(paths)

    def add_files(self, paths):
        item = None
        widget = self.win.findChild(QtWidgets.QTreeWidget, 'file_list')
        for path in paths:
            item = QtWidgets.QTreeWidgetItem()
            item.setText(0, path)
            item.setData(0, PATH_ROLE, path)
            item.setData(0, DONE_ROLE, False)
            item.setData(0, QtCore.Qt.ToolTipRole, path)
            widget.addTopLevelItem(item)
        if item:
            widget.setCurrentItem(item)
            self.analysis_timer.start()
            self.win.enable_csv_export.emit(False)

    def item_selection_changed(self):
        widget = self.win.findChild(QtWidgets.QTreeWidget, 'file_list')
        path = None
        for item in widget.selectedItems():
            path = item.data(0, PATH_ROLE)
        if path is None:
            self.load_preview(get_filename('media/default.png'))
        else:
            self.load_preview(path)
        self.redisplay_filenames()

    def redisplay_filenames(self):
        widget = self.win.findChild(QtWidgets.QTreeWidget, 'file_list')
        paths = []
        for i in range(widget.topLevelItemCount()):
            item = widget.topLevelItem(i)
            path = item.data(0, PATH_ROLE)
            paths.append(os.path.dirname(path))
        if paths:
            prefix = os.path.commonpath(paths)
            for i in range(widget.topLevelItemCount()):
                item = widget.topLevelItem(i)
                path = item.data(0, PATH_ROLE)
                item.setText(0, os.path.relpath(path, prefix))

    @action_handler('actionOpenDirectory')
    def open_file(self):
        path = QtWidgets.QFileDialog.getExistingDirectory(
                caption=translate('MainWindow', 'Add Image Directory'))
        if path:
            self.add_files(generate_paths([path]))

    @action_handler('actionRemoveFile')
    def remove_file(self):
        widget = self.win.findChild(QtWidgets.QTreeWidget, 'file_list')
        for item in widget.selectedItems():
            idx = widget.indexOfTopLevelItem(item)
            widget.takeTopLevelItem(idx)
        self.redisplay_filenames()
        self.reset_analysis()

    @action_handler('actionClearInput')
    def remove_all(self):
        widget = self.win.findChild(QtWidgets.QTreeWidget, 'file_list')
        while widget.topLevelItemCount():
            widget.takeTopLevelItem(0)
        self.reset_analysis()

    def reset_analysis(self):
        self.win.enable_csv_export.emit(False)
        widget = self.win.findChild(QtWidgets.QTreeWidget, 'file_list')
        for i in range(widget.topLevelItemCount()):
            item = widget.topLevelItem(i)
            for i in range(1, widget.columnCount()):
                item.setText(i, '')
            item.setData(0, DONE_ROLE, False)
            item.setData(0, DATA_ROLE, None)
        for item in widget.selectedItems():
            idx = widget.indexOfTopLevelItem(item)
            self._analysis_position = idx
            break
        self.analysis_timer.start()

    def do_analysis(self):
        widget = self.win.findChild(QtWidgets.QTreeWidget, 'file_list')
        N = widget.topLevelItemCount()
        pos = self._analysis_position
        if N:
            pos %= N
        else:
            pos = 0
        self._analysis_position += 1
        for i in itertools.chain(range(pos, N), range(pos)):
            item = widget.topLevelItem(i)
            if not item.data(0, DONE_ROLE):
                path = item.data(0, PATH_ROLE)
                filename = item.text(0)
                results = {'filename': filename, 'error': ''}
                try:
                    analyzer = ImageAnalyzer(path, settings=self.settings)
                    fields = Settings().csv_output_fields
                    for i, name in enumerate(fields, start=1):
                        result = analyzer.results[name]
                        results[name] = result
                        item.setData(i, DATA_ROLE, result)
                        if isinstance(result, float):
                            result = round(result, 2)
                        item.setText(i, str(result))
                except Exception as e:
                    msg = format_err(e)
                    results['error'] = msg
                    item.setText(self.error_column_no, msg)
                item.setData(0, DONE_ROLE, True)
                item.setData(0, DATA_ROLE, results)
                return False
        else:
            self.analysis_timer.stop()
            if N:
                self.win.enable_csv_export.emit(True)
            return True

    def get_csv(self):
        widget = self.win.findChild(QtWidgets.QTreeWidget, 'file_list')
        buffer = io.StringIO()
        columns = ('filename', *self.settings.csv_output_fields, 'error')
        lang = self.settings.lang
        writer = csv.DictWriter(buffer, columns, extrasaction='ignore',
                                lineterminator='\n')
        writer.writerow(FIELD_NAMES[lang])
        for i in range(widget.topLevelItemCount()):
            writer.writerow(widget.topLevelItem(i).data(0, DATA_ROLE))

        return buffer.getvalue()

    @action_handler('actionCopyCSV')
    def copy_csv(self):
        try:
            data = self.get_csv()

            clipboard = self.app.clipboard()
            clipboard.setText(data)
        except Exception as e:
            self.show_error_box(
                translate('MainWindow', 'Could not copy CSV'), e)

    @action_handler('actionSaveCSV')
    def copy_csv(self):
        try:
            data = self.get_csv()

            path, foo = QtWidgets.QFileDialog.getSaveFileName(
                    caption=translate('MainWindow', 'Save CSV'),
                    filter=translate('MainWindow', 'CSV files (*.csv)'),
                    )
            if path:
                with open(path, 'w', encoding='utf-8') as f:
                    f.write(data)
        except Exception as e:
            self.show_error_box(
                translate('MainWindow', 'Could not save CSV'), e)

    @action_handler('actionSaveToDir')
    def save_to_dir(self):
        widget = self.win.findChild(QtWidgets.QTreeWidget, 'file_list')
        paths = []
        for i in range(widget.topLevelItemCount()):
            paths.append(widget.topLevelItem(i).data(0, PATH_ROLE))

        if not paths:
            return

        try:
            path = QtWidgets.QFileDialog.getExistingDirectory(
                    caption=translate('MainWindow', 'Save to directory'),
                    )
            if path:
                generate_csv(None, paths, settings=self.settings, outdir=path)
        except Exception as e:
            self.show_error_box(
                translate('MainWindow', 'Could not save CSV'), e)

    @action_handler('actionAbout')
    def about(self):
        return self.show_about(0)

    @action_handler('actionOpenDocs')
    def about(self):
        return self.show_about(1)

    @action_handler('actionOpenLicence')
    def about(self):
        return self.show_about(1)

    def show_about(self, pageno):
        if self.about_dialog:
            dialog = self.about_dialog
        else:
            with open(get_filename('ui/about.ui'), encoding='utf-8') as f:
                form, cls = uic.loadUiType(f)

            dialog = self.about_dialog = AboutDialog(form())

            with open(get_filename('COPYING.html'), encoding='utf-8') as f:
                license_html = f.read()
            widget = dialog.findChild(QtWidgets.QTextBrowser, 'textLicense')
            widget.setHtml(license_html)

            # Remove Documentation tab
            widget = dialog.findChild(QtWidgets.QTabWidget, 'tabWidget')
            widget.removeTab(1)

        widget = dialog.findChild(QtWidgets.QTabWidget, 'tabWidget')
        widget.setCurrentIndex(pageno)

        dialog.show()
        dialog.raise_()


def main():
    gui = Gui()
    return gui.run()
