# -*- coding: utf-8 -*-

import os
import math
import re

from qgis.PyQt import uic
from qgis.PyQt import QtWidgets
from qgis.PyQt.QtWidgets import QAction, QFileDialog, QMessageBox
from qgis.PyQt.QtCore import QVariant

from qgis.core import (
                       QgsProject,
                       Qgis,
                       QgsVectorLayer,
                       QgsField,
                       QgsGeometry,
                       QgsFeature,
                       QgsFieldProxyModel,
                       QgsMapLayerProxyModel,
                       QgsPointXY,
                       QgsPoint,
                       QgsFeatureRequest,
                       QgsWkbTypes,
                       NULL
                      )
from .pie_dial import formCurveWells

from .utilib import *

#-----------------------------------------------------------------------------
# Класс который будет родительским классом для классов описывающих
# объекты на разрезе. В нем будут общие методы для этих классов
# например: процедура пересечения линий
# ----------------------------------------------------------------------------
class objCutline ():
    def cut_intersect_ln (self, geom_cutline, lines_layer, field):
        cutpoints = []
        x_beg = 0
        sectvert_iter = geom_cutline.vertices()
        sectvert_beg = next(sectvert_iter)
        for sectvert_end in sectvert_iter:
            interval_geom = QgsGeometry.fromPolyline([sectvert_beg,
                                                      sectvert_end])
            # определение области отрезка и запрос на пересечение
            rectbox = interval_geom.boundingBox()
            request = QgsFeatureRequest().setFilterRect(rectbox).setFlags(
                                             QgsFeatureRequest.ExactIntersect)
            # Перебор изолиний пересакающих область текущего отрезка
            for featline in lines_layer.getFeatures(request):
                featline_geom = featline.geometry()
                intersect_geom = featline_geom.intersection(interval_geom)

                if not intersect_geom.isEmpty():
                    for  part_geom in intersect_geom.asGeometryCollection() :
                        dist = part_geom.distance(
                                          QgsGeometry.fromPoint(sectvert_beg)
                                         )
                        cutpoints.append((x_beg+dist, featline[field]))
            # Наращивание расстояние от начала линии разреза
            x_beg += interval_geom.length()
            sectvert_beg = sectvert_end

        return  sorted(cutpoints, key=lambda x: x[0])

    #-------------------------------------------------------------------------
    # Пересечение линии разреза с полигонами
    # ------------------------------------------------------------------------
    def cut_intersect_plg (self, geom_cutline, polygons_layer, field):
        cutpoints = []
        x_beg = 0
        sectvert_iter = geom_cutline.vertices()
        sectvert_beg = next(sectvert_iter)
        for sectvert_end in sectvert_iter:
            interval_geom = QgsGeometry.fromPolyline([sectvert_beg,
                                                      sectvert_end])
            # определение области отрезка и запрос на пересечение
            rectbox = interval_geom.boundingBox()
            request = QgsFeatureRequest().setFilterRect(rectbox).setFlags(
                                             QgsFeatureRequest.ExactIntersect)
            # Перебор изолиний пересакающих область текущего отрезка
            for feat in polygons_layer.getFeatures(request):
                feat_geom = feat.geometry()
                intersect_geom = feat_geom.intersection(interval_geom)

                if not intersect_geom.isEmpty():
                    for  part_geom in intersect_geom.asGeometryCollection():
                        v1 = part_geom.vertexAt(0)
                        v2 = part_geom.vertexAt(1)
                        x1 = v1.distance(sectvert_beg)+x_beg
                        x2 = v2.distance(sectvert_beg)+x_beg
                        if x1 > x2: x1, x2 = x2, x1
                        cutpoints.append((x1, x2, feat[field]))
            # Наращивание расстояние от начала линии разреза
            x_beg += interval_geom.length()
            sectvert_beg = sectvert_end

        return  sorted(cutpoints, key=lambda x: x[0])

    #-------------------------------------------------------------------------
    # Объединение соседних полигонов с одинаковым признаком
    #-------------------------------------------------------------------------
    def union_intersect (self, data_list):

        index = 0
        while index < len(data_list)-1:
            x1, x2, name = data_list[index]
            n1, n2, next_name = data_list[index+1]
            if name == next_name:
                data_list[index+1] = (x1, n2, name)
                data_list.pop(index)
            index += 1

        return data_list

    # ------------------------------------------------------------------------
    # Определение типа слоя и типа поля атрибутов
    # ------------------------------------------------------------------------
    def type_field (self, layer, field):
        field_num = layer.fields().field(field).type()
        lname = layer.name()
        if field_num == 10: return QVariant.String, field, lname
        if field_num == 2 or field_num == 4: return QVariant.Int, field, lname

