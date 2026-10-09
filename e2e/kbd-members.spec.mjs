// @ts-check
import { expect, test } from '@playwright/test';
import { BASE_URL, SKINS } from './harness.mjs';
import { collectRuntimeErrors, installRuntimeErrorGuard } from './lib/errors.mjs';

/**
 * 辅种页 / 追剧页 · 展开分组后键盘上下键选中分组成员(2026-10-09)。
 *
 * 为什么需要它: 这条链此前**没有任何浏览器断言** —— 键盘导航只在静态守阵里查过"成员行在不在
 * 光标链上"(test_webui_static_dom_panel 的 _kbRows 断言), 而"按下去到底动不动、选没选中"
 * 只能靠真实按键。用户实报「展开分组后 ↑↓ 只能在分组间跳动」正是这类"静态看不出"的形态。
 *
 * 覆盖两条:
 *   1. 辅种页: 展开组 -> ↓ 光标落成员行(虚线框在 .member-row 上、不在组行) -> Space 选中
 *      -> Shift+↓ 在展开组的成员链内范围选中(此前一律走种子页平铺列表 => 选不中任何成员);
 *   2. 追剧页: 展开剧 -> ↓ 落集行 -> 展开集 -> ↓ 落成员行。
 * 另覆盖(2026-10-09 用户报「收起当前行快捷键无法在键盘光标进入分组后收起分组」):
 *   3. 辅种页: 光标落成员行后 ← 收起**所属分组**并把光标带回组行(此前成员行上 ← 静默无反应);
 *   4. 追剧页: 光标落集成员行后 ← 收起**所属集**并把光标带回集行(剧仍展开)。
 *
 * 断言口径: 按键走真实 keyboard(不借道 vm), 判据读 DOM(.kb-cursor / .selected 类, 与用户所见一致)。
 * 点行一律点名称格(.g-name / .ep-name) —— 行中心多半落在站点/标签挂件上(@click.stop 走筛选, 不展开)。
 */

