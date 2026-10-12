// @ts-check
import { expect, test } from '@playwright/test';
import { BASE_URL, SKINS } from './harness.mjs';
import { collectRuntimeErrors, installRuntimeErrorGuard } from './lib/errors.mjs';

/**
 * U3 Tracker 三变体(04 状态卡片栅格 / 05 健康分组 / 06 增强表格) 表格体接引擎后的表面手势守阵
 * (计划 26-10-12-0527 U3 验收面: 同 U2 口径, e2e 手势红绿双验) ——
 *
 * U3 起三变体的表格体不再是手搓 DOM: 变体外壳只留版式(计数胶囊/分段排序钮/分组头/工具条),
 * 行体由 <aq-dt-bridge> 按 DRAWER_TABLE_DEFS 描述符 Teleport 进变体锚(data-dt-table-anchor=
 * drawerTrackerV0X)。04 = 卡片行 + 分段钮经 dtSortSet 直设引擎 dyn 键(模式选择语义) +
 * 引擎响应式重排(无列头, 拖宽/右键隐藏不适用 —— Q3 记档); 05 = 分段桥五组(组头/折叠留外壳,
 * 无排序 dyn 空键); 06 = 8 列引擎表头(拖宽/右键隐藏/偏好持久化首次落地, 默认 sev 升序 =
 * 原口径「异常置顶」)。
 *
 * 手势清单(每条都是真手势, 不借道 vm):
 *   04: 分段排序并引擎(默认异常优先 → 按 tier, 次序真变) + 筛选 pills(anchTouch 桥换代,
 *       行子集真刷新; 轮询冻结手法排除 5s tick 假绿) + 虚拟合并卡(rowsFn 合成行);
 *   05: 分段锚五组 + 组内序(ok 组 tier 升序) + 折叠(class 翻转, 锚元素集合不变) + msg 展开;
 *   06: 引擎排序三态(默认异常置顶 → tier 降/升 → 回默认) + 拖宽落盘 + 右键隐藏落盘
 *       + 刷新偏好回放 + 仅看异常(容器类切换, benign 行隐藏) + msg 展开。
 *
 * 数据口径: page.route 桩掉 /api/torrents/{hash}/trackers, 8 条覆盖全桶 ——
 *   ok×2(tier 0/1, 供组内 tier 升序断言) / err×1(status 4) / warn×1(status 1) /
 *   upd×1(status 3) / off 实体×1(status 0) / 虚拟×2([DHT]/[PeX], drawerTrackerVirtual 判据)。
 * 手法同族: drawer-peers-variant-tables.spec(冻结轮询/拖宽/右键/偏好回放全套)。
 */

const WIDE = { width: 2560, height: 1200 };

/** 合成 tracker 列表(覆盖 04/05/06 的全部分桶; 字段与 qB 5.2.3 getTrackers 同名)。 */
function makeTrackers() {
  const now = Math.floor(Date.now() / 1000);
  const t = (url, status, tier, extra = {}) => ({
    url, status, tier,
    num_peers: 4, num_seeds: 10, num_complete: 12, num_leeches: 2, num_incomplete: 3,
    num_downloaded: 50, msg: '', next_announce: now + 1800, min_announce: now + 1800,
    ...extra,
  });
  return [
    t('https://tracker-a.example.org/announce.php', 2, 0),
    t('https://tracker-b.example.org/announce.php', 2, 1),
    t('https://tracker-c.example.org/announce.php', 4, 0, { msg: 'torrent not registered with this tracker' }),
    t('https://tracker-d.example.org/announce.php', 1, 2, { msg: 'Connection timed out' }),
    t('https://tracker-e.example.org/announce.php', 3, 0, { msg: 'Working' }),
    t('https://tracker-f.example.org/announce.php', 0, 3),
    t('[DHT]', 0, 0),
    t('[PeX]', 0, 0),
  ];
}

/** host 展示(变体 hostOf: 去 scheme 只留 host) */
const hostOf = (u) => new URL(u).host;

async function openTorrentDrawer(page) {
  await page.click('nav.tabs [data-view="torrents"]');
  await expect(page.locator('.torrent-row').first()).toBeVisible({ timeout: 15_000 });
  await page.dblclick('.torrent-row >> nth=0', { force: true });
  const drawer = page.locator('.drawer-dock > .drawer');
  await expect(drawer).toBeVisible({ timeout: 5_000 });
  return drawer;
}

