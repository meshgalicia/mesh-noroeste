"use strict";

const DATA_MANIFEST = "./data/manifest.json";
const PUBLIC_MANIFEST_SCHEMA = (
  "mesh-noroeste.manifest/v1"
);
const PUBLIC_DATA_SCHEMA = (
  "mesh-noroeste.data/v1"
);
const PUBLIC_CONFIGURATION_WARNINGS_SCHEMA = (
  "mesh-noroeste.configuration-warnings/v1"
);

const DATA_DOCUMENT_NAMES = Object.freeze({
  nodes: "nodes.json",
  edges: "edges.json",
  neighborInfo: "neighbor-info.json",
  observerReceptions: "observer-receptions.json",
  stats: "stats.json",
  meta: "meta.json",
  configurationWarnings: (
    "configuration-warnings.json"
  ),
});

const DATA_DOCUMENT_SCHEMAS = Object.freeze({
  nodes: PUBLIC_DATA_SCHEMA,
  edges: PUBLIC_DATA_SCHEMA,
  neighborInfo: PUBLIC_DATA_SCHEMA,
  observerReceptions: PUBLIC_DATA_SCHEMA,
  stats: PUBLIC_DATA_SCHEMA,
  meta: PUBLIC_DATA_SCHEMA,
  configurationWarnings: (
    PUBLIC_CONFIGURATION_WARNINGS_SCHEMA
  ),
});

const NETWORK_LABELS = Object.freeze({
  meshtastic: "Meshtastic",
  meshcore: "MeshCore",
});

const SOURCE_LABELS = Object.freeze({
  meshview_es: "Meshview España",
  malha_pt: "Malha Portugal",
  ozulo_map: "Comunidade O Zulo",
  meshcore_map: "MeshCore Map",
  meshcore_hub: "MeshCore Hub de Mesh Galicia",
});

const TYPE_LABELS = Object.freeze({
  client: "Cliente",
  repeater: "Repetidor",
  room_server: "Room Server",
  sensor: "Sensor",
  unknown: "Tipo descoñecido",
});

const MESHCORE_CONTACT_TYPES = Object.freeze({
  client: 1,
  repeater: 2,
  room_server: 3,
  sensor: 4,
});

const ROLE_LABELS = Object.freeze({
  CLIENT: "CLIENT · Cliente",
  CLIENT_BASE: "CLIENT_BASE · Cliente base",
  CLIENT_MUTE: "CLIENT_MUTE · Cliente silencioso",
  ROUTER: "ROUTER · Router",
  ROUTER_LATE: "ROUTER_LATE · Router tardío",
  TRACKER: "TRACKER · Rastreador",
  unknown: "Sen rol publicado",
});

const WARNING_LABELS = Object.freeze({
  range_test_active: "Range Test activo",
  fixed_position_frequent: (
    "Posición fixa emitida con demasiada frecuencia"
  ),
  mobile_position_frequent: (
    "Posición móbil emitida con demasiada frecuencia"
  ),
  node_info_frequent: (
    "Información do nodo emitida con demasiada frecuencia"
  ),
  device_telemetry_frequent: (
    "Telemetría do dispositivo demasiado frecuente"
  ),
  environment_telemetry_frequent: (
    "Telemetría ambiental demasiado frecuente"
  ),
  power_telemetry_frequent: (
    "Telemetría de alimentación demasiado frecuente"
  ),
  routing_frequent: (
    "Mensaxes de enrutamento demasiado frecuentes"
  ),
  position_fields_unnecessary: (
    "Campos de posición innecesarios para un nodo fixo"
  ),
  automatic_traceroute_frequent: (
    "Traceroutes automáticos demasiado frecuentes"
  ),
  hop_limit_high: "Límite de saltos excesivo",
  client_base_firmware_old: (
    "Firmware antigo nun nodo CLIENT_BASE"
  ),
  client_mute_mobile: (
    "CLIENT_MUTE configurado nun nodo móbil"
  ),
});

const WARNING_SEVERITY_LABELS = Object.freeze({
  medium: "media",
  high: "alta",
  critical: "crítica",
});

const AGE_LABELS = Object.freeze({
  hour: "Menos de 1 hora",
  day: "Entre 1 e 24 horas",
  week: "Entre 1 e 7 días",
  month: "Entre 7 e 30 días",
});

const AGE_OPACITY = Object.freeze({
  hour: 0.98,
  day: 0.86,
  week: 0.66,
  month: 0.46,
});

const MESHCORE_ACTIVITY_WINDOWS = Object.freeze({
  hour: 1,
  day: 24,
  week: 24 * 7,
});

const DETAILS_STORAGE_PREFIX = "mesh-noroeste:details:";
const SIDEBAR_STORAGE_KEY = (
  "mesh-noroeste:controls-collapsed"
);

const PRIVACY_STORAGE_KEY = (
  "mesh-noroeste:privacy-notice-dismissed"
);

const MOBILE_BREAKPOINT = "(max-width: 780px)";

const FOCUSABLE_SELECTOR = [
  "a[href]",
  "button:not([disabled])",
  "input:not([disabled])",
  "select:not([disabled])",
  "textarea:not([disabled])",
  "summary",
  '[tabindex]:not([tabindex="-1"])',
].join(", ");

const MOBILE_PANEL_TITLES = Object.freeze({
  search: "Buscar nodo",
  network: "Rede",
  filters: "Lenda e filtros",
  layers: "Mapa",
  info: "Información",
});

const DESKTOP_PANEL_TARGETS = Object.freeze({
  search: '[data-mobile-panel="search"]',
  network: '[data-mobile-panel="network"]',
  filters: "#legend-details",
  layers: '[data-mobile-panel="layers"]',
  info: '[data-mobile-panel="info"]',
});

let activeMobilePanel = null;
let lastMobileTrigger = null;
let lastDetailTrigger = null;

const MESHTASTIC_ROLE_STYLES = Object.freeze({
  CLIENT: {
    color: "#1b5e2a",
    fillColor: "#2b8a3e",
    radius: 6,
    weight: 1.6,
  },
  CLIENT_BASE: {
    color: "#075c68",
    fillColor: "#0c8599",
    radius: 7,
    weight: 2.2,
  },
  CLIENT_MUTE: {
    color: "#6a1b7b",
    fillColor: "#9c36b5",
    radius: 6.5,
    weight: 2,
    dashArray: "2 2",
  },
  ROUTER: {
    color: "#9c1f1f",
    fillColor: "#e03131",
    radius: 8.5,
    weight: 2.6,
  },
  ROUTER_LATE: {
    color: "#9c5a00",
    fillColor: "#f08c00",
    radius: 8.5,
    weight: 2.6,
    dashArray: "4 2",
  },
  TRACKER: {
    color: "#8f2449",
    fillColor: "#d6336c",
    radius: 7.5,
    weight: 2.3,
    dashArray: "1 2",
  },
  unknown: {
    color: "#212529",
    fillColor: "#495057",
    radius: 6,
    weight: 1.7,
    dashArray: "2 3",
  },
});

const COLORS = Object.freeze({
  repeater: {
    color: "#0b4f8a",
    fillColor: "#1971c2",
    radius: 7.5,
    weight: 2.2,
  },
  room_server: {
    color: "#000000",
    fillColor: "#212529",
    radius: 7.5,
    weight: 2.2,
  },
  client: {
    color: "#806500",
    fillColor: "#ffd43b",
    radius: 7,
    weight: 2.2,
  },
  unknown: {
    color: "#343a40",
    fillColor: "#868e96",
    radius: 6.5,
    weight: 2,
  },
});

const state = {
  map: null,
  renderer: null,
  baseLayers: new Map(),
  currentBaseLayer: null,
  currentBaseMapName: "street",
  nodeLayer: null,
  labelLayer: null,
  edgeLayer: null,
  nodes: [],
  edges: [],
  neighborInfo: [],
  observerReceptions: [],
  receptionsByNodeId: new Map(),
  receptionsByObserverId: new Map(),
  meshcoreActivityByNodeId: new Map(),
  stats: null,
  meta: null,
  configurationWarnings: null,
  warningByNodeId: new Map(),
  generatedAt: null,
  dataStatusObserver: null,
  labelRenderFrame: null,
  nodeById: new Map(),
  markerById: new Map(),
  visibleNodes: [],
  visibleIds: new Set(),
  selectedNodeId: null,
  locationMarker: null,
  accuracyCircle: null,
  nodePrecisionCircle: null,
};

const elements = {
  appShell: document.querySelector(".app-shell"),
  mapRegion: document.querySelector(".map-region"),
  mapContainer: document.querySelector("#map"),
  sidebar: document.querySelector("#sidebar-panel"),
  dataStatus: document.querySelector("#data-status"),
  mobileDataStatus: document.querySelector(
    "#mobile-data-status"
  ),
  mobileToolbar: document.querySelector("#mobile-toolbar"),
  mobileTabs: Array.from(
    document.querySelectorAll(".mobile-tab")
  ),
  desktopCollapsedNav: document.querySelector(
    "#desktop-collapsed-nav"
  ),
  desktopRailButtons: Array.from(
    document.querySelectorAll(".desktop-rail-button")
  ),
  mobileBackdrop: document.querySelector(
    "#mobile-backdrop"
  ),
  mobileSheetTitle: document.querySelector(
    "#mobile-sheet-title"
  ),
  mobileSheetClose: document.querySelector(
    "#mobile-sheet-close"
  ),
  mobilePanelBlocks: Array.from(
    document.querySelectorAll("[data-mobile-panel]")
  ),
  sidebarToggle: document.querySelector("#sidebar-toggle"),
  sidebarToggleLabel: document.querySelector(
    "#sidebar-toggle-label"
  ),
  sidebarControls: document.querySelector(
    "#sidebar-controls"
  ),
  search: document.querySelector("#node-search"),
  searchResults: document.querySelector("#search-results"),
  searchStatus: document.querySelector("#node-search-status"),
  traceroutes: document.querySelector("#traceroutes-toggle"),
  tracerouteControls: document.querySelector(
    "#traceroute-controls"
  ),
  tracerouteSource: document.querySelector(
    "#traceroute-source"
  ),
  tracerouteAge: document.querySelector(
    "#traceroute-age"
  ),
  meshcoreCompleteRoutes: document.querySelector(
    "#meshcore-complete-routes-toggle"
  ),
  meshcoreFragmentedRoutes: document.querySelector(
    "#meshcore-fragmented-routes-toggle"
  ),
  meshcoreNeighbors: document.querySelector(
    "#meshcore-neighbors-toggle"
  ),
  neighbors: document.querySelector("#neighbors-toggle"),
  neighborInfo: document.querySelector(
    "#neighbor-info-toggle"
  ),
  basemapInputs: Array.from(
    document.querySelectorAll('input[name="basemap"]')
  ),
  fitMap: document.querySelector("#fit-map"),
  locateMe: document.querySelector("#locate-me"),
  locationStatus: document.querySelector("#location-status"),
  visibleCount: document.querySelector("#visible-count"),
  meshtasticCount: document.querySelector("#meshtastic-count"),
  meshcoreCount: document.querySelector("#meshcore-count"),
  edgeCount: document.querySelector("#edge-count"),
  sourceStatus: document.querySelector("#source-status"),
  ageDetailsHome: document.querySelector(
    "#age-details-home"
  ),
  ageDetails: document.querySelector("#age-details"),
  legendDetailsHome: document.querySelector(
    "#legend-details-home"
  ),
  legendDetails: document.querySelector("#legend-details"),
  legendInformationHome: document.querySelector(
    "#legend-information-home"
  ),
  legendInformation: document.querySelector(
    "#legend-information"
  ),
  sourceDetails: document.querySelector("#source-details"),
  ageSummary: document.querySelector("#age-summary"),
  typeSummary: document.querySelector("#type-summary"),
  typeFilterReset: document.querySelector("#type-filter-reset"),
  mqttGatewayFilter: document.querySelector(
    "#mqtt-gateway-filter"
  ),
  mqttGatewaySummary: document.querySelector(
    "#mqtt-gateway-summary"
  ),
  meshcoreObserverFilter: document.querySelector(
    "#meshcore-observer-filter"
  ),
  meshcoreObserverSummary: document.querySelector(
    "#meshcore-observer-summary"
  ),
  meshcoreActivityFilter: document.querySelector(
    "#meshcore-activity-filter"
  ),
  meshcoreActivitySummary: document.querySelector(
    "#meshcore-activity-summary"
  ),
  meshcoreActivityControls: document.querySelector(
    "#meshcore-activity-controls"
  ),
  meshcoreActivityWindow: document.querySelector(
    "#meshcore-activity-window"
  ),
  filterEmptyPanel: document.querySelector(
    "#filter-empty-panel"
  ),
  loadingPanel: document.querySelector("#loading-panel"),
  errorPanel: document.querySelector("#error-panel"),
  privacyNotice: document.querySelector("#privacy-notice"),
  privacyDismiss: document.querySelector("#privacy-dismiss"),
  detailPanel: document.querySelector("#detail-panel"),
  detailNetwork: document.querySelector("#detail-network"),
  detailTitle: document.querySelector("#detail-title"),
  detailContent: document.querySelector("#detail-content"),
  detailSizeToggle: document.querySelector(
    "#detail-size-toggle"
  ),
  detailClose: document.querySelector("#detail-close"),
};

function normalizeText(value) {
  return String(value ?? "")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLocaleLowerCase("gl-ES")
    .trim();
}

function formatNumber(value) {
  return new Intl.NumberFormat("gl-ES").format(value);
}

function formatDate(value) {
  if (!value) {
    return "Sen datos";
  }

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return String(value);
  }

  return new Intl.DateTimeFormat("gl-ES", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(date);
}

function formatCoordinate(value) {
  return Number(value).toFixed(5);
}

function formatMetric(value, suffix = "") {
  if (
    value === null
    || value === undefined
    || value === ""
  ) {
    return null;
  }

  return `${value}${suffix}`;
}

