// @ts-check
import { expect, test } from '@playwright/test';
import { baseUrl, SKINS } from './harness.mjs';
import { collectRuntimeErrors, installRuntimeErrorGuard } from './lib/errors.mjs';
import { expectNoDeadClass } from './lib/dt-dead-class.mjs';

/**
 * general 三变体(01 英雄行 / 02 六卡聚类 / 03 双栏档案)行为级守阵(存量评审 R4·P12 批):
 *
 *   row14 → R5#91(major): 01 此前只有可见性断言(初始渲染被执行, 分支从未测) —— 本 spec
 *     补 01 手势 e2e: 折叠组头(data-fold)/展开全部字段(details rawOpen)/点复制钮,
 *     并在初始态断言英雄行 -1 哨兵守卫(R5#76: num_leechs/num_complete/connections_limit
 *     = -1 时渲染 —/「不限」, 不再出现裸 0(-1)、连接 8 / -1)与 HR 徽章单源文案(R5#79)。
 *   row15 → R5#89(major): 02 的 render 从未被任何测试真执行 —— localStorage 预置
 *     general:'02' 渲染六卡聚类, 断言卡片数/磁力钮在场, 覆盖一次卡片折叠手势;
 *     HR 达标徽章文案在此钉单源口径(修前 02 渲染「已触发 · 已达标」= 红)。
 *   row16 → R5#90(major): 03 同样零行为级覆盖 —— 选 03 渲染双栏档案, 断言 dt03-wrap/
 *     dt03-side 与 details(更多字段)展开手势; wide 类接线在此钉(R5#78: 数据契约对
 *     哈希/路径行发 wide:true, gridRows 挂 wide 类整行 span, 修前恒 class="dt03-item")。
 *   row77 → R5#93: 变体切换手势 —— 右键菜单把 general 从 01 切到 02, 断言旧变体根类
 *     (.dt01-wrap)不在场且点击只触发一次动作(剪贴板探针计数; 换变体必须摘旧监听,
 *     否则 wireEvents 的 __dtEvents 在册守卫会让新变体手势全哑)。
 *   issue 26-11-08-0229: 01/02 折叠手势补 aria-expanded 点击同步断言(核心 H.foldToggle
 *     单点, 修前点击到重渲之间读屏语义与视觉反向) + 02 补 secRows wide 接线钉(存储卡
 *     4 路径行挂 .wide 且 .v 折行, 非 wide 行仍 nowrap; 与 03 R5#78 同语义槽)。
 *
 * 数据面: page.route 拦单段 glob(只命中详情端点 /api/torrents/<hash>, 不波及 trackers/files
 * /peers 子路径) + route.fetch() 取真桩
 * 响应后只改写 body.torrent 指定字段(gtm-alert.spec 同手法) —— 载荷保持生产形状, 测试只钉
 * 自己关心的字段; relocate 置 null 让「迁移」段确定性离场(卡片数/分组数不随桩内 job 漂)。
 * 手势全部真实点击, 不借道 vm; 剪贴板探针 = addInitScript 包 writeText 记账(D4 evaluate
 * 允许的桩态注入类 —— navigator.clipboard 无 DOM 之外的计数口径)。
 */

const WIDE = { width: 2560, height: 1200 };

/** 详情桩共享补丁: 让与断言无关的字段确定性(迁移离场/哨兵字段取正常值/HR 全空)。 */
const BASE_PATCH = {
  relocate: null,
  num_seeds: 8, num_leechs: 5, num_complete: 12, num_incomplete: 3,
  connections_count: 8, connections_limit: 100,
  infohash_v1: 'a'.repeat(40), infohash_v2: 'b'.repeat(64),
  save_path: 'R:\\Downloads\\Set000\\Some.Show.S01E01.1080p.WEB-DL.x265-GROUP0',
  /* issue 26-11-08-1621 起「下载路径 / 根路径」的 wide 是条件式(值非空才整行折行)。
   * 桩不给这两个字段会让 dt02 路径 wide 行 4→2、dt03 wide 行 7→5 —— 下方断言验的是
   * 「有值场景」的正向接线, 故四个路径行必须都给非空值; 空值负向面由
   * tests/test_webui_static_r4_node_batteries.py 的 node battery 覆盖, 不在此重复。 */
  content_path: 'R:\\Downloads\\Set000\\Some.Show.S01E01.1080p.WEB-DL.x265-GROUP0\\ep01.mkv',
  download_path: 'R:\\Downloads\\Incomplete',
  root_path: 'R:\\Downloads\\Set000',
  site: 'hhanclub', category: 'tv', tags: 'HR,Free', private: true,
  up_limit: 0, dl_limit: 0,
  hr_triggered: false, hr_satisfied: false, hr_excluded: false,
  hr_req_time: 0, hr_req_ratio: 0, hr_state: '', hr_reason: '',
  hr_tag: '', hr_tag_done: '', hr_site_lane: '', hr_site_need: '', hr_site_remain: '',
};

