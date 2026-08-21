# Contrato de datos normalizado

## Objetivo

El backend transforma las respuestas de cada fuente en un modelo común.

El frontend solo consumirá este contrato y no conocerá la estructura interna
de Malha Portugal, Comunidade O Zulo, MeshCore Map ni MeshCore Hub de
Mesh Galicia.

Versión inicial:

    mesh-noroeste.data/v1

## Principios

1. Todos los tiempos se expresan en UTC.
2. Las fechas públicas usan ISO 8601 con sufijo Z.
3. Las coordenadas usan grados decimales WGS84.
4. Los valores desconocidos se representan con null.
5. Un valor null nuevo no elimina automáticamente un valor válido anterior.
6. Cada nodo conserva las fuentes que contribuyeron a su registro.
7. Las respuestas originales se almacenan fuera de Git.
8. Meshtastic y MeshCore usan espacios de identificadores separados.
9. El frontend recibe los datos ya normalizados y consolidados.

## Redes

El campo `network` admite:

- `meshtastic`
- `meshcore`

El modo «Ambas» pertenece al frontend y no es una tercera red.

## Fuentes iniciales

El campo `source` admite:

- `malha_pt`
- `ozulo_map`
- `meshcore_map`
- `meshcore_hub`

Solo se acreditarán fuentes realmente utilizadas.

## Identificador canónico de nodo

El campo `id` combina la red con el identificador técnico.

Ejemplos:

    meshtastic:!a35b4144
    meshcore:0101010101010101010101010101010101010101010101010101010101010101

### Meshtastic

El identificador se normaliza como:

    !xxxxxxxx

Reglas:

- signo de exclamación inicial;
- ocho caracteres hexadecimales;
- letras minúsculas;
- ceros iniciales conservados.

Un nodo recibido desde Malha Portugal o Comunidade O Zulo debe generar el
mismo identificador canónico y un único registro consolidado.

### Adaptación de Malha Portugal

El colector utiliza el documento público:

    https://malha.meshtastic.pt/api/locations

La respuesta se descarga mediante HTTPS y se decodifica como JSON. La raíz
debe ser un objeto que incluya las listas `locations` y `traceroute_links`.

El acceso mantiene fuera de Git:

- `cache/malha-pt.cookies`, en formato Netscape/Mozilla y modo `0600`;
- `cache/malha-pt.json`, con la última respuesta válida y modo `0644`.

La caché solo se sustituye después de decodificar y validar correctamente el
documento. Una descarga fallida o una respuesta inválida no elimina la última
caché válida. El cliente reutiliza exclusivamente cookies entregadas por la
fuente y no almacena sus valores en registros públicos.

Correspondencia inicial de nodos:

| Origen | Campo normalizado |
|---|---|
| `hex_id` y `node_id` | `source_id` e `id` |
| `timestamp` | `observed_at` |
| `timestamp` | `position_updated_at` |
| `short_name` | `short_name` |
| `long_name` | `long_name` |
| `hw_model` | `hardware` |
| `role` | `role` |
| `latitude` | `latitude` |
| `longitude` | `longitude` |
| `altitude` | `altitude_m` |
| `avg_snr` | `metrics.snr_db` |
| `primary_channel` | `radio.channel` |

`timestamp` es un timestamp Unix expresado en segundos. `hex_id` y `node_id`
deben representar el mismo identificador Meshtastic de 32 bits. Los
identificadores duplicados, las coordenadas fuera de rango y la posición
`0,0` se rechazan.

Correspondencia inicial de traceroutes:

| Origen | Campo normalizado |
|---|---|
| `from_node_id` | `from_id` |
| `to_node_id` | `to_id` |
| `last_seen` | `last_seen` |
| `avg_snr` | `metrics.snr_db` |
| presencia en `traceroute_links` | `edge_type: traceroute` |
| sentido origen-destino | `directed: true` |

Los autoenlaces se descartan. Dos rutas recíprocas se conservan como
conexiones dirigidas diferentes, mientras que una ruta dirigida duplicada
dentro del mismo documento se rechaza.

