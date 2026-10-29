// @ts-check
import { expect, test } from '@playwright/test';
import { SKINS } from './harness.mjs';
import { installRuntimeErrorGuard } from './lib/errors.mjs';
import { openApp } from './lib/gestures.mjs';
import { readInst } from './lib/vm.mjs';

/**
 * qB 流量图「缺口分区段」悬停文案的**真浏览器**守阵 —— issue「种子添加之前的空白被说成
 * qB 断联」回归栅。静态守阵(test_webui_static_dom_panel.py)只能钉字面量与模块级纯函数,
 * 它验不到这条链: uPlot setCursor 钩子 -> scope 化 hoverIdx -> computed -> 模板渲染。
 * 这就是本 spec 存在的理由 —— **真实鼠标悬停**落在 null 桶上时, 浮出的到底是那一句。
 *
 * 事故与修法(2026-10-30, 用户报「不符合实际情况」):
 *   旧实现对所有 null 桶一律出「无采样 · 程序未运行或 qB 断联」—— 判据**只有一条**
 *   (这一格是 null), 于是把三种完全不同成因的东西合并成同一种说法:
 *     ① 数据链首之前(种子刚添加 / 更早就没这个对象的数据)   → 系统只知道"没有数据";
 *     ② 数据链中间的洞(前后都有观测)                        → 「中断」才是可观测事实;
 *     ③ 数据链尾之后(种子已删 / 已停)                       → 同理只知道"没有数据"。
 *   修法 = 先按 chain bounds 判区段(_qbChainBounds/_qbGapZone, 纯函数已由 node 电池覆盖),
 *   再由 qbCurGapText 按「区段 × 作用域」出句: mid 三挂点统一「采样中断 · 该时段无数据」;
 *   outside 只陈述「该时段没有**这个对象**的数据」, 主语按作用域取 —— 种子态才是「此种子」,
 *   全局图上写「此种子」是又一个凭空编造的主语。
 *   ⇒ 本 spec 因此必须覆盖**两个作用域**: 种子(三区段) + 全局(主语分支)。
 *
 * 为什么边界**不用** added_on 推算(虽然 drawer.detail 上读得到): added_on 是「最近一次
 *   被塞回 qB」的时刻 —— 跳检就是删同 hash 再重加(ops_mod.py 的 torrents_delete ->
 *   torrents_add), 而流量按 infohash 长期留存、删种不清理(traffic_store.py)。拿 added_on
 *   切一刀会把跳检之前的**真实历史数据**整段标成「尚未添加」—— 与要修的失真同型反向。
 *   边界只能是「本帧数据链从哪到哪」, 这也是纯函数的判据。
 *
 * 桩口径(同族 spec 纪律: 不写 harness 共享的磁盘/config):
 *   · /api/webui/flags  —— 在真响应上**只覆盖** qb_traffic_enabled=true(流量页签入口有
 *     总门 v-if=qbTrafficOn, 桩服务没开这段 => 进不去流量页签); 其余旗标放行真值, 不连带改
 *     别的 UI 开关;
 *   · /api/traffic/qb/torrent|global —— 造一份**真契约形状**的帧(points/totals/limits/meta,
 *     键名照 /api/traffic/qb/* 契约: points 元素 = null | {t, dl, up}), 区段拓扑 = 三段。
 *   刻意偏差一处并说明: points **长度恒 60 桶**(点过「30分」后 window=30m / interval_s=30,
 *   这时 1800s / 30s = 60 桶**恰是契约实数**、零偏差; 在此之前那一下首拉仍是默认 24h, 也会
 *   拿到同一份 60 桶 —— 前端不校验「points 长度 vs window」)。为什么不真给 24h 的 2880 桶:
 *   2880 桶摊在 ~700px 图面上是 0.24px/桶, 鼠标无法稳定落在指定桶上, 而「落在哪一桶」正是
 *   本 spec 的断言对象。区段拓扑与真实同形, 长度不是本轮的守阵面。
 *   · 时刻取一个**静态基准**(测试起算时算一次, 之后每轮轮询回同一帧): 轮询会让图按节拍
 *     重拉, 若 payload 跟着 Date.now() 走, 悬停落点会在两次读数之间漂移。
 */

/** 帧(60 桶 · 桶宽 30s)的区段拓扑: [起点, 止点] 闭区间, 逐字对应 makePayload 的拼装序 */
const LEAD = [0, 14];      // 数据链首之前 -> outside
const HEAD = [15, 24];     // 数据链(有观测)
const MID = [25, 29];       // 数据链中间的洞 -> mid
const TAIL_SEG = [30, 39];  // 数据链(有观测)
const TRAIL = [40, 59];     // 数据链尾之后 -> outside
const N = 60;
const INTERVAL = 30;

/** 取区段中点(而非边界桶): 标定的亚像素误差不至于落错段 */
const mid = ([a, b]) => Math.floor((a + b) / 2);

