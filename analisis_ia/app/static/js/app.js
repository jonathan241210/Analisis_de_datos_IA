const TAB_TO_AGENT = { ingest: "eda", eda: "eda", clean: "cleaning", ml: "ml" };
const PICKER_IDS = [
  "hist-col", "box-cols", "impute-cols", "cast-col", "scale-cols",
  "encode-cols", "drop-cols", "ml-features", "ml-unsup-feats",
];
const CHAT_W_KEY = "analisis_ia.chatWidth";
const CHAT_H_KEY = "analisis_ia.chatHeight";
const CHAT_MIN_W = 280;
const CHAT_MAX_RATIO = 0.55;

let activeTab = "ingest";
let classifiers = [];
let regressors = [];
let ingestMeta = null;
let toastTimer = 0;
const UI_ERR = {
  chat: "La IA no responde",
  execute: "No se pudo ejecutar el código",
  plot: "Error al generar el gráfico",
  ml: "Error al entrenar el modelo",
  wrangle: "Error al aplicar la transformación",
  upload: "Error al cargar el archivo",
  eda: "Error al cargar el análisis descriptivo",
  abort: "Petición cancelada",
  copy: "No se pudo copiar el código",
};

let chatAbort = null;
let editingBubble = null;

function prefersReducedMotion() {
  return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function setButtonBusy(btn, busyLabel) {
  if (!btn) return;
  if (!btn.dataset.label) btn.dataset.label = btn.textContent;
  btn.classList.remove("is-ok");
  btn.classList.add("is-busy");
  btn.disabled = true;
  btn.setAttribute("aria-busy", "true");
  if (busyLabel) btn.textContent = busyLabel;
}

function clearButtonBusy(btn) {
  if (!btn) return;
  btn.classList.remove("is-busy", "is-ok");
  btn.removeAttribute("aria-busy");
  if (btn.dataset.label) btn.textContent = btn.dataset.label;
  btn.disabled = false;
}

async function markButtonOk(btn, ms = 700) {
  if (!btn) return;
  const original = btn.dataset.label || btn.textContent;
  btn.classList.remove("is-busy");
  btn.classList.add("is-ok");
  btn.removeAttribute("aria-busy");
  if (btn.dataset.okLabel) btn.textContent = btn.dataset.okLabel;
  else btn.textContent = original;
  btn.disabled = true;
  await sleep(prefersReducedMotion() ? 0 : ms);
  btn.classList.remove("is-ok");
  btn.textContent = original;
  btn.disabled = false;
}

async function withBusy(btn, fn, busyLabel) {
  if (!btn) return fn();
  setButtonBusy(btn, busyLabel);
  try {
    const result = await fn();
    await markButtonOk(btn);
    return result;
  } catch (err) {
    clearButtonBusy(btn);
    throw err;
  }
}

function isAbortError(err) {
  return Boolean(err && (err.name === "AbortError" || err.message === "The user aborted a request."));
}

function isChatStacked() {
  return window.matchMedia("(max-width: 1100px)").matches;
}

function toast(msg, kind = "ok") {
  const el = document.getElementById("toast");
  if (!el) return;
  const tone = kind === "error" ? "error" : (kind === "info" ? "info" : "ok");
  el.textContent = msg;
  el.hidden = false;
  el.classList.remove("is-ok", "is-error", "is-info", "is-out");
  el.classList.add(`is-${tone}`);
  placeToast(el);
  const ms = tone === "error" ? 5200 : 4000;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => {
    el.classList.add("is-out");
    toastTimer = setTimeout(() => { el.hidden = true; el.classList.remove("is-out"); }, 220);
  }, ms);
}

function placeToast(el) {
  const tools = document.querySelector(".tools");
  if (!tools) return;
  const r = tools.getBoundingClientRect();
  el.style.left = `${r.left + r.width / 2}px`;
  el.style.right = "auto";
  el.style.transform = "translateX(-50%)";
  if (isChatStacked()) {
    el.style.top = `${Math.max(12, r.top + 12)}px`;
    el.style.bottom = "auto";
  } else {
    el.style.top = "auto";
    el.style.bottom = `${Math.max(16, window.innerHeight - r.bottom + 14)}px`;
  }
}

function flashFrom(_anchor, msg, kind = "ok") {
  toast(msg, kind);
}

function columnsQuery(cols) {
  const params = new URLSearchParams();
  cols.forEach((c) => params.append("columns", c));
  return params.toString();
}

async function api(path, opts = {}) {
  const res = await fetch(path, opts);
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail || JSON.stringify(body);
    } catch (_) { /* ignore */ }
    const err = new Error(detail);
    err.status = res.status;
    throw err;
  }
  const ct = res.headers.get("content-type") || "";
  if (ct.includes("application/json")) return res.json();
  return res;
}

function renderTable(container, preview) {
  if (!container) return;
  if (!preview || !preview.columns || !preview.columns.length) {
    container.innerHTML = "";
    return;
  }
  const head = preview.columns.map((c) => `<th>${esc(c)}</th>`).join("");
  const body = (preview.rows || []).map((row) => {
    const tds = preview.columns.map((c) => `<td>${esc(row[c])}</td>`).join("");
    return `<tr>${tds}</tr>`;
  }).join("");
  container.innerHTML = `<table><thead><tr>${head}</tr></thead><tbody>${body}</tbody></table>`;
}

function recordsTable(container, rows) {
  if (!container) return;
  if (!rows || !rows.length) {
    container.innerHTML = "";
    return;
  }
  renderTable(container, { columns: Object.keys(rows[0]), rows });
}