Los `packet_links` quedan fuera de la integración inicial debido a anomalías
observadas en algunos identificadores y valores de radio.

Los traceroutes aceptados se almacenan en SQLite. Durante la publicación se
agrupan por identificador canónico y se conserva la observación con
`observed_at` más reciente. Una conexión solo se incorpora a `edges.json`
cuando `from_id` y `to_id` existen también en el `nodes.json` regional.

### Adaptación de Comunidade O Zulo

El colector utiliza los documentos públicos consolidados:

    https://mapa.mesh.comunidadeozulo.org/data/nodes.json
    https://mapa.mesh.comunidadeozulo.org/data/edges.json

Ambas respuestas se descargan mediante HTTPS y se decodifican como JSON.
La raíz de nodos debe ser un objeto con una lista `nodes`; la raíz de
conexiones debe ser un objeto con una lista `edges`.

Los nodos se identifican mediante `node_id` y se normalizan dentro del mismo
espacio canónico Meshtastic utilizado por Malha Portugal y el resto del
proyecto.
El adaptador puede conservar nombres, hardware, rol, posición, precisión,
altitud, telemetría, parámetros de radio, saltos y condición de gateway MQTT
cuando esos campos están presentes y son válidos.

Las conexiones utilizan `from_node`, `to_node`, `edge_type` y la información
temporal publicada por la fuente. Los autoenlaces se descartan. Las conexiones
repetidas se consolidan por identificador y se conserva la observación más
reciente.

Cada recolección sustituye atómicamente el snapshot de conexiones de
`ozulo_map`. Una conexión solo se incorpora a `edges.json` cuando sus dos
extremos sobreviven al mismo filtro regional aplicado a `nodes.json`.

### MeshCore

MeshCore Map publica como identificador estable una clave pública de
32 bytes. El adaptador la representa mediante 64 caracteres
hexadecimales en minúsculas:

    meshcore:<64 caracteres hexadecimales>

Reglas:

- no se deriva del nombre visible;
- los 32 bytes de `pk` se convierten directamente a hexadecimal;
- una cadena hexadecimal debe contener exactamente 64 caracteres;
- no se exponen claves privadas ni secretos;
- no se fusionan nodos únicamente porque compartan nombre;
- una clave ausente o mal formada invalida el registro.

### Adaptación de MeshCore Map

El colector utiliza el documento público compacto:

    https://map.meshcore.io/api/v1/nodes?binary=1&short=1

La respuesta se descarga mediante HTTPS y se decodifica como
MessagePack. La raíz debe ser una lista.

Correspondencia inicial:

| Origen | Campo normalizado |
|---|---|
| `pk` | `source_id` e `id` |
| `n` | `short_name` |
| `t` | `node_type` |
| `id` | `first_seen` |
| `ud` | `observed_at` |
| `ud` | `position_updated_at` |
| `lat` | `latitude` |
| `lon` | `longitude` |
| `p.freq` | `radio.frequency_mhz` |
| `p.bw` | `radio.bandwidth_khz` |
| `p.sf` | `radio.spreading_factor` |
| `p.cr` | `radio.coding_rate` |

La fuente no proporciona una fecha independiente para la posición, por
lo que `ud` se utiliza también como `position_updated_at`.

El campo `la` no se usa para calcular actividad o caducidad porque se
han observado fechas anómalas y valores futuros. La actividad se calcula
a partir de `ud`.

Los campos compactos `s` y `l` no se publican mientras su significado
completo no esté suficientemente documentado.

### Adaptación de MeshCore Hub de Mesh Galicia

El colector utiliza el endpoint autenticado de nodos:

    https://hub.mesh.gal/api/v1/nodes

La clave de lectura se recibe exclusivamente mediante
`MESHCORE_HUB_API_READ_KEY` y se envía en la cabecera `Authorization` como
token Bearer. La credencial no se incorpora al repositorio ni se incluye en
los resultados o mensajes de error del colector.

