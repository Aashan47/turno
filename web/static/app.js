"use strict";
const $ = (s) => document.querySelector(s);
const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
const WORK_W = { moderate: [234, 349], heavy: [350, 465], very_heavy: [466, 580] };
const WORK_NAME = { moderate: "moderate work", heavy: "heavy work", very_heavy: "very heavy work" };
let INDEX = null, DOC = null, PLAN = null, READER = null, SOURCES = {}, SELECTED = null, FIRST_PAINT = true;

function settings() {
  return { site: $("#site").value, day: $("#day").value, workload: $("#workload").value,
           accl: $("#accl").value, alto: document.querySelector("input[name=alto]:checked").value };
}
function limitC(workload, accl) {
  const m = WORK_W[workload][1];
  return accl === "accl" ? 56.7 - 11.5 * Math.log10(m) : 59.9 - 14.1 * Math.log10(m);
}
function heatColor(w) {
  // Five stops of the heat scale, interpolated in sRGB. Stops are WBGT in C.
  const stops = [[20, [127, 166, 188]], [24, [228, 185, 74]], [27, [238, 106, 44]], [30, [185, 35, 28]], [33, [90, 14, 18]]];
  if (w <= stops[0][0]) return `rgb(${stops[0][1]})`;
  for (let i = 1; i < stops.length; i++) {
    if (w <= stops[i][0]) {
      const t = (w - stops[i - 1][0]) / (stops[i][0] - stops[i - 1][0]);
      const c = stops[i - 1][1].map((a, k) => Math.round(a + (stops[i][1][k] - a) * t));
      return `rgb(${c})`;
    }
  }
  return `rgb(${stops[stops.length - 1][1]})`;
}
const dayName = (iso) => new Date(iso + "T12:00:00").toLocaleDateString("en-GB", { weekday: "long", day: "numeric", month: "long" });

async function init() {
  INDEX = await (await fetch("/data/index.json")).json();
  try { const r = await fetch("/evidence/ordinance_reader.json"); const d = r.ok ? await r.json() : null; READER = Array.isArray(d) ? d : null; } catch (e) { READER = null; }
  try { const r = await fetch("/data/ordinance_sources.json"); SOURCES = r.ok ? await r.json() : {}; } catch (e) { SOURCES = {}; }
  $("#site").innerHTML = INDEX.sites.map((s) => `<option value="${s.key}">${esc(s.name)}, ${esc(s.region)}</option>`).join("");
  $("#site").value = "roma";
  fillDays();
  if (INDEX.sites.find((s) => s.key === "roma").days.includes("2026-07-30")) $("#day").value = "2026-07-30";
  ["#site", "#day", "#workload", "#accl"].forEach((id) => $(id).addEventListener("change", () => { if (id === "#site") fillDays(); load(); }));
  document.querySelectorAll("input[name=alto]").forEach((r) => r.addEventListener("change", render));
  $("#btn-brief").addEventListener("click", briefing);
  $("#btn-csv").addEventListener("click", csv);
  evidence();
  load();
}
function fillDays() {
  const s = INDEX.sites.find((x) => x.key === $("#site").value);
  $("#day").innerHTML = `<option value="live">Tomorrow, live forecast</option>` + s.days.map((d) => `<option value="${d}">${dayName(d)}</option>`).join("");
  $("#day").value = s.days[s.days.length - 1];
}
async function load() {
  const { site, day } = settings();
  SELECTED = null;
  if (day === "live") {
    $("#where").textContent = "Fetching the latest ECMWF ensemble run.";
    const r = await fetch(`/api/live/${site}`);
    if (!r.ok) { $("#where").textContent = "The live forecast is unavailable right now. Pick a replay day."; return; }
    DOC = await r.json();
  } else {
    DOC = await (await fetch(`/data/${site}/${day}.json`)).json();
  }
  document.body.classList.toggle("is-live", !!DOC.live);
  render();
}

