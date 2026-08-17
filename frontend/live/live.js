"use strict";

const MANIFEST_URL = "../data/manifest.json";
const LIVE_URL = "../data/live.json";

const PUBLIC_MANIFEST_SCHEMA = (
  "mesh-noroeste.manifest/v1"
);

const PUBLIC_DATA_SCHEMA = (
  "mesh-noroeste.data/v1"
);

const PUBLIC_LIVE_SCHEMA = (
  "mesh-noroeste.live/v1"
);

const REFRESH_INTERVAL_MS = 60_000;

const LIVE_MOBILE_BREAKPOINT = "(max-width: 760px)";

const LIVE_MOBILE_PANEL_TITLES = Object.freeze({
  search: "Buscar nodo",
  activity: "Actividade",
  display: "Visualización",
  events: "Últimos eventos",
});

const state = {
  map: null,
  nodeLayer: null,
  eventLayer: null,
  nodes: [],
  nodeById: new Map(),
  live: null,
  refreshTimer: null,
  selectedEventId: null,
  selectionLayer: null,
  selectedNodeId: null,
  nodeSearchSelectionLayer: null,
  mobilePanel: null,
  lastMobileTrigger: null,
};

const elements = {
  status: document.querySelector("#live-status"),
  eventCount: document.querySelector("#event-count"),
  tracerouteCount: document.querySelector(
    "#traceroute-count"
  ),
  positionedCount: document.querySelector(
    "#positioned-count"
  ),
  liveWindow: document.querySelector("#live-window"),
  visibleEventCount: document.querySelector(
    "#visible-event-count"
  ),
  eventLimit: document.querySelector("#event-limit"),
  showReceptions: document.querySelector(
    "#show-receptions"
  ),
  showTraceroutes: document.querySelector(
    "#show-traceroutes"
  ),
  refresh: document.querySelector("#refresh-live"),
  eventList: document.querySelector("#event-list"),
  nodeSearch: document.querySelector("#live-node-search"),
  nodeSearchStatus: document.querySelector(
    "#live-node-search-status"
  ),
  nodeSearchResults: document.querySelector(
    "#live-node-search-results"
  ),
  loading: document.querySelector("#loading-panel"),
  error: document.querySelector("#error-panel"),
  app: document.querySelector(".live-app"),
  sidebar: document.querySelector("#live-sidebar"),
  mapRegion: document.querySelector(".live-map-region"),
  mobileBackdrop: document.querySelector(
    "#live-mobile-backdrop"
  ),
  mobileSheetTitle: document.querySelector(
    "#live-mobile-sheet-title"
  ),
  mobileSheetClose: document.querySelector(
    "#live-mobile-sheet-close"
  ),
  mobileTabs: Array.from(
    document.querySelectorAll(".live-mobile-tab")
  ),
  mobilePanels: Array.from(
    document.querySelectorAll("[data-mobile-panel]")
  ),
};

function isLiveMobileLayout() {
  return window.matchMedia(
    LIVE_MOBILE_BREAKPOINT
  ).matches;
}

function syncLiveMobilePanel() {
  const mobile = isLiveMobileLayout();
  const panel = (
    mobile
      ? state.mobilePanel
      : null
  );
  const open = Boolean(panel);

  elements.app.classList.toggle(
    "live-mobile-sheet-open",
    open
  );

  for (const block of elements.mobilePanels) {
    block.hidden = (
      mobile
      && block.dataset.mobilePanel !== panel
    );
  }

  for (const button of elements.mobileTabs) {
    const active = (
      button.dataset.liveMobileTarget === panel
    );

    button.setAttribute(
      "aria-pressed",
      String(active)
    );
    button.setAttribute(
      "aria-expanded",
      String(active)
    );
  }

  elements.mobileBackdrop.hidden = !open;

  elements.mobileSheetTitle.textContent = (
    open
      ? LIVE_MOBILE_PANEL_TITLES[panel]
      : "Controis"
  );

  if (open) {
    elements.sidebar.setAttribute(
      "role",
      "dialog"
    );
    elements.sidebar.setAttribute(
      "aria-modal",
      "true"
    );
    elements.sidebar.setAttribute(
      "aria-labelledby",
      "live-mobile-sheet-title"
    );

    elements.mapRegion.inert = true;
  } else {
    elements.sidebar.removeAttribute("role");
    elements.sidebar.removeAttribute("aria-modal");
    elements.sidebar.removeAttribute(
      "aria-labelledby"
    );

    elements.mapRegion.inert = false;
  }
}