/** 开抽屉 → Tracker 页签 → 等变体外壳与引擎行体点亮; 返回 drawer */
async function openTrackersVariant(page, variantId) {
  const drawer = await openTorrentDrawer(page);
  await drawer.locator('.drawer-tabs button', { hasText: 'Tracker' }).click();
  await expect(drawer.locator(`.dt${variantId}-wrap`)).toBeVisible({ timeout: 10_000 });
  const anchor = drawer.locator(`[data-dt-table-anchor="drawerTrackerV${variantId}"]`);
  await expect(anchor.locator(`.group-row[data-table="drawerTrackerV${variantId}"]`).first(),
    '变体桥行体点亮(U3: 表格体归引擎)').toBeVisible({ timeout: 10_000 });
  return drawer;
}

for (const skin of SKINS) {
  test.describe(`Tracker 三变体手势 ${skin}`, () => {
    installRuntimeErrorGuard(test);

    test(`dt04 卡片: 分段钮排序并引擎(dtSortSet 直设) + 筛选 pills anchTouch + 虚拟合并卡 @fast (${skin})`, async ({ page }) => {
      collectRuntimeErrors(page);
      await page.setViewportSize(WIDE);
      await page.route('**/api/torrents/*/trackers', (route) =>
        route.fulfill({ contentType: 'application/json', body: JSON.stringify(makeTrackers()) }));
      await page.addInitScript(() =>
        localStorage.setItem('autoqb.ui.drawerTpl', JSON.stringify({ trackers: '04' })));
      await page.goto(`${BASE_URL}/${skin}/`, { waitUntil: 'domcontentloaded' });
      await expect(page.locator('#app')).not.toHaveAttribute('v-cloak', { timeout: 15_000 });
      await expect(page.locator('.group-row').first()).toBeVisible({ timeout: 30_000 });
      const drawer = await openTrackersVariant(page, '04');
      const anchor = drawer.locator('[data-dt-table-anchor="drawerTrackerV04"]');
      const cards = anchor.locator('.group-row[data-table="drawerTrackerV04"]');

      // 卡片无列语义: 引擎列头隐藏(D5), 行体 = 6 实体卡 + 1 虚拟合并卡
      await expect(anchor.locator('.group-head[data-table="drawerTrackerV04"]'), '列头隐藏(卡片无列语义)').toBeHidden();
      await expect(cards).toHaveCount(7);

      // 默认序 = sev 升序(异常优先): 首卡 = 失败(tracker-c), 虚拟合并卡殿后(st-off + chips)
      await expect(cards.first(), '默认异常优先: 失败卡置顶').toHaveClass(/st-err/);
      await expect(cards.first()).toContainText(hostOf('https://tracker-c.example.org/announce.php'));
      const vcard = anchor.locator('.group-row:has(.dt04-vchip)');
      await expect(vcard, '虚拟合并卡 = rowsFn 合成行').toHaveCount(1);
      await expect(vcard).toContainText('虚拟条目 ×2');
      await expect(vcard.locator('.dt04-vchip')).toHaveCount(2);

      // 分段钮排序并引擎(U3/R7): 「按 tier」单击 → dtSortSet 直设 dyn 键, 引擎响应式重排
      // sev 序次卡 = warn(tier2); tier 序次卡 = upd(tier0, tier*10+sev=2) —— 次序真变可断言
      await expect(drawer.locator('.dt04-seg[data-sort="sev"]'), '默认激活「异常优先」').toHaveClass(/active/);
      await drawer.locator('.dt04-seg[data-sort="tier"]').click();
      await expect(drawer.locator('.dt04-seg[data-sort="tier"]'), '激活态随引擎排序态输出').toHaveClass(/active/);
      await expect(cards.nth(1), 'tier 模式次卡 = 更新中(tier0/sev2 权值 2 < warn 的 21)').toContainText(
        hostOf('https://tracker-e.example.org/announce.php'));
      await expect(drawer.locator('.dt04-seg[data-sort="sev"]')).not.toHaveClass(/active/);

      // 冻结轮询(初始数据已落袋): 后注册路由优先, 后续 trackers 请求全部挂起
      await page.route('**/api/torrents/*/trackers', (route) => { /* hang: 不 fulfill */ });

      // 筛选 pills(版式语义): anchTouch 桥换代重读 rowsFn, 行子集真刷新
      await drawer.locator('.dt04-pill[data-f="err"]').click();
      await expect(drawer.locator('.dt04-pill[data-f="err"]'), '激活态随筛选输出').toHaveClass(/active/);
      await expect(cards, 'anchTouch 换代重读 rowsFn: 只剩失败卡(虚拟卡不进 err 筛选)').toHaveCount(1);
      await drawer.locator('.dt04-pill[data-f="off"]').click();
      await expect(cards, '禁用筛选 = 实体禁用卡 + 虚拟合并卡').toHaveCount(2);
      await drawer.locator('.dt04-pill[data-f="all"]').click();
      await expect(cards, '回全部 = 6 实体 + 1 虚拟').toHaveCount(7);
    });

    test(`dt05 分组: 分段锚五组 + ok 组 tier 升序 + 折叠/展开 + msg 展开 @fast (${skin})`, async ({ page }) => {
      collectRuntimeErrors(page);
      await page.setViewportSize(WIDE);
      await page.route('**/api/torrents/*/trackers', (route) =>
        route.fulfill({ contentType: 'application/json', body: JSON.stringify(makeTrackers()) }));
      await page.addInitScript(() =>
        localStorage.setItem('autoqb.ui.drawerTpl', JSON.stringify({ trackers: '05' })));
      await page.goto(`${BASE_URL}/${skin}/`, { waitUntil: 'domcontentloaded' });
      await expect(page.locator('#app')).not.toHaveAttribute('v-cloak', { timeout: 15_000 });
      await expect(page.locator('.group-row').first()).toBeVisible({ timeout: 30_000 });
      const drawer = await openTrackersVariant(page, '05');

      // 五组锚(组头/折叠在外壳 —— 分组是版式; 空组整节缺席, 本数据五组全非空)
      await expect(drawer.locator('.dt05-group')).toHaveCount(5);
      for (const key of ['err', 'warn', 'upd', 'ok', 'off']) {
        await expect(drawer.locator(`[data-grp="${key}"] [data-dt-table-anchor="drawerTrackerV05"]`),
          `组 ${key} 锚在座`).toHaveCount(1);
      }

      // err 组 = 处置块行(msg 全文 + 处置建议); ok 组 = tier 升序(a T0 在 b T1 前)
      const errSec = drawer.locator('[data-grp="err"]');
      await expect(errSec.locator('.dt05-fail'), '失败组走处置块形态').toHaveCount(1);
      await expect(errSec.locator('.dt05-hint')).toContainText('处置建议');
      const okSec = drawer.locator('[data-grp="ok"]');
      await expect(okSec.locator('.group-row[data-table="drawerTrackerV05"]').first())
        .toContainText(hostOf('https://tracker-a.example.org/announce.php'));
      // off 组 = chips 合成行(2 虚拟) + 实体禁用行
      const offSec = drawer.locator('[data-grp="off"]');
      await expect(offSec.locator('.dt05-vchip')).toHaveCount(2);
      await expect(offSec.locator('.group-row[data-table="drawerTrackerV05"]'), 'chips 行 + 禁用实体行').toHaveCount(2);

      // 折叠手势: class 翻转不重挂(锚元素集合不变), 再点展开
      const warnSec = drawer.locator('[data-grp="warn"]');
      await warnSec.locator('.dt05-ghead').click();
      await expect(warnSec, '折叠态输出').toHaveClass(/folded/);
      await expect(warnSec.locator('[data-dt-table-anchor="drawerTrackerV05"]'),
        '锚元素仍在 DOM(display:none, 元素集合不变 → 桥零重挂)').toHaveCount(1);
      await warnSec.locator('.dt05-ghead').click();
      await expect(warnSec).not.toHaveClass(/folded/);

      // msg 展开行(分片内纯 span 模拟控件): 点击翻 open, 再点收起
      const sub = warnSec.locator('.dt05-sub');
      await sub.click();
      await expect(sub, 'msg 展开态').toHaveClass(/open/);
      await sub.click();
      await expect(sub).not.toHaveClass(/open/);
    });

    test(`dt06 增强表格: 引擎排序三态/拖宽/右键隐藏(偏好按 table-id 落盘+回放)/仅看异常/msg @fast (${skin})`, async ({ page }) => {
      collectRuntimeErrors(page);
      await page.setViewportSize(WIDE);
      await page.route('**/api/torrents/*/trackers', (route) =>
        route.fulfill({ contentType: 'application/json', body: JSON.stringify(makeTrackers()) }));
      await page.addInitScript(() =>
        localStorage.setItem('autoqb.ui.drawerTpl', JSON.stringify({ trackers: '06' })));
      await page.goto(`${BASE_URL}/${skin}/`, { waitUntil: 'domcontentloaded' });
      await expect(page.locator('#app')).not.toHaveAttribute('v-cloak', { timeout: 15_000 });
      await expect(page.locator('.group-row').first()).toBeVisible({ timeout: 30_000 });
      const drawer = await openTrackersVariant(page, '06');
      const anchor = drawer.locator('[data-dt-table-anchor="drawerTrackerV06"]');
      const rows = anchor.locator('.group-row[data-table="drawerTrackerV06"]');

      // 8 列引擎表头(U3: 拖宽/右键隐藏/偏好持久化首次落地) + 默认序 sev 升序(异常置顶)
      await expect(anchor.locator('.group-head .h-cell')).toHaveCount(8);
      await expect(rows).toHaveCount(8);
      await expect(rows.first(), '默认异常置顶: 失败行居首').toHaveClass(/err/);

      // 引擎排序三态: tier 列第一击降序 → 首行 tier3(tracker-f); 第二击升序 → 首行回到 tier0;
      // 第三击回默认(sev 升序) → 失败行居首
      await anchor.locator('.h-cell.hc-tier').click();
      await expect(anchor.locator('.h-cell.hc-tier .arrow svg'), '引擎排序箭头点亮').toBeVisible({ timeout: 5_000 });
      await expect(rows.first(), 'tier 降序: tier3 居首').toContainText(hostOf('https://tracker-f.example.org/announce.php'));
      await anchor.locator('.h-cell.hc-tier').click();
      await expect(rows.first(), 'tier 升序: tier0 居首(稳定序取 qB 原序首 tracker-a)').toContainText(
        hostOf('https://tracker-a.example.org/announce.php'));
      await anchor.locator('.h-cell.hc-tier').click();
      await expect(anchor.locator('.h-cell.hc-tier .arrow svg'), '第三击回默认: 箭头熄灭').toHaveCount(0);
      await expect(rows.first()).toHaveClass(/err/);

      // 仅看异常: 容器类切换(benign 行 display:none, 行不重装配 —— 原口径), msg 展开仍可手势
      // (须在右键隐藏 Tracker 列之前 —— msg 展开格住在 Tracker 列内, 隐藏列即随行消失)
      await drawer.locator('.dt06-toggle').click();
      await expect(drawer.locator('.dt06-list'), '容器类切换').toHaveClass(/only-bad/);
      await expect(drawer.locator('.group-row.benign').first(), '正常/未启用行隐藏').toBeHidden();
      await expect(drawer.locator('.group-row.err'), '异常行保留').toBeVisible();
      const msg = drawer.locator('.group-row.err .dt06-msg');
      await msg.click();
      await expect(msg, 'msg 展开态').toHaveClass(/open/);
      await drawer.locator('.dt06-toggle').click();
      await expect(drawer.locator('.group-row.benign').first()).toBeVisible();

      // 拖宽: Tracker 列 resizer 右拖 60px → 按 table-id 落盘(autoqb_cols_v5)
      const resizer = anchor.locator('.h-cell.hc-host .resizer');
      const rb = await resizer.boundingBox();
      await page.mouse.move(rb.x + rb.width / 2, rb.y + rb.height / 2);
      await page.mouse.down();
      await page.mouse.move(rb.x + rb.width / 2 + 60, rb.y + rb.height / 2, { steps: 6 });
      await page.mouse.up();
      const cols = JSON.parse(await page.evaluate(() => localStorage.getItem('autoqb_cols_v5') || '{}'));
      expect(cols?.pages?.drawerTrackerV06?.w?.host, '拖宽必须按 table-id 持久化(引擎同一漏斗)').toBeTruthy();

      // 右键隐藏: Tracker 列头右键 → 隐藏「Tracker」 → 8→7 列 + 落盘
      await anchor.locator('.h-cell.hc-host').click({ button: 'right' });
      await page.locator('.ctx-menu').locator('.ctx-item', { hasText: '隐藏「Tracker」' }).click();
      await expect(anchor.locator('.group-head .h-cell'), '右键隐藏即时生效').toHaveCount(7);
      const cols2 = JSON.parse(await page.evaluate(() => localStorage.getItem('autoqb_cols_v5') || '{}'));
      expect(cols2?.pages?.drawerTrackerV06?.hidden, '隐藏必须按 table-id 持久化').toContain('host');

      // 刷新偏好回放: 模板 + 列偏好都持久化
      await page.reload({ waitUntil: 'domcontentloaded' });
      await expect(page.locator('#app')).not.toHaveAttribute('v-cloak', { timeout: 15_000 });
      await expect(page.locator('.group-row').first()).toBeVisible({ timeout: 30_000 });
      const drawer2 = await openTrackersVariant(page, '06');
      const anchor2 = drawer2.locator('[data-dt-table-anchor="drawerTrackerV06"]');
      await expect(anchor2.locator('.group-head .h-cell'), '刷新后隐藏偏好回放(7 列)').toHaveCount(7);
    });
  });
}
