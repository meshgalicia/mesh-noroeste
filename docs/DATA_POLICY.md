# Política de datos, retención y retirada

## Estado del documento

Este documento fija la política técnica y editorial prevista para la primera
versión estable de Mesh Noroeste.

No describe únicamente el comportamiento actual. Las medidas todavía no
implementadas se identifican expresamente como pendientes y no deberán
presentarse como activas hasta que existan pruebas y despliegue verificados.

## Alcance

Mesh Noroeste agrega y normaliza información publicada por fuentes externas
sobre redes Meshtastic y MeshCore dentro de su ámbito regional.

El proyecto no debe:

- identificar propietarios o personas usuarias de los nodos;
- inferir domicilios, identidades o relaciones personales;
- enriquecer los datos con información personal procedente de otras fuentes;
- presentar las posiciones como localizaciones exactas de personas;
- publicar un histórico completo de movimientos o recepciones.

## Fuentes

La primera versión estable utiliza exclusivamente las fuentes documentadas por
el proyecto:

- Meshview España;
- Malha Portugal;
- O Zulo;
- MeshCore Map;
- MeshCore Hub de Mesh Galicia.

Cada dato publicado deberá conservar información suficiente para indicar su
procedencia.

La presencia de un dato en Mesh Noroeste no implica que el proyecto lo haya
verificado de forma independiente.

## Datos que pueden publicarse

Podrán publicarse los campos necesarios para representar y explicar el estado
técnico de la red:

- identificador canónico y, cuando sea necesario, identificadores de fuente;
- nombre corto y nombre largo publicados por el nodo o la fuente;
- red, función, rol, tipo y hardware;
- coordenadas, altitud, precisión y fecha de actualización de la posición;
- primera y última observación disponibles dentro de la ventana publicable;
- métricas técnicas y parámetros de radio;
- fuentes de procedencia;
- vecindades y traceroutes publicados por las fuentes.

Mesh Noroeste no añadirá ni buscará deliberadamente cuentas personales,
direcciones de contacto u otra información destinada a identificar a una
persona. Tampoco publicará cookies, credenciales ni direcciones IP de
visitantes.

Los campos de nombre corto y nombre largo se reproducen desde los nodos o las
fuentes y pueden contener alias, enlaces o texto de contacto introducido por
quien configuró el nodo. Mesh Noroeste no interpretará, ampliará ni cruzará ese
contenido con otras fuentes. Podrá retirarlo localmente mediante la exclusión
del nodo cuando exista una solicitud válida o un riesgo evidente.

## Calidad y precisión

Los datos pueden ser:

- aproximados;
- antiguos;
- incompletos;
- duplicados entre fuentes;
- incorrectos por configuración del nodo o por errores de origen.

Mesh Noroeste no corregirá automáticamente posiciones dudosas ni fusionará
nodos únicamente por nombre o coordenadas.

Cuando una fuente proporcione precisión de posición fiable, el mapa deberá
mostrarla o advertir que la posición es aproximada.

## Ventanas de publicación

Las ventanas iniciales son:

- activo: últimas 24 horas;
- reciente: últimos 7 días;
- histórico visible: hasta 30 días.

Un nodo cuya observación más reciente supere los 30 días deja de aparecer en
los documentos públicos.

La publicación y la persistencia aplican responsabilidades distintas. La
publicación decide qué nodos son visibles según estas ventanas; la poda elimina
de SQLite todas las observaciones completas que superan el límite de 30 días.
Los cursores técnicos de deduplicación no son observaciones publicables.


## Retención interna objetivo

La política está implementada y desplegada sobre el esquema SQLite 7.

Las observaciones completas de nodos y conexiones se conservan durante un
máximo de 30 días. Cuando una observación supera ese plazo, la poda elimina la
fila completa aunque sea la última recibida para esa combinación de fuente e
identificador.

Después de eliminar las observaciones completas se mantienen cursores técnicos
mínimos para evitar que una fuente restaure continuamente un snapshot antiguo.

El cursor de nodo conserva únicamente:

- fuente;
- identificador canónico;
- fecha de la última observación recibida.

El cursor de conexión conserva únicamente:

- fuente;
- identificador canónico de la conexión;
- red;
- identificadores técnicos de sus dos extremos;
- fecha de la última observación recibida.

Los extremos de una conexión se conservan porque son necesarios para retirar
también sus cursores cuando se purga voluntariamente un nodo. Estos cursores no
conservan nombres, coordenadas, altitud, telemetría, parámetros de radio,
hardware, métricas de conexión ni el resto del contenido de una observación.

Un cursor de conexión puede existir sin una fila actual en
`edge_observations`. Este estado es correcto cuando una actualización mediante
snapshot ha retirado la conexión: el cursor impide que una versión más antigua
vuelva a insertarla.

La primera poda real eliminó 17.767 observaciones completas de nodo y ninguna
conexión caducada. El conjunto público permaneció idéntico durante esa
operación. Una recolección posterior de Meshview España terminó correctamente
y confirmó que no reaparecieron observaciones anteriores al límite aplicado.


## Retirada voluntaria

Mesh Noroeste ofrecerá un mecanismo de retirada local por identificador de
nodo.

La retirada deberá aplicarse mediante una lista privada y persistente de
exclusiones, almacenada fuera de Git.

Un nodo excluido deberá:

- dejar de publicarse;
- no volver a almacenarse en nuevas recolecciones;
- eliminarse de las observaciones completas de SQLite;
- desaparecer de `nodes.json`;
- desaparecer de `configuration-warnings.json`;
- eliminar todas las conexiones en las que participe;
- dejar de influir en estadísticas públicas;
- permanecer excluido después de reinicios, actualizaciones y restauraciones.

La exclusión deberá comprobarse como mínimo:

1. antes de persistir datos recién recogidos;
2. durante la publicación, como defensa adicional.

La lista real de exclusiones no se publicará ni se incluirá en el repositorio.

La retirada se aplicará a los identificadores incorporados a la lista. Si un
dispositivo cambia de identificador y aparece como un nodo técnicamente nuevo,
podrá ser necesario añadir también ese nuevo identificador. Mesh Noroeste no
intentará relacionar identidades distintas mediante nombres, coordenadas u
otros indicios.

## Solicitudes de corrección o retirada

Las solicitudes deberán identificar preferentemente el nodo mediante su
identificador, porque los nombres pueden repetirse o cambiar.

Podrán solicitarse:

- retirada local del nodo;
- corrección de un error propio de Mesh Noroeste;
- revisión de una posición o dato claramente incorrecto.

Cuando el error proceda de la fuente original, Mesh Noroeste podrá:

- remitir a la fuente correspondiente;
- mantener una exclusión local;
- documentar que no puede corregir permanentemente el dato de origen.

As solicitudes poden enviarse por correo a `elena@tuiterx.rocks` ou a través
do grupo público de Telegram enlazado no mapa. Deben incluír o identificador
completo do nodo sempre que sexa posible.

No se conservarán en Git datos personales incluidos en comunicaciones de
retirada o corrección.

## Borrado técnico

La retirada de un nodo deberá contar con una operación explícita y comprobable
que elimine:

- todas sus observaciones de nodo;
- las conexiones donde aparezca como origen o destino;
- avisos de configuración asociados;
- cualquier caché pública derivada.

Después del borrado se regenerarán atómicamente todos los documentos públicos.

La operación deberá informar de las filas eliminadas y ejecutar una
comprobación de integridad SQLite.

## Copias de seguridad

Las copias operativas que contengan datos reales tendrán una retención máxima
de 30 días, salvo copias temporales necesarias para una migración concreta.

Las copias de migración deberán eliminarse cuando la migración quede validada y
ya no sean necesarias para una reversión razonable.

Después de restaurar una copia se deberá:

1. volver a aplicar la lista vigente de exclusiones;
2. ejecutar el borrado de los nodos retirados;
3. regenerar los documentos públicos;
4. comprobar la integridad de SQLite.

Ninguna base de datos ni copia operativa podrá incluirse en Git.

## Datos del visitante

El frontend no utiliza cookies de seguimiento ni herramientas de analítica.

Las preferencias de interfaz se guardan únicamente en el navegador.

Cuando una persona autoriza la geolocalización, la posición se procesa en su
dispositivo y no se envía al backend de Mesh Noroeste.

Esta política sobre visitantes deberá mostrarse separada de la información
sobre los datos de nodos representados en el mapa.

## Aviso público sobre los nodos

Antes de la versión estable, el mapa deberá informar de que:

- agrega datos publicados por fuentes externas;
- los nombres, identificadores y posiciones pueden ser aproximados o
  incorrectos;
- la presencia de un nodo no identifica necesariamente a una persona ni una
  ubicación privada exacta;
- existe un canal para solicitar corrección o retirada;
- el mapa no debe utilizarse para localizar, acosar o vigilar personas.

## Repositorio público

El repositorio podrá incluir:

- código fuente;
- esquemas de datos;
- documentación;
- datos ficticios de pruebas;
- un ejemplo vacío de configuración de exclusiones.

No podrá incluir:

- bases SQLite reales;
- archivos WAL o SHM;
- documentos JSON operativos;
- cookies o cachés de fuentes;
- credenciales;
- logs operativos;
- backups;
- listas reales de exclusión;
- mensajes o datos de contacto de solicitantes.

## Estado de aplicación

Ya existe:

- exclusión de bases, cachés, datos generados y secretos mediante
  `.gitignore`;
- publicación limitada por ventanas de 24 horas, 7 días y 30 días;
- retención absoluta de 30 días para observaciones completas;
- cursores mínimos de deduplicación para nodos y conexiones;
- migración y despliegue del esquema SQLite 7;
- poda diaria bajo el mismo bloqueo operativo que los colectores;
- comprobación de integridad SQLite;
- backup diario consistente y compactado mediante `VACUUM INTO` de SQLite;
- checksum SHA-256 y rotación automática a 30 días;
- restauración real validada con el comprobador del proyecto;
- filtrado de exclusiones en la caché interna de análisis;
- lector estricto de exclusiones privadas mediante `MESH_EXCLUSIONS_PATH`;
- lista privada operativa en `/etc/mesh-noroeste/exclusions.json`;
- configuración común en `/etc/mesh-noroeste/mesh-noroeste.env`;
- carga automática de esa configuración por los colectores de systemd;
- filtrado de exclusiones durante la recolección y la publicación;
- operación `purge-node` para eliminar nodos y conexiones incidentes;
- regeneración de los documentos públicos después de una purga;
- aviso sobre privacidad y geolocalización del visitante.
- aviso público sobre os datos dos nodos e a súa procedencia;
- canles públicas por correo e Telegram para solicitar retiradas.

Permanece pendiente:

- revisar toda la documentación del proyecto antes de la versión estable.
