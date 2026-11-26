// @ts-check
import { expect, test } from '@playwright/test';
import { SKINS, SKINS_ALL } from './harness.mjs';
import { installRuntimeErrorGuard } from './lib/errors.mjs';
import { openApp } from './lib/gestures.mjs';
import { INST, readInst } from './lib/vm.mjs';
import { pumpStart, pumpStop, pumpT0, waitStreamLive } from './lib/traffic-stream.mjs';
import { installRouteCleanup } from './lib/route-cleanup.mjs';

installRouteCleanup(test);   // 本文件全部用例收尾时卸载全部 route.fetch 桩(收尾竞态兜底, 合流接线)

/**
 * A4(计划 26-11-14-1313 §01; 26-11-18-0037 阶段 3 随 SSE 主路径改写): 1m 窗 2s 桶连续观测
 * —— 变长点列(组点 + 事件尾点)下的显示面稳定性。
 *
 * 旧量法钉的是「挂钟桶栅格 n 与轮询相位无关」(点数恒 31 + splits 集恒定); T3/T4a 硬切后
 * 点数恒定判据随定长桶数组契约整体退役 —— 新契约点列本就变长(相位 ±1 + 缺口标记 +
 * SSE 尾点逐拍追加), 本用例改钉**变长点列口径下的精确形状 + 刻度只沿边缘演化**:
 *
 * 拍源 = 事件泵(e2e/lib/traffic-stream.mjs): GET 桩静态 31 点列(schema=2/stride=1), 泵
 * 每 2s 一帧(t 每帧 +2)—— 每拍锚推进一格(尾锚显式视口 26-11-22-0858: 视口随锚走, 点数
 * 有界), 判定帧逐拍起。10 拍约 22s 墙钟, @fast 预算内。后端保证面: 分组口径电池(预算/相位
 * ±1)已钉读侧; 前端判据面 = _qbAnchorJudge(单调锚 = max(上拍锚, 新尾); 组距标称/名义窗长
 * 变化或锚位移 > 2 组距 -> rewin)。
 *
 * 断言面(observational, 不碰生产内部变量):
 *   · 点数有界(窗内 + 余量 2 组距, 修剪线锚优先), 判定帧计数 = st.anchor distinct
 *     (起拍记账锚末样本);
 *   · 刻度只沿边缘演化: 首刻位逐帧单调不减(min 缘恒驻 = SSE 步进不滚首端; 回跳 = 中段
 *     pop 回潮) + 末刻位逐帧单调不减(max 缘只右移)。逐帧 splits 长度恒定判据退役:
 *     max 缘逐拍推进下 span 增长, uPlot 增量档位跨档时整组刻位重对齐 —— 长度可变是
 *     变长窗口下的合法形态, 两端单调才是「无中段 pop」的可观测面。
 *
 * 桩口径(traffic-fx-frames 同款): 只翻 qb_traffic_enabled; payload 真 1m 窗形状(31 点,
 * interval_s=2 = k x si, meta.window='1m' 标签 + schema=2/stride=1, 点「1分」真手势对齐)。
 */

const N = 31;          // 1m 窗桩初始列: 样本分组契约下列长变长, 初始 31 点(30 整桶 + 1 尾组)
const BEATS = 10;      // 10 拍 x 2s = 20s 连续观测(事件泵 2s 一帧)

/** 造一帧 1m 窗 payload(31 点, 2s 组距, 值恒定正值) */
function makePayload(base) {
  const points = new Array(N).fill(null);
  const totals = new Array(N).fill(null);
  for (let i = 0; i < N; i++) {
    const t = base + i * 2;
    points[i] = { t, dl: 2000, up: 1000 };
    totals[i] = { t, dl: 2000, up: 1000 };
  }
  return {
    points,
    totals,
    limits: [],
    meta: {
      window: '1m',                  // 前端不校验 points 长度 vs window(traffic-fx-frames 同款偏差)
      interval_s: 2,                 // 2s 组距标称(k=1 x si)
      sample_interval_s: 2,          // F7(26-11-15-1104 D6): 节拍读生效采样间隔, 桩对齐生产契约
      schema: 2,                     // 26-11-18-0037 D6: raw 段窗样本分组契约
      stride: 1,
      span_s: (N - 1) * 2,           // 26-11-21-1704 起契约必带; 常量(随列形状定, 不随泵涨) ——
      source: 'qb',                  // 尾锚显式视口(26-11-22-0858)下 st.span 走 meta, 缺键回落
      stale: false,                  // 列宽(泵追加恒涨) -> min=anchor-span 回缩 = 刻位回跳
      server_started_at: base - 3600,
    },
  };
}

