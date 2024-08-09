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
def csv_write (features, wname, filename, enc) :
    try:
        with open(filename, 'w') as output_file:
            line = 'csv'
            for feature in features:
                # добавить кодировку
                line = line + ';' + enc.get_str(f"{feature[wname]}")
            line = line + '\n'
            output_file.write(line)

            for i, feature in enumerate(features):
                line = enc.get_str(f"{feature[wname]}")
                geom = feature.geometry()
                for j, feature_out in enumerate(features):
                    if i == j :
                        line = line + ';'
                    else :
                        geom_out = feature_out.geometry()
                        dist = geom.distance(geom_out)
                        line = line + ';' + "{:8.3f}".format(dist)
                line = line + '\n'
                output_file.write(line)
            return True, f"Таблица CSV: {filename}"
    except UnicodeError:
        return False, "Ошибка выбора кодировки!"
    except FileNotFoundError:
        return False, "Файл не найден!"
    except Exception as e:
        return False, f"Ошибка: {e}"

#-----------------------------------------------------------------------------
#    Запись результатов в вебфайл html
#    selField - выбранное поле с названиями объектов
#-----------------------------------------------------------------------------
def htm_write (features, wname, filename, enc) :
    try:
        cssname =  os.path.dirname(__file__) + '/css/style.css'
        with open(filename, 'w') as output_file, \
             open(cssname,'r') as css_file:
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

            for feature in features:
                # добавить кодировку
                line = line + '<th>' + \
                       enc.get_str(f"{feature[wname]}")\
                       + '</th>'
            line = line + '<tr>\n</thead>\n<tbody>\n'
            output_file.write(line)

            for i, feature in enumerate(features):
                line = '<tr><th>' + \
                       enc.get_str(f"{feature[wname]}") \
                       + '</th>'
                geom = feature.geometry()
                for j, feature_out in enumerate(features):
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
            return True, f"Таблица CSV: {filename}"
    except UnicodeError:
        return False, "Ошибка выбора кодировки!"
    except FileNotFoundError:
        return False, "Файл не найден!"
    except Exception as e:
        return False, f"Ошибка: {e}"

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
#
#
#-----------------------------------------------------------------------------
def dist_well_table():
    disttab_dialog = formWellsMatrix()
    result = disttab_dialog.run()
    if result:
        features = disttab_dialog.get_featwells()
        name_well = disttab_dialog.get_namefield()
        filename = disttab_dialog.filename()
        enc = disttab_dialog.enc
        if filename[-3:] == "csv":
            lvl, txt = csv_write(features, name_well, filename, enc)
            if not lvl: return Qgis.Critical, txt
        else:
            lvl, txt = htm_write(features, name_well, filename, enc)
            if not lvl: return Qgis.Critical, txt
        if disttab_dialog.is_graph():
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
    del disttab_dialog
    return Qgis.Info, txt
