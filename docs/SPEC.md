# Especificación funcional inicial

## Redes

El mapa debe admitir tres modos:

- Meshtastic
- MeshCore
- Ambas

## Fuentes

- Meshview España
- Malha Portugal
- Comunidade O Zulo
- MeshCore Map
- MeshCore Hub de Mesh Galicia

Solo se acreditarán fuentes realmente utilizadas.

## Estado de las fuentes

La integración se desarrolla de forma independiente para que el fallo de
una fuente no bloquee las demás.

Estado actual:

- `meshcore_map`: colector implementado y probado contra el documento
  público compacto de MeshCore Map;
- `meshcore_hub`: colector autenticado y paginado para los nodos de
  MeshCore Hub de Mesh Galicia;
- `meshview_es`: colector implementado y probado contra la API pública
  de nodos de Meshview España;
- `malha_pt`: adaptador, cliente HTTP y colector implementados para los
  nodos y traceroutes del documento público de Malha Portugal;
- `ozulo_map`: adaptador y colector implementados para los nodos y
  conexiones de los JSON consolidados de Comunidade O Zulo.

El cliente de Malha conserva las cookies entregadas por el servidor y la
última respuesta JSON válida en archivos persistentes fuera de Git. Puede
reintentar una vez después de una respuesta HTTP 403 para reutilizar una
cookie recién recibida, pero no fabrica credenciales ni elude el mecanismo
de protección de la fuente.

Los colectores implementados:

1. descargan cada documento mediante HTTPS;
2. aplican límites configurables de espera y tamaño;
3. validan la estructura y normalizan cada registro;
4. guardan las observaciones en SQLite;
5. registran el inicio, el éxito o el error de la ejecución;
6. conservan los últimos datos válidos si una ejecución posterior falla.

Meshview España, Malha Portugal, Comunidade O Zulo y MeshCore Hub se
consumen como JSON. MeshCore Map se solicita en su formato MessagePack
compacto. MeshCore Hub requiere una clave de lectura y pagina la respuesta
mediante `limit` y `offset`.

Malha aporta nodos y traceroutes dirigidos. Ambos se normalizan y persisten
en SQLite. Los `packet_links` no forman parte de la integración inicial por
las anomalías observadas en algunos identificadores y métricas.

## Ámbito inicial

La región predeterminada es la unión de nueve envolventes operativas:

- Galicia;
- Asturias;
- León;
- Zamora;
- Portugal norte;
- Portugal centro-norte;
- Portugal centro;
- Portugal sur;
- Portugal Algarve.

Esta definición se aplica por igual a Meshtastic y MeshCore. El uso de varias
áreas, en lugar de un único rectángulo, evita incorporar grandes zonas de
España ajenas al ámbito del mapa.

`meta.json` publica el rectángulo exterior que engloba las nueve áreas. Ese
rectángulo sirve como metadato y referencia visual, pero no describe por sí
solo el filtro geográfico real.

La opción `--bounds SOUTH WEST NORTH EAST` permite sustituir la región
predeterminada por un rectángulo explícito.

La ampliación hacia otras áreas se evaluará posteriormente sin perjudicar
el rendimiento ni la claridad del mapa regional.

## Backend

El backend deberá:

1. obtener datos de cada fuente de forma independiente;
2. guardar las respuestas originales fuera del control de versiones;
3. normalizar identificadores, coordenadas y fechas;
4. conservar observaciones completas durante un máximo de 30 días y
   cursores mínimos de deduplicación después de ese plazo;
5. aplicar ventanas de actividad y retención configurables;
6. generar JSON estáticos para el frontend, incluido el documento
   opcional de avisos de configuración;
7. funcionar mediante contenedores;
8. registrar errores sin almacenar secretos.

Operaciones disponibles actualmente:

```console
mesh-noroeste collect-meshview
mesh-noroeste collect-malha
mesh-noroeste collect-ozulo
mesh-noroeste collect-meshcore
mesh-noroeste collect-meshcore-hub
mesh-noroeste check
mesh-noroeste publish
mesh-noroeste prune
mesh-noroeste purge-node IDENTIFICADOR_CANÓNICO
```

La salida JSON de `publish` incluye los campos `observations`, `nodes` y
`edges`, además de las rutas de los documentos escritos.

## Operación y publicación

Los colectores se ejecutan de forma independiente mediante temporizadores de
systemd. Un bloqueo compartido evita que dos actualizaciones o una poda
modifiquen SQLite simultáneamente.

