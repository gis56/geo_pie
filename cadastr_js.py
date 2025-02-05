# -*- coding: utf-8 -*-
import os
from qgis.PyQt.QtCore import QVariant
from qgis.core import (
                       Qgis,
                       QgsField,
                       QgsGeometry,
                       QgsPointXY,
                       QgsJsonUtils,
                       QgsProject
                      )

from .pie_dial import formGeojsontoShape
from .utilib import *

import requests
#-----------------------------------------------------------------------------
# Создание слоя точек
#----------------------------------------------------------------------------
def cadastrshp(iface):
    url = 'https://nspd.gov.ru/api/geoportal/v2/search/geoportal?\
        thematicSearchId=1&query='
    dialog = formGeojsontoShape()
    result = dialog.run()
    if result:
        file = dialog.cadastr_path()

        with open (file, 'r') as cadastr_file:
            cad_ids = cadastr_file.readlines()
        txt=''
        feats = []
        for cad_id in cad_ids:
            cad_id = cad_id.rstrip('\n')
            response = requests.get(f'{url}{cad_id}', verify=False)
            json = response.text
            #json = response.content
            #num_section = line.split(':')
            txt += url+'\n'
            feats.extend(QgsJsonUtils.stringToFeatureList(json))
        cadastr_file.close()

        #vlayer = maplayer(feats, "point_csv", attr, "Point")

        project = QgsProject.instance()
        uri = "Polygon?crs=epsg:3857"
        virtLayer = QgsVectorLayer(uri, "cadastr_zone", "memory")
        virtProvider = virtLayer.dataProvider()
        #virtProvider.addAttributes(attr_list)
        virtProvider.addFeatures(feats)
        virtLayer.updateFields()
        virtLayer.updateExtents()
        del virtProvider

        project.addMapLayer(virtLayer, True)



    else: txt = "Отмена."
    del dialog
    #txt = "Ok."
    #txt = 'json'
    lvl = Qgis.Success
    iface.messageBar().pushMessage("Заврешено", txt, level=lvl, duration=5)
