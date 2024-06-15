import os

from qgis.PyQt import uic
from qgis.PyQt import QtWidgets
from qgis.PyQt.QtWidgets import QAction, QFileDialog
from qgis.PyQt.QtCore import QVariant

from qgis.core import (QgsProject,
                       Qgis,
                       QgsVectorLayer,
                       QgsField,
                       QgsGeometry,
                       QgsFeature,
                       QgsFieldProxyModel,
                       QgsMapLayerProxyModel)

from .utilib import *

FORM_CLASS_1, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'ui/wells_matrix.ui'))

class WellsMatrix(QtWidgets.QDialog, FORM_CLASS_1):

    project = QgsProject.instance()
    plugin_dir = os.path.dirname(__file__)
    filename = ''
    features = []
    cssname = os.path.dirname(__file__) + '/css/style.css'
    msgBox = QtWidgets.QMessageBox()

    def __init__(self, parent=None):
        super(WellsMatrix, self).__init__(parent)
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
        self.encode_combo.addItems(self.enc.get_codelist())
        self.encode_combo.currentIndexChanged.connect(self.set_encode)

        self.checkBox_matrix.setChecked(False)

    # Выбор кодировки
    def set_encode(self):
        self.enc.set_enc(self.encode_combo.currentIndex())

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
        # На случай удаления пути в ручную
        self.filename = self.mFile.lineEdit().text()
        # Проверка пути к файлу и выбранного поля
        dir_name = os.path.dirname(self.filename)
        if os.path.isdir(dir_name) and self.mField.currentField():
            self.exec_matrx()
            self.done(QtWidgets.QDialog.Accepted)
        else :
            self.msgBox.warning(self,"Матрица скважин",
                                "Не все поля заполнены.")

    # Подготовка и запуск формы диалога
    def run(self):
        self.activ_mLayer()
        self.exec_()

    # Подготовка данных для записи в файлы таблиц
    def exec_matrx (self) :
        # Получение выбранного слоя
        wells_vLayer = self.mLayer.currentLayer()
        # Создание списка объектов в зависимости от состояние галочки
        if self.checkBox_Features.isChecked() :
            self.features = wells_vLayer.selectedFeatures()
        else :
            self.features=[feature for feature in wells_vLayer.getFeatures()]
        # Получение поля с именами объектов
        selField = self.mField.currentField()
        # Запуск процедуры составления таблиц в зависимости от выбранного
        # фильтра (расширения файла)
        if  self.filename[-3:] ==  'htm' :
            self.htm_write (selField)
        else :
            self.csv_write (selField)
        # Создание временного слоя с графом в зависимости от состояние галочки
        if  self.checkBox_matrix.isChecked():
            self.create_graph(selField)

    """
    Запись результатов в .csv файл
    selField - выбранное поле с названиями объектов
    """
    def csv_write (self, selField) :

        with open(self.filename, 'w') as output_file:
            line = 'csv'
            for feature in self.features:
                # добавить кодировку
                #line = line + ';' + str(feature[selField])
                line = line + ';' + self.enc.get_utfstr(feature[selField])
            line = line + '\n'
            output_file.write(line)

            for i, feature in enumerate(self.features):
                #line = str(feature[selField])
                line = self.enc.get_utfstr(feature[selField])
                geom = feature.geometry()
                for j, feature_out in enumerate(self.features):
                    if i == j :
                        line = line + ';'
                    else :
                        geom_out = feature_out.geometry()
                        dist = geom.distance(geom_out)
                        line = line + ';' + "{:8.3f}".format(dist)
                line = line + '\n'
                output_file.write(line)

    """
    Запись результатов в вебфайл html
    selField - выбранное поле с названиями объектов
    """
    def htm_write (self, selField) :

        with open(self.filename, 'w') as output_file, \
             open(self.cssname,'r') as css_file:
            line = '''<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01//EN"\
            "http://www.w3.org/TR/html4/strict.dtd">\n<html>\n
            <head>\n<meta http-equiv="Content-Type"\
            content="text/html; charset=utf-8">\n
            <title>Матрица расстояний.</title>\n'''

            line = line + '<style>\n' + css_file.read() + '</style>\n'
            line = line + '</head>\n<body>\n'
            line = line + '<table class="table">\n<thead>\n'
            output_file.write(line)

            line = '<tr><th></th>'

            for feature in self.features:
                # добавить кодировку
                line = line + '<th>' + self.enc.get_utfstr(feature[selField])\
                    + '</th>'
            line = line + '<tr>\n</thead>\n<tbody>\n'
            output_file.write(line)

            for i, feature in enumerate(self.features):
                line = '<tr><th>' + self.enc.get_utfstr(feature[selField]) \
                    + '</th>'
                geom = feature.geometry()
                for j, feature_out in enumerate(self.features):
                    if i == j :
                        line = line + '<th></th>'
                    else :
                        geom_out = feature_out.geometry()
                        dist = geom.distance(geom_out)
                        line = line + '<td>' + "{:8.3f}".format(dist) + '</td>'
                line = line + '<tr>' + '\n'
                output_file.write(line)
            line = '</tbody>\n</table>\n</body>\n</html>'
            output_file.write(line)

    """
    Создание графа
    """
    def create_graph(self, selField):
        # Виртуальный слой графа
        uri = "LineString?crs=epsg:{}".format(self.project.crs().postgisSrid())
        graph_virtLayer = QgsVectorLayer(uri, "graph_line", "memory")
        graph_virtProvider = graph_virtLayer.dataProvider()
        graph_virtProvider.addAttributes([QgsField("dist",QVariant.Double),
                                          QgsField("well_beg",QVariant.String),
                                          QgsField("well_end",QVariant.String)
                                        ])

        graph_fet = QgsFeature()

        # Вычисление расстояний между точками
        i = 0
        while i < len(self.features):
            j = i+1
            geom = self.features[i].geometry()
            while j < len(self.features):
                geom_out = self.features[j].geometry()
                dist = geom.distance(geom_out)

                graph_line = QgsGeometry.fromPolylineXY([geom.asPoint(),
                                                         geom_out.asPoint()])
                graph_fet.setGeometry(graph_line)
                graph_fet.setAttributes([
                        dist,
                        self.enc.get_utfstr(self.features[i][selField]),
                        self.enc.get_utfstr(self.features[j][selField])
                ])
                graph_virtProvider.addFeature(graph_fet)

                j += 1
            i += 1

        graph_virtLayer.updateFields()
        graph_virtLayer.updateExtents()
        del graph_virtProvider

        self.project.addMapLayer(graph_virtLayer, True)
        graph_virtLayer.loadNamedStyle(
            self.plugin_dir + '/legstyle/graph_line.qml'
        )
