# Modelo de relacións e observacións

## 1. Obxectivo

Mesh Noroeste integra varias fontes que poden describir os mesmos nodos con
datos, marcas temporais, períodos de retención e significados diferentes.

Este documento define como distinguir:

- a entidade canónica do nodo;
- as observacións achegadas por cada fonte;
- as relacións consolidadas;
- os traceroutes;
- os anuncios NeighborInfo;
- as regras de fusión e publicación.

## 2. Principios

- O nodo é unha entidade canónica.
- As observacións pertencen ás fontes.
- A procedencia e a marca temporal forman parte do dato.
- A ausencia dun dato nunha fonte non invalida un dato válido doutra.
- Un valor nulo non debe borrar automaticamente outro valor válido.
- Só se deduplican observacións equivalentes.
- Non se fusionan conceptos con significados distintos.
- A publicación rexional non modifica o significado do dato orixinal.

## 3. Entidade canónica

Os nodos Meshtastic identifícanse mediante:

    !xxxxxxxx

O identificador canónico público incorpora a rede:

    meshtastic:!xxxxxxxx

Dúas fontes que publiquen o mesmo identificador describen a mesma entidade,
aínda que discrepen no nome, posición, rol, firmware ou última actividade.

Debe conservarse como mínimo:

- o identificador de cada fonte;
- a última observación por fonte;
- os metadatos achegados por cada fonte;
- a posición e a súa data cando existan.

## 4. Tipos de relación e observación

### 4.1. Veciñanza publicada

Corresponde actualmente a:

    edge_type: neighbor

Representa unha conexión directa consolidada e publicada explicitamente pola
fonte.

Características:

- é non dirixida;
- pode proceder dun procesamento interno da fonte;
- pode non conservar todo o histórico;
- pode non incluír SNR ou RSSI;
- non debe confundirse cun traceroute.

### 4.2. Traceroute

Corresponde actualmente a:

    edge_type: traceroute

Representa un camiño observado entre unha orixe e un destino.

Características:

- é dirixido;
- non implica comunicación directa entre os extremos;
- non converte os extremos en veciños directos;
- distintas fontes poden publicar rutas diferentes.

### 4.3. NeighborInfo

NeighborInfo é un anuncio Meshtastic emitido por un nodo que declara os
veciños que observa e o SNR asociado a cada un nese instante.

Características:

- conserva a dirección semántica emisor → veciño observado;
- poden existir múltiples anuncios da mesma parella;
- o SNR pode variar;
- a ausencia nun anuncio posterior non proba que a relación desaparecese;
- non equivale automaticamente a unha veciñanza consolidada.

Mesh Noroeste conserva estas observacións como histórico específico e
publícaas en `neighbor-info.json`. A interface preséntaas como «veciños
observados», separadas das relacións `neighbor` consolidadas e dos
traceroutes.

### 4.4. `observed` e `unknown`

O contrato v1 admite tamén:

    edge_type: observed
    edge_type: unknown

Actualmente ningún colector produce estes tipos.

`observed` existe desde a base inicial do proxecto, pero non ten unha semántica
suficientemente precisa para asumir que representa NeighborInfo. O exemplo
histórico do contrato é unha conexión MeshCore non dirixida, mentres que
NeighborInfo é unha observación Meshtastic emitida por un nodo concreto.

Por tanto:

- non se reutiliza `observed` para representar NeighborInfo;
- non se modifica o significado de `neighbor`;
- NeighborInfo non se publica como traceroute;
- publícase nun documento específico, `neighbor-info.json`.

## 5. Capacidades comprobadas das fontes

### Mapa consolidado de O Zulo

Mesh Noroeste consome:

- `data/nodes.json`;
- `data/edges.json`.

O ficheiro de conexións publica relacións `neighbor` e `traceroute`, que se
normalizan como `EdgeObservation`.

### Meshview de O Zulo

A ficha de nodo utiliza ademais:

    /api/packets?portnum=71&from_node_id=<nodo>&limit=500

A gráfica reconstrúe o histórico de NeighborInfo analizando os payloads dos
paquetes. Tamén utiliza `/api/nodes?node_id=<nodo>` para resolver nomes e
metadatos.

Estes datos non equivalen necesariamente aos de `data/edges.json`.

