/* W6 症状1 验收量具(计划 26-10-13-0811 §08 #1 后半): 表头背景与面板底一致。
 * 用户量化口径: 表头带 rgb(253,254,255)(--bg-card)≠ 面板底 rgb(242,246,251)(--bg)。
 * 修复口径(W6 单点): 抽屉表格面(06/07/09/11)的表头与行板背景族单点到 shared/dt_table.css,
 *   默认 var(--bg) —— 与主列表吸顶列头的「页面面板」语义同源(prism views.css:213 既有注释:
 *   改用不透明页底色读作「页面面板」), 表内(表头/行板)零色缝。
 * 断言:
 *   A. 表头计算背景 == 页面底(--bg): 用户量化的「面板底」口径;
 *   B. 表头计算背景 == 行板计算背景(行板经共享层也落 --bg): 表内无缝;
 *   C. --bg-card 不再出现在四个表格面的表头声明里(静态层另守, 此处运行时复核)。
 *
 * 2026-10-14 增补「必现列(吸左首格)底色」量具(修用户报「必现列背景与其他列不一致」,
 * 报障面 = 主表三页 + 抽屉全部变体表格):
 *   D. 八面(04/05/06/07/08/09/10/11)首格**可见底色** == 行板可见底色 —— 可见底色 =
 *      自元素向上收集半透明层(backgroundColor + 纯色双 stop 渐变)遇首个不透明层止,
 *      逐层 alpha 合成(行板半透明 tint over 抽屉卡底 与 首格渐变 tint over --bg-card
 *      须落到同一 rgb 才算一致, 裸计算样式相等覆盖不到摘底/透明行的面);
 *      悬停态同判(历史上首格无悬停规则, 悬停即现竖带)。
 *   E. 状态行同判: 06 err / 07·09 bad / 11 is-chk / 10 sel(半透明 tint 合成面)。
 *   F. 05 健康分组: 行与首格均摘掉引擎卡底(--bg-row 零残留), 失败行首格保 error 色;
 *   G. 主表 search-hit: 首格必须带同款 90deg accent 渐层(修前 backgroundImage=none,
 *      整条渐层丢失, 追剧表命中行名称列读作异色竖带)。
 * 数据口径沿用 dt-live-update / variant-tables 家族桩(bad 行由 client 名含 XL 合成)。 */
import { expect, test } from '@playwright/test';
import { collectRuntimeErrors, installRuntimeErrorGuard } from './lib/errors.mjs';
import { BASE_URL, SKINS } from './harness.mjs';

const WIDE = { width: 2560, height: 1200 };

