"use strict";

const MANIFEST_URL = "../data/manifest.json";

const HISTORY_MANIFEST_URL = (
  "../data/history/manifest.json"
);

const PUBLIC_MANIFEST_SCHEMA = (
  "mesh-noroeste.manifest/v1"
);

const PUBLIC_DATA_SCHEMA = (
  "mesh-noroeste.data/v1"
);

const HISTORY_MANIFEST_SCHEMA = (
  "mesh-noroeste.history-manifest/v1"
);

const HISTORY_HOUR_SCHEMA = (
  "mesh-noroeste.history-hour/v1"
);

const state = {
  map: null,
  nodeLayer: null,
  eventLayer: null,
  selectionLayer: null,
  eventAnimationLayer: null,
  eventAnimationFrame: null,
  eventAnimationToken: 0,
  nodes: [],
  nodeById: new Map(),
  manifest: null,
  selectedHour: null,
  hourDocument: null,
  selectedEventId: null,
  selectedNodeId: null,
  nodeEventFilterId: null,
  mobilePanel: null,
  restoringUrlState: false,
};

const elements = {
  status: document.querySelector(
    "#history-status"
  ),
  day: document.querySelector(
    "#history-day"
  ),
  hour: document.querySelector(
    "#history-hour"
  ),
  periodStatus: document.querySelector(
    "#history-period-status"
  ),
  dayTimelineBars: document.querySelector(
    "#history-day-timeline-bars"
  ),
  dayTimelineStatus: document.querySelector(
    "#history-day-timeline-status"
  ),
  dayTimelineTooltip: document.querySelector(
    "#history-day-timeline-tooltip"
  ),
  previous: document.querySelector(
    "#history-previous"
  ),
  next: document.querySelector(
    "#history-next"
  ),
  latest: document.querySelector(
    "#history-latest"
  ),
  nodeSearch: document.querySelector(
    "#history-node-search"
  ),
  nodeSearchStatus: document.querySelector(
    "#history-node-search-status"
  ),
  nodeSearchResults: document.querySelector(
    "#history-node-search-results"
  ),
  eventCount: document.querySelector(
    "#history-event-count"
  ),
  routeCount: document.querySelector(
    "#history-route-count"
  ),
  hourCount: document.querySelector(
    "#history-hour-count"
  ),
  retention: document.querySelector(
    "#history-retention"
  ),
  routesOnly: document.querySelector(
    "#history-routes-only"
  ),
  nodeFilterBanner: document.querySelector(
    "#history-node-filter-banner"
  ),
  nodeFilterLabel: document.querySelector(
    "#history-node-filter-label"
  ),
  nodeFilterClear: document.querySelector(
    "#history-node-filter-clear"
  ),
  eventStatus: document.querySelector(
    "#history-event-status"
  ),
  eventList: document.querySelector(
    "#history-event-list"
  ),
  selectedEventCard: document.querySelector(
    "#history-selected-event-card"
  ),
  selectedEventClose: document.querySelector(
    "#history-selected-event-close"
  ),
  selectedEventRoute: document.querySelector(
    "#history-selected-event-route"
  ),
  selectedEventMeta: document.querySelector(
    "#history-selected-event-meta"
  ),
  selectedEventState: document.querySelector(
    "#history-selected-event-state"
  ),
  selectedEventEvidence: document.querySelector(
    "#history-selected-event-evidence"
  ),
  selectedEventTowards: document.querySelector(
    "#history-selected-event-towards"
  ),
  selectedEventBack: document.querySelector(
    "#history-selected-event-back"
  ),
  selectedEventRouteDetails: document.querySelector(
    "#history-selected-event-route-details"
  ),
  selectedEventRouteSummary: document.querySelector(
    "#history-selected-event-route-summary"
  ),
  selectedNodeCard: document.querySelector(
    "#history-selected-node-card"
  ),
  selectedNodeClose: document.querySelector(
    "#history-selected-node-close"
  ),
  selectedNodeName: document.querySelector(
    "#history-selected-node-name"
  ),
  selectedNodeId: document.querySelector(
    "#history-selected-node-id"
  ),
  selectedNodeHistorySummary: document.querySelector(
    "#history-selected-node-history-summary"
  ),
  selectedNodeEventCount: document.querySelector(
    "#history-selected-node-event-count"
  ),
  selectedNodeRouteCount: document.querySelector(
    "#history-selected-node-route-count"
  ),
  selectedNodeOriginCount: document.querySelector(
    "#history-selected-node-origin-count"
  ),
  selectedNodeDestinationCount: document.querySelector(
    "#history-selected-node-destination-count"
  ),
  selectedNodeGatewayCount: document.querySelector(
    "#history-selected-node-gateway-count"
  ),
  selectedNodeActivity: document.querySelector(
    "#history-selected-node-activity"
  ),
  selectedNodeCopyLink: document.querySelector(
    "#history-selected-node-copy-link"
  ),
  selectedNodeCopyStatus: document.querySelector(
    "#history-selected-node-copy-status"
  ),
  selectedNodeCurrentHour: document.querySelector(
    "#history-selected-node-current-hour"
  ),
  selectedNodePreviousHour: document.querySelector(
    "#history-selected-node-previous-hour"
  ),
  selectedNodeNextHour: document.querySelector(
    "#history-selected-node-next-hour"
  ),
  loading: document.querySelector(
    "#history-loading"
  ),
  error: document.querySelector(
    "#history-error"
  ),
  mobileBackdrop: document.querySelector(
    "#history-mobile-backdrop"
  ),
  mobileTabs: Array.from(
    document.querySelectorAll(
      ".history-mobile-tab"
    )
  ),
  mobilePanels: Array.from(
    document.querySelectorAll(
      "[data-history-mobile-panel]"
    )
  ),
};


async function fetchJson(url) {
  const response = await fetch(
    new URL(
      url,
      window.location.href
    ),
    {
      cache: "no-store",
      headers: {
        Accept: "application/json",
      },
    }
  );

  if (!response.ok) {
    throw new Error(
      `${url}: resposta HTTP ${response.status}`
    );
  }

  return response.json();
}


function validatePublicManifest(document) {
  if (
    !document
    || document.schema !== PUBLIC_MANIFEST_SCHEMA
    || typeof document.generation !== "string"
    || !document.generation
    || !document.documents
  ) {
    throw new Error(
      "manifest.json non usa o contrato esperado."
    );
  }
}


function validateNodes(document) {
  if (
    !document
    || document.schema !== PUBLIC_DATA_SCHEMA
    || !Array.isArray(document.nodes)
  ) {
    throw new Error(
      "nodes.json non usa o contrato esperado."
    );
  }
}


function validateHistoryManifest(document) {
  if (
    !document
    || document.schema !== HISTORY_MANIFEST_SCHEMA
    || !Array.isArray(document.hours)
  ) {
    throw new Error(
      "O manifesto histórico non usa o contrato esperado."
    );
  }
}


function validateHistoryHour(document) {
  if (
    !document
    || document.schema !== HISTORY_HOUR_SCHEMA
    || !Array.isArray(document.events)
    || typeof document.start_us !== "number"
    || typeof document.end_us !== "number"
  ) {
    throw new Error(
      "O bloque histórico non usa o contrato esperado."
    );
  }
}



const MESHTASTIC_NODE_STYLES = Object.freeze({
  CLIENT: Object.freeze({
    color: "#1b5e2a",
    fillColor: "#2b8a3e",
    radius: 4.5,
    weight: 1.4,
  }),
  CLIENT_BASE: Object.freeze({
    color: "#075c68",
    fillColor: "#0c8599",
    radius: 5,
    weight: 1.7,
  }),
  CLIENT_MUTE: Object.freeze({
    color: "#6a1b7b",
    fillColor: "#9c36b5",
    radius: 4.8,
    weight: 1.6,
    dashArray: "2 2",
  }),
  ROUTER: Object.freeze({
    color: "#9c1f1f",
    fillColor: "#e03131",
    radius: 5.8,
    weight: 2,
  }),
  ROUTER_LATE: Object.freeze({
    color: "#9c5a00",
    fillColor: "#f08c00",
    radius: 5.8,
    weight: 2,
    dashArray: "4 2",
  }),
  TRACKER: Object.freeze({
    color: "#8f2449",
    fillColor: "#d6336c",
    radius: 5.2,
    weight: 1.8,
    dashArray: "1 2",
  }),
  unknown: Object.freeze({
    color: "#343a40",
    fillColor: "#868e96",
    radius: 4.4,
    weight: 1.3,
    dashArray: "2 3",
  }),
});


function nodeVisualStyle(node) {
  return (
    MESHTASTIC_NODE_STYLES[
      node.role || "unknown"
    ]
    || MESHTASTIC_NODE_STYLES.unknown
  );
}


