# -*- coding: utf-8 -*-

import os

from qgis.PyQt import uic
from qgis.PyQt import QtWidgets
from qgis.PyQt.QtWidgets import QAction, QFileDialog, QMessageBox
from qgis.PyQt.QtCore import QVariant

from qgis.core import (QgsProject,
                       Qgis,
                       QgsVectorLayer,
                       QgsField,
                       QgsGeometry,
                       QgsFeature,
                       QgsFieldProxyModel,
                       QgsMapLayerProxyModel)

from .utilib import EncDec

#-----------------------------------------------------------------------------
# Форма скрипта создающего таблицу расстояний между скважинами (точками )
# и записывающего результат в *.csv или *.htm файл. Опционально можно создать
# граф (линии ) между точками.
#-----------------------------------------------------------------------------
FORM_CLASS_1, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'ui/wells_matrix.ui'))


class formWellsMatrix(QtWidgets.QDialog, FORM_CLASS_1):

    msgBox = QtWidgets.QMessageBox()

    def __init__(self, parent=None):
        super(formWellsMatrix, self).__init__(parent)
        self.setupUi(self)

        # Реакция на выбор слоя в mLayer
        self.mLayer.activated.connect(self.activ_mLayer)
        self.mLayer.currentIndexChanged.connect(self.activ_mLayer)
        self.mFile.setFilter('Таблица с разделителем CSV (*.csv);;\
                              Web - страница  (*.htm)')

        # Инициализация выбора кодировки
        self.encode_combo.addItem('- не выбрана -')
        self.encode_combo.insertSeparator(1)
        self.enc = EncDec()
        self.encode_combo.addItems(self.enc.item)
        self.encode_combo.currentIndexChanged.connect(self.set_encode)

        self.decode_combo.addItems(self.enc.item)
        self.decode_combo.currentIndexChanged.connect(self.set_decode)

        self.checkBox_matrix.setChecked(False)

    # Выбор кодировки
    def set_encode(self):
        self.enc.set_enc(self.encode_combo.currentIndex()-2)

    def set_decode (self):
        self.enc.set_dec(self.decode_combo.currentIndex())

    # Описание реакции mLayer на активацию и выбор
    def activ_mLayer(self):
        self.mLayer.setFilters(QgsMapLayerProxyModel.PointLayer)
        self.mField.setFilters(QgsFieldProxyModel.String|QgsFieldProxyModel.Int)
        self.mField.setLayer(self.mLayer.currentLayer())

        self.checkBox_Features.setChecked(False)
        # Получение выбранного слоя
        # Перед тем как активировать галочку с отмеченными объектами
        # необходимо убедиться в наличии слоя
        wells_vLayer = False
        wells_vLayer = self.mLayer.currentLayer()
        # Проверка на наличие выборки. Если есть выбранные объекты,
        # сделать доступным галочку
        if wells_vLayer and wells_vLayer.selectedFeatures() :
            self.checkBox_Features.setEnabled(True)
        else :
            self.checkBox_Features.setEnabled(False)

    # Перегрузка метода диалогового окна accept для
    # проверки заполненности всех полей формы
    def accept (self) :
        filename = self.mFile.lineEdit().text()
        dir_name = os.path.dirname(filename)
        if os.path.isdir(dir_name) and self.mField.currentField():
            self.done(QtWidgets.QDialog.Accepted)
        else :
            self.msgBox.warning(self,"Матрица скважин",
                                "Не все поля заполнены.")

    # Подготовка и запуск формы диалога
    def run (self):
        self.activ_mLayer()
        self.exec_()
        return self.result()

    def featwells (self):
        wells_vLayer = self.mLayer.currentLayer()
        if self.checkBox_Features.isChecked() :
            features = wells_vLayer.selectedFeatures()
        else :
            features=[feature for feature in wells_vLayer.getFeatures()]

        return features

    def namefield (self):
        return self.mField.currentField()

    def filename (self):
        return self.mFile.lineEdit().text()

    def is_graph (self):
        return self.checkBox_matrix.isChecked()

    def layer (self):
        return self.mLayer.currentLayer()
#-----------------------------------------------------------------------------
#      formWellMatrix()
#-----------------------------------------------------------------------------

#-----------------------------------------------------------------------------
# Форма скрипта создающего точки из csv таблицы
# formCSVshape
#-----------------------------------------------------------------------------
FORM_CLASS_2, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'ui/csv_to_shape.ui'))


