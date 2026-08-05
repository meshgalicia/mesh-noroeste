# Estado funcional del frontend

Este documento describe el comportamiento realmente implementado en el
frontend de Mesh Noroeste. Complementa `docs/SPEC.md` y separa las funciones
operativas de las mejoras todavía pendientes.

## Alcance de la interfaz

El frontend es una aplicación estática basada en Leaflet. Consume los
documentos públicos:

- `data/nodes.json`;
- `data/edges.json`;
- `data/stats.json`;
- `data/meta.json`;
- `data/configuration-warnings.json`.

La interfaz principal está escrita en gallego y está adaptada a escritorio y
dispositivos móviles.

## Publicación actual

La versión funcional está publicada en:

`https://mapa.mesh.gal/`

El mapa anterior continúa separado en `https://mesh.tuiter.ovh/`.

El servicio usa HTTPS, permite la geolocalización del propio origen y mantiene
su puerto HTTP enlazado únicamente a la interfaz local.

## Funciones operativas

### Visualización del mapa

El mapa representa nodos Meshtastic y MeshCore mediante marcadores Leaflet.

Solo se dibujan nodos con coordenadas publicables. El encuadre puede ajustarse
al conjunto de nodos que permanece visible después de aplicar los filtros.

Los nodos se agrupan mediante Leaflet.markercluster hasta el nivel de zoom 11.
Las agrupaciones distinguen visualmente conjuntos Meshtastic, MeshCore y
mixtos, e indican el número de nodos contenidos.

Leaflet.markercluster 1.5.3, sus dos hojas de estilo y su archivo
`MIT-LICENCE.txt` se distribuyen desde
`frontend/vendor/leaflet.markercluster/`. El navegador no depende de acceder a
Unpkg para activar la agrupación.

Leaflet, Leaflet.markercluster y `app.js` se cargan con `defer` y en ese orden.
Así el complemento se registra después de que exista `window.L` y antes de que
la aplicación cree las agrupaciones.

### Selector de red

La interfaz permite mostrar:

- ambas redes;
- únicamente Meshtastic;
- únicamente MeshCore.

El selector afecta a marcadores, búsqueda, estadísticas y traceroutes.

### Controles en escritorio y navegación móvil

En escritorio se mantiene una barra lateral completa y plegable. Su anchura
máxima se limita a `21.5rem` para no restar espacio innecesario al mapa. Al
plegarla queda una barra estrecha y Leaflet recalcula el área disponible.

En pantallas de hasta 780 píxeles la barra lateral deja de formar parte del
flujo de la página. El mapa ocupa toda la altura visible y aparece una barra
inferior con cinco accesos:

- **Buscar**;
- **Rede**;
- **Filtros**;
- **Capas**;
- **Info**.

Cada acceso abre únicamente su grupo dentro de una tarjeta superpuesta con
desplazamiento interno y una altura máxima del 70 % de la pantalla. El mapa
permanece visible detrás de la tarjeta.

Puede cerrarse pulsando de nuevo el acceso activo, el botón de cierre, el fondo
del mapa o la tecla Escape. Las etiquetas acompañan a los iconos para evitar
ambigüedad y cada botón actualiza `aria-pressed` y `aria-expanded`.

Los controles reales no se duplican: la interfaz móvil reutiliza los mismos
campos y botones que la barra de escritorio. Por ello se conservan los filtros,
la búsqueda, la geolocalización, las cifras y sus estados.

### Filtros temporales

Los bloques **Antigüidade**, **Lenda e tipos** y **Estado das fontes** pueden
plegarse tanto en escritorio como en móvil. Sus encabezados muestran un
chevron orientado a la derecha cuando están cerrados y hacia abajo cuando
están abiertos. Se oculta el marcador nativo del navegador para mantener una
señal visual consistente.

Antigüidade y Lenda e tipos se abren inicialmente en escritorio y permanecen
cerrados en móvil. Estado das fontes se inicia cerrado. La elección de la
persona se conserva durante la sesión del navegador.

La instantánea se divide tomando `generated_at` como referencia estable:

