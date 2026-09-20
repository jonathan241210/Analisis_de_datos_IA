/**
 * Sandbox replay for Agent / Assist chat UX.
 * Canned NDJSON-like events, artificial delays, zero Gemini calls.
 */

const MIN_RUNNING_MS = 320;

const FIG_HIST = {
  data: [{
    x: ["ene", "feb", "mar", "abr", "may", "jun"],
    y: [118, 124, 131, 128, 142, 139],
    type: "bar",
    marker: { color: "#1e3a5f" },
  }],
  layout: {
    title: { text: "precio · media mensual", font: { size: 13 } },
    height: 220,
    margin: { t: 40, r: 12, b: 36, l: 36 },
    paper_bgcolor: "#fffef8",
    plot_bgcolor: "#fffef8",
    font: { family: "IBM Plex Sans, sans-serif", color: "#1b1a17" },
  },
};

const SCENARIOS = {
  audit: [
    { type: "step", id: "think-0", label: "Planificando pasos…", status: "running" },
    { delay: 720 },
    { type: "step", id: "think-0", label: "Planificando pasos…", status: "done" },
    { type: "step", id: "t1", label: "Revisando nulos…", status: "running", summary: "Cuento nulos por columna para ver qué hay que imputar." },
    { delay: 580 },
    {
      type: "display",
      display: {
        columns: ["columna", "nulos", "pct"],
        rows: [
          { columna: "precio", nulos: 3, pct: "4.2%" },
          { columna: "descuento", nulos: 11, pct: "15.3%" },
        ],
      },
    },
    { type: "step", id: "t1", label: "Revisando nulos", status: "done", summary: "Cuento nulos por columna para ver qué hay que imputar." },
    { type: "step", id: "think-0", label: "Planificando pasos…", status: "running" },
    { delay: 420 },
    { type: "step", id: "think-0", label: "Planificando pasos…", status: "done" },
    { type: "step", id: "t2", label: "Buscando duplicados…", status: "running", summary: "Reviso filas repetidas que inflarían el EDA." },
    { delay: 480 },
    { type: "step", id: "t2", label: "Buscando duplicados", status: "done", summary: "Reviso filas repetidas que inflarían el EDA." },
    { type: "step", id: "t3", label: "Revisando outliers…", status: "running", summary: "IQR en columnas numéricas para detectar extremos." },
    { delay: 540 },
    {
      type: "display",
      display: {
        columns: ["columna", "outliers_iqr"],
        rows: [
          { columna: "precio", outliers_iqr: 2 },
          { columna: "unidades", outliers_iqr: 0 },
        ],
      },
    },
    { type: "step", id: "t3", label: "Revisando outliers", status: "done", summary: "IQR en columnas numéricas para detectar extremos." },
    { type: "step", id: "t4", label: "Evaluando variables para ML…", status: "running", summary: "Miro cardinalidad y posibles objetivos de clasificación." },
    { delay: 500 },
    { type: "step", id: "t4", label: "Evaluando variables para ML", status: "done", summary: "Miro cardinalidad y posibles objetivos de clasificación." },
    { delay: 280 },
    {
      type: "final",
      content:
        "Auditoría: 72 filas × 12 columnas. Hay nulos en precio (3) y descuento (11), 4 filas duplicadas y 2 outliers IQR en precio. " +
        "categoria (5 valores) sirve como objetivo de clasificación; evita usar id. " +
        "Siguiente: imputar, quitar duplicados y luego un árbol o un K-Means sobre las numéricas.",
      proposed_actions: [
        { op: "impute", label: "Imputar nulos (mediana en numéricas)" },
        { op: "drop_duplicates", label: "Quitar filas duplicadas" },
      ],
    },
  ],

  query: [
    { type: "step", id: "think-0", label: "Planificando pasos…", status: "running" },
    { delay: 560 },
    { type: "step", id: "think-0", label: "Planificando pasos…", status: "done" },
    { type: "step", id: "t1", label: "Revisando el dataset…", status: "running", summary: "Saco esquema y una muestra para responder con evidencia." },
    { delay: 520 },
    {
      type: "display",
      display: {
        columns: ["columna", "dtype", "nunique"],
        rows: [
          { columna: "fecha", dtype: "object", nunique: 64 },
          { columna: "categoria", dtype: "object", nunique: 5 },
          { columna: "precio", dtype: "float64", nunique: 48 },
        ],
      },
    },
    { type: "step", id: "t1", label: "Revisando el dataset", status: "done", summary: "Saco esquema y una muestra para responder con evidencia." },
    { type: "step", id: "t2", label: "Armando tabla…", status: "running", summary: "Agrupo ventas por categoría para la consulta." },
    { delay: 480 },
    {
      type: "display",
      display: {
        columns: ["categoria", "n", "precio_medio"],
        rows: [
          { categoria: "A", n: 22, precio_medio: "131.20" },
          { categoria: "B", n: 18, precio_medio: "118.40" },
          { categoria: "C", n: 15, precio_medio: "142.10" },
        ],
      },
    },
    { type: "step", id: "t2", label: "Armando tabla", status: "done", summary: "Agrupo ventas por categoría para la consulta." },
    { delay: 220 },
    {
      type: "final",
      content:
        "La categoría C tiene el precio medio más alto (142.10) con 15 filas; A concentra más volumen (22). " +
        "fecha sigue como texto: si quieres series temporales, conviene castear antes. No toqué el dataset.",
    },
  ],

  plot: [
    { type: "step", id: "think-0", label: "Planificando pasos…", status: "running" },
    { delay: 500 },
    { type: "step", id: "think-0", label: "Planificando pasos…", status: "done" },
    { type: "step", id: "t1", label: "Revisando esquema…", status: "running", summary: "Confirmo que precio es numérica antes de graficar." },
    { delay: 420 },
    { type: "step", id: "t1", label: "Revisando esquema", status: "done", summary: "Confirmo que precio es numérica antes de graficar." },
    { type: "step", id: "t2", label: "Graficando…", status: "running", summary: "Histograma / barras de precio; la figura sale en Visualización." },
    { delay: 640 },
    { type: "fig", fig: FIG_HIST },
    { type: "step", id: "t2", label: "Graficando", status: "done", summary: "Histograma / barras de precio; la figura sale en Visualización." },
    { delay: 200 },
    {
      type: "final",
      content:
        "Listo: dibujé la media mensual de precio. En la app real la figura se abre en Visualización (EDA), no se duplica dentro del chat. " +
        "Aquí la dejo en el panel para que veas el momento en que llega el evento fig.",
    },
  ],

  clean: [
    { type: "step", id: "think-0", label: "Planificando pasos…", status: "running" },
    { delay: 480 },
    { type: "step", id: "think-0", label: "Planificando pasos…", status: "done" },
    { type: "step", id: "t1", label: "Revisando nulos…", status: "running", summary: "Confirmo cuántos nulos hay antes de proponer imputar." },
    { delay: 500 },
    { type: "step", id: "t1", label: "Revisando nulos", status: "done", summary: "Confirmo cuántos nulos hay antes de proponer imputar." },
    { type: "step", id: "t2", label: "Proponiendo limpieza…", status: "running", summary: "Armo acciones para que confirmes con Aplicar." },
    { delay: 420 },
    { type: "step", id: "t2", label: "Proponiendo limpieza", status: "done", summary: "Armo acciones para que confirmes con Aplicar." },
    { delay: 200 },
    {
      type: "final",
      content:
        "Puedo imputar descuento y precio con la mediana y quitar duplicados. " +
        "En modo Agente no muto df hasta que pulses Aplicar.",
      proposed_actions: [
        { op: "impute", label: "Imputar descuento y precio (mediana)" },
        { op: "drop_duplicates", label: "Quitar duplicados" },
      ],
    },
  ],

  assist: [
    { type: "thinking" },
    { delay: 1100 },
    {
      type: "assist",
      content:
        "Te dejo el código para un histograma de precio. En Asistente no corro tools: púlsalo con Ejecutar y la gráfica irá a Visualización.",
      code_blocks: [
        "fig = px.histogram(df, x=\"precio\", nbins=20, title=\"Distribución de precio\")",
      ],
    },
  ],

  happy: [
    { type: "step", id: "think-0", label: "Planificando pasos…", status: "running" },
    { delay: 480 },
    { type: "step", id: "think-0", label: "Planificando pasos…", status: "done" },
    { type: "step", id: "t1", label: "Revisando el dataset…", status: "running", summary: "12 columnas · 3 nulos en precio." },
    { delay: 520 },
    {
      type: "display",
      display: {
        columns: ["columna", "tipo", "nulos", "media"],
        rows: [
          { columna: "precio", tipo: "float64", nulos: 3, media: "128.40" },
          { columna: "categoria", tipo: "object", nulos: 0, media: "—" },
          { columna: "fecha", tipo: "object", nulos: 0, media: "—" },
        ],
      },
    },
    { type: "step", id: "t1", label: "Revisando el dataset", status: "done", summary: "12 columnas · 3 nulos en precio." },
    { delay: 220 },
    {
      type: "final",
      content:
        "Hay 3 nulos en precio y fecha está como texto. Puedo imputar con la mediana y castear fecha antes del EDA.",
      proposed_actions: [
        { op: "impute", label: "Imputar nulos en precio (mediana)" },
        { op: "cast", label: "Convertir fecha a datetime" },
      ],
    },
  ],

  "step-error": [
    { type: "step", id: "think-0", label: "Planificando pasos…", status: "running" },
    { delay: 400 },
    { type: "step", id: "think-0", label: "Planificando pasos…", status: "done" },
    { type: "step", id: "t1", label: "Revisando el dataset…", status: "running" },
    { delay: 420 },
    { type: "step", id: "t1", label: "Revisando el dataset", status: "done" },
    { type: "step", id: "t2", label: "Ejecutando análisis…", status: "running", summary: "Intento crear una columna que no existe." },
    { delay: 640 },
    { type: "step", id: "t2", label: "Ejecutando análisis", status: "error", summary: "KeyError: \"columna_x\"" },
    { delay: 200 },
    {
      type: "error",
      content: "No pude completar la transformación: la columna `columna_x` no existe en el dataset activo. Revisa el nombre exacto e intenta de nuevo.",
    },
  ],

  quota: [
    { type: "thinking" },
    { delay: 380 },
    { type: "error", content: "Se superó el límite de consultas", quota: true },
  ],

  fallback: [
    { type: "step", id: "think-0", label: "Planificando pasos…", status: "running" },
    { delay: 420 },
    {
      type: "fallback",
      from_id: "gemini",
      from_label: "Google Gemini",
      to_id: "openai",
      to_label: "OpenAI",
      to_model: "gpt-4o-mini",
    },
    { type: "step", id: "think-0", label: "Planificando pasos…", status: "done" },
    { type: "step", id: "t1", label: "Revisando el dataset…", status: "running", summary: "Sigo con OpenAI tras el cupo de Gemini." },
    { delay: 480 },
    {
      type: "display",
      display: {
        columns: ["columna", "nulos"],
        rows: [
          { columna: "precio", nulos: 3 },
          { columna: "descuento", nulos: 11 },
        ],
      },
    },
    { type: "step", id: "t1", label: "Revisando el dataset", status: "done", summary: "Sigo con OpenAI tras el cupo de Gemini." },
    { delay: 200 },
    {
      type: "final",
      content: "Gemini agotó el cupo; completé la auditoría con OpenAI. Siguen 3 nulos en precio y 11 en descuento.",
    },
  ],
};

