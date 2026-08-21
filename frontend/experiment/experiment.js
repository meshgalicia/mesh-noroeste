"use strict";

const EXPERIMENT_URL = "../data/experiment.json";

const EXPECTED_SCHEMA = (
  "mesh-noroeste.meshtastic-experiment/v1"
);

const CHANNELS = Object.freeze([
  "LongFast",
  "NarrowFast",
]);

const elements = {
  status: document.querySelector(
    "#experiment-status"
  ),
  testSituationBadge: document.querySelector(
    "#test-situation-badge"
  ),
  testSituationSummary: document.querySelector(
    "#test-situation-summary"
  ),
  testSituationMetrics: document.querySelector(
    "#test-situation-metrics"
  ),
  evidenceStatus: document.querySelector(
    "#evidence-status"
  ),
  evidenceGrid: document.querySelector(
    "#evidence-grid"
  ),
  evidenceLimitations: document.querySelector(
    "#evidence-limitations"
  ),
  summaryGrid: document.querySelector(
    "#summary-grid"
  ),
  sampleWarning: document.querySelector(
    "#sample-warning"
  ),
  sampleQualityGrid: document.querySelector(
    "#sample-quality-grid"
  ),
  comparisonReadiness: document.querySelector(
    "#comparison-readiness"
  ),
  comparisonWindowPanel: document.querySelector(
    "#comparison-window-panel"
  ),
  comparisonWindowStatus: document.querySelector(
    "#comparison-window-status"
  ),
  comparisonWindowSummary: document.querySelector(
    "#comparison-window-summary"
  ),
  comparisonWindowChannels: document.querySelector(
    "#comparison-window-channels"
  ),
  comparisonSummaryGrid: document.querySelector(
    "#comparison-summary-grid"
  ),
  commonComparisonPeriod: document.querySelector(
    "#common-comparison-period"
  ),
  commonComparisonNote: document.querySelector(
    "#common-comparison-note"
  ),
  derivedIndicatorsGrid: document.querySelector(
    "#derived-indicators-grid"
  ),
  territoriesGrid: document.querySelector(
    "#territories-grid"
  ),
  territoryComparisonLevel: document.querySelector(
    "#territory-comparison-level"
  ),
  territoryComparisonSelect: document.querySelector(
    "#territory-comparison-select"
  ),
  territoryComparisonStatus: document.querySelector(
    "#territory-comparison-status"
  ),
  territoryComparisonGrid: document.querySelector(
    "#territory-comparison-grid"
  ),
  bucketDescription: document.querySelector(
    "#bucket-description"
  ),
  methodologyGrid: document.querySelector(
    "#methodology-grid"
  ),
};

function formatNumber(
  value,
  digits = 0,
) {
  if (
    typeof value !== "number"
    || !Number.isFinite(value)
  ) {
    return "—";
  }

  return new Intl.NumberFormat(
    "gl-ES",
    {
      maximumFractionDigits: digits,
      minimumFractionDigits: digits,
    }
  ).format(value);
}

function countLabel(
  value,
  singular,
  plural,
) {
  const count = Number(value) || 0;

  return (
    `${formatNumber(count)} `
    + (count === 1 ? singular : plural)
  );
}


function formatDateTime(value) {
  if (
    typeof value !== "string"
    || !value
  ) {
    return "—";
  }

  const date = new Date(value);

  if (
    Number.isNaN(
      date.getTime()
    )
  ) {
    return value;
  }

  return new Intl.DateTimeFormat(
    "gl-ES",
    {
      dateStyle: "short",
      timeStyle: "short",
      timeZone: "UTC",
    }
  ).format(date) + " UTC";
}

function formatDuration(
  seconds,
) {
  if (
    typeof seconds !== "number"
    || !Number.isFinite(seconds)
    || seconds < 0
  ) {
    return "—";
  }

  const rounded = Math.round(seconds);

  const hours = Math.floor(
    rounded / 3600
  );

  const minutes = Math.floor(
    (
      rounded % 3600
    ) / 60
  );

  const remainingSeconds = (
    rounded % 60
  );

  const parts = [];

  if (hours > 0) {
    parts.push(
      `${hours} h`
    );
  }

  if (
    minutes > 0
    || hours > 0
  ) {
    parts.push(
      `${minutes} min`
    );
  }

  parts.push(
    `${remainingSeconds} s`
  );

  return parts.join(" ");
}


function testSituationMetric(
  label,
  value,
) {
  const wrapper = document.createElement(
    "div"
  );

  wrapper.className = "test-situation-metric";

  const term = document.createElement("span");
  term.textContent = label;

  const definition = document.createElement(
    "strong"
  );
  definition.textContent = value;

  wrapper.append(
    term,
    definition,
  );

  return wrapper;
}


function renderTestSituation(report) {
  if (
    !elements.testSituationBadge
    || !elements.testSituationSummary
    || !elements.testSituationMetrics
  ) {
    return;
  }

  const longfast = (
    report.channels?.LongFast || {}
  );

  const narrowfast = (
    report.channels?.NarrowFast || {}
  );

  const comparison = (
    report.comparison_window
  );

  const longPackets = (
    Number(longfast.packets) || 0
  );

  const narrowPackets = (
    Number(narrowfast.packets) || 0
  );

  const narrowNodes = (
    Number(narrowfast.nodes) || 0
  );

  const narrowRf = (
    Number(narrowfast.rf_samples) || 0
  );

  const hasCommonWindow = (
    comparison?.available === true
  );

  let level = "initial";
  let badge = "Proba en fase inicial";
  let summary = (
    "A infraestrutura de recollida está funcionando, "
    + "pero a mostra NarrowFast aínda non permite "
    + "unha comparación representativa."
  );

  if (narrowPackets === 0) {
    level = "waiting";
    badge = "Á espera de mostra NarrowFast";
    summary = (
      "A recollida LongFast está activa, pero aínda "
      + "non hai tráfico NarrowFast almacenado para "
      + "comezar a validar a comparación."
    );
  } else if (
    narrowPackets >= 30
    && narrowNodes >= 3
    && narrowRf >= 30
  ) {
    level = "collecting";
    badge = "Proba en recollida";
    summary = (
      "Xa existe unha base inicial nos dous presets. "
      + "Cómpre seguir recollendo datos antes de "
      + "interpretar diferenzas como resultados da proba."
    );
  }

  if (
    narrowPackets >= 100
    && narrowNodes >= 10
    && narrowRf >= 100
  ) {
    level = "comparable";
    badge = "Mostra descritiva dispoñible";
    summary = (
      "A mostra xa permite iniciar comparacións "
      + "descritivas entre presets, mantendo as "
      + "limitacións metodolóxicas indicadas nesta páxina."
    );
  }

  elements.testSituationBadge.className = (
    "test-situation-badge "
    + level
  );

  elements.testSituationBadge.textContent = badge;
  elements.testSituationSummary.textContent = summary;

  elements.testSituationMetrics.replaceChildren(
    testSituationMetric(
      "LongFast",
      countLabel(
        longPackets,
        "paquete",
        "paquetes",
      ),
    ),
    testSituationMetric(
      "NarrowFast",
      countLabel(
        narrowPackets,
        "paquete",
        "paquetes",
      ),
    ),
    testSituationMetric(
      "Nodos NarrowFast",
      countLabel(
        narrowNodes,
        "nodo",
        "nodos",
      ),
    ),
    testSituationMetric(
      "Mostras RF NarrowFast",
      countLabel(
        narrowRf,
        "mostra",
        "mostras",
      ),
    ),
    testSituationMetric(
      "Xanela común",
      hasCommonWindow
        ? "Dispoñible"
        : "Aínda non",
    ),
  );
}


function evidenceCard({
  title,
  status,
  text,
  available,
}) {
  const article = document.createElement(
    "article"
  );

  article.className = (
    "evidence-card "
    + (
      available
        ? "available"
        : "unavailable"
    )
  );

  const header = document.createElement(
    "header"
  );

  const heading = document.createElement(
    "h3"
  );

  heading.textContent = title;

  const badge = document.createElement(
    "span"
  );

  badge.className = "evidence-badge";
  badge.textContent = status;

  header.append(
    heading,
    badge,
  );

  const copy = document.createElement("p");
  copy.textContent = text;

  article.append(
    header,
    copy,
  );

  return article;
}


function evidenceLimitation(
  title,
  text,
) {
  const article = document.createElement(
    "article"
  );

  article.className = "evidence-limitation";

  const heading = document.createElement(
    "strong"
  );

  heading.textContent = title;

  const copy = document.createElement("p");
  copy.textContent = text;

  article.append(
    heading,
    copy,
  );

  return article;
}


