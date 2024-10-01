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
class GpWell ():
    def __init__(self, point, depthlist, alt, wname, filters, data_sect):
        self.name_well = wname
        self.alt = alt
        self.x, self.y = point
        self.depthlist = depthlist
        self.set_interval(*data_sect)
        self.points_depth, self.sect_points = self.well_point_dept()
        if not (filters == NULL): self.filters = self.add_filters(filters)
        else: self.filters = False

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
    # создает массив точек линии фильтра приинициализации
    # объекта фильтра
    #-------------------------------------------------------------------------
    def set_filter(self, filter_string, alt, well_pnts):
        try:
            records = filter_string.split(";")
            y_begin = alt - float(records[0].strip().replace(',','.'))
            y_end = alt - float(records[1].strip().replace(',','.'))
            l_code = int(records[2].strip())

            filter_pnts = []
            for point in well_pnts:
                x,y = point
                if (y <= y_begin) and (y >= y_end):
                    filter_pnts.append(point)

            return filter_pnts, l_code
        except:
            return False, -1

    def get_filter(self, scale):

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

#-----------------------------------------------------------------------------
# Класс линий профиля рельефа.
# Профиль рельефа строиться по srtm и по изолиниям
#-----------------------------------------------------------------------------
class GpProfiles ():
    def __init__(self, feature):
        self.geom_cutline = feature.geometry()
        self.ID = feature.id()
        self.sect_length = self.geom_cutline.length()
        # Расчитать шаг из длины линии разреза
        self.step_point = self.geom_cutline.length() // 100
        self.sectpnt_srtm = []
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
            self.sectpnt_srtm.append((sec_x, sec_y))
        self.alt_extrem.extend([min(alt_list), max(alt_list)])

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
class rulerSection ():
    def __init__ (self, ID, length, alt_min, alt_max, cutscale, intersect):
        self.intersect = intersect
        self.cm_step = cutscale * self.coef_unit()
        self.alt_min = math.floor(alt_min/self.cm_step)*self.cm_step
        self.alt_max = math.ceil(alt_max/self.cm_step)*self.cm_step
        self.length = length
        self.name = ID

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
        attr = ["ruler", "left"]
        ln_feats.append((geom, attr))
        # правая линейка
        points = [QgsPointXY(self.length, self.alt_min*scale),
                  QgsPointXY(self.length, self.alt_max*scale)]
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
            # Наращивание расстояние от начала линии разреза
            x_beg += interval_geom.length()
            sectvert_beg = sectvert_end

        return  sorted(cutpoints, key=lambda x: x[0])

    #-------------------------------------------------------------------------
    #   добавление профилей разреза
    # ------------------------------------------------------------------------
    def add_profile(self, izln, srtm):

        # создание объекта профиля
        self.profiline = GpProfiles(self.feat_cutline)

        # получение списка точек линии профиля пересечений разреза
        # с изолиниями, построение профиля
        verts = self.sect_cut_ln(*izln)
        self.profiline.add_izln(verts)

        # построение профиля по strm
        if srtm: self.profiline.add_srtm(srtm)

    #-------------------------------------------------------------------------
    # добавление линейки
    #-------------------------------------------------------------------------
    def add_ruler (self, cuts_layer, cutscale):
        min_alt, max_alt = self.profiline.get_extreme()
        min_depth = min(self.well_depths)
        if min_alt > min_depth:
            min_alt = min_depth

        cuts_layer.startEditing()
        cuts_layer.deleteFeature(self.Id)
        intersect_pnt = self.sect_cut_ln(cuts_layer,"id")
        cuts_layer.rollBack()

        # создание объекта линейки
        self.ruler = rulerSection(self.Id, self.length,
                                  min_alt, max_alt,
                                  cutscale, intersect_pnt)

    #-------------------------------------------------------------------------
    # добавление скважин
    #-------------------------------------------------------------------------
    def add_depthwells (self, layer_wells, fields):

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
                                  filters, data_sect
                                )
             self.depth_wells.append(well_depth)

        fname, falt, ffile, ffilters = fields
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
            filters= fet_req[ffilters]
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
            # добавление скважин
            errlist += cline.add_depthwells(wlayer, wfields)
            # добавление профилей разреза
            cline.add_profile(izln, srtm)
            # добавление линейки
            cline.add_ruler(dialog.get_layercut(), cutscale)
            # добавление объекта разреза в список
            cut_lines.append(cline)

        path = os.path.dirname(__file__)
        maingroup = creategroup("Разрезы", True)
        for cut in cut_lines:
            group = maingroup.addGroup(f"Разрез {cut.Id}")

            # профили разреза
            layer_data =  cut.profiline.get_profils(scale)
            if layer_data: layer = maplayer(*layer_data)
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

        txt = f'Результат в группе "Разрезы". {errlist}'
    else: txt = "Отмена."
    del dialog

    return Qgis.Success, txt, "Завершено"
