/*
 * x-axis / grid jump auto-capture probe (issue 26-11-17-0936)
 *
 * Fully automatic: no manual marking. A one-frame jump cannot be marked by hand.
 *
 * Usage:
 *   1. Open the page where the jump reproduces, stay on the traffic tab/window.
 *   2. Paste this whole file into DevTools Console and press Enter.
 *      Prints "[xgrid-probe] ready" and starts watching ALL chart scopes.
 *   3. Just watch the charts for a few minutes. Every time a real jump is
 *      detected, the probe freezes the frames around it automatically and logs
 *      "[xgrid-probe] CAPTURED ...".
 *   4. Export everything:
 *         copy(JSON.stringify(xgridProbe.report()))
 *      Paste the result back into the conversation.
 *
 * What it records per draw, for every scope (torrent / global / group):
 *   - x scale min/max, full splits array
 *   - u.bbox and canvas backing-store size
 *   - real grid-column pixels sampled from the canvas at mid-plot height
 *   - host clientWidth/clientHeight, and every u.setSize() call
 *   - beat phase / clock / pad / data length
 *
 * Jump detection: track the middle grid columns (excluding the two at each end,
 * which normally slide in/out) between consecutive draws. If any middle column
 * jumps more than 20px in one draw, or x scale jumps > 0.5s, or bbox/canvas size
 * changes, that draw is a real jump. This avoids the false positive where
 * splits[0] changes only because the array rotates.
 */
