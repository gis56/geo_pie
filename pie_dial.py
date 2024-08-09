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

        self.enc_out_combo.addItems(self.enc.item)
        self.enc_out_combo.currentIndexChanged.connect(self.set_out_enc)

        self.checkBox_matrix.setChecked(False)

    # Выбор кодировки
    def set_encode(self):
        self.enc.set_enc(self.encode_combo.currentIndex())

    def set_out_enc (self):
        self.enc.set_dec(self.enc_out_combo.currentIndex())

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

    def get_featwells (self):
        wells_vLayer = self.mLayer.currentLayer()
        if self.checkBox_Features.isChecked() :
            features = wells_vLayer.selectedFeatures()
        else :
            features=[feature for feature in wells_vLayer.getFeatures()]

        return features

    def get_namefield (self):
        return self.mField.currentField()

    def filename (self):
        return self.mFile.lineEdit().text()

    def is_graph (self):
        return self.checkBox_matrix.isChecked()
#-----------------------------------------------------------------------------
#      formWellMatrix()
#-----------------------------------------------------------------------------