## 6. Caso comprobado: SLG2

SLG2 corresponde a:

    !b03c4574
    2956739956

A API de paquetes devolveu tres anuncios NeighborInfo con sete veciños:

- SLG4;
- JJF1;
- OKK;
- SLG1;
- SLG5;
- VGC2;
- SLG3.

Tras recuperar o colector, `data/edges.json` publicou seis veciñanzas
consolidadas de SLG2:

- SLG4;
- JJF1;
- SLG1;
- SLG5;
- VGC2;
- SLG3.

OKK:

- aparece en NeighborInfo;
- aparece en `data/nodes.json` de O Zulo;
- non aparece como conexión SLG2–OKK en `data/edges.json`;
- non ten posición;
- non se publica en Mesh Noroeste;
- tampouco pode publicarse unha conexión cara a el no contrato actual.

Isto demostra que NeighborInfo e `neighbor` consolidado son datos distintos.

O valor inicial de cero veciñanzas de SLG2 non estaba causado pola
deduplicación entre fontes, senón polo fallo completo do colector de O Zulo.

## 7. Incidencia do colector de O Zulo

O Zulo publicou algúns nodos con coordenadas nulas e `precision_bits` non
nulo.

O dominio esixe correctamente que unha precisión só exista cando hai
coordenadas. O adaptador pasaba ese valor residual e abortaba toda a recollida.

Consecuencias observadas:

- fallos cada trinta minutos;
- actividade desactualizada de Vigo/Cepudo2;
- ausencia das novas veciñanzas de O Zulo;
- conservación da última instantánea correcta na base de datos.

O commit `388bbf5` omite a precisión cando non existen coordenadas. A
recollida real posterior completouse correctamente e publicou unha nova
xeración.

## 8. Regras de fusión

### Nodos

- Fusionar por identificador canónico.
- Conservar a última observación por fonte.
- Calcular `last_seen` coa observación válida máis recente.
- Escoller a posición entre observacións con coordenadas e data válidas.
- Non inferir posición por nome, veciñanza ou traceroute.
- Non permitir que unha observación sen posición borre outra válida.

### Relacións

- Deduplicar só relacións co mesmo identificador e tipo.
- Manter separados `neighbor`, `traceroute` e NeighborInfo.
- A ausencia nunha fonte non elimina unha relación válida doutra.
- Conservar procedencia e marca temporal.
- Un modelo futuro debería conservar varias fontes equivalentes, non só a
  fonte gañadora.

### Publicación rexional

Actualmente:

- só se publican nodos con posición dentro da rexión;
- só se publican conexións cuxos dous extremos están en `nodes.json`;
- só se publican observacións NeighborInfo cando os seus dous extremos están
  tamén no `nodes.json` da mesma xeración.

A base de datos pode conter observacións válidas que non aparecen na xeración
pública.

## 9. Implementación de NeighborInfo

NeighborInfo está implementado como unha entidade específica,
`NeighborObservation`, separada de `EdgeObservation`.

Regras actuais:

1. Consérvase o histórico das observacións recibidas dentro da retención.
2. As observacións completas teñen a mesma retención máxima de 30 días que o
   resto dos datos históricos publicables.
3. A identidade dunha observación combina fonte, emisor, veciño observado e
   marca temporal.
4. Persístese na táboa específica `neighbor_observations`.
5. Publícase no documento independente `neighbor-info.json`.
6. Unha observación só se publica cando os seus dous extremos existen no
   `nodes.json` da mesma xeración.
7. A interface diferencia explicitamente:
   - veciñanza publicada;
   - veciño observado;
   - traceroute.
8. A exclusión de calquera dos dous extremos impide almacenar novas
   observacións e impide tamén a súa publicación.

NeighborInfo non é un alias de `neighbor`: conserva dirección, marca temporal
e SNR da observación orixinal sen convertela nunha veciñanza consolidada.

## 10. Evolución futura

O modelo debe permitir incorporar:

- NeighborInfo doutras fontes;
- observacións RF;
- observacións MQTT;
- relacións específicas de MeshCore;
- observadores propios;
- novas fontes públicas.

Cada ampliación debe manter separadas identidade, procedencia, marca temporal,
tipo de observación e regras de publicación.
