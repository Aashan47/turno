"use strict";
const $ = (s) => document.querySelector(s);
const WORK_W = { moderate: [234, 349], heavy: [350, 465], very_heavy: [466, 580] };
let INDEX = null, DOC = null, PLAN = null, READER = null;

function limitAt(workload, accl) {
  const m = WORK_W[workload][1];
  return accl === "accl" ? 56.7 - 11.5 * Math.log10(m) : 59.9 - 14.1 * Math.log10(m);
}
function settings() {
  return { site: $("#site").value, day: $("#day").value, workload: $("#workload").value,
           accl: $("#accl").value, alto: document.querySelector("input[name=alto]:checked").value };
}
const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

async function init() {
  INDEX = await (await fetch("/data/index.json")).json();
  try {
    const r = await fetch("/evidence/ordinance_reader.json");
    const d = r.ok ? await r.json() : null;
    READER = Array.isArray(d) ? d : null;
  } catch (e) { READER = null; }
  $("#site").innerHTML = INDEX.sites.map((s) => `<option value="${s.key}">${esc(s.name)} (${esc(s.region)})</option>`).join("");
  $("#site").value = "roma";
  fillDays();
  $("#day").value = INDEX.sites.find((s) => s.key === "roma").days.includes("2026-07-30") ? "2026-07-30" : $("#day").value;
  ["#site", "#day", "#workload", "#accl"].forEach((id) => $(id).addEventListener("change", (e) => { if (id === "#site") fillDays(); load(); }));
  document.querySelectorAll("input[name=alto]").forEach((r) => r.addEventListener("change", render));
  $("#show-truth").addEventListener("change", () => document.body.classList.toggle("hide-truth", !$("#show-truth").checked));
  $("#btn-brief").addEventListener("click", briefing);
  $("#btn-csv").addEventListener("click", csv);
  window.addEventListener("hashchange", route); route();
  load();
}
function fillDays() {
  const s = INDEX.sites.find((x) => x.key === $("#site").value);
  $("#day").innerHTML = s.days.map((d) => `<option>${d}</option>`).join("");
  $("#day").value = s.days[s.days.length - 1];
}
async function load() {
  const { site, day } = settings();
  DOC = await (await fetch(`/data/${site}/${day}.json`)).json();
  render();
}

function render() {
  const st = settings();
  PLAN = DOC.plans[`${st.workload}|${st.accl}|${st.alto}`];
  $("#brief").textContent = ""; $("#brief-tag").textContent = "Gemma 4";
  $("#context").innerHTML = `${esc(DOC.name)}, ${esc(DOC.region)}, ${esc(DOC.work)} site. Replay of <b>${DOC.date}</b>, planned the day before from the ECMWF ensemble run of ${esc(DOC.forecast_init)}. Grid cell ${DOC.cell.lat}, ${DOC.cell.lon}.`;
  const sm = PLAN.summary;
  $("#s-work").textContent = `${(sm.work_minutes / 60).toFixed(1)} h`;
  $("#s-work-of").textContent = `of ${sm.of_minutes / 60} working hours (07:00 to 19:00)`;
  $("#s-ban").textContent = sm.banned_hours;
  $("#s-hand").textContent = sm.handed_over;
  let over = 0;
  const truthMin = DOC.truth_minutes[st.workload][st.accl];
  const rows = PLAN.hours.map((h) => {
    const hh = String(parseInt(h.hour));
    const tw = DOC.truth_wbgt_by_hour[hh], tm = truthMin[hh];
    const isOver = tm !== undefined && h.work_minutes > tm;
    if (isOver) over++;
    let pill;
    if (h.outcome === "banned") pill = `<span class="pill p-ban">Banned</span>`;
    else if (h.outcome === "undetermined") pill = `<span class="pill p-hand">Supervisor decides</span>`;
    else if (h.work_minutes === 60) pill = `<span class="pill p-work">Full work</span>`;
    else if (h.work_minutes === 0) pill = `<span class="pill p-stop">Stop</span>`;
    else pill = `<span class="pill p-part">${h.work_minutes} min / hour</span>`;
    const why = h.reasons.map(esc).join(" ");
    const btn = h.needs_supervisor ? `<br><button class="mini" data-h="${h.hour}">Explain (runs on AMD)</button><div class="exp" id="exp-${hh}"></div>` : "";
    return `<tr><td class="num">${h.hour}</td><td>${pill}</td><td class="num">${h.work_minutes}</td>
      <td class="num">${h.wbgt_c.min} to ${h.wbgt_c.max}</td>
      <td class="num t">${tw !== undefined ? tw.toFixed(1) : "-"}</td>
      <td class="num t ${isOver ? "over" : ""}">${tm !== undefined ? tm : "-"}${isOver ? " (plan too high)" : ""}</td>
      <td class="why">${why}${btn}</td></tr>`;
  });
  $("#hours tbody").innerHTML = rows.join("");
  $("#s-over").textContent = over;
  document.querySelectorAll("button.mini").forEach((b) => b.addEventListener("click", () => explain(b.dataset.h)));
  chart(st);
  ordinance();
  logTable();
}