Los nodos y los anuncios se descargan como JSON mediante páginas con
`limit` y `offset`. Cada página debe declarar un total coherente y una misma
clave pública no puede repetirse dentro de la recolección de nodos.

Los anuncios proceden de:

    https://hub.mesh.gal/api/v1/advertisements

Cada recepción atribuida a un observer se normaliza conservando el nodo
emisor, el observer receptor, el hash del paquete, la fecha de recepción,
el SNR y la longitud de ruta cuando esos campos están disponibles. Una misma
recepción puede aparecer en páginas consecutivas si el Hub cambia durante la
paginación; el colector la deduplica por su identificador normalizado.

Correspondencia inicial:

| Origen | Campo normalizado |
|---|---|
| `public_key` | `source_id` e `id` |
| `name` | `short_name` |
| `adv_type` | `node_type` |
| `first_seen` | `first_seen` |
| `last_seen` | `observed_at` |
| `last_seen` | `position_updated_at` |
| `is_observer` | `is_observer` |
| `lat` | `latitude` |
| `lon` | `longitude` |

`public_key` debe contener exactamente 64 caracteres hexadecimales. Los tipos
`chat`, `repeater`, `room` o `server` y `sensor` se traducen respectivamente
a `client`, `repeater`, `room_server` y `sensor`; cualquier otro valor se
conserva como `unknown`.

Las coordenadas parciales son inválidas y el punto `0, 0` se descarta.
`is_observer` identifica que el propio dispositivo registrado por el Hub está
dedicado a observación. Se conserva de forma independiente de `node_type`: no
excluye el nodo ni modifica por sí solo su representación visual.

Las recepciones de anuncios se persisten como observaciones específicas y no
se convierten en `edges.json`: prueban que un observer recibió por radio un
paquete atribuido a un nodo, pero no demuestran una conexión directa entre
ambos extremos ni una ruta extremo a extremo.

## Publicación por generaciones

El punto de entrada estable para los consumidores es:

    frontend/data/manifest.json

El manifiesto utiliza el contrato `mesh-noroeste.manifest/v1`:

    {
      "schema": "mesh-noroeste.manifest/v1",
      "generation": "20260725T120000Z-0123456789abcdef0123456789abcdef",
      "generated_at": "2026-07-25T12:00:00Z",
      "documents": {
        "nodes.json": "generations/20260725T120000Z-0123456789abcdef0123456789abcdef/nodes.json",
        "edges.json": "generations/20260725T120000Z-0123456789abcdef0123456789abcdef/edges.json",
        "neighbor-info.json": "generations/20260725T120000Z-0123456789abcdef0123456789abcdef/neighbor-info.json",
        "observer-receptions.json": "generations/20260725T120000Z-0123456789abcdef0123456789abcdef/observer-receptions.json",
        "stats.json": "generations/20260725T120000Z-0123456789abcdef0123456789abcdef/stats.json",
        "meta.json": "generations/20260725T120000Z-0123456789abcdef0123456789abcdef/meta.json",
        "configuration-warnings.json": "generations/20260725T120000Z-0123456789abcdef0123456789abcdef/configuration-warnings.json"
      }
    }

`generation` es un identificador opaco. Cada ruta debe apuntar exactamente al
directorio indicado por ese identificador. Los siete documentos y el
manifiesto deben compartir el mismo `generated_at`.

Cada directorio de generación es inmutable. El backend escribe y sincroniza
sus siete documentos antes de sustituir `manifest.json` mediante una única
operación atómica. Si el proceso falla antes de ese reemplazo, el manifiesto
anterior y todos sus documentos continúan activos.

Los consumidores deben descargar primero `manifest.json` y utilizar
exclusivamente las rutas que contiene. Las rutas planas históricas no forman
parte de una instantánea coordinada. El servicio conserva las doce
generaciones más recientes.

## Documento de nodos

Archivo previsto:

    frontend/data/generations/<generation>/nodes.json

Estructura superior:

    {
      "schema": "mesh-noroeste.data/v1",
      "generated_at": "2026-07-25T12:00:00Z",
      "nodes": []
    }

