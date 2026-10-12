// @ts-check
import { expect, test } from '@playwright/test';
import { BASE_URL, SKINS } from './harness.mjs';
import { collectRuntimeErrors, installRuntimeErrorGuard } from './lib/errors.mjs';

/**
 * 抽屉三列表(peers/trackers/files)软切换「不闪」守卫(2026-10-13 用户报障「切换种子时用户页闪
 * 『暂无已连接用户』, 我的目标是本地毫秒级的响应」)。
 *
 * 真根因(逐帧实测, 见 drawer-switch-flicker.md 第九次形态): 软切换(FX-29)保留的是**上一个目标的
 * 已落袋结果**, 而**空列表(没有对端 / 没有 tracker)是种子的常态** —— 但三个列表 fetcher 一律置
 * `loading`, 模板门 `loading && 无行` 就把这份既有的空态顶掉一帧换成「正在加载…」, 数据(空)回来
 * 再换回 ⇒ 用户看到「『暂无已连接用户』闪烁」(临时探针实测序列 `E→L→E`, 已删)。
 * 修法 = 换目标窗口内**不置**列表 loading 门(drawer_store.js::_drawerListLoadingOn), 保留旧结果直到
 * 被新结果取代 —— 「还没到新的」由 FX-29 遮罩(160ms 延迟点亮)表达, 不由列表 loading 门表达。
 *
 * 本 spec 用 route 让**本页签的列表对所有种子恒返回空**(即"常态没有数据")—— 桩服务对每个种子恒有
 * 数据且既有全部用例都只 `dblclick nth=0` 单次打开, 这条真机路径此前零覆盖。逐帧 rAF 采样三件事:
 * ①空态全程在场(既有已落袋空态不得消失); ②全程不得出现「正在加载…」; ③换目标不得触发**重试**请求
 * (钉住"不准把空当未就绪去重拉" —— 用户明确否掉过这一取舍)。
 */

/** 三页签: 标签 / 端点段 / 空态文案 / 恒空响应体(与真机同形)。 */
const TABS = [
  {
    tab: 'peers', label: '用户', api: 'peers', empty: '暂无已连接用户',
    body: { rid: 0, full_update: true, peers: {}, peers_removed: {} },
  },
  { tab: 'trackers', label: 'Tracker', api: 'trackers', empty: '暂无 tracker', body: [] },
  { tab: 'content', label: '内容', api: 'files', empty: '无文件列表', body: [] },
];

for (const skin of SKINS) {
  test.describe(`抽屉三列表切换种子不闪 ${skin}`, () => {
    installRuntimeErrorGuard(test);

    for (const t of TABS) {
      test(`${t.label}: 切到"没有数据"的种子不得闪空态/加载, 也不得重试 @fast (${skin})`, async ({ page }) => {
        collectRuntimeErrors(page);
        const hits = /** @type {Record<string, number>} */ ({});
        await page.route(`**/api/torrents/*/${t.api}**`, (route) => {
          const m = route.request().url().match(new RegExp(`torrents/([0-9a-fA-F]+)/${t.api}`));
          const h = m ? m[1] : '';
          hits[h] = (hits[h] || 0) + 1;
          return route.fulfill({
            status: 200, contentType: 'application/json', body: JSON.stringify(t.body),
          });
        });

        await page.goto(`${BASE_URL}/${skin}/`, { waitUntil: 'domcontentloaded' });
        await expect(page.locator('#app')).not.toHaveAttribute('v-cloak', { timeout: 15_000 });
        await expect(page.locator('.group-row').first()).toBeVisible({ timeout: 30_000 });
        await page.click('nav.tabs [data-view="torrents"]');
        await expect(page.locator('.torrent-row').first()).toBeVisible({ timeout: 15_000 });

        await page.dblclick('.torrent-row >> nth=0', { force: true });
        const drawer = page.locator('.drawer-dock > .drawer');
        await expect(drawer).toBeVisible({ timeout: 5_000 });
        await drawer.locator('.drawer-tabs button', { hasText: t.label }).click();
        await expect(drawer.locator('.empty', { hasText: t.empty })).toBeVisible({ timeout: 5_000 });

        // 逐帧(rAF)采样: 总帧 / 空态在场帧 / 「正在加载…」帧
        await page.evaluate((txt) => {
          const el = document.querySelector('.drawer-dock > .drawer');
          /** @type {any} */ (window).__f = { total: 0, empty: 0, busy: 0 };
          let stop = false;
          /** @type {any} */ (window).__stop = () => { stop = true; };
          const tick = () => {
            if (stop) return;
            const f = /** @type {any} */ (window).__f;
            f.total++;
            if (el) {
              const s = el.textContent || '';
              if (s.indexOf(txt) >= 0) f.empty++;
              if (s.indexOf('正在加载') >= 0) f.busy++;
            }
            requestAnimationFrame(tick);
          };
          requestAnimationFrame(tick);
        }, t.empty);

        await page.dblclick('.torrent-row >> nth=1', { force: true });   // 软切换换目标
        await page.waitForTimeout(1200);
        const f = await page.evaluate(() => {
          /** @type {any} */ (window).__stop();
          return /** @type {any} */ (window).__f;
        });
        expect(f.busy, '切换全程不得出现「正在加载…」(常态空态不得被 loading 门顶掉)').toBe(0);
        expect(f.empty, '空态必须全程在场(既有的已落袋空态不得消失)').toBe(f.total);

        // 不重试: 切换目标只应被请求 1 次(初开 1 次 + 换目标 1 次; 有"空→重拉"即 >1)
        const hashes = Object.keys(hits);
        expect(hashes.length, '应出现"初开"与"切换"两个目标').toBeGreaterThanOrEqual(2);
        const target = hashes[hashes.length - 1];   // 切换目标(后出现的 hash)
        expect(hits[target], '空响应不得触发重拉(用户明确否掉"把空当未就绪去等")').toBe(1);

        await expect(drawer.locator('.empty', { hasText: t.empty })).toBeVisible({ timeout: 3_000 });
      });
    }
  });
}
