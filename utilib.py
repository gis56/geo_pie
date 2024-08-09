from qgis.core import (
                        QgsProject,
                        QgsVectorLayer,
                        QgsFeature
                      )

class EncDec():
    item = ['utf-8', 'Windows-1251']
    enc = item[0]
    err = 'replace'
    dec = item[0]

    def get_codelist(self):
        return self.item

    def set_enc(self,index):
        if index == 0:
            self.err = 'replace'
            self.enc = self.item[0]
        else:
            self.err = 'strict'
            self.enc = self.item[index-2]

    def set_dec (self, index):
        self.dec = self.item[index]

    def get_str (self, string):
        if self.enc == self.dec:
            return string
        else:
            return string.encode(self.enc, errors=self.err).decode(self.dec)

    def get_utfstr(self, string):
        try:
            str_enc = string.encode(self.enc, errors=self.err).decode()
            return str_enc
        except UnicodeError:
            self.err = 'replace'
            str_enc = string.encode(self.enc, errors=self.err).decode()
            return str_enc

    def get_utf2sel(self, string):
        str_enc = string.encode('utf-8').decode(self.enc)
        return str_enc

# ----------------------------------------------------------------------------
# Создание слоя (пока точек, потом сделать универсальным)
# и дабавление его на карту (потом сделать возвращение виртуального слоя,
# а добавление и компановка слоев будет в другом месте.
# geomattr - список таплов геометрии и атрибутов объектов слоя
# layer_name -  имя слоя
# attr_list - список атрибутов слоя
# ----------------------------------------------------------------------------
def maplayer (geomattr, layer_name, attr_list, layer_type):

    project = QgsProject.instance()
    uri = "{}?crs=epsg:{}".format(layer_type, project.crs().postgisSrid())
    virtLayer = QgsVectorLayer(uri, layer_name, "memory")
    virtProvider = virtLayer.dataProvider()
    virtProvider.addAttributes(attr_list)

    vlayer_fet = QgsFeature()
    for fet in geomattr:
        geom, attr = fet
        vlayer_fet.setGeometry(geom)
        vlayer_fet.setAttributes(attr)
        virtProvider.addFeature(vlayer_fet)
    virtLayer.updateFields()
    virtLayer.updateExtents()
    del virtProvider

    project.addMapLayer(virtLayer, True)

    return virtLayer
