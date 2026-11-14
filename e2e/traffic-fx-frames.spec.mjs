// @ts-check
import { expect, test } from '@playwright/test';
import { SKINS } from './harness.mjs';
import { installRuntimeErrorGuard } from './lib/errors.mjs';
import { openApp } from './lib/gestures.mjs';
import { INST, readInst } from './lib/vm.mjs';
import { installRouteCleanup } from './lib/route-cleanup.mjs';

installRouteCleanup(test);   // 本文件全部用例收尾时卸载全部 route.fetch 桩(收尾竞态兜底, 合流接线)

/**
 * 节拍动效的**帧级采样探针**(plan 26-11-12-1139 §10 建议新增里判给 P8 的画布/真机面;
 * P7 覆盖矩阵 G1/G2/G5 三条的 e2e 端) —— 对应两条用例:
 *
 *   A. 左移连续性(G2/R1): 真窗口每拍滚动一格时, 相邻两拍**边界**的视口位移 <= 1px(不回跳),
 *      拍内视口平滑滑入一格(smooth 档真播)、每拍墙钟 <= animEnd + 采样余量(G1「真值落地
 *      <= 1s」的真机面)、data/xs0 全程冻结且逐拍右移(「L0 不动 data、只改视口」)。
 *      机理解释: 拍 N 收敛在真窗 [T-W, T], 拍 N+1 判定帧把视口摆回 [T-W, T](偏置 = 新真窗
 *      减 dx0), 数学上边界两值恒等 —— 断言 <= 1px 留的是浮点/时序余量; 若有人把偏置摆错
 *      (回跳/跳两格/瞬时落地), 边界位移立刻变成一格宽(数十 px), 必红。
 *
 *   B. 预览拍帧级探针(§05.9 面板拍 + §10 面板探针第 3 条/背景静态 G5): 预览期间逐帧断言
 *      u.data[0](xs)与 u.scales.x.min/max 不变、dx ≡ 0; 背景两点(绘图区中央 / 右缘带)
 *      连拍逐帧 alpha 恒 0 且两点相等(G5「背景 RGB 恒定且两点相等」的画布采样面 —— 画布
 *      未落墨的像素恒为全透明, 装饰描边/曲线/网格的像素 alpha > 0, 所以「alpha 恒 0」
 *      等价于「这两点整轮测试没有任何一笔铺底/呼吸」); 末帧还原真值(假值不留痕);
 *      粒子清单合计 <= 32。
 *
 * 为什么探针点敢选「右缘带」而装饰(束/环/粒子/回声)就在右缘活动: 装饰的空间范围由 I9 常量
 * 决定 —— 环 rMax <= 29px、粒子行程 <= 1.6x29 ≈ 47px、尾光沿末段 6 桶(约 6 格宽)、回声
 * span 用面板下拉钉到 100px; 探针点 2 取 R-130, 与最近装饰行程至少隔 30px。扫描一次透明带
 * 避开曲线/网格的静态像素; 预览期间窗口/轴全程冻结(无 setScale x、y 钉死), 几何不漂移,
 * 静态扫描结果对整窗有效 —— 这是选「预览拍」做像素探针的可行性根据。
 * 断言口径说明: 电池已钉「fx/束体域 fillRect 恰 1 处且 1px 级」(铺底面); 本探针补的是
 * 真渲染面 —— 任何整块铺底/背景呼吸会画到**所有**像素, 探针点虽在装饰行程之外也必红;
 * 装饰描边本身落在探针行程之外是几何常量决定的(见上), 不是断言放水。
 *
 * 采样纪律(对照 drawer-switch-no-flash 的量具模式): 采样器装在页面 rAF 上(Node 侧装不上
 * —— D4 第 2 类 evaluate: vm 内部时序探针), 结束条件是页面侧状态(拍段计数/预览令牌翻转),
 * Node 侧只 expect.poll 这个旗标 —— 零 waitForTimeout、零固定睡等。
 * 容器软件渲染的 rAF 帧距比真机大一个量级: 涉及墙钟的断言(拍时长)用 animEnd + 900ms 余量,
 * 帧数下限压到 3/5/10 —— 帧距变大只减少采样密度, 不改变逐帧不变性断言的语义。
 *
 * 量具裁剪留档(§10 扫描束探针不进 e2e): 束体「逐帧指令 <= 23 / 整块 fillRect = 0 / 回声
 * 行程与硬停」在电池 S1-S8 里用记账 ctx 真跑覆盖; e2e 真渲染下没有指令钩子可挂, 要逐帧数
 * 指令就得给生产热路径包 monkey-patch —— 量具改生产, 违反探针纪律, 故该面按可行性裁剪,
 * e2e 只保留画布像素面(本文件 B 的背景两点 + 左移连续性)。
 *
 * 同批留档(覆盖矩阵 G3/G6 两行「-> P8」的裁决): 曲线像素对比度(G3)与「任一帧 strokeStyle
 * 恒语义色」(G6)也不进 e2e —— 电池级等价 = 曲线描边恒 uPlot 系列原生(I11 黑名单钉: fx 域
 * 零触碰 series/legend/cursor) + 层序钉(drawAxes 整段先于系列原生, I6), 像素面拿不到确定性
 * 基准(描边色走四皮肤令牌现读, 随皮肤/明暗主题变; 抗锯齿混色逐帧噪), 强比对即 flaky。
 *
 * 桩口径(traffic-gap-zones 同款): 只翻 qb_traffic_enabled; /api/traffic/qb/torrent/* 造
 * 真契约形状的 60 桶帧。A 用 interval_s=2(轮询 2s 一拍 = beat 800ms, 三拍 ~7s 采完)且
 * **每次请求恰推进一格**(计数器递增 base, 与墙钟解耦 —— roll 判据 dx0 <= 2 格恒成立);
 * 值恒定 -> L1 静默(needsTail=false), 拍只剩 L0 视口左移, 边界断言不被数值收敛干扰。
 * B 用 interval_s=30(轮询 30s 一拍, 断言窗内无真拍来抢预览)且 base 固定(数据静止)。
 */

