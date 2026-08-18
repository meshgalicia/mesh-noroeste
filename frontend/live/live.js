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
  help: "Axuda",
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
  gatewaySelectionLayer: null,
  eventAnimationLayer: null,
  eventAnimationFrame: null,
  eventAnimationToken: 0,
  playbackActive: false,
  playbackToken: 0,
  playbackTimer: null,
  timelineRange: null,
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
  timelineBars: document.querySelector(
    "#live-timeline-bars"
  ),
  timelineStatus: document.querySelector(
    "#live-timeline-status"
  ),
  clearTimelineRange: document.querySelector(
    "#clear-timeline-range"
  ),
  eventGateway: document.querySelector(
    "#event-gateway"
  ),
  eventType: document.querySelector("#event-type"),
  eventAge: document.querySelector("#event-age"),
  eventLimit: document.querySelector("#event-limit"),
  showReceptions: document.querySelector(
    "#show-receptions"
  ),
  showTraceroutes: document.querySelector(
    "#show-traceroutes"
  ),
  toggleTraceroutePlayback: document.querySelector(
    "#toggle-traceroute-playback"
  ),
  playbackStatus: document.querySelector(
    "#playback-status"
  ),
  selectedEventCard: document.querySelector(
    "#selected-event-card"
  ),
  selectedEventCardClose: document.querySelector(
    "#selected-event-card-close"
  ),
  selectedEventCardRoute: document.querySelector(
    "#selected-event-card-route"
  ),
  selectedEventCardMeta: document.querySelector(
    "#selected-event-card-meta"
  ),
  selectedEventCardEvidence: document.querySelector(
    "#selected-event-card-evidence"
  ),
  selectedEventCardTowards: document.querySelector(
    "#selected-event-card-towards"
  ),
  selectedEventCardBack: document.querySelector(
    "#selected-event-card-back"
  ),
  selectedEventCardObservations: document.querySelector(
    "#selected-event-card-observations"
  ),
  selectedEventCardObservationsSummary: document.querySelector(
    "#selected-event-card-observations-summary"
  ),
  selectedEventCardObservationsContent: document.querySelector(
    "#selected-event-card-observations-content"
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
  liveMap: document.querySelector("#live-map"),
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
      "aria-labelledby",
      "live-mobile-sheet-title"
    );

    elements.liveMap.inert = true;
  } else {
    elements.sidebar.removeAttribute("role");
    elements.sidebar.removeAttribute(
      "aria-labelledby"
    );

    elements.liveMap.inert = false;
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

function clearNodeSelection({
  clearSearch = false,
} = {}) {
  state.selectedNodeId = null;
  state.nodeSearchSelectionLayer?.clearLayers();

  if (!clearSearch) {
    return;
  }

  elements.nodeSearch.value = "";
  elements.nodeSearchResults.replaceChildren();
  elements.nodeSearchResults.hidden = true;
  elements.nodeSearchStatus.textContent = "";
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
    clearNodeSelection();

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

  state.map.createPane("live-animation");
  state.map.getPane(
    "live-animation"
  ).style.zIndex = "480";
  state.map.getPane(
    "live-animation"
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

  state.gatewaySelectionLayer = (
    L.layerGroup().addTo(state.map)
  );

  state.eventAnimationLayer = (
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
        interactive: false,
      }
    ).addTo(state.eventLayer);

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
      }
    )
      .bindTooltip(
        eventTooltip(
          event,
          "Paquete observado por gateway"
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

function eventDistanceFromMapPoint(
  event,
  containerPoint
) {
  let minimum = Number.POSITIVE_INFINITY;

  for (const route of traceroutePaths(event)) {
    const points = route.nodeIds
      .map(nodePoint)
      .filter(Boolean)
      .map(
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


function nearestTracerouteEvent(
  containerPoint
) {
  const threshold = (
    isLiveMobileLayout()
      ? 26
      : 16
  );

  let nearest = null;
  let nearestDistance = threshold;

  for (const event of visibleEvents()) {
    if (!event.traceroute) {
      continue;
    }

    const distance = eventDistanceFromMapPoint(
      event,
      containerPoint
    );

    if (distance > nearestDistance) {
      continue;
    }

    nearest = event;
    nearestDistance = distance;
  }

  return nearest;
}

function nearestReceptionEvent(
  containerPoint
) {
  const threshold = (
    isLiveMobileLayout()
      ? 26
      : 16
  );

  let nearest = null;
  let nearestDistance = threshold;

  for (const event of visibleEvents()) {
    const distance = receptionDistanceFromMapPoint(
      event,
      containerPoint
    );

    if (distance > nearestDistance) {
      continue;
    }

    nearest = event;
    nearestDistance = distance;
  }

  return {
    event: nearest,
    distance: nearestDistance,
  };
}


function nearestMapEvent(
  containerPoint
) {
  let nearest = null;
  let nearestDistance = Number.POSITIVE_INFINITY;

  if (elements.showTraceroutes.checked) {
    const event = nearestTracerouteEvent(
      containerPoint
    );

    if (event) {
      const distance = eventDistanceFromMapPoint(
        event,
        containerPoint
      );

      nearest = event;
      nearestDistance = distance;
    }
  }

  if (elements.showReceptions.checked) {
    const reception = nearestReceptionEvent(
      containerPoint
    );

    if (
      reception.event
      && reception.distance < nearestDistance
    ) {
      nearest = reception.event;
    }
  }

  return nearest;
}


function initializeRouteMapSelection() {
  state.map.on(
    "click",
    (mapEvent) => {
      clearNodeSelection({
        clearSearch: true,
      });

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

function selectedEvent() {
  if (!state.selectedEventId || !state.live) {
    return null;
  }

  return state.live.events.find(
    (event) => event.id === state.selectedEventId
  ) || null;
}


function selectedEventGatewaySummary(event) {
  const ids = gatewayIds(event);

  if (ids.length === 0) {
    return "Sen gateways observadores";
  }

  const names = ids
    .slice(0, 3)
    .map(
      (gatewayId) => nodeNameById(gatewayId)
    );

  if (ids.length > 3) {
    names.push(`+${ids.length - 3}`);
  }

  return names.join(" · ");
}


function formatRadioMetric(
  value,
  {
    suffix,
    signed = false,
  }
) {
  const number = Number(value);

  if (!Number.isFinite(number)) {
    return "—";
  }

  const formatted = new Intl.NumberFormat(
    "gl-ES",
    {
      maximumFractionDigits: 1,
      minimumFractionDigits: Number.isInteger(number) ? 0 : 1,
      signDisplay: signed ? "exceptZero" : "auto",
    }
  ).format(number);

  return `${formatted} ${suffix}`;
}


function gatewayRadioSummary(gateway) {
  const rssi = Number(gateway?.rssi_dbm);
  const snr = Number(gateway?.snr_db);

  /*
   * Algúns rexistros propios/orixe chegan como 0/0.
   * Non os presentamos como unha medida radio real.
   */
  if (rssi === 0 && snr === 0) {
    return "RSSI — · SNR —";
  }

  return (
    `RSSI ${formatRadioMetric(rssi, { suffix: "dBm" })}`
    + " · "
    + `SNR ${formatRadioMetric(
      snr,
      {
        suffix: "dB",
        signed: true,
      }
    )}`
  );
}


function observationStageLabel(stage) {
  const hopStart = Number(stage?.hop_start);
  const hopLimit = Number(stage?.hop_limit);

  if (
    !Number.isFinite(hopStart)
    || !Number.isFinite(hopLimit)
  ) {
    return "";
  }

  return `Hop limit: ${hopStart} → ${hopLimit}`;
}


function renderSelectedEventObservations(event) {
  const details = (
    elements.selectedEventCardObservations
  );

  const container = (
    elements.selectedEventCardObservationsContent
  );

  container.replaceChildren();

  const stages = event?.observed?.stages || [];

  if (stages.length === 0) {
    details.hidden = true;
    details.open = false;
    return;
  }

  const gatewayCount = gatewayIds(event).length;
  const stageCount = stages.length;

  elements.selectedEventCardObservationsSummary.textContent = (
    "Observacións · "
    + `${gatewayCount} `
    + (gatewayCount === 1 ? "gateway" : "gateways")
    + " · "
    + `${stageCount} `
    + (stageCount === 1 ? "etapa" : "etapas")
  );

  const fragment = document.createDocumentFragment();

  for (const stage of stages) {
    const block = document.createElement("div");
    const stageMeta = document.createElement("strong");

    block.className = "live-selected-event-stage";
    stageMeta.className = "live-selected-event-stage-meta";
    stageMeta.textContent = (
      observationStageLabel(stage)
      || "Observación"
    );

    block.append(stageMeta);

    for (const gateway of stage.gateways || []) {
      const row = document.createElement("div");
      const name = document.createElement("span");
      const radio = document.createElement("span");

      row.className = "live-selected-event-gateway";

      name.className = "live-selected-event-gateway-name";
      name.textContent = nodeNameById(
        gateway.gateway_id
      );

      radio.className = "live-selected-event-gateway-radio";
      radio.textContent = gatewayRadioSummary(
        gateway
      );

      row.append(name, radio);
      block.append(row);
    }

    fragment.append(block);
  }

  container.append(fragment);

  /*
   * Cada novo evento empeza co detalle técnico pechado.
   * A información principal da ruta segue visible na ficha.
   */
  details.open = false;
  details.hidden = false;
}


function traceroutePathLabel(
  nodeIds,
  label
) {
  if (!Array.isArray(nodeIds) || nodeIds.length < 2) {
    return null;
  }

  const names = nodeIds.map(
    (nodeId) => nodeNameById(nodeId)
  );

  return `${label}: ${names.join(" → ")}`;
}


function tracerouteHopSummary(event) {
  const traceroute = event?.traceroute;

  if (!traceroute) {
    return "";
  }

  const towardsHops = Math.max(
    0,
    (traceroute.towards?.length || 0) - 1
  );

  const backHops = Math.max(
    0,
    (traceroute.back?.length || 0) - 1
  );

  const parts = [];

  if (traceroute.towards?.length >= 2) {
    parts.push(
      `ida ${towardsHops} `
      + (towardsHops === 1 ? "salto" : "saltos")
    );
  }

  if (traceroute.back?.length >= 2) {
    parts.push(
      `volta ${backHops} `
      + (backHops === 1 ? "salto" : "saltos")
    );
  } else {
    parts.push("volta non dispoñible");
  }

  return parts.join(" · ");
}


function renderSelectedEventCard() {
  const event = selectedEvent();

  if (!event) {
    elements.selectedEventCard.hidden = true;
    elements.selectedEventCardTowards.hidden = true;
    elements.selectedEventCardBack.hidden = true;
    elements.selectedEventCardObservations.hidden = true;
    elements.selectedEventCardObservations.open = false;
    elements.selectedEventCardObservationsContent.replaceChildren();
    return;
  }

  const hasTraceroute = Boolean(
    event.evidence?.includes("traceroute")
    || event.traceroute
  );

  elements.selectedEventCardRoute.textContent = [
    eventOriginName(event),
    "→",
    eventDestinationName(event),
  ].join(" ");

  elements.selectedEventCardMeta.textContent = [
    formatEventTime(event),
    event.channel || "Canal descoñecido",
    `portnum ${event.portnum}`,
    `${gatewayIds(event).length} gateway(s)`,
  ].join(" · ");

  elements.selectedEventCardEvidence.textContent = (
    hasTraceroute
      ? (
          "RouteDiscovery · "
          + tracerouteHopSummary(event)
          + " · percorrido indicado polo paquete"
        )
      : (
          "Paquete observado · "
          + selectedEventGatewaySummary(event)
        )
  );

  const towardsLabel = (
    hasTraceroute
      ? traceroutePathLabel(
          event.traceroute?.towards,
          "Ida"
        )
      : null
  );

  const backLabel = (
    hasTraceroute
      ? traceroutePathLabel(
          event.traceroute?.back,
          "Volta"
        )
      : null
  );

  elements.selectedEventCardTowards.hidden = (
    !towardsLabel
  );
  elements.selectedEventCardTowards.textContent = (
    towardsLabel || ""
  );

  elements.selectedEventCardBack.hidden = (
    !backLabel
  );
  elements.selectedEventCardBack.textContent = (
    backLabel || ""
  );

  renderSelectedEventObservations(event);

  elements.selectedEventCard.hidden = false;
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
        pane: "live-selection",
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

function selectedEventAnimationSegments(event) {
  const segments = [];

  for (const route of traceroutePaths(event)) {
    const points = route.nodeIds
      .map(nodePoint)
      .filter(Boolean);

    for (let index = 0; index < points.length - 1; index += 1) {
      const from = points[index];
      const to = points[index + 1];

      const length = state.map.distance(from, to);

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
      });
    }
  }

  return segments;
}

function animationPointAtDistance(
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

function receptionAnimationSegments(event) {
  const origin = nodePoint(event.from_id);

  if (!origin) {
    return [];
  }

  const segments = [];

  for (const gatewayId of gatewayIds(event)) {
    if (gatewayId === event.from_id) {
      continue;
    }

    const gateway = nodePoint(gatewayId);

    if (!gateway) {
      continue;
    }

    const length = state.map.distance(
      origin,
      gateway
    );

    if (
      !Number.isFinite(length)
      || length <= 0
    ) {
      continue;
    }

    segments.push({
      from: origin,
      to: gateway,
      length,
    });
  }

  return segments;
}


function animateSelectedReception(event) {
  cancelSelectedEventAnimation();

  if (
    !event
    || event.traceroute
    || !elements.showReceptions.checked
    || prefersReducedMotion()
  ) {
    return;
  }

  const segments = receptionAnimationSegments(
    event
  );

  if (segments.length === 0) {
    return;
  }

  const movementDuration = 1_600;
  const pauseDuration = 450;
  const cycleDuration = (
    movementDuration + pauseDuration
  );

  const marker = L.circleMarker(
    segments[0].from,
    {
      pane: "live-animation",
      radius: 6.5,
      color: "#075d68",
      weight: 3,
      opacity: 1,
      fillColor: "#bfe8ee",
      fillOpacity: 1,
      interactive: false,
    }
  ).addTo(state.eventAnimationLayer);

  const token = state.eventAnimationToken;
  let startedAt = null;
  let previousSegmentIndex = -1;

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

    const completedCycles = Math.floor(
      elapsed / cycleDuration
    );

    const segmentIndex = (
      completedCycles % segments.length
    );

    const cycleElapsed = (
      elapsed % cycleDuration
    );

    const segment = segments[segmentIndex];

    if (segmentIndex !== previousSegmentIndex) {
      previousSegmentIndex = segmentIndex;

      marker.setLatLng(
        segment.from
      );
    }

    const progress = (
      cycleElapsed >= movementDuration
        ? 1
        : cycleElapsed / movementDuration
    );

    const point = animationPointAtDistance(
      [segment],
      segment.length * progress
    );

    if (point) {
      marker.setLatLng(point);
    }

    state.eventAnimationFrame = (
      window.requestAnimationFrame(frame)
    );
  };

  state.eventAnimationFrame = (
    window.requestAnimationFrame(frame)
  );
}


function animateSelectedEvent(event) {
  cancelSelectedEventAnimation();

  if (
    !event
    || !event.traceroute
    || !elements.showTraceroutes.checked
    || prefersReducedMotion()
  ) {
    return;
  }

  const segments = selectedEventAnimationSegments(
    event
  );

  if (segments.length === 0) {
    return;
  }

  const totalDistance = segments.reduce(
    (total, segment) => total + segment.length,
    0
  );

  if (!Number.isFinite(totalDistance) || totalDistance <= 0) {
    return;
  }

  const movementDuration = Math.max(
    2_500,
    Math.min(
      9_000,
      segments.length * 900
    )
  );

  const pauseDuration = 900;
  const cycleDuration = (
    movementDuration + pauseDuration
  );

  const marker = L.circleMarker(
    segments[0].from,
    {
      pane: "live-animation",
      radius: 5.5,
      color: "#17201d",
      weight: 2.5,
      opacity: 1,
      fillColor: "#ffffff",
      fillOpacity: 1,
      interactive: false,
    }
  ).addTo(state.eventAnimationLayer);

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
    const cycleElapsed = (
      elapsed % cycleDuration
    );

    const progress = (
      cycleElapsed >= movementDuration
        ? 1
        : cycleElapsed / movementDuration
    );

    const point = animationPointAtDistance(
      segments,
      totalDistance * progress
    );

    if (point) {
      marker.setLatLng(point);
    }

    state.eventAnimationFrame = (
      window.requestAnimationFrame(frame)
    );
  };

  state.eventAnimationFrame = (
    window.requestAnimationFrame(frame)
  );
}

function playbackTracerouteEvents() {
  return filteredEventsByAge()
    .filter(
      (event) => (
        Boolean(event.traceroute)
        && selectedEventAnimationSegments(event).length > 0
      )
    )
    .sort(
      (left, right) => (
        Number(left.imported_at_us)
        - Number(right.imported_at_us)
      )
    );
}


function updatePlaybackControls() {
  const playable = (
    playbackTracerouteEvents().length > 0
  );

  elements.toggleTraceroutePlayback.disabled = (
    !playable && !state.playbackActive
  );

  elements.toggleTraceroutePlayback.textContent = (
    state.playbackActive
      ? "⏸ Pausar"
      : "▶ Reproducir"
  );

  elements.toggleTraceroutePlayback.setAttribute(
    "aria-pressed",
    String(state.playbackActive)
  );

  if (state.playbackActive) {
    return;
  }

  if (playable) {
    elements.playbackStatus.textContent = "Detido";
    return;
  }

  elements.playbackStatus.textContent = (
    state.timelineRange
      ? "Non hai RouteDiscovery neste intervalo"
      : "Non hai RouteDiscovery cos filtros actuais"
  );
}

function stopTraceroutePlayback({
  clearSelection = false,
} = {}) {
  state.playbackActive = false;
  state.playbackToken += 1;

  if (state.playbackTimer !== null) {
    window.clearTimeout(
      state.playbackTimer
    );
    state.playbackTimer = null;
  }

  cancelSelectedEventAnimation();

  if (clearSelection) {
    state.selectedEventId = null;
    renderEvents();
    renderEventList();
  }

  elements.playbackStatus.textContent = (
    "Reprodución detida"
  );

  updatePlaybackControls();
}

function animateEventOnce(
  event,
  onComplete
) {
  cancelSelectedEventAnimation();

  const segments = selectedEventAnimationSegments(
    event
  );

  if (
    segments.length === 0
    || prefersReducedMotion()
  ) {
    onComplete();
    return;
  }

  const totalDistance = segments.reduce(
    (total, segment) => total + segment.length,
    0
  );

  if (!Number.isFinite(totalDistance) || totalDistance <= 0) {
    onComplete();
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
      pane: "live-animation",
      radius: 5.5,
      color: "#17201d",
      weight: 2.5,
      opacity: 1,
      fillColor: "#ffffff",
      fillOpacity: 1,
      interactive: false,
    }
  ).addTo(state.eventAnimationLayer);

  const animationToken = state.eventAnimationToken;
  let startedAt = null;

  const frame = (timestamp) => {
    if (
      animationToken !== state.eventAnimationToken
      || !state.playbackActive
    ) {
      return;
    }

    if (startedAt === null) {
      startedAt = timestamp;
    }

    const elapsed = timestamp - startedAt;
    const progress = Math.min(
      1,
      elapsed / movementDuration
    );

    const point = animationPointAtDistance(
      segments,
      totalDistance * progress
    );

    if (point) {
      marker.setLatLng(point);
    }

    if (progress >= 1) {
      state.eventAnimationFrame = null;

      state.playbackTimer = window.setTimeout(
        onComplete,
        700
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

function runTraceroutePlayback(
  events,
  index,
  playbackToken
) {
  if (
    !state.playbackActive
    || playbackToken !== state.playbackToken
  ) {
    return;
  }

  if (index >= events.length) {
    stopTraceroutePlayback();
    return;
  }

  const event = events[index];

  state.selectedEventId = event.id;

  renderEvents();
  renderEventList();
  renderSelectedEventCard();

  elements.playbackStatus.textContent = (
    `Reproducindo ${index + 1} de ${events.length}: `
    + `${eventOriginName(event)} → ${eventDestinationName(event)}`
  );

  let started = false;

  const start = () => {
    if (
      started
      || !state.playbackActive
      || playbackToken !== state.playbackToken
    ) {
      return;
    }

    started = true;

    animateEventOnce(
      event,
      () => {
        runTraceroutePlayback(
          events,
          index + 1,
          playbackToken
        );
      }
    );
  };

  state.map.once(
    "moveend",
    start
  );

  focusEvent(event);

  window.setTimeout(
    () => {
      if (
        state.playbackActive
        && playbackToken === state.playbackToken
        && state.eventAnimationLayer.getLayers().length === 0
      ) {
        start();
      }
    },
    500
  );
}

function startTraceroutePlayback() {
  const events = playbackTracerouteEvents();

  if (events.length === 0) {
    elements.playbackStatus.textContent = (
      state.timelineRange
        ? "Non hai RouteDiscovery neste intervalo"
        : "Non hai RouteDiscovery cos filtros actuais"
    );
    updatePlaybackControls();
    return;
  }

  stopTraceroutePlayback();

  state.playbackActive = true;
  state.playbackToken += 1;

  const token = state.playbackToken;

  updatePlaybackControls();

  runTraceroutePlayback(
    events,
    0,
    token
  );
}

function syncSelectedEventAnimation() {
  if (state.playbackActive) {
    return;
  }

  const event = selectedVisibleEvent();

  if (!event) {
    cancelSelectedEventAnimation();
    return;
  }

  if (event.traceroute) {
    animateSelectedEvent(event);
    return;
  }

  animateSelectedReception(event);
}

function selectEvent(event) {
  clearNodeSelection({
    clearSearch: true,
  });

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
  renderSelectedEventCard();

  if (alreadySelected) {
    syncSelectedEventAnimation();
    return;
  }

  const startAnimation = () => {
    syncSelectedEventAnimation();
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


function eventHasGateway(event, gatewayId) {
  if (!gatewayId || gatewayId === "all") {
    return true;
  }

  return gatewayIds(event).includes(gatewayId);
}

function focusGateway(gatewayId) {
  if (!gatewayId || gatewayId === "all") {
    return;
  }

  const point = nodePoint(gatewayId);

  if (!point) {
    return;
  }

  state.map.setView(
    point,
    Math.max(state.map.getZoom(), 13)
  );
}

function renderGatewaySelection() {
  state.gatewaySelectionLayer.clearLayers();

  const gatewayId = elements.eventGateway.value;

  if (!gatewayId || gatewayId === "all") {
    return;
  }

  const point = nodePoint(gatewayId);

  if (!point) {
    return;
  }

  const node = state.nodeById.get(gatewayId);

  const name = (
    node?.long_name
    || node?.short_name
    || gatewayId
  );

  L.circleMarker(
    point,
    {
      pane: "live-selection",
      radius: 11,
      color: "#0b7285",
      weight: 4,
      opacity: 1,
      fillColor: "#ffffff",
      fillOpacity: 0.2,
      interactive: false,
    }
  )
    .bindTooltip(
      `<strong>${escapeHtml(name)}</strong>`
      + `<br><span>Gateway filtrado</span>`,
      {
        permanent: true,
        direction: "top",
        offset: [0, -12],
        className: "live-selected-gateway-label",
      }
    )
    .addTo(state.gatewaySelectionLayer);
}

function eventMatchesType(event) {
  const type = elements.eventType.value;

  if (type === "all") {
    return true;
  }

  const hasTraceroute = Boolean(
    event.evidence?.includes("traceroute")
    || event.traceroute
  );

  if (type === "traceroute") {
    return hasTraceroute;
  }

  if (type === "reception") {
    return !hasTraceroute;
  }

  return true;
}

function filteredEventsByType() {
  return state.live.events.filter(
    eventMatchesType
  );
}

function filteredEventsByGateway() {
  const gatewayId = elements.eventGateway.value;
  const events = filteredEventsByType();

  if (gatewayId === "all") {
    return events;
  }

  return events.filter(
    (event) => eventHasGateway(event, gatewayId)
  );
}

function gatewayOptionLabel(gatewayId) {
  const node = state.nodeById.get(gatewayId);

  if (!node) {
    return gatewayId;
  }

  const name = (
    node.long_name
    || node.short_name
    || gatewayId
  );

  return `${name} · ${gatewayId}`;
}

function updateGatewayOptions() {
  const currentValue = elements.eventGateway.value;

  const gatewayIdsSet = new Set();

  for (const event of state.live?.events || []) {
    for (const gatewayId of gatewayIds(event)) {
      gatewayIdsSet.add(gatewayId);
    }
  }

  const gatewayIdsList = [...gatewayIdsSet].sort(
    (left, right) => (
      gatewayOptionLabel(left).localeCompare(
        gatewayOptionLabel(right),
        "gl"
      )
    )
  );

  const fragment = document.createDocumentFragment();

  const allOption = document.createElement("option");
  allOption.value = "all";
  allOption.textContent = (
    `Todos os gateways (${formatNumber(gatewayIdsList.length)})`
  );

  fragment.append(allOption);

  for (const gatewayId of gatewayIdsList) {
    const option = document.createElement("option");

    option.value = gatewayId;
    option.textContent = gatewayOptionLabel(gatewayId);

    fragment.append(option);
  }

  elements.eventGateway.replaceChildren(fragment);

  if (
    currentValue
    && (
      currentValue === "all"
      || gatewayIdsSet.has(currentValue)
    )
  ) {
    elements.eventGateway.value = currentValue;
  } else {
    elements.eventGateway.value = "all";
  }
}

function timelineBaseEvents() {
  return filteredEventsByGateway()
    .sort(
      (left, right) => (
        Number(left.imported_at_us)
        - Number(right.imported_at_us)
      )
    );
}


function timelineNewestTimestamp(events) {
  return events.reduce(
    (maximum, event) => Math.max(
      maximum,
      Number(event.imported_at_us) || 0
    ),
    0
  );
}


function timelineBuckets() {
  const events = timelineBaseEvents();
  const newestTimestamp = timelineNewestTimestamp(
    events
  );

  if (!newestTimestamp) {
    return [];
  }

  const bucketDurationUs = (
    5 * 60 * 1_000_000
  );

  const hourStart = (
    newestTimestamp
    - 60 * 60 * 1_000_000
  );

  const buckets = Array.from(
    { length: 12 },
    (_, index) => {
      const startUs = (
        hourStart
        + index * bucketDurationUs
      );

      const endUs = (
        startUs + bucketDurationUs
      );

      return {
        index,
        startUs,
        endUs,
        count: 0,
        tracerouteCount: 0,
      };
    }
  );

  for (const event of events) {
    const timestamp = Number(
      event.imported_at_us
    );

    if (
      !Number.isFinite(timestamp)
      || timestamp < hourStart
      || timestamp > newestTimestamp
    ) {
      continue;
    }

    const rawIndex = Math.floor(
      (timestamp - hourStart)
      / bucketDurationUs
    );

    const index = Math.min(
      11,
      Math.max(0, rawIndex)
    );

    buckets[index].count += 1;

    if (
      event.traceroute
      && selectedEventAnimationSegments(event).length > 0
    ) {
      buckets[index].tracerouteCount += 1;
    }
  }

  return buckets;
}


function formatTimelineClock(timestampUs) {
  return new Intl.DateTimeFormat(
    "gl-ES",
    {
      hour: "2-digit",
      minute: "2-digit",
    }
  ).format(
    new Date(timestampUs / 1000)
  );
}


function renderTimeline() {
  const buckets = timelineBuckets();

  if (buckets.length === 0) {
    elements.timelineBars.replaceChildren();
    elements.timelineStatus.textContent = (
      "Sen actividade dispoñible"
    );
    elements.clearTimelineRange.disabled = true;
    return;
  }

  const maximum = Math.max(
    1,
    ...buckets.map(
      (bucket) => bucket.count
    )
  );

  const fragment = document.createDocumentFragment();

  for (const bucket of buckets) {
    const button = document.createElement("button");

    button.type = "button";
    button.className = "live-timeline-bar";
    button.dataset.timelineIndex = String(
      bucket.index
    );

    const selected = Boolean(
      state.timelineRange
      && state.timelineRange.startUs === bucket.startUs
      && state.timelineRange.endUs === bucket.endUs
    );

    button.classList.toggle(
      "selected",
      selected
    );

    button.classList.toggle(
      "has-traceroute",
      bucket.tracerouteCount > 0
    );

    button.dataset.tracerouteCount = String(
      bucket.tracerouteCount
    );

    button.setAttribute(
      "aria-pressed",
      String(selected)
    );

    const percentage = (
      bucket.count === 0
        ? 4
        : Math.max(
            12,
            Math.round(
              bucket.count / maximum * 100
            )
          )
    );

    button.style.setProperty(
      "--timeline-level",
      `${percentage}%`
    );

    const startLabel = formatTimelineClock(
      bucket.startUs
    );

    const endLabel = formatTimelineClock(
      bucket.endUs
    );

    const eventLabel = (
      `${formatNumber(bucket.count)} evento`
      + (bucket.count === 1 ? "" : "s")
    );

    const tracerouteLabel = (
      bucket.tracerouteCount > 0
        ? (
            ` · ${formatNumber(bucket.tracerouteCount)} `
            + "RouteDiscovery reproducible"
            + (bucket.tracerouteCount === 1 ? "" : "s")
          )
        : ""
    );

    button.setAttribute(
      "aria-label",
      (
        `${startLabel}–${endLabel}: `
        + eventLabel
        + tracerouteLabel
      )
    );

    button.title = (
      `${startLabel}–${endLabel} · `
      + eventLabel
      + tracerouteLabel
    );

    button.addEventListener(
      "click",
      () => {
        state.timelineRange = {
          startUs: bucket.startUs,
          endUs: bucket.endUs,
        };

        /*
         * Un tramo da timeline pertence sempre á última hora.
         * Evitamos que un filtro previo de 5/15 minutos o oculte.
         */
        elements.eventAge.value = "60";

        refreshEventView();
        focusVisibleEvents();
      }
    );

    fragment.append(button);
  }

  elements.timelineBars.replaceChildren(
    fragment
  );

  elements.clearTimelineRange.disabled = (
    state.timelineRange === null
  );

  if (!state.timelineRange) {
    elements.timelineStatus.textContent = (
      "Sen intervalo seleccionado"
    );
    return;
  }

  elements.timelineStatus.textContent = (
    "Mostrando "
    + formatTimelineClock(
      state.timelineRange.startUs
    )
    + "–"
    + formatTimelineClock(
      state.timelineRange.endUs
    )
  );
}


function eventsInsideTimelineRange(events) {
  if (!state.timelineRange) {
    return events;
  }

  const {
    startUs,
    endUs,
  } = state.timelineRange;

  return events.filter(
    (event) => {
      const timestamp = Number(
        event.imported_at_us
      );

      return (
        timestamp >= startUs
        && timestamp < endUs
      );
    }
  );
}


function filteredEventsByAge() {
  const value = elements.eventAge.value;

  const events = filteredEventsByGateway()
    .sort(
      (left, right) => (
        Number(right.imported_at_us)
        - Number(left.imported_at_us)
      )
    );

  if (value === "all") {
    return eventsInsideTimelineRange(
      events
    );
  }

  const minutes = Number(value);

  if (!Number.isFinite(minutes)) {
    return eventsInsideTimelineRange(
      events
    );
  }

  const newestTimestamp = events.reduce(
    (maximum, event) => Math.max(
      maximum,
      Number(event.imported_at_us) || 0
    ),
    0
  );

  if (!newestTimestamp) {
    return eventsInsideTimelineRange(
      events
    );
  }

  const cutoff = (
    newestTimestamp
    - minutes * 60 * 1_000_000
  );

  return eventsInsideTimelineRange(
    events.filter(
      (event) => (
        Number(event.imported_at_us) >= cutoff
      )
    )
  );
}

function visibleEvents() {
  const value = elements.eventLimit.value;
  const events = filteredEventsByAge();

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

  const events = visibleEvents();
  const selectedEvent = (
    state.selectedEventId
      ? state.live.events.find(
          (event) => event.id === state.selectedEventId
        ) || null
      : null
  );

  const selectedEventId = selectedEvent?.id || null;

  if (
    selectedEvent
    && !events.some(
      (event) => event.id === selectedEvent.id
    )
  ) {
    events.push(selectedEvent);
  }

  for (const event of events) {
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
        : "Paquete observado"
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

function focusVisibleEvents() {
  const points = [];

  for (const event of visibleEvents()) {
    points.push(
      ...eventPoints(event)
    );
  }

  if (points.length === 0) {
    return;
  }

  if (points.length === 1) {
    state.map.setView(
      points[0],
      Math.max(
        state.map.getZoom(),
        11
      )
    );

    return;
  }

  state.map.fitBounds(
    points,
    {
      padding: [45, 45],
      maxZoom: 12,
    }
  );
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

    updateGatewayOptions();
    updateEventLimitOptions();
    renderGatewaySelection();

    if (
      state.selectedEventId
      && !visibleEvents().some(
        (event) => event.id === state.selectedEventId
      )
    ) {
      state.selectedEventId = null;
    }

    updateSummary();
    renderEvents();
    renderEventList();
    renderSelectedEventCard();
    renderTimeline();
    syncSelectedEventAnimation();
    updatePlaybackControls();

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

function clearSelectedEvent() {
  if (state.playbackActive) {
    stopTraceroutePlayback({
      clearSelection: true,
    });
  } else {
    state.selectedEventId = null;
    cancelSelectedEventAnimation();
    renderEvents();
    renderEventList();
  }

  renderSelectedEventCard();
}


function refreshEventView() {
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
  renderSelectedEventCard();
  updateVisibleEventSummary();
  renderTimeline();
  syncSelectedEventAnimation();
  updatePlaybackControls();
}


function bindControls() {
  elements.selectedEventCardClose.addEventListener(
    "click",
    clearSelectedEvent
  );

  elements.clearTimelineRange.addEventListener(
    "click",
    () => {
      state.timelineRange = null;
      elements.eventAge.value = "60";
      refreshEventView();
    }
  );

  elements.nodeSearch.addEventListener(
    "input",
    renderNodeSearchResults
  );

  const refreshEventFilters = () => {
    state.timelineRange = null;
    refreshEventView();
  };

  elements.eventType.addEventListener(
    "change",
    refreshEventFilters
  );

  elements.eventGateway.addEventListener(
    "change",
    () => {
      refreshEventFilters();
      renderGatewaySelection();

      focusGateway(
        elements.eventGateway.value
      );
    }
  );

  elements.eventAge.addEventListener(
    "change",
    refreshEventFilters
  );

  elements.eventLimit.addEventListener(
    "change",
    () => {
      refreshEventFilters();
    }
  );

  elements.showReceptions.addEventListener(
    "change",
    renderEvents
  );

  elements.showTraceroutes.addEventListener(
    "change",
    () => {
      stopTraceroutePlayback();
      renderEvents();
      syncSelectedEventAnimation();
      updatePlaybackControls();
    }
  );

  elements.toggleTraceroutePlayback.addEventListener(
    "click",
    () => {
      if (state.playbackActive) {
        stopTraceroutePlayback();
        return;
      }

      startTraceroutePlayback();
    }
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
    initializeRouteMapSelection();

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