Cada nodo tendrá esta forma general:

    {
      "id": "meshtastic:!a35b4144",
      "network": "meshtastic",
      "source_ids": {
        "malha_pt": "!a35b4144",
        "ozulo_map": "!a35b4144"
      },
      "sources": [
        "malha_pt",
        "ozulo_map"
      ],
      "short_name": "BRUMA",
      "long_name": "Bruma Connection",
      "hardware": "HELTEC_V4",
      "role": "CLIENT_MUTE",
      "node_type": null,
      "is_observer": null,
      "latitude": 43.123456,
      "longitude": -8.123456,
      "altitude_m": 120,
      "first_seen": "2026-07-20T09:10:00Z",
      "last_seen": "2026-07-25T11:58:00Z",
      "position_updated_at": "2026-07-25T11:50:00Z",
      "metrics": {
        "battery_percent": 76,
        "voltage_v": 4.02,
        "channel_utilization_percent": 8.5,
        "air_util_tx_percent": 1.2,
        "snr_db": 7.25,
        "rssi_dbm": -91
      },
      "radio": {
        "channel": "LongFast",
        "firmware": "2.x",
        "hops_away": 2,
        "mqtt_gateway": false,
        "frequency_mhz": null,
        "bandwidth_khz": null,
        "spreading_factor": null,
        "coding_rate": null
      },
      "status": {
        "active": true,
        "recent": false,
        "historical": false,
        "has_position": true
      }
    }

## Campos comunes

| Campo | Tipo | Descripción |
|---|---|---|
| `id` | string | Identificador canónico |
| `network` | string | Red del nodo |
| `source_ids` | object | Identificadores originales por fuente |
| `sources` | array | Fuentes que contribuyeron al registro |
| `short_name` | string/null | Nombre corto |
| `long_name` | string/null | Nombre largo |
| `hardware` | string/null | Modelo del dispositivo |
| `role` | string/null | Rol Meshtastic |
| `node_type` | string/null | Tipo MeshCore |
| `is_observer` | boolean/null | Dispositivo MeshCore dedicado a observación segundo a fonte |
| `latitude` | number/null | Latitud |
| `longitude` | number/null | Longitud |
| `altitude_m` | number/null | Altitud en metros |
| `first_seen` | string/null | Primera observación conservada |
| `last_seen` | string | Observación más reciente |
| `position_updated_at` | string/null | Fecha de la posición |
| `metrics` | object | Telemetría normalizada |
| `radio` | object | Información de red |
| `status` | object | Estado calculado |

Todos los campos mantienen una estructura estable aunque su valor sea null.

### Campos del objeto `radio`

Todos los nodos publican el mismo objeto `radio`. Los datos que una fuente no proporcione se representan mediante `null`.

| Campo | Tipo | Significado |
|---|---|---|
| `channel` | string/null | Canal o preset conocido |
| `firmware` | string/null | Versión de firmware |
| `hops_away` | integer/null | Saltos observados hasta el nodo |
| `mqtt_gateway` | boolean/null | Recepción atribuida a una pasarela MQTT |
| `frequency_mhz` | number/null | Frecuencia central en MHz |
| `bandwidth_khz` | number/null | Ancho de banda LoRa en kHz |
| `spreading_factor` | integer/null | Factor de ensanchamiento LoRa |
| `coding_rate` | integer/null | Coding rate informado por la fuente |

Los cuatro últimos campos conservan los parámetros estructurados publicados por MeshCore Map sin mezclarlos con el nombre del canal.

## Tipos MeshCore

El campo `node_type` admite inicialmente:

- `client`
- `repeater`
- `room_server`
- `sensor`
- `unknown`

Para Meshtastic:

    {
      "role": "CLIENT",
      "node_type": null,
      "is_observer": null
    }

Para MeshCore:

    {
      "role": null,
      "node_type": "repeater",
      "is_observer": false
    }

`is_observer` no es un tipo de anuncio MeshCore ni sustituye a `node_type`.
Solo MeshCore Hub proporciona actualmente este dato; en las observaciones de
otras fuentes su valor es `null`.

