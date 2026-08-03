# Mesh Noroeste

Mapa regional independiente para visualizar redes Meshtastic y MeshCore
en el noroeste peninsular y Portugal.

Este repositorio es una implementación nueva escrita desde cero. No contiene
código copiado de Meshtastic-es-map ni de otros mapas sin licencia compatible.

## Licencias

Copyright © 2026 Elena Musk.

El software propio de este repositorio se distribuye bajo la licencia
[GNU Affero General Public License v3.0 o posterior](LICENSE)
(`AGPL-3.0-or-later`).

La documentación propia se distribuye bajo
[Creative Commons Atribución-CompartirIgual 4.0 Internacional](LICENSES/CC-BY-SA-4.0.txt)
(`CC-BY-SA-4.0`).

Los componentes de terceros conservan sus respectivas licencias.
Los avisos y atribuciones están recogidos en
[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

Estas licencias no se aplican a los datos, identificadores, posiciones,
observaciones, teselas cartográficas ni otros materiales obtenidos de
fuentes externas. Esos contenidos permanecen sometidos a las condiciones de
sus fuentes respectivas. La distribución de licencias se explica con más
detalle en [LICENSES/README.md](LICENSES/README.md).

## Objetivos iniciales

- Integrar Meshtastic y MeshCore.
- Obtener datos de Meshview España, Malha Portugal, Comunidade O Zulo y MeshCore Map.
- Normalizar los datos en un formato común.
- Mantener persistencia histórica regional.
- Generar datos estáticos para un frontend Leaflet.
- Ofrecer una interfaz accesible y adaptada a dispositivos móviles.

## Estado actual

El backend clean-room ya dispone de:

- contrato público `mesh-noroeste.data/v1`;
- persistencia de nodos, conexiones y ejecuciones en SQLite;
- clientes HTTPS con límites de tiempo y tamaño;
- adaptadores y colectores para Meshview España, Malha Portugal,
  Comunidade O Zulo y MeshCore Map;
- normalización y persistencia de los traceroutes publicados por Malha;
- generación de `manifest.json` y de `nodes.json`, `edges.json`,
  `stats.json`, `meta.json` y `configuration-warnings.json` dentro de
  generaciones inmutables;
- filtrado común de Meshtastic y MeshCore mediante nueve áreas regionales;
- comandos de recolección, publicación, poda y comprobación;
- actualización automatizada mediante temporizadores de systemd;
- activación atómica de cada generación mediante un único manifiesto;
- poda diaria con retención absoluta de 30 días para las observaciones
  completas y cursores mínimos de deduplicación;
- pruebas automatizadas y validación de contratos.

El acceso a Malha conserva en `cache/` un archivo de cookies y la última
respuesta JSON válida. Ambos quedan fuera de Git. El cliente únicamente
reutiliza las cookies entregadas por la propia fuente y no intenta eludir
sus mecanismos de protección HTTP.

Las conexiones persistidas se consolidan por identificador, conservando la
observación más reciente. Solo se incluyen en `edges.json` cuando ambos
extremos sobreviven al mismo filtro regional aplicado a `nodes.json`, por lo
que no se generan conexiones colgantes.

El frontend Leaflet ya dispone de filtros, búsqueda accesible, panel de
detalle, estadísticas, traceroutes dirigidos, geolocalización local,
agrupaciones diferenciadas por red, navegación móvil, controles táctiles y
soporte para alto contraste. El detalle de los nodos Meshtastic incluye
avisos automáticos de configuración cuando existe análisis disponible.
La primera versión estable está publicada en `https://mapa.mesh.gal/`.
El mapa anterior permanece separado en `https://mesh.tuiter.ovh/`.

El comportamiento implementado y los pendientes funcionales están
documentados en [docs/FUNCTIONAL.md](docs/FUNCTIONAL.md).

La instalación operativa carga
`/etc/mesh-noroeste/mesh-noroeste.env`. Este archivo define
`MESH_EXCLUSIONS_PATH=/etc/mesh-noroeste/exclusions.json`, una lista privada
fuera de Git que se aplica antes de almacenar y publicar datos.

La lista inicial está vacía. Si el archivo configurado desaparece o contiene
un JSON inválido, los colectores se detienen antes de descargar o modificar
SQLite.

Los comandos manuales que necesiten esta configuración deben cargar primero
el mismo entorno:

```console
set -a
. /etc/mesh-noroeste/mesh-noroeste.env
set +a
.venv/bin/mesh-noroeste purge-node meshtastic:!identificador
```

El identificador canónico completo debe añadirse previamente a
exclusions.json.

## Estado de la versión estable

La política de retención SQLite está cerrada, documentada, validada y
desplegada sobre la base operativa. Las observaciones completas de nodos y
conexiones se eliminan al superar 30 días, incluida la última fila de cada
fuente. Unos cursores mínimos conservan únicamente los identificadores y
marcas temporales necesarios para impedir la reinserción de snapshots antiguos.
La primera poda real no alteró el conjunto público y una recolección posterior
confirmó que los datos caducados no reaparecen.

El sistema de símbolos de los nodos está terminado y comprobado a tamaño real
en móvil. Las formas exteriores identifican familias funcionales y las marcas
interiores diferencian los principales roles Meshtastic sin depender solo del
color.

En móvil, el panel de leyenda y filtros muestra primero los filtros por rol y
tipo, después la antigüedad y finalmente la leyenda informativa. Los filtros se
abren directamente y el comportamiento de escritorio permanece sin cambios.

Mesh Noroeste genera ya su propio documento bruto de análisis en
`cache/configuration-analysis.json`. El analizador consulta exclusivamente la
API pública de Meshview España, escribe el resultado de forma atómica y se
ejecuta mediante un temporizador de systemd cada seis horas. Las actualizaciones
del mapa leen esa ruta mediante `MESH_CONFIGURATION_WARNINGS_PATH`; no existe
dependencia operativa del contenedor, almacenamiento ni código del mapa
anterior.

La primera versión estable está publicada y mantiene separado el mapa
anterior. Las mejoras posteriores se desarrollarán sin alterar el contrato
público ni presentar como activas funciones que aún no estén implementadas y
verificadas.

El mapa de alcance observado mediante RF o MQTT y una futura versión completa
de España se desarrollarán posteriormente como proyectos separados.

## Validación

La comprobación completa del proyecto se ejecuta con:

    ./scripts/check-project.sh

El script valida la sintaxis, ejecuta todas las pruebas automatizadas,
comprueba los contratos públicos y revisa la integridad del diff de Git.
Para JavaScript utiliza Node.js o, si no está instalado, Docker.

## Uso local

```console
.venv/bin/mesh-noroeste collect-meshview
.venv/bin/mesh-noroeste collect-malha
.venv/bin/mesh-noroeste collect-ozulo
.venv/bin/mesh-noroeste collect-meshcore
.venv/bin/mesh-noroeste check
.venv/bin/mesh-noroeste publish
.venv/bin/mesh-noroeste prune
```

Por defecto, SQLite se guarda en `MESH_STATE_DIR/mesh-noroeste.db` y los
documentos públicos se escriben en `MESH_DATA_DIR`. El análisis opcional
de configuración se lee desde `MESH_CONFIGURATION_WARNINGS_PATH`. Si el
archivo falta o es inválido, el mapa publica explícitamente el análisis
como no disponible sin bloquear la actualización general. Malha utiliza
`cache/malha-pt.cookies` y `cache/malha-pt.json` dentro del directorio raíz
del proyecto.

La publicación aplica automáticamente la región formada por Galicia, Asturias,
León, Zamora y cinco franjas de Portugal. La opción `--bounds SOUTH WEST NORTH
EAST` sustituye ese ámbito por un rectángulo explícito.

La respuesta JSON de `publish` informa del número de observaciones leídas,
nodos regionales publicados y conexiones incluidas en `edges.json`.

También pueden indicarse rutas explícitas:

```console
.venv/bin/mesh-noroeste collect-meshview \
  --database /ruta/mesh-noroeste.db

.venv/bin/mesh-noroeste collect-malha \
  --database /ruta/mesh-noroeste.db \
  --cookie-file /ruta/privada/malha-pt.cookies \
  --cache-file /ruta/privada/malha-pt.json

.venv/bin/mesh-noroeste collect-meshcore \
  --database /ruta/mesh-noroeste.db

.venv/bin/mesh-noroeste publish \
  --database /ruta/mesh-noroeste.db \
  --output /ruta/datos-publicos
```

La versión funcional de este repositorio se publica en
`https://mapa.mesh.gal/`. El proyecto anterior permanece separado y continúa
sirviéndose en `https://mesh.tuiter.ovh/`.
