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
    def cut_intersect_ln (self, feat_cutline, lines_layer, field):
        geom_cutline = feat_cutline.geometry()
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
                        #ID = featline.id()
                        #cutpoints.append((x_beg+dist, featline[field], ID))
                        cutpoints.append((x_beg+dist, featline[field]))
            # Наращивание расстояние от начала линии разреза
            x_beg += interval_geom.length()
            sectvert_beg = sectvert_end

        return  sorted(cutpoints, key=lambda x: x[0])

    #-------------------------------------------------------------------------
    # Пересечение линии разреза с полигонами
    # ------------------------------------------------------------------------
    def cut_intersect_plg (self, feat_cutline, polygons_layer, field):
        geom_cutline = feat_cutline.geometry()
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
                        if not v2.isEmpty():
                            x1 = v1.distance(sectvert_beg)+x_beg
                            x2 = v2.distance(sectvert_beg)+x_beg
                            if x1 > x2: x1, x2 = x2, x1
                            cutpoints.append((float(x1),float(x2),feat[field]))
            # Наращивание расстояние от начала линии разреза
            x_beg += interval_geom.length()
            sectvert_beg = sectvert_end
        sort_points = sorted(cutpoints, key=lambda x: x[0])

        # Объединение соседних полигонов с одинаковым признаком
        index = 0
        while index < len(sort_points)-1:
            x1, x2, name = sort_points[index]
            n1, n2, next_name = sort_points[index+1]
            if name == next_name:
                sort_points[index+1] = (x1, n2, name)
                sort_points.pop(index)
            else: index += 1

        return sort_points

    # ------------------------------------------------------------------------
    # Определение типа слоя и типа поля атрибутов
    # ------------------------------------------------------------------------
    def type_field (self, layer, field):
        field_num = layer.fields().field(field).type()
        lname = layer.name()
        if field_num == 10: return QVariant.String, field, lname
        if field_num == 2 or field_num == 4: return QVariant.Int, field, lname

    # ------------------------------------------------------------------------
    #   вертикальные координаты (по  y) для отображения пересечений
    #   на разрезе
    # ------------------------------------------------------------------------
    def y_view (self, extrem):
        y1, y2 = extrem
        buff = (y2-y1)/3
        y1 -= buff
        y2 += buff
        return y1, y2

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
    def __init__(self, point, depthlist, alt, wname, gtr, data_sect):
        self.name_well = wname
        self.alt = alt
        self.x, self.y = point
        self.depthlist = depthlist
        self.set_interval(*data_sect)
        self.points_depth, self.sect_points = self.well_point_dept()
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

    # ------------------------------------------------------------------------
    # добавление данных из паспорта скважин
    # список списков объектов по каждому ключу
    # ------------------------------------------------------------------------
    def add_gtr (self, gtr_dict):
        obj_dict = {}
        for key, vals in gtr_dict.items():
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
        lcode = False
        if self.gtr:
            keys = self.gtr.keys()
            if 'filters' in keys: lcode = True
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
        # на случай если данные будут по случайности перепутаны местами
        if y_begin < y_end: y_begin, y_end = y_end, y_begin

        filter_pnts = []
        index = 0
        x,y = well_pnts[index]
        """
        msgBox = QMessageBox()
        msgBox.setText(f"{y}<={y_begin}, {y_end}, {l_code}")
        msgBox.exec()
        """
        # начальное значение point_top если y_begin выше (больше) или равен
        # началу скважины. если не задать начальное значение,
        # то point_top будет не определен
        point_top = well_pnts[index]
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
    def __init__(self, feature, izln, srtm, cutname):
        self.geom_cutline = feature.geometry()
        self.feat = feature
        self.ID = feature.id()
        self.name = cutname
        self.sect_length = self.geom_cutline.length()
        # Расчитать шаг из длины линии разреза
        self.step_point = self.geom_cutline.length() // 100

        self.alt_extrem = []
        if srtm: self.sectpnt_srtm = self.add_srtm(srtm)
        else: self.sectpnt_srtm = False
        self.sectpnt_izln = self.add_izln(izln)

    def add_izln(self, izline):
        verts = self.cut_intersect_ln(self.feat, *izline)
        #verts = self.cut_intersect_ln(self.geom_cutline, *izline)
        izline_points = []
        for vert in verts:
            x, y = vert
            #x, y, ID = vert
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

        fields = [QgsField("name",QVariant.String),
                  QgsField("type",QVariant.String),
                  QgsField("sect_length", QVariant.Double),
                  QgsField("profil_length", QVariant.Double)]

        feats = []

        if self.sectpnt_srtm:
            geom = self.get_srtm_geom(scale)
            attr = [self.name, "srtm", self.sect_length, geom.length()]
            feats.append((geom,attr))
        if self.sectpnt_izln:
            geom = self.get_izln_geom(scale)
            attr = [self.name, "izln", self.sect_length, geom.length()]
            feats.append((geom, attr))
        else: return False

        return feats, f"profil-{self.name}", fields, "LineString", False
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
class GpRuler (objCutline):
    def __init__ (self, alt_min, alt_max, cutscale,
                  feat_cutline, feats_cut, fname):
        self.intersect = self.cut_intersect_ln(
                                                feat_cutline,
                                                feats_cut,
                                                fname
                                              )
        self.cm_step = cutscale * self.coef_unit()
        self.alt_min = math.floor(alt_min/self.cm_step)*self.cm_step
        self.alt_max = math.ceil(alt_max/self.cm_step)*self.cm_step
        self.geom_cutline = feat_cutline.geometry()
        self.length = self.geom_cutline.length()
        if fname: self.name = feat_cutline[fname]
        else: self.name = feat_cutline.id()

    def coef_unit (self):
        unit = QgsProject.instance().crs().mapUnits()
        if unit == Qgis.DistanceUnit.Millimeters: return 10
        elif unit == Qgis.DistanceUnit.Centimeters: return 1
        elif unit == Qgis.DistanceUnit.Meters: return 0.01
        elif unit == Qgis.DistanceUnit.Kilometers: return 0.0001
        else: return -1

    """
    def intersect_lines(self, feat_cutline, cuts_layer):
        geom_cut = feat_cutline.geometry()
        cuts_layer.startEditing()
        cuts_layer.deleteFeature(feat_cutline.id())
        intersect_pnt = self.cut_intersect_ln(geom_cut, cuts_layer,"id")
        cuts_layer.rollBack()

        return intersect_pnt
    """
    # ------------------------------------------------------------------------
    #   переопределения функции пересечения линии разреза с линиями на карте.
    #   адаптпция для поиска пересечения разрезов
    # ------------------------------------------------------------------------
    def cut_intersect_ln (self, feat_cutline, feats_cut, fname):
        feats = feats_cut.copy()
        feats.remove(feat_cutline)
        geom_cutline = feat_cutline.geometry()
        cutpoints = []
        x_beg = 0
        sectvert_iter = geom_cutline.vertices()
        sectvert_beg = next(sectvert_iter)
        for sectvert_end in sectvert_iter:
            interval_geom = QgsGeometry.fromPolyline([sectvert_beg,
                                                      sectvert_end])
            # Перебор изолиний пересакающих область текущего отрезка
            for featline in feats:
                featline_geom = featline.geometry()
                intersect_geom = featline_geom.intersection(interval_geom)

                if not intersect_geom.isEmpty():
                    for  part_geom in intersect_geom.asGeometryCollection() :
                        dist = part_geom.distance(
                                          QgsGeometry.fromPoint(sectvert_beg)
                                         )
                        if fname: cutname = featline[fname]
                        else: cutname = featline.id()
                        cutpoints.append((x_beg+dist, cutname))
            # Наращивание расстояние от начала линии разреза
            x_beg += interval_geom.length()
            sectvert_beg = sectvert_end

        return  sorted(cutpoints, key=lambda x: x[0])

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
            x, name = intercut
            points = [QgsPointXY(x, self.alt_min*scale),
                      QgsPointXY(x, self.alt_max*scale)]
            geom = QgsGeometry.fromPolylineXY(points)
            attr = ["intersect", f"{self.name} - {name}"]
            ln_feats.append((geom, attr))

        # точки шкалы
        pnt_feats = []
        i = self.alt_min
        while i <= self.alt_max:
            point = QgsPointXY(0, i*scale)
            pnt_feats.append((QgsGeometry.fromPointXY(point),
                              ['left', i, NULL]))
            point = QgsPointXY(self.length, i*scale)
            pnt_feats.append((QgsGeometry.fromPointXY(point),
                              ['right', i, NULL]))
            i += self.cm_step

        for i, v in  enumerate(self.geom_cutline.vertices()):
            x = self.geom_cutline.distanceToVertex(i)
            point = QgsPointXY(x, self.alt_max*scale)
            pnt_feats.append((QgsGeometry.fromPointXY(point),
                              ['cutpoint', x, f'{self.name}{i}']))

        ln_fields = [QgsField("type",QVariant.String),
                      QgsField("name", QVariant.String)]

        pnt_fields = [QgsField("type",QVariant.String),
                      QgsField("value", QVariant.Double),
                      QgsField("name", QVariant.String)]

        return ((ln_feats, f"ruler_ln-{self.name}", ln_fields,
                 "LineString", False),
               (pnt_feats, f"ruler_pnt-{self.name}", pnt_fields,
                "Point", False))
