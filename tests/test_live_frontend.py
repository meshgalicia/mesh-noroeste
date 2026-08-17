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
            "./live.css?v=20260817-live8",
            "./live.js?v=20260817-live8",
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
            '"Recepción observada por gateway"',
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


    def test_mobile_layout_exists(self) -> None:
        self.assertIn(
            "@media (max-width: 760px)",
            self.css,
        )


if __name__ == "__main__":
    unittest.main()