/** HR 已触发已达标补丁(R5#79 文案单源的断言面)。 */
const HR_TRIGGERED_OK = { hr_triggered: true, hr_satisfied: true, hr_req_time: 10800, hr_req_ratio: 2.5 };

/**
 * 详情拦截桩: route.fetch() 取真桩响应后只改写 body.torrent 的指定字段。
 * @param {import('@playwright/test').Page} page
 * @param {Record<string, *>} patch
 */
async function stubDetail(page, patch) {
  await page.route('**/api/torrents/*', async (route) => {
    const resp = await route.fetch();
    let body = null;
    try { body = await resp.json(); } catch { body = null; }
    if (!body || !body.torrent) { await route.fulfill({ response: resp }); return; }
    Object.assign(body.torrent, patch);
    await route.fulfill({ response: resp, json: body });
  });
}

/**
 * 剪贴板探针: 包掉 writeText 记账到 window.__copyCalls(恒 resolve, 不依赖无头权限)。
 * 读数一律走字符串 evaluate('window.__copyCalls ...')。
 * @param {import('@playwright/test').Page} page
 */
function spyClipboard(page) {
  return page.addInitScript(() => {
    (/** @type {any} */ (window)).__copyCalls = [];
    const writeText = (t) => {
      (/** @type {any} */ (window)).__copyCalls.push(String(t));
      return Promise.resolve();
    };
    try {
      if (navigator.clipboard) {
        Object.defineProperty(navigator.clipboard, 'writeText', { configurable: true, value: writeText });
      } else {
        Object.defineProperty(navigator, 'clipboard', { configurable: true, value: { writeText } });
      }
    } catch { /* 探针装不上时用例退化为仅 toast 断言 */ }
  });
}

/**
 * localStorage 预置 general 变体选择(照 drawer-content-variant-tables.spec 同款写法)。
 * @param {import('@playwright/test').Page} page
 * @param {string} id
 */