function esc(v) {
  if (v === null || v === undefined) return "";
  return String(v).replace(/[&<>"']/g, (ch) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[ch]));
}

function resolveEl(idOrEl) {
  return typeof idOrEl === "string" ? document.getElementById(idOrEl) : idOrEl;
}

function isPicker(el) {
  return Boolean(el && (el.classList.contains("picker") || el.hasAttribute("data-picker")));
}

function selected(idOrEl) {
  const el = resolveEl(idOrEl);
  if (!el) return [];
  if (isPicker(el)) {
    return [...el.querySelectorAll('input[type="checkbox"]:checked')].map((i) => i.value).filter(Boolean);
  }
  return [...el.selectedOptions].map((o) => o.value).filter(Boolean);
}

function closeAllPickers(except = null) {
  document.querySelectorAll(".picker").forEach((root) => {
    if (root === except) return;
    const menu = root.querySelector(".picker-menu");
    const toggle = root.querySelector(".picker-toggle");
    if (menu) menu.hidden = true;
    root.classList.remove("is-open");
    if (toggle) toggle.setAttribute("aria-expanded", "false");
  });
}

function renderChips(root) {
  const chips = root.querySelector(".picker-chips");
  if (!chips) return;
  const vals = selected(root);
  if (!vals.length) {
    chips.innerHTML = `<span class="picker-placeholder">Ninguna columna</span>`;
    return;
  }
  chips.innerHTML = vals.map((v) => (
    `<button type="button" class="picker-chip" data-value="${esc(v)}">`
    + `${esc(v)}<span aria-hidden="true">×</span></button>`
  )).join("");
  chips.querySelectorAll(".picker-chip").forEach((btn) => {
    btn.addEventListener("click", (ev) => {
      ev.stopPropagation();
      const value = btn.dataset.value;
      const cb = [...root.querySelectorAll('input[type="checkbox"]')].find((i) => i.value === value);
      if (cb) {
        cb.checked = false;
        renderChips(root);
      }
    });
  });
}

function initPicker(root) {
  if (!root || root.dataset.ready === "1") return;
  root.dataset.ready = "1";
  root.innerHTML = `
    <div class="picker-chips"><span class="picker-placeholder">Ninguna columna</span></div>
    <button type="button" class="picker-toggle ghost" aria-expanded="false">Elegir columnas</button>
    <div class="picker-menu" hidden role="listbox"></div>
  `;
  const toggle = root.querySelector(".picker-toggle");
  const menu = root.querySelector(".picker-menu");
  toggle.addEventListener("click", (e) => {
    e.stopPropagation();
    const willOpen = menu.hidden;
    closeAllPickers(willOpen ? root : null);
    menu.hidden = !willOpen;
    root.classList.toggle("is-open", willOpen);
    toggle.setAttribute("aria-expanded", String(willOpen));
  });
  menu.addEventListener("click", (e) => e.stopPropagation());
  menu.addEventListener("change", () => renderChips(root));
}

function fillPicker(root, items) {
  if (!root) return;
  initPicker(root);
  const prev = new Set(selected(root));
  const menu = root.querySelector(".picker-menu");
  if (!items.length) {
    menu.innerHTML = `<p class="picker-empty">Sin columnas</p>`;
  } else {
    menu.innerHTML = items.map((c) => {
      const checked = prev.has(c) ? "checked" : "";
      return `<label class="picker-opt"><input type="checkbox" value="${esc(c)}" ${checked} /><span>${esc(c)}</span></label>`;
    }).join("");
  }
  renderChips(root);
}

function fillSelect(sel, items, { multipleKeep = true } = {}) {
  if (!sel) return;
  if (isPicker(sel)) {
    fillPicker(sel, items);
    return;
  }
  const prevMulti = new Set([...sel.selectedOptions].map((o) => o.value));
  const prevSingle = sel.value;
  sel.innerHTML = items.map((c) => `<option value="${esc(c)}">${esc(c)}</option>`).join("");
  if (sel.multiple && multipleKeep) {
    [...sel.options].forEach((o) => { if (prevMulti.has(o.value)) o.selected = true; });
  } else if (prevSingle && items.includes(prevSingle)) {
    sel.value = prevSingle;
  }
}

function setChip(preview, fileName) {
  const chip = document.getElementById("dataset-chip");
  if (!preview) {
    chip.textContent = "Sin dataset";
    chip.classList.add("muted");
    return;
  }
  chip.classList.remove("muted");
  chip.textContent = `${fileName || "dataset"} · ${preview.shape[0]} × ${preview.shape[1]}`;
}

function setDupCount(preview) {
  const el = document.getElementById("dup-count");
  if (!el) return;
  el.textContent = preview && preview.duplicate_rows != null ? preview.duplicate_rows : "—";
}

function renderIngestMeta(meta, preview) {
  const metrics = document.getElementById("ingest-meta");
  const tech = document.getElementById("ingest-tech");
  if (!preview) {
    metrics.innerHTML = "";
    tech.innerHTML = "";
    return;
  }
  const [rows, cols] = preview.shape || [0, 0];
  const items = [
    ["Filas", rows],
    ["Columnas", cols],
    ["Formato", (meta && meta.formato) || "—"],
    ["Memoria", preview.memory || "—"],
  ];
  metrics.innerHTML = items
    .map(([k, v]) => `<span class="metric"><small>${esc(k)}</small><b>${esc(v)}</b></span>`)
    .join("");
  if (meta) {
    tech.innerHTML = [
      `Archivo: ${esc(meta.file_name || "—")}`,
      `Encoding: ${esc(meta.encoding || "—")}`,
      `Separador: ${esc(meta.separador || "—")}`,
    ].map((line) => `<p>${line}</p>`).join("");
  }
}

function applyPreview(preview, fileName) {
  setChip(preview, fileName);
  setDupCount(preview);
  renderTable(document.getElementById("ingest-table"), preview);
  renderTable(document.getElementById("clean-table"), preview);
  renderIngestMeta(ingestMeta, preview);
  syncColumns(preview);
  if (preview && preview.columns && preview.columns.length) {
    loadEda();
    if (activeTab === "ml") loadMlOptions();
  }
}

function syncColumns(preview) {
  if (!preview) return;
  const cols = preview.columns;
  fillPicker(document.getElementById("impute-cols"), cols);
  fillPicker(document.getElementById("cast-col"), cols);
  fillPicker(document.getElementById("drop-cols"), cols);
  fillPicker(document.getElementById("encode-cols"), cols);
  fillPicker(document.getElementById("ml-features"), cols);
  fillSelect(document.getElementById("rename-old"), cols);
  fillSelect(document.getElementById("ml-target"), cols, { multipleKeep: false });
  const nums = Object.entries(preview.dtypes)
    .filter(([, t]) => /int|float|Int|Float|number/i.test(t))
    .map(([c]) => c);
  const numeric = nums.length ? nums : cols;
  fillPicker(document.getElementById("scale-cols"), numeric);
  fillPicker(document.getElementById("ml-unsup-feats"), numeric);
  fillPicker(document.getElementById("box-cols"), numeric);
  fillPicker(document.getElementById("hist-col"), numeric);
}

async function refreshPreview() {
  try {
    const data = await api("/api/v1/datasets/preview");
    ingestMeta = data.meta;
    applyPreview(data.preview, data.file_name);
    return data;
  } catch (_) {
    return null;
  }
}

function setActiveTab(name) {
  const btn = document.querySelector(`.tab[data-tab="${name}"]`);
  if (!btn) return;
  document.querySelectorAll(".tab").forEach((b) => b.classList.remove("is-active"));
  btn.classList.add("is-active");
  activeTab = name;
  document.querySelectorAll(".panel").forEach((p) => p.classList.remove("is-active"));
  const panel = document.getElementById(`panel-${activeTab}`);
  if (panel) panel.classList.add("is-active");
  if (activeTab === "eda") loadEda();
  if (activeTab === "ml") loadMlOptions();
}

document.querySelectorAll(".tab").forEach((btn) => {
  btn.addEventListener("click", () => setActiveTab(btn.dataset.tab));
});

document.querySelectorAll("[data-subtabs]").forEach((group) => {
  group.querySelectorAll(":scope > .subtabs .subtab").forEach((btn) => {
    btn.addEventListener("click", () => {
      group.querySelectorAll(":scope > .subtabs .subtab").forEach((b) => b.classList.remove("is-active"));
      btn.classList.add("is-active");
      const pane = btn.dataset.pane;
      group.querySelectorAll(":scope > .subpane").forEach((p) => {
        p.classList.toggle("is-active", p.id === pane);
      });
    });
  });
});

PICKER_IDS.forEach((id) => initPicker(document.getElementById(id)));
document.addEventListener("click", () => closeAllPickers());

document.getElementById("chat-toggle").addEventListener("click", () => {
  document.querySelector(".workspace").classList.toggle("is-collapsed");
  applyChatSize();
});

const ALLOWED_EXT = /\.(csv|tsv|xlsx|xls)$/i;

async function uploadFile(file) {
  const drop = document.getElementById("dropzone");
  if (!file) return;
  if (!ALLOWED_EXT.test(file.name)) {
    toast("Formato no válido. Usa CSV, TSV o Excel.", "error");
    return;
  }
  const fd = new FormData();
  fd.append("file", file);
  try {
    const data = await api("/api/v1/datasets/upload", { method: "POST", body: fd });
    ingestMeta = data.meta;
    applyPreview(data.preview, data.meta.file_name);
    toast("Archivo cargado");
  } catch (err) {
    toast(UI_ERR.upload, "error");
  } finally {
    document.getElementById("file-input").value = "";
  }
}

function bindDropzone() {
  const drop = document.getElementById("dropzone");
  const input = document.getElementById("file-input");
  let dragDepth = 0;

  input.addEventListener("change", () => {
    const file = input.files[0];
    if (file) uploadFile(file);
  });

  drop.addEventListener("dragenter", (e) => {
    e.preventDefault();
    e.stopPropagation();
    dragDepth += 1;
    drop.classList.add("is-dragover");
  });
  drop.addEventListener("dragover", (e) => {
    e.preventDefault();
    e.stopPropagation();
    e.dataTransfer.dropEffect = "copy";
  });
  drop.addEventListener("dragleave", (e) => {
    e.preventDefault();
    e.stopPropagation();
    dragDepth -= 1;
    if (dragDepth <= 0) {
      dragDepth = 0;
      drop.classList.remove("is-dragover");
    }
  });
  drop.addEventListener("drop", (e) => {
    e.preventDefault();
    e.stopPropagation();
    dragDepth = 0;
    drop.classList.remove("is-dragover");
    const file = e.dataTransfer.files && e.dataTransfer.files[0];
    if (file) uploadFile(file);
  });

  window.addEventListener("dragover", (e) => { e.preventDefault(); });
  window.addEventListener("drop", (e) => { e.preventDefault(); });
}

bindDropzone();

document.getElementById("impute-strategy").addEventListener("change", () => {
  document.getElementById("impute-value-wrap").hidden =
    document.getElementById("impute-strategy").value !== "Constante";
});

function syncUnsupFields() {
  const method = document.getElementById("ml-unsup-method").value;
  document.getElementById("unsup-k").hidden = !["elbow", "kmeans"].includes(method);
  document.getElementById("unsup-eps").hidden = method !== "dbscan";
  document.getElementById("unsup-min").hidden = method !== "dbscan";
  document.getElementById("unsup-pca").hidden = method !== "pca";
}

document.getElementById("ml-unsup-method").addEventListener("change", syncUnsupFields);
syncUnsupFields();

async function loadEda() {
  const metricsEl = document.getElementById("eda-metrics");
  try {
    const report = await api("/api/v1/eda/report");
    const m = report.metrics;
    if (!m || metricsEl == null) return;
    const zv = (m.zero_variance_columns || []).length;
    metricsEl.innerHTML = [
      ["Filas × columnas", `${m.rows} × ${m.columns}`],
      ["Memoria", m.memory],
      ["Duplicados", m.duplicate_rows],
      ["Varianza cero", zv],
    ].map(([k, v]) => `<div class="metric"><small>${k}</small><b>${v}</b></div>`).join("");
    recordsTable(document.getElementById("eda-dtypes"), m.dtypes);
    recordsTable(document.getElementById("eda-numeric"), report.stats && report.stats.numeric);
    recordsTable(document.getElementById("eda-cats"), report.stats && report.stats.categorical);
    renderTable(document.getElementById("eda-quality"), {
      columns: ["columna", "nulos", "pct_nulos", "tipo"],
      rows: (report.quality && report.quality.columns) || [],
    });
    const catSel = document.getElementById("eda-cat-sel");
    if (catSel) {
      catSel.innerHTML = `<option value="">—</option>`
        + (report.categorical_columns || []).map((c) => `<option value="${esc(c)}">${esc(c)}</option>`).join("");
    }
    const detail = document.getElementById("eda-cat-detail");
    if (detail) detail.innerHTML = "";
    fillPicker(document.getElementById("hist-col"), report.numeric_columns || []);
    fillPicker(document.getElementById("box-cols"), report.numeric_columns || []);
  } catch (err) {
    if (metricsEl) {
      metricsEl.innerHTML = `<p class="hint">${esc(UI_ERR.eda)}</p>`;
    }
    toast(UI_ERR.eda, "error");
  }
}

document.getElementById("eda-cat-sel").addEventListener("change", async (ev) => {
  const col = ev.target.value;
  const box = document.getElementById("eda-cat-detail");
  if (!col) {
    box.innerHTML = "";
    return;
  }
  try {
    const data = await api(`/api/v1/eda/value-counts?column=${encodeURIComponent(col)}`);
    renderTable(box, data);
  } catch (err) {
    toast(UI_ERR.eda, "error");
  }
});

function figureHeight(fig) {
  const fromLayout = Number(fig && fig.layout && fig.layout.height);
  if (Number.isFinite(fromLayout) && fromLayout > 0) return fromLayout;
  const traces = (fig && fig.data && fig.data.length) || 1;
  return Math.max(320, 280 * traces);
}

function drawFigure(elOrId, fig) {
  const el = typeof elOrId === "string" ? document.getElementById(elOrId) : elOrId;
  if (!el || !fig) return false;
  try {
    const layout = { ...(fig.layout || {}) };
    const height = figureHeight(fig);
    layout.height = height;
    layout.autosize = true;
    delete layout.width;
    el.classList.add("has-fig");
    el.style.height = `${height}px`;
    Plotly.react(el, fig.data || [], layout, { responsive: true }).then(() => {
      el.style.height = `${height}px`;
      try { Plotly.relayout(el, { height, autosize: true }); } catch (_) { /* ignore */ }
    });
    setPlotClearVisible(el.id, true);
    el.scrollIntoView({ behavior: prefersReducedMotion() ? "auto" : "smooth", block: "nearest" });
    return true;
  } catch (err) {
    toast(UI_ERR.plot, "error");
    return false;
  }
}

function setPlotClearVisible(plotId, visible) {
  const map = { "eda-plot": "btn-clear-plot", "ml-plot": "btn-clear-ml-plot" };
  const btn = document.getElementById(map[plotId] || "");
  if (!btn) return;
  btn.hidden = !visible;
  const bar = btn.closest(".plot-bar");
  if (bar) bar.hidden = !visible;
}

function clearPlot(plotId) {
  const el = document.getElementById(plotId);
  if (!el) return;
  try { Plotly.purge(el); } catch (_) { /* ignore */ }
  el.innerHTML = "";
  el.classList.remove("has-fig");
  el.style.height = "";
  setPlotClearVisible(plotId, false);
}

document.getElementById("btn-clear-plot")?.addEventListener("click", () => clearPlot("eda-plot"));
document.getElementById("btn-clear-ml-plot")?.addEventListener("click", () => clearPlot("ml-plot"));

document.getElementById("btn-hist").addEventListener("click", async (ev) => {
  const cols = selected("hist-col");
  if (!cols.length) {
    toast("Elige al menos una columna para el histograma.", "error");
    return;
  }
  try {
    await withBusy(ev.currentTarget, async () => {
      const data = await api(`/api/v1/eda/histogram?${columnsQuery(cols)}`);
      drawFigure("eda-plot", data.figure);
    }, "Dibujando…");
  } catch (err) {
    toast(UI_ERR.plot, "error");
  }
});

document.getElementById("btn-box").addEventListener("click", async (ev) => {
  const cols = selected("box-cols");
  if (!cols.length) {
    toast("Elige al menos una columna para el boxplot.", "error");
    return;
  }
  try {
    await withBusy(ev.currentTarget, async () => {
      const data = await api(`/api/v1/eda/boxplot?${columnsQuery(cols)}`);
      drawFigure("eda-plot", data.figure);
    }, "Dibujando…");
  } catch (err) {
    toast(UI_ERR.plot, "error");
  }
});

document.getElementById("btn-corr").addEventListener("click", async (ev) => {
  try {
    await withBusy(ev.currentTarget, async () => {
      const data = await api("/api/v1/eda/correlation");
      drawFigure("eda-plot", data.figure);
    }, "Dibujando…");
  } catch (err) {
    toast(UI_ERR.plot, "error");
  }
});

const WRANGLE_OK = {
  impute: (n) => (n ? `Imputación aplicada (${n} columnas)` : "Imputación aplicada"),
  drop_duplicates: () => "Duplicados eliminados",
  cast: (n) => (n ? `Tipo convertido (${n} columnas)` : "Tipo convertido"),
  scale: (n) => (n ? `Escalado aplicado (${n} columnas)` : "Escalado aplicado"),
  encode: (n) => (n ? `Codificación aplicada (${n} columnas)` : "Codificación aplicada"),
  rename: () => "Columna renombrada",
  drop_columns: (n) => (n ? `Columnas eliminadas (${n})` : "Columnas eliminadas"),
};

async function wrangle(op, extra = {}, anchor = null) {
  try {
    await withBusy(anchor, async () => {
      const data = await api("/api/v1/wrangling/apply", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ op, ...extra }),
      });
      applyPreview(data.preview);
      const n = (extra.columns || []).length;
      const msg = (WRANGLE_OK[op] || (() => "Transformación aplicada"))(n);
      toast(msg, "ok", anchor);
    });
  } catch (err) {
    toast(UI_ERR.wrangle, "error", anchor);
  }
}