function makePeers(withBad = false) {
  const out = [];
  for (let i = 0; i < 12; i++) {
    out.push({
      ip: `${10 + (i % 200)}.${(i * 7) % 256}.${(i * 13) % 256}.${(i * 29) % 256}`,
      port: 30000 + i,
      /* 吸血嫌疑启发式(与 07/08/09 变体同判据): client 含独立 XL/迅雷 ⇒ .bad 行。
       * 注意 "XL" 后必须跟非字母(正则 (^|[^A-Za-z])XL([^A-Za-z]|$)) —— "XLPlayer" 不命中 */
      client: withBad && i % 4 === 0 ? 'XL 2.0' : `qBittorrent 5.${i % 5}.${i % 3}`,
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

/* 面 → (页签文案, 锚 id, 列表容器选择器, 变体选择, 状态行探测量) */
const FACES = {
  '04': { tab: 'Tracker', anchor: 'drawerTrackerV04', list: '.dt04-list', tpl: { trackers: '04' }, head: false },
  /* 05: 行只有单内容根(.dt05-rowin/.dt05-fail/.dt05-offline), 悬停带画在内容根上而非行板
   * ⇒ 悬停态不适用「首格可见底 == 行板可见底」 equality, 由专用用例断(见 hoverBand) */
  '05': { tab: 'Tracker', anchor: 'drawerTrackerV05', list: '.dt05-list', tpl: { trackers: '05' }, head: false, hoverBand: true },
  '06': { tab: 'Tracker', anchor: 'drawerTrackerV06', list: '.dt06-list', tpl: { trackers: '06' } },
  '07': { tab: '用户', anchor: 'drawerPeerV07', list: '.dt07-list', tpl: { peers: '07' } },
  '08': { tab: '用户', anchor: 'drawerPeerV08', list: '.dt08-rows', tpl: { peers: '08' } },
  '09': { tab: '用户', anchor: 'drawerPeerV09', list: '.dt09-list', tpl: { peers: '09' } },
  '10': { tab: '内容', anchor: 'drawerContentV10', list: '.dt10-list', tpl: { content: '10' } },
  '11': { tab: '内容', anchor: 'drawerContentV11', list: '.dt11-list', tpl: { content: '11' } },
};

/* 无状态修饰的普通行选择器(排除各面状态行/空行/占位行; 05 的 failrow/chipsrow 亦排除) */
const PLAIN_ROW =
  '.group-row:not(.err):not(.bad):not(.warn):not(.off):not(.is-chk):not(.empty-row)' +
  ':not(.failrow):not(.chipsrow):not(.st-err):not(.st-off):not(.sel)';

async function openFace(page, drawer, faceId) {
  const def = FACES[faceId];
  await drawer.locator('.drawer-tabs button', { hasText: def.tab }).first().click();
  const anchor = drawer.locator(`[data-dt-table-anchor="${def.anchor}"]`).first();
  await expect(anchor.locator('.group-row').first()).toBeVisible({ timeout: 10_000 });
  return def;
}

/* 首格 vs 行板的可见底色探针(页内执行, 自包含)。
 * visible(): 自 el 向上逐层收集半透明层(backgroundColor + 纯色双 stop 渐变),
 * 遇首个不透明层止, 自底向上 alpha 合成 —— 半透明 tint 行(06 err / 07·09 bad /
 * 11 is-chk / 10 sel 的 --error-soft/--sel-bg over 抽屉卡底)与首格的
 * 「linear-gradient(tint,tint) over --bg-card」须落到同一 rgb。 */
async function probeFirstVsRow(page, listSel, rowSel) {
  return page.evaluate(
    ({ listSel, rowSel }) => {
      const parseColor = (s) => {
        const m = /rgba?\(([^)]+)\)/.exec(s || '');
        if (!m) return null;
        const p = m[1].split(',').map((v) => parseFloat(v));
        return [p[0], p[1], p[2], p.length > 3 ? p[3] : 1];
      };
      const over = (t, b) => {
        const a = t[3] + b[3] * (1 - t[3]);
        if (!a) return [0, 0, 0, 0];
        return [
          (t[0] * t[3] + b[0] * b[3] * (1 - t[3])) / a,
          (t[1] * t[3] + b[1] * b[3] * (1 - t[3])) / a,
          (t[2] * t[3] + b[2] * b[3] * (1 - t[3])) / a,
          a,
        ];
      };
      /* 纯色双 stop 渐变(linear-gradient(tint, tint))取末个色 stop 作为一层;
       * 方向渐层(末 stop 为 transparent)不取 —— 空间衰减, 不参与整格比色。 */
      const gradLayer = (img) => {
        if (!img || img === 'none' || !img.startsWith('linear-gradient')) return null;
        const stops = img.match(/rgba?\([^)]*\)/g);
        if (!stops || stops.length < 2) return null;
        const c = parseColor(stops[stops.length - 1]);
        return c && c[3] > 0 && c[3] < 1 ? c : null;
      };
      const visible = (el) => {
        const layers = [];
        let node = el;
        while (node && node !== document.documentElement) {
          const cs = getComputedStyle(node);
          const g = gradLayer(cs.backgroundImage);
          if (g) layers.push(g);
          const c = parseColor(cs.backgroundColor);
          if (c && c[3] > 0) {
            layers.push(c);
            if (c[3] >= 1) break;
          }
          node = node.parentElement;
        }
        if (!layers.length) return 'rgba(0, 0, 0, 0)';
        let acc = layers[layers.length - 1];
        for (let i = layers.length - 2; i >= 0; i--) acc = over(layers[i], acc);
        return `rgb(${Math.round(acc[0])}, ${Math.round(acc[1])}, ${Math.round(acc[2])})`;
      };
      const list = document.querySelector(listSel);
      if (!list) return { error: 'no list ' + listSel };
      const row = list.querySelector(rowSel);
      if (!row) return { error: 'no row ' + rowSel };
      const first = row.firstElementChild;
      if (!first) return { error: 'no first cell' };
      const fcs = getComputedStyle(first);
      return {
        rowCls: String(row.className).slice(0, 60),
        firstCls: String(first.className).slice(0, 40),
        rowVisible: visible(row),
        firstVisible: visible(first),
        firstBg: fcs.backgroundColor,
        firstImg: fcs.backgroundImage === 'none' ? 'none' : 'gradient',
        rowBg: getComputedStyle(row).backgroundColor,
      };
    },
    { listSel, rowSel },
  );
}

for (const skin of SKINS) {
  test.describe(`W6 表格面背景族 ${skin}`, () => {
    installRuntimeErrorGuard(test);

    for (const faceId of ['06', '07', '09', '11']) {
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
          const row = document.querySelector(`${listSel} .group-row:not(.err):not(.bad):not(.warn):not(.off):not(.is-chk):not(.empty-row)`);
          return {
            head: bg(head),
            row: bg(row),
            body: bg(document.body),
            headShadow: head && getComputedStyle(head).boxShadow,
          };
        }, def.list);

        expect(colors.head, `面 ${faceId} 表头背景 == 页面底(--bg, 用户量化口径 242,246,251)`)
          .toBe(colors.body);
        expect(colors.row, `面 ${faceId} 行板背景 == 表头背景(表内无缝)`)
          .toBe(colors.head);
        expect(colors.headShadow, `面 ${faceId} 表头零落影(症状2: skin 吸顶列头的 --shadow-1 在抽屉里 = 速度列下方异常横条)`)
          .toBe('none');
      });
    }
  });
}