# ----------------------------------------------------------------------------
# Класс робительский для классов описывающих скважины по глубине:
# фильтры, возроста, литология
# ----------------------------------------------------------------------------
class objDepth ():
    #-------------------------------------------------------------------------
    # поиск координат пересечения отрезков
    # по координатам концов отрезков
    #-------------------------------------------------------------------------
    def my_intersect (self, p1b, p1e, p2b, p2e):
        x1b, y1b = p1b #x1 y1
        x1e, y1e = p1e #x2 y2
        x2b, y2b = p2b #x3 y3
        x2e, y2e = p2e #x4 y4

        def vm (ax, ay, bx, by):
            return ax*by-bx*ay

        def lc (x1b, y1b, x1e, y1e, x2b, y2b, x2e, y2e):
            v1 = vm(x2e-x2b, y2e-y2b, x1b-x2b, y1b-y2b)
            v2 = vm(x2e-x2b ,y2e-y2b, x1e-x2b, y1e-y2b)
            v3 = vm(x1e-x1b, y1e-y1b, x2b-x1b, y2b-y1b)
            v4 = vm(x1e-x1b, y1e-y1b, x2e-x1b, y2e-y1b)

            if (v1*v2<0) and (v3*v4<0): return True
            else: return False

        def funct(xb, yb, xe, ye):
            a = ye-yb
            b = xb-xe
            c = -xb*(ye-yb)+yb*(xe-xb)
            return a, b, c

        def point_intersect (a1, b1, c1, a2, b2, c2):
            d = a1*b2-b1*a2
            if lc(x1b, y1b, x1e, y1e, x2b, y2b, x2e, y2e):
                dx = -c1*b2+b1*c2
                dy = -a1*c2+c1*a2
                x = dx/d
                y = dy/d
                return x, y
            else: return False

        f1 = funct(x1b, y1b, x1e, y1e)
        f2 = funct(x2b, y2b, x2e, y2e)

        return point_intersect (*f1, *f2)

#-----------------------------------------------------------------------------
# Класс описывающий скважину на разрезе. Название скважины, расстояние от
# начала линии разреза, геометрию отрезка разреза до и после скважины, точки
# по глубине.
# ----------------------------------------------------------------------------
class GpWell ():
    def __init__(self, point, depthlist, alt, wname, filters, gtr, data_sect):
        self.name_well = wname
        self.alt = alt
        self.x, self.y = point
        self.depthlist = depthlist
        self.set_interval(*data_sect)
        self.points_depth, self.sect_points = self.well_point_dept()
        if not (filters == NULL): self.filters = self.add_filters(filters)
        else: self.filters = False
        if gtr: self.gtr = self.add_gtr(gtr)
        else: self.gtr = False

    #-------------------------------------------------------------------------
    # создание геометрии отрезков линии разреза до и после скважины
    # и получение расстояния от начала линии разреза до скважины
    # из данных полученных при создании объекта
    #-------------------------------------------------------------------------
    def set_interval (self, prv, cur, nxt, dist):
        self.pr_line = QgsGeometry.fromPolylineXY([QgsPointXY(prv),
                                                   QgsPointXY(cur)])
        self.nx_line = QgsGeometry.fromPolylineXY([QgsPointXY(cur),
                                                   QgsPointXY(nxt)])
        self.vertex = QgsGeometry.fromPointXY(cur)
        self.dist_begin = dist

    #-------------------------------------------------------------------------
    # Расчет координат точек каждого интервала глубины,
    # занесение в массив для дальнейшего отображения на карте
    # на плоскости или в пространстве в виде точек или линии
    # Массив кортежей координат
    # ------------------------------------------------------------------------
    def well_point_dept (self):
        # поиск координат на карте для кождой точки глубины
        # запись кортежа из трех координат в массив
        points_depth = [(self.x, self.y, self.alt)]
        sect_points = []
        prev_depth = 0
        x,y = self.x, self.y
        for record in self.depthlist:
            depth, zenit, azimut = record
            interval = depth - prev_depth
            z_radn = math.radians(zenit)
            a_radn = math.radians(azimut)
            lz = math.tan(z_radn)*interval
            x += math.sin(a_radn)*lz
            y += math.cos(a_radn)*lz
            z = self.alt - depth
            points_depth.append((x, y, z))

            # поиск координат линии скважины на разрезе
            # запись кортежа координат в массив
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
            sect_points.append((x_sect, z))

            prev_depth = depth

        return points_depth, sect_points

    # добавление фильтров
    def add_filters (self, filters_str):
        try:
            filters = []
            for filter_string in  filters_str.split(":"):
                filters.append(GpFilter(
                                         filter_string,
                                         self.alt,
                                         self.name_well,
                                         self.sect_points
                                        )
                              )
            return filters
        except:
            return False

    # ------------------------------------------------------------------------
    # добавление данных из паспорта скважин
    # список списков объектов по каждому ключу
    # ------------------------------------------------------------------------
    def add_gtr (self, gtr_dict):
        obj_dict = {}
        for key, vals in gtr_dict.items():
            #obj_dict = {key}
            obj_values = []
            for tupl in vals:
                obj_values.append(
                                  GpGtr(
                                        tupl,
                                        self.name_well,
                                        self.sect_points
                                       )
                                 )
            obj_dict[key] = obj_values
        return obj_dict

    # Линия скважины на разрезе
    def get_sectionLine (self, scale=1):
        line = []
        for point in self.sect_points:
            x, yz = point
            line.append(QgsPointXY(x, yz*scale))
        geom = QgsGeometry.fromPolylineXY(line)
        lcode = self.filters
        if lcode: lcode = True
        attr = [self.name_well, yz, lcode]

        return geom, attr

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

            points.append((QgsGeometry.fromPointXY(point),
                           [self.name_well, z])
                         )
        return points

    # Подготовка геометрии и атрибутов точек по глубине
    def depth_asPoint (self):
        points = []
        for point in self.points_depth:
            x, y, z = point
            point = QgsPoint(x, y, z)

            points.append((QgsGeometry.fromPoint(point),
                           [self.name_well, z])
                         )
        return points
