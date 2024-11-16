=====================
Классы  *curwells.py*
=====================

:any:`objCutline`
   | :any:`objCutline.cut_intersect_ln`
   | :any:`objCutline.cut_intersect_plg`
   | :any:`objCutline.type_field`
   | :any:`objCutline.y_view`

:any:`GpPolycut`
   | :any:`GpPolycut.lines`
   | :any:`GpPolycut.get`
   
:any:`GpLinecut`
   | :any:`GpLinecut.points`
   | :any:`GpLinecut.get`
 

.. py:class:: objCutline

   Родительский класс для: :any:`GpPolycut`, :any:`GpLinecut`.

   .. py:method:: cut_intersect_ln (feat_cutline, lines_layer, field)

      Поиск пересечений линии разреза с линейной темой карты и вычисление абсциссы точек пересечения для отображения на разрезе.
      Возвращает список кортежей. Tuple_ (*Абсцисса*: (Float_), *Имя объекта слоя*: (str_), *Идентификатор объекта слоя*: (Int_))

      :param QgsFeature feat_cutline: Объект линии разреза;
      :type feat_cutline: QgsFeature_

      :param QgsVectorLayer lines_layer: Слой карты ``LineGeometry``;
      :type lines_layer: QgsVectorLayer_

      :param QgsField field: Наименование поля атрибутов линейного слоя с именами объектов.
      :type field: QgsField_

      :return: Список ординат с идентификаторами.
      :rtype: List_

   .. py:method:: cut_intersect_plg (feat_cutline, polygons_layer, field)

      Поиск пересечений линии разреза с полигональной темой карты и вычисление абсцисс начала и конца интервалов пересечения для отображения на разрезе.
      Возвращает список кортежей. Tuple_ (*Абсцисса начала*: (Float_), *Абсцисса конца*: (Float_), *Имя объекта слоя*: (str_), *Идентификатор объекта слоя*: (Int_))

      :param QgsFeature feat_cutline: Объект линии разреза;
      :type feat_cutline: QgsFeature_

      :param QgsVectorLayer lines_layer: Слой карты ``PolygonGeometry``;
      :type lines_layer: QgsVectorLayer_

      :param QgsField field: Наименование поля атрибутов линейного слоя с именами объектов.
      :type field: QgsField_

      :return: Список ординат интервала с идентификаторами.
      :rtype: List_

   .. py:method:: type_field (layer, field)

      Определяет название слоя и типа поля атрибутов.

      :param QgsVectorLayer layer: Слой карты;
      :type layer: QgsVectorLayer_

      :param QgsField field: Поле атрибута слоя.
      :type field: QgsField_

      :return: *Тип атрибута*:(QVariant_), *Имя атрибута*:(QgsField_), *Имя слоя*:(str_).
      :rtype: Tuple_

   .. py:method:: y_view (extrem)

      Расчитывает вертикальный диапазон для обектов на разрезе исходя из максимального и минимального значения высот профиля.

      :param Tuple_ extrem: Слой карты;
      :type layer: Tuple_

      :return: *нижнее значение*:(Float_), *верхнее значение*:(Float_).
      :rtype: Tuple_


.. py:class:: GpPolycut (feature, polygons, extrem, cutname)

   Наследует класс :any:`objCutline`.

   :param QgsFeature feature: Объект линии разреза;
   :type feature: QgsFeature_ 

   :param Iterator polygons: Объекты (QgsFeature_) полигонального слоя;
   :type polygons: Iterator_ 
   
   :param List extrem: Экстремальныу значения (float_) высоты и глубины;
   :type extrem: List_ 
   
   :param str cutname: Идентификатор линии разреза.
   :type cutname: str_


   .. py:attribute:: cutname

      Наименование линии разреза. Используется для формирования имени слоя.

      :type: str_

   .. py:attribute:: lines

      Кортежи с интервалами пересечения.
      Tuple_: (начало: (float_), конец: (float_), идентификатор: (str_))

      :type: List_ 


   .. py:method:: get(profile_geom, scale=1)

      На основе координат начала и конца интервала пересечения взятых из :any:`GpPolycut.lines` строит полигоны и обрезает их линией профиля разреза **profil_geom**.
      Формирует и возращает кортеж данных для создания слоя:

        1. Список кортежей геометрии и аттрибутов пересечения List_ [Tuple_ (*Геометрия*: (QgsGeometry_), *Атрибуты*: (str_))];
        2. Наменование слоя: str_;
        3. Список полей атрибутивной таблицы List_ [*Поля*: (QgsField_)];
        4. Тип слоя: str_;
        5. bool_ = *False* - чтобы слой не добавлялся в список слоев сразу после создания.

      Если небыло найдено пересечений возвращает *False*.

      :param QgsGeometry profile_geom: Геометрия профиля разреза.
      :type profile_geom: QgsGeometry_

      :param Int scale: Вертикальный масштаб;
      :type scale: Int_

      :return: Данные для формирования слоя.
      :rtype: Tuple_

      :return: *False* - если нет пересечений
      :rtype: bool_