function renderEvidence(report) {
  if (
    !elements.evidenceStatus
    || !elements.evidenceGrid
    || !elements.evidenceLimitations
  ) {
    return;
  }

  const evidence = (
    report.evidence || {}
  );

  const methodology = (
    report.methodology || {}
  );

  const observationalAvailable = (
    evidence.observational?.available === true
  );

  const controlledAvailable = (
    evidence.controlled?.available === true
  );

  elements.evidenceGrid.replaceChildren(
    evidenceCard({
      title: "Observación da rede",
      status: (
        observationalAvailable
          ? "Dispoñible"
          : "Non dispoñible"
      ),
      text: (
        observationalAvailable
          ? (
            "A recollida pasiva permite describir "
            + "tráfico observado, diversidade de nodos, "
            + "recepcións RF cando existen, gateways, "
            + "RouteDiscovery e telemetría dispoñible."
          )
          : (
            "A fonte observacional non está dispoñible "
            + "neste informe."
          )
      ),
      available: observationalAvailable,
    }),
    evidenceCard({
      title: "Probas controladas",
      status: (
        controlledAvailable
          ? "Dispoñibles"
          : "Pendentes"
      ),
      text: (
        controlledAvailable
          ? (
            "O informe incorpora resultados procedentes "
            + "de probas controladas documentadas."
          )
          : (
            "Aínda non se incorporaron probas con envíos "
            + "e condicións controladas. Serán necesarias "
            + "para medir determinadas magnitudes con rigor."
          )
      ),
      available: controlledAvailable,
    }),
  );

  const limitations = [];

  if (
    methodology
      .observational_data_does_not_isolate_preset_effect
  ) {
    limitations.push([
      "Efecto do preset",
      (
        "Os datos observacionais non permiten atribuír "
        + "por si sós unha diferenza directamente ao preset. "
        + "Tamén inflúen nodos, localizacións, horarios, "
        + "tráfico e condicións de propagación."
      ),
    ]);
  }

  if (
    methodology.delivery_rate_requires_controlled_test
  ) {
    limitations.push([
      "Taxa de entrega",
      (
        "Para calcular unha taxa de entrega real hai que "
        + "coñecer cantos paquetes se enviaron de forma "
        + "controlada e cantos chegaron."
      ),
    ]);
  }

  if (
    methodology.collisions_are_not_directly_observed
  ) {
    limitations.push([
      "Colisións",
      (
        "As observacións dispoñibles non permiten confirmar "
        + "directamente unha colisión física de radio."
      ),
    ]);
  }

  if (
    methodology.ingestion_delay_is_not_radio_latency
  ) {
    limitations.push([
      "Latencia",
      (
        "O tempo de chegada dos datos ao sistema non equivale "
        + "á latencia extremo a extremo da comunicación LoRa."
      ),
    ]);
  }

  elements.evidenceLimitations.replaceChildren(
    ...limitations.map(
      ([title, text]) => (
        evidenceLimitation(
          title,
          text,
        )
      )
    )
  );

  if (
    observationalAvailable
    && !controlledAvailable
  ) {
    elements.evidenceStatus.className = (
      "evidence-status observational"
    );

    elements.evidenceStatus.textContent = (
      "Evidencia observacional activa · "
      + "probas controladas pendentes"
    );

    return;
  }

  if (
    observationalAvailable
    && controlledAvailable
  ) {
    elements.evidenceStatus.className = (
      "evidence-status complete"
    );

    elements.evidenceStatus.textContent = (
      "Evidencia observacional e controlada dispoñible"
    );

    return;
  }

  elements.evidenceStatus.className = (
    "evidence-status unavailable"
  );

  elements.evidenceStatus.textContent = (
    "Sen evidencia dispoñible"
  );
}


function comparisonWindowMetric(
  label,
  value,
) {
  const wrapper = document.createElement(
    "div"
  );

  wrapper.className = (
    "comparison-window-metric"
  );

  const labelElement = document.createElement(
    "span"
  );

  labelElement.textContent = label;

  const valueElement = document.createElement(
    "strong"
  );

  valueElement.textContent = value;

  wrapper.append(
    labelElement,
    valueElement,
  );

  return wrapper;
}


function comparisonWindowChannelCard(
  channel,
  summary,
) {
  const article = document.createElement(
    "article"
  );

  article.className = (
    "comparison-window-channel "
    + channel.toLowerCase()
  );

  const header = document.createElement(
    "header"
  );

  const title = document.createElement(
    "h4"
  );

  title.textContent = channel;

  const period = document.createElement(
    "span"
  );

  if (
    summary?.oldest_at
    && summary?.newest_at
  ) {
    period.textContent = (
      `${formatDateTime(summary.oldest_at)}`
      + " → "
      + `${formatDateTime(summary.newest_at)}`
    );
  } else {
    period.textContent = "Sen observacións";
  }

  header.append(
    title,
    period,
  );

  const metrics = document.createElement(
    "dl"
  );

  const values = [
    [
      "Paquetes",
      formatNumber(
        summary?.packets
      ),
    ],
    [
      "Nodos",
      formatNumber(
        summary?.nodes
      ),
    ],
    [
      "Mostras RF",
      formatNumber(
        summary?.rf_samples
      ),
    ],
    [
      "Paquetes con RF",
      formatNumber(
        summary?.packets_with_rf
      ),
    ],
    [
      "Telemetría",
      formatNumber(
        summary?.telemetry_samples
      ),
    ],
    [
      "Gateways media",
      formatNumber(
        metricValue(
          summary,
          "gateways",
          "mean",
        ),
        2,
      ),
    ],
  ];

  for (
    const [label, value]
    of values
  ) {
    const wrapper = document.createElement(
      "div"
    );

    const term = document.createElement(
      "dt"
    );

    term.textContent = label;

    const definition = document.createElement(
      "dd"
    );

    definition.textContent = value;

    wrapper.append(
      term,
      definition,
    );

    metrics.append(wrapper);
  }

  article.append(
    header,
    metrics,
  );

  return article;
}


function renderComparisonWindow(report) {
  if (
    !elements.comparisonWindowPanel
    || !elements.comparisonWindowStatus
    || !elements.comparisonWindowSummary
    || !elements.comparisonWindowChannels
  ) {
    return;
  }

  const comparison = (
    report.comparison_window
  );

  elements.comparisonWindowSummary
    .replaceChildren();

  elements.comparisonWindowChannels
    .replaceChildren();

  if (
    !comparison
    || typeof comparison !== "object"
    || comparison.available !== true
  ) {
    elements.comparisonWindowStatus.className = (
      "comparison-window-status unavailable"
    );

    const missing = (
      Array.isArray(
        comparison?.missing_channels
      )
        ? comparison.missing_channels
        : []
    );

    elements.comparisonWindowStatus.textContent = (
      missing.length
        ? (
          "Aínda non existe unha xanela común: "
          + missing.join(", ")
        )
        : (
          "Aínda non existe unha xanela "
          + "temporal común calculable."
        )
    );

    elements.comparisonWindowSummary.append(
      comparisonWindowMetric(
        "Estado",
        "Sen solapamento suficiente",
      )
    );

    return;
  }

  elements.comparisonWindowStatus.className = (
    "comparison-window-status available"
  );

  elements.comparisonWindowStatus.textContent = (
    "Hai observacións dos dous presets durante "
    + "o mesmo período temporal."
  );

  elements.comparisonWindowSummary.append(
    comparisonWindowMetric(
      "Duración simultánea",
      formatDuration(
        comparison.duration_seconds
      ),
    ),
    comparisonWindowMetric(
      "Inicio común",
      formatDateTime(
        comparison.start_at
      ),
    ),
    comparisonWindowMetric(
      "Fin común",
      formatDateTime(
        comparison.end_at
      ),
    ),
  );

  const channels = (
    comparison.channels
  );

  if (
    !channels
    || typeof channels !== "object"
  ) {
    return;
  }

  for (const channel of CHANNELS) {
    const summary = (
      channels[channel]
    );

    if (
      !summary
      || typeof summary !== "object"
    ) {
      continue;
    }

    elements.comparisonWindowChannels.append(
      comparisonWindowChannelCard(
        channel,
        summary,
      )
    );
  }
}


function metricValue(
  summary,
  group,
  field,
) {
  const value = summary?.[group];

  if (
    !value
    || typeof value !== "object"
  ) {
    return null;
  }

  return value[field];
}

function metricBlock(
  label,
  value,
) {
  const wrapper = document.createElement("div");
  wrapper.className = "metric";

  const term = document.createElement("dt");
  term.textContent = label;

  const definition = document.createElement("dd");
  definition.textContent = value;

  wrapper.append(
    term,
    definition,
  );

  return wrapper;
}

