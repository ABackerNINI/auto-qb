// @ts-check
import { expect, test } from '@playwright/test';
import { BASE_URL, SKINS } from './harness.mjs';
import { collectRuntimeErrors, installRuntimeErrorGuard } from './lib/errors.mjs';

/**
 * 抽屉页签合并(R2, 计划 26-10-09-2219) —— 右键开关 / 双列布局 / 宽度门:
 *   1. 宽视口(≥1920): 正文右键 → 菜单两项可用 → 点「常规+内容 并排」→ .drawer-split 双列
 *      (常规列 = classic 分组键值, 内容列 = classic 工具栏+文件表); 再右键 → 再点已选项 → 关。
 *   2. 窄视口(<1920): 菜单项置灰(.is-gated), 点击不产生任何状态变化(dtSetMerge 双保险拦截)。
 * 断言口径: 真实手势(右键 click button:'right'), 不借道 vm; 抽屉内容经页插件(classic)渲染。
 */

const WIDE = { width: 2560, height: 1200 };
const NARROW = { width: 1280, height: 800 };

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

    test(`宽视口: 右键开启常规+内容并排, 再点关闭 @fast (${skin})`, async ({ page }) => {
      collectRuntimeErrors(page);
      await page.setViewportSize(WIDE);
      await page.goto(`${BASE_URL}/${skin}/`, { waitUntil: 'domcontentloaded' });
      await expect(page.locator('#app')).not.toHaveAttribute('v-cloak', { timeout: 15_000 });
      await expect(page.locator('.group-row').first()).toBeVisible({ timeout: 30_000 });
      const drawer = await openTorrentDrawer(page);

      // 视口在 boot 后拉宽: 门判据走核心 resize 防抖回写(dtWinW), 等一拍再右键
      await page.waitForTimeout(300);
      await drawer.locator('.drawer-body').click({ button: 'right' });
      const menu = page.locator('.ctx-menu');
      await expect(menu).toBeVisible();
      const gcItem = menu.locator('.ctx-item', { hasText: '常规+内容 并排' });
      await expect(gcItem).not.toHaveClass(/is-gated/);

      // 开启合并: 双列出现, 列头 = 常规/内容; 两列各挂 classic 页插件(分组键值 + 内容工具栏)
      await gcItem.click();
      const split = drawer.locator('.drawer-split');
      await expect(split).toBeVisible({ timeout: 5_000 });
      await expect(split.locator('.dt-col-head', { hasText: '常规' })).toBeVisible();
      await expect(split.locator('.dt-col-head', { hasText: '内容' })).toBeVisible();
      await expect(split.locator('[data-dt-host="general"] .drawer-sec').first()).toBeVisible();
      await expect(split.locator('[data-dt-host="content"] .drawer-toolbar')).toBeVisible();
      // 桩灌了文件数据: 内容列经典表渲染出行(目录聚合行)
      await expect(split.locator('[data-dt-host="content"] table.drawer-table tbody tr').first()).toBeVisible();

      // 菜单已随动作收起; 再开 → 勾选态在 → 再点已选项 = 关 → 双列消失(单栏宿主回归)
      await expect(menu).toHaveCount(0);
      await drawer.locator('.drawer-body').click({ button: 'right' });
      await expect(gcItem).toBeVisible();
      await expect(gcItem.locator('.ctx-tick')).toHaveCount(1);
      await gcItem.click();
      await expect(split).toHaveCount(0);
      await expect(drawer.locator('[data-dt-host="general"] .drawer-sec').first()).toBeVisible();
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
      const gcItem = menu.locator('.ctx-item', { hasText: '常规+内容 并排' });
      await expect(gcItem).toHaveClass(/is-gated/);

      // 置灰项点击 = 零状态变化(菜单保持打开, 不出双列)
      await gcItem.click();
      await expect(menu).toBeVisible();
      await expect(drawer.locator('.drawer-split')).toHaveCount(0);
      // 单栏 classic 正文不受扰动
      await expect(drawer.locator('[data-dt-host="general"] .drawer-sec').first()).toBeVisible();
    });
  });
}