## Consolidación de observaciones

Cada fuente genera una observación independiente.

El normalizador las combina por identificador canónico siguiendo estas reglas:

1. `sources` contiene la unión ordenada de fuentes.
2. `source_ids` conserva el identificador original de cada fuente.
3. `first_seen` utiliza la fecha válida más antigua.
4. `last_seen` utiliza la fecha válida más reciente.
5. Los datos variables proceden de la observación válida más reciente.
6. Un valor null no sustituye automáticamente un dato anterior no nulo.
7. La posición se decide mediante `position_updated_at`.
8. No se fusionan nodos solo por nombre o coordenadas.
9. La procedencia elegida para cada campo se conserva internamente.

## Coordenadas

Una posición es válida cuando:

    -90 <= latitude <= 90
    -180 <= longitude <= 180

Se rechaza el punto `0, 0`.

No se corrigen automáticamente coordenadas intercambiadas o imposibles.

## Fechas

Las fuentes pueden entregar:

- segundos Unix;
- milisegundos Unix;
- microsegundos Unix;
- cadenas ISO 8601.

El normalizador produce:

    YYYY-MM-DDTHH:MM:SSZ

Una fecha inválida no se sustituye por la hora actual.

## Estado temporal

Variables previstas:

    ACTIVE_NODE_HOURS=24
    RECENT_NODE_DAYS=7
    HISTORICAL_NODE_DAYS=30

Interpretación:

- `active`: visto durante las últimas 24 horas;
- `recent`: visto hace más de 24 horas y hasta 7 días;
- `historical`: visto hace más de 7 días, dentro de la retención.

Estos estados deben ser mutuamente coherentes.

## Documento de conexiones

Archivo previsto:

    frontend/data/generations/<generation>/edges.json

Estructura superior:

    {
      "schema": "mesh-noroeste.data/v1",
      "generated_at": "2026-07-25T12:00:00Z",
      "edges": []
    }

Ejemplo:

    {
      "id": "meshtastic:neighbor:!a35b4144:!b1234567",
      "network": "meshtastic",
      "source": "ozulo_map",
      "from_id": "meshtastic:!a35b4144",
      "to_id": "meshtastic:!b1234567",
      "edge_type": "neighbor",
      "directed": false,
      "last_seen": "2026-07-25T11:58:00Z",
      "metrics": {
        "snr_db": 5.5,
        "rssi_dbm": -98
      }
    }

Tipos iniciales de conexión:

- `neighbor`
- `traceroute`
- `observed`
- `unknown`

Para conexiones no dirigidas, los extremos se ordenan antes de construir el
identificador.

Una conexión solo se publica si sus dos extremos existen en `nodes.json`.
Cuando SQLite contiene varias observaciones del mismo identificador de
conexión, se publica únicamente la de fecha `observed_at` más reciente.

La ausencia de conexiones MeshCore no impide publicar sus nodos.


## Documento de recepcións dos observers MeshCore

Archivo previsto:

    frontend/data/generations/<generation>/observer-receptions.json

Estructura superior:

    {
      "schema": "mesh-noroeste.data/v1",
      "generated_at": "2026-08-07T10:43:08Z",
      "receptions": []
    }

Cada entrada conserva:

| Campo | Tipo | Significado |
|---|---|---|
| `source` | string | Fuente de la observación; actualmente `meshcore_hub` |
| `network` | string | Siempre `meshcore` |
| `node_id` | string | Nodo al que se atribuye el anuncio |
| `observer_id` | string | Observer que recibió el paquete |
| `packet_hash` | string | Identificador publicado para el paquete |
| `observed_at` | timestamp | Momento de la recepción |
| `snr_db` | number/null | SNR medido por el observer al recibir ese paquete |
| `path_len` | integer/null | Longitud de ruta publicada por el Hub |

Las entradas se ordenan de forma determinista y se deduplican por nodo,
observer y hash de paquete. Se excluyen las recepciones cuando el nodo emisor
o el observer figuran en la lista privada de exclusiones.