for (const skin of SKINS) {
  test.describe(`键盘上下键选中分组成员 ${skin}`, () => {
    installRuntimeErrorGuard(test);

    test(`辅种页: 展开组后 ↓ 进入成员行 + Shift+↓ 范围选中 @fast (${skin})`, async ({ page }) => {
      collectRuntimeErrors(page);

      await page.goto(`${BASE_URL}/${skin}/`, { waitUntil: 'domcontentloaded' });
      await expect(page.locator('#app')).not.toHaveAttribute('v-cloak', { timeout: 15_000 });
      await expect(page.locator('.group-row').first()).toBeVisible({ timeout: 30_000 });

      // 展开第一组(点名称格)
      await page.locator('.group-row').first().locator('.g-name').click({ force: true });
      await expect(page.locator('.member-row').first()).toBeVisible({ timeout: 10_000 });

      // ↓ 必须进入成员行: 光标(虚线框)落在 .member-row, 且不再停在任何组行上
      await page.keyboard.press('ArrowDown');
      await expect(page.locator('.member-row.kb-cursor'), '↓ 必须把光标移进展开组的成员行').toHaveCount(1, {
        timeout: 5_000,
      });
      await expect(page.locator('.group-row.kb-cursor'), '光标应已离开组行').toHaveCount(0);

      // Space 选中当前成员 -> Shift+↓ 在展开组成员链内范围扩选(选中数 1 -> 2)
      await page.keyboard.press('Space');
      await expect(page.locator('.member-row.selected'), 'Space 必须选中光标所在成员').toHaveCount(1, {
        timeout: 5_000,
      });
      await page.keyboard.press('Shift+ArrowDown');
      await expect(page.locator('.member-row.selected'), 'Shift+↓ 必须在展开组的成员链内扩选').toHaveCount(2, {
        timeout: 5_000,
      });
    });

    test(`追剧页: 展开剧/集后 ↓ 进入集行与成员行 @fast (${skin})`, async ({ page }) => {
      collectRuntimeErrors(page);

      await page.goto(`${BASE_URL}/${skin}/`, { waitUntil: 'domcontentloaded' });
      await expect(page.locator('#app')).not.toHaveAttribute('v-cloak', { timeout: 15_000 });
      await page.click('nav.tabs [data-view="shows"]');
      await expect(page.locator('.show-row').first()).toBeVisible({ timeout: 30_000 });

      // 展开剧 -> ↓ 落集行
      await page.locator('.show-row').first().locator('.g-name').click({ force: true });
      await expect(page.locator('.ep-row').first()).toBeVisible({ timeout: 10_000 });
      await page.keyboard.press('ArrowDown');
      await expect(page.locator('.ep-row.kb-cursor'), '↓ 必须把光标移进展开剧的集行').toHaveCount(1, {
        timeout: 5_000,
      });

      // 展开集 -> ↓ 落成员行
      await page.locator('.ep-row').first().locator('.ep-name').click({ force: true });
      await expect(page.locator('.member-row').first()).toBeVisible({ timeout: 10_000 });
      await page.keyboard.press('ArrowDown');
      await expect(page.locator('.member-row.kb-cursor'), '↓ 必须把光标移进展开集的成员行').toHaveCount(1, {
        timeout: 5_000,
      });
    });

    test(`辅种页: 光标进成员行后 ← 收起所属分组并回组行 @fast (${skin})`, async ({ page }) => {
      collectRuntimeErrors(page);

      await page.goto(`${BASE_URL}/${skin}/`, { waitUntil: 'domcontentloaded' });
      await expect(page.locator('#app')).not.toHaveAttribute('v-cloak', { timeout: 15_000 });
      await expect(page.locator('.group-row').first()).toBeVisible({ timeout: 30_000 });

      // 展开第一组 -> ↓ 进成员行
      await page.locator('.group-row').first().locator('.g-name').click({ force: true });
      await expect(page.locator('.member-row').first()).toBeVisible({ timeout: 10_000 });
      await page.keyboard.press('ArrowDown');
      await expect(page.locator('.member-row.kb-cursor')).toHaveCount(1, { timeout: 5_000 });

      // ← 必须收起所属分组(成员行消失)并把光标带回组行(此前成员行上 ← 静默无反应)
      await page.keyboard.press('ArrowLeft');
      await expect(page.locator('.member-row'), '← 必须收起所属分组(成员行消失)').toHaveCount(0, {
        timeout: 5_000,
      });
      await expect(page.locator('.group-row.kb-cursor'), '← 后光标必须回到所属组行').toHaveCount(1, {
        timeout: 5_000,
      });
    });

    test(`追剧页: 光标进集成员行后 ← 收起所属集并回集行 @fast (${skin})`, async ({ page }) => {
      collectRuntimeErrors(page);

      await page.goto(`${BASE_URL}/${skin}/`, { waitUntil: 'domcontentloaded' });
      await expect(page.locator('#app')).not.toHaveAttribute('v-cloak', { timeout: 15_000 });
      await page.click('nav.tabs [data-view="shows"]');
      await expect(page.locator('.show-row').first()).toBeVisible({ timeout: 30_000 });

      // 展开剧 -> ↓ 落集行 -> 展开集 -> ↓ 落成员行
      await page.locator('.show-row').first().locator('.g-name').click({ force: true });
      await expect(page.locator('.ep-row').first()).toBeVisible({ timeout: 10_000 });
      await page.keyboard.press('ArrowDown');
      await expect(page.locator('.ep-row.kb-cursor')).toHaveCount(1, { timeout: 5_000 });
      await page.locator('.ep-row').first().locator('.ep-name').click({ force: true });
      await expect(page.locator('.member-row').first()).toBeVisible({ timeout: 10_000 });
      await page.keyboard.press('ArrowDown');
      await expect(page.locator('.member-row.kb-cursor')).toHaveCount(1, { timeout: 5_000 });

      // ← 收起所属集(成员行消失), 光标回集行; 剧仍展开(集行仍在)
      await page.keyboard.press('ArrowLeft');
      await expect(page.locator('.member-row'), '← 必须收起所属集(成员行消失)').toHaveCount(0, {
        timeout: 5_000,
      });
      await expect(page.locator('.ep-row.kb-cursor'), '← 后光标必须回到所属集行').toHaveCount(1, {
        timeout: 5_000,
      });
    });
  });
}
