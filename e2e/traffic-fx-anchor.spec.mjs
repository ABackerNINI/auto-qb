// @ts-check
import { expect, test } from '@playwright/test';
import { SKINS } from './harness.mjs';
import { installRuntimeErrorGuard } from './lib/errors.mjs';
import { openApp } from './lib/gestures.mjs';
import { INST, readInst } from './lib/vm.mjs';
import { installRouteCleanup } from './lib/route-cleanup.mjs';

installRouteCleanup(test);   // 本文件全部用例收尾时卸载全部 route.fetch 桩(收尾竞态兜底, 合流接线)

/**
 * F2 常驻菱形锚的**真浏览器**守阵(plan 26-11-14-1313 §03 F2/D2, §04 S2b 行, R3) ——
 * CSS 合成器常驻层(.qb-fx-anchor x2 挂 .u-wrap)的三面真机验证:
 *
 *   A. 存在 + 持续旋转 + 与末点像素对齐 + 换肤重建不残留:
 *      · 存在: 图宿主内恰两枚 .qb-fx-anchor(up/dl 可寻址), 颜色 = tk 语义色内联
 *        (与 --today-up/--today-down 现值一致 —— I10)。
 *      · 持续旋转(D2 核心: 零 rAF/零重绘 —— 旋转走 CSS keyframes 420ms 合成器动画): 页面侧
 *        rAF 只**读** getComputedStyle().transform 采样, 不驱动任何动画 —— 采样窗内矩阵值
 *        >= 2 个不同 = 旋转真的在走; 全同 = keyframes 没接上或被 reduced-motion 关掉, 即红。
 *      · 像素对齐(R3 的 e2e 钉): 锚中心 == (判定线 x, 末点 y) —— 判定线 = bbox 右缘
 *        (与画布 tipX 静止位/模板 xJudge 同源), 末点 y = 双轨 shown 对当前 y 轴档的换算
 *        (与画布 yOf 同式)。几何全部在页面侧用同一把尺现算(uPlot pxRatio 换算), Node 侧
 *        只收差值断言 —— 容差 0.75px(亚像素取整余量, 与左移连续性探针同量级)。
 *      · 换肤重建不残留: 给旧锚打 data-probe 标记 -> documentElement 派发 autoqb:themechange
 *        (theme.js 换肤契约事件, 触发 _qbChartDestroy->_qbChartBuild 整图重建) -> 断言旧标记
 *        元素已不在 DOM、锚仍恰两枚且对齐(重建后新令牌新元件)。
 *
 *   B. 三档门(A2: 关总开关 / reduced-motion 不出现; calm 档退化圆点):
 *      · 总开关: 面板「启用动效」真手势翻关 -> 锚立即隐藏(门面 _qbFxCfgSync 即时生效, 不等
 *        下一拍); 翻开复显。
 *      · calm: 面板「配色」真手势切「克制」-> computed border-radius: 50%(模板 isCalm 同款),
 *        切回故障档即时回方块。
 *      · reduced-motion(P2: 隐藏, 不是静态方块): emulateMedia 在**应用加载前**设 reduce
 *        (qbInitialFxReduce 在 data() 取初值) -> cfg.on=false(JS 门)且 CSS 媒体查询同步隐藏
 *        (双保险同结果) —— 锚不出现。
 *
 * 桩口径(traffic-fx-frames 同款): 只翻 qb_traffic_enabled; /api/traffic/qb/torrent/* 造真
 * 契约形状的 60 桶帧, base 固定 + interval_s=30 —— 断言窗内无真拍(数据静止, 锚位稳定,
 * 对齐断言不被 L0/L1 收敛干扰)。
 */

const N = 60;

function makePayload(base, interval) {
  const points = new Array(N).fill(null);
  const totals = new Array(N).fill(null);
  for (let i = 0; i < N; i++) {
    const t = base + i * interval;
    points[i] = { t, dl: 2000, up: 1000 };
    totals[i] = { t, dl: 2000, up: 1000 };
  }
  return {
    points,
    totals,
    limits: [],
    meta: {
      window: '24h',
      interval_s: interval,
      source: 'qb',
      stale: false,
      server_started_at: base - 3600,
    },
  };
}

async function stubFlags(page) {
  await page.route('**/api/webui/flags', async (route) => {
    const json = await (await route.fetch()).json();
    return route.fulfill({ json: { ...json, qb_traffic_enabled: true } });
  });
}

