// @ts-check
import { expect, test } from '@playwright/test';
import { BASE_URL, SKINS } from './harness.mjs';
import { collectRuntimeErrors, installRuntimeErrorGuard } from './lib/errors.mjs';

/**
 * 详情面板表格「几何一致性」守阵(计划 26-10-13-0811 W2) —— 把肉眼症状钉成数字。
 *
 * 背景(用户 2026-10-13 报障八项): 表头异色背景 / 速度列下方异常横条 / 多列内容挤在一起 /
 * 进度表头对齐与主表不一致 / 速度不实时 / 密度雷达列名多一个箭头 / 内容表按钮被当作单独的列 /
 * 勾选导致跳动。其中「横条 / 挤压 / 不对齐」三项的根因同一个: **网格轨道数、列头格数、数据行
 * 子格数三者不相等**, 以及**列头与值格的水平缘不对齐**。
 *
 * W2 首日用一次性探针实测了 11 个表格面(数据已记任务档案 26-10-13-webui-detail-table-rebuild):
 *   达标: 经典三张(drawerTracker/drawerPeer/drawerFile)、09 密度雷达 —— 三处计数相等且零偏移
 *     (2026-10-14: 经典三张随「移除四内容页签经典 UI」整体退役, 其用例从 CASES 摘除。)
 *   未达标(留给对应波次修好后纳入本守阵):
 *     04 卡片栅格  2 / 1 / 3  —— 变体 CSS 把行容器覆写成两列, 而列模型是单列, 行输出 3 格
 *     10 树+详情   6 / 5 / 5  —— 多出一条轨道(就是「多出来的横带」)
 *     08 五区分组  17 / 10 / 10 —— 分组表头几何塌了, 列头左缘全 0
 *     06 增强表格 / 11 树表批量 —— 计数一致, 但列头与值格有 6~14px 水平偏移
 *   另有「异色背景」实证: 06/09/07/11 的 sticky 表头被刷成 rgb(253,254,255), 与面板底
 *     rgb(242,246,251) 不同色 —— 那是 W6 样式单点化要收的口子。
 *
 * 本守阵只钉**当前已达标**的面 —— 不是放宽容忍, 而是「先立规格、未达标的按波次修到绿再纳入」;
 * 已达标面一旦回潮(多一格 / 差一点)立刻红。
 */

const TAB_TEXT = { trackers: 'Tracker', peers: '用户', content: '内容' };

/* 已达标面: 页签 + 变体 id + 期望的表 id + 期望列数
 * (2026-10-14: 经典三张 drawerTracker/drawerPeer/drawerFile 的行用例随经典渲染链移除退役 ——
 *  四内容页签此后恒为变体态, 本表只列变体表格面。) */
const CASES = [
  { tab: 'peers', tpl: '09', tid: 'drawerPeerV09', cols: 9 },
  /* W2 修复面: 偏移根因 = 变体覆写行几何时不带列头(06: 14-8=6px; 11: 14-4=10px + gap 8≠10 逐列累计)。
   * 修法 = --tbl-pad-x / --tbl-gap 变量, 列头与行同取, 变体只声明值。 */
  { tab: 'trackers', tpl: '06', tid: 'drawerTrackerV06', cols: 8 },
  { tab: 'content', tpl: '11', tid: 'drawerContentV11', cols: 4 },
  /* W3 实测自洽面(探针 2026-10-13): 05 单列分段(列头 1 格 = 行 1 格); 07/08 十列
   * (files 渐进列已删, 列常驻)。 */
  { tab: 'trackers', tpl: '05', tid: 'drawerTrackerV05', cols: 1 },
  { tab: 'peers', tpl: '07', tid: 'drawerPeerV07', cols: 10 },
  { tab: 'peers', tpl: '08', tid: 'drawerPeerV08', cols: 10 },
];

