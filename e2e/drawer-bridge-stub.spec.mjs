// @ts-check
import { expect, test } from '@playwright/test';
import { BASE_URL, SKINS } from './harness.mjs';
import { collectRuntimeErrors, installRuntimeErrorGuard } from './lib/errors.mjs';

/**
 * 变体表格体 Teleport 锚桥 —— U1 硬闸门(计划 26-10-12-0527, 拍板 D1 = Teleport 锚):
 * 变体外壳(字符串 DOM)在表格区输出空锚 `data-dt-table-anchor="<tableId>"`, drawer.html 的
 * <aq-dt-bridge> 把引擎表壳(aq-table)+ 行渲染器 Teleport 进锚 —— 排序/拖宽/右键隐藏/偏好
 * 持久化与主视图同源(columns.js/sort.js 按 table-id 消费)。
 *
 * 验证载体 = stub 变体 `stubbridge`(drawer_tpl/90, 仅 ?dtstub 查询参数激活, 生产零观感):
 * chrome + 锚, 表格体全走引擎(drawerStubV0 描述符: peer 行模型 × 5 列子集)。
 *
 * 四条挂载时序路径(W7 $nextTick 教训面, 每条都必须真手势通过):
 *   A 初开: 打开抽屉 → 右键选 stub → 桥点亮(表头 + 行在锚内);
 *   B 页签切换: peers → trackers → peers: 宿主卸/挂(锚换代), 桥重挂进当前锚;
 *   C 软切换换目标: stub 激活下双击另一种子 → 抽屉不关、数据重拉, 桥稳定存活且行更新;
 *   D 合并双列: 开 tp 合并对 → peers 列选 stub → 桥在合并列锚内点亮。
 *
 * 断言口径: 真实手势(右键/拖拽/双击), 不借道 vm; 手势三件套(排序箭头 / 拖宽落盘 /
 * 右键隐藏落盘)证明引擎行为真到桥内 —— 不是只把 DOM 摆进去。
 */

const WIDE = { width: 2560, height: 1200 };
const STUB_ITEM = '.ctx-item:has-text("桥验证")';
const ANCHOR = '[data-dt-table-anchor="drawerStubV0"]';

async function openTorrentDrawer(page) {
  await page.click('nav.tabs [data-view="torrents"]');
  await expect(page.locator('.torrent-row').first()).toBeVisible({ timeout: 15_000 });
  await page.dblclick('.torrent-row >> nth=0', { force: true });
  const drawer = page.locator('.drawer-dock > .drawer');
  await expect(drawer).toBeVisible({ timeout: 5_000 });
  return drawer;
}

/* 打开抽屉 → 切用户页签 → 右键选 stub → 桥点亮; 返回 drawer 与锚 locator */
async function selectStub(page, drawer) {
  await drawer.locator('.drawer-tabs button', { hasText: /^用户$/ }).click();
  await expect(drawer.locator('.group-row[data-table="drawerPeer"]').first()).toBeVisible({ timeout: 10_000 });
  await drawer.locator('.drawer-body').click({ button: 'right' });
  await page.locator('.ctx-menu').locator(STUB_ITEM).click();
  const anchor = drawer.locator(ANCHOR);
  await expect(anchor.locator('.group-head[data-table="drawerStubV0"]'), '桥表头点亮(U1 闸门)')
    .toBeVisible({ timeout: 10_000 });
  await expect(anchor.locator('.group-row[data-table="drawerStubV0"]').first()).toBeVisible();
  return anchor;
}