function render() {
  const st = settings();
  PLAN = DOC.plans[`${st.workload}|${st.accl}|${st.alto}`];
  const truthMin = (DOC.truth_minutes[st.workload] || {})[st.accl] || {};
  const sm = PLAN.summary;
  const hrs = PLAN.hours.length;
  const workH = sm.work_minutes / 60;

  $("#where").textContent = DOC.live
    ? `${DOC.name}, ${DOC.region}. Tomorrow, ${dayName(DOC.date)}, ${WORK_NAME[st.workload]}, crew ${st.accl === "accl" ? "acclimatized" : "new to the heat"}. Live, from the ${DOC.forecast_init}.`
    : `${DOC.name}, ${DOC.region}. ${dayName(DOC.date)} 2026, ${WORK_NAME[st.workload]}, crew ${st.accl === "accl" ? "acclimatized" : "new to the heat"}. Planned the day before.`;

  const parts = [`<span class="n">${workH % 1 ? workH.toFixed(1) : workH} ${workH === 1 ? "hour" : "hours"}</span> of safe work in a ${hrs}-hour day.`];
  if (sm.banned_hours) parts.push(`<span class="ban"><span class="n">${sm.banned_hours} hours</span> banned by law.</span>`);
  if (sm.handed_over) parts.push(`<span class="hand"><span class="n">${sm.handed_over} ${sm.handed_over === 1 ? "hour is" : "hours are"}</span> yours to decide.</span>`);
  if (!sm.banned_hours && !sm.handed_over) parts.push("No bans, no hand-offs.");
  $("#verdict").innerHTML = parts.join(" ");

  let over = 0, restricted = 0, kept = 0;
  PLAN.hours.forEach((h) => { const t = truthMin[String(parseInt(h.hour))]; if (t === undefined) return; if (t < 60) { restricted++; if (h.work_minutes <= t) kept++; else over++; } });
  if (DOC.live) $("#checked").innerHTML = `This day has not happened yet. On the ten tested summer days, the same forecast and rules kept the plan within the limit in 99% of heat-restricted hours one day ahead.`;
  else if (over === 0) $("#checked").innerHTML = `Checked against what actually happened: <span class="good">no hour allowed too much work</span>. ${restricted} hours were heat-restricted in reality; the plan held all of them.`;
  else $("#checked").innerHTML = `Checked against what actually happened: the plan <span class="bad">allowed too much work in ${over} ${over === 1 ? "hour" : "hours"}</span> of ${restricted} that were heat-restricted. They are marked on the strip; nothing is hidden.`;

  strip(st, truthMin);
  facts(st, truthMin, restricted, kept, over);
  law();
  amd();
  logTable();
  $("#brief").textContent = ""; $("#brief-tag").textContent = "";
  if (SELECTED) showDetail(SELECTED); else $("#detail").hidden = true;
}

