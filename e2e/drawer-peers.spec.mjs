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
 * 2026-10-13 补软切换空态守卫(用户报「切换种子时用户页闪『暂无已连接用户』」): 既有全部用例只
 * dblclick nth=0 **单次打开**(切换种子路径零覆盖), 且桩每种子恒有 1~7 对端 —— 「换目标后首个
 * /peers 为空」这条真机路径从未被走过。新增用例用 route 让切换目标的首个 /peers 返回空并逐帧
 * 采样, 钉住「换种子期间不得出现空态」(修法见 drawer_store.js::_fetchDrawerPeers 的宽限重拉)。
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

    /* 2026-10-13 用户报障「种子详情用户页切换种子时『暂无已连接用户』闪烁」的回归守卫。
     * 病根(见 drawer-switch-flicker.md 第九次形态): 软切换本意"保留旧数据撑几何 + 遮罩防串显",
     * 但换目标后 qB 对新种子的**首个** /peers 常为瞬时**空**(连接/状态未就绪), 空响应直接落袋
     * 会覆盖旧数据渲染成空态, 下一拍(5s)真实对端到达再顶回表格 = "闪一下"。修法 = 换目标窗口内
     * 首个空响应视为「未就绪」: 不落袋/不掀罩, 1s 后快速重拉一次(见 drawer_store.js::_fetchDrawerPeers)。
     * 本用例即把这条路径钉死: route 让**切换目标**的首个 /peers 返回空(其余走桩), 逐帧采样抽屉内
     * 不得出现空态文案, 且重拉后对端表须就位(宽限不是"永久停在加载")。 */
    test(`切换种子首个空 peers 响应不得闪现空态 @fast (${skin})`, async ({ page }) => {
      collectRuntimeErrors(page);
      const seen = /** @type {Record<string, number>} */ ({});
      await page.route('**/api/torrents/*/peers**', (route) => {
        const m = route.request().url().match(/torrents\/([0-9a-fA-F]+)\/peers/);
        const h = m ? m[1] : '';
        seen[h] = (seen[h] || 0) + 1;
        // 第一个 hash = 初开种子; 出现第二个 hash 即"切换目标", 其首个 /peers 返回空
        const isSwitchTarget = Object.keys(seen).length > 1;
        if (isSwitchTarget && seen[h] === 1) {
          return route.fulfill({
            status: 200, contentType: 'application/json',
            body: JSON.stringify({ rid: 0, full_update: true, peers: {}, peers_removed: {} }),
          });
        }
        return route.continue();  // 其余(初开/重拉/轮询)走桩服务真实对端
      });

      await page.goto(`${BASE_URL}/${skin}/`, { waitUntil: 'domcontentloaded' });
      await expect(page.locator('#app')).not.toHaveAttribute('v-cloak', { timeout: 15_000 });
      await expect(page.locator('.group-row').first()).toBeVisible({ timeout: 30_000 });
      await page.click('nav.tabs [data-view="torrents"]');
      await expect(page.locator('.torrent-row').first()).toBeVisible({ timeout: 15_000 });

      await page.dblclick('.torrent-row >> nth=0', { force: true });
      const drawer = page.locator('.drawer-dock > .drawer');
      await expect(drawer).toBeVisible({ timeout: 5_000 });
      await drawer.locator('.drawer-tabs button', { hasText: '用户' }).click();
      await expect(drawer.locator('.group-row[data-table="drawerPeer"]').first())
        .toBeVisible({ timeout: 5_000 });

      // 逐帧(rAF)采样: 换目标全程抽屉内不得出现空态文案(经典 .empty 与变体 .dt0X-empty 同文本)
      await page.evaluate(() => {
        const el = document.querySelector('.drawer-dock > .drawer');
        /** @type {any} */ (window).__emptyFrames = 0;
        let stop = false;
        /** @type {any} */ (window).__stopSample = () => { stop = true; };
        const tick = () => {
          if (stop) return;
          if (el && (el.textContent || '').indexOf('暂无已连接用户') >= 0)
            /** @type {any} */ (window).__emptyFrames++;
          requestAnimationFrame(tick);
        };
        requestAnimationFrame(tick);
      });

      await page.dblclick('.torrent-row >> nth=1', { force: true });   // 软切换换目标
      await page.waitForTimeout(2500);                                  // 覆盖首拍空(0ms) + 宽限重拉(1s)
      const emptyFrames = await page.evaluate(() => {
        /** @type {any} */ (window).__stopSample();
        return /** @type {any} */ (window).__emptyFrames;
      });
      expect(emptyFrames, '换种子期间不得出现「暂无已连接用户」空态').toBe(0);

      // 宽限重拉拿到真实对端 ⇒ 对端表就位(不得永久停在加载态)
      await expect(drawer.locator('.group-row[data-table="drawerPeer"]').first())
        .toBeVisible({ timeout: 10_000 });
    });
  });
}
