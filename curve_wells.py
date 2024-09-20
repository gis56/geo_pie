# -*- coding: utf-8 -*-

import os
import math

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
                       NULL
                      )
from .pie_dial import formCurveWells

from .utilib import *
#-----------------------------------------------------------------------------
# Класс описывающий скважину на разрезе. Название скважины, расстояние от
# начала линии разреза, геометрию отрезка разреза до и после скважины, точки
# по глубине.
# ----------------------------------------------------------------------------
class pointDepthwell ():
    def __init__(self, point, depthlist, alt, wname):
        self.name_well = wname
        self.alt = alt
        self.x, self.y = point
        self.depthlist = depthlist
        self.points_depth = self.well_point_dept()

        self.dist_begin = 0
        self.pr_line = QgsGeometry()
        self.nx_line = QgsGeometry()
        self.vertex = QgsGeometry()

    # Расчет координат точек интервалов глубины
    def well_point_dept (self):

        points_depth = [(self.x, self.y, self.alt)]
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

            points_depth.append((x, y, self.alt-depth))

            prev_depth = depth

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
        self.sectpnt_izln = []
        self.alt_extrem = []

    def add_izln(self, verts):
        for vert in verts:
            x, y = vert
            self.sectpnt_izln.append((float(x), float(y)))
        self.alt_extrem.extend([
                        min(self.sectpnt_izln, key=lambda y: y[1])[1],
                        max(self.sectpnt_izln, key=lambda y: y[1])[1]
                        ])

    def add_srtm(self, srtm):
        # Уплотнение линии точками
        densify_line = self.geom_cutline.densifyByDistance(self.step_point)
        # Получение списка вершин уплотненной линии разреза
        vertexs = densify_line.asPolyline()
        # Получение координат вершин уплотненной линии разреза и
        # расстояний от начала до каждой из вершин
        #profile_points = list()
        alt_list = []
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
        self.alt_extrem.extend([min(alt_list), max(alt_list)])

    def get_extreme (self):
        return min(self.alt_extrem), max(self.alt_extrem)

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

    def get_izln_geom (self, scale=1):
        x,y = self.sectpnt_izln[0]
        points = [QgsPointXY(0, y*scale)]
        for point in self.sectpnt_izln:
            x,y = point
            points.append(QgsPointXY(x,y*scale))
        points.append(QgsPointXY(self.geom_cutline.length(), y*scale))

        return  QgsGeometry.fromPolylineXY(points)


#-----------------------------------------------------------------------------
#     profilSectionline
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
class rulerSection ():
    def __init__ (self, length, alt_min, alt_max, cutscale):
        self.cm_step = cutscale * self.coef_unit()
        self.alt_min = math.floor(alt_min/self.cm_step)*self.cm_step
        self.alt_max = math.ceil(alt_max/self.cm_step)*self.cm_step
        self.length = length

    def coef_unit (self):
        unit = QgsProject.instance().crs().mapUnits()
        if unit == Qgis.DistanceUnit.Millimeters: return 10
        elif unit == Qgis.DistanceUnit.Centimeters: return 1
        elif unit == Qgis.DistanceUnit.Meters: return 0.01
        elif unit == Qgis.DistanceUnit.Kilometers: return 0.0001
        else: return -1

    def get_ruler(self, scale=1):
        # линии шкалы
        ln_feats = []
        # левая линейка
        points = [QgsPointXY(0,self.alt_min*scale),
                  QgsPointXY(0,self.alt_max*scale)]
        geom = QgsGeometry.fromPolylineXY(points)
        attr = ["left",0]
        ln_feats.append((geom, attr))
        # правая линейка
        points = [QgsPointXY(self.length, self.alt_min*scale),
                  QgsPointXY(self.length, self.alt_max*scale)]
        geom = QgsGeometry.fromPolylineXY(points)
        attr = ["right",0]
        ln_feats.append((geom, attr))
        # нулевая линия (если есть)
        if self.alt_min < 0 and self.alt_max > 0:
            points = [QgsPointXY(0,0), QgsPointXY(self.length, 0)]
            geom = QgsGeometry.fromPolylineXY(points)
            attr = ["null",1]
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

        return ln_feats, pnt_feats