const N = 60;

/** 造一帧 payload; advancing 时 base 由调用方按请求序推进一格 */
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
      window: '24h',                 // 前端不校验 points 长度 vs window(traffic-gap-zones 同款偏差)
      interval_s: interval,
      source: 'qb',
      stale: false,
      server_started_at: base - 3600,  // 远在链末前 -> 接缝提示出 null, 不干扰
    },
  };
}

async function stubFlags(page) {
  await page.route('**/api/webui/flags', async (route) => {
    const json = await (await route.fetch()).json();
    return route.fulfill({ json: { ...json, qb_traffic_enabled: true } });
  });
}

/** A 用: 每次请求恰推进一格(计数器解耦墙钟), interval_s=2 -> 轮询 2s/拍 800ms */
async function stubTrafficAdvancing(page) {
  const interval = 2;
  const b0 = Math.floor(Date.now() / 1000 / interval) * interval - (N - 1) * interval;
  let calls = 0;
  await page.route('**/api/traffic/qb/torrent/*', (route) =>
    route.fulfill({ json: makePayload(b0 + (calls++) * interval, interval) }));
  return interval;
}

/** B 用: base 固定(数据静止), interval_s=30 -> 断言窗内无真拍 */
async function stubTrafficStill(page) {
  const interval = 30;
  const b0 = Math.floor(Date.now() / 1000 / interval) * interval - (N - 1) * interval;
  await page.route('**/api/traffic/qb/torrent/*', (route) =>
    route.fulfill({ json: makePayload(b0, interval) }));
}

