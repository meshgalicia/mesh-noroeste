"""Probas estruturais do frontend experimental."""

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]

HTML_PATH = (
    ROOT
    / "frontend"
    / "experiment"
    / "index.html"
)

JS_PATH = (
    ROOT
    / "frontend"
    / "experiment"
    / "experiment.js"
)

CSS_PATH = (
    ROOT
    / "frontend"
    / "experiment"
    / "experiment.css"
)


class ExperimentFrontendTests(
    unittest.TestCase
):
    @classmethod
    def setUpClass(cls) -> None:
        cls.html = HTML_PATH.read_text()
        cls.javascript = JS_PATH.read_text()
        cls.css = CSS_PATH.read_text()

    def test_experiment_has_independent_entrypoint(
        self,
    ) -> None:
        for expected in (
            "<title>",
            "Experimento LongFast / NarrowFast",
            "./experiment.css?v=",
            "./experiment.js?v=",
            "../data/experiment.json",
        ):
            self.assertIn(
                expected,
                self.html + self.javascript,
            )

    def test_experiment_uses_expected_contract(
        self,
    ) -> None:
        for expected in (
            'const EXPERIMENT_URL = "../data/experiment.json";',
            '"mesh-noroeste.meshtastic-experiment/v1"',
            "document.schema !== EXPECTED_SCHEMA",
        ):
            self.assertIn(
                expected,
                self.javascript,
            )

    def test_experiment_has_main_navigation(
        self,
    ) -> None:
        for expected in (
            'aria-label="Navegación principal"',
            '<a href="../">',
            '<a href="../live/">',
            '<a href="../history/">',
            "Mapa",
            "Tráfico en directo",
            "Histórico",
        ):
            self.assertIn(
                expected,
                self.html,
            )

    def test_experiment_exposes_open_data(
        self,
    ) -> None:
        for expected in (
            "../data/experiment.xlsx",
            "../data/experiment.csv",
            "../data/experiment-territories.csv",
            "../data/experiment.json",
            "Descargar XLSX",
            "Descargar CSV",
            "Descargar CSV territorial",
            "Ver JSON",
        ):
            self.assertIn(
                expected,
                self.html,
            )

    def test_experiment_has_comparable_window(
        self,
    ) -> None:
        for expected in (
            'id="comparison-window-panel"',
            'id="comparison-window-status"',
            'id="comparison-window-summary"',
            'id="comparison-window-channels"',
            'id="comparison-summary-grid"',
            'id="common-comparison-period"',
            "function renderComparisonWindow(report)",
            "function renderComparisonSummary(report)",
        ):
            self.assertIn(
                expected,
                self.html + self.javascript,
            )

    def test_experiment_has_sample_quality(
        self,
    ) -> None:
        for expected in (
            'id="sample-quality-grid"',
            'id="comparison-readiness"',
            "function sampleQualityForChannel(",
            "function comparisonReadiness(",
            "function renderSampleQuality(report)",
            ".sample-quality-badge",
        ):
            self.assertIn(
                expected,
                self.html
                + self.javascript
                + self.css,
            )

    def test_experiment_distinguishes_accumulated_data(
        self,
    ) -> None:
        for expected in (
            "Cobertura acumulada",
            "Todo o recollido",
            'id="summary-grid"',
            "non deben empregarse como comparación directa",
            "function renderSummaries(document)",
        ):
            self.assertIn(
                expected,
                self.html + self.javascript,
            )

    def test_experiment_has_territorial_distribution(
        self,
    ) -> None:
        for expected in (
            'href="#territories"',
            'id="territories"',
            'id="territories-grid"',
            "Distribución territorial",
            "Onde se observa cada preset?",
            "function renderTerritories(report)",
            "function territoryChannelCard(",
            "function territoryProvinceMetric(",
            "function territoryProvinceList(",
            "function territoryMunicipalityList(",
            "ChUtil media",
            "Air Util TX media",
            "SNR medio",
            "RSSI medio",
            ".territory-province-metrics",
            ".territory-province-hint",
            ".territory-province-icon",
            ".territory-province-chevron",
            "Toca unha provincia",
            "function territoryUncertainty(",
            "report.territories",
            "renderTerritories(report);",
            ".territories-grid",
            ".territory-card",
            ".territory-details",
            "Compatible",
            "Ambiguos",
            "Sen localizar",
        ):
            self.assertIn(
                expected,
                self.html
                + self.javascript
                + self.css,
            )


    def test_experiment_can_compare_same_territory_by_preset(
        self,
    ) -> None:
        for expected in (
            'id="territory-comparison-level"',
            'id="territory-comparison-select"',
            'id="territory-comparison-status"',
            'id="territory-comparison-grid"',
            "Comparación territorial",
            "LongFast / NarrowFast no mesmo territorio",
            "function territoryComparisonEntries(",
            "function territoryComparisonCard(",
            "function populateTerritoryComparison(",
            "function renderTerritoryComparisonSelection(",
            "function setupTerritoryComparison(",
            "Sen observacións deste preset",
            "setupTerritoryComparison(report);",
            ".territory-comparison-controls",
            ".territory-comparison-grid",
            ".territory-comparison-card",
            ".territory-comparison-metrics",
        ):
            self.assertIn(
                expected,
                self.html
                + self.javascript
                + self.css,
            )


    def test_experiment_has_time_series(
        self,
    ) -> None:
        for expected in (
            'id="chart-packets"',
            'id="chart-snr"',
            'id="chart-rssi"',
            'id="chart-gateways"',
            'id="chart-utilization"',
            'id="chart-air-tx"',
            "function renderChart(",
            "function numericSeries(",
        ):
            self.assertIn(
                expected,
                self.html + self.javascript,
            )

    def test_experiment_has_methodological_limits(
        self,
    ) -> None:
        for expected in (
            "Que estamos medindo",
            "Límites dos datos",
            "Taxa de entrega",
            "Colisións",
            "Latencia",
            "RSSI/SNR 0/0",
            "function methodologyEntries(",
        ):
            self.assertIn(
                expected,
                self.html + self.javascript,
            )


    def test_experiment_uses_clear_comparison_language(
        self,
    ) -> None:
        for expected in (
            "Solapamento temporal",
            "Período con datos simultáneos",
            "O solapamento temporal só confirma",
            "Duración simultánea",
            "function countLabel(",
            '"nodo distinto"',
            '"nodos distintos"',
            '"paquete observado"',
            '"paquetes observados"',
        ):
            self.assertIn(
                expected,
                self.html
                + self.javascript,
            )



    def test_experiment_is_responsive(
        self,
    ) -> None:
        for expected in (
            "@media (max-width: 820px)",
            "@media (max-width: 520px)",
            "grid-template-columns: 1fr",
        ):
            self.assertIn(
                expected,
                self.css,
            )


    def test_experiment_explains_available_evidence(
        self,
    ) -> None:
        for expected in (
            'id="evidence-title"',
            'id="evidence-status"',
            'id="evidence-grid"',
            'id="evidence-limitations"',
            "Que evidencia temos agora?",
            "function evidenceCard(",
            "function evidenceLimitation(",
            "function renderEvidence(report)",
            "report.evidence || {}",
            "evidence.observational?.available === true",
            "evidence.controlled?.available === true",
            "observational_data_does_not_isolate_preset_effect",
            "Efecto do preset",
            "Taxa de entrega",
            "Colisións",
            "Latencia",
            "renderEvidence(report);",
            ".evidence-panel",
            ".evidence-grid",
            ".evidence-limitations",
        ):
            self.assertIn(
                expected,
                self.html
                + self.javascript
                + self.css,
            )


    def test_experiment_has_test_situation_panel(
        self,
    ) -> None:
        for expected in (
            'id="test-situation-title"',
            'id="test-situation-badge"',
            'id="test-situation-summary"',
            'id="test-situation-metrics"',
            "Situación da proba",
            "Esta páxina acompaña unha proba en curso.",
            "function renderTestSituation(report)",
            "function testSituationMetric(",
            "renderTestSituation(report);",
            '"Proba en fase inicial"',
            '"Á espera de mostra NarrowFast"',
            '"Proba en recollida"',
            '"Mostra descritiva dispoñible"',
            ".test-situation",
            ".test-situation-badge",
            ".test-situation-metrics",
        ):
            self.assertIn(
                expected,
                self.html
                + self.javascript
                + self.css,
            )



    def test_experiment_has_derived_comparable_indicators(
        self,
    ) -> None:
        for expected in (
            'id="derived-indicators-grid"',
            "Indicadores derivados",
            "Proporcións dentro da xanela comparable",
            "function percentageLabel(",
            "function derivedIndicator(",
            "function derivedChannelCard(",
            "function renderDerivedIndicators(report)",
            "renderDerivedIndicators(report);",
            "packets_multi_gateway",
            "packets_with_rf",
            "route_discovery_packets",
            "telemetry_samples",
            '"stages"',
            ".derived-indicators-grid",
        ):
            self.assertIn(
                expected,
                self.html
                + self.javascript
                + self.css,
            )



    def test_experiment_charts_expose_metric_semantics(
        self,
    ) -> None:
        for expected in (
            'label = field',
            'unit = ""',
            "`Serie temporal de ${label}${unitSuffix}`",
            'label: "Paquetes observados"',
            'unit: "paquetes"',
            'label: "SNR medio"',
            'unit: "dB"',
            'label: "RSSI medio"',
            'unit: "dBm"',
            'label: "Gateways observadores por paquete"',
            'label: "Ocupación media do canal"',
            'label: "Air util TX medio"',
        ):
            self.assertIn(
                expected,
                self.javascript,
            )


    def test_experiment_charts_have_accessible_summary(
        self,
    ) -> None:
        for expected in (
            'summary.className = "chart-accessible-summary";',
            "availableChannels",
            "datos dispoñibles para",
            ".chart-accessible-summary",
        ):
            self.assertIn(
                expected,
                self.javascript + self.css,
            )


    def test_experiment_presets_do_not_rely_only_on_colour(
        self,
    ) -> None:
        for expected in (
            ".chart-line.narrowfast",
            "stroke-dasharray: 9 6",
            '"· liña continua"',
            '"· liña descontinua"',
        ):
            self.assertIn(
                expected,
                self.css,
            )



    def test_experiment_has_internal_section_navigation(
        self,
    ) -> None:
        for expected in (
            'class="experiment-sections"',
            'aria-label="Seccións do experimento"',
            'href="#test-situation"',
            'href="#evidence"',
            'href="#comparison"',
            'href="#series"',
            'href="#methodology"',
            'id="test-situation"',
            'id="evidence"',
            'id="comparison"',
            'id="series"',
            'id="methodology"',
            ".experiment-sections",
            "position: sticky",
            "scroll-margin-top: 5rem",
        ):
            self.assertIn(
                expected,
                self.html + self.css,
            )


if __name__ == "__main__":
    unittest.main()
