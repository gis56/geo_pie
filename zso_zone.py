import os
import math

from qgis.PyQt import uic
from qgis.PyQt import QtWidgets
from qgis.PyQt.QtWidgets import QAction, QFileDialog
from qgis.PyQt.QtCore import QVariant

from qgis.core import (QgsProject,
                       Qgis,
                       QgsVectorLayer,
                       QgsField,
                       QgsGeometry,
                       QgsFeature,
                       QgsFieldProxyModel,
                       QgsMapLayerProxyModel,
                       QgsEllipse,
                       QgsPointXY)

FORM_CLASS_1, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'ui/zone_zso.ui'))

class zsoZone(QtWidgets.QDialog, FORM_CLASS_1):

    project = QgsProject.instance()
    plugin_dir = os.path.dirname(__file__)
    filename = ''
    features = []
    # Состояние наличия данных в атрибутивной таблицы для поясов
    # [III пояс, II пояс, I пояс]
    fields_check = [False,False,False]
    azimut = 0
    msgBox = QtWidgets.QMessageBox()

    def __init__(self, parent=None):
        super(zsoZone, self).__init__(parent)
        self.setupUi(self)

        # Реакция на выбор слоя в mLayer
        self.layer_ComboBox.activated.connect(self.activ_layerbox)
        self.layer_ComboBox.currentIndexChanged.connect(self.activ_layerbox)

        self.select_checkBox.setChecked(False)

    # Описание реакции mLayer на активацию и выбор
    def activ_layerbox(self):
        self.layer_ComboBox.setFilters(QgsMapLayerProxyModel.PointLayer)

        self.select_checkBox.setChecked(False)
        # Получение выбранного слоя
        wells_vLayer = self.layer_ComboBox.currentLayer()
        # Проверка на наличие выборки. Если есть выбранные объекты,
        # сделать доступным галочку
        if wells_vLayer.selectedFeatures() :
            self.select_checkBox.setEnabled(True)
        else :
            self.select_checkBox.setEnabled(False)


    # Перегрузка метода диалогового окна accept для
    # проверки заполненности всех полей формы
    def accept (self) :
        self.exec_zsozone()
        self.done(QtWidgets.QDialog.Accepted)

    # Подготовка и запуск формы диалога
    def run(self):
        self.activ_layerbox()
        self.exec_()

    # Подготовка данных для записи в файлы таблиц
    def exec_zsozone (self) :
        self.azimut = self.azimut_spinBox.value()
        # Получение выбранного слоя
        wells_vLayer = self.layer_ComboBox.currentLayer()
        # Создание списка объектов в зависимости от состояние галочки
        if self.select_checkBox.isChecked() :
            self.features = wells_vLayer.selectedFeatures()
        else :
            self.features=[feature for feature in wells_vLayer.getFeatures()]
        # Список полей атрибутивной таблицы
        fnm = wells_vLayer.fields().names()
        # Проверка на наличие полей,
        # запуск построения зон,
        # установка состояния наличия атрибутов для последующей корректной
        # отрисовки радиусов
        if 'r1' in fnm:
            self.layer_qudrat_zone()
            self.fields_check[2] = True
        else:
            self.msgBox.warning(self,"Проверка атрибутов.",
                                "Отсутствует поле первого пояса 'r1'.")
        if (('r_n2' in fnm) and ('r_w2' in fnm) and
            ('r_s2' in fnm) and ('r_o2' in fnm)):
            self.layer_ellipse_zone('Зона R2','zso_R2',2)
            self.fields_check[1] = True
        else:
            self.msgBox.warning(self,"Проверка атрибутов.",
                                "Отсутствует поля второго пояса 'r_?2'.")
        if (('r_n3' in fnm) and ('r_w3' in fnm) and
            ('r_s3' in fnm) and ('r_o3' in fnm)):
            self.layer_ellipse_zone('Зона R3','zso_R3',3)
            self.fields_check[0] = True
        else:
            self.msgBox.warning(self,"Проверка атрибутов.",
                                "Отсутствует поля третьего пояса 'r_?3'.")

        self.arrow_dist()

    """ Отрисовка эллипса
    center - центр эллипса QgsPoint()
    R - радиус в положительном направлении оси X (после поворота на Север)
    D - в положительном направлении оси Y (Восток)
    r - в отрицательном направлении оси X (Юг)
    d - в отрицательном направлении оси Y (Запад)
    azimut - угол поворота в градусах
    Возвращает полигон геометрии эллипса QgsGeometry
    """
    def draw_ellipse (self, center, R, D, r, d, azimut):
        # Построение дуги по параметрическому уровнению эллипса
        # radius_begin - начальный радиус
        # radius_end - конечный радиус
        # angle_begin - начальный угол
        # angle_end - конечный угол
        # Взвращает список точек дуги эллипса
        def arc_draw (radius_begin, radius_end, angle_range):
            arcpoint_list = []
            for angle in angle_range:
                angle_radian = math.radians(angle)
                arc_x = radius_begin*math.cos(angle_radian)+center_x
                arc_y = radius_end*math.sin(angle_radian)+center_y
                # Геометрия дуги эллипса
                arc_point = QgsPointXY(arc_x,arc_y)
                arcpoint_list.append(arc_point)
            return arcpoint_list

        # Координаты центра эллипса
        center_x = center.x()
        center_y = center.y()
        # Список точек конечного эллипса
        ellipse_list = []
        ellipse_list.extend(arc_draw(R,d,range(-90,0)))
        ellipse_list.extend(arc_draw(R,D,range(0,90)))
        ellipse_list.extend(arc_draw(r,D,range(90,180)))
        ellipse_list.extend(arc_draw(r,d,range(180,270)))
        ellipse_list.append(ellipse_list[0])
        # Геометрия эллипса
        ellipse_geom = QgsGeometry.fromPolygonXY([ellipse_list])
        azimut = azimut-90 # Разворот большим радиусом на Север
        ellipse_geom.rotate(azimut, QgsPointXY(center_x,center_y))

        return ellipse_geom

    """ Создание слоев зон II-го и III-го пояса
    name_layer - название слоя
    num_zone - номер пояса зоны
    """
    def layer_ellipse_zone(self,name_layer,name_style,num_zone):
        # Виртуальный слой полигона эллипса зоны 2-го и 3-го пояса
        uri = "Polygon?crs=epsg:{}".format(self.project.crs().postgisSrid())
        virtLayer = QgsVectorLayer(uri, name_layer, "memory")
        virtProvider = virtLayer.dataProvider()
        virtProvider.addAttributes([QgsField("wells_name",QVariant.String),
                                    QgsField("radius_name",QVariant.String)])
        # Объекты виртуального слоя
        fet_zone = QgsFeature()
        # Геометрия эллипсов
        for feature in self.features:
            geom_center = feature.geometry().get()
            R = feature['r_n{}'.format(num_zone)]
            r = feature['r_s{}'.format(num_zone)]
            D = feature['r_w{}'.format(num_zone)]
            d = feature['r_o{}'.format(num_zone)]
            ellipse_line = self.draw_ellipse(geom_center,R,D,r,d,self.azimut)
            # Запись геометрии в слой
            fet_zone.setGeometry(ellipse_line)
            fet_zone.setAttributes([feature['name'],'R{}'.format(num_zone)])
            virtProvider.addFeature(fet_zone)
        # Обновление слоя
        virtLayer.updateFields()
        virtLayer.updateExtents()
        del virtProvider
        # Добавление слоя на карту, привязка стиля
        self.project.addMapLayer(virtLayer, True)
        virtLayer.loadNamedStyle(
            self.plugin_dir + '/legstyle/{}.qml'.format(name_style)
        )

    """ Создание слоя зоны I-го пояса
    """
    def layer_qudrat_zone(self):
        # Виртуальный слой полигона квадрата зоны 1-го пояса
        uri = "Polygon?crs=epsg:{}".format(self.project.crs().postgisSrid())
        virtLayer = QgsVectorLayer(uri, "zona R1", "memory")
        virtProvider = virtLayer.dataProvider()
        virtProvider.addAttributes([QgsField("R_name",QVariant.String)])
        # Объекты виртуального слоя
        fet_zone = QgsFeature()
        # Геометрия квадрата
        for feature in self.features:
            geom_center = feature.geometry().get()
            # Координаты центра эллипса
            center_x = geom_center.x()
            center_y = geom_center.y()
            radius = feature['r1']
            # Геометрия точки углов квадрата
            pointNO = QgsPointXY(center_x+radius,center_y+radius)
            pointNW = QgsPointXY(center_x-radius,center_y+radius)
            pointSW = QgsPointXY(center_x-radius,center_y-radius)
            pointSO = QgsPointXY(center_x+radius,center_y-radius)
            # Геометрия квадрата
            qudrat_geom = QgsGeometry.fromPolygonXY([
                [pointNO,pointNW,pointSW,pointSO]
            ])
            qudrat_geom.rotate(self.azimut, QgsPointXY(center_x,center_y))
            # Запись геометрии в слой
            fet_zone.setGeometry(qudrat_geom)
            fet_zone.setAttributes(['R1'])
            virtProvider.addFeature(fet_zone)
        # Обновление слоя
        virtLayer.updateFields()
        virtLayer.updateExtents()
        del virtProvider
        # Добавление слоя на карту, привязка стиля
        self.project.addMapLayer(virtLayer, True)
        virtLayer.loadNamedStyle(self.plugin_dir + '/legstyle/zso.qml')

    """ Отрисовка стрелочек
    """
    def arrow_dist (self):
        # Создание геометрии стрелки, поворот геометрии и запись в слой
        def create_arrgeom (arr_end,radius,nz,nr):
            arrow_geom = QgsGeometry.fromPolylineXY([arr_begin,arr_end])
            arrow_geom.rotate(self.azimut-90, QgsPointXY(arr_begin))
            # Запись геометрии в слой
            fet_zone.setGeometry(arrow_geom)
            fet_zone.setAttributes([nr,nz,radius])
            virtProvider.addFeature(fet_zone)
        # Определение координат конца стрелки и аттритбута названия радиуса
        def write_in_layer (rN,rW,rS,rO,nz):
            # Подготовка атрибутов для поля r_name
            nr=['R','D','r','d']
            if rW == rO: nr=['R','d','r','d']
            if nz == 1: nr=['r','r','r','r']
            arr_end = QgsPointXY(center_x+rN,center_y)
            create_arrgeom(arr_end,rN,nz,nr[0])
            arr_end = QgsPointXY(center_x,center_y+rW)
            create_arrgeom(arr_end,rW,nz,nr[1])
            arr_end = QgsPointXY(center_x-rS,center_y)
            create_arrgeom(arr_end,rS,nz,nr[2])
            arr_end = QgsPointXY(center_x,center_y-rO)
            create_arrgeom(arr_end,rO,nz,nr[3])

        # Виртуальный слой линий стрелок радиусов зон
        uri = "LineString?crs=epsg:{}".format(self.project.crs().postgisSrid())
        virtLayer = QgsVectorLayer(uri, "arrow", "memory")
        virtProvider = virtLayer.dataProvider()
        virtProvider.addAttributes([QgsField("r_name",QVariant.String),
                                    QgsField("n_zone",QVariant.Int),
                                    QgsField("dist",QVariant.Double)])
        # Объекты виртуального слоя
        fet_zone = QgsFeature()
        # Геометрия стрелок
        for feature in self.features:
            geom_center = feature.geometry().get()
            # Координаты скважины
            center_x = geom_center.x()
            center_y = geom_center.y()
            arr_begin = QgsPointXY(center_x,center_y)
            # Радиусы III-ей зоны ЗСО
            if self.fields_check[0]:
                write_in_layer(feature['r_n3'],
                               feature['r_w3'],
                               feature['r_s3'],
                               feature['r_o3'],
                               3)
            # Радиусы II-ой зоны ЗСО
            if self.fields_check[1]:
                write_in_layer(feature['r_n2'],
                               feature['r_w2'],
                               feature['r_s2'],
                               feature['r_o2'],
                               2)
            # Радиусы I-ой зоны ЗСО
            if self.fields_check[2]:
                write_in_layer(feature['r1'],
                               feature['r1'],
                               feature['r1'],
                               feature['r1'],
                               1)
     # Обновление слоя
        virtLayer.updateFields()
        virtLayer.updateExtents()
        del virtProvider
        # Добавление слоя на карту, привязка стиля
        self.project.addMapLayer(virtLayer, True)
        virtLayer.loadNamedStyle(self.plugin_dir + '/legstyle/zso_arrow.qml')
