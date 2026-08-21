# Mesh Noroeste

Mesh Noroeste é un proxecto independente para observar, explorar e
conservar información pública das redes Meshtastic e MeshCore no
noroeste peninsular e Portugal.

A versión pública está dispoñible en:

**https://mapa.mesh.gal/**

O proxecto combina un mapa da situación actual con ferramentas para
consultar actividade recente, explorar o histórico e analizar datos
experimentais.

## Funcionalidades

### Mapa

A vista principal consolida nun único mapa información procedente de
Meshtastic e MeshCore.

Inclúe, entre outras funcións:

- filtrado por rede, fonte, rol, tipo e antigüidade;
- busca de nodos;
- fichas detalladas;
- traceroutes e outras relacións observadas;
- información de recepción mediante observers MeshCore;
- avisos de configuración Meshtastic cando existe análise dispoñible;
- estatísticas da xeración publicada;
- navegación adaptada a móbil;
- soporte de teclado, alto contraste e outras melloras de accesibilidade.

As conexións só se publican cando os dous extremos sobreviven ao mesmo
filtro rexional aplicado aos nodos, evitando relacións colgantes.

### Live

`/live/` ofrece unha vista da actividade Meshtastic recente observada a
través da fonte de Comunidade O Zulo.

Live está pensado para explorar eventos e tráfico recente, non como unha
representación completa do estado de toda a malla.

Permite, entre outras cousas:

- consultar eventos recentes;
- filtrar por tipo de evento e nodo;
- abrir a actividade asociada a un nodo;
- inspeccionar rutas cando están dispoñibles;
- navegar desde un evento ao mapa;
- continuar a análise no histórico.

### Histórico

`/history/` permite consultar a actividade Meshtastic histórica
preparada polo proxecto para a súa exploración temporal.

Inclúe:

- busca e filtrado temporal;
- consulta da actividade dun nodo;
- timeline de eventos;
- navegación entre períodos;
- URLs reproducibles para compartir unha consulta;
- integración coa vista Live.

O histórico e Live teñen finalidades distintas: Live mostra actividade
recente, mentres que o histórico permite estudar a evolución dos datos
conservados.

### Experimento LongFast / NarrowFast

`/experiment/` presenta os datos preparados para o seguimento do
experimento Meshtastic LongFast/NarrowFast.

A interface permite examinar, cando existe mostra suficiente:

- calidade e tamaño da mostra;
- distribución por preset;
- métricas comparativas;
- clasificación territorial;
- distribución por concello;
- evolución temporal;
- exportación dos datos territoriais.

A presentación separa os datos observados das conclusións e explicita as
limitacións da mostra para evitar interpretar como resultado definitivo
o que aínda é evidencia parcial.

## Redes e fontes

Mesh Noroeste integra actualmente estas fontes:

### Meshtastic

- **Malha Portugal**
- **Comunidade O Zulo**

### MeshCore

- **MeshCore Map**
- **MeshCore Hub de Mesh Galicia**

Cada fonte mantén a súa propia natureza e limitacións. Mesh Noroeste
normaliza a información necesaria para poder representala mediante un
modelo común, sen asumir que todas as fontes publican os mesmos datos.

## Ámbito xeográfico

A publicación principal aplica unha rexión formada por:

- Galicia;
- Asturias;
- León;
- Zamora;
- Portugal.

A implementación utiliza varias áreas xeográficas en lugar dun único
rectángulo para reducir a inclusión accidental de territorios alleos á
rexión de interese.

O ámbito pode substituírse por un rectángulo explícito ao executar a
publicación mediante `--bounds SOUTH WEST NORTH EAST`.

## Arquitectura

O fluxo principal é:

```text
fontes externas
      │
      ▼
colectores e adaptadores
      │
      ▼
     SQLite
      │
      ├── observacións de nodos
      ├── relacións
      ├── recepcións de observers
      ├── cursores de deduplicación
      └── execucións das fontes
      │
      ▼
consolidación e publicación
      │
      ▼
xeracións JSON inmutables
      │
      ▼
 manifest.json
      │
      ▼
frontend
```

Cada publicación crea unha xeración independente e actívaa de forma
atómica mediante `manifest.json`.

O contrato público principal é `mesh-noroeste.data/v1`.

## Persistencia e retención

SQLite conserva observacións históricas para poder consolidar os datos e
alimentar as funcionalidades que requiren información temporal.

A política operativa aplica unha retención absoluta de 30 días ás
observacións completas de nodos e conexións.

Cando unha observación caduca, poden permanecer cursores mínimos cos
identificadores e marcas temporais necesarios para impedir que
snapshots antigos sexan introducidos outra vez como datos novos.

A política de datos está documentada en `docs/DATA_POLICY.md`.

## Datos públicos xerados

A publicación principal utiliza `manifest.json` para activar unha
xeración que contén actualmente documentos como:

- `nodes.json`
- `edges.json`
- `neighbor-info.json`
- `observer-receptions.json`
- `stats.json`
- `meta.json`
- `configuration-warnings.json`

Os contratos correspondentes están documentados en
`docs/DATA_CONTRACT.md`.

## Análise de configuración Meshtastic

Mesh Noroeste pode xerar avisos de configuración a partir da actividade
publicada pola API de Comunidade O Zulo.