#-----------------------------------------------------------------------------
#     GpWell (feature, fields, csvdir)
#-----------------------------------------------------------------------------

#-----------------------------------------------------------------------------
# Класс содержащий информацию
# о фильтрах скважин
#-----------------------------------------------------------------------------
class GpFilter ():
    def __init__(self, filter_string, alt, name_well, well_pnts):
        self.filters_pnt, self.l_code = self.set_filter(
                                                         filter_string,
                                                         alt,
                                                         well_pnts
                                                        )
        self.name_well = name_well

    #-------------------------------------------------------------------------
    # создает массив точек линии фильтра при инициализации
    # объекта фильтра
    #-------------------------------------------------------------------------
    def set_filter(self, filter_string, alt, well_pnts):
        records = filter_string.split(";")
        y_begin = alt - float(records[0].strip().replace(',','.'))
        y_end = alt - float(records[1].strip().replace(',','.'))
        l_code = int(records[2].strip())

        filter_pnts = []
        index = 0
        x,y = well_pnts[index]
        while index < len(well_pnts) and y >= y_end:
            x,y = well_pnts[index]
            if y <= y_begin:
                filter_pnts.append(well_pnts[index])
            else: point_top = well_pnts[index]
            index += 1
        if index < len(well_pnts): point_bottom = well_pnts[index]
        else: point_bottom = well_pnts[index-1]

        xt, yt = point_top
        xs, ys = filter_pnts[0]
        xb, yb = point_bottom
        xe, ye = filter_pnts[-1]

        if not y_begin == ys:
            if xs == xt: filter_pnts.insert(0, (xs, y_begin))
            else:
                ip = self.my_intersect(
                                        point_top, filter_pnts[0],
                                        (xt,y_begin),(xs,y_begin)
                                       )

                if ip: filter_pnts.insert(0, ip)

        if not y_end == ye:
            if xe == xb: filter_pnts.append((xe, y_end))
            else:
                ip = self.my_intersect(
                                       filter_pnts[-1], point_bottom,
                                       (xb, y_end), (xe, y_end)
                                      )
                if ip: filter_pnts.append(ip)

        return filter_pnts, l_code

    #-------------------------------------------------------------------------
    # поиск координат пересечения отрезков
    # по координатам концов отрезков
    #-------------------------------------------------------------------------
    def my_intersect (self, p1b, p1e, p2b, p2e):
        x1b, y1b = p1b #x1 y1
        x1e, y1e = p1e #x2 y2
        x2b, y2b = p2b #x3 y3
        x2e, y2e = p2e #x4 y4

        def vm (ax, ay, bx, by):
            return ax*by-bx*ay

        def lc (x1b, y1b, x1e, y1e, x2b, y2b, x2e, y2e):
            v1 = vm(x2e-x2b, y2e-y2b, x1b-x2b, y1b-y2b)
            v2 = vm(x2e-x2b ,y2e-y2b, x1e-x2b, y1e-y2b)
            v3 = vm(x1e-x1b, y1e-y1b, x2b-x1b, y2b-y1b)
            v4 = vm(x1e-x1b, y1e-y1b, x2e-x1b, y2e-y1b)

            if (v1*v2<0) and (v3*v4<0): return True
            else: return False

        def funct(xb, yb, xe, ye):
            a = ye-yb
            b = xb-xe
            c = -xb*(ye-yb)+yb*(xe-xb)
            return a, b, c

        def point_intersect (a1, b1, c1, a2, b2, c2):
            d = a1*b2-b1*a2
            if lc(x1b, y1b, x1e, y1e, x2b, y2b, x2e, y2e):
                dx = -c1*b2+b1*c2
                dy = -a1*c2+c1*a2
                x = dx/d
                y = dy/d
                return x, y
            else: return False

        f1 = funct(x1b, y1b, x1e, y1e)
        f2 = funct(x2b, y2b, x2e, y2e)

        return point_intersect (*f1, *f2)

    def get_filter(self, scale):

        if self.filters_pnt:
            line = []
            for point in self.filters_pnt:
                x, y = point
                line.append(QgsPointXY(x, y*scale))
            geom = QgsGeometry.fromPolylineXY(line)
            attr = [self.name_well, self.l_code]

            return geom, attr

#-----------------------------------------------------------------------------
#     GpFilter
#-----------------------------------------------------------------------------

