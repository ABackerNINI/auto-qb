/* W5 验收量具(计划 26-10-13-0811 §08 #5/#7/#8 + 26-10-14 四复查 #9)—— 四条症状各一条真浏览器量化:
 *   #5 速度实时(症状 5): 注入两轮相邻 peers 响应, 速度格文本变化且 DOM 节点身份不变
 *      —— 「写字段, 不是重建」(L5): keyed 补丁的原节点续用, 重建则 data-live-probe 失踪。
 *   #8 勾选不跳动(症状 8, 变体 11): 连续勾选三行, 行容器 offsetTop 累计偏移为 0、行数
 *      不变、行 DOM 身份不变 —— 勾选态进驱动数据(反应式), 不走 anchTouch 换代重挂。
 *   #7 按钮不占列(症状 7, 变体 11): 交互件锁定不可被列管理删除 —— 2026-10-14 复查后交互件
 *      已收编进 name 格(ck 勾选列 locked / name 列 locked), 右键隐藏菜单不渲染其勾选框
 *      (columns.js:458 双保险) —— 折叠钮与徽章随 name 格走, 删除 name = 废掉两个交互件.
 *      !2026-10-14 二次复查: ck 勾选框亦收进 name 格(ck 列删除, 拖宽随 name 列), 三交互件
 *      随 name 格走, 删除 name = 废掉三个交互件.
 *   #9 数据回路点击不跳动(26-10-14 四复查「点击跳动, 持续 0.x 秒后回位」, 变体 10/11):
 *      优先级徽章点击走 POST→补拉→整帧换帧; 行选中点击走 rerender 整帧换帧。**跳动是瞬态**
 *      (root cause: 抽屉表格体是长生命周期元素, anchFill 每帧摘插锚 = CSS 入场动画重播,
 *      整表 translateY(4px) 后 ~0.22s 缓回) —— 点前/点后各拍一张的比对式量具(如 #8 的
 *      before/after offsetTop)必然错过, 必须**逐帧采样**(rAF + 4ms 双路)覆盖整个
 *      数据回路窗口, 取全程最大偏移。atlas/console 双皮肤都中过招(prism 无该动画规则)。
 *   #10/#11 千级止血量具(计划 26-11-02-0351 W1): 千文件桩下勾选单行/数据回路补拉,
 *      longtask PerformanceObserver 钉主线程无回归量级(>=100ms)长任务(记忆化跳渲 + 廉价 sig +
 *      O(D×F) 消除), 失效面(_cls 染色/三态框)与未变行身份同步盯住。
 *   #12 千级窗口化量具(计划 26-11-02-0351 W3): 千文件桩下 content 变体挂 window:"drawerContent"
 *      —— 常驻 DOM 行数 << 数据行数(渲染基数收口)/ 滚到底末行可见(占位撑总高)/ 键盘 ↓ 跨窗
 *      先滚动后回焦(dtWinKbd 前缀和换算)。
 * 数据口径沿用 drawer-peers-variant-tables / drawer-content-variant-tables 的桩. */
import { test, expect } from '@playwright/test';
import { installRuntimeErrorGuard, collectRuntimeErrors } from './lib/errors.mjs';
import { baseUrl, SKINS } from './harness.mjs';

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

/* #9 专用: 40 文件 6 目录的高树 —— 表格必须高到可滚动(滚动位非 0 时, 内容塌陷/clamp/
 * 动画位移才会在采样里现形); 目录/文件交错, nth(20)/nth(21) 落在视口中部(点击不触发
 * Playwright 自动滚动污染基线)。 */
function makeFilesTall(n = 40) {
  const out = [];
  for (let i = 0; i < n; i++) {
    out.push({
      name: `S${1 + (i % 6)}/sub${i % 3}/ep${String(i).padStart(2, '0')} - file.mkv`,
      size: 1_000_000 + i * 777,
      progress: (i % 5) / 5,
      priority: [1, 6, 0, 1, 7][i % 5],
      availability: i % 4 === 0 ? undefined : 0.3 + (i % 7) / 10,
    });
  }
  return out;
}

/* W1(#10/#11)专用: 千文件桩 —— 单层目录 D 下 1000 个文件(1 目录行 + 1000 文件行)。
 * file0 priority 固定 6(徽章「高」): #11 点徽章走 PRIO_CYCLE 6→7, 补拉后断言「最高」。 */
function makeFilesK(n = 1000) {
  const out = [];
  for (let i = 0; i < n; i++) {
    out.push({
      name: `D/f${String(i).padStart(4, '0')} - file.mkv`,
      size: 1_000_000 + i * 999,
      progress: (i % 4) / 4,
      priority: i === 0 ? 6 : 1,
      availability: i % 5 === 0 ? undefined : 0.3 + (i % 7) / 10,
    });
  }
  return out;
}

