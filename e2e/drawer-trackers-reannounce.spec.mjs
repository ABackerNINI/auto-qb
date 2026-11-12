// @ts-check
import { expect, test } from '@playwright/test';
import { baseUrl, SKINS } from './harness.mjs';
import { collectRuntimeErrors, installRuntimeErrorGuard } from './lib/errors.mjs';
import { installRouteCleanup } from './lib/route-cleanup.mjs';

/* 收尾竞态兜底(issue 26-11-13-0234): 详情/trackers 双桩回调内 await route.fetch 飞行中
 * 撞用例结束 → "Test ended" 假红; file 级 afterEach 统一卸载(机制见 route-cleanup.mjs)。 */
installRouteCleanup(test);

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
 *
 * P13 批补测(R5#94): nextOf 的**回退分支**(qB < 5.2 无 next_announce → 种子级 detail
 * .reannounce_in 全局近似 + 「全局」标 dt06-gb + 种子级微条 dt06-tbar)从未被任何测试渲染 ——
 * 上一条的真口径 spec 反而断言 .dt06-gb 恒 0, 桩恒给 next_announce。本条用 route.fetch() 取
 * 真桩响应后剥掉 next_announce/min_announce(qB<5.2 形态) + 详情桩补 reannounce/reannounce_in
 * (FakeClient 缺省 0 = nextOf 的「数据未落袋」none 档, 回退分支要求 > 0), 断言「全局」标出现、
 * 全部行同显种子级同一值(全局近似的语义本体)、微条出现、工具条注切到种子级口径文案。
 */

for (const skin of SKINS) {
  test.describe(`详情抽屉 06 逐行汇报倒计时 ${skin}`, () => {
    installRuntimeErrorGuard(test);

    test(`逐行倒计时互不相同且无「全局」标 @fast (${skin})`, async ({ page }) => {
      collectRuntimeErrors(page);

      // 选 06 为 trackers 页签模板(addInitScript 必须赶在 app.js 读 localStorage 之前)
      await page.addInitScript(() => localStorage.setItem('autoqb.ui.drawerTpl', JSON.stringify({ trackers: '06' })));

      await page.goto(`${baseUrl()}/${skin}/`, { waitUntil: 'domcontentloaded' });
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

    test(`qB<5.2 回退分支: 无 next_announce → 种子级全局近似 +「全局」标 + 微条 @fast (${skin})`, async ({ page }) => {
      collectRuntimeErrors(page);

      // 详情桩: 取真桩响应后补 reannounce/reannounce_in(FakeClient 缺省 0 = nextOf 的
      // 「数据未落袋」none 档; 回退分支要求 reannounce_in > 0, reannounce 作微条分母)
      // —— 单段 glob 只命中详情端点, 不波及 trackers 子路径(drawer-general-variants 同手法)。
      await page.route('**/api/torrents/*', async (route) => {
        const resp = await route.fetch();
        let body = null;
        try { body = await resp.json(); } catch { body = null; }
        if (!body || !body.torrent) { await route.fulfill({ response: resp }); return; }
        body.torrent.reannounce = 1800;
        body.torrent.reannounce_in = 900;
        await route.fulfill({ response: resp, json: body });
      });
      // trackers 桩: 取真桩响应后剥掉 next_announce/min_announce(qB<5.2 形态, 回退分支触发面)
      await page.route('**/api/torrents/*/trackers', async (route) => {
        const resp = await route.fetch();
        let body = null;
        try { body = await resp.json(); } catch { body = null; }
        for (const t of (Array.isArray(body) ? body : [])) {
          delete t.next_announce;
          delete t.min_announce;
        }
        await route.fulfill({ response: resp, json: body });
      });

      await page.addInitScript(() => localStorage.setItem('autoqb.ui.drawerTpl', JSON.stringify({ trackers: '06' })));
      await page.goto(`${baseUrl()}/${skin}/`, { waitUntil: 'domcontentloaded' });
      await expect(page.locator('#app')).not.toHaveAttribute('v-cloak', { timeout: 15_000 });
      await expect(page.locator('.group-row').first()).toBeVisible({ timeout: 30_000 });
      await page.click('nav.tabs [data-view="torrents"]');
      await expect(page.locator('.torrent-row').first()).toBeVisible({ timeout: 15_000 });
      await page.dblclick('.torrent-row >> nth=0', { force: true });
      const drawer = page.locator('.drawer-dock > .drawer');
      await expect(drawer).toBeVisible({ timeout: 5_000 });
      await drawer.locator('.drawer-tabs button', { hasText: 'Tracker' }).click();

      // 回退行形态: .dt06-next + 「全局」标(真口径 spec 断言恒 0 —— 这里必须出现)
      const next = drawer.locator('.dt06-next');
      await expect(next.first()).toBeVisible({ timeout: 5_000 });
      const gbs = drawer.locator('.dt06-gb');
      const gbCount = await gbs.count();
      expect(gbCount, `回退分支渲染「全局」标(桩无 next_announce), 实测 ${gbCount}`).toBeGreaterThanOrEqual(2);
      for (let i = 0; i < gbCount; i++) {
        await expect(gbs.nth(i), '全局标文案').toHaveText('全局');
      }
      // 全局近似的语义本体: 非更新中行全部同显种子级同一值(单次快照读, 免拍间竞态)
      const texts = await next.locator('b').evaluateAll((els) => els.map((e) => e.textContent.trim()));
      expect(texts.length, '非更新中行都有倒计时值').toBeGreaterThanOrEqual(2);
      expect(new Set(texts).size, `回退分支全部行同显种子级全局值, 实得 ${JSON.stringify(texts)}`).toBe(1);
      // 种子级微条(reannounce_in / reannounce = 900/1800 = 50%)出现
      const bars = drawer.locator('.dt06-tbar');
      await expect(bars.first(), '种子级微条出现(真口径行不画微条)').toBeVisible();
      expect(await bars.count(), '微条与回退行同数量').toBe(gbCount);
      // 工具条注切到种子级口径文案
      await expect(drawer.locator('.dt06-note'), '工具条注 = 种子级全局口径').toContainText('种子级全局值');
    });
  });
}
