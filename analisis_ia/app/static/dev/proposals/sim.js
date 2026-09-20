/**
 * Local simulation of ingest → EDA → clean → ML → copilot for design proposals.
 * No API calls. One theme CSS is loaded from ?tema=.
 */
(() => {
  const TEMAS = {
    gaceta: { title: "Gaceta", kicker: "edición I · papel de periódico", file: "tema-gaceta.css" },
    observatorio: { title: "Observatorio", kicker: "edición II · carta nocturna", file: "tema-observatorio.css" },
    atelier: { title: "Atelier", kicker: "edición III · mesa de dibujo", file: "tema-atelier.css" },
    herbario: { title: "Herbario", kicker: "edición IV · cuaderno de campo", file: "tema-herbario.css" },
  };
  const PLOT = {
    gaceta: { paper: "#fffaf1", plot: "#fffaf1", ink: "#14110e", accent: "#b42318" },
    observatorio: { paper: "#16202e", plot: "#121b28", ink: "#dbe3ec", accent: "#c47a3a" },
    atelier: { paper: "#fdfbf5", plot: "#f6f3ea", ink: "#2c2a26", accent: "#2a6f97" },
    herbario: { paper: "#fbf7ee", plot: "#f3ecdd", ink: "#2a2f2a", accent: "#3d5c45" },
  };
  const CLASIF = ["Árbol de decisión", "Random Forest", "Regresión logística", "KNN"];
  const REGRES = ["Regresión lineal", "Random Forest", "Gradient Boosting"];
  const PICKER_IDS = [
    "hist-col", "box-cols", "impute-cols", "cast-col", "scale-cols",
    "encode-cols", "drop-cols", "ml-features", "ml-unsup-feats",
  ];
  const RAW_ROWS = [
    { fecha: "2024-01-12", categoria: "A", region: "Norte", precio: 118.2, unidades: 12, descuento: 0.05 },
    { fecha: "2024-01-18", categoria: "B", region: "Sur", precio: 97.4, unidades: 8, descuento: 0.1 },
    { fecha: "2024-02-03", categoria: "C", region: "Norte", precio: 142.1, unidades: 5, descuento: null },
    { fecha: "2024-02-11", categoria: "A", region: "Este", precio: 131.0, unidades: 9, descuento: 0.0 },
    { fecha: "2024-02-22", categoria: "B", region: "Oeste", precio: null, unidades: 14, descuento: 0.15 },
    { fecha: "2024-03-04", categoria: "C", region: "Norte", precio: 155.8, unidades: 3, descuento: 0.02 },
    { fecha: "2024-03-19", categoria: "A", region: "Sur", precio: 124.6, unidades: 11, descuento: null },
    { fecha: "2024-04-01", categoria: "D", region: "Este", precio: 88.0, unidades: 20, descuento: 0.2 },
    { fecha: "2024-04-14", categoria: "B", region: "Norte", precio: 110.3, unidades: 7, descuento: 0.08 },
    { fecha: "2024-04-14", categoria: "B", region: "Norte", precio: 110.3, unidades: 7, descuento: 0.08 },
    { fecha: "2024-05-09", categoria: "C", region: "Oeste", precio: 149.9, unidades: 4, descuento: 0.0 },
    { fecha: "2024-05-21", categoria: "A", region: "Norte", precio: null, unidades: 10, descuento: 0.12 },
  ];

  const params = new URLSearchParams(location.search);
  const tema = TEMAS[params.get("tema")] ? params.get("tema") : "gaceta";
  document.documentElement.dataset.tema = tema;
  const temaLink = document.getElementById("tema-css");
  if (temaLink) temaLink.href = `./${TEMAS[tema].file}`;
  document.title = `${TEMAS[tema].title} · analisis_ia`;
  const titleEl = document.getElementById("prop-title");
  const kickerEl = document.getElementById("prop-kicker");
  if (titleEl) titleEl.textContent = TEMAS[tema].title;
  if (kickerEl) kickerEl.textContent = TEMAS[tema].kicker;
  document.querySelectorAll(".prop-switch a").forEach((a) => {
    a.classList.toggle("is-current", a.dataset.tema === tema);
  });

  const state = {
    fileName: "",
    origin: null,
    preview: null,
    history: [],
    dtypes: {},
    chatMode: "agent",
    chatBusy: false,
  };

  let toastTimer = 0;
  const CHAT_W_KEY = `prop-chat-w-${tema}`;
  const CHAT_H_KEY = `prop-chat-h-${tema}`;

  const esc = (v) => String(v ?? "")
    .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
  const clone = (v) => JSON.parse(JSON.stringify(v));
  const sleep = (ms) => new Promise((ok) => setTimeout(ok, prefersReduced() ? Math.min(80, ms) : ms));
  const prefersReduced = () => window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const isChatStacked = () => window.matchMedia("(max-width: 1100px)").matches;
  const isNumType = (t) => /int|float|number/i.test(t || "");
  const isBlank = (v) => v === null || v === undefined || v === "";

  function toast(msg, kind = "ok") {
    const el = document.getElementById("toast");
    if (!el) return;
    const tone = kind === "error" ? "error" : (kind === "info" ? "info" : "ok");
    el.textContent = msg;
    el.hidden = false;
    el.classList.remove("is-ok", "is-error", "is-info", "is-out");
    el.classList.add(`is-${tone}`);
    const tools = document.querySelector(".tools");
    if (tools) {
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
    const ms = tone === "error" ? 5200 : 4000;
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => {
      el.classList.add("is-out");
      toastTimer = setTimeout(() => { el.hidden = true; el.classList.remove("is-out"); }, 220);
    }, ms);
  }

  async function withBusy(btn, fn) {
    if (!btn) return fn();
    btn.classList.remove("is-ok");
    btn.classList.add("is-busy");
    await sleep(380);
    try {
      await fn();
      btn.classList.remove("is-busy");
      btn.classList.add("is-ok");
      setTimeout(() => btn.classList.remove("is-ok"), 900);
    } catch (err) {
      btn.classList.remove("is-busy");
      throw err;
    }
  }

  function renderTable(container, preview) {
    if (!container) return;
    if (!preview || !preview.columns || !preview.columns.length) {
      container.innerHTML = "";
      return;
    }
    const head = preview.columns.map((c) => `<th>${esc(c)}</th>`).join("");
    const body = (preview.rows || []).map((row) => {
      const tds = preview.columns.map((c) => `<td>${esc(isBlank(row[c]) ? "—" : row[c])}</td>`).join("");
      return `<tr>${tds}</tr>`;
    }).join("");
    container.innerHTML = `<table><thead><tr>${head}</tr></thead><tbody>${body}</tbody></table>`;
  }

  function recordsTable(container, rows) {
    if (!container) return;
    if (!rows || !rows.length) { container.innerHTML = ""; return; }
    const cols = Object.keys(rows[0]);
    renderTable(container, { columns: cols, rows });
  }

  function selected(idOrEl) {
    const el = typeof idOrEl === "string" ? document.getElementById(idOrEl) : idOrEl;
    if (!el) return [];
    if (el.matches?.("[data-picker]") || el.classList.contains("picker")) {
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
      `<button type="button" class="picker-chip" data-value="${esc(v)}">${esc(v)}<span aria-hidden="true">×</span></button>`
    )).join("");
    chips.querySelectorAll(".picker-chip").forEach((btn) => {
      btn.addEventListener("click", (ev) => {
        ev.stopPropagation();
        const cb = [...root.querySelectorAll('input[type="checkbox"]')].find((i) => i.value === btn.dataset.value);
        if (cb) { cb.checked = false; renderChips(root); }
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
    menu.innerHTML = items.length
      ? items.map((c) => `<label class="picker-opt"><input type="checkbox" value="${esc(c)}" ${prev.has(c) ? "checked" : ""} /><span>${esc(c)}</span></label>`).join("")
      : `<p class="picker-empty">Sin columnas</p>`;
    renderChips(root);
  }

  function fillSelect(sel, items) {
    if (!sel) return;
    const prev = sel.value;
    sel.innerHTML = items.map((c) => `<option value="${esc(c)}">${esc(c)}</option>`).join("");
    if (prev && items.includes(prev)) sel.value = prev;
  }

  function countNulls(rows, col) {
    return rows.filter((r) => isBlank(r[col])).length;
  }

  function countDups(rows) {
    const seen = new Set();
    let n = 0;
    rows.forEach((r) => {
      const key = JSON.stringify(r);
      if (seen.has(key)) n += 1;
      else seen.add(key);
    });
    return n;
  }

  function numericCols(preview) {
    return preview.columns.filter((c) => isNumType(preview.dtypes[c]));
  }

  function catCols(preview) {
    return preview.columns.filter((c) => !isNumType(preview.dtypes[c]));
  }

  function mean(vals) {
    const xs = vals.filter((v) => !isBlank(v)).map(Number).filter(Number.isFinite);
    if (!xs.length) return 0;
    return xs.reduce((a, b) => a + b, 0) / xs.length;
  }

  function median(vals) {
    const xs = vals.filter((v) => !isBlank(v)).map(Number).filter(Number.isFinite).sort((a, b) => a - b);
    if (!xs.length) return 0;
    const m = Math.floor(xs.length / 2);
    return xs.length % 2 ? xs[m] : (xs[m - 1] + xs[m]) / 2;
  }

  function mode(vals) {
    const freq = new Map();
    vals.filter((v) => !isBlank(v)).forEach((v) => freq.set(v, (freq.get(v) || 0) + 1));
    let best = vals.find((v) => !isBlank(v));
    let n = 0;
    freq.forEach((c, k) => { if (c > n) { n = c; best = k; } });
    return best;
  }

  function snapshotFrom(rows, dtypes, fileName) {
    const columns = Object.keys(rows[0] || dtypes);
    return {
      columns,
      rows: rows.slice(0, 20),
      allRows: rows,
      dtypes: { ...dtypes },
      shape: [rows.length, columns.length],
      memory: `${Math.max(1, Math.round(rows.length * columns.length * 0.08))} KB`,
      duplicate_rows: countDups(rows),
      fileName,
    };
  }

  function makeOrigin(fileName) {
    const dtypes = {
      fecha: "object", categoria: "object", region: "object",
      precio: "float64", unidades: "int64", descuento: "float64",
    };
    return snapshotFrom(clone(RAW_ROWS), dtypes, fileName);
  }

  function applyPreview(preview, fileName, { pushHistory = false } = {}) {
    if (pushHistory && state.preview) {
      state.history.push(clone(state.preview));
      if (state.history.length > 15) state.history.shift();
    }
    state.preview = preview;
    state.fileName = fileName || preview.fileName || state.fileName;
    const chip = document.getElementById("dataset-chip");
    chip.classList.remove("muted");
    chip.textContent = `${state.fileName} · ${preview.shape[0]} × ${preview.shape[1]}`;
    document.getElementById("dup-count").textContent = preview.duplicate_rows;
    renderTable(document.getElementById("ingest-table"), preview);
    renderTable(document.getElementById("clean-table"), preview);
    renderIngestMeta(preview);
    syncColumns(preview);
    paintEda(preview);
    ["eda-empty", "clean-empty", "ml-empty"].forEach((id) => {
      const el = document.getElementById(id);
      if (el) el.hidden = true;
    });
  }

  function renderIngestMeta(preview) {
    const metrics = document.getElementById("ingest-meta");
    const tech = document.getElementById("ingest-tech");
    const wrap = document.getElementById("ingest-tech-wrap");
    const [rows, cols] = preview.shape;
    metrics.innerHTML = [
      ["Filas", rows], ["Columnas", cols], ["Formato", "csv"], ["Memoria", preview.memory],
    ].map(([k, v]) => `<span class="metric"><small>${esc(k)}</small><b>${esc(v)}</b></span>`).join("");
    tech.innerHTML = [
      ["Archivo", state.fileName], ["Encoding", "utf-8"], ["Separador", ","],
    ].map(([k, v]) => `<div class="tech-item"><dt>${esc(k)}</dt><dd>${esc(v)}</dd></div>`).join("");
    wrap.hidden = false;
  }

  function syncColumns(preview) {
    const cols = preview.columns;
    const nums = numericCols(preview);
    const cats = catCols(preview);
    fillPicker(document.getElementById("impute-cols"), cols);
    fillPicker(document.getElementById("cast-col"), cols);
    fillPicker(document.getElementById("drop-cols"), cols);
    fillPicker(document.getElementById("encode-cols"), cats.length ? cats : cols);
    fillPicker(document.getElementById("ml-features"), cols);
    fillPicker(document.getElementById("scale-cols"), nums.length ? nums : cols);
    fillPicker(document.getElementById("ml-unsup-feats"), nums.length ? nums : cols);
    fillPicker(document.getElementById("box-cols"), nums.length ? nums : cols);
    fillPicker(document.getElementById("hist-col"), nums.length ? nums : cols);
    fillSelect(document.getElementById("rename-old"), cols);
    fillSelect(document.getElementById("ml-target"), cols);
    fillSelect(document.getElementById("eda-cat-sel"), ["", ...cats]);
    fillAlgos();
  }

  function fillAlgos() {
    const task = document.getElementById("ml-task").value;
    fillSelect(document.getElementById("ml-algo"), task === "Regresión" ? REGRES : CLASIF);
  }

  function paintEda(preview) {
    const rows = preview.allRows;
    const cols = preview.columns;
    document.getElementById("eda-metrics").innerHTML = [
      ["Filas", preview.shape[0]],
      ["Columnas", preview.shape[1]],
      ["Nulos", cols.reduce((n, c) => n + countNulls(rows, c), 0)],
      ["Duplicados", preview.duplicate_rows],
    ].map(([k, v]) => `<div class="metric"><small>${esc(k)}</small><b>${esc(v)}</b></div>`).join("");

    recordsTable(document.getElementById("eda-dtypes"), cols.map((c) => ({
      columna: c, dtype: preview.dtypes[c], nulos: countNulls(rows, c), unicos: new Set(rows.map((r) => r[c])).size,
    })));

    const nums = numericCols(preview);
    recordsTable(document.getElementById("eda-numeric"), nums.map((c) => {
      const xs = rows.map((r) => r[c]).filter((v) => !isBlank(v)).map(Number).filter(Number.isFinite);
      const mn = xs.length ? Math.min(...xs) : "—";
      const mx = xs.length ? Math.max(...xs) : "—";
      return { columna: c, media: mean(xs).toFixed(2), mediana: median(xs).toFixed(2), min: mn, max: mx };
    }));

    const cats = catCols(preview);
    recordsTable(document.getElementById("eda-cats"), cats.map((c) => ({
      columna: c, unicos: new Set(rows.map((r) => r[c])).size, moda: mode(rows.map((r) => r[c])),
    })));

    recordsTable(document.getElementById("eda-quality"), cols.map((c) => {
      const nulos = countNulls(rows, c);
      return { columna: c, nulos, pct: `${((nulos / rows.length) * 100).toFixed(1)}%`, duplicados_col: "—" };
    }));
  }

  function plotLayout(title) {
    const p = PLOT[tema];
    return {
      title: { text: title, font: { size: 13 } },
      height: 280,
      margin: { t: 42, r: 16, b: 42, l: 48 },
      paper_bgcolor: p.paper,
      plot_bgcolor: p.plot,
      font: { family: "IBM Plex Sans, sans-serif", color: p.ink },
      colorway: [p.accent],
    };
  }

  function showPlot(target, fig) {
    const el = document.getElementById(target);
    const bar = el?.previousElementSibling?.classList.contains("plot-bar")
      ? el.previousElementSibling
      : el.parentElement.querySelector(".plot-bar");
    if (window.Plotly) {
      Plotly.react(el, fig.data, fig.layout, { displayModeBar: false, responsive: true });
    } else {
      el.innerHTML = `<p class="hint">Plotly no cargó; la figura iría aquí.</p>`;
    }
    if (bar) {
      bar.hidden = false;
      const btn = bar.querySelector("button");
      if (btn) btn.hidden = false;
    }
    el.scrollIntoView({ block: "nearest", behavior: prefersReduced() ? "auto" : "smooth" });
  }

  function loadSample(fileName = "ventas_demo.csv") {
    const preview = makeOrigin(fileName);
    state.origin = clone(preview);
    state.history = [];
    applyPreview(preview, fileName);
    toast("Archivo cargado (simulación)");
  }

  function requirePreview() {
    if (state.preview) return true;
    toast("Carga un dataset primero.", "error");
    return false;
  }

  function hasNulls(preview) {
    return preview.columns.some((c) => countNulls(preview.allRows, c) > 0);
  }

  function mutate(fn, msg) {
    const nextRows = fn(clone(state.preview.allRows), clone(state.preview.dtypes));
    const dtypes = nextRows._dtypes || state.preview.dtypes;
    delete nextRows._dtypes;
    const preview = snapshotFrom(nextRows, dtypes, state.fileName);
    applyPreview(preview, state.fileName, { pushHistory: true });
    toast(msg);
  }

  document.querySelectorAll(".tab[data-tab]").forEach((btn) => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".tab[data-tab]").forEach((t) => t.classList.toggle("is-active", t === btn));
      document.querySelectorAll(".panel").forEach((p) => p.classList.toggle("is-active", p.id === `panel-${btn.dataset.tab}`));
    });
  });

  document.querySelectorAll("[data-subtabs]").forEach((root) => {
    root.querySelectorAll(".subtab").forEach((btn) => {
      btn.addEventListener("click", () => {
        root.querySelectorAll(".subtab").forEach((s) => s.classList.toggle("is-active", s === btn));
        root.querySelectorAll(".subpane").forEach((p) => p.classList.toggle("is-active", p.id === btn.dataset.pane));
      });
    });
  });

  PICKER_IDS.forEach((id) => initPicker(document.getElementById(id)));
  document.addEventListener("click", () => closeAllPickers());

  const drop = document.getElementById("dropzone");
  const input = document.getElementById("file-input");
  let dragDepth = 0;
  input.addEventListener("change", () => {
    const file = input.files[0];
    if (file) loadSample(file.name);
    input.value = "";
  });
  drop.addEventListener("dragenter", (e) => { e.preventDefault(); dragDepth += 1; drop.classList.add("is-dragover"); });
  drop.addEventListener("dragover", (e) => { e.preventDefault(); e.dataTransfer.dropEffect = "copy"; });
  drop.addEventListener("dragleave", (e) => {
    e.preventDefault();
    dragDepth -= 1;
    if (dragDepth <= 0) { dragDepth = 0; drop.classList.remove("is-dragover"); }
  });
  drop.addEventListener("drop", (e) => {
    e.preventDefault();
    dragDepth = 0;
    drop.classList.remove("is-dragover");
    const file = e.dataTransfer.files && e.dataTransfer.files[0];
    if (file) loadSample(file.name);
  });
  document.getElementById("btn-sample").addEventListener("click", () => loadSample());

  document.getElementById("db-engine").addEventListener("change", () => {
    const sqlite = document.getElementById("db-engine").value === "sqlite";
    ["db-host-wrap", "db-port-wrap", "db-name-wrap", "db-user-wrap", "db-pass-wrap"].forEach((id) => {
      document.getElementById(id).hidden = sqlite;
    });
    document.getElementById("db-path-wrap").hidden = !sqlite;
  });
  document.getElementById("btn-db-connect").addEventListener("click", (ev) => {
    withBusy(ev.currentTarget, async () => {
      toast("Conexión a base de datos aún no está disponible (501).", "error");
    });
  });

  document.getElementById("eda-cat-sel").addEventListener("change", () => {
    if (!state.preview) return;
    const col = document.getElementById("eda-cat-sel").value;
    if (!col) { document.getElementById("eda-cat-detail").innerHTML = ""; return; }
    const freq = new Map();
    state.preview.allRows.forEach((r) => {
      const k = isBlank(r[col]) ? "(nulo)" : r[col];
      freq.set(k, (freq.get(k) || 0) + 1);
    });
    recordsTable(document.getElementById("eda-cat-detail"), [...freq.entries()].map(([valor, n]) => ({ valor, n })));
  });

  document.getElementById("btn-hist").addEventListener("click", (ev) => {
    if (!requirePreview()) return;
    const cols = selected("hist-col");
    if (!cols.length) { toast("Elige al menos una columna.", "error"); return; }
    withBusy(ev.currentTarget, async () => {
      const traces = cols.map((c) => ({
        x: state.preview.allRows.map((r) => r[c]).filter((v) => !isBlank(v)),
        type: "histogram",
        name: c,
        opacity: 0.78,
      }));
      showPlot("eda-plot", { data: traces, layout: plotLayout(cols.join(" · ")) });
    });
  });
  document.getElementById("btn-box").addEventListener("click", (ev) => {
    if (!requirePreview()) return;
    const cols = selected("box-cols");
    if (!cols.length) { toast("Elige columnas numéricas.", "error"); return; }
    withBusy(ev.currentTarget, async () => {
      const traces = cols.map((c) => ({
        y: state.preview.allRows.map((r) => r[c]).filter((v) => !isBlank(v)),
        type: "box",
        name: c,
      }));
      showPlot("eda-plot", { data: traces, layout: plotLayout("boxplots") });
    });
  });
  document.getElementById("btn-corr").addEventListener("click", (ev) => {
    if (!requirePreview()) return;
    if (hasNulls(state.preview)) {
      toast("Limpia el dataset primero y vuelve a intentar el gráfico.", "error");
      return;
    }
    withBusy(ev.currentTarget, async () => {
      const nums = numericCols(state.preview);
      const z = nums.map((a) => nums.map((b) => {
        const xs = state.preview.allRows.map((r) => [r[a], r[b]]).filter(([x, y]) => !isBlank(x) && !isBlank(y));
        const mx = mean(xs.map((p) => p[0]));
        const my = mean(xs.map((p) => p[1]));
        let num = 0; let dx = 0; let dy = 0;
        xs.forEach(([x, y]) => {
          const a0 = Number(x) - mx; const b0 = Number(y) - my;
          num += a0 * b0; dx += a0 * a0; dy += b0 * b0;
        });
        return dx && dy ? num / Math.sqrt(dx * dy) : 0;
      }));
      showPlot("eda-plot", {
        data: [{ z, x: nums, y: nums, type: "heatmap", colorscale: "RdBu", zmid: 0 }],
        layout: plotLayout("correlación"),
      });
    });
  });
  document.getElementById("btn-clear-plot").addEventListener("click", () => {
    const el = document.getElementById("eda-plot");
    if (window.Plotly) Plotly.purge(el);
    el.innerHTML = "";
    document.getElementById("btn-clear-plot").hidden = true;
    document.getElementById("btn-clear-plot").parentElement.hidden = true;
  });

  document.getElementById("impute-strategy").addEventListener("change", () => {
    document.getElementById("impute-value-wrap").hidden = document.getElementById("impute-strategy").value !== "Constante";
  });

  function runOp(op) {
    if (!requirePreview()) return;
    if (op === "impute") {
      const cols = selected("impute-cols");
      if (!cols.length) { toast("Elige columnas a imputar.", "error"); return; }
      const strategy = document.getElementById("impute-strategy").value;
      mutate((rows, dtypes) => {
        if (strategy === "Eliminar filas") {
          return rows.filter((r) => cols.every((c) => !isBlank(r[c])));
        }
        cols.forEach((c) => {
          let fill;
          if (strategy === "Media") fill = Number(mean(rows.map((r) => r[c])).toFixed(2));
          else if (strategy === "Mediana") fill = Number(median(rows.map((r) => r[c])).toFixed(2));
          else if (strategy === "Constante") fill = document.getElementById("impute-value").value;
          else fill = mode(rows.map((r) => r[c]));
          rows.forEach((r) => { if (isBlank(r[c])) r[c] = fill; });
        });
        return rows;
      }, "Nulos imputados");
    } else if (op === "drop_duplicates") {
      mutate((rows) => {
        const seen = new Set();
        return rows.filter((r) => {
          const k = JSON.stringify(r);
          if (seen.has(k)) return false;
          seen.add(k);
          return true;
        });
      }, "Duplicados eliminados");
    } else if (op === "cast") {
      const cols = selected("cast-col");
      const type = document.getElementById("cast-type").value;
      if (!cols.length) { toast("Elige columnas a convertir.", "error"); return; }
      mutate((rows, dtypes) => {
        cols.forEach((c) => { dtypes[c] = type === "numeric" ? "float64" : type; });
        rows._dtypes = dtypes;
        return rows;
      }, "Tipo convertido");
    } else if (op === "scale") {
      const cols = selected("scale-cols");
      if (!cols.length) { toast("Elige columnas numéricas.", "error"); return; }
      const method = document.getElementById("scale-method").value;
      mutate((rows) => {
        cols.forEach((c) => {
          const xs = rows.map((r) => r[c]);
          if (method === "MinMaxScaler") {
            const mn = Math.min(...xs.filter((v) => !isBlank(v)).map(Number));
            const mx = Math.max(...xs.filter((v) => !isBlank(v)).map(Number));
            const span = mx - mn || 1;
            rows.forEach((r) => { if (!isBlank(r[c])) r[c] = Number(((Number(r[c]) - mn) / span).toFixed(3)); });
          } else {
            const m = mean(xs); const sd = Math.sqrt(mean(xs.map((v) => (Number(v) - m) ** 2))) || 1;
            rows.forEach((r) => { if (!isBlank(r[c])) r[c] = Number(((Number(r[c]) - m) / sd).toFixed(3)); });
          }
        });
        return rows;
      }, "Escalado aplicado");
    } else if (op === "encode") {
      const cols = selected("encode-cols");
      if (!cols.length) { toast("Elige columnas categóricas.", "error"); return; }
      const method = document.getElementById("encode-method").value;
      mutate((rows, dtypes) => {
        if (method === "Label Encoding") {
          cols.forEach((c) => {
            const levels = [...new Set(rows.map((r) => r[c]))];
            rows.forEach((r) => { r[c] = levels.indexOf(r[c]); });
            dtypes[c] = "int64";
          });
        } else {
          cols.forEach((c) => {
            const levels = [...new Set(rows.map((r) => r[c]))];
            levels.forEach((lv) => {
              const name = `${c}_${lv}`;
              rows.forEach((r) => { r[name] = r[c] === lv ? 1 : 0; });
              dtypes[name] = "int64";
            });
            rows.forEach((r) => { delete r[c]; });
            delete dtypes[c];
          });
        }
        rows._dtypes = dtypes;
        return rows;
      }, "Codificación aplicada");
    } else if (op === "rename") {
      const old = document.getElementById("rename-old").value;
      const neu = document.getElementById("rename-new").value.trim();
      if (!old || !neu) { toast("Indica el nombre nuevo.", "error"); return; }
      mutate((rows, dtypes) => {
        rows.forEach((r) => { r[neu] = r[old]; delete r[old]; });
        dtypes[neu] = dtypes[old];
        delete dtypes[old];
        rows._dtypes = dtypes;
        return rows;
      }, "Columna renombrada");
    } else if (op === "drop_columns") {
      const cols = selected("drop-cols");
      if (!cols.length) { toast("Elige columnas a eliminar.", "error"); return; }
      mutate((rows, dtypes) => {
        cols.forEach((c) => {
          rows.forEach((r) => { delete r[c]; });
          delete dtypes[c];
        });
        rows._dtypes = dtypes;
        return rows;
      }, "Columnas eliminadas");
    }
  }

  document.querySelectorAll("[data-op]").forEach((btn) => {
    btn.addEventListener("click", () => withBusy(btn, async () => runOp(btn.dataset.op)));
  });

  document.getElementById("btn-undo").addEventListener("click", (ev) => {
    withBusy(ev.currentTarget, async () => {
      const prev = state.history.pop();
      if (!prev) { toast("Nada que deshacer", "info"); return; }
      applyPreview(prev, state.fileName);
      toast("Se deshizo la última operación");
    });
  });
  document.getElementById("btn-undo-all").addEventListener("click", (ev) => {
    withBusy(ev.currentTarget, async () => {
      if (!state.origin) { toast("Nada que deshacer", "info"); return; }
      state.history = [];
      applyPreview(clone(state.origin), state.fileName);
      toast("Se restauró el dataset original");
    });
  });
  document.getElementById("btn-export").addEventListener("click", (e) => {
    e.preventDefault();
    if (!requirePreview()) return;
    const cols = state.preview.columns;
    const lines = [cols.join(","), ...state.preview.allRows.map((r) => cols.map((c) => r[c] ?? "").join(","))];
    const blob = new Blob([lines.join("\n")], { type: "text/csv" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = state.fileName.replace(/\.\w+$/, "") + "_limpio.csv";
    a.click();
    toast("CSV exportado (simulación)");
  });

  document.getElementById("ml-task").addEventListener("change", fillAlgos);
  document.getElementById("ml-unsup-method").addEventListener("change", () => {
    const m = document.getElementById("ml-unsup-method").value;
    document.getElementById("unsup-k").hidden = m === "dbscan" || m === "pca";
    document.getElementById("unsup-eps").hidden = m !== "dbscan";
    document.getElementById("unsup-min").hidden = m !== "dbscan";
    document.getElementById("unsup-pca").hidden = m !== "pca";
  });

  document.getElementById("btn-train").addEventListener("click", (ev) => {
    if (!requirePreview()) return;
    if (hasNulls(state.preview)) { toast("Limpia el dataset primero.", "error"); return; }
    const y = document.getElementById("ml-target").value;
    const xs = selected("ml-features");
    if (!y || !xs.length) { toast("Elige objetivo y predictoras.", "error"); return; }
    withBusy(ev.currentTarget, async () => {
      const task = document.getElementById("ml-task").value;
      const algo = document.getElementById("ml-algo").value;
      const text = task === "Clasificación"
        ? `accuracy: 0.83\nmacro-F1: 0.79\nalgoritmo: ${algo}\ntest: ${document.getElementById("ml-test").value}`
        : `RMSE: 12.4\nR²: 0.71\nalgoritmo: ${algo}\ntest: ${document.getElementById("ml-test").value}`;
      document.getElementById("ml-metrics").textContent = text;
      showPlot("ml-plot", {
        data: [{ type: "bar", x: xs.slice(0, 6), y: xs.slice(0, 6).map((_, i) => 0.62 - i * 0.07) }],
        layout: plotLayout("importancia (simulación)"),
      });
      document.getElementById("btn-clear-ml-plot").hidden = false;
      document.getElementById("btn-clear-ml-plot").parentElement.hidden = false;
      toast("Modelo entrenado (simulación)");
    });
  });
  document.getElementById("btn-unsup").addEventListener("click", (ev) => {
    if (!requirePreview()) return;
    if (hasNulls(state.preview)) { toast("Limpia el dataset primero.", "error"); return; }
    const feats = selected("ml-unsup-feats");
    if (!feats.length) { toast("Elige columnas numéricas.", "error"); return; }
    withBusy(ev.currentTarget, async () => {
      const method = document.getElementById("ml-unsup-method").value;
      document.getElementById("ml-metrics").textContent = `método: ${method}\ncolumnas: ${feats.join(", ")}\ninercia / silueta: 0.61 (simulación)`;
      showPlot("ml-plot", {
        data: [{
          type: "scatter",
          mode: "markers",
          x: state.preview.allRows.map((_, i) => i),
          y: state.preview.allRows.map((r) => Number(r[feats[0]]) || 0),
          marker: { color: PLOT[tema].accent },
        }],
        layout: plotLayout(`${method} (simulación)`),
      });
      document.getElementById("btn-clear-ml-plot").hidden = false;
      document.getElementById("btn-clear-ml-plot").parentElement.hidden = false;
    });
  });
  document.getElementById("btn-clear-ml-plot").addEventListener("click", () => {
    const el = document.getElementById("ml-plot");
    if (window.Plotly) Plotly.purge(el);
    el.innerHTML = "";
    document.getElementById("btn-clear-ml-plot").hidden = true;
    document.getElementById("btn-clear-ml-plot").parentElement.hidden = true;
  });

  /* --- chat --- */
  const HINT = {
    assist: "Modo Asistente (simulado): una respuesta, bloque de código y botón Ejecutar.",
    agent: "Modo Agente (simulado): planifica, tools y panel de actividad. Prueba «audita», «grafica precio» o «limpia nulos».",
  };

  function setChatMode(mode) {
    state.chatMode = mode;
    document.querySelectorAll("[data-chat-mode]").forEach((b) => {
      const on = b.dataset.chatMode === mode;
      b.classList.toggle("is-active", on);
      b.setAttribute("aria-selected", String(on));
    });
    document.getElementById("chat-mode-hint").innerHTML = HINT[mode];
  }
  document.querySelectorAll("[data-chat-mode]").forEach((btn) => {
    btn.addEventListener("click", () => setChatMode(btn.dataset.chatMode));
  });

  const chatToggle = document.getElementById("chat-toggle");
  chatToggle.addEventListener("click", () => {
    const ws = document.querySelector(".workspace");
    const collapsed = ws.classList.toggle("is-collapsed");
    chatToggle.setAttribute("aria-expanded", String(!collapsed));
    chatToggle.textContent = collapsed ? "⟩" : "⟨";
    applyChatSize();
  });

  function clampChatWidth(px, ws) {
    const max = Math.max(280, ws.getBoundingClientRect().width - 280);
    return Math.min(Math.max(268, px), max);
  }
  function clampChatHeight(px) {
    return Math.min(Math.max(220, px), Math.round(window.innerHeight * 0.7));
  }
  function applyChatSize() {
    const ws = document.querySelector(".workspace");
    const splitter = document.getElementById("splitter");
    if (ws.classList.contains("is-collapsed")) {
      ws.style.removeProperty("--chat-w");
      ws.style.removeProperty("--chat-h");
      splitter.setAttribute("aria-orientation", isChatStacked() ? "horizontal" : "vertical");
      return;
    }
    if (isChatStacked()) {
      const stored = Number(localStorage.getItem(CHAT_H_KEY));
      const h = clampChatHeight(Number.isFinite(stored) && stored > 0 ? stored : Math.round(window.innerHeight * 0.4));
      ws.style.setProperty("--chat-h", `${h}px`);
      splitter.setAttribute("aria-orientation", "horizontal");
    } else {
      const stored = Number(localStorage.getItem(CHAT_W_KEY));
      const w = clampChatWidth(Number.isFinite(stored) && stored > 0 ? stored : 352, ws);
      ws.style.setProperty("--chat-w", `${w}px`);
      splitter.setAttribute("aria-orientation", "vertical");
    }
  }
  (function bindSplitter() {
    const splitter = document.getElementById("splitter");
    const ws = document.querySelector(".workspace");
    let dragging = false;
    splitter.addEventListener("pointerdown", (e) => {
      if (ws.classList.contains("is-collapsed")) return;
      dragging = true;
      splitter.setPointerCapture(e.pointerId);
      e.preventDefault();
    });
    splitter.addEventListener("pointermove", (e) => {
      if (!dragging) return;
      const rect = ws.getBoundingClientRect();
      if (isChatStacked()) {
        localStorage.setItem(CHAT_H_KEY, String(clampChatHeight(rect.bottom - e.clientY)));
      } else {
        localStorage.setItem(CHAT_W_KEY, String(clampChatWidth(rect.right - e.clientX, ws)));
      }
      applyChatSize();
    });
    const stop = () => { dragging = false; };
    splitter.addEventListener("pointerup", stop);
    splitter.addEventListener("pointercancel", stop);
  })();
  window.addEventListener("resize", applyChatSize);
  applyChatSize();

  function appendUser(text) {
    const log = document.getElementById("chat-log");
    const div = document.createElement("div");
    div.className = "bubble user";
    div.innerHTML = `<div class="bubble-text">${esc(text)}</div>`;
    log.appendChild(div);
    log.scrollTop = log.scrollHeight;
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

  async function typeText(el, text) {
    if (prefersReduced()) { el.textContent = text; return; }
    el.textContent = "";
    for (const ch of text) {
      el.textContent += ch;
      await sleep(8);
    }
  }

  function createAgentRun() {
    const log = document.getElementById("chat-log");
    const div = document.createElement("div");
    div.className = "bubble assistant agent-run";
    const activity = document.createElement("details");
    activity.className = "agent-activity is-running";
    activity.innerHTML = `
      <summary class="agent-activity-summary">
        <span class="agent-activity-status">
          <span class="agent-spinner" aria-hidden="true"></span>
          <span class="agent-activity-label">Planificando pasos…</span>
        </span>
        <span class="agent-activity-chevron" aria-hidden="true"></span>
      </summary>
      <div class="agent-activity-body"><ol class="agent-trail"></ol></div>
    `;
    const artifacts = document.createElement("div");
    artifacts.className = "agent-artifacts";
    const body = document.createElement("div");
    body.className = "bubble-text";
    div.append(activity, artifacts, body);
    log.appendChild(div);
    log.scrollTop = log.scrollHeight;
    return {
      div,
      activity,
      label: activity.querySelector(".agent-activity-label"),
      trail: activity.querySelector(".agent-trail"),
      artifacts,
      body,
    };
  }

  function setActivity(run, cls, label) {
    run.activity.classList.remove("is-running", "is-done", "is-error");
    run.activity.classList.add(cls);
    if (label) run.label.textContent = label;
  }

  async function addStep(run, id, label, summary) {
    setActivity(run, "is-running", "Planificando pasos…");
    await sleep(220);
    let li = run.trail.querySelector(`[data-step-id="${id}"]`);
    if (!li) {
      li = document.createElement("li");
      li.dataset.stepId = id;
      run.trail.appendChild(li);
    }
    li.className = "is-running";
    li.innerHTML = `<span class="agent-step-label">${esc(label)}…</span>${summary ? `<span class="agent-step-why">${esc(summary)}</span>` : ""}`;
    await sleep(420);
    li.className = "is-done";
    li.querySelector(".agent-step-label").textContent = label;
  }

  function addDisplay(run, columns, rows) {
    const box = document.createElement("div");
    box.className = "exec-result";
    renderTable(box, { columns, rows });
    run.artifacts.appendChild(box);
  }

  function addProposals(run, actions) {
    const wrap = document.createElement("div");
    wrap.className = "agent-proposals";
    actions.forEach((action) => {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.textContent = action.label;
      btn.addEventListener("click", () => {
        if (action.op === "impute") {
          const nums = numericCols(state.preview);
          fillPicker(document.getElementById("impute-cols"), state.preview.columns);
          nums.forEach((c) => {
            const cb = document.querySelector(`#impute-cols input[value="${CSS.escape(c)}"]`);
            if (cb) cb.checked = true;
          });
          renderChips(document.getElementById("impute-cols"));
          document.getElementById("impute-strategy").value = "Mediana";
          runOp("impute");
        } else {
          runOp(action.op);
        }
        btn.disabled = true;
      });
      wrap.appendChild(btn);
    });
    run.div.appendChild(wrap);
  }

  function scenarioFor(text) {
    const t = text.toLowerCase();
    if (/limpi|nulo|duplic/.test(t)) return "clean";
    if (/gráf|graf|histo|plot|visual/.test(t)) return "plot";
    if (/entren|modelo|ml|cluster|kmeans/.test(t)) return "ml";
    if (/audit|calidad|revisa|inspec/.test(t)) return "audit";
    return "query";
  }

  async function runAgent(prompt) {
    if (!state.preview) {
      toast("Carga un dataset para que el copiloto tenga contexto.", "error");
      return;
    }
    const run = createAgentRun();
    const kind = scenarioFor(prompt);
    await addStep(run, "t1", "Revisando el dataset", "Saco esquema y nulos para responder con evidencia.");
    addDisplay(run, ["columna", "nulos"], state.preview.columns.map((c) => ({
      columna: c, nulos: countNulls(state.preview.allRows, c),
    })));

    if (kind === "audit") {
      await addStep(run, "t2", "Buscando duplicados", "Reviso filas repetidas que inflarían el EDA.");
      await addStep(run, "t3", "Revisando outliers", "IQR en columnas numéricas.");
      addDisplay(run, ["columna", "outliers_iqr"], [{ columna: "precio", outliers_iqr: 1 }, { columna: "unidades", outliers_iqr: 0 }]);
      setActivity(run, "is-done", "Listo · pasos completados");
      run.activity.open = false;
      await typeText(run.body, `Auditoría: ${state.preview.shape[0]} filas × ${state.preview.shape[1]} columnas. Hay nulos y ${state.preview.duplicate_rows} duplicado(s). categoria sirve como objetivo de clasificación. Siguiente: imputar, quitar duplicados y luego un árbol o un K-Means.`);
      addProposals(run, [
        { op: "impute", label: "Imputar nulos (mediana en numéricas)" },
        { op: "drop_duplicates", label: "Quitar filas duplicadas" },
      ]);
    } else if (kind === "clean") {
      await addStep(run, "t2", "Proponiendo limpieza", "Armo acciones para que confirmes con Aplicar.");
      setActivity(run, "is-done", "Listo · pasos completados");
      run.activity.open = false;
      await typeText(run.body, "Propongo imputar nulos en precio y descuento con la mediana, y quitar la fila duplicada. No muté el dataset: confirma con los botones.");
      addProposals(run, [
        { op: "impute", label: "Imputar nulos (mediana)" },
        { op: "drop_duplicates", label: "Quitar duplicados" },
      ]);
    } else if (kind === "plot") {
      await addStep(run, "t2", "Graficando", "Histograma de precio; la figura sale en Visualización.");
      document.querySelector('.tab[data-tab="eda"]').click();
      showPlot("eda-plot", {
        data: [{ x: state.preview.allRows.map((r) => r.precio).filter((v) => !isBlank(v)), type: "histogram", name: "precio" }],
        layout: plotLayout("precio"),
      });
      setActivity(run, "is-done", "Listo · pasos completados");
      run.activity.open = false;
      await typeText(run.body, "Listo: dibujé el histograma de precio en Visualización (EDA). No se duplica dentro del chat.");
    } else if (kind === "ml") {
      await addStep(run, "t2", "Evaluando variables para ML", "Miro cardinalidad y posibles objetivos.");
      setActivity(run, "is-done", "Listo · pasos completados");
      run.activity.open = false;
      await typeText(run.body, hasNulls(state.preview)
        ? "Hay nulos: limpia antes de entrenar. categoria (pocos valores) sirve como Y de clasificación; evita usar fecha como feature cruda."
        : "Dataset limpio. Sugiero clasificación sobre categoria con un árbol, o K-Means sobre precio y unidades. Ábrelo en la pestaña Machine Learning.");
    } else {
      await addStep(run, "t2", "Armando tabla", "Agrupo por categoría.");
      const freq = new Map();
      state.preview.allRows.forEach((r) => freq.set(r.categoria, (freq.get(r.categoria) || 0) + 1));
      addDisplay(run, ["categoria", "n"], [...freq.entries()].map(([categoria, n]) => ({ categoria, n })));
      setActivity(run, "is-done", "Listo · pasos completados");
      run.activity.open = false;
      await typeText(run.body, "La categoría A concentra más filas. fecha sigue como texto: si quieres series, conviene castear antes. No toqué el dataset.");
    }
  }

  async function runAssist(prompt) {
    const thinking = showThinking();
    await sleep(700);
    thinking.remove();
    const log = document.getElementById("chat-log");
    const div = document.createElement("div");
    div.className = "bubble assistant";
    const body = document.createElement("div");
    body.className = "bubble-text";
    div.appendChild(body);
    const pre = document.createElement("pre");
    pre.textContent = "df = df.drop_duplicates()\nprint(df.shape)";
    const actions = document.createElement("div");
    actions.className = "code-run-actions";
    const runBtn = document.createElement("button");
    runBtn.type = "button";
    runBtn.textContent = "Ejecutar";
    runBtn.addEventListener("click", () => {
      if (!state.preview) { toast("Carga un dataset primero.", "error"); return; }
      runOp("drop_duplicates");
      const box = document.createElement("div");
      box.className = "exec-result";
      box.innerHTML = `<p class="exec-ok">Ejecutado. shape = (${state.preview.shape[0]}, ${state.preview.shape[1]})</p>`;
      div.appendChild(box);
      runBtn.disabled = true;
    });
    actions.appendChild(runBtn);
    div.append(pre, actions);
    log.appendChild(div);
    await typeText(body, `Puedo quitar duplicados con pandas. Pulsa Ejecutar para aplicarlo al dataset de la simulación.\n\nPedido: ${prompt}`);
  }

  document.getElementById("chat-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    if (state.chatBusy) return;
    const ta = document.getElementById("chat-input");
    const text = ta.value.trim();
    if (!text) return;
    ta.value = "";
    appendUser(text);
    state.chatBusy = true;
    try {
      if (state.chatMode === "assist") await runAssist(text);
      else await runAgent(text);
    } finally {
      state.chatBusy = false;
      document.getElementById("chat-log").scrollTop = 9e9;
    }
  });
  document.getElementById("chat-input").addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      document.getElementById("chat-form").requestSubmit();
    }
  });

  const DEMO_SLOTS = [
    { id: "gemini", label: "Google Gemini", model: "gemini-2.5-flash", key_mode: "builtin", has_builtin_key: true, ready: true },
    { id: "openai", label: "OpenAI", model: "gpt-4o-mini", key_mode: "user", has_builtin_key: false, ready: false },
    { id: "anthropic", label: "Anthropic", model: "claude-sonnet-4-5", key_mode: "user", has_builtin_key: false, ready: false },
  ];
  let llm = { active_id: "gemini", slots: DEMO_SLOTS.map((s) => ({ ...s })) };

  function paintChip() {
    const el = document.getElementById("chat-model");
    const slot = llm.slots.find((s) => s.id === llm.active_id);
    el.textContent = `${slot.label} · ${slot.model}`;
  }
  function renderSlots() {
    document.getElementById("llm-slots").innerHTML = llm.slots.map((slot) => `
      <article class="llm-slot" data-slot-id="${slot.id}">
        <div class="llm-slot-head">
          <label class="llm-slot-pick">
            <input type="radio" name="llm-active" value="${slot.id}" ${slot.id === llm.active_id ? "checked" : ""} />
            <span>${slot.label}</span>
          </label>
          <span class="${slot.ready ? "llm-ready" : "llm-missing"}">${slot.ready ? "listo" : "sin clave"}</span>
        </div>
        <label>Modelo <input class="llm-model" value="${esc(slot.model)}" /></label>
        <fieldset class="llm-key-mode">
          <legend>Clave</legend>
          <label><input type="radio" name="key-${slot.id}" value="builtin" ${slot.key_mode === "builtin" ? "checked" : ""} ${slot.has_builtin_key ? "" : "disabled"} /> Del servidor</label>
          <label><input type="radio" name="key-${slot.id}" value="user" ${slot.key_mode === "user" ? "checked" : ""} /> La mía</label>
        </fieldset>
        <label>API key <input class="llm-key" type="password" autocomplete="new-password" placeholder="Pega tu clave (demo)" /></label>
      </article>
    `).join("");
  }
  function setSettingsOpen(open) {
    const pop = document.getElementById("llm-settings");
    pop.hidden = !open;
    document.getElementById("chat-settings-btn").setAttribute("aria-expanded", String(open));
  }
  renderSlots();
  paintChip();
  document.getElementById("chat-settings-btn").addEventListener("click", (ev) => {
    ev.stopPropagation();
    setSettingsOpen(document.getElementById("llm-settings").hidden);
  });
  document.getElementById("chat-model").addEventListener("click", (ev) => {
    ev.stopPropagation();
    setSettingsOpen(document.getElementById("llm-settings").hidden);
  });
  document.getElementById("llm-settings-close").addEventListener("click", () => setSettingsOpen(false));
  document.getElementById("llm-settings-save").addEventListener("click", () => {
    const root = document.getElementById("llm-slots");
    const active = root.querySelector("input[name='llm-active']:checked");
    if (active) llm.active_id = active.value;
    [...root.querySelectorAll(".llm-slot")].forEach((card) => {
      const slot = llm.slots.find((s) => s.id === card.dataset.slotId);
      slot.model = card.querySelector(".llm-model")?.value || slot.model;
      slot.key_mode = card.querySelector(`input[name="key-${slot.id}"]:checked`)?.value || slot.key_mode;
      if (card.querySelector(".llm-key")?.value) slot.ready = true;
    });
    paintChip();
    renderSlots();
    setSettingsOpen(false);
    toast("Ajustes de modelo guardados (simulación)");
  });

  fillAlgos();
})();
