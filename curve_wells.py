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

FORM_CLASS_1, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'ui/curve_wells.ui'))

class formCurveWells(QtWidgets.QDialog, FORM_CLASS_1):
    msgBox = QtWidgets.QMessageBox()

    def __init__(self, parent=None):
        super(formCurveWells, self).__init__(parent)
        self.setupUi(self)

        # Настройка mLayer (скважины)
        self.mLayer.setFilters(QgsMapLayerProxyModel.PointLayer)
        self.mLayer.activated.connect(self.activ_mLayer)
        self.mLayer.currentIndexChanged.connect(self.activ_mLayer)

        # Настройка mLayer_cut (разрез)
        self.mLayer_cut.setFilters(QgsMapLayerProxyModel.LineLayer)
        self.mLayer_cut.activated.connect(self.activ_mLayer_cut)

        # Настройка типов полей атрибутов
        self.mField_well.setFilters(QgsFieldProxyModel.String)
        self.mField_file.setFilters(QgsFieldProxyModel.String)
        self.mField_alt.setFilters(QgsFieldProxyModel.Double)

        # Инициализация чекбокса выбранных скважин
        #self.checkBox_Features.setChecked(False)

    # Действия на активацию и выбор слоя разреза в mLayer_cut
    def activ_mLayer_cut(self):
        self.cutline_layer = self.mLayer_cut.currentLayer()

    # Действия на активацию и выбор слоя скважин в mLayer
    def activ_mLayer(self):
        # Инициализация полей атрибутов
        self.mField_well.setLayer(self.mLayer.currentLayer())
        self.mField_file.setLayer(self.mLayer.currentLayer())
        self.mField_alt.setLayer(self.mLayer.currentLayer())

    # Подготовка и запуск формы диалога
    def run(self):
        self.activ_mLayer()
        self.activ_mLayer_cut()
        self.exec_()
        return self.result()

    # Перегрузка метода диалогового окна accept для
    # проверки заполненности всех полей формы
    def accept (self) :
        # Проверка пути к файлу и выбранного поля
        if (self.mField_well.currentField() and
            self.mField_alt.currentField() and
            self.mField_file.currentField()):
            self.done(QtWidgets.QDialog.Accepted)
        else:
            self.msgBox.warning(self,"Матрица скважин",
                                "Не все поля заполнены.")
    def get_layerwells (self):
        return self.mLayer.currentLayer()

    def get_layercut (self):
        return self.mLayer_cut.currentLayer()

    def get_featwells (self):
        return [feat for feat in self.mLayer.currentLayer().getFeatures()]

    def get_selfeatwells (self):
        return self.mLayer.currentLayer().selectedFeatures()

    def get_featcut (self):
        return [feat for feat in self.mLayer_cut.currentLayer().getFeatures()]

    def get_fieldwells (self):
        return (self.mField_well.currentField(),
                self.mField_alt.currentField(),
                self.mField_file.currentField()
               )

    def get_dirlayer (self):
        return  os.path.dirname(self.mLayer.currentLayer().source())

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

#-----------------------------------------------------------------------------
#   pointDepthwell (feature, fields, csvdir)
#-----------------------------------------------------------------------------

#-----------------------------------------------------------------------------
# Класс линии разреза. Мега большой класс с информацией по каждой линии
# разреза. Рельеф, пересечения рек и возрастов. Скважины массив объектов
# pointDepthwell.
#-----------------------------------------------------------------------------
class geoSectionline ():
    def __init__(self, feature):
        self.feat_cutline = feature
        self.depth_wells = []

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

# -----------------------------------------------------------
# Создание слоя (пока точек, потом сделать универсальным)
# и дабавление его на карту (потом сделать возвращение виртуального слоя,
# а добавление и компановка слоев будет в другом месте.
# features - объекты слоя
# layer_name -  имя слоя
# attr_list - список атрибутов слоя
# ------------------------------------------------------------
def maplayer (features, layer_name, attr_list, layer_type):

    project = QgsProject.instance()
    uri = "{}?crs=epsg:{}".format(layer_type, project.crs().postgisSrid())
    virtLayer = QgsVectorLayer(uri, layer_name, "memory")
    virtProvider = virtLayer.dataProvider()
    virtProvider.addAttributes(attr_list)

    vlayer_fet = QgsFeature()
    for fet in features:
        geom, attr = fet
        vlayer_fet.setGeometry(geom)
        vlayer_fet.setAttributes(attr)
        virtProvider.addFeature(vlayer_fet)
    virtLayer.updateFields()
    virtLayer.updateExtents()
    del virtProvider

    project.addMapLayer(virtLayer, True)

def cut_curvwell():

    msgBox = QMessageBox()

    curvwells_dialog = formCurveWells()
    result = curvwells_dialog.run()
    if result:
        attr = [QgsField("name",QVariant.String),
                QgsField("depth",QVariant.Int)
               ]

        cut_lines = []
        wlayer = curvwells_dialog.get_layerwells()
        wfields = curvwells_dialog.get_fieldwells()
        for cfeat in  curvwells_dialog.get_featcut():
            cline = geoSectionline(cfeat)
            cline.add_depthwells(wlayer, wfields)
            cut_lines.append(cline)

        g,a = cut_lines[0].depth_wells[0].depth_asline()
        feature = [tuple([g,a])]
        maplayer(feature, "sLine3d_obj", attr, "LineString")

        features = cut_lines[0].depth_wells[0].depth_asPointXY()
        maplayer(features,"sPointXY_obj", attr, "Point")

        features = cut_lines[0].depth_wells[0].depth_asPoint()
        maplayer(features,"sPoint3dY_obj", attr, "Point")

        #msgBox.setWindowTitle("Сообщение.")
        #msgBox.setText(str(cut_lines[0].depth_wells[0].dist_begin))
        #self.msgBox.setText(f"\
        #                    id скважины - {well_id} \n \
        #                    индекс - {icur} \n \
        #                    до - {iprv} \n \
        #                    после - {inxt})")
        #self.msgBox.setInformativeText("")
        #self.msgBox.setDetailedText("")
        #msgBox.exec()

        del curvwells_dialog