function nodeDisplayName(node) {
  return (
    node.long_name
    || node.short_name
    || node.id
    || "Nodo"
  );
}


function positionedNode(node) {
  return (
    Number.isFinite(
      Number(node.latitude)
    )
    && Number.isFinite(
      Number(node.longitude)
    )
  );
}


function nodeName(node) {
  return (
    node?.long_name
    || node?.short_name
    || node?.id
    || "Nodo"
  );
}


function nodeNameById(nodeId) {
  return nodeName(
    state.nodeById.get(nodeId)
  );
}


function nodePoint(nodeId) {
  const node = state.nodeById.get(
    nodeId
  );

  if (!node || !positionedNode(node)) {
    return null;
  }

  return [
    Number(node.latitude),
    Number(node.longitude),
  ];
}


function createMap() {
  state.map = L.map(
    "history-map",
    {
      preferCanvas: true,
      minZoom: 5,
      maxZoom: 18,
    }
  );

  state.map.attributionControl.setPrefix(
    false
  );

  state.map.createPane(
    "history-routes"
  );
  state.map.getPane(
    "history-routes"
  ).style.zIndex = "390";

  state.map.createPane(
    "history-nodes"
  );
  state.map.getPane(
    "history-nodes"
  ).style.zIndex = "430";

  state.map.createPane(
    "history-selection"
  );
  state.map.getPane(
    "history-selection"
  ).style.zIndex = "460";
  state.map.getPane(
    "history-selection"
  ).style.pointerEvents = "none";

  state.map.createPane(
    "history-animation"
  );
  state.map.getPane(
    "history-animation"
  ).style.zIndex = "480";
  state.map.getPane(
    "history-animation"
  ).style.pointerEvents = "none";

  L.tileLayer(
    "https://{s}.basemaps.cartocdn.com/"
      + "light_nolabels/{z}/{x}/{y}.png",
    {
      maxZoom: 20,
      subdomains: "abcd",
      attribution:
        '&copy; <a href="https://www.openstreetmap.org/copyright">'
        + "OpenStreetMap</a> contributors "
        + '&copy; <a href="https://carto.com/attributions">'
        + "CARTO</a>",
    }
  ).addTo(state.map);

  state.eventLayer = (
    L.layerGroup().addTo(state.map)
  );

  state.nodeLayer = (
    L.layerGroup().addTo(state.map)
  );

  state.selectionLayer = (
    L.layerGroup().addTo(state.map)
  );

  state.eventAnimationLayer = (
    L.layerGroup().addTo(state.map)
  );
}


function renderNodes() {
  state.nodeLayer.clearLayers();

  for (const node of state.nodes) {
    if (!positionedNode(node)) {
      continue;
    }

    const point = [
      Number(node.latitude),
      Number(node.longitude),
    ];

    const marker = L.circleMarker(
      point,
      {
        pane: "history-nodes",
        radius: (
          5
          + (
            isHistoryMobileLayout()
              ? 0.8
              : 0
          )
        ),
        weight: 1.4,
        color: "#65757c",
        opacity: 0.55,
        fillColor: "#aeb9bd",
        fillOpacity: 0.34,
        bubblingMouseEvents: false,
      }
    );

    const hitMarker = L.circleMarker(
      point,
      {
        pane: "history-nodes",
        radius: (
          isHistoryMobileLayout()
            ? 12
            : 8
        ),
        stroke: false,
        fillColor: "#ffffff",
        fillOpacity: 0,
        bubblingMouseEvents: false,
      }
    );

    marker.bindTooltip(
      nodeDisplayName(node),
      {
        className:
          "history-node-tooltip",
      }
    );

    const selectThisNode = () => {
      selectNode(node);
    };

    marker.on(
      "click",
      selectThisNode
    );

    hitMarker.on(
      "click",
      selectThisNode
    );

    marker.addTo(state.nodeLayer);
    hitMarker.addTo(state.nodeLayer);
  }
}


function setInitialBounds() {
  const points = state.nodes
    .filter(positionedNode)
    .map(
      (node) => [
        Number(node.latitude),
        Number(node.longitude),
      ]
    );

  if (points.length === 0) {
    state.map.setView(
      [42.8, -8.3],
      7
    );
    return;
  }

  state.map.fitBounds(
    points,
    {
      padding: [24, 24],
      maxZoom: 7,
    }
  );
}


function availableDays() {
  return Array.from(
    new Set(
      state.manifest.hours.map(
        (hour) => hour.key.slice(0, 10)
      )
    )
  ).sort();
}


function hoursForDay(day) {
  return state.manifest.hours.filter(
    (hour) => (
      hour.key.slice(0, 10) === day
    )
  );
}


function renderDayOptions() {
  const days = availableDays();

  elements.day.replaceChildren();

  for (const day of days) {
    const option = document.createElement(
      "option"
    );

    option.value = day;
    option.textContent = day;

    elements.day.append(option);
  }

  elements.day.disabled = (
    days.length === 0
  );
}


function renderHourOptions(
  day,
  preferredKey = null
) {
  const hours = hoursForDay(day);

  elements.hour.replaceChildren();

  for (const hour of hours) {
    const option = document.createElement(
      "option"
    );

    option.value = hour.key;
    option.textContent = (
      hour.key.slice(11, 13)
      + ":00 UTC"
      + ` · ${hour.events} eventos`
    );

    elements.hour.append(option);
  }

  elements.hour.disabled = (
    hours.length === 0
  );

  if (
    preferredKey
    && hours.some(
      (hour) => hour.key === preferredKey
    )
  ) {
    elements.hour.value = preferredKey;
  }
}


function hourForDayAndNumber(
  day,
  hourNumber
) {
  const hourKey = (
    `${day}T`
    + String(hourNumber).padStart(2, "0")
  );

  return (
    state.manifest.hours.find(
      (hour) => hour.key === hourKey
    )
    || null
  );
}


function hideDayTimelineTooltip() {
  elements.dayTimelineTooltip.hidden = true;
  elements.dayTimelineTooltip.textContent = "";
}


function showDayTimelineTooltip(
  button,
  label
) {
  if (!button || !label) {
    hideDayTimelineTooltip();
    return;
  }

  elements.dayTimelineTooltip.textContent = label;
  elements.dayTimelineTooltip.hidden = false;

  const timelineRect = (
    elements.dayTimelineBars.getBoundingClientRect()
  );

  const buttonRect = button.getBoundingClientRect();

  const center = (
    buttonRect.left
    - timelineRect.left
    + buttonRect.width / 2
  );

  elements.dayTimelineTooltip.style.setProperty(
    "--history-day-tooltip-x",
    `${center}px`
  );
}


function renderDayTimeline() {
  const day = elements.day.value;

  elements.dayTimelineBars.replaceChildren();
  hideDayTimelineTooltip();

  if (!day || !state.manifest) {
    elements.dayTimelineStatus.textContent = "—";
    return;
  }

  const hours = hoursForDay(day);

  const maxEvents = Math.max(
    1,
    ...hours.map(
      (hour) => Number(hour.events) || 0
    )
  );

  const totalEvents = hours.reduce(
    (total, hour) => (
      total + (Number(hour.events) || 0)
    ),
    0
  );

  elements.dayTimelineStatus.textContent = (
    `${hours.length} horas · `
    + `${totalEvents} eventos`
  );

  for (
    let hourNumber = 0;
    hourNumber < 24;
    hourNumber += 1
  ) {
    const hour = hourForDayAndNumber(
      day,
      hourNumber
    );

    const button = document.createElement(
      "button"
    );

    button.type = "button";
    button.className = "history-day-timeline-bar";

    const hourLabel = (
      String(hourNumber).padStart(2, "0")
      + ":00 UTC"
    );

    if (!hour) {
      button.disabled = true;
      button.setAttribute(
        "aria-label",
        `${hourLabel} · sen datos`
      );

      button.style.setProperty(
        "--history-day-level",
        "0%"
      );

      elements.dayTimelineBars.append(button);
      continue;
    }

    const eventCount = (
      Number(hour.events) || 0
    );

    const tracerouteCount = (
      Number(hour.traceroutes) || 0
    );

    const level = Math.max(
      8,
      Math.round(
        (eventCount / maxEvents) * 100
      )
    );

    button.style.setProperty(
      "--history-day-level",
      `${level}%`
    );

    button.classList.toggle(
      "has-traceroute",
      tracerouteCount > 0
    );

    button.classList.toggle(
      "selected",
      state.selectedHour?.key === hour.key
    );

    button.setAttribute(
      "aria-pressed",
      String(
        state.selectedHour?.key === hour.key
      )
    );

    const activityLabel = (
      `${hourLabel} · `
      + `${eventCount} eventos`
      + (
        tracerouteCount > 0
          ? ` · ${tracerouteCount} RouteDiscovery`
          : " · sen RouteDiscovery"
      )
    );

    button.setAttribute(
      "aria-label",
      activityLabel
    );

    button.title = activityLabel;

    const showTooltip = () => {
      showDayTimelineTooltip(
        button,
        activityLabel
      );
    };

    button.addEventListener(
      "mouseenter",
      showTooltip
    );

    button.addEventListener(
      "focus",
      showTooltip
    );

    button.addEventListener(
      "mouseleave",
      hideDayTimelineTooltip
    );

    button.addEventListener(
      "blur",
      hideDayTimelineTooltip
    );

    button.addEventListener(
      "pointerdown",
      showTooltip
    );

    button.addEventListener(
      "click",
      async () => {
        await selectManifestHour(hour);

        if (isHistoryMobileLayout()) {
          setHistoryMobilePanel(null);
        }
      }
    );

    elements.dayTimelineBars.append(button);
  }
}


