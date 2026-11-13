// @ts-check
import { expect, test } from '@playwright/test';
import { baseUrl } from './harness.mjs';
import { collectRuntimeErrors, installRuntimeErrorGuard } from './lib/errors.mjs';

/**
 * flux HR 分类 chip 三态: 语义色 + 行状态不让路 + 排除态 + 抽屉 hero(计划 26-11-14-0001 S4, D7)
 *
 * **报障面**: 配了 add_category* 的 HR 种子, 分类列 cat-chip 的语义色此前在 seeding 行被
 * 行状态色覆盖(染绿)—— T3 给四皮肤行状态规则补 :not() 让路。静态守阵
 * (test_webui_static_skins_widget::test_frontend_cat_chip_hr_semantics_css)只读 CSS 文本,
 * 看不见级联胜负; computed 背景才是"行状态不让路"的运行时证明(R6: 断言用 computed 值而非
 * 仅类名 —— 类名命中而级联被覆盖时背景仍是行状态色, 只查类名会假绿)。
 *
 * **数据面**: spec 无 route 级 mock, 行数据全走 ui_harness.py 桩单点 —— 桩把站点 HR 规则的
 * 输出值对齐合成种子既有分类池(add_category=TV / add_category_for_satisfied=Anime /
 * exclude_categories=Movies, 不新增分类值), 三态行数据与搜索词见 _inject_hr_category docstring:
 *   pending 样本 = 搜 "x265-GROUP82"(TV, 触发未达标, stalledUP seeding 态, s-seeding 行);
 *   done 样本    = 搜 "x265-GROUP102"(对内 103 号 Anime, 触发已达标, 同为 seeding 态);
 *   排除样本     = 全部 Movies 行(hr_excluded_by="category", 首窗口即有);
 *   抽屉样本     = pending 行双击 -> 详情 hero 的 .dt01-chip.is-hr。
 *
 * **主判据**: cat-chip 的 backgroundColor === var(--hr-*) 的解析值(探针元素现算)且不等于
 * 该行行状态色(green-soft/error-soft); 排除态 computed borderTopStyle=dashed + 背景透明。
 * flux 单皮肤(D7 口径: 四皮肤 CSS 是同一镜像模板, 齐装由静态守阵兜住)。
 */

/** 搜索收窄: fill 换词即重查(防抖+服务端 searchHits 两段延迟), 落袋判据 = 期望行真进窗口。 */
async function searchTorrents(page, token, waitSel) {
  await page.locator('.search-box input').fill(token);
  await expect(page.locator(waitSel).first(),
    `搜索 ${token} 后期望行未进窗口 —— 桩样本/搜索词漂移? 同步 scripts/ui_harness.py::_inject_hr_category`)
    .toBeVisible({ timeout: 15_000 });
}

/** 读一行里目标 chip 的 computed 背景 + 相关令牌解析值(探针元素现算, 不比对 CSS 字面)。 */
async function readChipBg(page, rowSel, chipSel) {
  return page.evaluate(({ rowSel, chipSel }) => {
    const row = document.querySelector(rowSel);
    const chip = row && row.querySelector(chipSel);
    if (!chip) return null;
    const probe = (v) => {
      const el = document.createElement('i');
      el.style.background = v;
      document.body.appendChild(el);
      const c = getComputedStyle(el).backgroundColor;
      el.remove();
      return c;
    };
    return {
      rowClass: row.className,
      chipClass: chip.className,
      bg: getComputedStyle(chip).backgroundColor,
      soft: probe('var(--hr-pending-soft)'),
      doneSoft: probe('var(--hr-done-soft)'),
      green: probe('var(--green-soft)'),
      error: probe('var(--error-soft)'),
    };
  }, { rowSel, chipSel });
}

