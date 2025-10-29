=====================
Документация Geo Pie.
=====================

**Geo Pie** набор скриптов для любимой жены. Модуль  для **QGis**.

 Чтобы установить модуль необходимо скачать его из репозитария *Github* по `ссылке <https://github.com/gis56/geo_pie.git>`_.
 Папку с файлами модуля разместить в директории плагинов *QGis*.

* путь для *Windows*:: 

   User/AppData/Roaming/QGIS/QGIS3/profiles/default/python/plugins/
 

* путь для *Ubuntu*::

   usr/share/qgis/python/plugins/

* Зайти в диалог управления модулями и добавить ссылку на репозитарий :menuselection:`Управление модулями --> Параметры модуля --> Добавить репозитарий`::
 
   http://gis56.github.io/plugins.xml

.. image:: /image/repo.png
     :alt: Добавить репозитарий
     :height: 355px
     :width: 545px
     :scale: 60 %
     :align: center

Установить модуль **Geo Pie** через диалог Управления модулями.


В меню QGis выбрать пункт :menuselection:`Вектор  --> Мои скрипты`.
Опции меню будут содержать скрипты модуля.

.. toctree::
   :maxdepth: 2 
   :caption: Содержание:

   curwells
   matrix
   zso

.. toctree::
   :maxdepth: 2 
   :caption: Комментарии:

   dialogs
   cutclass