function nodeHistoryHourKeys(nodeId) {
  if (
    !nodeId
    || !state.manifest
    || !state.manifest.node_hours
  ) {
    return [];
  }

  const keys = state.manifest.node_hours[
    nodeId
  ];

  return Array.isArray(keys)
    ? keys
    : [];
}


function historyHourNavigationLabel(hour) {
  if (!hour?.key) {
    return "";
  }

  return (
    hour.key.slice(0, 10)
    + " · "
    + hour.key.slice(11, 13)
    + ":00 UTC"
  );
}


function historyNodeHourShortLabel(key) {
  if (!key) {
    return "—";
  }

  const day = key.slice(8, 10);
  const month = key.slice(5, 7);
  const hour = key.slice(11, 13);

  return `${day}/${month} ${hour}:00`;
}


function historyNodePresenceSummary(nodeId) {
  const keys = nodeHistoryHourKeys(nodeId);

  if (keys.length === 0) {
    return "Sen actividade indexada";
  }

  const countLabel = (
    keys.length === 1
      ? "Activo en 1 bloque"
      : `Activo en ${keys.length} bloques`
  );

  if (keys.length === 1) {
    return (
      `${countLabel} · `
      + `${historyNodeHourShortLabel(keys[0])} UTC`
    );
  }

  return (
    `${countLabel} · `
    + `${historyNodeHourShortLabel(keys[0])}`
    + " → "
    + `${historyNodeHourShortLabel(keys.at(-1))} UTC`
  );
}


function selectedHistoryHourRangeLabel() {
  if (!state.selectedHour?.key) {
    return "—";
  }

  const hour = Number(
    state.selectedHour.key.slice(11, 13)
  );

  const nextHour = (
    (hour + 1) % 24
  );

  return (
    state.selectedHour.key.slice(0, 10)
    + " · "
    + String(hour).padStart(2, "0")
    + ":00–"
    + String(nextHour).padStart(2, "0")
    + ":00 UTC"
  );
}


function nodeHistoryHourPosition(nodeId) {
  if (!state.selectedHour) {
    return -1;
  }

  return nodeHistoryHourKeys(nodeId).indexOf(
    state.selectedHour.key
  );
}


function adjacentNodeHistoryHour(
  nodeId,
  offset
) {
  if (
    !Number.isInteger(offset)
    || ![-1, 1].includes(offset)
  ) {
    throw new TypeError(
      "offset debe ser -1 ou 1"
    );
  }

  const keys = nodeHistoryHourKeys(
    nodeId
  );

  const index = nodeHistoryHourPosition(
    nodeId
  );

  if (index < 0) {
    return null;
  }

  const key = keys[
    index + offset
  ];

  if (!key) {
    return null;
  }

  return (
    state.manifest.hours.find(
      (hour) => hour.key === key
    )
    || null
  );
}


async function selectAdjacentNodeHistoryHour(
  offset
) {
  const node = selectedNode();

  if (!node) {
    return;
  }

  const hour = adjacentNodeHistoryHour(
    node.id,
    offset
  );

  if (!hour) {
    return;
  }

  await selectManifestHour(hour);
}


function historyHourFromUrl() {
  if (!state.manifest) {
    return null;
  }

  const params = new URLSearchParams(
    window.location.search
  );

  const key = params.get("hour");

  if (!key) {
    return null;
  }

  return (
    state.manifest.hours.find(
      (hour) => hour.key === key
    )
    || null
  );
}


function historyNodeIdFromUrl() {
  const params = new URLSearchParams(
    window.location.search
  );

  const value = params.get("node");

  if (!value) {
    return null;
  }

  if (value.startsWith("meshtastic:")) {
    return value;
  }

  if (value.startsWith("!")) {
    return `meshtastic:${value}`;
  }

  return value;
}


function historyNodeFromUrl() {
  const nodeId = historyNodeIdFromUrl();

  if (!nodeId) {
    return null;
  }

  return (
    state.nodeById.get(nodeId)
    || null
  );
}


function historyUrlNodeValue(nodeId) {
  if (!nodeId) {
    return null;
  }

  const prefix = "meshtastic:";

  return nodeId.startsWith(prefix)
    ? nodeId.slice(prefix.length)
    : nodeId;
}


async function copyHistoryUrl() {
  const url = window.location.href;

  try {
    await navigator.clipboard.writeText(url);

    elements.selectedNodeCopyStatus.textContent = (
      "Enlace copiado"
    );
  } catch (error) {
    console.error(error);

    elements.selectedNodeCopyStatus.textContent = (
      "Non foi posible copiar o enlace"
    );
  }

  window.setTimeout(
    () => {
      elements.selectedNodeCopyStatus.textContent = "";
    },
    2200
  );
}


function syncHistoryUrl(
  mode = "push"
) {
  if (state.restoringUrlState) {
    return;
  }

  const url = new URL(
    window.location.href
  );

  if (state.selectedHour?.key) {
    url.searchParams.set(
      "hour",
      state.selectedHour.key
    );
  } else {
    url.searchParams.delete("hour");
  }

  const nodeValue = historyUrlNodeValue(
    state.selectedNodeId
  );

  if (nodeValue) {
    url.searchParams.set(
      "node",
      nodeValue
    );
  } else {
    url.searchParams.delete("node");
  }

  if (url.href === window.location.href) {
    return;
  }

  if (mode === "replace") {
    window.history.replaceState(
      null,
      "",
      url
    );
    return;
  }

  window.history.pushState(
    null,
    "",
    url
  );
}


async function restoreHistoryStateFromUrl() {
  if (!state.manifest) {
    return;
  }

  state.restoringUrlState = true;

  try {
    const hour = (
      historyHourFromUrl()
      || latestHour()
    );

    if (
      hour
      && state.selectedHour?.key !== hour.key
    ) {
      await selectManifestHour(hour);
    }

    /*
     * O filtro de actividade non forma parte do contrato
     * compartible da URL. Restaurar unha URL sempre parte
     * dun estado determinista.
     */
    state.nodeEventFilterId = null;

    const node = historyNodeFromUrl();

    if (node) {
      selectNode(node);
    } else {
      state.selectedNodeId = null;

      renderSelectedNodeCard();
      renderEventList();
      renderMapEvents();
    }
  } finally {
    state.restoringUrlState = false;
  }

  /*
   * Canonicalizamos parámetros inexistentes ou inválidos
   * sen engadir unha nova entrada ao historial.
   */
  syncHistoryUrl("replace");
}


function initializeHistoryUrlNavigation() {
  window.addEventListener(
    "popstate",
    async () => {
      await restoreHistoryStateFromUrl();
    }
  );
}


function selectedHourIndex() {
  if (
    !state.manifest
    || !state.selectedHour
  ) {
    return -1;
  }

  return state.manifest.hours.findIndex(
    (hour) => (
      hour.key === state.selectedHour.key
    )
  );
}


async function selectManifestHour(hour) {
  if (!hour) {
    return;
  }

  const day = hour.key.slice(
    0,
    10
  );

  elements.day.value = day;

  renderHourOptions(
    day,
    hour.key
  );

  renderDayTimeline();

  await loadHour(hour);

  renderDayTimeline();
}


async function selectAdjacentHour(offset) {
  if (
    !Number.isInteger(offset)
    || ![-1, 1].includes(offset)
  ) {
    throw new TypeError(
      "offset debe ser -1 ou 1"
    );
  }

  const index = selectedHourIndex();

  if (index < 0) {
    return;
  }

  const target = (
    state.manifest.hours[
      index + offset
    ]
    || null
  );

  if (!target) {
    return;
  }

  await selectManifestHour(target);
}