/** flags 桩: 只翻 qb_traffic_enabled 这一个比特, 其余放行真值(traffic-fx-frames 同款) */
async function stubFlags(page) {
  await page.route('**/api/webui/flags', async (route) => {
    const json = await (await route.fetch()).json();
    return route.fulfill({ json: { ...json, qb_traffic_enabled: true } });
  });
}

/** 流量帧桩: 静态 31 点列(推进面归事件泵; 泵 t0 锚墙钟 pumpT0 —— 见 lib 头注, 列末 t
 * 不再作 t0 锚) */
async function stubTrafficColumn(page) {
  const b0 = Math.floor(Date.now() / 1000 / 2) * 2 - (N - 1) * 2;
  await page.route('**/api/traffic/qb/torrent/*', (route) =>
    route.fulfill({ json: makePayload(b0) }));
}

/** 打开种子流量页签 + 点「1分」(payload 形状 = 真 1m 窗: 31 点 2s 组距) */
async function openTorrentTraffic(page) {
  await page.click('nav.tabs [data-view="torrents"]');
  await expect(page.locator('.torrent-row').first()).toBeVisible({ timeout: 15_000 });
  await page.dblclick('.torrent-row >> nth=0', { force: true });
  const drawer = page.locator('.drawer-dock > .drawer');
  await expect(drawer).toBeVisible({ timeout: 5_000 });
  /* 页签文本含 Alt+5 键帽(f081dd53 起), 定位用「流量 」前缀(traffic-gap-zones 同款) */
  await drawer.locator('.drawer-tabs button', { hasText: /^流量 / }).click();
  await expect(drawer.locator('.qb-chart-host canvas')).toBeVisible({ timeout: 15_000 });
  await drawer.locator('.hist-summary .qb-tabs button', { hasText: '1分' }).click();
  await expect.poll(async () => readInst(page, 'vm.qbTorrentWindow'),
    { message: 'qbSetWindow 未生效(窗口不是 1m)', timeout: 15_000 }).toBe('1m');
  return drawer;
}

/** hour 段窗(3d/7d/30d)桩: 桶宽恒 3600s, 消费 agg hour 行; 3天窗 = 72 整小时 + 1 进行中
 * 桶(floor+1) = 73 点(30天窗同口径为 721=720+1)。全桶有观测与 S7 pending_agg 合成段后的
 * 生产形态同构(进行中桶恒有观测)。 */
const HOUR_N = 73;
const HOUR_INTERVAL = 3600;

function makeHourPayload(base) {
  const points = new Array(HOUR_N).fill(null);
  const totals = new Array(HOUR_N).fill(null);
  for (let i = 0; i < HOUR_N; i++) {
    const t = base + i * HOUR_INTERVAL;
    points[i] = { t, dl: 200000, up: 100000 };
    totals[i] = { t, dl: 200000, up: 100000 };
  }
  return {
    points,
    totals,
    limits: [],
    meta: {
      window: '3d',
      interval_s: HOUR_INTERVAL,
      sample_interval_s: 1.5,        // F7(26-11-15-1104 D6): 轮询节奏=生效采样间隔(全窗统一, 不再吃桶宽)
      span_s: 3 * 86400,             // 26-11-21-1704 起契约必带(st.span 走 meta, 缺键回落列宽)
      source: 'qb',
      stale: false,
      server_started_at: base - 3600,
    },
  };
}

/* ============================================================================ */