for (const skin of SKINS) {
  test.describe(`详情表格几何一致性 ${skin}`, () => {
    installRuntimeErrorGuard(test);

    for (const c of CASES) {
      test(`${c.tid} 三处计数相等且列头与值格同缘 (${skin})`, async ({ page }) => {
        collectRuntimeErrors(page);

        if (c.tpl) {
          await page.addInitScript(
            (o) => localStorage.setItem('autoqb.ui.drawerTpl', JSON.stringify(o)),
            { [c.tab]: c.tpl },
          );
        }
        await page.goto(`${BASE_URL}/${skin}/`, { waitUntil: 'domcontentloaded' });
        await expect(page.locator('#app')).not.toHaveAttribute('v-cloak', { timeout: 15_000 });
        await expect(page.locator('.group-row').first()).toBeVisible({ timeout: 30_000 });
        await page.click('nav.tabs [data-view="torrents"]');
        await expect(page.locator('.torrent-row').first()).toBeVisible({ timeout: 15_000 });
        await page.dblclick('.torrent-row >> nth=0', { force: true });
        const drawer = page.locator('.drawer-dock > .drawer');
        await expect(drawer).toBeVisible({ timeout: 5_000 });
        await drawer.locator('.drawer-tabs button', { hasText: TAB_TEXT[c.tab] }).click();

        const row = drawer.locator(`.group-row[data-table="${c.tid}"]`).first();
        await expect(row).toBeVisible({ timeout: 5_000 });

        const probe = await page.evaluate((tid) => {
          /* 取**行所在段**的表头配对(2026-10-18 分段变体空组改原地 hidden 类后, 帧内首座
           * 表头可能属于 display:none 的空组 section, rect 恒 0 —— 与可见行配对必假红;
           * 列头与行本就在同一座锚里(aq-table + .group-table 同段 teleport), 按行反查即真值) */
          const rowEl = document.querySelector('.group-row[data-table="' + tid + '"]');
          if (!rowEl) return null;
          const anchor = rowEl.closest('[data-dt-table-anchor]');
          const head = anchor && anchor.querySelector('.group-head[data-table="' + tid + '"]');
          if (!head) return null;
          const cs = getComputedStyle(head);
          const tracks = (cs.gridTemplateColumns || '').trim().split(/\s+/).filter(Boolean).length;
          const headCells = head.querySelectorAll(':scope > .h-cell').length;
          const cells = rowEl.children.length;
          const hc = Array.from(head.querySelectorAll(':scope > .h-cell'));
          const rc = Array.from(rowEl.children);
          const n = Math.min(hc.length, rc.length);
          const leftDiff = [];
          const alignDiff = [];
          for (let i = 0; i < n; i++) {
            const d = Math.round(hc[i].getBoundingClientRect().left - rc[i].getBoundingClientRect().left);
            if (Math.abs(d) > 1) leftDiff.push({ i, d });
            const ha = getComputedStyle(hc[i]).textAlign;
            const ra = getComputedStyle(rc[i]).textAlign;
            if (ha !== ra) alignDiff.push({ i, ha, ra });
          }
          return { tracks, headCells, cells, leftDiff, alignDiff };
        }, c.tid);

        expect(probe, `未找到 ${c.tid} 的表头或行(表格面改名/未挂载? 同步本 spec)`).not.toBeNull();
        expect(probe.tracks, '网格轨道数 == 列数').toBe(c.cols);
        expect(probe.headCells, '列头格数 == 列数').toBe(c.cols);
        expect(probe.cells, '数据行子格数 == 列数').toBe(c.cols);
        expect(probe.leftDiff, '列头与值格左缘对齐(±1px)').toEqual([]);
        expect(probe.alignDiff, '列头与值格 text-align 一致').toEqual([]);
      });
    }

    /* 04 状态卡片栅格 —— 非网格形态, 不适用「三处计数」表格规格(W3 探针实测:
     * 列头被变体有意隐藏, 容器两列卡片栅格, 行是 display:block 卡片)。本规格钉的是
     * 卡片形态本身不回潮成表格、栅格不塌:
     *   ① 列头 display:none(变体声明, 不许以「修对齐」之名复活);
     *   ② 行容器 display:block(卡片), 不是 grid 行;
     *   ③ 容器 .group-table 两列栅格(栅格数 = 变体声明, 塌成单列/三列即红);
     *   ④ 卡内块结构 dt04-head/dt04-stats 存在(head 必须, stats 必须, msg 可选)。 */
    test(`drawerTrackerV04 卡片形态规格: 列头隐藏 + 行是卡片 + 容器两列栅格 (${skin})`, async ({ page }) => {
      collectRuntimeErrors(page);
      await page.addInitScript(
        (o) => localStorage.setItem('autoqb.ui.drawerTpl', JSON.stringify(o)),
        { trackers: '04' },
      );
      await page.goto(`${BASE_URL}/${skin}/`, { waitUntil: 'domcontentloaded' });
      await expect(page.locator('#app')).not.toHaveAttribute('v-cloak', { timeout: 15_000 });
      await expect(page.locator('.group-row').first()).toBeVisible({ timeout: 30_000 });
      await page.click('nav.tabs [data-view="torrents"]');
      await expect(page.locator('.torrent-row').first()).toBeVisible({ timeout: 15_000 });
      await page.dblclick('.torrent-row >> nth=0', { force: true });
      const drawer = page.locator('.drawer-dock > .drawer');
      await expect(drawer).toBeVisible({ timeout: 5_000 });
      await drawer.locator('.drawer-tabs button', { hasText: 'Tracker' }).click();

      const row = drawer.locator('.group-row[data-table="drawerTrackerV04"]').first();
      await expect(row).toBeVisible({ timeout: 5_000 });

      const probe = await page.evaluate(() => {
        const head = document.querySelector('.group-head[data-table="drawerTrackerV04"]');
        const table = document.querySelector('[data-dt-table-anchor="drawerTrackerV04"] .group-table');
        const rowEl = document.querySelector('.group-row[data-table="drawerTrackerV04"]');
        if (!head || !table || !rowEl) return null;
        return {
          headDisplay: getComputedStyle(head).display,
          tableGTC: getComputedStyle(table).gridTemplateColumns.trim().split(/\s+/).filter(Boolean).length,
          rowDisplay: getComputedStyle(rowEl).display,
          hasHead: !!rowEl.querySelector(':scope > .dt04-head'),
          hasStats: !!rowEl.querySelector(':scope > .dt04-stats'),
        };
      });

      expect(probe, '未找到 04 的表格面(改名/未挂载? 同步本 spec)').not.toBeNull();
      expect(probe.headDisplay, '列头隐藏是卡片形态的声明(不许复活)').toBe('none');
      expect(probe.tableGTC, '容器保持两列卡片栅格(塌成单列/三列即红)').toBe(2);
      expect(probe.rowDisplay, '行是卡片(block), 不是网格行').toBe('block');
      expect(probe.hasHead, '卡内有 dt04-head 块').toBe(true);
      expect(probe.hasStats, '卡内有 dt04-stats 块').toBe(true);
    });

    /* 10 树 + 详情 —— 非网格形态(W4 探针实测: 列头声明隐藏, 行 3 格 3 轨道, 缩进 =
     * name 格内 paddingLeft, 与「树缩进是单元格渲染器」的计划口径一致)。2026-10-14 复查
     * 修法(26-10-14-0136 §02): tgl/prio 两列已收编进 name 格(折叠钮在格首随缩进 = 层级,
     * 徽章在格尾右对齐 = 不占列), 行由 5 轨变 3 轨。规格钉:
     *   ① 列头 display:none(声明); ② 行轨道 3 段 + 3 格; ③ 树缩进存在(子层 paddingLeft>0);
     *   ④ 交互件在 name 格内(dt10-tgl/dt10-pbadge 且是 .dt10-n 的后代)。 */
    test(`drawerContentV10 树形态规格: 列头隐藏 + 行 3 格 3 轨道 + 树缩进 + 交互件在 name 格 (${skin})`, async ({ page }) => {
      collectRuntimeErrors(page);
      await page.addInitScript(
        (o) => localStorage.setItem('autoqb.ui.drawerTpl', JSON.stringify(o)),
        { content: '10' },
      );
      await page.goto(`${BASE_URL}/${skin}/`, { waitUntil: 'domcontentloaded' });
      await expect(page.locator('#app')).not.toHaveAttribute('v-cloak', { timeout: 15_000 });
      await expect(page.locator('.group-row').first()).toBeVisible({ timeout: 30_000 });
      await page.click('nav.tabs [data-view="torrents"]');
      await expect(page.locator('.torrent-row').first()).toBeVisible({ timeout: 15_000 });
      await page.dblclick('.torrent-row >> nth=0', { force: true });
      const drawer = page.locator('.drawer-dock > .drawer');
      await expect(drawer).toBeVisible({ timeout: 5_000 });
      await drawer.locator('.drawer-tabs button', { hasText: '内容' }).click();

      const row = drawer.locator('.group-row[data-table="drawerContentV10"]').first();
      await expect(row).toBeVisible({ timeout: 5_000 });

      const probe = await page.evaluate(() => {
        const head = document.querySelector('.group-head[data-table="drawerContentV10"]');
        const rows = Array.from(
          document.querySelectorAll('.group-row[data-table="drawerContentV10"]'),
        ).filter((r) => r.children.length > 1);
        if (!head || !rows.length) return null;
        const nameIndents = rows
          .map((r) => r.querySelector('.dt10-n'))
          .filter(Boolean)
          .map((el) => parseFloat(getComputedStyle(el).paddingLeft) || 0);
        const dirRow = rows.find((r) => r.querySelector('.dt10-tgl'));
        const fileRow = rows.find((r) => r.querySelector('.dt10-pbadge')) || rows[0];
        return {
          headDisplay: getComputedStyle(head).display,
          tracks: (getComputedStyle(rows[0]).gridTemplateColumns || '').trim().split(/\s+/).filter(Boolean).length,
          cells: rows[0].children.length,
          maxIndent: Math.max(...nameIndents),
          hasProg: !!rows[0].querySelector('.dt10-prog'),
          tglInName: !!dirRow && !!dirRow.querySelector('.dt10-n .dt10-tgl'),
          badgeInName: !!fileRow.querySelector('.dt10-n .dt10-pbadge'),
        };
      });

      expect(probe, '未找到 drawerContentV10(改名/未挂载? 同步本 spec)').not.toBeNull();
      expect(probe.headDisplay, '列头隐藏是树形态的声明(不许复活)').toBe('none');
      expect(probe.tracks, '行轨道 3 段(多一条轨道 = 「横带」类症状; tgl/prio 独立列已删)').toBe(3);
      expect(probe.cells, '行 3 格').toBe(3);
      expect(probe.maxIndent, '树缩进存在(子层 paddingLeft > 0)').toBeGreaterThan(0);
      expect(probe.hasProg, '进度格在').toBe(true);
      expect(probe.tglInName, '折叠钮在 name 格内(随缩进 = 层级, 治「展开按钮没有层级」)').toBe(true);
      expect(probe.badgeInName, '徽章在 name 格内(不占列, 治「操作按钮独立成列」)').toBe(true);
    });
  });
}
