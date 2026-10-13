/* W5 验收量具(计划 26-10-13-0811 §08 #5/#7/#8)—— 三条症状各一条真浏览器量化:
 *   #5 速度实时(症状 5): 注入两轮相邻 peers 响应, 速度格文本变化且 DOM 节点身份不变
 *      —— 「写字段, 不是重建」(L5): keyed 补丁的原节点续用, 重建则 data-live-probe 失踪。
 *   #8 勾选不跳动(症状 8, 变体 11): 连续勾选三行, 行容器 offsetTop 累计偏移为 0、行数
 *      不变、行 DOM 身份不变 —— 勾选态进驱动数据(反应式), 不走 anchTouch 换代重挂。
 *   #7 按钮不占列(症状 7, 变体 11): 交互列(ck 勾选/tgl 折叠/prio 徽章)locked 声明,
 *      右键隐藏菜单不渲染其勾选框(columns.js:458 双保险) —— 按钮列不可被列管理删除。
 * 数据口径沿用 drawer-peers-variant-tables / drawer-content-variant-tables 的桩。 */
import { test, expect } from '@playwright/test';
import { installRuntimeErrorGuard, collectRuntimeErrors } from './lib/errors.mjs';
import { BASE_URL, SKINS } from './harness.mjs';

const WIDE = { width: 2560, height: 1200 };

function makePeers(dlSpeed0) {
  const out = [];
  for (let i = 0; i < 12; i++) {
    out.push({
      ip: `${10 + (i % 200)}.${(i * 7) % 256}.${(i * 13) % 256}.${(i * 29) % 256}`,
      port: 30000 + i,
      client: `qBittorrent 5.${i % 5}.${i % 3}`,
      flags: i === 0 ? 'U D' : 'D',
      progress: (i % 10) / 10,
      dl_speed: i === 0 ? dlSpeed0 : (i % 4) * 125000,
      up_speed: (i % 3) * 250000,
      relevance: 0.5 + (i % 50) / 100,
      country_code: ['CN', 'US', 'DE'][i % 3],
      connection: ['UV', 'UT', 'IU'][i % 3],
    });
  }
  return out;
}

/* 两轮速度取「格式化后判然不同」的值(格子显示 fmtSpeedOrDash 文案, 非原始字节) */
const DL_A = 111_111;     // ≈ 108.5 KiB/s
const DL_B = 987_654_321; // ≈ 941.8 MiB/s

function makeFiles() {
  return [
    { name: 'Season 1/E01 - intro.mkv', size: 1_000_000, progress: 1, priority: 1, availability: 1.5 },
    { name: 'Season 1/E02 - part.mkv', size: 2_000_000, progress: 0.5, priority: 6, availability: 0.4 },
    { name: 'Season 2/E01 - finale.mkv', size: 4_000_000, progress: 0, priority: 0, availability: 0.8 },
    { name: 'bonus.txt', size: 100_000, progress: 1, priority: 1, availability: undefined },
  ];
}

async function openTorrentDrawer(page) {
  await page.click('nav.tabs [data-view="torrents"]');
  await expect(page.locator('.torrent-row').first()).toBeVisible({ timeout: 15_000 });
  await page.dblclick('.torrent-row >> nth=0', { force: true });
  const drawer = page.locator('.drawer-dock > .drawer');
  await expect(drawer).toBeVisible({ timeout: 5_000 });
  return drawer;
}