El análisis opcional de configuración se carga desde
`MESH_CONFIGURATION_WARNINGS_PATH`. Un documento ausente o inválido se
publica como análisis no disponible y no bloquea los datos principales.

Los colectores cargan
`/etc/mesh-noroeste/mesh-noroeste.env` mediante `EnvironmentFile`. Esta
configuración define `MESH_EXCLUSIONS_PATH` y apunta a una lista privada fuera
de Git. También contiene `MESHCORE_HUB_API_READ_KEY` cuando se activa el
colector autenticado del Hub. Ninguna de estas configuraciones forma parte de
Git. Si la lista de exclusiones falta o no supera la validación, la
recolección se detiene antes de descargar o modificar SQLite.

Cada actualización correcta:

1. recoge y normaliza la fuente correspondiente;
2. comprueba la integridad de SQLite;
3. escribe los cinco documentos dentro de un nuevo directorio inmutable en
   `frontend/data/generations/`;
4. sincroniza la generación completa con el sistema de archivos;
5. activa el conjunto sustituyendo atómicamente
   `frontend/data/manifest.json`.

El frontend descarga primero el manifiesto y obtiene de él las cinco rutas de
una única generación. No combina documentos de generaciones diferentes. Si
la escritura falla antes de sustituir el manifiesto, la generación anterior
continúa activa. Se conservan las doce generaciones más recientes para que
las lecturas ya iniciadas puedan terminar después de una nueva activación.

La poda diaria utiliza la ventana histórica configurada para eliminar
todas las observaciones completas caducadas, incluida la última fila de cada
combinación de `source` y `canonical_id`.

Los cursores mínimos de nodo y conexión conservan el último timestamp conocido
y los identificadores técnicos imprescindibles. Los métodos de persistencia
los consultan para impedir que una fuente vuelva a insertar snapshots antiguos
que ya fueron eliminados.

La visibilidad temporal continúa decidiéndose durante la publicación. Los
cursores no forman parte de `nodes.json`, `edges.json` ni de las estadísticas
públicas.

## Frontend

El frontend deberá incluir progresivamente:

- mapa Leaflet;
- interfaz y textos principales en gallego;
- selector Meshtastic, MeshCore y Ambas;
- búsqueda de nodos;
- filtros;
- leyenda;
- estadísticas;
- panel de detalle;
- representación diferenciada de tipos MeshCore;
- conexiones, agrupaciones y traceroutes;
- control independiente para mostrar u ocultar traceroutes;
- diseño accesible;
- funcionamiento móvil;
- avisos contextuales de configuración para nodos Meshtastic analizados;
- créditos de las fuentes.

La identidad visual será propia y no reproducirá la estética del proyecto
anterior. Puede conservar conceptos funcionales útiles, pero la estructura,
los estilos y la implementación se desarrollarán de forma independiente.

Los traceroutes se representarán como recorridos dirigidos a partir de las
entradas de `edges.json` cuyo campo `edge_type` sea `traceroute`. El frontend
no inferirá ni fabricará rutas cuando la fuente no proporcione conexiones.
El mapa funcionará normalmente sin trazados cuando ninguna conexión supere
los criterios de publicación.

El backend normaliza y persiste en SQLite los traceroutes procedentes de
Malha Portugal. Para cada conexión conserva la observación más reciente y
solo la incorpora a `edges.json` cuando sus dos extremos aparecen también en
el `nodes.json` regional. Las estadísticas generales y por red incluyen el
número de conexiones finalmente publicadas.

## Análisis propio de configuración

Mesh Noroeste genera el documento bruto de avisos mediante una implementación
propia. El proceso consulta los endpoints públicos de nodos, paquetes y
recepciones de Meshview España, analiza una ventana reciente de actividad y
escribe atómicamente `cache/configuration-analysis.json`.

La unidad `mesh-noroeste-analysis.service` se ejecuta cada seis horas mediante
`mesh-noroeste-analysis.timer`. Su fallo no bloquea los colectores ni la
publicación general: el último documento válido permanece intacto y, cuando no
existe una entrada válida, el contrato público representa el análisis como no
disponible. No hay dependencia del contenedor, volumen ni código del mapa
anterior.

## Fuera del alcance inicial

- mapa completo de España;
- alcance observado por recepciones RF o MQTT;
- integración directa con cuentas de usuario;
- edición manual de nodos;
- publicación de datos históricos completos.
