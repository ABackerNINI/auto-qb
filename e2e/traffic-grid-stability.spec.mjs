// @ts-check
import { expect, test } from '@playwright/test';
import { SKINS } from './harness.mjs';
import { installRuntimeErrorGuard } from './lib/errors.mjs';
import { openApp } from './lib/gestures.mjs';
import { INST, readInst } from './lib/vm.mjs';
import { installRouteCleanup } from './lib/route-cleanup.mjs';

installRouteCleanup(test);   // 本文件全部用例收尾时卸载全部 route.fetch 桩(收尾竞态兜底, 合流接线)

/**
 * A4(计划 26-11-14-1313 §01): 1m 窗 2s 桶连续观测(>=10 分钟)—— 显示列点数恒定、x 轴 split 集
 * 稳定(仅视口边界的自然滑入滑出, 无中段 pop)。
 *
 * 为什么不真跑 10 分钟: 真实轮询节奏 2s/拍 x 300 拍 = 600s 墙钟, e2e 预算内不可行 —— 量法
 * 等价在**数据时间**不在墙钟: F3(栅格 ceil->floor+1)要钉的判据本体是「W 恰为桶宽整倍时
 * n 与轮询相位无关」, 本用例用「每次轮询恰好推进一整窗
 * (30 桶 = 60s 数据时间)」的压缩桩连续喂 10 轮(累计 300 桶 = 600s >= 10 分钟的 2s 桶连续
 * payload), 每轮都让数据窗整体右移。观测性质边界: 桩恒填 31 点, n 在本用例结构上不可能
 * 漂移(后端 ceil 栅格回潮时本用例不可见 —— 该面由 B1 的相位不变性电池承接, 本用例只钉
 * 前端消费面: 显示列点数恒定 + splits 稳定的显示面)。又: 每轮 dx0 = 30 格 >
 * step x 2, 生产走瞬时落地路径(26-11-15-1104 F5 后 = 跨窗换档判据 |dx0| > 2 格翻真, 显示
 * 面同旧: 瞬时落地; 补尾格也不触发 —— 补点只在 1-2 整格滚动拍), roll 动画期的逐帧面不在
 * 本用例域(由 traffic-fx-frames 的左移连续性用例承接)。10 轮真轮询(2s 周期)约 22s 墙钟,
 * @fast 预算内。后端保证面: B1 电池(相位不变性/t1 边界)已钉 _floor_buckets 的 n 恒等;
 * 前端判据面 = qb_traffic_chart.js _qbRollJudge(F5: 桶宽/窗起点不连续才换档, 点数退役) ——
 * 两面在本用例的显示面合流。
 *
 * 断言面(observational, 不碰生产内部变量):
 *   · 显示列点数恒 31(floor+1: 1m 窗 2s 桶 = 30 整桶 + 1 进行中桶): dx0 = 30 格非整格滚动,
 *     F5 补尾格不触发(补点只在 1-2 整格滚动拍), 点数漂移即显示面回潮;
 *   · split 集稳定: u.axes[0].splits(uPlot 网格/轴标刻位真值)逐帧长度恒定(A4 量法「split 数
 *     分布单峰」的压缩等价: 分布退化为单值)+ 首刻位逐帧单调不减(窗口右移 -> 刻度只自然
 *     滑入滑出, 无回跳 pop)。
 *
 * 桩口径(traffic-fx-frames 同款): 只翻 qb_traffic_enabled; payload 真 1m 窗形状(31 桶,
 * interval_s=2, meta.window='1m', 点「1分」真手势对齐); 每请求 base 右移 30 桶。
 */

const N = 31;          // floor+1: 60s / 2s = 30 整桶 + 1 进行中桶
const STEP = 30;       // 每次轮询推进的桶数(一整窗 = 60s 数据时间)
const POLLS = 10;      // 10 轮 x 30 桶 = 300 桶 = 600s >= 10 分钟连续观测

/** 造一帧 1m 窗 payload(31 桶, 2s 桶宽, 值恒定正值) */
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
      interval_s: 2,                 // 2s 桶宽 -> 轮询 2s 一拍
      sample_interval_s: 2,          // F7(26-11-15-1104 D6): 轮询节奏读生效采样间隔, 桩对齐生产契约
      source: 'qb',
      stale: false,
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