/** 打开种子流量页签(不点窗口档: A 靠 interval_s=2 出快拍, B 靠 interval_s=30 隔离真拍) */
async function openTorrentTraffic(page) {
  await page.click('nav.tabs [data-view="torrents"]');
  await expect(page.locator('.torrent-row').first()).toBeVisible({ timeout: 15_000 });
  await page.dblclick('.torrent-row >> nth=0', { force: true });
  const drawer = page.locator('.drawer-dock > .drawer');
  await expect(drawer).toBeVisible({ timeout: 5_000 });
  await drawer.locator('.drawer-tabs button', { hasText: /^流量$/ }).click();
  await expect(drawer.locator('.qb-chart-host canvas')).toBeVisible({ timeout: 15_000 });
  return drawer;
}

/**
 * 把轮询周期重排到 interval_s 档(真实 UI 手势: 切走页签再切回流量)。
 * 为什么要这一步: drawer_store._loadDrawerTab('traffic') 的次序是 _qbLoad(异步)后立刻
 * _qbPollStart —— 起拍时 meta 还没落袋, _qbPollMs 读不到 interval_s 回落 30s fallback,
 * arm() 要等第一拍烧完才重读 ms()。切走页签再切回, _qbPollStart 自带先停后起且此刻数据
 * 已在, 新周期 = interval_s x 1000(A 档 2s) —— 拍在 2s 节奏上出, 用例不用陪等首轮 30s。
 */
async function rearmTrafficPoll(page, drawer) {
  await drawer.locator('.drawer-tabs button', { hasText: /^常规$/ }).click();
  await drawer.locator('.drawer-tabs button', { hasText: /^流量$/ }).click();
  await expect(drawer.locator('.qb-chart-host canvas')).toBeVisible({ timeout: 15_000 });
  await expect.poll(() => readInst(page, 'vm._qbPollMs("torrent")'), {
    message: '轮询周期未重排到 interval_s 档(数据未落袋时的 fallback 30s 还在)', timeout: 15_000,
  }).toBeLessThanOrEqual(2100);
}

/** 图记录快照(xs 界值/尾值/x 尺) —— 预览前后各取一次, 断言「真值零改写 + 末帧还原」 */
const SNAP_EXPR = `(() => {
  const vm = ${INST};
  const u = vm._qbCharts && vm._qbCharts.torrent;
  if (!u || !u.data || !u.data.length) return null;
  const xs = u.data[0];
  const n = xs.length;
  let cks = 0;
  for (let i = 0; i < n; i++) cks += xs[i];
  return { xsLen: n, xs0: xs[0], xsN: xs[n - 1], xsCks: cks,
    tailUp: u.data[1] ? u.data[1][n - 1] : null, tailDl: u.data[2] ? u.data[2][n - 1] : null,
    min: u.scales.x.min, max: u.scales.x.max };
})()`;

async function readSnapshot(page) {
  const snap = await page.evaluate(SNAP_EXPR);
  if (!snap) throw new Error('图记录取不到(vm._qbCharts.torrent 未建图)');
  return snap;
}

/* ============================================================================ */