function presetGeneralVariant(page, id) {
  return page.addInitScript(
    (v) => localStorage.setItem('autoqb.ui.drawerTpl', JSON.stringify({ general: v })), id);
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
  test.describe(`general 三变体手势 ${skin}`, () => {
    installRuntimeErrorGuard(test);

    test(`dt01 英雄行: -1 哨兵守卫 + HR 单源文案 + 折叠/展开/复制手势 @fast (${skin})`, async ({ page }) => {
      collectRuntimeErrors(page);
      spyClipboard(page);
      presetGeneralVariant(page, '01');
      await stubDetail(page, { ...BASE_PATCH, ...HR_TRIGGERED_OK, num_leechs: -1, num_complete: -1, connections_limit: -1 });
      await page.setViewportSize(WIDE);
      await page.goto(`${baseUrl()}/${skin}/`, { waitUntil: 'domcontentloaded' });
      await expect(page.locator('#app')).not.toHaveAttribute('v-cloak', { timeout: 15_000 });
      await expect(page.locator('.group-row').first()).toBeVisible({ timeout: 30_000 });
      const drawer = await openTorrentDrawer(page);
      const host = drawer.locator('.dt-host[data-dt-host="general"]');
      await expect(host).toHaveClass(/dt-tpl/, { timeout: 5_000 });
      const wrap = drawer.locator('.dt01-wrap');
      await expect(wrap).toBeVisible();
      await expectNoDeadClass(page, '变体 01 挂载态');

      // ---- R5#76: 英雄行做种/用户槽(-1 哨兵守卫) —— 大值 "8 / —", 副行 "swarm 8 · 连接 8 / 不限"
      const peersCell = wrap.locator('.dt01-hero > div').nth(3);
      await expect(peersCell.locator('.dt01-v')).toContainText('/ —');
      await expect(peersCell.locator('.dt01-s')).toContainText('swarm 8 · 连接 8 / 不限');
      expect(await peersCell.innerText(), '-1 哨兵不得原样上屏(修前: swarm 0(-1) · 连接 8 / -1)')
        .not.toContain('-1');

      // ---- R5#79: HR 徽章单源文案 + 先时长字段序(01 侧; 修前是「H&R 已达标」)
      const hr = wrap.locator('.dt01-hr');
      await expect(hr).toHaveClass(/is-done/);
      await expect(hr.locator('.dt01-hr-badge')).toHaveText('HR 已触发 · 已达标');
      const hrText = await hr.innerText();
      expect(hrText.indexOf('要求做种'), '要求做种(时长)必须在要求分享率之前(01/03 多数派口径)')
        .toBeGreaterThanOrEqual(0);
      expect(hrText.indexOf('要求做种')).toBeLessThan(hrText.indexOf('要求分享率'));

      // ---- R5#91 手势 1: 折叠组头(data-fold) —— 时间组真收拢, 再点展开(来回各一次)
      // (aria-expanded 点击同步走核心 H.foldToggle 单点, issue 26-11-08-0229 #3 —— 修前只翻 class)
      const timeSec = wrap.locator('.dt01-sec[data-sec="时间"]');
      await expect(timeSec.locator('[data-fold]')).toHaveAttribute('aria-expanded', 'true');
      await timeSec.locator('[data-fold]').click();
      await expect(timeSec, '折叠后该组挂 .folded').toHaveClass(/folded/);
      await expect(timeSec.locator('[data-fold]'), '点击拍即同步 aria-expanded(修前要等重渲)')
        .toHaveAttribute('aria-expanded', 'false');
      await expect(timeSec.locator('.dt01-grid'), '折叠后组体隐藏').toBeHidden();
      await timeSec.locator('[data-fold]').click();
      await expect(timeSec.locator('[data-fold]'), '再点展开 aria-expanded 回 true')
        .toHaveAttribute('aria-expanded', 'true');
      await expect(timeSec.locator('.dt01-grid'), '再点展开回原状').toBeVisible();

      // ---- R5#91 手势 2: 展开全部字段(details rawOpen) —— summary 点击原生翻转 open
      const raw = wrap.locator('.dt01-raw');
      await expect(raw).not.toHaveAttribute('open');
      await raw.locator('.dt01-rawsum').click();
      await expect(raw, '展开全部字段后 details 持 open').toHaveAttribute('open');

      // ---- R5#91 手势 3: 点复制钮 —— 剪贴板探针恰好 1 条且内容 = 哈希行文本
      await wrap.locator('.dt01-cell', { hasText: '信息哈希值 v1' }).locator('[data-act="copy"]').click();
      const calls = await page.evaluate('window.__copyCalls || []');
      expect(calls, '复制钮恰好触发一次 copyText').toHaveLength(1);
      expect(calls[0], '复制内容 = 信息哈希值 v1 单元格文本').toBe('a'.repeat(40));
      await expect(page.locator('.toast-wrap .toast').first(), '复制有 toast 回执').toContainText('已复制');
    });

    test(`dt02 六卡聚类: 卡片数/磁力入口下线 + HR 单源文案 + 卡片折叠手势 @fast (${skin})`, async ({ page }) => {
      collectRuntimeErrors(page);
      presetGeneralVariant(page, '02');
      await stubDetail(page, { ...BASE_PATCH, ...HR_TRIGGERED_OK });
      await page.setViewportSize(WIDE);
      await page.goto(`${baseUrl()}/${skin}/`, { waitUntil: 'domcontentloaded' });
      await expect(page.locator('#app')).not.toHaveAttribute('v-cloak', { timeout: 15_000 });
      await expect(page.locator('.group-row').first()).toBeVisible({ timeout: 30_000 });
      const drawer = await openTorrentDrawer(page);
      const wrap = drawer.locator('.dt02-wrap');
      await expect(wrap, 'localStorage 预置 general=02 直接渲染六卡聚类').toBeVisible({ timeout: 5_000 });
      await expectNoDeadClass(page, '变体 02 挂载态(六卡聚类)');

      // ---- R5#89: 六卡聚类(base/time/xfer/id/meta/store)+ HR 触发时的 HR 卡 = 7
      // (relocate 桩置空, 「迁移」卡确定性离场)
      const cards = drawer.locator('.dt02-card');
      await expect(cards, '六卡聚类 + HR 卡 = 7').toHaveCount(7);
      for (const id of ('base time xfer id meta store').split(' ')) {
        await expect(drawer.locator(`.dt02-card[data-card="${id}"]`), `卡 ${id} 在场`).toBeVisible();
      }
      // ---- 复制 magnet 入口已下线(issue 26-11-09-0639): magnet_uri 入库即 tr= 掩码,
      // 复制出私站无法 announce 的废链接。此处钉住「入口不得回潮」, 与 ctx_menu_registry 守阵同口径。
      await expect(drawer.locator('[data-act="magnet"]'), '磁力钮不得回潮(标识卡)').toHaveCount(0);
      await expect(drawer.locator('.dt02-card[data-card="id"]'), '标识卡不再渲染 magnet 行')
        .not.toContainText('magnet');

      // ---- R5#79: HR 达标徽章单源文案(修前 02 渲染「已触发 · 已达标」= 红)
      await expect(drawer.locator('.dt02-hr-badge')).toHaveText('HR 已触发 · 已达标');
      const reqText = await drawer.locator('.dt02-hr-req').innerText();
      expect(reqText.indexOf('要求做种'), '02 字段序对齐先时长(修前先比率)').toBeGreaterThanOrEqual(0);
      expect(reqText.indexOf('要求做种')).toBeLessThan(reqText.indexOf('要求分享率'));

      // ---- 卡片折叠手势: 基础卡头点击 -> .folded, 卡体隐藏; 再点展开
      // (aria-expanded 点击同步走核心 H.foldToggle 单点, issue 26-11-08-0229 #3 —— 修前只翻 class)
      const card = drawer.locator('.dt02-card[data-card="base"]');
      await card.locator('[data-fold]').click();
      await expect(card, '折叠后该卡挂 .folded').toHaveClass(/folded/);
      await expect(card.locator('[data-fold]'), '点击拍即同步 aria-expanded(修前要等重渲)')
        .toHaveAttribute('aria-expanded', 'false');
      await expect(card.locator('.dt02-card-b'), '折叠后卡体隐藏').toBeHidden();
      await card.locator('[data-fold]').click();
      await expect(card.locator('[data-fold]'), '再点展开 aria-expanded 回 true')
        .toHaveAttribute('aria-expanded', 'true');
      await expect(card.locator('.dt02-card-b'), '再点展开回原状').toBeVisible();

      // ---- issue 26-11-08-0229 #13: secRows wide 接线(与 03 .dt03-item.wide 同语义槽) ——
      // 存储与行为卡 4 条路径行(契约恒发 wide:true)挂 .wide 且长值不再 nowrap 截断
      const storeWide = drawer.locator('.dt02-card[data-card="store"] .dt02-kv.wide');
      await expect(storeWide, '路径行恰 4 条挂 wide(修前恒 class="dt02-kv")').toHaveCount(4);
      const wideWs = await storeWide.first().locator('.v').evaluate((el) => getComputedStyle(el).whiteSpace);
      expect(wideWs, 'wide 行长值折行展示(修前 nowrap 截断)').toBe('normal');
      const normWs = await drawer.locator('.dt02-card[data-card="time"] .dt02-kv .v').first()
        .evaluate((el) => getComputedStyle(el).whiteSpace);
      expect(normWs, '非 wide 行仍 nowrap').toBe('nowrap');
    });

    test(`dt03 双栏档案: wrap/side 骨架 + wide 整行接线 + 更多字段 details 手势 @fast (${skin})`, async ({ page }) => {
      collectRuntimeErrors(page);
      presetGeneralVariant(page, '03');
      await stubDetail(page, BASE_PATCH);
      await page.setViewportSize(WIDE);
      await page.goto(`${baseUrl()}/${skin}/`, { waitUntil: 'domcontentloaded' });
      await expect(page.locator('#app')).not.toHaveAttribute('v-cloak', { timeout: 15_000 });
      await expect(page.locator('.group-row').first()).toBeVisible({ timeout: 30_000 });
      const drawer = await openTorrentDrawer(page);
      const wrap = drawer.locator('.dt03-wrap');
      await expect(wrap, 'localStorage 预置 general=03 渲染双栏档案').toBeVisible({ timeout: 5_000 });
      await expectNoDeadClass(page, '变体 03 挂载态(双栏档案)');
      const side = drawer.locator('.dt03-side');
      await expect(side, '右 252px 元信息栏在场').toBeVisible();
      await expect(side).toContainText('元信息');
      await expect(side.locator('[data-act="magnet"]'), '右栏磁力钮不得回潮(入口已下线)').toHaveCount(0);

      // ---- R5#78: wide 类接线 —— 数据契约发 wide:true 的哈希/路径行挂 .wide 且整行 span
      // (基础: 哈希 v1/v2/备注 3 条; 路径: 保存/内容/下载/根 4 条 —— 契约行恒发, 共 7)
      const wides = wrap.locator('.dt03-item.wide');
      await expect(wides, 'wide 行恰 7 条(修前 gridRows 恒 class="dt03-item")').toHaveCount(7, { timeout: 5_000 });
      const spanRatio = await wides.first().evaluate((el) => {
        const grid = /** @type {HTMLElement} */ (el.parentElement);
        return el.getBoundingClientRect().width / grid.getBoundingClientRect().width;
      });
      expect(spanRatio, 'wide 项占满整行(三列格子的非 wide 项约 0.3)').toBeGreaterThan(0.9);

      // ---- 右栏标识: 哈希 v1 复制钮在场(数据契约 copy 动作直通)
      await expect(side.locator('.dt03-crow', { hasText: '信息哈希值 v1' }).locator('[data-act="copy"]'))
        .toBeVisible();

      // ---- details 展开手势: 更多字段(扩展) summary 点击 -> open
      const ext = side.locator('.dt03-ext');
      await expect(ext).not.toHaveAttribute('open');
      await ext.locator('summary').click();
      await expect(ext, '展开更多字段后 details 持 open').toHaveAttribute('open');
    });

    test(`变体切换: 右键 01 切 02 旧根类不在场 + 点击只触发一次动作 @fast (${skin})`, async ({ page }) => {
      collectRuntimeErrors(page);
      spyClipboard(page);
      presetGeneralVariant(page, '01');
      await stubDetail(page, BASE_PATCH);
      await page.setViewportSize(WIDE);
      await page.goto(`${baseUrl()}/${skin}/`, { waitUntil: 'domcontentloaded' });
      await expect(page.locator('#app')).not.toHaveAttribute('v-cloak', { timeout: 15_000 });
      await expect(page.locator('.group-row').first()).toBeVisible({ timeout: 30_000 });
      const drawer = await openTorrentDrawer(page);
      await expect(drawer.locator('.dt01-wrap')).toBeVisible({ timeout: 5_000 });

      // 右键正文 -> 模板菜单选「六卡聚类」(真实手势, 不借道 vm)
      await drawer.locator('.drawer-body').click({ button: 'right' });
      const menu = page.locator('.ctx-menu');
      await expect(menu).toBeVisible();
      await menu.locator('.ctx-item', { hasText: '六卡聚类' }).click();
      await expect(menu, '选择落盘后菜单收起').toHaveCount(0, { timeout: 5_000 });

      // 旧变体根类不在场, 新变体挂载(register.destroy -> H.unwireEvents -> 换变体重挂)
      await expect(drawer.locator('.dt02-cards')).toBeVisible({ timeout: 5_000 });
      await expect(drawer.locator('.dt01-wrap'), '旧变体根类不得残留').toHaveCount(0);

      // 点击只触发一次动作: 复制钮 -> 剪贴板探针恰好 1 条(监听叠加/新变体手势哑火都会在这红)
      await drawer.locator('[data-act="copy"]').first().click();
      const calls = await page.evaluate('window.__copyCalls || []');
      expect(calls, '切换变体后点击必须恰好触发一次 copyText').toHaveLength(1);
      expect(calls[0], '复制内容 = 哈希 v1(标识卡行)').toBe('a'.repeat(40));
      await expect(page.locator('.toast-wrap .toast').first()).toContainText('已复制');
    });
  });
}
