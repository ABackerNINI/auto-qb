// @ts-check
import { expect, test } from '@playwright/test';
import { BASE_URL, SKINS } from './harness.mjs';
import { collectRuntimeErrors, installRuntimeErrorGuard } from './lib/errors.mjs';

/**
 * 停靠面板几何稳定(2026-10-07 修「种子详情面板/流量图在搜索/筛选时跳动」) —— 静态守阵
 * (test_webui_static_skins.py::test_frontend_search_pending_no_collapse)钉的是接线存在性; 本 spec 钉**行为**:
 * 静态守阵探不到「调用存在但几何/时机错」的缺陷(dock-panel 坑档 2026-10-04 教训), 必须真浏览器采样。
 *
 * 两个被修缺陷的真机指纹(修复前取证, prism 皮肤 1280x800, 逐帧采样):
 * 1. 搜索待响应窗(防抖 400ms + 请求往返)把列表塌成 0 行 => docH 18582→800(塌到视口高)→1141,
 *    滚动位置被钳回 0(列表中部搜一次整页跳顶), 面板 top 430↔416 反复横跳;
 * 2. 列表被筛短后文档变矮, .drawer-dock 的 sticky 吸底脱锚, 面板跟着内容末尾上浮(视口越高跳越多)。
 *
 * 断言口径: 面板开着逐字输入搜索词, 全程逐帧采样 —— 面板 top 偏差 ≤2px(吸底锚点稳定),
 * 且 docH 任一时刻不塌到视口高 +150px 以内(真结果落袋 docH = 视口高+行数; 待响应塌列表 = 恰视口高)。
 */

for (const skin of SKINS) {
  test.describe(`停靠面板几何稳定 ${skin}`, () => {
    installRuntimeErrorGuard(test);

    test(`搜索全程面板 top 不变、文档高不塌 @fast (${skin})`, async ({ page }) => {
      collectRuntimeErrors(page);

      await page.goto(`${BASE_URL}/${skin}/`, { waitUntil: 'domcontentloaded' });
      await expect(page.locator('#app')).not.toHaveAttribute('v-cloak', { timeout: 15_000 });
      await expect(page.locator('.group-row').first()).toBeVisible({ timeout: 30_000 });

      // 种子视图平铺行双击开详情面板
      await page.click('nav.tabs [data-view="torrents"]');
      await expect(page.locator('.torrent-row').first()).toBeVisible({ timeout: 15_000 });
      await page.dblclick('.torrent-row >> nth=0', { force: true }); // force: 整表 2s 重渲染抢点击(smoke.md)
      await expect(page.locator('.drawer-dock > .drawer')).toBeVisible({ timeout: 5_000 });
      // 等面板几何落定(enter 动画 + 详情到手长到 42vh): top/height 连续 250ms 不再变化才算落定,
      // 否则采样把"进场长高"也算进偏差, 与搜索无关的初始 settle 会误红
      await page.waitForFunction(() => {
        const r = document.querySelector('.drawer-dock').getBoundingClientRect();
        const cur = JSON.stringify([Math.round(r.top), Math.round(r.height)]);
        if (window.__geoSettled === cur) return true;
        window.__geoSettled = cur;
        return false;
      }, undefined, { timeout: 10_000, polling: 250 });

      // 逐帧采样贯穿: 输入 → 防抖 → 请求在途 → 落袋换列表
      await page.evaluate(() => {
        window.__geo = [];
        const tick = () => {
          const r = document.querySelector('.drawer-dock').getBoundingClientRect();
          window.__geo.push({ top: Math.round(r.top), docH: document.documentElement.scrollHeight });
          if (window.__geo.length < 1200) requestAnimationFrame(tick);
        };
        requestAnimationFrame(tick);
      });

      const input = page.locator('.search-box input');
      await input.click();
      await input.pressSequentially('GROUP7', { delay: 120 }); // 桩数据里 ~5 个命中(短结果, 落袋必缩列表)
      // 等落袋: 列表确实换成短结果(docH 缩小)后, 几何才允许定格
      await expect
        .poll(() => page.evaluate(() => document.documentElement.scrollHeight), { timeout: 10_000 })
        .toBeLessThan(15_000);

      const geo = await page.evaluate(() => { window.__geo = window.__geo || []; return window.__geo; });
      expect(geo.length, '逐帧采样应有足够样本').toBeGreaterThan(30);
      const tops = geo.map((s) => s.top);
      const topSpan = Math.max(...tops) - Math.min(...tops);
      expect(topSpan, `面板 top 全程偏差(实测 ${Math.min(...tops)}~${Math.max(...tops)})`).toBeLessThanOrEqual(2);
      const minDocH = Math.min(...geo.map((s) => s.docH));
      // 塌列表指纹 = 恰视口高(内容撑不起文档); 留 150px 余量把真短结果(视口高 + 数行)与塌列表分开
      expect(minDocH, `文档高不得塌到近视口高(实测最小 ${minDocH}, 视口 ${await page.evaluate(() => innerHeight)})`)
        .toBeGreaterThan(await page.evaluate(() => innerHeight) + 150);
    });
  });
}
