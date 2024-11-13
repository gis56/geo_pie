Классы создания разреза
=======================   

Описание классов и методов
--------------------------
.. py:function:: lumache.get_random_ingredients(kind=None)

   Return a list of random ingredients as strings.

   :param kind: Optional "kind" of ingredients.
   :type kind: list[str] or None
   :return: The ingredients list.
   :rtype: list[str]

.. py:class:: GpAges
.. py:method:: get(scale=1)

   Метод возращает данные для создания слоя

   :param int scale: Масштаб
   :type scale: Intrger
   :return: Кортеж
   :rtype: tuple

Исходный код
------------

.. highlight:: pyton
   :linenothreshold: 5

.. code-block:: python

   class GpAges(objCutline):
       def __init__ (self, feature, data, extrem, cutname):
           self.geom = feature.geometry()
           self.cutname = f'{cutname}'
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
               y1, y2 = self.y_view(self.extrem)
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


.. note::

   | Внимание, внимане говорит германия
