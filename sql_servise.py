import sqlite3 as sl
from sqlite3 import Error
from qgis.PyQt import QtWidgets

""" Функции работы с базой sqlite
"""
class db_servise():
    msgBox = QtWidgets.QMessageBox()
    def __init__(self, db_name) :
        self.conn = self.create_connection(db_name)

    # Соединение с базой данных
    def create_connection(self, path):
        connection = None
        try:
            connection = sl.connect(path)

            #self.msgBox.warning(self,
            #                   "Профиль разреза",
            #                   "Connection to SQLite DB successful")

        except Error as e:
            pass

            #self.msgBox.warning(self,
            #                    "Профиль разреза",
            #                    f"The error '{e}' occurred")

        return connection

    # Запрос к базе
    def execute_query(self, query, query_value):
        cursor = self.conn.cursor()
        try:
            cursor.execute(query, query_value)
            self.conn.commit()

            #self.msgBox.warning(self,
            #                    "Профиль разреза",
            #                    "Query executed successfully")

        except Error as e:
            pass

            #self.msgBox.warning(self,
            #                    "Профиль разреза",
            #                    f"The error '{e}' occurred")

    # Запрос к базе запись нескольких строк
    def executemany_query(self, query, list_value):
        cursor = self.conn.cursor()
        try:
            cursor.executemany(query, list_value)
            self.conn.commit()

            #self.msgBox.warning(self,
            #                    "Профиль разреза",
            #                    "Query executed successfully")

        except Error as e:
            pass

            #self.msgBox.warning(self,
            #                    "Профиль разреза",
            #                    f"The error '{e}' occurred")

    # Извлечение записей из базы
    def execute_read_query(self, query, query_value = False):
        cursor = self.conn.cursor()
        result = None
        try:
            if query_value:
                cursor.execute(query,query_value)
                result = cursor.fetchall()
            else:
                cursor.execute(query)
                result = cursor.fetchall()
            return result
        except Error as e:
            pass

            #self.msgBox.warning(self,
            #                    "Профиль разреза",
            #                    f"The error '{e}' occurred")

    def close_connection (self):
        self.conn.close()

    # Очистка таблиц wells и filters_wells
    def clear_table (self):
        cursor = self.conn.cursor()
        query = 'DELETE FROM filter_probe;'
        cursor.execute(query)
        query = 'DELETE FROM wells;'
        cursor.execute(query)
        self.conn.commit()

    def juliy_data(self, date_user):

        #con = sl.connect(":memory:")
        #return list(con.execute("select julianday('2017-01-01')"))[0][0]

        cursor = self.conn.cursor()
        query = "select julianday(%s)" % date_user
        cursor.execute(query)
        result = cursor.fetchall()
        return result[0][0]

    def create_filter_table (self):
        cursor = self.conn.cursor()
        """
        #query = 'CREATE TABLE filters_wells (id INTEGER PRIMARY KEY '\
                  'AUTOINCREMENT,id_wells INTEGER, beg INTEGER, '\
                  'finish INTEGER, mineral INTEGER);'
        name = "filter_probe"
        query = '''CREATE TABLE {0}
            (id_filter {1} PRIMARY KEY AUTOINCREMENT,
            id_well {1} {5},
            beg  {2} {5},
            fin  {2} {5},
            ph  {2},
            fe_anion  {2},
            cl_anion  {2},
            so4_anion  {2},
            no3_anion  {2},
            no2_anion  {2},
            co3_anion  {2},
            hco3_anion  {2},
            f_anion  {2},
            i_anion  {2},
            br_anion  {2},
            u_anion  {2});'''.format(name, 'INTEGER',' REAL','TEXT',
                                     'BLOB','NOT NULL')

        cursor.execute(query)
        query = 'CREATE INDEX idx_id_well ON %s (id_well)' % name
        cursor.execute(query)

        name = "litol_dict"
        query = '''CREATE TABLE {0}
            (id_dl {1} PRIMARY KEY AUTOINCREMENT,
            name_dl {3} {5},
            lcode_dl  {1} {6} {5});'''.format(name, 'INTEGER',' REAL','TEXT',
                                              'BLOB','NOT NULL','UNIQUE')

        query = '''CREATE TABLE litol_wells (
            id_lit INTEGER PRIMARY KEY AUTOINCREMENT,
            id_wells INTEGER,
            depth REAL,
            comment TEXT,
            id_litol_dict INTEGER);'''

        query = '''CREATE TABLE age_wells (
            id_age INTEGER PRIMARY KEY AUTOINCREMENT,
            id_wells INTEGER,
            depth REAL,
            id_age_dict INTEGER);'''


        query = '''CREATE TABLE age_dict (
            id_da INTEGER PRIMARY KEY AUTOINCREMENT,
            name_da TEXT NOT NULL,
            lcode_da  INTEGER UNIQUE NOT NULL,
            geoindx_da TEXT UNIQUE NOT NULL);'''
        """
        query = '''CREATE TABLE wells (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            longitude REAL NOT NULL,
            latitude REAL NOT NULL,
            data_begin REAL,
            data_end REAL,
            alt_wellhead REAL,
            depth_well REAL,
            work_diamtr_mm INTEGER,
            debit REAL,
            decrease REAL,
            static_level REAL,
            dinamic_level REAL,
            temp_с REAL);'''
        cursor.execute(query)

        query = '''CREATE INDEX wells_id_IDX ON wells (id);'''
        cursor.execute(query)

        self.conn.commit()
        return query