function nodeName(node) {
  return (
    node.long_name
    || node.short_name
    || node.id.replace(/^[^:]+:/, "")
  );
}

function networkLabel(network) {
  return NETWORK_LABELS[network] || network;
}

function meshtasticRoleKey(node) {
  if (
    node.role
    && Object.prototype.hasOwnProperty.call(
      MESHTASTIC_ROLE_STYLES,
      node.role
    )
  ) {
    return node.role;
  }

  return "unknown";
}

function typeLabel(node) {
  if (node.network === "meshtastic") {
    return ROLE_LABELS[meshtasticRoleKey(node)];
  }

  return TYPE_LABELS[node.node_type] || TYPE_LABELS.unknown;
}

function ageKey(node) {
  const reference = state.generatedAt?.getTime();
  const observed = Date.parse(node.last_seen || "");

  if (
    Number.isFinite(reference)
    && Number.isFinite(observed)
  ) {
    const ageHours = Math.max(
      0,
      (reference - observed) / 3_600_000
    );

    if (ageHours < 1) {
      return "hour";
    }

    if (ageHours < 24) {
      return "day";
    }

    if (ageHours < 24 * 7) {
      return "week";
    }

    return "month";
  }

  if (node.status.active) {
    return "day";
  }

  if (node.status.recent) {
    return "week";
  }

  return "month";
}

function statusLabel(node) {
  return AGE_LABELS[ageKey(node)];
}

function markerStyle(node) {
  let base;

  if (node.network === "meshtastic") {
    base = MESHTASTIC_ROLE_STYLES[
      meshtasticRoleKey(node)
    ];
  } else {
    base = COLORS[node.node_type] || COLORS.unknown;
  }

  const fillOpacity = AGE_OPACITY[ageKey(node)];

  return {
    ...base,
    weight: base.weight ?? 1.5,
    opacity: Math.min(1, fillOpacity + 0.08),
    fillOpacity,
  };
}

function positionPrecisionRadiusMeters(node) {
  if (
    node.position_precision_bits == null
    || node.latitude == null
  ) {
    return 0;
  }

  const precisionBits = Number(
    node.position_precision_bits
  );
  const latitude = Number(node.latitude);

  if (
    !Number.isInteger(precisionBits)
    || precisionBits < 0
    || precisionBits > 32
    || !Number.isFinite(latitude)
  ) {
    return 0;
  }

  if (precisionBits >= 32) {
    return 0;
  }

  const stepDegrees = (
    Math.pow(2, 32 - precisionBits)
    / 10_000_000
  );

  return (
    stepDegrees
    * 111_320
    * Math.cos(latitude * Math.PI / 180)
  );
}

function clearSelectedNodePrecision() {
  if (
    state.map
    && state.nodePrecisionCircle
  ) {
    state.map.removeLayer(
      state.nodePrecisionCircle
    );
  }

  state.nodePrecisionCircle = null;
}

function renderSelectedNodePrecision(node) {
  clearSelectedNodePrecision();

  if (!state.map || !node) {
    return;
  }

  const radius = positionPrecisionRadiusMeters(node);

  if (!Number.isFinite(radius) || radius <= 10) {
    return;
  }

  const style = markerStyle(node);

  state.nodePrecisionCircle = L.circle(
    [node.latitude, node.longitude],
    {
      pane: "precision",
      radius,
      color: "#d000ff",
      weight: 1.5,
      opacity: 0.75,
      fillColor: "#d000ff",
      fillOpacity: 0.06,
      interactive: false,
    }
  ).addTo(state.map);
}

function precisionFocusZoom(node) {
  const radius = positionPrecisionRadiusMeters(node);

  if (!Number.isFinite(radius) || radius <= 10) {
    return Math.max(state.map.getZoom(), 15);
  }

  if (radius <= 100) {
    return 15;
  }

  if (radius <= 1_500) {
    return 13;
  }

  if (radius <= 3_000) {
    return 12;
  }

  if (radius <= 5_000) {
    return 11;
  }

  return 10;
}

function focusNode(node) {
  state.map.setView(
    [node.latitude, node.longitude],
    precisionFocusZoom(node),
    { animate: false }
  );

  showNodeDetail(node);
}

function connectionTypeLabel(edge) {
  return {
    traceroute: "Traceroute",
    neighbor: "Veciñanza",
    observed: "Ruta observada",
  }[edge.edge_type] || edge.edge_type;
}

function connectionDirectionLabel(edge, nodeId) {
  if (!edge.directed) {
    return "Bidireccional";
  }

  return edge.from_id === nodeId
    ? "Saínte"
    : "Entrante";
}

function connectionsForNode(
  node,
  edgeType
) {
  return state.edges
    .filter(
      (edge) => (
        edge.edge_type === edgeType
        && (
          edge.from_id === node.id
          || edge.to_id === node.id
        )
      )
    )
    .sort(
      (left, right) => String(
        right.last_seen ?? ""
      ).localeCompare(
        String(left.last_seen ?? "")
      )
    );
}

function connectionCountLabel(
  count,
  singular,
  plural
) {
  return [
    formatNumber(count),
    count === 1 ? singular : plural,
  ].join(" ");
}

function appendConnectionItems(
  list,
  node,
  connections
) {
  for (const edge of connections) {
    const outgoing = edge.from_id === node.id;
    const otherId = outgoing
      ? edge.to_id
      : edge.from_id;
    const otherNode = state.nodeById.get(otherId);

    const item = document.createElement("li");
    const button = document.createElement("button");
    const title = document.createElement("strong");
    const kind = document.createElement("span");
    const metadata = document.createElement("span");

    button.type = "button";
    button.className = "connection-button";

    title.textContent = otherNode
      ? nodeName(otherNode)
      : otherId;

    kind.className = "connection-kind";
    kind.textContent = [
      connectionTypeLabel(edge),
      connectionDirectionLabel(edge, node.id),
    ].join(" · ");

    const metricParts = [
      `Última: ${formatDate(edge.last_seen)}`,
      formatMetric(edge.metrics?.snr_db, " dB")
        ? `SNR: ${formatMetric(
          edge.metrics.snr_db,
          " dB"
        )}`
        : null,
      formatMetric(edge.metrics?.rssi_dbm, " dBm")
        ? `RSSI: ${formatMetric(
          edge.metrics.rssi_dbm,
          " dBm"
        )}`
        : null,
      SOURCE_LABELS[edge.source] || edge.source,
    ].filter(Boolean);

    metadata.className = "connection-metadata";
    metadata.textContent = metricParts.join(" · ");

    button.append(title, kind, metadata);

    if (otherNode) {
      button.setAttribute(
        "aria-label",
        `Abrir o nodo ${nodeName(otherNode)}`
      );

      button.addEventListener("click", () => {
        focusNode(otherNode);
      });
    } else {
      button.disabled = true;
      button.setAttribute(
        "aria-label",
        `Nodo relacionado non dispoñible: ${otherId}`
      );
    }

    item.append(button);
    list.append(item);
  }
}

function createConnectionGroup(
  node,
  {
    title,
    connections,
    emptyText,
  }
) {
  const group = document.createElement("section");
  const heading = document.createElement("h4");

  group.className = "connection-group";
  heading.className = "connection-group-heading";
  heading.textContent = [
    title,
    `(${formatNumber(connections.length)})`,
  ].join(" ");

  group.append(heading);

  if (connections.length === 0) {
    const empty = document.createElement("p");

    empty.className = "connection-empty";
    empty.textContent = emptyText;
    group.append(empty);

    return group;
  }

  const list = document.createElement("ul");

  list.className = "connection-list";
  appendConnectionItems(list, node, connections);
  group.append(list);

  return group;
}

function createConnectionsSection(node) {
  const section = document.createElement("section");
  const heading = document.createElement("h3");
  const neighbors = connectionsForNode(
    node,
    "neighbor"
  );
  const traceroutes = connectionsForNode(
    node,
    "traceroute"
  );
  const observed = connectionsForNode(
    node,
    "observed"
  ).filter(
    (edge) => edge.network === "meshcore"
  );
  const total = (
    neighbors.length
    + traceroutes.length
    + observed.length
  );

  section.className = "detail-section";
  heading.textContent = "Conexións publicadas";
  section.append(heading);

  if (total === 0) {
    const empty = document.createElement("p");

    empty.className = "connection-empty";
    empty.textContent = (
      "Non hai conexións publicadas para este nodo."
    );

    section.append(empty);
    return section;
  }

  const summary = document.createElement("p");

  summary.className = "connection-summary";
  summary.textContent = [
    connectionCountLabel(
      neighbors.length,
      "veciñanza directa",
      "veciñanzas directas"
    ),
    connectionCountLabel(
      traceroutes.length,
      "traceroute",
      "traceroutes"
    ),
    connectionCountLabel(
      observed.length,
      "ruta observada de MeshCore",
      "rutas observadas de MeshCore"
    ),
  ].join(" · ");

  section.append(
    summary,
    createConnectionGroup(
      node,
      {
        title: "Veciños directos",
        connections: neighbors,
        emptyText: (
          "Non hai veciños directos publicados "
          + "para este nodo."
        ),
      }
    ),
    createConnectionGroup(
      node,
      {
        title: "Traceroutes",
        connections: traceroutes,
        emptyText: (
          "Non hai traceroutes publicados "
          + "para este nodo."
        ),
      }
    ),
    createConnectionGroup(
      node,
      {
        title: "Rutas observadas de MeshCore",
        connections: observed,
        emptyText: (
          "Non hai rutas observadas de MeshCore "
          + "publicadas para este nodo."
        ),
      }
    )
  );

  return section;
}

function selectedNetwork() {
  return document.querySelector(
    'input[name="network"]:checked'
  ).value;
}

function selectedAgeBands() {
  return new Set(
    Array.from(
      document.querySelectorAll(
        'input[name="age"]:checked'
      )
    ).map((input) => input.value)
  );
}

function categoryKey(node) {
  if (node.network === "meshtastic") {
    return `meshtastic:${meshtasticRoleKey(node)}`;
  }

  return `meshcore:${node.node_type || "unknown"}`;
}

function selectedCategories() {
  return new Set(
    Array.from(
      document.querySelectorAll(
        ".legend-filter[aria-pressed='true']"
      )
    ).map((button) => button.dataset.category)
  );
}

function isMqttGateway(node) {
  return (
    node.network === "meshtastic"
    && node.radio?.mqtt_gateway === true
  );
}

function isMeshcoreObserver(node) {
  return (
    node.network === "meshcore"
    && node.is_observer === true
  );
}

function meshcoreObserverFilterEnabled() {
  return (
    elements.meshcoreObserverFilter.getAttribute(
      "aria-pressed"
    ) === "true"
  );
}

function meshcoreActivityEnabled() {
  return (
    elements.meshcoreActivityFilter.getAttribute(
      "aria-pressed"
    ) === "true"
  );
}

function selectedMeshcoreActivityHours() {
  return (
    MESHCORE_ACTIVITY_WINDOWS[
      elements.meshcoreActivityWindow.value
    ]
    || MESHCORE_ACTIVITY_WINDOWS.day
  );
}

function meshcoreActivityCutoff() {
  const reference = state.generatedAt?.getTime();

  if (!Number.isFinite(reference)) {
    return null;
  }

  return (
    reference
    - selectedMeshcoreActivityHours() * 3_600_000
  );
}

function meshcoreActivityForNode(node) {
  if (node.network !== "meshcore") {
    return null;
  }

  const activity = state.meshcoreActivityByNodeId.get(
    node.id
  );

  if (!activity) {
    return null;
  }

  const cutoff = meshcoreActivityCutoff();
  const observed = Date.parse(activity.latestObservedAt || "");

  if (
    !Number.isFinite(cutoff)
    || !Number.isFinite(observed)
    || observed < cutoff
  ) {
    return null;
  }

  return activity;
}

function matchesBaseFilters(node) {
  const network = selectedNetwork();
  const ageBands = selectedAgeBands();
  const categories = selectedCategories();

  return (
    node.status.has_position
    && ageBands.has(ageKey(node))
    && categories.has(categoryKey(node))
    && (
      network === "both"
      || node.network === network
    )
  );
}

function matchesFilters(node) {
  return (
    matchesBaseFilters(node)
    && (
      elements.mqttGatewayFilter.getAttribute(
        "aria-pressed"
      ) !== "true"
      || isMqttGateway(node)
    )
    && (
      !meshcoreObserverFilterEnabled()
      || isMeshcoreObserver(node)
    )
  );
}

function searchText(node) {
  return normalizeText([
    node.id,
    node.short_name,
    node.long_name,
    node.hardware,
    node.role,
    node.node_type,
    node.is_observer === true ? "observer observador" : "",
    node.sources.join(" "),
    Object.values(node.source_ids).join(" "),
  ].join(" "));
}

function roleClass(node) {
  if (node.network === "meshtastic") {
    return `role-${meshtasticRoleKey(node)
      .toLocaleLowerCase("en-US")
      .replaceAll("_", "-")}`;
  }

  return `type-${String(node.node_type || "unknown")
    .toLocaleLowerCase("en-US")
    .replaceAll("_", "-")}`;
}

function isPriorityName(node) {
  return (
    (
      node.network === "meshtastic"
      && [
        "ROUTER",
        "ROUTER_LATE",
        "TRACKER",
      ].includes(node.role)
    )
    || (
      node.network === "meshcore"
      && node.node_type === "room_server"
    )
  );
}

function nodeMapLabelName(node, zoom) {
  const fallback = node.id.replace(/^[^:]+:/, "");
  const compactName = String(
    node.short_name
    || node.long_name
    || fallback
  ).trim();
  const completeName = String(
    node.long_name
    || node.short_name
    || fallback
  ).trim();
  const rawName = zoom >= 14
    ? completeName
    : compactName;
  const maximumLength = isMobileLayout()
    ? 23
    : 30;

  return rawName.length > maximumLength
    ? `${rawName.slice(0, maximumLength - 1)}…`
    : rawName;
}

