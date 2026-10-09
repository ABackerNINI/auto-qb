// @ts-check
import { expect, test } from '@playwright/test';
import { BASE_URL, SKINS } from './harness.mjs';
import { collectRuntimeErrors, installRuntimeErrorGuard } from './lib/errors.mjs';

/**
 * 07「增强仪表盘」/ 09「密度表」(peers 页签)吸顶表头贴边几何守阵(2026-10-10 同族清偿) ——
 *
 * 与 dt11 同一机理(单点: pitfalls/web-ui/sticky-scrollpad-inset.md): sticky 视矩形被滚动
 * 容器 `.drawer-body` 自身 padding 内缩 —— 表头写 top:0 时实际停在 padding-top(14px)之下,
 * 中途滚动时 peer 行文字从那条缝里漏出来。修复 = top:-14px 抵消。本阵在两变体 × 双皮肤上
 * 量「吸顶态表头顶缘 == .drawer-body 顶缘(±1px)」; 滚动容器 padding 一变或 inset 被改回 0 即红。
 *
 * 断言口径: page.route 桩掉 /api/torrents/{hash}/peers(合成 40 个 peer 保证可滚 —— 桩服务
 * 默认每种子只有 1~7 个 peer, 滚不起来) → 预置 localStorage 选 07/09 为 peers 页签模板 →
 * 开抽屉切「用户」页签 → 中途滚动量齐平。文件列表端点的同款守阵见
 * drawer-content-dt11-sticky.spec.mjs(dt11 吸顶 + 吸底两档)。
 */

/** 合成 peer 列表: 40 行让 .drawer-body 滚出数屏。字段集与 qB sync/torrentPeers 同形。 */
function makePeers(n) {
  const ccs = ['CN', 'US', 'DE', 'JP', 'BR'];
  const conns = ['UV', 'UT', 'IU', 'IT'];
  const out = [];
  for (let i = 0; i < n; i++) {
    out.push({
      ip: `${10 + (i % 200)}.${(i * 7) % 256}.${(i * 13) % 256}.${(i * 29) % 256}`,
      port: 30000 + i,
      client: `qBittorrent 5.${i % 5}.${i % 3}`,
      flags: i % 3 ? 'U D' : 'U D H',
      progress: (i % 10) / 10,
      dlspeed: (i % 4) * 125000,
      upspeed: (i % 3) * 250000,
      relevance: 0.5 + (i % 50) / 100,
      country_code: ccs[i % ccs.length],
      connection: conns[i % conns.length],
    });
  }
  return out;
}

const VARIANTS = [
  { id: '07', label: '增强仪表盘' },
  { id: '09', label: '密度表' },
];

for (const skin of SKINS) {
  test.describe(`详情抽屉 07/09 peers 吸顶贴边 ${skin}`, () => {
    installRuntimeErrorGuard(test);

    for (const v of VARIANTS) {
      test(`dt${v.id} ${v.label}中途滚动表头顶缘与正文顶缘齐平 @fast (${skin})`, async ({ page }) => {
        collectRuntimeErrors(page);

        // peers 端点桩: 必须在 goto 之前注册; 桩服务默认每种子 1~7 个 peer 滚不起来
        await page.route('**/api/torrents/*/peers', (route) =>
          route.fulfill({ contentType: 'application/json', body: JSON.stringify({ peers: makePeers(40) }) }));

        // 预选变体(addInitScript 必须赶在 app.js 读 localStorage 之前)
        await page.addInitScript(
          (id) => localStorage.setItem('autoqb.ui.drawerTpl', JSON.stringify({ peers: id })),
          v.id,
        );

        await page.goto(`${BASE_URL}/${skin}/`, { waitUntil: 'domcontentloaded' });
        await expect(page.locator('#app')).not.toHaveAttribute('v-cloak', { timeout: 15_000 });
        await expect(page.locator('.group-row').first()).toBeVisible({ timeout: 30_000 });

        // 种子视图平铺行双击开详情抽屉(整表 2s 重渲染抢点击 ⇒ force, 同 drawer-peers.spec)
        await page.click('nav.tabs [data-view="torrents"]');
        await expect(page.locator('.torrent-row').first()).toBeVisible({ timeout: 15_000 });
        await page.dblclick('.torrent-row >> nth=0', { force: true });

        const drawer = page.locator('.drawer-dock > .drawer');
        await expect(drawer).toBeVisible({ timeout: 5_000 });
        await drawer.locator('.drawer-tabs button', { hasText: '用户' }).click();

        const wrap = drawer.locator(`.dt${v.id}-wrap`);
        await expect(wrap).toBeVisible({ timeout: 5_000 });
        await expect(drawer.locator(`.dt${v.id}-r`).first()).toBeVisible({ timeout: 5_000 });

        await page.evaluate(() => { document.querySelector('.drawer .drawer-body').scrollTop = 300; });
        const geom = await page.evaluate((id) => {
          const body = document.querySelector('.drawer .drawer-body');
          return new Promise((res) => requestAnimationFrame(() => requestAnimationFrame(() => {
            const b = body.getBoundingClientRect();
            const head = document.querySelector(`.drawer .dt${id}-head`);
            const h = head.getBoundingClientRect();
            res({
              scrollable: body.scrollHeight - body.clientHeight,
              headSticky: getComputedStyle(head).position,
              gapAboveHead: h.top - b.top,
            });
          })));
        }, v.id);

        expect(geom.scrollable, '合成 peer 应足以滚动(桩数据 40 行)').toBeGreaterThan(200);
        expect(geom.headSticky, '表头应为 sticky').toBe('sticky');
        expect(Math.abs(geom.gapAboveHead), '吸顶表头顶缘与正文顶缘差(旧缺陷恒 14px)').toBeLessThanOrEqual(1);
      });
    }
  });
}
