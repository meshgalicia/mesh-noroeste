from __future__ import annotations

from html.parser import HTMLParser
from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "frontend"


class FrontendParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.ids: set[str] = set()
        self.links: list[str] = []
        self.scripts: list[str] = []
        self.language: str | None = None

    def handle_starttag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        attributes = dict(attrs)

        if tag == "html":
            self.language = attributes.get("lang")

        element_id = attributes.get("id")

        if element_id:
            self.ids.add(element_id)

        if tag == "link" and attributes.get("href"):
            self.links.append(attributes["href"])

        if tag == "script" and attributes.get("src"):
            self.scripts.append(attributes["src"])


class FrontendStaticTests(unittest.TestCase):
    def setUp(self) -> None:
        self.html = (
            FRONTEND / "index.html"
        ).read_text(encoding="utf-8")
        self.css = (
            FRONTEND / "styles.css"
        ).read_text(encoding="utf-8")
        self.javascript = (
            FRONTEND / "app.js"
        ).read_text(encoding="utf-8")

        self.parser = FrontendParser()
        self.parser.feed(self.html)

    def test_html_has_galician_interface_and_controls(
        self,
    ) -> None:
        self.assertEqual(self.parser.language, "gl")

        required_ids = {
            "map",
            "network-filter",
            "status-filter",
            "age-details",
            "age-summary",
            "legend-details",
            "type-filter",
            "type-summary",
            "type-filter-reset",
            "mqtt-gateway-filter",
            "mqtt-gateway-summary",
            "meshcore-activity-filter",
            "meshcore-activity-summary",
            "meshcore-activity-controls",
            "meshcore-activity-window",
            "source-details",
            "filter-empty-panel",
            "node-search",
            "search-results",
            "traceroutes-toggle",
            "traceroute-controls",
            "traceroute-source",
            "traceroute-age",
            "neighbors-toggle",
            "fit-map",
            "locate-me",
            "location-status",
            "visible-count",
            "meshtastic-count",
            "meshcore-count",
            "edge-count",
            "source-status",
            "detail-panel",
            "detail-size-toggle",
            "detail-close",
            "error-panel",
            "privacy-notice",
            "privacy-dismiss",
        }

        self.assertTrue(
            required_ids.issubset(self.parser.ids)
        )

    def test_footer_identifies_sources_and_attribution(
        self,
    ) -> None:
        self.assertIn(
            "Datos: Meshview España, Malha Portugal,",
            self.html,
        )
        self.assertIn(
            "Comunidade O Zulo, MeshCore Map e",
            self.html,
        )
        self.assertIn(
            "MeshCore Hub de Mesh Galicia.",
            self.html,
        )
        self.assertIn(
            "Cartografía: © contribuidores de",
            self.html,
        )
        self.assertIn(
            "https://www.openstreetmap.org/copyright",
            self.html,
        )
        self.assertIn(
            "OpenStreetMap</a>. Proxecto independente.",
            self.html,
        )

    def test_leaflet_and_local_assets_are_declared(
        self,
    ) -> None:
        self.assertIn(
            "./styles.css?v=20260809-meshcore-activity1",
            self.parser.links,
        )
        self.assertIn(
            "./app.js?v=20260809-meshcore-activity1",
            self.parser.scripts,
        )

        self.assertTrue(
            any(
                "leaflet@1.9.4" in asset
                for asset in (
                    self.parser.links
                    + self.parser.scripts
                )
            )
        )

    def test_leaflet_assets_use_official_sri(
        self,
    ) -> None:
        css_tag = re.search(
            r'<link\s+rel="stylesheet"\s+'
            r'href="https://unpkg\.com/leaflet@1\.9\.4/'
            r'dist/leaflet\.css"(?P<attrs>[^>]*)>',
            self.html,
            flags=re.DOTALL,
        )
        self.assertIsNotNone(css_tag)
        assert css_tag is not None

        self.assertIn(
            'integrity="sha256-p4NxAoJBhIIN+hmNHrzRCf9tD/'
            'miZyoHS5obTRR9BMY="',
            css_tag.group(0),
        )
        self.assertIn(
            'crossorigin=""',
            css_tag.group(0),
        )

        script_tag = re.search(
            r'<script\s+'
            r'src="https://unpkg\.com/leaflet@1\.9\.4/'
            r'dist/leaflet\.js"(?P<attrs>[^>]*)>',
            self.html,
            flags=re.DOTALL,
        )
        self.assertIsNotNone(script_tag)
        assert script_tag is not None

        self.assertIn(
            'integrity="sha256-20nQCchB9co0qIjJZRGuk2/'
            'Z9VM+kNiyxNV1lvTlZBo="',
            script_tag.group(0),
        )
        self.assertIn(
            'crossorigin=""',
            script_tag.group(0),
        )


    def test_favicon_is_declared(self) -> None:
        self.assertIn(
            "./favicon.ico",
            self.parser.links,
        )

    def test_javascript_identifies_all_sources(
        self,
    ) -> None:
        for expected in (
            'meshview_es: "Meshview España"',
            'malha_pt: "Malha Portugal"',
            'ozulo_map: "Comunidade O Zulo"',
            'meshcore_map: "MeshCore Map"',
            (
                'meshcore_hub: '
                '"MeshCore Hub de Mesh Galicia"'
            ),
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, self.javascript)

        self.assertIn(
            '"ozulo_map",',
            self.javascript,
        )
        self.assertIn(
            '"meshcore_hub",',
            self.javascript,
        )

    def test_javascript_uses_atomic_manifest(
        self,
    ) -> None:
        for expected in (
            'const DATA_MANIFEST = "./data/manifest.json"',
            '"mesh-noroeste.manifest/v1"',
            "function validateManifest(manifest)",
            "manifest.documents[filename]",
            "manifest.generated_at",
            "validateDocuments(documents, manifest)",
        ):
            with self.subTest(expected=expected):
                self.assertIn(
                    expected,
                    self.javascript,
                )

        for filename in (
            "nodes.json",
            "edges.json",
            "neighbor-info.json",
            "stats.json",
            "meta.json",
            "configuration-warnings.json",
        ):
            self.assertIn(filename, self.javascript)

    def test_javascript_validates_document_schemas(
        self,
    ) -> None:
        for expected in (
            '"mesh-noroeste.data/v1"',
            '"mesh-noroeste.configuration-warnings/v1"',
            "const DATA_DOCUMENT_SCHEMAS = Object.freeze({",
            "const expectedSchema = DATA_DOCUMENT_SCHEMAS[key]",
            "document.schema !== expectedSchema",
            "${filename} usa un contrato descoñecido.",
        ):
            with self.subTest(expected=expected):
                self.assertIn(
                    expected,
                    self.javascript,
                )

    def test_observer_receptions_are_loaded_and_shown(
        self,
    ) -> None:
        for expected in (
            'observerReceptions: "observer-receptions.json"',
            "documents.observerReceptions.receptions",
            "state.observerReceptions = (",
            "state.receptionsByNodeId = new Map()",
            "state.receptionsByObserverId = new Map()",
            "function observerReceptionSummary(receptions)",
            "function observerReceptionDescription(summary)",
            "function observerReceptionsSection(node)",
            "receptionsByObserver = new Map()",
            "state.nodeById.get(observerId)",
            '"Recepcións dos observers"',
            "recepcións publicadas",
            "observers",
            "observerReceptionDescription(",
            "focusNode(entry.observer)",
            "observerReceptionsSection(node)",
            "function observedNodesSection(node)",
            "state.receptionsByObserverId.get(node.id)",
            '"Nodos escoitados"',
            '"Ver nodos escoitados"',
            "coñecidos no mapa",
            "con posición",
            "focusNode(entry.node)",
            "observedNodesSection(node)",
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, self.javascript)

        for expected in (
            ".observer-receptions-summary",
            ".observer-reception-list",
            ".observer-reception-item",
            ".observer-reception-link",
            ".observer-reception-meta",
            ".observer-heard-nodes-details",
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, self.css)

        self.assertIn(
            "20260809-meshcore-activity1",
            self.html,
        )


    def test_neighbor_info_can_be_shown_on_the_map(
        self,
    ) -> None:
        for expected in (
            'neighborInfo: "neighbor-info.json"',
            "DATA_DOCUMENT_NAMES.neighborInfo",
            "documents.neighborInfo.observations",
            "state.neighborInfo = neighborInfo.observations",
            'neighborInfo: document.querySelector(',
            '"#neighbor-info-toggle"',
            "function addNeighborInfo(observation)",
            "state.neighborInfo.filter(",
            "elements.neighborInfo.checked",
            "elements.neighborInfo.addEventListener(",
            'selected ? "#9c2f6f" : "#c2255c"',
            'dashArray: "2 6"',
            "visibleNeighborInfo.length",
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, self.javascript)

        for expected in (
            'id="neighbor-info-toggle"',
            "Mostrar anuncios NeighborInfo",
            'class="legend-line neighbor-info-line"',
            "Anuncio NeighborInfo",
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, self.html)

        self.assertIn(
            ".legend-line.neighbor-info-line",
            self.css,
        )
        self.assertIn(
            "border-top-color: var(--neighbor-info)",
            self.css,
        )

    def test_neighbor_info_is_disabled_by_default(
        self,
    ) -> None:
        control = self.html[
            self.html.index('id="neighbor-info-toggle"'):
            self.html.index(
                'class="control-subheading">Capa base'
            )
        ]

        self.assertNotIn("checked", control)

    def test_configuration_warning_data_are_indexed(
        self,
    ) -> None:
        for expected in (
            "DATA_DOCUMENT_NAMES.configurationWarnings",
            "state.configurationWarnings = configurationWarnings",
            "state.warningByNodeId = new Map(",
            "configurationWarnings.nodes.map(",
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, self.javascript)

    def test_configuration_warnings_are_contextual(
        self,
    ) -> None:
        for expected in (
            "function configurationWarningsSection(node)",
            "state.warningByNodeId.get(node.id)",
            "configurationWarningsSection(node)",
            "Non se detectaron avisos na análise dispoñible",
            "Isto non equivale a unha validación completa",
            "Análise non dispoñible para este nodo. ",
            "As demais fontes non publican todos os ",
            "parámetros de configuración necesarios.",
            "WARNING_SEVERITY_LABELS",
            "warningDocument?.analysis",
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, self.javascript)

        self.assertNotIn(
            "const document = state.configurationWarnings",
            self.javascript,
        )

    def test_traceroutes_use_published_endpoints(
        self,
    ) -> None:
        self.assertIn(
            'edge.edge_type !== "traceroute"',
            self.javascript,
        )
        self.assertIn("edge.from_id", self.javascript)
        self.assertIn("edge.to_id", self.javascript)
        self.assertIn(
            "state.visibleIds.has(edge.from_id)",
            self.javascript,
        )
        self.assertIn(
            "state.visibleIds.has(edge.to_id)",
            self.javascript,
        )

    def test_neighbor_is_present_in_the_legend(
        self,
    ) -> None:
        self.assertIn(
            'class="legend-line neighbor-line"',
            self.html,
        )
        self.assertIn("Veciñanza", self.html)
        self.assertIn(
            ".legend-line.neighbor-line",
            self.css,
        )
        self.assertIn(
            "border-top-color: var(--neighbor)",
            self.css,
        )

    def test_neighbors_can_be_shown_on_the_map(
        self,
    ) -> None:
        required_javascript = (
            'neighbors: document.querySelector(',
            '"#neighbors-toggle"',
            "function addNeighbor(edge)",
            'edge.edge_type !== "neighbor"',
            "function addVisibleEdge(edge)",
            "function globalEdgeEnabled(",
            "elements.neighbors.checked",
            "elements.neighbors.addEventListener(",
            'selected ? "#006d77" : "#343a40"',
            "weight: selected ? 2.6 : 2.2",
            "regularEdges.length",
            "selectedEdges.length",
        )

        for text in required_javascript:
            self.assertIn(text, self.javascript)

    def test_meshcore_routes_can_be_filtered_by_completeness(
        self,
    ) -> None:
        for expected in (
            'id="meshcore-complete-routes-toggle"',
            "Mostrar rutas completas de MeshCore",
            'id="meshcore-fragmented-routes-toggle"',
            "Mostrar rutas fragmentadas de MeshCore",
        ):
            with self.subTest(html=expected):
                self.assertIn(expected, self.html)

        for expected in (
            "meshcoreCompleteRoutes: document.querySelector(",
            '"#meshcore-complete-routes-toggle"',
            "meshcoreFragmentedRoutes: document.querySelector(",
            '"#meshcore-fragmented-routes-toggle"',
            "function meshcoreRouteCompleteness(edges)",
            "const indexesByRouteId = new Map()",
            "const complete = new Set()",
            "const fragmented = new Set()",
            "value > ordered[index - 1] + 1",
            "function meshcoreObservedEdgeEnabled(",
            "routeCompleteness.fragmented.has(edge.route_id)",
            "elements.meshcoreFragmentedRoutes.checked",
            "elements.meshcoreCompleteRoutes.checked",
            "elements.meshcoreCompleteRoutes.addEventListener(",
            "elements.meshcoreFragmentedRoutes.addEventListener(",
        ):
            with self.subTest(javascript=expected):
                self.assertIn(expected, self.javascript)

        complete_control = self.html[
            self.html.index(
                'id="meshcore-complete-routes-toggle"'
            ):
            self.html.index(
                'id="meshcore-fragmented-routes-toggle"'
            )
        ]
        fragmented_control = self.html[
            self.html.index(
                'id="meshcore-fragmented-routes-toggle"'
            ):
            self.html.index('id="neighbors-toggle"')
        ]

        self.assertNotIn("checked", complete_control)
        self.assertNotIn("checked", fragmented_control)

    def test_meshcore_observed_connections_can_be_shown_on_the_map(
        self,
    ) -> None:
        required_javascript = (
            'meshcoreCompleteRoutes: document.querySelector(',
            '"#meshcore-complete-routes-toggle"',
            'meshcoreFragmentedRoutes: document.querySelector(',
            '"#meshcore-fragmented-routes-toggle"',
            "function addMeshcoreObserved(edge)",
            'edge.edge_type !== "observed"',
            'edge.network !== "meshcore"',
            "function addVisibleEdge(edge)",
            "function globalEdgeEnabled(",
            "function meshcoreObservedEdgeEnabled(",
            "elements.meshcoreCompleteRoutes.checked",
            "elements.meshcoreFragmentedRoutes.checked",
            'className: selected',
            '? "meshcore-route-arrow selected"',
            ': "meshcore-route-arrow"',
            "midpoint(fromNode, toNode)",
            "bearing(",
        )

        for expected in required_javascript:
            with self.subTest(expected=expected):
                self.assertIn(expected, self.javascript)

        for expected in (
            'id="meshcore-complete-routes-toggle"',
            "Mostrar rutas completas de MeshCore",
            'id="meshcore-fragmented-routes-toggle"',
            "Mostrar rutas fragmentadas de MeshCore",
            'class="legend-line meshcore-observed-line"',
            "Ruta observada de MeshCore",
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, self.html)

        self.assertIn(
            ".legend-line.meshcore-observed-line",
            self.css,
        )
        self.assertIn(
            "border-top-color: var(--meshcore-observed)",
            self.css,
        )
        self.assertIn(
            ".meshcore-route-arrow {",
            self.css,
        )
        self.assertIn(
            "color: var(--meshcore-observed)",
            self.css,
        )
        self.assertIn(
            ".meshcore-route-arrow.selected",
            self.css,
        )

    def test_meshcore_observed_neighbors_can_be_shown(
        self,
    ) -> None:
        for expected in (
            'id="meshcore-neighbors-toggle"',
            "Mostrar veciñanzas observadas MeshCore",
        ):
            with self.subTest(html=expected):
                self.assertIn(expected, self.html)

        for expected in (
            "meshcoreNeighbors: document.querySelector(",
            '"#meshcore-neighbors-toggle"',
            "function meshcoreObservedNeighborPairs(edges)",
            "function addMeshcoreObservedNeighbor(",
            "elements.meshcoreNeighbors.checked",
            "elements.meshcoreNeighbors.addEventListener(",
        ):
            with self.subTest(javascript=expected):
                self.assertIn(expected, self.javascript)

    def test_neighbors_are_disabled_by_default(
        self,
    ) -> None:
        neighbors_block = self.html[
            self.html.index('id="neighbors-toggle"'):
            self.html.index(
                'class="control-subheading">Capa base'
            )
        ]

        self.assertNotIn(
            "checked",
            neighbors_block,
        )

    def test_node_detail_lists_published_connections(
        self,
    ) -> None:
        required_javascript = (
            "function createConnectionsSection(node)",
            "function createConnectionGroup(",
            "function appendConnectionItems(",
            'heading.textContent = "Conexións publicadas"',
            "edge.from_id === node.id",
            "edge.to_id === node.id",
            'traceroute: "Traceroute"',
            'neighbor: "Veciñanza"',
            'connectionsForNode(\n    node,\n    "neighbor"',
            'connectionsForNode(\n    node,\n    "traceroute"',
            'title: "Veciños directos"',
            'title: "Traceroutes"',
            "connectionDirectionLabel(edge, node.id)",
            "focusNode(otherNode)",
            "edge.metrics?.snr_db",
            "edge.metrics?.rssi_dbm",
        )

        for text in required_javascript:
            self.assertIn(text, self.javascript)

        for selector in (
            ".connection-group",
            ".connection-group-heading",
            ".connection-list",
            ".connection-button",
            ".connection-kind",
            ".connection-metadata",
            ".connection-empty",
        ):
            self.assertIn(selector, self.css)

    def test_meshtastic_nodes_offer_source_links(
        self,
    ) -> None:
        for expected in (
            "function sourceLinkIsRecent(node, source)",
            "node.source_last_seen?.[source]",
            "state.meta?.retention?.recent_days",
            "reference - observed",
            "function meshtasticNodeLinks(node)",
            'node.network !== "meshtastic"',
            "!Array.isArray(node.sources)",
            r"/^meshtastic:!([0-9a-f]{8})$/",
            "Number.parseInt(idMatch[1], 16)",
            'node.sources.includes("meshview_es")',
            'sourceLinkIsRecent(node, "meshview_es")',
            '"https://meshview.meshtastic.es/node/"',
            '"Abrir en Meshview España"',
            'node.sources.includes("malha_pt")',
            'sourceLinkIsRecent(node, "malha_pt")',
            '"https://malha.meshtastic.pt/node/"',
            '"Abrir en Malha Portugal"',
            'node.sources.includes("ozulo_map")',
            'sourceLinkIsRecent(node, "ozulo_map")',
            '"https://meshview.mesh.comunidadeozulo.org/node/"',
            '"Abrir en Meshview de O Zulo"',
            "function meshcoreNodeLinks(node)",
            'node.network !== "meshcore"',
            r"/^meshcore:([0-9a-f]{64})$/",
            'node.sources.includes("meshcore_map")',
            'sourceLinkIsRecent(node, "meshcore_map")',
            '"https://map.meshcore.io/?public_key="',
            '"Abrir en MeshCore Map"',
            'node.sources.includes("meshcore_hub")',
            'sourceLinkIsRecent(node, "meshcore_hub")',
            '"https://hub.mesh.gal/nodes/"',
            '"Abrir no Hub de Mesh Galicia"',
            "...meshtasticNodeLinks(node)",
            "...meshcoreNodeLinks(node)",
            "function externalNodeLinksSection(node)",
            'heading.textContent = "Fichas externas"',
            '"Consulta este nodo nos mapas públicos das fontes "',
            '"que o recollen."',
            "window.location.href = link.url",
            "externalNodeLinksSection(node),",
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, self.javascript)

        self.assertIn(
            "./app.js?v=20260809-meshcore-activity1",
            self.parser.scripts,
        )

    def test_meshcore_detail_offers_contact_link(
        self,
    ) -> None:
        for expected in (
            "const MESHCORE_CONTACT_TYPES",
            "client: 1",
            "repeater: 2",
            "room_server: 3",
            "sensor: 4",
            "function meshcoreContactUrl(node)",
            r"/^meshcore:([0-9a-f]{64})$/",
            "new URLSearchParams",
            "public_key: keyMatch[1]",
            "type: String(contactType)",
            "meshcore://contact/add?",
            "function meshcoreAppSection(node)",
            'openButton.textContent = "Abrir en MeshCore"',
            "window.location.href = contactUrl",
            'copyButton.textContent = "Copiar ligazón"',
            "navigator.clipboard?.writeText",
            'document.execCommand("copy")',
            "meshcoreAppSection(node),",
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, self.javascript)

        self.assertIn(
            "./app.js?v=20260809-meshcore-activity1",
            self.parser.scripts,
        )

    def test_node_detail_prioritizes_direct_neighbors(
        self,
    ) -> None:
        neighbors = self.javascript.index(
            'title: "Veciños directos"'
        )
        traceroutes = self.javascript.index(
            'title: "Traceroutes"',
            neighbors,
        )

        self.assertLess(neighbors, traceroutes)
        self.assertIn(
            '"Non hai veciños directos publicados "',
            self.javascript,
        )
        self.assertIn(
            '"Non hai traceroutes publicados "',
            self.javascript,
        )

    def test_neighbors_render_above_traceroutes(
        self,
    ) -> None:
        for expected in (
            "function edgeRenderPriority(edge)",
            'edge.edge_type === "neighbor" ? 1 : 0',
            "function edgesInRenderOrder(edges)",
            "edgesInRenderOrder(regularEdges)",
            "edgesInRenderOrder(selectedEdges)",
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, self.javascript)

    def test_selected_node_highlights_its_traceroutes(
        self,
    ) -> None:
        required_javascript = (
            "selectedNodeId: null",
            "function edgeTouchesSelectedNode(edge)",
            "function renderVisibleEdges()",
            "state.selectedNodeId = node.id",
            "const selected = edgeTouchesSelectedNode(edge)",
            'state.currentBaseMapName === "satellite"',
            '? "#a61e4d"',
            "const routePoints = [",
            'satellite ? "#845ef7" : "#5f3dc4"',
            "weight: selected ? 1.6 : 1.5",
            "satellite ? 0.62 : 0.48",
            "function edgeEndpointsAreVisible(edge)",
            "const candidateEdges = state.edges.filter(",
            "const selectedRouteIds = selectedMeshcoreRouteIds(",
            "const selectedEdges = state.edges.filter(",
            "edgeBelongsToSelectedMeshcoreRoute(",
            "const regularEdges = candidateEdges.filter(",
            "!edgeTouchesSelectedNode(edge)",
            "&& globalEdgeEnabled(",
            "routeCompleteness",
            "function closeNodeDetail()",
            "state.selectedNodeId = null",
        )

        for text in required_javascript:
            self.assertIn(text, self.javascript)

        self.assertIn(
            ".route-arrow.selected",
            self.css,
        )

    def test_global_traceroutes_have_source_and_age_filters(
        self,
    ) -> None:
        for expected in (
            'id="traceroute-controls"',
            'aria-label="Filtros dos traceroutes"',
            'aria-expanded="false"',
            'id="traceroute-source"',
            'value="ozulo_map"',
            "Comunidade O Zulo",
            'value="meshview_es" selected',
            "Meshview España",
            'value="malha_pt"',
            "Malha Portugal",
            'value="all"',
            "Todas as fontes",
            'id="traceroute-age"',
            'value="day" selected',
            "Últimas 24 horas",
            'value="week"',
            "Últimos 7 días",
            "Todo o histórico",
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, self.html)

        for expected in (
            "function tracerouteSourceMatches(edge)",
            "function tracerouteAgeMatches(edge)",
            'selectedSource === "all"',
            "edge.source === selectedSource",
            'selectedAge === "all"',
            "state.generatedAt?.getTime()",
            "Date.parse(edge.last_seen ||",
            'selectedAge === "day"',
            "24 * 7",
            "&& tracerouteSourceMatches(edge)",
            "&& tracerouteAgeMatches(edge)",
            "function updateTracerouteControlsVisibility()",
            "elements.tracerouteControls.hidden = !enabled",
            "elements.tracerouteSource.disabled = !enabled",
            "elements.tracerouteAge.disabled = !enabled",
            '"aria-expanded",',
            "elements.tracerouteSource.addEventListener(",
            "elements.tracerouteAge.addEventListener(",
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, self.javascript)

        traceroute_block = self.html[
            self.html.index('id="traceroutes-toggle"'):
            self.html.index('id="neighbors-toggle"')
        ]

        self.assertNotIn(
            "checked",
            traceroute_block,
        )
        self.assertIn(
            "hidden",
            traceroute_block,
        )

        for expected in (
            ".traceroute-filters {",
            ".traceroute-filters[hidden] {",
            ".traceroute-filters select {",
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, self.css)

    def test_selected_meshcore_node_shows_complete_observed_routes(
        self,
    ) -> None:
        for expected in (
            "function selectedMeshcoreRouteIds(edges)",
            'edge.edge_type === "observed"',
            'edge.network === "meshcore"',
            "edge.route_id",
            "edgeTouchesSelectedNode(edge)",
            ".map((edge) => edge.route_id)",
            "function edgeBelongsToSelectedMeshcoreRoute(",
            "routeIds.has(edge.route_id)",
            "const selectedRouteIds = selectedMeshcoreRouteIds(",
            "const selectedEdges = state.edges.filter(",
            "edgeBelongsToSelectedMeshcoreRoute(",
            "selectedRouteIds",
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, self.javascript)

    def test_fragmented_meshcore_routes_are_detected_from_route_index(
        self,
    ) -> None:
        required_javascript = (
            "function meshcoreRouteFragments(edges)",
            "edge.route_index",
            "left.route_id === right.route_id",
            "right.route_index > left.route_index + 1",
            "function addMeshcoreRouteGap(",
            "meshcore-route-gap",
            "Ruta incompleta",
        )

        for expected in required_javascript:
            with self.subTest(expected=expected):
                self.assertIn(expected, self.javascript)

        self.assertIn(
            ".meshcore-route-gap",
            self.css,
        )

    def test_selected_node_connections_ignore_global_toggles(
        self,
    ) -> None:
        selected_block = self.javascript[
            self.javascript.index(
                "const selectedEdges = state.edges.filter("
            ):
            self.javascript.index(
                "const regularEdges = candidateEdges.filter("
            )
        ]

        self.assertIn(
            "edgeTouchesSelectedNode",
            selected_block,
        )
        self.assertIn(
            "edgeBelongsToSelectedMeshcoreRoute",
            selected_block,
        )
        self.assertNotIn(
            "globalEdgeEnabled",
            selected_block,
        )

        regular_block = self.javascript[
            self.javascript.index(
                "const regularEdges = candidateEdges.filter("
            ):
            self.javascript.index(
                "const edge of edgesInRenderOrder(regularEdges)"
            )
        ]

        self.assertIn(
            "state.selectedNodeId === null",
            regular_block,
        )
        self.assertIn(
            "globalEdgeEnabled(",
            regular_block,
        )
        self.assertIn(
            "routeCompleteness",
            regular_block,
        )

    def test_selected_node_shows_reliable_position_precision(
        self,
    ) -> None:
        required_javascript = (
            "nodePrecisionCircle: null",
            "function positionPrecisionRadiusMeters(node)",
            "node.position_precision_bits",
            "node.position_precision_bits == null",
            "node.latitude == null",
            "Math.pow(2, 32 - precisionBits)",
            "function clearSelectedNodePrecision()",
            "function renderSelectedNodePrecision(node)",
            "radius <= 10",
            'pane: "precision"',
            "state.nodePrecisionCircle = L.circle(",
            "renderSelectedNodePrecision(node);",
            'state.map.createPane("precision")',
            'style.zIndex = "380"',
            'color: "#d000ff"',
            "weight: 1.5,",
            "opacity: 0.75,",
            "fillOpacity: 0.06,",
            "function precisionFocusZoom(node)",
            "radius <= 1_500",
            "radius <= 3_000",
            "radius <= 5_000",
            "precisionFocusZoom(node)",
            "{ animate: false }",
        )

        for text in required_javascript:
            self.assertIn(text, self.javascript)

        self.assertGreaterEqual(
            self.javascript.count(
                "clearSelectedNodePrecision();"
            ),
            3,
        )

    def test_overlay_palette_is_distinct_from_osm(
        self,
    ) -> None:
        for expected in (
            "--network-meshtastic: #267a4d;",
            "--network-meshcore: #675184;",
            "--traceroute: #5f3dc4;",
            "--neighbor: #343a40;",
            "background: var(--network-meshtastic);",
            "background: var(--network-meshcore);",
            "rgb(38 122 77 / 0.82)",
            "rgb(103 81 132 / 0.82)",
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, self.css)

        for expected in (
            'satellite ? "#845ef7" : "#5f3dc4"',
            'selected ? "#006d77" : "#343a40"',
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, self.javascript)

    def test_mixed_clusters_show_both_networks(
        self,
    ) -> None:
        self.assertNotIn("conic-gradient(", self.css)

        for expected in (
            ".node-cluster.mixed",
            ".legend-cluster.mixed",
            "linear-gradient(",
            "var(--network-meshtastic) 0 48.5%",
            "rgb(255 255 255 / 0.84) 48.5% 51.5%",
            "var(--network-meshcore) 51.5% 100%",
            "-0.6px -0.6px 0 rgb(31 35 48 / 0.78)",
            "0.6px 0.6px 0 rgb(31 35 48 / 0.78)",
            "0 1px 2px rgb(31 35 48 / 0.52)",
            "Highlight 48.5% 51.5%",
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, self.css)

        for unexpected in (
            ".node-cluster.mixed::before",
            ".legend-cluster.mixed::before",
            "0 0 0 4px var(--network-meshcore)",
        ):
            with self.subTest(unexpected=unexpected):
                self.assertNotIn(unexpected, self.css)

    def test_meshtastic_roles_have_distinct_visual_styles(
        self,
    ) -> None:
        roles = (
            "CLIENT",
            "CLIENT_BASE",
            "CLIENT_MUTE",
            "ROUTER",
            "ROUTER_LATE",
            "TRACKER",
            "unknown",
        )

        for role in roles:
            self.assertIn(
                f"{role}: {{",
                self.javascript,
            )

        self.assertIn(
            "function meshtasticRoleKey(node)",
            self.javascript,
        )
        self.assertIn(
            "MESHTASTIC_ROLE_STYLES[",
            self.javascript,
        )
        self.assertIn(
            "weight: base.weight ?? 1.5",
            self.javascript,
        )

        role_classes = (
            "meshtastic-client",
            "meshtastic-client-base",
            "meshtastic-client-mute",
            "meshtastic-router",
            "meshtastic-router-late",
            "meshtastic-tracker",
            "meshtastic-unknown",
        )

        for role_class in role_classes:
            self.assertIn(
                f"legend-symbol {role_class}",
                self.html,
            )
            self.assertIn(
                f".legend-symbol.{role_class}",
                self.css,
            )

        for expected in (
            ".node-marker-visual.role-router,",
            ".node-marker-visual.role-router-late {",
            ".legend-symbol.meshtastic-router,",
            ".legend-symbol.meshtastic-router-late {",
            "clip-path: polygon(",
            "25% 6.7%,",
            "100% 50%,",
            "0 50%",
            ".node-marker-visual.role-router.selected,",
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, self.css)

        for age_class in (
            "age-hour",
            "age-day",
            "age-week",
            "age-month",
        ):
            self.assertIn(
                f"age-dot {age_class}",
                self.html,
            )
            self.assertIn(
                f".age-dot.{age_class}",
                self.css,
            )

    def test_meshtastic_clients_use_inner_marks(
        self,
    ) -> None:
        for expected in (
            ".node-marker-visual.role-client-base::after,",
            ".legend-symbol.meshtastic-client-base::after",
            "width: 42%;",
            "border: 2px solid #ffffff;",
            ".node-marker-visual.role-client-mute::after,",
            ".legend-symbol.meshtastic-client-mute::after",
            "width: 64%;",
            "height: 4px;",
            ".node-marker-visual.role-tracker::after,",
            ".legend-symbol.meshtastic-tracker::after",
            "width: 66%;",
            "radial-gradient(",
            "center top / 3px 28% no-repeat",
            "center bottom / 3px 28% no-repeat",
            "left center / 28% 3px no-repeat",
            "right center / 28% 3px no-repeat",
            "linear-gradient(Canvas, Canvas)",
            "linear-gradient(HighlightText, HighlightText)",
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, self.css)

    def test_meshcore_unknown_symbol_matches_map(
        self,
    ) -> None:
        for expected in (
            ".node-marker-visual.network-meshcore.type-unknown {",
            ".legend-symbol.meshcore-unknown {",
            "border-radius: 0;",
            "border-style: dashed;",
            "background: transparent;",
            ".node-marker-visual.network-meshcore.type-unknown,\n"
            "  .legend-symbol.meshcore-unknown",
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, self.css)

    def test_clustering_zoom_names_and_visual_system(
        self,
    ) -> None:
        expected_cluster_assets = (
            "./vendor/leaflet.markercluster/"
            "MarkerCluster.css?v=1.5.3-local1",
            "./vendor/leaflet.markercluster/"
            "MarkerCluster.Default.css?v=1.5.3-local1",
        )

        for asset in expected_cluster_assets:
            self.assertIn(asset, self.parser.links)

        self.assertIn(
            "./vendor/leaflet.markercluster/"
            "leaflet.markercluster.js?v=1.5.3-local1",
            self.parser.scripts,
        )

        self.assertNotIn(
            "unpkg.com/leaflet.markercluster",
            self.html,
        )

        vendor = FRONTEND / "vendor" / "leaflet.markercluster"

        for relative_path in (
            "leaflet.markercluster.js",
            "MarkerCluster.css",
            "MarkerCluster.Default.css",
            "MIT-LICENCE.txt",
        ):
            self.assertTrue(
                (vendor / relative_path).is_file()
            )

        required_javascript = (
            "L.markerClusterGroup({",
            "return zoom < 12 ? 44 : 0.01;",
            "zoomToBoundsOnClick: false",
            "spiderfyOnMaxZoom: false",
            "iconCreateFunction: createClusterIcon",
            "function renderVisibleNodes()",
            "function nodeMapLabelName(node, zoom)",
            "function nodeMapLabelAllowed(node, zoom)",
            "function nodeMapLabelPriority(node)",
            "function renderNodeLabels()",
            "function scheduleNodeLabels()",
            "getVisibleParent(marker) === marker",
            "nodeMapLabelRectanglesOverlap",
            "const rawName = zoom >= 14",
            'state.map.on("moveend", scheduleNodeLabels)',
            "function isPriorityName(node)",
            "function createNodeIcon(node)",
            "L.divIcon({",
            "Math.max(state.map.getZoom(), 15)",
            "maxZoom: 12",
            "Math.round(style.radius * 3.15)",
            "iconSize: [52, 52]",
        )

        for text in required_javascript:
            self.assertIn(text, self.javascript)

        required_css = (
            ".node-marker-visual",
            ".node-cluster.meshtastic",
            ".node-cluster.meshcore",
            ".node-cluster.mixed",
            ".node-map-label-icon",
            ".node-map-label",
            ".node-map-label.selected",
            ".node-map-label.network-meshtastic",
            ".node-map-label.network-meshcore",
            "font-size: 0.78rem",
            "font-size: 0.88rem",
            "font-size: 0.72rem",
            ".network-meshcore.type-repeater",
            ".network-meshcore.type-room-server",
            ".network-meshcore.type-client",
            "--meshcore-client: #ffd43b",
            "--meshtastic-router: #e03131",
            "--meshtastic-router-late: #f08c00",
        )

        for text in required_css:
            self.assertIn(text, self.css)

        for cluster_class in (
            "legend-cluster meshtastic",
            "legend-cluster meshcore",
            "legend-cluster mixed",
        ):
            self.assertIn(cluster_class, self.html)

    def test_identical_positions_can_be_spiderfied(
        self,
    ) -> None:
        required_javascript = (
            "function clusterSharesExactPosition(cluster)",
            "cluster.getAllChildMarkers()",
            "first.lat === position.lat",
            "first.lng === position.lng",
            "function activateCluster(event)",
            "cluster.spiderfy();",
            "cluster.zoomToBounds();",
            '"clusterclick clusterkeypress"',
            "return zoom < 12 ? 44 : 0.01;",
            "zoomToBoundsOnClick: false",
            "spiderfyOnMaxZoom: false",
        )

        for expected in required_javascript:
            with self.subTest(expected=expected):
                self.assertIn(expected, self.javascript)

        self.assertNotIn(
            "disableClusteringAtZoom",
            self.javascript,
        )

    def test_collapsible_and_interactive_filters(
        self,
    ) -> None:
        required_html = (
            'id="age-details-home"',
            'id="age-details"',
            'id="legend-details-home"',
            'id="legend-details"',
            'id="legend-information-home"',
            'id="legend-information"',
            'id="source-details"',
            'id="age-summary"',
            'id="type-summary"',
            'id="type-filter-reset"',
            'id="mqtt-gateway-filter"',
            'id="mqtt-gateway-summary"',
            "Características Meshtastic",
            "Gateway MQTT",
            "O aro violeta identifica gateways confirmados;",
            "a cor e a forma interiores indican o rol.",
            'class="feature-filter"',
            'aria-pressed="false"',
            'id="filter-empty-panel"',
            'value="hour"',
            'value="day"',
            'value="week"',
            'value="month"',
            'data-category="meshtastic:ROUTER"',
            'data-category="meshcore:repeater"',
            'aria-pressed="true"',
            "Tipos de nodos e símbolos",
        )

        for text in required_html:
            with self.subTest(html=text):
                self.assertIn(text, self.html)

        self.assertEqual(
            self.html.count('class="legend-filter"'),
            11,
        )

        self.assertNotIn(
            '<p class="legend-heading">Actividade</p>',
            self.html,
        )

        required_javascript = (
            "const AGE_LABELS",
            "const AGE_OPACITY",
            "function ageKey(node)",
            "function categoryKey(node)",
            "function selectedAgeBands()",
            "function selectedCategories()",
            "function isMqttGateway(node)",
            "function matchesBaseFilters(node)",
            "node.radio?.mqtt_gateway === true",
            "function updateMqttGatewaySummary()",
            "elements.mqttGatewayFilter.addEventListener(",
            '"aria-pressed"',
            'String(!enabled)',
            "function updateFilterSummaries()",
            "function initializeResponsiveDetails()",
            "function storedDetailsState(details)",
            "categories.has(categoryKey(node))",
            "state.generatedAt = generatedAt",
            "elements.filterEmptyPanel.hidden",
        )

        for text in required_javascript:
            with self.subTest(javascript=text):
                self.assertIn(text, self.javascript)

        required_css = (
            ".filter-details > summary",
            ".filter-details > summary::after",
            ".filter-details[open] > summary::after",
            ".filter-details > summary::-webkit-details-marker",
            ".legend-filter-list",
            ".feature-filter",
            ".feature-filter-copy",
            ".legend-symbol.mqtt-gateway",
            "0 0 0 4px #7048e8;",
            '.feature-filter[aria-pressed="true"]',
            '.legend-filter[aria-pressed="false"]',
            ".cluster-legend",
            ".age-dot.age-hour",
            ".age-dot.age-month",
        )

        for text in required_css:
            with self.subTest(css=text):
                self.assertIn(text, self.css)

    def test_meshcore_observers_are_identified(
        self,
    ) -> None:
        for expected in (
            'node.is_observer === true',
            '" meshcore-observer"',
            '`${nodeName(node)} · Observer`',
            '"Función no Hub"',
            '"observer observador"',
        ):
            with self.subTest(javascript=expected):
                self.assertIn(expected, self.javascript)

        for expected in (
            ".node-marker-badge.meshcore-observer::after",
            ".legend-symbol.meshcore-observer",
            "border: 2px dashed #087f8c;",
            "width: calc(var(--node-size) + 14px);",
        ):
            with self.subTest(css=expected):
                self.assertIn(expected, self.css)

        self.assertIn(
            "Observer de MeshCore Hub",
            self.html,
        )
        self.assertIn(
            "./styles.css?v=20260809-meshcore-activity1",
            self.parser.links,
        )
        self.assertIn(
            "./app.js?v=20260809-meshcore-activity1",
            self.parser.scripts,
        )

    def test_meshcore_observer_filter_is_available(
        self,
    ) -> None:
        for expected in (
            'id="meshcore-observer-filter"',
            'id="meshcore-observer-summary"',
            "Só Observers MeshCore",
            "Mostra unicamente os observers publicados",
            "polo Hub.",
        ):
            with self.subTest(html=expected):
                self.assertIn(expected, self.html)

        for expected in (
            "meshcoreObserverFilter: document.querySelector(",
            '"#meshcore-observer-filter"',
            "meshcoreObserverSummary: document.querySelector(",
            '"#meshcore-observer-summary"',
            "function isMeshcoreObserver(node)",
            'node.network === "meshcore"',
            "node.is_observer === true",
            "function meshcoreObserverFilterEnabled()",
            "function updateMeshcoreObserverSummary()",
            "elements.meshcoreObserverFilter.addEventListener(",
        ):
            with self.subTest(javascript=expected):
                self.assertIn(expected, self.javascript)

        matches_start = self.javascript.index(
            "function matchesFilters(node)"
        )
        matches_end = self.javascript.index(
            "function searchText(node)",
            matches_start,
        )
        matches = self.javascript[matches_start:matches_end]

        self.assertIn(
            "!meshcoreObserverFilterEnabled()",
            matches,
        )
        self.assertIn(
            "|| isMeshcoreObserver(node)",
            matches,
        )


    def test_meshcore_activity_mode_uses_hub_receptions(
        self,
    ) -> None:
        for expected in (
            'id="meshcore-activity-filter"',
            'aria-controls="meshcore-activity-controls"',
            "Actividade MeshCore",
            "Destaca os nodos vistos recentemente",
            'id="meshcore-activity-window"',
            'value="hour"',
            'value="day" selected',
            'value="week"',
        ):
            with self.subTest(html=expected):
                self.assertIn(expected, self.html)

        for expected in (
            "const MESHCORE_ACTIVITY_WINDOWS",
            "meshcoreActivityByNodeId: new Map()",
            "function meshcoreActivityEnabled()",
            "function selectedMeshcoreActivityHours()",
            "function meshcoreActivityForNode(node)",
            '" meshcore-activity-visible"',
            '" meshcore-activity-muted"',
            "function updateMeshcoreActivitySummary()",
            "function updateMeshcoreActivityControls()",
            "state.meshcoreActivityByNodeId.set(",
            "elements.meshcoreActivityFilter.addEventListener(",
            "elements.meshcoreActivityWindow.addEventListener(",
        ):
            with self.subTest(javascript=expected):
                self.assertIn(expected, self.javascript)

        for expected in (
            ".node-marker-badge.meshcore-activity-muted",
            ".node-marker-badge.meshcore-activity-visible",
            ".legend-symbol.meshcore-activity",
            ".feature-filter-options",
            ".feature-filter-options[hidden]",
        ):
            with self.subTest(css=expected):
                self.assertIn(expected, self.css)

        self.assertIn(
            "20260809-meshcore-activity1",
            self.html,
        )


    def test_mqtt_gateways_have_a_persistent_map_ring(
        self,
    ) -> None:
        for expected in (
            'const gatewayClass = isMqttGateway(node)',
            '" mqtt-gateway"',
            'class="node-marker-badge${gatewayClass}${observerClass}${activityClass}"',
        ):
            with self.subTest(javascript=expected):
                self.assertIn(expected, self.javascript)

        for expected in (
            ".node-marker-badge {",
            ".node-marker-badge.mqtt-gateway::before",
            "width: calc(var(--node-size) + 8px);",
            "height: calc(var(--node-size) + 8px);",
            "border: 2px solid #7048e8;",
            "z-index: 1;",
        ):
            with self.subTest(css=expected):
                self.assertIn(expected, self.css)

    def test_network_filter_preserves_map_view(
        self,
    ) -> None:
        network_start = self.javascript.index(
            ".querySelectorAll('input[name=\"network\"]')"
        )
        age_start = self.javascript.index(
            ".querySelectorAll('input[name=\"age\"]')",
            network_start,
        )
        listener = self.javascript[network_start:age_start]

        self.assertIn("applyFilters();", listener)
        self.assertNotIn("fit: true", listener)

    def test_visible_summary_follows_node_legend(
        self,
    ) -> None:
        legend_position = self.html.index(
            'id="legend-details"'
        )
        summary_position = self.html.index(
            "<h2>Resumo visible</h2>"
        )
        source_position = self.html.index(
            'id="source-details"'
        )

        self.assertLess(legend_position, summary_position)
        self.assertLess(summary_position, source_position)

    def test_street_and_satellite_basemaps_are_available(
        self,
    ) -> None:
        for expected in (
            'id="basemap-filter"',
            'name="basemap"',
            'value="street"',
            'value="satellite"',
            "<span>Mapa</span>",
            "<span>Satélite</span>",
        ):
            with self.subTest(html=expected):
                self.assertIn(expected, self.html)

        for expected in (
            "baseLayers: new Map()",
            "currentBaseLayer: null",
            'currentBaseMapName: "street"',
            "function setBaseMap(name)",
            "state.currentBaseMapName = name",
            'state.currentBaseMapName === "satellite"',
            "renderVisibleEdges();",
            "World_Imagery/MapServer/tile/{z}/{y}/{x}",
            '["street", streetLayer]',
            '["satellite", satelliteLayer]',
            "elements.basemapInputs",
            "setBaseMap(input.value)",
        ):
            with self.subTest(javascript=expected):
                self.assertIn(expected, self.javascript)

        self.assertIn(
            ".segmented-control.basemap-control",
            self.css,
        )

    def test_selected_connections_are_less_obtrusive(
        self,
    ) -> None:
        self.assertIn(
            "weight: selected ? 1.6 : 1.5",
            self.javascript,
        )
        self.assertIn(
            "weight: selected ? 2.6 : 2.2",
            self.javascript,
        )
        self.assertNotIn(
            "weight: selected ? 4 :",
            self.javascript,
        )

    def test_map_tools_are_grouped_for_desktop_and_mobile(
        self,
    ) -> None:
        required_html = (
            "<h2>Mapa</h2>",
            '<p class="control-subheading">Conexións</p>',
            '<p class="control-subheading">Vista</p>',
            '<p class="control-subheading">Localización</p>',
            "<span>Tipos de nodos e símbolos</span>",
            "<span>Conexións</span>",
            "<span>Lenda e filtros</span>",
            "<span>Mapa</span>",
        )

        for text in required_html:
            with self.subTest(html=text):
                self.assertIn(text, self.html)

        self.assertIn(
            'filters: "Lenda e filtros"',
            self.javascript,
        )
        self.assertIn('layers: "Mapa"', self.javascript)
        self.assertIn(".control-subheading", self.css)

    def test_desktop_collapse_and_mobile_toolbar(
        self,
    ) -> None:
        desktop_html = (
            'id="sidebar-toggle"',
            'id="sidebar-controls"',
            'id="sidebar-panel"',
            'id="desktop-collapsed-nav"',
            'data-desktop-target="search"',
            'data-desktop-target="network"',
            'data-desktop-target="filters"',
            'data-desktop-target="layers"',
            'data-desktop-target="info"',
            "Ocultar controis",
        )

        for text in desktop_html:
            with self.subTest(desktop_html=text):
                self.assertIn(text, self.html)

        mobile_html = (
            'id="mobile-toolbar"',
            'id="mobile-backdrop"',
            'id="mobile-sheet-title"',
            'id="mobile-sheet-close"',
            'id="mobile-data-status"',
            'data-mobile-target="search"',
            'data-mobile-target="network"',
            'data-mobile-target="filters"',
            'data-mobile-target="layers"',
            'data-mobile-target="info"',
            'data-mobile-panel="search"',
            'data-mobile-panel="network"',
            'data-mobile-panel="filters"',
            'data-mobile-panel="layers"',
            'data-mobile-panel="info"',
        )

        for text in mobile_html:
            with self.subTest(mobile_html=text):
                self.assertIn(text, self.html)

        self.assertEqual(
            self.html.count('class="mobile-tab"'),
            5,
        )
        self.assertEqual(
            self.html.count('class="desktop-rail-button"'),
            5,
        )

        required_javascript = (
            "const MOBILE_BREAKPOINT",
            "const MOBILE_PANEL_TITLES",
            "const DESKTOP_PANEL_TARGETS",
            'filters: "#legend-details"',
            "window.setTimeout(invalidate, 220)",
            "block.getBoundingClientRect()",
            "elements.sidebar.scrollTo({",
            "function openDesktopControlPanel(target)",
            "let activeMobilePanel = null",
            "elements.desktopCollapsedNav.hidden",
            "elements.desktopRailButtons",
            "function openDesktopControlPanel(target)",
            "button.dataset.desktopTarget",
            "function isMobileLayout()",
            "function arrangeResponsiveFilterSections()",
            "elements.ageDetailsHome.after(",
            "elements.legendDetails.after(",
            "elements.ageDetails.after(",
            "elements.legendInformationHome.after(",
            "function openMobileFilterSections()",
            "function setMobilePanel(",
            "elements.ageDetails.open = true",
            "elements.legendDetails.open = true",
            "elements.sidebar.scrollTop = 0",
            "function synchronizeResponsiveNavigation()",
            "function initializeResponsiveNavigation()",
            "block.dataset.mobilePanel !== activeMobilePanel",
            "button.dataset.mobileTarget",
            '"mobile-sheet-open"',
            "initializeResponsiveNavigation();",
            'event.key === "Escape"',
            "elements.mobileBackdrop.addEventListener(",
        )

        for text in required_javascript:
            with self.subTest(javascript=text):
                self.assertIn(text, self.javascript)

        required_css = (
            "minmax(18.5rem, 21.5rem)",
            ".desktop-collapsed-nav",
            ".desktop-rail-button",
            ".desktop-rail-icon svg",
            ".mobile-toolbar",
            ".mobile-tab",
            '.mobile-tab[aria-pressed="true"]',
            ".mobile-backdrop",
            ".mobile-sheet-heading",
            ".app-shell.mobile-sheet-open .sidebar",
            "max-height: min(70dvh, 43rem)",
            "height: 100dvh",
            "grid-template-columns: repeat(5, minmax(0, 1fr))",
        )

        for text in required_css:
            with self.subTest(css=text):
                self.assertIn(text, self.css)

    def test_leaflet_scripts_load_in_dependency_order(
        self,
    ) -> None:
        script_tags = re.findall(
            r'<script\b[^>]*\bsrc="[^"]+"[^>]*></script>',
            self.html,
            flags=re.DOTALL,
        )

        dependencies = []

        for tag in script_tags:
            match = re.search(
                r'\bsrc="([^"]+)"',
                tag,
            )

            if match is None:
                continue

            source = match.group(1)

            if (
                "leaflet@1.9.4/dist/leaflet.js" in source
                or "leaflet.markercluster.js" in source
                or source == "./app.js?v=20260809-meshcore-activity1"
            ):
                dependencies.append((source, tag))

        self.assertEqual(
            [
                source
                for source, _tag in dependencies
            ],
            [
                "https://unpkg.com/leaflet@1.9.4/"
                "dist/leaflet.js",
                "./vendor/leaflet.markercluster/"
                "leaflet.markercluster.js?v=1.5.3-local1",
                "./app.js?v=20260809-meshcore-activity1",
            ],
        )

        for source, tag in dependencies:
            with self.subTest(source=source):
                self.assertRegex(tag, r"\bdefer\b")

    def test_node_withdrawal_contacts_are_public(
        self,
    ) -> None:
        self.assertIn(
            "mailto:elena@tuiterx.rocks",
            self.html,
        )
        self.assertIn(
            "https://t.me/+ulPcpc4QDYc2ZTE0",
            self.html,
        )
        self.assertRegex(
            self.html,
            r"solicitar a exclusión dun nodo",
        )
        self.assertRegex(
            self.html,
            r"identificador completo\s+do nodo",
        )

    def test_privacy_notice_is_informational_and_dismissible(
        self,
    ) -> None:
        self.assertRegex(
            self.html,
            r"non utiliza cookies\s+nin ferramentas de seguimento",
        )
        self.assertRegex(
            self.html,
            r"As preferencias gárdanse só\s+neste navegador",
        )
        self.assertRegex(
            self.html,
            r"úsase unicamente\s+no teu dispositivo e non se envía",
        )
        self.assertIn(
            'aria-label="Información sobre privacidade"',
            self.html,
        )
        self.assertRegex(
            self.html,
            r">\s*Entendido\s*</button>",
        )
        self.assertIn(".privacy-notice {", self.css)
        self.assertIn(
            "PRIVACY_STORAGE_KEY",
            self.javascript,
        )
        self.assertIn(
            "window.localStorage.getItem(",
            self.javascript,
        )
        self.assertIn(
            "window.localStorage.setItem(",
            self.javascript,
        )
        self.assertIn(
            "elements.privacyNotice.hidden = false",
            self.javascript,
        )
        self.assertIn(
            "elements.privacyNotice.hidden = true",
            self.javascript,
        )
        self.assertNotIn(
            "document.cookie",
            self.javascript,
        )
        self.assertNotIn("Aceptar", self.html)
        self.assertNotIn("Rexeitar", self.html)

    def test_geolocation_is_local_and_permission_based(
        self,
    ) -> None:
        self.assertIn(
            "navigator.geolocation",
            self.javascript,
        )
        self.assertIn(
            "getCurrentPosition",
            self.javascript,
        )
        self.assertIn(
            "window.isSecureContext",
            self.javascript,
        )
        self.assertIn(
            "enableHighAccuracy: true",
            self.javascript,
        )
        self.assertRegex(
            self.html,
            r"non se\s+garda nin se envía",
        )

    def test_mobile_control_sheet_is_modal_and_traps_focus(
        self,
    ) -> None:
        self.assertLess(
            self.html.index('id="mobile-backdrop"'),
            self.html.index('<main class="map-region">'),
        )

        for expected in (
            'tabindex="-1"',
            "const FOCUSABLE_SELECTOR",
            "function setDialogState(",
            'element.setAttribute("role", "dialog")',
            'element.setAttribute("aria-modal", "true")',
            "function syncModalAccessibility()",
            "elements.mapContainer.inert = sheetOpen;",
            "elements.detailPanel.inert = sheetOpen;",
            "function trapKeyboardFocus(event, container)",
            "trapKeyboardFocus(event, elements.sidebar);",
            "syncModalAccessibility();",
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, self.javascript)

    def test_mobile_node_detail_keeps_map_interactive(
        self,
    ) -> None:
        for forbidden in (
            "const detailOpen =",
            "elements.mapContainer.inert = sheetOpen || detailOpen;",
            "elements.mobileToolbar.inert = detailOpen;",
            "elements.sidebar.inert = detailOpen;",
            "trapKeyboardFocus(event, elements.detailPanel);",
            '"detail-title",',
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, self.javascript)

        self.assertIn(
            'event.key === "Escape"',
            self.javascript,
        )
        self.assertIn(
            "restoreDetailTrigger();",
            self.javascript,
        )

    def test_node_detail_restores_focus(
        self,
    ) -> None:
        for expected in (
            "let lastDetailTrigger = null;",
            "function rememberDetailTrigger()",
            "function restoreDetailTrigger()",
            "elements.searchResults.contains(activeElement)",
            "restoreDetailTrigger();",
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, self.javascript)

    def test_mobile_detail_keeps_node_visible(
        self,
    ) -> None:
        for expected in (
            "function keepNodeVisibleAboveDetail(node)",
            "state.map.getContainer().getBoundingClientRect()",
            "elements.detailPanel.getBoundingClientRect()",
            "state.map.latLngToContainerPoint(",
            "state.map.panBy(",
            "keepNodeVisibleAboveDetail(node);",
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, self.javascript)

    def test_mobile_search_closes_before_node_detail(
        self,
    ) -> None:
        self.assertIn(
            """      if (isMobileLayout()) {
        setMobilePanel(null);
      }

      focusNode(node);""",
            self.javascript,
        )
        self.assertIn(
            """isMobileLayout()
          ? lastMobileTrigger
          : elements.search""",
            self.javascript,
        )

    def test_search_announces_dynamic_results(
        self,
    ) -> None:
        for expected in (
            'role="search"',
            'aria-labelledby="node-search-label"',
            'aria-describedby="node-search-help"',
            'id="node-search-status"',
            'role="status"',
            'aria-live="polite"',
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, self.html)

        for expected in (
            'searchStatus: document.querySelector(',
            'elements.searchStatus.textContent = "";',
            '"1 resultado dispoñible."',
            'resultados dispoñibles.',
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, self.javascript)

    def test_map_uses_region_semantics(
        self,
    ) -> None:
        self.assertIn(
            'role="region"',
            self.html,
        )
        self.assertIn(
            'aria-label="Mapa interactivo de nodos Meshtastic e MeshCore"',
            self.html,
        )
        self.assertNotIn(
            'role="application"',
            self.html,
        )

    def test_mobile_panel_uses_soft_violet_palette(
        self,
    ) -> None:
        for expected in (
            "background: rgb(252 251 255 / 0.96);",
            "border: 1px solid #d9d4e8;",
            "box-shadow: 0 8px 24px rgb(52 46 73 / 0.18);",
            "background: #eee9ff;",
            "color: var(--network-meshtastic);",
            "color: #5e6a66;",
            "background: rgb(49 43 68 / 0.14);",
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, self.css)

        backdrop = re.search(
            r"\.mobile-backdrop\s*\{(?P<body>.*?)\n  \}",
            self.css,
            flags=re.DOTALL,
        )
        self.assertIsNotNone(backdrop)
        backdrop_css = backdrop.group("body")
        self.assertIn("backdrop-filter: none;", backdrop_css)
        self.assertNotIn("blur(", backdrop_css)

    def test_configuration_warnings_have_accessible_styles(
        self,
    ) -> None:
        for expected in (
            ".configuration-warning-list",
            'li[data-severity="medium"]',
            'li[data-severity="high"]',
            'li[data-severity="critical"]',
            ".configuration-warning-date",
            "@media (forced-colors: active)",
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, self.css)

        self.assertIn(
            "20260809-meshcore-activity1",
            self.html,
        )

    def test_interface_uses_compact_violet_controls(
        self,
    ) -> None:
        for expected in (
            "/* Pulido visual exclusivo de escritorio. */",
            "@media (min-width: 781px)",
            "minmax(18rem, 19rem)",
            "padding-block: 0.85rem;",
            "background: var(--network-meshtastic);",
            "accent-color: var(--network-meshtastic);",
            "border: 1px solid var(--network-meshtastic);",
            "color: var(--network-meshtastic);",
            '.legend-filter[aria-pressed="true"]',
            "border-color: #cfc5f2;",
            "background: #f7f4ff;",
            ".filter-details > summary::after",
            "--age-hour: #5f3dc4;",
            "--age-month: #bbb3e5;",
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, self.css)

        self.assertIn(
            "./styles.css?v=20260809-meshcore-activity1",
            self.parser.links,
        )

    def test_detail_panel_uses_soft_neutral_palette(
        self,
    ) -> None:
        for expected in (
            "background: rgb(252 251 255 / 0.98);",
            "box-shadow: 0 14px 36px rgb(52 46 73 / 0.2);",
            ".detail-panel .icon-button",
            "background: #f7f4ff;",
            "--heading: #33464f;",
            "color: var(--heading);",
            "color: var(--network-meshtastic);",
            "color: #5e6a66;",
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, self.css)

        self.assertNotIn(
            "color: var(--network-meshcore);",
            self.css,
        )

    def test_checkbox_rows_have_large_targets_and_visible_focus(
        self,
    ) -> None:
        for expected in (
            "min-height: 2.75rem;",
            ".check-list label:has(input:focus-visible)",
            ".toggle-row:has(input:focus-visible)",
            ".check-list input:focus-visible",
            ".toggle-row input:focus-visible",
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, self.css)

    def test_forced_colors_preserve_map_symbols(
        self,
    ) -> None:
        for expected in (
            "@media (forced-colors: active)",
            "forced-color-adjust: none;",
            ".node-marker-visual.selected",
            ".node-cluster.mixed",
            ".legend-cluster.mixed",
            "border-top-color: CanvasText !important;",
            "color: Highlight;",
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, self.css)

    def test_mobile_map_attribution_is_compact(
        self,
    ) -> None:
        for expected in (
            "state.map.attributionControl.setPrefix(false)",
            '"&copy; Esri, Maxar, Earthstar Geographics, "',
            '+ "GIS User Community"',
        ):
            with self.subTest(javascript=expected):
                self.assertIn(expected, self.javascript)

        for expected in (
            "max-width: calc(100vw - 0.9rem);",
            "padding: 1px 3px;",
            "font-size: 0.56rem;",
            "line-height: 1.1;",
            "white-space: nowrap;",
        ):
            with self.subTest(css=expected):
                self.assertIn(expected, self.css)

    def test_accessibility_and_mobile_rules_exist(
        self,
    ) -> None:
        self.assertIn(":focus-visible", self.css)
        self.assertIn(
            "@media (max-width: 780px)",
            self.css,
        )
        self.assertIn(
            "prefers-reduced-motion",
            self.css,
        )
        self.assertIn(
            'aria-live="polite"',
            self.html,
        )


    def test_node_tooltip_escapes_html(
        self,
    ) -> None:
        escape_start = self.javascript.index(
            "function escapeHtmlText(value) {"
        )
        start = self.javascript.index(
            "function bindNodeTooltip(marker, node) {"
        )
        end = self.javascript.index(
            "\nfunction refreshNodeMarker(",
            start,
        )
        function = self.javascript[escape_start:end]

        for expected in (
            '.replaceAll("&", "&amp;")',
            '.replaceAll("<", "&lt;")',
            '.replaceAll(">", "&gt;")',
            "escapeHtmlText(name)",
            "marker.bindTooltip(",
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, function)

        self.assertNotIn(
            'document.createElement("span")',
            function,
        )



if __name__ == "__main__":
    unittest.main()