function strip(st, truthMin) {
  const svg = $("#strip");
  const W = 1300, H = 420, L = 54, R = 16, TOP = 16, BAND = 120, GAP = 26, BASE = H - 54, BARS = BASE - (TOP + BAND + GAP);
  const hours = PLAN.hours.map((h) => parseInt(h.hour));
  const n = hours.length, colW = (W - L - R) / n, bw = colW * 0.72;
  const x = (i) => L + i * colW, cx = (i) => x(i) + colW / 2;
  const members = hours.map((h) => DOC.members_by_hour[String(h)] || []);
  const all = members.flat().concat(hours.map((h) => DOC.truth_wbgt_by_hour[String(h)]).filter((v) => v !== undefined));
  const lim = limitC(st.workload, st.accl);
  const lo = Math.floor(Math.min(...all, lim) - 1), hi = Math.ceil(Math.max(...all, lim) + 1);
  const yb = (v) => TOP + BAND - ((v - lo) / (hi - lo)) * BAND;
  const ym = (m) => BASE - (m / 60) * BARS;
  let s = `<defs><pattern id="hatch" width="7" height="7" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><rect width="7" height="7" fill="var(--paper)"/><rect width="2.6" height="7" fill="var(--ink)"/></pattern></defs>`;

  // Ban window, behind everything, across both bands.
  const ord = DOC.ordinances.find((o) => o.status === "VERIFIED_PRIMARY");
  if (ord && st.alto !== "not_alto") {
    const [a, b] = ord.ban.split("-").map((t) => { const [hh, mm] = t.split(":").map(Number); return hh + mm / 60; });
    const xa = L + (a - hours[0]) * colW, xb = L + (b - hours[0]) * colW;
    s += `<rect x="${xa}" y="${TOP - 6}" width="${xb - xa}" height="${BASE - TOP + 6}" fill="var(--soft)" rx="4"/>`;
    s += `<text x="${(xa + xb) / 2}" y="${BASE + 38}" text-anchor="middle" font-size="12" font-weight="700" fill="var(--ink)">${esc(ord.ban.replace("-", " to "))} ${st.alto === "alto" ? "banned today" : "banned on ALTO days"}</text>`;
  }

  // Forecast band: min to max of the members, and the truth line.
  const path = (vals) => vals.map((v, i) => `${cx(i)},${yb(v)}`).join(" ");
  const mins = members.map((m) => Math.min(...m)), maxs = members.map((m) => Math.max(...m));
  s += `<polygon points="${path(maxs)} ${members.map((m, i) => `${cx(n - 1 - i)},${yb(mins[n - 1 - i])}`).join(" ")}" fill="var(--hot)" fill-opacity=".22"/>`;
  s += `<polyline points="${path(maxs)}" fill="none" stroke="var(--hot)" stroke-width="1.6" stroke-opacity=".9"/>`;
  s += `<line x1="${L}" x2="${W - R}" y1="${yb(lim)}" y2="${yb(lim)}" stroke="var(--danger)" stroke-dasharray="6 5" stroke-width="1.2"/>`;
  s += `<text x="${W - R}" y="${yb(lim) - 5}" text-anchor="end" font-size="11.5" fill="var(--danger)">full hour allowed below ${lim.toFixed(1)} C</text>`;
  const truthPts = hours.map((h, i) => [i, DOC.truth_wbgt_by_hour[String(h)]]).filter((p) => p[1] !== undefined);
  if (truthPts.length) s += `<polyline points="${truthPts.map(([i, v]) => `${cx(i)},${yb(v)}`).join(" ")}" fill="none" stroke="var(--ink)" stroke-width="2.4"/>`;
  s += `<text x="${L - 8}" y="${yb(hi) + 10}" text-anchor="end" font-size="11" fill="var(--muted)">${hi} C</text><text x="${L - 8}" y="${yb(lo)}" text-anchor="end" font-size="11" fill="var(--muted)">${lo} C</text>`;
  s += `<text x="${L - 8}" y="${TOP + BAND / 2 + 4}" text-anchor="end" font-size="11" fill="var(--muted)">WBGT</text>`;

  // Minute gridlines and labels for the bars.
  [15, 30, 45, 60].forEach((m) => { s += `<line x1="${L}" x2="${W - R}" y1="${ym(m)}" y2="${ym(m)}" stroke="var(--rule)" stroke-width="1"/><text x="${L - 8}" y="${ym(m) + 4}" text-anchor="end" font-size="11" fill="var(--muted)">${m}</text>`; });
  s += `<text x="${L - 8}" y="${BASE + 4}" text-anchor="end" font-size="11" fill="var(--muted)">min</text>`;

  // One column per hour.
  PLAN.hours.forEach((h, i) => {
    const hh = String(parseInt(h.hour));
    const t = truthMin[hh];
    const tooHigh = t !== undefined && h.work_minutes > t;
    const x0 = cx(i) - bw / 2;
    let bar = "";
    if (h.outcome === "banned") {
      bar = `<rect class="bar" x="${x0}" y="${FIRST_PAINT ? BASE : ym(60)}" width="${bw}" height="${FIRST_PAINT ? 0 : BARS}" fill="url(#hatch)" rx="3"/>`;
    } else if (h.outcome === "undetermined") {
      // The whole hour is in question, so the dashed outline is the full hour; the
      // cautious bar inside is what the plan allows until the supervisor decides.
      const hMax = ym(60);
      bar = `<rect x="${x0}" y="${hMax}" width="${bw}" height="${BASE - hMax}" fill="none" stroke="var(--ink)" stroke-width="1.6" stroke-dasharray="5 4" rx="3"/>`
          + `<rect class="bar" x="${x0}" y="${FIRST_PAINT ? BASE : ym(h.work_minutes)}" width="${bw}" height="${FIRST_PAINT ? 0 : BASE - ym(h.work_minutes)}" fill="${heatColor(h.wbgt_c.max)}" rx="3"/>`
          + `<text x="${cx(i)}" y="${hMax + 22}" text-anchor="middle" font-size="17" font-weight="800" fill="var(--ink)">?</text>`;
    } else {
      const col = h.work_minutes === 0 ? "var(--stop)" : heatColor(h.wbgt_c.max);
      const hgt = h.work_minutes === 0 ? 5 : BASE - ym(h.work_minutes);
      bar = `<rect class="bar" x="${x0}" y="${FIRST_PAINT ? BASE : BASE - hgt}" width="${bw}" height="${FIRST_PAINT ? 0 : hgt}" fill="${col}" rx="3"/>`;
    }
    const label = h.outcome === "banned" ? "ban" : h.outcome === "undetermined" ? "you" : h.work_minutes === 60 ? "60" : String(h.work_minutes);
    s += `<g class="col${SELECTED === h.hour ? " sel" : ""}" data-h="${h.hour}" tabindex="0" role="button" aria-label="${h.hour}: ${esc(label)} minutes">`
       + `<rect class="hit" x="${x(i)}" y="${TOP + BAND + GAP}" width="${colW}" height="${BARS + 40}" fill="transparent" rx="6"/>`
       + bar
       + (tooHigh ? `<text x="${cx(i)}" y="${BASE + 34}" text-anchor="middle" font-size="11" font-weight="700" fill="var(--danger)">too high</text>` : "")
       + `<text x="${cx(i)}" y="${BASE + 18}" text-anchor="middle" font-size="13" font-weight="${h.outcome === "undetermined" ? 800 : 500}" fill="var(--ink)">${h.hour.slice(0, 2)}</text>`
       + `<text x="${cx(i)}" y="${Math.min(ym(h.work_minutes), BASE - 8) - 6}" text-anchor="middle" font-size="12" font-weight="700" fill="var(--ink)">${h.outcome === "banned" || h.outcome === "undetermined" ? "" : h.work_minutes}</text>`
       + `</g>`;
  });
  svg.innerHTML = s;
  svg.querySelectorAll(".col").forEach((g) => {
    g.addEventListener("click", () => { SELECTED = g.dataset.h; render(); $("#detail").scrollIntoView({ block: "nearest", behavior: "smooth" }); });
    g.addEventListener("keydown", (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); g.click(); } });
  });
  if (FIRST_PAINT) {
    FIRST_PAINT = false;
    requestAnimationFrame(() => requestAnimationFrame(() => strip(st, truthMin)));
  }
}

