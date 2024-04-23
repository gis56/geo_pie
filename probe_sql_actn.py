import os

import sqlite3 as sl
from sqlite3 import Error

from .sql_servise import *

from qgis.PyQt import uic
from qgis.PyQt import QtWidgets
from qgis.PyQt.QtWidgets import (QAction,
                                 QFileDialog,
                                 QTableWidgetItem,
                                 QAbstractItemView,
                                 QComboBox)
from qgis.PyQt.QtCore import QVariant, Qt

from qgis.core import (QgsProject,
                       Qgis,
                       QgsVectorLayer,
                       QgsField,
                       QgsGeometry,
                       QgsFeature)

FORM_CLASS_2, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'ui/wells_db_editor.ui'))

# Для отключения редактирования столбца
# как работает не понимаю, но работает
class ReadOnlyDelegate(QtWidgets.QStyledItemDelegate):
    def createEditor(self, parent, option, index):
        return


class DBEditor(QtWidgets.QDialog, FORM_CLASS_2):

    project = QgsProject.instance()
    plugin_dir = os.path.dirname(__file__)
    msgBox = QtWidgets.QMessageBox()
    longitude = 0
    latitude = 0
    name_wells = ""
    id_wells = 0
    id_layer = ""
    litol_code = ['', False]
    litol_dict = dict()
    age_code = ['', False]
    age_dict = dict()

    def __init__(self, parent=None):
        """Constructor."""
        super(DBEditor, self).__init__(parent)
        self.setupUi(self)

        #self.sql_serv = db_servise(os.path.join(self.plugin_dir,
        #                                        'db/orders.db'))
        self.sql_serv = db_servise(os.path.join('/home/jh56/qgis/db/'\
                                                'orders.db'))
        # Добавление/Удаление строк в фильтрах
        self.add_litol_pushButton.clicked.connect(self.add_clicked)
        self.del_litol_pushButton.clicked.connect(self.del_clicked)

        # Добавление/Удаление строк в литологии
        self.add_filter_pushButton.clicked.connect(self.add_colmn_clicked)
        self.del_filter_pushButton.clicked.connect(self.del_colmn_clicked)
        # Выбор из справочника литологии
        self.litol_comboBox.currentIndexChanged.connect(self.comboBox_clicked)

        # Добавление/Удаление строк в возрастах
        self.add_age_pushButton.clicked.connect(self.add_row_age_clicked)
        self.del_age_pushButton.clicked.connect(self.del_row_age_clicked)
        # Выбор из справочника возрастов
        self.age_comboBox.currentIndexChanged.connect(
            self.age_comboBox_clicked)

        # Очистка таблиц
        self.clearTable_pushButton.clicked.connect(self.clear_table)
        # Создание таблицы
        self.creat_db_pushButton.clicked.connect(self.create_table)

    # Очистка таблиц
    def clear_table (self):
        self.sql_serv.clear_table()

    # Создание таблицы
    def create_table (self):
        txt = self.sql_serv.create_filter_table()
        self.msgBox.warning(self,"query", txt)

    # Выбор из справочника литологии
    def comboBox_clicked (self):
        row = self.litol_tableWidget.currentRow()
        #self.filters_tableWidget.setItem(
        #    row,
        #    2,
        #    QTableWidgetItem(self.mineral_comboBox.currentText()))

        code = self.litol_code[self.litol_comboBox.currentIndex()]
        #code = self.mineral_comboBox.currentIndex()
        self.litol_tableWidget.setItem(row,2,QTableWidgetItem(str(code)))

     # Кнопка добавить колонку фильтр
    def add_colmn_clicked (self):
        colmn = self.filters_tableWidget.columnCount()
        self.filters_tableWidget.insertColumn(colmn)

        item = list()
        i=0
        while i < (self.filters_tableWidget.rowCount()):
            item.append(QTableWidgetItem())
            item[i].setData(Qt.DisplayRole, 0.00)
            item[i].setData(Qt.UserRole, float)
            item[i].setTextAlignment(Qt.AlignHCenter);
            self.filters_tableWidget.setItem(i,colmn,item[i])
            i = i+1

    # Кнопка удалить колонку фильтр
    def del_colmn_clicked (self):
        colmn = self.filters_tableWidget.currentColumn()
        if self.filters_tableWidget.columnCount() > 0 :
            self.filters_tableWidget.removeColumn(colmn)

    # Кнопка добавить литологию
    def add_clicked (self):
        # Сортировка фильтров по глубине залегания
        self.litol_tableWidget.sortItems(0,0)
        row = self.litol_tableWidget.rowCount()
        self.litol_tableWidget.insertRow(row)
        # Задание ячейке типа вводимых данных
        item = QTableWidgetItem()
        item.setData(Qt.DisplayRole, 0.00)
        item.setData(Qt.UserRole, float)
        item.setTextAlignment(Qt.AlignHCenter);
        self.litol_tableWidget.setItem(row,0,item)

        #self.filters_tableWidget.item(row,2).setEditTriggers(
        #    QAbstractItemView.NoEditTriggers)
        #self.filters_tableWidget.setItem(
        #    0,0,
        #    QTableWidgetItem(u'%s' % str(row)))

    # Кнопка удалить литологию
    def del_clicked (self):
        #!!!!!!!
        #self.name_lineEdit.setText(self.filters_tableWidget.item(0,0).text())
        row = self.litol_tableWidget.currentRow()
        if self.litol_tableWidget.rowCount() > 0 :
            #self.filters_tableWidget.removeCellWidget(row,2)
            self.litol_tableWidget.removeRow(row)

    # Запись литологии в базу данных
    def write_litol (self, id_wells):
        # Сортировка фильтров по глубине залегания
        self.litol_tableWidget.sortItems(0,0)
        i = 0
        query = 'INSERT INTO litol_wells (id_wells, depth, comment, '\
            'id_litol_dict) VALUES (?,?,?,?)'

        while i < self.litol_tableWidget.rowCount():
            depth = self.litol_tableWidget.item(i,0).text()
            comment = self.litol_tableWidget.item(i,1).text()
            # !!! Записывать в базу нужно id из litol_dict, а не lcode
            lcode_lit = self.litol_tableWidget.item(i,2).text()
            query_value = (id_wells,float(depth),
                           comment,
                           int(self.litol_dict[int(lcode_lit)]))
            self.sql_serv.execute_query(query, query_value)
            i = i+1

    # Кнопка добавить возраст
    def add_row_age_clicked (self):
        # Сортировка фильтров по глубине залегания
        self.age_tableWidget.sortItems(0,0)
        row = self.age_tableWidget.rowCount()
        self.age_tableWidget.insertRow(row)
        # Задание ячейке типа вводимых данных
        item = QTableWidgetItem()
        item.setData(Qt.DisplayRole, 0.00)
        item.setData(Qt.UserRole, float)
        item.setTextAlignment(Qt.AlignHCenter);
        self.age_tableWidget.setItem(row,0,item)

        #self.filters_tableWidget.item(row,2).setEditTriggers(
        #    QAbstractItemView.NoEditTriggers)
        #self.filters_tableWidget.setItem(
        #    0,0,
        #    QTableWidgetItem(u'%s' % str(row)))

    # Кнопка удалить возраст
    def del_row_age_clicked (self):
        #!!!!!!!
        #self.name_lineEdit.setText(self.filters_tableWidget.item(0,0).text())
        row = self.age_tableWidget.currentRow()
        if self.age_tableWidget.rowCount() > 0 :
            #self.filters_tableWidget.removeCellWidget(row,2)
            self.age_tableWidget.removeRow(row)

    # Выбор из справочника возрастов
    def age_comboBox_clicked (self):
        row = self.age_tableWidget.currentRow()
        #self.filters_tableWidget.setItem(
        #    row,2,
        #    QTableWidgetItem(self.mineral_comboBox.currentText()))
        code = self.age_code[self.age_comboBox.currentIndex()]
        #code = self.mineral_comboBox.currentIndex()
        self.age_tableWidget.setItem(row,1,QTableWidgetItem(str(code)))

    # Запись литологии в базу данных
    def write_age (self, id_wells):
        # Сортировка фильтров по глубине залегания
        self.age_tableWidget.sortItems(0,0)
        i = 0
        query = 'INSERT INTO age_wells (id_wells, depth, id_age_dict) '\
            'VALUES (?,?,?)'

        while i < self.age_tableWidget.rowCount():
            depth = self.age_tableWidget.item(i,0).text()
            # !!! Записывать в базу нужно id из litol_dict, а не lcode
            lcode_age = self.age_tableWidget.item(i,1).text()
            query_value = (id_wells,
                           float(depth),
                           int(self.age_dict[int(lcode_age)])
                           )
            self.sql_serv.execute_query(query, query_value)
            i = i+1

    """
    # Запись фильтров в базу данных
    def write_filters (self, id_wells):
        i = 0
        j = 0
        query = 'INSERT INTO filter_probe (id_well, beg, fin, ph, fe_anion, '\
            'cl_anion, so4_anion, no3_anion, no2_anion, co3_anion, '\
            'hco3_anion, f_anion, i_anion, br_anion, u_anion) '\
            'VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)'
        while i < self.filters_tableWidget.columnCount():
            query_value = list()
            query_value.append(id_wells)
            while j < self.filters_tableWidget.rowCount():
                query_value.append(
                    float(self.filters_tableWidget.item(j,i).text()))
                j = j+1
            query_value = (query_value)
            self.sql_serv.execute_query(query, query_value)
            j = 0
            i = i+1
    """
    # Запись фильтров в базу данных
    def write_filters (self, id_wells):
        i = 0
        j = 0
        many_value = list()
        query = 'INSERT INTO filter_probe (id_well, beg, fin, ph, fe_anion, '\
            'cl_anion, so4_anion, no3_anion, no2_anion, co3_anion, '\
            'hco3_anion, f_anion, i_anion, br_anion, u_anion) '\
            'VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)'
        while i < self.filters_tableWidget.columnCount():
            query_value = list()
            query_value.append(id_wells)
            while j < self.filters_tableWidget.rowCount():
                query_value.append(
                    float(self.filters_tableWidget.item(j,i).text()))
                j = j+1
            many_value.append((query_value))
            j = 0
            i = i+1
        self.sql_serv.executemany_query(query, many_value)

    """ Пометка скважины как заполненной
    """
    def wells_ok_status(self):
        layer = QgsProject.instance().mapLayer(self.id_layer)
        layer.startEditing()
        layer.changeAttributeValue(self.id_wells, 5, 1)
        layer.commitChanges()

    """  Перегрузка метода диалогового окна accept
    для проверки заполненности всех полей формы
    """
    def accept (self) :

        ju_data = self.sql_serv.juliy_data(
            self.begin_dateEdit.date().toString('yyyy-dd-MM'))
        #self.msgBox.warning(self,"Профиль разреза", str(ju_data))
        #self.msgBox.warning(self,
        #                    "Профиль разреза",
        #                    self.begin_dateEdit.date().toString('yyyy.dd.MM'))

        # Устанавливаем соединение с базой данных
        query = 'INSERT INTO wells (name, longitude, latitude, data_begin) '\
            'VALUES (?,?,?,?)'
        query_value = (self.name_wells,self.longitude,self.latitude, ju_data)
        # Добавляем новую скважину
        self.sql_serv.execute_query(query, query_value)
        # Получить id скважины для заполнения таблицы фильтров
        query = 'SELECT MAX(id) FROM wells'
        fetch = self.sql_serv.execute_read_query(query)
        id_wells = fetch[0][0]

        # Запись фильтров
        self.write_filters(id_wells)

        # Запись литологии
        self.write_litol (id_wells)

        # Запись возрастов
        self.write_age (id_wells)

        # Сохраняем изменения и закрываем соединение
        self.sql_serv.close_connection()
        #self.conn.close()
        # Помечаеи скважину
        self.wells_ok_status()
        # Закрываем форму
        self.done(QtWidgets.QDialog.Accepted)

        #self.msgBox.warning(self,
        #                    "Профиль разреза",
        #                    self.begin_dateEdit.date().toString())
        """
        # Проверка пути к файлу и выбранного поля
        # os.path.isfile(self.filename)
        if self.id_ln_layer[self.comboBox_outcrop.currentIndex()]:
            self.exec_profile()
            self.done(QtWidgets.QDialog.Accepted)
        else :
            self.msgBox.warning(self,
                                "Профиль разреза",
                                "Не указана линия разреза")
        """

    def run(self):
        self.name_lineEdit.setText(self.name_wells)
        self.long_lineEdit.setText(str(self.longitude))
        self.lat_lineEdit.setText(str(self.latitude))
        # Проверка наличия в базе со схожими координатами
        fetchs = False
        query = 'SELECT name, longitude, latitude FROM wells '\
            'WHERE (longitude == ?  AND latitude == ?)'
        query_value = (self.longitude, self.latitude)
        fetchs = self.sql_serv.execute_read_query(query, query_value)

        if fetchs:
            self.msgBox.warning(self,
                                "Профиль разреза",
                                "Скважина с такими координатами уже '\
                                'есть.\nСкважина №  " + \
                                str(fetchs[0][0]))

        # Отключает редактирование в столбце литологии
        delegate = ReadOnlyDelegate(self.litol_tableWidget)
        self.litol_tableWidget.setItemDelegateForColumn(2, delegate)

        # Заполнение справочника литологии
        query = 'SELECT name_dl, lcode_dl, id_dl FROM litol_dict'
        fetchs = self.sql_serv.execute_read_query(query)

        self.litol_comboBox.clear()
        self.litol_comboBox.addItem("- Не выбран - ")
        self.litol_comboBox.insertSeparator(1)

        for fetch in fetchs:
            self.litol_dict[fetch[1]] = fetch[2]
            self.litol_code.append(fetch[1])
            self.litol_comboBox.addItem(fetch[0])

        # Отключает редактирование в столбце возрастов
        delegate = ReadOnlyDelegate(self.age_tableWidget)
        self.age_tableWidget.setItemDelegateForColumn(1, delegate)

        # Заполнение справочника возрастов
        query = 'SELECT name_da, lcode_da, id_da FROM age_dict'
        fetchs = self.sql_serv.execute_read_query(query)

        self.age_comboBox.clear()
        self.age_comboBox.addItem("- Не выбран - ")
        self.age_comboBox.insertSeparator(1)

        for fetch in fetchs:
            self.age_dict[fetch[1]] = fetch[2]
            self.age_code.append(fetch[1])
            self.age_comboBox.addItem(fetch[0])

        # show the dialog
        self.show()
        # Run the dialog event loop
        self.exec_()
"""
def wells_actn (name,x,y):
    msgBox = QtWidgets.QMessageBox()
    msgBox.warning(msgBox,
                "Данные скважины",
                "Наменование: "+name+"\nДолгота: "+str(x)+"\nШирота: "+str(y))

from save_attributes.probe_sql_actn import DBEditor
dbe = DBEditor()
dbe.name_wells = "[%name%]"
dbe.longitude = [% $y %]
dbe.latitude = [% $x %]
dbe.run()
"""
