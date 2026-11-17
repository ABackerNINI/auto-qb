// @ts-check
import { expect, test } from '@playwright/test';
import { baseUrl, SKINS } from './harness.mjs';
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
 *
 * 口径更新(计划 26-11-10-0027 W1 委托落地 / W3 改述): 表格几何(轨道串 / aligns)已单点到
 * DT_TABLE.layout —— columns_grid._gridTemplate / colAlignCss 内部委托该单点, 旁路拼接已删。
 * 本守阵因此不再是「两处计算一致」的 parity 比对(几何只剩一处产出), 语义改为**钉住单点输出不变**:
 * 下面断言的轨道数 / 计数 / 对齐 / text-align 全部出自 DT_TABLE.layout 的生产输出,
 * 单点实现回归(轨道漂移 / 对齐漂移)即红。
 *
 * HR 三面纳入(计划 26-11-17-0059 W3(1)): hrDetail/hrWave/hrKv 已随该计划 W1(3) 迁 aq-table grid
 * 链路(几何同走 DT_TABLE.layout 单点), W3(1) 起纳入本守阵 —— 与抽屉面同规格(轨道数/列头格数/
 * 行子格数三处相等 + 列头与值格左缘对齐 + text-align 一致), 但导航与数据面不同:
 *   · 导航: HR 三表在设置页 HR 分区的 .hr-full-modal 全屏覆盖层里(v-show 显隐, 不走抽屉),
 *     hrWave/hrKv 还要展开「排障视图」<details> 才挂行;
 *   · 数据: ui_harness 桩只灌表3 history, /api/hr/status 波次(lanes)与表1 entries 真读磁盘
 *     未播种 —— 默认场景 HR 明细/波次表恒空态, 无行可钉。沿用 variant-tables 家族既有手法
 *     page.route 拦截喂合成载荷(单站点, 规避桩默认双站点导致的行集重复); 合成行字段对齐
 *     EntryDetail.to_dict + 路由层 mark_local_present 追加的 local_present(前端默认视图
 *     只看 local_present=true, 缺它整表被筛空)。
 *   · 期望列数 = hr_status.js HR_TABLE_DEFS 列定义(单点): hrDetail 10 / hrWave 8 / hrKv 2。
 * 本文件既有用例不带 @fast(几何 parity 全量轮口径, 见 playwright.config.mjs 门禁分工),
 * HR 三面沿用同口径不标 @fast。
 */

const TAB_TEXT = { trackers: 'Tracker', peers: '用户', content: '内容' };

/* ---------------- HR 三面(计划 26-11-17-0059 W3(1)) ----------------
 * 期望列数 = hr_status.js HR_TABLE_DEFS 列定义(单点); openDiag = 行挂在「排障视图」
 * <details> 内, 导航多一步点 summary。 */
const HR_CASES = [
  { tid: 'hrDetail', cols: 10, openDiag: false },
  { tid: 'hrWave', cols: 8, openDiag: true },
  { tid: 'hrKv', cols: 2, openDiag: true },
];

/* /api/hr/status 合成载荷: 单站点(HHan) + A/B/C 三档 lanes(hrWave 行集)。字段对齐
 * SiteStatus.to_dict(人话字段后端算好口径), 缺省字段前端模板有兜底不空转。 */