#-----------------------------------------------------------------------------
#     rulerSection
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
        # создается объект линии разреза
        #self.profiline = profilSectionline(feature)
        # список глубин всех вынесенных на разрез скважин
        # для поиска наиболее глубокой и расчета минимального значения линейки
        self.well_depths = []

    #------------------------------------------------------------------------
    # точки пересечения линий с линиями
    # на входе слой с линиями и фьючерс объекта линии разреза
    # на выходе геометрия и атрибуты точек пересечения
    # геометрия: X=расстояние от начала разреза, Y=либо атрибуту поля с
    # высотами в случае с изолиниями, либо точке пересечения вертикали
    # с линией профиля
    # ------------------------------------------------------------------------
    def sect_cut_ln (self, lines_layer, field):
        cutpoints = []
        x_beg = 0
        sectvert_iter = self.feat_cutline.geometry().vertices()
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
                """
                if intersect_geom.isMultipart():
                    if not intersect_geom.isEmpty():
                        dist = intersect_geom.distance(
                                          QgsGeometry.fromPoint(sectvert_beg)
                                         )
                        cutpoints.append((x_beg+dist, featline[field]))
                else :
                    for  part_geom in intersect_geom.asGeometryCollection() :
                        dist = part_geom.distance(
                                          QgsGeometry.fromPoint(sectvert_beg)
                                         )
                        cutpoints.append((x_beg+dist, featline[field]))
                """
            # Наращивание расстояние от начала линии разреза
            x_beg += interval_geom.length()
            sectvert_beg = sectvert_end

        return  sorted(cutpoints, key=lambda x: x[0])

    #-------------------------------------------------------------------------
    #   sect_cut_ln
    #-------------------------------------------------------------------------
    """
    # добавление профиля построенного по изолиниям
    def add_izline(self, izln):
        verts = self.sect_cut_ln(*izln)
        for vert in verts:
            x, y = vert
            self.profiline.sectpnt_izln.append((float(x), float(y)))
    """
    # добавление профиля построенного по изолиниям
    def add_profile(self, izln, srtm):

        self.profiline = profilSectionline(self.feat_cutline)

        verts = self.sect_cut_ln(*izln)
        self.profiline.add_izln(verts)
        """
        for vert in verts:
            x, y = vert
            self.profiline.sectpnt_izln.append((float(x), float(y)))
        min_y = min(self.profiline.sectpnt_izln, key=lambda y: y[1])
        max_y = max(self.profiline.sectpnt_izln, key=lambda y: y[1])
        """
        if srtm: self.profiline.add_srtm(srtm)

    # добавление линейки
    def add_ruler (self, cutscale):
        min_alt, max_alt = self.profiline.get_extreme()
        #min_alt, max_alt = self.profiline.alt_extrem
        min_depth = min(self.well_depths)
        if min_alt > min_depth:
            min_alt = min_depth
        self.ruler = rulerSection(self.length, min_alt, max_alt, cutscale)

    # добавление скважин
    def add_depthwells (self, layer_wells, fields):

        def addwell():
             # создание объекта скважины
             well_depth = pointDepthwell((x,y),depthlist,alt,wname)
             well_depth.add_begin(cut_geom.distanceToVertex(icur))
             well_depth.add_geomsection(
                                         cut_geom.vertexAt(iprv),
                                         vertx_geom,
                                         cut_geom.vertexAt(inxt)
                                        )
             self.depth_wells.append(well_depth)

        fname, falt, ffile= fields
        csvdir = os.path.dirname(layer_wells.source())
        cut_geom = self.feat_cutline.geometry()
        errlist = ""
        request = QgsFeatureRequest()
        request.setDistanceWithin(cut_geom, 1)

        for fet_req in layer_wells.getFeatures(request):
            vertx_geom, icur, iprv, inxt, sqr_dist = \
                 cut_geom.closestVertex(fet_req.geometry().asPoint())

            csv = fet_req[ffile]
            wname = fet_req[fname]
            if csv == NULL:
                errlist += f"\n{wname} - нет данных о глубине."
                continue
            x = fet_req.geometry().asPoint().x()
            y = fet_req.geometry().asPoint().y()
            alt = fet_req[falt]
            # Чтение файла
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
                addwell()

            except FileNotFoundError:
                try:
                    depth = float(csv.strip().replace(',','.'))
                    depthlist = [(depth,0,0)]
                    self.well_depths.append(alt-depth)
                    addwell()
                except ValueError:
                    errlist += f"\n{wname} -  данные о глубине не число."
            except ValueError:
                errlist += f"\n{wname} -  в данных о глубине не число."
            except Exception as e:
                errlist += f"\n{wname} - {e}."
        return errlist

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
        #scale = dialog.getscale()
        mapscale, cutscale = dialog.get_mapcut_scale()
        scale = mapscale / cutscale
        # Список объектов линии разреза
        cut_lines = []
        errlist = ""
        for cfeat in  dialog.get_featcut():
            # создание объекта разреза
            cline = geoSectionline(cfeat)
            errlist += cline.add_depthwells(wlayer, wfields)
            # создание профилей разреза
            cline.add_profile(izln, srtm)
            #cline.profiline.add_srtm(srtm)
            #cline.add_izline(izln)
            # линейки
            cline.add_ruler(cutscale)
            #errlist += cline.ruler.get_ruler()
            cut_lines.append(cline)

        # Поля атрибутов линии разреза
        fields_cut = [QgsField("name",QVariant.String),
                      QgsField("length",QVariant.Double)]

        # Поля атрибутов изогнутых скважин
        fields_well = [QgsField("name",QVariant.String),
                       QgsField("depth",QVariant.Double)]

        #errtxt = ""
        maingroup = creategroup("Разрезы", True)
        for cut in cut_lines:
            # профиль srtm
            geom = cut.profiline.get_srtm_geom(scale)
            attr = [f"{cut.Id}", cut.length]
            feat = [(geom, attr)]

            group = maingroup.addGroup(f"Разрез {cut.Id}")
            layer = maplayer(feat, f"srtm_profil-{cut.Id}",
                             fields_cut, "LineString", False)
            group.addLayer(layer)

            # профиль изолиний
            geom = cut.profiline.get_izln_geom(scale)
            attr = [f"{cut.Id}", cut.length]
            feat = [(geom, attr)]

            layer = maplayer(feat, f"izline_profil-{cut.Id}",
                             fields_cut, "LineString", False)
            group.addLayer(layer)

            # линейка
            ln_feats, pnt_feats = cut.ruler.get_ruler(scale)
            layer = maplayer(ln_feats, f"ruler-{cut.Id}",
                             fields_cut, "LineString", False)
            group.addLayer(layer)
            layer = maplayer(pnt_feats, f"titl_ruler-{cut.Id}",
                             fields_cut, "Point", False)
            group.addLayer(layer)

            feature = []
            for well in cut.depth_wells:
                geom, attr = well.get_sectionLine(scale)
                feature.append((geom, attr))
                #errtxt += well.err_msg
            layer = maplayer(feature, "wells_line",
                             fields_well, "LineString", False)
            group.addLayer(layer)

        txt = f'Результат в группе "Разрезы". {errlist}'
    else: txt = "Отмена."
    del dialog

    return Qgis.Success, txt, "Завершено"
