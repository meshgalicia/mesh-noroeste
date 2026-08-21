# Avisos de terceiros

Mesh Noroeste utiliza os seguintes compoñentes e servizos de terceiros.
Cada elemento conserva a súa propia licenza ou condicións de uso.

## Software

### Leaflet 1.9.4

- Proxecto: https://leafletjs.com/
- Código: https://github.com/Leaflet/Leaflet
- Licenza: BSD-2-Clause
- Cárgase no navegador mediante un CDN e non se inclúe unha copia do
  seu código neste repositorio.

### Leaflet.markercluster 1.5.3

- Código: https://github.com/Leaflet/Leaflet.markercluster
- Licenza: MIT
- Os recursos distribúense en
  `frontend/vendor/leaflet.markercluster/`.
- O texto da licenza acompaña o código en
  `frontend/vendor/leaflet.markercluster/MIT-LICENCE.txt`.

### msgpack para Python

- Código: https://github.com/msgpack/msgpack-python
- Licenza: Apache-2.0
- Dependencia de execución declarada en `pyproject.toml`.

### jsonschema para Python

- Código: https://github.com/python-jsonschema/jsonschema
- Licenza: MIT
- Dependencia opcional utilizada na validación e nas probas.

### XlsxWriter

- Código: https://github.com/jmcnamara/XlsxWriter
- Licenza: BSD-2-Clause
- Dependencia de execución declarada en `pyproject.toml`.
- Utilízase para xerar os informes experimentais en formato XLSX.

## Cartografía, datos e servizos

O mapa consulta ou representa materiais procedentes de OpenStreetMap,
CARTO, Esri World Imagery, Malha Portugal, Comunidade O Zulo e
MeshCore Map.

- OpenStreetMap: datos e teselas sometidos ás condicións publicadas pola
  OpenStreetMap Foundation. A interface mostra a atribución correspondente.
- CARTO: provedor dunha das capas base; a súa atribución móstrase xunto coa
  de OpenStreetMap.
- Esri World Imagery: capa de imaxe de Esri e os seus provedores; a interface
  conserva a atribución indicada para a capa.
- Malha Portugal, Comunidade O Zulo e MeshCore Map: fontes externas de
  datos. Mesh Noroeste consulta as súas interfaces
  públicas e normaliza os datos mediante adaptadores propios.

Eses datos, teselas, marcas e servizos non se relicencian como parte de
Mesh Noroeste. O seu uso continúa sometido ás condicións, licenzas e
políticas publicadas por cada provedor.
