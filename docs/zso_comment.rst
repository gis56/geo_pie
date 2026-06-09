======================
Зоны санитарной охраны
======================

.. function:: zsozone()

.. py:function:: draw_qudrat (center, radius, azimut, wname)

   :module: geo_pie.zso

   :param QgsPointXY center: координаты скважины

   :param float_ radius: расстояние от скважины до стороны квадрата
   
   :param Int_ azimut: Угол поворота зоны вдоль направления потока
   
   :param str_ wname: наименование скважины

   :return: Кортеж геометрий граней и вершин первой зоны
   :rtype: Tuple_ (QgsGeometry_, QgsGeometry_ | QgsGeometry_, False)

.. literalinclude:: _templates/zso_zone.py
   :language: python
   :encoding: utf-8 
   :lines: 133-154
   :lineno-match:
   :linenos:

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