function latestHour() {
  if (
    !state.manifest
    || state.manifest.hours.length === 0
  ) {
    return null;
  }

  return state.manifest.hours[
    state.manifest.hours.length - 1
  ];
}


function selectedManifestHour() {
  const key = elements.hour.value;

  return (
    state.manifest.hours.find(
      (hour) => hour.key === key
    )
    || null
  );
}


function eventPortnumLabel(portnum) {
  const value = Number(portnum);

  const labels = new Map([
    [1, "Mensaxe"],
    [2, "Hardware remoto"],
    [3, "Posición"],
    [4, "Información do nodo"],
    [5, "Routing"],
    [8, "Waypoint"],
    [67, "Telemetría"],
    [70, "RouteDiscovery"],
    [71, "Veciñanza"],
  ]);

  return (
    labels.get(value)
    || `portnum ${portnum}`
  );
}


function eventOriginName(event) {
  return (
    event.long_name
    || nodeNameById(event.from_id)
  );
}


function eventDestinationName(event) {
  if (
    event.to_id
    === "meshtastic:!ffffffff"
  ) {
    return "Broadcast";
  }

  return (
    event.to_long_name
    || nodeNameById(event.to_id)
  );
}


function eventTime(event) {
  return new Intl.DateTimeFormat(
    "gl-ES",
    {
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
      timeZone: "UTC",
    }
  ).format(
    new Date(
      event.imported_at_us / 1000
    )
  );
}


function traceroutePaths(event) {
  const traceroute = event.traceroute;

  if (!traceroute) {
    return [];
  }

  return [
    {
      key: "towards",
      label: "RouteDiscovery · ida",
      nodeIds: traceroute.towards || [],
    },
    {
      key: "back",
      label: "RouteDiscovery · volta",
      nodeIds: traceroute.back || [],
    },
  ];
}


function eventHasTraceroutePath(event) {
  return traceroutePaths(event).some(
    (route) => route.nodeIds.length >= 2
  );
}


function eventHasDrawableTraceroute(event) {
  return traceroutePaths(event).some(
    (route) => (
      routePointSegments(route).length > 0
    )
  );
}


function routePointSegments(route) {
  const segments = [];
  let current = [];

  for (const nodeId of route.nodeIds) {
    const point = nodePoint(nodeId);

    if (!point) {
      if (current.length >= 2) {
        segments.push(current);
      }

      current = [];
      continue;
    }

    current.push(point);
  }

  if (current.length >= 2) {
    segments.push(current);
  }

  return segments;
}


function prefersReducedMotion() {
  return window.matchMedia(
    "(prefers-reduced-motion: reduce)"
  ).matches;
}


function cancelSelectedEventAnimation() {
  state.eventAnimationToken += 1;

  if (state.eventAnimationFrame !== null) {
    window.cancelAnimationFrame(
      state.eventAnimationFrame
    );

    state.eventAnimationFrame = null;
  }

  state.eventAnimationLayer?.clearLayers();
}


function selectedHistoryEventAnimationSegments(event) {
  const segments = [];

  for (const route of traceroutePaths(event)) {
    for (const points of routePointSegments(route)) {
      for (
        let index = 0;
        index < points.length - 1;
        index += 1
      ) {
        const from = points[index];
        const to = points[index + 1];

        const length = state.map.distance(
          from,
          to
        );

        if (
          !Number.isFinite(length)
          || length <= 0
        ) {
          continue;
        }

        segments.push({
          from,
          to,
          length,
          routeKey: route.key,
        });
      }
    }
  }

  return segments;
}


function historyAnimationPointAtDistance(
  segments,
  targetDistance
) {
  let consumed = 0;

  for (const segment of segments) {
    const end = consumed + segment.length;

    if (targetDistance <= end) {
      const ratio = Math.max(
        0,
        Math.min(
          1,
          (
            targetDistance - consumed
          ) / segment.length
        )
      );

      return [
        segment.from[0]
          + (
            segment.to[0] - segment.from[0]
          ) * ratio,
        segment.from[1]
          + (
            segment.to[1] - segment.from[1]
          ) * ratio,
      ];
    }

    consumed = end;
  }

  return segments.at(-1)?.to || null;
}


function animateSelectedHistoryEventOnce(event) {
  cancelSelectedEventAnimation();

  if (
    !event
    || !event.traceroute
    || prefersReducedMotion()
  ) {
    return;
  }

  const segments = (
    selectedHistoryEventAnimationSegments(
      event
    )
  );

  if (segments.length === 0) {
    return;
  }

  const totalDistance = segments.reduce(
    (total, segment) => (
      total + segment.length
    ),
    0
  );

  if (
    !Number.isFinite(totalDistance)
    || totalDistance <= 0
  ) {
    return;
  }

  const movementDuration = Math.max(
    1_800,
    Math.min(
      6_000,
      segments.length * 700
    )
  );

  const marker = L.circleMarker(
    segments[0].from,
    {
      pane: "history-animation",
      radius: 6.5,
      color: "#7c1738",
      weight: 3,
      opacity: 1,
      fillColor: "#f8c4d3",
      fillOpacity: 1,
      interactive: false,
    }
  ).addTo(
    state.eventAnimationLayer
  );

  const token = state.eventAnimationToken;
  let startedAt = null;

  const frame = (timestamp) => {
    if (
      token !== state.eventAnimationToken
      || state.selectedEventId !== event.id
    ) {
      return;
    }

    if (startedAt === null) {
      startedAt = timestamp;
    }

    const elapsed = timestamp - startedAt;

    const progress = Math.max(
      0,
      Math.min(
        1,
        elapsed / movementDuration
      )
    );

    const point = historyAnimationPointAtDistance(
      segments,
      totalDistance * progress
    );

    if (point) {
      marker.setLatLng(point);
    }

    if (progress >= 1) {
      state.eventAnimationFrame = null;

      window.setTimeout(
        () => {
          if (
            token === state.eventAnimationToken
            && state.selectedEventId === event.id
          ) {
            state.eventAnimationLayer.clearLayers();
          }
        },
        350
      );

      return;
    }

    state.eventAnimationFrame = (
      window.requestAnimationFrame(frame)
    );
  };

  state.eventAnimationFrame = (
    window.requestAnimationFrame(frame)
  );
}


function eventHasPartialTraceroute(event) {
  for (const route of traceroutePaths(event)) {
    if (route.nodeIds.length < 2) {
      continue;
    }

    if (
      route.nodeIds.some(
        (nodeId) => !nodePoint(nodeId)
      )
    ) {
      return true;
    }
  }

  return false;
}


function addTraceroute(
  event,
  {
    selected = false,
    dimmed = false,
  } = {}
) {
  let rendered = false;

  for (const route of traceroutePaths(event)) {
    const routeColor = (
      route.key === "back"
        ? "#087f8c"
        : "#5f3dc4"
    );

    for (const points of routePointSegments(route)) {
      L.polyline(
        points,
        {
          pane: "history-routes",
          color: selected
            ? "#a61e4d"
            : routeColor,
          weight: (
            selected
              ? 4
              : route.key === "back"
                ? 2.8
                : 2.2
          ),
          opacity: (
            dimmed
              ? 0.1
              : selected
                ? 1
                : route.key === "back"
                  ? 0.92
                  : 0.68
          ),
          dashArray: (
            route.key === "back"
              ? "8 5"
              : null
          ),
          interactive: false,
        }
      ).addTo(state.eventLayer);

      rendered = true;
    }
  }

  return rendered;
}

function gatewayIds(event) {
  const ids = new Set();

  for (const stage of event.observed?.stages || []) {
    for (const gateway of stage.gateways || []) {
      if (gateway.gateway_id) {
        ids.add(gateway.gateway_id);
      }
    }
  }

  return [...ids];
}


function addGatewayObservations(
  event,
  {
    selected = false,
    dimmed = false,
  } = {}
) {
  const origin = nodePoint(event.from_id);

  if (!origin) {
    return false;
  }

  let rendered = false;

  for (const gatewayId of gatewayIds(event)) {
    if (gatewayId === event.from_id) {
      continue;
    }

    const gateway = nodePoint(gatewayId);

    if (!gateway) {
      continue;
    }

    L.polyline(
      [
        origin,
        gateway,
      ],
      {
        pane: "history-routes",
        color: selected
          ? "#087f8c"
          : "#495057",
        weight: selected ? 3.2 : 1.8,
        opacity: (
          dimmed
            ? 0.1
            : selected
              ? 0.95
              : 0.52
        ),
        dashArray: selected ? "5 5" : "4 6",
        interactive: false,
      }
    ).addTo(state.eventLayer);

    rendered = true;
  }

  return rendered;
}



