// @ts-check
import { expect, test } from '@playwright/test';
import { BASE_URL, SKINS } from './harness.mjs';
import { collectRuntimeErrors, installRuntimeErrorGuard } from './lib/errors.mjs';

/**
 * 06 变体逐行汇报倒计时真 per-tracker 口径渲染(issue 26-10-07-0149, P-02 升级, 2026-10-09) ——
 *
 * 为什么需要它: 06「增强表格」变体的逐行「下次汇报」列此前对**所有行**显示同一个种子级全局值
 * (detail.reannounce_in)并标「全局」。P-02 升级后改读**行级 next_announce**(qB 5.2+ 随
 * /trackers 透传, Unix epoch 秒)减 now —— 桩服务若不灌多条含 next_announce 的 tracker
 * (FakeClient 默认只回单条无该字段), 真口径渲染路径在 e2e / 截图里从未被覆盖。
 *
 * 断言口径: 预置 localStorage 选 06 为 trackers 页签模板 → 打开种子详情抽屉 → 切「Tracker」
 * 页签 → 变体宿主内渲染出 ≥2 行 .dt06-next, 且其文本**至少两种**(逐行真值不同), 同时「全局」标
 * (.dt06-gb)数量为 0(真口径行不标全局)。真实手势(locator click), 不借道 vm。
 */

for (const skin of SKINS) {
  test.describe(`详情抽屉 06 逐行汇报倒计时 ${skin}`, () => {
    installRuntimeErrorGuard(test);

    test(`逐行倒计时互不相同且无「全局」标 @fast (${skin})`, async ({ page }) => {
      collectRuntimeErrors(page);

      // 选 06 为 trackers 页签模板(addInitScript 必须赶在 app.js 读 localStorage 之前)
      await page.addInitScript(() => localStorage.setItem('autoqb.ui.drawerTpl', JSON.stringify({ trackers: '06' })));

      await page.goto(`${BASE_URL}/${skin}/`, { waitUntil: 'domcontentloaded' });
      await expect(page.locator('#app')).not.toHaveAttribute('v-cloak', { timeout: 15_000 });
      await expect(page.locator('.group-row').first()).toBeVisible({ timeout: 30_000 });

      // 种子视图平铺行双击开详情抽屉(整表 2s 重渲染抢点击 ⇒ force, 同 drawer-peers.spec)
      await page.click('nav.tabs [data-view="torrents"]');
      await expect(page.locator('.torrent-row').first()).toBeVisible({ timeout: 15_000 });
      await page.dblclick('.torrent-row >> nth=0', { force: true });

      const drawer = page.locator('.drawer-dock > .drawer');
      await expect(drawer).toBeVisible({ timeout: 5_000 });

      // 切「Tracker」页签: 触发 /api/torrents/{hash}/trackers 拉取 + 06 变体渲染
      await drawer.locator('.drawer-tabs button', { hasText: 'Tracker' }).click();

      // 变体宿主内的逐行倒计时(桩恒有 2 行非「更新中」, 真口径倒计时可渲染)
      const next = drawer.locator('.dt06-next b');
      await expect(next.first()).toBeVisible({ timeout: 5_000 });
      const count = await next.count();
      expect(count, '06 逐行倒计时渲染出 ≥2 行').toBeGreaterThanOrEqual(2);

      const texts = [];
      for (let i = 0; i < count; i++) texts.push((await next.nth(i).innerText()).trim());
      expect(new Set(texts).size, `逐行倒计时应互不相同, 实得 ${JSON.stringify(texts)}`).toBeGreaterThan(1);

      // 真口径行不得带「全局」标(只有回退分支才有)
      await expect(drawer.locator('.dt06-gb')).toHaveCount(0);
    });
  });
}
