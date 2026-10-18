// @ts-check
import { expect, test } from '@playwright/test';
import { BASE_URL, SKINS } from './harness.mjs';
import { collectRuntimeErrors, installRuntimeErrorGuard } from './lib/errors.mjs';

/**
 * U2 用户表三变体(07 四卡仪表 / 08 五区分组 / 09 密度表) 表格体接引擎后的表面手势守阵
 * (计划 26-10-12-0527 验收面: e2e 手势红绿双验 + 偏好按 table-id 落盘) ——
 *
 * U2 起三变体的表格体不再是手搓 DOM: 变体外壳只留版式(卡片/分组头/chips), 行体/表头由
 * <aq-dt-bridge> 按 DRAWER_TABLE_DEFS 描述符 Teleport 进变体锚(data-dt-table-anchor=
 * drawerPeerV0X) —— 排序(dyn 默认 addr 升序, IP 点分数值化比较)/拖宽/右键隐藏/偏好持久化全走引擎漏斗。
 *
 * 手势清单(每条都是真手势, 不借道 vm):
 *   07: 引擎排序(默认序→点「下载」翻序) + 拖宽落盘 + 右键隐藏落盘 + 刷新双偏好回放;
 *   07/09: 筛选 chips(纯前端态) → anchTouch 桥换代重读 rowsFn, 行子集真刷新;
 *   08: 分段锚(每组一座) + 折叠组头(display 翻转不重挂) + 只看在传(quiet 组整组离场)
 *       + 组内 dyn 排序(跨组共享一座键, 与原手搓状态机同口径)。
 *
 * 数据口径: page.route 桩掉 /api/torrents/{hash}/peers, 12 个对端 flags 覆盖五桶
 * (take 'U D' / feed 'D E','D' / choke 'u' / idle 'K' / hand '') —— 与 08 bucketOf
 * 判据对齐; 速度留零档(i%3==0 无上传 / i%4==0 无下载)供 chips 过滤出非平凡子集。
 * 手法同族: drawer-bridge-stub.spec(手势三件套) / drawer-peers-columns.spec(桩 peers)。
 */

const WIDE = { width: 2560, height: 1200 };

/** 合成 peer 列表。速度键是 qB 原始的 dl_speed / up_speed(前端落袋适配, 同族 spec 口径)。 */
function makePeers() {
  const flagsPool = ['U D', 'D E', 'u', 'K', '']; // take/feed/choke/idle/hand 五桶各有着落
  const out = [];
  for (let i = 0; i < 12; i++) {
    out.push({
      ip: `${10 + (i % 200)}.${(i * 7) % 256}.${(i * 13) % 256}.${(i * 29) % 256}`,
      port: 30000 + i,
      client: `qBittorrent 5.${i % 5}.${i % 3}`,
      flags: flagsPool[i % flagsPool.length],
      progress: (i % 10) / 10,
      dl_speed: (i % 4) * 125000, // i%4==0 → 0(「下载中」chips 的非平凡子集)
      up_speed: (i % 3) * 250000, // i%3==0 → 0(「上传中」chips 同理); 峰值 i%3==2
      relevance: 0.5 + (i % 50) / 100,
      country_code: ['CN', 'US', 'DE'][i % 3],
      connection: ['UV', 'UT', 'IU'][i % 3],
    });
  }
  return out;
}

/** 第 i 个对端的 addr(行 key = ip:port, 与 rowOf 装配口径一致) */
function addrOf(i) {
  return `${10 + (i % 200)}.${(i * 7) % 256}.${(i * 13) % 256}.${(i * 29) % 256}:${30000 + i}`;
}

async function openTorrentDrawer(page) {
  await page.click('nav.tabs [data-view="torrents"]');
  await expect(page.locator('.torrent-row').first()).toBeVisible({ timeout: 15_000 });
  await page.dblclick('.torrent-row >> nth=0', { force: true });
  const drawer = page.locator('.drawer-dock > .drawer');
  await expect(drawer).toBeVisible({ timeout: 5_000 });
  return drawer;
}