function renderSummaryCard(
  channel,
  summary,
) {
  const article = document.createElement(
    "article"
  );

  article.className = (
    "summary-card "
    + channel.toLowerCase()
  );

  const header = document.createElement(
    "header"
  );

  header.className = "summary-card-header";

  const title = document.createElement("h3");
  title.textContent = channel;

  const period = document.createElement("span");

  if (
    summary.oldest_at
    && summary.newest_at
  ) {
    period.textContent = (
      `${formatDateTime(summary.oldest_at)}`
      + " → "
      + `${formatDateTime(summary.newest_at)}`
    );
  } else {
    period.textContent = "Sen datos";
  }

  header.append(
    title,
    period,
  );

  const metrics = document.createElement(
    "dl"
  );

  metrics.className = "metrics-grid";

  metrics.append(
    metricBlock(
      "Paquetes",
      formatNumber(summary.packets)
    ),
    metricBlock(
      "Nodos",
      formatNumber(summary.nodes)
    ),
    metricBlock(
      "Mostras RF",
      formatNumber(summary.rf_samples)
    ),
    metricBlock(
      "Paquetes >1 gateway",
      formatNumber(
        summary.packets_multi_gateway
      )
    ),
    metricBlock(
      "RouteDiscovery",
      formatNumber(
        summary.route_discovery_packets
      )
    ),
    metricBlock(
      "Telemetría",
      formatNumber(
        summary.telemetry_samples
      )
    ),
    metricBlock(
      "SNR mediana",
      formatNumber(
        metricValue(
          summary,
          "snr",
          "median",
        ),
        2,
      )
    ),
    metricBlock(
      "RSSI mediana",
      formatNumber(
        metricValue(
          summary,
          "rssi",
          "median",
        ),
        2,
      )
    ),
    metricBlock(
      "Gateways media",
      formatNumber(
        metricValue(
          summary,
          "gateways",
          "mean",
        ),
        2,
      )
    ),
    metricBlock(
      "Channel utilization",
      formatNumber(
        metricValue(
          summary,
          "channel_utilization",
          "mean",
        ),
        2,
      )
    ),
    metricBlock(
      "Air util TX",
      formatNumber(
        metricValue(
          summary,
          "air_util_tx",
          "mean",
        ),
        2,
      )
    ),
    metricBlock(
      "Paquetes con RF",
      formatNumber(
        summary.packets_with_rf
      )
    ),
  );

  article.append(
    header,
    metrics,
  );

  return article;
}

function renderSummaries(document) {
  elements.summaryGrid.replaceChildren();

  for (const channel of CHANNELS) {
    const summary = (
      document.channels?.[channel]
    );

    if (
      !summary
      || typeof summary !== "object"
    ) {
      continue;
    }

    elements.summaryGrid.append(
      renderSummaryCard(
        channel,
        summary,
      )
    );
  }
}

const SAMPLE_QUALITY_LEVELS = Object.freeze({
  NONE: "none",
  INSUFFICIENT: "insufficient",
  LIMITED: "limited",
  REASONABLE: "reasonable",
});


const SAMPLE_QUALITY_LABELS = Object.freeze({
  none: "Sen datos",
  insufficient: "Insuficiente",
  limited: "Limitada",
  reasonable: "Razoable",
});


function qualityTraffic(
  packets,
  referencePackets,
) {
  const value = (
    Number(packets) || 0
  );

  const reference = (
    Number(referencePackets) || 0
  );

  if (value === 0) {
    return SAMPLE_QUALITY_LEVELS.NONE;
  }

  if (
    value < 30
    || (
      reference > 0
      && value < reference * 0.1
    )
  ) {
    return SAMPLE_QUALITY_LEVELS.INSUFFICIENT;
  }

  if (value < 100) {
    return SAMPLE_QUALITY_LEVELS.LIMITED;
  }

  return SAMPLE_QUALITY_LEVELS.REASONABLE;
}


function qualityNodes(nodes) {
  const value = (
    Number(nodes) || 0
  );

  if (value === 0) {
    return SAMPLE_QUALITY_LEVELS.NONE;
  }

  if (value < 3) {
    return SAMPLE_QUALITY_LEVELS.INSUFFICIENT;
  }

  if (value < 10) {
    return SAMPLE_QUALITY_LEVELS.LIMITED;
  }

  return SAMPLE_QUALITY_LEVELS.REASONABLE;
}


function qualityRf(samples) {
  const value = (
    Number(samples) || 0
  );

  if (value === 0) {
    return SAMPLE_QUALITY_LEVELS.NONE;
  }

  if (value < 30) {
    return SAMPLE_QUALITY_LEVELS.INSUFFICIENT;
  }

  if (value < 100) {
    return SAMPLE_QUALITY_LEVELS.LIMITED;
  }

  return SAMPLE_QUALITY_LEVELS.REASONABLE;
}


function qualityTelemetry(samples) {
  const value = (
    Number(samples) || 0
  );

  if (value === 0) {
    return SAMPLE_QUALITY_LEVELS.NONE;
  }

  if (value < 10) {
    return SAMPLE_QUALITY_LEVELS.INSUFFICIENT;
  }

  if (value < 30) {
    return SAMPLE_QUALITY_LEVELS.LIMITED;
  }

  return SAMPLE_QUALITY_LEVELS.REASONABLE;
}


function sampleQualityForChannel(
  summary,
  referencePackets,
) {
  return {
    traffic: qualityTraffic(
      summary?.packets,
      referencePackets,
    ),
    diversity: qualityNodes(
      summary?.nodes,
    ),
    rf: qualityRf(
      summary?.rf_samples,
    ),
    telemetry: qualityTelemetry(
      summary?.telemetry_samples,
    ),
  };
}


function sampleQualityDescription(
  dimension,
  summary,
) {
  if (dimension === "traffic") {
    return (
      countLabel(
        summary?.packets,
        "paquete observado",
        "paquetes observados",
      )
    );
  }

  if (dimension === "diversity") {
    return (
      countLabel(
        summary?.nodes,
        "nodo distinto",
        "nodos distintos",
      )
    );
  }

  if (dimension === "rf") {
    return (
      countLabel(
        summary?.rf_samples,
        "mostra RSSI/SNR válida",
        "mostras RSSI/SNR válidas",
      )
    );
  }

  if (dimension === "telemetry") {
    return (
      countLabel(
        summary?.telemetry_samples,
        "mostra de ocupación",
        "mostras de ocupación",
      )
    );
  }

  return "";
}


function sampleQualityTitle(
  dimension,
) {
  const titles = {
    traffic: "Tráfico",
    diversity: "Diversidade",
    rf: "RF",
    telemetry: "Ocupación",
  };

  return (
    titles[dimension]
    || dimension
  );
}


function createQualityBadge(level) {
  const badge = document.createElement(
    "span"
  );

  badge.className = (
    "sample-quality-badge "
    + level
  );

  badge.textContent = (
    SAMPLE_QUALITY_LABELS[level]
    || level
  );

  return badge;
}


function createQualityCard(
  channel,
  summary,
  quality,
) {
  const article = document.createElement(
    "article"
  );

  article.className = (
    "sample-quality-card "
    + channel.toLowerCase()
  );

  const header = document.createElement(
    "header"
  );

  header.className = (
    "sample-quality-card-header"
  );

  const title = document.createElement("h4");
  title.textContent = channel;

  const samples = document.createElement(
    "span"
  );

  samples.textContent = (
    countLabel(
      summary?.packets,
      "paquete",
      "paquetes",
    )
  );

  header.append(
    title,
    samples,
  );

  const list = document.createElement("ul");
  list.className = "sample-quality-list";

  for (const dimension of [
    "traffic",
    "diversity",
    "rf",
    "telemetry",
  ]) {
    const item = document.createElement("li");
    item.className = "sample-quality-item";

    const label = document.createElement(
      "div"
    );

    label.className = (
      "sample-quality-item-label"
    );

    const strong = document.createElement(
      "strong"
    );

    strong.textContent = (
      sampleQualityTitle(
        dimension
      )
    );

    const detail = document.createElement(
      "span"
    );

    detail.textContent = (
      sampleQualityDescription(
        dimension,
        summary,
      )
    );

    label.append(
      strong,
      detail,
    );

    item.append(
      label,
      createQualityBadge(
        quality[dimension]
      ),
    );

    list.append(item);
  }

  article.append(
    header,
    list,
  );

  return article;
}