document.querySelectorAll("[data-op]").forEach((btn) => {
  btn.addEventListener("click", () => {
    const op = btn.dataset.op;
    const extra = {};
    if (op === "impute") {
      extra.columns = selected("impute-cols");
      extra.strategy = document.getElementById("impute-strategy").value;
      extra.value = document.getElementById("impute-value").value;
    } else if (op === "cast") {
      extra.columns = selected("cast-col");
      extra.target_type = document.getElementById("cast-type").value;
    } else if (op === "scale") {
      extra.columns = selected("scale-cols");
      extra.method = document.getElementById("scale-method").value;
    } else if (op === "encode") {
      extra.columns = selected("encode-cols");
      extra.method = document.getElementById("encode-method").value;
    } else if (op === "rename") {
      extra.columns = [document.getElementById("rename-old").value];
      extra.new_name = document.getElementById("rename-new").value;
    } else if (op === "drop_columns") {
      extra.columns = selected("drop-cols");
    }
    wrangle(op, extra, btn);
  });
});

document.getElementById("btn-undo").addEventListener("click", async (ev) => {
  try {
    await withBusy(ev.currentTarget, async () => {
      const data = await api("/api/v1/wrangling/undo", { method: "POST" });
      if (!data.undone) {
        toast("Nada que deshacer", "info");
        return;
      }
      applyPreview(data.preview);
      toast("Se deshizo la última operación", "ok");
    });
  } catch (err) {
    toast(UI_ERR.wrangle, "error");
  }
});

