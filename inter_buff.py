import os
import math

from qgis.PyQt.QtCore import QVariant, QMetaType

from qgis.core import (
                        Qgis,
                        QgsField,
                        QgsGeometry,
                        QgsFeature,
                        QgsEllipse,
                        QgsCircle,
                        QgsPointXY,
                        QgsPoint,
                        QgsCoordinateReferenceSystem,
                        QgsCoordinateTransform,
                        NULL
                      )
from .pie_dial import formBufferIntersectZone
from .utilib import *

#-----------------------------------------------------------------------------
#
#-----------------------------------------------------------------------------
def inter_buffer():
    dialog =  formBufferIntersectZone()
    result = dialog.run()
    if result:
        features = dialog.getfeatures()

        # Подготовка к трансформации CRS
        global crs_prj
        global xform
        crs_lyr, crs_prj = dialog.getcrs()
        if crs_prj :
            crsSrc = QgsCoordinateReferenceSystem(crs_lyr.authid())   # WGS 84
            crsDest = QgsCoordinateReferenceSystem(crs_prj.authid())  # UTM zone 33N
            transformContext = QgsProject.instance().transformContext()
            xform = QgsCoordinateTransform(crsSrc, crsDest, transformContext)

        txt = ""
        sum_area_circles = 0

        feats_circle = []
        list_circle_geom = []
        name = dialog.getnamefield()
        decim = dialog.getDecimal()
        for feat in features:
            # генерация круговых зон вокруг скважин
            radius = feat[name]
            if (radius == NULL) or (radius == 0):
                txt += f"\nРадиус зоны для ID: {feat.id()+1} не указан."
            else:
                # трасформация в метровую СК
                if crs_prj : center = xform.transform(feat.geometry().asPoint())
                else: center = feat.geometry().asPoint()

                circle = QgsCircle(QgsPoint(center.x(), center.y()), radius)
                circle_wkt = circle.toPolygon(36).asWkt()
                circle_geom = QgsGeometry().fromWkt(circle_wkt)
                circle_area = circle.area()
                sum_area_circles += circle_area # счетчик площади кругов
                list_circle_geom.append(circle_geom) # список зон окружностей
                attr_circle = [circle_area]
                feats_circle.append((circle_geom, attr_circle))

        if list_circle_geom:
            union_geom = QgsGeometry().unaryUnion(list_circle_geom)
            union_list =union_geom.asGeometryCollection()
            list_circle = feats_circle.copy()
            feats_buffer = []
            for buffer_geom in union_list:
                sum_area_circles = 0
                for index, value in enumerate(list_circle):
                    circle_geom, attr_circle = value
                    pnt = circle_geom.centroid()
                    if pnt.within(buffer_geom):
                        sum_area_circles += attr_circle[0]

                area_unio = buffer_geom.area() # площадь обЪединения
                area_buff = area_unio
                rule = (sum_area_circles / 100 ) * decim
                while True:
                    r1 = math.sqrt(area_buff/math.pi)
                    r2 = math.sqrt((sum_area_circles-area_buff)/math.pi + r1*r1)
                    buff = r2 - r1
                    buffer_geom = buffer_geom.buffer(buff, 336)
                    area_buff = buffer_geom.area() # площадь буфера
                    if abs(sum_area_circles - area_buff) < rule: break

                if crs_prj :
                    buffer_geom.transform(xform,
                                      QgsCoordinateTransform.ReverseTransform)

                attr_buffer = [area_buff, area_unio, sum_area_circles,
                               sum_area_circles - area_buff]
                feats_buffer.append((buffer_geom, attr_buffer))
        else: txt += "\nНет значений радиусов."

        # обратная трансформация в исходную СК
        if crs_prj :
            for feat in list_circle:
                circle_geom, attr = feat
                circle_geom.transform(xform,
                                      QgsCoordinateTransform.ReverseTransform)
        #path = os.path.dirname(__file__)
        group = creategroup("intersect")
        if feats_circle:
            fields = [QgsField("area", QVariant.Double)]
            vlayer = maplayer(feats_circle, "circle", fields, "Polygon",
                            False, crs_lyr)
            #vlayer.loadNamedStyle(f'{path}/legstyle/zso.qml')
            group.addLayer(vlayer)

        if feats_buffer:
            fields = [QgsField("area_buffer", QVariant.Double),
                      QgsField("area_union", QVariant.Double),
                      QgsField("area_circls", QVariant.Double),
                      QgsField("difference", QVariant.Double)]
            #vlayer = maplayer([(union_geom.simplify(100),
            vlayer = maplayer(feats_buffer, "union", fields,
                              "Polygon", False, crs_lyr)
            group.addLayer(vlayer)

    else: txt = "Отмена."

    del dialog
    lvl = Qgis.Success
    return Qgis.Success, txt, "Завершено"