function pointToSegmentDistance(
  point,
  start,
  end
) {
  const dx = end.x - start.x;
  const dy = end.y - start.y;

  if (dx === 0 && dy === 0) {
    return point.distanceTo(start);
  }

  const lengthSquared = (
    dx * dx + dy * dy
  );

  const projection = (
    (
      (point.x - start.x) * dx
      + (point.y - start.y) * dy
    )
    / lengthSquared
  );

  const ratio = Math.max(
    0,
    Math.min(1, projection)
  );

  const closest = L.point(
    start.x + ratio * dx,
    start.y + ratio * dy
  );

  return point.distanceTo(closest);
}


function tracerouteDistanceFromMapPoint(
  event,
  containerPoint
) {
  let minimum = Number.POSITIVE_INFINITY;

  for (const route of traceroutePaths(event)) {
    for (const segment of routePointSegments(route)) {
      const points = segment.map(
        (point) => (
          state.map.latLngToContainerPoint(point)
        )
      );

      for (
        let index = 0;
        index < points.length - 1;
        index += 1
      ) {
        minimum = Math.min(
          minimum,
          pointToSegmentDistance(
            containerPoint,
            points[index],
            points[index + 1]
          )
        );
      }
    }
  }

  return minimum;
}


function receptionDistanceFromMapPoint(
  event,
  containerPoint
) {
  const origin = nodePoint(event.from_id);

  if (!origin) {
    return Number.POSITIVE_INFINITY;
  }

  const originPoint = (
    state.map.latLngToContainerPoint(origin)
  );

  let minimum = Number.POSITIVE_INFINITY;

  for (const gatewayId of gatewayIds(event)) {
    if (gatewayId === event.from_id) {
      continue;
    }

    const gateway = nodePoint(gatewayId);

    if (!gateway) {
      continue;
    }

    const gatewayPoint = (
      state.map.latLngToContainerPoint(gateway)
    );

    minimum = Math.min(
      minimum,
      pointToSegmentDistance(
        containerPoint,
        originPoint,
        gatewayPoint
      )
    );
  }

  return minimum;
}


function historyMapSelectionThreshold() {
  return (
    isHistoryMobileLayout()
      ? 26
      : 16
  );
}


function nearestMapEvent(
  containerPoint
) {
  const threshold = (
    historyMapSelectionThreshold()
  );

  let nearest = null;
  let nearestDistance = threshold;

  for (const event of filteredEvents()) {
    const tracerouteDistance = (
      event.traceroute
        ? tracerouteDistanceFromMapPoint(
            event,
            containerPoint
          )
        : Number.POSITIVE_INFINITY
    );

    const receptionDistance = (
      receptionDistanceFromMapPoint(
        event,
        containerPoint
      )
    );

    const distance = Math.min(
      tracerouteDistance,
      receptionDistance
    );

    if (distance > nearestDistance) {
      continue;
    }

    nearest = event;
    nearestDistance = distance;
  }

  return nearest;
}


function initializeRouteMapSelection() {
  state.map.on(
    "click",
    (mapEvent) => {
      const event = nearestMapEvent(
        mapEvent.containerPoint
      );

      if (!event) {
        return;
      }

      selectEvent(event);
    }
  );
}



function normalizeSearchText(value) {
  return String(value ?? "")
    .normalize("NFD")
    .replace(/\p{Diacritic}/gu, "")
    .toLocaleLowerCase("gl-ES")
    .trim();
}


function searchableNodeText(node) {
  return normalizeSearchText(
    [
      node.long_name,
      node.short_name,
      node.id,
    ]
      .filter(Boolean)
      .join(" ")
  );
}


function clearNodeSearchResults() {
  elements.nodeSearchResults.replaceChildren();
  elements.nodeSearchResults.hidden = true;
  elements.nodeSearchStatus.textContent = "";
}


function focusNode(node) {
  const point = nodePoint(node.id);

  if (!point) {
    return;
  }

  selectNode(node);

  state.map.setView(
    point,
    Math.max(
      state.map.getZoom(),
      14
    )
  );
}


function renderNodeSearchResults() {
  const query = normalizeSearchText(
    elements.nodeSearch.value
  );

  if (!query) {
    clearNodeSearchResults();
    return;
  }

  const matches = state.nodes
    .filter(positionedNode)
    .filter(
      (node) => (
        searchableNodeText(node).includes(query)
      )
    )
    .slice(0, 20);

  const fragment = document.createDocumentFragment();

  for (const node of matches) {
    const item = document.createElement(
      "li"
    );

    const button = document.createElement(
      "button"
    );

    const name = document.createElement(
      "strong"
    );

    const identifier = document.createElement(
      "span"
    );

    button.type = "button";
    button.className = (
      "history-search-result"
    );

    name.textContent = (
      node.long_name
      || node.short_name
      || node.id
    );

    identifier.textContent = node.id;

    button.append(
      name,
      identifier
    );

    button.addEventListener(
      "click",
      () => {
        focusNode(node);
        clearNodeSearchResults();
      }
    );

    item.append(button);
    fragment.append(item);
  }

  elements.nodeSearchResults.replaceChildren(
    fragment
  );

  elements.nodeSearchResults.hidden = (
    matches.length === 0
  );

  if (matches.length === 0) {
    elements.nodeSearchStatus.textContent = (
      "Non se atoparon nodos con posición."
    );
    return;
  }

  elements.nodeSearchStatus.textContent = (
    `${matches.length} resultado`
    + (matches.length === 1 ? "" : "s")
    + (
      matches.length === 20
        ? " como máximo"
        : ""
    )
  );
}


function selectedNode() {
  if (!state.selectedNodeId) {
    return null;
  }

  return (
    state.nodeById.get(
      state.selectedNodeId
    )
    || null
  );
}


function eventInvolvesNode(
  event,
  nodeId
) {
  if (!event || !nodeId) {
    return false;
  }

  return eventNodeIds(event).includes(nodeId);
}


function nodeRolesInEvent(
  event,
  nodeId
) {
  if (!event || !nodeId) {
    return [];
  }

  const roles = [];

  if (event.from_id === nodeId) {
    roles.push("Orixe");
  }

  if (event.to_id === nodeId) {
    roles.push("Destino");
  }

  if (gatewayIds(event).includes(nodeId)) {
    roles.push("Gateway");
  }

  const routeContainsNode = traceroutePaths(event).some(
    (route) => (
      route.nodeIds.includes(nodeId)
    )
  );

  if (routeContainsNode) {
    roles.push("Ruta");
  }

  return roles;
}


function nodeRelatedEvents(nodeId) {
  if (
    !state.hourDocument
    || !nodeId
  ) {
    return [];
  }

  return state.hourDocument.events.filter(
    (event) => (
      eventInvolvesNode(
        event,
        nodeId
      )
    )
  );
}


function nodeActivitySummary(nodeId) {
  const events = nodeRelatedEvents(nodeId);

  let originCount = 0;
  let destinationCount = 0;
  let gatewayCount = 0;
  let routeCount = 0;

  for (const event of events) {
    if (event.from_id === nodeId) {
      originCount += 1;
    }

    if (event.to_id === nodeId) {
      destinationCount += 1;
    }

    if (gatewayIds(event).includes(nodeId)) {
      gatewayCount += 1;
    }

    if (
      event.traceroute
      && (
        event.traceroute.towards?.length >= 2
        || event.traceroute.back?.length >= 2
      )
    ) {
      routeCount += 1;
    }
  }

  return {
    events,
    originCount,
    destinationCount,
    gatewayCount,
    routeCount,
  };
}