function nodeMapLabelAllowed(node, zoom) {
  if (node.id === state.selectedNodeId) {
    return true;
  }

  if (zoom < 10) {
    return false;
  }

  if (zoom < 12) {
    return ["hour", "day"].includes(ageKey(node));
  }

  return true;
}

function nodeMapLabelPriority(node) {
  const observed = Date.parse(node.last_seen || "");
  const safeObserved = Number.isFinite(observed)
    ? -observed
    : Number.MAX_SAFE_INTEGER;
  const active = ["hour", "day"].includes(ageKey(node));

  return [
    node.id === state.selectedNodeId ? 0 : 1,
    active ? 0 : 1,
    isPriorityName(node) ? 0 : 1,
    safeObserved,
  ];
}

function compareNodeMapLabelPriority(first, second) {
  const firstPriority = nodeMapLabelPriority(first);
  const secondPriority = nodeMapLabelPriority(second);

  for (
    let index = 0;
    index < firstPriority.length;
    index += 1
  ) {
    if (firstPriority[index] !== secondPriority[index]) {
      return (
        firstPriority[index]
        - secondPriority[index]
      );
    }
  }

  return 0;
}

function nodeMapLabelRectangle(
  marker,
  name,
  direction
) {
  const point = state.map.latLngToContainerPoint(
    marker.getLatLng()
  );
  const width = Math.min(
    isMobileLayout() ? 176 : 224,
    Math.max(52, name.length * 7 + 20)
  );
  const height = 28;
  const gap = 14;
  const left = direction === "left"
    ? point.x - gap - width
    : point.x + gap;
  const top = point.y - height / 2;

  return {
    left,
    right: left + width,
    top,
    bottom: top + height,
  };
}

function nodeMapLabelRectanglesOverlap(first, second) {
  const margin = 4;

  return !(
    first.right + margin < second.left
    || first.left - margin > second.right
    || first.bottom + margin < second.top
    || first.top - margin > second.bottom
  );
}

function makeNodeMapLabelIcon(
  node,
  direction,
  zoom
) {
  const label = document.createElement("span");
  const selected = node.id === state.selectedNodeId;

  label.className = [
    "node-map-label",
    `network-${node.network}`,
    `node-map-label-${direction}`,
    selected ? "selected" : "",
  ].filter(Boolean).join(" ");

  label.textContent = nodeMapLabelName(node, zoom);

  return L.divIcon({
    html: label,
    iconSize: [1, 1],
    iconAnchor: [0, 0],
    className: "node-map-label-icon",
  });
}

function renderNodeLabels() {
  if (
    !state.map
    || !state.nodeLayer
    || !state.labelLayer
  ) {
    return;
  }

  state.labelLayer.clearLayers();

  const zoom = state.map.getZoom();
  const mapSize = state.map.getSize();
  const multipleNetworks = new Set(
    state.visibleNodes.map((node) => node.network)
  ).size > 1;

  const candidates = state.visibleNodes
    .filter((node) => {
      const marker = state.markerById.get(node.id);

      return (
        marker
        && state.nodeLayer.getVisibleParent(marker) === marker
        && nodeMapLabelAllowed(node, zoom)
      );
    })
    .sort(compareNodeMapLabelPriority);

  let maximumLabels;

  if (isMobileLayout()) {
    maximumLabels = multipleNetworks
      ? 18
      : zoom >= 17
        ? 32
        : 20;
  } else {
    maximumLabels = multipleNetworks
      ? 42
      : zoom >= 17
        ? 80
        : 48;
  }

  const occupied = [];
  let rendered = 0;

  for (const node of candidates) {
    if (rendered >= maximumLabels) {
      break;
    }

    const marker = state.markerById.get(node.id);

    if (!marker) {
      continue;
    }

    const point = state.map.latLngToContainerPoint(
      marker.getLatLng()
    );
    const direction = point.x > mapSize.x * 0.68
      ? "left"
      : "right";
    const name = nodeMapLabelName(node, zoom);
    const rectangle = nodeMapLabelRectangle(
      marker,
      name,
      direction
    );

    const outsideViewport = (
      rectangle.right < 0
      || rectangle.left > mapSize.x
      || rectangle.bottom < 0
      || rectangle.top > mapSize.y
    );

    if (outsideViewport) {
      continue;
    }

    const selected = node.id === state.selectedNodeId;
    const collides = occupied.some(
      (previous) => nodeMapLabelRectanglesOverlap(
        rectangle,
        previous
      )
    );

    if (collides && !selected) {
      continue;
    }

    const labelMarker = L.marker(
      marker.getLatLng(),
      {
        icon: makeNodeMapLabelIcon(
          node,
          direction,
          zoom
        ),
        pane: "labels",
        interactive: false,
        keyboard: false,
        zIndexOffset: selected ? 1000 : 0,
      }
    );

    state.labelLayer.addLayer(labelMarker);
    occupied.push(rectangle);
    rendered += 1;
  }
}

function scheduleNodeLabels() {
  if (!state.map) {
    return;
  }

  if (state.labelRenderFrame !== null) {
    window.cancelAnimationFrame(
      state.labelRenderFrame
    );
  }

  state.labelRenderFrame = window.requestAnimationFrame(
    () => {
      state.labelRenderFrame = null;
      renderNodeLabels();
    }
  );
}

function createNodeIcon(node) {
  const style = markerStyle(node);
  const selected = node.id === state.selectedNodeId;
  const size = Math.max(
    20,
    Math.round(style.radius * 3.15)
  );

  const classes = [
    "node-marker-visual",
    `network-${node.network}`,
    roleClass(node),
    `activity-${ageKey(node)}`,
    selected ? "selected" : "",
  ].filter(Boolean);

  const cssVariables = [
    `--node-fill:${style.fillColor}`,
    `--node-border:${style.color}`,
    `--node-size:${size}px`,
    `--node-stroke:${style.weight}px`,
    `--node-opacity:${style.fillOpacity}`,
  ].join(";");

  const gatewayClass = isMqttGateway(node)
    ? " mqtt-gateway"
    : "";
  const observerClass = (
    node.network === "meshcore"
    && node.is_observer === true
  )
    ? " meshcore-observer"
    : "";
  const activity = meshcoreActivityForNode(node);
  const activityClass = (
    meshcoreActivityEnabled()
    && node.network === "meshcore"
  )
    ? (
      activity
        ? " meshcore-activity-visible"
        : " meshcore-activity-muted"
    )
    : "";

  return L.divIcon({
    className: "node-marker-icon",
    html:
      `<span class="node-marker-badge${gatewayClass}${observerClass}${activityClass}"`
      + ` style="${cssVariables}">`
      + `<span class="${classes.join(" ")}"></span>`
      + "</span>",
    iconSize: [52, 52],
    iconAnchor: [26, 26],
    tooltipAnchor: [0, -25],
  });
}

function bindNodeTooltip(marker, node) {
  marker.unbindTooltip();

  marker.bindTooltip(
    (
      node.network === "meshcore"
      && node.is_observer === true
    )
      ? `${nodeName(node)} · Observer`
      : nodeName(node),
    {
      className: "node-tooltip",
      direction: "top",
      offset: [0, -3],
      permanent: false,
      opacity: 0.96,
    }
  );
}

function refreshNodeMarker(nodeId) {
  if (!nodeId) {
    return;
  }

  const marker = state.markerById.get(nodeId);
  const node = state.nodeById.get(nodeId);

  if (!marker || !node) {
    return;
  }

  marker.setIcon(createNodeIcon(node));
  bindNodeTooltip(marker, node);
}

function createClusterIcon(cluster) {
  const markers = cluster.getAllChildMarkers();
  const meshtastic = markers.filter(
    (marker) => marker.meshNode?.network === "meshtastic"
  ).length;
  const meshcore = markers.length - meshtastic;

  let kind = "mixed";

  if (meshcore === 0) {
    kind = "meshtastic";
  } else if (meshtastic === 0) {
    kind = "meshcore";
  }

  const size = markers.length >= 100
    ? 50
    : markers.length >= 20
      ? 46
      : 42;

  return L.divIcon({
    className: "node-cluster-icon",
    html:
      `<span class="node-cluster ${kind}">`
      + `${formatNumber(markers.length)}`
      + "</span>",
    iconSize: [size, size],
    iconAnchor: [size / 2, size / 2],
  });
}

function renderVisibleNodes() {
  state.labelLayer.clearLayers();
  state.nodeLayer.clearLayers();
  state.markerById.clear();

  const markers = state.visibleNodes.map((node) => {
    const marker = createMarker(node);

    state.markerById.set(node.id, marker);
    return marker;
  });

  state.nodeLayer.addLayers(markers);
  scheduleNodeLabels();
}

function setBaseMap(name) {
  const nextLayer = state.baseLayers.get(name);

  if (
    !nextLayer
    || nextLayer === state.currentBaseLayer
  ) {
    return;
  }

  if (
    state.currentBaseLayer
    && state.map.hasLayer(state.currentBaseLayer)
  ) {
    state.map.removeLayer(state.currentBaseLayer);
  }

  nextLayer.addTo(state.map);
  state.currentBaseLayer = nextLayer;
  state.currentBaseMapName = name;
  renderVisibleEdges();
}

function clusterSharesExactPosition(cluster) {
  const markers = cluster.getAllChildMarkers();

  if (markers.length < 2) {
    return false;
  }

  const first = markers[0].getLatLng();

  return markers.every((marker) => {
    const position = marker.getLatLng();

    return (
      first.lat === position.lat
      && first.lng === position.lng
    );
  });
}

function activateCluster(event) {
  const cluster = event.layer;

  event.originalEvent?.preventDefault();

  if (clusterSharesExactPosition(cluster)) {
    cluster.spiderfy();
    return;
  }

  cluster.zoomToBounds();
}

function createMap() {
  state.map = L.map("map", {
    preferCanvas: true,
    minZoom: 5,
    maxZoom: 18,
  });

  state.map.attributionControl.setPrefix(false);

  state.renderer = L.canvas({
    padding: 0.5,
  });

  state.map.createPane("precision");
  state.map.getPane("precision").style.zIndex = "380";
  state.map.getPane("precision").style.pointerEvents = "none";

  state.map.createPane("routes");
  state.map.getPane("routes").style.zIndex = "390";

  state.map.createPane("nodes");
  state.map.getPane("nodes").style.zIndex = "430";

  state.map.createPane("labels");
  state.map.getPane("labels").style.zIndex = "460";
  state.map.getPane("labels").style.pointerEvents = "none";

  const streetLayer = L.tileLayer(
    "https://tile.openstreetmap.org/{z}/{x}/{y}.png",
    {
      maxZoom: 19,
      attribution:
        '&copy; <a href="https://www.openstreetmap.org/copyright">'
        + "OpenStreetMap</a> contributors",
    }
  );

  const satelliteLayer = L.tileLayer(
    "https://server.arcgisonline.com/ArcGIS/rest/services/"
      + "World_Imagery/MapServer/tile/{z}/{y}/{x}",
    {
      maxZoom: 19,
      attribution:
        "&copy; Esri, Maxar, Earthstar Geographics, "
        + "GIS User Community",
    }
  );

  state.baseLayers = new Map([
    ["street", streetLayer],
    ["satellite", satelliteLayer],
  ]);

  state.currentBaseLayer = streetLayer;
  streetLayer.addTo(state.map);

  state.edgeLayer = L.layerGroup().addTo(state.map);
  state.labelLayer = L.layerGroup().addTo(state.map);

  state.nodeLayer = L.markerClusterGroup({
    maxClusterRadius: (zoom) => {
      if (zoom <= 8) {
        return 52;
      }

      return zoom < 12 ? 44 : 0.01;
    },
    showCoverageOnHover: false,
    zoomToBoundsOnClick: false,
    spiderfyOnMaxZoom: false,
    removeOutsideVisibleBounds: true,
    chunkedLoading: true,
    chunkProgress: (processed, total) => {
      if (processed === total) {
        scheduleNodeLabels();
      }
    },
    animate: true,
    iconCreateFunction: createClusterIcon,
  }).addTo(state.map);

  state.map.on("zoomend", scheduleNodeLabels);
  state.map.on("moveend", scheduleNodeLabels);

  state.nodeLayer.on(
    "clusterclick clusterkeypress",
    activateCluster
  );

  state.nodeLayer.on(
    "animationend spiderfied unspiderfied",
    scheduleNodeLabels
  );
}

function setRegionalView() {
  const bounds = state.meta.region.bounds;

  const south = bounds.south;
  const west = bounds.west;
  const north = bounds.north;
  const east = bounds.east;

  state.map.fitBounds(
    [
      [south, west],
      [north, east],
    ],
    {
      padding: [24, 24],
      maxZoom: 7,
    }
  );
}

function setLocationStatus(message, tone = "") {
  elements.locationStatus.textContent = message;
  elements.locationStatus.className = "location-status";

  if (tone) {
    elements.locationStatus.classList.add(tone);
  }
}

function removePreviousLocation() {
  for (const layer of [
    state.locationMarker,
    state.accuracyCircle,
  ]) {
    if (layer && state.map.hasLayer(layer)) {
      state.map.removeLayer(layer);
    }
  }

  state.locationMarker = null;
  state.accuracyCircle = null;
}

function geolocationErrorMessage(error) {
  const messages = {
    1: "Permiso de localización denegado.",
    2: "Non foi posible determinar a posición.",
    3: "A procura da posición superou o tempo límite.",
  };

  return (
    messages[error.code]
    || "Produciuse un erro ao obter a posición."
  );
}