function comparisonReadiness(
  qualities,
) {
  const requiredDimensions = [
    "traffic",
    "diversity",
    "rf",
  ];

  const levels = [];

  for (const channel of CHANNELS) {
    const quality = qualities[channel];

    if (!quality) {
      continue;
    }

    for (
      const dimension
      of requiredDimensions
    ) {
      levels.push(
        quality[dimension]
      );
    }
  }

  if (
    levels.some(
      (level) => (
        level === SAMPLE_QUALITY_LEVELS.NONE
        || level
          === SAMPLE_QUALITY_LEVELS.INSUFFICIENT
      )
    )
  ) {
    return {
      level: "not-ready",
      text: (
        "A comparación aínda non está preparada "
        + "para extraer conclusións LongFast / NarrowFast."
      ),
    };
  }

  if (
    levels.some(
      (level) => (
        level
        === SAMPLE_QUALITY_LEVELS.LIMITED
      )
    )
  ) {
    return {
      level: "limited",
      text: (
        "Xa existe unha base comparativa, "
        + "pero algunhas dimensións seguen limitadas."
      ),
    };
  }

  return {
    level: "ready",
    text: (
      "A mostra xa é razoable para iniciar "
      + "comparacións descritivas entre presets."
    ),
  };
}


function renderSampleQuality(report) {
  if (
    !elements.sampleQualityGrid
    || !elements.comparisonReadiness
  ) {
    return;
  }

  elements.sampleQualityGrid.replaceChildren();

  const comparison = (
    report.comparison_window
  );

  const summaries = (
    comparison?.available === true
    && comparison.channels
    && typeof comparison.channels === "object"
      ? comparison.channels
      : {}
  );

  const referencePackets = Math.max(
    ...CHANNELS.map(
      (channel) => (
        Number(
          summaries[channel]?.packets
        ) || 0
      )
    ),
  );

  const qualities = {};

  for (const channel of CHANNELS) {
    const summary = (
      summaries[channel]
    );

    if (
      !summary
      || typeof summary !== "object"
    ) {
      continue;
    }

    const quality = (
      sampleQualityForChannel(
        summary,
        referencePackets,
      )
    );

    qualities[channel] = quality;

    elements.sampleQualityGrid.append(
      createQualityCard(
        channel,
        summary,
        quality,
      )
    );
  }

  const readiness = (
    comparisonReadiness(
      qualities
    )
  );

  elements.comparisonReadiness.className = (
    "comparison-readiness "
    + readiness.level
  );

  elements.comparisonReadiness.textContent = (
    readiness.text
  );
}


function renderSampleWarning(document) {
  const longfast = (
    document.channels?.LongFast
  );

  const narrowfast = (
    document.channels?.NarrowFast
  );

  const longPackets = (
    Number(longfast?.packets) || 0
  );

  const narrowPackets = (
    Number(narrowfast?.packets) || 0
  );

  if (
    narrowPackets === 0
  ) {
    elements.sampleWarning.textContent = (
      "Aínda non hai observacións NarrowFast "
      + "na base experimental. A páxina queda "
      + "preparada para incorporalas cando aparezan."
    );

    elements.sampleWarning.hidden = false;
    return;
  }

  if (
    narrowPackets < 30
    || (
      longPackets > 0
      && narrowPackets < longPackets * 0.1
    )
  ) {
    elements.sampleWarning.textContent = (
      "A mostra NarrowFast aínda é moi pequena "
      + `(${formatNumber(narrowPackets)} paquetes) `
      + "fronte a LongFast "
      + `(${formatNumber(longPackets)}). `
      + "As cifras actuais non deben interpretarse "
      + "como unha comparación concluínte."
    );

    elements.sampleWarning.hidden = false;
    return;
  }

  elements.sampleWarning.hidden = true;
}

function numericSeries(
  document,
  field,
) {
  const result = {};

  for (const channel of CHANNELS) {
    const rows = (
      document.series?.[channel]
    );

    if (!Array.isArray(rows)) {
      result[channel] = [];
      continue;
    }

    result[channel] = rows
      .map((row) => {
        const time = (
          typeof row.start_us === "number"
            ? row.start_us
            : null
        );

        const value = row[field];

        if (
          time === null
          || typeof value !== "number"
          || !Number.isFinite(value)
        ) {
          return null;
        }

        return {
          time,
          value,
        };
      })
      .filter(Boolean);
  }

  return result;
}

function chartBounds(series) {
  const points = CHANNELS.flatMap(
    (channel) => series[channel] || []
  );

  if (!points.length) {
    return null;
  }

  const times = points.map(
    (point) => point.time
  );

  const values = points.map(
    (point) => point.value
  );

  let minValue = Math.min(...values);
  let maxValue = Math.max(...values);

  if (minValue === maxValue) {
    const padding = (
      Math.abs(minValue) > 1
        ? Math.abs(minValue) * 0.1
        : 1
    );

    minValue -= padding;
    maxValue += padding;
  }

  return {
    minTime: Math.min(...times),
    maxTime: Math.max(...times),
    minValue,
    maxValue,
  };
}

function svgElement(name) {
  return document.createElementNS(
    "http://www.w3.org/2000/svg",
    name,
  );
}

function renderChart(
  targetId,
  report,
  field,
  {
    valueDigits = 1,
    label = field,
    unit = "",
  } = {},
) {
  const container = document.querySelector(
    `#${targetId}`
  );

  if (!container) {
    return;
  }

  container.replaceChildren();

  const series = numericSeries(
    report,
    field,
  );

  const bounds = chartBounds(series);

  if (!bounds) {
    const empty = document.createElement(
      "div"
    );

    empty.className = "chart-empty";
    empty.textContent = (
      "Aínda non hai datos suficientes "
      + "para representar esta serie."
    );

    container.append(empty);
    return;
  }

  const width = 720;
  const height = 300;

  const margin = {
    top: 18,
    right: 18,
    bottom: 42,
    left: 68,
  };

  const innerWidth = (
    width - margin.left - margin.right
  );

  const innerHeight = (
    height - margin.top - margin.bottom
  );

  const timeSpan = Math.max(
    1,
    bounds.maxTime - bounds.minTime,
  );

  const valueSpan = Math.max(
    1e-9,
    bounds.maxValue - bounds.minValue,
  );

  const x = (value) => (
    margin.left
    + (
      (value - bounds.minTime)
      / timeSpan
    )
    * innerWidth
  );

  const y = (value) => (
    margin.top
    + innerHeight
    - (
      (value - bounds.minValue)
      / valueSpan
    )
    * innerHeight
  );

  const svg = svgElement("svg");

  svg.setAttribute(
    "viewBox",
    `0 0 ${width} ${height}`
  );

  svg.setAttribute(
    "role",
    "img"
  );

  const unitSuffix = (
    unit ? ` ${unit}` : ""
  );

  svg.setAttribute(
    "aria-label",
    `Serie temporal de ${label}${unitSuffix}`
  );

  const yTicks = 5;

  for (
    let index = 0;
    index <= yTicks;
    index += 1
  ) {
    const ratio = index / yTicks;

    const value = (
      bounds.maxValue
      - ratio * valueSpan
    );

    const yy = (
      margin.top
      + ratio * innerHeight
    );

    const grid = svgElement("line");

    grid.setAttribute("x1", margin.left);
    grid.setAttribute(
      "x2",
      width - margin.right
    );
    grid.setAttribute("y1", yy);
    grid.setAttribute("y2", yy);
    grid.setAttribute(
      "class",
      "chart-grid-line"
    );

    svg.append(grid);

    const label = svgElement("text");

    label.setAttribute(
      "x",
      margin.left - 10
    );
    label.setAttribute(
      "y",
      yy + 4
    );
    label.setAttribute(
      "text-anchor",
      "end"
    );
    label.setAttribute(
      "class",
      "chart-label"
    );

    label.textContent = formatNumber(
      value,
      valueDigits,
    );

    svg.append(label);
  }

  const axisX = svgElement("line");
  axisX.setAttribute(
    "x1",
    margin.left
  );
  axisX.setAttribute(
    "x2",
    width - margin.right
  );
  axisX.setAttribute(
    "y1",
    margin.top + innerHeight
  );
  axisX.setAttribute(
    "y2",
    margin.top + innerHeight
  );
  axisX.setAttribute(
    "class",
    "chart-axis"
  );

  svg.append(axisX);

  for (const channel of CHANNELS) {
    const points = series[channel];

    if (!points?.length) {
      continue;
    }

    const polyline = svgElement(
      "polyline"
    );

    polyline.setAttribute(
      "points",
      points
        .map(
          (point) => (
            `${x(point.time)},`
            + `${y(point.value)}`
          )
        )
        .join(" ")
    );

    polyline.setAttribute(
      "class",
      (
        "chart-line "
        + channel.toLowerCase()
      )
    );

    svg.append(polyline);

    for (const point of points) {
      const circle = svgElement("circle");

      circle.setAttribute(
        "cx",
        x(point.time)
      );
      circle.setAttribute(
        "cy",
        y(point.value)
      );
      circle.setAttribute(
        "r",
        4
      );
      circle.setAttribute(
        "class",
        (
          "chart-point "
          + channel.toLowerCase()
        )
      );

      const title = svgElement("title");

      title.textContent = (
        `${channel}: `
        + `${formatNumber(
          point.value,
          valueDigits,
        )}`
        + unitSuffix
        + " · "
        + formatDateTime(
          new Date(
            point.time / 1000
          ).toISOString()
        )
      );

      circle.append(title);
      svg.append(circle);
    }
  }

  const startLabel = svgElement("text");
  startLabel.setAttribute(
    "x",
    margin.left
  );
  startLabel.setAttribute(
    "y",
    height - 10
  );
  startLabel.setAttribute(
    "text-anchor",
    "start"
  );
  startLabel.setAttribute(
    "class",
    "chart-label"
  );

  startLabel.textContent = formatDateTime(
    new Date(
      bounds.minTime / 1000
    ).toISOString()
  );

  svg.append(startLabel);

  const endLabel = svgElement("text");
  endLabel.setAttribute(
    "x",
    width - margin.right
  );
  endLabel.setAttribute(
    "y",
    height - 10
  );
  endLabel.setAttribute(
    "text-anchor",
    "end"
  );
  endLabel.setAttribute(
    "class",
    "chart-label"
  );

  endLabel.textContent = formatDateTime(
    new Date(
      bounds.maxTime / 1000
    ).toISOString()
  );

  svg.append(endLabel);

  container.append(svg);

  const summary = document.createElement(
    "p"
  );

  summary.className = "chart-accessible-summary";

  const availableChannels = CHANNELS.filter(
    (channel) => (
      series[channel]?.length > 0
    )
  );

  summary.textContent = (
    availableChannels.length
      ? (
        `${label}: datos dispoñibles para `
        + availableChannels.join(" e ")
        + ". "
        + (
          unit
            ? `Valores expresados en ${unit}.`
            : "Valores expresados na unidade propia da métrica."
        )
      )
      : `Non hai datos dispoñibles para ${label}.`
  );

  container.append(summary);

  const legend = document.createElement(
    "div"
  );

  legend.className = "chart-legend";

  for (const channel of CHANNELS) {
    const item = document.createElement(
      "span"
    );

    item.className = "legend-item";

    const swatch = document.createElement(
      "span"
    );

    swatch.className = (
      "legend-swatch "
      + channel.toLowerCase()
    );

    const label = document.createElement(
      "span"
    );

    label.textContent = channel;

    item.append(
      swatch,
      label,
    );

    legend.append(item);
  }

  container.append(legend);
}