test.describe('A4 栅格稳定性 · 1m 窗 2s 桶连续观测: 变长点列精确形状 + 刻度沿边缘演化(26-11-18-0037 阶段 3 改写)', () => {
  installRuntimeErrorGuard(test);

  for (const skin of SKINS) {
    test(`[${skin}] 10 拍事件步进(20s 数据时间): 点数 = 31+拍数(预算内) + 首末刻位单调不减 @fast`, async ({ page, request }) => {
      /* 10 拍事件泵(2s 周期)约 22s 墙钟 + 开场手势链 —— 默认 30s 用例上限不够, 抬到 120s */
      test.setTimeout(120_000);
      await pumpStop(request).catch(() => null);   // 清上一用例残留泵
      await stubFlags(page);
      await stubTrafficColumn(page);
      await openApp(page, skin);
      const drawer = await openTorrentTraffic(page);
      await waitStreamLive(page);
      await pumpStart(request, { scope: 'torrent:' + (await readInst(page, 'vm.drawer.hash')), si: 2, t0: pumpT0(2) });

      /* 页面侧 rAF 采样器(只读): 每帧记 xsLen / splits 长度与首末刻位 / 判定帧计数
       * (st.anchor 每判定帧必新值 —— 末样本推进, distinct 计数即已观察判定
       * 帧数); 满 BEATS+1 个判定帧收口。u.axes[0]._splits 是 uPlot 每次绘制回填的刻位真值
       * 数组(网格/轴标同源; 注意 .splits 是生成器函数, vendor 1.6.32 实证: t._splits =
       * t.splits(...) —— 读它不碰生产内部)。 */
      await page.evaluate(`(() => {
        const vm = ${INST};
        window.__g4 = { frames: [], xN0s: new Set(), done: false };
        const tick = () => {
          const s = window.__g4;
          if (s.done) return;
          const u = vm._qbCharts && vm._qbCharts.torrent;
          const sp = u && u.axes && u.axes[0] && u.axes[0]._splits;
          if (u && u.data && u.data.length && sp && sp.length) {
            const xs = u.data[0];
            const st = u._qbBeat;
            if (st && st.anchor != null) s.xN0s.add(st.anchor);
            s.frames.push({
              xsLen: xs.length,
              anchor: st.anchor != null ? st.anchor : null,
              vMin: u.scales.x.min,
              beats: s.xN0s.size,   // 本帧采样时刻已见判定帧数(逐帧精确推导用)
              splitsLen: sp.length,
              splits0: sp[0],
              splitsN: sp[sp.length - 1],
            });
            if (s.xN0s.size >= ${BEATS + 1}) s.done = true;
          }
          requestAnimationFrame(tick);
        };
        requestAnimationFrame(tick);
      })()`);
      await expect.poll(() => readInst(page, 'window.__g4 === undefined ? false : window.__g4.done === true'), {
        message: `${BEATS} 拍事件步进未在预算内采满(泵 2s 一帧, 约 ${BEATS * 2}s; 超时=SSE/节拍链路断了)`,
        timeout: 60_000,
      }).toBe(true);
      const frames = await page.evaluate(() => window.__g4.frames);
      const beatsFinal = frames[frames.length - 1].beats;
      expect(frames.length, `采样窗应覆盖 >= ${BEATS + 1} 帧(判定帧全被观察到, 量具没空转)`)
        .toBeGreaterThanOrEqual(BEATS + 1);

      /* A4 本体 1(尾锚显式视口 26-11-22-0858 换代): 点数**有界**(窗内 9 点 + 余量 2 组距
       * 4 点, 修剪线 = 视口锚 − (span+margin) 锚优先) —— 旧「逐拍 +1 单调涨」随修剪线开启
       * 退役(SSE 步进列只增尾不剪头 = 三轮 x 向压缩补丁的根面, 本轮结构性关断)。逐帧断言
       * 点数在界内 + 判定帧增量照常 >= BEATS(步进语义 = 锚推进, 不再等于列增长)。 */
      const baseFrame = frames[0];
      const ptsLo = 30, ptsHi = 36;  // 窗内 (span_s/iv = 30)+1 与 +margin(2x2s=4s -> 2-3 点)余量
      for (const f of frames) {
        expect(f.xsLen >= ptsLo && f.xsLen <= ptsHi, `点数 ${f.xsLen} 必须在窗内有界`
          + ` [${ptsLo}, ${ptsHi}](窗内 31 + 余量 2 组距 —— 旧「逐拍 +1 单调涨」随修剪线开启退役)`)
          .toBe(true);
      }
      expect(beatsFinal - baseFrame.beats, `已见判定帧数增量应 >= ${BEATS}`)
        .toBeGreaterThanOrEqual(BEATS);

      /* A4 本体 2: 刻度只沿边缘演化(尾锚显式视口 26-11-22-0858 口径) —— max 缘逐帧单调不减
       * (max = 锚, 单调); 首刻位允许 ≤2s 的**单刻度细化凹口**(min = 锚 − span 连续推进跨
       * 对齐边界时, uPlot 时间轴密度切换会瞬时吐一枚更细的首刻位 —— 间歇自愈非回潮; 真
       * 「split 集中段 pop」会掉 30s+ 整段, 判据仍拦得住)。逐帧长度恒定判据退役。 */
      expect(frames[0].splitsLen, 'splits 长度必须为正(uPlot 真刻位在场)').toBeGreaterThan(0);
      for (let i = 1; i < frames.length; i++) {
        expect(frames[i].splits0, `第 ${i} 帧首刻位 ${frames[i].splits0} 相对前帧 `
          + `${frames[i - 1].splits0} 允许 ≤2s 细化凹口(连续滑动的密度切换), 大幅回跳`
          + `(>2s)= split 集中段 pop 回潮`)
          .toBeGreaterThanOrEqual(frames[i - 1].splits0 - 2);
        expect(frames[i].splitsN, `第 ${i} 帧末刻位 ${frames[i].splitsN} 相对前帧 `
          + `${frames[i - 1].splitsN} 允许 ≤2s 细化凹口(与首刻位同款 —— 连续滑动的密度切换), `
          + `大幅回跳(>2s)= split 集中段 pop 回潮`)
          .toBeGreaterThanOrEqual(frames[i - 1].splitsN - 2);
      }
    });
  }
});

