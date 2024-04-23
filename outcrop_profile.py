import os

from qgis.PyQt import uic
from qgis.PyQt import QtWidgets

from qgis.PyQt.QtWidgets import QAction, QFileDialog

from qgis.core import QgsProject, Qgis

from .profile_outcrop import *

# This loads your .ui file so that PyQt can populate your plugin with
# the elements from Qt Designer
FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'ui/outcrop_profile.ui'))


class OutcropProfile(QtWidgets.QDialog, FORM_CLASS):

    project = QgsProject.instance()
    plugin_dir = os.path.dirname(__file__)
    msgBox = QtWidgets.QMessageBox()

    def __init__(self, parent=None):
        """Constructor."""
        super(OutcropProfile, self).__init__(parent)
        self.setupUi(self)

        self.id_pnt_layer = [False, False]
        self.id_ln_layer = [False, False]
        self.id_plg_layer = [False, False]
        self.id_srtm_layer = [False, False]

        self.pushButton.clicked.connect(self.select_output_file)

        self.comboBox_izline.activated.connect(self.activ_combo_izline)
        self.comboBox_izline.currentIndexChanged.connect(
            self.activ_combo_izline)

        self.comboBox_lnRiver.activated.connect(self.activ_combo_lnRiver)
        self.comboBox_lnRiver.currentIndexChanged.connect(
            self.activ_combo_lnRiver)

        self.comboBox_age.activated.connect(self.activ_combo_age)
        self.comboBox_age.currentIndexChanged.connect(self.activ_combo_age)

        self.comboBox_plgRiver.activated.connect(self.activ_combo_plgRiver)
        self.comboBox_plgRiver.currentIndexChanged.connect(
            self.activ_combo_plgRiver)

        self.groupBox_river.clicked.connect(self.activ_checkbox_river)

    """
        Переделать под выбор каталога
    """
    def select_output_file(self):
        filename, _filter = QFileDialog.getSaveFileName(
            self,
            "Select   output file ","", '*.csv')
        self.lineEdit.setText(filename)

    """
        Слот подбора полей таблицы для изолиний
        4 - Integer64/32, 6 - Real, 10 - String, 14 - Date
    """
    def activ_combo_izline(self) :
        vectorLayer = self.id_ln_layer[self.comboBox_izline.currentIndex()]
        if vectorLayer:
            fields = vectorLayer.fields()
            fields_int = []

            # Выбор полей по типу
            for field in fields :
                if field.type() == 6 or field.type() == 4 :
                    fields_int.append(field.name())
            self.comboBox_attrIzline.clear()
            self.comboBox_attrIzline.addItems(fields_int)
            # Поиск поля current по умолчанию
            try :
                indx_item = fields_int.index("ELEV")
                self.comboBox_attrIzline.setCurrentIndex(indx_item)
            except :
                pass
        else: self.comboBox_attrIzline.clear()
    '''
        Слот подбора полей таблицы для линии Рек
    '''
    def activ_combo_lnRiver(self) :

        vectorLayer = self.id_ln_layer[self.comboBox_lnRiver.currentIndex()]
        if vectorLayer:
            fields = vectorLayer.fields()
            fields_int = []

            # Выбор полей по типу
            for field in fields:
                if field.type() == 10 :
                    fields_int.append(field.name())
            self.comboBox_attrLnriver.clear()
            self.comboBox_attrLnriver.addItems(fields_int)
            # Поиск поля current по умолчанию
            try :
                indx_item = fields_int.index("name")
                self.comboBox_attrLnriver.setCurrentIndex(indx_item)
            except:
                pass
        else: self.comboBox_attrLnriver.clear()

    '''
        Слот подбора полей таблицы для полигоны рек
    '''
    def activ_combo_plgRiver(self) :

        vectorLayer = self.id_plg_layer[self.comboBox_plgRiver.currentIndex()]
        if vectorLayer:
            fields = vectorLayer.fields()
            fields_int = []

            # Выбор полей по типу
            for field in fields :
                if field.type() == 10 :
                    fields_int.append(field.name())
            self.comboBox_attrPlgriver.clear()
            self.comboBox_attrPlgriver.addItems(fields_int)
            # Поиск поля current по умолчанию
            try :
                indx_item = fields_int.index("name")
                self.comboBox_attrPlgriver.setCurrentIndex(indx_item)
            except :
                pass
        else: self.comboBox_attrPlgriver.clear()

    '''
        Слот подбора полей таблицы для Возрастов
    '''
    def activ_combo_age(self) :

        vectorLayer = self.id_plg_layer[self.comboBox_age.currentIndex()]
        if vectorLayer:
            fields = vectorLayer.fields()
            fields_int = []

            # Выбор полей по типу
            for field in fields :
                if field.type() == 4 :
                    fields_int.append(field.name())
            self.comboBox_attrAge.clear()
            self.comboBox_attrAge.addItems(fields_int)
            # Поиск поля current по умолчанию
            try :
                indx_item = fields_int.index("l_code")
                self.comboBox_attrAge.setCurrentIndex(indx_item)
            except :
                pass
        else: self.comboBox_attrAge.clear()

    def activ_checkbox_river(self) :
        if self.groupBox_river.isChecked() :
            # Линии рек
            self.comboBox_lnRiver.addItem("- Не выбран - ")
            self.comboBox_lnRiver.insertSeparator(1)
            self.comboBox_lnRiver.addItems(
                [layer.name() for layer in self.id_ln_layer[2::]])
            # Полигоны рек
            self.comboBox_plgRiver.addItem("- Не выбран - ")
            self.comboBox_plgRiver.insertSeparator(1)
            self.comboBox_plgRiver.addItems(
                [layer.name() for layer in self.id_plg_layer[2::]])
        else :
            # Линии рек
            self.comboBox_lnRiver.clear()
            self.comboBox_attrLnriver.clear()
            # Полигоны рек
            self.comboBox_plgRiver.clear()
            self.comboBox_attrPlgriver.clear()

    # Перегрузка метода диалогового окна accept для проверки
    # заполненности всех полей формы
    def accept (self) :
        # Путь к файлу должен быть взят из lineEdit
        # На случай удаления пути в ручную
        #self.filename = self.lineEdit_save_html.text()
        # Проверка пути к файлу и выбранного поля
        # os.path.isfile(self.filename)
        if self.id_ln_layer[self.comboBox_outcrop.currentIndex()]:
            self.exec_profile()
            self.done(QtWidgets.QDialog.Accepted)
        else :
            self.msgBox.warning(
                self,
                "Профиль разреза",
                "Не указана линия разреза")

    def run (self) :

        # Получение списка векторных слоев проекта
        layers = self.project.mapLayers()
        layers_val = layers.values()
        # Очистка comboBox перед первым запуском
        # Линия разреза comboBox_outcrop
        self.comboBox_outcrop.clear()
        self.comboBox_outcrop.addItem("- Не выбран - ")
        self.comboBox_outcrop.insertSeparator(1)
        # SRTM comboBox_SRTM
        self.comboBox_SRTM.clear()
        self.comboBox_SRTM.addItem("- Не выбран - ")
        self.comboBox_SRTM.insertSeparator(1)
        # Скважины comboBox_wells
        self.comboBox_wells.clear()
        self.comboBox_wells.addItem("- Не выбран - ")
        self.comboBox_wells.insertSeparator(1)
        # Возроста comboBox_age
        self.comboBox_age.clear()
        self.comboBox_age.addItem("- Не выбран - ")
        self.comboBox_age.insertSeparator(1)

        # Изолинии comboBox_izline
        self.comboBox_izline.clear()
        self.comboBox_izline.addItem("- Не выбран - ")
        self.comboBox_izline.insertSeparator(1)

        # Изолинии атрибуты comboBox_attrIzline
        self.comboBox_attrIzline.clear()

        for layer in layers_val:
            if layer.type() == 0:
                if layer.geometryType() == 1 :
                    self.id_ln_layer.append(layer)
                    self.comboBox_outcrop.addItems([layer.name()])
                if layer.geometryType() == 0 :
                    self.id_pnt_layer.append(layer)
                    self.comboBox_wells.addItems([layer.name()])
                if layer.geometryType() == 2 :
                    self.id_plg_layer.append(layer)
                    self.comboBox_age.addItems([layer.name()])
            else:
                self.id_srtm_layer.append(layer)
                self.comboBox_SRTM.addItems([layer.name()])

        self.comboBox_izline.addItems(
            [layer.name() for layer in self.id_ln_layer[2::]])
        # Водоемы groupBox_river
        self.groupBox_river.setChecked(False)

        # show the dialog
        self.show()
        # Run the dialog event loop
        self.exec_()

    def exec_profile (self) :
        # Линия разреза
        outcrop_vectorLayer = \
            self.id_ln_layer[self.comboBox_outcrop.currentIndex()]
        # Масштаб вертикальный spinBox_vScale
        scale_prof = self.spinBox_vScale.value()
        # Масштаб карты spinBox_mapScale
        map_scale = self.spinBox_mapScale.value()
        # Растр рельефа SRTM
        srtm_rastrLayer = \
            self.id_srtm_layer[self.comboBox_SRTM.currentIndex()]
        filename = self.lineEdit.text()
        # Создание группы для слоев разреза
        root = self.project.layerTreeRoot()
        group_exlusiv = root.addGroup("Разрезы")
        group_exlusiv.setIsMutuallyExclusive (1)

        outcrop_features = outcrop_vectorLayer.getFeatures()
        for feature in outcrop_features:

            profile = incision_maker(feature, srtm_rastrLayer)
            # Имя профиля получать из класса
            profile_group = group_exlusiv.addGroup(
                "Профиль разреза - " + profile.nameOutcrop)

            # Профиль
            profileLayer = profile.get_layerProfile()
            self.project.addMapLayer(profileLayer, False)
            profile_group.addLayer(profileLayer)
            # Скважины и фильтры
            wells_vectorLayer = \
                self.id_pnt_layer[self.comboBox_wells.currentIndex()]
            if wells_vectorLayer:
                wellsLayer, filtersLayer = \
                    profile.get_wells_filters(wells_vectorLayer)
                filtersLayer.loadNamedStyle(
                    self.plugin_dir + '/legstyle/filter_line.qml')
                self.project.addMapLayer(filtersLayer, False)
                profile_group.addLayer(filtersLayer)
                wellsLayer.loadNamedStyle(
                    self.plugin_dir + '/legstyle/wells_line.qml')
                self.project.addMapLayer(wellsLayer, False)
                profile_group.addLayer(wellsLayer)
            # Возроста
            age_vectorLayer = \
                self.id_plg_layer[self.comboBox_age.currentIndex()]
            if age_vectorLayer:
                age_attr = self.comboBox_attrAge.currentText()
                ageLayer = profile.get_Age( age_vectorLayer, age_attr )
                ageLayer.loadNamedStyle(
                    self.plugin_dir + '/legstyle/litology_polygon.qml')
                self.project.addMapLayer(ageLayer, False)
                profile_group.addLayer(ageLayer)
            # Изолинии
            izln_vectorLayer = \
                self.id_ln_layer[self.comboBox_izline.currentIndex()]
            if izln_vectorLayer:
                izln_attr = self.comboBox_attrIzline.currentText()
                izlnLayer = profile.get_Izline( izln_vectorLayer, izln_attr)
                self.project.addMapLayer(izlnLayer, False)
                profile_group.addLayer(izlnLayer)
            # Реки
            if self.groupBox_river.isChecked() :
                # Пересечения с линиями рек. Точки на профиле.
                riverln_vectorLayer = \
                    self.id_ln_layer[self.comboBox_lnRiver.currentIndex()]
                riverln_attr = self.comboBox_attrLnriver.currentText()
                riverLayer = profile.get_River(
                    riverln_vectorLayer,
                    riverln_attr
                )
                if riverLayer :
                    riverLayer.loadNamedStyle(
                        self.plugin_dir + '/legstyle/river_line.qml')
                    self.project.addMapLayer(riverLayer, False)
                    profile_group.addLayer(riverLayer)
                # Пересечения с полигонами рек. Линии на профиле.
                sea_vectorLayer = \
                    self.id_plg_layer[self.comboBox_plgRiver.currentIndex()]
                sea_attr = self.comboBox_attrPlgriver.currentText()
                seaLayer = profile.get_Sea( sea_vectorLayer, sea_attr)
                if seaLayer :
                    self.project.addMapLayer(seaLayer, False)
                    profile_group.addLayer(seaLayer)

            # Отрисовка линейки
            ln_dialLayer, pnt_dialLayer = profile.get_dial(outcrop_vectorLayer)
            self.project.addMapLayer(ln_dialLayer, False)
            ln_dialLayer.loadNamedStyle(
                self.plugin_dir + '/legstyle/dial_line.qml')
            profile_group.addLayer(ln_dialLayer)
            self.project.addMapLayer(pnt_dialLayer, False)
            pnt_dialLayer.loadNamedStyle(
                self.plugin_dir + '/legstyle/dial_point.qml')
            profile_group.addLayer(pnt_dialLayer)
            #self.msgBox.warning(
            #    self,
            #    "Не все поля заполнены.",
            #    "Min = "+str(profile.altMin)+"\nMax = "+str(profile.altMax)
            #)