function showDetail(hour) {
  const h = PLAN.hours.find((p) => p.hour === hour);
  if (!h) { $("#detail").hidden = true; return; }
  const st = settings();
  const hh = String(parseInt(hour));
  const tw = DOC.truth_wbgt_by_hour[hh], tm = ((DOC.truth_minutes[st.workload] || {})[st.accl] || {})[hh];
  const title = h.outcome === "banned" ? "Banned by the ordinance" : h.outcome === "undetermined" ? "Your decision"
    : h.work_minutes === 60 ? "A full hour of work" : h.work_minutes === 0 ? "Stop: heat over the limit" : `${h.work_minutes} minutes of work, then rest in shade`;
  const nums = [`<div><b>${h.wbgt_c.min} to ${h.wbgt_c.max} C</b><span>forecast heat stress, lowest to hottest of ${h.wbgt_c.members} members</span></div>`,
    `<div><b>${h.work_minutes} min</b><span>planned, on the hottest member</span></div>`];
  if (tw !== undefined) nums.push(`<div><b>${tw.toFixed(1)} C</b><span>what happened</span></div><div><b class="${tm < h.work_minutes ? "bad" : ""}">${tm} min</b><span>what reality allowed</span></div>`);
  const why = h.reasons.length ? h.reasons.map((r) => `<p class="why">${esc(r)}</p>`).join("") : `<p class="why">Every member keeps this hour inside the NIOSH limit for ${WORK_NAME[st.workload]}.</p>`;
  const explainBtn = h.needs_supervisor ? `<button class="btn ghost" id="btn-explain">Explain this hour (a model on AMD)</button><div class="exp" id="exp"></div>` : "";
  $("#detail").innerHTML = `<button class="close" aria-label="Close">&times;</button><h3>${hour}: ${title}</h3><div class="nums">${nums.join("")}</div>${why}${explainBtn}`;
  $("#detail").hidden = false;
  $("#detail .close").addEventListener("click", () => { SELECTED = null; render(); });
  if (h.needs_supervisor) $("#btn-explain").addEventListener("click", () => explain(h));
}

function facts(st, truthMin, restricted, kept, over) {
  const hrs = Object.keys(truthMin).map(Number);
  const outside = hrs.filter((h) => truthMin[h] < 60 && (h < 12 || h > 15)).length;
  if (DOC.live) {
    $("#facts").innerHTML = `<div><span class="k">Forecast</span><span class="v">10 members</span><span class="s">ECMWF ensemble, same frozen rules as the tested replay days.</span></div>
      <div><span class="k">Hours for you</span><span class="v">${PLAN.summary.handed_over}</span><span class="s">Where the members disagree by 30 minutes of work or more.</span></div>
      <div><span class="k">Before you start</span><span class="v">${st.alto === "unconfirmed" ? "Rating?" : st.alto === "alto" ? "ALTO" : "Not ALTO"}</span><span class="s">Confirm tomorrow's Worklimate rating in the morning; the ban is assumed until you do.</span></div>`;
    return;
  }
  $("#facts").innerHTML = `
    <div><span class="k">Heat-restricted hours outside the 12:30 to 16:00 ban, this day</span><span class="v">${outside} of ${restricted}</span><span class="s">Hours the law alone leaves uncovered. About two in three, all summer.</span></div>
    <div><span class="k">Restricted hours the plan kept within the limit</span><span class="v ${kept === restricted ? "good" : ""}">${kept} of ${restricted}</span><span class="s">Planned the day before.</span></div>
    <div><span class="k">Hours the plan allowed too much work</span><span class="v ${over ? "bad" : "good"}">${over}</span><span class="s">Marked on the strip.</span></div>`;
}

