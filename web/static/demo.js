"use strict";
// The demo scene. Loaded only with ?demo=1. It drives the real page: the same
// data, the same model calls, the same checks. Nothing here draws a result.
//
// record.py calls window.__demoPlay() and reads window.__demoMarks, one entry
// per beat with the second its picture appeared, so narration can be timed to
// the take that was actually recorded.
(() => {
  const marks = [], t0 = performance.now();
  const now = () => (performance.now() - t0) / 1000;
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  const mark = (id) => marks.push({ id, at: +now().toFixed(3) });
  window.__demoMarks = marks; window.__demoDone = false; window.__demoError = null; window.__demoFacts = {};

  // A synthetic cursor: Playwright clicks without moving a mouse, so the
  // viewer would otherwise see things happen with no hand behind them.
  const cur = document.createElement("div");
  cur.id = "demo-cursor";
  cur.style.cssText = "position:fixed;z-index:99;width:18px;height:18px;border-radius:50%;background:rgba(30,26,21,.85);border:2px solid #fff;box-shadow:0 2px 8px rgba(0,0,0,.35);pointer-events:none;left:50%;top:50%;transform:translate(-50%,-50%);transition:left .7s cubic-bezier(.3,.7,.2,1),top .7s cubic-bezier(.3,.7,.2,1),transform .15s";
  document.body.appendChild(cur);
  async function moveTo(el) {
    const r = el.getBoundingClientRect();
    cur.style.left = `${r.left + r.width / 2}px`; cur.style.top = `${r.top + r.height / 2}px`;
    await sleep(800);
  }
  async function press() { cur.style.transform = "translate(-50%,-50%) scale(.7)"; await sleep(140); cur.style.transform = "translate(-50%,-50%)"; }
  // dispatchEvent rather than el.click(): the strip's columns are SVG groups,
  // and SVG elements have no click() method.
  async function click(el) { await moveTo(el); await press(); el.dispatchEvent(new MouseEvent("click", { bubbles: true, cancelable: true })); }
  async function choose(sel, value) { const el = document.querySelector(sel); await moveTo(el); await press(); el.value = value; el.dispatchEvent(new Event("change")); }
  async function scrollTo(el, block = "start") { el.scrollIntoView({ behavior: "smooth", block }); await sleep(900); }
  const waitFor = async (fn, ms = 30000) => { const t = performance.now(); while (!fn()) { if (performance.now() - t > ms) throw new Error("waited too long for " + fn); await sleep(100); } };
  const $ = (s) => document.querySelector(s);

  // Full-screen slates at the start and the end, in the page's own type and colours.
  const slate = document.createElement("div");
  slate.style.cssText = "position:fixed;inset:0;z-index:98;background:var(--paper);color:var(--ink);display:flex;flex-direction:column;justify-content:center;padding:0 120px;opacity:1;transition:opacity .8s;font-family:'Bricolage Grotesque',system-ui,sans-serif";
  document.body.appendChild(slate);
  const showSlate = (html) => { slate.innerHTML = html; slate.style.opacity = "1"; slate.style.pointerEvents = "auto"; };
  const hideSlate = async () => { slate.style.opacity = "0"; slate.style.pointerEvents = "none"; await sleep(850); };

  window.__demoPlay = async () => {
    try {
      // Opening slate.
      showSlate(`<div style="font-size:120px;font-weight:800;letter-spacing:-.03em;line-height:1">Turno</div>
        <div style="font-size:34px;margin-top:22px;max-width:30ch">Heat-safe shift planning for outdoor crews.</div>
        <div style="font-size:20px;color:var(--muted);margin-top:40px">AMD Developer Hackathon: ACT III</div>`);
      mark("title"); await sleep(5500);

      // Milan, 31 July 2026, heavy work, crew new to the heat.
      await choose("#site", "milano"); await sleep(500);
      await choose("#day", "2026-07-31");
      await waitFor(() => /31 July/.test($("#where").textContent) && document.querySelectorAll("#strip .col").length > 5);
      await sleep(300);
      window.scrollTo({ top: 0 }); await hideSlate();
      mark("open"); await sleep(9000);

      mark("verdict"); await sleep(9000);

      await scrollTo($(".strip"), "center");
      mark("strip"); await sleep(10000);

      // The hour the plan got wrong.
      await click($('#strip .col[data-h="09:00"]'));
      await waitFor(() => !$("#detail").hidden && /09:00/.test($("#detail").textContent));
      await scrollTo($("#detail"), "center");
      mark("toohigh"); await sleep(10000);

      // Confirm the official rating: the law takes over the afternoon.
      await scrollTo($(".rating"), "center");
      await click(document.querySelector('input[name=alto][value=alto]').closest("label"));
      await waitFor(() => /banned by law/.test($("#verdict").textContent));
      await scrollTo($(".strip"), "center");
      mark("alto"); await sleep(9000);

      await click($('#strip .col[data-h="14:00"]'));
      await waitFor(() => /14:00: Banned/.test($("#detail").textContent));
      await scrollTo($("#detail"), "center");
      mark("banned"); await sleep(7000);

      // Before the rating is known, the same hours are the supervisor's.
      await scrollTo($(".rating"), "center");
      await click(document.querySelector('input[name=alto][value=unconfirmed]').closest("label"));
      await waitFor(() => /yours to decide/.test($("#verdict").textContent));
      await click($('#strip .col[data-h="12:00"]'));
      await waitFor(() => /12:00: Your decision/.test($("#detail").textContent));
      await scrollTo($("#detail"), "center");
      mark("decide"); await sleep(8000);

      // A model on AMD explains it, and the numbers are checked.
      await click($("#btn-explain"));
      await waitFor(() => /ENGLISH/.test($("#exp").textContent) || /failed/.test($("#exp").textContent), 60000);
      await scrollTo($("#exp"), "center");
      window.__demoFacts.explain = $("#exp").textContent.slice(0, 200);
      mark("explain"); await sleep(12000);

      // Gemma writes the briefing.
      await scrollTo($("#btn-brief"), "center");
      await click($("#btn-brief"));
      await waitFor(() => /ENGLISH/.test($("#brief").textContent), 90000);
      await scrollTo($("#brief"), "center");
      window.__demoFacts.briefTag = $("#brief-tag").textContent;
      mark("briefing"); await sleep(12000);

      // The ordinance, read on AMD.
      await scrollTo($("#amd-section"), "start");
      mark("law"); await sleep(8000);
      await click($("#btn-reread"));
      await waitFor(() => /Live re-read/.test($("#reread").textContent) || /failed|unchanged/.test($("#reread").textContent), 240000);
      await scrollTo($("#reread"), "center");
      window.__demoFacts.reread = $("#reread").textContent.slice(0, 160);
      mark("reread"); await sleep(12000);

      // Tomorrow, from the latest forecast run.
      window.scrollTo({ top: 0, behavior: "smooth" }); await sleep(900);
      await choose("#day", "live");
      await waitFor(() => /Tomorrow/.test($("#where").textContent) && document.querySelectorAll("#strip .col").length > 5, 60000);
      await sleep(400);
      mark("live"); await sleep(9000);

      // The evidence.
      const ev = $("#evidence details"); ev.open = true;
      await scrollTo($("#evidence"), "start");
      mark("evidence"); await sleep(10000);

      // Closing slate.
      showSlate(`<div style="font-size:64px;font-weight:800;letter-spacing:-.02em;line-height:1.05;max-width:22ch">The models read and explain. The rules decide. The supervisor has the last word.</div>
        <div style="font-size:26px;margin-top:36px;line-height:1.5">turno.aashanjaved.com<br>github.com/Aashan47/turno</div>
        <div style="font-size:18px;color:var(--muted);margin-top:30px;max-width:70ch">On AMD: the ordinance reader and the hand-off explanations, through AMD Token Factory. Forecast: ECMWF ensemble. What happened: ERA5. Limits: NIOSH 2016-106.</div>`);
      await sleep(900);
      mark("close"); await sleep(9000);

      window.__demoElapsed = +now().toFixed(3);
      window.__demoDone = true;
    } catch (e) { window.__demoError = String(e); window.__demoDone = true; }
  };
})();