(() => {
  const app = document.querySelector('#app');
  const vm = app && app._vnode && app._vnode.component.proxy;
  if (!vm) { console.error('[xgrid-probe] Vue instance not found'); return; }

  const KEYS = ['torrent', 'global', 'group'];
  const BUF = 800;            // ring buffer length per scope
  const KEEP = 12;            // frames kept before/after a captured jump
  const COOLDOWN = 15;        // frames to wait before capturing again
  const CAP_MAX = 100;        // hard cap on stored captures (each holds 2*KEEP frames)
  const PX_TH = 20;           // grid column jump threshold (px)
  const S_TH = 0.5;           // x scale jump threshold (s)
  const state = {
    buf: {}, captures: [], sizeEvents: [], attached: {},
    cool: {}, t0: performance.now(), err: null, running: true,
  };
  for (const k of KEYS) state.buf[k] = [];

  // Sample real grid columns from the canvas at mid-plot height.
  // Grid lines are neutral gray thin columns; curves are colored and excluded.
  function gridCols(u) {
    try {
      const cv = u.ctx && u.ctx.canvas;
      if (!cv) return null;
      const px = (window.uPlot && uPlot.pxRatio) || 1;
      const b = u.bbox;
      const y = Math.max(1, Math.min(cv.height - 2,
        Math.round((b.top / px + (b.height / px) * 0.5) * px)));
      const row = u.ctx.getImageData(0, y, cv.width, 1).data;
      const cols = [];
      const x0 = Math.round(b.left), x1 = Math.round(b.left + b.width);
      for (let x = x0; x < x1 && x < cv.width; x++) {
        const i = x * 4, r = row[i], g = row[i + 1], bl = row[i + 2];
        const mx = Math.max(r, g, bl), mn = Math.min(r, g, bl);
        if (mx - mn <= 12 && mn >= 40 && mn <= 180) cols.push(x);
      }
      return cols;
    } catch (e) { return null; }
  }

  function hostSize(u) {
    try {
      const h = u.root && u.root.parentElement;
      return h ? [h.clientWidth, h.clientHeight] : null;
    } catch (e) { return null; }
  }

  // Compare middle grid columns between two consecutive draws.
  function detect(rec, prev) {
    if (!prev) return null;
    let pixelStep = 0;
    if (Array.isArray(rec.cols) && Array.isArray(prev.cols)) {
      const a = prev.cols, b = rec.cols;
      const start = 2, end = Math.min(a.length, b.length) - 2;
      for (let k = start; k < end; k++) {
        const d = Math.abs(b[k] - a[k]);
        if (d > pixelStep) pixelStep = d;
      }
    }
    const vStep = (rec.vMin != null && prev.vMin != null)
      ? Math.abs(rec.vMin - prev.vMin) : 0;
    const vMaxStep = (rec.vMax != null && prev.vMax != null)
      ? Math.abs(rec.vMax - prev.vMax) : 0;
    // Classify the jump by beat phase so the report pins the code path immediately:
    //   setdata-t0   : prev was converged/tail, rec has no anim (decision-frame setData+setScale)
    //   l0-first     : rec just entered impact with small clock (L0 viewport rewind)
    //   converge     : rec phase null/anim cleared right after an impact run
    //   mid-l0       : inside impact with a step far larger than neighbors
    //   pure-scale   : scale jumped but phase looks steady (layout/rescale/external setScale)
    let kind = 'steady';
    const cp = rec.phase, pp = prev.phase;
    if (vStep > S_TH || vMaxStep > S_TH) {
      if (cp == null && (pp === 'impact' || pp === 'tail')) kind = 'converge/setData';
      else if (cp === 'impact' && (rec.clock == null || rec.clock < 40)) kind = 'decision-frame t0 rewind';
      else if (cp === 'impact') kind = 'mid-L0';
      else if (cp === 'tail') kind = 'tail phase';
      else kind = 'pure-scale (no anim; external setScale/rescale)';
    }
    const colsValid = Array.isArray(rec.cols) && Array.isArray(prev.cols)
      && rec.cols.length >= 5 && prev.cols.length >= 5;
    const bboxChanged = rec.bbox.join() !== prev.bbox.join();
    const canvasChanged = rec.canvas.join() !== prev.canvas.join();
    const hostChanged = (rec.host && prev.host)
      ? rec.host.join() !== prev.host.join() : false;
    const bad = pixelStep > PX_TH || vStep > S_TH || vMaxStep > S_TH
      || bboxChanged || canvasChanged || hostChanged;
    return { bad, kind, pixelStep, colsValid, vStep, vMaxStep,
      bboxChanged, canvasChanged, hostChanged };
  }

  function attach(u, key) {
    if (!u || !u.hooks || state.attached[key] === u) return;
    state.attached[key] = u;
    if (!u.__xgridSizePatched && typeof u.setSize === 'function') {
      const orig = u.setSize;
      u.setSize = function (...args) {
        try {
          state.sizeEvents.push({ key, t: +(performance.now() - state.t0).toFixed(1),
            args: JSON.parse(JSON.stringify(args)), bbox: (this.bbox && [this.bbox.left, this.bbox.top, this.bbox.width, this.bbox.height]) });
          if (state.sizeEvents.length > 500) state.sizeEvents.shift();
        } catch (e) { /* ignore */ }
        return orig.apply(this, args);
      };
      u.__xgridSizePatched = true;
    }
    u.hooks.draw = u.hooks.draw || [];
    u.hooks.draw.push((uu) => {
      if (!state.running) return;
      try {
        const st = uu._qbBeat || {};
        const a = st.anim || {};
        const sp = (uu.axes && uu.axes[0] && uu.axes[0]._splits) || [];
        const b = uu.bbox || {};
        const cv = uu.ctx && uu.ctx.canvas;
        const rec = {
          key, t: +(performance.now() - state.t0).toFixed(1),
          vMin: uu.scales && uu.scales.x && uu.scales.x.min,
          vMax: uu.scales && uu.scales.x && uu.scales.x.max,
          splits: Array.prototype.slice.call(sp),
          bbox: [b.left, b.top, b.width, b.height],
          canvas: cv ? [cv.width, cv.height] : null,
          host: hostSize(uu),
          cols: gridCols(uu),
          xs0: st.xs0, pad: uu._qbPad,
          len: uu.data && uu.data[0] ? uu.data[0].length : null,
          phase: a.phase || null, clock: a.clock != null ? +a.clock.toFixed(1) : null,
          needShift: a.needsShift, needTail: a.needsTail,
        };
        const buf = state.buf[key];
        const prev = buf[buf.length - 1];
        const d = detect(rec, prev);
        buf.push(rec);
        if (buf.length > BUF) buf.shift();
        if (d && d.bad && (state.cool[key] || 0) <= 0) {
          state.cool[key] = COOLDOWN;
          const i = buf.length - 1;
          const from = Math.max(0, i - KEEP), to = Math.min(buf.length, i + KEEP + 1);
          state.captures.push({
            key, t: rec.t, reason: d,
            frames: buf.slice(from, to).map((r) => JSON.parse(JSON.stringify(r))),
            sizeEvents: state.sizeEvents.filter((s) => s.key === key
              && s.t >= (buf[from] ? buf[from].t : 0) && s.t <= rec.t),
          });
          if (state.captures.length > CAP_MAX) state.captures.shift();
          console.warn('[xgrid-probe] CAPTURED', key, 't=' + rec.t,
            'kind=' + d.kind,
            'pixelStep=' + d.pixelStep.toFixed(1), 'colsValid=' + d.colsValid,
            'vStep=' + d.vStep.toFixed(3), 'vMaxStep=' + d.vMaxStep.toFixed(3),
            'phase=' + rec.phase, 'clock=' + rec.clock, 'xs0=' + rec.xs0,
            'pad=' + rec.pad, 'len=' + rec.len,
            'bbox=' + d.bboxChanged, 'canvas=' + d.canvasChanged, 'host=' + d.hostChanged);
        }
        if (state.cool[key] > 0) state.cool[key]--;
      } catch (e) { state.err = String(e) + ' @ ' + (e.stack || '').slice(0, 300); }
    });
  }

  function pump() {
    if (!state.running) return;
    for (const k of KEYS) attach(vm._qbCharts && vm._qbCharts[k], k);
    requestAnimationFrame(pump);
  }
  requestAnimationFrame(pump);

  window.xgridProbe = {
    report() {
      return {
        captured: state.captures.length,
        captures: state.captures,
        sizeEvents: state.sizeEvents,
        bufSizes: Object.keys(state.buf).reduce((o, k) => { o[k] = state.buf[k].length; return o; }, {}),
        err: state.err,
      };
    },
    summary() {
      return state.captures.map((c) => ({
        key: c.key, t: c.t, kind: c.reason.kind,
        pixelStep: +c.reason.pixelStep.toFixed(1), colsValid: c.reason.colsValid,
        vStep: +c.reason.vStep.toFixed(3), vMaxStep: +c.reason.vMaxStep.toFixed(3),
        phase: c.frames[c.frames.length - 1] && c.frames[c.frames.length - 1].phase,
        clock: c.frames[c.frames.length - 1] && c.frames[c.frames.length - 1].clock,
        xs0: c.frames[c.frames.length - 1] && c.frames[c.frames.length - 1].xs0,
        bbox: c.reason.bboxChanged, canvas: c.reason.canvasChanged, host: c.reason.hostChanged,
      }));
    },
    status() {
      return { running: state.running, captured: state.captures.length,
        bufSizes: Object.keys(state.buf).reduce((o, k) => { o[k] = state.buf[k].length; return o; }, {}),
        err: state.err };
    },
    stop() { state.running = false; console.log('[xgrid-probe] stopped'); },
  };
  console.log('[xgrid-probe] ready — watching torrent/global/group. '
    + 'Just watch the charts; jumps are captured automatically.');
  console.log('[xgrid-probe] after reproducing, run: copy(JSON.stringify(xgridProbe.report()))');
})();