#-----------------------------------------------------------------------------
#     rulerSection
#-----------------------------------------------------------------------------

#-----------------------------------------------------------------------------
#     GpPolycut - Класс пересечения возрастов с линией разреза
#-----------------------------------------------------------------------------
class GpPolycut(objCutline):
    def __init__ (self, feature, polygons, extrem, cutname):
        self.cutname = f'{cutname}'
        self.lines = self.cut_intersect_plg(feature, *polygons)
        self.extrem = self.y_view(extrem)
        self.ftype, self.fname, self.lname = self.type_field(*polygons)

    def get(self, profil_geom, scale=1):

        if self.lines:
            feat = []
            y1, y2 = self.extrem
            for line in self.lines:
                x1, x2, lcode =line
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
                      QgsField("cutname",QVariant.String),
                      QgsField(self.fname, self.ftype)
                     ]

            return (feat,f"{self.lname}-{self.cutname}",fields,"Polygon",False)
        else: return False

#-----------------------------------------------------------------------------
#     GpLinecut - Класс пересечения рек с линией разреза
#-----------------------------------------------------------------------------
class GpLinecut(objCutline):
    def __init__(self, feature, lines, extrem, cutname):
        self.cutname = f'{cutname}'
        self.extrem = self.y_view(extrem)
        self.points = self.cut_intersect_ln(feature, *lines)
        self.ftype, self.fname, self.lname = self.type_field(*lines)

    def get(self, scale=1):
        if self.points:
            feat = []
            y1, y2 = self.extrem
            for point in self.points:
                x, name = point
                y = 0
                geom = QgsGeometry.fromPolylineXY([QgsPointXY(x,y1*scale),
                                                   QgsPointXY(x,y2*scale)])
                attr = [self.cutname, name]
                feat.append((geom, attr))

            fields = [
                      QgsField("cutname",QVariant.String),
                      QgsField(self.fname, self.ftype)
                     ]

            return (feat, f"{self.lname}-{self.cutname}",fields,
                    "LineString",False)
        else: return False