test.describe('flux HR 分类 chip 三态', () => {
  installRuntimeErrorGuard(test);

  test('pending/done 语义色让路 + 排除态 + 抽屉 hero @fast (flux)', async ({ page }) => {
    collectRuntimeErrors(page);
    // 抽屉 hero 的 dt01-chip is-hr 承载在 general 变体 01(drawer-general-variants 同款预置)
    await page.addInitScript(
      (v) => localStorage.setItem('autoqb.ui.drawerTpl', JSON.stringify({ general: v })), '01');
    await page.goto(`${baseUrl()}/flux/`, { waitUntil: 'domcontentloaded' });
    await expect(page.locator('#app')).not.toHaveAttribute('v-cloak', { timeout: 15_000 });
    await page.click('nav.tabs [data-view="torrents"]');
    await expect(page.locator('.torrent-row').first()).toBeVisible({ timeout: 30_000 });

    // 1. pending: seeding 行的 hr-pending cat-chip 背景 = pending-soft, 不让路给 green-soft(R3)
    await searchTorrents(page, 'x265-GROUP82', '.torrent-row.s-seeding:has(.cat-chip.hr-pending)');
    const p = await readChipBg(page, '.torrent-row.s-seeding:has(.cat-chip.hr-pending)', '.cat-chip.hr-pending');
    expect(p, 'seeding 态 hr-pending 行读数失败(行/chip 结构变了?)').not.toBeNull();
    expect(p.soft, 'pending-soft 与 green-soft 解析同值 —— 令牌面漂移, 让路断言失去对照')
      .not.toBe(p.green);
    expect(p.bg, `hr-pending chip 背景(${p.bg})应为 pending-soft(${p.soft}) —— 语义色没上屏`)
      .toBe(p.soft);
    expect(p.bg, `hr-pending chip 背景(${p.bg})被 seeding 行染成 green-soft(${p.green}) —— ` +
      '行状态 :not() 让路失效(R3 回归)')
      .not.toBe(p.green);

    // 2. done: seeding 行的 hr-done cat-chip 背景 = done-soft, 不让路给 green-soft(同理;
    //    桩的 done 样本与 pending 样本同为 stalledUP —— errored 不是合法 qB 状态名, 桩数据里
    //    kind=other 没有覆盖规则, 只有 seeding/downloading/checking/moving/error 五态可让路)
    await searchTorrents(page, 'x265-GROUP102', '.torrent-row.s-seeding:has(.cat-chip.hr-done)');
    const d = await readChipBg(page, '.torrent-row.s-seeding:has(.cat-chip.hr-done)', '.cat-chip.hr-done');
    expect(d, 'seeding 态 hr-done 行读数失败(行/chip 结构变了?)').not.toBeNull();
    expect(d.doneSoft, 'done-soft 与 green-soft 解析同值 —— 令牌面漂移, 让路断言失去对照')
      .not.toBe(d.green);
    expect(d.bg, `hr-done chip 背景(${d.bg})应为 done-soft(${d.doneSoft}) —— 语义色没上屏`)
      .toBe(d.doneSoft);
    expect(d.bg, `hr-done chip 背景(${d.bg})被 seeding 行染成 green-soft(${d.green}) —— ` +
      '行状态 :not() 让路失效(R3 回归)')
      .not.toBe(d.green);

    // 3. 排除态: Movies 行(排除表命中 excluded_by=category)的 cat-chip 虚线描边 + 背景透明,
    //    行状态(s-seeding)不再给它上色 —— 排除态压过行状态与语义色(三态互斥的排除支)
    await searchTorrents(page, 'x265-GROUP296', '.torrent-row.s-seeding:has(.cat-chip.hr-excl)');
    const excl = await page.evaluate(() => {
      const chip = document.querySelector('.torrent-row .cat-chip.hr-excl');
      if (!chip) return null;
      const cs = getComputedStyle(chip);
      return { border: cs.borderTopStyle, bg: cs.backgroundColor };
    });
    expect(excl, '排除行读数失败: 窗口内没有 .cat-chip.hr-excl(排除链/绑定断了?)').not.toBeNull();
    expect(excl.border, '排除 chip 描边不是 dashed —— 虚线排除态形态丢失(计划 S3 排除态)').toBe('dashed');
    expect(excl.bg, `排除 chip 背景(${excl.bg})不透明 —— 排除态应转灰(transparent 底)`).toBe('rgba(0, 0, 0, 0)');

    // 4. 抽屉: pending 行双开详情 -> hero 出现 dt01-chip is-hr(文本 = hr_category 展开值 "TV")
    await searchTorrents(page, 'x265-GROUP82', '.torrent-row.s-seeding:has(.cat-chip.hr-pending)');
    const row = page.locator('.torrent-row.s-seeding:has(.cat-chip.hr-pending)').first();
    await row.dblclick({ force: true }); // force: 整表 2s 重渲染抢点击(drawer-dock-stability 同款)
    const drawer = page.locator('.drawer-dock > .drawer');
    await expect(drawer).toBeVisible({ timeout: 5_000 });
    await expect(drawer.locator('.dt01-hr .dt01-chip.is-hr'),
      '详情抽屉 hero 没有出现 HR 分类 chip(dt01-chip is-hr) —— 抽屉 2 行绑定断了(D6 修复面)')
      .toHaveText('TV', { timeout: 5_000 });
  });
});