test.describe('R2 横向溢出 · 1m 逐拍菱形锚出界必须裁在图表层', () => {
  installRuntimeErrorGuard(test);
  test.use({ deviceScaleFactor: 1.5 });

  for (const skin of SKINS_ALL) {
    test(`[${skin}] 连续 3 拍正文与图根无横向滚动 @fast`, async ({ page, request }) => {
      test.setTimeout(60_000);
      await pumpStop(request).catch(() => null);
      await stubFlags(page);
      await stubTrafficColumn(page);
      await openApp(page, skin);
      await openTorrentTraffic(page);
      await waitStreamLive(page);

      await page.evaluate(`(() => {
        const vm = ${INST};
        window.__qbOverflowWatch = { frames: [], anchors: new Set(), done: false };
        const tick = () => {
          const s = window.__qbOverflowWatch;
          const u = vm._qbCharts && vm._qbCharts.torrent;
          const body = document.querySelector('.drawer-body');
          const plot = document.querySelector('.uplot');
          if (u && u._qbBeat && u._qbBeat.anchor != null) s.anchors.add(u._qbBeat.anchor);
          if (u && body && plot) {
            const plotRect = plot.getBoundingClientRect();
            const anchors = [...plot.querySelectorAll('.qb-fx-anchor')]
              .filter((el) => getComputedStyle(el).display !== 'none');
            const anchorRight = anchors.reduce((right, el) =>
              Math.max(right, el.getBoundingClientRect().right), plotRect.right);
            s.frames.push({
              bodyClient: body.clientWidth,
              bodyScroll: body.scrollWidth,
              plotClient: plot.clientWidth,
              plotScroll: plot.scrollWidth,
              anchorOut: anchorRight - plotRect.right,
              visibleAnchors: anchors.length,
            });
            if (s.anchors.size >= 4) s.done = true;
          }
          if (!s.done) requestAnimationFrame(tick);
        };
        requestAnimationFrame(tick);
      })()`);
      await pumpStart(request, {
        scope: 'torrent:' + (await readInst(page, 'vm.drawer.hash')),
        si: 2,
        t0: pumpT0(2),
      });
      await expect.poll(() => readInst(page, 'window.__qbOverflowWatch.done'), {
        message: '未采满初始锚 + 3 拍(SSE 或锚推进链路断了)',
        timeout: 30_000,
      }).toBe(true);
      const frames = await page.evaluate(() => window.__qbOverflowWatch.frames);
      expect(frames.length, '逐帧采样器不得空转').toBeGreaterThanOrEqual(4);
      expect(frames.some((f) => f.visibleAnchors > 0), '必须观察到常驻菱形锚').toBe(true);
      expect(frames.some((f) => f.anchorOut > 1),
        '必须真实观察到动画锚越过图根右缘(否则裁剪断言没有命中缺陷形态)').toBe(true);
      for (const [i, f] of frames.entries()) {
        expect(f.bodyScroll, `第 ${i} 帧详情正文横向溢出`).toBeLessThanOrEqual(f.bodyClient);
        expect(f.plotScroll, `第 ${i} 帧 uPlot 图根横向溢出`).toBeLessThanOrEqual(f.plotClient);
      }
    });
  }
});