function methodologyEntries(
  methodology,
) {
  const definitions = {
    rf_zero_zero_missing: {
      title: "RSSI/SNR 0/0",
      text: (
        "Os pares 0/0 considéranse "
        + "unha medida RF ausente."
      ),
    },

    delivery_rate_requires_controlled_test: {
      title: "Taxa de entrega",
      text: (
        "Para calcular unha taxa de entrega "
        + "real precisamos unha proba controlada "
        + "con número coñecido de envíos."
      ),
    },

    collisions_are_not_directly_observed: {
      title: "Colisións",
      text: (
        "A fonte non permite observar "
        + "directamente unha colisión física "
        + "de radio."
      ),
    },

    ingestion_delay_is_not_radio_latency: {
      title: "Latencia",
      text: (
        "O retardo de importación da fonte "
        + "non se presenta como latencia "
        + "extremo a extremo da radio."
      ),
    },

    observational_data_does_not_isolate_preset_effect: {
      title: "Efecto do preset",
      text: (
        "A observación pasiva non permite "
        + "atribuír por si soa unha diferenza "
        + "ao preset empregado."
      ),
    },
  };

  return Object.entries(definitions)
    .filter(
      ([key]) => (
        methodology?.[key] === true
      )
    )
    .map(
      ([, value]) => value
    );
}

function percentageLabel(
  numerator,
  denominator,
  digits = 1,
) {
  const num = Number(numerator) || 0;
  const den = Number(denominator) || 0;

  if (den <= 0) {
    return "—";
  }

  return (
    formatNumber(
      num / den * 100,
      digits,
    )
    + " %"
  );
}


function derivedIndicator(
  label,
  numerator,
  denominator,
  description,
) {
  const wrapper = document.createElement(
    "div"
  );

  wrapper.className = "derived-indicator";

  const term = document.createElement("dt");
  term.textContent = label;

  const definition = document.createElement(
    "dd"
  );

  const value = document.createElement(
    "strong"
  );

  value.textContent = percentageLabel(
    numerator,
    denominator,
  );

  const sample = document.createElement(
    "span"
  );

  sample.textContent = (
    `${formatNumber(Number(numerator) || 0)}`
    + " / "
    + `${formatNumber(Number(denominator) || 0)}`
    + " paquetes"
  );

  const explanation = document.createElement(
    "small"
  );

  explanation.textContent = description;

  definition.append(
    value,
    sample,
    explanation,
  );

  wrapper.append(
    term,
    definition,
  );

  return wrapper;
}


function derivedChannelCard(
  channel,
  summary,
) {
  const article = document.createElement(
    "article"
  );

  article.className = (
    "derived-indicators-card "
    + channel.toLowerCase()
  );

  const title = document.createElement("h5");
  title.textContent = channel;

  const packets = (
    Number(summary?.packets) || 0
  );

  const list = document.createElement("dl");

  list.append(
    derivedIndicator(
      "Máis dun gateway",
      summary?.packets_multi_gateway,
      packets,
      (
        "Paquetes observados por máis dun gateway."
      ),
    ),
    derivedIndicator(
      "Con medida RF",
      summary?.packets_with_rf,
      packets,
      (
        "Paquetes con polo menos unha medida "
        + "RSSI/SNR válida."
      ),
    ),
    derivedIndicator(
      "RouteDiscovery",
      summary?.route_discovery_packets,
      packets,
      (
        "Paquetes identificados como RouteDiscovery."
      ),
    ),
    derivedIndicator(
      "Telemetría",
      summary?.telemetry_samples,
      packets,
      (
        "Mostras de telemetría respecto ao número "
        + "de paquetes observados."
      ),
    ),
  );

  const stages = document.createElement(
    "div"
  );

  stages.className = "derived-stage-summary";

  const stagesLabel = document.createElement(
    "span"
  );

  stagesLabel.textContent = "Etapas observadas";

  const stagesValue = document.createElement(
    "strong"
  );

  stagesValue.textContent = formatNumber(
    metricValue(
      summary,
      "stages",
      "mean",
    ),
    2,
  );

  const stagesDescription = document.createElement(
    "small"
  );

  stagesDescription.textContent = (
    "Media de etapas rexistradas por paquete "
    + "na evidencia observacional."
  );

  stages.append(
    stagesLabel,
    stagesValue,
    stagesDescription,
  );

  article.append(
    title,
    list,
    stages,
  );

  return article;
}


function renderDerivedIndicators(report) {
  if (!elements.derivedIndicatorsGrid) {
    return;
  }

  elements.derivedIndicatorsGrid
    .replaceChildren();

  const comparison = (
    report.comparison_window
  );

  if (
    comparison?.available !== true
    || !comparison.channels
    || typeof comparison.channels !== "object"
  ) {
    return;
  }

  for (const channel of CHANNELS) {
    const summary = (
      comparison.channels[channel]
    );

    if (
      !summary
      || typeof summary !== "object"
    ) {
      continue;
    }

    elements.derivedIndicatorsGrid.append(
      derivedChannelCard(
        channel,
        summary,
      )
    );
  }
}