/* ------------------------------------------------------------------ *
 * 必现列(吸左首格)底色按面重锚(2026-10-14 修「必现列背景与其他列不一致」) *
 * ------------------------------------------------------------------ */
for (const skin of SKINS) {
  test.describe(`必现列底色按面 ${skin}`, () => {
    installRuntimeErrorGuard(test);

    /* 每面一套: 开抽屉 → 页签 → 变体(桩 peers 带 XL 客户端供 07/08/09 的 bad 行) */
    async function openDrawerFace(page, faceId) {
      await page.setViewportSize(WIDE);
      await page.route('**/api/torrents/*/peers', (route) =>
        route.fulfill({ contentType: 'application/json', body: JSON.stringify({ peers: makePeers(true) }) }));
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
      return openFace(page, drawer, faceId);
    }

    for (const faceId of Object.keys(FACES)) {
      test(`面 ${faceId}: 首格可见底色 == 行板(常态 + 悬停) @fast (${skin})`, async ({ page }) => {
        collectRuntimeErrors(page);
        const def = await openDrawerFace(page, faceId);

        const base = await probeFirstVsRow(page, def.list, PLAIN_ROW);
        expect(base.error, `面 ${faceId} 常态行探针`).toBeUndefined();
        expect(base.firstVisible, `面 ${faceId} 常态: 首格(${base.firstCls})可见底 != 行板(${base.rowCls})`
          + ` —— 首格 ${base.firstVisible}(bg=${base.firstBg}${base.firstImg === 'gradient' ? '+渐变' : ''})`
          + ` vs 行板 ${base.rowVisible}(bg=${base.rowBg})`)
          .toBe(base.rowVisible);

        /* 悬停: 首格须随行板同色(修前首格无悬停规则, 悬停即现竖带)。
         * 05 例外(单内容根架构): 悬停带画在内容根 .dt05-rowin 上, 行板恒透明 ——
         * 由专用用例断「带宽在、行仍摘底」, 不走 equality。 */
        if (!def.hoverBand) {
          await page.locator(`${def.list} ${PLAIN_ROW}`).first().hover();
          await page.waitForTimeout(150);
          const hov = await probeFirstVsRow(page, def.list, PLAIN_ROW);
          expect(hov.error, `面 ${faceId} 悬停行探针`).toBeUndefined();
          expect(hov.firstVisible, `面 ${faceId} 悬停: 首格可见底 != 行板`
            + ` —— 首格 ${hov.firstVisible} vs 行板 ${hov.rowVisible}`)
            .toBe(hov.rowVisible);
        }
      });
    }

    /* 状态行: 半透明 tint 行(06 err / 07·09 bad / 11 is-chk / 10 sel)首格须同色合成。
     * ⚠ 交互后必须等过渡走完再量底 —— .group-row 有 transition: background,
     * 类刚翻转时 getComputedStyle 拿到的是**旧值/中间值**(坑档 frozen-column.md 量测陷阱:
     * 实测点完勾选立刻读, 行底还是 base --bg 而首格渐变已 snap, 误报「不一致」)。 */
    const STATE_CASES = {
      '06': { sel: '.group-row.err', prep: null },
      '07': { sel: '.group-row.bad', prep: null },
      '09': { sel: '.group-row.bad', prep: null },
      '11': { sel: '.group-row.is-chk', prep: 'check' },
      '10': { sel: '.group-row.sel', prep: 'select' },
    };
    for (const [faceId, cs] of Object.entries(STATE_CASES)) {
      test(`面 ${faceId}: 状态行(${cs.sel.replace('.group-row.', '')})首格可见底色 == 行板 @fast (${skin})`, async ({ page }) => {
        collectRuntimeErrors(page);
        const def = await openDrawerFace(page, faceId);
        const rowLoc = page.locator(`${def.list} ${cs.sel}`).first();
        if (cs.prep === 'check') {
          /* 11: 点名字格首的勾选框 ⇒ 行落 is-chk */
          await page.locator(`${def.list} .dt11-ck`).first().click();
        } else if (cs.prep === 'select') {
          /* 10: 点行 ⇒ 行落 sel */
          await page.locator(`${def.list} .group-row`).first().click();
        }
        await expect(rowLoc, `面 ${faceId} 状态行 ${cs.sel} 未出现(桩数据/交互未触发?)`).toHaveCount(1, { timeout: 5000 });
        await page.waitForTimeout(500); /* 等 transition: background 走完(旧值/中间值不算) */
        const st = await probeFirstVsRow(page, def.list, cs.sel);
        expect(st.error, `面 ${faceId} 状态行探针`).toBeUndefined();
        expect(st.firstVisible, `面 ${faceId} 状态行 ${cs.sel}: 首格可见底 != 行板`
          + ` —— 首格 ${st.firstVisible}(bg=${st.firstBg}${st.firstImg === 'gradient' ? '+渐变' : ''})`
          + ` vs 行板 ${st.rowVisible}(bg=${st.rowBg})`)
          .toBe(st.rowVisible);
      });
    }

    /* 05 健康分组: 行与首格均摘引擎卡底(六条 .group-row 规则靠内层行容器 dt05-list
     * 前缀生效 —— 修前只有单层 dt05-wrap, 前缀不匹配致规则全程空转、行带主表卡底);
     * 失败行首格保 error 色; 悬停带画在内容根(.dt05-rowin)上, 行板恒透明
     * (单内容根架构, 无兄弟列可失配)。 */
    test(`面 05: 行/首格摘引擎卡底 + 失败行首格保 error 色 + 悬停带在内容根 @fast (${skin})`, async ({ page }) => {
      collectRuntimeErrors(page);
      const def = await openDrawerFace(page, '05');
      const plain = await probeFirstVsRow(page, def.list, PLAIN_ROW);
      expect(plain.error, '面 05 常态行探针').toBeUndefined();
      expect(plain.rowBg, `面 05 常态行残留引擎卡底(${plain.rowBg}) —— .dt05-list .group-row 摘底规则空转?`
        + '(U3 接线坑: 外壳类名须 dt05-list)').toBe('rgba(0, 0, 0, 0)');
      expect(plain.firstBg, `面 05 常态行首格残留主表卡底(${plain.firstBg})`).toBe('rgba(0, 0, 0, 0)');
      /* 失败行(err 组): 首格 = .dt05-fail 内容根(整行唯一子元素), 保 error 色 ——
       * 摘底规则对 failrow 显式重声明过(同特异性后来者胜), 这里断它没被误摘 */
      const fail = await probeFirstVsRow(page, def.list, '.group-row.failrow');
      expect(fail.error, '面 05 失败行探针').toBeUndefined();
      expect(fail.firstBg, `面 05 失败行首格丢 error 色(${fail.firstBg})`).not.toBe('rgba(0, 0, 0, 0)');
      expect(fail.rowBg, `面 05 失败行行板须保持摘底(${fail.rowBg})`).toBe('rgba(0, 0, 0, 0)');
      /* 悬停: 带宽落在内容根上(不透明), 行板仍透明 —— 单内容根无兄弟列, 带宽即整行观感 */
      await page.locator(`${def.list} ${PLAIN_ROW}`).first().hover();
      await page.waitForTimeout(150);
      const hov = await probeFirstVsRow(page, def.list, PLAIN_ROW);
      expect(hov.error, '面 05 悬停行探针').toBeUndefined();
      expect(hov.firstBg, `面 05 悬停带宽未落在内容根上(${hov.firstBg})`).not.toBe('rgba(0, 0, 0, 0)');
      expect(hov.rowBg, `面 05 悬停行板被误涂(${hov.rowBg})`).toBe('rgba(0, 0, 0, 0)');
    });
  });
}