function hrStatusPayload() {
  const now = Date.now() / 1000;
  const lane = (l, extra) => ({
    lane: l,
    status: 'ok',
    status_text: '本波有效',
    lane_text: `${l} 考察中`,
    wave_ts: now - 600,
    pages: 3,
    rows: 96,
    cutoff_done: now - 300,
    full_depth: true,
    fail_streak: 0,
    count_claim: 96,
    count_match: true,
    detail: '全深度翻完',
    text: '',
    ...extra,
  });
  return {
    enabled: true,
    note: 'parity e2e 合成载荷',
    channel: {},
    fetch_enabled: false,
    worker_running: false,
    poll_interval: 300,
    sites: [
      {
        site: 'HHan',
        enabled: true,
        listing: 'list',
        now,
        channel_state: 'ok',
        channel_text: '扩展已连接',
        revision: 7,
        file_path: '',
        read_error: '',
        fetched_at: now - 600,
        healthy_ts: now - 600,
        expires_at: now + 3600,
        next_wave_at: now + 1800,
        refresh_interval: 3600,
        idle_mode: false,
        stale: false,
        fresh_text: '10m前',
        releases_enabled: true,
        zero_rows: false,
        empty_confirmed: false,
        count_attested_empty: false,
        retention_text: '保留 30 天',
        notes: '',
        writer_instance: 'parity-stub',
        writer_heartbeat: now,
        index_total: 3,
        index_active: 3,
        lane_counts: { A: 1, B: 1, C: 1, D: 0 },
        pending_infohash: 0,
        backfill_ratio: 1,
        managed: 3,
        keys: 3,
        downloaded: 3,
        fails: 0,
        verified: 2,
        observing: 1,
        quota: { day: 0, day_max: 0, left: 0, last_fetch_ts: 0, min_interval: 0, next_reset: 0, text: '额度充足' },
        allow_window: '',
        blocking: '',
        lanes: [lane('A'), lane('B'), lane('C', { full_depth: false, count_claim: null, count_match: null, fail_streak: 1 })],
        lanes_text: 'A/B/C',
      },
    ],
  };
}

/* /api/hr/sites/<site>/entries 合成载荷: 行字段对齐 EntryDetail.to_dict(status.py 契约),
 * 另带路由层 mark_local_present 追加的 local_present(默认视图只看 local_present=true,
 * 缺它整表被筛空 —— routes/hr.py join 口径)。 */
function hrEntriesPayload() {
  const now = Date.now() / 1000;
  const entries = [0, 1, 2].map((i) => ({
    tid: 100 + i,
    dl_id: i,
    name: `parity 合成种子 ${i}`,
    lane: ['A', 'B', 'C'][i],
    lane_text: ['A 考察中', 'B 达标', 'C 未达标'][i],
    uploaded_bytes: 1024 * (i + 1),
    downloaded_bytes: 4096 * (i + 1),
    ratio: 0.5 + i * 0.25,
    need_seed_seconds: 86400 * (i + 1),
    need_seed_text: ['1 天', '2 天', '3 天'][i],
    infohash_v1: '',
    infohash_v2: '',
    verified_ts: i === 0 ? 0 : now - 7200,
    verified_source: i === 0 ? '' : 'satisfied',
    verified_source_text: i === 0 ? '未核实' : '已达标',
    done_iso: '2026-01-02T03:04:05Z',
    active: true,
    missing_streak: 0,
    first_seen: now - 86400,
    last_seen: now - 3600,
    local_present: true,
  }));
  return { entries, now, read_error: '' };
}

/* HR 三面共同导航: 设置页 hub → HR 在线核实 → 站点状态全屏弹层(手势链与 hr-history.spec
 * openHrHistoryTable 同族; route 拦截须在 goto 前挂, 弹层打开即触发 /api/hr/status 首拉)。 */