/**
 * 等窗口化表格渲染窗落定: 连续三拍采样(节拍 = expect.poll 默认间隔, 静默跨度 >= 350ms)行键集
 * 一致 —— 滚动触发的合帧 rAF + 窗口重渲没有单一 DOM 终点, 旧 120/400ms 睡等「赌重算跑完」的
 * 显式化; 三拍口径防「重渲尚未开始就判稳」的提前通过。
 * @param {import('@playwright/test').Page} page
 * @param {import('@playwright/test').Locator} anchor 表格锚
 */
const awaitWindowSettled = (page, anchor, timeout = 5_000) => {
  const seq = [];
  return expect.poll(async () => {
    seq.push(await anchor.evaluate((a) => Array.from(a.querySelectorAll('.group-row[data-dt-key]'))
      .map((r) => r.getAttribute('data-dt-key')).join('|')));
    if (seq.length > 3) seq.shift();
    return seq.length === 3 && seq[0] !== '' && seq[0] === seq[1] && seq[1] === seq[2];
  }, { timeout }).toBe(true);
};

/**
 * 量具观察窗(测量程序参数, 非条件等待): #9 的逐帧采样量具必须覆盖「点击 → 数据回路 → 换帧」
 * 整个窗口取全程最大偏移(300/1600ms); #10/#11 的 mut/longtask 预算按「点击后固定窗内计数」
 * 定版(500/800ms) —— 窗内计数含 patch 本身, 窗时长是量具口径的一部分, 等待即测量程序本身。
 * 属 e2e setTimeout 审计的「业务/量具延迟语义, 保留并注释」类, 走 Node 侧 setTimeout 不占页面时钟。
 * @param {number} ms
 */
const measureWindow = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

/* W1 长任务预算的量级线(2026-11-13 W5 修, issue 26-11-13-0519): W4 收紧的 count==0 只在静机
 * 成立 —— 44.8m 全量负载轮实测 1 个 63ms GC/调度毛刺混进测量窗即假红(prism 孪生同轮 0/0,
 * 静机单跑 14/14)。口径改「无回归量级长任务」: 阈值 100ms 锚三处 —— (1)负载噪声实测上限 63ms
 * (Chromium GC 停顿常规 <100ms); (2)回归面 = W1 千行 keyed diff 残留(W1 长任务预算 <150ms,
 * 同 longtask 口径; W6a 旧全路径同面可见延迟 171-174ms 含 100ms 回执延迟, 非 longtask 口径,
 * 仅旁证旧路径慢一个量级); (3)长任务定义界(>50ms)的 2 倍。≥100ms 即红仍钉住千行重写回潮;
 * 行侧零重建的主守阵是 mut 预算(DOM 记录数与 CPU 负载无关), longtask 预算只作计时伴证。
 * 同形口径先例: perf.spec.mjs W5「同屏交互无灾难冻结帧(实测 max <500ms)」。 */
