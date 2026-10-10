// @ts-check
import { expect, test } from '@playwright/test';
import { BASE_URL, SKINS } from './harness.mjs';
import { collectRuntimeErrors, installRuntimeErrorGuard } from './lib/errors.mjs';

/**
 * 抽屉页签合并(R2 计划 26-10-09-2219 · R3 修订) —— 单开关 / 合并页签 / 双列布局 / 宽度门:
 *   1. 宽视口(≥1920): 正文右键 → 菜单「合并页签」可用 → 点击 → 页签栏收敛为
 *      [常规&内容][Tracker&用户] 两张合并页签, 正文双列(列头 常规/内容, 两列各挂 classic 页插件);
 *      再右键 → 勾选态在 → 再点已开启项 → 关闭, 页签栏回四页签单栏。
 *   2. R3 回归(用户报「选择并排后 tracker/用户标签显示常规/内容且为空」): 合并开启下点
 *      [Tracker&用户] 合并页签 → 列头变 Tracker/用户 且两列有内容(不再渲染旧对列头 + 空列)。
 *   3. 窄视口(<1920): 菜单项置灰(.is-gated), 点击零状态变化(dtToggleMerge 双保险拦截), 四页签原样。
 *   4. 2026-10-10 模板选择迁右键: 合并态右键左列弹常规变体、右列弹内容变体(菜单选项集按命中列),
 *      两列各自选择互不影响。
 * 断言口径: 真实手势(右键 click button:'right'), 不借道 vm; 抽屉内容经页插件(classic)渲染。
 */

const WIDE = { width: 2560, height: 1200 };
const NARROW = { width: 1280, height: 800 };

const MERGE_ITEM = '.ctx-item:has-text("合并页签")';

async function openTorrentDrawer(page) {
  await page.click('nav.tabs [data-view="torrents"]');
  await expect(page.locator('.torrent-row').first()).toBeVisible({ timeout: 15_000 });
  await page.dblclick('.torrent-row >> nth=0', { force: true });
  const drawer = page.locator('.drawer-dock > .drawer');
  await expect(drawer).toBeVisible({ timeout: 5_000 });
  return drawer;
}