function showUserLocation(position) {
  const latitude = Number(position.coords.latitude);
  const longitude = Number(position.coords.longitude);
  const accuracy = Number(position.coords.accuracy);

  if (
    !Number.isFinite(latitude)
    || !Number.isFinite(longitude)
  ) {
    throw new Error(
      "O navegador devolveu coordenadas inválidas."
    );
  }

  removePreviousLocation();

  const point = [latitude, longitude];

  if (Number.isFinite(accuracy) && accuracy >= 0) {
    state.accuracyCircle = L.circle(
      point,
      {
        pane: "routes",
        radius: Math.max(accuracy, 1),
        color: "#a61e4d",
        weight: 1,
        opacity: 0.65,
        fillColor: "#d63384",
        fillOpacity: 0.08,
        interactive: false,
      }
    ).addTo(state.map);
  }

  state.locationMarker = L.circleMarker(
    point,
    {
      pane: "nodes",
      radius: 8,
      color: "#ffffff",
      weight: 3,
      opacity: 1,
      fillColor: "#d63384",
      fillOpacity: 1,
    }
  )
    .bindTooltip(
      "A túa posición aproximada",
      {
        direction: "top",
        offset: [0, -6],
      }
    )
    .addTo(state.map);

  if (
    state.accuracyCircle
    && accuracy > 25
  ) {
    state.map.fitBounds(
      state.accuracyCircle.getBounds(),
      {
        padding: [40, 40],
        maxZoom: 16,
      }
    );
  } else {
    state.map.setView(
      point,
      Math.max(state.map.getZoom(), 15)
    );
  }

  const accuracyText = (
    Number.isFinite(accuracy)
      ? ` · precisión aproximada ±${Math.round(accuracy)} m`
      : ""
  );

  setLocationStatus(
    `Posición localizada${accuracyText}.`,
    "success"
  );
}

function locateUser() {
  if (!window.isSecureContext) {
    setLocationStatus(
      "A localización require HTTPS.",
      "error"
    );
    return;
  }

  if (!navigator.geolocation) {
    setLocationStatus(
      "Este navegador non ofrece xeolocalización.",
      "error"
    );
    return;
  }

  elements.locateMe.disabled = true;

  setLocationStatus(
    "Solicitando permiso e procurando a posición…"
  );

  navigator.geolocation.getCurrentPosition(
    (position) => {
      elements.locateMe.disabled = false;

      try {
        showUserLocation(position);
      } catch (error) {
        setLocationStatus(
          String(error.message || error),
          "error"
        );
      }
    },
    (error) => {
      elements.locateMe.disabled = false;

      setLocationStatus(
        geolocationErrorMessage(error),
        "error"
      );
    },
    {
      enableHighAccuracy: true,
      timeout: 15000,
      maximumAge: 30000,
    }
  );
}

function createMarker(node) {
  const marker = L.marker(
    [node.latitude, node.longitude],
    {
      icon: createNodeIcon(node),
      pane: "nodes",
      keyboard: true,
      riseOnHover: true,
      title: nodeName(node),
      alt: `Nodo ${nodeName(node)}`,
    }
  );

  marker.meshNode = node;
  bindNodeTooltip(marker, node);

  marker.on("click", () => {
    showNodeDetail(node);
  });

  return marker;
}

function bearing(fromNode, toNode) {
  const lat1 = fromNode.latitude * Math.PI / 180;
  const lat2 = toNode.latitude * Math.PI / 180;
  const deltaLongitude = (
    toNode.longitude - fromNode.longitude
  ) * Math.PI / 180;

  const y = Math.sin(deltaLongitude) * Math.cos(lat2);
  const x = (
    Math.cos(lat1) * Math.sin(lat2)
    - Math.sin(lat1)
    * Math.cos(lat2)
    * Math.cos(deltaLongitude)
  );

  return (
    Math.atan2(y, x) * 180 / Math.PI + 360
  ) % 360;
}

function midpoint(fromNode, toNode) {
  return [
    (fromNode.latitude + toNode.latitude) / 2,
    (fromNode.longitude + toNode.longitude) / 2,
  ];
}

function edgeTouchesSelectedNode(edge) {
  return (
    state.selectedNodeId !== null
    && (
      edge.from_id === state.selectedNodeId
      || edge.to_id === state.selectedNodeId
    )
  );
}

function addTraceroute(edge) {
  if (edge.edge_type !== "traceroute") {
    return;
  }

  const fromNode = state.nodeById.get(edge.from_id);
  const toNode = state.nodeById.get(edge.to_id);

  if (!fromNode || !toNode) {
    return;
  }

  const selected = edgeTouchesSelectedNode(edge);
  const satellite = (
    state.currentBaseMapName === "satellite"
  );
  const routePoints = [
    [fromNode.latitude, fromNode.longitude],
    [toNode.latitude, toNode.longitude],
  ];

  L.polyline(
    routePoints,
    {
      pane: "routes",
      renderer: state.renderer,
      color: selected
        ? "#a61e4d"
        : (satellite ? "#845ef7" : "#5f3dc4"),
      weight: selected ? 1.6 : 1.5,
      opacity: selected
        ? 0.92
        : (satellite ? 0.62 : 0.48),
      dashArray: selected ? "9 5" : "5 6",
      interactive: false,
    }
  ).addTo(state.edgeLayer);

  L.marker(
    midpoint(fromNode, toNode),
    {
      pane: "routes",
      interactive: false,
      keyboard: false,
      icon: L.divIcon({
        className: selected
          ? "route-arrow selected"
          : "route-arrow",
        html:
          `<span style="transform:rotate(${bearing(
            fromNode,
            toNode
          )}deg)">▲</span>`,
        iconSize: selected ? [18, 18] : [14, 14],
        iconAnchor: selected ? [9, 9] : [7, 7],
      }),
    }
  ).addTo(state.edgeLayer);
}

function addMeshcoreObserved(edge) {
  if (
    edge.edge_type !== "observed"
    || edge.network !== "meshcore"
  ) {
    return;
  }

  const fromNode = state.nodeById.get(edge.from_id);
  const toNode = state.nodeById.get(edge.to_id);

  if (!fromNode || !toNode) {
    return;
  }

  const selected = edgeTouchesSelectedNode(edge);

  const routePoints = [
    [fromNode.latitude, fromNode.longitude],
    [toNode.latitude, toNode.longitude],
  ];

  L.polyline(
    routePoints,
    {
      pane: "routes",
      renderer: state.renderer,
      color: selected ? "#7048a8" : "#8f70b5",
      weight: selected ? 2.6 : 1.8,
      opacity: selected ? 0.94 : 0.62,
      dashArray: "8 4 2 4",
      interactive: false,
    }
  ).addTo(state.edgeLayer);

  L.marker(
    midpoint(fromNode, toNode),
    {
      pane: "routes",
      interactive: false,
      keyboard: false,
      icon: L.divIcon({
        className: selected
          ? "meshcore-route-arrow selected"
          : "meshcore-route-arrow",
        html:
          `<span style="transform:rotate(${bearing(
            fromNode,
            toNode
          )}deg)">▲</span>`,
        iconSize: selected ? [18, 18] : [14, 14],
        iconAnchor: selected ? [9, 9] : [7, 7],
      }),
    }
  ).addTo(state.edgeLayer);
}


function meshcoreObservedNeighborPairs(edges) {
  const pairs = new Map();

  for (const edge of edges) {
    if (
      edge.edge_type !== "observed"
      || edge.network !== "meshcore"
      || !edge.from_id
      || !edge.to_id
      || edge.from_id === edge.to_id
    ) {
      continue;
    }

    const endpoints = [
      edge.from_id,
      edge.to_id,
    ].sort();

    const key = endpoints.join("|");
    const previous = pairs.get(key);

    if (
      !previous
      || String(edge.last_seen || "")
        > String(previous.last_seen || "")
    ) {
      pairs.set(
        key,
        {
          ...edge,
          from_id: endpoints[0],
          to_id: endpoints[1],
          directed: false,
        }
      );
    }
  }

  return Array.from(pairs.values());
}

function addMeshcoreObservedNeighbor(edge) {
  const fromNode = state.nodeById.get(edge.from_id);
  const toNode = state.nodeById.get(edge.to_id);

  if (!fromNode || !toNode) {
    return;
  }

  L.polyline(
    [
      [fromNode.latitude, fromNode.longitude],
      [toNode.latitude, toNode.longitude],
    ],
    {
      pane: "routes",
      renderer: state.renderer,
      color: "#087f8c",
      weight: 1.8,
      opacity: 0.48,
      dashArray: "3 5",
      interactive: false,
    }
  ).addTo(state.edgeLayer);
}


function addNeighbor(edge) {
  if (edge.edge_type !== "neighbor") {
    return;
  }

  const fromNode = state.nodeById.get(edge.from_id);
  const toNode = state.nodeById.get(edge.to_id);

  if (!fromNode || !toNode) {
    return;
  }

  const selected = edgeTouchesSelectedNode(edge);

  L.polyline(
    [
      [fromNode.latitude, fromNode.longitude],
      [toNode.latitude, toNode.longitude],
    ],
    {
      pane: "routes",
      renderer: state.renderer,
      color: selected ? "#006d77" : "#343a40",
      weight: selected ? 2.6 : 2.2,
      opacity: selected ? 0.92 : 0.52,
      interactive: false,
    }
  ).addTo(state.edgeLayer);
}

function addVisibleEdge(edge) {
  if (edge.edge_type === "traceroute") {
    addTraceroute(edge);
    return;
  }

  if (
    edge.edge_type === "observed"
    && edge.network === "meshcore"
  ) {
    addMeshcoreObserved(edge);
    return;
  }

  if (edge.edge_type === "neighbor") {
    addNeighbor(edge);
  }
}

function addNeighborInfo(observation) {
  const fromNode = state.nodeById.get(
    observation.from_id
  );
  const toNode = state.nodeById.get(
    observation.to_id
  );

  if (!fromNode || !toNode) {
    return;
  }

  const selected = edgeTouchesSelectedNode(
    observation
  );

  L.polyline(
    [
      [fromNode.latitude, fromNode.longitude],
      [toNode.latitude, toNode.longitude],
    ],
    {
      pane: "routes",
      renderer: state.renderer,
      color: selected ? "#9c2f6f" : "#c2255c",
      weight: selected ? 2.4 : 1.8,
      opacity: selected ? 0.94 : 0.62,
      dashArray: "2 6",
      interactive: false,
    }
  ).addTo(state.edgeLayer);
}


function edgeEndpointsAreVisible(edge) {
  return (
    state.visibleIds.has(edge.from_id)
    && state.visibleIds.has(edge.to_id)
  );
}

function tracerouteSourceMatches(edge) {
  const selectedSource = elements.tracerouteSource.value;

  return (
    selectedSource === "all"
    || edge.source === selectedSource
  );
}

function tracerouteAgeMatches(edge) {
  const selectedAge = elements.tracerouteAge.value;

  if (selectedAge === "all") {
    return true;
  }

  const reference = state.generatedAt?.getTime();
  const observed = Date.parse(edge.last_seen || "");

  if (
    !Number.isFinite(reference)
    || !Number.isFinite(observed)
  ) {
    return false;
  }

  const maximumHours = (
    selectedAge === "day"
      ? 24
      : 24 * 7
  );

  const ageHours = Math.max(
    0,
    (reference - observed) / 3_600_000
  );

  return ageHours <= maximumHours;
}

function meshcoreRouteCompleteness(edges) {
  const indexesByRouteId = new Map();

  for (const edge of edges) {
    if (
      edge.edge_type !== "observed"
      || edge.network !== "meshcore"
      || !edge.route_id
      || !Number.isInteger(edge.route_index)
    ) {
      continue;
    }

    const indexes = indexesByRouteId.get(
      edge.route_id
    ) || [];

    indexes.push(edge.route_index);
    indexesByRouteId.set(edge.route_id, indexes);
  }

  const complete = new Set();
  const fragmented = new Set();

  for (const [routeId, indexes] of indexesByRouteId) {
    const ordered = [...new Set(indexes)].sort(
      (left, right) => left - right
    );

    const hasGap = ordered.some(
      (value, index) => (
        index > 0
        && value > ordered[index - 1] + 1
      )
    );

    (hasGap ? fragmented : complete).add(routeId);
  }

  return {
    complete,
    fragmented,
  };
}

function meshcoreObservedEdgeEnabled(
  edge,
  routeCompleteness
) {
  if (
    edge.edge_type !== "observed"
    || edge.network !== "meshcore"
  ) {
    return false;
  }

  if (
    edge.route_id
    && routeCompleteness.fragmented.has(edge.route_id)
  ) {
    return elements.meshcoreFragmentedRoutes.checked;
  }

  return elements.meshcoreCompleteRoutes.checked;
}

function globalEdgeEnabled(
  edge,
  routeCompleteness
) {
  if (edge.edge_type === "traceroute") {
    return (
      elements.traceroutes.checked
      && tracerouteSourceMatches(edge)
      && tracerouteAgeMatches(edge)
    );
  }

  if (
    edge.edge_type === "observed"
    && edge.network === "meshcore"
  ) {
    return meshcoreObservedEdgeEnabled(
      edge,
      routeCompleteness
    );
  }

  if (edge.edge_type === "neighbor") {
    return elements.neighbors.checked;
  }

  return false;
}

function updateTracerouteControlsVisibility() {
  const enabled = elements.traceroutes.checked;

  elements.tracerouteControls.hidden = !enabled;
  elements.tracerouteSource.disabled = !enabled;
  elements.tracerouteAge.disabled = !enabled;
  elements.traceroutes.setAttribute(
    "aria-expanded",
    String(enabled)
  );
}

function edgeRenderPriority(edge) {
  return edge.edge_type === "neighbor" ? 1 : 0;
}

function edgesInRenderOrder(edges) {
  return [...edges].sort(
    (left, right) => (
      edgeRenderPriority(left)
      - edgeRenderPriority(right)
    )
  );
}

function selectedMeshcoreRouteIds(edges) {
  if (state.selectedNodeId === null) {
    return new Set();
  }

  return new Set(
    edges
      .filter(
        (edge) => (
          edge.edge_type === "observed"
          && edge.network === "meshcore"
          && edge.route_id
          && edgeTouchesSelectedNode(edge)
        )
      )
      .map((edge) => edge.route_id)
  );
}

