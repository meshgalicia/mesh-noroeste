# Observers de MeshCore Hub

Guía para instalar e configurar observers remotos que envían ao Hub de Mesh
Galicia os paquetes recibidos por unha radio MeshCore en modo Companion.

## Que é un observer

Neste proxecto, un observer está formado por:

- unha radio con firmware MeshCore Companion;
- un computador conectado á radio mediante BLE, serie ou TCP;
- MeshCore Packet Capture;
- unha conexión a Internet para publicar os datos en `mqtt.mesh.gal`.

O observer escoita o tráfico que recibe a radio e publica no Hub os paquetes e
o estado do dispositivo. Non crea rutas, non actúa como repetidor e non xera
traceroutes por si mesmo.

Esta guía foi contrastada co código e co instalador de MeshCore Packet Capture 2.1.0.

## Alcance

O procedemento recomendado é unha instalación administrada como servizo
`systemd` en Linux. É tamén o procedemento previsto para unha Raspberry Pi cun
sistema Linux compatible.

MeshCore Packet Capture admite estas conexións coa radio:

1. Bluetooth Low Energy (BLE).
2. Serie mediante USB.
3. TCP mediante unha ponte de rede, por exemplo `ser2net`.

A radio debe usar firmware **Companion**. Este programa non captura paquetes
desde repetidores, Room Servers nin sensores usando o protocolo propio deses
roles.

## Requisitos

Antes de instalar o observer fan falta:

- unha radio MeshCore con firmware Companion;
- Linux con `systemd`;
- Python 3.11 ou posterior;
- acceso de administración mediante `sudo`;
- acceso a Internet;
- unha conexión BLE, serie ou TCP coa radio;
- os parámetros de radio correctos para a rede que se quere observar.

Non é necesario abrir portos de entrada no router. O observer inicia unha
conexión saínte cifrada por WebSocket a `mqtt.mesh.gal:443`.

## Preset de Mesh Galicia

Mesh Galicia publica un preset para evitar configurar manualmente o broker:

```
https://mesh.gal/config/meshcore-galicia.toml
```

O preset configura:

- servidor `mqtt.mesh.gal`;
- porto 443;
- transporte WebSocket;
- TLS con verificación do certificado;
- autenticación mediante token;
- audiencia `mqtt.mesh.gal`;
- publicación dos paquetes e do estado do observer;
- inclusión dos datos descodificados dispoñibles.

A conexión coa radio e o código territorial GAL configúranse localmente
durante a instalación.

O preset é público e non contén contrasinais nin claves privadas.

## Instalación en Linux ou Raspberry Pi

Executa o instalador administrado oficial:

```
sudo bash -c "$(curl -fsSL https://raw.githubusercontent.com/agessaman/meshcore-packet-capture/main/install.sh)"
```

O instalador descarga a última versión publicada, crea un usuario de
servizo, instala o programa baixo `/opt`, escribe a configuración baixo
`/etc` e pode crear o servizo systemd.

### Método de instalación

Cando apareza o menú Installation Method, selecciona:

```
1) System service (systemd/launchd)
```

En Linux isto instala o servizo:

```
meshcore-packet-capture.service
```

A opción Docker existe, pero non é a recomendada para esta guía. O acceso a
BLE e aos dispositivos serie é máis directo mediante o servizo nativo.

### Conexión coa radio

No menú Device Connection Configuration, escolle unha opción:

```
1) Bluetooth Low Energy (BLE)
2) Serial
3) TCP
```

**BLE**

O instalador pode buscar radios próximas. Selecciona a radio Companion que
funcionará como observer.

Tamén é posible omitir a busca e introducir:

- o enderezo BLE ou UUID;
- o nome do dispositivo, de maneira opcional.

O instalador comproba e prepara BlueZ cando é necesario.

**Serie**

Conecta a radio por USB e selecciona o dispositivo serie correspondente. En
Linux adoita ter unha ruta como:

```
/dev/ttyACM0
```

ou:

```
/dev/ttyUSB0
```

Debe seleccionarse a ruta que mostre realmente o instalador no equipo.

**TCP**

Introduce o nome ou enderezo IP da ponte TCP e o porto configurado. O valor
predeterminado do instalador é o porto 5000.

Esta opción é útil cando a radio está conectada por serie a outro equipo que
expón a conexión na rede.

### Configuración do broker MQTT

Cando apareza o menú MQTT Broker Configuration, selecciona:

```
2) Import a preset from a URL or local path
```

Introduce esta URL:

```
https://mesh.gal/config/meshcore-galicia.toml
```

O instalador descarga o ficheiro, valida que sexa TOML e comproba que
conteña polo menos un broker válido.

O preset queda instalado normalmente como:

```
/etc/meshcore-packet-capture/config.d/10-meshcore-galicia.toml
```

Cando pregunte se queres engadir ou xestionar outro broker, responde que
non, salvo que necesites publicar tamén noutro servizo.

### Código territorial

O instalador pedirá un código IATA de tres letras. Para os observers de
Mesh Galicia utiliza:

```
GAL
```

Este valor forma parte dos temas MQTT publicados polo observer:

```
meshcore/GAL/<CLAVE_PUBLICA>/status
meshcore/GAL/<CLAVE_PUBLICA>/packets
```

### Identificación opcional da persoa responsable

Os presets con autenticación por token permiten engadir de maneira
opcional:

- a clave pública MeshCore da persoa responsable;
- un enderezo de correo electrónico.

Estes datos non son necesarios para que o observer publique paquetes. Serven
para asociar voluntariamente o observer coa persoa que o administra.

Non introduzas a clave privada da radio nin ningunha frase de recuperación.
A autenticación utiliza a identidade criptográfica do dispositivo Companion.

### Ficheiros de configuración

Nunha instalación administrada, os ficheiros principais están en:

```
/etc/meshcore-packet-capture/config.toml
/etc/meshcore-packet-capture/config.d/
```

A configuración importada desde Mesh Galicia estará normalmente en:

```
/etc/meshcore-packet-capture/config.d/10-meshcore-galicia.toml
```

As opcións locais do dispositivo, do código territorial e da identidade
opcional gárdanse normalmente en:

```
/etc/meshcore-packet-capture/config.d/99-user.toml
```

Os ficheiros de `config.d` cárganse por orde alfabética. O ficheiro
`99-user.toml` aplícase despois dos presets e permite conservar as opcións
propias do observer.

Non publiques unha copia completa de `99-user.toml`: pode conter un correo
electrónico ou credenciais doutros brokers engadidos posteriormente.

## Comprobación do servizo

Comproba que o servizo está habilitado e activo:

```
sudo systemctl is-enabled meshcore-packet-capture.service
sudo systemctl is-active meshcore-packet-capture.service
```

Consulta o estado detallado:

```
sudo systemctl --no-pager --full status meshcore-packet-capture.service
```

Consulta os últimos rexistros:

```
sudo journalctl \
  --unit meshcore-packet-capture.service \
  --no-pager \
  --lines 100
```

Para seguir os rexistros en tempo real:

```
sudo journalctl \
  --unit meshcore-packet-capture.service \
  --follow
```

Nos rexistros debe poder comprobarse:

- a conexión coa radio Companion;
- o inicio da captura;
- a conexión co broker MQTT;
- a publicación do estado ou dos paquetes recibidos.

Os textos concretos poden cambiar entre versións. Non se debe depender
dunha mensaxe literal para considerar válida a instalación.

### Reinicio do servizo

Despois de cambiar a configuración:

```
sudo systemctl restart meshcore-packet-capture.service
```

Volta comprobar o estado:

```
sudo systemctl --no-pager --full status meshcore-packet-capture.service
```

### Proba de arranque automático

Un observer non debe considerarse terminado ata comprobar o arranque tras
un reinicio do equipo.

Reinicia:

```
sudo reboot
```

Despois de volver conectar ao equipo, comproba:

```
sudo systemctl is-enabled meshcore-packet-capture.service
sudo systemctl is-active meshcore-packet-capture.service
sudo journalctl \
  --unit meshcore-packet-capture.service \
  --boot \
  --no-pager \
  --lines 100
```

O resultado esperado é:

```
enabled
active
```

## Verificación no Hub e no mapa

Unha vez conectado o observer:

1. comproba nos rexistros que a radio e MQTT están conectados;
2. deixa que a radio reciba anuncios ou outros paquetes MeshCore;
3. comproba que o Hub de Mesh Galicia recibe información;
4. comproba posteriormente a aparición ou actualización dos nodos no mapa.

Servizos públicos:

```
https://hub.mesh.gal
https://mapa.mesh.gal
```