for (const skin of SKINS) {
  test.describe(`W5 数据通路验收 ${skin}`, () => {
    installRuntimeErrorGuard(test);

    test(`#5 速度实时: 两轮响应后速度格文本变化且节点身份不变 @fast (${skin})`, async ({ page }) => {
      collectRuntimeErrors(page);
      await page.setViewportSize(WIDE);
      let fulfillAt = 0; // 第二轮响应落地时刻(量「响应落地 → 格子更新」的延迟)
      await page.route('**/api/torrents/*/peers', (route) =>
        route.fulfill({ contentType: 'application/json', body: JSON.stringify({ peers: makePeers(DL_A) }) }));
      await page.goto(`${BASE_URL}/${skin}/`, { waitUntil: 'domcontentloaded' });
      await expect(page.locator('#app')).not.toHaveAttribute('v-cloak', { timeout: 15_000 });
      await expect(page.locator('.group-row').first()).toBeVisible({ timeout: 30_000 });

      const drawer = await openTorrentDrawer(page);
      await drawer.locator('.drawer-tabs button', { hasText: '用户' }).click();
      const firstRow = drawer.locator('.group-row[data-table="drawerPeer"]').first();
      await expect(firstRow).toBeVisible({ timeout: 10_000 });

      // 首轮: 给第 0 行的 dlspeed 格(第 5 列)打身份戳, 记下首轮文案
      const text0 = await firstRow.evaluate((row) => {
        const cell = row.children[4];
        cell.setAttribute('data-live-probe', '1');
        return cell.textContent.trim();
      });
      expect(text0, '首轮速度文案非空且非占位').not.toBe('—');

      // 第二轮: 后注册路由优先生效, 5s 轮询下一拍拿到 B 值
      await page.route('**/api/torrents/*/peers', async (route) => {
        fulfillAt = Date.now();
        await route.fulfill({ contentType: 'application/json', body: JSON.stringify({ peers: makePeers(DL_B) }) });
      });

      // 轮询最快 5s 一拍: 等文本变化(上限 8s), 落地时刻已由 fulfillAt 记录
      const changedAt = await (async () => {
        const t0 = Date.now();
        for (;;) {
          const txt = await firstRow.evaluate((row) => row.children[4] && row.children[4].textContent.trim());
          if (txt && txt !== text0) return Date.now();
          if (Date.now() - t0 > 8_000) return -1;
          await page.waitForTimeout(40);
        }
      })();
      expect(changedAt, '两轮注入后 dlspeed 格文案变化(速度实时更新)').toBeGreaterThan(0);
      expect(changedAt - fulfillAt, `响应落地→格子更新 <500ms(实测 ${changedAt - fulfillAt}ms)`).toBeLessThan(500);
      await expect(firstRow.locator('[data-live-probe="1"]'),
        '速度更新后仍是同一 DOM 节点(行未重建 = L5 写字段)').toBeAttached();
    });

    test(`#8 勾选不跳动: 连续勾选三行, 行偏移/行数/行身份零变化 @fast (${skin})`, async ({ page }) => {
      collectRuntimeErrors(page);
      await page.setViewportSize(WIDE);
      await page.route('**/api/torrents/*/files', (route) =>
        route.fulfill({ contentType: 'application/json', body: JSON.stringify(makeFiles()) }));
      await page.addInitScript(() =>
        localStorage.setItem('autoqb.ui.drawerTpl', JSON.stringify({ content: '11' })));
      await page.goto(`${BASE_URL}/${skin}/`, { waitUntil: 'domcontentloaded' });
      await expect(page.locator('#app')).not.toHaveAttribute('v-cloak', { timeout: 15_000 });
      await expect(page.locator('.group-row').first()).toBeVisible({ timeout: 30_000 });
      const drawer = await openTorrentDrawer(page);
      await drawer.locator('.drawer-tabs button', { hasText: '内容' }).click();
      const anchor = drawer.locator('[data-dt-table-anchor="drawerContentV11"]');
      await expect(anchor.locator('.group-row[data-table="drawerContentV11"]').first()).toBeVisible({ timeout: 10_000 });

      // 快照: 各行 offsetTop + 行数 + 给首行打身份戳
      const before = await anchor.evaluate((a) => {
        const rows = Array.from(a.querySelectorAll('.group-row[data-table="drawerContentV11"]'));
        rows[0].setAttribute('data-row-probe', '1');
        return { tops: rows.map((r) => r.offsetTop), n: rows.length };
      });

      // 连续勾选三个文件勾选框(非目录行 data-act="ck")
      const boxes = anchor.locator('.dt11-ck[data-act="ck"]');
      const n = Math.min(3, await boxes.count());
      expect(n).toBeGreaterThanOrEqual(2);
      for (let i = 0; i < n; i++) {
        await boxes.nth(i).click();
        await page.waitForTimeout(80); // 等一帧渲染(换代重挂若有, 此处即暴露)
      }

      const after = await anchor.evaluate((a) => {
        const rows = Array.from(a.querySelectorAll('.group-row[data-table="drawerContentV11"]'));
        return {
          tops: rows.map((r) => r.offsetTop),
          n: rows.length,
          probeAlive: !!a.querySelector('[data-row-probe="1"]'),
        };
      });
      expect(after.n, '行数不变').toBe(before.n);
      expect(after.probeAlive, '首行 DOM 身份不变(勾选=写字段, 非换代重挂)').toBe(true);
      expect(after.tops, '各行 offsetTop 逐行相等(零跳动)').toEqual(before.tops);
      // 勾选态真进驱动: 勾选框 checked 反映
      await expect(anchor.locator('.dt11-ck[data-act="ck"]:checked')).toHaveCount(n);
    });

    test(`#7 按钮不占列(不可被列管理删除): 交互列 locked 必显 @fast (${skin})`, async ({ page }) => {
      collectRuntimeErrors(page);
      await page.setViewportSize(WIDE);
      await page.route('**/api/torrents/*/files', (route) =>
        route.fulfill({ contentType: 'application/json', body: JSON.stringify(makeFiles()) }));
      await page.addInitScript(() =>
        localStorage.setItem('autoqb.ui.drawerTpl', JSON.stringify({ content: '11' })));
      await page.goto(`${BASE_URL}/${skin}/`, { waitUntil: 'domcontentloaded' });
      await expect(page.locator('#app')).not.toHaveAttribute('v-cloak', { timeout: 15_000 });
      await expect(page.locator('.group-row').first()).toBeVisible({ timeout: 30_000 });
      const drawer = await openTorrentDrawer(page);
      await drawer.locator('.drawer-tabs button', { hasText: '内容' }).click();
      const anchor = drawer.locator('[data-dt-table-anchor="drawerContentV11"]');
      const head = anchor.locator('.group-head[data-table="drawerContentV11"]');
      await expect(head).toBeVisible({ timeout: 10_000 });

      // 右键「优先级」列头(徽章 = 行动作按钮) → 列头菜单: locked 列的隐藏项为 muted「必显」,
      // 点击走 headMenuHide 的 locked 分支(只 toast 不隐藏, menu.js); ck/tgl 同口径。
      const prioHeader = head.locator('.h-cell', { hasText: '优先级' });
      await prioHeader.click({ button: 'right' });
      const menu = page.locator('.ctx-menu');
      await expect(menu).toBeVisible({ timeout: 3_000 });
      const hideItem = menu.locator('.ctx-item', { hasText: '优先级' }).first();
      await expect(hideItem, '优先级列的隐藏项标必显(L4: 动作钮不可被列管理删除)').toHaveClass(/muted/);
      await hideItem.click(); // locked: headMenuHide 只 toast 不隐藏, 菜单自收
      await expect(anchor.locator('.dt11-pbadge').first(), '点必显项后徽章列仍在').toBeAttached();
      // !勿用 Esc 收菜单 —— lifecycle 的 Esc 链优先关抽屉(drawerVisible 分支先于 headMenu),
      // 会把面板整个关掉。headMenuHide 已自收菜单, 这里直接做终态断言。

      // 终态不变量: 三类交互格子全部还在
      await expect(anchor.locator('.dt11-ck').first()).toBeAttached();
      await expect(anchor.locator('.dt11-tgl').first()).toBeAttached();
      await expect(anchor.locator('.dt11-pbadge').first()).toBeAttached();
    });
  });
}