/* ------------------------------------------------------------------ *
 * 主表 search-hit 首格镜像(2026-10-14 修「必现列背景与其他列不一致」②) *
 * ------------------------------------------------------------------ */
for (const skin of SKINS) {
  test.describe(`主表 search-hit 首格镜像 ${skin}`, () => {
    installRuntimeErrorGuard(test);

    test(`追剧表搜索命中行: 首格带同款 accent 渐层(修前 backgroundImage=none 丢整条渐层) @fast (${skin})`, async ({ page }) => {
      collectRuntimeErrors(page);
      await page.setViewportSize(WIDE);
      await page.goto(`${BASE_URL}/${skin}/`, { waitUntil: 'domcontentloaded' });
      await expect(page.locator('#app')).not.toHaveAttribute('v-cloak', { timeout: 15_000 });
      await page.click('nav.tabs [data-view="shows"]');
      await expect(page.locator('.group-row').first()).toBeVisible({ timeout: 15_000 });

      /* 桩种子名 Some.Show.S01E{nn}... ⇒ "Some" 命中多行(服务端单点 searchHits) */
      await page.locator('.topbar input[placeholder="搜索种子或文件名..."]').fill('Some');
      const hit = page.locator('.group-row.search-hit').first();
      await expect(hit, '追剧表无 search-hit 行(搜索未命中? 桩数据口径漂移?)').toBeVisible({ timeout: 10_000 });

      const shot = await page.evaluate(() => {
        const row = document.querySelector('.group-row.search-hit');
        const first = row.firstElementChild;
        const rs = getComputedStyle(row);
        const fs = getComputedStyle(first);
        return {
          rowImg: rs.backgroundImage,
          rowBg: rs.backgroundColor,
          firstImg: fs.backgroundImage,
          firstBg: fs.backgroundColor,
          firstCls: String(first.className).slice(0, 40),
        };
      });
      expect(shot.rowImg, 'search-hit 行自身缺 accent 渐层(components.css 同款被删?)').toContain('linear-gradient');
      expect(shot.firstImg, `面 追剧表 search-hit 首格(${shot.firstCls})缺同款渐层`
        + `(修前 backgroundImage=none: 整条渐层丢失, 名称列读作异色竖带; 现 ${shot.firstImg})`)
        .toContain('linear-gradient');
      expect(shot.firstBg, `search-hit 首格基色 != 行基色(须同为 --bg-row)`)
        .toBe(shot.rowBg);
    });
  });
}