function chart(st) {
  const svg = $("#chart"), W = 860, H = 260, L = 40, R = 10, T = 12, B = 28;
  const hours = Object.keys(DOC.members_by_hour).map(Number).sort((a, b) => a - b);
  const all = [];
  hours.forEach((h) => all.push(...DOC.members_by_hour[h], DOC.truth_wbgt_by_hour[h] ?? NaN));
  const lim = limitAt(st.workload, st.accl);
  all.push(lim);
  const lo = Math.floor(Math.min(...all.filter(isFinite)) - 1), hi = Math.ceil(Math.max(...all.filter(isFinite)) + 1);
  const x = (h) => L + ((h - hours[0]) / (hours[hours.length - 1] - hours[0])) * (W - L - R);
  const y = (v) => T + (1 - (v - lo) / (hi - lo)) * (H - T - B);
  let s = "";
  const ord = DOC.ordinances.find((o) => o.status === "VERIFIED_PRIMARY");
  if (ord && st.alto !== "not_alto") {
    const [a, b] = ord.ban.split("-").map((t) => { const [h, m] = t.split(":").map(Number); return h + m / 60; });
    s += `<rect x="${x(a)}" y="${T}" width="${x(b) - x(a)}" height="${H - T - B}" fill="var(--ban-bg)"/>`;
  }
  for (let v = lo; v <= hi; v += 2) s += `<line x1="${L}" x2="${W - R}" y1="${y(v)}" y2="${y(v)}" stroke="var(--line)"/><text x="${L - 6}" y="${y(v) + 4}" font-size="10" text-anchor="end" fill="var(--muted)">${v}</text>`;
  hours.forEach((h) => (s += `<text x="${x(h)}" y="${H - 8}" font-size="10" text-anchor="middle" fill="var(--muted)">${String(h).padStart(2, "0")}</text>`));
  s += `<line x1="${L}" x2="${W - R}" y1="${y(lim)}" y2="${y(lim)}" stroke="var(--stop)" stroke-dasharray="5 4"/><text x="${W - R}" y="${y(lim) - 4}" font-size="10" text-anchor="end" fill="var(--stop)">limit for a full hour of this work</text>`;
  const n = DOC.members_by_hour[hours[0]].length;
  for (let m = 0; m < n; m++) s += `<polyline fill="none" stroke="#f08c00" stroke-opacity=".45" stroke-width="1.2" points="${hours.map((h) => `${x(h)},${y(DOC.members_by_hour[h][m])}`).join(" ")}"/>`;
  const th = hours.filter((h) => DOC.truth_wbgt_by_hour[h] !== undefined);
  s += `<polyline fill="none" stroke="var(--ink)" stroke-width="2.4" points="${th.map((h) => `${x(h)},${y(DOC.truth_wbgt_by_hour[h])}`).join(" ")}"/>`;
  svg.innerHTML = s;
}

function ordinance() {
  const o = DOC.ordinances.find((x) => x.status === "VERIFIED_PRIMARY") || DOC.ordinances[0];
  if (!o) { $("#ord").innerHTML = `<p class="hint">No ordinance on record for this region.</p>`; return; }
  const win = o.windows.map((w) => `${w[0]} to ${w[1]}`).join(", ");
  let reader = "";
  const r = Array.isArray(READER) ? READER.find((x) => x.region === DOC.region) : null;
  if (r) {
    const f = r.fields, ok = Object.keys(f).filter((k) => f[k].accepted), rev = Object.keys(f).filter((k) => !f[k].accepted);
    reader = `<p class="check">Re-read from the source by ${esc(r.model)} on AMD (${esc(r.source)}): <span class="ok">${ok.length} fields verified against the text</span>${rev.length ? `, <span class="bad">${rev.length} sent to a person (${rev.join(", ")})</span>` : ""}.</p>`;
  }
  $("#ord").innerHTML = `<p><b>${esc(DOC.region)}, ordinance ${esc(o.number)}</b><br>No work ${esc(o.ban)} on ALTO days, in force ${esc(win)}. <a href="${esc(o.url)}" target="_blank" rel="noopener">source</a></p>
    <blockquote>${esc(o.trigger).slice(0, 360)}</blockquote>${reader}`;
}

function logTable() {
  const st = settings();
  $("#log tbody").innerHTML = PLAN.hours.map((h) => `<tr><td class="num">${h.hour}</td><td>${h.outcome}</td><td class="num">${h.work_minutes}</td><td class="why">${esc(h.reasons.join(" ") || "Within the NIOSH limit for this work.")}</td></tr>`).join("");
}
function csv() {
  const st = settings();
  const head = [`# Turno compliance log`, `# Site: ${DOC.name} (${DOC.region}); day ${DOC.date}; forecast ${DOC.forecast_init}`,
    `# Work: ${st.workload}; crew: ${st.accl}; Worklimate rating confirmed by supervisor: ${st.alto}`, "hour,decision,work_minutes,wbgt_min_c,wbgt_max_c,basis"];
  const rows = PLAN.hours.map((h) => [h.hour, h.outcome, h.work_minutes, h.wbgt_c.min, h.wbgt_c.max, `"${(h.reasons.join(" ") || "Within the NIOSH limit").replace(/"/g, "'")}"`].join(","));
  const blob = new Blob([head.concat(rows).join("\n")], { type: "text/csv" });
  const a = document.createElement("a"); a.href = URL.createObjectURL(blob); a.download = `turno-${DOC.site}-${DOC.date}.csv`; a.click();
}