/** base 固定(数据静止) + interval_s=30 -> 断言窗内无真拍(traffic-fx-frames B 用同款) */
async function stubTrafficStill(page) {
  const interval = 30;
  const b0 = Math.floor(Date.now() / 1000 / interval) * interval - (N - 1) * interval;
  await page.route('**/api/traffic/qb/torrent/*', (route) =>
    route.fulfill({ json: makePayload(b0, interval) }));
}

async function openTorrentTraffic(page) {
  await page.click('nav.tabs [data-view="torrents"]');
  await expect(page.locator('.torrent-row').first()).toBeVisible({ timeout: 15_000 });
  await page.dblclick('.torrent-row >> nth=0', { force: true });
  const drawer = page.locator('.drawer-dock > .drawer');
  await expect(drawer).toBeVisible({ timeout: 5_000 });
  /* 页签文本含 Alt+5 键帽(f081dd53 起), 定位用「流量 」前缀(traffic-gap-zones 同款) */
  await drawer.locator('.drawer-tabs button', { hasText: /^流量 / }).click();
  await expect(drawer.locator('.qb-chart-host canvas')).toBeVisible({ timeout: 15_000 });
  return drawer;
}

/** 语义色现值(--today-up/--today-down)的 computed rgb(与内联背景同格式), 页面侧现算 */
const TOKEN_COLORS_EXPR = `(() => {
  const probe = document.createElement('span');
  probe.style.display = 'none';
  document.body.appendChild(probe);
  const read = (name) => {
    probe.style.color = 'var(' + name + ')';
    return getComputedStyle(probe).color;
  };
  const out = { up: read('--today-up'), down: read('--today-down') };
  probe.remove();
  return out;
})()`;

/** 锚面快照: 存在性/颜色/圆角/显隐/中心位(相对 .u-wrap)/期望位(判定线 x + 末点 y, 同尺现算) */
const ANCHOR_SNAP_EXPR = `(() => {
  const vm = ${INST};
  const u = vm._qbCharts && vm._qbCharts.torrent;
  if (!u || !u._qbFxAnchors || !u.bbox) return null;
  const px = (typeof uPlot !== 'undefined' && uPlot.pxRatio) || 1;
  const wrap = u.root.querySelector('.u-wrap');
  if (!wrap) return null;
  const wr = wrap.getBoundingClientRect();
  const L = u.bbox.left / px;
  const T = u.bbox.top / px;
  const W = u.bbox.width / px;
  const H = u.bbox.height / px;
  const st = u._qbBeat;
  const yMax = u.scales.y && u.scales.y.max > 0 ? u.scales.y.max : 1;
  const of = (k) => {
    const tr = st && st.tracks && st.tracks[k];
    const el = u._qbFxAnchors[k];
    if (!el) return null;
    const r = el.getBoundingClientRect();
    const shown = tr && tr.shown != null ? tr.shown : 0;
    return {
      cls: el.className,
      bg: getComputedStyle(el).backgroundColor,
      radius: getComputedStyle(el).borderRadius,
      display: getComputedStyle(el).display,
      act: { x: r.left + r.width / 2 - wr.left, y: r.top + r.height / 2 - wr.top },
      exp: { x: L + W, y: T + H * (1 - Math.min(shown, yMax) / yMax) },
    };
  };
  return {
    wrapChildren: wrap.querySelectorAll('.qb-fx-anchor').length,
    staleProbe: document.querySelectorAll('[data-probe="old-anchor"]').length,
    up: of('up'), dl: of('dl'),
  };
})()`;

async function anchorSnap(page) {
  return page.evaluate(ANCHOR_SNAP_EXPR);
}

/** 轮询锚就绪后取快照(建图/锚层未就绪时 evaluate 返 null) */
async function awaitAnchorReady(page) {
  await expect.poll(async () => {
    const s = await anchorSnap(page);
    return s && s.up && s.dl ? 1 : 0;
  }, { message: '锚快照取不到(建图/锚层未就绪)', timeout: 10_000 }).toBe(1);
  return anchorSnap(page);
}

