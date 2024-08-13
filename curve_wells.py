# -*- coding: utf-8 -*-

import os
import math

from qgis.PyQt import uic
from qgis.PyQt import QtWidgets
from qgis.PyQt.QtWidgets import QAction, QFileDialog, QMessageBox
from qgis.PyQt.QtCore import QVariant

from qgis.core import (QgsProject,
                       Qgis,
                       QgsVectorLayer,
                       QgsField,
                       QgsGeometry,
                       QgsFeature,
                       QgsFieldProxyModel,
                       QgsMapLayerProxyModel,
                       QgsPointXY,
                       QgsPoint,
                       QgsFeatureRequest)
from .pie_dial import formCurveWells

from .utilib import *
#-----------------------------------------------------------------------------
# Класс описывающий скважину на разрезе. Название скважины, расстояние от
# начала линии разреза, геометрию отрезка разреза до и после скважины, точки
# по глубине.
# ----------------------------------------------------------------------------
class pointDepthwell ():
    def __init__(self, feature, fields, dircsv):
        self.feat_well = feature
        self.name_field, self.alt_field, self.file_field = fields
        self.csv_path = os.path.join(dircsv, feature[self.file_field])

        self.msgBox = QMessageBox()
        self.points_depth = self.well_point_dept()
        self.name_well = feature[self.name_field]

        self.dist_begin = 0
        self.pr_line = QgsGeometry()
        self.nx_line = QgsGeometry()
        self.vertex = QgsGeometry()

    # Расчет координат точек интервалов глубины
    def well_point_dept (self):

        x = self.feat_well.geometry().asPoint().x()
        y = self.feat_well.geometry().asPoint().y()

        # Чтение файла
        try:
            with open (self.csv_path, 'r') as csvfile:
                points_depth = [tuple([x, y, self.feat_well[self.alt_field]])]
                prev_depth = 0
                for line in csvfile:
                    records = line.split(";")
                    depth = int(records[0].strip())
                    zenit = float(records[1].strip().replace(',','.'))
                    azimut = float(records[2].strip().replace(',','.'))

                    interval = depth - prev_depth

                    z_radn = math.radians(zenit)
                    a_radn = math.radians(azimut)
                    lz = math.tan(z_radn)*interval
                    dx = math.sin(a_radn)*lz
                    dy = math.cos(a_radn)*lz

                    x = x+dx
                    y = y+dy

                    points_depth.append(tuple([x, y,
                                              self.feat_well[self.alt_field]-depth
                                              ])
                                       )

                    prev_depth = depth

        except FileNotFoundError:
            self.msgBox.setWindowTitle("Сообщение")
            self.msgBox.setText("Файл указанный в атрибутах не найден.")
            self.msgBox.exec()
        except Exception as e:
            self.msgBox.setWindowTitle("Сообщение")
            self.msgBox.setText("Ошибка.")
            self.msgBox.setInformativeText(str(e))
            self.msgBox.exec()

        return points_depth

    def add_begin (self, dist):
        self.dist_begin = dist

    def add_geomsection (self, prv, cur, nxt):
        self.pr_line = QgsGeometry.fromPolylineXY([QgsPointXY(prv),
                                                   QgsPointXY(cur)])
        self.nx_line = QgsGeometry.fromPolylineXY([QgsPointXY(cur),
                                                   QgsPointXY(nxt)])
        self.vertex = QgsGeometry.fromPointXY(cur)

    # Подготовка геометрии и атрибутов линий скважин в пространстве
    def depth_asline (self):
        points = []
        for point in self.points_depth:
            x, y, z = point
            point = QgsPoint(x, y, z)
            points.append(point)

        geom = QgsGeometry.fromPolyline(points)
        attr = [self.name_well, z]

        return geom, attr

    # Подготовка геометрии и атрибутов точек на плоскости
    def depth_asPointXY (self):
        points = []
        for point in self.points_depth:
            x, y, z = point
            point = QgsPointXY(x, y)

            points.append(tuple([QgsGeometry.fromPointXY(point),
                                 [self.name_well, z]
                                ])
                         )
        return points

    # Подготовка геометрии и атрибутов точек по глубине
    def depth_asPoint (self):
        points = []
        for point in self.points_depth:
            x, y, z = point
            point = QgsPoint(x, y, z)

            points.append(tuple([QgsGeometry.fromPoint(point),
                                 [self.name_well, z]
                                ])
                         )
        return points

    # Линия скважины на разрезе
    def get_sectionLine (self, scale=1):
        sect_points = []
        for point in self.points_depth:
            x, y, z = point
            point = QgsPointXY(x, y)
            point_geom = QgsGeometry.fromPointXY(point)
            pr_near = self.pr_line.nearestPoint(point_geom)
            nx_near = self.nx_line.nearestPoint(point_geom)

            pr_dist = pr_near.distance(point_geom)
            nx_dist = nx_near.distance(point_geom)

            if pr_dist < nx_dist:
                x_sect =  self.dist_begin - pr_near.distance(self.vertex)
            else:
                x_sect  = self.dist_begin + nx_near.distance(self.vertex)

            sect_points.append(QgsPointXY(x_sect, z*scale))

        geom = QgsGeometry.fromPolylineXY(sect_points)
        attr = [self.name_well, z]

        return geom, attr