document.getElementById("btn-undo-all").addEventListener("click", async (ev) => {
  try {
    await withBusy(ev.currentTarget, async () => {
      const data = await api("/api/v1/wrangling/reset", { method: "POST" });
      if (!data.reset) {
        toast("Nada que deshacer", "info");
        return;
      }
      applyPreview(data.preview);
      toast("Se restauró el dataset original", "ok");
    });
  } catch (err) {
    toast(UI_ERR.wrangle, "error");
  }
});

function syncAlgo() {
  const task = document.getElementById("ml-task").value;
  const list = task === "Clasificación" ? classifiers : regressors;
  fillSelect(document.getElementById("ml-algo"), list, { multipleKeep: false });
}

async function loadMlOptions() {
  try {
    const opts = await api("/api/v1/ml/options");
    classifiers = opts.classifiers;
    regressors = opts.regressors;
    fillSelect(document.getElementById("ml-target"), opts.columns, { multipleKeep: false });
    fillPicker(document.getElementById("ml-features"), opts.columns);
    fillPicker(document.getElementById("ml-unsup-feats"), opts.numeric_columns);
    const t = document.getElementById("ml-target").value;
    if (opts.suggested[t]) document.getElementById("ml-task").value = opts.suggested[t];
    syncAlgo();
  } catch (err) {
    toast(UI_ERR.ml, "error");
  }
}

