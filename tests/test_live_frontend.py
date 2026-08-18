"""Probas estruturais da visualización web do tráfico live."""

from __future__ import annotations

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parent.parent


class LiveFrontendTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.html = (
            ROOT / "frontend/live/index.html"
        ).read_text(encoding="utf-8")

        cls.javascript = (
            ROOT / "frontend/live/live.js"
        ).read_text(encoding="utf-8")

        cls.css = (
            ROOT / "frontend/live/live.css"
        ).read_text(encoding="utf-8")

    def test_live_page_has_independent_entrypoint(
        self,
    ) -> None:
        for expected in (
            "<title>Tráfico en directo · Mesh Noroeste</title>",
            'id="live-map"',
            "./live.css?v=20260817-live15",
            "./live.js?v=20260817-live15",
            "../",
        ):
            self.assertIn(expected, self.html)

    def test_live_page_uses_live_contract(
        self,
    ) -> None:
        for expected in (
            'const LIVE_URL = "../data/live.json"',
            '"mesh-noroeste.live/v1"',
            "function validateLive(document)",
            "document.schema !== PUBLIC_LIVE_SCHEMA",
            "Array.isArray(document.events)",
        ):
            self.assertIn(expected, self.javascript)

    def test_live_page_uses_manifest_for_node_positions(
        self,
    ) -> None:
        for expected in (
            'const MANIFEST_URL = "../data/manifest.json"',
            '"mesh-noroeste.manifest/v1"',
            'manifest.documents["nodes.json"]',
            "state.nodeById = new Map(",
            "function nodePoint(nodeId)",
        ):
            self.assertIn(expected, self.javascript)

    def test_gateway_receptions_are_not_called_direct_links(
        self,
    ) -> None:
        for expected in (
            "function addGatewayObservations(",
            'selected ? "5 5" : "4 6"',
            '"Paquete observado por gateway"',
            "non demostran unha ligazón radio directa",
        ):
            self.assertIn(
                expected,
                self.javascript + self.html,
            )

    def test_route_discovery_has_separate_rendering(
        self,
    ) -> None:
        for expected in (
            "function traceroutePaths(event)",
            "traceroute.towards",
            "traceroute.back",
            "function addTraceroute(",
            'route.key === "back"',
        ):
            self.assertIn(expected, self.javascript)

    def test_page_refreshes_live_data_periodically(
        self,
    ) -> None:
        for expected in (
            "const REFRESH_INTERVAL_MS = 60_000",
            "async function refreshLive()",
            "window.setInterval(",
            "REFRESH_INTERVAL_MS",
        ):
            self.assertIn(expected, self.javascript)

    def test_events_can_be_selected_and_highlighted(
        self,
    ) -> None:
        for expected in (
            "selectedEventId: null",
            "selectionLayer: null",
            'state.map.createPane("live-selection")',
            "function selectedVisibleEvent()",
            "function eventNodeIds(event)",
            "function renderEventSelection()",
            "function selectEvent(event)",
            "state.selectedEventId === event.id",
            '"aria-pressed"',
            '"live-event-button"',
            '" selected"',
            "selectedEventId !== null",
            "&& !selected",
            "renderEventSelection();",
            'color: selected',
            '? "#a61e4d"',
        ):
            with self.subTest(expected=expected):
                self.assertIn(
                    expected,
                    self.javascript,
                )

        for expected in (
            ".live-event-button.selected",
            '.live-event-button[aria-pressed="true"]',
            "var(--traceroute-selected)",
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, self.css)

    def test_live_node_search_exists(self) -> None:
        for expected in (
            'data-mobile-panel="search"',
            'id="live-node-search"',
            'id="live-node-search-results"',
            'data-live-mobile-target="search"',
            'search: "Buscar nodo"',
            "function renderNodeSearchResults()",
            "function focusNode(node)",
            ".filter(positionedNode)",
            "searchableNodeText(node).includes(query)",
        ):
            self.assertIn(
                expected,
                self.html + self.javascript,
            )

    def test_node_search_selection_is_highlighted(
        self,
    ) -> None:
        for expected in (
            "selectedNodeId: null",
            "nodeSearchSelectionLayer: null",
            "function renderNodeSearchSelection()",
            "state.selectedNodeId = node.id",
            "live-selected-node-label",
        ):
            self.assertIn(
                expected,
                self.javascript + self.css,
            )


    def test_live_gateway_filter_exists(self) -> None:
        for expected in (
            'id="event-gateway"',
            "Todos os gateways",
            'eventGateway: document.querySelector(',
            "function eventHasGateway(event, gatewayId)",
            "function filteredEventsByGateway()",
            "function gatewayOptionLabel(gatewayId)",
            "function updateGatewayOptions()",
            "filteredEventsByGateway()",
            "function focusGateway(gatewayId)",
            "function renderGatewaySelection()",
            "gatewaySelectionLayer: null",
            "live-selected-gateway-label",
            "elements.eventGateway.addEventListener(",
        ):
            self.assertIn(
                expected,
                self.html + self.javascript,
            )


    def test_live_time_filter_exists(self) -> None:
        for expected in (
            'id="event-age"',
            '<option value="60">Última hora</option>',
            '<option value="15">Últimos 15 min</option>',
            '<option value="5">Últimos 5 min</option>',
            'eventAge: document.querySelector("#event-age")',
            "function filteredEventsByAge()",
            "minutes * 60 * 1_000_000",
            "elements.eventAge.addEventListener(",
        ):
            self.assertIn(
                expected,
                self.html + self.javascript,
            )


    def test_live_event_type_filter_exists(self) -> None:
        for expected in (
            'id="event-type"',
            '<option value="traceroute">RouteDiscovery</option>',
            '<option value="reception">Recepcións observadas</option>',
            'eventType: document.querySelector("#event-type")',
            "function eventMatchesType(event)",
            "function filteredEventsByType()",
            'type === "traceroute"',
            'type === "reception"',
            "const events = filteredEventsByType();",
            "elements.eventType.addEventListener(",
        ):
            self.assertIn(
                expected,
                self.html + self.javascript,
            )


    def test_traceroute_can_be_selected_from_map(self) -> None:
        for expected in (
            "function pointToSegmentDistance(",
            "function eventDistanceFromMapPoint(",
            "function nearestTracerouteEvent(",
            "function initializeRouteMapSelection()",
            'state.map.on(',
            '"click"',
            "mapEvent.containerPoint",
            "isLiveMobileLayout()",
            "? 26",
            ": 16",
            "selectEvent(event);",
            "initializeRouteMapSelection();",
        ):
            self.assertIn(
                expected,
                self.javascript,
            )



    def test_receptions_can_be_selected_from_map(self) -> None:
        for expected in (
            "function receptionDistanceFromMapPoint(",
            "function nearestReceptionEvent(",
            "function nearestMapEvent(",
            "elements.showReceptions.checked",
            "receptionDistanceFromMapPoint(",
            "const event = nearestMapEvent(",
            "selectEvent(event);",
        ):
            self.assertIn(
                expected,
                self.javascript,
            )




    def test_selected_event_card_shows_observation_metrics(
        self,
    ) -> None:
        for expected in (
            'id="selected-event-card-observations"',
            "selectedEventCardObservations",
            "function formatRadioMetric(",
            "function gatewayRadioSummary(",
            "function observationStageLabel(",
            "function renderSelectedEventObservations(",
            '"RSSI — · SNR —"',
            '"salto consumido"',
            '"saltos consumidos"',
            '`hop ${hopStart} → ${hopLimit}`',
            "event.channel ||",
            ".live-selected-event-card-observations",
            ".live-selected-event-gateway-radio",
        ):
            self.assertIn(
                expected,
                self.html + self.javascript + self.css,
            )


    def test_selected_event_card_shows_traceroute_paths(
        self,
    ) -> None:
        for expected in (
            'id="selected-event-card-towards"',
            'id="selected-event-card-back"',
            "function traceroutePathLabel(",
            'names.join(" → ")',
            '"Ida"',
            '"Volta"',
            "selectedEventCardTowards",
            "selectedEventCardBack",
            ".live-selected-event-card-path",
        ):
            self.assertIn(
                expected,
                self.html + self.javascript + self.css,
            )


    def test_selected_event_card_shows_traceroute_hops(
        self,
    ) -> None:
        for expected in (
            "function tracerouteHopSummary(event)",
            "traceroute.towards?.length",
            "traceroute.back?.length",
            "`ida ${towardsHops} `",
            "`volta ${backHops} `",
            '"volta non dispoñible"',
            "tracerouteHopSummary(event)",
        ):
            self.assertIn(
                expected,
                self.javascript,
            )


    def test_selected_event_card_exists(self) -> None:
        for expected in (
            'id="selected-event-card"',
            'id="selected-event-card-close"',
            'id="selected-event-card-route"',
            'id="selected-event-card-meta"',
            'id="selected-event-card-evidence"',
            "function selectedEvent()",
            "function renderSelectedEventCard()",
            "function clearSelectedEvent()",
            "renderSelectedEventCard();",
            ".live-selected-event-card",
        ):
            self.assertIn(
                expected,
                self.html + self.javascript + self.css,
            )


    def test_selected_route_can_be_animated(self) -> None:
        for expected in (
            "eventAnimationLayer: null",
            "eventAnimationFrame: null",
            "eventAnimationToken: 0",
            'state.map.createPane("live-animation")',
            "function prefersReducedMotion()",
            "function cancelSelectedEventAnimation()",
            "function selectedEventAnimationSegments(event)",
            "function animationPointAtDistance(",
            "function animateSelectedEvent(event)",
            "function syncSelectedEventAnimation()",
            "window.requestAnimationFrame(frame)",
            "window.cancelAnimationFrame(",
            "const pauseDuration = 900",
            "const cycleDuration = (",
            "cycleElapsed >= movementDuration",
            'state.selectedEventId !== event.id',
            "!elements.showTraceroutes.checked",
            '"(prefers-reduced-motion: reduce)"',
        ):
            self.assertIn(
                expected,
                self.javascript,
            )



    def test_selected_reception_can_be_animated(
        self,
    ) -> None:
        for expected in (
            "function receptionAnimationSegments(event)",
            "function animateSelectedReception(event)",
            "!elements.showReceptions.checked",
            'color: "#075d68"',
            'fillColor: "#bfe8ee"',
            "completedCycles % segments.length",
            "animateSelectedReception(event);",
        ):
            self.assertIn(
                expected,
                self.javascript,
            )


    def test_mobile_tabs_remain_available_with_sheet_open(
        self,
    ) -> None:
        for expected in (
            'liveMap: document.querySelector("#live-map")',
            "elements.liveMap.inert = true",
            "elements.liveMap.inert = false",
        ):
            self.assertIn(
                expected,
                self.javascript,
            )

        self.assertNotIn(
            "elements.mapRegion.inert = true",
            self.javascript,
        )

        self.assertNotIn(
            '"aria-modal",\n      "true"',
            self.javascript,
        )

    def test_node_search_selection_can_be_cleared(
        self,
    ) -> None:
        for expected in (
            "function clearNodeSelection({",
            "state.selectedNodeId = null",
            "state.nodeSearchSelectionLayer?.clearLayers()",
            "elements.nodeSearch.value = \"\"",
            "clearSearch: true",
        ):
            self.assertIn(
                expected,
                self.javascript,
            )


    def test_traceroute_playback_controls_exist(self) -> None:
        for expected in (
            'id="toggle-traceroute-playback"',
            'id="playback-status"',
            "live-map-playback",
            "aria-pressed",
            "playbackActive: false",
            "playbackToken: 0",
            "playbackTimer: null",
            "function playbackTracerouteEvents()",
            "return filteredEventsByAge()",
                        "function stopTraceroutePlayback(",
            "function animateEventOnce(",
                                    "function runTraceroutePlayback(",
            "function startTraceroutePlayback()",
            "if (state.playbackActive) {",
            "elements.toggleTraceroutePlayback.addEventListener(",
        ):
            self.assertIn(
                expected,
                self.html + self.javascript,
            )



    def test_playback_selected_route_is_rendered_outside_limit(
        self,
    ) -> None:
        for expected in (
            "const events = visibleEvents();",
            "state.live.events.find(",
            "event.id === state.selectedEventId",
            "events.push(selectedEvent);",
            "for (const event of events) {",
        ):
            self.assertIn(
                expected,
                self.javascript,
            )



    def test_live_activity_timeline_exists(self) -> None:
        for expected in (
            'id="live-timeline-bars"',
            'id="live-timeline-status"',
            'id="clear-timeline-range"',
            "timelineRange: null",
            "function timelineBaseEvents()",
            "function timelineBuckets()",
            "function renderTimeline()",
            "function eventsInsideTimelineRange(events)",
            "5 * 60 * 1_000_000",
            "{ length: 12 }",
            "state.timelineRange = {",
            'elements.eventAge.value = "60"',
            "function refreshEventView()",
            "renderTimeline();",
            ".live-timeline-bars",
            ".live-timeline-bar.selected",
        ):
            self.assertIn(
                expected,
                self.html + self.javascript + self.css,
            )




    def test_timeline_marks_reproducible_traceroutes(
        self,
    ) -> None:
        for expected in (
            "tracerouteCount: 0",
            "buckets[index].tracerouteCount += 1",
            '"has-traceroute"',
            "bucket.tracerouteCount > 0",
            "dataset.tracerouteCount",
            "RouteDiscovery reproducible",
            ".live-timeline-bar.has-traceroute::after",
        ):
            self.assertIn(
                expected,
                self.javascript + self.css,
            )


    def test_mobile_layout_exists(self) -> None:
        self.assertIn(
            "@media (max-width: 760px)",
            self.css,
        )


if __name__ == "__main__":
    unittest.main()