function renderComparisonSummary(report) {
  if (
    !elements.comparisonSummaryGrid
    || !elements.commonComparisonPeriod
    || !elements.commonComparisonNote
  ) {
    return;
  }

  elements.comparisonSummaryGrid.replaceChildren();

  const comparison = (
    report.comparison_window
  );

  if (
    !comparison
    || typeof comparison !== "object"
    || comparison.available !== true
  ) {
    elements.commonComparisonPeriod.textContent = (
      "Sen período común"
    );

    elements.commonComparisonNote.textContent = (
      "Non existe aínda unha xanela temporal común "
      + "utilizable para comparar ambos presets."
    );

    return;
  }

  const channels = (
    comparison.channels
  );

  if (
    !channels
    || typeof channels !== "object"
  ) {
    elements.commonComparisonPeriod.textContent = (
      "Sen datos comparables"
    );

    elements.commonComparisonNote.textContent = (
      "A xanela común existe, pero non contén "
      + "os resumos por preset esperados."
    );

    return;
  }

  const startAt = formatDateTime(
    comparison.start_at
  );

  const endAt = formatDateTime(
    comparison.end_at
  );

  let durationText = "";

  const durationSeconds = (
    comparison.duration_seconds
  );

  if (
    typeof durationSeconds === "number"
    && Number.isFinite(durationSeconds)
    && durationSeconds >= 0
  ) {
    const hours = (
      durationSeconds / 3600
    );

    durationText = (
      " · "
      + formatNumber(
        hours,
        hours < 10 ? 2 : 1
      )
      + " h"
    );
  }

  elements.commonComparisonPeriod.textContent = (
    `${startAt} → ${endAt}`
    + durationText
  );

  let rendered = 0;

  for (const channel of CHANNELS) {
    const summary = (
      channels[channel]
    );

    if (
      !summary
      || typeof summary !== "object"
    ) {
      continue;
    }

    elements.comparisonSummaryGrid.append(
      renderSummaryCard(
        channel,
        summary,
      )
    );

    rendered += 1;
  }

  if (rendered === CHANNELS.length) {
    elements.commonComparisonNote.textContent = (
      "Os valores destas dúas tarxetas pertencen "
      + "á mesma xanela temporal [inicio, fin). "
      + "Son os que deben empregarse para unha "
      + "comparación directa entre LongFast e NarrowFast."
    );
  } else {
    elements.commonComparisonNote.textContent = (
      "A xanela temporal común existe, pero falta "
      + "o resumo dalgún dos presets."
    );
  }
}



function territoryMetric(
  label,
  value,
) {
  const wrapper = document.createElement(
    "div"
  );

  wrapper.className = "territory-metric";

  const term = document.createElement(
    "span"
  );
  term.textContent = label;

  const definition = document.createElement(
    "strong"
  );
  definition.textContent = value;

  wrapper.append(
    term,
    definition,
  );

  return wrapper;
}


function territoryProvinceMetric(
  label,
  value,
  detail = null,
) {
  const wrapper = document.createElement(
    "div"
  );
  wrapper.className = "territory-province-metric";

  const term = document.createElement(
    "span"
  );
  term.textContent = label;

  const definition = document.createElement(
    "strong"
  );
  definition.textContent = value;

  wrapper.append(
    term,
    definition,
  );

  if (detail) {
    const note = document.createElement(
      "small"
    );
    note.textContent = detail;

    wrapper.append(note);
  }

  return wrapper;
}


function territoryProvinceList(
  provinces,
) {
  const section = document.createElement(
    "section"
  );
  section.className = "territory-provinces";

  const title = document.createElement("h4");
  title.textContent = "Por provincia";

  const hint = document.createElement("p");
  hint.className = "territory-province-hint";
  hint.textContent = (
    "Toca unha provincia para ver as métricas observadas."
  );

  const list = document.createElement("div");
  list.className = "territory-province-list";

  const values = Array.isArray(provinces)
    ? provinces
    : [];

  if (values.length === 0) {
    const empty = document.createElement("p");
    empty.className = "territory-empty";
    empty.textContent = "Sen territorios atribuídos.";

    list.append(empty);
  }

  for (const province of values) {
    const metrics = province?.metrics || {};

    const details = document.createElement(
      "details"
    );
    details.className = "territory-province";

    const summary = document.createElement(
      "summary"
    );

    const identityWrapper = document.createElement(
      "span"
    );
    identityWrapper.className = (
      "territory-province-identity"
    );

    const icon = document.createElement(
      "span"
    );
    icon.className = "territory-province-icon";
    icon.setAttribute("aria-hidden", "true");
    icon.textContent = "⌖";

    const identity = document.createElement(
      "span"
    );
    identity.className = (
      "territory-province-name"
    );

    identity.textContent = (
      province?.name
      || province?.province
      || "Sen nome"
    );

    identityWrapper.append(
      icon,
      identity,
    );

    const counts = document.createElement(
      "strong"
    );
    counts.className = (
      "territory-province-counts"
    );

    counts.textContent = (
      countLabel(
        metrics.packets
          ?? province?.packets,
        "paquete",
        "paquetes",
      )
      + " · "
      + countLabel(
        metrics.nodes
          ?? province?.nodes,
        "emisor",
        "emisores",
      )
    );

    const chevron = document.createElement(
      "span"
    );
    chevron.className = "territory-province-chevron";
    chevron.setAttribute("aria-hidden", "true");
    chevron.textContent = "›";

    summary.append(
      identityWrapper,
      counts,
      chevron,
    );

    const grid = document.createElement(
      "div"
    );
    grid.className = (
      "territory-province-metrics"
    );

    const channelUtilization = (
      metrics.channel_utilization || {}
    );

    const airUtilTx = (
      metrics.air_util_tx || {}
    );

    const snr = metrics.snr || {};
    const rssi = metrics.rssi || {};
    const gateways = metrics.gateways || {};
    const stages = metrics.stages || {};

    grid.append(
      territoryProvinceMetric(
        "ChUtil media",
        formatNumber(
          channelUtilization.mean,
          2,
        ) + (
          typeof channelUtilization.mean
            === "number"
          ? " %"
          : ""
        ),
        countLabel(
          channelUtilization.samples,
          "mostra",
          "mostras",
        ),
      ),

      territoryProvinceMetric(
        "ChUtil mediana",
        formatNumber(
          channelUtilization.median,
          2,
        ) + (
          typeof channelUtilization.median
            === "number"
          ? " %"
          : ""
        ),
      ),

      territoryProvinceMetric(
        "Air Util TX media",
        formatNumber(
          airUtilTx.mean,
          2,
        ) + (
          typeof airUtilTx.mean
            === "number"
          ? " %"
          : ""
        ),
        countLabel(
          airUtilTx.samples,
          "mostra",
          "mostras",
        ),
      ),

      territoryProvinceMetric(
        "SNR medio",
        formatNumber(
          snr.mean,
          2,
        ) + (
          typeof snr.mean === "number"
          ? " dB"
          : ""
        ),
        countLabel(
          metrics.rf_samples,
          "mostra RF",
          "mostras RF",
        ),
      ),

      territoryProvinceMetric(
        "RSSI medio",
        formatNumber(
          rssi.mean,
          1,
        ) + (
          typeof rssi.mean === "number"
          ? " dBm"
          : ""
        ),
      ),

      territoryProvinceMetric(
        "Gateways por paquete",
        formatNumber(
          gateways.mean,
          2,
        ),
      ),

      territoryProvinceMetric(
        "Etapas por paquete",
        formatNumber(
          stages.mean,
          2,
        ),
      ),

      territoryProvinceMetric(
        "Telemetría",
        countLabel(
          metrics.telemetry_samples,
          "mostra",
          "mostras",
        ),
      ),
    );

    details.append(
      summary,
      grid,
    );

    list.append(details);
  }

  section.append(
    title,
    hint,
    list,
  );

  return section;
}


function municipalityLine(
  municipality,
) {
  const item = document.createElement("li");

  const identity = document.createElement(
    "span"
  );

  const name = (
    municipality?.name
    || "Sen nome"
  );

  const province = municipality?.province;

  identity.textContent = province
    ? `${name} (${province})`
    : name;

  const metrics = document.createElement(
    "strong"
  );

  metrics.textContent = (
    countLabel(
      municipality?.metrics?.packets,
      "paquete",
      "paquetes",
    )
    + " · "
    + countLabel(
      municipality?.metrics?.nodes,
      "emisor",
      "emisores",
    )
  );

  item.append(
    identity,
    metrics,
  );

  return item;
}


function territoryMunicipalityList(
  municipalities,
) {
  const section = document.createElement(
    "section"
  );
  section.className = "territory-municipalities";

  const title = document.createElement("h4");
  title.textContent = "Concellos con máis paquetes";

  const values = (
    Array.isArray(municipalities)
      ? municipalities
      : []
  );

  const ordered = [...values].sort(
    (left, right) => (
      Number(
        right?.metrics?.packets
      ) || 0
    ) - (
      Number(
        left?.metrics?.packets
      ) || 0
    )
  );

  const visible = ordered.slice(0, 8);
  const remaining = ordered.slice(8);

  const list = document.createElement("ol");
  list.className = "territory-list territory-ranking";

  if (visible.length === 0) {
    const empty = document.createElement("li");
    empty.className = "territory-empty";
    empty.textContent = "Sen concellos atribuídos.";
    list.append(empty);
  }

  for (const municipality of visible) {
    list.append(
      municipalityLine(
        municipality
      )
    );
  }

  section.append(
    title,
    list,
  );

  if (remaining.length > 0) {
    const details = document.createElement(
      "details"
    );
    details.className = "territory-details";

    const summary = document.createElement(
      "summary"
    );

    summary.textContent = (
      "Ver "
      + countLabel(
        remaining.length,
        "concello restante",
        "concellos restantes",
      )
    );

    const remainingList = document.createElement(
      "ol"
    );

    remainingList.className = (
      "territory-list territory-ranking "
      + "territory-ranking-more"
    );

    for (const municipality of remaining) {
      remainingList.append(
        municipalityLine(
          municipality
        )
      );
    }

    details.append(
      summary,
      remainingList,
    );

    section.append(details);
  }

  return section;
}


