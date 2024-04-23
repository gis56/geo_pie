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
                       QgsPointXY)

FORM_CLASS_1, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'ui/csv_to_shape.ui'))


class csvShape(QtWidgets.QDialog, FORM_CLASS_1):

    #pnt_layer = []
    project = QgsProject.instance()
    #plugin_dir = os.path.dirname(__file__)
    #filename = ''
    #features = []
    #cssname = os.path.dirname(__file__) + '/css/style.css'
    msgBox = QtWidgets.QMessageBox()
    encode_list = ['-не выбрана-','utf-8','Windows-1251']
    csv_head = []
    csvline = []
    split_char = ';'

    def __init__(self, parent=None):
        super(csvShape, self).__init__(parent)
        self.setupUi(self)
        self.encode_comboBox.addItems(self.encode_list)
        self.csv_file_widget.setFilter('*.csv;; *.txt;; *')
        self.csv_file_widget.fileChanged.connect(self.csv_open)
        self.field_check.clicked.connect(self.change_head)
        self.encode_comboBox.currentIndexChanged.connect(self.csv_open)

    # Подготовка и запуск формы диалога
    def run(self):
        self.exec_()

    # Перегрузка ok
    def accept(self):
        if not self.csv_file_widget.lineEdit().text():
            self.msgBox.warning(self,
                                "Ошибка выполнения",
                                "Файла не существует"
                                )
        elif not self.csvline:
            self.msgBox.warning(self,
                                "Ошибка выполнения",
                                "Смените кодировку."
                                )
        else:
            self.point_csv()
            self.done(QtWidgets.QDialog.Accepted)

    # Выбор файла
    def csv_open(self):
        csvpath = self.csv_file_widget.lineEdit().text()
        if self.encode_comboBox.currentIndex() == 0:
            encode = 'utf-8'
            encode_err = 'replace'
        else:
            encode = self.encode_comboBox.currentText()
            encode_err = 'strict'
        self.csvline = []
        try:
            with open (csvpath, 'r',
                       encoding=encode, errors=encode_err) as csvfile:
                for line in csvfile:
                    self.csvline.append(line.rstrip('\n'))
            self.change_head()
        except FileNotFoundError:
            self.msgBox.warning(self,
                                "Ошибка при открытии файла",
                                "Файл не найден."
                                )
        except UnicodeError:
            self.msgBox.warning(self,
                                "Ошибка при открытии файла",
                                "Смените кодировку"
                                )
            self.latitude_comboBox.clear()
            self.longitude_comboBox.clear()
        except Exception as e:
            self.msgBox.warning(self, "Ошибка при открытии файла", e)

    # Строка заголовка
    def change_head(self):
        self.latitude_comboBox.clear()
        self.longitude_comboBox.clear()
        if self.csvline:
            csv_head = self.csvline[0].split(self.split_char)
            if self.field_check.isChecked():
                self.latitude_comboBox.addItems(csv_head)
                self.longitude_comboBox.addItems(csv_head)
                self.csv_head = csv_head
            else:
                cl = ['field'+str(i+1)+' | '+cl
                      for i, cl in enumerate(csv_head)]
                self.latitude_comboBox.addItems(cl)
                self.longitude_comboBox.addItems(cl)
                self.csv_head = ['field'+str(i+1)
                                 for i in range(0, len(csv_head))]

    def point_csv(self):
        csvpoint_virtLayer = QgsVectorLayer("Point?crs=epsg:28410",
                                            "csvpoint",
                                            "memory")
        csvpoint_virtProvider = csvpoint_virtLayer.dataProvider()
        # Сформировать список аттрибутов
        attr_list = []
        for name_field in self.csv_head:
            attr_list.append(QgsField(name_field.strip(),QVariant.String))
        # Создаем список аттрибутов (поля аттрибутивной таблицы)
        csvpoint_virtProvider.addAttributes(attr_list)
        # Удалить первую запись в списке строк файлов если она заголовок
        if self.field_check.isChecked():
            self.csvline.pop(0)
        # Формирование геометрии точек
        ix = self.longitude_comboBox.currentIndex()
        iy = self.latitude_comboBox.currentIndex()
        csvpoint_fet = QgsFeature()
        for feat in self.csvline:
            records = feat.split(self.split_char)
            csvpoint_geom = QgsGeometry.fromPointXY(QgsPointXY(
                                float(records[ix].strip().replace(',','.')),
                                float(records[iy].strip().replace(',','.'))
                            )
            )
            csvpoint_fet.setGeometry(csvpoint_geom)
            # Формирование аттрибутов точек (запись в аттрибутивную таблицу)
            csvpoint_fet.setAttributes(records)
            csvpoint_virtProvider.addFeature(csvpoint_fet)

        csvpoint_virtLayer.updateFields()
        csvpoint_virtLayer.updateExtents()
        del csvpoint_virtProvider

        self.project.addMapLayer(csvpoint_virtLayer, True)
    """
        graph_virtLayer.loadNamedStyle(
            self.plugin_dir + '/legstyle/graph_line.qml'
        )
    """