- menos de 1 hora;
- entre 1 y 24 horas;
- entre 1 y 7 días;
- entre 7 y 30 días.

Los cuatro intervalos pueden combinarse libremente. El encabezado indica si
están activos todos, ninguno o una parte de ellos. El filtrado temporal también
modifica la opacidad del marcador sin sustituir su color, forma, rol o tipo.

### Lenda interactiva e filtros por categoría

Cada entrada de rol Meshtastic o tipo MeshCore funciona como filtro y expone
su estado mediante `aria-pressed`.

Es posible combinar roles y tipos, por ejemplo mostrar únicamente routers,
routers tardíos y repetidores MeshCore. El control «Mostrar todos» restaura las
once categorías.

La búsqueda, las cifras visibles, los nodos, las agrupaciones y las conexiones
publicadas respetan conjuntamente los filtros de red, antigüedad, rol y tipo.
Cuando ninguna combinación produce nodos se muestra un estado vacío explícito.

La actividad no se repite dentro de la leyenda: sus cuatro intervalos ya están
representados en Antigüidade. Las agrupaciones Meshtastic, MeshCore y mixtas se
presentan en una línea compacta.

### Búsqueda de nodos

El buscador admite nombres, identificadores, hardware, rol, tipo y fuente.

Los resultados respetan los filtros activos. Al seleccionar un resultado, el
mapa se centra en el nodo y abre su panel de detalle.

### Panel de detalle

Al seleccionar un nodo se muestran los campos disponibles:

- identificadores;
- nombre corto y nombre largo;
- hardware;
- rol Meshtastic o tipo MeshCore;
- estado de actividad;
- primera y última observación;
- actualización de la posición;
- coordenadas y altitud;
- parámetros de radio;
- saltos y gateway MQTT;
- batería, voltaje, SNR, RSSI y utilización del canal;
- conexiones publicadas, dirección, fecha y métricas;
- avisos automáticos de configuración cuando existe análisis;
- fuentes e identificadores originales.

Los datos ausentes no se inventan ni se sustituyen por estimaciones.

La selección directa mediante un marcador abre el panel de detalle y activa
el resaltado de las conexiones asociadas. Este comportamiento se ha vuelto a
comprobar en navegador móvil y en la versión publicada mediante HTTPS.

### Roles y tipos MeshCore

Los tipos funcionales de MeshCore ya se representan de forma diferenciada:

- repetidor;
- Room Server;
- cliente;
- desconocido.

Cada tipo tiene un color propio y una entrada en la leyenda. Esta
diferenciación ya está implementada y debe conservarse al revisar la paleta,
la forma o el tamaño de los marcadores.

El tipo MeshCore y el estado de actividad son dimensiones independientes: el
tipo determina la identidad visual básica y la actividad modifica la
opacidad.

### Traceroutes

El frontend representa exclusivamente las conexiones cuyo campo
`edge_type` sea `traceroute`.

No infiere enlaces, vecinos ni rutas por proximidad geográfica.

Un traceroute solo se dibuja cuando:

1. está presente en `edges.json`;
2. su nodo de origen permanece visible;
3. su nodo de destino permanece visible;
4. está activado el control «Mostrar traceroutes».

Las conexiones actuales son dirigidas. Se representan mediante:

- línea verde discontinua;
- grosor de 1,5 píxeles;
- opacidad de 0,38;
- flecha situada aproximadamente en el punto medio;
- orientación desde `from_id` hacia `to_id`.

La representación es funcional, pero resulta deliberadamente discreta. Su
contraste y legibilidad con distintos niveles de zoom deben revisarse.

### Conexiones publicadas en el detalle

El panel de detalle incluye una sección «Conexións publicadas».

Para cada conexión asociada al nodo muestra:

- el otro extremo;
- el tipo `traceroute`, `neighbor` u otro tipo publicado;
- la dirección entrante, saliente o bidireccional;
- la fecha de la última observación;
- SNR y RSSI cuando existen;
- la fuente original.

El nombre del otro nodo funciona como control de navegación: al activarlo, el
mapa se centra en ese nodo y abre su detalle.

