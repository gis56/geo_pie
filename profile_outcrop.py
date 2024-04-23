from qgis.core import (QgsProject,
                       QgsVectorLayer,
                       QgsField,
                       QgsFields,
                       QgsFeature,
                       QgsGeometry,
                       QgsPointXY,
                       QgsVectorFileWriter,
                       QgsWkbTypes,
                       QgsRasterDataProvider,
                       QgsFeatureRequest,
                       Qgis)
from qgis.PyQt.QtCore import QVariant
import math

""" Поиск персечений линии разреза с объектами карты и
создание профиля разреза
featureOutcrop - объект слоя разреза (линия разреза)
nameOutcrop
layerSRTM
vertScale
"""
class incision_maker():

    def __init__(self,
                 featureOutcrop,
                 layerSRTM,
                 vertScale = 10,
                 step_point = 10) :
        self.geomOutcrop = featureOutcrop.geometry().mergeLines()
        self.featureOutcrop = featureOutcrop
        self.nameOutcrop = self.set_nameOutcpor()
        self.srtm = layerSRTM.dataProvider()
        self.vertScale = vertScale
        self.step_point = step_point
        self.geomProfile, self.altMin, self.altMax = self.line_profile()


    def set_nameOutcpor(self):
        try:
            return  self.featureOutcrop['name']
        except:
            return  str(self.featureOutcrop['id'])

    def line_profile(self):
        """ Создание геометрии профиля разреза и
        нахождение максимальной и минимальной высоты профиля
        функция используется во время инициализации объекта

        """
        # Уплотнение линии точками
        densify_outcrop_line = self.geomOutcrop.densifyByDistance(
                                                    self.step_point)
        # Получение списка вершин уплотненной линии разреза
        densify_outcrop_vertex = densify_outcrop_line.asPolyline()
        # Получение координат вершин уплотненной линии разреза и
        # расстояний от начала до каждой из вершин
        profile_points = list()
        alt_list = list()
        for i, vertx in enumerate(densify_outcrop_vertex) :
            # Получение высоты с растра strm (координата Y профиля)
            point_outcrop = QgsPointXY(densify_outcrop_line.vertexAt(i))
            altitude_rastr = self.srtm.sample(point_outcrop,1)[0]
            alt_list.append(altitude_rastr)
            # Получение расстояний от начала линии разреза
            # до текущей точки (координата X профиля)
            distance_outcrop = densify_outcrop_line.distanceToVertex(i)
            # Накопление списка точек профиля
            profile_points.append(QgsPointXY(distance_outcrop,
                                             altitude_rastr*self.vertScale))
        # Создание геометрии линии профиля
        profile_line = QgsGeometry.fromPolylineXY(profile_points)
        # Упрощение линии профиля
        simplify_profile_line = profile_line.simplify(5)
        # Сглаживание линии профиля
        smooth_profile_line = simplify_profile_line.smooth(5, 0.4, 1, 180)
        # Упрощение линии профиля после сглаживания (удаление лишних точек)
        simplify_profile_line = smooth_profile_line.simplify(0.5)

        return (simplify_profile_line, min(alt_list), max(alt_list))

    """
        Создание слоя профиля разреза
        Линейная тема с полем названия разреза в атрибутах
    """
    def get_layerProfile (self) :
        profile_virtLayer = QgsVectorLayer("LineString?crs=epsg:28410",
                                           "profile_line-"+self.nameOutcrop,
                                           "memory")
        profile_virtProvider = profile_virtLayer.dataProvider()
        profile_virtProvider.addAttributes([QgsField("name",QVariant.String)])

         # Добавление объектов слоя
        fet = QgsFeature()
        fet.setGeometry(self.geomProfile)
        fet.setAttributes([self.nameOutcrop])
        profile_virtProvider.addFeature(fet)
        del profile_virtProvider

        return profile_virtLayer

    """
        Создание слоев скважин и фильтров на профиле
    """
    def get_wells_filters (self, wells_point_vectorLayer) :

        # Виртуальный слой скважин на разрезе
        wells_virtLayer = QgsVectorLayer("LineString?crs=epsg:28410",
                                         "wells_line",
                                         "memory")
        wells_virtProvider = wells_virtLayer.dataProvider()
        wells_virtProvider.addAttributes([QgsField("name",QVariant.String),
                                          QgsField("head",QVariant.Double),
                                          QgsField("depth",QVariant.Double)])
        # Виртуальный слой фильтров на разрезе
        filter_virtLayer = QgsVectorLayer("LineString?crs=epsg:28410",
                                          "filter_line",
                                          "memory")
        filter_virtProvider = filter_virtLayer.dataProvider()
        filter_virtProvider.addAttributes([QgsField("name",QVariant.String),
                                           QgsField("depth",QVariant.Double),
                                           QgsField("l_code",QVariant.Int)])


        # Поиск скважин на линии разреза и извлечение
        # расстояний от начала линии
        # Извлечение параметров скважины из атрибутов
        outcrop_vertex = self.geomOutcrop.asPolyline()
        wells_fet = QgsFeature()
        filter_fet = QgsFeature()
        # Надо чтобы начальное значение было равно Hmax
        altMin = list()

        for i, out_vertx in enumerate(outcrop_vertex):
            point_wells = QgsPointXY(self.geomOutcrop.vertexAt(i))

            request = QgsFeatureRequest().setDistanceWithin(
                                    QgsGeometry.fromPointXY(point_wells),1)
            request.setLimit(1)
            head_well = 0
            bottom_well = 0
            # Один элемент. Как обойтись без цикла?
            for feature in wells_point_vectorLayer.getFeatures(request):
                # Y - координата устья скважины
                head_well = feature['head']
                # Y - координата глубины скважины
                bottom_well = head_well - feature['depth']
                altMin.append(bottom_well)
                # Строка с данными фильтров текущей скважины
                filters_well = feature['filters']

            if (head_well != 0) and (bottom_well != 0):
                # X - координата скважины на профиле
                distance_wells = self.geomOutcrop.distanceToVertex(i)
                wells_field = [
                    feature['name'],
                    feature['head'],
                    feature['depth']
                ]
                well_ln = [
                    QgsPointXY(distance_wells, bottom_well*self.vertScale),
                    QgsPointXY(distance_wells, head_well*self.vertScale)
                ]
                wells_line = QgsGeometry.fromPolylineXY(well_ln)
                wells_fet.setGeometry(wells_line)
                wells_fet.setAttributes(wells_field)
                wells_virtProvider.addFeature(wells_fet)

                filters_well = '10:50:100033;10:50:100031;10:25:100032;'\
                    '10:100:100033;10:15:100034'
                # Y координаты фильтра
                # Проверить filters_well <> NULL

                for filter in filters_well.split(';'):
                    filter_tmp = filter.split(':')
                    filter_ln = [
                        QgsPointXY(
                            distance_wells,
                            self.vertScale*(head_well - float(filter_tmp[0]))
                        ),
                        QgsPointXY(
                            distance_wells,
                            self.vertScale*(head_well - float(filter_tmp[1]))
                        )
                    ]
                    filter_line = QgsGeometry.fromPolylineXY(filter_ln)
                    filter_fet.setGeometry(filter_line)
                    filter_field = [
                        feature['name'],
                        float(filter_tmp[1])-float(filter_tmp[0]),
                        int(filter_tmp[2])
                    ]

                    filter_fet.setAttributes(filter_field)
                    filter_virtProvider.addFeature(filter_fet)

        self.altMin = min(altMin)

        filter_virtLayer.updateFields()
        del filter_virtProvider

        wells_virtLayer.updateExtents()
        del wells_virtProvider

        return (wells_virtLayer, filter_virtLayer)


    """
    Создание слоя геологических возрастов
        agegeo_layer  - векторный слой полигона
        attr - имя поля с аттрибутами возрастов

        !!! Если начало линии замкнуто на границу полигона, то ошибка.
        Не может найти вторую вершину отрезка, потому что она одна
        То же самое думаю справедливо и для конца. Проверить и исправить.
    """
    def get_Age ( self, agegeo_layer, attr ) :

        agegeo_geom = self.cut_line (self.geomOutcrop, agegeo_layer, attr)

        # Создание слоя из списка отрезков.
        cutln_virtLayer = QgsVectorLayer("Polygon?crs=epsg:28410",
                                         "cutline",
                                         "memory"
                                         )
        cutln_virtProvider = cutln_virtLayer.dataProvider()
        cutln_virtProvider.addAttributes([QgsField("id",QVariant.Int),
                                          QgsField("length",QVariant.Double),
                                          QgsField(attr,QVariant.Int)])

        pnt_fet = QgsFeature()

        for i, dict_lit in enumerate(agegeo_geom) :
            # Геометрия прямоугольного шаблона
            litol_line = [
                QgsPointXY(dict_lit['X1'], self.altMin*self.vertScale),
                QgsPointXY(dict_lit['X2'], self.altMin*self.vertScale),
                QgsPointXY(dict_lit['X2'],self.altMax*self.vertScale),
                QgsPointXY(dict_lit['X1'],self.altMax*self.vertScale)
            ]
            litol_plg_geom = QgsGeometry.fromPolygonXY([litol_line])
            # Разрезание прямоугольных полигонов линией профиля
            result, new_geometries, point_xy = \
                litol_plg_geom.splitGeometry(
                    self.geomProfile.asPolyline(),
                    False, False
                )
            pnt_fet.setGeometry(new_geometries[0])
            pnt_fet.setAttributes([i, dict_lit['length'], dict_lit[attr]])
            cutln_virtProvider.addFeature(pnt_fet)

        del cutln_virtProvider

        return cutln_virtLayer

    """
        Создание слоя профиля пересечения изолиний с линией разреза
    """
    def get_Izline ( self, izline_layer, attr ) :

        list_cut_point = self.cut_ln_ln (self.geomOutcrop, izline_layer, attr)

        # Линия на разрезе соединяющая точки пересечения линии разреза
        # с другими линиями на карте
        cutline_virtLayer = QgsVectorLayer("LineString?crs=epsg:28410",
                                           "cutline",
                                           "memory"
                                           )
        cutline_virtProvider = cutline_virtLayer.dataProvider()
        cutline_virtProvider.addAttributes([
            QgsField("id",QVariant.Int),
            QgsField(attr,QVariant.String)
            ]
        )
        # Создание слоя с линиями
        pro_line_fet = QgsFeature()
        # Сортировка точек. Нужна только для отрисовки линий.
        def custom_key ( dict_pnt ) :
            return dict_pnt['X1']
        list_cut_point.sort(key=custom_key)

        # Дополнение конечными точками линии профиля
        # outcrop_length = self.geomOutcrop.length()
        start_pnt = {'X1': 0,
                     attr: list_cut_point[0][attr]}
        list_cut_point.append({'X1': self.geomOutcrop.length(),
                               attr: list_cut_point[-1][attr]})
        for i, dict_pnt in enumerate(list_cut_point) :
            # Проверка на повторяющуюся точку (может появляться если
            # изолиния проходит через вершину линии разреза)
            if start_pnt['X1'] != dict_pnt['X1'] :
                cut_line_list = [
                    QgsPointXY(start_pnt['X1'],start_pnt[attr]*self.vertScale),
                    QgsPointXY(dict_pnt['X1'],dict_pnt[attr]*self.vertScale)
                ]
                cut_line_geom = QgsGeometry.fromPolylineXY(cut_line_list)
                pro_line_fet.setGeometry(cut_line_geom)
                pro_line_fet.setAttributes(
                    [i, str(start_pnt[attr])+" - "+str(dict_pnt[attr])]
                )
                cutline_virtProvider.addFeature(pro_line_fet)

            start_pnt = dict_pnt

        cutline_virtLayer.updateFields()
        del cutline_virtProvider

        return cutline_virtLayer

    """
        Создание слоя пересечения линий рек с разрезом
    """
    def get_River ( self, river_layer, attr ) :

        list_cut_point = self.cut_ln_ln (self.geomOutcrop, river_layer, attr)
        if list_cut_point :
            # Точки на разрезе пересечения
            # линии разреза с другими линиями на карте
            cutpoint_virtLayer = QgsVectorLayer("Point?crs=epsg:28410",
                                                "cutpoint",
                                                "memory")
            cutpoint_virtProvider = cutpoint_virtLayer.dataProvider()
            cutpoint_virtProvider.addAttributes([
                QgsField("id",QVariant.Int),
                QgsField(attr,QVariant.String),
                QgsField("XOC",QVariant.Double),
                QgsField("YOC",QVariant.Double)
                ]
            )
            # Создание слоя с точками
            pro_point_fet = QgsFeature()
            for i, dict_pnt in enumerate(list_cut_point) :
                # Числовой атрибут с высотами используется
                # в качестве второй координаты.
                if isinstance(dict_pnt[attr], str) or dict_pnt[attr] == None:
                    altY = self.srtm.sample(dict_pnt['point'],1)[0]
                    cut_pnt_geom = QgsGeometry.fromPointXY(
                        QgsPointXY(dict_pnt['X1'], altY*self.vertScale)
                    )
                else :
                    cut_pnt_geom = QgsGeometry.fromPointXY(
                        QgsPointXY(
                            dict_pnt['X1'],
                            dict_pnt[attr]*self.vertScale
                        )
                    )
                pro_point_fet.setGeometry(cut_pnt_geom)
                pro_point_fet.setAttributes([
                    i, dict_pnt[attr],
                    dict_pnt['point'].x(),
                    dict_pnt['point'].y()
                    ]
                )
                cutpoint_virtProvider.addFeature(pro_point_fet)

            cutpoint_virtLayer.updateFields()
            del cutpoint_virtProvider
            return cutpoint_virtLayer
        else :
            return False

    """
        Создание слоя пересечения линий рек с разрезом
    """
    def get_Sea ( self, river_plg_layer, attr ) :
        sea_dict_list = self.cut_line(self.geomOutcrop, river_plg_layer, attr)

        if sea_dict_list :
            # Создание слоя из списка отрезков.
            sea_virtLayer = QgsVectorLayer("Polygon?crs=epsg:28410",
                                           "sea",
                                           "memory"
                                           )
            sea_virtProvider = sea_virtLayer.dataProvider()
            sea_virtProvider.addAttributes([QgsField("id",QVariant.Int),
                                            QgsField("length",QVariant.Double),
                                            QgsField(attr,QVariant.String)])

            sea_features = QgsFeature()
            Hmin = 0
            for i, sea_dict in enumerate(sea_dict_list) :
                # Поиск середины
                media_pnt = (sea_dict['X2'] - sea_dict['X1'])/2 + sea_dict['X1']
                segmt_line = QgsGeometry.fromPolylineXY([
                    QgsPointXY(sea_dict['X1OC'], sea_dict['Y1OC']),
                    QgsPointXY(sea_dict['X2OC'], sea_dict['Y2OC'])
                    ]
                )
                # Поиск высоты расположения поверхности реки
                # в центре масс линии разреза
                altY = self.srtm.sample(sea_dict['centr'].asPoint(),1)[0]
                # Геометрия прямоугольного шаблона
                sea_line = [
                    QgsPointXY(sea_dict['X1'],altY*self.vertScale),
                    QgsPointXY(sea_dict['X2'],altY*self.vertScale),
                    QgsPointXY(media_pnt, (altY-10)*self.vertScale)
                ]
                sea_plg_geom = QgsGeometry.fromPolygonXY([sea_line])

                sea_features.setGeometry(sea_plg_geom)
                sea_features.setAttributes(
                    [i, sea_dict['length'], sea_dict[attr]]
                )
                sea_virtProvider.addFeature(sea_features)

            sea_virtLayer.updateFields()
            del sea_virtProvider

            return sea_virtLayer
        else :
            return False

    """
        Создание слоев шкал
    """
    def get_dial(self, outcrop_vectorLayer, map_scale=100000 ):

        outcrop_length = self.geomOutcrop.length()

        dial_ln_virtLayer = QgsVectorLayer("LineString?crs=epsg:28410",
                                           "dial_line",
                                           "memory"
                                           )
        dial_ln_virtProvider = dial_ln_virtLayer.dataProvider()

        dial_ln_virtProvider.addAttributes([QgsField("name",QVariant.String),
                                            QgsField("l_code",QVariant.Int)])
        dial_ln_fet = QgsFeature()

        # Отрисовка нулевого уровня
        tmp_ln = [QgsPointXY(0, 0), QgsPointXY(outcrop_length, 0)]
        dial_field = [ "Нулевая отметка", 100001 ]
        dial_line = QgsGeometry.fromPolylineXY(tmp_ln)

        dial_ln_fet.setGeometry(dial_line)
        dial_ln_fet.setAttributes(dial_field)
        dial_ln_virtProvider.addFeature(dial_ln_fet)

        # Отрисовка боковых шкал
        add_one_sm = map_scale/(100*self.vertScale)
        Hmin = math.floor(self.altMin/add_one_sm)*add_one_sm
        Hmax = math.ceil(self.altMax/add_one_sm)*add_one_sm

        tmp_ln = [
            QgsPointXY(0, Hmin*self.vertScale),
            QgsPointXY(0, Hmax*self.vertScale)
        ]
        dial_field = [ "Левая шкала", 100002 ]
        dial_line = QgsGeometry.fromPolylineXY(tmp_ln)

        dial_ln_fet.setGeometry(dial_line)
        dial_ln_fet.setAttributes(dial_field)
        dial_ln_virtProvider.addFeature(dial_ln_fet)

        tmp_ln = [
            QgsPointXY(outcrop_length, Hmin*self.vertScale),
            QgsPointXY(outcrop_length, Hmax*self.vertScale)
        ]
        dial_field = [ "Правая шкала", 100002 ]
        dial_line = QgsGeometry.fromPolylineXY(tmp_ln)

        dial_ln_fet.setGeometry(dial_line)
        dial_ln_fet.setAttributes(dial_field)
        dial_ln_virtProvider.addFeature(dial_ln_fet)

        # Отрисовка пересечений линий разреза
        cross_point_list = self.cross_outcrop(outcrop_vectorLayer)
        if len(cross_point_list) :
            for cross_point in cross_point_list :
                tmp_ln = [
                    QgsPointXY(cross_point['X1'],
                    Hmin*self.vertScale),
                    QgsPointXY(cross_point['X1'],
                    Hmax*self.vertScale)
                ]
                dial_field = [ str(cross_point['id']), 100001 ]
                dial_line = QgsGeometry.fromPolylineXY(tmp_ln)

                dial_ln_fet.setGeometry(dial_line)
                dial_ln_fet.setAttributes(dial_field)
                dial_ln_virtProvider.addFeature(dial_ln_fet)


        dial_ln_virtLayer.updateFields()
        del dial_ln_virtProvider

        # Значение вертикальной шкалы
        dial_pnt_virtLayer = QgsVectorLayer("Point?crs=epsg:28410",
                                            "dial_point","memory")
        dial_pnt_virtProvider = dial_pnt_virtLayer.dataProvider()

        dial_pnt_virtProvider.addAttributes([
            QgsField("name",QVariant.String),
            QgsField("alt_value",QVariant.Double),
            QgsField("l_code",QVariant.Int)
            ]
        )
        dial_pnt_fet = QgsFeature()
        '''
        tmp_point = [
            QgsPointXY(0,Hmin*self.vertScale),
            QgsPointXY(0,Hmax*self.vertScale),
            QgsPointXY(outcrop_length,Hmin*self.vertScale),
            QgsPointXY(outcrop_length,Hmax*self.vertScale)
        ]
        dial_field = [
            ['Левая шкала',round(Hmin, 2),100013],
            ['Левая шкала',round(Hmax, 2),100014],
            ['Правая шкала',round(Hmin, 2),100013],
            ['Правая шкала',round(Hmax, 2),100014]
        ]
        '''
        tmp_point =[]
        dial_field = []

        i = add_one_sm
        while i <= Hmax:
            tmp_point.append(QgsPointXY(0, i*self.vertScale))
            dial_field.append(['Левая шкала', round(i, 2), 100011])
            tmp_point.append(QgsPointXY(outcrop_length, i*self.vertScale))
            dial_field.append(['Правая шкала', round(i, 2), 100012])
            i += add_one_sm
        i = 0
        while i >= Hmin:
            tmp_point.append(QgsPointXY(0, i*self.vertScale))
            dial_field.append(['Левая шкала', round(i, 2), 100011])
            tmp_point.append(QgsPointXY(outcrop_length, i*self.vertScale))
            dial_field.append(['Правая шкала', round(i, 2), 100012])
            i -= add_one_sm

        for i, point in enumerate(tmp_point):
            dial_point = QgsGeometry.fromPointXY(point)
            dial_pnt_fet.setGeometry(dial_point)
            dial_pnt_fet.setAttributes(dial_field[i])
            dial_pnt_virtProvider.addFeature(dial_pnt_fet)

        # Обязательно сделать апдейт полей во всех созданных
        # слоях для занесения данных
        dial_pnt_virtLayer.updateFields()
        del dial_pnt_virtProvider

        return (dial_ln_virtLayer, dial_pnt_virtLayer)

    """
        Создание линий пересечения разрезов
    """

    def cross_outcrop ( self, outcrop_vectorLayer) :
        temp_outlayer = QgsVectorLayer("LineString?crs=epsg:28410",
                                       "temp_line","memory")
        temp_outlayerProvider = temp_outlayer.dataProvider()
        temp_outlayerProvider.addAttributes([QgsField("id", QVariant.Int)])

        outFeatures = outcrop_vectorLayer.getFeatures()

        list_cross_point=list()
        for outFeature in outFeatures :
            if self.featureOutcrop != outFeature :
                temp_outlayerProvider.addFeature(outFeature)

        temp_outlayer.updateFields()

        list_cross_point = self.cut_ln_ln(self.geomOutcrop,
                                          temp_outlayer,
                                          'id')

        del temp_outlayerProvider, temp_outlayer
        return list_cross_point

    '''
    Нарезка линии разреза линейным слоем (пока конкретно изолиниями).
    Потом сделать алгоритм универсальным с параметром необходимого атрибута
        outcrop_geom - геометрия линииразреза
        ln_layer - линейная тема
        attr - атрибут из пересекающего слоя. Для линии обязательно
        числовой, используется в качестве второй координаты Y.
    '''
    def cut_ln_ln ( self, outcrop_geom, ln_layer, attr ) :

        #global offset_profile_Y

        outcrop_verts = outcrop_geom.asPolyline()
        start_pnt = outcrop_verts.pop(0)
        start_length = 0
        list_cut_point = []
        # Итерация по вершинам линии разреза
        for vert in outcrop_verts :
            end_pnt = vert
            cut_ln_geom = QgsGeometry.fromPolylineXY([start_pnt, end_pnt])
            # Определение области отрезка и запрос на пересечение
            rect = cut_ln_geom.boundingBox()
            request = QgsFeatureRequest().setFilterRect(rect).setFlags(
                QgsFeatureRequest.ExactIntersect)

             # Перебор изолиний пересакающих область текущего отрезка
            for ln_ln in ln_layer.getFeatures(request):
                ln_ln_geom = ln_ln.geometry()
                pnt_intrsct_geom = ln_ln_geom.intersection(cut_ln_geom)

                # Проверка результата пересечения на Multy вид
                geomSingleType = QgsWkbTypes.isSingleType(
                    pnt_intrsct_geom.wkbType())
                if geomSingleType :
                    # Поиск расстояния от начала сегмента
                    # до начала отрезка ( выбор ближайшего конца отрезка)
                    if not pnt_intrsct_geom.isEmpty() :
                        dist = pnt_intrsct_geom.asPoint().distance(start_pnt)
                        X1 = start_length + dist
                        dict_pnt = {'X1': X1,
                                    attr: ln_ln[attr],
                                    'point': pnt_intrsct_geom.asPoint()}
                        list_cut_point.append(dict_pnt)
                else :
                    for divid_cut in pnt_intrsct_geom.asGeometryCollection() :
                        # Поиск расстояния от начала сегмента до начала
                        # отрезка ( выбор ближайшего конца отрезка)
                        dist = divid_cut.asPoint().distance(start_pnt)
                        X1 = start_length + dist
                        dict_pnt = {'X1': X1,
                                    attr: ln_ln[attr],
                                    'point': divid_cut.asPoint()}
                        list_cut_point.append(dict_pnt)
            # Наращивание расстояние от начала линии разреза
            start_length += cut_ln_geom.length()
            # Конечная точка текущего сегмента становится начальной
            # следующего сегмента
            start_pnt = end_pnt

        return list_cut_point


    """
        Процедура пересечения линии сполигоном на карте и
        построение линии пересечений на профиле
    """
    def cut_line ( self, outcrop_geom, polygon_layer, attr ) :
        '''
        Поиск расстояния от начала сегмента до начала отрезка
        ( выбор ближайшего конца отрезка)
        На входе:
            start_vert - начальная координата отрезка
            segment_geom - геометрия сегмента
        На выходе расстояние до начала отрезка

        !!! Если начало линии замкнуто на границу полигона, то ошибка.
        Не может найти вторую вершину отрезка, потому что она одна
            То же самое думаю справедливо и для конца. Проверить и исправить.
            И может быть даже если любая вершина разреза попадает
            на границу полигона
        '''
        def start_to_begin_vertex ( start_vert, segment_geom) :
            pbe = segment_geom.asPolyline()
            dist_b = pbe[0].distance(start_vert)
            dist_e = pbe[1].distance(start_vert)
            if dist_b < dist_e :
                return pbe, dist_b
            else :
                return pbe, dist_e

        pointsVert = outcrop_geom.asPolyline()
        start_pnt = pointsVert.pop(0)
        start_length = 0
        list_start_length = []
        list_dict_proline = []
        # Итерация по вершинам линии разреза
        for vert in pointsVert :
            end_pnt = vert
            cut_ln_geom = QgsGeometry.fromPolylineXY([start_pnt, end_pnt])

            # Определение области отрезка и запрос на пересечение
            rect = cut_ln_geom.boundingBox()
            request = QgsFeatureRequest().setFilterRect(rect).setFlags(
                QgsFeatureRequest.ExactIntersect)

            # Перебор объектов литологии пересакающих область текущего отрезка
            for polygon_feature in polygon_layer.getFeatures(request):
                polygon_geom = polygon_feature.geometry()
                intrsct_geom = polygon_geom.intersection(cut_ln_geom)
                # Проверка результата пересечения на Multy вид
                geomSingleType = QgsWkbTypes.isSingleType(
                    intrsct_geom.wkbType())
                if geomSingleType :
                    # Поиск расстояния от начала сегмента до начала отрезка
                    # выбор ближайшего конца отрезка)
                    if not intrsct_geom.isEmpty() :
                        intrsct_line, dist = start_to_begin_vertex(
                            start_pnt, intrsct_geom)
                        X1 = start_length + dist
                        X2 = X1 + intrsct_geom.length()
                        dict_proline = {'X1': X1,
                                        'X2': X2,
                                        'length': intrsct_geom.length(),
                                        attr: polygon_feature[attr],
                                        'X1OC': intrsct_line[0].x(),
                                        'Y1OC': intrsct_line[0].y(),
                                        'X2OC': intrsct_line[1].x(),
                                        'Y2OC': intrsct_line[1].y(),
                                        'centr': intrsct_geom.centroid()}
                        list_dict_proline.append(dict_proline)

                else :
                    for divid_cut in intrsct_geom.asGeometryCollection() :
                        if divid_cut.wkbType() != 1 :
                        # Поиск расстояния от начала сегмента до начала
                        # отрезка ( выбор ближайшего конца отрезка)
                            divid_line, dist = start_to_begin_vertex(
                                start_pnt, divid_cut)
                            X1 = start_length + dist
                            X2 = X1 + divid_cut.length()
                            dict_proline = {'X1': X1,
                                            'X2': X2,
                                            'length': divid_cut.length(),
                                            attr: polygon_feature[attr],
                                            'X1OC': divid_line[0].x(),
                                            'Y1OC': divid_line[0].y(),
                                            'X2OC': divid_line[1].x(),
                                            'Y2OC': divid_line[1].y(),
                                            'centr': divid_cut.centroid()}
                            list_dict_proline.append(dict_proline)

            # Наращивание расстояние от начала линии разреза
            start_length += cut_ln_geom.length()
            list_start_length.append(start_length)
            # Конечная точка текущего сегмента становится
            # начальной следующего сегмента
            start_pnt = end_pnt
        # Объединение отрезков с одинаковым атрибутом
        # на границе вершин разреза.
        list_start_length.pop(-1)
        for vert in list_start_length :
            # Инициализация индексов
            prev_index = (-1)
            post_index = (-1)
            for i, dict_proline in enumerate(list_dict_proline) :
                if vert == dict_proline['X1'] :
                    post_current = dict_proline
                    post_index = i
                if vert == dict_proline['X2'] :
                    prev_current = dict_proline
                    prev_index = i
            if ( prev_index != (-1) ) and ( post_index != (-1) ) :
                if prev_current[attr] == post_current[attr] :
                    # Аттрибуты нужно обновлять все для актуальности.
                    # Центр линии, если нужен, искать здесь по линии
                    # из трех координат!!!
                    segmt_line = QgsGeometry.fromPolylineXY(
                        [QgsPointXY(prev_current['X1OC'],
                                    prev_current['Y1OC']),
                         QgsPointXY(prev_current['X2OC'],
                                    prev_current['Y2OC']),
                         QgsPointXY(post_current['X2OC'],
                                    post_current['Y2OC'])])

                    merge_up = {'X2': post_current['X2'],
                                'length': prev_current['length'] + \
                                post_current['length'],
                                'X2OC': post_current['X2OC'],
                                'Y2OC': post_current['Y2OC'],
                                'centr': segmt_line.centroid()}

                    list_dict_proline[prev_index].update(merge_up)
                    list_dict_proline.pop(post_index)

        return list_dict_proline