async function openHrModal(page, skin) {
  await page.route('**/api/hr/status', (route) =>
    route.fulfill({ contentType: 'application/json', body: JSON.stringify(hrStatusPayload()) }));
  await page.route('**/api/hr/sites/*/entries', (route) =>
    route.fulfill({ contentType: 'application/json', body: JSON.stringify(hrEntriesPayload()) }));
  await page.goto(`${baseUrl()}/${skin}/`, { waitUntil: 'domcontentloaded' });
  await expect(page.locator('.group-row').first()).toBeVisible({ timeout: 30_000 });
  await page.locator('nav.tabs-right button').click(); // 顶栏右侧「设置」(hr-history 同款手势)
  await expect(page.locator('.hb-grid .hb-card').first()).toBeVisible({ timeout: 20_000 });
  await page.locator('.hb-card', { hasText: 'HR 在线核实' }).click();
  await page
    .locator('.hb-blk-hd', { hasText: '站点状态' })
    .locator('button[aria-expanded="false"]', { hasText: '展开' })
    .click();
  await expect(page.locator('.hr-full-modal')).toBeVisible({ timeout: 10_000 });
}

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
        await page.goto(`${baseUrl()}/${skin}/`, { waitUntil: 'domcontentloaded' });
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
     *   1. 列头 display:none(变体声明, 不许以「修对齐」之名复活);
     *   2. 行容器 display:block(卡片), 不是 grid 行;
     *   3. 容器 .group-table 两列栅格(栅格数 = 变体声明, 塌成单列/三列即红);
     *   4. 卡内块结构 dt04-head/dt04-stats 存在(head 必须, stats 必须, msg 可选)。 */
    test(`drawerTrackerV04 卡片形态规格: 列头隐藏 + 行是卡片 + 容器两列栅格 (${skin})`, async ({ page }) => {
      collectRuntimeErrors(page);
      await page.addInitScript(
        (o) => localStorage.setItem('autoqb.ui.drawerTpl', JSON.stringify(o)),
        { trackers: '04' },
      );
      await page.goto(`${baseUrl()}/${skin}/`, { waitUntil: 'domcontentloaded' });
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
     *   1. 列头 display:none(声明); 2. 行轨道 3 段 + 3 格; 3. 树缩进存在(子层 paddingLeft>0);
     *   4. 交互件在 name 格内(dt10-tgl/dt10-pbadge 且是 .dt10-n 的后代)。 */
    test(`drawerContentV10 树形态规格: 列头隐藏 + 行 3 格 3 轨道 + 树缩进 + 交互件在 name 格 (${skin})`, async ({ page }) => {
      collectRuntimeErrors(page);
      await page.addInitScript(
        (o) => localStorage.setItem('autoqb.ui.drawerTpl', JSON.stringify(o)),
        { content: '10' },
      );
      await page.goto(`${baseUrl()}/${skin}/`, { waitUntil: 'domcontentloaded' });
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

    /* HR 三面(W3(1), 26-11-17-0059): 与抽屉面同规格, 差异只在导航与数据喂法(见 HR_CASES 注)。
     * 探针取头/行不用 data-dt-table-anchor(HR 表头/行是 .group-table 同容器兄弟, 非 Teleport
     * 变体锚形态), 直接按 data-table 单站点查即唯一。 */
    for (const c of HR_CASES) {
      test(`HR ${c.tid} 三处计数相等且列头与值格同缘 (${skin})`, async ({ page }) => {
        collectRuntimeErrors(page);
        await openHrModal(page, skin);
        if (c.openDiag) {
          await page.locator('.hr-full-modal details.hrs-diag summary', { hasText: '排障视图' }).click();
        }
        const row = page.locator(`.hr-full-modal .group-row[data-table="${c.tid}"]`).first();
        await expect(row, `HR ${c.tid} 行集不可见(载荷/导航断? 同步本 spec)`).toBeVisible({ timeout: 10_000 });

        const probe = await page.evaluate((tid) => {
          const head = document.querySelector('.hr-full-modal .group-head[data-table="' + tid + '"]');
          const rowEl = document.querySelector('.hr-full-modal .group-row[data-table="' + tid + '"]');
          if (!head || !rowEl) return null;
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

        expect(probe, `未找到 HR ${c.tid} 的表头或行(表格面改名/未挂载? 同步本 spec)`).not.toBeNull();
        expect(probe.tracks, '网格轨道数 == 列数').toBe(c.cols);
        expect(probe.headCells, '列头格数 == 列数').toBe(c.cols);
        expect(probe.cells, '数据行子格数 == 列数').toBe(c.cols);
        expect(probe.leftDiff, '列头与值格左缘对齐(±1px)').toEqual([]);
        expect(probe.alignDiff, '列头与值格 text-align 一致').toEqual([]);
      });
    }
  });
}