La sección se mantiene visible con un mensaje explícito cuando el nodo no
tiene conexiones publicadas. No infiere relaciones por proximidad.

### Resaltado de conexiones del nodo seleccionado

Al abrir el detalle de un nodo, los traceroutes visibles asociados a ese nodo
se resaltan sobre el resto de conexiones.

El resaltado utiliza:

- color magenta oscuro;
- grosor de 4 píxeles;
- opacidad de 0,92;
- línea discontinua más marcada;
- flecha direccional ampliada;
- orden de dibujo posterior a las conexiones generales.

Al cerrar el panel de detalle se elimina la selección y las rutas recuperan su
estilo general.

El resaltado respeta los filtros activos y el control para mostrar u ocultar
traceroutes. No fuerza la aparición de conexiones cuyos dos extremos no estén
visibles.

### Estadísticas visibles

La interfaz informa del número actual de:

- nodos visibles;
- nodos Meshtastic;
- nodos MeshCore;
- traceroutes visibles.

Las cifras cambian al modificar los filtros o la red seleccionada.

### Estado de las fuentes

Se muestra la última actualización correcta conocida de:

- Meshview España;
- Malha Portugal;
- Comunidade O Zulo;
- MeshCore Map;
- MeshCore Hub de Mesh Galicia.

### Avisos de configuración

El detalle de los nodos Meshtastic puede mostrar una sección
«Configuración» basada en `configuration-warnings.json`.

La integración mantiene estas reglas:

- solo se analizan nodos Meshtastic presentes en Meshview España;
- los nodos que aparecen también en Malha Portugal se cruzan mediante su
  identificador canónico y no se duplican;
- los nodos exclusivos de Malha o de Comunidade O Zulo muestran que el
  análisis no está disponible cuando no existe una entrada del analizador;
- los nodos MeshCore quedan fuera de este análisis;
- un nodo analizado sin avisos se describe de forma prudente y no se presenta
  como configuración correcta;
- un fallo o ausencia del analizador no impide cargar el resto del mapa.

Los avisos se muestran únicamente en el panel de detalle. No modifican el
marcador, no crean filtros nuevos y no se utilizan para ocultar nodos.

El análisis distingue gravedad media, alta y crítica. La presentación añade
texto explícito además del color y mantiene bordes visibles en modo de colores
forzados.

El documento de origen lo genera el analizador propio de Mesh Noroeste.
Consulta la API pública de Meshview España, analiza la actividad reciente de
cada nodo y escribe atómicamente
`cache/configuration-analysis.json`. Un temporizador de systemd lo ejecuta cada
seis horas de forma independiente de los colectores del mapa.

La publicación consume ese documento mediante
`MESH_CONFIGURATION_WARNINGS_PATH`. El analizador no utiliza contenedores,
volúmenes, cachés de geolocalización ni código del mapa anterior.

### Posición del navegador

El botón «A miña posición» solicita permiso explícito al navegador.

Cuando se concede:

- centra el mapa en la posición aproximada;
- muestra un marcador independiente;
- dibuja el círculo de precisión;
- informa de la precisión aproximada en metros.

La posición se usa únicamente en el navegador. No se guarda ni se envía al
servidor. La función requiere HTTPS.

## Semántica de conexiones y vecinos

El contrato admite inicialmente:

- `traceroute`;
- `neighbor`.

Las conexiones publicadas pueden proceder de las fuentes Meshtastic que
ofrecen traceroutes o vecindades. Sus extremos no deben presentarse
automáticamente como «vecinos directos»: la interfaz conserva el
`edge_type` declarado por cada fuente.

La interfaz incluye una sección «Conexións publicadas» en el panel de
detalle. Distingue expresamente:

- vecinos publicados como `edge_type: neighbor`;
- nodos relacionados mediante `edge_type: traceroute`;
- origen y destino de conexiones dirigidas;
- fecha, SNR, RSSI y fuente cuando están disponibles.

Mientras no existan conexiones `neighbor`, la denominación correcta sigue
siendo «Conexións publicadas», no «Veciños».

## Codificación visual actual

### Meshtastic

