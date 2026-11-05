// @ts-check
import { expect, test } from '@playwright/test';
import { baseUrl, SKINS } from './harness.mjs';
import { collectRuntimeErrors, installRuntimeErrorGuard } from './lib/errors.mjs';
import { INST } from './lib/vm.mjs';

/**
 * W4 千级验收(抽屉内容表): 计划 26-11-02-0351 §W4 —— 千文件桩下 V10+V11 × prism/atlas
 * 全矩阵的窗口化守阵 + 实测数字采集(常驻 DOM 行数 / rowsFn 耗时 / 折叠长任务 / 滚动丢帧)。
 * 名字按计划指名 drawer-content-perf.spec.mjs(perf.spec.mjs 的主表轨不在此重复)。
 *
 * ── 与既有量具的分工(不重复断言) ──
 *  · dt-live-update.spec.mjs #10/#11(W1): V11 勾选单行/数据回路预算 + 勾选锚内 DOM 变更;
 *    #12(W3): V11 窗口化首渲/滚到底/键盘跨窗。V10 的同面判据由本 spec 补齐(W3 自查:
 *    V10 未进全矩阵), V11 在此只跑折叠/展开与丢帧这两个 #12 未覆盖的面。
 *  · 预算断言口径(perf-cadence「埋点必须有人消费 + A/B 不拍绝对 ms」): 长任务/耗时断言
 *    按 2026-11-02 千级实测收紧(数字写在断言消息里), 不是拍的; 滚动丢帧只钉
 *    「无灾难冻结」粗界(>250ms 的单帧), 精细数字进任务档案(基线切片统一建)。
 *  · W1「sig 不再全量 stringify」的直接证据 = #11 数据回路 0 longtask + rowsFn 直测耗时
 *    (本 spec K1); dt12:323 残留 stringify 属计划外缺陷池, 不在本矩阵内。
 *
 * 桩口径: page.route 拦 /api/torrents/(星号)/files(同 drawer-content-dt11-sticky), 千文件树 =
 * 单层目录 D 下 1000 文件(1 目录行 + 1000 文件行, 与 dt-live-update 的 makeFilesK 同源同构,
 * 折叠/展开重测判据要单目录覆盖全部数据行)。E2E_TORRENTS 不影响本 spec 判据(只关抽屉)。 */

const WIDE = { width: 2560, height: 1200 };

/**
 * 量具观察窗(测量程序参数, 非条件等待): 折叠交互后的 longtask/MutationObserver 计数预算
 * (≤1 个 / ≤64 条)是按「交互 + 窗口重算余波落进 ~500ms 观察窗」量得值标定的 —— 窗后读数,
 * 窗长即测量口径的一部分, 不能换成条件等待(等更久会让后台状态轮的 DOM 变更灌进计数)。
 * 走 Node 侧 setTimeout(不占页面时钟); e2e setTimeout 审计口径: 量具延迟语义, 保留并注释。
 * @param {number} ms
 */
const measureWindow = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

/* 千文件树桩: 单层目录 D 下 1000 个文件 —— 与 dt-live-update.spec.mjs makeFilesK 同构
 * (file0 priority 6 备用; 折叠判据只需要 path 前缀树)。 */
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

const VARIANTS = [
  { id: '10', wrap: '.dt10-wrap', table: 'drawerContentV10' },
  { id: '11', wrap: '.dt11-wrap', table: 'drawerContentV11' },
];

/* 占位件总高(.row-pad 上下两段之和): 窗口重测正确性的量具 —— 折叠后必须塌到个位行高,
 * 展开后必须回到千行量级(占位 == 全量渲染高度契约, BUG-1 家族)。 */
async function padHeight(page, table) {
  return page.evaluate((tid) => {
    const a = document.querySelector(`[data-dt-table-anchor="${tid}"]`);
    if (!a) return -1;
    let sum = 0;
    for (const p of a.querySelectorAll('.row-pad')) sum += p.getBoundingClientRect().height;
    return Math.round(sum);
  }, table);
}

