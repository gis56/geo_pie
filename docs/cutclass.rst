=====================
Классы  *curwells.py*
=====================

:any:`GpPolycut`
:any:`GpRivers`

.. py:class:: GpPolycut [objCutline](feature, data, extrem, cutname)

   :param QgsFeature feature: Объект линии разреза;
   :type feature: QgsFeature_ 

   :param Iterator data: Объекты (QgsFeature_) полигонального слоя;
   :type data: Iterator_ 
   
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


   .. py:method:: get(scale=1)

      Возращает кортеж данных для создания слоя:

        1. Список кортежей геометрии и аттрибутов пересечения;
        2. Наменование слоя;
        3. Список полей атрибутивной таблицы;
        4. Тип слоя;
        5. *False* - чтобы слой не добавлялся в список слоев сразу после создания.

      Если небыло найдено пересечений возвращает *False*.

      :param Int scale: Вертикальный масштаб;
      :type scale: Int_

      :param QgsGeometry profile_geom: Геометрия профиля разреза.
      :type profile_geom: QgsGeometry_

      :return: Данные для формирования слоя. List_: [tuple_ (QgsGeometry_, List_ [str_, str_]), str_, List_ [QgsField_], str_, bool_]
      :rtype: Tuple_

      :return: *False* - если нет пересечений
      :rtype: bool_

.. _str : https://docs.python.org/3/library/stdtypes.html#text-sequence-type-str
.. _List : https://docs.python.org/3/library/stdtypes.html#lists
.. _float : https://docs.python.org/3/library/stdtypes.html#numeric-types-int-float-complex
.. _Int : https://docs.python.org/3/library/stdtypes.html#numeric-types-int-float-complex
.. _QgsGeometry : https://qgis.org/pyqgis/3.34/core/QgsGeometry.html#module-QgsGeometry
.. _QgsFeature : https://qgis.org/pyqgis/3.34/core/QgsFeature.html#module-QgsFeature
.. _QgsField : https://qgis.org/pyqgis/3.34/core/QgsField.html#module-QgsField> 
.. _bool : https://docs.python.org/3/library/stdtypes.html#boolean-type-bool
.. _Tuple : https://docs.python.org/3/library/stdtypes.html#tuples
.. _Iterator :  https://docs.python.org/3/library/stdtypes.html#iterator-types


.. py:class:: GpRivers


.. py:class:: GpRuler

   
.. py:class:: GpProfiles


.. py:function:: add(kind=None)

   Return a list of random ingredients as strings.

   :param kind: Optional "kind" of ingredients.
   :type kind: list[str] or None
   :return: The ingredients list.
   :rtype: list[str]


Исходный код
------------

.. highlight:: pyton
   :linenothreshold: 5

.. code-block:: python

   class GpPolycut(objCutline):
       def __init__ (self, feature, data, extrem, cutname):
           # геометрию брать в cut_intersect_plg
           # преобразовать там же x1 b x2 во float
           #self.geom = feature.geometry()
           self.cutname = f'{cutname}'
           self.lines = self.cut_intersect_plg(feature, *data)

           #self.extrem = extrem
           self.verical = self.y_view(extrem)
           self.ftype, self.fname, self.lname = self.type_field(*data)

       # становиться не нужен
       """
       def add(self, data):
           inters = self.cut_intersect_plg(self.geom, *data)
           unions = self.union_intersect(inters)
           lines = []
           for line in unions:
               x1, x2, lcode = line
               lines.append((float(x1), float(x2), lcode))
           return lines
       """

       def get(self, profil_geom, scale=1):
           if self.lines:
               feat = []
               y1, y2 = self.vertical
               #y1, y2 = self.y_view(self.extrem)
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

             return (feat,f"{self.lname}-{self.cutname}",fields,"Polygon",False
         else: return False