Los roles Meshtastic utilizan marcadores circulares y se distinguen mediante
color, tamaño y patrón del borde:

- `CLIENT`: verde;
- `CLIENT_BASE`: cian;
- `CLIENT_MUTE`: violeta con borde discontinuo;
- `ROUTER`: rojo y marcador de mayor tamaño;
- `ROUTER_LATE`: naranja, tamaño de router y borde discontinuo;
- `TRACKER`: rosa intenso con borde punteado;
- sin rol publicado: gris oscuro con borde discontinuo.

La diferenciación no depende exclusivamente del color. Los routers tienen
mayor tamaño y los roles silencioso, tardío, tracker y desconocido conservan
patrones de borde propios.

### MeshCore

Los tipos MeshCore utilizan forma y color propios:

- repetidor: cuadrado azul;
- Room Server: rombo negro;
- cliente: triángulo amarillo;
- desconocido: cuadrado gris.

Las formas permiten distinguir MeshCore de Meshtastic incluso cuando el color
no se percibe con claridad.

Los marcadores individuales tienen un tamaño visible mínimo de 20 píxeles y
conservan una zona interactiva de 52 píxeles. Esto mejora su reconocimiento y
su pulsación en pantallas móviles sin alterar la posición geográfica.

### Actividad

La diferenciación por antigüedad se implementa mediante cuatro niveles de
opacidad calculados respecto de `generated_at`:

- menos de 1 hora: opacidad máxima;
- entre 1 y 24 horas: opacidad alta;
- entre 1 y 7 días: opacidad intermedia;
- entre 7 y 30 días: opacidad reducida.

La antigüedad no sustituye la diferenciación de rol o tipo. Cada nodo conserva
su identidad visual y cambia únicamente de opacidad según el intervalo al que
pertenece.

### Agrupación y nombres

La agrupación está activa hasta zoom 11 inclusive. A partir de zoom 12 se
muestran los marcadores individuales.

Los nombres siguen una presentación progresiva:

- el nodo seleccionado conserva siempre su nombre visible;
- desde zoom 12 se muestran nombres de routers, routers tardíos, trackers y
  Room Servers;
- desde zoom 13 se muestran los nombres de todos los nodos;
- en niveles anteriores el nombre continúa disponible mediante tooltip.

Esta estrategia evita intentar representar simultáneamente los 1199 nombres
en la vista regional.

### Zoom y encuadre

El comportamiento actual utiliza:

- zoom regional máximo 7 al recuperar la vista completa;
- zoom mínimo 15 al abrir un resultado de búsqueda o una conexión;
- zoom 15 cuando solo queda un nodo visible;
- zoom máximo 12 al ajustar el mapa a varios nodos filtrados;
- agrupaciones hasta zoom 11 y marcadores individuales desde zoom 12.

## Estado del pulido funcional

Ya están completados y comprobados:

- el encuadre regional, los niveles de zoom y la apertura de resultados;
- las agrupaciones hasta zoom 11 y los marcadores individuales desde zoom 12;
- la paleta diferenciada de Meshtastic, MeshCore, traceroutes y vecinos;
- la agrupación mixta con representación simultánea de ambas redes;
- la legibilidad de traceroutes generales y del nodo seleccionado;
- la navegación móvil, los paneles superpuestos y el detalle de nodo;
- los controles táctiles, la restauración del foco y el buscador accesible;
- la visualización en modos de alto contraste;
- la coherencia visual entre mapa, leyenda y paneles.

El burdeos continúa reservado para el nodo seleccionado. El verde conserva su
uso semántico en estados activos o visibles, y la navegación emplea la paleta
violeta, pizarra y lavanda.

## Retención SQLite cerrada

La política de retención está implementada y desplegada sobre el esquema
SQLite 5. La comprobación sobre la base operativa confirmó que:

- las observaciones completas de nodos y conexiones tienen una retención
  absoluta de 30 días;
- la poda elimina también la última fila completa cuando supera ese límite;
- los cursores mínimos impiden reinsertar snapshots antiguos ya eliminados;
- los cursores de conexión pueden permanecer sin fila actual cuando una fuente
  publica snapshots completos;