#-----------------------------------------------------------------------------
#     pointDepthwell (feature, fields, csvdir)
#-----------------------------------------------------------------------------

#-----------------------------------------------------------------------------
# Класс линий профиля рельефа.
# Профиль рельефа строиться по srtm и по изолиниям
#-----------------------------------------------------------------------------
class profilSectionline ():
    def __init__(self, feature):
        self.geom_cutline = feature.geometry()
        # Расчитать шаг из длины линии разреза
        self.step_point = self.geom_cutline.length() // 100
        self.section_points = []

    def add_srtm(self, srtm):
        # Уплотнение линии точками
        densify_line = self.geom_cutline.densifyByDistance(self.step_point)
        # Получение списка вершин уплотненной линии разреза
        vertexs = densify_line.asPolyline()
        # Получение координат вершин уплотненной линии разреза и
        # расстояний от начала до каждой из вершин
        #profile_points = list()
        alt_list = list()
        for i, vertx in enumerate(vertexs) :
            # Получение высоты с растра strm (координата Y профиля)
            point_outcrop = QgsPointXY(densify_line.vertexAt(i))
            sec_y = srtm.sample(point_outcrop,1)[0]
            alt_list.append(sec_y)
            # Получение расстояний от начала линии разреза
            # до текущей точки (координата X профиля)
            sec_x = densify_line.distanceToVertex(i)
            # Накопление списка точек профиля
            self.section_points.append((sec_x, sec_y))

    def get_srtm_geom (self, scale=1):
        points = []
        for point in self.section_points:
            x,y = point
            points.append(QgsPointXY(x, y*scale))
        # Создание геометрии линии профиля
        profile_line = QgsGeometry.fromPolylineXY(points)
        # Упрощение линии профиля
        simplify_profile_line = profile_line.simplify(5)
        # Сглаживание линии профиля
        smooth_profile_line = simplify_profile_line.smooth(5, 0.4, 1, 180)
        # Упрощение линии профиля после сглаживания (удаление лишних точек)
        simplify_profile_line = smooth_profile_line.simplify(0.5)

        return simplify_profile_line

#-----------------------------------------------------------------------------
#     profilSectionline
#-----------------------------------------------------------------------------

#-----------------------------------------------------------------------------
# Класс линии разреза. Мега большой класс с информацией по каждой линии
# разреза. Рельеф, пересечения рек и возрастов. Скважины массив объектов
# pointDepthwell.
#-----------------------------------------------------------------------------
class geoSectionline ():
    def __init__(self, feature):
        self.feat_cutline = feature
        self.Id = feature.id()
        self.length = feature.geometry().length()
        self.depth_wells = []
        self.srtm_profil = profilSectionline(feature)

    def add_depthwells (self, layer_wells, fields):
        csvdir = os.path.dirname(layer_wells.source())
        cut_geom = self.feat_cutline.geometry()

        request = QgsFeatureRequest()
        request.setDistanceWithin(cut_geom, 1)

        for fet_req in layer_wells.getFeatures(request):
            vertx_geom, icur, iprv, inxt, sqr_dist = \
                 cut_geom.closestVertex(fet_req.geometry().asPoint())

            well_depth = pointDepthwell(fet_req, fields, csvdir)
            well_depth.add_begin(cut_geom.distanceToVertex(icur))
            well_depth.add_geomsection(
                                       cut_geom.vertexAt(iprv),
                                       vertx_geom,
                                       cut_geom.vertexAt(inxt)
            )
            self.depth_wells.append(well_depth)

        return self.depth_wells

#-----------------------------------------------------------------------------
#    geoSectionline
#-----------------------------------------------------------------------------

def cut_curvwell():

    curvwells_dialog = formCurveWells()
    result = curvwells_dialog.run()
    if result:
        attr = [QgsField("name",QVariant.String),
                QgsField("depth",QVariant.Int)
               ]

        cut_lines = []
        wlayer = curvwells_dialog.get_layerwells()
        wfields = curvwells_dialog.get_fieldwells()
        srtm = curvwells_dialog.get_strm()

        scale = 0.1

        for cfeat in  curvwells_dialog.get_featcut():
            cline = geoSectionline(cfeat)
            cline.add_depthwells(wlayer, wfields)
            cline.srtm_profil.add_srtm(srtm)
            cut_lines.append(cline)

        for cut in cut_lines:
            g = cut.srtm_profil.get_srtm_geom(scale)
            a = [f"{cut.Id}", cut.length]
            feat = [(g,a)]
            maplayer(feat, f"cut_line-{cut.Id}", attr, "LineString")
            feature = []
            for well in cut.depth_wells:
                g,a = well.get_sectionLine(scale)
                feature.append((g,a))
            maplayer(feature, "wells_line", attr, "LineString")
        txt = "Результат в cut_line."
    else: txt = "Отмена."
    del curvwells_dialog
    return Qgis.Success, txt, "Завершено"