const META = {
  audit: {
    mode: "agent",
    prompt: "Analiza el dataset, no sé por dónde empezar.",
  },
  query: {
    mode: "agent",
    prompt: "¿Qué categoría tiene el precio medio más alto?",
  },
  plot: {
    mode: "agent",
    prompt: "Hazme un gráfico de precio a lo largo del tiempo.",
  },
  clean: {
    mode: "agent",
    prompt: "Limpia nulos y duplicados, pero espera a que confirme.",
  },
  assist: {
    mode: "assist",
    prompt: "Pásame el código de un histograma de precio.",
  },
  happy: {
    mode: "agent",
    prompt: "Revisa el dataset de ventas y dime si hay algo que limpiar.",
  },
  "step-error": {
    mode: "agent",
    prompt: "Crea una columna derivada de columna_x multiplicada por 2.",
  },
  quota: {
    mode: "assist",
    prompt: "¿Puedes generar 5 gráficos distintos de este dataset?",
  },
  fallback: {
    mode: "agent",
    prompt: "Haz una auditoría completa, aunque Gemini esté al límite.",
  },
};

const chatLog = document.getElementById("chat-log");
const demoLog = document.getElementById("demo-log");
const speedInput = document.getElementById("demo-speed");
const hintEl = document.getElementById("demo-mode-hint");
let currentScenario = "audit";
let replayToken = 0;
let figSeq = 0;

