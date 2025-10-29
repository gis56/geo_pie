import os
import math

from qgis.PyQt.QtCore import QVariant

from qgis.core import (
                        Qgis,
                        QgsField,
                        QgsGeometry,
                        QgsFeature,
                        QgsEllipse,
                        QgsPointXY,
                        NULL
                      )
from .pie_dial import formZonezso
from .utilib import *

#-----------------------------------------------------------------------------
#
#
#-----------------------------------------------------------------------------
def zsozone():
    dialog = formZonezso()
    result = dialog.run()
    if result:
        features = dialog.getfeatures()
        chlist = dialog.checklist
        azimut = dialog.getazimut()

        feats_zone = []
        feats_arr = []
        warn_txt = ''
        for feat in features:
            center = feat.geometry().asPoint()
            if chlist[2]:
                radiuss = (feat['r_n3'], feat['r_s3'],
                           feat['r_w3'], feat['r_o3'])
                if (NULL in radiuss) or (0 in radiuss):
                    warn_txt += f"\nРадиусы третьей зоны для {feat['name']}\
                        не указаны."
                else:
                    zone = draw_ellipse(center, radiuss, azimut)
                    attr_zone = [feat['name'],'R3']
                    feats_zone.append((zone, attr_zone))
                    arrow = draw_arrow(center, radiuss, azimut, feat['name'],3)
                    feats_arr.extend(arrow)
            if chlist[1]:
                radiuss = (feat['r_n2'], feat['r_s2'],
                           feat['r_w2'], feat['r_o2'])
                if (NULL in radiuss) or (0 in radiuss):
                    warn_txt += f"\nРадиусы второй зоны для {feat['name']}\
                        не указаны."
                else:
                    zone = draw_ellipse(center, radiuss, azimut)
                    attr_zone = [feat['name'],'R2']
                    feats_zone.append((zone, attr_zone))
                    arrow = draw_arrow(center, radiuss, azimut, feat['name'],2)
                    feats_arr.extend(arrow)
            if chlist[0]:
                r = feat['r1']
                if (r == NULL) or (r == 0):
                    warn_txt += f"\nРадиус первой зоны для {feat['name']}\
                        не указан."
                else:
                    zone = draw_qudrat(center, r, azimut)
                    attr_zone = [feat['name'],'r1']
                    feats_zone.append((zone, attr_zone))
                    arrow = draw_arrow(center,(r,r,r,r),azimut,feat['name'],1)
                    feats_arr.extend(arrow)

        path = os.path.dirname(__file__)
        fields = [QgsField("well", QVariant.String),
                  QgsField("nameradius", QVariant.String)
                 ]
        group = creategroup("zso")
        vlayer = maplayer(feats_zone, "zone_zso", fields, "Polygon", False)
        vlayer.loadNamedStyle(f'{path}/legstyle/zso.qml')
        group.addLayer(vlayer)

        fields = [QgsField("well", QVariant.String),
                  QgsField("nameradius", QVariant.String),
                  QgsField("radius", QVariant.Int)
                 ]
        vlayer = maplayer(feats_arr, "arrow_zone", fields, "LineString", False)
        vlayer.loadNamedStyle(f'{path}/legstyle/zso_arrow.qml')
        group.addLayer(vlayer)
        txt = "Результат в группе zso." + warn_txt
    else: txt = "Отмена."
    del dialog
    return Qgis.Success, txt, "Завершено"

#-----------------------------------------------------------------------------
#   Геометрия первой зоны ЗСО
#   (квадрат)
#-----------------------------------------------------------------------------
def draw_qudrat (center, radius, azimut):
    # Координаты центра эллипса
    cx = center.x()
    cy = center.y()
    # Геометрия точки углов квадрата
    pntNO = QgsPointXY(cx+radius,cy+radius)
    pntNW = QgsPointXY(cx-radius,cy+radius)
    pntSW = QgsPointXY(cx-radius,cy-radius)
    pntSO = QgsPointXY(cx+radius,cy-radius)
    # Геометрия квадрата
    geom = QgsGeometry.fromPolygonXY([[pntNO,pntNW,pntSW,pntSO]])
    geom.rotate(azimut, center)
    return geom

#-----------------------------------------------------------------------------
# Отрисовка эллипса
# center - центр эллипса QgsPoint()
# R - радиус в положительном направлении оси X (после поворота на Север)
# D - в положительном направлении оси Y (Восток)
# r - в отрицательном направлении оси X (Юг)
# d - в отрицательном направлении оси Y (Запад)
#-----------------------------------------------------------------------------
def draw_ellipse (center, radiuss, azimut):
    # Построение дуги по параметрическому уровнению эллипса
    def arc_draw (radius_begin, radius_end, angle_range):
        arcpoints = []
        for angle in angle_range:
            angle_radian = math.radians(angle)
            arc_x = radius_begin*math.cos(angle_radian)+center_x
            arc_y = radius_end*math.sin(angle_radian)+center_y
            arcpoints.append(QgsPointXY(arc_x,arc_y))
        return arcpoints

    # Координаты центра эллипса
    center_x = center.x()
    center_y = center.y()
    n, s, w, o = radiuss
    # Список точек конечного эллипса
    ellipse_list = []
    ellipse_list.extend(arc_draw(n,o,range(-90,0)))
    ellipse_list.extend(arc_draw(n,w,range(0,90)))
    ellipse_list.extend(arc_draw(s,w,range(90,180)))
    ellipse_list.extend(arc_draw(s,o,range(180,270)))

    ellipse_list.append(ellipse_list[0])
    # Геометрия эллипса
    ellipse_geom = QgsGeometry.fromPolygonXY([ellipse_list])
    ellipse_geom.rotate(azimut, center)

    return ellipse_geom

#-----------------------------------------------------------------------------
#   Геометрия и атрибуты стрелок
#-----------------------------------------------------------------------------
def draw_arrow (center, radiuss, azimut, wname, num):
    n, s, w, o = radiuss
    x = center.x()
    y = center.y()
    rtxt = 'R'
    if num == 1: rtxt = "r"
    feats = []
    geom = QgsGeometry.fromPolylineXY([center, QgsPointXY(x+n, y)])
    geom.rotate(azimut, center)
    attr = [wname, f"{rtxt}_n{num}", n]
    feats.append((geom, attr))

    geom = QgsGeometry.fromPolylineXY([center, QgsPointXY(x, y+w)])
    geom.rotate(azimut, center)
    attr = [wname, f"{rtxt}_w{num}", w]
    feats.append((geom, attr))

    geom = QgsGeometry.fromPolylineXY([center, QgsPointXY(x-s, y)])
    geom.rotate(azimut, center)
    attr = [wname, f"{rtxt}_s{num}", s]
    feats.append((geom, attr))

    geom = QgsGeometry.fromPolylineXY([center, QgsPointXY(x, y-o)])
    geom.rotate(azimut, center)
    attr = [wname, f"{rtxt}_o{num}", o]
    feats.append((geom, attr))

    return feats