class formCSVshape(QtWidgets.QDialog, FORM_CLASS_2):
    msgBox = QtWidgets.QMessageBox()
    split_char = ';'

    def __init__(self, parent=None):
        super(formCSVshape, self).__init__(parent)
        self.setupUi(self)

        self.csv_file_widget.setFilter('Таблица с разделителем CSV (*.csv);;\
                                       Любой файл (*)')
        self.csv_file_widget.fileChanged.connect(self.change_head)
        # Инициализация выбора кодировки
        self.encode_comboBox.addItem('- не выбрана -')
        self.encode_comboBox.insertSeparator(1)
        self.enc = EncDec()
        self.encode_comboBox.addItems(self.enc.item)
        self.encode_comboBox.setCurrentIndex(0)
        self.encode_comboBox.currentIndexChanged.connect(self.set_encode)

        self.field_check.clicked.connect(self.change_head)

    # Выбор кодировки
    def set_encode(self):
        self.enc.set_enc(self.encode_comboBox.currentIndex()-2)
        self.enc.set_dec(self.encode_comboBox.currentIndex()-2)
        if self.csv_file_widget.lineEdit().text():
            self.change_head()

    # Подготовка и запуск формы диалога
    def run(self):
        self.exec_()
        return self.result()

    # Перегрузка ok
    def accept(self):
        if not self.csv_file_widget.lineEdit().text():
            self.msgBox.warning(self,
                                "Ошибка выполнения",
                                "Файла не существует"
                                )
        elif (self.longitude_comboBox.currentIndex()<0 or
              self.latitude_comboBox.currentIndex()<0):
            self.msgBox.warning(self,
                                "Ошибка выполнения",
                                "Не все поля выбраны."
                                )
        else:
            if self.decode_check.isChecked():
                self.enc.set_dec(0)
            self.done(QtWidgets.QDialog.Accepted)

    # Выбор файла
    def csv_open(self):
        # Чтение файла
        csvpath = self.csv_file_widget.lineEdit().text()
        try:
            with open (csvpath, 'r',
                       encoding=self.enc.enc,
                       errors=self.enc.err) as csvfile:
                line = csvfile.readline().rstrip('\n')
            csvfile.close()
            return line
        except FileNotFoundError:
            self.msgBox.warning(self,
                                "Ошибка при открытии файла",
                                "Файл не найден."
                                )
            return False
        except UnicodeError:
            self.msgBox.warning(self,
                                "Ошибка при открытии файла",
                                "Смените кодировку"
                                )
            return False
        except Exception as e:
            self.msgBox.warning(self, "Ошибка при открытии файла", e)
            return False

    # Строка заголовка
    def change_head(self):
        self.latitude_comboBox.clear()
        self.longitude_comboBox.clear()
        head = self.csv_open()
        if head:
            head = head.split(self.split_char)
            if not self.field_check.isChecked():
                head = [f'Поле-{i+1} | {cl}' for i, cl in enumerate(head)]
            self.latitude_comboBox.addItems(head)
            self.longitude_comboBox.addItems(head)

    # Возвращает наличие заголовков полей и полное имя файла
    def csvpath (self):
        if self.field_check.isChecked():
            return True, self.csv_file_widget.lineEdit().text()
        else:
            return False, self.csv_file_widget.lineEdit().text()

    def xyFields (self):
        return  (self.longitude_comboBox.currentIndex(),
                self.latitude_comboBox.currentIndex())
#-----------------------------------------------------------------------------
#   formCSVshape
#-----------------------------------------------------------------------------

#-----------------------------------------------------------------------------
# Форма ввода данных для построения изогнутых скважин.
# В будущем должна разрастись до полноценного разреза
#-----------------------------------------------------------------------------
FORM_CLASS_3, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'ui/curve_wells.ui'))

