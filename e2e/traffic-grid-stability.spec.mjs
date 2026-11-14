// @ts-check
import { expect, test } from '@playwright/test';
import { SKINS } from './harness.mjs';
import { installRuntimeErrorGuard } from './lib/errors.mjs';
import { openApp } from './lib/gestures.mjs';
import { INST, readInst } from './lib/vm.mjs';
import { installRouteCleanup } from './lib/route-cleanup.mjs';

installRouteCleanup(test);   // 本文件全部用例收尾时卸载全部 route.fetch 桩(收尾竞态兜底, 合流接线)

/**
 * A4(计划 26-11-14-1313 §01): 1m 窗 2s 桶连续观测(>=10 分钟)—— rewin 0 次、x 轴 split 集
 * 稳定(仅视口边界的自然滑入滑出, 无中段 pop)。
 *
 * 为什么不真跑 10 分钟: 真实轮询节奏 2s/拍 x 300 拍 = 600s 墙钟, e2e 预算内不可行 —— 量法
 * 等价在**数据时间**不在墙钟: F3(栅格 ceil->floor+1)要钉的判据本体是「W 恰为桶宽整倍时
 * n 与轮询相位无关」(rewin 判据 st.n !== n 因此恒 false), 本用例用「每次轮询恰好推进一整窗
 * (30 桶 = 60s 数据时间)」的压缩桩连续喂 10 轮(累计 300 桶 = 600s >= 10 分钟的 2s 桶连续
 * payload), 每轮都让数据窗整体右移。观测性质边界: 桩恒填 31 点, n 在本用例结构上不可能
 * 漂移(后端 ceil 栅格回潮时本用例不可见 —— 该面由 B1 的相位不变性电池承接, 本用例只钉
 * 前端消费面: n 恒定下 rewin 判据恒 false + splits 稳定的显示面)。又: 每轮 dx0 = 30 格 >
 * step x 2, 生产走瞬时落地路径, roll 动画期的逐帧面不在本用例域(由 traffic-fx-frames 的
 * 左移连续性用例承接)。10 轮真轮询(2s 周期)约 22s 墙钟, @fast 预算内。后端保证面: B1
 * 电池(相位不变性/t1 边界)已钉 _floor_buckets 的 n 恒等; 前端 rewin 判据面 =
 * qb_traffic_chart.js _qbBeatStart 的 st.n !== n(点数变化才 rewin) —— 两面在本用例的显示面合流。
 *
 * 断言面(observational, 不碰生产内部变量):
 *   · rewin 0 次: rewin 的可观测定义就是点数变化(st.n !== n) —— 全采样窗 xsLen 恒 31
 *     (floor+1: 1m 窗 2s 桶 = 30 整桶 + 1 进行中桶)即 rewin 恒 false;
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
      source: 'qb',
      stale: false,
      server_started_at: base - 3600,
    },
  };
}

/* ============================================================================ */

test.describe('A4 栅格稳定性 · 1m 窗 2s 桶连续观测: rewin 0 + split 集稳定(plan 26-11-14-1313)', () => {
  installRuntimeErrorGuard(test);

  for (const skin of SKINS) {
    test(`[${skin}] 10 轮压缩轮询(600s 数据时间): 点数恒 31(rewin 恒 false) + splits 长度恒定 + 首刻位不回跳 @fast`, async ({ page }) => {
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

      /* A4 本体 1: 点数恒 31 -> rewin(st.n !== n)恒 0 次(可观测定义 = 点数不变) */
      const lens = [...new Set(frames.map((f) => f.xsLen))];
      expect(lens, `全采样窗点数集合必须单值 [31](实测 ${JSON.stringify(lens)}) —— 点数漂移即 `
        + 'rewin 判据 st.n !== n 翻真(瞬时多格跳回潮: 旧 ceil 栅格的 k/k+1 方波)').toEqual([31]);

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

test.describe('R1 处置 · hour 段窗(3天档)栅格语义: floor+1 形状 + 桶宽 3600 消费(plan 26-11-14-1313 §07)', () => {
  installRuntimeErrorGuard(test);

  for (const skin of SKINS) {
    test(`[${skin}] 切「3天」: meta.interval_s=3600 被消费(轮询周期抬到 600s 夹取上限)+ 点数形状 73=72+1(末桶=进行中桶且有观测) @fast`, async ({ page }) => {
      /* R1(plan §07)处置行「hour 面 e2e 回归」的最小落点: 3d/7d/30d 消费 agg hour 行,
       * 桶宽恒 3600s(traffic_grid.py:69-71); F3 floor+1 后 3天窗 = 72 整小时 + 1 进行中
       * 桶 = 73 点(30天窗同口径 721=720+1)。桩恒回同一份 hour 帧(窗口档回切不换数据),
       * 静图断言; 轮询周期被 meta.interval_s 抬到 1h, 断言窗内无第二拍。 */
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

      /* R1 面 1: meta.interval_s=3600 被前端消费 —— 轮询周期实算 3600000ms, 被节奏内核
       * 夹取上限钳到 600s(_qbPollMs = clamp(interval_s x 1000, 1.5s, 600s), I1 口径;
       * 最初 fallback 30s 在 meta 落袋后的下一臂被抬到该档) */
      await expect.poll(() => readInst(page, 'vm._qbPollMs("torrent")'), {
        message: '轮询周期未抬到夹取上限档(meta.interval_s=3600 未被消费)', timeout: 15_000,
      }).toBe(600000);

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
