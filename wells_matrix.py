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
                       QgsFeature)

FORM_CLASS_1, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'ui/wells_matrix.ui'))

class WellsMatrix(QtWidgets.QDialog, FORM_CLASS_1):

    pnt_layer = []
    project = QgsProject.instance()
    plugin_dir = os.path.dirname(__file__)
    filename = ''
    features = []
    cssname = os.path.dirname(__file__) + '/css/style.css'
    msgBox = QtWidgets.QMessageBox()

    def __init__(self, parent=None):
        super(WellsMatrix, self).__init__(parent)
        self.setupUi(self)

        self.pushButton_save_html.clicked.connect(self.select_html_file)

        self.comboBox_layerName.activated.connect(self.activ_layerName)
        self.comboBox_layerName.currentIndexChanged.connect(self.activ_layerName)

        self.checkBox_matrix.setChecked(False)

    # Описание реакции кнопки выбора файла
    def select_html_file(self):
        self.filename, filter = QFileDialog.getSaveFileName(
            self,
            "Выберите файл для хранения таблицы ",
            "w_mtrx01",
            'Web (*.htm);;CSV table (*.csv)'
        )
        self.lineEdit_save_html.setText(self.filename)

    # Описание реакции comboBox со слоями точек (скважин)
    def activ_layerName(self) :
        wells_vLayer = self.pnt_layer[self.comboBox_layerName.currentIndex()]
        if wells_vLayer :
            fields = wells_vLayer.fields()
            fields_int = []

            for field in fields :
                fields_int.append(field.name())

            self.comboBox_selField.clear()
            self.comboBox_selField.addItems(fields_int)
            self.checkBox_Features.setChecked(False)

            # Проверка на наличие выборки. Если есть выбранные объекты,
            # сделать доступным галочку

            if wells_vLayer.selectedFeatures() :
                self.checkBox_Features.setEnabled(True)
            else :
                self.checkBox_Features.setEnabled(False)

    # Перегрузка метода диалогового окна accept для
    # проверки заполненности всех полей формы
    def accept (self) :
        # Путь к файлу должен быть взят из lineEdit
        # На случай удаления пути в ручную
        self.filename = self.lineEdit_save_html.text()
        # Проверка пути к файлу и выбранного поля
        #if os.path.isfile(self.filename) and \
        #self.comboBox_selField.currentText():
        dir_name = os.path.dirname(self.filename)
        if os.path.isdir(dir_name) and self.comboBox_selField.currentText():
            self.exec_matrx()
            self.done(QtWidgets.QDialog.Accepted)
        else :
            self.msgBox.warning(self,"Матрица скважин", "Не все поля заполнены.")

    # Подготовка и запуск формы диалога
    def run(self):
        self.comboBox_layerName.clear()
        self.comboBox_selField.clear()

        # Получение списка векторных слоев проекта
        layers = self.project.mapLayers()
        layers_val = layers.values()
        layer_name = [layer.name() for layer in layers_val]
        layer_type = [str(layer.type()) for layer in layers_val]

        for layer in layers_val:
            # Тип слоя - векторный
            if layer.type() == 0:
                # Тип геометрии - точка
                if layer.geometryType() == 0 :
                    # Отсеянные слои в список. Индексы в pnt_layer и в
                    # comboBox_layerName для слоя будут одинаковые
                    self.pnt_layer.append(layer)
                    self.comboBox_layerName.addItems([layer.name()])
        self.exec_()

    # Подготовка данных для записи в файлы таблиц
    def exec_matrx (self) :
        # Получение уникального индекса слоя по выбранному индексу
        # comboBox_layerName и поиск по нему слоя в проекте
        wells_vLayer = self.pnt_layer[self.comboBox_layerName.currentIndex()]
        # Создание списка объектов в зависимости от состояние галочки
        if self.checkBox_Features.isChecked() :
            self.features = wells_vLayer.selectedFeatures()
        else :
            self.features =  [feature for feature in wells_vLayer.getFeatures()]
        # Название поля с именами объектов
        selField = self.comboBox_selField.currentText()
        # Запуск процедуры составления таблиц в зависимости от выбранного
        # фильтра (расширения файла)
        if  self.filename[-3:] ==  'htm' :
            self.htm_write (selField)
        else :
            self.csv_write (selField)
        # Создание временного слоя с графом в зависимости от состояние галочки
        if  self.checkBox_matrix.isChecked():
            self.create_graph()

    """
    Запись результатов в .csv файл
    selField - выбранное поле с названиями объектов
    """
    def csv_write (self, selField) :

        with open(self.filename, 'w') as output_file:
            line = 'csv'
            for feature in self.features:
                line = line + ';' + str(feature[selField])
            line = line + '\n'
            output_file.write(line)

            for i, feature in enumerate(self.features):
                line = str(feature[selField])
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
            line = '<style>\n' + css_file.read() + '</style>\n'
            line = line + '<table class="table">\n<thead>\n'
            output_file.write(line)

            line = '<tr><th></th>'

            for feature in self.features:
                line = line + '<th>' + str(feature[selField]) + '</th>'
            line = line + '<tr>\n</thead>\n<tbody>\n'
            output_file.write(line)

            for i, feature in enumerate(self.features):
                line = '<tr><th>' + str(feature[selField]) + '</th>'
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
            line = '</tbody>\n</table>'
            output_file.write(line)

    """
    Создание графа
    """
    def create_graph(self):
        # Виртуальный слой графа
        graph_virtLayer = QgsVectorLayer("LineString?crs=epsg:28410",
                                         "graph_line",
                                         "memory")
        graph_virtProvider = graph_virtLayer.dataProvider()
        graph_virtProvider.addAttributes([QgsField("dist",QVariant.Double)])

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
                graph_fet.setAttributes([dist])
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