class formCurveWells(QtWidgets.QDialog, FORM_CLASS_3):
    msgBox = QtWidgets.QMessageBox()

    def __init__(self, parent=None):
        super(formCurveWells, self).__init__(parent)
        self.setupUi(self)

        # Настройка mLayer (скважины)
        self.mLayer.setFilters(QgsMapLayerProxyModel.PointLayer)
        self.mLayer.activated.connect(self.activ_mLayer)
        self.mLayer.currentIndexChanged.connect(self.activ_mLayer)

        # Настройка mLayer_cut (разрез)
        self.mLayer_cut.setFilters(QgsMapLayerProxyModel.LineLayer)

        # Настройка mLayer_srtm
        self.mLayer_srtm.setFilters(QgsMapLayerProxyModel.RasterLayer)
        self.mLayer_srtm.setAdditionalItems([" -не выбрано- "])

        # Настройка поелй с изолиниями mLayer_izln
        self.mLayer_izln.setFilters(QgsMapLayerProxyModel.LineLayer)
        self.mLayer_izln.activated.connect(self.activ_mLayer_izln)
        self.mLayer_izln.currentIndexChanged.connect(self.activ_mLayer_izln)

        # Настройка списка слоев пересечения
        self.data_lnplg = []
        self.mLayer_lnplg.setFilters(
                                     QgsMapLayerProxyModel.PolygonLayer |
                                     QgsMapLayerProxyModel.LineLayer
                                    )
        self.mLayer_lnplg.currentIndexChanged.connect(self.activ_mLayer_lnplg)
        self.pButton_add.clicked.connect(self.add_click)
        self.pButton_remove.clicked.connect(self.remove_click)

        # Настройка типов полей атрибутов
        self.mField_well.setFilters(QgsFieldProxyModel.String)
        self.mField_file.setFilters(QgsFieldProxyModel.String)
        self.mField_filters.setFilters(QgsFieldProxyModel.String)
        self.mField_alt.setFilters(QgsFieldProxyModel.Double)
        self.mField_gtr.setFilters(QgsFieldProxyModel.String)
        self.mField_elev.setFilters(
                                    QgsFieldProxyModel.Int |
                                    QgsFieldProxyModel.Double |
                                    QgsFieldProxyModel.LongLong
                                   )
        self.mField_lnplg.setFilters(
                                     QgsFieldProxyModel.String |
                                     QgsFieldProxyModel.Int |
                                     QgsFieldProxyModel.LongLong
                                    )
        # Настройка масштабов
        self.map_mScale.setScale(100000)
        self.cut_mScale.setScale(25000)
        # Инициализация чекбокса выбранных скважин
        #self.checkBox_Features.setChecked(False)

    # Действия на активацию и выбор слоя скважин в mLayer
    def activ_mLayer (self):
        # Инициализация полей атрибутов
        self.mField_well.setLayer(self.mLayer.currentLayer())
        self.mField_file.setLayer(self.mLayer.currentLayer())
        self.mField_alt.setLayer(self.mLayer.currentLayer())
        self.mField_filters.setLayer(self.mLayer.currentLayer())
        self.mField_gtr.setLayer(self.mLayer.currentLayer())

    # Действия на активацию и выбор слоя изолиний
    def activ_mLayer_izln (self):
        self.mField_elev.setLayer(self.mLayer_izln.currentLayer())

    # Действия на активацию и выбор слоев пересечения
    def activ_mLayer_lnplg (self):
         self.mField_lnplg.setLayer(self.mLayer_lnplg.currentLayer())

    # Действия на нажатие клавиши добавить в список
    def add_click (self):
        layer = self.mLayer_lnplg.currentLayer()
        field = self.mField_lnplg.currentField()
        self.list_lnplg.addItem(f'{layer.name()}\t{field}')
        self.data_lnplg.append((layer, field))

   # Действия на нажатие клавиши удалить из списка
    def remove_click (self):
        index = self.list_lnplg.currentRow()
        self.list_lnplg.takeItem(index)
        self.data_lnplg.pop(index)

    # Подготовка и запуск формы диалога
    def run(self):
        self.activ_mLayer()
        self.activ_mLayer_izln()
        self.activ_mLayer_lnplg()
        self.exec_()
        return self.result()

    # Перегрузка метода диалогового окна accept для
    # проверки заполненности всех полей формы
    def accept (self) :
        # Проверка пути к файлу и выбранного поля
        if (
            self.mField_well.currentField() and
            self.mField_alt.currentField() and
            self.mField_file.currentField() and
            self.mField_gtr.currentField()
           ):
            self.done(QtWidgets.QDialog.Accepted)
        else:
            self.msgBox.warning(self,"Матрица скважин",
                                "Не все поля заполнены.")
    def get_layerwells (self):
        return self.mLayer.currentLayer()

    def get_layercut (self):
        return self.mLayer_cut.currentLayer()

    def get_strm (self):
        if self.mLayer_srtm.currentLayer():
            return  self.mLayer_srtm.currentLayer().dataProvider()
        else: return False

    def get_featwells (self):
        return [feat for feat in self.mLayer.currentLayer().getFeatures()]

    def get_selfeatwells (self):
        return self.mLayer.currentLayer().selectedFeatures()

    def get_featcut (self):
        return [feat for feat in self.mLayer_cut.currentLayer().getFeatures()]

    def get_fieldwells (self):
        return (
                self.mField_well.currentField(),
                self.mField_alt.currentField(),
                self.mField_file.currentField(),
                self.mField_filters.currentField(),
                self.mField_gtr.currentField()
               )

    def get_dirlayer (self):
        return  os.path.dirname(self.mLayer.currentLayer().source())

    def getscale(self):
        return self.map_mScale.scale() / self.cut_mScale.scale()

    def get_mapcut_scale (self):
        return self.map_mScale.scale(), self.cut_mScale.scale()

    def get_izline (self):
        return (
                self.mLayer_izln.currentLayer(),
                self.mField_elev.currentField()
               )

    def get_rivers (self):
        if self.groupBox_rivers.isChecked():
            return (
                    self.mLayer_rivers.currentLayer(),
                    self.mField_rivers.currentField()
                   )
        else: return False

    def get_ages (self):
        if self.groupBox_ages.isChecked():
            return (
                    self.mLayer_ages.currentLayer(),
                    self.mField_ages.currentField()
                   )
        else: return False

    def get_lnplg (self):
        return self.data_lnplg

