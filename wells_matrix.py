# -*- coding: utf-8 -*-
import os
from qgis.PyQt.QtCore import QVariant
from qgis.core import (
                       Qgis,
                       QgsField,
                       QgsGeometry
                      )
from .pie_dial import formWellsMatrix
from .utilib import *

#-----------------------------------------------------------------------------
#    Запись результатов в .csv файл
#    wname - выбранное поле с названиями объектов
#-----------------------------------------------------------------------------
def csv_write (features, wname, filename, enc, lname) :
    try:
        with open(filename, 'w', encoding=enc.dec, errors=enc.err)\
            as output_file:
            line = lname
            for feature in features:
                # добавить кодировку
                line = f"{line}; {feature[wname]}"
            line += '\n'
            output_file.write(enc.get_str(line))

            for i, feature in enumerate(features):
                line = f"{feature[wname]}"
                geom = feature.geometry()
                for j, feature_out in enumerate(features):
                    if i == j :
                        line += ';'
                    else :
                        geom_out = feature_out.geometry()
                        dist = geom.distance(geom_out)
                        line += ";{:8.3f}".format(dist)
                line += '\n'
                output_file.write(enc.get_str(line))
        output_file.close()
        return True, f"Таблица CSV: {filename}"
    except UnicodeError:
        return False, "Ошибка выбора кодировки!"
    except FileNotFoundError:
        return False, "Файл не найден!"
    except Exception as e:
        return False, f"Ошибка: {e}"

#-----------------------------------------------------------------------------
#    Запись результатов в вебфайл html
#    wname - выбранное поле с названиями объектов
#-----------------------------------------------------------------------------
def htm_write (features, wname, filename, enc, lname) :
    try:
        cssname =  os.path.dirname(__file__) + '/css/style.css'
        with open(filename, 'w', encoding=enc.dec, errors=enc.err)\
            as output_file, open(cssname,'r') as css_file:
            line = f'''<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01//EN" \
"http://www.w3.org/TR/html4/strict.dtd">\n<html>\n<head>\n\
<meta http-equiv="Content-Type" content="text/html; charset={enc.dec}">\n\
<title>Матрица расстояний.</title>\n'''

            line += '<style>\n{}</style>\n'.format(css_file.read())
            line += '</head>\n<body>\n'
            line += '<table class="table">\n<thead>\n'
            output_file.write(enc.get_str(line))

            line = f'<tr><th>{lname}</th>'

            for feature in features:
                # добавить кодировку
                line += f'<th>{feature[wname]}</th>'
            line += '<tr>\n</thead>\n<tbody>\n'
            output_file.write(enc.get_str(line))

            for i, feature in enumerate(features):
                line = f'<tr><th>{feature[wname]}</th>'
                geom = feature.geometry()
                for j, feature_out in enumerate(features):
                    if i == j :
                        line += '<th></th>'
                    else :
                        geom_out = feature_out.geometry()
                        dist = geom.distance(geom_out)
                        line += '<td>{:8.3f}</td>'.format(dist)
                line += '<tr>\n'
                output_file.write(enc.get_str(line))
            line = '</tbody>\n</table>\n</body>\n</html>'
            output_file.write(enc.get_str(line))
            output_file.close()
            css_file.close()
            return True, f'Таблица HTML: {filename}'
    except UnicodeError:
        return False, 'Ошибка выбора кодировки!'
    except FileNotFoundError:
        return False, 'Файл не найден!'
    except Exception as e:
        return False, f'Ошибка: {e}'

#-----------------------------------------------------------------------------
#    Создание графа
#-----------------------------------------------------------------------------
def create_graph(features, wname, enc):

    # Вычисление расстояний между точками
    lines = []
    i = 0
    while i < len(features):
        j = i+1
        geom_beg = features[i].geometry()
        while j < len(features):
            geom_end = features[j].geometry()
            dist = geom_beg.distance(geom_end)

            geom = QgsGeometry.fromPolylineXY([
                                                geom_beg.asPoint(),
                                                geom_end.asPoint()
                                              ])
            attr = [
                    dist,
                    enc.get_str(f"{features[i][wname]}"),
                    enc.get_str(f"{features[j][wname]}")
                   ]
            lines.append((geom, attr))
            j += 1
        i += 1

    return lines
#-----------------------------------------------------------------------------
# Главная функция
# features - объекты слоя
# name_well - поле с именами скважин
# filename - полное имя файла для записи талицы
# lname - наименование слоя
# enc - объект кодировки
#-----------------------------------------------------------------------------
def dist_well_table():
    dialog = formWellsMatrix()
    result = dialog.run()
    if result:
        features = dialog.featwells()
        name_well = dialog.namefield()
        filename = dialog.filename()
        enc = dialog.enc
        lname = dialog.layer().name()
        if filename[-3:] == "csv":
            lvl, txt = csv_write(features, name_well, filename, enc, lname)
            if not lvl: return Qgis.Warning, txt, "Ошибка"
        else:
            lvl, txt = htm_write(features, name_well, filename, enc, lname)
            if not lvl: return Qgis.Warning, txt, "Ошибка"
        if dialog.is_graph():
            feats = create_graph(features, name_well, enc)
            attr = [
                    QgsField("dist",QVariant.Double),
                    QgsField("well_beg",QVariant.String),
                    QgsField("well_end",QVariant.String)
                   ]
            graph_vlayer = maplayer(feats, "graph", attr, "LineString")
            graph_vlayer.loadNamedStyle(
                  os.path.dirname(__file__) + '/legstyle/graph_line.qml')
            txt += "\nГраф помещен  в слой graph."
    else: txt = "Отмена."
    del dialog
    return Qgis.Success, txt, "Завершено"