# ----------------------------------------------------------------------------
# Класс GpGtr
# ----------------------------------------------------------------------------
class GpGtr (objDepth):
    def __init__(self, tupl, name_well, well_pnts):
        self.filters_pnt, self.l_code = self.set_gtr(
                                                     tupl,
                                                     well_pnts
                                                    )
        self.name_well = name_well

    #-------------------------------------------------------------------------
    # создает массив точек линии фильтра при инициализации
    # объекта фильтра
    #-------------------------------------------------------------------------
    def set_gtr(self, tupl, well_pnts):
        y_begin, y_end, l_code = tupl
        filter_pnts = []
        index = 0
        x,y = well_pnts[index]
        """
        msgBox = QMessageBox()
        msgBox.setText(f"{y}<={y_begin}, {y_end}, {l_code}")
        msgBox.exec()
        """
        # !!!! проверить список well_pnts
        # начинается не с первой точки а со второй (на 10 метров ниже)!!!!
        while index < len(well_pnts) and y >= y_end:
            x,y = well_pnts[index]
            if y <= y_begin:
                filter_pnts.append(well_pnts[index])
            else: point_top = well_pnts[index]
            index += 1
        if index < len(well_pnts): point_bottom = well_pnts[index]
        else: point_bottom = well_pnts[index-1]

        xt, yt = point_top
        xs, ys = filter_pnts[0]
        xb, yb = point_bottom
        xe, ye = filter_pnts[-1]

        if not y_begin == ys:
            if xs == xt: filter_pnts.insert(0, (xs, y_begin))
            else:
                ip = self.my_intersect(
                                        point_top, filter_pnts[0],
                                        (xt,y_begin),(xs,y_begin)
                                       )

                if ip: filter_pnts.insert(0, ip)

        if not y_end == ye:
            if xe == xb: filter_pnts.append((xe, y_end))
            else:
                ip = self.my_intersect(
                                       filter_pnts[-1], point_bottom,
                                       (xb, y_end), (xe, y_end)
                                      )
                if ip: filter_pnts.append(ip)

        return filter_pnts, l_code

    def get_gtr(self, scale):

        if self.filters_pnt:
            line = []
            for point in self.filters_pnt:
                x, y = point
                line.append(QgsPointXY(x, y*scale))
            geom = QgsGeometry.fromPolylineXY(line)
            attr = [self.name_well, self.l_code]

            return geom, attr

#-----------------------------------------------------------------------------
# Класс линий профиля рельефа.
# Профиль рельефа строиться по srtm и по изолиниям
#-----------------------------------------------------------------------------
class GpProfiles (objCutline):
    def __init__(self, feature, izln, srtm):
        self.geom_cutline = feature.geometry()
        self.ID = feature.id()
        self.sect_length = self.geom_cutline.length()
        # Расчитать шаг из длины линии разреза
        self.step_point = self.geom_cutline.length() // 100

        self.alt_extrem = []
        if srtm: self.sectpnt_srtm = self.add_srtm(srtm)
        else: self.sectpnt_srtm = False
        self.sectpnt_izln = self.add_izln(izln)

    def add_izln(self, izline):
        verts = self.cut_intersect_ln(self.geom_cutline, *izline)
        izline_points = []
        for vert in verts:
            x, y = vert
            izline_points.append((float(x), float(y)))
        self.alt_extrem.extend([
                        min(izline_points, key=lambda y: y[1])[1],
                        max(izline_points, key=lambda y: y[1])[1]
                        ])

        return izline_points

    def add_srtm(self, srtm):
        # Уплотнение линии точками
        densify_line = self.geom_cutline.densifyByDistance(self.step_point)
        # Получение списка вершин уплотненной линии разреза
        vertexs = densify_line.asPolyline()
        # Получение координат вершин уплотненной линии разреза и
        # расстояний от начала до каждой из вершин
        alt_list = []
        srtm_points = []
        for i, vertx in enumerate(vertexs) :
            # Получение высоты с растра strm (координата Y профиля)
            point_outcrop = QgsPointXY(densify_line.vertexAt(i))
            sec_y = srtm.sample(point_outcrop,1)[0]
            alt_list.append(sec_y)
            # Получение расстояний от начала линии разреза
            # до текущей точки (координата X профиля)
            sec_x = densify_line.distanceToVertex(i)
            # Накопление списка точек профиля
            srtm_points.append((sec_x, sec_y))
        self.alt_extrem.extend([min(alt_list), max(alt_list)])

        return srtm_points

    def get_extreme (self):
        return min(self.alt_extrem), max(self.alt_extrem)

    def get_srtm_geom (self, scale=1):
        points = []
        for point in self.sectpnt_srtm:
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

    def get_izln_geom (self, scale=1):
        x,y = self.sectpnt_izln[0]
        points = [QgsPointXY(0, y*scale)]
        for point in self.sectpnt_izln:
            x,y = point
            points.append(QgsPointXY(x,y*scale))
        points.append(QgsPointXY(self.geom_cutline.length(), y*scale))

        return  QgsGeometry.fromPolylineXY(points)

    #-------------------------------------------------------------------------
    #   создание профилей разреза
    #   возможно нужно будет здесь попутно сохранить геометрии профилей
    #   в свойствах класса
    #-------------------------------------------------------------------------
    def get_profils (self, scale):
        profil_name = f"sect_{self.ID}"

        fields = [QgsField("name",QVariant.String),
                  QgsField("type",QVariant.String),
                  QgsField("sect_length", QVariant.Double),
                  QgsField("profil_length", QVariant.Double)]

        feats = []
        if self.sectpnt_srtm:
            geom = self.get_srtm_geom(scale)
            attr = [profil_name, "srtm", self.sect_length, geom.length()]
            feats.append((geom,attr))
        if self.sectpnt_izln:
            geom = self.get_izln_geom(scale)
            attr = [profil_name, "izln", self.sect_length, geom.length()]
            feats.append((geom, attr))
        else: return False

        return feats, f"profil-{profil_name}", fields, "LineString", False
