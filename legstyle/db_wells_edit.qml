<!DOCTYPE qgis PUBLIC 'http://mrcc.com/qgis.dtd' 'SYSTEM'>
<qgis styleCategories="Actions" version="3.28.0-Firenze">
  <attributeactions>
    <defaultAction key="Canvas" value="{cd1517b4-259c-413f-875d-c3c5cae63735}"/>
    <actionsetting isEnabledOnlyWhenEditable="0" action="from save_attributes.probe_sql_actn import DBEditor&#xd;&#xa;dbe = DBEditor()&#xd;&#xa;dbe.name_wells = &quot;[%name%]&quot;&#xd;&#xa;dbe.id_layer = &quot;[% @layer_id %]&quot;&#xd;&#xa;dbe.id_wells = [%@id%]&#xd;&#xa;dbe.longitude = [% $y %]&#xd;&#xa;dbe.latitude = [% $x %]&#xd;&#xa;dbe.run()" name="Данные скважин" icon="" notificationMessage="" capture="0" shortTitle="" type="1" id="{cd1517b4-259c-413f-875d-c3c5cae63735}">
      <actionScope id="Canvas"/>
      <actionScope id="Feature"/>
    </actionsetting>
  </attributeactions>
  <layerGeometryType>0</layerGeometryType>
</qgis>