- la primera poda real eliminó 17.767 observaciones de nodo y ninguna conexión
  caducada;
- SQLite mantuvo su integridad antes y después de la operación;
- el conjunto público de nodos y conexiones no cambió durante la poda;
- una recolección posterior de Meshview España terminó correctamente y no
  restauró observaciones caducadas;
- los avisos de configuración continuaron publicados.


## Sistema de símbolos cerrado

El sistema visual se comprobó sobre el mapa real y queda definido así:

- `CLIENT`: círculo liso;
- `CLIENT_BASE`: círculo con anillo interior;
- `CLIENT_MUTE`: círculo con barra horizontal;
- `TRACKER`: círculo con mira de seguimiento;
- nodos Meshtastic sin rol: círculo gris;
- `ROUTER` y `ROUTER_LATE`: hexágonos;
- repetidor MeshCore: cuadrado redondeado;
- Room Server: rombo;
- cliente MeshCore: triángulo;
- tipo MeshCore desconocido: cuadrado discontinuo.

La forma exterior identifica la familia funcional. El color, el tamaño, el
borde y las marcas interiores aportan señales redundantes para móvil, baja
visión, alto contraste y situaciones en las que el color no sea suficiente.

## Leyenda y filtros en móvil

Al abrir `Lenda e filtros` en móvil, los bloques interactivos aparecen
desplegados y el desplazamiento vuelve al inicio del panel. El orden prioriza
las acciones más habituales:

1. filtros por rol y tipo de nodo;
2. filtros por antigüedad;
3. agrupaciones y otros elementos de la leyenda informativa.

Los bloques pueden plegarse durante el uso. En escritorio se conserva el orden
y el comportamiento desplegable original.

## Estado de la primera versión estable

La primera versión estable está publicada en `https://mapa.mesh.gal/`.
El mapa anterior permanece separado en `https://mesh.tuiter.ovh/`.
Las mejoras posteriores se incorporarán únicamente después de su
implementación, validación automatizada y comprobación funcional.

## Funciones fuera del alcance actual

No se desarrolla todavía un analizador completo propio para Malha Portugal ni
para MeshCore. Tampoco se generan recomendaciones personalizadas ni se
modifica automáticamente la configuración de ningún nodo.

No se presentarán traceroutes como vecinos directos. Una sección
específica de vecinos solo tendrá contenido cuando alguna fuente publique
conexiones reales con `edge_type: neighbor`.

## Instantánea histórica auditada

Datos generados en `2026-07-26T08:29:21Z`. Esta instantánea documenta una
validación anterior y no representa el estado operativo actual:

- nodos totales: 1199;
- Meshtastic: 714;
- MeshCore: 485;
- activos: 438;
- recientes: 361;
- históricos: 400;
- conexiones publicadas: 351;
- traceroutes: 351;
- vecinos publicados: 0;
- nodos con alguna conexión publicada: 231;
- nodos sin conexiones publicadas: 968;
- máximo de conexiones asociadas a un nodo: 17.

### Roles Meshtastic de la instantánea

- `CLIENT`: 314
- `CLIENT_BASE`: 173
- `CLIENT_MUTE`: 155
- `sin rol publicado`: 29
- `ROUTER`: 24
- `ROUTER_LATE`: 15
- `TRACKER`: 4

### Tipos MeshCore de la instantánea

- `repeater`: 459
- `room_server`: 17
- `client`: 9

Estas cifras se conservan como referencia de auditoría. Los recuentos actuales
deben consultarse en los documentos públicos generados por la última
recolección y publicación.

## Criterios de integridad

El frontend debe:

- no fabricar nodos ni conexiones;
- no llamar vecino a un enlace que solo consta como traceroute;
- no dibujar conexiones con extremos ausentes;
- no mostrar datos fuera del filtro regional;
- funcionar aunque `edges.json` esté vacío;
- conservar las fuentes originales;
- distinguir entre análisis disponible, nodo no analizado y ausencia de
  avisos;
- distinguir entre datos disponibles y funciones pendientes.