for (const skin of SKINS) {
  test.describe(`变体表格体桥(stub) ${skin}`, () => {
    installRuntimeErrorGuard(test);

    test(`生产不可见: 无 ?dtstub 时菜单无 stub 项、锚零个 @fast (${skin})`, async ({ page }) => {
      collectRuntimeErrors(page);
      await page.setViewportSize(WIDE);
      await page.goto(`${BASE_URL}/${skin}/`, { waitUntil: 'domcontentloaded' });
      await expect(page.locator('#app')).not.toHaveAttribute('v-cloak', { timeout: 15_000 });
      await expect(page.locator('.group-row').first()).toBeVisible({ timeout: 30_000 });
      const drawer = await openTorrentDrawer(page);
      await drawer.locator('.drawer-tabs button', { hasText: /^用户$/ }).click();
      await expect(drawer.locator('.group-row[data-table="drawerPeer"]').first()).toBeVisible({ timeout: 10_000 });
      await drawer.locator('.drawer-body').click({ button: 'right' });
      await expect(page.locator('.ctx-menu')).toBeVisible();
      await expect(page.locator('.ctx-menu').locator(STUB_ITEM), 'stub 必须被 ?dtstub 门挡在生产外').toHaveCount(0);
      await expect(drawer.locator(ANCHOR)).toHaveCount(0);
    });

    test(`路径A 初开 + 手势三件套: 排序/拖宽/右键隐藏(偏好按 table-id 落盘) @fast (${skin})`, async ({ page }) => {
      collectRuntimeErrors(page);
      await page.setViewportSize(WIDE);
      await page.goto(`${BASE_URL}/${skin}/?dtstub=1`, { waitUntil: 'domcontentloaded' });
      await expect(page.locator('#app')).not.toHaveAttribute('v-cloak', { timeout: 15_000 });
      await expect(page.locator('.group-row').first()).toBeVisible({ timeout: 30_000 });
      const drawer = await openTorrentDrawer(page);
      const anchor = await selectStub(page, drawer);

      // 列子集(D2): 5 列 = DRAWER_PEER_COLUMNS 裁剪(addr/client/progress/dlspeed/upspeed)
      await expect(anchor.locator('.group-head .h-cell')).toHaveCount(5);

      // 排序: 点 addr 列头 → 引擎三态第一击(降序箭头 svg 亮 —— grid 模式指示器 = svg 本身) —— setSort(key, tableId) 桥内生效
      await anchor.locator('.h-cell.hc-addr').click();
      await expect(anchor.locator('.h-cell.hc-addr .arrow svg'), '桥内排序箭头点亮').toBeVisible({ timeout: 5_000 });

      // 拖宽: client 列 resizer 右拖 60px → 引擎固化宽度并按 table-id 落盘(autoqb_cols_v5)
      const resizer = anchor.locator('.h-cell.hc-client .resizer');
      const rb = await resizer.boundingBox();
      await page.mouse.move(rb.x + rb.width / 2, rb.y + rb.height / 2);
      await page.mouse.down();
      await page.mouse.move(rb.x + rb.width / 2 + 60, rb.y + rb.height / 2, { steps: 6 });
      await page.mouse.up();
      const cols = JSON.parse(await page.evaluate(() => localStorage.getItem('autoqb_cols_v5') || '{}'));
      expect(cols?.pages?.drawerStubV0?.w?.client, '拖宽必须按 table-id 持久化(引擎同一漏斗)').toBeTruthy();

      // 右键隐藏: client 列头右键 → 隐藏「客户端」 → 列出表(h-cell 5→4) + 落盘
      await anchor.locator('.h-cell.hc-client').click({ button: 'right' });
      await page.locator('.ctx-menu').locator('.ctx-item', { hasText: '隐藏「客户端」' }).click();
      await expect(anchor.locator('.group-head .h-cell'), '右键隐藏即时生效').toHaveCount(4);
      const cols2 = JSON.parse(await page.evaluate(() => localStorage.getItem('autoqb_cols_v5') || '{}'));
      expect(cols2?.pages?.drawerStubV0?.hidden, '隐藏必须按 table-id 持久化').toContain('client');

      // 刷新后双偏好回放: 模板选择(autoqb.ui.drawerTpl)+ 列偏好(autoqb_cols_v5)都持久化 ——
      // 重开抽屉 stub 自动恢复(无需再选), 隐藏列保持(4 列)。
      await page.reload({ waitUntil: 'domcontentloaded' });
      await expect(page.locator('#app')).not.toHaveAttribute('v-cloak', { timeout: 15_000 });
      await expect(page.locator('.group-row').first()).toBeVisible({ timeout: 30_000 });
      const drawer2 = await openTorrentDrawer(page);
      await drawer2.locator('.drawer-tabs button', { hasText: /^用户$/ }).click();
      const anchor2 = drawer2.locator(ANCHOR);
      await expect(anchor2.locator('.group-head[data-table="drawerStubV0"]'),
        '刷新后模板选择回放: 桥自动恢复').toBeVisible({ timeout: 10_000 });
      await expect(anchor2.locator('.group-head .h-cell'), '刷新后隐藏偏好回放(4 列)').toHaveCount(4);
    });

    test(`路径B 页签切换: peers→trackers→peers 桥重挂进当前锚 @fast (${skin})`, async ({ page }) => {
      collectRuntimeErrors(page);
      await page.setViewportSize(WIDE);
      await page.goto(`${BASE_URL}/${skin}/?dtstub=1`, { waitUntil: 'domcontentloaded' });
      await expect(page.locator('#app')).not.toHaveAttribute('v-cloak', { timeout: 15_000 });
      await expect(page.locator('.group-row').first()).toBeVisible({ timeout: 30_000 });
      const drawer = await openTorrentDrawer(page);
      const anchor = await selectStub(page, drawer);
      await expect(anchor.locator('.group-head[data-table="drawerStubV0"]')).toBeVisible();

      // 切走: peers 宿主卸载(锚清代数) → trackers 经典
      await drawer.locator('.drawer-tabs button', { hasText: /^Tracker$/ }).click();
      await expect(drawer.locator('.group-row[data-table="drawerTracker"]').first()).toBeVisible({ timeout: 10_000 });
      await expect(drawer.locator(ANCHOR), '切走后锚随宿主卸载').toHaveCount(0);

      // 切回: 桥重挂进新锚(新代数) —— 手势仍通(再点排序)
      await drawer.locator('.drawer-tabs button', { hasText: /^用户$/ }).click();
      const anchor2 = drawer.locator(ANCHOR);
      await expect(anchor2.locator('.group-head[data-table="drawerStubV0"]'), '切回后桥重挂').toBeVisible({ timeout: 10_000 });
      await anchor2.locator('.h-cell.hc-addr').click();
      await expect(anchor2.locator('.h-cell.hc-addr .arrow svg')).toBeVisible({ timeout: 5_000 });
    });

    test(`路径C 软切换换目标: 换种子数据重拉, 桥稳定存活 @fast (${skin})`, async ({ page }) => {
      collectRuntimeErrors(page);
      await page.setViewportSize(WIDE);
      await page.goto(`${BASE_URL}/${skin}/?dtstub=1`, { waitUntil: 'domcontentloaded' });
      await expect(page.locator('#app')).not.toHaveAttribute('v-cloak', { timeout: 15_000 });
      await expect(page.locator('.group-row').first()).toBeVisible({ timeout: 30_000 });
      const drawer = await openTorrentDrawer(page);
      const anchor = await selectStub(page, drawer);
      const headBefore = await anchor.locator('.group-head[data-table="drawerStubV0"]').innerHTML();

      // 换目标: 抽屉开着双击另一行(软切换 —— _loadDrawerTab 重拉四域, _dtNotify 走 skipUnchanged)
      await page.dblclick('.torrent-row >> nth=1', { force: true });
      await expect(drawer).toBeVisible();
      await page.waitForTimeout(800);
      const anchor2 = drawer.locator(ANCHOR);
      await expect(anchor2.locator('.group-head[data-table="drawerStubV0"]'), '软切换后桥稳定存活(不重挂)').toBeVisible({ timeout: 10_000 });
      await expect(anchor2.locator('.group-row[data-table="drawerStubV0"]').first()).toBeVisible();
      // chrome 未重建(skipUnchanged 纪律): 锚内表头 DOM 引用面恒定(innerHTML 稳定)
      const headAfter = await anchor2.locator('.group-head[data-table="drawerStubV0"]').innerHTML();
      expect(headAfter).toBe(headBefore);
    });

    test(`路径D 合并双列: tp 对开启, peers 列选 stub → 桥在合并列锚内点亮 @fast (${skin})`, async ({ page }) => {
      collectRuntimeErrors(page);
      await page.setViewportSize(WIDE);
      await page.goto(`${BASE_URL}/${skin}/?dtstub=1`, { waitUntil: 'domcontentloaded' });
      await expect(page.locator('#app')).not.toHaveAttribute('v-cloak', { timeout: 15_000 });
      await expect(page.locator('.group-row').first()).toBeVisible({ timeout: 30_000 });
      const drawer = await openTorrentDrawer(page);

      // 开 tp 合并对: Tracker 页签右键 → 合并页签
      await drawer.locator('.drawer-tabs button', { hasText: /^Tracker$/ }).click();
      await expect(drawer.locator('.group-row[data-table="drawerTracker"]').first()).toBeVisible({ timeout: 10_000 });
      await drawer.locator('.drawer-body').click({ button: 'right' });
      await page.locator('.ctx-menu').locator('.ctx-item:has-text("合并页签")').click();
      const split = drawer.locator('.drawer-split');
      await expect(split).toHaveAttribute('data-merge', 'tp', { timeout: 5_000 });

      // peers 列选 stub → 合并列内桥点亮 + 手势通(排序点击)
      const peersCol = split.locator('.dt-col[data-dt-tab="peers"]');
      await peersCol.click({ button: 'right' });
      await page.locator('.ctx-menu').locator(STUB_ITEM).click();
      const anchor = peersCol.locator(ANCHOR);
      await expect(anchor.locator('.group-head[data-table="drawerStubV0"]'), '合并列桥点亮').toBeVisible({ timeout: 10_000 });
      await expect(anchor.locator('.group-row[data-table="drawerStubV0"]').first()).toBeVisible();
      await anchor.locator('.h-cell.hc-addr').click();
      await expect(anchor.locator('.h-cell.hc-addr .arrow svg'), '合并列桥内引擎手势通').toBeVisible({ timeout: 5_000 });
    });
  });
}