function renderSelectedNodeCard() {
  const node = selectedNode();

  if (!node) {
    elements.selectedNodeCard.hidden = true;
    return;
  }

  const summary = nodeActivitySummary(
    node.id
  );

  elements.selectedNodeName.textContent = (
    node.long_name
    || node.short_name
    || node.id
  );

  elements.selectedNodeId.textContent = (
    node.id
  );

  elements.selectedNodeHistorySummary.textContent = (
    historyNodePresenceSummary(node.id)
  );

  elements.selectedNodeEventCount.textContent = (
    String(summary.events.length)
  );

  elements.selectedNodeRouteCount.textContent = (
    String(summary.routeCount)
  );

  elements.selectedNodeOriginCount.textContent = (
    String(summary.originCount)
  );

  elements.selectedNodeDestinationCount.textContent = (
    String(summary.destinationCount)
  );

  elements.selectedNodeGatewayCount.textContent = (
    String(summary.gatewayCount)
  );

  const filtering = (
    state.nodeEventFilterId === node.id
  );

  elements.selectedNodeActivity.textContent = (
    filtering
      ? "Mostrar toda a actividade"
      : "Ver actividade deste nodo"
  );

  elements.selectedNodeActivity.setAttribute(
    "aria-pressed",
    String(filtering)
  );

  const previousHour = adjacentNodeHistoryHour(
    node.id,
    -1
  );

  const nextHour = adjacentNodeHistoryHour(
    node.id,
    1
  );

  elements.selectedNodeCurrentHour.textContent = (
    selectedHistoryHourRangeLabel()
  );

  elements.selectedNodePreviousHour.disabled = (
    previousHour === null
  );

  elements.selectedNodeNextHour.disabled = (
    nextHour === null
  );

  elements.selectedNodePreviousHour.textContent = (
    previousHour
      ? `← ${historyHourNavigationLabel(previousHour)}`
      : "← Sen actividade anterior"
  );

  elements.selectedNodeNextHour.textContent = (
    nextHour
      ? `${historyHourNavigationLabel(nextHour)} →`
      : "Sen actividade seguinte →"
  );

  elements.selectedNodePreviousHour.title = (
    previousHour
      ? (
          "Ir á actividade anterior: "
          + historyHourNavigationLabel(previousHour)
        )
      : "Non hai unha hora anterior con actividade"
  );

  elements.selectedNodeNextHour.title = (
    nextHour
      ? (
          "Ir á actividade seguinte: "
          + historyHourNavigationLabel(nextHour)
        )
      : "Non hai unha hora posterior con actividade"
  );

  elements.selectedNodeCard.hidden = false;
}


function clearSelectedNode({
  clearFilter = true,
} = {}) {
  state.selectedNodeId = null;

  if (clearFilter) {
    state.nodeEventFilterId = null;
  }

  syncHistoryUrl();

  renderSelectedNodeCard();
  renderEventList();
  renderMapEvents();
}


function selectNode(node) {
  if (!node) {
    return;
  }

  state.selectedEventId = null;
  cancelSelectedEventAnimation();
  state.selectedNodeId = node.id;

  syncHistoryUrl();

  renderSelectedEventCard();
  renderSelectedNodeCard();
  renderEventList();
  renderMapEvents();

  const point = nodePoint(node.id);

  if (point) {
    state.map.setView(
      point,
      Math.max(
        state.map.getZoom(),
        13
      )
    );
  }

  if (isHistoryMobileLayout()) {
    setHistoryMobilePanel(null);
  }
}


function toggleSelectedNodeActivity() {
  const node = selectedNode();

  if (!node) {
    return;
  }

  const activatingFilter = (
    state.nodeEventFilterId !== node.id
  );

  state.nodeEventFilterId = (
    activatingFilter
      ? node.id
      : null
  );

  state.selectedEventId = null;
  cancelSelectedEventAnimation();

  renderSelectedEventCard();
  renderSelectedNodeCard();
  renderEventList();
  renderMapEvents();

  if (
    activatingFilter
    && isHistoryMobileLayout()
  ) {
    setHistoryMobilePanel("events");
  }
}


function renderNodeFilterBanner() {
  const nodeId = state.nodeEventFilterId;

  if (!nodeId) {
    elements.nodeFilterBanner.hidden = true;
    elements.nodeFilterLabel.textContent = "";
    return;
  }

  elements.nodeFilterLabel.textContent = (
    "Filtrando por "
    + nodeNameById(nodeId)
  );

  elements.nodeFilterBanner.hidden = false;
}


function filteredEvents() {
  let events = (
    state.hourDocument?.events
    || []
  );

  if (state.nodeEventFilterId) {
    events = events.filter(
      (event) => (
        eventInvolvesNode(
          event,
          state.nodeEventFilterId
        )
      )
    );
  }

  if (!elements.routesOnly.checked) {
    return events;
  }

  return events.filter(
    (event) => (
      event.traceroute !== null
    )
  );
}


function renderMapEvents() {
  state.eventLayer.clearLayers();
  state.selectionLayer.clearLayers();

  const events = filteredEvents();

  const selectedEvent = (
    state.selectedEventId
      ? events.find(
          (event) => (
            event.id === state.selectedEventId
          )
        ) || null
      : null
  );

  for (const event of events) {
    const selected = (
      selectedEvent?.id === event.id
    );

    const dimmed = (
      selectedEvent !== null
      && !selected
    );

    if (event.traceroute) {
      addTraceroute(
        event,
        {
          selected,
          dimmed,
        }
      );
    }

    addGatewayObservations(
      event,
      {
        selected,
        dimmed,
      }
    );
  }

  renderEventSelection();
}

function eventNodeIds(event) {
  const ids = new Set();

  if (event.from_id) {
    ids.add(event.from_id);
  }

  if (
    event.to_id
    && event.to_id !== "meshtastic:!ffffffff"
  ) {
    ids.add(event.to_id);
  }

  for (const gatewayId of gatewayIds(event)) {
    ids.add(gatewayId);
  }

  for (const route of traceroutePaths(event)) {
    for (const nodeId of route.nodeIds) {
      if (nodeId) {
        ids.add(nodeId);
      }
    }
  }

  return [...ids];
}


function addHistoryEventEndpointLabel(
  nodeId,
  label,
  className
) {
  if (
    !nodeId
    || nodeId === "meshtastic:!ffffffff"
  ) {
    return;
  }

  const point = nodePoint(nodeId);

  if (!point) {
    return;
  }

  L.circleMarker(
    point,
    {
      pane: "history-selection",
      radius: 1,
      stroke: false,
      fillOpacity: 0,
      interactive: false,
    }
  )
    .bindTooltip(
      label,
      {
        permanent: true,
        direction: "top",
        offset: [0, -11],
        className,
      }
    )
    .addTo(state.selectionLayer);
}


function renderEventSelection() {
  state.selectionLayer.clearLayers();

  if (!state.selectedEventId) {
    return;
  }

  const event = filteredEvents().find(
    (item) => item.id === state.selectedEventId
  );

  if (!event) {
    return;
  }

  const selectionColor = (
    event.traceroute
      ? "#a61e4d"
      : "#087f8c"
  );

  for (const nodeId of eventNodeIds(event)) {
    const point = nodePoint(nodeId);

    if (!point) {
      continue;
    }

    L.circleMarker(
      point,
      {
        pane: "history-selection",
        radius: 8,
        color: selectionColor,
        weight: 3,
        opacity: 1,
        fillColor: "#ffffff",
        fillOpacity: 0.28,
        interactive: false,
      }
    ).addTo(state.selectionLayer);
  }

  addHistoryEventEndpointLabel(
    event.from_id,
    "Orixe",
    "history-event-endpoint-label history-event-endpoint-origin"
  );

  addHistoryEventEndpointLabel(
    event.to_id,
    "Destino",
    "history-event-endpoint-label history-event-endpoint-destination"
  );
}


function eventPoints(event) {
  const points = [];

  for (const route of traceroutePaths(event)) {
    for (const nodeId of route.nodeIds) {
      const point = nodePoint(nodeId);

      if (point) {
        points.push(point);
      }
    }
  }

  const origin = nodePoint(event.from_id);

  if (origin) {
    points.push(origin);
  }

  for (const gatewayId of gatewayIds(event)) {
    const point = nodePoint(gatewayId);

    if (point) {
      points.push(point);
    }
  }

  return points;
}


function focusEvent(event) {
  const points = eventPoints(event);

  if (points.length === 0) {
    return;
  }

  if (points.length === 1) {
    state.map.setView(
      points[0],
      Math.max(
        state.map.getZoom(),
        12
      )
    );

    return;
  }

  state.map.fitBounds(
    points,
    {
      padding: [40, 40],
      maxZoom: 13,
    }
  );
}


function selectedHistoryEvent() {
  if (
    !state.selectedEventId
    || !state.hourDocument
  ) {
    return null;
  }

  return (
    state.hourDocument.events.find(
      (event) => (
        event.id === state.selectedEventId
      )
    )
    || null
  );
}


function historyTraceroutePathText(
  nodeIds,
  label
) {
  if (!Array.isArray(nodeIds) || nodeIds.length < 2) {
    return "";
  }

  return (
    `${label}: `
    + nodeIds
      .map((nodeId) => nodeNameById(nodeId))
      .join(" → ")
  );
}


function historyTracerouteSummary(event) {
  const traceroute = event.traceroute;

  if (!traceroute) {
    return "";
  }

  const parts = [];

  if ((traceroute.towards || []).length >= 2) {
    const hops = Math.max(
      0,
      traceroute.towards.length - 1
    );

    parts.push(
      `ida ${hops} `
      + (hops === 1 ? "salto" : "saltos")
    );
  }

  if ((traceroute.back || []).length >= 2) {
    const hops = Math.max(
      0,
      traceroute.back.length - 1
    );

    parts.push(
      `volta ${hops} `
      + (hops === 1 ? "salto" : "saltos")
    );
  }

  if (parts.length === 0) {
    return "RouteDiscovery · sen percorrido";
  }

  return (
    "RouteDiscovery · "
    + parts.join(" · ")
  );
}