function territoryUncertainty(
  data,
) {
  const section = document.createElement(
    "section"
  );
  section.className = "territory-uncertainty";

  const title = document.createElement("h4");
  title.textContent = "Incerteza territorial";

  const summary = data?.summary || {};
  const ambiguous = Number(
    summary.ambiguous_emitters
  ) || 0;

  const outside = Number(
    summary.outside_emitters
  ) || 0;

  const unlocated = Number(
    summary.unlocated_emitters
  ) || 0;

  const list = document.createElement("ul");
  list.className = "territory-list";

  const entries = [
    [
      "Ambiguos",
      countLabel(
        ambiguous,
        "emisor",
        "emisores",
      ),
    ],
    [
      "Fóra de Galicia",
      countLabel(
        outside,
        "emisor",
        "emisores",
      ),
    ],
    [
      "Sen localizar",
      countLabel(
        unlocated,
        "emisor",
        "emisores",
      ),
    ],
  ];

  for (const [label, value] of entries) {
    const item = document.createElement("li");

    const name = document.createElement("span");
    name.textContent = label;

    const count = document.createElement(
      "strong"
    );
    count.textContent = value;

    item.append(
      name,
      count,
    );

    list.append(item);
  }

  section.append(
    title,
    list,
  );

  return section;
}


function territoryComparisonKey(
  level,
  territory,
) {
  if (level === "municipality") {
    return (
      territory?.id
      || ""
    );
  }

  return (
    territory?.name
    || territory?.province
    || ""
  );
}


function territoryComparisonLabel(
  level,
  territory,
) {
  const name = (
    territory?.name
    || territory?.province
    || "Sen nome"
  );

  if (
    level === "municipality"
    && territory?.province
  ) {
    return (
      `${name} (${territory.province})`
    );
  }

  return name;
}


function territoryComparisonEntries(
  territories,
  level,
) {
  const collectionName = (
    level === "municipality"
      ? "municipalities"
      : "provinces"
  );

  const entries = new Map();

  for (const channel of CHANNELS) {
    const values = (
      territories?.[channel]?.[
        collectionName
      ]
    );

    if (!Array.isArray(values)) {
      continue;
    }

    for (const territory of values) {
      const key = territoryComparisonKey(
        level,
        territory,
      );

      if (!key) {
        continue;
      }

      if (!entries.has(key)) {
        entries.set(
          key,
          {
            key,
            label: territoryComparisonLabel(
              level,
              territory,
            ),
            channels: {},
          }
        );
      }

      entries.get(key).channels[channel] = (
        territory
      );
    }
  }

  return [...entries.values()].sort(
    (left, right) => (
      left.label.localeCompare(
        right.label,
        "gl",
        {
          sensitivity: "base",
        },
      )
    )
  );
}


function territoryComparisonMetric(
  label,
  value,
  detail = null,
) {
  const wrapper = document.createElement(
    "div"
  );

  wrapper.className = (
    "territory-comparison-metric"
  );

  const term = document.createElement(
    "span"
  );
  term.textContent = label;

  const definition = document.createElement(
    "strong"
  );
  definition.textContent = value;

  wrapper.append(
    term,
    definition,
  );

  if (detail) {
    const note = document.createElement(
      "small"
    );
    note.textContent = detail;

    wrapper.append(note);
  }

  return wrapper;
}


function territoryComparisonCard(
  channel,
  territory,
) {
  const article = document.createElement(
    "article"
  );

  article.className = (
    "territory-comparison-card "
    + channel.toLowerCase()
  );

  const header = document.createElement(
    "header"
  );

  header.className = (
    "territory-comparison-card-header"
  );

  const title = document.createElement(
    "h4"
  );
  title.textContent = channel;

  header.append(title);

  if (
    !territory
    || typeof territory !== "object"
  ) {
    const empty = document.createElement(
      "p"
    );

    empty.className = (
      "territory-comparison-empty"
    );

    empty.textContent = (
      "Sen observacións deste preset "
      + "neste territorio."
    );

    article.append(
      header,
      empty,
    );

    return article;
  }

  const metrics = territory.metrics || {};
  const classification = (
    territory.classification || {}
  );

  const snr = metrics.snr || {};
  const rssi = metrics.rssi || {};
  const gateways = metrics.gateways || {};
  const stages = metrics.stages || {};

  const utilization = (
    metrics.channel_utilization || {}
  );

  const airUtilTx = (
    metrics.air_util_tx || {}
  );

  const grid = document.createElement(
    "div"
  );

  grid.className = (
    "territory-comparison-metrics"
  );

  grid.append(
    territoryComparisonMetric(
      "Paquetes",
      formatNumber(
        metrics.packets
      ),
    ),

    territoryComparisonMetric(
      "Emisores",
      formatNumber(
        metrics.nodes
      ),
    ),

    territoryComparisonMetric(
      "Asignación exacta",
      formatNumber(
        classification.exact_nodes
      ),
    ),

    territoryComparisonMetric(
      "Asignación compatible",
      formatNumber(
        classification.compatible_nodes
      ),
    ),

    territoryComparisonMetric(
      "Mostras RF",
      formatNumber(
        metrics.rf_samples
      ),
    ),

    territoryComparisonMetric(
      "SNR medio",
      formatNumber(
        snr.mean,
        2,
      ) + (
        typeof snr.mean === "number"
          ? " dB"
          : ""
      ),
    ),

    territoryComparisonMetric(
      "RSSI medio",
      formatNumber(
        rssi.mean,
        1,
      ) + (
        typeof rssi.mean === "number"
          ? " dBm"
          : ""
      ),
    ),

    territoryComparisonMetric(
      "Gateways por paquete",
      formatNumber(
        gateways.mean,
        2,
      ),
    ),

    territoryComparisonMetric(
      "Etapas por paquete",
      formatNumber(
        stages.mean,
        2,
      ),
    ),

    territoryComparisonMetric(
      "ChUtil media",
      formatNumber(
        utilization.mean,
        2,
      ) + (
        typeof utilization.mean === "number"
          ? " %"
          : ""
      ),
      countLabel(
        utilization.samples,
        "mostra",
        "mostras",
      ),
    ),

    territoryComparisonMetric(
      "Air Util TX media",
      formatNumber(
        airUtilTx.mean,
        2,
      ) + (
        typeof airUtilTx.mean === "number"
          ? " %"
          : ""
      ),
      countLabel(
        airUtilTx.samples,
        "mostra",
        "mostras",
      ),
    ),

    territoryComparisonMetric(
      "RouteDiscovery",
      formatNumber(
        metrics.route_discovery_packets
      ),
    ),

    territoryComparisonMetric(
      "Telemetría",
      formatNumber(
        metrics.telemetry_samples
      ),
    ),
  );

  article.append(
    header,
    grid,
  );

  return article;
}


function renderTerritoryComparisonSelection(
  report,
) {
  if (
    !elements.territoryComparisonLevel
    || !elements.territoryComparisonSelect
    || !elements.territoryComparisonStatus
    || !elements.territoryComparisonGrid
  ) {
    return;
  }

  const territories = report?.territories;

  elements.territoryComparisonGrid
    .replaceChildren();

  if (
    !territories
    || typeof territories !== "object"
  ) {
    elements.territoryComparisonStatus
      .textContent = (
        "A clasificación territorial "
        + "non está dispoñible."
      );

    return;
  }

  const level = (
    elements.territoryComparisonLevel.value
    || "province"
  );

  const entries = territoryComparisonEntries(
    territories,
    level,
  );

  const selectedKey = (
    elements.territoryComparisonSelect.value
  );

  const selected = entries.find(
    (entry) => (
      entry.key === selectedKey
    )
  );

  if (!selected) {
    elements.territoryComparisonStatus
      .textContent = (
        "Selecciona un territorio para comparar."
      );

    return;
  }

  elements.territoryComparisonStatus
    .textContent = (
      "Comparando "
      + selected.label
      + " nos dous presets."
    );

  for (const channel of CHANNELS) {
    elements.territoryComparisonGrid.append(
      territoryComparisonCard(
        channel,
        selected.channels[channel],
      )
    );
  }
}


