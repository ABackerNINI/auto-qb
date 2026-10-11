// @ts-check
import { expect, test } from '@playwright/test';
import { BASE_URL, SKINS } from './harness.mjs';
import { collectRuntimeErrors, installRuntimeErrorGuard } from './lib/errors.mjs';

/**
 * 11「树表批量」吸顶表头 / 吸底统计条的贴边几何守阵(2026-10-10 用户报障) ——
 *
 * 缺陷机理: sticky 的视矩形被**滚动容器自身的 padding 内缩** —— .dt11-head 写 top:0 时
 * 实际停在 .drawer-body 的 padding-top(14px)之下, .dt11-foot 写 bottom:0 时实际停在
 * padding-bottom(20px)之上; 中途滚动时数据行文字从这两条缝里漏出来(实测 headTop 比
 * body 顶缘恒低 14px / footBottom 比 body 底缘恒高 20px)。修复 = 负 inset 抵消
 * (top:-14px / bottom:-20px, 见 11-content-treegrid-batch-low.js 内注释)。
 *
 * 断言口径: 预置 localStorage 选 11 为 content 页签模板 → page.route 桩掉
 * /api/torrents/{hash}/files(合成 90 个文件保证可滚) → 开抽屉切「内容」页签 →
 * 中途滚动 + 滚到底两档, 量 .dt11-head 顶缘 == .drawer-body 顶缘、.dt11-foot 底缘 ==
 * .drawer-body 底缘(±1px)。滚动容器 padding 一变(任一皮肤)或 inset 被改回 0, 本阵即红。
 * 桩服务的 FakeClient 默认 files=[](变体只会渲染「无文件列表」空态), 必须拦端点喂数据。
 */

/** 合成文件树: 3 季 x 6 集 x 5 文件 = 90 行(目录行另计), 足够把 .drawer-body 滚出多屏。 */
function makeFiles() {
  const files = [];
  for (let s = 0; s < 3; s++) {
    for (let e = 0; e < 6; e++) {
      for (let f = 0; f < 5; f++) {
        files.push({
          name: `Season ${s + 1} (2026)/Episode ${String(e + 1).padStart(2, '0')} - 合成数据行 S${s}E${e}F${f}.mkv`,
          size: 1_000_000_000 + f * 111_111_111 + s * 37_000_000,
          progress: f === 0 ? 1 : (f % 3) / 3,
          priority: f === 0 ? 0 : f % 2 ? 1 : 6,
          availability: f === 0 ? 0.5 : 1.2 + f * 0.1,
        });
      }
    }
  }
  return files;
}

for (const skin of SKINS) {
  test.describe(`详情抽屉 11 树表批量吸顶吸底贴边 ${skin}`, () => {
    installRuntimeErrorGuard(test);

    test('中途滚动与滚到底, 表头顶缘/统计条底缘与正文可视缘齐平 @fast', async ({ page }) => {
      collectRuntimeErrors(page);

      // files 端点桩: 必须在 goto 之前注册; FakeClient 默认文件列表为空
      await page.route('**/api/torrents/*/files', (route) =>
        route.fulfill({ contentType: 'application/json', body: JSON.stringify(makeFiles()) }));

      // 选 11 为 content 页签模板(addInitScript 必须赶在 app.js 读 localStorage 之前)
      await page.addInitScript(() => localStorage.setItem('autoqb.ui.drawerTpl', JSON.stringify({ content: '11' })));

      await page.goto(`${BASE_URL}/${skin}/`, { waitUntil: 'domcontentloaded' });
      await expect(page.locator('#app')).not.toHaveAttribute('v-cloak', { timeout: 15_000 });
      await expect(page.locator('.group-row').first()).toBeVisible({ timeout: 30_000 });

      // 种子视图平铺行双击开详情抽屉(整表 2s 重渲染抢点击 ⇒ force, 同 drawer-peers.spec)
      await page.click('nav.tabs [data-view="torrents"]');
      await expect(page.locator('.torrent-row').first()).toBeVisible({ timeout: 15_000 });
      await page.dblclick('.torrent-row >> nth=0', { force: true });

      const drawer = page.locator('.drawer-dock > .drawer');
      await expect(drawer).toBeVisible({ timeout: 5_000 });
      await drawer.locator('.drawer-tabs button', { hasText: '内容' }).click();

      const wrap = drawer.locator('.dt11-wrap');
      await expect(wrap).toBeVisible({ timeout: 5_000 });
      await expect(drawer.locator('.dt11-r').first()).toBeVisible({ timeout: 5_000 });

      const geom = () => page.evaluate(() => {
        const body = document.querySelector('.drawer .drawer-body');
        const head = document.querySelector('.drawer .dt11-head');
        const foot = document.querySelector('.drawer .dt11-foot');
        const b = body.getBoundingClientRect();
        const h = head.getBoundingClientRect();
        const f = foot.getBoundingClientRect();
        return {
          scrollable: body.scrollHeight - body.clientHeight,
          headSticky: getComputedStyle(head).position,
          footSticky: getComputedStyle(foot).position,
          gapAboveHead: h.top - b.top,
          gapBelowFoot: b.bottom - f.bottom,
        };
      });

      // 中途滚动: 表头吸顶态必须与 body 顶缘齐平(gap 0), 统计条吸底态与底缘齐平。
      // 旧缺陷形态: gap 恒等于滚动容器 padding(上 14 / 下 20), 行文字从缝里漏出。
      await page.evaluate(() => { document.querySelector('.drawer .drawer-body').scrollTop = 400; });
      await expect
        .poll(async () => (await geom()).gapAboveHead, { timeout: 5_000 })
        .toBeLessThanOrEqual(1);
      let g = await geom();
      expect(g.scrollable, '合成文件应足以滚动(桩数据 90 行)').toBeGreaterThan(400);
      expect(g.headSticky, '表头应为 sticky').toBe('sticky');
      expect(g.footSticky, '统计条应为 sticky').toBe('sticky');
      expect(Math.abs(g.gapAboveHead), '吸顶表头顶缘与正文顶缘差(旧缺陷恒 14px)').toBeLessThanOrEqual(1);
      expect(Math.abs(g.gapBelowFoot), '吸底统计条底缘与正文底缘差(旧缺陷恒 20px)').toBeLessThanOrEqual(1);

      // 滚到底: 统计条自然位(与吸底态同点), 顶缘约束依旧成立
      await page.evaluate(() => {
        const body = document.querySelector('.drawer .drawer-body');
        body.scrollTop = body.scrollHeight;
      });
      await expect
        .poll(async () => (await geom()).gapBelowFoot, { timeout: 5_000 })
        .toBeLessThanOrEqual(1);
      g = await geom();
      expect(Math.abs(g.gapAboveHead), '滚到底表头仍应贴顶').toBeLessThanOrEqual(1);
      expect(Math.abs(g.gapBelowFoot), '滚到底统计条仍应贴底').toBeLessThanOrEqual(1);
    });
  });
}