#-----------------------------------------------------------------------------
#     GpProfiles
#-----------------------------------------------------------------------------

#-----------------------------------------------------------------------------
#     rulerSection
# Вычисление шкал
# на входе: максимум и минимум рельефа, глубина самой глубокой скважины на
# разрезе или глубина выбранная поьзователем, отношение
# масштаба карты к вертикальному масштабу
# длина разреза
# вычислить шаг шкалы, сколько метров в одном сантиметре карты для выбранного
# масштаба разреза.
# создать геометрии боковых шкал, нулевой линии (если она есть)
# подумать над созданием линии пересечения разоезов
#-----------------------------------------------------------------------------
class rulerSection (objCutline):
    #def __init__ (self, ID, length, alt_min, alt_max, cutscale, intersect):
    def __init__ (self, alt_min, alt_max, cutscale, feat_cutline, cuts_layer):
        #self.intersect = intersect
        self.intersect = self.intersect_lines(feat_cutline, cuts_layer)
        self.cm_step = cutscale * self.coef_unit()
        self.alt_min = math.floor(alt_min/self.cm_step)*self.cm_step
        self.alt_max = math.ceil(alt_max/self.cm_step)*self.cm_step
        self.length = feat_cutline.geometry().length()
        #self.length = length
        #self.name = ID
        self.name = feat_cutline.id()

    def coef_unit (self):
        unit = QgsProject.instance().crs().mapUnits()
        if unit == Qgis.DistanceUnit.Millimeters: return 10
        elif unit == Qgis.DistanceUnit.Centimeters: return 1
        elif unit == Qgis.DistanceUnit.Meters: return 0.01
        elif unit == Qgis.DistanceUnit.Kilometers: return 0.0001
        else: return -1

    def intersect_lines(self, feat_cutline, cuts_layer):
        geom_cut = feat_cutline.geometry()
        cuts_layer.startEditing()
        cuts_layer.deleteFeature(feat_cutline.id())
        intersect_pnt = self.cut_intersect_ln(geom_cut, cuts_layer,"id")
        cuts_layer.rollBack()

        return intersect_pnt

    def get_ruler(self, scale=1):
        # линии шкалы
        ln_feats = []
        # левая линейка
        # создать линейку из сатиметровых отрезков
        points = []
        dop = self.alt_min
        while dop <= self.alt_max:
            points.append(QgsPointXY(0,dop*scale))
            dop += self.cm_step
        #points = [QgsPointXY(0,self.alt_min*scale),
        #          QgsPointXY(0,self.alt_max*scale)]
        geom = QgsGeometry.fromPolylineXY(points)
        attr = ["ruler", "left"]
        ln_feats.append((geom, attr))
        # правая линейка
        points = []
        dop = self.alt_min
        while dop <= self.alt_max:
            points.append(QgsPointXY(self.length, dop*scale))
            dop += self.cm_step
        #points = [QgsPointXY(self.length, self.alt_min*scale),
        #          QgsPointXY(self.length, self.alt_max*scale)]
        geom = QgsGeometry.fromPolylineXY(points)
        attr = ["ruler", "right"]
        ln_feats.append((geom, attr))
        # нулевая линия (если есть)
        if self.alt_min < 0 and self.alt_max > 0:
            points = [QgsPointXY(0,0), QgsPointXY(self.length, 0)]
            geom = QgsGeometry.fromPolylineXY(points)
            attr = ["null", f"{self.name}"]
            ln_feats.append((geom, attr))
        # пересечение разрезов
        for intercut in self.intersect:
            x, ID = intercut
            points = [QgsPointXY(x, self.alt_min*scale),
                      QgsPointXY(x, self.alt_max*scale)]
            geom = QgsGeometry.fromPolylineXY(points)
            attr = ["intersect", f"{self.name} - {ID}"]
            ln_feats.append((geom, attr))
        # точки шкалы
        pnt_feats = []
        i = self.alt_min
        while i <= self.alt_max:
            point = QgsPointXY(0, i*scale)
            pnt_feats.append((QgsGeometry.fromPointXY(point),
                              ['left', i]))
            point = QgsPointXY(self.length, i*scale)
            pnt_feats.append((QgsGeometry.fromPointXY(point),
                              ['right', i]))
            i += self.cm_step

        ln_fields = [QgsField("type",QVariant.String),
                      QgsField("name", QVariant.String)]

        pnt_fields = [QgsField("type",QVariant.String),
                      QgsField("value", QVariant.Double)]

        return ((ln_feats, f"ruler_ln-{self.name}", ln_fields,
                 "LineString", False),
               (pnt_feats, f"ruler_pnt-{self.name}", pnt_fields,
                "Point", False))
#-----------------------------------------------------------------------------
#     rulerSection
#-----------------------------------------------------------------------------