test.describe('节拍动效 · 左移连续性(G2/R1 帧级探针)', () => {
  installRuntimeErrorGuard(test);

  for (const skin of SKINS) {
    test(`[${skin}] 相邻两拍边界视口位移 <= 1px, 拍内平滑滑入一格, 真值落地 <= animEnd+余量 @fast`, async ({ page }) => {
      await stubFlags(page);
      await stubTrafficAdvancing(page);
      await openApp(page, skin);
      const drawer = await openTorrentTraffic(page);
      await rearmTrafficPoll(page, drawer);

      /* 页面侧 rAF 采样器: 记录每帧的 x 尺/数据界值/拍状态; 第 3 拍起点出现且动画归位即停
       * (三个拍段 = 三条边界, 每条边界都有前值可对照)。零固定睡等 —— Node 侧只 poll 旗标。 */
      await page.evaluate(`(() => {
        const vm = ${INST};
        window.__fs = { frames: [], starts: 0, prevAnim: false, done: false };
        const tick = () => {
          const fs = window.__fs;
          if (fs.done) return;
          const u = vm._qbCharts && vm._qbCharts.torrent;
          if (u && u._qbBeat && u.data && u.data.length) {
            const a = u._qbBeat.anim;
            const xs = u.data[0];
            const n = xs.length;
            fs.frames.push({
              t: performance.now(),
              anim: !!a,
              dx0: a ? a.dx0 : null,
              animEnd: a && a.tl ? a.tl.animEndMs : null,
              min: u.scales.x.min,
              max: u.scales.x.max,
              w: u.bbox.width,
              dpr: (typeof uPlot !== 'undefined' && uPlot.pxRatio) || 1,
              xsLen: n, xs0: xs[0], xsN: xs[n - 1],
              tailUp: u.data[1] ? u.data[1][n - 1] : null,
              tailDl: u.data[2] ? u.data[2][n - 1] : null,
            });
            if (a && !fs.prevAnim) fs.starts++;
            fs.prevAnim = !!a;
            if (fs.starts >= 3 && !a) fs.done = true;
          }
          requestAnimationFrame(tick);
        };
        requestAnimationFrame(tick);
      })()`);
      await expect.poll(() => readInst(page, 'window.__fs === undefined ? false : window.__fs.done === true'), {
        message: '三个拍段未在预算内采满(轮询 2s 一拍, 三拍约 7s; 超时=轮询/节拍链路断了)',
        timeout: 30_000,
      }).toBe(true);
      const frames = await page.evaluate(() => window.__fs.frames);

      /* 连续 anim=true 的帧为一段拍; 段数 >= 3 */
      const runs = [];
      let cur = null;
      for (const f of frames) {
        if (f.anim) {
          if (!cur) { cur = []; runs.push(cur); }
          cur.push(f);
        } else {
          cur = null;
        }
      }
      expect(runs.length, '采样窗内应记录到 >= 3 个拍段(轮询推进的窗口滚动拍)').toBeGreaterThanOrEqual(3);

      for (let i = 0; i < runs.length; i++) {
        const run = runs[i];
        const idx0 = frames.indexOf(run[0]);
        expect(idx0, '拍段前必须有前帧(边界对照值)').toBeGreaterThanOrEqual(1);
        const prev = frames[idx0 - 1];

        /* 边界连续性(G2 本体): 新拍判定帧把视口摆回旧位, 与上一拍收敛位置差 <= 1px。
         * px 换算: plotCssWidth = bbox.width / pxRatio(bbox 是设备像素); 用边界帧自己的
         * 尺度换算(拍前后窗宽同格数, 尺度不跳)。 */
        const pxPerUnit = (run[0].w / run[0].dpr) / (run[0].max - run[0].min);
        const dpx = Math.abs(run[0].min - prev.min) * pxPerUnit;
        expect(dpx, `第 ${i + 1} 拍边界视口位移 ${dpx.toFixed(3)}px 必须 <= 1px(相邻两拍边界曲线不回跳不跳格)` +
          ` [prev.min=${prev.min} -> first.min=${run[0].min}]`).toBeLessThanOrEqual(1);

        /* 拍内平滑(G2 三档口径的 smooth 档): 视口滑过约一格宽, 且逐帧单调不回跳 */
        const cellPx = (run[0].w / run[0].dpr) / run[0].xsLen;
        const glidePx = (run[run.length - 1].min - run[0].min) * pxPerUnit;
        expect(glidePx, `第 ${i + 1} 拍视口行程 ${glidePx.toFixed(2)}px 应约一格(>= ${ (cellPx * 0.5).toFixed(2) }px) —— ` +
          'instant 化(不播 L0)即红').toBeGreaterThanOrEqual(cellPx * 0.5);
        expect(run.length, `第 ${i + 1} 拍应有 >= 3 个采样帧(动画经多帧推进, 非一次跳变)`).toBeGreaterThanOrEqual(3);
        for (let j = 1; j < run.length; j++) {
          expect(run[j].min, `第 ${i + 1} 拍第 ${j} 帧视口单调(不回跳)`).toBeGreaterThanOrEqual(run[j - 1].min - 1e-6);
        }
        expect(run[0].dx0, `第 ${i + 1} 拍 dx0 必须为正(窗口滚动一格驱动)`).toBeGreaterThan(0);

        /* G1 真值落地时限: 拍墙钟 <= animEnd + 900ms(容器软件渲染 rAF 帧距大, dt 钳 100ms
         * 的吞帧机制会拉长墙钟 —— 余量按掉帧形态给, 收紧到 animEnd 是电池面的事) */
        const dur = run[run.length - 1].t - run[0].t;
        expect(dur, `第 ${i + 1} 拍墙钟 ${Math.round(dur)}ms 必须 <= animEnd(${run[0].animEnd}ms)+900ms`).toBeLessThanOrEqual(run[0].animEnd + 900);

        /* 拍内数据冻结: 窗口列与尾值一帧不动(L0 只改视口) */
        for (const f of run) {
          expect(f.xs0, '拍内 xs[0] 冻结(L0 不动 data)').toBe(run[0].xs0);
          expect(f.xsN, '拍内 xs 末值冻结').toBe(run[0].xsN);
        }
      }

      /* 全窗数据不变量: 点数/尾值恒定(L1 静默: 恒定数据零收敛), 拍间 xs[0] 逐拍右移 */
      const f0 = frames[0];
      for (const f of frames) {
        expect(f.xsLen, '点数恒定(无重定标)').toBe(f0.xsLen);
        expect(f.tailUp, '上传尾值恒定(恒定数据零装饰零收敛)').toBe(f0.tailUp);
        expect(f.tailDl, '下载尾值恒定').toBe(f0.tailDl);
      }
      for (let i = 1; i < runs.length; i++) {
        expect(runs[i][0].xs0, '相邻两拍 xs[0] 必须右移(窗口每拍滚动一格)').toBeGreaterThan(runs[i - 1][0].xs0);
      }
    });
  }
});