for (const skin of SKINS) {
  for (const v of VARIANTS) {
    test.describe(`W4 千级验收 抽屉内容 dt${v.id} ${skin}`, () => {
      installRuntimeErrorGuard(test);

      /* 开抽屉 → 内容页签 → 等变体外壳 + 引擎桥行体 + 窗口化占位件点亮(量齐后收窗)。 */
      async function openK(page) {
        await page.setViewportSize(WIDE);
        await page.route('**/api/torrents/*/files', (route) =>
          route.fulfill({ contentType: 'application/json', body: JSON.stringify(makeFilesK()) }));
        await page.addInitScript((vid) =>
          localStorage.setItem('autoqb.ui.drawerTpl', JSON.stringify({ content: vid })), v.id);
        await page.goto(`${baseUrl()}/${skin}/`, { waitUntil: 'domcontentloaded' });
        await expect(page.locator('#app')).not.toHaveAttribute('v-cloak', { timeout: 15_000 });
        await expect(page.locator('.group-row').first()).toBeVisible({ timeout: 30_000 });
        await page.click('nav.tabs [data-view="torrents"]');
        await expect(page.locator('.torrent-row').first()).toBeVisible({ timeout: 15_000 });
        await page.dblclick('.torrent-row >> nth=0', { force: true });
        const drawer = page.locator('.drawer-dock > .drawer');
        await expect(drawer).toBeVisible({ timeout: 5_000 });
        await drawer.locator('.drawer-tabs button', { hasText: '内容' }).click();
        await expect(drawer.locator(v.wrap)).toBeVisible({ timeout: 10_000 });
        const anchor = drawer.locator(`[data-dt-table-anchor="${v.table}"]`);
        await expect(anchor.locator(`.group-row[data-table="${v.table}"]`).first()).toBeVisible({ timeout: 10_000 });
        await expect(anchor.locator('.row-pad').first(), '窗口化占位件在场(量齐后收窗)').toBeAttached({ timeout: 10_000 });
        return { drawer, anchor };
      }

      test(`K1 千文件首渲窗口化: 常驻 DOM 行数 << 数据行数 + rowsFn 直测耗时 @fast (${skin} dt${v.id})`, async ({ page }) => {
        test.setTimeout(60_000);
        collectRuntimeErrors(page);
        const { anchor } = await openK(page);

        // ① 常驻 DOM 行数 << 1001(视口窗 + OVERSCAN 10×2; 300 是回归上界不是刻度, 同 #12)
        const domRows = await anchor.locator(`.group-row[data-table="${v.table}"]`).count();
        expect(domRows, `常驻 DOM 行数远小于数据行数(实测 ${domRows}, 数据 1001)`).toBeLessThan(300);
        const domNodes = await page.evaluate((tid) =>
          document.querySelector(`[data-dt-table-anchor="${tid}"]`).getElementsByTagName('*').length, v.table);

        // ② rowsFn 直测(dtTplRows → 变体 rowsFn, 记忆化热态 = 千级常驻代价): 20 次采样取最大。
        //    全量装配判据: 返回行数必须 == 1001(窗口化收的是渲染基数, 行装配仍是全量虚表)。
        const bench = await page.evaluate(`(() => {
          const vm = ${INST};
          const rows = vm.dtTplRows('content');
          const t = [];
          for (let i = 0; i < 20; i++) {
            const t0 = performance.now();
            vm.dtTplRows('content');
            t.push(performance.now() - t0);
          }
          return { n: rows.length, max: Math.round(Math.max(...t) * 100) / 100, mean: Math.round((t.reduce((a, b) => a + b, 0) / t.length) * 100) / 100 };
        })()`);
        expect(bench.n, 'rowsFn 装配的是全量虚表(1001 = 1 目录 + 1000 文件)').toBe(1001);
        expect(bench.max, `rowsFn 千级热态单次耗时 <25ms(实测 max ${bench.max}ms / mean ${bench.mean}ms; 20 次采样, 记忆化命中)`).toBeLessThan(25);
        // ③ 节点数只进档案不钉数(皮肤/列数差异大), 实测数字在断言消息里随报告带走
        expect(domNodes, `首渲常驻 DOM 节点数(实测 ${domNodes}, 全量渲染 ≈ 千行 × 每行 10+ 格)`).toBeLessThan(12_000);
        console.log(`      [K1 dt${v.id} ${skin}] 常驻 DOM 行数 ${domRows} / 节点数 ${domNodes} / rowsFn max ${bench.max}ms mean ${bench.mean}ms (n=20)`);
      });

      test(`K2 千文件折叠/展开窗口重测: 折叠长任务预算 + 占位塌缩 + 滚动丢帧粗界 @fast (${skin} dt${v.id})`, async ({ page }) => {
        test.setTimeout(60_000);
        collectRuntimeErrors(page);
        const { drawer, anchor } = await openK(page);
        const padH0 = await padHeight(page, v.table);
        expect(padH0, `展开态占位总高覆盖千行(实测 ${padH0}px)`).toBeGreaterThan(15_000);

        // 探针在 settle 后安装 —— 只量「折叠单目录」这一次交互(longtask + 锚内 DOM 变更,
        // 口径同 dt-live-update #10)
        await page.evaluate((tid) => {
          window.__lt = [];
          window.__mut = 0;
          if (window.__po) window.__po.disconnect();
          window.__po = new PerformanceObserver((l) => {
            for (const e of l.getEntries()) window.__lt.push(Math.round(e.duration));
          });
          window.__po.observe({ entryTypes: ['longtask'] });
          new MutationObserver((ms) => { window.__mut += ms.length; })
            .observe(document.querySelector(`[data-dt-table-anchor="${tid}"]`),
              { attributes: true, childList: true, subtree: true });
        }, v.table);

        const tgl = anchor.locator('.group-row.dir [data-act="fold"]').first();
        await tgl.click();
        await measureWindow(500); // 交互 + 窗口重算余波落进观察窗(量具窗, 见 measureWindow 注)

        // 折叠后: 千行子树真收拢 —— 行数塌到目录行 + 窗口余量, 占位总高按新窗重测塌缩
        const foldRows = await anchor.locator(`.group-row[data-table="${v.table}"]`).count();
        expect(foldRows, `折叠后常驻行数塌到目录行级(实测 ${foldRows}, 数据余 1)`).toBeLessThan(20);
        const padH1 = await padHeight(page, v.table);
        expect(padH1, `折叠后占位总高按新窗重测塌缩(实测 ${padH1}px, 折叠前 ${padH0}px)`).toBeLessThan(padH0 / 10);
        const ltFold = await page.evaluate(() => window.__lt || []);
        const mutFold = await page.evaluate(() => window.__mut || 0);
        const ltFoldSum = ltFold.reduce((a, b) => a + b, 0);
        expect(ltFold.length, `折叠单目录长任务数 ≤1(实测 ${ltFold.join('/') || '无'}; W3 窗口化后渲染基数 ~47 行, 残留只可能是 rowsFn 全量装配)`).toBeLessThanOrEqual(1);
        expect(ltFoldSum, `折叠单目录长任务总时长 <50ms(实测 ${ltFoldSum}ms)`).toBeLessThan(50);
        expect(mutFold, `折叠锚内 DOM 变更记录 ≤64(实测 ${mutFold}; 收窗 = 摘千行窗内行 + 占位改高; ` +
          `2026-11-02 四格实测 50/52/53/53, 预算按量得值 + 视口行数方差给 1 档余量)`).toBeLessThanOrEqual(64);

        // 展开还原: 再点一次, 窗口必须重测回千行态(不是停在折叠窗也不塌成全量)
        await tgl.click();
        // 旧 500ms 睡等「交互 + 窗口重算余波落定」→ poll 等展开态落定(行数回常驻窗 + 占位还原)
        await expect.poll(async () => {
          const rows = await anchor.locator(`.group-row[data-table="${v.table}"]`).count();
          const pad = await padHeight(page, v.table);
          return rows < 300 && pad > padH0 * 0.9;
        }, { timeout: 10_000, message: `展开后窗口重测未回千行态(行数回常驻窗且占位总高还原, 首渲 ${padH0}px)` })
          .toBe(true);
        const unfoldRows = await anchor.locator(`.group-row[data-table="${v.table}"]`).count();
        expect(unfoldRows, `展开后窗口重测回常驻窗(实测 ${unfoldRows}, 仍 << 1001)`).toBeLessThan(300);
        const padH2 = await padHeight(page, v.table);
        expect(padH2, `展开后占位总高还原(实测 ${padH2}px, 首渲 ${padH0}px)`).toBeGreaterThan(padH0 * 0.9);

        // 滚动丢帧采样: rAF 逐帧 gap, 40 步匀速滚到底(窗口随滚动连续重算)。
        // 断言只钉灾难冻结粗界; 精细分布进档案(A/B 口径, CI 不拍绝对 ms)。粗界取 500ms:
        // 2026-11-02 实测四格 maxGap 50/100/233/100ms —— 233ms 出现在多 worker 并行争用下,
        // 250ms 会假红; 而回归方向(W3 前全量渲染随滚动逐帧重建千行)远超 500ms, 判别力保留。
        const sweep = await page.evaluate(() => new Promise((resolve) => {
          const body = document.querySelector('.drawer .drawer-body');
          const gaps = [];
          let last = performance.now();
          let step = 0;
          const H = body.scrollHeight;
          function tick(now) {
            gaps.push(now - last);
            last = now;
            if (step < 40) {
              step++;
              body.scrollTop = (H * step) / 40;
              requestAnimationFrame(tick);
            } else {
              const tail = gaps.slice(1);
              resolve({
                n: tail.length,
                maxGap: Math.round(Math.max(...tail)),
                drops: tail.filter((g) => g > 100).length,
              });
            }
          }
          requestAnimationFrame(tick);
        }));
        expect(sweep.maxGap, `滚动全程无灾难冻结帧(实测 max gap ${sweep.maxGap}ms, >100ms 帧 ${sweep.drops}/${sweep.n}; 粗界 500ms, 依据见上)`).toBeLessThan(500);
        console.log(`      [K2 dt${v.id} ${skin}] 折叠 longtask ${ltFold.join('/') || '无'}(合 ${ltFoldSum}ms) mut ${mutFold} | ` +
          `padH ${padH0}->${padH1}px(折叠)->${padH2}px(展开) | 行数 常驻→折叠 ${foldRows}→展开 ${unfoldRows} | ` +
          `滚动 maxGap ${sweep.maxGap}ms, >100ms 帧 ${sweep.drops}/${sweep.n}`);

        // 滚到底不塌陷: 末行进窗且可见(占位撑住总高, 同 #12 ②)
        const body = drawer.locator('.drawer-body');
        await body.evaluate((el) => { el.scrollTop = el.scrollHeight; });
        await expect(anchor.locator('.group-row[data-dt-key="D/f0999 - file.mkv"]'),
          '滚到底末行进窗且可见(占位总高 == 全量渲染高度)').toBeVisible({ timeout: 10_000 });
      });
    });
  }
}