#-----------------------------------------------------------------------------
# Класс линии разреза. Мега большой класс с информацией по каждой линии
# разреза. Рельеф, пересечения рек и возрастов. Скважины массив объектов
# GpWell.
#-----------------------------------------------------------------------------
class geoSectionline ():
    def __init__(self, feature, fcutname):
        self.feat_cutline = feature
        self.fname = fcutname
        if fcutname: self.name = feature[fcutname]
        else: self.name = feature.id()
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
        self.profiline = GpProfiles(self.feat_cutline, izln, srtm, self.name)

    #-------------------------------------------------------------------------
    # добавление линейки
    #-------------------------------------------------------------------------
    def add_ruler (self, feats_cut, cutscale):
        min_alt, max_alt = self.profiline.get_extreme()
        extreme = [min_alt, max_alt] + self.well_depths
        min_alt = min(extreme)
        max_alt = max(extreme)
        # создание объекта линейки
        self.ruler = GpRuler(
                             min_alt, max_alt, cutscale,
                             self.feat_cutline, feats_cut,
                             self.fname
                            )

    #-------------------------------------------------------------------------
    # добавление слоев пересечения в массивы линий и полигонов
    #-------------------------------------------------------------------------
    def add_lnplg (self, lnplg):
        for data in lnplg:
            layer, field = data
            if layer.geometryType() == QgsWkbTypes.LineGeometry:
                self.ln_layer.append(GpLinecut(
                                              self.feat_cutline,
                                              data,
                                              self.profiline.get_extreme(),
                                              self.name
                                             )
                                    )
            elif layer.geometryType() == QgsWkbTypes.PolygonGeometry:
                self.plg_layer.append(GpPolycut(
                                             self.feat_cutline,
                                             data,
                                             self.profiline.get_extreme(),
                                             self.name
                                             )
                                    )

    # ------------------------------------------------------------------------
    # чтение файла паспорта скважины
    # ------------------------------------------------------------------------
    def read_gtr (self, path, alt):
        err = ""
        try:
            #csv_path = os.path.join(csvdir, csv)
            with open (path, 'r') as gtr:
                gtr_dict = {}
                value = []
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
            return False
        except ValueError:
            return False

    # ------------------------------------------------------------------------
    # чтение файла с глубин изогнутых скважин
    # ------------------------------------------------------------------------
    def read_depth_cvs (self, csv, path, alt):
        err = ""
        try:
            with open (path, 'r') as csvfile:
                depthlist = [(0,0,0)]
                for line in csvfile:
                    records = line.split(";")
                    depth = int(records[0].strip())
                    zenit = float(records[1].strip().replace(',','.'))
                    azimut = float(records[2].strip().replace(',','.'))
                    depthlist.append((depth,zenit,azimut))
                self.well_depths.extend([alt, alt-depth])
                #self.well_depths.append(alt-depth)

            csvfile.close()
        except FileNotFoundError:
            try:
                depth = float(csv.strip().replace(',','.'))
                depthlist = [(0,0,0),(depth,0,0)]
                self.well_depths.append(alt-depth)
                err = "прямая скважина."
            except ValueError:
                err = "данные о глубине не число."
        except ValueError:
            err = "в данных о глубине не число."
        except Exception as e:
            err = f"{e}."

        return err, depthlist


    #-------------------------------------------------------------------------
    # добавление скважин
    #-------------------------------------------------------------------------
    def add_depthwells (self, layer_wells, fields):

        fname, falt, ffile, fgtr = fields

        csvdir = os.path.dirname(layer_wells.source())
        cut_geom = self.feat_cutline.geometry()
        errlist = ""
        request = QgsFeatureRequest()
        request.setDistanceWithin(cut_geom, 1)

        for fet_req in layer_wells.getFeatures(request):
            # проверка наличия основных параметров скважины
            csv = fet_req[ffile]
            alt = fet_req[falt]
            wname = fet_req[fname]
            if not csv == NULL and not alt == NULL:
                vertx_geom, icur, iprv, inxt, sqr_dist = \
                     cut_geom.closestVertex(fet_req.geometry().asPoint())

                if iprv == -1: iprv = inxt
                if inxt == -1: inxt = iprv
                data_sect = (
                             cut_geom.vertexAt(iprv),
                             vertx_geom,
                             cut_geom.vertexAt(inxt),
                             cut_geom.distanceToVertex(icur)
                            )

                x = fet_req.geometry().asPoint().x()
                y = fet_req.geometry().asPoint().y()


                csv_path = os.path.join(csvdir, csv)
                err, depthlist = self.read_depth_cvs(csv, csv_path, alt)

                if depthlist:

                    # чтение gtr-файла
                    if fgtr: gtr = fet_req[fgtr]
                    else: gtr = NULL
                    if not gtr == NULL:
                        gtr_path = os.path.join(csvdir, gtr)
                        gtr_dict = self.read_gtr(gtr_path, alt)
                    else: gtr_dict = False

                    self.depth_wells.append(
                                            GpWell(
                                                   (x,y),
                                                   depthlist,
                                                   alt,
                                                   wname,
                                                   gtr_dict,
                                                   data_sect
                                                  )
                                           )

            else: err = "поля атрибутов скважины не заполнены"
            if err: errlist += f"\nСкв. {wname} - {err}"

        return errlist

    #-------------------------------------------------------------------------
    # передача массива скважин в слой
    #-------------------------------------------------------------------------
    def get_wells (self, scale):
        # Поля атрибутов изогнутых скважин
        fields = [QgsField("name",QVariant.String),
                  QgsField("depth",QVariant.Double),
                  QgsField("lcode", QVariant.Bool)]
        feats = []
        for well in self.depth_wells:
            geom, attr = well.get_sectionLine(scale)
            feats.append((geom, attr))

        return feats, f"wells_{self.name}", fields, "LineString", False

    # ------------------------------------------------------------------------
    # передача данных паспорта скважин
    # в ообъектах скважин хранится словарь со списками объектов gtr
    # ------------------------------------------------------------------------
    def get_gtr (self, scale):
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
                                      f"{key}_{self.name}",
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
        if self.profiline.sectpnt_srtm:
            profil_geom = self.profiline.get_srtm_geom(scale)
        else: profil_geom = False
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
        fcutname, *wfields = dialog.get_fieldwells()
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
            cline = geoSectionline(cfeat, fcutname)
            # добавление скважин
            errlist += cline.add_depthwells(wlayer, wfields)
            # добавление профилей разреза
            cline.add_profile(izln, srtm)
            # добавление линейки
            cline.add_ruler(dialog.get_featcut(), cutscale)
            # добавление слоев линий и полигонов
            cline.add_lnplg(lnplg)
            # добавление объекта разреза в список
            cut_lines.append(cline)

        path = os.path.dirname(__file__)
        maingroup = creategroup("Разрезы", True)
        for cut in cut_lines:
            group = maingroup.addGroup(f"Разрез {cut.name}")

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
    else: txt = "Галя, у нас отмена."
    del dialog

    return Qgis.Success, txt, "Завершено"