function edgeBelongsToSelectedMeshcoreRoute(
  edge,
  routeIds
) {
  return (
    edge.edge_type === "observed"
    && edge.network === "meshcore"
    && edge.route_id
    && routeIds.has(edge.route_id)
  );
}

function meshcoreRouteFragments(edges) {
  const ordered = edges
    .filter(
      (edge) => (
        edge.edge_type === "observed"
        && edge.network === "meshcore"
        && edge.route_id
        && Number.isInteger(edge.route_index)
      )
    )
    .sort(
      (left, right) => (
        left.route_id.localeCompare(right.route_id)
        || left.route_index - right.route_index
      )
    );

  const fragments = [];

  for (let index = 0; index < ordered.length - 1; index += 1) {
    const left = ordered[index];
    const right = ordered[index + 1];

    if (
      left.route_id === right.route_id
      && right.route_index > left.route_index + 1
    ) {
      fragments.push({
        left,
        right,
      });
    }
  }

  return fragments;
}

function addMeshcoreRouteGap(fragment) {
  const fromNode = state.nodeById.get(
    fragment.left.to_id
  );
  const toNode = state.nodeById.get(
    fragment.right.from_id
  );

  if (!fromNode || !toNode) {
    return;
  }

  L.polyline(
    [
      [fromNode.latitude, fromNode.longitude],
      [toNode.latitude, toNode.longitude],
    ],
    {
      pane: "routes",
      renderer: state.renderer,
      color: "#6c757d",
      weight: 1.4,
      opacity: 0.72,
      dashArray: "2 8",
      interactive: false,
    }
  ).addTo(state.edgeLayer);

  L.marker(
    midpoint(fromNode, toNode),
    {
      pane: "routes",
      interactive: false,
      keyboard: false,
      icon: L.divIcon({
        className: "meshcore-route-gap",
        html: '<span aria-hidden="true">?</span><span class="visually-hidden">Ruta incompleta</span>',
        iconSize: [18, 18],
        iconAnchor: [9, 9],
      }),
    }
  ).addTo(state.edgeLayer);
}

function renderVisibleEdges() {
  state.edgeLayer.clearLayers();

  const candidateEdges = state.edges.filter(
    edgeEndpointsAreVisible
  );
  const selectedRouteIds = selectedMeshcoreRouteIds(
    state.edges
  );
  const routeCompleteness = meshcoreRouteCompleteness(
    state.edges
  );
  const visibleMeshcoreNeighbors = (
    elements.meshcoreNeighbors.checked
    && state.selectedNodeId === null
      ? meshcoreObservedNeighborPairs(state.edges).filter(
          edgeEndpointsAreVisible
        )
      : []
  );
  const visibleNeighborInfo = (
    elements.neighborInfo.checked
      ? state.neighborInfo.filter(
          edgeEndpointsAreVisible
        )
      : []
  );
  const selectedEdges = state.edges.filter(
    (edge) => (
      edgeTouchesSelectedNode(edge)
      || edgeBelongsToSelectedMeshcoreRoute(
        edge,
        selectedRouteIds
      )
    )
  );
  const regularEdges = candidateEdges.filter(
    (edge) => (
      state.selectedNodeId === null
      && !edgeTouchesSelectedNode(edge)
      && globalEdgeEnabled(
        edge,
        routeCompleteness
      )
    )
  );

  for (
    const edge of edgesInRenderOrder(regularEdges)
  ) {
    addVisibleEdge(edge);
  }

  for (const edge of visibleMeshcoreNeighbors) {
    addMeshcoreObservedNeighbor(edge);
  }

  for (const observation of visibleNeighborInfo) {
    addNeighborInfo(observation);
  }

  for (
    const edge of edgesInRenderOrder(selectedEdges)
  ) {
    addVisibleEdge(edge);
  }

  for (
    const fragment
    of meshcoreRouteFragments(selectedEdges)
  ) {
    addMeshcoreRouteGap(fragment);
  }

  updateVisibleStatistics(
    regularEdges.length
    + selectedEdges.length
    + visibleMeshcoreNeighbors.length
    + visibleNeighborInfo.length
  );
}

function updateVisibleStatistics(edgeCount) {
  const meshtastic = state.visibleNodes.filter(
    (node) => node.network === "meshtastic"
  ).length;

  elements.visibleCount.textContent = formatNumber(
    state.visibleNodes.length
  );
  elements.meshtasticCount.textContent = formatNumber(
    meshtastic
  );
  elements.meshcoreCount.textContent = formatNumber(
    state.visibleNodes.length - meshtastic
  );
  elements.edgeCount.textContent = formatNumber(edgeCount);
}

function updateMqttGatewaySummary() {
  const available = state.nodes.filter(
    (node) => (
      matchesBaseFilters(node)
      && isMqttGateway(node)
    )
  ).length;

  elements.mqttGatewaySummary.textContent = (
    `${formatNumber(available)} dispoñibles`
  );
}

function updateMeshcoreObserverSummary() {
  const available = state.nodes.filter(
    (node) => (
      matchesBaseFilters(node)
      && isMeshcoreObserver(node)
    )
  ).length;

  elements.meshcoreObserverSummary.textContent = (
    `${formatNumber(available)} dispoñibles`
  );
}

function updateMeshcoreActivitySummary() {
  const available = state.nodes.filter(
    (node) => (
      matchesBaseFilters(node)
      && node.network === "meshcore"
      && meshcoreActivityForNode(node) !== null
    )
  ).length;

  elements.meshcoreActivitySummary.textContent = (
    available === 1
      ? "1 nodo observado"
      : `${formatNumber(available)} nodos observados`
  );
}

function updateMeshcoreActivityControls() {
  const enabled = meshcoreActivityEnabled();

  elements.meshcoreActivityControls.hidden = !enabled;
  elements.meshcoreActivityWindow.disabled = !enabled;
  elements.meshcoreActivityFilter.setAttribute(
    "aria-expanded",
    String(enabled)
  );
}

function applyFilters({ fit = false } = {}) {
  updateMqttGatewaySummary();
  updateMeshcoreObserverSummary();
  updateMeshcoreActivitySummary();
  state.visibleNodes = state.nodes.filter(matchesFilters);
  state.visibleIds = new Set(
    state.visibleNodes.map((node) => node.id)
  );

  if (
    state.selectedNodeId !== null
    && !state.visibleIds.has(state.selectedNodeId)
  ) {
    state.selectedNodeId = null;
    clearSelectedNodePrecision();
    elements.detailPanel.hidden = true;
  }

  renderVisibleNodes();
  renderVisibleEdges();
  renderSearchResults();

  elements.filterEmptyPanel.hidden = (
    state.visibleNodes.length !== 0
  );

  if (fit) {
    fitVisibleNodes();
  }
}

function fitVisibleNodes() {
  if (state.visibleNodes.length === 0) {
    setRegionalView();
    return;
  }

  if (state.visibleNodes.length === 1) {
    const [node] = state.visibleNodes;

    state.map.setView(
      [node.latitude, node.longitude],
      15
    );
    return;
  }

  state.map.fitBounds(
    L.latLngBounds(
      state.visibleNodes.map(
        (node) => [node.latitude, node.longitude]
      )
    ),
    {
      padding: [30, 30],
      maxZoom: 12,
    }
  );
}

function renderSearchResults() {
  const query = normalizeText(elements.search.value);

  if (query.length < 2) {
    elements.searchResults.replaceChildren();
    elements.searchResults.hidden = true;
    elements.searchStatus.textContent = "";
    return;
  }

  const matches = state.visibleNodes
    .filter((node) => searchText(node).includes(query))
    .slice(0, 12);

  const items = matches.map((node) => {
    const item = document.createElement("li");
    const button = document.createElement("button");
    const title = document.createElement("strong");
    const subtitle = document.createElement("span");

    button.type = "button";
    title.textContent = nodeName(node);
    subtitle.textContent = [
      networkLabel(node.network),
      typeLabel(node),
      statusLabel(node),
    ].join(" · ");

    button.append(title, subtitle);

    button.addEventListener("click", () => {
      if (isMobileLayout()) {
        setMobilePanel(null);
      }

      focusNode(node);
      elements.searchResults.hidden = true;
    });

    item.append(button);

    return item;
  });

  if (items.length === 0) {
    const item = document.createElement("li");
    const message = document.createElement("span");

    message.textContent = "Non se atoparon nodos visibles.";
    message.style.display = "block";
    message.style.padding = "0.65rem";

    item.append(message);
    items.push(item);
  }

  elements.searchResults.replaceChildren(...items);
  elements.searchResults.hidden = false;
  elements.searchStatus.textContent = (
    matches.length === 0
      ? "Non se atoparon nodos visibles."
      : matches.length === 1
        ? "1 resultado dispoñible."
        : `${formatNumber(matches.length)} resultados dispoñibles.`
  );
}

function detailSection(title, rows) {
  const entries = rows.filter(
    ([, value]) => (
      value !== null
      && value !== undefined
      && value !== ""
    )
  );

  if (entries.length === 0) {
    return null;
  }

  const section = document.createElement("section");
  const heading = document.createElement("h3");
  const list = document.createElement("dl");

  section.className = "detail-section";
  heading.textContent = title;
  list.className = "detail-list";

  for (const [term, value] of entries) {
    const dt = document.createElement("dt");
    const dd = document.createElement("dd");

    dt.textContent = term;
    dd.textContent = String(value);

    list.append(dt, dd);
  }

  section.append(heading, list);

  return section;
}

function sourceLinkIsRecent(node, source) {
  const observed = Date.parse(
    node.source_last_seen?.[source] || ""
  );
  const reference = state.generatedAt?.getTime();
  const recentDays = Number(
    state.meta?.retention?.recent_days
  );

  if (
    !Number.isFinite(observed)
    || !Number.isFinite(reference)
    || !Number.isFinite(recentDays)
    || recentDays < 1
  ) {
    return true;
  }

  const ageMilliseconds = Math.max(
    0,
    reference - observed
  );

  return (
    ageMilliseconds
    <= recentDays * 24 * 60 * 60 * 1000
  );
}

function meshtasticNodeLinks(node) {
  if (
    node.network !== "meshtastic"
    || !Array.isArray(node.sources)
  ) {
    return [];
  }

  const idMatch = /^meshtastic:!([0-9a-f]{8})$/.exec(node.id);

  if (!idMatch) {
    return [];
  }

  const nodeNumber = String(Number.parseInt(idMatch[1], 16));
  const links = [];

  if (
    node.sources.includes("meshview_es")
    && sourceLinkIsRecent(node, "meshview_es")
  ) {
    links.push({
      label: "Abrir en Meshview España",
      url: "https://meshview.meshtastic.es/node/" + nodeNumber,
    });
  }

  if (
    node.sources.includes("malha_pt")
    && sourceLinkIsRecent(node, "malha_pt")
  ) {
    links.push({
      label: "Abrir en Malha Portugal",
      url: "https://malha.meshtastic.pt/node/" + nodeNumber,
    });
  }

  if (
    node.sources.includes("ozulo_map")
    && sourceLinkIsRecent(node, "ozulo_map")
  ) {
    links.push({
      label: "Abrir en Meshview de O Zulo",
      url: (
        "https://meshview.mesh.comunidadeozulo.org/node/"
        + nodeNumber
      ),
    });
  }

  return links;
}

function meshcoreNodeLinks(node) {
  if (
    node.network !== "meshcore"
    || !Array.isArray(node.sources)
  ) {
    return [];
  }

  const keyMatch = /^meshcore:([0-9a-f]{64})$/.exec(node.id);

  if (!keyMatch) {
    return [];
  }

  const publicKey = keyMatch[1];
  const links = [];

  if (
    node.sources.includes("meshcore_map")
    && sourceLinkIsRecent(node, "meshcore_map")
  ) {
    links.push({
      label: "Abrir en MeshCore Map",
      url: (
        "https://map.meshcore.io/?public_key="
        + encodeURIComponent(publicKey)
      ),
    });
  }

  if (
    node.sources.includes("meshcore_hub")
    && sourceLinkIsRecent(node, "meshcore_hub")
  ) {
    links.push({
      label: "Abrir no Hub de Mesh Galicia",
      url: (
        "https://hub.mesh.gal/nodes/"
        + encodeURIComponent(publicKey)
      ),
    });
  }

  return links;
}

function meshcoreContactUrl(node) {
  if (node.network !== "meshcore") {
    return null;
  }

  const contactType = MESHCORE_CONTACT_TYPES[node.node_type];
  const keyMatch = /^meshcore:([0-9a-f]{64})$/.exec(node.id);

  if (!contactType || !keyMatch) {
    return null;
  }

  const parameters = new URLSearchParams({
    name: nodeName(node),
    public_key: keyMatch[1],
    type: String(contactType),
  });

  return `meshcore://contact/add?${parameters.toString()}`;
}

async function copyText(text) {
  if (navigator.clipboard?.writeText) {
    await navigator.clipboard.writeText(text);
    return;
  }

  const input = document.createElement("textarea");

  input.value = text;
  input.setAttribute("readonly", "");
  input.style.position = "fixed";
  input.style.opacity = "0";

  document.body.append(input);
  input.select();

  const copied = document.execCommand("copy");

  input.remove();

  if (!copied) {
    throw new Error("Non se puido copiar o texto.");
  }
}

function externalNodeLinksSection(node) {
  const links = [
    ...meshtasticNodeLinks(node),
    ...meshcoreNodeLinks(node),
  ];

  if (links.length === 0) {
    return null;
  }

  const section = document.createElement("section");
  const heading = document.createElement("h3");
  const description = document.createElement("p");

  section.className = "detail-section";
  heading.textContent = "Fichas externas";

  description.className = "connection-summary";
  description.textContent = (
    "Consulta este nodo nos mapas públicos das fontes "
    + "que o recollen."
  );

  section.append(heading, description);

  for (const link of links) {
    const openButton = document.createElement("button");

    openButton.className = "secondary-button";
    openButton.type = "button";
    openButton.textContent = link.label;
    openButton.addEventListener("click", () => {
      window.location.href = link.url;
    });

    section.append(openButton);
  }

  return section;
}

