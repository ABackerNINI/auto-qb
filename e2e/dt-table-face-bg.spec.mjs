/* W6 症状1 验收量具(计划 26-10-13-0811 §08 #1 后半): 表头背景与面板底一致。
 * 用户量化口径: 表头带 rgb(253,254,255)(--bg-card)≠ 面板底 rgb(242,246,251)(--bg)。
 * 修复口径(W6 单点): 抽屉表格面(06/07/09/11)的表头与行板背景族单点到 shared/dt_table.css,
 *   默认 var(--bg) —— 与主列表吸顶列头的「页面面板」语义同源(prism views.css:213 既有注释:
 *   改用不透明页底色读作「页面面板」), 表内(表头/行板)零色缝。
 * 断言:
 *   A. 表头计算背景 == 页面底(--bg): 用户量化的「面板底」口径;
 *   B. 表头计算背景 == 行板计算背景(行板经共享层也落 --bg): 表内无缝;
 *   C. --bg-card 不再出现在四个表格面的表头声明里(静态层另守, 此处运行时复核)。
 * 四面 × 双皮肤全量; 数据口径沿用 dt-live-update / variant-tables 家族桩。 */
import { expect, test } from '@playwright/test';
import { collectRuntimeErrors, installRuntimeErrorGuard } from './lib/errors.mjs';
import { BASE_URL, SKINS } from './harness.mjs';

const WIDE = { width: 2560, height: 1200 };

function makePeers() {
  const out = [];
  for (let i = 0; i < 12; i++) {
    out.push({
      ip: `${10 + (i % 200)}.${(i * 7) % 256}.${(i * 13) % 256}.${(i * 29) % 256}`,
      port: 30000 + i,
      client: `qBittorrent 5.${i % 5}.${i % 3}`,
      flags: 'D', progress: 0.5, dl_speed: 125000, up_speed: 250000,
      relevance: 0.6, country_code: 'CN', connection: 'UV',
    });
  }
  return out;
}

function makeFiles() {
  return [
    { name: 'E01.mkv', size: 1_000_000, progress: 1, priority: 1, availability: 1.5 },
    { name: 'E02.mkv', size: 2_000_000, progress: 0.5, priority: 6, availability: 0.4 },
  ];
}

/** 合成 tracker 列表(字段与 qB getTrackers 同名, 口径同 drawer-trackers-variant-tables)。 */
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
    t('https://tracker-c.example.org/announce.php', 4, 0, { msg: 'torrent not registered' }),
    t('https://tracker-d.example.org/announce.php', 1, 2, { msg: 'Connection timed out' }),
    t('https://tracker-e.example.org/announce.php', 3, 0, { msg: 'Working' }),
    t('https://tracker-f.example.org/announce.php', 0, 3),
    t('[DHT]', 0, 0),
    t('[PeX]', 0, 0),
  ];
}

/* 面 → (页签文案, 锚 id, 列表容器选择器) */
const FACES = {
  '06': { tab: 'Tracker', anchor: 'drawerTrackerV06', list: '.dt06-list', tpl: { trackers: '06' } },
  '07': { tab: '用户', anchor: 'drawerPeerV07', list: '.dt07-list', tpl: { peers: '07' } },
  '09': { tab: '用户', anchor: 'drawerPeerV09', list: '.dt09-list', tpl: { peers: '09' } },
  '11': { tab: '内容', anchor: 'drawerContentV11', list: '.dt11-list', tpl: { content: '11' } },
};

async function openFace(page, drawer, faceId) {
  const def = FACES[faceId];
  await drawer.locator('.drawer-tabs button', { hasText: def.tab }).first().click();
  const anchor = drawer.locator(`[data-dt-table-anchor="${def.anchor}"]`);
  await expect(anchor.locator('.group-head').first()).toBeVisible({ timeout: 10_000 });
  return def;
}

for (const skin of SKINS) {
  test.describe(`W6 表格面背景族 ${skin}`, () => {
    installRuntimeErrorGuard(test);

    for (const faceId of Object.keys(FACES)) {
      test(`面 ${faceId}: 表头/行板背景 == 页面底(--bg), 表内无缝 @fast (${skin})`, async ({ page }) => {
        collectRuntimeErrors(page);
        await page.setViewportSize(WIDE);
        await page.route('**/api/torrents/*/peers', (route) =>
          route.fulfill({ contentType: 'application/json', body: JSON.stringify({ peers: makePeers() }) }));
        await page.route('**/api/torrents/*/files', (route) =>
          route.fulfill({ contentType: 'application/json', body: JSON.stringify(makeFiles()) }));
        await page.route('**/api/torrents/*/trackers', (route) =>
          route.fulfill({ contentType: 'application/json', body: JSON.stringify(makeTrackers()) }));
        await page.addInitScript((tpl) =>
          localStorage.setItem('autoqb.ui.drawerTpl', JSON.stringify(tpl)), FACES[faceId].tpl);
        await page.goto(`${BASE_URL}/${skin}/`, { waitUntil: 'domcontentloaded' });
        await expect(page.locator('#app')).not.toHaveAttribute('v-cloak', { timeout: 15_000 });
        await expect(page.locator('.group-row').first()).toBeVisible({ timeout: 30_000 });

        await page.click('nav.tabs [data-view="torrents"]');
        await expect(page.locator('.torrent-row').first()).toBeVisible({ timeout: 15_000 });
        await page.dblclick('.torrent-row >> nth=0', { force: true });
        const drawer = page.locator('.drawer-dock > .drawer');
        await expect(drawer).toBeVisible({ timeout: 5_000 });

        const def = await openFace(page, drawer, faceId);

        const colors = await page.evaluate((listSel) => {
          const bg = (el) => el && getComputedStyle(el).backgroundColor;
          const head = document.querySelector(`${listSel} .group-head`);
          /* 取无状态修饰的普通行(err/bad/warn/off/is-chk 等状态底是变体个性, 不在族断言内) */
          const row = document.querySelector(
            `${listSel} .group-row:not(.err):not(.bad):not(.warn):not(.off):not(.is-chk):not(.empty-row)`);
          return { head: bg(head), row: bg(row), body: bg(document.body) };
        }, def.list);

        expect(colors.head, `面 ${faceId} 表头背景 == 页面底(--bg, 用户量化口径 242,246,251)`)
          .toBe(colors.body);
        expect(colors.row, `面 ${faceId} 行板背景 == 表头背景(表内无缝)`)
          .toBe(colors.head);
      });
    }
  });
}
