// @ts-check
import { expect, test } from '@playwright/test';
import { SKINS } from './harness.mjs';
import { collectRuntimeErrors } from './lib/errors.mjs';
import { openApp } from './lib/gestures.mjs';
import { INST, readInst } from './lib/vm.mjs';
import { pumpStart, pumpStop, pumpStatus, pumpT0, waitStreamLive } from './lib/traffic-stream.mjs';
import { installRouteCleanup } from './lib/route-cleanup.mjs';

installRouteCleanup(test);   // 本文件全部用例收尾时卸载全部 route.fetch 桩(收尾竞态兜底, 合流接线)

/**
 * 运行期错误把关(手工面, 不装公共守阵 —— settings-backup 失败路径组同款先例): 用例 2/3
 * 的断言对象**就是**失败路径(票据 503 / stream abort), Chromium 网络层对每个失败响应都记
 * 一条 console.error("Failed to load resource: ...") —— 那是测试注入的已知噪音而非页面
 * 运行期错误。三案统一改手工断言: pageerror 为零 + console.error 只许已知网络噪音
 * (用例 1 零噪音; 用例 2 只许 ERR_FAILED; 用例 3 只许 503) —— 比全量静默更强。
 * allowedPattern 语义(评审 T4b #4): null = **零网络噪音放行**(一条都不许有), 非 null =
 * 只放行匹配该模式的网络噪音 —— 不再有「null 恒真放行任意条数」的口径(旧 `!pattern ||`
 * 与用例 1 的「零噪音」声明相反)。
 */
function assertNoRealRuntimeErrors(errors, allowedPattern, label) {
  const pageErrors = errors.filter((t) => t.startsWith('pageerror:'));
  expect(pageErrors, `${label} 无页面运行期错误:\n${pageErrors.join('\n')}`).toEqual([]);
  const noise = errors.filter((t) => t.startsWith('console.error: Failed to load resource')
    && !!allowedPattern && allowedPattern.test(t));
  expect(errors.length, `${label} 除已知网络噪音外零 console.error/pageerror:\n`
    + `${errors.filter((t) => !noise.includes(t)).join('\n')}`).toBe(noise.length);
}

/**
 * SSE 主路径三案(plan 26-11-18-0037 阶段 3 验收新增: 事件到达->渲染延迟 / 徽标可见性 /
 * 降级路径)—— T4a 后取数主路 = 票据 POST /api/events/ticket -> EventSource
 * /api/traffic/qb/stream(scope=torrent:<hash>), 判定帧节拍源 = 事件到达。桩面:
 *   · 票据与 stream 两端点是**真生产代码**(ui_harness = 真 create_app), 不另造假端点;
 *   · 数据面 = 事件泵(/__harness__/traffic_stream, e2e/lib/traffic-stream.mjs): 把每 tick
 *     显示点真值按到生产同一发布点(publish_traffic_batch), 帧走真 SSE 线(一次性票据/
 *     心跳/seq/扇出全真); GET 桩静态列承担初始列 + 对账基准 —— 用例 3(降级案)例外: 其
 *     GET 桩每请求现算 base(降级轮询每 si 一发都回当前墙钟列, 非静态列; 评审 T4b #5)。
 * 三案断言面(DOM 状态机/管线延迟)与皮肤无关, 单皮肤(chromium)足够 —— 双皮肤翻倍不增
 * 判别力, @fast 预算留给时序窗。
 *
 * 用例 1 渲染延迟: 泵每 2s 推一帧, 以泵 status 的 last_push_at(time.time, 与浏览器
 * Date.now 同主机时钟)为「样本落地」时刻, 断言每个落地后的首个判定帧(fxBeatAt)在
 * **< 1000ms** 内提交。阈值依据: 回环 e2e 实测量级 ~10-50ms(EventSource 派发 -> JSON
 * 解析 -> $nextTick -> _qbBeatStart 全程微任务/毫秒级), 1s = 20x 余量给足容器/GC 抖动;
 * 判别力 = 5/5 帧推送都各自在 1s 内出判定帧 —— 轮询级管线(GET 对账 30s/降级轮询 si)
 * 对 5 个连续推送的响应延迟必有一位远超 1s, 即红。fxBeatAt 只在 qbCurScope 对齐的真拍
 * 判定帧写入( torrent 流量页签在场 = 对齐), 是「判定帧提交」的页面侧权威读数。
 *
 * 用例 2 徽标可见性(D3 停流可见): 泵推 2 帧后停推 -> 静默(>3 x si = 6s, R7)起显
 * 「滞后 Ns」(诚实等待, N = 末样本 ts 落后墙钟秒数, watchdog 1s 步进); 恢复推帧 -> 消显;
 * 流断连(route abort -> onerror -> retry) -> 「已断连」; 放行重连(真换票重开) ->
 * 来帧 -> 消显。徽标 = 尾点旁 DOM 常驻层(.qb-stall-badge), 文案两态互斥。
 *
 * 用例 3 降级路径(E7): 票据恒 503 -> 连续 3 轮建流失败(~6-7s) -> degraded ->
 * GET 轮询接管(每 si 一发), 图照常出数据(降级不是白屏)—— 降级态徽标「已断连」照显。
 * 恢复面(60s 静默重试/重开抽屉回主路)在用例 2 的重连段已覆盖(真换票重开来帧消显)。
 */