El SNR es una métrica de la recepción RF realizada por el observer. No expresa
la calidad extremo a extremo desde el nodo emisor ni permite afirmar por sí
solo cuál fue cada salto intermedio.

## Documento de estadísticas

Archivo previsto:

    frontend/data/generations/<generation>/stats.json

Debe incluir:

- totales generales;
- totales por red;
- nodos activos, recientes e históricos;
- nodos con posición;
- número de conexiones;
- estado de cada fuente;
- última obtención correcta;
- último error;
- número de registros recibidos.

Un fallo de una fuente no debe impedir publicar los últimos datos válidos de
las demás fuentes.

### Ejecuciones de fuentes

Cada intento de recolección se registra internamente en `source_runs`.

Por cada fuente, `stats.json` publica:

- `last_success`: finalización del último intento correcto;
- `records_received`: registros recibidos en ese último éxito;
- `last_error_at`: finalización del último intento fallido;
- `last_error`: descripción controlada del último error.

Una ejecución sin finalizar no cuenta como éxito ni como fallo. Un error
posterior tampoco elimina la información del último éxito válido.

`records_received` representa los registros aceptados y normalizados por el
adaptador, no las filas nuevas insertadas. Una observación duplicada puede
recibirse correctamente sin generar otra fila en SQLite.

En Malha, el valor suma los nodos normalizados y los traceroutes aceptados.
Los autoenlaces descartados y los `packet_links` no se contabilizan.

## Documento de metadatos

Archivo previsto:

    frontend/data/generations/<generation>/meta.json

Debe incluir:

- versión del contrato;
- fecha de generación;
- nombre y versión de la aplicación;
- nombre y límites de la región;
- ventanas de actividad y retención.

En la configuración predeterminada, `region.bounds` contiene el rectángulo
envolvente de todas las áreas operativas:

    south: 36.75
    west: -9.75
    north: 43.95
    east: -4.25

Estos límites son metadatos públicos y no implican que se acepten todos los
puntos interiores. El filtro real es la unión de nueve áreas correspondientes
a Galicia, Asturias, León, Zamora y cinco franjas de Portugal.

El mismo filtro se aplica a los nodos Meshtastic y MeshCore. Los nodos sin
posición no se publican dentro de una región geográfica.

Cuando se proporciona un rectángulo personalizado mediante `--bounds`, ese
rectángulo sustituye tanto el filtro predeterminado como los límites publicados
en `meta.json`.

## Documento de avisos de configuración

Archivo previsto:

    frontend/data/generations/<generation>/configuration-warnings.json

Este documento utiliza un contrato independiente:

    mesh-noroeste.configuration-warnings/v1

Estructura superior:

    {
      "schema": "mesh-noroeste.configuration-warnings/v1",
      "generated_at": "2026-07-28T03:16:06Z",
      "analysis": {
        "source": "ozulo_map",
        "available": true,
        "updated_at": "2026-07-27T23:04:17Z",
        "eligible_nodes": 306,
        "analyzed_nodes": 303,
        "nodes_with_warnings": 75
      },
      "nodes": []
    }

El documento de entrada se genera dentro del propio proyecto mediante el
analizador de configuración. Este consulta la API pública de Meshview de
Comunidade O Zulo, analiza la actividad reciente y sustituye
`cache/configuration-analysis.json` de forma atómica. La ejecución se programa
cada seis horas y es independiente de las actualizaciones ordinarias del mapa.

Solo son elegibles los nodos consolidados que:

- pertenecen a la red `meshtastic`;
- incluyen `ozulo_map` dentro de `sources`.

Un nodo presente simultáneamente en Comunidade O Zulo y Malha Portugal
conserva un único identificador canónico y puede recibir el análisis de O
Zulo. Los nodos exclusivos de Malha no se consideran analizados, porque el
documento público de Malha no incluye todos los parámetros necesarios. Los
nodos
MeshCore tampoco forman parte de este contrato.