const LT_REGRESSION_MS = 100;

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
      await page.goto(`${baseUrl()}/${skin}/`, { waitUntil: 'domcontentloaded' });
      await expect(page.locator('#app')).not.toHaveAttribute('v-cloak', { timeout: 15_000 });
      await expect(page.locator('.group-row').first()).toBeVisible({ timeout: 30_000 });

      const drawer = await openTorrentDrawer(page);
      await drawer.locator('.drawer-tabs button', { hasText: '用户' }).click();
      const firstRow = drawer.locator('.group-row[data-table="drawerPeerV07"]').first();
      await expect(firstRow).toBeVisible({ timeout: 10_000 });

      // 2026-10-14: 经典对端表(未排序, 首行 = 桩的第 0 个对端)已删 —— 改钉缺省变体 07。
      // 07 默认按 addr **升序**(2026-10-18 用户报障改口径, 原 upspeed 降序), 桩 ip 首段恒
      // 10 → 数值序 = i 升序, 第 0 个对端(10.0.0.0)就是首行 —— 探针按地址定位该行,
      // 与首行重合; 桩只给它换 dl_speed, 两轮输入必不同(否则探测格两轮相同 = 测假)。
      const row0 = drawer.locator('.group-row[data-table="drawerPeerV07"]', { hasText: '10.0.0.0:30000' }).first();
      await expect(row0, '第 0 个对端(10.0.0.0)必须在 07 表里').toBeVisible({ timeout: 10_000 });
      const text0 = await row0.evaluate((row) => {
        const cell = row.querySelector('.dt07-spd.d');
        cell.setAttribute('data-live-probe', '1');
        return cell.textContent.trim();
      });
      expect(text0, '首轮速度文案非空且非占位').not.toBe('—');

      // 第二轮: 后注册路由优先生效, 5s 轮询下一拍拿到 B 值
      await page.route('**/api/torrents/*/peers', async (route) => {
        fulfillAt = Date.now();
        await route.fulfill({ contentType: 'application/json', body: JSON.stringify({ peers: makePeers(DL_B) }) });
      });

      // 轮询最快 5s 一拍: poll 等文本变化(上限 8s, 节拍 40ms 保住「响应落地→格子更新」量程粒度),
      // 落地时刻已由 fulfillAt 记录
      let changedAt = -1;
      await expect.poll(async () => {
        const txt = await row0.evaluate((row) => { const c = row.querySelector('.dt07-spd.d'); return c && c.textContent.trim(); });
        if (txt && txt !== text0) {
          changedAt = Date.now();
          return true;
        }
        return false;
      }, { timeout: 8_000, intervals: [40] }).toBe(true);
      expect(changedAt, '两轮注入后 dlspeed 格文案变化(速度实时更新)').toBeGreaterThan(0);
      expect(changedAt - fulfillAt, `响应落地→格子更新 <500ms(实测 ${changedAt - fulfillAt}ms)`).toBeLessThan(500);
      await expect(row0.locator('[data-live-probe="1"]'),
        '速度更新后仍是同一 DOM 节点(行未重建 = L5 写字段)').toBeAttached();
    });

    test(`#8 勾选不跳动: 连续勾选三行, 行偏移/行数/行身份零变化 @fast (${skin})`, async ({ page }) => {
      collectRuntimeErrors(page);
      await page.setViewportSize(WIDE);
      await page.route('**/api/torrents/*/files', (route) =>
        route.fulfill({ contentType: 'application/json', body: JSON.stringify(makeFiles()) }));
      await page.addInitScript(() =>
        localStorage.setItem('autoqb.ui.drawerTpl', JSON.stringify({ content: '11' })));
      await page.goto(`${baseUrl()}/${skin}/`, { waitUntil: 'domcontentloaded' });
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
        // 旧 80ms 睡等「等一帧渲染」→ 等勾选态上屏(渲染产物的显式等待; 换代重挂若有, 终态快照即暴露)
        await expect(boxes.nth(i), `第 ${i + 1} 个勾选框勾选态上屏`).toBeChecked();
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

    test(`#7 按钮不占列(交互件收编 name 格): name 列 locked 必显, 三件交互格子仍在 @fast (${skin})`, async ({ page }) => {
      collectRuntimeErrors(page);
      await page.setViewportSize(WIDE);
      await page.route('**/api/torrents/*/files', (route) =>
        route.fulfill({ contentType: 'application/json', body: JSON.stringify(makeFiles()) }));
      await page.addInitScript(() =>
        localStorage.setItem('autoqb.ui.drawerTpl', JSON.stringify({ content: '11' })));
      await page.goto(`${baseUrl()}/${skin}/`, { waitUntil: 'domcontentloaded' });
      await expect(page.locator('#app')).not.toHaveAttribute('v-cloak', { timeout: 15_000 });
      await expect(page.locator('.group-row').first()).toBeVisible({ timeout: 30_000 });
      const drawer = await openTorrentDrawer(page);
      await drawer.locator('.drawer-tabs button', { hasText: '内容' }).click();
      const anchor = drawer.locator('[data-dt-table-anchor="drawerContentV11"]');
      const head = anchor.locator('.group-head[data-table="drawerContentV11"]');
      await expect(head).toBeVisible({ timeout: 10_000 });

      // 2026-10-14 复查修法(26-10-14-0136 §02): 优先级徽章不再是独立列 —— 收编进 name 格
      // (margin-left:auto 右对齐)。「按钮不可被列管理删除」的 L4 口径随之改挂 name 列:
      // 右键「名称」列头 → 隐藏项为 muted「必显」, 点击走 headMenuHide 的 locked 分支
      // (只 toast 不隐藏, menu.js); ck 列同口径(勾选三态同在格内)。
      const nameHeader = head.locator('.h-cell', { hasText: '名称' });
      await nameHeader.click({ button: 'right' });
      const menu = page.locator('.ctx-menu');
      await expect(menu).toBeVisible({ timeout: 3_000 });
      const hideItem = menu.locator('.ctx-item', { hasText: '名称' }).first();
      await expect(hideItem, 'name 列的隐藏项标必显(L4: 折叠钮/徽章在格内, 隐藏即废)').toHaveClass(/muted/);
      await hideItem.click(); // locked: headMenuHide 只 toast 不隐藏, 菜单自收
      await expect(anchor.locator('.dt11-pbadge').first(), '点必显项后徽章仍在(name 格内)').toBeAttached();
      // !勿用 Esc 收菜单 —— lifecycle 的 Esc 链优先关抽屉(drawerVisible 分支先于 headMenu),
      // 会把面板整个关掉。headMenuHide 已自收菜单, 这里直接做终态断言。

      // 终态不变量: 三类交互件全部还在(勾选框/折叠钮/徽章 = 收进 name 格内, 2026-10-14 二次复查)
      await expect(anchor.locator('.dt11-n .dt11-ck').first(), '勾选框在 name 格内(不占列, 拖宽随 name)').toBeAttached();
      await expect(anchor.locator('.dt11-n .dt11-tgl').first(), '折叠钮在 name 格内(随缩进 = 层级)').toBeAttached();
      await expect(anchor.locator('.dt11-n .dt11-pbadge').first(), '徽章在 name 格内(不占列)').toBeAttached();
    });

    /* #9 数据回路点击不跳动(26-10-14 四复查「点击跳动, 持续 0.x 秒后回到原位」) ——
     * 根因(探针实锤): 抽屉表格体(.group-table/.group-head)是**长生命周期元素**(桥 Teleport
     * + 锚保活), anchFill 每次整帧换帧把锚**摘下再插回** slot 位 ⇒ CSS 动画重播(元素移除再
     * 插入 = 动画重启) ⇒ atlas/console 的 page-in 入场动画(translateY(4px) + 淡入, .22s)每
     * 次点击重渲都整表跳 4px 再缓回。修法 = 两皮肤 views.css 加 .drawer 作用域 animation:none
     * (主列表表格随视图真重建才播, 不受影响)。**量具口径**: 跳动是瞬态且自回位, before/after
     * 比对式量具(#8 那种)必然错过 —— 必须逐帧采样(rAF + 4ms 双路)覆盖整个点击窗口取全程最大
     * 偏移; 这正是前三轮量具全绿而用户仍报跳动的盲区(只测勾选这类纯前端态, 没测数据回路)。
     * 桩口径: POST 走**真实端点**(harness 命令泵回执 ok) —— 桩掉 POST 会断 waitCmd 链
     * (无回执⇒不补拉⇒不换帧, 量具空转); GET 在 POST 后翻转 file0 优先级(模拟真后端数据
     * 变化, 否则 sig 不变跳过换帧)。 */
    test(`#9 数据回路点击不跳动: 逐帧采样下行/scrollTop 全程零偏移 @fast (${skin})`, async ({ page }) => {
      collectRuntimeErrors(page);
      await page.setViewportSize(WIDE);
      let posted = false;
      const base = makeFilesTall();
      page.on('request', (r) => { if (r.url().includes('/files/priority')) posted = true; });
      await page.route('**/api/torrents/*/files', (route) => {
        const files = posted ? base.map((f, i) => (i === 0 ? { ...f, priority: 7 } : f)) : base;
        route.fulfill({ contentType: 'application/json', body: JSON.stringify(files) });
      });
      await page.addInitScript(() =>
        localStorage.setItem('autoqb.ui.drawerTpl', JSON.stringify({ content: '10' })));
      await page.goto(`${baseUrl()}/${skin}/`, { waitUntil: 'domcontentloaded' });
      await expect(page.locator('#app')).not.toHaveAttribute('v-cloak', { timeout: 15_000 });
      await expect(page.locator('.group-row').first()).toBeVisible({ timeout: 30_000 });
      const drawer = await openTorrentDrawer(page);
      await drawer.locator('.drawer-tabs button', { hasText: '内容' }).click();
      const anchor = drawer.locator('[data-dt-table-anchor="drawerContentV10"]');
      await expect(anchor.locator('.group-row').first()).toBeVisible({ timeout: 10_000 });

      // 滚到中部: 滚动位非 0 —— 内容塌陷→clamp 或动画位移都会在采样里现形
      await drawer.locator('.drawer-body').evaluate((el) => {
        el.scrollTop = Math.round((el.scrollHeight - el.clientHeight) * 0.45);
      });
      await awaitWindowSettled(page, anchor);  // 旧 120ms 睡等: 滚动触发的窗口重渲落定的显式化

      // 逐帧采样器(rAF 每帧 + 4ms 定时双路): 钉两行(靠顶部 + 中部)的视口 rect 与 scrollTop
      await page.evaluate(() => {
        const sc = document.querySelector('.drawer-body');
        const P = (window.__jumpProbe = { t0: performance.now(), s: [] });
        const keys = Array.from(sc.querySelectorAll('.group-row[data-dt-key]'))
          .map((r) => r.getAttribute('data-dt-key'));
        const kTop = keys[2], kMid = keys[Math.floor(keys.length / 2)];
        const rectOf = (k) => {
          const el = sc.querySelector(`.group-row[data-dt-key="${CSS.escape(k)}"]`);
          return el ? el.getBoundingClientRect().top : null;
        };
        const sample = () => P.s.push({ st: sc.scrollTop, rt: rectOf(kTop), rm: rectOf(kMid) });
        const iv = setInterval(sample, 4);
        const raf = () => { sample(); P.raf = requestAnimationFrame(raf); };
        requestAnimationFrame(raf);
        P.stop = () => { clearInterval(iv); cancelAnimationFrame(P.raf); };
      });
      await expect.poll(() => page.evaluate(() => window.__jumpProbe.s.length),
        { message: '探针攒够基线采样帧(与旧 80ms 睡等同量级: 4ms 间隔 x 20)' })
        .toBeGreaterThan(20); // 攒基线采样

      // 点击 1: 优先级徽章 → 小菜单 → 最高(POST files/priority → 静默补拉 → 整帧换帧)
      const badge = anchor.locator('.group-row').nth(21).locator('.dt10-pbadge');
      await expect(badge, '中部文件行徽章在视口内(点击不触发自动滚动)').toBeVisible();
      await badge.click();
      const menu = page.locator('.ctx-menu', { hasText: '最高' });
      await expect(menu).toBeVisible({ timeout: 3_000 });
      await menu.locator('.ctx-item', { hasText: '最高' }).click();
      await measureWindow(300); // 数据回路窗口内持续采样(量具观察窗, 见 measureWindow 注)

      // 点击 2: 行选中(rerender 整帧换帧 + 右详情变化)
      await anchor.locator('.group-row').nth(22).click();
      await measureWindow(1600); // 覆盖换帧后的全部余波(量具观察窗, 见 measureWindow 注)

      const dev = await page.evaluate(() => {
        window.__jumpProbe.stop();
        const s = window.__jumpProbe.s;
        const b = s[0];
        return {
          st: Math.max(...s.map((x) => Math.abs(x.st - b.st))),
          rt: Math.max(...s.map((x) => (x.rt == null ? 0 : Math.abs(x.rt - b.rt)))),
          rm: Math.max(...s.map((x) => (x.rm == null ? 0 : Math.abs(x.rm - b.rm)))),
          n: s.length,
        };
      });
      expect(dev.n, '采样覆盖整个点击窗口(瞬态只有细间隔能抓住)').toBeGreaterThan(200);
      expect(dev.rt, `数据回路+选中点击: 靠顶行全程零偏移(实测 ${dev.rt}px)`).toBeLessThanOrEqual(0.5);
      expect(dev.rm, `数据回路+选中点击: 中部行全程零偏移(实测 ${dev.rm}px)`).toBeLessThanOrEqual(0.5);
      expect(dev.st, `数据回路+选中点击: scrollTop 全程零偏移(实测 ${dev.st}px)`).toBeLessThanOrEqual(0.5);
    });

    /* W1(计划 26-11-02-0351)止血量具: 千级文件列表两态 ——
     *   #10 勾选单行: 记忆化 + O(D×F) 消除后行侧零重建(锚内 MutationObserver 记录数钉住
     *       —— 旧实现 = 1000+ 行全量重写), 长任务(PerformanceObserver longtask, 口径同
     *       perf.spec.mjs 既有埋点)钉回归下界。W1 时预算 ≤1/<150ms(残留 = 桥 v-for 千行
     *       keyed diff); W4 A/B 收紧为 0(W3 收窗后基数 ~47 行, 2026-11-02 实测双皮 0);
     *       2026-11-13 W5 改量级口径 >=100ms(W4 的 count==0 在负载轮假红, 锚点见
     *       LT_REGRESSION_MS 注释)。
     *       失效面同钉: 勾选行 _cls 翻 is-chk、目录行三态框 indeterminate 跟进(漏键 =
     *       染色停旧值, node 电池同判据)。
     *   #11 数据回路: 徽章点击 → POST → 静默补拉(仅一个文件 priority 变), 廉价 sig 不再
     *       全量 JSON.stringify、记忆化只重装配脏行 —— 长任务下界同 #10 收紧为 0 + 未变行
     *       DOM 身份与徽章值不抖(首行身份戳沿用 #8 口径)。
     *   探针 settle 判据(W4 修): 收窗(占位件在场)完成后才装探针, 否则量进收窗本身。 */
    test(`#10 千文件勾选单行: 行侧零重建 + 长任务预算内 + 勾选链染色即时翻转 @fast (${skin})`, async ({ page }) => {
      test.setTimeout(60_000); // 千行桩首渲 + 皮肤循环, 30s 默认太紧
      collectRuntimeErrors(page);
      await page.setViewportSize(WIDE);
      await page.route('**/api/torrents/*/files', (route) =>
        route.fulfill({ contentType: 'application/json', body: JSON.stringify(makeFilesK()) }));
      await page.addInitScript(() =>
        localStorage.setItem('autoqb.ui.drawerTpl', JSON.stringify({ content: '11' })));
      await page.goto(`${baseUrl()}/${skin}/`, { waitUntil: 'domcontentloaded' });
      await expect(page.locator('#app')).not.toHaveAttribute('v-cloak', { timeout: 15_000 });
      await expect(page.locator('.group-row').first()).toBeVisible({ timeout: 30_000 });
      const drawer = await openTorrentDrawer(page);
      await drawer.locator('.drawer-tabs button', { hasText: '内容' }).click();
      const anchor = drawer.locator('[data-dt-table-anchor="drawerContentV11"]');
      await expect(anchor.locator('.group-row[data-table="drawerContentV11"]').first()).toBeVisible({ timeout: 10_000 });
      await measureWindow(400); // 首渲 settle + 启动噪声吸收窗(千行挂载自身的成本不计入判据窗口)
      // W4(计划 26-11-02-0351)修测量口径: W3 窗口化后首渲是「全量量高 → 收窗」两拍, 固定
      // 400ms 等不到收窗完成 —— 探针把收窗(摘 ~950 行, mut 实测 957/961)算进交互窗, 预算
      // 断言量错对象恒红(2026-11-02 实测取证)。对齐 #12 的 settle 判据: 占位件在场 = 收窗完成,
      // 之后的交互量测才是「勾选单行」本身。
      await expect(anchor.locator('.row-pad').first(), '窗口化收窗完成(占位件在场 = 量齐后已收窗)').toBeAttached({ timeout: 10_000 });

      // 探针在 settle 后安装 —— 只量「勾选单行」这一次交互: longtask + 锚内 DOM 变更
      await page.evaluate(() => {
        window.__lt = [];
        window.__mut = 0;
        if (window.__po) window.__po.disconnect();
        window.__po = new PerformanceObserver((l) => {
          for (const e of l.getEntries()) window.__lt.push(Math.round(e.duration));
        });
        window.__po.observe({ entryTypes: ['longtask'] });
        new MutationObserver((ms) => { window.__mut += ms.length; })
          .observe(document.querySelector('[data-dt-table-anchor="drawerContentV11"]'),
            { attributes: true, childList: true, subtree: true });
      });

      const firstCk = anchor.locator('.dt11-ck[data-act="ck"]').first();
      await firstCk.click();
      await measureWindow(500); // 交互 + patch 全部余波落进观察窗(探针测量窗, 预算按窗内计数定版)

      const lt = await page.evaluate(() => window.__lt || []);
      const mut = await page.evaluate(() => window.__mut || 0);
      const ltSum = lt.reduce((a, b) => a + b, 0);
      // W4 A/B 收紧(计划 26-11-02-0351 §W4): W1 时预算 ≤1/<150ms, 钉的残留面是「桥 v-for
      // 千行 keyed diff」; W3 收窗后渲染基数 ~47 行, 该面随基数消失。2026-11-02 实测(收窗
      // settle 判据对齐 #12 后)双皮 0 longtask / 0ms —— 回归下界收紧为 0。
      // W5 改道(2026-11-13, issue 26-11-13-0519): count==0 在 44.8m 全量负载轮被 1 个 63ms
      // GC/调度毛刺打穿(prism 孪生同轮 0/0, 静机 14/14) —— 静机取证下的收紧把环境噪声当回归。
      // 改量级口径 LT_REGRESSION_MS(锚点与先例见其注释): <100ms 毛刺不计, >=100ms 即红。
      expect(Math.max(0, ...lt), `勾选单行无>=${LT_REGRESSION_MS}ms长任务(实测 ${lt.join('/') || '无'}; ` +
        `W4 A/B 收紧 count==0 负载轮假红改量级口径)`).toBeLessThan(LT_REGRESSION_MS);
      expect(mut, `锚内 DOM 变更记录 ≤8(实测 ${mut}; 行侧零重建 —— 旧实现 = 1000+ 行全量重写)`).toBeLessThanOrEqual(8);
      console.log(`      [#10 ${skin}] 勾选单行: longtask ${lt.join('/') || '无'}(合 ${ltSum}ms), 锚内 mut ${mut}`);
      // 失效面在真浏览器成立: 勾选行 _cls 翻 is-chk(rowCls="_cls" 绑行容器), 目录行三态跟进
      const chkRow = anchor.locator('.group-row.is-chk[data-table="drawerContentV11"]');
      await expect(chkRow, '勾选行容器拿到 is-chk 染色').toHaveCount(1);
      await expect(chkRow.locator('.dt11-ck[data-act="ck"]')).toBeChecked();
      const dirCk = anchor.locator('.group-row.dir .dt11-ck[data-act="dirck"]');
      await expect(dirCk, '目录行三态框进入 indeterminate(部分勾选)').toHaveJSProperty('indeterminate', true);
      await expect(dirCk).not.toBeChecked();
    });

    test(`#11 千文件数据回路: 补拉一文件变值预算内 + 未变行身份/徽章不抖 @fast (${skin})`, async ({ page }) => {
      test.setTimeout(60_000); // 千行桩首渲 + 补拉回路, 30s 默认太紧(时间预算, 非睡等)
      collectRuntimeErrors(page);
      await page.setViewportSize(WIDE);
      let posted = false;
      const base = makeFilesK();
      page.on('request', (r) => { if (r.url().includes('/files/priority')) posted = true; });
      await page.route('**/api/torrents/*/files', (route) => {
        // POST 后静默补拉: 只有 file0 priority 变(6→7, 徽章循环一档) —— 脏行 = file0, 目录聚合不变
        const files = posted ? base.map((f, i) => (i === 0 ? { ...f, priority: 7 } : f)) : base;
        route.fulfill({ contentType: 'application/json', body: JSON.stringify(files) });
      });
      await page.addInitScript(() =>
        localStorage.setItem('autoqb.ui.drawerTpl', JSON.stringify({ content: '11' })));
      await page.goto(`${baseUrl()}/${skin}/`, { waitUntil: 'domcontentloaded' });
      await expect(page.locator('#app')).not.toHaveAttribute('v-cloak', { timeout: 15_000 });
      await expect(page.locator('.group-row').first()).toBeVisible({ timeout: 30_000 });
      const drawer = await openTorrentDrawer(page);
      await drawer.locator('.drawer-tabs button', { hasText: '内容' }).click();
      const anchor = drawer.locator('[data-dt-table-anchor="drawerContentV11"]');
      await expect(anchor.locator('.group-row[data-table="drawerContentV11"]').first()).toBeVisible({ timeout: 10_000 });
      await measureWindow(400); // 首渲 settle + 启动噪声吸收窗(同 #10 口径)
      // W4 settle 判据同 #10(占位件在场 = 收窗完成), 探针别量进收窗本身(取证见 #10 注)
      await expect(anchor.locator('.row-pad').first(), '窗口化收窗完成(占位件在场)').toBeAttached({ timeout: 10_000 });

      // 脏行(file0)与未变参照行(file5)打身份戳; longtask + 锚内变更探针同 #10 口径
      await page.evaluate(() => {
        const a = document.querySelector('[data-dt-table-anchor="drawerContentV11"]');
        a.querySelector('.group-row[data-dt-key="D/f0000 - file.mkv"]').setAttribute('data-row-probe', 'f0');
        a.querySelector('.group-row[data-dt-key="D/f0005 - file.mkv"]').setAttribute('data-row-probe', 'f5');
        window.__lt = [];
        window.__mut = 0;
        if (window.__po) window.__po.disconnect();
        window.__po = new PerformanceObserver((l) => {
          for (const e of l.getEntries()) window.__lt.push(Math.round(e.duration));
        });
        window.__po.observe({ entryTypes: ['longtask'] });
        new MutationObserver((ms) => { window.__mut += ms.length; })
          .observe(a, { attributes: true, childList: true, subtree: true });
      });

      // 点击 file0 优先级徽章(循环 6→7 一次真实提交) → waitCmd 回执 → 静默补拉 → 换帧
      const badge0 = anchor.locator('.group-row[data-dt-key="D/f0000 - file.mkv"] .dt11-pbadge');
      await badge0.click();
      await measureWindow(800); // 覆盖 POST→回执→补拉→换帧全程(探针测量窗, 预算按窗内计数定版)

      const lt = await page.evaluate(() => window.__lt || []);
      const mut = await page.evaluate(() => window.__mut || 0);
      const ltSum = lt.reduce((a, b) => a + b, 0);
      // W4 A/B 收紧(口径同 #10): W1 预算 ≤2/<200ms 钉的是「整包 JSON.stringify + 千行全量
      // 重装配」残留面; W3 收窗 + 廉价 sig 后该面消失, 2026-11-02 实测双皮 0 longtask / 0ms
      // (POST→补拉→换帧全程, settle 判据对齐 #12)→ 回归下界 0。
      // W5 改道同 #10(count==0 负载轮假红, issue 26-11-13-0519): 改量级口径 LT_REGRESSION_MS。
      expect(Math.max(0, ...lt), `数据回路无>=${LT_REGRESSION_MS}ms长任务(实测 ${lt.join('/') || '无'}; ` +
        `W4 A/B 收紧 count==0 负载轮假红改量级口径)`).toBeLessThan(LT_REGRESSION_MS);
      expect(mut, `锚内 DOM 变更记录 ≤16(实测 ${mut}; 记忆化只重装配脏行)`).toBeLessThanOrEqual(16);
      console.log(`      [#11 ${skin}] 数据回路: longtask ${lt.join('/') || '无'}(合 ${ltSum}ms), 锚内 mut ${mut}`);
      await expect(anchor.locator('[data-row-probe="f0"]'), '脏行 file0 DOM 身份保持(keyed 补丁)').toBeAttached();
      await expect(anchor.locator('[data-row-probe="f5"]'), '未变行 DOM 身份保持').toBeAttached();
      const f0Badge = await anchor.locator('[data-row-probe="f0"] .dt11-pbadge').textContent();
      expect(f0Badge.trim(), '脏行徽章随补拉新值翻转(最高)').toBe('最高');
      const f5Badge = await anchor.locator('[data-row-probe="f5"] .dt11-pbadge').textContent();
      expect(f5Badge.trim(), '未变行徽章值不抖(记忆化命中)').toBe('正常');
    });

    /* W3(计划 26-11-02-0351)窗口化量具: 千文件桩下 content 变体 11 挂 window:"drawerContent"
     * (滚动源 = .drawer-body 容器型描述符, 桥切片消费)。三判据:
     *   1. 常驻 DOM 行数 << 数据行数(1000 文件 + 目录行) —— 渲染基数收口(千行 keyed diff 的
     *      残留 longtask 面随基数消失, #10/#11 的预算断言为伴证);
     *   2. 占位撑住总高: 滚到底末行进窗且可见(滚动条长度与「滚到底」契约, BUG-1 家族);
     *   3. 键盘 ↓ 跨窗: 焦点移出已渲染块端沿时先滚动后回焦(dtWinKbd 前缀和换算), 焦点行在
     *      DOM 且可见 —— 回焦目标必须在重渲后的窗内(kbd-cursor-collapse-dangling 家族)。 */
    test(`#12 千文件窗口化: 常驻 DOM 行数 << 数据行数 + 滚到底不塌陷 + 键盘跨窗回焦 @fast (${skin})`, async ({ page }) => {
      test.setTimeout(60_000); // 千行桩首渲 + 滚动/键盘遍历, 30s 默认太紧(时间预算, 非睡等)
      collectRuntimeErrors(page);
      await page.setViewportSize(WIDE);
      await page.route('**/api/torrents/*/files', (route) =>
        route.fulfill({ contentType: 'application/json', body: JSON.stringify(makeFilesK()) }));
      await page.addInitScript(() =>
        localStorage.setItem('autoqb.ui.drawerTpl', JSON.stringify({ content: '11' })));
      await page.goto(`${baseUrl()}/${skin}/`, { waitUntil: 'domcontentloaded' });
      await expect(page.locator('#app')).not.toHaveAttribute('v-cloak', { timeout: 15_000 });
      await expect(page.locator('.group-row').first()).toBeVisible({ timeout: 30_000 });
      const drawer = await openTorrentDrawer(page);
      await drawer.locator('.drawer-tabs button', { hasText: '内容' }).click();
      const anchor = drawer.locator('[data-dt-table-anchor="drawerContentV11"]');
      await expect(anchor.locator('.group-row[data-table="drawerContentV11"]').first()).toBeVisible({ timeout: 10_000 });
      // 占位件在场 = 窗口化已激活(全量首轮量行高 → 收窗, 量齐前不给占位)
      await expect(anchor.locator('.row-pad').first(), '窗口化占位件在场(量齐后收窗)').toBeAttached({ timeout: 10_000 });

      // 1. 常驻 DOM 行数 << 数据行数(视口窗 + OVERSCAN 10×2, 300 是回归上界不是刻度)
      const domRows = await anchor.locator('.group-row[data-table="drawerContentV11"]').count();
      expect(domRows, `常驻 DOM 行数远小于数据行数(实测 ${domRows}, 数据 1001)`).toBeLessThan(300);

      // 2. 滚到底: 末行进窗且可见(占位撑总高, 滚到底够得着)
      const body = drawer.locator('.drawer-body');
      await body.evaluate((el) => { el.scrollTop = el.scrollHeight; });
      await expect(anchor.locator('.group-row[data-dt-key="D/f0999 - file.mkv"]'),
        '滚到底末行进窗且可见(占位总高 == 全量渲染高度)').toBeVisible({ timeout: 10_000 });

      // 3. 键盘跨窗: 回顶, 焦点落首行, 连按 ↓ 越过窗底沿 —— 目标行先被滚进窗再回焦
      await body.evaluate((el) => { el.scrollTop = 0; });
      await awaitWindowSettled(page, anchor);  // 旧 400ms 睡等: 窗口重算(合帧 rAF + 重渲)落定的显式化
      await anchor.locator('.group-row[data-dt-key="D/f0000 - file.mkv"]').focus();
      const focusedKey = () => page.evaluate(() => {
        const el = document.activeElement;
        const row = el && el.closest ? el.closest('[data-dt-key]') : null;
        return row ? row.getAttribute('data-dt-key') : '';
      });
      let prevKey = await focusedKey();
      for (let i = 0; i < 80; i++) {
        await page.keyboard.press('ArrowDown');
        // 旧 30ms 睡等「让每拍按键的滚动+回焦处理完」→ poll 等焦点行实际前进到新行(逐拍收敛)
        await expect.poll(async () => {
          const k = await focusedKey();
          return k && k !== prevKey ? k : '';
        }, { timeout: 5_000, intervals: [15] }).not.toBe('');
        prevKey = await focusedKey();
      }
      const fk = await page.evaluate(() => {
        const el = document.activeElement;
        const row = el && el.closest ? el.closest('[data-dt-key]') : null;
        return row ? row.getAttribute('data-dt-key') : '';
      });
      const m = /f(\d{4})/.exec(fk || '');
      const idx = m ? Number(m[1]) : -1;
      expect(idx, `连按 80 次 ↓ 后焦点行已越过初始窗底沿(实测 ${fk})`).toBeGreaterThanOrEqual(60);
      expect(idx, `焦点行仍在数据范围内且未丢焦(实测 ${fk})`).toBeLessThanOrEqual(80);
      await expect(anchor.locator(`.group-row[data-dt-key="${fk}"]`),
        '跨窗回焦的焦点行就在已渲染窗内且可见').toBeVisible();
    });
  });
}