function meshcoreAppSection(node) {
  const contactUrl = meshcoreContactUrl(node);

  if (contactUrl === null) {
    return null;
  }

  const section = document.createElement("section");
  const heading = document.createElement("h3");
  const description = document.createElement("p");
  const openButton = document.createElement("button");
  const copyButton = document.createElement("button");
  const status = document.createElement("p");

  section.className = "detail-section";
  heading.textContent = "Contacto MeshCore";

  description.className = "connection-summary";
  description.textContent = (
    "Engade este nodo como contacto na app de MeshCore."
  );

  openButton.className = "secondary-button";
  openButton.type = "button";
  openButton.textContent = "Abrir en MeshCore";
  openButton.addEventListener("click", () => {
    window.location.href = contactUrl;
  });

  copyButton.className = "secondary-button";
  copyButton.type = "button";
  copyButton.textContent = "Copiar ligazón";

  status.className = "location-status";
  status.setAttribute("role", "status");
  status.setAttribute("aria-live", "polite");

  copyButton.addEventListener("click", async () => {
    copyButton.disabled = true;
    status.classList.remove("success", "error");

    try {
      await copyText(contactUrl);
      status.textContent = "Ligazón copiada.";
      status.classList.add("success");
    } catch {
      status.textContent = "Non se puido copiar a ligazón.";
      status.classList.add("error");
    } finally {
      copyButton.disabled = false;
    }
  });

  section.append(
    heading,
    description,
    openButton,
    copyButton,
    status
  );

  return section;
}

function observerReceptionSummary(receptions) {
  const latestObservedAt = receptions.reduce(
    (latest, reception) => (
      latest === null
      || reception.observed_at > latest
        ? reception.observed_at
        : latest
    ),
    null
  );

  const snrValues = receptions
    .map((reception) => reception.snr_db)
    .filter(Number.isFinite);

  const pathLengths = receptions
    .map((reception) => reception.path_len)
    .filter(Number.isInteger);

  return {
    count: receptions.length,
    latestObservedAt,
    bestSnr: (
      snrValues.length > 0
        ? Math.max(...snrValues)
        : null
    ),
    shortestPath: (
      pathLengths.length > 0
        ? Math.min(...pathLengths)
        : null
    ),
  };
}

function observerReceptionDescription(summary) {
  const parts = [
    (
      summary.count === 1
        ? "1 recepción"
        : `${formatNumber(summary.count)} recepcións`
    ),
    `última ${formatDate(summary.latestObservedAt)}`,
  ];

  if (summary.bestSnr !== null) {
    parts.push(`mellor SNR ${summary.bestSnr} dB`);
  }

  if (summary.shortestPath !== null) {
    parts.push(`ruta mínima ${summary.shortestPath}`);
  }

  return parts.join(" · ");
}

function observerReceptionsSection(node) {
  if (node.network !== "meshcore") {
    return null;
  }

  const receptions = (
    state.receptionsByNodeId.get(node.id) || []
  );

  if (receptions.length === 0) {
    return null;
  }

  const receptionsByObserver = new Map();

  for (const reception of receptions) {
    const observerReceptions = (
      receptionsByObserver.get(reception.observer_id) || []
    );

    observerReceptions.push(reception);
    receptionsByObserver.set(
      reception.observer_id,
      observerReceptions
    );
  }

  const section = document.createElement("section");
  const heading = document.createElement("h3");
  const summary = document.createElement("p");
  const list = document.createElement("ul");

  section.className = (
    "detail-section observer-receptions-section"
  );
  heading.textContent = "Recepcións dos observers";
  summary.className = "observer-receptions-summary";
  summary.textContent = [
    (
      receptions.length === 1
        ? "1 recepción publicada"
        : `${formatNumber(receptions.length)} recepcións publicadas`
    ),
    (
      receptionsByObserver.size === 1
        ? "1 observer"
        : `${formatNumber(receptionsByObserver.size)} observers`
    ),
  ].join(" · ");
  list.className = "observer-reception-list";

  const observers = Array.from(
    receptionsByObserver.entries()
  ).map(([observerId, observerReceptions]) => {
    const observer = state.nodeById.get(observerId) || null;

    return {
      observer,
      name: (
        observer
          ? nodeName(observer)
          : observerId.replace(/^meshcore:/, "")
      ),
      summary: observerReceptionSummary(
        observerReceptions
      ),
    };
  }).sort((first, second) => (
    second.summary.latestObservedAt.localeCompare(
      first.summary.latestObservedAt
    )
    || first.name.localeCompare(
      second.name,
      "gl-ES"
    )
  ));

  for (const entry of observers) {
    const item = document.createElement("li");
    const observerName = entry.observer
      ? document.createElement("button")
      : document.createElement("span");
    const description = document.createElement("span");

    item.className = "observer-reception-item";
    observerName.className = entry.observer
      ? "observer-reception-link"
      : "observer-reception-name";
    observerName.textContent = entry.name;

    if (entry.observer) {
      observerName.type = "button";
      observerName.addEventListener("click", () => {
        focusNode(entry.observer);
      });
    }

    description.className = "observer-reception-meta";
    description.textContent = observerReceptionDescription(
      entry.summary
    );

    item.append(observerName, description);
    list.append(item);
  }

  section.append(heading, summary, list);
  return section;
}

function observedNodesSection(node) {
  if (
    node.network !== "meshcore"
    || node.is_observer !== true
  ) {
    return null;
  }

  const receptions = (
    state.receptionsByObserverId.get(node.id) || []
  );

  if (receptions.length === 0) {
    return null;
  }

  const receptionsByNode = new Map();

  for (const reception of receptions) {
    const nodeReceptions = (
      receptionsByNode.get(reception.node_id) || []
    );

    nodeReceptions.push(reception);
    receptionsByNode.set(
      reception.node_id,
      nodeReceptions
    );
  }

  const entries = Array.from(
    receptionsByNode.entries()
  ).map(([observedNodeId, nodeReceptions]) => {
    const observedNode = (
      state.nodeById.get(observedNodeId) || null
    );

    return {
      node: observedNode,
      id: observedNodeId,
      name: observedNode
        ? nodeName(observedNode)
        : observedNodeId.replace(/^meshcore:/, ""),
      summary: observerReceptionSummary(nodeReceptions),
    };
  }).sort((first, second) => (
    second.summary.latestObservedAt.localeCompare(
      first.summary.latestObservedAt
    )
    || first.name.localeCompare(
      second.name,
      "gl-ES"
    )
  ));

  const knownCount = entries.filter(
    (entry) => entry.node !== null
  ).length;
  const positionedCount = entries.filter(
    (entry) => (
      entry.node !== null
      && Number.isFinite(entry.node.latitude)
      && Number.isFinite(entry.node.longitude)
    )
  ).length;

  const section = document.createElement("section");
  const heading = document.createElement("h3");
  const summary = document.createElement("p");
  const details = document.createElement("details");
  const detailsSummary = document.createElement("summary");
  const list = document.createElement("ul");

  section.className = (
    "detail-section observer-heard-nodes-section"
  );
  heading.textContent = "Nodos escoitados";

  summary.className = "observer-receptions-summary";
  summary.textContent = [
    `${formatNumber(entries.length)} nodos distintos`,
    `${formatNumber(knownCount)} coñecidos no mapa`,
    `${formatNumber(positionedCount)} con posición`,
    (
      receptions.length === 1
        ? "1 recepción"
        : `${formatNumber(receptions.length)} recepcións`
    ),
  ].join(" · ");

  details.className = "observer-heard-nodes-details";
  detailsSummary.textContent = "Ver nodos escoitados";
  list.className = "observer-reception-list";

  for (const entry of entries) {
    const item = document.createElement("li");
    const nodeNameElement = entry.node
      ? document.createElement("button")
      : document.createElement("span");
    const description = document.createElement("span");

    item.className = "observer-reception-item";
    nodeNameElement.className = entry.node
      ? "observer-reception-link"
      : "observer-reception-name";
    nodeNameElement.textContent = entry.name;

    if (entry.node) {
      nodeNameElement.type = "button";
      nodeNameElement.addEventListener("click", () => {
        focusNode(entry.node);
      });
    }

    description.className = "observer-reception-meta";
    description.textContent = observerReceptionDescription(
      entry.summary
    );

    item.append(nodeNameElement, description);
    list.append(item);
  }

  details.append(detailsSummary, list);
  section.append(heading, summary, details);

  return section;
}

function configurationWarningsSection(node) {
  if (node.network !== "meshtastic") {
    return null;
  }

  const warningDocument = state.configurationWarnings;
  const analysis = warningDocument?.analysis;

  if (!analysis?.available) {
    return detailSection(
      "Configuración",
      [
        [
          "Análise",
          "Non dispoñible neste momento.",
        ],
      ]
    );
  }

  if (!node.sources.includes("meshview_es")) {
    return detailSection(
      "Configuración",
      [
        [
          "Cobertura",
          "Análise non dispoñible para este nodo. "
          + "As demais fontes non publican todos os "
          + "parámetros de configuración necesarios.",
        ],
      ]
    );
  }

  const analyzed = state.warningByNodeId.get(node.id);

  if (!analyzed) {
    return detailSection(
      "Configuración",
      [
        [
          "Análise",
          "Sen datos de análise para este nodo.",
        ],
        [
          "Actualización",
          formatDate(analysis.updated_at),
        ],
      ]
    );
  }

  const section = document.createElement("section");
  const heading = document.createElement("h3");
  const status = document.createElement("p");

  section.className = (
    "detail-section configuration-warnings"
  );
  heading.textContent = "Configuración";

  if (analyzed.warnings.length === 0) {
    status.textContent = (
      "Non se detectaron avisos na análise dispoñible. "
      + "Isto non equivale a unha validación completa."
    );

    section.append(heading, status);
  } else {
    const list = document.createElement("ul");

    status.textContent = (
      "Avisos automáticos detectados. "
      + "Non constitúen unha validación completa."
    );
    list.className = "configuration-warning-list";

    for (const warning of analyzed.warnings) {
      const item = document.createElement("li");
      const label = (
        WARNING_LABELS[warning.key]
        || warning.key
      );
      const severity = (
        WARNING_SEVERITY_LABELS[warning.severity]
        || warning.severity
      );

      item.textContent = (
        `${label} · gravidade ${severity}`
      );
      item.dataset.severity = warning.severity;
      list.append(item);
    }

    section.append(heading, status, list);
  }

  const updated = document.createElement("p");

  updated.className = "configuration-warning-date";
  updated.textContent = (
    `Análise actualizada ${formatDate(
      analysis.updated_at
    )}.`
  );
  section.append(updated);

  return section;
}

function setDetailExpanded(expanded) {
  const active = Boolean(expanded && isMobileLayout());

  elements.detailPanel.classList.toggle(
    "detail-expanded",
    active
  );
  elements.detailSizeToggle.setAttribute(
    "aria-expanded",
    String(active)
  );
  elements.detailSizeToggle.textContent = (
    active ? "Reducir" : "Ampliar"
  );
}

function rememberDetailTrigger() {
  if (!elements.detailPanel.hidden) {
    return;
  }

  const activeElement = document.activeElement;

  if (
    !(activeElement instanceof HTMLElement)
    || activeElement === document.body
    || activeElement === document.documentElement
  ) {
    lastDetailTrigger = null;
    return;
  }

  lastDetailTrigger = (
    elements.searchResults.contains(activeElement)
      ? (
        isMobileLayout()
          ? lastMobileTrigger
          : elements.search
      )
      : activeElement
  );
}

function restoreDetailTrigger() {
  const trigger = lastDetailTrigger;

  lastDetailTrigger = null;

  if (
    trigger
    && trigger.isConnected
    && !trigger.closest("[hidden]")
  ) {
    trigger.focus({
      preventScroll: true,
    });
  }
}

function keepNodeVisibleAboveDetail(node) {
  if (!isMobileLayout()) {
    return;
  }

  window.requestAnimationFrame(() => {
    const mapRect = (
      state.map.getContainer().getBoundingClientRect()
    );
    const detailRect = (
      elements.detailPanel.getBoundingClientRect()
    );
    const point = state.map.latLngToContainerPoint(
      [node.latitude, node.longitude]
    );
    const freeBottom = detailRect.top - mapRect.top - 20;
    const targetY = Math.max(72, freeBottom * 0.45);
    const offsetY = Math.max(0, point.y - targetY);

    if (offsetY > 0) {
      state.map.panBy(
        [0, Math.round(offsetY)],
        {
          animate: false,
        }
      );
    }
  });
}

function closeNodeDetail() {
  const previousNodeId = state.selectedNodeId;

  state.selectedNodeId = null;
  clearSelectedNodePrecision();
  setDetailExpanded(false);
  elements.detailPanel.hidden = true;
  syncModalAccessibility();

  refreshNodeMarker(previousNodeId);
  renderVisibleEdges();
  scheduleNodeLabels();
  restoreDetailTrigger();
}

