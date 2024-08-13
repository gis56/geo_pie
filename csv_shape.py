# -*- coding: utf-8 -*-
import os
from qgis.PyQt.QtCore import QVariant
from qgis.core import (
                       Qgis,
                       QgsField,
                       QgsGeometry,
                       QgsPointXY)

from .pie_dial import formCSVshape
from .utilib import *

#-----------------------------------------------------------------------------
# Создание слоя точек
#----------------------------------------------------------------------------
def csvtoshp():

    def linefeat (line, xf, yf):
        line = dialog.enc.utftodec(line)
        records = line.split(dialog.split_char)
        try:
            x = float(records[xf].strip().replace(',','.'))
            y = float(records[yf].strip().replace(',','.'))
            geom = QgsGeometry.fromPointXY(QgsPointXY(x,y))
            return True, (geom, records)
        except ValueError as e:
            txt =  f"Приведение типов {e}."
            return False, txt

    def addfeat():
        boo, feat = linefeat(line, xf, yf)
        if boo:
            feats.append(feat)
            return True, "ok!"
        else:
            return  False, feat

    dialog = formCSVshape()
    result = dialog.run()
    if result:
        head, file = dialog.csvpath()
        xf, yf = dialog.xyFields()

        with open (file, 'r',
                   encoding=dialog.enc.enc,
                   errors=dialog.enc.err) as csvfile:

            # Формирование списка аттрибутов
            line = csvfile.readline().rstrip('\n')
            fields = line.split(dialog.split_char)
            feats = []
            if not head:
                fields = [f'field_{i}' for i, field in enumerate(fields)]
                err, txt = addfeat()
                if not err:
                    return Qgis.Warning, txt, "Ошибка"
            attr = []
            for field in fields:
                attr.append(QgsField(field.strip(), QVariant.String))

            # Формирование геометрии точек
            for line in csvfile:
                err, txt = addfeat()
                if not err:
                    return Qgis.Warning, txt, "Ошибка"
        csvfile.close()

        vlayer = maplayer(feats, "point_csv", attr, "Point")
        #vlayer.loadNamedStyle(
        #          os.path.dirname(__file__) + '/legstyle/graph_line.qml')
        txt = "Результат в point_csv."
    else: txt = "Отмена."
    del dialog
    return Qgis.Success, txt, "Завершено"
