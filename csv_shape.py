import os
from sys import getdefaultencoding
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
from .utilib import *

FORM_CLASS_1, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'ui/csv_to_shape.ui'))


class csvShape(QtWidgets.QDialog, FORM_CLASS_1):
    project = QgsProject.instance()
    msgBox = QtWidgets.QMessageBox()
    # Список кодировок
    encode_list = ['utf-8',
                   'Windows-1251']
    encode_sel = {'name':'utf-8', 'err':'replace'}
    # Заголовки полей атрибутивной таблицы
    csv_head = []
    # Список стор файла .csv
    csvline = []
    split_char = ';'

    def __init__(self, parent=None):
        super(csvShape, self).__init__(parent)
        self.setupUi(self)
        # Инициализация выбора кодировки
        self.encode_comboBox.addItem('- не выбрана -')
        self.encode_comboBox.insertSeparator(1)
        self.enc = EncDec()
        self.encode_comboBox.addItems(self.enc.get_codelist())
        self.encode_comboBox.currentIndexChanged.connect(self.set_encode)

        #self.encode_comboBox.addItems(self.encode_list)
        #self.encode_comboBox.currentIndexChanged.connect(self.set_encode)

        self.csv_file_widget.setFilter('Таблица с разделителем CSV (*.csv);;\
                                       Любой файл (*)')
        self.csv_file_widget.fileChanged.connect(self.csv_open)
        self.field_check.clicked.connect(self.change_head)

    # Выбор кодировки
    def set_encode(self):
        self.enc.set_enc(self.encode_comboBox.currentIndex())
        if self.csv_file_widget.lineEdit().text():
            self.csv_open(False)

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
    def csv_open(self, update_head=True):
        # Чтение файла
        csvpath = self.csv_file_widget.lineEdit().text()
        self.csvline = []
        try:
            with open (csvpath, 'r',
                       encoding=self.enc.enc,
                       errors=self.enc.err) as csvfile:
                for line in csvfile:
                    self.csvline.append(line.rstrip('\n'))

            if update_head:
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
    # Создание слоя точек
    def point_csv(self):
        uri = "Point?crs=epsg:{}".format(self.project.crs().postgisSrid())
        csvpoint_virtLayer = QgsVectorLayer(uri, "csvpoint", "memory")
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
        index_x = self.longitude_comboBox.currentIndex()
        index_y = self.latitude_comboBox.currentIndex()
        csvpoint_fet = QgsFeature()
        for feat in self.csvline:
            if not self.decode_check.isChecked():
                #feat = feat.encode('utf-8').decode(self.encode_sel['name'])
                feat = self.enc.get_utf2sel(feat)
            records = feat.split(self.split_char)
            try:
                point_x = float(records[index_x].strip().replace(',','.'))
                point_y = float(records[index_y].strip().replace(',','.'))
            except ValueError as e:
                self.msgBox.warning(self, "Ошибка приведения типов.", str(e))
                break
            csvpoint_geom = QgsGeometry.fromPointXY(QgsPointXY(point_x,
                                                               point_y)
                            )
            csvpoint_fet.setGeometry(csvpoint_geom)
            # Формирование аттрибутов точек (запись в аттрибутивную таблицу)
            csvpoint_fet.setAttributes(records)
            csvpoint_virtProvider.addFeature(csvpoint_fet)

        csvpoint_virtLayer.updateFields()
        csvpoint_virtLayer.updateExtents()
        del csvpoint_virtProvider

        self.project.addMapLayer(csvpoint_virtLayer, True)