function showNodeDetail(node) {
  rememberDetailTrigger();

  const previousNodeId = state.selectedNodeId;

  state.selectedNodeId = node.id;
  renderSelectedNodePrecision(node);
  setDetailExpanded(false);

  refreshNodeMarker(previousNodeId);
  refreshNodeMarker(node.id);
  renderVisibleEdges();
  scheduleNodeLabels();

  elements.detailNetwork.textContent = [
    networkLabel(node.network),
    typeLabel(node),
  ].join(" · ");

  elements.detailTitle.textContent = nodeName(node);

  const sections = [
    detailSection(
      "Identidade",
      [
        ["Identificador", node.id],
        ["Nome curto", node.short_name],
        ["Nome longo", node.long_name],
        ["Hardware", node.hardware],
        [
          node.network === "meshtastic" ? "Rol" : "Tipo",
          typeLabel(node),
        ],
        [
          "Función no Hub",
          (
            node.network === "meshcore"
            && node.is_observer === true
          )
            ? "Observer"
            : null,
        ],
        ["Estado", statusLabel(node)],
      ]
    ),
    externalNodeLinksSection(node),
    meshcoreAppSection(node),
    detailSection(
      "Actividade",
      [
        ["Última observación", formatDate(node.last_seen)],
        ["Primeira observación", formatDate(node.first_seen)],
        [
          "Posición actualizada",
          formatDate(node.position_updated_at),
        ],
      ]
    ),
    detailSection(
      "Posición",
      [
        ["Latitude", formatCoordinate(node.latitude)],
        ["Lonxitude", formatCoordinate(node.longitude)],
        [
          "Altitude",
          formatMetric(node.altitude_m, " m"),
        ],
      ]
    ),
    detailSection(
      "Radio",
      [
        [
          "Frecuencia",
          formatMetric(node.radio.frequency_mhz, " MHz"),
        ],
        [
          "Largura de banda",
          formatMetric(node.radio.bandwidth_khz, " kHz"),
        ],
        [
          "Spreading factor",
          formatMetric(node.radio.spreading_factor),
        ],
        [
          "Coding rate",
          formatMetric(node.radio.coding_rate),
        ],
        ["Canle", node.radio.channel],
        ["Firmware", node.radio.firmware],
        ["Saltos", formatMetric(node.radio.hops_away)],
        ["Gateway MQTT", node.radio.mqtt_gateway],
      ]
    ),
    detailSection(
      "Métricas",
      [
        [
          "Batería",
          formatMetric(node.metrics.battery_percent, " %"),
        ],
        [
          "Voltaxe",
          formatMetric(node.metrics.voltage_v, " V"),
        ],
        [
          "SNR",
          formatMetric(node.metrics.snr_db, " dB"),
        ],
        [
          "RSSI",
          formatMetric(node.metrics.rssi_dbm, " dBm"),
        ],
        [
          "Uso de canle",
          formatMetric(
            node.metrics.channel_utilization_percent,
            " %"
          ),
        ],
        [
          "Emisión no aire",
          formatMetric(
            node.metrics.air_util_tx_percent,
            " %"
          ),
        ],
      ]
    ),
    createConnectionsSection(node),
    observerReceptionsSection(node),
    observedNodesSection(node),
    configurationWarningsSection(node),
    detailSection(
      "Fontes",
      [
        [
          "Procedencia",
          node.sources
            .map(
              (source) => SOURCE_LABELS[source] || source
            )
            .join(", "),
        ],
        ...Object.entries(node.source_ids).map(
          ([source, sourceId]) => [
            SOURCE_LABELS[source] || source,
            sourceId,
          ]
        ),
      ]
    ),
  ].filter(Boolean);

  elements.detailContent.replaceChildren(...sections);
  elements.detailPanel.hidden = false;
  syncModalAccessibility();
  keepNodeVisibleAboveDetail(node);
  elements.detailClose.focus();
}

function renderSourceStatus() {
  const fragment = document.createDocumentFragment();

  for (const source of [
    "meshview_es",
    "malha_pt",
    "ozulo_map",
    "meshcore_map",
    "meshcore_hub",
  ]) {
    const sourceData = state.stats.sources[source];
    const dt = document.createElement("dt");
    const dd = document.createElement("dd");

    dt.textContent = SOURCE_LABELS[source];
    dd.textContent = sourceData.last_success
      ? formatDate(sourceData.last_success)
      : "Sen actualización correcta";

    fragment.append(dt, dd);
  }

  elements.sourceStatus.replaceChildren(fragment);
}

async function fetchJson(url) {
  const response = await fetch(url, {
    cache: "no-store",
    headers: {
      Accept: "application/json",
    },
  });

  if (!response.ok) {
    throw new Error(
      `${url}: resposta HTTP ${response.status}`
    );
  }

  return response.json();
}

function validateManifest(manifest) {
  if (
    !manifest
    || manifest.schema !== PUBLIC_MANIFEST_SCHEMA
  ) {
    throw new Error(
      "manifest.json usa un contrato descoñecido."
    );
  }

  if (
    typeof manifest.generation !== "string"
    || !manifest.generation
    || typeof manifest.generated_at !== "string"
    || !manifest.generated_at
    || !manifest.documents
  ) {
    throw new Error(
      "manifest.json non describe unha xeración válida."
    );
  }

  for (
    const filename
    of Object.values(DATA_DOCUMENT_NAMES)
  ) {
    const expectedPath = (
      `generations/${manifest.generation}/${filename}`
    );

    if (manifest.documents[filename] !== expectedPath) {
      throw new Error(
        `manifest.json non referencia correctamente ${filename}.`
      );
    }
  }
}

function validateDocuments(documents, manifest) {
  for (
    const [key, filename]
    of Object.entries(DATA_DOCUMENT_NAMES)
  ) {
    const document = documents[key];
    const expectedSchema = DATA_DOCUMENT_SCHEMAS[key];

    if (
      !document
      || document.schema !== expectedSchema
    ) {
      throw new Error(
        `${filename} usa un contrato descoñecido.`
      );
    }

    if (
      document.generated_at
      !== manifest.generated_at
    ) {
      throw new Error(
        `${filename} non pertence á xeración publicada.`
      );
    }
  }

  if (!Array.isArray(documents.nodes.nodes)) {
    throw new Error(
      "nodes.json non contén unha lista de nodos."
    );
  }

  if (!Array.isArray(documents.edges.edges)) {
    throw new Error(
      "edges.json non contén unha lista de conexións."
    );
  }

  if (
    !Array.isArray(
      documents.neighborInfo.observations
    )
  ) {
    throw new Error(
      "neighbor-info.json non contén unha lista "
      + "de observacións."
    );
  }

  if (
    !Array.isArray(
      documents.observerReceptions.receptions
    )
  ) {
    throw new Error(
      "observer-receptions.json non contén unha lista "
      + "de recepcións."
    );
  }

  if (
    !documents.stats.totals
    || !documents.stats.sources
  ) {
    throw new Error(
      "stats.json non contén o resumo esperado."
    );
  }

  if (!documents.meta.region?.bounds) {
    throw new Error(
      "meta.json non contén os límites rexionais."
    );
  }

  if (
    !documents.configurationWarnings.analysis
    || !Array.isArray(
      documents.configurationWarnings.nodes
    )
  ) {
    throw new Error(
      "configuration-warnings.json non contén "
      + "a análise esperada."
    );
  }
}

function countSummary(
  selected,
  total,
  allLabel,
  noneLabel
) {
  if (selected === total) {
    return allLabel;
  }

  if (selected === 0) {
    return noneLabel;
  }

  return `${selected} de ${total}`;
}

function updateFilterSummaries() {
  const ageInputs = Array.from(
    document.querySelectorAll('input[name="age"]')
  );

  const categoryButtons = Array.from(
    document.querySelectorAll(".legend-filter")
  );

  const selectedAgeCount = ageInputs.filter(
    (input) => input.checked
  ).length;

  const selectedCategoryCount = categoryButtons.filter(
    (button) => (
      button.getAttribute("aria-pressed") === "true"
    )
  ).length;

  elements.ageSummary.textContent = countSummary(
    selectedAgeCount,
    ageInputs.length,
    "Todas",
    "Ningunha"
  );

  elements.typeSummary.textContent = countSummary(
    selectedCategoryCount,
    categoryButtons.length,
    "Todos",
    "Ningún"
  );

  elements.typeFilterReset.disabled = (
    selectedCategoryCount === categoryButtons.length
  );
}

function storedControlsCollapsed() {
  try {
    const value = window.sessionStorage.getItem(
      SIDEBAR_STORAGE_KEY
    );

    if (value === null) {
      return null;
    }

    return value === "true";
  } catch (_error) {
    return null;
  }
}

function storeControlsCollapsed(collapsed) {
  try {
    window.sessionStorage.setItem(
      SIDEBAR_STORAGE_KEY,
      String(collapsed)
    );
  } catch (_error) {
    // O mapa continúa funcionando sen almacenamento.
  }
}

function refreshMapSize() {
  const invalidate = () => {
    state.map?.invalidateSize({
      pan: false,
      debounceMoveend: true,
    });
  };

  window.requestAnimationFrame(invalidate);
  window.setTimeout(invalidate, 220);
}

function setControlsCollapsed(
  collapsed,
  { persist = true } = {}
) {
  const label = (
    collapsed
      ? "Mostrar controis"
      : "Ocultar controis"
  );

  elements.appShell.classList.toggle(
    "controls-collapsed",
    collapsed
  );

  elements.sidebarControls.hidden = collapsed;
  elements.desktopCollapsedNav.hidden = (
    !collapsed || isMobileLayout()
  );

  elements.sidebarToggle.setAttribute(
    "aria-expanded",
    String(!collapsed)
  );

  elements.sidebarToggle.setAttribute(
    "aria-label",
    label
  );

  elements.sidebarToggle.title = label;
  elements.sidebarToggleLabel.textContent = label;

  if (persist) {
    storeControlsCollapsed(collapsed);
  }

  refreshMapSize();
}

function openDesktopControlPanel(target) {
  if (
    isMobileLayout()
    || !DESKTOP_PANEL_TARGETS[target]
  ) {
    return;
  }

  if (target === "filters") {
    openMobileFilterSections();
  }

  const block = document.querySelector(
    DESKTOP_PANEL_TARGETS[target]
  );

  setControlsCollapsed(false);

  window.setTimeout(() => {
    if (!block) {
      elements.sidebarToggle.focus({
        preventScroll: true,
      });
      return;
    }

    const sidebarBox = (
      elements.sidebar.getBoundingClientRect()
    );
    const blockBox = block.getBoundingClientRect();
    const targetTop = (
      elements.sidebar.scrollTop
      + blockBox.top
      - sidebarBox.top
      - 12
    );

    elements.sidebar.scrollTo({
      top: Math.max(0, targetTop),
      behavior: "auto",
    });

    const focusTarget = block.querySelector(
      [
        "summary",
        "input:not([disabled])",
        "button:not([disabled])",
        "a[href]",
        "h2",
        "h3",
      ].join(", ")
    ) || block;

    if (!focusTarget.matches(
      "input, button, summary, a[href]"
    )) {
      focusTarget.setAttribute("tabindex", "-1");
    }

    focusTarget.focus({
      preventScroll: true,
    });
  }, 220);
}

function isMobileLayout() {
  return window.matchMedia(MOBILE_BREAKPOINT).matches;
}

function syncMobileDataStatus() {
  elements.mobileDataStatus.textContent = (
    elements.dataStatus.textContent
  );
}

function initializeMobileDataStatus() {
  syncMobileDataStatus();

  state.dataStatusObserver = new MutationObserver(
    syncMobileDataStatus
  );

  state.dataStatusObserver.observe(
    elements.dataStatus,
    {
      childList: true,
      subtree: true,
      characterData: true,
    }
  );
}

function arrangeResponsiveFilterSections() {
  if (isMobileLayout()) {
    elements.ageDetailsHome.after(
      elements.legendDetails
    );
    elements.legendDetails.after(
      elements.ageDetails
    );
    elements.ageDetails.after(
      elements.legendInformation
    );
    return;
  }

  elements.ageDetailsHome.after(elements.ageDetails);
  elements.legendDetailsHome.after(
    elements.legendDetails
  );
  elements.legendInformationHome.after(
    elements.legendInformation
  );
}

function openMobileFilterSections() {
  elements.ageDetails.open = true;
  elements.legendDetails.open = true;
}

function setDialogState(
  element,
  active,
  labelledBy,
) {
  if (active) {
    element.setAttribute("role", "dialog");
    element.setAttribute("aria-modal", "true");
    element.setAttribute("aria-labelledby", labelledBy);
    return;
  }

  element.removeAttribute("role");
  element.removeAttribute("aria-modal");
  element.removeAttribute("aria-labelledby");
}

function syncModalAccessibility() {
  const sheetOpen = (
    isMobileLayout()
    && Boolean(activeMobilePanel)
  );

  elements.mapContainer.inert = sheetOpen;
  elements.detailPanel.inert = sheetOpen;
  elements.privacyNotice.inert = sheetOpen;

  for (const element of [
    elements.filterEmptyPanel,
    elements.loadingPanel,
    elements.errorPanel,
  ]) {
    element.inert = sheetOpen;
  }

  setDialogState(
    elements.sidebar,
    sheetOpen,
    "mobile-sheet-title",
  );
}

function focusableElements(container) {
  return Array.from(
    container.querySelectorAll(FOCUSABLE_SELECTOR)
  ).filter(
    (element) => (
      !element.closest("[hidden]")
      && !element.closest("[inert]")
      && element.getClientRects().length > 0
    )
  );
}

function trapKeyboardFocus(event, container) {
  if (event.key !== "Tab") {
    return;
  }

  const focusable = focusableElements(container);

  if (!focusable.length) {
    event.preventDefault();
    return;
  }

  const first = focusable[0];
  const last = focusable[focusable.length - 1];
  const active = document.activeElement;
  const outside = !container.contains(active);

  if (
    event.shiftKey
    && (active === first || outside)
  ) {
    event.preventDefault();
    last.focus();
    return;
  }

  if (
    !event.shiftKey
    && (active === last || outside)
  ) {
    event.preventDefault();
    first.focus();
  }
}