.. py:class:: GpLinecut (feature, lines, extrem, cutname)

   Наследует класс :any:`objCutline`.

   :param QgsFeature feature: Объект линии разреза;
   :type feature: QgsFeature_ 

   :param Iterator lines: Объекты (QgsFeature_) линейного слоя;
   :type data: Iterator_ 
   
   :param List extrem: Экстремальныу значения (float_) профиля;
   :type extrem: List_ 
   
   :param str cutname: Идентификатор линии разреза.
   :type cutname: str_


   .. py:attribute:: cutname

      Наименование линии разреза. Используется для формирования имени слоя.

      :type: str_

   .. py:attribute:: points

      Кортежи с точками пересечения.
      Tuple_: (*абсцисса*: (float_), идентификатор: (str_))

      :type: List_ 


   .. py:method:: get(profile_geom, scale=1)

      На основе координат начала и конца интервала пересечения взятых из :any:`GpPolycut.lines` строит полигоны и обрезает их линией профиля разреза **profil_geom**.
      Формирует и возращает кортеж данных для создания слоя:

        1. Список кортежей геометрии и аттрибутов пересечения List_ [Tuple_ (*Геометрия*: (QgsGeometry_), *Атрибуты*: (str_))];
        2. Наменование слоя: str_;
        3. Список полей атрибутивной таблицы List_ [*Поля*: (QgsField_)];
        4. Тип слоя: str_;
        5. bool_ = *False* - чтобы слой не добавлялся в список слоев сразу после создания.

      Если небыло найдено пересечений возвращает *False*.

      :param QgsGeometry profile_geom: Геометрия профиля разреза.
      :type profile_geom: QgsGeometry_

      :param Int scale: Вертикальный масштаб;
      :type scale: Int_

      :return: Данные для формирования слоя.
      :rtype: Tuple_

      :return: *False* - если нет пересечений
      :rtype: bool_


.. _str : https://docs.python.org/3/library/stdtypes.html#text-sequence-type-str
.. _List : https://docs.python.org/3/library/stdtypes.html#lists
.. _float : https://docs.python.org/3/library/stdtypes.html#numeric-types-int-float-complex
.. _Int : https://docs.python.org/3/library/stdtypes.html#numeric-types-int-float-complex
.. _QgsVectorLayer : https://qgis.org/pyqgis/3.34/core/QgsVectorLayer.html#module-QgsVectorLayer
.. _QgsGeometry : https://qgis.org/pyqgis/3.34/core/QgsGeometry.html#module-QgsGeometry
.. _QgsFeature : https://qgis.org/pyqgis/3.34/core/QgsFeature.html#module-QgsFeature
.. _QgsField : https://qgis.org/pyqgis/3.34/core/QgsField.html#module-QgsField> 
.. _bool : https://docs.python.org/3/library/stdtypes.html#boolean-type-bool
.. _Tuple : https://docs.python.org/3/library/stdtypes.html#tuples
.. _Iterator : https://docs.python.org/3/library/stdtypes.html#iterator-types
.. _QVariant : https://doc.qt.io/qt-6/qvariant.html#QVariant  


.. py:class:: GpRuler

   
.. py:class:: GpProfiles


Исходный код
------------

.. highlight:: pyton
   :linenothreshold: 5

.. code-block:: python

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
                        ID = featline.id()
                        cutpoints.append((x_beg+dist, featline[field], ID))
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
                        x1 = v1.distance(sectvert_beg)+x_beg
                        x2 = v2.distance(sectvert_beg)+x_beg
                        if x1 > x2: x1, x2 = x2, x1
                        cutpoints.append((float(x1), float(x2), feat[field]))
            # Наращивание расстояние от начала линии разреза
            x_beg += interval_geom.length()
            sectvert_beg = sectvert_end

        return self.union_intersect (sorted(cutpoints, key=lambda x: x[0]))

    #-------------------------------------------------------------------------
    # Объединение соседних полигонов с одинаковым признаком
    #-------------------------------------------------------------------------
    def union_intersect (self, data_list):

        index = 0
        while index < len(data_list)-2:
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

   #-----------------------------------------------------------------------------
   #     GpRivers - Класс пересечения рек с линией разреза
   #-----------------------------------------------------------------------------
   class GpRivers(objCutline):
       def __init__(self, feature, rivers, extrem, cutname):
           self.geom = feature.geometry()
           self.cutname = f'{cutname}'
           self.extrem = extrem
           self.points = self.add(rivers)
           self.ftype, self.fname, self.lname = self.type_field(*rivers)

       def add(self, rivers):
           verts = self.cut_intersect_ln(self.geom, *rivers)
           points = []
           for vert in verts:
               x, name, ID = vert
               points.append((float(x), name))
           return points

       def get(self, scale=1):
           if self.points:
               feat = []
               y1, y2 = self.y_view(self.extrem)
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

                #QgsField("name", QVariant.String)
               return (feat, f"{self.lname}-{self.cutname}",fields,
                       "LineString",False)
           else: return False
