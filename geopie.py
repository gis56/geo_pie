# -*- coding: utf-8 -*-
"""
/***************************************************************************
 SaveAttributes
                                 A QGIS plugin
 Проба пера
 Generated by Plugin Builder: http://g-sherman.github.io/Qgis-Plugin-Builder/
                              -------------------
        begin                : 2022-03-26
        git sha              : $Format:%H$
        copyright            : (C) 2022 by Jh
        email                : jh56@bk.ru
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""
from qgis.PyQt.QtCore import QSettings, QTranslator, QCoreApplication
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction, QFileDialog

# Initialize Qt resources from file resources.py
from .resources import *
# Import the code for the dialog
from .outcrop_profile import OutcropProfile
from .wells_matrix import *
from .csv_shape import *
from .zso_zone import *
from .curve_wells import *
from .cadastr_js import *
import os.path
import webbrowser

from qgis.core import QgsProject, Qgis

from .profile_outcrop import *

class GeoPie:
    """QGIS Plugin Implementation."""
    def __init__(self, iface):
        """Constructor.
        :param iface: экземпляр интерфейса, который будет передан этому классу.
            который предоставляет хук, с помощью которого вы можете манипулировать QGIS
            приложение во время выполнения.
        :type iface: QgsInterface
        """
        # Сохранить ссылку на интерфейс QGIS
        self.iface = iface
        # initialize plugin directory
        self.plugin_dir = os.path.dirname(__file__)
        # initialize locale
        locale = QSettings().value('locale/userLocale')[0:2]
        locale_path = os.path.join(
            self.plugin_dir,
            'i18n',
            'SaveAttributes_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)
            QCoreApplication.installTranslator(self.translator)

        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'Мои скрипты')

        # Check if plugin was started the first time in current QGIS session
        # Must be set in initGui() to survive plugin reloads
        self.first_start = None

    # noinspection PyMethodMayBeStatic
    def tr(self, message):
        """Get the translation for a string using Qt translation API.

        We implement this ourselves since we do not inherit QObject.

        :param message: String for translation.
        :type message: str, QString

        :returns: Translated version of message.
        :rtype: QString
        """
        # noinspection PyTypeChecker,PyArgumentList,PyCallByClass
        return QCoreApplication.translate('My scripts', message)


    def add_action(
        self,
        icon_path,
        text,
        callback,
        enabled_flag=True,
        add_to_menu=True,
        add_to_toolbar=True,
        status_tip=None,
        whats_this=None,
        parent=None):
        """Add a toolbar icon to the toolbar.

        :param icon_path: Path to the icon for this action. Can be a resource
            path (e.g. ':/plugins/foo/bar.png') or a normal file system path.
        :type icon_path: str

        :param text: Text that should be shown in menu items for this action.
        :type text: str

        :param callback: Function to be called when the action is triggered.
        :type callback: function

        :param enabled_flag: A flag indicating if the action should be enabled
            by default. Defaults to True.
        :type enabled_flag: bool

        :param add_to_menu: Flag indicating whether the action should also
            be added to the menu. Defaults to True.
        :type add_to_menu: bool

        :param add_to_toolbar: Flag indicating whether the action should also
            be added to the toolbar. Defaults to True.
        :type add_to_toolbar: bool

        :param status_tip: Optional text to show in a popup when mouse pointer
            hovers over the action.
        :type status_tip: str

        :param parent: Parent widget for the new action. Defaults None.
        :type parent: QWidget

        :param whats_this: Optional text to show in the status bar when the
            mouse pointer hovers over the action.

        :returns: The action that was created. Note that the action is also
            added to self.actions list.
        :rtype: QAction
        """

        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)

        if status_tip is not None:
            action.setStatusTip(status_tip)

        if whats_this is not None:
            action.setWhatsThis(whats_this)

        #if add_to_toolbar:
            # Adds plugin icon to Plugins toolbar
            #self.iface.addToolBarIcon(action)

        if add_to_menu:
            self.iface.addPluginToVectorMenu(
                self.menu,
                action)

        self.actions.append(action)

        return action

    def initGui(self):
        """Создайте элементы меню и значки панели инструментов внутри QGIS GUI."""
        """
        icon_path = self.plugin_dir + '/icons/wells.png'
        self.add_action(
            icon_path,
            text=self.tr(u'Конструкция скважин'),
            callback=self.run,
            parent=self.iface.mainWindow())

        icon_path = self.plugin_dir + '/icons/icon.png'
        self.add_action(
            icon_path,
            text=self.tr(u'Профиль разреза'),
            callback=self.profile,
            parent=self.iface.mainWindow())
        # will be set False in run()
        """

        icon_path = self.plugin_dir + '/icons/icon.png'
        self.add_action(
            icon_path,
            text=self.tr(u'Конструктор разреза'),
            callback=self.curvwells,
            parent=self.iface.mainWindow())

        icon_path = self.plugin_dir + '/icons/matrx.png'
        self.add_action(
            icon_path,
            text=self.tr(u'Матрица расстояний'),
            callback=self.matrix,
            parent=self.iface.mainWindow())

        self.first_start = True

        icon_path = self.plugin_dir + '/icons/csv_shape.png'
        self.add_action(
            icon_path,
            text=self.tr(u'Точки из .csv'),
            callback=self.pointcsv,
            parent=self.iface.mainWindow())

        icon_path = self.plugin_dir + '/icons/zso48.svg'
        self.add_action(
            icon_path,
            text=self.tr(u'Зоны СО'),
            callback=self.zsozone,
            parent=self.iface.mainWindow())

        icon_path = self.plugin_dir + '/icons/cadastr48.svg'
        self.add_action(
            icon_path,
            text=self.tr(u'Кадастровые объекты'),
            callback=self.cadastr_zone,
            parent=self.iface.mainWindow())

        icon_path = self.plugin_dir + '/icons/rtd_help48.svg'
        self.add_action(
            icon_path,
            text=self.tr(u'Справка'),
            callback=self.helpbook,
            parent=self.iface.mainWindow())

    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginVectorMenu(
                self.tr(u'&Мои скрипты'),
                action)
            self.iface.removeToolBarIcon(action)

    """
        Постороение профиля разреза

    def profile(self):
        # Создать диалог с элементами (после перевода) и сохранить ссылку
        # Создавайте GUI только ОДИН РАЗ в обратном вызове, чтобы он
        # загружался только при запуске плагина
        if self.first_start == True:
            self.first_start = False

        out_profile = OutcropProfile()
        out_profile.run()
        del out_profile
    """

    """
        Расчет расстояний между точечными объектами
        и запись результатов в таблицу в виде
        веб- или .csv файла
    """
    def matrix(self):
        lvl, txt, ttl = dist_well_table()
        self.iface.messageBar().pushMessage(ttl, txt, level=lvl, duration=5)

    def pointcsv(self):
        lvl, txt, ttl = csvtoshp()
        self.iface.messageBar().pushMessage(ttl, txt, level=lvl, duration=5)

    """ Отрисовка зоны ЗСО
        эллипсы, квадраты, радиусы
    """
    def zsozone(self):
        lvl, txt, ttl = zsozone()
        self.iface.messageBar().pushMessage(ttl, txt, level=lvl, duration=5)

    """ Проекция профиля изогнутой скважины на линию разреза
    """
    def curvwells (self):
        cut_curvwell(self.iface)
    """
        Конструкция скважин
    def run(self):
        pass
    """
    """ Скачивание кадастровых зон в формате GeoJson
    """
    def cadastr_zone(self):
        cadastrshp(self.iface)

    def helpbook (self):
        webbrowser.open_new_tab('https://geo-pie.readthedocs.io/')