function historyEventState(event) {
  if (!event.traceroute) {
    return {
      key: "observed",
      label: "Só observación",
    };
  }

  if (!eventHasTraceroutePath(event)) {
    return {
      key: "empty",
      label: "Sen percorrido",
    };
  }

  if (eventHasPartialTraceroute(event)) {
    return {
      key: "partial",
      label: "Percorrido parcial",
    };
  }

  if (eventHasDrawableTraceroute(event)) {
    return {
      key: "complete",
      label: "Percorrido dispoñible",
    };
  }

  return {
    key: "partial",
    label: "Percorrido parcial",
  };
}


function renderSelectedEventCard() {
  const event = selectedHistoryEvent();

  if (!event) {
    elements.selectedEventCard.hidden = true;
    elements.selectedEventTowards.hidden = true;
    elements.selectedEventBack.hidden = true;
    elements.selectedEventRouteDetails.hidden = true;
    elements.selectedEventRouteDetails.open = false;
    return;
  }

  elements.selectedEventRoute.textContent = (
    `${eventOriginName(event)}`
    + " → "
    + `${eventDestinationName(event)}`
  );

  elements.selectedEventMeta.textContent = [
    `${eventTime(event)} UTC`,
    eventPortnumLabel(event.portnum),
    event.channel || "Canal descoñecido",
    `${gatewayIds(event).length} `
      + (
        gatewayIds(event).length === 1
          ? "gateway"
          : "gateways"
      ),
  ].join(" · ");

  const eventState = historyEventState(event);

  elements.selectedEventState.className = (
    "history-selected-event-state "
    + `state-${eventState.key}`
  );

  elements.selectedEventState.textContent = (
    eventState.label
  );

  if (event.traceroute) {
    elements.selectedEventEvidence.textContent = (
      historyTracerouteSummary(event)
      + (
        eventHasPartialTraceroute(event)
          ? " · Faltan posicións para representar todo o percorrido"
          : ""
      )
    );
  } else {
    elements.selectedEventEvidence.textContent = (
      gatewayIds(event).length > 0
        ? "Paquete observado polos gateways indicados no mapa"
        : "Paquete observado"
    );
  }

  const towardsText = (
    event.traceroute
      ? historyTraceroutePathText(
          event.traceroute.towards,
          "Ida"
        )
      : ""
  );

  const backText = (
    event.traceroute
      ? historyTraceroutePathText(
          event.traceroute.back,
          "Volta"
        )
      : ""
  );

  elements.selectedEventTowards.textContent = towardsText;
  elements.selectedEventTowards.hidden = !towardsText;

  elements.selectedEventBack.textContent = backText;
  elements.selectedEventBack.hidden = !backText;

  const hasRouteContent = Boolean(
    towardsText || backText
  );

  elements.selectedEventRouteDetails.hidden = (
    !hasRouteContent
  );

  if (hasRouteContent) {
    const traceroute = event.traceroute || {};
    const parts = [];

    if (towardsText) {
      const hops = Math.max(
        0,
        (traceroute.towards?.length || 0) - 1
      );

      parts.push(
        `ida ${hops} `
        + (hops === 1 ? "salto" : "saltos")
      );
    }

    if (backText) {
      const hops = Math.max(
        0,
        (traceroute.back?.length || 0) - 1
      );

      parts.push(
        `volta ${hops} `
        + (hops === 1 ? "salto" : "saltos")
      );
    }

    elements.selectedEventRouteSummary.textContent = (
      "Percorrido da ruta"
      + (
        parts.length
          ? ` · ${parts.join(" · ")}`
          : ""
      )
    );
  } else {
    elements.selectedEventRouteDetails.open = false;
  }

  elements.selectedEventCard.hidden = false;
}


function clearSelectedEvent() {
  state.selectedEventId = null;
  cancelSelectedEventAnimation();

  renderEventList();
  renderMapEvents();
  renderSelectedEventCard();
}


function selectEvent(event) {
  state.selectedNodeId = null;
  syncHistoryUrl();
  renderSelectedNodeCard();

  const alreadySelected = (
    state.selectedEventId === event.id
  );

  state.selectedEventId = (
    alreadySelected
      ? null
      : event.id
  );

  renderEventList();
  renderMapEvents();
  renderSelectedEventCard();

  if (alreadySelected) {
    cancelSelectedEventAnimation();
    return;
  }

  const startAnimation = () => {
    if (state.selectedEventId === event.id) {
      animateSelectedHistoryEventOnce(event);
    }
  };

  state.map.once(
    "moveend",
    startAnimation
  );

  focusEvent(event);

  window.setTimeout(
    () => {
      if (
        state.selectedEventId === event.id
        && state.eventAnimationLayer.getLayers().length === 0
      ) {
        startAnimation();
      }
    },
    700
  );
}


function renderEventList() {
  const events = filteredEvents();

  renderNodeFilterBanner();
  elements.eventList.replaceChildren();

  elements.eventStatus.textContent = (
    `${events.length} eventos mostrados`
  );

  for (
    const event
    of [...events].reverse()
  ) {
    const item = document.createElement(
      "li"
    );

    const button = document.createElement(
      "button"
    );

    button.type = "button";
    button.className = (
      "history-event-button"
    );

    const selected = (
      event.id === state.selectedEventId
    );

    button.classList.toggle(
      "selected",
      selected
    );

    button.setAttribute(
      "aria-pressed",
      String(selected)
    );

    const title = document.createElement(
      "span"
    );

    title.className = (
      "history-event-title"
    );

    title.textContent = (
      `${eventOriginName(event)}`
      + " → "
      + `${eventDestinationName(event)}`
    );

    const meta = document.createElement(
      "span"
    );

    meta.className = (
      "history-event-meta"
    );

    meta.textContent = (
      `${eventTime(event)} UTC`
      + ` · ${eventPortnumLabel(event.portnum)}`
    );

    button.append(
      title,
      meta
    );

    if (state.nodeEventFilterId) {
      const roles = document.createElement(
        "span"
      );

      roles.className = (
        "history-event-node-roles"
      );

      for (
        const role
        of nodeRolesInEvent(
          event,
          state.nodeEventFilterId
        )
      ) {
        const badge = document.createElement(
          "span"
        );

        badge.className = (
          "history-event-node-role "
          + `role-${role.toLocaleLowerCase("gl-ES")}`
        );

        badge.textContent = role;
        roles.append(badge);
      }

      if (roles.childElementCount > 0) {
        button.append(roles);
      }
    }

    if (event.traceroute) {
      const badge = document.createElement(
        "span"
      );

      badge.className = (
        "history-route-badge"
      );
      badge.textContent = (
        "RouteDiscovery"
        + (
          !eventHasTraceroutePath(event)
            ? " · sen percorrido"
            : eventHasPartialTraceroute(event)
              ? " · Ruta parcial"
              : ""
        )
      );

      button.append(badge);
    }

    button.addEventListener(
      "click",
      () => {
        selectEvent(event);

        if (isHistoryMobileLayout()) {
          setHistoryMobilePanel(null);
        }
      }
    );

    item.append(button);
    elements.eventList.append(item);
  }
}


function updateSummary() {
  const document = state.hourDocument;

  if (!document) {
    elements.eventCount.textContent = "—";
    elements.routeCount.textContent = "—";
    return;
  }

  const routes = document.events.filter(
    (event) => event.traceroute !== null
  ).length;

  elements.eventCount.textContent = (
    String(document.events.length)
  );

  elements.routeCount.textContent = (
    String(routes)
  );
}


function updateManifestSummary() {
  elements.hourCount.textContent = (
    String(state.manifest.hour_count)
  );

  const days = Math.round(
    Number(
      state.manifest.retention_seconds
    ) / 86400
  );

  elements.retention.textContent = (
    `${days} días`
  );
}