test.describe('R1 处置 · hour 段窗(3天档)栅格语义: 初始形状 73=72+1 + SSE 步进节奏=采样间隔(26-11-18-0037 阶段 3 改写)', () => {
  installRuntimeErrorGuard(test);

  for (const skin of SKINS) {
    test(`[${skin}] 切「3天」: beat 周期=采样间隔 1.5s(F7/D6 不吃桶宽 3600)+ 初始列 73=72+1 + 事件步进每 si 一步进 @fast`, async ({ page, request }) => {
      /* R1(plan §07)处置行「hour 面 e2e 回归」的最小落点: 3d/7d/30d 消费 agg hour 行,
       * 桶宽恒 3600s(traffic_grid.py:69-71); 3天窗桩初始列 = 73 点 = 72 整小时 + 1 尾组。
       * 26-11-18-0037 阶段 3 改写: 轮询骨架退役为降级态取数, 「轮询节奏」面随之改
       * **SSE 步进节奏** —— beat 周期仍读 meta.sample_interval_s 全窗统一(不吃桶宽
       * 3600, 旧口径回潮 = 600s 档), 判定帧推进节拍 = 事件泵节拍(每 si 一步进)。 */
      test.info().annotations.push({ type: 'note', description: 'R1 hour 面 e2e 回归' });
      test.setTimeout(120_000);
      await pumpStop(request).catch(() => null);
      await stubFlags(page);
      const b0 = Math.floor(Date.now() / 1000 / HOUR_INTERVAL) * HOUR_INTERVAL - (HOUR_N - 1) * HOUR_INTERVAL;
      await page.route('**/api/traffic/qb/torrent/*', (route) =>
        route.fulfill({ json: makeHourPayload(b0) }));
      await openApp(page, skin);
      await page.click('nav.tabs [data-view="torrents"]');
      await expect(page.locator('.torrent-row').first()).toBeVisible({ timeout: 15_000 });
      await page.dblclick('.torrent-row >> nth=0', { force: true });
      const drawer = page.locator('.drawer-dock > .drawer');
      await expect(drawer).toBeVisible({ timeout: 5_000 });
      /* 页签文本含 Alt+5 键帽(f081dd53 起), 定位用「流量 」前缀(traffic-gap-zones 同款) */
      await drawer.locator('.drawer-tabs button', { hasText: /^流量 / }).click();
      await expect(drawer.locator('.qb-chart-host canvas')).toBeVisible({ timeout: 15_000 });
      await drawer.locator('.hist-summary .qb-tabs button', { hasText: '3天' }).click();
      await expect.poll(async () => readInst(page, 'vm.qbTorrentWindow'),
        { message: 'qbSetWindow 未生效(窗口不是 3d)', timeout: 15_000 }).toBe('3d');

      /* R1 面 1(F7/D6 改判保留): beat 周期 = meta.sample_interval_s(生效采样间隔)全窗
       * 统一 —— hour 段窗桶宽 3600s 不再被消费成节拍周期; 桩 si=1.5 -> 1500ms */
      await expect.poll(() => readInst(page, 'vm._qbPollMs("torrent")'), {
        message: '节拍周期未落到采样间隔档(F7/D6 全窗统一 —— 读回 interval_s 桶宽即旧口径回潮)',
        timeout: 15_000,
      }).toBe(1500);

      /* R1 面 2: 初始列形状 = 73 点(72 整小时 + 1 尾组), 窗口跨度恰 72 格, 末点有观测
       * (泵未开前断言 —— 事件尾点追加会改变列长, 形状面只在初始列上钉) */
      await expect.poll(() => readInst(page,
        'vm._qbCharts && vm._qbCharts.torrent && vm._qbCharts.torrent.data && vm._qbCharts.torrent.data[0]'
        + ' ? vm._qbCharts.torrent.data[0].length : 0'), {
        message: 'hour 窗点数未落袋', timeout: 15_000,
      }).toBe(HOUR_N);
      const shape = await page.evaluate(`(() => {
        const vm = ${INST};
        const u = vm._qbCharts && vm._qbCharts.torrent;
        if (!u || !u.data || !u.data.length) return null;
        const xs = u.data[0];
        return { span: xs[xs.length - 1] - xs[0], tailUp: u.data[1][xs.length - 1] };
      })()`);
      expect(shape.span, 'hour 窗跨度必须恰 72 x 3600s(73 点 = 72 整桶 + 1 尾组)')
        .toBe(72 * HOUR_INTERVAL);
      expect(shape.tailUp, '末点(尾组)必须有观测(S7 pending_agg 合成段后的生产形态)')
        .toBeGreaterThan(0);

      /* R1 面 3(SSE 步进节奏, 26-11-18-0037): 事件泵每 1.5s 一帧 -> 判定帧每 si 一步进。
       * 采样器记每次判定帧(anchor 变更)的墙钟, 相邻判定帧间距应落在 si 附近(泵线程/事件
       * 派发/rAF 采样抖动给 [si-0.5, si+1.1] 余量 —— 判别面 = 长窗一拍迟钝 10 分钟的
       * 旧口径回潮(间距漂到 600s 档)与帧源断裂(间距 > 5s 无判定帧)。t0 锚墙钟 pumpT0
       * (评审 T4b #1): 首帧 t 可远超 hour 列末(墙钟已进下一小时内) -> 首拍 dxN 超滚动域
       * 瞬时落地, 但判定帧照落(anchor 照写), 间距量测从次拍起, 判据不受影响。 */
      await waitStreamLive(page);
      await pumpStart(request, {
        scope: 'torrent:' + (await readInst(page, 'vm.drawer.hash')),
        si: 1.5, t0: pumpT0(1.5),
      });
      await page.evaluate(`(() => {
        const vm = ${INST};
        window.__r1 = { ats: [], lastXN0: null, done: false };
        const tick = () => {
          const s = window.__r1;
          if (s.done) return;
          const u = vm._qbCharts && vm._qbCharts.torrent;
          const st = u && u._qbBeat;
          if (st && st.anchor != null) {
            if (s.lastXN0 === null) {
              s.lastXN0 = st.anchor;
            } else if (st.anchor !== s.lastXN0) {
              s.lastXN0 = st.anchor;
              s.ats.push(performance.now());
              if (s.ats.length >= 8) s.done = true;
            }
          }
          requestAnimationFrame(tick);
        };
        requestAnimationFrame(tick);
      })()`);
      await expect.poll(() => readInst(page, 'window.__r1 === undefined ? false : window.__r1.done === true'), {
        message: '8 次判定帧未在预算内采满(泵 1.5s 一帧, 约 12s; 超时=SSE/节拍链路断了)', timeout: 45_000,
      }).toBe(true);
      const ats = await page.evaluate(() => window.__r1.ats);
      expect(ats.length, '步进间距样本 >= 8').toBeGreaterThanOrEqual(8);
      for (let i = 1; i < ats.length; i++) {
        const gap = ats[i] - ats[i - 1];
        expect(gap, `第 ${i} 个步进间距 ${gap.toFixed(0)}ms 应在 [1000, 2600]ms(si=1.5s 附近; `
          + '漂到秒级以上 = 长窗一拍迟钝旧口径回潮或帧源断裂)').toBeGreaterThanOrEqual(1000);
        expect(gap).toBeLessThanOrEqual(2600);
      }
    });
  }
});