document.getElementById("ml-task").addEventListener("change", syncAlgo);
document.getElementById("ml-target").addEventListener("change", loadMlOptions);

document.getElementById("btn-train").addEventListener("click", async (ev) => {
  try {
    await withBusy(ev.currentTarget, async () => {
      const data = await api("/api/v1/ml/supervised", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          target: document.getElementById("ml-target").value,
          features: selected("ml-features"),
          task_type: document.getElementById("ml-task").value,
          algorithm: document.getElementById("ml-algo").value,
          test_size: Number(document.getElementById("ml-test").value),
        }),
      });
      document.getElementById("ml-metrics").textContent = JSON.stringify(data, (k, v) => (k === "figures" ? "[figuras]" : v), 2);
      if (data.figures && data.figures[0]) drawFigure("ml-plot", data.figures[0]);
      toast("Modelo entrenado", "ok");
    }, "Entrenando…");
  } catch (err) {
    toast(UI_ERR.ml, "error");
  }
});

document.getElementById("btn-unsup").addEventListener("click", async (ev) => {
  try {
    await withBusy(ev.currentTarget, async () => {
      const data = await api("/api/v1/ml/unsupervised", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          features: selected("ml-unsup-feats"),
          method: document.getElementById("ml-unsup-method").value,
          k: Number(document.getElementById("ml-k").value),
          max_k: Number(document.getElementById("ml-k").value),
          eps: Number(document.getElementById("ml-eps").value),
          min_samples: Number(document.getElementById("ml-min-samples").value),
          n_components: Number(document.getElementById("ml-pca-dim").value),
        }),
      });
      document.getElementById("ml-metrics").textContent = JSON.stringify(data, (k, v) => (k === "figures" ? "[figuras]" : v), 2);
      if (data.figures && data.figures[0]) drawFigure("ml-plot", data.figures[0]);
      toast("Análisis no supervisado listo", "ok");
    }, "Ejecutando…");
  } catch (err) {
    toast(UI_ERR.ml, "error");
  }
});

