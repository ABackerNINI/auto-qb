// @ts-check
import { expect, test } from '@playwright/test';
import { baseUrl, SKINS } from './harness.mjs';
import { collectRuntimeErrors, installRuntimeErrorGuard } from './lib/errors.mjs';
import { withVm } from './lib/vm.mjs';

/**
 * 外部旧路径种子通知面(T5, 计划 26-11-20-0434) —— pytest 侧钉的是投影函数面
 * (test_webui_relocate_visibility)与浮窗组装 node 探针(test_webui_relocate_pop),
 * 本 spec 钉的是**真浏览器接线面**(数据出口 = relocate 面板既有模式: 模块发布视图 ->
 * 行标注回落 -> decorate 单排警示色 + 迁移状态筛选档 + 悬停浮窗):
 *   1. 行标注回落: 无 job 的外部种子行路径列走 foreign 单排警示色(.rel-tone-foreign,
 *      不出 A->B 双排 —— R3 D17 路径筛选位置集钉扎矩阵不动);
 *   2. 「迁移状态」筛选档出现「旧路径外部种子」选项且计数 = 1(计数即面板计数徽标;
 *      空态不显示的对照面 = 桩上其余种子无该标注, 选项恰一条);
 *   3. 悬停浮窗: verdict「旧路径外部种子」+ 旧路径/数据现位置两行(T5 通知文案的
 *      两组关键事实; 相位/别名等 job 机械面不出 —— node 探针已钉, 这里验真机装配)。
 * 桩面: ui_harness._inject_relocate_jobs 给 torrents[5](无 job)灌 foreign 发布视图条目
 * (root=Set002 / location=Relocated), 与 job 注入共用同一 FakeRelocateJobs 句柄。
 */

const OLD_ROOT = 'R:\\Downloads\\Set002';
const NEW_LOC = 'R:\\Downloads\\Relocated';

/** 滚入 + 双 rAF 渲染沉降(relocate-pop-terminal 同款纪律): hover 自带 scrollIntoView 的
 * scroll 事件若在 mouseenter 之后送达, 会经「滚动即关」监听把挂起的 120ms 调度掐掉。 */
const scrollSettle = async (page, loc) => {
  await loc.scrollIntoViewIfNeeded();
  await page.evaluate(() => new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r))));
};

for (const skin of SKINS) {
  test.describe(`外部旧路径种子通知面 ${skin}`, () => {
    installRuntimeErrorGuard(test);

    test(`行警示色单排 + 筛选档计数 + 悬停浮窗 @fast (${skin})`, async ({ page }) => {
      collectRuntimeErrors(page);

      await page.goto(`${baseUrl()}/${skin}/`, { waitUntil: 'domcontentloaded' });
      await expect(page.locator('#app')).not.toHaveAttribute('v-cloak', { timeout: 15_000 });
      await expect(page.locator('.group-row').first()).toBeVisible({ timeout: 30_000 });

      // 2. 筛选档(计数徽标): 「旧路径外部种子」选项恰一条且计数 = 1(全库仅 torrents[5] 携带)
      await expect.poll(() =>
        withVm(page, 'return JSON.stringify((vm.relocateOptions || []).filter((o) => o.value === "旧路径外部种子"));'),
      ).toBe(JSON.stringify([{ value: '旧路径外部种子', count: 1 }]));

      // 1. 行标注回落: 种子页平铺 + 按添加时间升序把注入窗口外的行拉进视口
      //    (i=5 的 added_on 排第 6, 升序后进窗口顶部; 与 relocate-pair-filter 同款真实手势)
      await page.click('nav.tabs [data-view="torrents"]');
      const sortCell = page.locator('[data-table="torrent"].group-head .h-cell.hc-added_on');
      await sortCell.focus();
      await page.keyboard.press('Enter');
      const cell = page.locator('.torrent-row .g-save-path .sp-body.rel-tone-foreign');
      await expect(cell).toBeVisible({ timeout: 15_000 });
      // 恒单排: foreign 行自身不得渲染 A->B 双排块(路径筛选位置集钉扎矩阵不动;
      // 平铺视图里 moving/armed/failed 三行的双排不在本断言射程)
      await expect(cell.locator('xpath=ancestor::div[contains(@class,"torrent-row")]//div[contains(@class,"rel-pair")]')).toHaveCount(0);

      // 3. 悬停浮窗: 通知态专属路径块(旧路径/数据现位置)+ verdict 词, 零请求装配
      await scrollSettle(page, cell);
      await cell.hover();
      const pop = page.locator('.relpop');
      await expect(pop).toBeVisible({ timeout: 5_000 });
      await expect(pop).toContainText('旧路径外部种子');
      await expect(pop).toContainText('旧路径');
      await expect(pop).toContainText(OLD_ROOT);
      await expect(pop).toContainText('数据现位置');
      await expect(pop).toContainText(NEW_LOC);
      await expect(pop).not.toContainText('清空迁移历史'); // 通知态非终态, 清空入口不亮
    });
  });
}