A publicación no mapa non ten por que ser instantánea. O Hub recibe primeiro
os datos e Mesh Noroeste incorpóraos nos seus ciclos de recollida e
publicación.

## Diagnóstico básico

### O servizo non arranca

Executa:

```
sudo systemctl --no-pager --full status meshcore-packet-capture.service
sudo journalctl \
  --unit meshcore-packet-capture.service \
  --no-pager \
  --lines 200
```

Revisa especialmente:

- erros de sintaxe TOML;
- ausencia da conexión coa radio;
- permisos sobre o dispositivo serie;
- enderezo BLE incorrecto;
- host ou porto TCP incorrectos;
- falta do código GAL;
- ausencia dun broker configurado.

### Non aparece o preset

Comproba:

```
sudo find /etc/meshcore-packet-capture/config.d \
  -maxdepth 1 \
  -type f \
  -name '*.toml' \
  -print
```

Debe aparecer un ficheiro equivalente a:

```
10-meshcore-galicia.toml
```

Tamén podes comprobar que o preset público segue accesible:

```
curl \
  --fail \
  --location \
  --silent \
  --show-error \
  https://mesh.gal/config/meshcore-galicia.toml
```

### A radio está conectada pero non se publican paquetes

Comproba:

- que o dispositivo executa firmware Companion;
- que a radio está recibindo tráfico MeshCore;
- que os parámetros de frecuencia, ancho de banda, spreading factor e
  coding rate son os correctos;
- que o servizo está conectado a `mqtt.mesh.gal`;
- que o reloxo do sistema é correcto;
- que o código configurado é GAL.

O observer só pode publicar o tráfico que recibe realmente a súa radio.

### O observer publica estado pero non aparecen nodos novos

Isto pode ser normal cando a radio non recibiu anuncios útiles. O estado do
observer e os paquetes MeshCore publícanse en temas distintos.

Espera a que a radio reciba tráfico e revisa os rexistros antes de
modificar a configuración.

## Actualización ou reconfiguración

O instalador administrado pode volver executarse para actualizar ou revisar
unha instalación existente:

```
sudo bash -c "$(curl -fsSL https://raw.githubusercontent.com/agessaman/meshcore-packet-capture/main/install.sh)"
```

Antes de aceptar cambios, comproba que o instalador detecta a instalación
existente e conserva a configuración de:

```
/etc/meshcore-packet-capture/
```

Despois dunha actualización repite:

```
sudo systemctl is-active meshcore-packet-capture.service
sudo journalctl \
  --unit meshcore-packet-capture.service \
  --no-pager \
  --lines 100
```

## Desinstalación

O proxecto upstream publica este desinstalador:

```
sudo bash -c "$(curl -fsSL https://raw.githubusercontent.com/agessaman/meshcore-packet-capture/main/uninstall.sh)"
```

Antes de executalo, conserva unha copia da configuración cando poida ser
necesario reinstalar o observer.

## Windows

MeshCore Packet Capture inclúe `install.ps1`, pero o soporte actual de
Windows é manual e está orientado a desenvolvemento.

Limitacións documentadas polo proxecto upstream:

- non instala un servizo con arranque automático;
- utiliza unha contorna virtual e execución manual;
- escribe parte da configuración en `.env.local`;
- BLE en Windows é limitado e non está probado;
- serie e TCP son as conexións previstas nesa plataforma.

Por estes motivos, Mesh Galicia non considera aínda Windows unha plataforma
recomendada para observers permanentes.

A instalación básica desde unha copia do repositorio é:

```
.\install.ps1
```

Antes de publicar unha guía completa para Windows debe probarse de
principio a fin:

- instalación limpa;
- conexión serie ou TCP;
- importación ou adaptación do preset;
- autenticación contra `mqtt.mesh.gal`;
- execución persistente;
- recuperación tras un reinicio.

## Lista de aceptación

Un observer queda validado cando se comproba todo o seguinte:

- [ ] a radio utiliza firmware Companion;
- [ ] a conexión BLE, serie ou TCP funciona;
- [ ] o preset de Mesh Galicia está instalado;
- [ ] o código territorial é GAL;
- [ ] `meshcore-packet-capture.service` está habilitado;
- [ ] o servizo está activo;
- [ ] os rexistros confirman a conexión MQTT;
- [ ] o Hub recibe tráfico da radio;
- [ ] o servizo recupera a conexión tras reinicialo;
- [ ] o observer volve funcionar despois de reiniciar o equipo.