/** 流量帧桩: 每次请求 base 恰推进 STEP 桶(一整窗), 与墙钟解耦 */
async function stubTrafficAdvancing(page) {
  const b0 = Math.floor(Date.now() / 1000 / 2) * 2 - (N - 1) * 2;
  let calls = 0;
  await page.route('**/api/traffic/qb/torrent/*', (route) =>
    route.fulfill({ json: makePayload(b0 + (calls++) * STEP * 2) }));
}

/** 打开种子流量页签 + 点「1分」(payload 形状 = 真 1m 窗: 31 桶 2s 桶宽) */
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

/** 把轮询周期重排到 interval_s 档(traffic-fx-frames.rearmTrafficPoll 同款, 注释见彼处) */
async function rearmTrafficPoll(page, drawer) {
  // 页签文本含键帽徽标(f081dd53 起 Alt+1..5), 定位一律带尾随空格(traffic-gap-zones 同款)
  await drawer.locator('.drawer-tabs button', { hasText: /^常规 / }).click();
  await drawer.locator('.drawer-tabs button', { hasText: /^流量 / }).click();
  await expect(drawer.locator('.qb-chart-host canvas')).toBeVisible({ timeout: 15_000 });
  await expect.poll(() => readInst(page, 'vm._qbPollMs("torrent")'), {
    message: '轮询周期未重排到 interval_s 档(数据未落袋时的 fallback 30s 还在)', timeout: 15_000,
  }).toBeLessThanOrEqual(2100);
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
      source: 'qb',
      stale: false,
      server_started_at: base - 3600,
    },
  };
}

/* ============================================================================ */

test.describe('A4 栅格稳定性 · 1m 窗 2s 桶连续观测: 显示列点数恒定 + split 集稳定(plan 26-11-14-1313)', () => {
  installRuntimeErrorGuard(test);

  for (const skin of SKINS) {
    test(`[${skin}] 10 轮压缩轮询(600s 数据时间): 点数恒 31(F5 补尾格不触发) + splits 长度恒定 + 首刻位不回跳 @fast`, async ({ page }) => {
      /* 10 轮真轮询(2s 周期)约 22s 墙钟 + 开场手势链 —— 默认 30s 用例上限不够, 抬到 120s */
      test.setTimeout(120_000);
      await stubFlags(page);
      await stubTrafficAdvancing(page);
      await openApp(page, skin);
      const drawer = await openTorrentTraffic(page);
      await rearmTrafficPoll(page, drawer);

      /* 页面侧 rAF 采样器(只读): 每帧记 xsLen / splits 长度与首刻位 / 判定帧计数(st.xs0 每
       * 判定帧必新值 —— distinct 计数即已观察判定帧数); 满 POLLS+1 个判定帧收口。
       * u.axes[0]._splits 是 uPlot 每次绘制回填的刻位真值数组(网格/轴标同源; 注意 .splits 是
       * 生成器函数, vendor 1.6.32 实证: t._splits = t.splits(...) —— 读它不碰生产内部)。 */
      await page.evaluate(`(() => {
        const vm = ${INST};
        window.__g4 = { frames: [], xs0s: new Set(), done: false };
        const tick = () => {
          const s = window.__g4;
          if (s.done) return;
          const u = vm._qbCharts && vm._qbCharts.torrent;
          const sp = u && u.axes && u.axes[0] && u.axes[0]._splits;
          if (u && u.data && u.data.length && sp && sp.length) {
            const xs = u.data[0];
            const st = u._qbBeat;
            if (st && st.xs0 != null) s.xs0s.add(st.xs0);
            s.frames.push({
              xsLen: xs.length,
              splitsLen: sp.length,
              splits0: sp[0],
            });
            if (s.xs0s.size >= ${POLLS + 1}) s.done = true;
          }
          requestAnimationFrame(tick);
        };
        requestAnimationFrame(tick);
      })()`);
      await expect.poll(() => readInst(page, 'window.__g4 === undefined ? false : window.__g4.done === true'), {
        message: `${POLLS} 轮压缩轮询未在预算内采满(轮询 2s 一拍, 约 ${POLLS * 2}s; 超时=轮询链路断了)`,
        timeout: 60_000,
      }).toBe(true);
      const frames = await page.evaluate(() => window.__g4.frames);
      expect(frames.length, `采样窗应覆盖 >= ${POLLS + 1} 帧(判定帧全被观察到, 量具没空转)`)
        .toBeGreaterThanOrEqual(POLLS + 1);

      /* A4 本体 1: 显示列点数恒 31(dx0 = 30 格非整格滚动, F5 补尾格不触发 —— 点数漂移即回潮) */
      const lens = [...new Set(frames.map((f) => f.xsLen))];
      expect(lens, `全采样窗点数集合必须单值 [31](实测 ${JSON.stringify(lens)}) —— 点数漂移即 `
        + '显示列形态回潮(旧 ceil 栅格的 k/k+1 方波 / 补尾格误触发)').toEqual([31]);

      /* A4 本体 2: split 集稳定 —— 长度恒定(A4 量法「split 数分布单峰」) */
      const slens = [...new Set(frames.map((f) => f.splitsLen))];
      expect(slens.length, `splits 长度集合必须单值(实测 ${JSON.stringify(slens)}) —— 中段 pop 即多值`)
        .toBe(1);
      expect(slens[0], 'splits 长度必须为正(uPlot 真刻位在场)').toBeGreaterThan(0);

      /* A4 本体 3: 刻度只自然滑入滑出 —— 首刻位逐帧单调不减(窗口整体右移, 刻位不回跳) */
      for (let i = 1; i < frames.length; i++) {
        expect(frames[i].splits0, `第 ${i} 帧首刻位 ${frames[i].splits0} 不得小于前帧 `
          + `${frames[i - 1].splits0}(窗口右移中刻位回跳 = split 集中段 pop)`).toBeGreaterThanOrEqual(frames[i - 1].splits0);
      }
    });
  }
});