function law() {
  const o = DOC.ordinances.find((x) => x.status === "VERIFIED_PRIMARY") || DOC.ordinances[0];
  if (!o) { $("#ord").innerHTML = `<p class="lead">No ordinance on record for this region.</p>`; return; }
  const win = o.windows.map((w) => `${dayName(w[0])} to ${dayName(w[1])}`).join("; ");
  $("#ord").innerHTML = `<p class="law-h">${esc(DOC.region)}, ordinance ${esc(o.number)}</p>
    <p class="law-s">No work ${esc(o.ban.replace("-", " to "))} on days Worklimate rates ALTO. In force ${esc(win)} 2026. <a href="${esc(o.url)}" target="_blank" rel="noopener">Read the source</a></p>
    <blockquote>${esc(o.trigger).slice(0, 380)}</blockquote>`;
}

function amd() {
  const reg = DOC.region;
  const r = Array.isArray(READER) ? READER.find((x) => x.region === reg) : null;
  let html = r ? fieldsTable(r.fields, `${esc(reg)}: read by ${esc(r.model)} on AMD from ${esc(r.source)}, ${r.latency_s} s.`) : `<p class="check">No stored reading for ${esc(reg)}.</p>`;
  html += SOURCES[reg]
    ? `<button class="btn" id="btn-reread">Re-read ${esc(reg)}'s signed PDF now, on AMD</button><div id="reread"></div>`
    : `<p class="check">${esc(reg)} publishes its order in a bulletin rather than one signed PDF, so the reading above came from the saved primary text. Live re-reads run for Liguria, Lombardia, Puglia, Sicilia, Calabria, Sardegna and Umbria: pick Imperia, Milano or Foggia.</p>`;
  $("#amd").innerHTML = html;
  if (SOURCES[reg]) $("#btn-reread").addEventListener("click", reread);
}
function fieldsTable(fields, caption) {
  const rows = Object.entries(fields).map(([k, f]) => `<tr><td>${esc(k.replace("_", " "))}</td><td>${esc(f.value ?? "")}</td>
    <td>${f.accepted ? '<span class="ok-pill">verified</span>' : '<span class="rev-pill">to a person</span>'}</td>
    <td class="q">${esc(f.reason)}${f.quote ? `<br>&ldquo;${esc(String(f.quote).slice(0, 170))}${String(f.quote).length > 170 ? "..." : ""}&rdquo;` : ""}</td></tr>`).join("");
  return `<p class="check">${caption}</p><table class="fields"><thead><tr><th>Field</th><th>Proposed</th><th>Check</th><th>Why, and the quote it rests on</th></tr></thead><tbody>${rows}</tbody></table>`;
}
async function reread() {
  const reg = DOC.region;
  const say = (h) => { if (DOC.region === reg && $("#reread")) $("#reread").innerHTML = h; };
  say(`<p class="check">Reading the signed PDF on AMD: MinerU, then DeepSeek, then the quote checks. 30 to 120 seconds.</p>`);
  try {
    await fetch("/api/reread", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ region: reg }) });
    for (let i = 0; i < 80; i++) {
      await new Promise((r) => setTimeout(r, 3000));
      const r = await (await fetch(`/api/reread/${encodeURIComponent(reg)}`)).json();
      if (r.status === "running") { say(`<p class="check">Still reading on AMD, ${3 * (i + 1)} s.</p>`); continue; }
      if (r.status === "error") { say(`<p class="check bad">AMD's service failed this time (${esc(r.message)}). The stored reading is unchanged. Try again in a minute.</p>`); return; }
      const ok = Object.values(r.fields).filter((f) => f.accepted).length, n = Object.keys(r.fields).length;
      say(fieldsTable(r.fields, `Live re-read at ${esc(r.at)}: OCR ${r.ocr_seconds} s (${r.chars} characters), extraction ${r.read_seconds} s, cost $${Number(r.cost_usd).toFixed(5)}. ${ok} of ${n} fields verified.`));
      return;
    }
    say(`<p class="check bad">No answer from AMD within 4 minutes. The stored reading is unchanged.</p>`);
  } catch (e) { say(`<p class="check bad">The AMD call failed. The stored reading is unchanged.</p>`); }
}