test.describe('F2 常驻菱形锚 · 存在/旋转/对齐/换肤不残留(plan 26-11-14-1313 S2b)', () => {
  installRuntimeErrorGuard(test);

  for (const skin of SKINS) {
    test(`[${skin}] 恰两枚语义色锚, 420ms 合成器旋转持续在走, 与末点像素对齐, 换肤重建零残留 @fast`, async ({ page }) => {
      await stubFlags(page);
      await stubTrafficStill(page);
      await openApp(page, skin);
      const drawer = await openTorrentTraffic(page);
      const anchors = drawer.locator('.qb-chart-host .qb-fx-anchor');
      await expect(anchors).toHaveCount(2);

      /* 存在: 恰两枚(挂 .u-wrap), 可见, 颜色 = tk 语义色内联(I10) */
      let snap = await awaitAnchorReady(page);
      expect(snap.wrapChildren, '挂 .u-wrap 的 .qb-fx-anchor 必须恰两枚(F2: 两枚 DOM 方块)').toBe(2);
      const tokens = await page.evaluate(TOKEN_COLORS_EXPR);
      expect([snap.up.bg, snap.dl.bg], '锚颜色 = tk 语义色内联(上/下载各一 —— I10)')
        .toEqual([tokens.up, tokens.down]);
      expect(snap.up.cls, 'up 锚类名可寻址').toContain('qb-fx-anchor-up');
      expect(snap.dl.cls, 'dl 锚类名可寻址').toContain('qb-fx-anchor-dl');

      /* 像素对齐(R3 的 e2e 钉): 锚中心 == (判定线 x, 末点 y), 容差 0.75px 亚像素余量 */
      for (const k of ['up', 'dl']) {
        const s = snap[k];
        expect(Math.abs(s.act.x - s.exp.x), `${k} 锚中心 x ${s.act.x.toFixed(2)} 应 = 判定线 x ${s.exp.x.toFixed(2)}(bbox 右缘)`)
          .toBeLessThanOrEqual(0.75);
        expect(Math.abs(s.act.y - s.exp.y), `${k} 锚中心 y ${s.act.y.toFixed(2)} 应 = 末点 y ${s.exp.y.toFixed(2)}(yOf(shown) 同式)`)
          .toBeLessThanOrEqual(0.75);
      }

      /* 持续旋转(D2: CSS keyframes 合成器动画; 页面 rAF 只读不驱动): 700ms 窗(>420ms 周期)
       * 内 transform 矩阵 >= 2 个不同值; 全同 = keyframes 没接上, 即红 */
      await page.evaluate(`(() => {
        const vm = ${INST};
        const u = vm._qbCharts.torrent;
        window.__ar = { mats: new Set(), done: false };
        const t0 = performance.now();
        const tick = () => {
          const ar = window.__ar;
          if (ar.done) return;
          const el = u._qbFxAnchors && u._qbFxAnchors.up;
          if (el && el.isConnected) ar.mats.add(getComputedStyle(el).transform);
          if (performance.now() - t0 >= 700) { ar.done = true; return; }
          requestAnimationFrame(tick);
        };
        requestAnimationFrame(tick);
      })()`);
      await expect.poll(() => readInst(page, 'window.__ar && window.__ar.done === true'), {
        message: '旋转采样窗未收口(700ms)',
        timeout: 5_000,
      }).toBe(true);
      const matCount = await page.evaluate(() => window.__ar.mats.size);
      expect(matCount, `700ms 采样窗内 transform 矩阵应 >= 2 个不同值(实测 ${matCount}) —— `
        + '旋转是 CSS keyframes 420ms 合成器动画(D2), 停转/未接线即红').toBeGreaterThanOrEqual(2);

      /* 换肤重建不残留: 旧锚打标记 -> 派发 theme.js 契约事件(整图 destroy->build) ->
       * 旧标记元素已拆、锚仍恰两枚且对齐(新令牌新元件) */
      await page.evaluate(`(() => {
        const vm = ${INST};
        const u = vm._qbCharts.torrent;
        u._qbFxAnchors.up.setAttribute('data-probe', 'old-anchor');
        u._qbFxAnchors.dl.setAttribute('data-probe', 'old-anchor');
        return true;
      })()`);
      await page.evaluate(`document.documentElement.dispatchEvent(new CustomEvent('autoqb:themechange'))`);
      await expect(drawer.locator('.qb-chart-host canvas')).toBeVisible({ timeout: 15_000 });
      await expect(anchors).toHaveCount(2);
      await expect.poll(async () => {
        const s = await anchorSnap(page);
        return s ? s.staleProbe : -1;
      }, { message: '换肤重建后旧锚残留(data-probe=old-anchor 仍在 DOM)' }).toBe(0);
      snap = await awaitAnchorReady(page);
      expect(snap.wrapChildren, '重建后锚仍恰两枚(幂等建, 不翻倍)').toBe(2);
      for (const k of ['up', 'dl']) {
        const s = snap[k];
        expect(Math.abs(s.act.x - s.exp.x), `重建后 ${k} 锚 x 仍对齐判定线`).toBeLessThanOrEqual(0.75);
        expect(Math.abs(s.act.y - s.exp.y), `重建后 ${k} 锚 y 仍对齐末点`).toBeLessThanOrEqual(0.75);
      }
    });
  }
});