#-----------------------------------------------------------------------------
#       formCurveWells
#-----------------------------------------------------------------------------

#-----------------------------------------------------------------------------
#  Диалог зоны ЗСО
#  formZonezso
#-----------------------------------------------------------------------------
FORM_CLASS_4, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'ui/zone_zso.ui'))

class formZonezso(QtWidgets.QDialog, FORM_CLASS_4):

    checklist = []
    msgBox = QtWidgets.QMessageBox()

    def __init__(self, parent=None):
        super(formZonezso, self).__init__(parent)
        self.setupUi(self)

        # Реакция на выбор слоя в mLayer
        self.layer_ComboBox.currentIndexChanged.connect(self.activ_layerbox)
        self.layer_ComboBox.setFilters(QgsMapLayerProxyModel.PointLayer)

        self.select_checkBox.setChecked(False)

    # Описание реакции mLayer на активацию и выбор
    def activ_layerbox(self):
        layer = False
        layer = self.layer_ComboBox.currentLayer()
        if layer and layer.selectedFeatures() :
            self.select_checkBox.setEnabled(True)
        else :
            self.select_checkBox.setEnabled(False)

    # Перегрузка метода диалогового окна accept для
    # проверки заполненности всех полей формы
    def accept (self) :
        check, checklist = self.checkzone()
        if check:
            self.checklist = checklist
            self.done(QtWidgets.QDialog.Accepted)
        else:
            self.msgBox.warning(self,
                                "Проверка ввода данных",
                                "Не одно поле радиусов зон не найдено!"
                                )

    # Подготовка и запуск формы диалога
    def run(self):
        self.exec_()
        return self.result()

    # Проверка наличия полей с радиусами
    def checkzone (self) :
        layer = self.layer_ComboBox.currentLayer()
        fnm = layer.fields().names()
        check = [False, False, False]
        if 'r1' in fnm:
            check[0] = True
        else:
            self.msgBox.warning(self,"Проверка атрибутов.",
                                "Отсутствует поле первого пояса 'r1'.")
        if (('r_n2' in fnm) and ('r_w2' in fnm) and
            ('r_s2' in fnm) and ('r_o2' in fnm)):
            check[1] = True
        else:
            self.msgBox.warning(self,"Проверка атрибутов.",
                                "Отсутствует поля второго пояса 'r_2'.")
        if (('r_n3' in fnm) and ('r_w3' in fnm) and
            ('r_s3' in fnm) and ('r_o3' in fnm)):
            check[2] = True
        else:
            self.msgBox.warning(self,"Проверка атрибутов.",
                                "Отсутствует поля третьего пояса 'r_3'.")
        if True in check:
            return True, check
        else:
            return False, check

    def getfeatures(self):
        layer = self.layer_ComboBox.currentLayer()
        if self.select_checkBox.isChecked() :
            features = layer.selectedFeatures()
        else :
            features=[feature for feature in layer.getFeatures()]
        return features

    def getazimut(self):
        return self.azimut_spinBox.value()-90
#-----------------------------------------------------------------------------
#       formZonezso
#-----------------------------------------------------------------------------