function populateTerritoryComparison(
  report,
) {
  if (
    !elements.territoryComparisonLevel
    || !elements.territoryComparisonSelect
    || !elements.territoryComparisonStatus
    || !elements.territoryComparisonGrid
  ) {
    return;
  }

  const territories = report?.territories;

  if (
    !territories
    || typeof territories !== "object"
  ) {
    elements.territoryComparisonLevel.disabled = true;
    elements.territoryComparisonSelect.disabled = true;

    elements.territoryComparisonStatus
      .textContent = (
        "A clasificación territorial "
        + "non está dispoñible."
      );

    elements.territoryComparisonGrid
      .replaceChildren();

    return;
  }

  const level = (
    elements.territoryComparisonLevel.value
    || "province"
  );

  const entries = territoryComparisonEntries(
    territories,
    level,
  );

  const previous = (
    elements.territoryComparisonSelect.value
  );

  elements.territoryComparisonSelect
    .replaceChildren();

  const placeholder = document.createElement(
    "option"
  );

  placeholder.value = "";
  placeholder.textContent = (
    level === "municipality"
      ? "Selecciona un concello"
      : "Selecciona unha provincia"
  );

  elements.territoryComparisonSelect.append(
    placeholder
  );

  for (const entry of entries) {
    const option = document.createElement(
      "option"
    );

    option.value = entry.key;
    option.textContent = entry.label;

    elements.territoryComparisonSelect.append(
      option
    );
  }

  const stillExists = entries.some(
    (entry) => entry.key === previous
  );

  elements.territoryComparisonSelect.value = (
    stillExists
      ? previous
      : ""
  );

  elements.territoryComparisonLevel.disabled = (
    entries.length === 0
  );

  elements.territoryComparisonSelect.disabled = (
    entries.length === 0
  );

  if (entries.length === 0) {
    elements.territoryComparisonStatus
      .textContent = (
        "Non hai territorios deste nivel "
        + "na mostra actual."
      );

    elements.territoryComparisonGrid
      .replaceChildren();

    return;
  }

  renderTerritoryComparisonSelection(
    report
  );
}


function setupTerritoryComparison(
  report,
) {
  if (
    !elements.territoryComparisonLevel
    || !elements.territoryComparisonSelect
  ) {
    return;
  }

  elements.territoryComparisonLevel.onchange = () => {
    populateTerritoryComparison(
      report
    );
  };

  elements.territoryComparisonSelect.onchange = () => {
    renderTerritoryComparisonSelection(
      report
    );
  };

  populateTerritoryComparison(
    report
  );
}


function territoryChannelCard(
  channel,
  data,
) {
  const article = document.createElement(
    "article"
  );

  article.className = (
    "territory-card "
    + channel.toLowerCase()
  );

  const header = document.createElement(
    "header"
  );
  header.className = "territory-card-header";

  const title = document.createElement("h3");
  title.textContent = channel;

  const summary = data?.summary || {};

  const subtitle = document.createElement(
    "span"
  );

  subtitle.textContent = countLabel(
    summary.emitters,
    "emisor observado",
    "emisores observados",
  );

  header.append(
    title,
    subtitle,
  );

  const metrics = document.createElement(
    "div"
  );
  metrics.className = "territory-metrics";

  metrics.append(
    territoryMetric(
      "Paquetes atribuídos",
      formatNumber(
        summary.assigned_packets
      ),
    ),
    territoryMetric(
      "Emisores atribuídos",
      formatNumber(
        summary.assigned_emitters
      ),
    ),
    territoryMetric(
      "Asignación exacta",
      formatNumber(
        summary.exact_emitters
      ),
    ),
    territoryMetric(
      "Asignación compatible",
      formatNumber(
        summary.compatible_emitters
      ),
    ),
  );

  const body = document.createElement(
    "div"
  );
  body.className = "territory-card-body";

  body.append(
    territoryProvinceList(
      data?.provinces
    ),
    territoryMunicipalityList(
      data?.municipalities
    ),
    territoryUncertainty(
      data
    ),
  );

  article.append(
    header,
    metrics,
    body,
  );

  return article;
}


function renderTerritories(report) {
  if (!elements.territoriesGrid) {
    return;
  }

  elements.territoriesGrid.replaceChildren();

  const territories = report.territories;

  if (
    !territories
    || typeof territories !== "object"
  ) {
    const empty = document.createElement("p");
    empty.className = "territories-empty";
    empty.textContent = (
      "A clasificación territorial non está dispoñible "
      + "neste informe."
    );

    elements.territoriesGrid.append(empty);
    return;
  }

  let rendered = 0;

  for (const channel of CHANNELS) {
    const data = territories[channel];

    if (
      !data
      || typeof data !== "object"
    ) {
      continue;
    }

    elements.territoriesGrid.append(
      territoryChannelCard(
        channel,
        data,
      )
    );

    rendered += 1;
  }

  if (rendered === 0) {
    const empty = document.createElement("p");
    empty.className = "territories-empty";
    empty.textContent = (
      "Aínda non hai datos territoriais publicables."
    );

    elements.territoriesGrid.append(empty);
  }
}


function renderMethodology(report) {
  elements.methodologyGrid.replaceChildren();

  const entries = methodologyEntries(
    report.methodology
  );

  for (const entry of entries) {
    const article = document.createElement(
      "article"
    );

    article.className = "methodology-item";

    const title = document.createElement(
      "strong"
    );

    title.textContent = entry.title;

    const text = document.createElement("p");
    text.textContent = entry.text;

    article.append(
      title,
      text,
    );

    elements.methodologyGrid.append(
      article
    );
  }
}

function render(report) {
  renderTestSituation(report);
  renderEvidence(report);
  renderSummaries(report);
  renderSampleWarning(report);
  renderSampleQuality(report);
  renderComparisonWindow(report);
  renderComparisonSummary(report);
  renderDerivedIndicators(report);
  renderTerritories(report);
  setupTerritoryComparison(report);
  renderMethodology(report);

  const bucketSeconds = (
    report.bucket_seconds
  );

  if (
    typeof bucketSeconds === "number"
  ) {
    elements.bucketDescription.textContent = (
      "Intervalos de "
      + formatNumber(
        bucketSeconds / 60
      )
      + " minutos."
    );
  }

  renderChart(
    "chart-packets",
    report,
    "packets",
    {
      valueDigits: 0,
      label: "Paquetes observados",
      unit: "paquetes",
    },
  );

  renderChart(
    "chart-snr",
    report,
    "snr_mean",
    {
      valueDigits: 1,
      label: "SNR medio",
      unit: "dB",
    },
  );

  renderChart(
    "chart-rssi",
    report,
    "rssi_mean",
    {
      valueDigits: 1,
      label: "RSSI medio",
      unit: "dBm",
    },
  );

  renderChart(
    "chart-gateways",
    report,
    "gateway_mean",
    {
      valueDigits: 2,
      label: "Gateways observadores por paquete",
      unit: "gateways",
    },
  );

  renderChart(
    "chart-utilization",
    report,
    "channel_utilization_mean",
    {
      valueDigits: 2,
      label: "Ocupación media do canal",
      unit: "%",
    },
  );

  renderChart(
    "chart-air-tx",
    report,
    "air_util_tx_mean",
    {
      valueDigits: 2,
      label: "Air util TX medio",
      unit: "%",
    },
  );
}

async function loadExperiment() {
  try {
    const response = await fetch(
      EXPERIMENT_URL,
      {
        cache: "no-store",
        headers: {
          Accept: "application/json",
        },
      }
    );

    if (!response.ok) {
      throw new Error(
        `HTTP ${response.status}`
      );
    }

    const document = await response.json();

    if (
      document.schema !== EXPECTED_SCHEMA
    ) {
      throw new Error(
        "Contrato experiment.json non soportado"
      );
    }

    render(document);

    elements.status.textContent = (
      "Actualizado "
      + formatDateTime(
        document.generated_at
      )
    );

    elements.status.classList.add("ok");

  } catch (error) {
    console.error(error);

    elements.status.textContent = (
      "Non foi posible cargar "
      + "os datos experimentais."
    );

    elements.status.classList.add(
      "error"
    );

    const empty = document.createElement(
      "p"
    );

    empty.className = "sample-warning";
    empty.textContent = (
      "A páxina non puido cargar "
      + "../data/experiment.json."
    );

    elements.summaryGrid.replaceChildren(
      empty
    );
  }
}

loadExperiment();