async function briefing() {
  const st = settings();
  $("#brief").textContent = "Writing...";
  const o = DOC.ordinances.find((x) => x.status === "VERIFIED_PRIMARY");
  const plan = { site: DOC.name, date: DOC.date, crew: `${st.workload} work, ${st.accl === "accl" ? "acclimatized" : "not acclimatized"}`,
                 ban_window: o && st.alto === "alto" ? o.ban.split("-") : [], hours: PLAN.hours };
  const r = await (await fetch("/api/briefing", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ plan }) })).json();
  $("#brief").textContent = r.text;
  $("#brief-tag").textContent = r.by_model ? `${r.model} (${r.backend}), checked` : "template (model text failed the check)";
  if (!r.by_model && r.problems && r.problems.length) $("#brief").textContent += `\n\n[Model text rejected: ${r.problems.slice(0, 3).join("; ")}]`;
}
async function explain(hour) {
  const h = PLAN.hours.find((x) => x.hour === hour), hh = String(parseInt(hour));
  $(`#exp-${hh}`).innerHTML = `<span class="hint">Asking a model on AMD...</span>`;
  const r = await (await fetch("/api/explain", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ hour: h, site: DOC.name, date: DOC.date }) })).json();
  $(`#exp-${hh}`).innerHTML = r.text
    ? `<pre class="out">${esc(r.text)}</pre><div class="check ok">${esc(r.model)} on ${esc(r.runs_on)}, ${r.latency_s} s, numbers checked</div>`
    : `<div class="check bad">Model text failed the number check; showing the plan's reasons.</div>`;
}

async function route() {
  const id = (location.hash || "#plan").slice(1);
  ["plan", "how", "evidence"].forEach((s) => $(`#${s}`).classList.toggle("hidden", s !== id));
  document.querySelectorAll("nav a").forEach((a) => a.classList.toggle("on", a.getAttribute("href") === `#${id}`));
  if (id === "evidence") evidence();
}
function md(text) {
  const out = []; let table = null;
  for (const line of text.split("\n")) {
    if (line.startsWith("|")) {
      const cells = line.split("|").slice(1, -1).map((c) => c.trim());
      if (cells.every((c) => /^-+$/.test(c))) continue;
      if (!table) { table = []; out.push(table); }
      table.push(cells); continue;
    }
    table = null;
    if (line.startsWith("# ")) out.push(`<h2>${esc(line.slice(2))}</h2>`);
    else if (line.startsWith("## ")) out.push(`<h3>${esc(line.slice(3))}</h3>`);
    else if (line.trim()) out.push(`<p>${esc(line).replace(/\*\*(.+?)\*\*/g, "<b>$1</b>").replace(/`(.+?)`/g, "<code>$1</code>")}</p>`);
  }
  return out.map((b) => Array.isArray(b)
    ? `<div class="table-wrap"><table><thead><tr>${b[0].map((c) => `<th>${esc(c).replace(/\*\*(.+?)\*\*/g, "<b>$1</b>")}</th>`).join("")}</tr></thead><tbody>${b.slice(1).map((r) => `<tr>${r.map((c) => `<td>${esc(c).replace(/\*\*(.+?)\*\*/g, "<b>$1</b>")}</td>`).join("")}</tr>`).join("")}</tbody></table></div>`
    : b).join("");
}
async function evidence() {
  const parts = [];
  for (const f of ["grid_summary.md", "ordinance_reader.md", "rule_sweep_june.md", "solar-validation.md"]) {
    try { const r = await fetch(`/evidence/${f}`); if (r.ok) parts.push(`<div class="card">${md(await r.text())}</div>`); } catch (e) {}
  }
  try {
    const lines = (await (await fetch("/evidence/amd_calls.jsonl")).text()).trim().split("\n").map((l) => JSON.parse(l));
    const lat = lines.map((l) => l.latency_s).sort((a, b) => a - b), cost = lines.reduce((a, l) => a + l.cost_usd, 0);
    parts.unshift(`<div class="card"><h2>Model calls on AMD (Token Factory)</h2><p>${lines.length} calls logged; median latency ${lat[Math.floor(lat.length / 2)]} s; total cost $${cost.toFixed(4)}. Every call's model, latency, tokens and cost is in <code>results/amd_calls.jsonl</code>.</p></div>`);
  } catch (e) {}
  $("#evidence-body").innerHTML = `<h2>Evidence</h2><p>Every number below was produced by a script in the repository and can be rerun. The comparison dates and predictions were pre-registered before the July and August test set was scored (<code>results/PREREGISTRATION.md</code>).</p>` + parts.join("");
}
init();
