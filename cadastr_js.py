# -*- coding: utf-8 -*-
import os
from qgis.PyQt.QtCore import QVariant
from qgis.core import (
                       Qgis,
                       QgsField,
                       QgsFields,
                       QgsGeometry,
                       QgsPointXY,
                       QgsJsonUtils,
                       QgsProject
                      )

from .pie_dial import formGeojsontoShape
from .utilib import *

import requests
from requests import Session
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

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

        # Чтение из списка ссылок
        # и получения json с серевера
        with open (file, 'r') as cadastr_file:
            cad_ids = cadastr_file.readlines()
        cadastr_file.close()

        retries = Retry(total=5, backoff_factor=0.1,
                        status_forcelist=[500, 502, 503, 504])
        session = Session()
        session.mount('http://', HTTPAdapter(max_retries=retries))
        session.mount('https://', HTTPAdapter(max_retries=retries))

        feats = []
        for cad_id in cad_ids:
            cad_id = cad_id.rstrip('\n')

            try:
                #response = requests.get(f'{url}{cad_id}', verify=False)
                response = session.get(f'{url}{cad_id}', verify=False)
                txt = 'Ok.'
            except requests.ConnectionError as e:
                txt = f'Ошибка подключения: {e}'
            except requests.Timeout as e:
                txt = f'Ошибка тайм-аута: {e}'
            except requests.RequestException as e:
                txt = f'Ошибка запроса: {e}'

            json = response.text
            #json = response.content
            fields = QgsJsonUtils.stringToFields(json)
            feats.extend(QgsJsonUtils.stringToFeatureList(json, fields))

        """
        # чтение json с компьютера
        txt = "Поля\n"
        with open(file,'r') as json_file:
            json = json_file.read()
        json_file.close()
        fields = QgsJsonUtils.stringToFields(json)
        fieldS = QgsFields()
        for field in fields:
            if not (field.type() == 8):
                fieldS.append(field)
                txt += f'{field.name()} | {field.type()}\n'
        feats = QgsJsonUtils.stringToFeatureList(json, fields)
        """

        #vlayer = maplayer(feats, "point_csv", attr, "Point")

        project = QgsProject.instance()
        uri = "Polygon?crs=epsg:3857"
        virtLayer = QgsVectorLayer(uri, "cadastr_zone", "memory")
        virtProvider = virtLayer.dataProvider()
        virtProvider.addAttributes(fields)
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