function setLiveMobilePanel(
  panel,
  {
    restoreFocus = false,
  } = {}
) {
  state.mobilePanel = (
    panel && LIVE_MOBILE_PANEL_TITLES[panel]
      ? panel
      : null
  );

  syncLiveMobilePanel();

  if (state.mobilePanel) {
    window.requestAnimationFrame(() => {
      if (state.mobilePanel === "search") {
        elements.nodeSearch.focus({
          preventScroll: true,
        });
        return;
      }

      elements.mobileSheetClose.focus({
        preventScroll: true,
      });
    });

    return;
  }

  if (
    restoreFocus
    && state.lastMobileTrigger
  ) {
    state.lastMobileTrigger.focus({
      preventScroll: true,
    });
  }
}

function initializeLiveMobileNavigation() {
  for (const button of elements.mobileTabs) {
    button.addEventListener(
      "click",
      () => {
        const target = (
          button.dataset.liveMobileTarget
        );

        if (state.mobilePanel === target) {
          setLiveMobilePanel(
            null,
            {
              restoreFocus: true,
            }
          );
          return;
        }

        state.lastMobileTrigger = button;
        setLiveMobilePanel(target);
      }
    );
  }

  elements.mobileSheetClose.addEventListener(
    "click",
    () => {
      setLiveMobilePanel(
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
      setLiveMobilePanel(
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
        event.key === "Escape"
        && state.mobilePanel
      ) {
        setLiveMobilePanel(
          null,
          {
            restoreFocus: true,
          }
        );
      }
    }
  );

  window.matchMedia(
    LIVE_MOBILE_BREAKPOINT
  ).addEventListener(
    "change",
    () => {
      if (!isLiveMobileLayout()) {
        state.mobilePanel = null;
      }

      syncLiveMobilePanel();
      state.map?.invalidateSize();
    }
  );

  syncLiveMobilePanel();
}

function formatNumber(value) {
  return new Intl.NumberFormat("gl-ES").format(value);
}

function eventDate(event) {
  const microseconds = Number(event.imported_at_us);

  if (!Number.isFinite(microseconds)) {
    return null;
  }

  return new Date(microseconds / 1000);
}

function formatEventTime(event) {
  const date = eventDate(event);

  if (!date || Number.isNaN(date.getTime())) {
    return "Hora descoñecida";
  }

  return new Intl.DateTimeFormat(
    "gl-ES",
    {
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    }
  ).format(date);
}

function formatWindowDate(date) {
  if (!date || Number.isNaN(date.getTime())) {
    return "Hora descoñecida";
  }

  return new Intl.DateTimeFormat(
    "gl-ES",
    {
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    }
  ).format(date);
}

function liveEventWindow(events) {
  const dates = events
    .map(eventDate)
    .filter(
      (date) => (
        date
        && !Number.isNaN(date.getTime())
      )
    )
    .sort(
      (left, right) => left.getTime() - right.getTime()
    );

  if (dates.length === 0) {
    return "Sen hora dispoñible";
  }

  if (dates.length === 1) {
    return formatWindowDate(dates[0]);
  }

  return [
    formatWindowDate(dates[0]),
    "–",
    formatWindowDate(dates[dates.length - 1]),
  ].join(" ");
}

function updateVisibleEventSummary() {
  const visible = visibleEvents().length;
  const total = state.live?.events?.length || 0;

  elements.visibleEventCount.textContent = (
    `${formatNumber(visible)} de ${formatNumber(total)}`
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

function focusNode(node) {
  const point = nodePoint(node.id);

  if (!point) {
    return;
  }

  state.selectedNodeId = node.id;
  renderNodeSearchSelection();

  state.map.setView(
    point,
    Math.max(state.map.getZoom(), 14)
  );

  if (isLiveMobileLayout()) {
    setLiveMobilePanel(null);
  }
}

function renderNodeSearchResults() {
  const query = normalizeSearchText(
    elements.nodeSearch.value
  );

  if (!query) {
    elements.nodeSearchResults.replaceChildren();
    elements.nodeSearchResults.hidden = true;
    elements.nodeSearchStatus.textContent = "";
    return;
  }

  const matches = state.nodes
    .filter(positionedNode)
    .filter(
      (node) => searchableNodeText(node).includes(query)
    )
    .slice(0, 20);

  const fragment = document.createDocumentFragment();

  for (const node of matches) {
    const item = document.createElement("li");
    const button = document.createElement("button");
    const name = document.createElement("strong");
    const identifier = document.createElement("span");

    button.type = "button";
    button.className = "live-search-result";

    name.textContent = (
      node.long_name
      || node.short_name
      || node.id
    );

    identifier.textContent = node.id;

    button.append(name, identifier);

    button.addEventListener(
      "click",
      () => focusNode(node)
    );

    item.append(button);
    fragment.append(item);
  }

  elements.nodeSearchResults.replaceChildren(fragment);
  elements.nodeSearchResults.hidden = matches.length === 0;

  if (matches.length === 0) {
    elements.nodeSearchStatus.textContent = (
      "Non se atoparon nodos con posición."
    );
    return;
  }

  elements.nodeSearchStatus.textContent = (
    `${formatNumber(matches.length)} resultado`
    + (matches.length === 1 ? "" : "s")
    + (matches.length === 20 ? " como máximo" : "")
  );
}

function nodeNameById(nodeId, fallback = null) {
  const node = state.nodeById.get(nodeId);

  if (node) {
    return (
      node.long_name
      || node.short_name
      || node.id
    );
  }

  return fallback || nodeId;
}

function eventOriginName(event) {
  return (
    event.long_name
    || nodeNameById(event.from_id)
  );
}

function eventDestinationName(event) {
  if (event.to_id === "meshtastic:!ffffffff") {
    return "Broadcast";
  }

  return (
    event.to_long_name
    || nodeNameById(event.to_id)
  );
}

async function fetchJson(url) {
  const response = await fetch(
    new URL(url, window.location.href),
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

function validateManifest(manifest) {
  if (
    !manifest
    || manifest.schema !== PUBLIC_MANIFEST_SCHEMA
    || typeof manifest.generation !== "string"
    || !manifest.generation
    || !manifest.documents
  ) {
    throw new Error(
      "manifest.json non usa o contrato esperado."
    );
  }

  const nodesPath = (
    `generations/${manifest.generation}/nodes.json`
  );

  if (
    manifest.documents["nodes.json"]
    !== nodesPath
  ) {
    throw new Error(
      "manifest.json non referencia nodes.json correctamente."
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

function validateLive(document) {
  if (
    !document
    || document.schema !== PUBLIC_LIVE_SCHEMA
    || !Array.isArray(document.events)
    || !document.sources
  ) {
    throw new Error(
      "live.json non usa o contrato esperado."
    );
  }
}

function createMap() {
  state.map = L.map("live-map", {
    preferCanvas: true,
    minZoom: 5,
    maxZoom: 18,
  });

  state.map.attributionControl.setPrefix(false);

  state.map.createPane("live-routes");
  state.map.getPane("live-routes").style.zIndex = "390";

  state.map.createPane("live-nodes");
  state.map.getPane("live-nodes").style.zIndex = "430";

  state.map.createPane("live-selection");
  state.map.getPane("live-selection").style.zIndex = "460";
  state.map.getPane(
    "live-selection"
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

  state.eventLayer = L.layerGroup().addTo(state.map);
  state.nodeLayer = L.layerGroup().addTo(state.map);
  state.selectionLayer = L.layerGroup().addTo(state.map);
  state.nodeSearchSelectionLayer = (
    L.layerGroup().addTo(state.map)
  );
}

function positionedNode(node) {
  return (
    node.network === "meshtastic"
    && Number.isFinite(Number(node.latitude))
    && Number.isFinite(Number(node.longitude))
  );
}

function nodePoint(nodeId) {
  const node = state.nodeById.get(nodeId);

  if (!node || !positionedNode(node)) {
    return null;
  }

  return [
    Number(node.latitude),
    Number(node.longitude),
  ];
}

function renderNodeSearchSelection() {
  state.nodeSearchSelectionLayer.clearLayers();

  if (!state.selectedNodeId) {
    return;
  }

  const node = state.nodeById.get(
    state.selectedNodeId
  );

  if (!node) {
    return;
  }

  const point = nodePoint(node.id);

  if (!point) {
    return;
  }

  const name = (
    node.long_name
    || node.short_name
    || node.id
  );

  L.circleMarker(
    point,
    {
      pane: "live-selection",
      radius: 9,
      color: "#a61e4d",
      weight: 3.5,
      opacity: 1,
      fillColor: "#ffffff",
      fillOpacity: 0.32,
      interactive: false,
    }
  )
    .bindTooltip(
      escapeHtml(name),
      {
        permanent: true,
        direction: "top",
        offset: [0, -10],
        className: "live-selected-node-label",
      }
    )
    .addTo(state.nodeSearchSelectionLayer);
}


function renderNodes() {
  state.nodeLayer.clearLayers();

  for (const node of state.nodes) {
    if (!positionedNode(node)) {
      continue;
    }

    const marker = L.circleMarker(
      [
        Number(node.latitude),
        Number(node.longitude),
      ],
      {
        pane: "live-nodes",
        radius: 4,
        color: "#175632",
        weight: 1.3,
        opacity: 0.72,
        fillColor: "#267a4d",
        fillOpacity: 0.55,
      }
    );

    const name = (
      node.long_name
      || node.short_name
      || node.id
    );

    marker.bindTooltip(
      `<div class="live-node-tooltip">`
      + `<strong>${escapeHtml(name)}</strong>`
      + `<span>${escapeHtml(node.id)}</span>`
      + `</div>`,
      {
        direction: "top",
      }
    );

    marker.addTo(state.nodeLayer);
  }
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function eventTooltip(event, label) {
  const gatewayCount = (
    event.observed?.gateway_count || 0
  );

  return [
    `<div class="live-event-tooltip-content">`,
    `<strong>${escapeHtml(label)}</strong>`,
    `<span class="live-event-tooltip-route">`,
    `${escapeHtml(eventOriginName(event))}`,
    ` → `,
    `${escapeHtml(eventDestinationName(event))}`,
    `</span>`,
    `<span class="live-event-tooltip-meta">`,
    `${escapeHtml(formatEventTime(event))}`,
    ` · portnum ${escapeHtml(event.portnum)}`,
    `</span>`,
    `<span class="live-event-tooltip-meta">`,
    `${escapeHtml(gatewayCount)} gateway(s) observador(es)`,
    `</span>`,
    `</div>`,
  ].join("");
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

function addTraceroute(
  event,
  {
    selected = false,
    dimmed = false,
  } = {}
) {
  let rendered = false;

  for (const route of traceroutePaths(event)) {
    const points = route.nodeIds
      .map(nodePoint)
      .filter(Boolean);

    if (points.length < 2) {
      continue;
    }

    const routeColor = (
      route.key === "back"
        ? "#087f8c"
        : "#5f3dc4"
    );

    L.polyline(
      points,
      {
        pane: "live-routes",
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
      }
    )
      .bindTooltip(
        eventTooltip(event, route.label),
        {
          className: "live-event-tooltip live-route-tooltip",
          sticky: true,
        }
      )
      .addTo(state.eventLayer);

    rendered = true;
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
        pane: "live-routes",
        color: selected
          ? "#a61e4d"
          : "#495057",
        weight: selected ? 2.8 : 1.8,
        opacity: (
          dimmed
            ? 0.1
            : selected
              ? 0.92
              : 0.52
        ),
        dashArray: selected ? "5 5" : "4 6",
      }
    )
      .bindTooltip(
        eventTooltip(
          event,
          "Recepción observada por gateway"
        ),
        {
          className: "live-event-tooltip live-reception-tooltip",
          sticky: true,
        }
      )
      .addTo(state.eventLayer);

    rendered = true;
  }

  return rendered;
}

function selectedVisibleEvent() {
  if (!state.selectedEventId) {
    return null;
  }

  return visibleEvents().find(
    (event) => event.id === state.selectedEventId
  ) || null;
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

function renderEventSelection() {
  state.selectionLayer.clearLayers();

  const event = selectedVisibleEvent();

  if (!event) {
    return;
  }

  for (const nodeId of eventNodeIds(event)) {
    const point = nodePoint(nodeId);

    if (!point) {
      continue;
    }

    L.circleMarker(
      point,
      {
        pane: "live-selection",
        radius: 8,
        color: "#a61e4d",
        weight: 3,
        opacity: 1,
        fillColor: "#ffffff",
        fillOpacity: 0.28,
        interactive: false,
      }
    ).addTo(state.selectionLayer);
  }
}

function selectEvent(event) {
  const alreadySelected = (
    state.selectedEventId === event.id
  );

  state.selectedEventId = (
    alreadySelected
      ? null
      : event.id
  );

  renderEvents();
  renderEventList();

  if (!alreadySelected) {
    focusEvent(event);
  }
}


function visibleEvents() {
  const value = elements.eventLimit.value;

  const events = [...state.live.events]
    .sort(
      (left, right) => (
        Number(right.imported_at_us)
        - Number(left.imported_at_us)
      )
    );

  if (value === "all") {
    return events;
  }

  const limit = Number(value);

  return events.slice(
    0,
    Number.isFinite(limit) ? limit : 50
  );
}

function updateEventLimitOptions() {
  const allOption = elements.eventLimit.querySelector(
    'option[value="all"]'
  );

  if (!allOption) {
    return;
  }

  const total = state.live?.events?.length || 0;

  allOption.textContent = (
    `Todos (${formatNumber(total)})`
  );
}

function renderEvents() {
  state.eventLayer.clearLayers();

  let positioned = 0;

  const selectedEvent = selectedVisibleEvent();
  const selectedEventId = selectedEvent?.id || null;

  for (const event of visibleEvents()) {
    let rendered = false;

    const selected = (
      selectedEventId === event.id
    );

    const dimmed = (
      selectedEventId !== null
      && !selected
    );

    if (
      elements.showTraceroutes.checked
      && event.traceroute
    ) {
      rendered = (
        addTraceroute(
          event,
          {
            selected,
            dimmed,
          }
        )
        || rendered
      );
    }

    if (elements.showReceptions.checked) {
      rendered = (
        addGatewayObservations(
          event,
          {
            selected,
            dimmed,
          }
        )
        || rendered
      );
    }

    if (rendered) {
      positioned += 1;
    }
  }

  elements.positionedCount.textContent = (
    formatNumber(positioned)
  );

  renderEventSelection();
}

function renderEventList() {
  const fragment = document.createDocumentFragment();

  for (const event of visibleEvents()) {
    const item = document.createElement("li");
    const button = document.createElement("button");
    const name = document.createElement("span");
    const metadata = document.createElement("span");
    const type = document.createElement("span");

    const selected = (
      state.selectedEventId === event.id
    );

    button.type = "button";
    button.className = (
      "live-event-button"
      + (selected ? " selected" : "")
    );
    button.setAttribute(
      "aria-pressed",
      String(selected)
    );

    name.className = "live-event-name";
    name.textContent = [
      eventOriginName(event),
      "→",
      eventDestinationName(event),
    ].join(" ");

    metadata.className = "live-event-meta";
    metadata.textContent = [
      formatEventTime(event),
      `portnum ${event.portnum}`,
      `${event.observed?.gateway_count || 0} gateway(s)`,
    ].join(" · ");

    const hasRoute = (
      event.evidence?.includes("traceroute")
    );

    type.className = (
      "live-event-type"
      + (hasRoute ? " traceroute" : "")
    );

    type.textContent = (
      hasRoute
        ? "RouteDiscovery"
        : "Recepción observada"
    );

    button.append(name, metadata, type);

    button.addEventListener(
      "click",
      () => selectEvent(event)
    );

    item.append(button);
    fragment.append(item);
  }

  elements.eventList.replaceChildren(fragment);
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
      Math.max(state.map.getZoom(), 12)
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

function updateSummary() {
  const events = state.live.events;

  const traceroutes = events.filter(
    (event) => (
      event.evidence?.includes("traceroute")
    )
  ).length;

  elements.eventCount.textContent = (
    formatNumber(events.length)
  );

  elements.tracerouteCount.textContent = (
    formatNumber(traceroutes)
  );

  elements.liveWindow.textContent = (
    liveEventWindow(events)
  );

  updateVisibleEventSummary();
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
    state.map.setView([42.8, -8.3], 7);
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

async function loadBaseData() {
  const manifest = await fetchJson(MANIFEST_URL);

  validateManifest(manifest);

  const manifestUrl = new URL(
    MANIFEST_URL,
    window.location.href
  );

  const nodesUrl = new URL(
    manifest.documents["nodes.json"],
    manifestUrl
  );

  const nodes = await fetchJson(nodesUrl);

  validateNodes(nodes);

  state.nodes = nodes.nodes;
  state.nodeById = new Map(
    state.nodes.map(
      (node) => [node.id, node]
    )
  );

  renderNodes();
  setInitialBounds();
}

async function refreshLive() {
  elements.refresh.disabled = true;

  try {
    const live = await fetchJson(LIVE_URL);

    validateLive(live);

    state.live = live;

    updateEventLimitOptions();

    if (
      state.selectedEventId
      && !live.events.some(
        (event) => event.id === state.selectedEventId
      )
    ) {
      state.selectedEventId = null;
    }

    updateSummary();
    renderEvents();
    renderEventList();

    elements.status.textContent = (
      `Actualizado ${new Intl.DateTimeFormat(
        "gl-ES",
        {
          dateStyle: "short",
          timeStyle: "medium",
        }
      ).format(new Date(live.generated_at))}`
    );

    elements.error.hidden = true;
  } catch (error) {
    console.error(error);

    elements.error.textContent = (
      "Non foi posible actualizar o tráfico en directo. "
      + String(error.message || error)
    );

    elements.error.hidden = false;
    elements.status.textContent = "Erro de actualización";
  } finally {
    elements.refresh.disabled = false;
  }
}

function bindControls() {
  elements.nodeSearch.addEventListener(
    "input",
    renderNodeSearchResults
  );

  elements.eventLimit.addEventListener(
    "change",
    () => {
      if (
        state.selectedEventId
        && !visibleEvents().some(
          (event) => event.id === state.selectedEventId
        )
      ) {
        state.selectedEventId = null;
      }

      renderEvents();
      renderEventList();
      updateVisibleEventSummary();
    }
  );

  elements.showReceptions.addEventListener(
    "change",
    renderEvents
  );

  elements.showTraceroutes.addEventListener(
    "change",
    renderEvents
  );

  elements.refresh.addEventListener(
    "click",
    refreshLive
  );
}

async function initialize() {
  try {
    createMap();
    bindControls();
    initializeLiveMobileNavigation();

    await loadBaseData();
    await refreshLive();

    elements.loading.hidden = true;

    state.refreshTimer = window.setInterval(
      refreshLive,
      REFRESH_INTERVAL_MS
    );
  } catch (error) {
    console.error(error);

    elements.loading.hidden = true;

    elements.error.textContent = (
      "Non foi posible iniciar o mapa en directo. "
      + String(error.message || error)
    );

    elements.error.hidden = false;
    elements.status.textContent = "Erro de carga";
  }
}

initialize();