/** 开抽屉 → 用户页签 → 等变体外壳与引擎表体点亮; 返回 drawer */
async function openPeersVariant(page, variantId) {
  const drawer = await openTorrentDrawer(page);
  await drawer.locator('.drawer-tabs button', { hasText: /^用户$/ }).click();
  await expect(drawer.locator(`.dt${variantId}-wrap`)).toBeVisible({ timeout: 10_000 });
  const anchor = drawer.locator(`[data-dt-table-anchor="drawerPeerV${variantId}"]`);
  await expect(anchor.locator('.group-head[data-table="drawerPeerV' + variantId + '"]').first(),
    '变体桥表头点亮(U2: 表格体归引擎)').toBeVisible({ timeout: 10_000 });
  return drawer;
}

for (const skin of SKINS) {
  test.describe(`用户表三变体手势 ${skin}`, () => {
    installRuntimeErrorGuard(test);

    test(`dt07 手势三件套: 默认序/引擎排序/拖宽/右键隐藏(偏好按 table-id 落盘+回放) @fast (${skin})`, async ({ page }) => {
      collectRuntimeErrors(page);
      await page.setViewportSize(WIDE);
      await page.route('**/api/torrents/*/peers', (route) =>
        route.fulfill({ contentType: 'application/json', body: JSON.stringify({ peers: makePeers() }) }));
      await page.addInitScript(() =>
        localStorage.setItem('autoqb.ui.drawerTpl', JSON.stringify({ peers: '07' })));
      await page.goto(`${BASE_URL}/${skin}/`, { waitUntil: 'domcontentloaded' });
      await expect(page.locator('#app')).not.toHaveAttribute('v-cloak', { timeout: 15_000 });
      await expect(page.locator('.group-row').first()).toBeVisible({ timeout: 30_000 });
      const drawer = await openPeersVariant(page, '07');
      const anchor = drawer.locator('[data-dt-table-anchor="drawerPeerV07"]');

      // files 列常驻(26-10-13-0811 渐进已删): 无 files 数据仍 10 列, 值格出 — 占位
      await expect(anchor.locator('.group-head .h-cell')).toHaveCount(10);
      await expect(
        anchor.locator('.group-row[data-table="drawerPeerV07"]').first().locator('.dt07-files'),
      ).toHaveText('—');

      // 默认序 = addr 升序(2026-10-18 用户报障改口径, defKey/defDir; IP 点分数值化比较):
      // 桩 fixture 首段恒 10, 数值序 = i 升序 → 首行 = i=0
      await expect(anchor.locator('.group-row[data-table="drawerPeerV07"]').first())
        .toContainText(addrOf(0));

      // 排序: 点「下载」列头 → 引擎三态第一击(降序箭头亮), 首行换人(375000 峰值 = i=3)
      await anchor.locator('.h-cell.hc-dlspeed').click();
      await expect(anchor.locator('.h-cell.hc-dlspeed .arrow svg'), '引擎排序箭头点亮').toBeVisible({ timeout: 5_000 });
      await expect(anchor.locator('.group-row[data-table="drawerPeerV07"]').first())
        .toContainText(addrOf(3));

      // 拖宽: client 列 resizer 右拖 60px → 按桌 table-id 落盘(autoqb_cols_v5)
      const resizer = anchor.locator('.h-cell.hc-client .resizer');
      const rb = await resizer.boundingBox();
      await page.mouse.move(rb.x + rb.width / 2, rb.y + rb.height / 2);
      await page.mouse.down();
      await page.mouse.move(rb.x + rb.width / 2 + 60, rb.y + rb.height / 2, { steps: 6 });
      await page.mouse.up();
      const cols = JSON.parse(await page.evaluate(() => localStorage.getItem('autoqb_cols_v5') || '{}'));
      expect(cols?.pages?.drawerPeerV07?.w?.client, '拖宽必须按 table-id 持久化(引擎同一漏斗)').toBeTruthy();

      // 右键隐藏: client 列头右键 → 隐藏「客户端」 → 10→9 列 + 落盘
      await anchor.locator('.h-cell.hc-client').click({ button: 'right' });
      await page.locator('.ctx-menu').locator('.ctx-item', { hasText: '隐藏「客户端」' }).click();
      await expect(anchor.locator('.group-head .h-cell'), '右键隐藏即时生效').toHaveCount(9);
      const cols2 = JSON.parse(await page.evaluate(() => localStorage.getItem('autoqb_cols_v5') || '{}'));
      expect(cols2?.pages?.drawerPeerV07?.hidden, '隐藏必须按 table-id 持久化').toContain('client');

      // 刷新双偏好回放: 模板(autoqb.ui.drawerTpl) + 列偏好(autoqb_cols_v5)都持久化
      await page.reload({ waitUntil: 'domcontentloaded' });
      await expect(page.locator('#app')).not.toHaveAttribute('v-cloak', { timeout: 15_000 });
      await expect(page.locator('.group-row').first()).toBeVisible({ timeout: 30_000 });
      const drawer2 = await openPeersVariant(page, '07');
      const anchor2 = drawer2.locator('[data-dt-table-anchor="drawerPeerV07"]');
      await expect(anchor2.locator('.group-head .h-cell'), '刷新后隐藏偏好回放(9 列)').toHaveCount(9);
    });

    /* 红验手法: 初始数据落袋后把 peers 端点**挂起不响应**(路由 hang, fetch 永远 pending,
     * peersError 不落) —— 落袋数据冻结, 行刷新唯一驱动 = anchTouch 桥换代重读 rowsFn。
     * 排除「5s 轮询 tick 重读恰好路过」的假绿(实测 anchTouch 空操作时行靠轮询延迟刷新)。 */
    test(`dt07 筛选 chips: anchTouch 桥换代重读 rowsFn, 行子集真刷新 @fast (${skin})`, async ({ page }) => {
      collectRuntimeErrors(page);
      await page.setViewportSize(WIDE);
      await page.route('**/api/torrents/*/peers', (route) =>
        route.fulfill({ contentType: 'application/json', body: JSON.stringify({ peers: makePeers() }) }));
      await page.addInitScript(() =>
        localStorage.setItem('autoqb.ui.drawerTpl', JSON.stringify({ peers: '07' })));
      await page.goto(`${BASE_URL}/${skin}/`, { waitUntil: 'domcontentloaded' });
      await expect(page.locator('#app')).not.toHaveAttribute('v-cloak', { timeout: 15_000 });
      await expect(page.locator('.group-row').first()).toBeVisible({ timeout: 30_000 });
      const drawer = await openPeersVariant(page, '07');
      const anchor = drawer.locator('[data-dt-table-anchor="drawerPeerV07"]');
      await expect(anchor.locator('.group-row[data-table="drawerPeerV07"]')).toHaveCount(12);

      // 冻结轮询(初始数据已落袋): 后注册的路由优先生效, 后续 peers 请求全部挂起
      await page.route('**/api/torrents/*/peers', (route) => { /* hang: 不 fulfill */ });

      await drawer.locator('.dt07-fchip[data-f="up"]').click();
      await expect(drawer.locator('.dt07-fchip[data-f="up"]'), '激活态随筛选输出').toHaveClass(/active/);
      await expect(anchor.locator('.group-row[data-table="drawerPeerV07"]'),
        'anchTouch 换代重读 rowsFn: 行子集真刷新(轮询已冻结, 只能靠桥换代)').toHaveCount(8);
      await expect(anchor.locator('.group-head[data-table="drawerPeerV07"]'),
        '桥重挂后表头仍在(锚保活, 锚元素身份未变)').toBeVisible();

      await drawer.locator('.dt07-fchip[data-f="all"]').click();
      await expect(anchor.locator('.group-row[data-table="drawerPeerV07"]')).toHaveCount(12);
    });

    test(`dt09 筛选 chips: anchTouch 桥换代重读 rowsFn, 行子集真刷新 @fast (${skin})`, async ({ page }) => {
      collectRuntimeErrors(page);
      await page.setViewportSize(WIDE);
      await page.route('**/api/torrents/*/peers', (route) =>
        route.fulfill({ contentType: 'application/json', body: JSON.stringify({ peers: makePeers() }) }));
      await page.addInitScript(() =>
        localStorage.setItem('autoqb.ui.drawerTpl', JSON.stringify({ peers: '09' })));
      await page.goto(`${BASE_URL}/${skin}/`, { waitUntil: 'domcontentloaded' });
      await expect(page.locator('#app')).not.toHaveAttribute('v-cloak', { timeout: 15_000 });
      await expect(page.locator('.group-row').first()).toBeVisible({ timeout: 30_000 });
      const drawer = await openPeersVariant(page, '09');
      const anchor = drawer.locator('[data-dt-table-anchor="drawerPeerV09"]');
      await expect(anchor.locator('.group-row[data-table="drawerPeerV09"]')).toHaveCount(12);

      await page.route('**/api/torrents/*/peers', (route) => { /* hang: 冻结轮询(同 07 红验手法) */ });

      await drawer.locator('.dt09-fchip[data-f="down"]').click();
      await expect(anchor.locator('.group-row[data-table="drawerPeerV09"]')).toHaveCount(9);
      await drawer.locator('.dt09-fchip[data-f="all"]').click();
      await expect(anchor.locator('.group-row[data-table="drawerPeerV09"]')).toHaveCount(12);
    });

    test(`dt08 分段锚/折叠/只看在传/组内 dyn 排序 @fast (${skin})`, async ({ page }) => {
      collectRuntimeErrors(page);
      await page.setViewportSize(WIDE);
      await page.route('**/api/torrents/*/peers', (route) =>
        route.fulfill({ contentType: 'application/json', body: JSON.stringify({ peers: makePeers() }) }));
      await page.addInitScript(() =>
        localStorage.setItem('autoqb.ui.drawerTpl', JSON.stringify({ peers: '08' })));
      await page.goto(`${BASE_URL}/${skin}/`, { waitUntil: 'domcontentloaded' });
      await expect(page.locator('#app')).not.toHaveAttribute('v-cloak', { timeout: 15_000 });
      await expect(page.locator('.group-row').first()).toBeVisible({ timeout: 30_000 });
      const drawer = await openPeersVariant(page, '08');
      const anchor = drawer.locator('[data-dt-table-anchor="drawerPeerV08"]');

      // 分段桥: 桶覆盖 take(3)/feed(3)/choke(2)/idle(2)/hand(2); idle+hand 默认折叠 → 未折叠组恰 3
      await expect(drawer.locator('.dt08-grp:not(.folded) [data-dt-table-anchor="drawerPeerV08"]'),
        '分段锚逐组一座(折叠组不计)').toHaveCount(3);
      await expect(anchor.locator('.group-head[data-table="drawerPeerV08"]').first()).toBeVisible();

      // 组内 dyn 排序(D3 默认 addr 升序, 跨组共享一座键): take 组成员 {0,5,10}, 数值序首行 = i=0
      const take = drawer.locator('.dt08-grp[data-grp="take"]');
      await expect(take.locator('.group-row[data-table="drawerPeerV08"]').first())
        .toContainText(addrOf(0));

      // 折叠手势: 展开 idle(默认折叠) → 段锚内 2 行可见; 折叠 take → display 翻转(不重挂)
      const idle = drawer.locator('.dt08-grp[data-grp="idle"]');
      await expect(idle, 'idle 默认折叠').toHaveClass(/folded/);
      await idle.locator('.dt08-ghead').click();
      await expect(idle).not.toHaveClass(/folded/);
      await expect(idle.locator('.group-row[data-table="drawerPeerV08"]')).toHaveCount(2);
      await take.locator('.dt08-ghead').click();
      await expect(take).toHaveClass(/folded/);

      // 只看在传: quiet 组(idle/hand)整组离场(anchTouch 换代重读 rowsFn), 在传组保留
      await drawer.locator('[data-toggle]').click();
      await expect(drawer.locator('.dt08-toggle'), '只看在传激活态').toHaveClass(/active/);
      await expect(drawer.locator('[data-grp="idle"]'), 'quiet 组整组离场').toHaveCount(0);
      await expect(drawer.locator('[data-grp="hand"]')).toHaveCount(0);
      await expect(drawer.locator('.dt08-grp:not(.folded)'), '在传组(feed/choke)保留').toHaveCount(2);
      await expect(drawer.locator('.dt08-grp:not(.folded) .group-head[data-table="drawerPeerV08"]').first(),
        '桥重挂后表头仍在(锚保活; take 上一步被折叠, 取未折叠组量)').toBeVisible();

      // 关掉只看: idle 回场且保持用户展开态(折叠态自保, 不回默认)
      await drawer.locator('[data-toggle]').click();
      await expect(drawer.locator('[data-grp="idle"]')).toHaveCount(1);
      await expect(idle).not.toHaveClass(/folded/);
      await expect(idle.locator('.group-row[data-table="drawerPeerV08"]')).toHaveCount(2);
      await expect(take, 'take 折叠态自保').toHaveClass(/folded/);
    });
  });
}