function assistantPlain(content) {
  return String(content || "").replace(/```python[\s\S]*?```/g, "").trim();
}

function typeText(el, text) {
  const plain = assistantPlain(text);
  if (prefersReducedMotion() || plain.length < 12) {
    el.innerHTML = esc(plain).replace(/\n/g, "<br>");
    return Promise.resolve();
  }
  el.innerHTML = "";
  const step = Math.max(2, Math.ceil(plain.length / 90));
  let i = 0;
  return new Promise((resolve) => {
    function tick() {
      i = Math.min(plain.length, i + step);
      el.innerHTML = esc(plain.slice(0, i)).replace(/\n/g, "<br>");
      const log = document.getElementById("chat-log");
      log.scrollTop = log.scrollHeight;
      if (i >= plain.length) resolve();
      else requestAnimationFrame(tick);
    }
    tick();
  });
}

function addRetryButton(parent, onClick) {
  const existing = parent.querySelector(".retry-btn");
  if (existing) existing.remove();
  const btn = document.createElement("button");
  btn.type = "button";
  btn.className = "ghost retry-btn";
  btn.textContent = "Reiniciar respuesta";
  btn.addEventListener("click", async () => {
    try {
      await withBusy(btn, () => onClick(btn), "Reiniciando…");
    } catch (_) { /* shown in chat */ }
  });
  parent.appendChild(btn);
  return btn;
}

async function copyText(text) {
  try {
    await navigator.clipboard.writeText(text);
  } catch (_) {
    const ta = document.createElement("textarea");
    ta.value = text;
    ta.setAttribute("readonly", "");
    ta.style.position = "fixed";
    ta.style.left = "-9999px";
    document.body.appendChild(ta);
    ta.select();
    document.execCommand("copy");
    ta.remove();
  }
}

function appendCodeBlock(div, code) {
  const wrap = document.createElement("div");
  wrap.className = "code-run";
  const pre = document.createElement("pre");
  pre.textContent = code;
  if (!prefersReducedMotion()) pre.classList.add("is-revealing");
  const actions = document.createElement("div");
  actions.className = "code-run-actions";
  const runBtn = document.createElement("button");
  runBtn.type = "button";
  runBtn.textContent = "Ejecutar";
  runBtn.addEventListener("click", () => runCode(code, runBtn));
  const copyBtn = document.createElement("button");
  copyBtn.type = "button";
  copyBtn.className = "ghost";
  copyBtn.textContent = "Copiar";
  copyBtn.setAttribute("aria-label", "Copiar código");
  copyBtn.addEventListener("click", async () => {
    try {
      await copyText(code);
      if (!copyBtn.dataset.label) copyBtn.dataset.label = "Copiar";
      copyBtn.dataset.okLabel = "Copiado";
      await markButtonOk(copyBtn, 1500);
    } catch (_) {
      toast(UI_ERR.copy, "error");
    }
  });
  actions.appendChild(runBtn);
  actions.appendChild(copyBtn);
  wrap.appendChild(pre);
  wrap.appendChild(actions);
  div.appendChild(wrap);
}

function setUserBubbleText(div, content) {
  let body = div.querySelector(".bubble-text");
  if (!body) {
    body = document.createElement("div");
    body.className = "bubble-text";
    div.prepend(body);
  }
  body.innerHTML = esc(content).replace(/\n/g, "<br>");
  div.dataset.message = content;
}

function addEditButton(div, content) {
  div.dataset.message = content;
  if (div.querySelector(".bubble-edit")) return;
  const edit = document.createElement("button");
  edit.type = "button";
  edit.className = "bubble-edit";
  edit.textContent = "Editar";
  edit.setAttribute("aria-label", "Editar mensaje");
  edit.addEventListener("click", () => {
    const ta = document.getElementById("chat-input");
    ta.value = div.dataset.message || "";
    editingBubble = div;
    autosizeComposer();
    ta.focus();
  });
  div.appendChild(edit);
}

