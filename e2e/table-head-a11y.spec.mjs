// @ts-check
import { expect, test } from '@playwright/test';
import { BASE_URL, SKINS } from './harness.mjs';
import { collectRuntimeErrors, installRuntimeErrorGuard } from './lib/errors.mjs';

/**
 * 引擎表头可访问性真浏览器用例(issue 26-10-12-0800, 计划 26-10-12-2330 方案 C)。
 *
 * 静态守阵 `test_frontend_table_head_a11y` 只能钉 markup(role/tabindex/aria-sort/keydown 在不在);
 * 本 spec 钉**键盘真按下去**的行为 —— click-only 的 `.h-cell` 加了 role/tabindex 后, 若 keydown
 * 转发没接上激活单点, 静态守阵全绿而键盘用户按了毫无反应(纯静默)。三条:
 *   ① 语义与可达: 列头是 `columnheader`; 可排序列才进 Tab 序(`tabindex="0"`), Tab 进得去;
 *   ② 键盘触发: Enter → 该列 `aria-sort="descending"`(三态首击降序)+ 箭头点亮; Space → 翻 ascending;
 *   ③ 全域同源: 抽屉变体表(drawerTrackerV06)同一组件, 键盘同样可用(引擎一处受益全域)。
 * thead 模式(设置页 HR 详情表)的 `<th>` 结构由静态守阵钉; 其 `$emit('sort')` 运行时路径随 HR 表
 * 既有 e2e/静态用例覆盖, 本 spec 不重复铺 HR 场景的长前置。
 */

const groupHead = (page) => page.locator('.group-head[data-table="group"]');

for (const skin of SKINS) {
  test.describe(`引擎表头 a11y ${skin}`, () => {
    installRuntimeErrorGuard(test);

    test(`主视图表头: columnheader + 可排序列进 Tab 序 + Enter/Space 触发排序与 aria-sort @fast (${skin})`, async ({ page }) => {
      collectRuntimeErrors(page);
      await page.goto(`${BASE_URL}/${skin}/`, { waitUntil: 'domcontentloaded' });
      await expect(page.locator('#app')).not.toHaveAttribute('v-cloak', { timeout: 15_000 });
      await expect(page.locator('.group-row').first()).toBeVisible({ timeout: 30_000 });

      const cells = groupHead(page).locator('.h-cell');
      const sortable = groupHead(page).locator('.h-cell.sortable');
      const nSortable = await sortable.count();
      expect(nSortable, '分组表应有可排序列').toBeGreaterThan(0);

      // ① 语义载体 = columnheader(不是 button); 可排序列才进 Tab 序(不可排序列不设 tabindex)
      await expect(cells.first()).toHaveAttribute('role', 'columnheader');
      await expect(groupHead(page).locator('.h-cell.sortable[tabindex="0"]'), '可排序列全部可聚焦').toHaveCount(nSortable);

      // ② 键盘: 聚焦一列(取第 2 个可排序列, 避开默认排序键以免与初始态混淆)
      const target = sortable.nth(Math.min(1, nSortable - 1));
      await target.focus();
      await expect(target, '列头可被键盘聚焦').toBeFocused();

      await page.keyboard.press('Enter');
      await expect(target, 'Enter 后 aria-sort=descending(三态首击降序)').toHaveAttribute('aria-sort', 'descending');
      await expect(target.locator('.arrow .ico'), 'Enter 后排序箭头点亮(与 aria-sort 同源)').toHaveCount(1);

      await page.keyboard.press(' ');
      await expect(target, 'Space 再点翻成 ascending').toHaveAttribute('aria-sort', 'ascending');
    });

    test(`抽屉变体表表头: 键盘排序可用(引擎全域同源) @fast (${skin})`, async ({ page }) => {
      collectRuntimeErrors(page);
      await page.setViewportSize({ width: 2560, height: 1200 });
      // 2026-10-14: 经典 Tracker 表(drawerTracker)随经典渲染链退役 —— 改钉变体 06「增强表格」
      // (Tracker 页签唯一带 8 列引擎表头的变体; 04 卡片/05 分段无表头)。引擎同源判据不变。
      await page.addInitScript(
        (o) => localStorage.setItem('autoqb.ui.drawerTpl', JSON.stringify(o)),
        { trackers: '06' },
      );
      await page.goto(`${BASE_URL}/${skin}/`, { waitUntil: 'domcontentloaded' });
      await expect(page.locator('#app')).not.toHaveAttribute('v-cloak', { timeout: 15_000 });
      await expect(page.locator('.group-row').first()).toBeVisible({ timeout: 30_000 });

      // 打开种子详情 → Tracker 页签(与 e2e/drawer-tables.spec.mjs 同路径)
      await page.click('nav.tabs [data-view="torrents"]');
      await expect(page.locator('.torrent-row').first()).toBeVisible({ timeout: 15_000 });
      await page.dblclick('.torrent-row >> nth=0', { force: true });
      const drawer = page.locator('.drawer-dock > .drawer');
      await expect(drawer).toBeVisible({ timeout: 5_000 });
      await drawer.locator('.drawer-tabs button', { hasText: /^Tracker$/ }).click();

      const head = drawer.locator('.group-head[data-table="drawerTrackerV06"]');
      await expect(head).toBeVisible({ timeout: 5_000 });
      const sortable = head.locator('.h-cell.sortable');
      expect(await sortable.count(), 'Tracker 变体表应有可排序列').toBeGreaterThan(0);

      const target = sortable.nth(1);
      await target.focus();
      await expect(target, '抽屉列头可被键盘聚焦').toBeFocused();
      await page.keyboard.press('Enter');
      await expect(target, '抽屉列头 Enter 触发排序(与主视图同一份组件)').toHaveAttribute('aria-sort', 'descending');
    });
  });
}