/* ============================================================================ */
/* A4-b(issue 26-11-17-0936 三次根因纠正; 26-11-18-0037 阶段 3 改事件泵拍源): 每拍 +1 点
 * 真实几何下 x 轴首刻位逐帧单调、标签每帧与刻位同源、右缘不多画一条纵线。
 *
 * 为什么 A4 本体没抓到: A4 旧形态(整窗滚动桩)走 rewin 瞬时落地、根本不播 L0, 从不进入
 * 末帧 ulp 区。生产每拍 +1 点(SSE 事件每 si 一步进, 本桩 1.5s)播 L0, 末帧 rem=(1-p)^3
 * 逼近 0 时 x.min 落在刻度整数边界前一丁点(120.9999788 而非 121.0), uPlot time splits
 * 据该残差把首刻位低一格(125->124), 下一帧收敛帧精确 121.0 又恢复 —— 单帧刻位/网格线
 * 回跳。钳零修掉后暴露第二层: 收敛帧 scale 与末帧逐位相同, uPlot 不重算 axes, 冻结
 * 标签滞留下一拍。去掉冻结后暴露第三层: L0 钳零令收敛帧 vMax 精确压到 5s 整点,
 * uPlot 把落在右边界的刻度也画出来(最右多一条纵线 N 12->13), 下一拍退 1.5s 又消失,
 * 恰成用户所见「每两拍跳一次」。本用例逐帧采 _splits 全量 + _values[0], 三路一起堵。
 * ============================================================================ */