function speedFactor() {
  const v = Number(speedInput.value || 1);
  return v > 0 ? v : 1;
}

function wait(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms / speedFactor()));
}

function logEvent(ev) {
  const line = document.createElement("div");
  const stamp = new Date().toLocaleTimeString("es-ES", { hour12: false });
  const slim = { ...ev };
  if (slim.fig) slim.fig = "[fig Plotly]";
  line.textContent = `${stamp}  ${JSON.stringify(slim)}`;
  demoLog.appendChild(line);
  demoLog.scrollTop = demoLog.scrollHeight;
}

function esc(v) {
  return String(v ?? "").replace(/[&<>"']/g, (c) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  }[c]));
}

function toast(msg) {
  const el = document.getElementById("toast");
  if (!el) return;
  el.hidden = false;
  el.className = "toast is-info";
  el.textContent = msg;
  clearTimeout(toast._t);
  toast._t = setTimeout(() => { el.hidden = true; }, 2800);
}

function renderTable(container, table) {
  if (!table || !table.columns || !table.columns.length) return;
  const head = table.columns.map((c) => `<th>${esc(c)}</th>`).join("");
  const body = (table.rows || []).map((row) => {
    const tds = table.columns.map((c) => `<td>${esc(row[c])}</td>`).join("");
    return `<tr>${tds}</tr>`;
  }).join("");
  container.innerHTML = `<table><thead><tr>${head}</tr></thead><tbody>${body}</tbody></table>`;
}

function setChatMode(mode) {
  document.querySelectorAll("[data-chat-mode]").forEach((btn) => {
    const on = btn.dataset.chatMode === mode;
    btn.classList.toggle("is-active", on);
    btn.setAttribute("aria-selected", on ? "true" : "false");
  });
  if (hintEl) {
    hintEl.textContent = mode === "agent"
      ? "Modo Agente (simulado): planifica, tools y panel de actividad."
      : "Modo Asistente (simulado): burbuja Pensando… y luego código + Ejecutar.";
  }
}

function createAgentRunBubble() {
  const div = document.createElement("div");
  div.className = "bubble assistant agent-run";

  const activity = document.createElement("details");
  activity.className = "agent-activity is-running";

  const summary = document.createElement("summary");
  summary.className = "agent-activity-summary";
  summary.innerHTML = `
    <span class="agent-activity-status">
      <span class="agent-spinner" aria-hidden="true"></span>
      <span class="agent-activity-label">Planificando pasos…</span>
    </span>
    <span class="agent-activity-chevron" aria-hidden="true"></span>
  `;

  const body = document.createElement("div");
  body.className = "agent-activity-body";
  const trail = document.createElement("ol");
  trail.className = "agent-trail";
  body.appendChild(trail);
  activity.appendChild(summary);
  activity.appendChild(body);

  const artifacts = document.createElement("div");
  artifacts.className = "agent-artifacts";

  const bubbleText = document.createElement("div");
  bubbleText.className = "bubble-text";
  div.appendChild(activity);
  div.appendChild(artifacts);
  div.appendChild(bubbleText);
  chatLog.appendChild(div);
  chatLog.scrollTop = chatLog.scrollHeight;

  return {
    div,
    activity,
    label: summary.querySelector(".agent-activity-label"),
    trail,
    body,
    artifacts,
    bubbleText,
    pendingSettle: new Map(),
  };
}

function paintStep(li, ev) {
  li.replaceChildren();
  const main = document.createElement("span");
  main.className = "agent-step-label";
  main.textContent = ev.label || "";
  li.appendChild(main);
  if (ev.summary && ev.summary !== ev.label) {
    const why = document.createElement("span");
    why.className = "agent-step-why";
    why.textContent = ev.summary;
    li.appendChild(why);
  }
  li.classList.remove("is-running", "is-done", "is-error");
  li.classList.add(ev.status === "error" ? "is-error" : ev.status === "done" ? "is-done" : "is-running");
}

function upsertStep(run, ev) {
  if (ev.id === "think-0") {
    if (ev.status === "running") {
      setActivityState(run, "is-running", ev.label || "Planificando pasos…");
    }
    return;
  }
  const { trail, pendingSettle } = run;
  let li = trail.querySelector(`[data-step-id="${ev.id}"]`);
  if (!li) {
    li = document.createElement("li");
    li.dataset.stepId = ev.id;
    trail.appendChild(li);
  }
  const applyState = () => paintStep(li, ev);
  if (ev.status === "running") {
    li.dataset.startedAt = String(Date.now());
    applyState();
    return;
  }
  const startedAt = Number(li.dataset.startedAt || 0);
  const elapsed = startedAt ? Date.now() - startedAt : MIN_RUNNING_MS;
  const remaining = Math.max(0, (MIN_RUNNING_MS - elapsed) / speedFactor());
  clearTimeout(pendingSettle.get(ev.id));
  pendingSettle.set(ev.id, setTimeout(applyState, remaining));
}

function setActivityState(run, state, label) {
  run.activity.classList.remove("is-running", "is-done", "is-error");
  run.activity.classList.add(state);
  if (label) run.label.textContent = label;
}

async function typeText(el, text, speedMs) {
  el.textContent = "";
  const plain = text || "";
  const step = Math.max(2, Math.ceil(plain.length / 90));
  let i = 0;
  return new Promise((resolve) => {
    const tick = () => {
      i = Math.min(plain.length, i + step);
      el.textContent = plain.slice(0, i);
      chatLog.scrollTop = chatLog.scrollHeight;
      if (i < plain.length) setTimeout(tick, speedMs);
      else resolve();
    };
    tick();
  });
}

function renderProposedActions(parent, actions) {
  if (!actions || !actions.length) return;
  const wrap = document.createElement("div");
  wrap.className = "agent-proposals";
  actions.forEach((action) => {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.textContent = action.label || `Aplicar ${action.op}`;
    btn.addEventListener("click", () => {
      btn.classList.add("is-busy");
      btn.disabled = true;
      setTimeout(() => {
        btn.classList.remove("is-busy");
        btn.classList.add("is-ok");
        btn.textContent = "Aplicado";
        toast("Cambio aplicado (simulado)");
      }, 480);
    });
    wrap.appendChild(btn);
  });
  parent.appendChild(wrap);
}

function appendCodeBlock(div, code) {
  const wrap = document.createElement("div");
  wrap.className = "code-run";
  const pre = document.createElement("pre");
  pre.className = "is-revealing";
  pre.textContent = code;
  const actions = document.createElement("div");
  actions.className = "code-run-actions";
  const runBtn = document.createElement("button");
  runBtn.type = "button";
  runBtn.textContent = "Ejecutar";
  runBtn.addEventListener("click", () => {
    runBtn.classList.add("is-busy");
    runBtn.disabled = true;
    setTimeout(() => {
      runBtn.classList.remove("is-busy");
      runBtn.classList.add("is-ok");
      toast("Gráfico en Análisis descriptivo (simulado)");
      setTimeout(() => {
        runBtn.classList.remove("is-ok");
        runBtn.disabled = false;
      }, 900);
    }, 520);
  });
  const copyBtn = document.createElement("button");
  copyBtn.type = "button";
  copyBtn.className = "ghost";
  copyBtn.textContent = "Copiar";
  copyBtn.addEventListener("click", async () => {
    try {
      await navigator.clipboard.writeText(code);
      copyBtn.textContent = "Copiado";
      setTimeout(() => { copyBtn.textContent = "Copiar"; }, 1200);
    } catch (_) { /* ignore */ }
  });
  actions.appendChild(runBtn);
  actions.appendChild(copyBtn);
  wrap.appendChild(pre);
  wrap.appendChild(actions);
  div.appendChild(wrap);
}

function showFig(run, fig) {
  const note = document.createElement("p");
  note.className = "exec-fig-note";
  note.textContent = "Gráfico mostrado en Análisis descriptivo.";
  const slot = document.createElement("div");
  slot.className = "exec-result demo-fig";
  const plot = document.createElement("div");
  figSeq += 1;
  plot.id = `demo-plot-${figSeq}`;
  plot.className = "demo-plot";
  slot.appendChild(note);
  slot.appendChild(plot);
  run.body.appendChild(slot);
  run.activity.open = true;
  toast("Gráfico en Análisis descriptivo");
  if (window.Plotly && fig) {
    window.Plotly.newPlot(plot, fig.data, fig.layout, { displayModeBar: false, responsive: true });
  }
}

function appendUserBubble(text) {
  const div = document.createElement("div");
  div.className = "bubble user";
  const body = document.createElement("div");
  body.className = "bubble-text";
  body.textContent = text;
  div.appendChild(body);
  chatLog.appendChild(div);
  chatLog.scrollTop = chatLog.scrollHeight;
}

function showThinking() {
  const div = document.createElement("div");
  div.className = "bubble assistant is-thinking";
  div.innerHTML = `<span class="thinking-label">Pensando</span><span class="dots" aria-hidden="true"><span>.</span><span>.</span><span>.</span></span>`;
  chatLog.appendChild(div);
  chatLog.scrollTop = chatLog.scrollHeight;
  return div;
}

function appendErrorBubble(text) {
  const div = document.createElement("div");
  div.className = "bubble assistant is-error";
  const body = document.createElement("div");
  body.className = "bubble-text";
  body.textContent = text;
  div.appendChild(body);
  chatLog.appendChild(div);
  chatLog.scrollTop = chatLog.scrollHeight;
  return div;
}

async function runScenario(name) {
  const myToken = ++replayToken;
  const events = SCENARIOS[name] || [];
  const meta = META[name] || { mode: "agent", prompt: "Consulta de ejemplo" };
  demoLog.textContent = "";
  chatLog.innerHTML = "";
  setChatMode(meta.mode);

  appendUserBubble(meta.prompt);
  await wait(260);
  if (myToken !== replayToken) return;

  let run = null;
  let thinking = null;

  for (const raw of events) {
    if (myToken !== replayToken) return;

    if (raw.delay) {
      await wait(raw.delay);
      continue;
    }

    logEvent(raw);

    if (raw.type === "thinking") {
      thinking = showThinking();
    } else if (raw.type === "assist") {
      if (thinking) thinking.remove();
      thinking = null;
      const div = document.createElement("div");
      div.className = "bubble assistant";
      const body = document.createElement("div");
      body.className = "bubble-text";
      div.appendChild(body);
      chatLog.appendChild(div);
      await typeText(body, raw.content || "", 14 / speedFactor());
      (raw.code_blocks || []).forEach((code) => appendCodeBlock(div, code));
    } else if (raw.type === "step") {
      if (!run) run = createAgentRunBubble();
      upsertStep(run, raw);
    } else if (raw.type === "display") {
      if (!run) run = createAgentRunBubble();
      const box = document.createElement("div");
      box.className = "exec-result";
      renderTable(box, raw.display);
      (run.artifacts || run.body).appendChild(box);
    } else if (raw.type === "fallback") {
      applyDemoFallback(raw);
    } else if (raw.type === "fig") {
      if (!run) run = createAgentRunBubble();
      showFig(run, raw.fig);
    } else if (raw.type === "final") {
      if (!run) run = createAgentRunBubble();
      setActivityState(run, "is-done", "Listo · pasos completados");
      run.activity.open = false;
      await wait(160);
      await typeText(run.bubbleText, raw.content, 14 / speedFactor());
      renderProposedActions(run.div, raw.proposed_actions);
    } else if (raw.type === "error") {
      if (thinking) {
        thinking.remove();
        thinking = null;
      }
      if (run) {
        setActivityState(run, "is-error", "Se detuvo con un error");
        run.activity.open = true;
        await wait(160);
        await typeText(run.bubbleText, raw.content, 14 / speedFactor());
        run.div.classList.add("is-error");
      } else {
        appendErrorBubble(raw.content);
      }
    }
  }
}

function setActiveScenarioButton(name) {
  document.querySelectorAll(".demo-scenario-btn").forEach((btn) => {
    btn.classList.toggle("is-active", btn.dataset.scenario === name);
  });
}

document.querySelectorAll(".demo-scenario-btn").forEach((btn) => {
  btn.addEventListener("click", () => {
    currentScenario = btn.dataset.scenario;
    setActiveScenarioButton(currentScenario);
    runScenario(currentScenario);
  });
});

document.getElementById("demo-replay").addEventListener("click", () => runScenario(currentScenario));
document.getElementById("demo-run-current").addEventListener("click", (e) => {
  e.preventDefault();
  runScenario(currentScenario);
});
document.getElementById("demo-clear").addEventListener("click", () => {
  replayToken += 1;
  chatLog.innerHTML = "";
  demoLog.textContent = "";
});

document.querySelectorAll("[data-chat-mode]").forEach((btn) => {
  btn.addEventListener("click", () => {
    const mode = btn.dataset.chatMode;
    setChatMode(mode);
    const match = Object.keys(META).find((key) => META[key].mode === mode);
    if (match && META[currentScenario].mode !== mode) {
      currentScenario = match;
      setActiveScenarioButton(currentScenario);
      runScenario(currentScenario);
    }
  });
});

const chatToggle = document.getElementById("chat-toggle");
if (chatToggle) {
  chatToggle.addEventListener("click", () => {
    const expanded = chatToggle.getAttribute("aria-expanded") !== "false";
    chatToggle.setAttribute("aria-expanded", String(!expanded));
    chatToggle.textContent = expanded ? "⟩" : "⟨";
    document.getElementById("chat-aside").classList.toggle("is-collapsed", expanded);
  });
}

runScenario(currentScenario);

const DEMO_SLOTS = [
  { id: "gemini", label: "Google Gemini", model: "gemini-2.5-flash", key_mode: "builtin", has_builtin_key: true, has_user_key: false, ready: true },
  { id: "openai", label: "OpenAI", model: "gpt-4o-mini", key_mode: "user", has_builtin_key: false, has_user_key: false, ready: false },
  { id: "anthropic", label: "Anthropic", model: "claude-sonnet-4-5", key_mode: "user", has_builtin_key: false, has_user_key: false, ready: false },
];
let demoLlm = { active_id: "gemini", slots: DEMO_SLOTS.map((s) => ({ ...s })) };

function paintDemoChip() {
  const el = document.getElementById("chat-model");
  if (!el) return;
  const slot = demoLlm.slots.find((s) => s.id === demoLlm.active_id) || demoLlm.slots[0];
  el.textContent = `${slot.label} · ${slot.model}`;
}

function renderDemoSlots() {
  const root = document.getElementById("llm-slots");
  if (!root) return;
  root.innerHTML = demoLlm.slots.map((slot) => `
    <article class="llm-slot" data-slot-id="${slot.id}">
      <div class="llm-slot-head">
        <label class="llm-slot-pick">
          <input type="radio" name="llm-active" value="${slot.id}" ${slot.id === demoLlm.active_id ? "checked" : ""} />
          <span>${slot.label}</span>
        </label>
        <span class="${slot.ready ? "llm-ready" : "llm-missing"}">${slot.ready ? "listo" : "sin clave"}</span>
      </div>
      <label>Modelo
        <input class="llm-model" value="${esc(slot.model)}" />
      </label>
      <fieldset class="llm-key-mode">
        <legend>Clave</legend>
        <label><input type="radio" name="key-${slot.id}" value="builtin" ${slot.key_mode === "builtin" ? "checked" : ""} ${slot.has_builtin_key ? "" : "disabled"} /> Del servidor</label>
        <label><input type="radio" name="key-${slot.id}" value="user" ${slot.key_mode === "user" ? "checked" : ""} /> La mía</label>
      </fieldset>
      <label>API key
        <input class="llm-key" type="password" autocomplete="new-password" placeholder="${slot.has_user_key ? "•••• guardada" : "Pega tu clave (demo local)"}" />
      </label>
    </article>
  `).join("");
}

function applyDemoFallback(ev) {
  demoLlm.active_id = ev.to_id || "openai";
  const slot = demoLlm.slots.find((s) => s.id === demoLlm.active_id);
  if (slot) {
    slot.ready = true;
    if (ev.to_model) slot.model = ev.to_model;
  }
  paintDemoChip();
  toast(`Se superó el cupo de ${ev.from_label}. Pasé a ${ev.to_label}.`);
}

function setDemoSettingsOpen(open) {
  const pop = document.getElementById("llm-settings");
  const btn = document.getElementById("chat-settings-btn");
  if (!pop) return;
  pop.hidden = !open;
  if (btn) btn.setAttribute("aria-expanded", open ? "true" : "false");
}

(function bindDemoSettings() {
  const openBtn = document.getElementById("chat-settings-btn");
  const chip = document.getElementById("chat-model");
  const closeBtn = document.getElementById("llm-settings-close");
  const saveBtn = document.getElementById("llm-settings-save");
  const pop = document.getElementById("llm-settings");
  if (!openBtn || !pop) return;
  renderDemoSlots();
  paintDemoChip();
  const toggle = () => {
    const willOpen = pop.hidden;
    if (willOpen) renderDemoSlots();
    setDemoSettingsOpen(willOpen);
  };
  openBtn.addEventListener("click", (ev) => { ev.stopPropagation(); toggle(); });
  chip?.addEventListener("click", (ev) => { ev.stopPropagation(); toggle(); });
  closeBtn?.addEventListener("click", () => setDemoSettingsOpen(false));
  saveBtn?.addEventListener("click", () => {
    const root = document.getElementById("llm-slots");
    const active = root.querySelector("input[name='llm-active']:checked");
    if (active) demoLlm.active_id = active.value;
    [...root.querySelectorAll(".llm-slot")].forEach((card) => {
      const slot = demoLlm.slots.find((s) => s.id === card.dataset.slotId);
      if (!slot) return;
      slot.model = card.querySelector(".llm-model")?.value || slot.model;
      slot.key_mode = card.querySelector(`input[name="key-${slot.id}"]:checked`)?.value || slot.key_mode;
      const typed = card.querySelector(".llm-key")?.value || "";
      if (typed) {
        slot.has_user_key = true;
        slot.ready = true;
      }
    });
    paintDemoChip();
    renderDemoSlots();
    setDemoSettingsOpen(false);
    toast("Ajustes de modelo guardados (demo)");
  });
})();