Cada entrada analizada tiene esta forma:

    {
      "id": "meshtastic:!a35b4144",
      "warnings": [
        {
          "key": "fixed_position_frequent",
          "severity": "high"
        }
      ]
    }

Un nodo analizado puede aparecer con `warnings: []`. Esto significa únicamente
que no se detectaron avisos mediante las comprobaciones disponibles; no
equivale a una validación completa de su configuración.

Las claves normalizadas admitidas son:

- `range_test_active`;
- `fixed_position_frequent`;
- `mobile_position_frequent`;
- `node_info_frequent`;
- `device_telemetry_frequent`;
- `environment_telemetry_frequent`;
- `power_telemetry_frequent`;
- `routing_frequent`;
- `position_fields_unnecessary`;
- `automatic_traceroute_frequent`;
- `hop_limit_high`;
- `client_base_firmware_old`;
- `client_mute_mobile`.

La gravedad admite `medium`, `high` y `critical`.

Cuando el archivo configurado mediante
`MESH_CONFIGURATION_WARNINGS_PATH` no existe, no puede leerse o no supera la
validación, la publicación general continúa con:

- `available: false`;
- `updated_at: null`;
- cero nodos analizados;
- cero nodos con avisos;
- una lista `nodes` vacía.

En ese estado se conserva el número de nodos elegibles para distinguir la
ausencia temporal del análisis de la ausencia de nodos Meshtastic.

## Retención y compactación de observaciones

La recepción, la persistencia y la publicación aplican responsabilidades
distintas:

- los colectores reciben y normalizan los registros válidos entregados por las
  fuentes, aunque su fecha sea antigua;
- la persistencia compara cada registro con el cursor de su fuente e
  identificador y solo inserta observaciones posteriores al último timestamp
  conocido;
- la publicación clasifica los nodos mediante las ventanas de actividad,
  recientes e históricos;
- un nodo cuya última observación supera `HISTORICAL_NODE_DAYS` no se publica;
- la poda elimina todas las observaciones completas anteriores al límite de
  retención, incluida la última fila de cada combinación;
- los cursores mínimos permanecen después de la poda para impedir que un
  snapshot antiguo vuelva a insertarse.

El cursor de nodo utiliza `source`, `canonical_id` y `last_observed_at`. El
cursor de conexión añade `network`, `from_source_id` y `to_source_id`, campos
necesarios para localizar y eliminar conexiones incidentes durante una
retirada voluntaria. No conserva métricas ni el resto del contenido de la
observación.

`save()` y `save_edges()` rechazan registros cuya fecha sea igual o anterior a
su cursor. `replace_edges()` conserva la semántica de snapshot completo: puede
eliminar una conexión actual y mantener únicamente su cursor. Por ello es
válido que exista un cursor de conexión sin una fila correspondiente en
`edge_observations`.

La restricción única por fuente, identificador y fecha continúa evitando
duplicados dentro de la ventana retenida. El cursor extiende esa protección a
las observaciones completas que ya fueron eliminadas.

La limpieza de SQLite no debe modificar los documentos públicos cuando las
filas retiradas ya estaban fuera de la ventana histórica. Las conexiones solo
se publican cuando ambos extremos sobreviven al filtro temporal, regional y de
exclusiones.


## Persistencia interna

La base de datos deberá separar:

- nodos canónicos;
- observaciones por fuente;
- posiciones;
- conexiones;
- anuncios NeighborInfo;
- recepcións de paquetes atribuídas a observers MeshCore;
- ejecuciones de colectores;
- errores de obtención;
- errores de normalización.

No se publicarán:

- contraseñas;
- tokens;
- cookies;
- cabeceras de autenticación;
- claves privadas;
- respuestas completas sin filtrar.

## Compatibilidad

Los cambios compatibles pueden añadir campos manteniendo:

    mesh-noroeste.data/v1

Los cambios incompatibles requieren una nueva versión:

    mesh-noroeste.data/v2

El frontend deberá rechazar una versión de contrato desconocida en lugar de
interpretarla de manera incorrecta.