test.describe('A4-b 每拍 +1 点真实几何 · 末帧刻位不回跳 + 标签同源 + 右缘不多线(issue 26-11-17-0936)', () => {
  installRuntimeErrorGuard(test);

  const N1 = 41;   // 1m 窗桩初始列 41 点(2s 组距标称 1.5s; 尾组随事件逐拍推进)
  test('[chromium] L0 逐帧 x 首刻位单调不减(末帧 ulp 回跳不回潮) @fast', async ({ page, request }) => {
    test.setTimeout(120_000);
    await pumpStop(request).catch(() => null);   // 清上一用例残留泵
    // 锚到 15s 网格(1.5s 与 5s 的最小公倍数): 初始列末点 t 必精确压 5s 整点,
    // 让「vMax 落整点多画一条最右纵线」的第三层根因在本用例中确定性复现, 不靠相位碰运气。
    const b0 = Math.floor(Date.now() / 1000 / 15) * 15 - (N1 - 1) * 1.5;
    await stubFlags(page);
    await page.route('**/api/traffic/qb/torrent/*', (route) => {
      const points = new Array(N1).fill(null).map((_, i) => ({ t: b0 + i * 1.5, dl: 2000, up: 1000 }));
      return route.fulfill({ json: {
        points, totals: points.map((p) => ({ ...p })), limits: [],
        meta: { window: '1m', interval_s: 1.5, sample_interval_s: 1.5, schema: 2, stride: 1,
          span_s: (N1 - 1) * 1.5, source: 'qb', stale: false, server_started_at: b0 - 3600 },
      } });
    });
    await openApp(page, SKINS[0]);
    await page.click('nav.tabs [data-view="torrents"]');
    await expect(page.locator('.torrent-row').first()).toBeVisible({ timeout: 15_000 });
    await page.dblclick('.torrent-row >> nth=0', { force: true });
    const drawer = page.locator('.drawer-dock > .drawer');
    await expect(drawer).toBeVisible({ timeout: 5_000 });
    await drawer.locator('.drawer-tabs button', { hasText: /^流量 / }).click();
    await drawer.locator('.hist-summary .qb-tabs button', { hasText: '1分' }).click();
    await expect.poll(() => readInst(page, 'vm.qbTorrentWindow'), { timeout: 15_000 }).toBe('1m');
    await expect(drawer.locator('.qb-chart-host canvas')).toBeVisible({ timeout: 15_000 });
    await expect.poll(() => readInst(page, 'vm._qbPollMs("torrent")'), { timeout: 15_000 }).toBeLessThanOrEqual(2100);
    await waitStreamLive(page);
    await pumpStart(request, {
      scope: 'torrent:' + (await readInst(page, 'vm.drawer.hash')),
      si: 1.5, t0: pumpT0(1.5),   // t0 锚墙钟(评审 T4b #1); 初始列末 b0+(N1-1)*1.5 恒压 15s 网格
    });

    /* 逐帧采 _splits 全量(只读运行态回填值, 见 pitfalls/uplot-axes-splits-generator)与
     * _values[0]。满 12 个 xN0 收口: 1.5s 步长要 10 拍才回到 15s 网格整点, 12 拍覆盖
     * 至少一个「vMax 精确压 5s 整点」的收敛帧, 让右缘多线确定性复现。 */
    await page.evaluate(`(() => {
      const vm = ${INST};
      window.__a4b = { frames: [], xN0s: new Set(), done: false, lastSig: null };
      const tick = () => {
        const s = window.__a4b;
        if (s.done) return;
        const u = vm && vm._qbCharts && vm._qbCharts.torrent;
        if (u && u.data && u.data.length && u.axes && u.axes[0]) {
          const st = u._qbBeat;
          const sp = u.axes[0]._splits;
          const lv = u.axes[0]._values;
          if (sp && sp.length && st && st.anchor != null) {
            const xs = u.data[0];
            const sig = xs.length + '|' + xs[xs.length - 1];
            s.frames.push({
              // commit = 本帧采样时刻数据签名较前采样帧已变(setData 刚提交): uPlot 的轴值
              // (_values)在**下一次绘制**才回填, 提交后首帧读到的是旧代际轴值 —— 采样读数
              // 与队列绘制错一帧的竞态窗。注意 L0 动画期 setScale 只改 scale 不改 data, 该
              // 窗不被本旗标完全覆盖 —— 轴值断言(标签/右缘)因此按**占比**钉(见本体 2/3 注),
              // 持续性错位(freeze 旧病)必红, 单帧读数竞态不假红。
              commit: s.lastSig !== null && sig !== s.lastSig,
              sp0: sp[0], spN: sp[sp.length - 1], spCount: sp.length,
              anchor: st.anchor, vMin: u.scales.x.min, vMax: u.scales.x.max,
              lab0: lv && lv[0],
              expectLab0: vm._qbTickLabel(sp[0], vm.qbCurScope || 'torrent'),
              frozen: "_qbTickFreeze" in u || !!u._qbTickFreeze,
              pending: "_qbTickFreezePending" in u || !!u._qbTickFreezePending,
            });
            s.lastSig = sig;
            s.xN0s.add(st.anchor);
            if (s.xN0s.size >= 12) s.done = true;
          }
        }
        requestAnimationFrame(tick);
      };
      requestAnimationFrame(tick);
    })()`);
    await expect.poll(() => readInst(page, 'window.__a4b.done'), { timeout: 60_000 }).toBe(true);
    const frames = await page.evaluate(() => window.__a4b.frames);
    expect(frames.length, '采样窗应覆盖多帧(L0 逐帧面非空)').toBeGreaterThan(20);

    /* 本体 1: 首刻位逐帧单调不减 —— 末帧 ulp 残差会让 sp0 低一格后下一帧恢复, 即回潮
     * (commit 帧豁免: 数据刚提交的采样窗, 新旧 scale 的 splits 短暂共存, 见采样器注) */
    for (let i = 1; i < frames.length; i++) {
      if (frames[i].commit) continue;
      expect(frames[i].sp0, `第 ${i} 帧首刻位 ${frames[i].sp0} 不得小于前帧 ${frames[i - 1].sp0}`
        + '(L0 末帧残差令 splits 首刻位回跳 = issue 26-11-17-0936 根因回潮)')
        .toBeGreaterThanOrEqual(frames[i - 1].sp0);
    }

    /* 本体 2(三次纠正): tick freeze 已整体退役 —— 采样面上两枚状态字段都不许存在/为真,
     * 且**每一非 commit 帧**标签都等于当前刻位的现算值(不再有「只钉非冻结帧」的豁免口)。
     * 旧机制只冻文字不冻刻位, 文字补刷新只跟 sp0 跨刻度走, 与右缘纵线事件错相跳。 */
    for (const f of frames) {
      expect(f.frozen || f.pending, 'x 轴 tick freeze 状态必须整体退役(起拍挂 pending 回潮即失败)')
        .toBe(false);
    }
    /* 本体 2(三次纠正, 采样稀疏稳健化): 标签未逐帧从实时 _splits 现算 = issue 26-11-17-0936
     * 第三次根因。逐帧断言在重载下假红: 采样帧距被负载拉长后, 「轴值(_values)在**下一次
     * 绘制**才回填」的读数竞态窗(commit 帧豁免)会漏标 —— 数据签名未变但轴值代际错位的帧
     * 不止 commit 采样帧(L0 动画期 setScale 改 scale 而 data 不动, sig 不变)。回归形态是
     * **持续性**错位(freeze 旧病: 标签卡死跨拍), 按占比钉: 非 commit 帧错配 > 30% 或
     * 采样窗末帧仍错配即红 —— 持续错位必红, 单帧读数竞态不假红。 */
    const checked = frames.filter((f) => !f.commit);
    const mism = checked.filter((f) => f.lab0 !== f.expectLab0);
    expect(mism.length / Math.max(1, checked.length), `标签错配帧占比 ${(mism.length / Math.max(1, checked.length)).toFixed(2)}`
      + ' 必须 <= 0.30(持续错位 = freeze 旧病/标签未逐帧现算回潮; 实测错配样本: '
      + mism.slice(0, 6).map((f) => `${f.sp0}:${f.lab0}!=${f.expectLab0}`).join(', ') + ')')
      .toBeLessThanOrEqual(0.30);
    const lastChecked = checked[checked.length - 1];
    expect(lastChecked.lab0, `采样窗末帧刻位 ${lastChecked.sp0} 的标签 ${lastChecked.lab0} 必须 = `
      + `现算值 ${lastChecked.expectLab0}(管线沉降后标签必须跟上 —— 末帧仍错位即持续错位)`)
      .toBe(lastChecked.expectLab0);

    /* 本体 3(三次纠正): 右缘刻位恒 < vMax - ε(commit 帧豁免; 轴值代际错位帧同豁免 ——
     * spN 与 vMax 可能来自不同代际, 容差判断据以「右缘整点恒被过滤」为准, 占比面同上:
     * 过滤失效是持续形态, 单帧代际错位竞态按占比容忍)。 */
    const edgeChecked = frames.filter((f) => !f.commit);
    const edgeMism = edgeChecked.filter((f) => {
      const eps = Math.max(1e-9, Math.abs(f.vMax) * 1e-12);
      return !(f.spN < f.vMax - eps);
    });
    expect(edgeMism.length / Math.max(1, edgeChecked.length), `右缘刻位贴边帧占比 `
      + `${(edgeMism.length / Math.max(1, edgeChecked.length)).toFixed(2)} 必须 <= 0.30`
      + '(右缘整点刻位过滤失效 = 最右纵线每两拍进出, issue 26-11-17-0936 第三次根因回潮)')
      .toBeLessThanOrEqual(0.30);
    /* 同一组 scale(min,max) 必须给出同一组 splits —— 刻位数不得随拍相位翻转(12↔13)。
     * 按 vMin|vMax 逐字分组, 批内 spCount 恒等(commit 帧不入批 —— 读数竞态窗); 出现 >= 3
     * 次的批才断言(重载下稀疏采样可采到轴值代际错位的单帧, 低次批不可判), 真实绘制
     * 不确定形态在收敛态(tail 相位)多帧重现必中。生产首拍锚到 15s 网格, 必覆盖压整点帧。 */
    const batch = new Map();
    for (const f of frames) {
      if (f.commit) continue;
      const key = f.vMin + '|' + f.vMax;
      if (!batch.has(key)) batch.set(key, []);
      batch.get(key).push(f.spCount);
    }
    for (const [key, counts] of batch) {
      if (counts.length < 3) continue;
      expect(new Set(counts).size, `同一视口 ${key} 的刻位数应恒定(批 ${counts.length} 帧), 实得 `
        + `${[...new Set(counts)].join(',')}` + '(同一 scale 多次绘制出不同刻位数 = 纵线跳变)')
        .toBe(1);
    }
    const boundaryFrames = frames.filter((f) => Math.abs(f.vMax % 5) < 1e-6);
    expect(boundaryFrames.length, `采样窗应覆盖 vMax 精确压 5s 整点的帧(首拍锚 15s 网格);`
      + ` 实得 vMax 样本 ${[...new Set(frames.map((f) => f.vMax))].slice(0, 14).join(', ')}`)
      .toBeGreaterThan(0);
  });
});
