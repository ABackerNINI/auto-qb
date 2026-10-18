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
 *      before/after offsetTop)必然错过, 必须**逐帧采样**(rAF + 4ms 定时双路)覆盖整个
 *      数据回路窗口, 取全程最大偏移。atlas/console 双皮肤都中过招(prism 无该动画规则)。
 * 数据口径沿用 drawer-peers-variant-tables / drawer-content-variant-tables 的桩. */
import { test, expect } from '@playwright/test';
import { installRuntimeErrorGuard, collectRuntimeErrors } from './lib/errors.mjs';
import { BASE_URL, SKINS } from './harness.mjs';

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
      await page.goto(`${BASE_URL}/${skin}/`, { waitUntil: 'domcontentloaded' });
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

      // 轮询最快 5s 一拍: 等文本变化(上限 8s), 落地时刻已由 fulfillAt 记录
      const changedAt = await (async () => {
        const t0 = Date.now();
        for (;;) {
          const txt = await row0.evaluate((row) => { const c = row.querySelector('.dt07-spd.d'); return c && c.textContent.trim(); });
          if (txt && txt !== text0) return Date.now();
          if (Date.now() - t0 > 8_000) return -1;
          await page.waitForTimeout(40);
        }
      })();
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
      await page.goto(`${BASE_URL}/${skin}/`, { waitUntil: 'domcontentloaded' });
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
        await page.waitForTimeout(80); // 等一帧渲染(换代重挂若有, 此处即暴露)
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
      await page.goto(`${BASE_URL}/${skin}/`, { waitUntil: 'domcontentloaded' });
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
      await page.goto(`${BASE_URL}/${skin}/`, { waitUntil: 'domcontentloaded' });
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
      await page.waitForTimeout(120);

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
      await page.waitForTimeout(80); // 攒基线采样

      // 点击①: 优先级徽章 → 小菜单 → 最高(POST files/priority → 静默补拉 → 整帧换帧)
      const badge = anchor.locator('.group-row').nth(21).locator('.dt10-pbadge');
      await expect(badge, '中部文件行徽章在视口内(点击不触发自动滚动)').toBeVisible();
      await badge.click();
      const menu = page.locator('.ctx-menu', { hasText: '最高' });
      await expect(menu).toBeVisible({ timeout: 3_000 });
      await menu.locator('.ctx-item', { hasText: '最高' }).click();
      await page.waitForTimeout(300); // 数据回路窗口内持续采样

      // 点击②: 行选中(rerender 整帧换帧 + 右详情变化)
      await anchor.locator('.group-row').nth(22).click();
      await page.waitForTimeout(1600); // 覆盖换帧后的全部余波

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
  });
}