const N = 60;
const INTERVAL = 2;

/** 造一帧恒定 payload(静态列; 推进面归事件泵) */
function makePayload(base) {
  const points = new Array(N).fill(null);
  const totals = new Array(N).fill(null);
  for (let i = 0; i < N; i++) {
    const t = base + i * INTERVAL;
    points[i] = { t, dl: 2000, up: 1000 };
    totals[i] = { t, dl: 2000, up: 1000 };
  }
  return {
    points,
    totals,
    limits: [],
    meta: {
      window: '24h',
      interval_s: INTERVAL,
      sample_interval_s: INTERVAL,
      schema: 2,
      stride: 1,
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

/** 静态 GET 列桩(base 固定一次算定, 每请求回同一帧; 泵 t0 锚墙钟 pumpT0 —— 见 lib 头注,
 * 列末 t 不再作 t0 锚) */
async function stubTrafficColumn(page) {
  const b0 = Math.floor(Date.now() / 1000 / INTERVAL) * INTERVAL - (N - 1) * INTERVAL;
  await page.route('**/api/traffic/qb/torrent/*', (route) =>
    route.fulfill({ json: makePayload(b0) }));
  return b0 + (N - 1) * INTERVAL;
}

/** 打开种子流量页签(traffic-fx-frames 同款手势链) */
async function openTorrentTraffic(page) {
  await page.click('nav.tabs [data-view="torrents"]');
  await expect(page.locator('.torrent-row').first()).toBeVisible({ timeout: 15_000 });
  await page.dblclick('.torrent-row >> nth=0', { force: true });
  const drawer = page.locator('.drawer-dock > .drawer');
  await expect(drawer).toBeVisible({ timeout: 5_000 });
  await drawer.locator('.drawer-tabs button', { hasText: /^流量 / }).click();
  await expect(drawer.locator('.qb-chart-host canvas')).toBeVisible({ timeout: 15_000 });
  return drawer;
}

/** 泵 scope = 前端实际订阅串(st.streamScope = "torrent:" + drawer.hash) */
async function torrentStreamScope(page) {
  const hash = await readInst(page, 'vm.drawer && vm.drawer.hash');
  if (!hash) throw new Error('drawer.hash 取不到(种子抽屉未开)');
  return 'torrent:' + hash;
}

/* ============================================================================ */

test.describe('SSE 主路径 · 渲染延迟 / 徽标可见性 / 降级路径(plan 26-11-18-0037 阶段 3)', () => {
  test('[chromium] 事件到达->渲染延迟: 每帧推送的判定帧提交 < 1s(毫秒级管线的 e2e 级证据) @fast', async ({ page, request }) => {
    const runtimeErrors = collectRuntimeErrors(page);   // goto 前挂监听
    test.setTimeout(90_000);
    await pumpStop(request).catch(() => null);
    await stubFlags(page);
    await stubTrafficColumn(page);
    await openApp(page, SKINS[0]);
    await openTorrentTraffic(page);   // 流 = 页签打开即连(E1): 先开图再等 live
    await waitStreamLive(page);
    await pumpStart(request, { scope: await torrentStreamScope(page), si: 2, t0: pumpT0(2) });

    /* 5 个连续推送各测一次: 等泵落新帧(status.last_push_at 前进 = 样本落地时刻, 避开
     * 读到旧帧的相位) -> 等 fxBeatAt 越过该时刻(该帧的判定帧已提交) -> 记延迟。 */
    const SAMPLES = 5;
    let prevPushAt = ((await pumpStatus(request)).last_push_at) || 0;
    const lats = [];
    const beatAts = [];
    for (let k = 0; k < SAMPLES; k++) {
      await expect.poll(async () => (await pumpStatus(request)).last_push_at, {
        message: `第 ${k + 1} 帧未在 5s 内落地(泵 si=2s 节拍断了)`, timeout: 5000,
      }).toBeGreaterThan(prevPushAt);
      const st = await pumpStatus(request);
      const pushAtMs = st.last_push_at * 1000;
      prevPushAt = st.last_push_at;
      await expect.poll(() => readInst(page, 'vm.fxBeatAt || 0'), {
        message: `第 ${k + 1} 帧(落地于 ${new Date(pushAtMs).toISOString()})后 1s 内无判定帧提交`
          + '(管线延迟超阈或帧没驱动判定帧)', timeout: 5000,
      }).toBeGreaterThan(pushAtMs);
      const beatAt = await readInst(page, 'vm.fxBeatAt || 0');
      expect(beatAt, 'fxBeatAt 必须是墙钟毫秒(判定帧提交时刻)')
        .toBeGreaterThan(1_600_000_000_000);
      lats.push(beatAt - pushAtMs);
      if (beatAts.length) {
        expect(beatAt, '判定帧提交时刻必须逐帧严格递增(每帧推送各驱动一次判定帧)')
          .toBeGreaterThan(beatAts[beatAts.length - 1]);
      }
      beatAts.push(beatAt);
    }
    /* 本体: 每帧延迟 < 1000ms(阈值依据见文件头 —— 实测 ~10-50ms, 1s = 20x 余量; 判别力
     * = 5/5 推送各自出帧, 轮询级管线必红)。 */
    for (let k = 0; k < lats.length; k++) {
      expect(lats[k], `第 ${k + 1} 帧渲染延迟 ${lats[k]}ms 必须 < 1000ms(事件到达->判定帧提交)`)
        .toBeLessThan(1000);
    }
    assertNoRealRuntimeErrors(runtimeErrors, null, '渲染延迟案');   // 本案无注入失败: 零网络噪音
  });

  test('[chromium] 徽标可见性: 停推 >3x si 出「滞后 Ns」/ 恢复推帧消显 / 流断连出「已断连」/ 重连来帧消显 @fast', async ({ page, request }) => {
    const runtimeErrors = collectRuntimeErrors(page);   // goto 前挂监听
    test.setTimeout(120_000);
    await pumpStop(request).catch(() => null);
    await stubFlags(page);
    await stubTrafficColumn(page);
    await openApp(page, SKINS[0]);
    const drawer = await openTorrentTraffic(page);
    const badge = drawer.locator('.qb-stall-badge');
    await waitStreamLive(page);

    /* 阶段 1: 泵恰推 2 帧后停推(si=2 -> 静默阈值 3 x 2 = 6s)。来帧期徽标恒隐
     * (state=live 且 lastT 跟住墙钟 —— t0 锚墙钟 pumpT0, 建桩->开泵耗时不进入滞后量纲,
     * 评审 T4b #1), 断言基线 = 隐。 */
    await pumpStart(request, { scope: await torrentStreamScope(page), si: 2, t0: pumpT0(2), steps: 2 });
    await expect.poll(() => readInst(page,
      '(vm._qbCharts && vm._qbCharts.torrent && vm._qbCharts.torrent.data && vm._qbCharts.torrent.data[1])'
      + ' ? vm._qbCharts.torrent.data[1].length : 0'), {
      message: '2 帧未落袋(事件尾点未追加)', timeout: 15_000,
    }).toBe(N + 2);
    await expect(badge, '来帧期徽标必须隐藏(live 且末样本跟住墙钟)').toBeHidden();

    /* 阶段 2: 停推 -> 静默沿(>6s)起显「滞后 Ns」; 恢复推帧即消显(D3/R7: 诚实等待,
     * 恢复自动消显不等 watchdog 下一跳)。恢复泵 t0 同锚墙钟 pumpT0(评审 T4b #1): 静默期
     * 墙钟已前进, 续 lastT + si 会让新帧 lastT 仍落后墙钟(落后量 = 徽标检出耗时) —— 滞后
     * 量纲贴着 3 x si 阈值, 慢环境消显断言假红; 锚墙钟后新帧 lastT >= 墙钟, 消显与静默
     * 时长无关(显示列留静默期缺口, 无断言依赖)。 */
    await expect.poll(async () => (await badge.textContent()) || '', {
      message: '停推后 15s 内未出「滞后 Ns」徽标(静默 3 x si 判据/R7 徽标面回潮)',
      timeout: 15_000,
    }).toMatch(/^滞后 \d+s$/);
    const lastT = await readInst(page, 'vm._qbStreams && vm._qbStreams.torrent ? vm._qbStreams.torrent.lastT : 0');
    expect(lastT, '滞后量纲锚末样本 ts(lastT > 0)').toBeGreaterThan(0);
    await pumpStart(request, { scope: await torrentStreamScope(page), si: 2, t0: pumpT0(2), ttl: 60 });
    await expect.poll(async () => (await badge.textContent()) || '', {
      message: '恢复推帧后徽标未消显(D3: 恢复自动消显回潮)', timeout: 15_000,
    }).toBe('');

    /* 阶段 3: 流断连出「已断连」。route.abort 只拦**新请求**、掐不断已建立的 EventSource
     * 连接 —— 断连入口走真生命周期: 挂 abort 桩后页签切走再切回(流量页签重入 =
     * _qbStreamStart 先停后起, 新建流被 abort -> onerror -> retry 态, 徽标即「已断连」);
     * 快速放行后 3s 换票重开(真重连路径)-> 来帧 -> 消显。放行须在 failRun 撞满 3 轮
     * 降级(~6s)之前完成。 */
    await page.route('**/api/traffic/qb/stream*', (route) => route.abort());
    await drawer.locator('.drawer-tabs button', { hasText: /^常规 / }).click();
    await drawer.locator('.drawer-tabs button', { hasText: /^流量 / }).click();
    await expect(drawer.locator('.qb-chart-host canvas')).toBeVisible({ timeout: 15_000 });
    await expect.poll(async () => (await badge.textContent()) || '', {
      message: '断流后未出「已断连」徽标(retry 态徽标面回潮)', timeout: 5000,
    }).toBe('已断连');
    await page.unroute('**/api/traffic/qb/stream*');
    await expect.poll(async () => (await badge.textContent()) || '', {
      message: '重连来帧后徽标未消显(3s 换票重开 + 事件恢复面回潮)', timeout: 20_000,
    }).toBe('');
    await expect.poll(() => readInst(page,
      'vm._qbStreams && vm._qbStreams.torrent ? vm._qbStreams.torrent.state : null'), {
      message: '重连未回到 live 态', timeout: 15_000,
    }).toBe('live');
    /* 已知网络噪音 = abort 掉的建流请求(ERR_FAILED); 除此之外零运行期错误 */
    assertNoRealRuntimeErrors(runtimeErrors, /ERR_FAILED/, '徽标案');
  });

    test('[chromium] 降级路径(E7): 票据 503 x3 -> degraded -> GET 轮询接管仍出图 @fast', async ({ page, request }) => {
    const runtimeErrors = collectRuntimeErrors(page);   // goto 前挂监听
    test.setTimeout(120_000);
    await pumpStop(request).catch(() => null);
    await stubFlags(page);
    let getLoads = 0;
    await page.route('**/api/traffic/qb/torrent/*', (route) => {
      getLoads++;
      return route.fulfill({ json: makePayload(
        Math.floor(Date.now() / 1000 / INTERVAL) * INTERVAL - (N - 1) * INTERVAL) });
    });
    /* 票据端点桩恒 503(照真满额语义: {detail}, status 503 —— 生产 routes/events.py 同形)。
     * 开图前挂好 —— 首次换票就失败, 不留活流。 */
    await page.route('**/api/events/ticket', (route) =>
      route.fulfill({ status: 503, json: { detail: 'event ticket quota exhausted, retry later' } }));
    await openApp(page, SKINS[0]);
    const drawer = await openTorrentTraffic(page);
    await expect(drawer.locator('.qb-chart-host canvas')).toBeVisible({ timeout: 15_000 });

    /* E7 本体 1: 连续 3 轮建流失败(每轮 3s 换票重开, ~6-7s) -> degraded 落位 */
    await expect.poll(() => readInst(page,
      'vm._qbStreams && vm._qbStreams.torrent ? vm._qbStreams.torrent.degraded : null'), {
      message: '未进降级态(票据 503 x3 -> 降级链路断了)', timeout: 20_000,
    }).toBe(true);
    await expect.poll(() => readInst(page,
      'vm._qbStreams && vm._qbStreams.torrent ? vm._qbStreams.torrent.state : null'), {
      message: '降级态状态字未落位', timeout: 10_000,
    }).toBe('degraded');

    /* E7 本体 2: 降级态徽标「已断连」照显(D3: 降级 = 两条取数路径都断的诚实文案) */
    const badge = drawer.locator('.qb-stall-badge');
    await expect.poll(async () => (await badge.textContent()) || '', {
      message: '降级态未出「已断连」徽标', timeout: 10_000,
    }).toBe('已断连');

    /* E7 本体 3: GET 轮询接管仍出图 —— 初始 GET(1) + 降级轮询(每 si=2s 一发)累计
     * >= 3 发, 显示列 = 桩列 60 点且图在(降级不是白屏)。 */
    await expect.poll(() => getLoads >= 3, {
      message: '降级后 GET 轮询未接管线(2s 内应每 si 一发)', timeout: 15_000,
    }).toBe(true);
    await expect.poll(() => readInst(page,
      '(vm._qbCharts && vm._qbCharts.torrent && vm._qbCharts.torrent.data && vm._qbCharts.torrent.data[0])'
      + ' ? vm._qbCharts.torrent.data[0].length : 0'), {
      message: '降级态显示列未落袋(轮询取数面断了)', timeout: 15_000,
    }).toBe(N);
    await expect(drawer.locator('.qb-chart-host canvas'), '降级态图必须仍在(降级不是白屏)')
      .toBeVisible();
    const before = getLoads;
    await expect.poll(() => getLoads > before, {
      message: '降级轮询停摆(5s 内无新 GET)', timeout: 10_000,
    }).toBe(true);
    /* 已知网络噪音 = 票据 503 注入(每次换票一条); 除此之外零运行期错误 */
    assertNoRealRuntimeErrors(runtimeErrors, /503/, '降级案');
  });
});