/** 造一帧选定区段的 points/totals(points 元素 = null | {t, dl, up}, 契约同 /api/traffic/qb/*) */
function makePayload(window, base) {
  const points = new Array(N).fill(null);
  const totals = new Array(N).fill(null);
  for (let i = 0; i < N; i++) {
    const t = base + i * INTERVAL;
    const live = (i >= HEAD[0] && i <= HEAD[1]) || (i >= TAIL_SEG[0] && i <= TAIL_SEG[1]);
    if (!live) continue;                       // 缺口桶 = null(契约: 无观测)
    points[i] = { t, dl: 2000, up: 1000 };     // 速率桶非零: 不走 template 的「0 B/s · 空闲/做种」行
    totals[i] = { t, dl: 2000, up: 1000 };     // 累计增量(统计栏 qbCurSummary 求和用, 只需非 null)
  }
  return {
    points,
    totals,
    limits: [],
    meta: {
      window,                                  // 回显查询串: 同一份桩跨 window 重拉也不说谎
      interval_s: INTERVAL,                    // 30m/24h 同为 raw 段窗, 桶宽 = 采样间隔 30s(契约真值)
      source: 'qb',
      stale: false,
      // 远在「链末桶前一桶起点」之前 => _qbSeamHint 出 null(不给「数据接缝中」行)。本 spec 不
      // 验接缝那一支(node 电池 + 静态守阵已覆盖), 这里把它排除掉免得两条注解互相干扰。
      server_started_at: base - 3600,
    },
  };
}

/** 帧基准一次算定(末桶 ≈ 当下, 同真数据右沿语义); 轮询重拉取同一帧 => 悬停落点不漂移 */
async function stubQbTraffic(page, paths) {
  const base = Math.floor(Date.now() / 1000 / INTERVAL) * INTERVAL - (N - 1) * INTERVAL;
  for (const p of paths) {
    await page.route(p, (route) => {
      const w = new URL(route.request().url()).searchParams.get('window') || '24h';
      return route.fulfill({ json: makePayload(w, base) });
    });
  }
}

/** flags 桩: 只翻 qb_traffic_enabled 这一个比特, 其余放行真值(避免连带改掉别的 UI 门) */
async function stubFlags(page) {
  await page.route('**/api/webui/flags', async (route) => {
    const json = await (await route.fetch()).json();
    return route.fulfill({ json: { ...json, qb_traffic_enabled: true } });
  });
}

/**
 * 桶 index -> 鼠标落点 px: **两点标定**而非按公式推 —— uPlot 的 x 尺取值域、纵轴槽宽、
 * 设备像素比都不是本 spec 该猜的东西; 标定等于在这**张**图上实测量:
 *   左探头 -> idx_a, 右探头 -> idx_b; 等距栅格下 (idx, px) 严格线性 => 目标 px 一解即得。
 * 落点后回读 hoverIdx 断言命中(D4 第②类 evaluate: 这是「我点在哪一桶」的唯一权威读数 ——
 * 光看 tooltip 的时刻会因刻度与 fmtTime 粒度分不清相邻桶)。
 *
 * !参考盒必须是 **.u-over**(uPlot 的鼠标交互层, 实测 1298xN 宿主上它是 x+84 起、宽 1273
 *   的那块), **不能**用 .qb-chart-host: 宿主盒含 84px 纵轴槽与 x 轴槽, 拿它推满宽的右探头
 *   会落在 u-over 之外 => uPlot 收不到 mousemove, hoverIdx 回落 -1(踩过, 首跑四红)。
 *
 * @param {import('@playwright/test').Page} page
 * @param {import('@playwright/test').Locator} drawer
 * @param {string} idxKey —— 该类图的 hoverIdx 字段名(scope 化: torrent/global 各一份)
 * @param {number} target
 */
async function hoverBucket(page, drawer, idxKey, target) {
  const over = drawer.locator('.qb-chart-host .u-over');
  const box = await over.boundingBox();
  if (!box) throw new Error('uPlot 交互层未渲染(.qb-chart-host .u-over 取不到盒)');
  const y = box.y + box.height / 2;                 // 竖直居中: 必在交互面内
  const probe = async (x) => {
    await page.mouse.move(x, y);
    return Number(await readInst(page, `vm.${idxKey}`));
  };
  const xa = box.x + 2;                             // 两端各留 2px, 不出 u-over
  const xb = box.x + box.width - 2;
  const ia = await probe(xa);
  const ib = await probe(xb);
  expect(ia, `左探头(${xa}px)没拿到桶(hoverIdx=${ia}) —— 落点在 u-over 之外`).toBeGreaterThanOrEqual(0);
  expect(ib, `右探头(${xb}px)没拿到桶(hoverIdx=${ib}) —— 落点在 u-over 之外`).toBeGreaterThan(ia);
  const x = xa + ((target - ia) * (xb - xa)) / (ib - ia);
  const got = await probe(x);
  expect(got, `标定后落点未命中目标桶(期望 ${target}, 实测 ${got}; 标定 [${ia}@${xa}px, ${ib}@${xb}px])`)
    .toBe(target);
  return { x, y };
}

/** 悬停 tooltip 本体(模板里它是 .qb-chart 的兄弟, 绝对定位) */
const tipLines = (drawer) => drawer.locator('.hist-tip');