function logTable() {
  $("#log tbody").innerHTML = PLAN.hours.map((h) => `<tr><td>${h.hour}</td><td>${h.outcome === "banned" ? "banned" : h.outcome === "undetermined" ? "supervisor decides" : h.work_minutes === 60 ? "full work" : h.work_minutes === 0 ? "stop" : `${h.work_minutes} min`}</td><td>${h.work_minutes}</td><td class="basis">${esc(h.reasons.join(" ") || "Within the NIOSH limit for this work.")}</td></tr>`).join("");
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
  $("#brief").textContent = "Writing.";
  const o = DOC.ordinances.find((x) => x.status === "VERIFIED_PRIMARY");
  const plan = { site: DOC.name, date: DOC.date, crew: `${st.workload} work, ${st.accl === "accl" ? "acclimatized" : "not acclimatized"}`,
                 ban_window: o && st.alto === "alto" ? o.ban.split("-") : [], hours: PLAN.hours };
  const r = await (await fetch("/api/briefing", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ plan }) })).json();
  $("#brief").textContent = r.text;
  $("#brief-tag").textContent = r.by_model ? `Written by ${r.model} (${r.backend}). Every number checked against the plan.` : `The model's text failed the number check (${(r.problems || []).slice(0, 2).join("; ")}), so this is the fixed wording.`;
}
async function explain(h) {
  $("#exp").innerHTML = `<p class="check">Asking a model on AMD.</p>`;
  const r = await (await fetch("/api/explain", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ hour: h, site: DOC.name, date: DOC.date }) })).json();
  $("#exp").innerHTML = r.text
    ? `<pre>${esc(r.text)}</pre><p class="check">${esc(r.model)} on ${esc(r.runs_on)}, ${r.latency_s} s. Numbers checked against the plan.</p>`
    : `<p class="check bad">The model's text failed the number check, so only the plan's own reasons are shown.</p>`;
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
    if (line.startsWith("# ")) out.push(`<h3>${esc(line.slice(2))}</h3>`);
    else if (line.startsWith("## ")) out.push(`<h3>${esc(line.slice(3))}</h3>`);
    else if (line.trim()) out.push(`<p>${esc(line).replace(/\*\*(.+?)\*\*/g, "<b>$1</b>").replace(/`(.+?)`/g, "<code>$1</code>")}</p>`);
  }
  const cell = (c) => esc(c).replace(/\*\*(.+?)\*\*/g, "<b>$1</b>");
  return out.map((b) => Array.isArray(b)
    ? `<div class="evid"><table><thead><tr>${b[0].map((c) => `<th>${cell(c)}</th>`).join("")}</tr></thead><tbody>${b.slice(1).map((r) => `<tr>${r.map((c) => `<td>${cell(c)}</td>`).join("")}</tr>`).join("")}</tbody></table></div>`
    : b).join("");
}
async function evidence() {
  const parts = [];
  try {
    const lines = (await (await fetch("/evidence/amd_calls.jsonl")).text()).trim().split("\n").map((l) => JSON.parse(l));
    const lat = lines.map((l) => l.latency_s).sort((a, b) => a - b), cost = lines.reduce((a, l) => a + l.cost_usd, 0);
    parts.push(`<p>${lines.length} model calls on AMD Token Factory are logged in <code>results/amd_calls.jsonl</code>: median latency ${lat[Math.floor(lat.length / 2)]} s, total cost $${cost.toFixed(4)}.</p>`);
  } catch (e) {}
  for (const f of ["value.md", "grid_summary.md", "ordinance_reader.md", "ordinance_reader_run1.md", "rule_sweep_june.md", "solar-validation.md"]) {
    try { const r = await fetch(`/evidence/${f}`); if (r.ok) parts.push(md(await r.text())); } catch (e) {}
  }
  $("#evidence-body").innerHTML = `<p>Every number here comes from a script in the repository and can be rerun. The comparison dates and predictions were written down before the July and August test set was scored (<code>results/PREREGISTRATION.md</code>).</p>` + parts.join("");
}
init();