test.describe('R1 处置 · hour 段窗(3天档)栅格语义: floor+1 形状 + 轮询节奏=采样间隔(F7/D6 全窗统一, plan 26-11-14-1313 §07)', () => {
  installRuntimeErrorGuard(test);

  for (const skin of SKINS) {
    test(`[${skin}] 切「3天」: 轮询节奏=采样间隔 1.5s(F7/D6 全窗统一, 不吃桶宽 3600)+ 点数形状 73=72+1(末桶=进行中桶且有观测) @fast`, async ({ page }) => {
      /* R1(plan §07)处置行「hour 面 e2e 回归」的最小落点: 3d/7d/30d 消费 agg hour 行,
       * 桶宽恒 3600s(traffic_grid.py:69-71); F3 floor+1 后 3天窗 = 72 整小时 + 1 进行中
       * 桶 = 73 点(30天窗同口径 721=720+1)。桩恒回同一份 hour 帧(窗口档回切不换数据),
       * 形状断言全走 expect.poll; 轮询节奏自 F7/D6(26-11-15-1104)= meta.sample_interval_s
       * 全窗统一(桩 si=1.5 -> 1.5s/拍) —— 旧口径「桶宽 3600 被夹到 600s 上界」正式反转,
       * 长窗一拍迟钝 10 分钟的形态即回潮。 */
      test.info().annotations.push({ type: 'note', description: 'R1 hour 面 e2e 回归' });
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

      /* R1 面 1(F7/D6 改判, plan 26-11-15-1104): 轮询节奏 = meta.sample_interval_s(生效
       * 采样间隔)全窗统一 —— hour 段窗桶宽 3600s 不再被消费成轮询周期; 桩 si=1.5 -> 1.5s */
      await expect.poll(() => readInst(page, 'vm._qbPollMs("torrent")'), {
        message: '轮询节奏未落到采样间隔档(F7/D6 全窗统一 —— 读回 interval_s 桶宽即旧口径回潮)',
        timeout: 15_000,
      }).toBe(1500);

      /* R1 面 2: 点数形状 = floor+1 的 73 = 72 整小时 + 1 进行中桶, 且窗口跨度恰 72 格 */
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
      expect(shape.span, 'hour 窗跨度必须恰 72 x 3600s(73 点 = 72 整桶 + 1 进行中桶, floor+1)')
        .toBe(72 * HOUR_INTERVAL);
      expect(shape.tailUp, '末桶(进行中桶)必须有观测(S7 pending_agg 合成段后的生产形态)')
        .toBeGreaterThan(0);
    });
  }
});