O documento bruto de análise almacénase normalmente en
`cache/configuration-analysis.json`.

Na instalación operativa actualízase periodicamente e a publicación le
a ruta indicada mediante `MESH_CONFIGURATION_WARNINGS_PATH`.

Se o documento non existe ou non é válido, a actualización xeral do
mapa non se bloquea: a análise publícase explicitamente como non
dispoñible.

## MeshCore Hub e observers

Mesh Noroeste utiliza tamén o MeshCore Hub de Mesh Galicia para obter
nodos, relacións observadas e recepcións atribuídas a observers.

A clave de lectura configúrase fóra do repositorio mediante
`MESHCORE_HUB_API_READ_KEY`.

As coordenadas ausentes ou xeograficamente imposibles publicadas polo
Hub non bloquean a actualización completa: descártase a posición
afectada e consérvase o resto da información válida do nodo.

Para instalar un observer que publique no Hub de Mesh Galicia, consulta
`docs/OBSERVERS.md`.

## Exclusións e privacidade operativa

A instalación pode definir:

```bash
MESH_EXCLUSIONS_PATH=/etc/mesh-noroeste/exclusions.json
```

O ficheiro de exclusións é privado e queda fóra de Git.

As exclusións aplícanse antes de almacenar e publicar os datos. Se o
ficheiro configurado desaparece ou contén JSON inválido, os colectores
detéñense antes de descargar ou modificar SQLite.

Para executar manualmente comandos que dependan da configuración
operativa:

```bash
set -a
. /etc/mesh-noroeste/mesh-noroeste.env
set +a
```

## Automatización

A instalación de produción utiliza unidades e temporizadores de
systemd para executar de forma independente:

- actualización desde Malha Portugal;
- actualización desde Comunidade O Zulo;
- actualización desde MeshCore Map;
- actualización desde MeshCore Hub;
- actualización do tráfico Live;
- poda da base histórica;
- copias de seguridade.

Un fallo temporal dunha fonte non debe impedir que as demais continúen
actualizándose.

## Uso local

Os principais comandos do backend son:

```bash
.venv/bin/mesh-noroeste collect-malha
.venv/bin/mesh-noroeste collect-ozulo
.venv/bin/mesh-noroeste collect-meshcore
.venv/bin/mesh-noroeste collect-meshcore-hub
.venv/bin/mesh-noroeste check
.venv/bin/mesh-noroeste publish
.venv/bin/mesh-noroeste prune
```

Por defecto, SQLite almacénase en `MESH_STATE_DIR/mesh-noroeste.db` e
os documentos públicos escríbense en `MESH_DATA_DIR`.

Tamén poden indicarse rutas explícitas:

```bash
.venv/bin/mesh-noroeste collect-malha \
  --database /ruta/mesh-noroeste.db \
  --cookie-file /ruta/privada/malha-pt.cookies \
  --cache-file /ruta/privada/malha-pt.json

.venv/bin/mesh-noroeste collect-meshcore \
  --database /ruta/mesh-noroeste.db

.venv/bin/mesh-noroeste collect-meshcore-hub \
  --database /ruta/mesh-noroeste.db

.venv/bin/mesh-noroeste publish \
  --database /ruta/mesh-noroeste.db \
  --output /ruta/datos-publicos
```

## Validación

A comprobación completa do proxecto execútase con:

```bash
./scripts/check-project.sh
```

O script comproba a sintaxe, executa as probas automatizadas, valida
os contratos públicos e revisa a integridade do diff de Git.

## Documentación

A documentación técnica principal está repartida entre:

- `docs/FUNCTIONAL.md`: comportamento funcional;
- `docs/SPEC.md`: especificación xeral;
- `docs/DATA_CONTRACT.md`: contratos dos datos;
- `docs/DATA_POLICY.md`: política de conservación e publicación;
- `docs/RELATIONSHIP_MODEL.md`: modelo de relacións;
- `docs/CLEAN_ROOM.md`: desenvolvemento clean-room;
- `docs/OBSERVERS.md`: instalación de observers MeshCore.

## Desenvolvemento clean-room

Este repositorio é unha implementación independente escrita desde cero.

Non contén código copiado de Meshtastic-es-map nin doutros mapas sen
licenza compatible.

## Licenzas

O software propio deste repositorio distribúese baixo a GNU Affero
General Public License v3.0 ou posterior (AGPL-3.0-or-later).

A documentación propia distribúese baixo Creative Commons
Atribución-CompartirIgual 4.0 Internacional (CC-BY-SA-4.0).

Os compoñentes de terceiros conservan as súas respectivas licenzas. Os
avisos e atribucións están recollidos en `THIRD_PARTY_NOTICES.md`.

Estas licenzas non se aplican automaticamente aos datos, identificadores,
posicións, observacións, teselas cartográficas nin outros materiais
obtidos de fontes externas. Eses contidos permanecen sometidos ás
condicións das súas fontes respectivas.

A distribución de licenzas explícase con máis detalle en
`LICENSES/README.md`.

## Proxectos e despregamentos anteriores

A versión actual de Mesh Noroeste publícase en:

https://mapa.mesh.gal/

O mapa anterior é un proxecto separado e continúa dispoñible en:

https://mesh.tuiter.ovh/