function setMobilePanel(
  panel,
  {
    restoreFocus = false,
  } = {}
) {
  const validPanel = (
    panel && MOBILE_PANEL_TITLES[panel]
      ? panel
      : null
  );

  activeMobilePanel = (
    isMobileLayout()
      ? validPanel
      : null
  );

  const open = Boolean(activeMobilePanel);

  if (activeMobilePanel === "filters") {
    openMobileFilterSections();
  }

  elements.appShell.classList.toggle(
    "mobile-sheet-open",
    open
  );

  elements.sidebar.dataset.mobilePanel = (
    activeMobilePanel || ""
  );

  for (const block of elements.mobilePanelBlocks) {
    block.hidden = (
      isMobileLayout()
      && block.dataset.mobilePanel !== activeMobilePanel
    );
  }

  for (const button of elements.mobileTabs) {
    const active = (
      button.dataset.mobileTarget === activeMobilePanel
    );

    button.setAttribute("aria-pressed", String(active));
    button.setAttribute("aria-expanded", String(active));
  }

  elements.mobileBackdrop.hidden = !open;

  elements.mobileSheetTitle.textContent = (
    open
      ? MOBILE_PANEL_TITLES[activeMobilePanel]
      : "Controis"
  );

  syncModalAccessibility();

  if (open) {
    elements.sidebarControls.hidden = false;

    window.requestAnimationFrame(() => {
      if (activeMobilePanel === "filters") {
        elements.sidebar.scrollTop = 0;
      }

      elements.mobileSheetClose.focus({
        preventScroll: true,
      });
    });
  } else if (restoreFocus && lastMobileTrigger) {
    lastMobileTrigger.focus({
      preventScroll: true,
    });
  }

  refreshMapSize();
}

function synchronizeResponsiveNavigation() {
  arrangeResponsiveFilterSections();

  if (isMobileLayout()) {
    setControlsCollapsed(
      false,
      {
        persist: false,
      }
    );

    setMobilePanel(null);
    return;
  }

  setMobilePanel(null);

  for (const block of elements.mobilePanelBlocks) {
    block.hidden = false;
  }

  const stored = storedControlsCollapsed();

  setControlsCollapsed(
    stored ?? false,
    {
      persist: false,
    }
  );
}

function initializeResponsiveNavigation() {
  const query = window.matchMedia(MOBILE_BREAKPOINT);

  synchronizeResponsiveNavigation();
  initializeMobileDataStatus();

  query.addEventListener(
    "change",
    synchronizeResponsiveNavigation
  );
}

function storedDetailsState(details) {
  try {
    const value = window.sessionStorage.getItem(
      `${DETAILS_STORAGE_PREFIX}${details.id}`
    );

    if (value === null) {
      return null;
    }

    return value === "true";
  } catch (_error) {
    return null;
  }
}

function storeDetailsState(details) {
  try {
    window.sessionStorage.setItem(
      `${DETAILS_STORAGE_PREFIX}${details.id}`,
      String(details.open)
    );
  } catch (_error) {
    // O mapa continúa funcionando sen almacenamento.
  }
}

function initializeResponsiveDetails() {
  const mobile = window.matchMedia(
    "(max-width: 780px)"
  ).matches;

  const settings = [
    [elements.ageDetails, !mobile],
    [elements.legendDetails, !mobile],
    [elements.sourceDetails, false],
  ];

  for (const [details, defaultOpen] of settings) {
    const stored = storedDetailsState(details);

    details.open = stored ?? defaultOpen;

    details.addEventListener(
      "toggle",
      () => storeDetailsState(details)
    );
  }
}

function privacyNoticeDismissed() {
  try {
    return window.localStorage.getItem(
      PRIVACY_STORAGE_KEY
    ) === "1";
  } catch (_error) {
    return false;
  }
}

function dismissPrivacyNotice() {
  elements.privacyNotice.hidden = true;

  try {
    window.localStorage.setItem(
      PRIVACY_STORAGE_KEY,
      "1"
    );
  } catch (_error) {
    // O aviso pode pecharse aínda que non se poida lembrar.
  }
}

function initializePrivacyNotice() {
  if (!privacyNoticeDismissed()) {
    elements.privacyNotice.hidden = false;
  }

  elements.privacyDismiss.addEventListener(
    "click",
    dismissPrivacyNotice
  );
}

function bindControls() {
  initializePrivacyNotice();
  initializeResponsiveNavigation();
  initializeResponsiveDetails();
  updateFilterSummaries();
  updateTracerouteControlsVisibility();

  elements.sidebarToggle.addEventListener(
    "click",
    () => {
      if (isMobileLayout()) {
        return;
      }

      const collapsed = elements.appShell.classList.contains(
        "controls-collapsed"
      );

      setControlsCollapsed(!collapsed);
    }
  );

  for (const button of elements.desktopRailButtons) {
    button.addEventListener(
      "click",
      () => openDesktopControlPanel(
        button.dataset.desktopTarget
      )
    );
  }

  for (const button of elements.mobileTabs) {
    button.addEventListener(
      "click",
      () => {
        const target = button.dataset.mobileTarget;

        if (activeMobilePanel === target) {
          setMobilePanel(
            null,
            {
              restoreFocus: true,
            }
          );
          return;
        }

        lastMobileTrigger = button;
        setMobilePanel(target);
      }
    );
  }

  elements.mobileSheetClose.addEventListener(
    "click",
    () => {
      setMobilePanel(
        null,
        {
          restoreFocus: true,
        }
      );
    }
  );

  elements.mobileBackdrop.addEventListener(
    "click",
    () => {
      setMobilePanel(
        null,
        {
          restoreFocus: true,
        }
      );
    }
  );

  document.addEventListener(
    "keydown",
    (event) => {
      if (
        event.key === "Tab"
        && activeMobilePanel
      ) {
        trapKeyboardFocus(event, elements.sidebar);
        return;
      }

      if (
        event.key === "Escape"
        && activeMobilePanel
      ) {
        setMobilePanel(
          null,
          {
            restoreFocus: true,
          }
        );
      }
    }
  );

  document
    .querySelectorAll('input[name="network"]')
    .forEach((input) => {
      input.addEventListener("change", () => {
        applyFilters();
      });
    });

  document
    .querySelectorAll('input[name="age"]')
    .forEach((input) => {
      input.addEventListener("change", () => {
        updateFilterSummaries();
        applyFilters();
      });
    });

  document
    .querySelectorAll(".legend-filter")
    .forEach((button) => {
      button.addEventListener("click", () => {
        const enabled = (
          button.getAttribute("aria-pressed") === "true"
        );

        button.setAttribute(
          "aria-pressed",
          String(!enabled)
        );

        updateFilterSummaries();
        applyFilters();
      });
    });

  elements.typeFilterReset.addEventListener(
    "click",
    () => {
      document
        .querySelectorAll(".legend-filter")
        .forEach((button) => {
          button.setAttribute("aria-pressed", "true");
        });

      updateFilterSummaries();
      applyFilters();
    }
  );

  elements.mqttGatewayFilter.addEventListener(
    "click",
    () => {
      const enabled = (
        elements.mqttGatewayFilter.getAttribute(
          "aria-pressed"
        ) === "true"
      );

      elements.mqttGatewayFilter.setAttribute(
        "aria-pressed",
        String(!enabled)
      );

      applyFilters();
    }
  );

  elements.meshcoreObserverFilter.addEventListener(
    "click",
    () => {
      const enabled = meshcoreObserverFilterEnabled();

      elements.meshcoreObserverFilter.setAttribute(
        "aria-pressed",
        String(!enabled)
      );

      applyFilters();
    }
  );

  elements.meshcoreActivityFilter.addEventListener(
    "click",
    () => {
      const enabled = meshcoreActivityEnabled();

      elements.meshcoreActivityFilter.setAttribute(
        "aria-pressed",
        String(!enabled)
      );

      updateMeshcoreActivityControls();
      applyFilters();
    }
  );

  elements.meshcoreActivityWindow.addEventListener(
    "change",
    () => applyFilters()
  );

  for (const input of elements.basemapInputs) {
    input.addEventListener(
      "change",
      () => {
        if (input.checked) {
          setBaseMap(input.value);
        }
      }
    );
  }

  elements.traceroutes.addEventListener(
    "change",
    () => {
      updateTracerouteControlsVisibility();
      applyFilters();
    }
  );

  elements.tracerouteSource.addEventListener(
    "change",
    () => applyFilters()
  );

  elements.tracerouteAge.addEventListener(
    "change",
    () => applyFilters()
  );

  elements.meshcoreCompleteRoutes.addEventListener(
    "change",
    () => applyFilters()
  );

  elements.meshcoreFragmentedRoutes.addEventListener(
    "change",
    () => applyFilters()
  );

  elements.meshcoreNeighbors.addEventListener(
    "change",
    () => applyFilters()
  );

  elements.neighbors.addEventListener(
    "change",
    () => applyFilters()
  );

  elements.neighborInfo.addEventListener(
    "change",
    () => applyFilters()
  );

  elements.fitMap.addEventListener(
    "click",
    fitVisibleNodes
  );

  elements.locateMe.addEventListener(
    "click",
    locateUser
  );

  if (!window.isSecureContext) {
    elements.locateMe.disabled = true;

    setLocationStatus(
      "A localización estará dispoñible ao publicar o mapa con HTTPS."
    );
  } else if (!navigator.geolocation) {
    elements.locateMe.disabled = true;

    setLocationStatus(
      "Este navegador non ofrece xeolocalización."
    );
  }

  elements.search.addEventListener(
    "input",
    renderSearchResults
  );

  elements.search.addEventListener(
    "keydown",
    (event) => {
      if (event.key === "Escape") {
        elements.search.value = "";
        renderSearchResults();
      }
    }
  );

  elements.detailSizeToggle.addEventListener(
    "click",
    () => {
      setDetailExpanded(
        !elements.detailPanel.classList.contains(
          "detail-expanded"
        )
      );
    }
  );

  elements.detailClose.addEventListener(
    "click",
    closeNodeDetail
  );

  document.addEventListener(
    "keydown",
    (event) => {
      if (
        event.key === "Escape"
        && !elements.detailPanel.hidden
      ) {
        closeNodeDetail();
      }
    }
  );
}

async function initialize() {
  try {
    createMap();
    bindControls();

    const manifestUrl = new URL(
      DATA_MANIFEST,
      window.location.href
    );
    const manifest = await fetchJson(manifestUrl);

    validateManifest(manifest);

    const documentUrl = (filename) => new URL(
      manifest.documents[filename],
      manifestUrl
    );

    const [
      nodes,
      edges,
      neighborInfo,
      observerReceptions,
      stats,
      meta,
      configurationWarnings,
    ] = await Promise.all([
      fetchJson(
        documentUrl(DATA_DOCUMENT_NAMES.nodes)
      ),
      fetchJson(
        documentUrl(DATA_DOCUMENT_NAMES.edges)
      ),
      fetchJson(
        documentUrl(DATA_DOCUMENT_NAMES.neighborInfo)
      ),
      fetchJson(
        documentUrl(
          DATA_DOCUMENT_NAMES.observerReceptions
        )
      ),
      fetchJson(
        documentUrl(DATA_DOCUMENT_NAMES.stats)
      ),
      fetchJson(
        documentUrl(DATA_DOCUMENT_NAMES.meta)
      ),
      fetchJson(
        documentUrl(
          DATA_DOCUMENT_NAMES.configurationWarnings
        )
      ),
    ]);

    const documents = {
      nodes,
      edges,
      neighborInfo,
      observerReceptions,
      stats,
      meta,
      configurationWarnings,
    };

    validateDocuments(documents, manifest);

    const generatedAt = new Date(nodes.generated_at);

    if (Number.isNaN(generatedAt.getTime())) {
      throw new Error(
        "nodes.json non contén unha data de xeración válida."
      );
    }

    state.generatedAt = generatedAt;
    state.nodes = nodes.nodes;
    state.edges = edges.edges;
    state.neighborInfo = neighborInfo.observations;
    state.observerReceptions = (
      observerReceptions.receptions
    );
    state.receptionsByNodeId = new Map();
    state.receptionsByObserverId = new Map();
    state.meshcoreActivityByNodeId = new Map();

    for (
      const reception
      of state.observerReceptions
    ) {
      const receptions = (
        state.receptionsByNodeId.get(
          reception.node_id
        ) || []
      );

      receptions.push(reception);

      state.receptionsByNodeId.set(
        reception.node_id,
        receptions
      );

      const observerReceptions = (
        state.receptionsByObserverId.get(
          reception.observer_id
        ) || []
      );

      observerReceptions.push(reception);

      state.receptionsByObserverId.set(
        reception.observer_id,
        observerReceptions
      );

      const current = state.meshcoreActivityByNodeId.get(
        reception.node_id
      );
      const observed = Date.parse(reception.observed_at || "");
      const currentObserved = Date.parse(
        current?.latestObservedAt || ""
      );

      if (
        Number.isFinite(observed)
        && (
          !current
          || !Number.isFinite(currentObserved)
          || observed > currentObserved
        )
      ) {
        state.meshcoreActivityByNodeId.set(
          reception.node_id,
          {
            latestObservedAt: reception.observed_at,
          }
        );
      }
    }

    state.stats = stats;
    state.meta = meta;
    state.configurationWarnings = configurationWarnings;
    state.warningByNodeId = new Map(
      configurationWarnings.nodes.map(
        (node) => [node.id, node]
      )
    );
    state.nodeById = new Map(
      state.nodes.map((node) => [node.id, node])
    );

    renderSourceStatus();
    updateMeshcoreActivityControls();
    setRegionalView();
    applyFilters();

    elements.dataStatus.textContent = (
      `Actualizado ${formatDate(nodes.generated_at)}`
    );
    elements.loadingPanel.hidden = true;

    window.setTimeout(
      () => state.map.invalidateSize(),
      0
    );
  } catch (error) {
    console.error(error);

    elements.loadingPanel.hidden = true;
    elements.errorPanel.textContent = (
      "Non foi posible cargar os datos do mapa. "
      + String(error.message || error)
    );
    elements.errorPanel.hidden = false;
    elements.dataStatus.textContent = "Erro de carga";
  }
}

initialize();