function removeFollowingAssistants(userBubble) {
  let sib = userBubble.nextElementSibling;
  while (sib && sib.classList.contains("assistant")) {
    const next = sib.nextElementSibling;
    sib.remove();
    sib = next;
  }
}

function setSendMode(mode) {
  const form = document.getElementById("chat-form");
  const btn = form && form.querySelector("button[type='submit']");
  if (!btn) return;
  if (!btn.dataset.label) btn.dataset.label = "Enviar";
  btn.classList.remove("danger", "is-busy", "is-ok");
  btn.disabled = false;
  btn.removeAttribute("aria-busy");
  if (mode === "stop") {
    btn.textContent = "Detener";
    btn.classList.add("danger");
  } else {
    btn.textContent = btn.dataset.label;
  }
}

function appendChat(role, content, codeBlocks = []) {
  const log = document.getElementById("chat-log");
  const div = document.createElement("div");
  div.className = `bubble ${role}`;
  const body = document.createElement("div");
  body.className = "bubble-text";
  body.innerHTML = esc(assistantPlain(content)).replace(/\n/g, "<br>");
  div.appendChild(body);
  if (role === "user") addEditButton(div, content);
  codeBlocks.forEach((code) => appendCodeBlock(div, code));
  log.appendChild(div);
  log.scrollTop = log.scrollHeight;
  return div;
}

async function appendAssistant(content, codeBlocks = []) {
  const log = document.getElementById("chat-log");
  const div = document.createElement("div");
  div.className = "bubble assistant";
  const body = document.createElement("div");
  body.className = "bubble-text";
  div.appendChild(body);
  log.appendChild(div);
  await typeText(body, content);
  codeBlocks.forEach((code) => appendCodeBlock(div, code));
  log.scrollTop = log.scrollHeight;
  return div;
}

function showThinking() {
  const log = document.getElementById("chat-log");
  const div = document.createElement("div");
  div.className = "bubble assistant is-thinking";
  div.innerHTML = `<span class="thinking-label">Pensando</span><span class="dots" aria-hidden="true"><span>.</span><span>.</span><span>.</span></span>`;
  log.appendChild(div);
  log.scrollTop = log.scrollHeight;
  return div;
}

function ensureResultBox(runBtn) {
  const actions = runBtn && runBtn.closest(".code-run-actions");
  const after = actions || runBtn;
  let box = after ? after.nextElementSibling : null;
  if (!box || !box.classList.contains("exec-result")) {
    box = document.createElement("div");
    box.className = "exec-result";
    if (after) after.after(box);
  }
  return box;
}

function renderExecResult(box, data) {
  box.innerHTML = "";
  box.classList.remove("is-error");
  if (data.stdout) {
    const pre = document.createElement("pre");
    pre.className = "exec-stdout";
    pre.textContent = data.stdout;
    box.appendChild(pre);
  }
  const tableSrc = data.display || (data.mutated ? data.preview : null);
  if (tableSrc && tableSrc.columns && tableSrc.columns.length) {
    const wrap = document.createElement("div");
    wrap.className = "table-wrap exec-table";
    renderTable(wrap, tableSrc);
    box.appendChild(wrap);
  }
  if (data.fig) {
    const p = document.createElement("p");
    p.className = "exec-fig-note";
    p.textContent = activeTab === "ml"
      ? "Gráfico mostrado en Machine Learning."
      : "Gráfico mostrado en Análisis descriptivo.";
    box.appendChild(p);
  }
  if (!box.childNodes.length) {
    const p = document.createElement("p");
    p.className = "exec-ok";
    p.textContent = "Código ejecutado.";
    box.appendChild(p);
  }
}

function showCopilotFigure(fig) {
  const destTab = activeTab === "ml" ? "ml" : "eda";
  const destPlot = destTab === "ml" ? "ml-plot" : "eda-plot";
  const label = destTab === "ml" ? "Machine Learning" : "Análisis descriptivo";
  setActiveTab(destTab);
  drawFigure(destPlot, fig);
  toast(`Gráfico en ${label}`, "info");
}

async function runCode(code, runBtn) {
  const box = runBtn ? ensureResultBox(runBtn) : null;
  if (box) {
    box.classList.remove("is-error");
    box.innerHTML = `<p class="exec-status">Ejecutando…</p>`;
  }
  try {
    await withBusy(runBtn, async () => {
      const data = await api("/api/v1/chat/execute", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ code }),
      });
      if (!data.success) {
        if (box) {
          box.classList.add("is-error");
          box.innerHTML = `<p class="exec-error">${esc(data.error || UI_ERR.execute)}</p>`;
        }
        toast(UI_ERR.execute, "error");
        throw new Error(UI_ERR.execute);
      }
      if (data.mutated && data.preview) applyPreview(data.preview);
      if (data.fig) showCopilotFigure(data.fig);
      if (box) renderExecResult(box, data);
      const log = document.getElementById("chat-log");
      log.scrollTop = log.scrollHeight;
    }, "Ejecutando…");
  } catch (err) {
    if (box && !box.classList.contains("is-error")) {
      box.classList.add("is-error");
      box.innerHTML = `<p class="exec-error">${esc(UI_ERR.execute)}</p>`;
      toast(UI_ERR.execute, "error");
    }
  }
}