#-----------------------------------------------------------------------------
#     GpAges - Класс пересечения возрастов с линией разреза
#-----------------------------------------------------------------------------
class GpAges(objCutline):
    def __init__ (self, feature, data, extrem):
        self.geom = feature.geometry()
        self.cutname = feature.id()
        self.lines = self.add(data)
        self.extrem = extrem
        self.ftype, self.fname, self.lname = self.type_field(*data)

    def add(self, data):
        inters = self.cut_intersect_plg(self.geom, *data)
        unions = self.union_intersect(inters)
        lines = []
        for line in unions:
            x1, x2, lcode = line
            lines.append((float(x1), float(x2), lcode))
        return lines

    def get(self, profil_geom, scale=1):

        if self.lines:
            feat = []
            for line in self.lines:
                x1, x2, lcode =line
                y1, y2 = self.extrem
                y1 -= (y2-y1)/3
                geom = QgsGeometry.fromPolygonXY([[
                                                  QgsPointXY(x1,y1*scale),
                                                  QgsPointXY(x1,y2*scale),
                                                  QgsPointXY(x2,y2*scale),
                                                  QgsPointXY(x2,y1*scale)
                                                 ]])
                geom.splitGeometry( profil_geom.asPolyline(), False)
                attr = [self.cutname, lcode]
                feat.append((geom, attr))

            fields = [
                      QgsField("idcut",QVariant.Int),
                      QgsField(self.fname, self.ftype)
                     ]

            return (feat,f"{self.lname}-{self.cutname}",fields,"Polygon",False)
        else: return False

#-----------------------------------------------------------------------------
#     GpRivers - Класс пересечения рек с линией разреза
#-----------------------------------------------------------------------------
class GpRivers(objCutline):
    def __init__(self, feature, rivers):
        self.geom = feature.geometry()
        self.cutname = feature.id()
        self.points = self.add(rivers)
        self.ftype, self.fname, self.lname = self.type_field(*rivers)

    def add(self, rivers):
        verts = self.cut_intersect_ln(self.geom, *rivers)
        points = []
        for vert in verts:
            x, name = vert
            points.append((float(x), name))
        return points

    def get(self, scale=1):
        if self.points:
            feat = []
            for point in self.points:
                x, name = point
                y = 0
                geom = QgsGeometry.fromPointXY(QgsPointXY(x,y*scale))
                attr = [self.cutname, name]
                feat.append((geom, attr))

            fields = [
                      QgsField("idcut",QVariant.Int),
                      QgsField(self.fname, self.ftype)
                     ]

             #QgsField("name", QVariant.String)
            return (feat, f"{self.lname}-{self.cutname}",fields,"Point",False)
        else: return False
