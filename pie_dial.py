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
        wells_vLayer = self.mLayer.currentLayer()
        # Проверка на наличие выборки. Если есть выбранные объекты,
        # сделать доступным галочку
        if wells_vLayer.selectedFeatures() :
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