document.getElementById("chat-input").addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    document.getElementById("chat-form").requestSubmit();
  }
});
document.getElementById("chat-input").addEventListener("input", autosizeComposer);

function autosizeComposer() {
  const ta = document.getElementById("chat-input");
  if (!ta) return;
  ta.style.height = "auto";
  const cap = isChatStacked() ? Math.round(window.innerHeight * 0.3) : 230;
  ta.style.height = `${Math.min(cap, Math.max(52, ta.scrollHeight))}px`;
}

let lastChatMessage = "";

async function requestAssistant(message, { echoUser = true } = {}) {
  const form = document.getElementById("chat-form");
  if (!message || form.dataset.busy === "1") return;
  lastChatMessage = message;
  if (editingBubble && echoUser) {
    setUserBubbleText(editingBubble, message);
    removeFollowingAssistants(editingBubble);
    editingBubble = null;
    echoUser = false;
  } else if (echoUser) {
    appendChat("user", message);
  }
  form.dataset.busy = "1";
  setSendMode("stop");
  const thinking = showThinking();
  chatAbort = new AbortController();
  try {
    const data = await api("/api/v1/chat/message", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message, tab: TAB_TO_AGENT[activeTab] }),
      signal: chatAbort.signal,
    });
    thinking.remove();
    const bubble = await appendAssistant(data.content, data.code_blocks || []);
    addRetryButton(bubble, async () => {
      bubble.remove();
      await requestAssistant(lastChatMessage, { echoUser: false });
    });
  } catch (err) {
    if (thinking.isConnected) thinking.remove();
    if (isAbortError(err)) {
      toast(UI_ERR.abort, "info");
      const ta = document.getElementById("chat-input");
      if (ta && !ta.value.trim()) {
        ta.value = lastChatMessage;
        autosizeComposer();
      }
      return;
    }
    const div = appendChat("assistant", UI_ERR.chat);
    div.classList.add("is-error");
    addRetryButton(div, async () => {
      div.remove();
      await requestAssistant(lastChatMessage, { echoUser: false });
    });
  } finally {
    chatAbort = null;
    form.dataset.busy = "0";
    setSendMode("send");
  }
}

document.getElementById("chat-form").addEventListener("submit", async (ev) => {
  ev.preventDefault();
  const form = document.getElementById("chat-form");
  if (form.dataset.busy === "1") {
    if (chatAbort) chatAbort.abort();
    return;
  }
  const input = document.getElementById("chat-input");
  const message = input.value.trim();
  if (!message) return;
  input.value = "";
  autosizeComposer();
  await requestAssistant(message);
});

function clampChatWidth(px, workspace) {
  const maxW = Math.round(workspace.clientWidth * CHAT_MAX_RATIO);
  return Math.min(Math.max(CHAT_MIN_W, px), Math.max(CHAT_MIN_W, maxW));
}

function clampChatHeight(px) {
  const minH = 200;
  const maxH = Math.round(window.innerHeight * 0.55);
  return Math.min(Math.max(minH, px), maxH);
}

function applyChatSize() {
  const ws = document.querySelector(".workspace");
  const splitter = document.getElementById("splitter");
  if (!ws) return;
  if (ws.classList.contains("is-collapsed")) {
    ws.style.removeProperty("--chat-w");
    ws.style.removeProperty("--chat-h");
    if (splitter) splitter.setAttribute("aria-orientation", isChatStacked() ? "horizontal" : "vertical");
    return;
  }
  if (isChatStacked()) {
    const stored = Number(localStorage.getItem(CHAT_H_KEY));
    const h = clampChatHeight(Number.isFinite(stored) && stored > 0 ? stored : Math.round(window.innerHeight * 0.4));
    ws.style.setProperty("--chat-h", `${h}px`);
    if (splitter) splitter.setAttribute("aria-orientation", "horizontal");
  } else {
    const stored = Number(localStorage.getItem(CHAT_W_KEY));
    const w = clampChatWidth(Number.isFinite(stored) && stored > 0 ? stored : 360, ws);
    ws.style.setProperty("--chat-w", `${w}px`);
    if (splitter) splitter.setAttribute("aria-orientation", "vertical");
  }
}

function bindSplitter() {
  const splitter = document.getElementById("splitter");
  const ws = document.querySelector(".workspace");
  let dragging = false;

  splitter.addEventListener("pointerdown", (e) => {
    if (ws.classList.contains("is-collapsed")) return;
    dragging = true;
    ws.classList.add("is-resizing");
    splitter.setPointerCapture(e.pointerId);
    e.preventDefault();
  });
  splitter.addEventListener("pointermove", (e) => {
    if (!dragging) return;
    const rect = ws.getBoundingClientRect();
    if (isChatStacked()) {
      const h = clampChatHeight(rect.bottom - e.clientY);
      localStorage.setItem(CHAT_H_KEY, String(h));
    } else {
      const w = clampChatWidth(rect.right - e.clientX, ws);
      localStorage.setItem(CHAT_W_KEY, String(w));
    }
    applyChatSize();
  });
  const stop = () => {
    if (!dragging) return;
    dragging = false;
    ws.classList.remove("is-resizing");
  };
  splitter.addEventListener("pointerup", stop);
  splitter.addEventListener("pointercancel", stop);
}

window.addEventListener("resize", () => {
  applyChatSize();
  autosizeComposer();
  const el = document.getElementById("toast");
  if (el && !el.hidden) placeToast(el);
});
bindSplitter();
applyChatSize();
autosizeComposer();

refreshPreview();
