"use strict";
// The demo scene. Loaded only with ?demo=1. It drives the real page: the same
// data, the same model calls, the same checks. Nothing here draws a result.
//
// record.py calls window.__demoPlay(timing, breath) with the length of every
// narration line, so the pointer moves to what the voice is talking about as
// each line starts, and each beat holds exactly as long as its lines need.
// It reads window.__demoMarks back, one entry per beat with the second its
// picture appeared, so narration is timed to the take that was recorded.
(() => {
  const marks = [], t0 = performance.now();
  const now = () => (performance.now() - t0) / 1000;
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  const until = async (t) => { const ms = (t - now()) * 1000; if (ms > 0) await sleep(ms); };
  const mark = (id) => marks.push({ id, at: +now().toFixed(3) });
  window.__demoMarks = marks; window.__demoDone = false; window.__demoError = null; window.__demoFacts = {};
  const $ = (s) => document.querySelector(s);
  const $$ = (s) => Array.from(document.querySelectorAll(s));

  // A pointer drawn on the page, because a headless screencast has no cursor.
  // It is the standard arrow, and it moves the way a hand moves a mouse: along
  // a slight curve, fast in the middle, settling at the end.
  const cur = document.createElement("div");
  cur.id = "demo-cursor";
  cur.style.cssText = "position:fixed;z-index:99;left:0;top:0;width:20px;height:28px;pointer-events:none;opacity:0;transition:opacity .4s;will-change:transform";
  cur.innerHTML = `<svg width="20" height="28" viewBox="0 0 20 28" style="filter:drop-shadow(0 1px 1.5px rgba(0,0,0,.45))">
    <path d="M2 1.5 L2 21.5 L7.2 16.8 L10.6 25 L14.2 23.4 L10.9 15.5 L17.8 15.5 Z" fill="#111" stroke="#fff" stroke-width="1.6" stroke-linejoin="round"/></svg>`;
  document.body.appendChild(cur);
  let px = innerWidth * 0.62, py = innerHeight * 0.55;
  const put = (x, y) => { px = x; py = y; cur.style.transform = `translate(${x - 2}px,${y - 1.5}px)`; };
  put(px, py);
  const show = () => { cur.style.opacity = "1"; };
  const hide = () => { cur.style.opacity = "0"; };
  const rnd = (a, b) => a + Math.random() * (b - a);
  const ease = (t) => t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;
  async function glide(x, y, opts = {}) {
    const dx = x - px, dy = y - py, dist = Math.hypot(dx, dy);
    if (dist < 1) return;
    const ms = opts.ms || Math.min(1300, Math.max(260, 240 + dist * 0.75)) * rnd(0.9, 1.1);
    // The control point sits a little off the straight line, so the path bends.
    const bend = (opts.bend ?? 0.12) * dist * (Math.random() < 0.5 ? -1 : 1);
    const cxp = px + dx / 2 - dy / dist * bend, cyp = py + dy / 2 + dx / dist * bend;
    const x0 = px, y0 = py, start = performance.now();
    await new Promise((done) => {
      const step = () => {
        const u = Math.min(1, (performance.now() - start) / ms), t = ease(u);
        const bx = (1 - t) * (1 - t) * x0 + 2 * (1 - t) * t * cxp + t * t * x;
        const by = (1 - t) * (1 - t) * y0 + 2 * (1 - t) * t * cyp + t * t * y;
        put(bx, by);
        if (u < 1) requestAnimationFrame(step); else done();
      };
      requestAnimationFrame(step);
    });
    // A hand never stops dead: a small settle at the end.
    if (!opts.noSettle) { await glide(x + rnd(-2, 2), y + rnd(-1.5, 1.5), { ms: 140, bend: 0, noSettle: true }); }
  }
  // Point at an element: fx, fy are fractions of its box (0.5, 0.5 is its centre).
  const at = (el, fx = 0.5, fy = 0.5) => { const r = el.getBoundingClientRect(); return [r.left + r.width * fx, r.top + r.height * fy]; };
  async function hover(el, fx = 0.5, fy = 0.5, opts) { if (!el) return; const [x, y] = at(el, fx, fy); await glide(x, y, opts); }
  async function press() { cur.style.transition = "opacity .4s, transform .09s"; cur.style.transform += " scale(.86)"; await sleep(90); put(px, py); await sleep(110); }
  // dispatchEvent rather than el.click(): the strip's columns are SVG groups,
  // and SVG elements have no click() method.
  async function click(el, fx = 0.5, fy = 0.5) { await hover(el, fx, fy); await press(); el.dispatchEvent(new MouseEvent("click", { bubbles: true, cancelable: true })); }
  async function choose(sel, value) { const el = $(sel); await click(el, 0.5, 0.5); el.value = value; el.dispatchEvent(new Event("change")); await sleep(300); }
  async function scrollTo(el, block = "start") { el.scrollIntoView({ behavior: "smooth", block }); await sleep(900); }
  // Move along a list of points over a span of seconds, pausing on each.
  async function trace(points, secs) {
    const n = points.length, each = Math.max(0.25, secs / n);
    for (const [x, y] of points) { const t = now(); await glide(x, y); await until(t + each); }
  }
  const col = (h) => $(`#strip .col[data-h="${h}"]`);
  const colTop = (h, dy = -6) => { const r = (col(h).querySelector(".bar") || col(h)).getBoundingClientRect(); return [r.left + r.width / 2, r.top + dy]; };
  const colLabel = (h) => { const r = col(h).getBoundingClientRect(); return [r.left + r.width / 2, r.bottom - 22]; };
  const polylinePts = (el, k) => {  // k evenly spaced points along an SVG polyline, in page pixels
    const pts = el.getAttribute("points").trim().split(/\s+/).map((p) => p.split(",").map(Number));
    const ctm = el.getScreenCTM();
    const pick = Array.from({ length: k }, (_, i) => pts[Math.round(i * (pts.length - 1) / (k - 1))]);
    return pick.map(([x, y]) => { const p = el.ownerSVGElement.createSVGPoint(); p.x = x; p.y = y; const q = p.matrixTransform(ctm); return [q.x, q.y]; });
  };
  const waitFor = async (fn, ms = 30000) => { const t = performance.now(); while (!fn()) { if (performance.now() - t > ms) throw new Error("waited too long for " + fn); await sleep(100); } };

  // Full-screen slates at the start and the end, in the page's own type and colours.
  const slate = document.createElement("div");
  slate.style.cssText = "position:fixed;inset:0;z-index:98;background:var(--paper);color:var(--ink);display:flex;flex-direction:column;justify-content:center;padding:0 120px;opacity:1;transition:opacity .8s;font-family:'Bricolage Grotesque',system-ui,sans-serif";
  document.body.appendChild(slate);
  const showSlate = (html) => { slate.innerHTML = html; slate.style.opacity = "1"; slate.style.pointerEvents = "auto"; };
  const hideSlate = async () => { slate.style.opacity = "0"; slate.style.pointerEvents = "none"; await sleep(850); };

  // A beat: mark its start, then run each line's pointer work when that line
  // starts in the narration, and hold until the last line has ended.
  let TIMING = {}, BREATH = 0.45;
  function lines(beat) {
    const secs = TIMING[beat] || [];
    let t = 0; const out = [];
    for (const s of secs) { t += BREATH; out.push({ start: t, secs: s, end: t + s }); t += s; }
    return { lines: out, hold: t + BREATH + 1.2 };
  }
  async function beat(id, actions = []) {
    const { lines: ls, hold } = lines(id);
    const t = now(); mark(id);
    for (let i = 0; i < ls.length; i++) {
      await until(t + ls[i].start);
      if (actions[i]) await actions[i](ls[i].secs);
    }
    await until(t + hold);
  }

  window.__demoPlay = async (timing, breath) => {
    TIMING = timing || {}; BREATH = breath || BREATH;
    try {
      // The Lombardia re-read starts now, on AMD, with its OCR cache cleared by
      // record.py, so both the OCR and the extraction run while the film plays.
      fetch("/api/reread", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ region: "Lombardia", force: true }) }).catch(() => {});

      // Opening slate.
      showSlate(`<div style="font-size:120px;font-weight:800;letter-spacing:-.03em;line-height:1">Turno</div>
        <div style="font-size:34px;margin-top:22px;max-width:30ch">Heat-safe shift planning for outdoor crews.</div>
        <div style="font-size:20px;color:var(--muted);margin-top:40px">AMD Developer Hackathon: ACT III</div>`);
      await beat("title");

      // Milan, 31 July 2026, heavy work, crew new to the heat: set while the slate still covers the page.
      $("#site").value = "milano"; $("#site").dispatchEvent(new Event("change")); await sleep(500);
      $("#day").value = "2026-07-31"; $("#day").dispatchEvent(new Event("change"));
      await waitFor(() => /31 July/.test($("#where").textContent) && $$("#strip .col").length > 5);
      await sleep(300);
      window.scrollTo({ top: 0 }); put(innerWidth * 0.64, innerHeight * 0.5); await hideSlate(); show();
      await beat("open", [
        async () => { await hover($("#where"), 0.15, 0.5); },
        async (s) => { await sleep(s * 400); await hover($("#where"), 0.72, 0.5); },
      ]);

      await beat("verdict", [
        async (s) => { await trace([at($("#site")), at($("#day")), at($("#workload")), at($("#accl"))], s * 0.85); },
        async (s) => { await hover($("#verdict .n"), 0.5, 0.6); await sleep(s * 350); await hover($("#verdict"), 0.6, 0.75); },
        async (s) => { await sleep(s * 300); await hover($("#checked .bad") || $("#checked"), 0.5, 0.5); },
      ]);

      await scrollTo($(".strip"), "center");
      await beat("strip", [
        async (s) => { await trace(["07:00", "09:00", "11:00", "13:00", "15:00", "17:00", "19:00"].map(colLabel), s * 0.9); },
        async (s) => {
          await hover(...[col("07:00")], 0.5, 0.3); await glide(...colTop("07:00")); await until(now() + s * 0.12);  // height
          await trace([colTop("08:00"), colTop("09:00")], s * 0.2);                                                  // colour
          const band = $("#strip polygon"); await hover(band, 0.45, 0.5); await until(now() + s * 0.15);              // the spread
          const truth = $$("#strip polyline").find((p) => p.getAttribute("stroke") === "var(--ink)");               // the black line
          if (truth) await trace(polylinePts(truth, 5), s * 0.4);
        },
      ]);

      // The hour the plan got wrong.
      await click(col("09:00"), 0.5, 0.6);
      await waitFor(() => !$("#detail").hidden && /09:00/.test($("#detail").textContent));
      await scrollTo($("#detail"), "center");
      await beat("toohigh", [
        async (s) => { const n = $$("#detail .nums > div"); await hover(n[1], 0.3, 0.4); await until(now() + s * 0.45); await hover(n[3] || n[1], 0.3, 0.4); },
        async (s) => { const th = $$('#strip .col[data-h="09:00"] text').find((t) => t.textContent === "too high"); if (th) await hover(th); await until(now() + s * 0.45); await hover($("#detail .why"), 0.25, 0.5); },
      ]);

      // Confirm the official rating: the law takes over the afternoon.
      await scrollTo($(".rating"), "center");
      const altoBtn = document.querySelector('input[name=alto][value=alto]').closest("label");
      await click(altoBtn);
      await waitFor(() => /banned by law/.test($("#verdict").textContent));
      await scrollTo($(".strip"), "center");
      await beat("alto", [
        async (s) => { await hover($("#verdict .ban .n") || $("#verdict"), 0.5, 0.6); },
        async (s) => { await trace([colTop("13:00", 40), colTop("14:00", 40), colTop("15:00", 40)], s * 0.55); await hover($("#strip polygon"), 0.6, 0.5); },
      ]);

      await click(col("14:00"), 0.5, 0.6);
      await waitFor(() => /14:00: Banned/.test($("#detail").textContent));
      await scrollTo($("#detail"), "center");
      await beat("banned", [
        async (s) => { await hover($("#detail h3"), 0.3, 0.5); await until(now() + s * 0.4); await hover($("#detail .why"), 0.3, 0.5); },
      ]);

      // Before the rating is known, the same hours are the supervisor's.
      await scrollTo($(".rating"), "center");
      await click(document.querySelector('input[name=alto][value=unconfirmed]').closest("label"));
      await waitFor(() => /yours to decide/.test($("#verdict").textContent));
      await click(col("12:00"), 0.5, 0.6);
      await waitFor(() => /12:00: Your decision/.test($("#detail").textContent));
      await scrollTo($("#detail"), "center");
      await beat("decide", [
        async (s) => { await trace(["12:00", "13:00", "14:00", "15:00"].map((h) => colTop(h, 30)), s * 0.8); },
        async (s) => { await hover($("#detail h3"), 0.3, 0.5); await until(now() + s * 0.4); await hover($("#detail .why"), 0.3, 0.5); },
      ]);

      // A model on AMD explains it, and the numbers are checked.
      await click($("#btn-explain"));
      await waitFor(() => /ENGLISH/.test($("#exp").textContent) || /failed/.test($("#exp").textContent), 60000);
      await scrollTo($("#exp"), "center");
      window.__demoFacts.explain = $("#exp").textContent.slice(0, 200);
      await beat("explain", [
        async (s) => { await hover($("#exp"), 0.2, 0.15); await until(now() + s * 0.5); await hover($("#exp"), 0.2, 0.6); },
        async (s) => { await hover($("#exp"), 0.5, 0.65); await until(now() + s * 0.5); await hover($("#exp"), 0.7, 0.85); },
      ]);

      // Gemma writes the briefing.
      await scrollTo($("#btn-brief"), "center");
      await click($("#btn-brief"));
      await waitFor(() => /ENGLISH/.test($("#brief").textContent), 90000);
      await scrollTo($("#brief"), "center");
      window.__demoFacts.briefTag = $("#brief-tag").textContent;
      await beat("briefing", [
        async (s) => { await hover($("#brief"), 0.2, 0.1); await until(now() + s * 0.5); await hover($("#brief"), 0.3, 0.4); },
        async (s) => { await hover($("#brief-tag"), 0.2, 0.5); },
      ]);

      // The ordinance, read on AMD.
      await scrollTo($("#amd-section"), "start");
      await beat("law", [
        async (s) => { await hover($(".law-h"), 0.3, 0.5); await until(now() + s * 0.55); await hover($("#amd .check"), 0.3, 0.5); },
        async (s) => { const rows = $$("#amd table.fields tbody tr").slice(0, 4); await trace(rows.map((r) => at(r.querySelector("td.q"), 0.2, 0.3)), s * 0.9); },
      ]);
      await click($("#btn-reread"));
      await waitFor(() => /Live re-read/.test($("#reread").textContent) || /failed|unchanged/.test($("#reread").textContent), 300000);
      if (!/Live re-read/.test($("#reread").textContent)) {  // AMD's OCR answers 502 now and then: one more try
        await sleep(4000); await click($("#btn-reread"));
        await waitFor(() => /Live re-read/.test($("#reread").textContent) || /failed|unchanged/.test($("#reread").textContent), 300000);
      }
      await scrollTo($("#reread"), "center");
      window.__demoFacts.reread = $("#reread").textContent.slice(0, 160);
      await beat("reread", [
        async (s) => { await hover($("#reread .check"), 0.25, 0.5); },
        async (s) => { const rows = $$("#reread table.fields tbody tr"); const r = rows[2] || rows[0]; if (!r) return;
          await hover(r.querySelector(".ok-pill, .rev-pill")); await until(now() + s * 0.35); await hover(r.querySelector("td.q"), 0.3, 0.6); await until(now() + s * 0.35);
          const r2 = rows[3] || r; await hover(r2.querySelector("td.q"), 0.3, 0.6); },
      ]);

      // Tomorrow, from the latest forecast run.
      window.scrollTo({ top: 0, behavior: "smooth" }); await sleep(900);
      await choose("#day", "live");
      await waitFor(() => /Tomorrow/.test($("#where").textContent) && $$("#strip .col").length > 5, 60000);
      await sleep(400);
      await beat("live", [
        async (s) => { await hover($("#where"), 0.3, 0.5); await until(now() + s * 0.5); await hover($("#verdict"), 0.3, 0.5); },
      ]);

      // The evidence.
      const ev = $("#evidence details"); ev.open = true;
      await scrollTo($("#evidence"), "start");
      await beat("evidence", [
        async (s) => { const p = $("#evidence-body p"); await hover(p || $("#evidence"), 0.2, 0.5); },
        async (s) => { const rows = $$("#evidence-body table tbody tr").slice(0, 3); if (rows.length) await trace(rows.map((r) => at(r, 0.35, 0.5)), s * 0.8); },
      ]);

      // Closing slate.
      hide();
      showSlate(`<div style="font-size:64px;font-weight:800;letter-spacing:-.02em;line-height:1.05;max-width:22ch">The models read and explain. The rules decide. The supervisor has the last word.</div>
        <div style="font-size:26px;margin-top:36px;line-height:1.5">turno.aashanjaved.com<br>github.com/Aashan47/turno</div>
        <div style="font-size:18px;color:var(--muted);margin-top:30px;max-width:70ch">On AMD: the ordinance reader and the hand-off explanations, through AMD Token Factory. Forecast: ECMWF ensemble. What happened: ERA5. Limits: NIOSH 2016-106.</div>`);
      await sleep(900);
      await beat("close");

      window.__demoElapsed = +now().toFixed(3);
      window.__demoDone = true;
    } catch (e) { window.__demoError = String(e); window.__demoDone = true; }
  };
})();
