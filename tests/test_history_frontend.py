"""Probas estruturais do frontend histórico."""

from __future__ import annotations

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parent.parent


class HistoryFrontendTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.html = (
            ROOT / "frontend/history/index.html"
        ).read_text(encoding="utf-8")

        cls.javascript = (
            ROOT / "frontend/history/history.js"
        ).read_text(encoding="utf-8")

        cls.css = (
            ROOT / "frontend/history/history.css"
        ).read_text(encoding="utf-8")


    def test_history_has_independent_entrypoint(
        self,
    ) -> None:
        for expected in (
            "<title>Histórico de tráfico · Mesh Noroeste</title>",
            'id="history-map"',
            "./history.css?v=20260819-history3",
            "./history.js?v=20260819-history3",
            "../live/",
        ):
            self.assertIn(
                expected,
                self.html,
            )


    def test_history_uses_public_manifest_for_nodes(
        self,
    ) -> None:
        for expected in (
            'const MANIFEST_URL = "../data/manifest.json"',
            '"mesh-noroeste.manifest/v1"',
            'manifest.documents["nodes.json"]',
            "state.nodeById = new Map(",
            "function nodePoint(nodeId)",
        ):
            self.assertIn(
                expected,
                self.javascript,
            )


    def test_history_uses_history_manifest(
        self,
    ) -> None:
        for expected in (
            '"../data/history/manifest.json"',
            '"mesh-noroeste.history-manifest/v1"',
            "function validateHistoryManifest(document)",
            "state.manifest.hours",
            "function availableDays()",
            "function hoursForDay(day)",
        ):
            self.assertIn(
                expected,
                self.javascript,
            )


    def test_history_loads_hour_documents(
        self,
    ) -> None:
        for expected in (
            '"mesh-noroeste.history-hour/v1"',
            "async function loadHour(hour)",
            '"../data/history/"',
            "hour.path",
            "validateHistoryHour(",
            "state.hourDocument = document",
        ):
            self.assertIn(
                expected,
                self.javascript,
            )


    def test_history_has_day_and_hour_controls(
        self,
    ) -> None:
        for expected in (
            'id="history-day"',
            'id="history-hour"',
            'id="history-latest"',
            "renderHourOptions(",
            "selectLatestHour()",
        ):
            self.assertIn(
                expected,
                self.html + self.javascript,
            )


    def test_history_period_reports_loaded_hour(
        self,
    ) -> None:
        for expected in (
            'id="history-period-status"',
            "Bloque mostrado: —",
            "<span>Día (UTC)</span>",
            "<span>Hora</span>",
            'periodStatus: document.querySelector(',
            '"#history-period-status"',
            "const periodLabel = (",
            '"Bloque mostrado: "',
            "elements.periodStatus.textContent",
            ".history-period-status",
        ):
            self.assertIn(
                expected,
                self.html
                + self.javascript
                + self.css,
            )


    def test_history_has_daily_activity_timeline(
        self,
    ) -> None:
        for expected in (
            'id="history-day-timeline-bars"',
            'id="history-day-timeline-status"',
            'id="history-day-timeline-tooltip"',
            "Actividade do día",
            "function hourForDayAndNumber(",
            "function showDayTimelineTooltip(",
            "function hideDayTimelineTooltip()",
            "const activityLabel = (",
            '"mouseenter"',
            '"focus"',
            '"pointerdown"',
            "function renderDayTimeline()",
            "for (",
            "hourNumber < 24",
            "Number(hour.events)",
            "Number(hour.traceroutes)",
            '"has-traceroute"',
            '"selected"',
            "await selectManifestHour(hour);",
            "renderDayTimeline();",
            ".history-day-timeline",
            ".history-day-timeline-bars",
            ".history-day-timeline-bar",
            ".history-day-timeline-bar.has-traceroute",
            ".history-day-timeline-tooltip",
        ):
            self.assertIn(
                expected,
                self.html
                + self.javascript
                + self.css,
            )


    def test_history_daily_timeline_returns_to_map_on_mobile(
        self,
    ) -> None:
        start = self.javascript.index(
            "function renderDayTimeline()"
        )

        end = self.javascript.index(
            "\n\nfunction nodeHistoryHourKeys(",
            start,
        )

        block = self.javascript[start:end]

        for expected in (
            "await selectManifestHour(hour);",
            "if (isHistoryMobileLayout())",
            "setHistoryMobilePanel(null);",
        ):
            self.assertIn(
                expected,
                block,
            )


    def test_history_can_navigate_adjacent_hours(
        self,
    ) -> None:
        for expected in (
            'id="history-previous"',
            'id="history-next"',
            "function selectedHourIndex()",
            "async function selectManifestHour(hour)",
            "async function selectAdjacentHour(offset)",
            "await selectAdjacentHour(-1)",
            "await selectAdjacentHour(1)",
            "index === 0",
            "index === state.manifest.hours.length - 1",
        ):
            self.assertIn(
                expected,
                self.html
                + self.javascript,
            )


    def test_history_can_show_routes(
        self,
    ) -> None:
        for expected in (
            "function traceroutePaths(event)",
            "function addTraceroute(",
            "event.traceroute",
            'id="history-routes-only"',
            '"RouteDiscovery"',
        ):
            self.assertIn(
                expected,
                self.html + self.javascript,
            )


    def test_history_is_responsive(
        self,
    ) -> None:
        for expected in (
            "@media (max-width: 760px)",
            ".history-map-region",
            ".history-period-grid",
        ):
            self.assertIn(
                expected,
                self.css,
            )


    def test_history_mobile_toolbar_exists(
        self,
    ) -> None:
        for expected in (
            'id="history-mobile-backdrop"',
            "history-mobile-toolbar",
            'data-history-mobile-target="search"',
            'data-history-mobile-target="period"',
            'data-history-mobile-target="events"',
            'data-history-mobile-target="info"',
            "initializeHistoryMobileNavigation()",
            "function setHistoryMobilePanel(panel)",
        ):
            self.assertIn(
                expected,
                self.html
                + self.javascript
                + self.css,
            )


    def test_history_mobile_panels_exist(
        self,
    ) -> None:
        for expected in (
            'data-history-mobile-panel="search"',
            'data-history-mobile-panel="period"',
            'data-history-mobile-panel="events"',
            'data-history-mobile-panel="info"',
            "body.history-mobile-panel-open",
            ".history-sidebar",
            ".history-mobile-backdrop",
            ".history-mobile-toolbar",
        ):
            self.assertIn(
                expected,
                self.html + self.css,
            )


    def test_latest_button_reports_current_state(
        self,
    ) -> None:
        for expected in (
            "function updateLatestButtonState()",
            '"Xa estás na máis recente"',
            '"Ir á máis recente"',
            "state.selectedHour?.key === latest.key",
        ):
            self.assertIn(
                expected,
                self.javascript,
            )


    def test_history_uses_live_cartographic_semantics(
        self,
    ) -> None:
        for expected in (
            "function addTraceroute(",
            'route.key === "back"',
            '? "#087f8c"',
            ': "#5f3dc4"',
            'dashArray: (',
            '? "8 5"',
            "function gatewayIds(event)",
            "function addGatewayObservations(",
            'selected ? "5 5" : "4 6"',
            "function eventPoints(event)",
            "function focusEvent(event)",
        ):
            self.assertIn(
                expected,
                self.javascript,
            )


    def test_history_focus_uses_observed_evidence(
        self,
    ) -> None:
        start = self.javascript.index(
            "function eventPoints(event)"
        )
        end = self.javascript.index(
            "function focusEvent(event)",
            start,
        )

        code = self.javascript[start:end]

        self.assertIn(
            "traceroutePaths(event)",
            code,
        )
        self.assertIn(
            "nodePoint(event.from_id)",
            code,
        )
        self.assertIn(
            "gatewayIds(event)",
            code,
        )
        self.assertNotIn(
            "nodePoint(event.to_id)",
            code,
        )


    def test_history_selected_event_has_map_card(
        self,
    ) -> None:
        for expected in (
            'id="history-selected-event-card"',
            'id="history-selected-event-close"',
            'id="history-selected-event-route"',
            'id="history-selected-event-meta"',
            'id="history-selected-event-state"',
            'id="history-selected-event-evidence"',
            'id="history-selected-event-route-details"',
            'id="history-selected-event-route-summary"',
            'id="history-selected-event-towards"',
            'id="history-selected-event-back"',
            "function historyTraceroutePathText(",
            '"Ida"',
            '"Volta"',
            "Percorrido da ruta",
            ".history-selected-event-route-details",
            ".history-selected-event-path",
            "function selectedHistoryEvent()",
            "function historyTracerouteSummary(event)",
            "function renderSelectedEventCard()",
            "function clearSelectedEvent()",
            "renderSelectedEventCard();",
            "Faltan posicións para representar todo o percorrido",
            ".history-selected-event-card",
            ".history-selected-event-close",
        ):
            self.assertIn(
                expected,
                self.html
                + self.javascript
                + self.css,
            )


    def test_history_selected_event_reports_route_state(
        self,
    ) -> None:
        for expected in (
            "function historyEventState(event)",
            '"Só observación"',
            '"Sen percorrido"',
            '"Percorrido parcial"',
            '"Percorrido dispoñible"',
            "eventHasTraceroutePath(event)",
            "eventHasPartialTraceroute(event)",
            "eventHasDrawableTraceroute(event)",
            '"history-selected-event-state "',
            ".history-selected-event-state",
            ".state-complete",
            ".state-partial",
            ".state-empty",
            ".state-observed",
        ):
            self.assertIn(
                expected,
                self.html + self.javascript + self.css,
            )


    def test_history_mobile_event_selection_returns_to_map(
        self,
    ) -> None:
        for expected in (
            "if (isHistoryMobileLayout())",
            "setHistoryMobilePanel(null);",
        ):
            self.assertIn(
                expected,
                self.javascript,
            )


    def test_selected_history_route_matches_live_semantics(
        self,
    ) -> None:
        add_start = self.javascript.index(
            "function addTraceroute("
        )

        add_end = self.javascript.index(
            "\nfunction gatewayIds(",
            add_start,
        )

        add_code = self.javascript[
            add_start:add_end
        ]

        for expected in (
            'pane: "history-routes"',
            'selected',
            '"#a61e4d"',
            'route.key === "back"',
            '"8 5"',
            'state.eventLayer',
        ):
            self.assertIn(
                expected,
                add_code,
            )

        selection_start = self.javascript.index(
            "function renderEventSelection()"
        )

        selection_end = self.javascript.index(
            "\n\nfunction eventPoints(",
            selection_start,
        )

        selection_code = self.javascript[
            selection_start:selection_end
        ]

        for expected in (
            'pane: "history-selection"',
            "eventNodeIds(event)",
            "state.selectionLayer",
            "radius: 8",
            "weight: 3",
        ):
            self.assertIn(
                expected,
                selection_code,
            )

        self.assertNotIn(
            'pane: selected',
            add_code,
        )


    def test_history_distinguishes_route_renderability(
        self,
    ) -> None:
        for expected in (
            "function eventHasTraceroutePath(event)",
            "route.nodeIds.length >= 2",
            "function eventHasDrawableTraceroute(event)",
            "function routePointSegments(route)",
            "routePointSegments(route).length > 0",
            "if (!point)",
            "current = [];",
        ):
            self.assertIn(
                expected,
                self.javascript,
            )

    def test_selected_history_route_can_animate_once(
        self,
    ) -> None:
        for expected in (
            "eventAnimationLayer: null",
            "eventAnimationFrame: null",
            "eventAnimationToken: 0",
            '"history-animation"',
            "function prefersReducedMotion()",
            "function cancelSelectedEventAnimation()",
            "function selectedHistoryEventAnimationSegments(event)",
            "function historyAnimationPointAtDistance(",
            "function animateSelectedHistoryEventOnce(event)",
            "window.requestAnimationFrame(frame)",
            "window.cancelAnimationFrame(",
            '"(prefers-reduced-motion: reduce)"',
            "state.selectedEventId !== event.id",
            "state.eventAnimationLayer.clearLayers()",
            "animateSelectedHistoryEventOnce(event)",
        ):
            self.assertIn(
                expected,
                self.javascript,
            )


    def test_history_animation_does_not_bridge_missing_nodes(
        self,
    ) -> None:
        start = self.javascript.index(
            "function selectedHistoryEventAnimationSegments(event)"
        )

        end = self.javascript.index(
            "\n\nfunction historyAnimationPointAtDistance(",
            start,
        )

        block = self.javascript[start:end]

        self.assertIn(
            "routePointSegments(route)",
            block,
        )

        self.assertNotIn(
            ".filter(Boolean)",
            block,
        )


    def test_history_marks_partial_routes(
        self,
    ) -> None:
        for expected in (
            "function eventHasPartialTraceroute(event)",
            "route.nodeIds.length < 2",
            "!nodePoint(nodeId)",
            '" · Ruta parcial"',
        ):
            self.assertIn(
                expected,
                self.javascript,
            )


    def test_history_labels_routes_as_routediscovery(
        self,
    ) -> None:
        for expected in (
            "function eventPortnumLabel(portnum)",
            '[70, "RouteDiscovery"]',
            "badge.textContent = (",
            '"RouteDiscovery"',
            "eventHasPartialTraceroute(event)",
            "${eventPortnumLabel(event.portnum)}",
        ):
            self.assertIn(
                expected,
                self.javascript,
            )

        self.assertIn(
            "RouteDiscovery · sen percorrido",
            self.javascript,
        )

    def test_history_selection_matches_live_semantics(
        self,
    ) -> None:
        for expected in (
            "function eventNodeIds(event)",
            "function renderEventSelection()",
            'pane: "history-selection"',
            "radius: 8",
            "weight: 3",
            'fillColor: "#ffffff"',
            "renderEventSelection();",
            'pane: "history-routes"',
            'route.key === "back"',
            '"8 5"',
        ):
            self.assertIn(
                expected,
                self.javascript,
            )


    def test_selected_history_event_marks_origin_and_destination(
        self,
    ) -> None:
        for expected in (
            "function addHistoryEventEndpointLabel(",
            '"Orixe"',
            '"Destino"',
            "event.from_id",
            "event.to_id",
            '"meshtastic:!ffffffff"',
            '"history-event-endpoint-label history-event-endpoint-origin"',
            '"history-event-endpoint-label history-event-endpoint-destination"',
            ".history-event-endpoint-label",
            ".history-event-endpoint-origin",
            ".history-event-endpoint-destination",
        ):
            self.assertIn(
                expected,
                self.javascript + self.css,
            )


    def test_history_focus_matches_live(
        self,
    ) -> None:
        start = self.javascript.index(
            "function focusEvent(event)"
        )

        end = self.javascript.index(
            "\n\nfunction selectEvent(",
            start,
        )

        code = self.javascript[start:end]

        for expected in (
            "eventPoints(event)",
            "padding: [40, 40]",
            "maxZoom: 13",
            "Math.max(",
            "12",
        ):
            self.assertIn(
                expected,
                code,
            )


    def test_history_node_search_exists(
        self,
    ) -> None:
        for expected in (
            'id="history-node-search"',
            'id="history-node-search-status"',
            'id="history-node-search-results"',
            'type="search"',
            "function normalizeSearchText(value)",
            "function searchableNodeText(node)",
            "function clearNodeSearchResults()",
            "function focusNode(node)",
            "function renderNodeSearchResults()",
            ".filter(positionedNode)",
            "searchableNodeText(node).includes(query)",
            ".slice(0, 20)",
            '"history-search-result"',
            "focusNode(node);",
            "elements.nodeSearch.addEventListener(",
            '"input"',
            ".history-node-search",
            ".history-search-results",
            ".history-search-result",
        ):
            self.assertIn(
                expected,
                self.html
                + self.javascript
                + self.css,
            )


    def test_empty_history_search_preserves_node_context(
        self,
    ) -> None:
        start = self.javascript.index(
            "function renderNodeSearchResults()"
        )

        end = self.javascript.index(
            "\n\nfunction selectedNode()",
            start,
        )

        block = self.javascript[start:end]

        self.assertIn(
            "clearNodeSearchResults();",
            block,
        )

        self.assertNotIn(
            "state.selectedNodeId = null;",
            block,
        )

        self.assertNotIn(
            "state.nodeEventFilterId = null;",
            block,
        )


    def test_history_nodes_can_be_selected_from_map(
        self,
    ) -> None:
        for expected in (
            'id="history-selected-node-card"',
            'id="history-selected-node-close"',
            'id="history-selected-node-name"',
            'id="history-selected-node-id"',
            'id="history-selected-node-event-count"',
            'id="history-selected-node-route-count"',
            'id="history-selected-node-origin-count"',
            'id="history-selected-node-destination-count"',
            'id="history-selected-node-gateway-count"',
            'id="history-selected-node-activity"',
            "selectedNodeId: null",
            "nodeEventFilterId: null",
            "function selectedNode()",
            "function nodeActivitySummary(",
            "function renderSelectedNodeCard()",
            "function selectNode(node)",
            "function clearSelectedNode(",
            "function toggleSelectedNodeActivity()",
            "const hitMarker = L.circleMarker(",
            "bubblingMouseEvents: false",
            'marker.on(',
            'hitMarker.on(',
            "selectNode(node)",
            ".history-selected-node-card",
            ".history-selected-node-stats",
            ".history-selected-node-activity",
        ):
            self.assertIn(
                expected,
                self.html + self.javascript + self.css,
            )


    def test_history_nodes_use_neutral_style_and_large_hit_area(
        self,
    ) -> None:
        start = self.javascript.index(
            "function renderNodes()"
        )

        end = self.javascript.index(
            "\n\nfunction setInitialBounds()",
            start,
        )

        block = self.javascript[start:end]

        for expected in (
            "isHistoryMobileLayout()",
            "? 0.8",
            'color: "#65757c"',
            'fillColor: "#aeb9bd"',
            "opacity: 0.55",
            "fillOpacity: 0.34",
            "weight: 1.4",
            "const hitMarker = L.circleMarker(",
            "? 12",
            ": 8",
            "fillOpacity: 0",
        ):
            self.assertIn(
                expected,
                block,
            )

        self.assertNotIn(
            "nodeVisualStyle(node)",
            block,
        )


    def test_history_selected_node_reports_global_presence(
        self,
    ) -> None:
        for expected in (
            'id="history-selected-node-history"',
            'id="history-selected-node-history-summary"',
            "Presenza no histórico",
            "function historyNodeHourShortLabel(key)",
            "function historyNodePresenceSummary(nodeId)",
            "nodeHistoryHourKeys(nodeId)",
            '"Activo en 1 bloque"',
            "`Activo en ${keys.length} bloques`",
            "historyNodeHourShortLabel(keys[0])",
            "historyNodeHourShortLabel(keys.at(-1))",
            "elements.selectedNodeHistorySummary.textContent",
            ".history-selected-node-history",
        ):
            self.assertIn(
                expected,
                self.html + self.javascript + self.css,
            )


    def test_history_can_navigate_selected_node_activity_hours(
        self,
    ) -> None:
        for expected in (
            'id="history-selected-node-current-hour"',
            'id="history-selected-node-previous-hour"',
            'id="history-selected-node-next-hour"',
            "function historyHourNavigationLabel(hour)",
            "function selectedHistoryHourRangeLabel()",
            "function nodeHistoryHourKeys(nodeId)",
            "state.manifest.node_hours",
            "function nodeHistoryHourPosition(nodeId)",
            "function adjacentNodeHistoryHour(",
            "function selectAdjacentNodeHistoryHour(",
            "await selectManifestHour(hour);",
            "adjacentNodeHistoryHour(",
            "elements.selectedNodeCurrentHour.textContent",
            "elements.selectedNodePreviousHour.disabled",
            "elements.selectedNodeNextHour.disabled",
            "historyHourNavigationLabel(previousHour)",
            "historyHourNavigationLabel(nextHour)",
            "await selectAdjacentNodeHistoryHour(-1);",
            "await selectAdjacentNodeHistoryHour(1);",
            ".history-selected-node-hour-navigation",
            ".history-selected-node-hour-button",
        ):
            self.assertIn(
                expected,
                self.html + self.javascript + self.css,
            )


    def test_history_can_filter_events_by_selected_node(
        self,
    ) -> None:
        for expected in (
            "function eventInvolvesNode(",
            "eventNodeIds(event).includes(nodeId)",
            "function nodeRelatedEvents(",
            "function filteredEvents()",
            "if (state.nodeEventFilterId)",
            "eventInvolvesNode(",
            "state.nodeEventFilterId",
            "function toggleSelectedNodeActivity()",
            "renderEventList();",
            "renderMapEvents();",
        ):
            self.assertIn(
                expected,
                self.javascript,
            )



    def test_history_node_filter_has_visible_banner(
        self,
    ) -> None:
        for expected in (
            'id="history-node-filter-banner"',
            'id="history-node-filter-label"',
            'id="history-node-filter-clear"',
            "Mostrar todos",
            "function renderNodeFilterBanner()",
            '"Filtrando por "',
            "renderNodeFilterBanner();",
            "elements.nodeFilterClear.addEventListener(",
            "state.nodeEventFilterId = null;",
            ".history-node-filter-banner",
            ".history-node-filter-clear",
        ):
            self.assertIn(
                expected,
                self.html + self.javascript + self.css,
            )

    def test_history_node_filter_shows_event_roles(
        self,
    ) -> None:
        for expected in (
            "function nodeRolesInEvent(",
            'roles.push("Orixe")',
            'roles.push("Destino")',
            'roles.push("Gateway")',
            'roles.push("Ruta")',
            "route.nodeIds.includes(nodeId)",
            '"history-event-node-roles"',
            '"history-event-node-role "',
            "roles.childElementCount > 0",
            ".history-event-node-role.role-orixe",
            ".history-event-node-role.role-destino",
            ".history-event-node-role.role-gateway",
            ".history-event-node-role.role-ruta",
        ):
            self.assertIn(
                expected,
                self.javascript + self.css,
            )


    def test_history_hour_change_preserves_node_context(
        self,
    ) -> None:
        start = self.javascript.index(
            "async function loadHour(hour)"
        )

        end = self.javascript.index(
            "\n\nasync function selectLatestHour()",
            start,
        )

        block = self.javascript[start:end]

        self.assertIn(
            "state.selectedEventId = null;",
            block,
        )

        self.assertNotIn(
            "state.selectedNodeId = null;",
            block,
        )

        self.assertNotIn(
            "state.nodeEventFilterId = null;",
            block,
        )

        for expected in (
            "renderEventList();",
            "renderMapEvents();",
            "renderSelectedNodeCard();",
        ):
            self.assertIn(
                expected,
                block,
            )


    def test_history_event_and_node_selections_are_exclusive(
        self,
    ) -> None:
        select_event_start = self.javascript.index(
            "function selectEvent(event)"
        )

        select_event_end = self.javascript.index(
            "\n\nfunction renderEventList()",
            select_event_start,
        )

        select_event = self.javascript[
            select_event_start:select_event_end
        ]

        self.assertIn(
            "state.selectedNodeId = null;",
            select_event,
        )
        self.assertIn(
            "renderSelectedNodeCard();",
            select_event,
        )

        select_node_start = self.javascript.index(
            "function selectNode(node)"
        )

        select_node_end = self.javascript.index(
            "\n\nfunction toggleSelectedNodeActivity()",
            select_node_start,
        )

        select_node = self.javascript[
            select_node_start:select_node_end
        ]

        self.assertIn(
            "state.selectedEventId = null;",
            select_node,
        )
        self.assertIn(
            "renderSelectedEventCard();",
            select_node,
        )



    def test_history_events_can_be_selected_from_map(
        self,
    ) -> None:
        for expected in (
            "function pointToSegmentDistance(",
            "function tracerouteDistanceFromMapPoint(",
            "function receptionDistanceFromMapPoint(",
            "function historyMapSelectionThreshold()",
            "isHistoryMobileLayout()",
            "? 26",
            ": 16",
            "function nearestMapEvent(",
            "for (const event of filteredEvents())",
            "Math.min(",
            "function initializeRouteMapSelection()",
            'state.map.on(',
            '"click"',
            "mapEvent.containerPoint",
            "selectEvent(event)",
            "initializeRouteMapSelection();",
        ):
            self.assertIn(
                expected,
                self.javascript,
            )

        selection_start = self.javascript.index(
            "function tracerouteDistanceFromMapPoint("
        )
        selection_end = self.javascript.index(
            "\n\nfunction filteredEvents()",
            selection_start,
        )

        selection_code = self.javascript[
            selection_start:selection_end
        ]

        self.assertIn(
            "routePointSegments(route)",
            selection_code,
        )



    def test_history_selected_node_can_copy_reproducible_url(
        self,
    ) -> None:
        for expected in (
            'id="history-selected-node-copy-link"',
            'id="history-selected-node-copy-status"',
            "Copiar enlace",
            "async function copyHistoryUrl()",
            "window.location.href",
            "navigator.clipboard.writeText(url)",
            '"Enlace copiado"',
            '"Non foi posible copiar o enlace"',
            "elements.selectedNodeCopyLink.addEventListener(",
            ".history-selected-node-copy-link",
            ".history-selected-node-copy-status",
        ):
            self.assertIn(
                expected,
                self.html
                + self.javascript
                + self.css,
            )



    def test_history_state_is_reproducible_from_url(
        self,
    ) -> None:
        for expected in (
            "restoringUrlState: false",
            "function historyHourFromUrl()",
            "function historyNodeIdFromUrl()",
            "function historyNodeFromUrl()",
            "function historyUrlNodeValue(nodeId)",
            "function syncHistoryUrl(",
            "function restoreHistoryStateFromUrl()",
            "function initializeHistoryUrlNavigation()",
            'params.get("hour")',
            'params.get("node")',
            '"meshtastic:"',
            'url.searchParams.set(',
            '"hour"',
            '"node"',
            "window.history.pushState(",
            "window.history.replaceState(",
            '"popstate"',
            'syncHistoryUrl("replace");',
            "await restoreHistoryStateFromUrl();",
            "initializeHistoryUrlNavigation();",
        ):
            self.assertIn(
                expected,
                self.javascript,
            )


if __name__ == "__main__":
    unittest.main()