test.describe('节拍动效 · 预览拍帧级探针(§05.9 面板拍 + G5 背景静态)', () => {
  installRuntimeErrorGuard(test);

  for (const skin of SKINS) {
    test(`[${skin}] 预览期间 xs/x 尺逐帧不变 + dx=0; 背景两点 alpha 恒 0 且相等; 末帧还原真值 @fast`, async ({ page }) => {
      await stubFlags(page);
      await stubTrafficStill(page);
      await openApp(page, skin);
      const drawer = await openTorrentTraffic(page);

      /* 开面板 -> 高级折叠 -> 把竖扫回声行程钉到 100px(真手势改字段; 回声 span 100 让
       * 探针点 R-130 站在装饰行程之外) */
      await drawer.locator('.qb-chart-host').click({ button: 'right' });
      const panel = page.locator('.fx-panel');
      await expect(panel).toBeVisible({ timeout: 5_000 });
      await panel.locator('.fx-adv summary').click();
      await panel.locator('.fx-row', { hasText: '竖扫回声行程' }).locator('select').selectOption('100');
      await expect.poll(() => readInst(page, 'window.AQB_FX_CFG && window.AQB_FX_CFG.echoSpan'), {
        message: 'echoSpan=100 未贯通 CFG(预览探针的装饰范围前提)', timeout: 5_000,
      }).toBe('100');

      /* 探针点扫描(D4 第 2 类: vm 内部几何探针): 两列各找一段 >= 8px 的透明带取中点。
       * 列 1 = 绘图区中央; 列 2 = 右缘带 R-130(环 <=29px/粒子 <=47px/尾光 6 格/回声 100px
       * 的行程之外)。扫描天然避开曲线/网格的静态像素; 预览期间轴冻结, 几何不漂移。 */
      const probe = await page.evaluate(`(() => {
        const vm = ${INST};
        const u = vm._qbCharts && vm._qbCharts.torrent;
        if (!u || !u.ctx || !u.bbox) return { error: 'unbuilt' };
        const px = (typeof uPlot !== 'undefined' && uPlot.pxRatio) || 1;
        const L = u.bbox.left / px;
        const T = u.bbox.top / px;
        const W = u.bbox.width / px;
        const H = u.bbox.height / px;
        const R = L + W;
        const devH = u.ctx.canvas.height;
        const pick = (x, tag) => {
          const col = u.ctx.getImageData(Math.round(x * px), 0, 1, devH).data;
          const lo = Math.round((T + 24) * px);
          const hi = Math.round((T + H - 24) * px);
          let best = null;
          let run = 0;
          let runStart = -1;
          for (let dy = lo; dy <= hi; dy++) {
            if (col[dy * 4 + 3] === 0) {
              if (run === 0) runStart = dy;
              run++;
              if (!best || run > best.run) best = { run, start: runStart };
            } else {
              run = 0;
            }
          }
          if (!best || best.run < 8) return tag + ' 列找不到 >= 8px 透明带(扫描区被占满?)';
          return { x, y: (best.start + Math.floor(best.run / 2)) / px };
        };
        const p1 = pick(L + W * 0.45, 'center');
        if (typeof p1 === 'string') return { error: p1 };
        const p2 = pick(R - 130, 'right');
        if (typeof p2 === 'string') return { error: p2 };
        return { p1, p2, R };
      })()`);
      if (!probe || probe.error) {
        throw new Error('探针点扫描失败: ' + ((probe && probe.error) || 'evaluate 返回空'));
      }

      /* 装扫描器前取真值快照(预览前), 装完后点「预览一拍」 */
      const snap = await readSnapshot(page);
      await page.evaluate(`((p1, p2) => {
        const vm = ${INST};
        const u = vm._qbCharts.torrent;
        const px = (typeof uPlot !== 'undefined' && uPlot.pxRatio) || 1;
        const cks0 = () => {
          let s = 0;
          const xs = u.data[0];
          for (let i = 0; i < xs.length; i++) s += xs[i];
          return s;
        };
        window.__pf = { frames: [], done: false, sawAnim: false,
          snap: { min: u.scales.x.min, max: u.scales.x.max, xsCks: cks0() }, p1, p2, dpr: px };
        const tick = () => {
          const pf = window.__pf;
          if (pf.done) return;
          const u2 = vm._qbCharts && vm._qbCharts.torrent;
          if (u2 && u2.ctx && u2.data && u2.data.length) {
            const a = u2._qbBeat && u2._qbBeat.anim;
            let cks = 0;
            const xs = u2.data[0];
            for (let i = 0; i < xs.length; i++) cks += xs[i];
            const g1 = u2.ctx.getImageData(Math.round(pf.p1.x * pf.dpr), Math.round(pf.p1.y * pf.dpr), 1, 1).data;
            const g2 = u2.ctx.getImageData(Math.round(pf.p2.x * pf.dpr), Math.round(pf.p2.y * pf.dpr), 1, 1).data;
            const fx = a && a.fx ? a.fx : null;
            const parts = fx
              ? (fx.specs.up ? fx.specs.up.length : 0) + (fx.specs.dl ? fx.specs.dl.length : 0)
                + (fx.specs.merge ? fx.specs.merge.length : 0)
              : 0;
            pf.frames.push({
              anim: !!a,
              isPreview: !!(a && a.preview !== undefined),
              dx0: a ? a.dx0 : null,
              min: u2.scales.x.min,
              max: u2.scales.x.max,
              xsCks: cks,
              parts,
              g1: [g1[0], g1[1], g1[2], g1[3]],
              g2: [g2[0], g2[1], g2[2], g2[3]],
            });
            if (a && a.preview !== undefined) pf.sawAnim = true;
            if (pf.sawAnim && !a) pf.done = true;
          }
          requestAnimationFrame(tick);
        };
        requestAnimationFrame(tick);
      })(${JSON.stringify(probe.p1)}, ${JSON.stringify(probe.p2)})`);

      await panel.locator('button', { hasText: '预览一拍' }).click();
      await expect.poll(() => readInst(page, 'window.__pf === undefined ? false : window.__pf.done === true'), {
        message: '预览拍未在预算内收场(预览无 tail 相位, 窗 = animEnd 600ms 档; 超时=预览链路断了或假 Δ 零变化)',
        timeout: 15_000,
      }).toBe(true);
      const frames = await page.evaluate(() => window.__pf.frames);

      /* 帧数与预览在场(S4-b 评审 major2 重标): 预览拍**没有 tail 相位** —— _qbBeatFrame 在
       * clock >= tl.animEndMs 时对 preview 直走 _qbPreviewEnd 收口(tail 相位只属于真拍
       * _qbBeatConverge), 采样窗 = animEnd = max(shiftRatio,0.6) x beat = 600ms 档。
       * 下限按两侧实测帧距落数(2026-11-14 诊断跑实测: testbed anim 帧 38 / Windows 37-38,
       * 600ms 窗两侧都 ≈16ms/帧全速 —— 本量具是轻 canvas, 不是 41.7m/344 例那种重渲染面;
       * 容器慢是重负载 spec 的形态差异): anim 帧 >= 3 证明「预览真的跑了且被逐帧采样」,
       * 全帧 >= 3 再证采样器跨过了「动画在场 -> 归位」边界(done 条件的结构性结果);
       * 下限 3 只吃「预览在途 rAF 完全饿死」的病理形态, 常规负载余量一个量级。
       * 逐帧不变性断言(min/max/xsCks/背景两点)与帧数无关 —— 帧距变大只降低采样密度。 */
      expect(frames.length, '采样窗应有 >= 3 帧(采样器须跨过预览收场边界)').toBeGreaterThanOrEqual(3);
      const animFrames = frames.filter((f) => f.anim);
      expect(animFrames.length, '预览动画必须有采样帧(预览一拍真的跑了; 600ms 窗在慢机约 3-4 帧)')
        .toBeGreaterThanOrEqual(3);

      /* 全帧不变量: xs 列与 x 尺逐帧不变(§05.9: 预览不动数据面) */
      for (const f of frames) {
        expect(f.min, 'u.scales.x.min 逐帧不变(预览零 setScale x)').toBe(snap.min);
        expect(f.max, 'u.scales.x.max 逐帧不变').toBe(snap.max);
        expect(f.xsCks, 'u.data[0] 逐帧不变(窗口列零变化)').toBe(snap.xsCks);
      }
      /* 预览帧语义: preview 令牌在场 + dx ≡ 0 + 粒子预算 */
      for (const f of animFrames) {
        expect(f.isPreview, '动画帧必须携带 preview 令牌(不是真拍)').toBe(true);
        expect(f.dx0, '预览 dx ≡ 0(不动窗口)').toBe(0);
        expect(f.parts, '粒子 spawn 清单合计必须 <= 32(I9 两轨合计)').toBeLessThanOrEqual(32);
      }
      expect(animFrames[0].parts, '预览假 Δ(Lv.2+)必须有装饰清单在场(零装饰=探针空转)').toBeGreaterThanOrEqual(2);

      /* G5 背景两点: 整窗每帧 alpha 恒 0(任何铺底/呼吸即红)且两点相等(均未落墨) */
      for (const f of frames) {
        expect(f.g1[3], '背景点 1(绘图区中央)alpha 恒 0').toBe(0);
        expect(f.g2[3], '背景点 2(右缘带, 装饰行程之外)alpha 恒 0').toBe(0);
        expect(f.g1, '两点像素相等(均未落墨 —— 「背景 RGB 恒定且两点相等」的画布采样面)').toEqual(f.g2);
      }

      /* 末帧还原真值(假值不留痕): 预览收场后 xs/尾值/x 尺与预览前快照逐值相等 */
      const endSnap = await readSnapshot(page);
      expect(endSnap.tailUp, '预览末帧必须还原上传真值').toBe(snap.tailUp);
      expect(endSnap.tailDl, '预览末帧必须还原下载真值').toBe(snap.tailDl);
      expect(endSnap.min).toBe(snap.min);
      expect(endSnap.max).toBe(snap.max);
      expect(endSnap.xsCks).toBe(snap.xsCks);
    });
  }
});