/* ============================================================================ */
/* A4-b(issue 26-11-17-0936 三次根因纠正): 每拍 +1 桶真实几何下 x 轴首刻位逐帧单调、
 * 标签每帧与刻位同源、右缘不多画一条纵线。
 *
 * 为什么 A4 本体没抓到: A4 用每拍 +30 桶(整窗)压缩桩, dx0=30 格走 rewin 瞬时落地、根本
 * 不播 L0, 从不进入末帧 ulp 区。生产每拍 +1 桶(轮询=桶宽=1.5s)播 L0, 末帧 rem=(1-p)^3
 * 逼近 0 时 x.min 落在刻度整数边界前一丁点(120.9999788 而非 121.0), uPlot time splits
 * 据该残差把首刻位低一格(125->124), 下一帧收敛帧精确 121.0 又恢复 —— 单帧刻位/网格线
 * 回跳。钳零修掉后暴露第二层: 收敛帧 scale 与末帧逐位相同, uPlot 不重算 axes, 冻结
 * 标签滞留下一拍。去掉冻结后暴露第三层: L0 钳零令收敛帧 vMax 精确压到 5s 整点,
 * uPlot 把落在右边界的刻度也画出来(最右多一条纵线 N 12->13), 下一拍退 1.5s 又消失,
 * 恰成用户所见「每两拍跳一次」。本用例逐帧采 _splits 全量 + _values[0], 三路一起堵。
 * ============================================================================ */