for (const skin of SKINS) {
  test.describe(`抽屉页签合并 ${skin}`, () => {
    installRuntimeErrorGuard(test);

    test(`宽视口: 合并页签开关 + 双列 + 切对不受污染 @fast (${skin})`, async ({ page }) => {
      collectRuntimeErrors(page);
      await page.setViewportSize(WIDE);
      await page.goto(`${BASE_URL}/${skin}/`, { waitUntil: 'domcontentloaded' });
      await expect(page.locator('#app')).not.toHaveAttribute('v-cloak', { timeout: 15_000 });
      await expect(page.locator('.group-row').first()).toBeVisible({ timeout: 30_000 });
      const drawer = await openTorrentDrawer(page);
      await page.waitForTimeout(300);

      // 默认四页签(合并关闭): Tracker 单页签在
      await expect(drawer.locator('.drawer-tabs button', { hasText: /^Tracker$/ })).toBeVisible();

      // 开启合并: 右键 → 单开关「合并页签」(门内可点)
      await drawer.locator('.drawer-body').click({ button: 'right' });
      const menu = page.locator('.ctx-menu');
      await expect(menu).toBeVisible();
      const item = menu.locator(MERGE_ITEM);
      await expect(item).not.toHaveClass(/is-gated/);
      await item.click();

      // 页签栏收敛为两合并页签(四页签隐去)
      await expect(drawer.locator('.drawer-tabs button', { hasText: '常规&内容' })).toBeVisible();
      await expect(drawer.locator('.drawer-tabs button', { hasText: 'Tracker&用户' })).toBeVisible();
      await expect(drawer.locator('.drawer-tabs button', { hasText: /^Tracker$/ })).toHaveCount(0);

      // gc 双列: 列头 常规/内容; 两列各挂 classic 页插件(分组键值 + 内容工具栏/文件表)
      const split = drawer.locator('.drawer-split');
      await expect(split).toBeVisible({ timeout: 5_000 });
      await expect(split).toHaveAttribute('data-merge', 'gc');
      await expect(split.locator('.dt-col-head', { hasText: '常规' })).toBeVisible();
      await expect(split.locator('.dt-col-head', { hasText: '内容' })).toBeVisible();
      await expect(split.locator('[data-dt-host="general"] .drawer-sec').first()).toBeVisible();
      await expect(split.locator('[data-dt-host="content"] .drawer-toolbar')).toBeVisible();
      // 桩灌了文件数据: 内容列经典表渲染出行(目录聚合行)
      await expect(split.locator('[data-dt-host="content"] table.drawer-table tbody tr').first()).toBeVisible();

      // R3 回归: 点 [Tracker&用户] 合并页签 → 列组换成 Tracker/用户 且两列有内容(不再空列)
      await drawer.locator('.drawer-tabs button', { hasText: 'Tracker&用户' }).click();
      await expect(split).toHaveAttribute('data-merge', 'tp');
      await expect(split.locator('.dt-col-head', { hasText: 'Tracker' })).toBeVisible();
      await expect(split.locator('.dt-col-head', { hasText: '用户' })).toBeVisible();
      // trackers classic 恒渲染工具栏(添加 tracker); peers 列非空(表格或加载/空态)
      await expect(split.locator('[data-dt-host="trackers"] .drawer-toolbar')).toBeVisible();
      await expect(split.locator('[data-dt-host="peers"]')).not.toBeEmpty();
      await expect(split).not.toHaveAttribute('data-merge', 'gc');

      // 再右键 → 勾选态在 → 再点已开启项 = 关 → 双列消失, 页签栏回四页签(单栏宿主回归)
      await drawer.locator('.drawer-body').click({ button: 'right' });
      await expect(menu).toBeVisible();
      await expect(menu.locator(MERGE_ITEM).locator('.ctx-tick')).toHaveCount(1);
      await menu.locator(MERGE_ITEM).click();
      await expect(split).toHaveCount(0);
      await expect(drawer.locator('.drawer-tabs button', { hasText: /^Tracker$/ })).toBeVisible();
      await expect(drawer.locator('.drawer-tabs button', { hasText: 'Tracker&用户' })).toHaveCount(0);
    });

    test(`窄视口: 门内置灰可见, 点击零状态变化 @fast (${skin})`, async ({ page }) => {
      collectRuntimeErrors(page);
      await page.setViewportSize(NARROW);
      await page.goto(`${BASE_URL}/${skin}/`, { waitUntil: 'domcontentloaded' });
      await expect(page.locator('#app')).not.toHaveAttribute('v-cloak', { timeout: 15_000 });
      await expect(page.locator('.group-row').first()).toBeVisible({ timeout: 30_000 });
      const drawer = await openTorrentDrawer(page);

      await drawer.locator('.drawer-body').click({ button: 'right' });
      const menu = page.locator('.ctx-menu');
      await expect(menu).toBeVisible();
      const item = menu.locator(MERGE_ITEM);
      await expect(item).toHaveClass(/is-gated/);

      // 置灰项点击 = 零状态变化(菜单保持打开, 不出双列, 页签栏仍四页签)
      await item.click();
      await expect(menu).toBeVisible();
      await expect(drawer.locator('.drawer-split')).toHaveCount(0);
      await expect(drawer.locator('.drawer-tabs button', { hasText: '常规&内容' })).toHaveCount(0);
      await expect(drawer.locator('.drawer-tabs button', { hasText: /^Tracker$/ })).toBeVisible();
      // 单栏 classic 正文不受扰动
      await expect(drawer.locator('[data-dt-host="general"] .drawer-sec').first()).toBeVisible();
    });

    test(`合并态快捷键: Alt+1/2 切两合并页签, Alt+4 停用 @fast (${skin})`, async ({ page }) => {
      /* 2026-10-10 用户报「标签合并后没有同步修改快捷键」的回归: 合并成功时 Alt+1..5 按位次重排到
       * 三张可见页签(1=常规&内容 / 2=Tracker&用户 / 3=流量), 4/5 停用。此处真按键验 Alt+1/2 切对、
       * Alt+4 零变化(不借道 vm; 判据读双列 data-merge, 与用户所见一致)。 */
      collectRuntimeErrors(page);
      await page.setViewportSize(WIDE);
      await page.goto(`${BASE_URL}/${skin}/`, { waitUntil: 'domcontentloaded' });
      await expect(page.locator('#app')).not.toHaveAttribute('v-cloak', { timeout: 15_000 });
      await expect(page.locator('.group-row').first()).toBeVisible({ timeout: 30_000 });
      const drawer = await openTorrentDrawer(page);
      await page.waitForTimeout(300);

      // 开合并: 右键单开关 -> 页签栏收敛, 默认双列 = gc
      await drawer.locator('.drawer-body').click({ button: 'right' });
      await page.locator('.ctx-menu').locator(MERGE_ITEM).click();
      const split = drawer.locator('.drawer-split');
      await expect(split).toHaveAttribute('data-merge', 'gc', { timeout: 5_000 });

      // Alt+2 -> Tracker&用户(tp); Alt+1 -> 回常规&内容(gc); Alt+4 合并态停用 -> 零变化(仍 gc)
      await page.keyboard.press('Alt+Digit2');
      await expect(split, 'Alt+2 必须切到 Tracker&用户 对').toHaveAttribute('data-merge', 'tp', { timeout: 5_000 });
      await page.keyboard.press('Alt+Digit1');
      await expect(split, 'Alt+1 必须切回 常规&内容 对').toHaveAttribute('data-merge', 'gc', { timeout: 5_000 });
      await page.keyboard.press('Alt+Digit4');
      await expect(split, 'Alt+4 合并态停用, 双列不得切换').toHaveAttribute('data-merge', 'gc', { timeout: 5_000 });
    });

    test(`宽视口: 右键各列弹各自模板选择(左常规/右内容) @fast (${skin})`, async ({ page }) => {
      /* 2026-10-10 用户动议「模板选择改为右键选择, 在对应的区域弹右键; 合并时左边弹常规的模板选择,
       * 右边弹内容的模板选择」: 头部下拉退役, 右键命中的列决定菜单里的模板选项集(左列=常规变体,
       * 右列=内容变体), 两列选择互不影响(各自页签记忆)。断言口径: 真实手势(右键 click button:'right'),
       * 不借道 vm; 变体挂载态经宿主 .dt-tpl 类(DOM 可见事实)。 */
      collectRuntimeErrors(page);
      await page.setViewportSize(WIDE);
      await page.goto(`${BASE_URL}/${skin}/`, { waitUntil: 'domcontentloaded' });
      await expect(page.locator('#app')).not.toHaveAttribute('v-cloak', { timeout: 15_000 });
      await expect(page.locator('.group-row').first()).toBeVisible({ timeout: 30_000 });
      const drawer = await openTorrentDrawer(page);
      await page.waitForTimeout(300);

      // 开合并 -> gc 双列
      await drawer.locator('.drawer-body').click({ button: 'right' });
      await page.locator('.ctx-menu').locator(MERGE_ITEM).click();
      const split = drawer.locator('.drawer-split');
      await expect(split).toHaveAttribute('data-merge', 'gc', { timeout: 5_000 });

      const menu = page.locator('.ctx-menu');
      const leftCol = split.locator('.dt-col[data-dt-tab="general"]');
      const rightCol = split.locator('.dt-col[data-dt-tab="content"]');
      const leftItem = menu.locator('.ctx-item', { hasText: '英雄行·键值栅格' }); // general 变体 01
      const rightItem = menu.locator('.ctx-item', { hasText: '树 + 详情' }); // content 变体 10

      // 左列右键 -> 菜单出常规变体, 不出内容变体
      await leftCol.click({ button: 'right' });
      await expect(menu).toBeVisible();
      await expect(leftItem).toBeVisible();
      await expect(menu.locator('.ctx-item', { hasText: '树 + 详情' })).toHaveCount(0);
      await leftItem.click();
      // 左列挂上变体(宿主加 .dt-tpl), 右列仍是经典
      await expect(split.locator('[data-dt-host="general"]')).toHaveClass(/dt-tpl/, { timeout: 5_000 });
      await expect(split.locator('[data-dt-host="content"]')).not.toHaveClass(/dt-tpl/);

      // 右列右键 -> 菜单出内容变体, 不出常规变体
      await rightCol.click({ button: 'right' });
      await expect(menu).toBeVisible();
      await expect(rightItem).toBeVisible();
      await expect(menu.locator('.ctx-item', { hasText: '英雄行·键值栅格' })).toHaveCount(0);
      await rightItem.click();
      await expect(split.locator('[data-dt-host="content"]')).toHaveClass(/dt-tpl/, { timeout: 5_000 });
      // 左列选择不受右列影响(两列各自记忆)
      await expect(split.locator('[data-dt-host="general"]')).toHaveClass(/dt-tpl/);
    });
  });
}
