// @ts-check
import { expect, test } from '@playwright/test';
import { BASE_URL, SKINS } from './harness.mjs';
import { collectRuntimeErrors, installRuntimeErrorGuard } from './lib/errors.mjs';

/**
 * 详情抽屉 peers 页签内容渲染(issue 26-10-07-2309, 用户指派认领并修复) —— 补一条 @fast 断言:
 * 桩服务有 peers 数据时, 抽屉「用户」页签渲染出对端表(而非空态)。
 *
 * 为什么需要它: 桩服务 `scripts/ui_harness.py` 的 `FakeClient.peers_map` 曾恒空 ⇒ 端点
 * `/api/torrents/{hash}/peers` 恒回 `{peers: []}`, peers 页签在桩服务下**永远**只走到空态分支
 * (「暂无已连接用户」), e2e 与截图目检从未覆盖「有数据」渲染路径 —— 前端 drawerPeerRows 的
 * dict/数组双形态归一、经典表 9 列映射、变体 07/08/09 的四卡派生全在盲区里(当时靠 Playwright
 * route 拦截注入合成数据才完成 tooltip 修复轮的场景验证)。修复 = 桩按种子灌合成对端
 * (`_make_peers_response`, 含 flags/速度/进度/客户端多样性), 本 spec 钉住这条渲染路径不再回退空态。
 *
 * 断言口径: 打开种子详情抽屉 → 切「用户」页签 → 对端列表渲染出对端行(>0)且首行地址列有
 * IP:port 文本, 同时「暂无已连接用户」空态**不出现**。真实手势(locator click), 不借道 vm。
 *
 * !2026-10-11 锚点改版(计划 26-10-11-2106 W2「三列表接表壳」): 三张抽屉列表不再自带
 * `<table class="drawer-table">`, 改成与主视图同一条路 —— 表头 `<aq-table grid>` + 行容器
 * `.group-table` + 行 `.group-row[data-table="drawerPeer"]` + `<aq-peer-cells>` 值格。故本 spec
 * 的行/单元格锚点从 `tbody tr` / `td` 换成 `.group-row[data-table=...]` / 其**直接子元素**
 * (行是 grid, 单元格就是行的直接子元素; :nth-child 列对齐依赖这层)。这是 R3「文案/类名变了
 * 同轮改 spec」的同轮改版, 不是放宽容忍 —— 断言口径(有行 / 地址像 ip:port / 速度非全"—")一字未动。
 * 默认模板为 classic(`drawerTplSel.peers` 初值), 故断言落在接壳后的网格列表上。
 *
 * 2026-10-10 补速度列守卫: 真 qB sync/torrentPeers 的速度键是 dl_speed / up_speed(与列表侧
 * torrents/info 的 dlspeed / upspeed 不同名)。前端落袋单点 `_drawerNormPeers` 若漏适配, 用户页
 * 上下行恒 0(用户报障) —— 而本 specs 原先只断「有行 + 地址有 ip:port」, 速度列全 "—" 也不红。
 * 现加「上下行至少一格含数字」守卫, 桩每种子恒有非零速度对端, 确保失配即红。
 *
 * 2026-10-13: 软切换空态守卫(换种子后首个列表响应为空不得闪现空态)是跨三列表(peers/trackers/files)
 * 的**同一条数据落袋语义**问题, 单点在 e2e/drawer-switch-empty-grace.spec.mjs(三页签各钉一条),
 * 本文件不再重复。此处只留指针, 免得两处各自演化。
 */

for (const skin of SKINS) {
  test.describe(`详情抽屉 peers 页签内容渲染 ${skin}`, () => {
    installRuntimeErrorGuard(test);

    test(`用户页签渲染对端表(非空态) @fast (${skin})`, async ({ page }) => {
      collectRuntimeErrors(page);

      await page.goto(`${BASE_URL}/${skin}/`, { waitUntil: 'domcontentloaded' });
      await expect(page.locator('#app')).not.toHaveAttribute('v-cloak', { timeout: 15_000 });
      await expect(page.locator('.group-row').first()).toBeVisible({ timeout: 30_000 });

      // 种子视图平铺行双击开详情抽屉(与 drawer-dock-stability.spec 同款: 整表 2s 重渲染抢点击 ⇒ force)
      await page.click('nav.tabs [data-view="torrents"]');
      await expect(page.locator('.torrent-row').first()).toBeVisible({ timeout: 15_000 });
      await page.dblclick('.torrent-row >> nth=0', { force: true });

      const drawer = page.locator('.drawer-dock > .drawer');
      await expect(drawer).toBeVisible({ timeout: 5_000 });

      // 切到「用户」页签(peers): 触发 /api/torrents/{hash}/peers 拉取
      await drawer.locator('.drawer-tabs button', { hasText: '用户' }).click();

      // 接壳后的对端列表: 行容器 .group-table + 行 .group-row[data-table="drawerPeer"]。
      // data-table 是列对齐(colAlignCss)与行宽(gridStyle)的锚 —— 少了它列会全左对齐且宽谱错乱。
      const table = drawer.locator('.group-table');
      await expect(table.first()).toBeVisible({ timeout: 5_000 });
      const rows = drawer.locator('.group-row[data-table="drawerPeer"]');
      await expect(rows.first()).toBeVisible({ timeout: 5_000 });
      expect(await rows.count(), 'peers 列表渲染出对端行(>0)').toBeGreaterThan(0);

      // 首行地址列 = "ip:port"(drawerPeerRows 归一后的 addr), 证明是真内容不是占位行。
      // 地址格自带 .mono-cell(等宽), 与列定义 addr 一一对应; 比 nth-child 更抗列序变化。
      const addr = (await rows.first().locator('.mono-cell').first().innerText()).trim();
      expect(addr, `peers 首行地址="${addr}"`).toMatch(/[\d.:]+/);

      // 上下行(第5/6列)必须渲染出真实速度 —— 回归守卫: qB sync/torrentPeers 的速度键是
      // dl_speed / up_speed(与列表侧 dlspeed / upspeed 不同名)。落袋单点(drawer.js::
      // _drawerNormPeers)若未做键名适配, 取不到值 → 全部退化成 "—"(用户报「上下行始终为 0」)。
      // 桩每个种子恒有 >=1 个非零速度对端, 故「至少一格含数字」在有适配时恒真、失配时恒假。
      // !按**列位**取(与列定义序绑定, 不绑值格的类名): 速度格与进度格都是 .g-stat, 按类名取会取错。
      const speedCells = await rows.locator('xpath=./*[position()=5 or position()=6]').allInnerTexts();
      expect(
        speedCells.some((t) => /\d/.test(t)),
        `peers 上下行应渲染出真实速度(非全 "—"), 实际=${JSON.stringify(speedCells)}`,
      ).toBe(true);

      // 空态文案必须消失(「有数据」与「真没有」在此分界)
      await expect(drawer.locator('.empty', { hasText: '暂无已连接用户' })).toHaveCount(0);
    });
  });
}