#-----------------------------------------------------------------------------
# Класс линии разреза. Мега большой класс с информацией по каждой линии
# разреза. Рельеф, пересечения рек и возрастов. Скважины массив объектов
# GpWell.
#-----------------------------------------------------------------------------
class geoSectionline ():
    def __init__(self, feature):
        self.feat_cutline = feature
        self.Id = feature.id()
        self.length = feature.geometry().length()
        self.depth_wells = []
        # список глубин всех вынесенных на разрез скважин
        # для поиска наиболее глубокой и расчета минимального значения линейки
        self.well_depths = []
        self.ln_layer = []
        self.plg_layer = []

    #-------------------------------------------------------------------------
    #   добавление профилей разреза
    # ------------------------------------------------------------------------
    def add_profile(self, izln, srtm):

        # создание объекта профиля
        self.profiline = GpProfiles(self.feat_cutline, izln, srtm)

    #-------------------------------------------------------------------------
    # добавление линейки
    #-------------------------------------------------------------------------
    def add_ruler (self, cuts_layer, cutscale):
        min_alt, max_alt = self.profiline.get_extreme()
        min_depth = min(self.well_depths)
        if min_alt > min_depth:
            min_alt = min_depth

        # создание объекта линейки
        self.ruler = rulerSection(
                                  min_alt, max_alt, cutscale,
                                  self.feat_cutline, cuts_layer
                                 )
    """
    #-------------------------------------------------------------------------
    # добавление рек
    # ------------------------------------------------------------------------
    def add_rivers (self, rivers):
        if rivers:
            self.rivers = GpRivers(self.feat_cutline, rivers)

    #-------------------------------------------------------------------------
    # добавление возрастов
    # ------------------------------------------------------------------------
    def add_ages (self, ages):
        if ages:
            extrem = self.profiline.get_extreme()
            self.ages = GpAges(self.feat_cutline, ages, extrem)
    """
    #-------------------------------------------------------------------------
    # добавление слоев пересечения в массивы линий и полигонов
    #-------------------------------------------------------------------------
    def add_lnplg (self, lnplg):
        for data in lnplg:
            layer, field = data
            if layer.geometryType() == QgsWkbTypes.LineGeometry:
                self.ln_layer.append(GpRivers(self.feat_cutline, data))
            elif layer.geometryType() == QgsWkbTypes.PolygonGeometry:
                self.plg_layer.append(GpAges(
                                             self.feat_cutline,
                                             data,
                                             self.profiline.get_extreme()
                                             )
                                    )

    # ------------------------------------------------------------------------
    # чтение файла паспорта скважины
    # ------------------------------------------------------------------------
    def read_gtr (self, path, alt):
        try:
            #csv_path = os.path.join(csvdir, csv)
            with open (path, 'r') as gtr:
                gtr_dict = {}
                value = []
                err = ""
                for line in gtr:
                    name = re.match(r'^\[\D+\]', line)
                    if not name == None:
                        value = []
                        key = name.group(0)[1:-1].strip()
                        gtr_dict[key] = value
                    else:
                        records = line.split(";")
                        depth1 = float(records[0].strip().replace(',','.'))
                        depth2 = float(records[1].strip().replace(',','.'))
                        param = int(records[2].strip())
                        gtr_dict[key].append((alt-depth1, alt-depth2, param))

            gtr.close()
            return gtr_dict
        except FileNotFoundError:
            return f"{name}данные о глубине не число."
        except ValueError:
            return False
            #return f"{name} -  в данных о глубине не число."
        except Exception as e:
            return False #, f"gtr - {name} - {e}."
            #return f"gtr - {name} - {e}."

    #-------------------------------------------------------------------------
    # добавление скважин
    #-------------------------------------------------------------------------
    def add_depthwells (self, layer_wells, fields):
        """
        def addwell():
             # создание объекта скважины
             data_sect = (
                           cut_geom.vertexAt(iprv),
                           vertx_geom,
                           cut_geom.vertexAt(inxt),
                           cut_geom.distanceToVertex(icur)
                         )

             well_depth = GpWell(
                                  (x,y), depthlist,
                                  alt, wname,
                                  filters, gtr_dict, data_sect
                                )

             self.depth_wells.append(well_depth)
        """

        fname, falt, ffile, ffilters, fgtr = fields
        csvdir = os.path.dirname(layer_wells.source())
        cut_geom = self.feat_cutline.geometry()
        errlist = ""
        request = QgsFeatureRequest()
        request.setDistanceWithin(cut_geom, 1)

        for fet_req in layer_wells.getFeatures(request):
            vertx_geom, icur, iprv, inxt, sqr_dist = \
                 cut_geom.closestVertex(fet_req.geometry().asPoint())

            data_sect = (
                         cut_geom.vertexAt(iprv),
                         vertx_geom,
                         cut_geom.vertexAt(inxt),
                         cut_geom.distanceToVertex(icur)
                        )

            x = fet_req.geometry().asPoint().x()
            y = fet_req.geometry().asPoint().y()
            alt = fet_req[falt]

            csv = fet_req[ffile]
            wname = fet_req[fname]
            filters= fet_req[ffilters]

            # чтение gtr-файла
            gtr = fet_req[fgtr]
            if not gtr == NULL:
                gtr_path = os.path.join(csvdir, gtr)
                gtr_dict = self.read_gtr(gtr_path, alt)
            else: gtr_dict = False

            # пересмотреть условие с not и без continue
            if csv == NULL:
                errlist += f"\n{wname} - нет данных о глубине."
                continue
            # Чтение файла
            # вынести чтение файла глубин в отдельную функцию
            # и убрать из этой функции try except
            try:
                csv_path = os.path.join(csvdir, csv)
                with open (csv_path, 'r') as csvfile:
                    depthlist = []
                    for line in csvfile:
                        records = line.split(";")
                        depth = int(records[0].strip())
                        zenit = float(records[1].strip().replace(',','.'))
                        azimut = float(records[2].strip().replace(',','.'))
                        depthlist.append((depth,zenit,azimut))
                    self.well_depths.append(alt-depth)

                csvfile.close()

                self.depth_wells.append(
                                        GpWell(
                                               (x,y),
                                               depthlist,
                                               alt,
                                               wname,
                                               filters,
                                               gtr_dict,
                                               data_sect
                                              )
                                       )

                #addwell()

            except FileNotFoundError:
                try:
                    depth = float(csv.strip().replace(',','.'))
                    depthlist = [(depth,0,0)]
                    self.well_depths.append(alt-depth)
                    self.depth_wells.append(
                                            GpWell(
                                                   (x,y),
                                                   depthlist,
                                                   alt,
                                                   wname,
                                                   filters,
                                                   gtr_dict,
                                                   data_sect
                                                  )
                                           )
                    #addwell()
                except ValueError:
                    errlist += f"\n{wname} -  данные о глубине не число."
            except ValueError:
                errlist += f"\n{wname} -  в данных о глубине не число."
            except Exception as e:
                errlist += f"\n{wname} - {e}."

        return errlist

    #-------------------------------------------------------------------------
    # передача массива скважин в слой
    #-------------------------------------------------------------------------
    def get_wells (self, scale):
        # Поля атрибутов изогнутых скважин
        profil_name = self.Id
        fields = [QgsField("name",QVariant.String),
                  QgsField("depth",QVariant.Double),
                  QgsField("lcode", QVariant.Bool)]
        feats = []
        for well in self.depth_wells:
            geom, attr = well.get_sectionLine(scale)
            feats.append((geom, attr))

        return feats, f"wells-{profil_name}", fields, "LineString", False

    # ------------------------------------------------------------------------
    # Геометрия фильтров скважины
    # перенести вывод фильтров надо в класс разреза, потомучто один слой
    # на все фильтры всех скважин
    # добавить еще один цикл по скважинам
    # ------------------------------------------------------------------------
    def get_filters (self, scale):
        profil_name = self.Id
        fields = [QgsField("name",QVariant.String),
                  QgsField("lcode",QVariant.Int)]
        feads = []
        for well in self.depth_wells:
            if well.filters:
                for filtr in well.filters:
                    feads.append(filtr.get_filter(scale))

        return feads, f"filters-{profil_name}", fields, "LineString", False

    # ------------------------------------------------------------------------
    # передача данных паспорта скважин
    # в ообъектах скважин хранится словарь со списками объектов gtr
    # ------------------------------------------------------------------------
    def get_gtr (self, scale):
        profil_name = self.Id
        fields = [QgsField("name",QVariant.String),
                  QgsField("lcode",QVariant.Int)]
        key_list = []
        for well in self.depth_wells:
            if well.gtr: key_list.extend(well.gtr.keys())

        keys = set(key_list)
        data_list = []
        for key in keys:
            feads =[]
            for well in self.depth_wells:
                # использовать get для словаря
                gtr = False
                if well.gtr: gtr = well.gtr.get(key, False)
                if gtr:
                    for objs in gtr:
                        if objs: feads.append(objs.get_gtr(scale))
                    data_list.append((
                                      feads,
                                      f"{key}-{profil_name}",
                                      fields,
                                      "LineString",
                                      False
                                    ))
        return data_list
    # ------------------------------------------------------------------------
    # передача геометрий линейных слоев
    # ------------------------------------------------------------------------
    def get_lnlayer (self, scale):
        list_data = []
        for layer in self.ln_layer:
            list_data.append(layer.get(scale))
        return list_data

    # ------------------------------------------------------------------------
    # передача геометрий полигональных слоев
    # ------------------------------------------------------------------------
    def get_plglayer (self, scale):
        list_data = []
        profil_geom = self.profiline.get_srtm_geom(scale)
        if not profil_geom:
            profil_geom = self.profiline.get_izln_geom(scale)
        for layer in self.plg_layer:
            list_data.append(layer.get(profil_geom, scale))
        return list_data

