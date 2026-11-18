// @ts-check
import { expect, test } from '@playwright/test';
import { baseUrl, BOOT_FIRST, TORRENTS } from './harness.mjs';
import { collectRuntimeErrors, installRuntimeErrorGuard } from './lib/errors.mjs';
import { readInst } from './lib/vm.mjs';
import { requireMode } from './lib/mode.mjs';

/**
 * 桩冷启动两跳落位形状(plan 26-11-18-0259 S2) —— 启动首轮「提前发布基础代」的端到端面。
 *
 * 被测行为(计划 §03 D3): 重启后首个含落库数据的视图代不再被首轮管线挡住 —— apply_sync
 * 落库后即经同一发布单点先落一代「基础视图」(flat 全量 / singles 全量超集 / groups 空 /
 * shows 按名称解析), 管线照常, 结束时既有发布点落「补全代」(groups 落位 / singles 收缩 /
 * flat 恒满)。R2: delta 客户端多吃一代 —— 本 spec 的观察端(轮询 /api/state)与页面
 * (默认轮询 + SSE)全程跨两代消费, 即该回归面。
 *
 * 可观测性(为什么需要模式与闸口): 桩管线(进程内 FakeClient)毫秒级跑完, HTTP 观察窗口
 * 天然不存在 —— 与 S0 真机取证同款「管线挡发布窗口」。E2E_BOOT_FIRST=on 时桩 store
 * **不预灌**(ui_harness.py --boot-first on), 启动首轮由主线程经真实 _sync_line 跑:
 *   空库空代(首拍, S0 §02.2 第 3 点竞态形态) -> POST boot_go 放行 -> 提前发布基础代 ->
 *   归组 files 单发在闸口挂起(确定性停车) -> POST boot_gate 开闸 -> 补全代。
 * 默认模式(off)桩行为逐字不变, 本 spec 整组 skip(requireMode)。
 *
 * 断言面: HTTP 形状(四视图两跳) + UI 落位(种子页行先出、分组页空->有、flat 恒满);
 * rid 严格 +1(两跳间零中间代 —— 版本号单调不跳不重)。
 * 只跑单皮肤(prism): 两跳形状是后端数据面, 与皮肤渲染无关(其余 e2e 双皮肤口径不变)。
 */

/** 导航页签定位器(tpl/topbar.html `nav.tabs [data-view]`, delta-sync 同款)。 */
const tab = (page, view) => page.locator(`nav.tabs [data-view="${view}"]`);

test.describe('桩冷启动两跳落位形状(plan 26-11-18-0259 S2)', () => {
  installRuntimeErrorGuard(test);
  requireMode(test, { bootFirst: 'on' });

  test('首跳基础代(flat 满/groups 空/singles 超集)UI 落位 -> 开闸后第二跳补全代(groups 有/flat 恒满)', async ({ page, request }) => {
    const base = baseUrl();
    /** /api/state 快照(rid=-1 恒全量; 观察端轮询本身就是 web.touch, 撑住提前发布的活跃门控) */
    const st = async () => await (await request.get(`${base}/api/state?rid=-1`)).json();
    collectRuntimeErrors(page);

    // 第一拍(t0): 管线未放行、store 空 —— 首个请求经 ensure_state 发布 0 行空代
    // (S0 §02.2 第 3 点的「首请求早于落库」竞态形态; 提前发布判据对它免疫, S1 单测钉过)
    const empty = await st();
    expect(empty.rid).toBeGreaterThan(0);
    expect(empty.torrents.length).toBe(0);

    // 页面壳先出(bootstrap 闸 = 首个 /api/state 成功, 空代也算) —— 之后轮询/SSE 常驻
    await page.goto(`${base}/prism/`, { waitUntil: 'domcontentloaded' });
    await expect(tab(page, 'torrents')).toBeVisible({ timeout: 30_000 });

    // 放行启动首轮: apply_sync 落库 -> 提前发布基础代 -> 归组 files 单发在闸口挂起
    await request.post(`${base}/__harness__/boot_go`);

    // —— 首跳(基础代)HTTP 形状: flat 满量 / groups 空 / singles 全量超集 / shows 按名称解析
    await expect.poll(async () => {
      const s = await st();
      return s.torrents.length === TORRENTS && s.groups.length === 0 && s.singles.length === TORRENTS;
    }, { message: '首跳基础代形状(flat 满/groups 空/singles 全量超集)', timeout: 15_000 }).toBe(true);
    const hop1 = await st();
    expect(hop1.shows.list.length).toBeGreaterThan(0);
    const rid1 = hop1.rid;

    // UI 落位(首跳): 种子页行渲染(flat 满) —— 首份数据不等管线(North Star 的形状面);
    // 分组页仍无行(闸口挂起 = 确定性空组窗口, 负断言 2s)
    await tab(page, 'torrents').click();
    await expect(page.locator('.torrent-row').first()).toBeVisible({ timeout: 15_000 });
    expect(await readInst(page, 'vm.torrents.length'), 'UI flat 满量').toBe(TORRENTS);
    await tab(page, 'groups').click();
    await expect(page.locator('.group-row')).toHaveCount(0, { timeout: 2_000 });

    // —— 第二跳: 开闸放行归组 -> 管线完成 -> 既有收尾发布点落补全代
    await request.post(`${base}/__harness__/boot_gate`);
    await expect.poll(async () => {
      const s = await st();
      return s.groups.length === TORRENTS / 2 && s.singles.length === 0 && s.torrents.length === TORRENTS;
    }, { message: '第二跳补全代形状(groups 落位/singles 收缩/flat 恒满)', timeout: 15_000 }).toBe(true);
    const hop2 = await st();
    expect(hop2.rid, 'rid 严格 +1(两跳间零中间代: 版本号单调不跳不重)').toBe(rid1 + 1);

    // UI 落位(第二跳): 分组页行出现, 种子页行仍在(flat 恒满; UI 侧轮询/SSE 自行走完两跳消费)
    await expect.poll(async () => await readInst(page, 'vm.groups.length'), {
      message: 'UI 分组行落位', timeout: 15_000,
    }).toBe(TORRENTS / 2);
    expect(await readInst(page, 'vm.torrents.length'), 'UI flat 恒满(两跳不变)').toBe(TORRENTS);
  });
});
