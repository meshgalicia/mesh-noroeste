# Investigación de O Zulo

Fecha de la investigación: 29 de julio de 2026.

## Objetivo

Evaluar los servicios de O Zulo como posible fuente para Mesh Noroeste,
inicialmente planteada como respaldo de Meshview España.

La investigación se realizó en modo de solo lectura y con permiso de O
Zulo. No se guardan credenciales MQTT en este repositorio.

## Servicios examinados

- Mapa: `https://mapa.mesh.comunidadeozulo.org/`
- Meshview: `https://meshview.mesh.comunidadeozulo.org/`
- Malla: `https://malla.mesh.comunidadeozulo.org/`

El broker MQTT de O Zulo está interconectado con el servicio español. Para
Mesh Noroeste se prefiere consumir datos HTTP históricos o consolidados,
sin mantener un cliente MQTT permanentemente conectado.

## API de Meshview de O Zulo

Endpoints comprobados:

- `/api/nodes`
- `/api/packets?portnum=3&limit=1000`
- `/api/edges?type=traceroute`
- `/api/edges?type=neighbor`
- `/api/config`
- `/api/channels`

Resultados observados:

- 858 nodos.
- 1.000 paquetes de posición disponibles en la consulta probada.
- 293 conexiones traceroute.
- 0 conexiones neighbor.
- Estructura de nodos, paquetes y traceroutes compatible con Meshview
  España.

Los parsers actuales de Mesh Noroeste pudieron interpretar sus nodos,
precisiones y traceroutes. Sin embargo, el adaptador actual fija
internamente la fuente como `meshview_es`, por lo que no puede reutilizarse
directamente sin parametrizar la procedencia.

## JSON publicados por el mapa de O Zulo

Endpoints comprobados:

- `/data/nodes.json`
- `/data/edges.json`
- `/data/stats.json`
- `/data/config.json`

Estado observado:

- 366 nodos publicados.
- 254 nodos con posición.
- 239 nodos con `precision_bits`.
- 9 gateways MQTT.
- 1.064 conexiones, todas traceroute.
- Todas las conexiones incluyen `last_seen`.
- Retención declarada de 15 días.
- Actualización declarada cada 5 minutos.

Estos documentos son más compactos y ya contienen posición, precisión,
actividad y conexiones consolidadas.

## Solapamiento con Meshview España

Comparación de las APIs completas:

- Meshview España: 2.762 nodos.
- Meshview O Zulo: 858 nodos.
- Nodos compartidos: 224.
- Solapamiento total de O Zulo con España: 26,1 %.

Solapamiento reciente:

- Último día: 53,8 %.
- Últimos 7 días: 54,4 %.
- Últimos 30 días: 34,4 %.
- Últimos 90 días: 26,1 %.

Los históricos y criterios de retención de ambos Meshview no son
equivalentes, aunque los brokers estén interconectados.

## Aportación dentro de la región de Mesh Noroeste

En la instantánea analizada del mapa de O Zulo:

- 237 nodos con posición estaban dentro de la región publicada.
- 123 también aparecían en Meshview España.
- 114 no aparecían en Meshview España.
- 27 de esos nodos exclusivos habían estado activos durante la última hora.
- 99 no estaban publicados entonces por Mesh Noroeste.

Por tanto, O Zulo aporta cobertura regional real y no debe considerarse
únicamente una fuente de respaldo.

## Decisión arquitectónica propuesta

Integrar O Zulo como fuente complementaria regional:

- Nombre interno propuesto: `ozulo_map`.
- Meshview España conserva la prioridad principal.
- O Zulo añade nodos regionales ausentes y puede completar precisión,
  actividad y traceroutes.
- Deduplicación por identificador canónico Meshtastic.
- Conservación explícita de la procedencia de cada nodo y conexión.
- Frecuencia inicial propuesta: cada 15 o 30 minutos.
- No consumir permanentemente el MQTT.
- Preferir inicialmente los JSON consolidados del mapa de O Zulo.

O Zulo también podría actuar como respaldo parcial si Meshview España
falla, pero esa no sería su única función.

## Trabajo pendiente

Antes de implementar esta fuente:

1. Cerrar, validar y commitear los cambios de halo y zoom.
2. Parametrizar o separar el adaptador compatible con Meshview.
3. Añadir `ozulo_map` al dominio, SQLite, estadísticas y esquemas públicos.
4. Definir prioridad por campos y reglas de deduplicación.
5. Crear pruebas de nodos, precisión, traceroutes y datos obsoletos.
6. Añadir un temporizador independiente.
7. Medir carga, tamaño de SQLite y efecto sobre la publicación.
8. Documentar atribución, límites y comportamiento de respaldo.