test.describe('F2 常驻菱形锚 · 三档门(A2: 总开关/reduced-motion 隐藏, calm 圆点)', () => {
  installRuntimeErrorGuard(test);

  for (const skin of SKINS) {
    test(`[${skin}] 总开关关->立即隐藏/开->复显; 配色 calm->圆点/glitch->方块 @fast`, async ({ page }) => {
      await stubFlags(page);
      await stubTrafficStill(page);
      await openApp(page, skin);
      const drawer = await openTorrentTraffic(page);
      const anchors = drawer.locator('.qb-chart-host .qb-fx-anchor');
      await expect(anchors).toHaveCount(2);
      await awaitAnchorReady(page);
      const displayOf = async () => {
        const s = await anchorSnap(page);
        return s && s.up ? s.up.display : 'missing';
      };
      await expect.poll(displayOf, { message: '锚未显形(门全开应 display != none)' }).not.toBe('none');

      /* 总开关: 面板真手势翻关 -> 锚立即隐藏(_qbFxCfgSync 门面, 不等下一拍); 翻开复显 */
      await drawer.locator('.qb-chart-host').click({ button: 'right' });
      const panel = page.locator('.fx-panel');
      await expect(panel).toBeVisible({ timeout: 5_000 });
      await panel.locator('.fx-master input[type="checkbox"]').uncheck();
      await expect.poll(displayOf, { message: '总开关翻关后锚仍可见(门面未即时生效 —— F2 门=cfg.on)' })
        .toBe('none');
      await panel.locator('.fx-master input[type="checkbox"]').check();
      await expect.poll(displayOf, { message: '总开关翻开后锚未复显' }).not.toBe('none');

      /* calm 档退化圆点(模板 isCalm 同款): computed border-radius 50%; 切回故障档即时回方块 */
      const radiusOf = async () => {
        const s = await anchorSnap(page);
        return s && s.up ? s.up.radius : 'missing';
      };
      await panel.locator('.fx-row', { hasText: '配色' }).locator('select').selectOption('calm');
      await expect.poll(radiusOf, { message: 'calm 档锚未退化圆点(border-radius 应 50%)' }).toBe('50%');
      await panel.locator('.fx-row', { hasText: '配色' }).locator('select').selectOption('glitch');
      await expect.poll(radiusOf, { message: 'glitch 档锚应回到方块(border-radius 0px)' }).toBe('0px');
      await panel.locator('.fx-x').click();
    });

    test(`[${skin}] reduced-motion: 锚不出现(P2 隐藏 —— JS 门 cfg.on 与 CSS 媒体查询双保险) @fast`, async ({ page }) => {
      /* emulateMedia 必须在应用加载前(qbInitialFxReduce 在 data() 取初值) */
      await page.emulateMedia({ reducedMotion: 'reduce' });
      await stubFlags(page);
      await stubTrafficStill(page);
      await openApp(page, skin);
      const drawer = await openTorrentTraffic(page);
      const anchors = drawer.locator('.qb-chart-host .qb-fx-anchor');
      await expect(anchors).toHaveCount(2);
      const visible = await anchors.evaluateAll((els) => els.map((e) => getComputedStyle(e).display));
      expect(visible, 'reduced-motion 下锚必须隐藏(P2: 隐藏, 不是静态方块)').toEqual(['none', 'none']);
      expect(await readInst(page, 'window.AQB_FX_CFG && window.AQB_FX_CFG.on'), 'JS 门 on 必须为 false(reduce 分量)')
        .toBe(false);
    });
  }
});