test.describe('A4-b 每拍 +1 桶真实几何 · 末帧刻位不回跳 + 标签同源 + 右缘不多线(issue 26-11-17-0936)', () => {
  installRuntimeErrorGuard(test);

  const N1 = 41;   // 1m 窗 60/1.5 = 40 整桶 + 1 进行中桶
  test('[chromium] L0 逐帧 x 首刻位单调不减(末帧 ulp 回跳不回潮) @fast', async ({ page }) => {
    test.setTimeout(90_000);
    // 锚到 15s 网格(1.5s 与 5s 的最小公倍数): 首拍末桶 xs[40] 必精确压 5s 整点,
    // 让「vMax 落整点多画一条最右纵线」的第三层根因在本用例中确定性复现, 不靠相位碰运气。
    const b0 = Math.floor(Date.now() / 1000 / 15) * 15 - (N1 - 1) * 1.5;
    let calls = 0;
    await stubFlags(page);
    await page.route('**/api/traffic/qb/torrent/*', (route) => {
      const base = b0 + (calls++) * 1.5;   // 每拍 +1 桶(生产真实: 轮询=桶宽=1.5s)
      const points = new Array(N1).fill(null).map((_, i) => ({ t: base + i * 1.5, dl: 2000, up: 1000 }));
      return route.fulfill({ json: {
        points, totals: points.map((p) => ({ ...p })), limits: [],
        meta: { window: '1m', interval_s: 1.5, sample_interval_s: 1.5, source: 'qb', stale: false,
          server_started_at: base - 3600 },
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
    await drawer.locator('.drawer-tabs button', { hasText: /^常规 / }).click();
    await drawer.locator('.drawer-tabs button', { hasText: /^流量 / }).click();
    await expect(drawer.locator('.qb-chart-host canvas')).toBeVisible({ timeout: 15_000 });
    await expect.poll(() => readInst(page, 'vm._qbPollMs("torrent")'), { timeout: 15_000 }).toBeLessThanOrEqual(2100);

    /* 逐帧采 _splits 全量(只读运行态回填值, 见 pitfalls/uplot-axes-splits-generator)与
     * _values[0]。满 12 个 xs0 收口: 1.5s 步长要 10 拍才回到 15s 网格整点, 12 拍覆盖
     * 至少一个「vMax 精确压 5s 整点」的收敛帧, 让右缘多线确定性复现。 */
    await page.evaluate(`(() => {
      const vm = ${INST};
      window.__a4b = { frames: [], lastXs0: null, done: false };
      const tick = () => {
        const s = window.__a4b;
        if (s.done) return;
        const u = vm && vm._qbCharts && vm._qbCharts.torrent;
        if (u && u.data && u.data.length && u.axes && u.axes[0]) {
          const st = u._qbBeat;
          const sp = u.axes[0]._splits;
          const lv = u.axes[0]._values;
          if (sp && sp.length && st && st.xs0 != null) {
            s.frames.push({
              sp0: sp[0], spN: sp[sp.length - 1], spCount: sp.length,
              xs0: st.xs0, vMin: u.scales.x.min, vMax: u.scales.x.max,
              lab0: lv && lv[0],
              expectLab0: vm._qbTickLabel(sp[0], vm.qbCurScope || 'torrent'),
              frozen: "_qbTickFreeze" in u || !!u._qbTickFreeze,
              pending: "_qbTickFreezePending" in u || !!u._qbTickFreezePending,
            });
            if (s.xs0s === undefined) s.xs0s = new Set();
            s.xs0s.add(st.xs0);
            if (s.xs0s.size >= 12) s.done = true;
          }
        }
        requestAnimationFrame(tick);
      };
      requestAnimationFrame(tick);
    })()`);
    await expect.poll(() => readInst(page, 'window.__a4b.done'), { timeout: 45_000 }).toBe(true);
    const frames = await page.evaluate(() => window.__a4b.frames);
    expect(frames.length, '采样窗应覆盖多帧(L0 逐帧面非空)').toBeGreaterThan(20);

    /* 本体 1: 首刻位逐帧单调不减 —— 末帧 ulp 残差会让 sp0 低一格后下一帧恢复, 即回潮 */
    for (let i = 1; i < frames.length; i++) {
      expect(frames[i].sp0, `第 ${i} 帧首刻位 ${frames[i].sp0} 不得小于前帧 ${frames[i - 1].sp0}`
        + '(L0 末帧残差令 splits 首刻位回跳 = issue 26-11-17-0936 根因回潮)')
        .toBeGreaterThanOrEqual(frames[i - 1].sp0);
    }

    /* 本体 2(三次纠正): tick freeze 已整体退役 —— 采样面上两枚状态字段都不许存在/为真,
     * 且**每一帧**标签都等于当前刻位的现算值(不再有「只钉非冻结帧」的豁免口)。旧机制
     * 只冻文字不冻刻位, 文字补刷新只跟 sp0 跨刻度走, 与右缘纵线事件错相跳。 */
    for (const f of frames) {
      expect(f.frozen || f.pending, 'x 轴 tick freeze 状态必须整体退役(起拍挂 pending 回潮即失败)')
        .toBe(false);
      expect(f.lab0, `刻位 ${f.sp0} 的标签 ${f.lab0} 必须等于现算值 ${f.expectLab0}`
        + '(标签未逐帧从实时 _splits 现算 = issue 26-11-17-0936 第三次根因回潮)')
        .toBe(f.expectLab0);
    }

    /* 本体 3(三次纠正): 右缘刻位恒 < vMax - ε。vMax 精确压 5s 整点时 uPlot 原生 splits
     * 会把该刻位也算进来, 最右多画一条纵线; 下一拍 vMax 退 1.5s 又消失 —— 每两拍一跳。
     * _qbDropRightEdgeSplits 挂上后该刻位恒被丢掉, 本断言直接钉住行为面。 */
    for (const f of frames) {
      const eps = Math.max(1e-9, Math.abs(f.vMax) * 1e-12);
      expect(f.spN, `第 ${frames.indexOf(f)} 帧右缘刻位 ${f.spN} 不得贴到 vMax ${f.vMax}`
        + '(右缘整点刻位过滤失效 = 最右纵线每两拍进出, issue 26-11-17-0936 第三次根因回潮)')
        .toBeLessThan(f.vMax - eps);
    }
    /* 同一组 scale(min,max) 必须给出同一组 splits —— 刻位数不得随拍相位翻转(12↔13)。
     * 按 vMin|vMax 逐字分组, 批内 spCount 恒等; 生产首拍锚到 15s 网格, 必覆盖压整点帧。 */
    const batch = new Map();
    for (const f of frames) {
      const key = f.vMin + '|' + f.vMax;
      if (!batch.has(key)) batch.set(key, new Set());
      batch.get(key).add(f.spCount);
    }
    for (const [key, counts] of batch) {
      expect(counts.size, `同一视口 ${key} 的刻位数应恒定, 实得 ${[...counts].join(',')}`
        + '(同一 scale 两次绘制出不同刻位数 = 纵线跳变)').toBe(1);
    }
    const boundaryFrames = frames.filter((f) => Math.abs(f.vMax % 5) < 1e-6);
    expect(boundaryFrames.length, `采样窗应覆盖 vMax 精确压 5s 整点的帧(首拍锚 15s 网格);`
      + ` 实得 vMax 样本 ${[...new Set(frames.map((f) => f.vMax))].slice(0, 14).join(', ')}`)
      .toBeGreaterThan(0);
  });
});