async function loadHour(hour) {
  if (!hour) {
    return;
  }

  elements.loading.hidden = false;
  elements.error.hidden = true;

  try {
    const url = (
      "../data/history/"
      + hour.path
    );

    const document = await fetchJson(
      url
    );

    validateHistoryHour(
      document
    );

    state.selectedHour = hour;
    state.hourDocument = document;
    state.selectedEventId = null;
    cancelSelectedEventAnimation();

    /*
     * Conservamos o nodo seleccionado e o filtro de actividade
     * ao navegar entre horas. A ficha e os eventos recalculanse
     * contra o novo bloque histórico.
     */
    updateLatestButtonState();
    updateSummary();
    renderEventList();
    renderMapEvents();
    renderSelectedEventCard();
    renderSelectedNodeCard();

    const periodLabel = (
      `${hour.key.slice(0, 10)}`
      + " · "
      + `${hour.key.slice(11, 13)}:00–`
      + `${String(
        (
          Number(
            hour.key.slice(11, 13)
          ) + 1
        ) % 24
      ).padStart(2, "0")}:00 UTC`
    );

    elements.status.textContent = periodLabel;

    elements.periodStatus.textContent = (
      "Bloque mostrado: "
      + periodLabel
    );

    syncHistoryUrl();
  } catch (error) {
    console.error(error);

    elements.error.textContent = (
      "Non foi posible cargar este bloque histórico. "
      + String(
        error.message || error
      )
    );

    elements.error.hidden = false;
    elements.status.textContent = (
      "Erro cargando o histórico"
    );
  } finally {
    elements.loading.hidden = true;
  }
}


async function selectLatestHour() {
  await selectManifestHour(
    latestHour()
  );
}


async function loadBaseData() {
  const manifest = await fetchJson(
    MANIFEST_URL
  );

  validatePublicManifest(
    manifest
  );

  const manifestUrl = new URL(
    MANIFEST_URL,
    window.location.href
  );

  const nodesUrl = new URL(
    manifest.documents["nodes.json"],
    manifestUrl
  );

  const nodes = await fetchJson(
    nodesUrl
  );

  validateNodes(nodes);

  state.nodes = nodes.nodes;

  state.nodeById = new Map(
    state.nodes.map(
      (node) => [
        node.id,
        node,
      ]
    )
  );

  renderNodes();
  setInitialBounds();
}


async function loadHistoryManifest() {
  const manifest = await fetchJson(
    HISTORY_MANIFEST_URL
  );

  validateHistoryManifest(
    manifest
  );

  state.manifest = manifest;

  updateManifestSummary();
  renderDayOptions();
  renderDayTimeline();

  elements.latest.disabled = (
    manifest.hours.length === 0
  );

  updateLatestButtonState();

  if (manifest.hours.length === 0) {
    elements.status.textContent = (
      "Aínda non hai histórico dispoñible"
    );

    elements.loading.hidden = true;
    return;
  }

  await restoreHistoryStateFromUrl();
}



const HISTORY_MOBILE_BREAKPOINT = (
  "(max-width: 760px)"
);

const HISTORY_MOBILE_PANEL_TITLES = Object.freeze({
  search: "Buscar nodo",
  period: "Período",
  events: "Eventos",
  info: "Información",
});


function isHistoryMobileLayout() {
  return window.matchMedia(
    HISTORY_MOBILE_BREAKPOINT
  ).matches;
}


function renderHistoryMobilePanel() {
  const active = (
    isHistoryMobileLayout()
    && Boolean(state.mobilePanel)
  );

  document.body.classList.toggle(
    "history-mobile-panel-open",
    active
  );

  elements.mobileBackdrop.hidden = (
    !active
  );

  for (const panel of elements.mobilePanels) {
    const selected = (
      active
      && panel.dataset.historyMobilePanel
        === state.mobilePanel
    );

    panel.hidden = (
      isHistoryMobileLayout()
      && !selected
    );
  }

  for (const button of elements.mobileTabs) {
    const selected = (
      active
      && button.dataset.historyMobileTarget
        === state.mobilePanel
    );

    button.setAttribute(
      "aria-pressed",
      String(selected)
    );
  }

  window.requestAnimationFrame(
    () => state.map?.invalidateSize()
  );
}


function setHistoryMobilePanel(panel) {
  if (
    panel !== null
    && !Object.prototype.hasOwnProperty.call(
      HISTORY_MOBILE_PANEL_TITLES,
      panel
    )
  ) {
    return;
  }

  state.mobilePanel = panel;

  renderHistoryMobilePanel();

  if (
    panel
    && isHistoryMobileLayout()
  ) {
    const selectedPanel = (
      elements.mobilePanels.find(
        (item) => (
          item.dataset.historyMobilePanel
          === panel
        )
      )
    );

    if (selectedPanel) {
      selectedPanel.hidden = false;
      selectedPanel.style.pointerEvents = "auto";
    }
  }
}


function initializeHistoryMobileNavigation() {
  for (const button of elements.mobileTabs) {
    button.addEventListener(
      "click",
      () => {
        const target = (
          button.dataset.historyMobileTarget
        );

        setHistoryMobilePanel(
          state.mobilePanel === target
            ? null
            : target
        );
      }
    );
  }

  for (const panel of elements.mobilePanels) {
    panel.addEventListener(
      "click",
      (event) => {
        event.stopPropagation();
      }
    );
  }

  elements.mobileBackdrop.addEventListener(
    "click",
    () => {
      setHistoryMobilePanel(null);
    }
  );

  document.addEventListener(
    "keydown",
    (event) => {
      if (
        event.key === "Escape"
        && state.mobilePanel
      ) {
        setHistoryMobilePanel(null);
      }
    }
  );

  window.matchMedia(
    HISTORY_MOBILE_BREAKPOINT
  ).addEventListener(
    "change",
    () => {
      if (!isHistoryMobileLayout()) {
        state.mobilePanel = null;
      }

      renderHistoryMobilePanel();
    }
  );

  renderHistoryMobilePanel();
}


function updateLatestButtonState() {
  const latest = latestHour();
  const index = selectedHourIndex();

  if (!latest || index < 0) {
    elements.previous.disabled = true;
    elements.next.disabled = true;
    elements.latest.disabled = true;
    elements.latest.textContent = (
      "Non hai histórico"
    );
    return;
  }

  elements.previous.disabled = (
    index === 0
  );

  elements.next.disabled = (
    index === state.manifest.hours.length - 1
  );

  const alreadyLatest = (
    state.selectedHour?.key === latest.key
  );

  elements.latest.disabled = (
    alreadyLatest
  );

  elements.latest.textContent = (
    alreadyLatest
      ? "Xa estás na máis recente"
      : "Ir á máis recente"
  );
}


function bindControls() {
  elements.nodeSearch.addEventListener(
    "input",
    renderNodeSearchResults
  );

  elements.selectedNodeClose.addEventListener(
    "click",
    () => {
      clearSelectedNode();
    }
  );

  elements.selectedNodeActivity.addEventListener(
    "click",
    toggleSelectedNodeActivity
  );

  elements.selectedNodeCopyLink.addEventListener(
    "click",
    copyHistoryUrl
  );

  elements.selectedNodePreviousHour.addEventListener(
    "click",
    async () => {
      await selectAdjacentNodeHistoryHour(-1);
    }
  );

  elements.selectedNodeNextHour.addEventListener(
    "click",
    async () => {
      await selectAdjacentNodeHistoryHour(1);
    }
  );

  elements.nodeFilterClear.addEventListener(
    "click",
    () => {
      state.nodeEventFilterId = null;
      state.selectedEventId = null;

      renderSelectedEventCard();
      renderSelectedNodeCard();
      renderEventList();
      renderMapEvents();
    }
  );

  elements.selectedEventClose.addEventListener(
    "click",
    clearSelectedEvent
  );

  elements.day.addEventListener(
    "change",
    async () => {
      renderHourOptions(
        elements.day.value
      );

      renderDayTimeline();

      const hour = selectedManifestHour();

      if (hour) {
        await loadHour(hour);
      }
    }
  );

  elements.hour.addEventListener(
    "change",
    async () => {
      await loadHour(
        selectedManifestHour()
      );
    }
  );

  elements.previous.addEventListener(
    "click",
    async () => {
      await selectAdjacentHour(-1);
    }
  );

  elements.next.addEventListener(
    "click",
    async () => {
      await selectAdjacentHour(1);
    }
  );

  elements.latest.addEventListener(
    "click",
    selectLatestHour
  );

  elements.routesOnly.addEventListener(
    "change",
    () => {
      state.selectedEventId = null;
      renderEventList();
      renderMapEvents();
      renderSelectedEventCard();
      renderSelectedNodeCard();
    }
  );
}


async function initialize() {
  try {
    createMap();
    bindControls();
    initializeHistoryMobileNavigation();
    initializeRouteMapSelection();
    initializeHistoryUrlNavigation();

    await loadBaseData();
    await loadHistoryManifest();

    elements.loading.hidden = true;
  } catch (error) {
    console.error(error);

    elements.loading.hidden = true;

    elements.error.textContent = (
      "Non foi posible iniciar o histórico. "
      + String(error.message || error)
    );

    elements.error.hidden = false;
    elements.status.textContent = (
      "Erro de carga"
    );
  }
}


initialize();