#-----------------------------------------------------------------------------
#    geoSectionline
#-----------------------------------------------------------------------------

def cut_curvwell():

    dialog = formCurveWells()
    result = dialog.run()
    if result:
        wlayer = dialog.get_layerwells()
        wfields = dialog.get_fieldwells()
        srtm = dialog.get_strm()
        izln = dialog.get_izline()
        lnplg = dialog.get_lnplg()
        #scale = dialog.getscale()
        mapscale, cutscale = dialog.get_mapcut_scale()
        scale = mapscale / cutscale
        # Список объектов линии разреза
        cut_lines = []
        errlist = ""
        for cfeat in  dialog.get_featcut():
            # создание объекта разреза
            cline = geoSectionline(cfeat)
            # добавление скважин
            errlist += cline.add_depthwells(wlayer, wfields)
            # добавление профилей разреза
            cline.add_profile(izln, srtm)
            # добавление линейки
            cline.add_ruler(dialog.get_layercut(), cutscale)
            # добавление слоев линий и полигонов
            cline.add_lnplg(lnplg)
            # добавление объекта разреза в список
            cut_lines.append(cline)

        path = os.path.dirname(__file__)
        maingroup = creategroup("Разрезы", True)
        for cut in cut_lines:
            group = maingroup.addGroup(f"Разрез {cut.Id}")

            # профили разреза
            layer_data =  cut.profiline.get_profils(scale)
            if layer_data:
                layer = maplayer(*layer_data)
                group.addLayer(layer)

            # линейка
            ln_ruler, pnt_ruler = cut.ruler.get_ruler(scale)
            layer = maplayer(*ln_ruler)
            layer.loadNamedStyle(f'{path}/legstyle/ruler_ln.qml')
            group.addLayer(layer)
            layer = maplayer(*pnt_ruler)
            layer.loadNamedStyle(f'{path}/legstyle/ruler_pnt.qml')
            group.addLayer(layer)

            # скважины
            layer_data = cut.get_wells(scale)
            layer = maplayer(*layer_data)
            layer.loadNamedStyle(f'{path}/legstyle/wells_ln.qml')
            group.addLayer(layer)

            # фильтры
            feads, *layer_data = cut.get_filters(scale)
            if feads:
                layer = maplayer(feads, *layer_data)
                layer.loadNamedStyle(f'{path}/legstyle/filters_ln.qml')
                group.addLayer(layer)

            # данные паспорта скважины
            for data in cut.get_gtr(scale):
                feads, *layer_data = data
                if feads:
                    layer = maplayer(feads, *layer_data)
                    group.addLayer(layer)

            # вывод линейных слоев
            for layer_data in cut.get_lnlayer(scale):
                layer = maplayer(*layer_data)
                group.addLayer(layer)

            # вывод полигональных слоев
            for layer_data in cut.get_plglayer(scale):
                layer = maplayer(*layer_data)
                group.addLayer(layer)

        txt = f'Результат в группе "Разрезы". {errlist}'
    else: txt = "Отмена."
    del dialog

    return Qgis.Success, txt, "Завершено"