/** 打开种子流量页签 + 点「30分」(这条路一并验 _qbSetWindow 重拉重画) */
async function openTorrentTraffic(page) {
  await page.click('nav.tabs [data-view="torrents"]');
  await expect(page.locator('.torrent-row').first()).toBeVisible({ timeout: 15_000 });
  await page.dblclick('.torrent-row >> nth=0', { force: true });
  const drawer = page.locator('.drawer-dock > .drawer');
  await expect(drawer).toBeVisible({ timeout: 5_000 });
  await drawer.locator('.drawer-tabs button', { hasText: /^流量$/ }).click();
  await expect(drawer.locator('.qb-chart-host canvas')).toBeVisible({ timeout: 15_000 });
  await drawer.locator('.hist-summary .qb-tabs button', { hasText: '30分' }).click();
  await expect.poll(async () => readInst(page, 'vm.qbTorrentWindow'),
    { message: 'qbSetWindow 未生效(窗口不是 30m)', timeout: 15_000 }).toBe('30m');
  return drawer;
}

/* ============================================================================ */

test.describe('种子流量图 · 缺口悬停分区段(不再是「一律断联」)', () => {
  installRuntimeErrorGuard(test);

  for (const skin of SKINS) {
    test(`[${skin}] 链首前/链中洞/链尾后三区段各出各句, 且都不再说「程序未运行或 qB 断联」 @fast`, async ({ page }) => {
      await stubFlags(page);
      await stubQbTraffic(page, ['**/api/traffic/qb/torrent/*']);
      await openApp(page, skin);
      const drawer = await openTorrentTraffic(page);
      const tip = tipLines(drawer);

      /* ① 链首之前 —— 用户报障的那一处: 旧文案在这里断言成「程序未运行或 qB 断联」 */
      await hoverBucket(page, drawer, 'qbTorrentHoverIdx', mid(LEAD));
      await expect(tip).toContainText('该时段无此种子数据');
      await expect(tip, '缺口文案仍在归因"为什么没有数据" —— 报障口径复辟').not.toContainText('断联');
      await expect(tip).not.toContainText('程序未运行');

      /* ② 对照组: 有观测的常规桶出速率行 —— 证明 ① 的结论不是"tooltip 恒显缺口文案" */
      await hoverBucket(page, drawer, 'qbTorrentHoverIdx', mid(HEAD));
      await expect(tip).toContainText('上传');
      await expect(tip).toContainText('下载');
      await expect(tip).not.toContainText('该时段无此种子数据');

      /* ③ 数据链中间的洞 —— 前后都有观测, 只有这里谈得上「中断」 */
      await hoverBucket(page, drawer, 'qbTorrentHoverIdx', mid(MID));
      await expect(tip).toContainText('采样中断 · 该时段无数据');
      await expect(tip, '链中洞被误判成链外(chain bounds 判据失灵)').not.toContainText('该时段无此种子数据');

      /* ④ 链尾之后 —— 与 ① 同源的另一半(旧实现同样把它说成断联) */
      await hoverBucket(page, drawer, 'qbTorrentHoverIdx', mid(TRAIL));
      await expect(tip).toContainText('该时段无此种子数据');
      await expect(tip).not.toContainText('采样中断');
    });
  }
});

test.describe('全局流量图 · 链外文案主语不写「此种子」', () => {
  installRuntimeErrorGuard(test);

  for (const skin of SKINS) {
    test(`[${skin}] 全局图链首前 = 「该时段无数据」, 链中洞 = 「采样中断 · 该时段无数据」 @fast`, async ({ page }) => {
      await stubFlags(page);
      await stubQbTraffic(page, ['**/api/traffic/qb/global*']);
      await openApp(page, skin);
      /* Ctrl+Backslash = 全局 qB 流量图入口(shortcuts open-qb-traffic 同 target 切换语义) */
      await page.keyboard.press('Control+Backslash');
      const drawer = page.locator('.drawer-dock > .drawer');
      await expect(drawer).toBeVisible({ timeout: 10_000 });
      await expect(drawer.locator('.qb-chart-host canvas'),
        'Ctrl+反斜杠没开出全局流量图(入口/总门没通)').toBeVisible({ timeout: 15_000 });
      await drawer.locator('.hist-summary .qb-tabs button', { hasText: '30分' }).click();
      await expect.poll(async () => readInst(page, 'vm.qbHistWindow'),
        { message: 'qbSetWindow 未生效(窗口不是 30m)', timeout: 15_000 }).toBe('30m');

      const tip = tipLines(drawer);
      await hoverBucket(page, drawer, 'qbHistHoverIdx', mid(LEAD));
      await expect(tip).toContainText('该时段无数据');
      await expect(tip, '全局图上写出了「此种子」主语 —— 这里根本没有种子概念').not.toContainText('此种子');

      await hoverBucket(page, drawer, 'qbHistHoverIdx', mid(MID));
      await expect(tip).toContainText('采样中断 · 该时段无数据');
    });
  }
});
