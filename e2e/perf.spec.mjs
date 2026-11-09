// @ts-check
import { expect, test } from '@playwright/test';
import { baseUrl, SKINS, TORRENTS } from './harness.mjs';
import { collectRuntimeErrors, installRuntimeErrorGuard } from './lib/errors.mjs';
import { INST, readInst } from './lib/vm.mjs';

/**
 * 性能埋点(S5 批, 计划 26-10-06-0708 §3.3/§04 S5) —— 承接旧单页冒烟脚本(S7 退役,
 * git 历史可查)的**块B**
 * (性能埋点 P1-2/P1-3 + 行窗口化 + 占位总高 + 滚动不塌陷)。行号为取证时点值(计划 §2.2),
 * 已按 grep 锚点复核(2026-10-06, 删块前; S1–S4 已删块A/F/C/E/D, 行号较计划漂移):
 *
 * 块B grep 锚点: `强制全量重渲染 N 轮, 用 PerformanceObserver(longtask) 量"主线程被占住多久"` 起,
 * 至 `window.scrollTo(0, 0)` 收尾止(删块前 L137–254; 计划取证 L500–585)。内含 6 个旧 add() 名:
 * P1-2 单轮主线程阻塞下降 / P1-3 重渲染不再按全表强制布局 / P1-2 行窗口化生效(EXPECT_N>500 才跑) /
 * P1-2 占位总高 == 全量渲染 / 滚动到底不塌陷(占位撑住总高) / 最后一屏有行且可见。
 *
 * ── 对账映射表(旧断言名 → 新 test 名; 旧块 add() 调用点 5 处/皮肤 @ --torrents 300, 6 处 @ >500) ──
 *  旧 add() 行号(删块前 grep 实测)      旧断言名                                   新去向下落
 *  L194  P1-2 单轮主线程阻塞下降                                    → P1-2/P1-3 A/B 埋点(1 test 2 断言 ——
 *                                                                    共享同一次 3+3 轮 bench, 拆开要跑两遍)
 *  L203  P1-3 重渲染不再按全表强制布局                               → 同上
 *  L209  P1-2 行窗口化生效(EXPECT_N && EXPECT_N>500 才跑)           → 行窗口化生效(TORRENTS>500 门控, 同条件
 *                                                                    test.skip; 默认 300 档 skip, 消息带当前值)
 *  L230  P1-2 占位总高 == 全量渲染                                   → 占位总高 == 全量渲染
 *  L250  滚动到底不塌陷(占位撑住总高)                                → 滚动到底: 总高不塌陷 + 末行可见
 *                                                                    (1 test 2 断言 —— 共享同一次滚到底 arrange)
 *  L251  最后一屏有行且可见                                          → 同上
 *  另: 旧块包在 `if (nav.length >= 3)` 兜底分支里(L131), 兜底 add 不迁移 ——
 *  新轨定位器拿不到页签/行直接红。旧收尾总检 L581「无 console.error / pageerror」→
 *  installRuntimeErrorGuard afterEach(每条 test 各自把关, e2e/lib/errors.mjs)。
 *  计数口径: 块B add() 5 处/皮肤(--torrents 300; >500 时 6 处) → 新 3 test/皮肤(+1 门控 test)
 *  —— 1:N(合并)成立, 每个旧名都有去向下落。
 *
 * ── 对账实跑数字(五步对账 §5.1, 2026-10-06 S5 批实测回填) ──
 *  · 步骤1 新 spec: commands run dev.e2e 全量 66 passed / 10 skipped / 0 failed(2.4m;
 *    10 skipped = 本 spec 行窗口化 ×2(TORRENTS=300 门控, 旧脚本同条件跳过)+ optimistic hang 组
 *    ×2 + menus off 组 ×6)。本批首跑 2.1m 时曾因 hr-history 漏调 arrange 红 2 条, 修复后全绿。
 *  · 步骤2 旧脚本同参数轮: 桩 8235(--torrents 300 --hr-scene on 默认), 旧脚本
 *    --base http://127.0.0.1:8235 --torrents 300 --ui both = 32 项 0 FAIL(1m26s), 无存量失败;
 *    对账范围内块B 5 断言名 × 2 皮肤全 PASS(实测: prism 长任务 167→0 ms/轮, refresh 145→33ms,
 *    gbr 82 次(窗口 20 行/轮, 预算 120); atlas 161→0, 145→34ms, gbr 82; 占位总高 prism 18215
 *    /atlas 18520, Δ 均 0, 行间距 5/6px; 滚动前后高度均不变)。
 *  · 步骤3 对账映射: 见上表 —— 块B 5 旧名/皮肤 → 3 test/皮肤(+1 门控 test), 1:N(合并)成立,
 *    每个旧名有去向下落。
 *  · 步骤4 删旧块(与本 spec 同 commit): 旧脚本删块B 段(含仅供块B 的 nav 页签/种子视图/
 *    tRows/tTotal 脚手架)+ 随块失去最后调用方的 readInst helper(单点在 e2e/lib/vm.mjs)与
 *    EXPECT_N 常量(块B 行窗口化门控是它最后一个调用方; 单点在 e2e/harness.mjs TORRENTS),
 *    与块G 段同批, 净 73+/251-; `--torrents` CLI 参数降为不再消费(头注释注明)。
 *  · 步骤5 双复跑: 旧脚本(删段后, 同桩 8235)14 项 0 FAIL(37.9s) —— 32−(块B 5 + 块G 4)×2 皮肤
 *    = 14, 项数下降恰对应两块断言数, 零残余失败; 新 spec 复跑 commands run dev.e2e 全量
 *    66 passed / 10 skipped / 0 failed(2.4m); npm run test:e2e:fast 4 passed(7.6s)不变;
 *    E2E_HR_SCENE=empty 抽验 62 passed / 14 skipped(1.3m), hr-history 组 4 test 整组 skip。
 *  · 时长(R3 监控): 全量 2.4m vs S4 批 1.2m —— 增量主要来自每 test 独立 context + 页面加载
 *    (本批 +12 test)与块B bench(3+3 轮全量/窗口化刷新); 未超「旧脚本同口径 1.5×」启动线
 *    (旧脚本删段前全轮 1m26s), 按计划不做预防性优化。
 *
 * ── D4 断言翻译守则落地说明(计划 §3.5) ──
 *  · evaluate 保留处(均有注释, 全部属允许两类): 1) longtask PerformanceObserver + gbr 计数器 +
 *    A/B bench 直调 vm.rowWin/lastRid/refresh —— 量的是"渲染管线占了主线程多久/强制布局几次",
 *    这些度量点只在页面内部, 且被测对象就是 vm 的渲染行为本身(第2类时序探针, 旧块原样移植);
 *    2) 占位总高的 rowWin 开关对照 —— rowWin 没有 UI 开关, 开/关两侧必须同一帧序列读数(第1类
 *    注入/复原桩态, 旧块同款); 3) 末行视口可见性的 getBoundingClientRect 读数(第2类, 视口相交
 *    没有 locator 之外的取径)。
 *  · 阈值数字逐字保留(回归基准, 不是实现细节): rounds=3、gbrBudget = 窗口行数×(rounds+2)+20、
 *    占位总高 Δ<50px、滚动塌陷 Δ<200px、行窗口化判据 tRows < tTotal×0.5(EXPECT_N>500 才有判别力)。
 *  · 保留的 sleep 均有注释: 滚动后 400ms×2 —— 行窗口化按滚动位置异步补行, 读总高/末行前要让
 *    补行 settle, 旧块同值同节奏(量的是 settle 后的布局不变量, 等待即测量程序的一部分)。
 *  · 旧脚本单页流水里的跨块收尾(scrollTo(0,0) 等)不再需要 —— 每 test 独立 context。
 *
 * ── W5 增补(计划 26-11-02-0351 §W5, 2026-11-02): 尾部「主表×抽屉同屏交叉」describe ——
 * 千级种子(E2E_TORRENTS>500)下抽屉滚动/折叠不扰动主表文档型窗口 + 不放大主表轮询节拍,
 * W3 窗口状态分家的端到端零回归确认; 抽屉侧判据在 drawer-content-perf / dt-live-update, 不在此重复。
 */

/** 导航页签定位器(tpl/topbar.html `nav.tabs [data-view]`)。 */
const tab = (page, view) => page.locator(`nav.tabs [data-view="${view}"]`);

/**
 * 等主表窗口化(补行/重测)落定: 滚动位+总高+行键集连续三拍采样(节拍 = expect.poll 默认间隔,
 * 静默跨度 >= 350ms)一致 —— 滚动后的异步补行与视口重测没有单一 DOM 终点, 旧 400/600ms 睡等
 * 「赌 settle 跑完」的显式化(读的是 settle 后的布局不变量, 等待即测量程序的一部分口径不变,
 * 见头部 D4 落地说明); 三拍口径防「补行尚未开始就判稳」的提前通过。
 * @param {import('@playwright/test').Page} page
 */
const awaitMainSettled = async (page, timeout = 10_000) => {
  const seq = [];
  await expect.poll(async () => {
    seq.push(await page.evaluate(() => `${window.scrollY}#${document.documentElement.scrollHeight}#` +
      Array.from(document.querySelectorAll('.torrent-row')).map((r) => r.getAttribute('data-hash')).join(',')));
    if (seq.length > 3) seq.shift();
    return seq.length === 3 && seq[0] === seq[1] && seq[1] === seq[2];
  }, { timeout }).toBe(true);
};

/**
 * 等抽屉表格渲染窗落定(行键集连续三拍采样一致, 静默跨度 >= 350ms) —— 回顶/折叠后的窗口重渲
 * 没有单一 DOM 终点, 旧 400ms 睡等「赌重渲跑完」的显式化。
 * @param {import('@playwright/test').Page} page
 * @param {import('@playwright/test').Locator} anchor 表格锚
 */
const awaitDrawerSettled = async (page, anchor, timeout = 10_000) => {
  const seq = [];
  await expect.poll(async () => {
    seq.push(await anchor.evaluate((a) => Array.from(a.querySelectorAll('.group-row[data-dt-key]'))
      .map((r) => r.getAttribute('data-dt-key')).join('|')));
    if (seq.length > 3) seq.shift();
    return seq.length === 3 && seq[0] !== '' && seq[0] === seq[1] && seq[1] === seq[2];
  }, { timeout }).toBe(true);
};

/**
 * 量具节拍(测量程序参数, 非条件等待): 40 步匀速滚到底的步进节奏是量具口径 —— 窗口随滚动连续
 * 重算, 交互窗时长是「轮询节拍不被放大/拖累」断言的分母(2000ms 档期望 2±1 拍按此时长定版)。
 * 属 e2e setTimeout 审计的「业务/量具延迟语义, 保留并注释」类, 走 Node 侧 setTimeout 不占页面时钟。
 * @param {number} ms
 */
const measureWindow = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

/**
 * 首访估算开窗阈值(镜像 `src/auto_qb/webui/static/shared/app.js` 的 ROW_WIN_EST_MIN;
 * 真值单点仍在 app.js, 这里只给本 spec 的断言分档用): n >= 此值的首访用估算行高开窗、
 * 随滚动渐进实测收敛(issue 26-11-02-0902) —— 占位总高只做粗界守阵, 滚到底按"不塌陷"判。
 * 2026-11-02 二轮按拐点实测(150 行 215ms / 200 行 334ms, 250ms 线)从 1000 下移到 200,
 * 与 ROW_WIN_MIN 合并; 低于此值窗口化本身关闭(off 全量渲染), win==full 恒等平凡成立。
 */
const ROW_WIN_EST_MIN = 200;

/** 进种子视图并等行渲染(块B 所有用例的共同 arrange, 旧脚本 nav[1] 点击同口径)。 */
async function gotoTorrents(page, skin) {
  collectRuntimeErrors(page);
  await page.goto(`${baseUrl()}/${skin}/`, { waitUntil: 'domcontentloaded' });
  await expect(page.locator('.group-row').first()).toBeVisible({ timeout: 30_000 });
  await tab(page, 'torrents').click();
  await expect(page.locator('.torrent-row').first()).toBeVisible({ timeout: 15_000 });
}

for (const skin of SKINS) {
  test.describe(`皮肤 ${skin}(块B: 性能埋点)`, () => {
    /* 旧脚本收尾总检「无 console.error / pageerror」的框架化(同 views.spec 口径)。 */
    installRuntimeErrorGuard(test);

    test('P1-2/P1-3 A/B 埋点: 主线程阻塞下降 + 重渲染不再按全表强制布局', async ({ page }) => {
      test.setTimeout(90_000); // 3+3 轮全量/窗口化 bench(每轮一次全量 refresh), 30s 默认太紧
      await gotoTorrents(page, skin);

      /* 窗口行数(窗口化默认开)与数据总数: P1-3 预算的输入。vm 内部字段读数(evaluate 第2类)。 */
      const tRows = await page.locator('.torrent-row').count();
      const tTotal = await readInst(page, 'vm.filteredTorrents.length');
      expect(tRows, '窗口行数 > 0(种子视图有数据)').toBeGreaterThan(0);

      /*
       * 强制全量重渲染 N 轮, 用 PerformanceObserver(longtask) 量"主线程被占住多久" ——
       * 这才是"不跟手"的真身: renderMs 只测同步赋值, Vue 的 DOM patch 发生在之后的
       * 调度里, 埋点抓不到; longtask(>50ms 的任务)能把整表替换的真实阻塞量出来。
       * 行窗口化(P1-2)的收益就体现在这个数字上。(旧块原样移植 —— 第2类时序探针)
       */
      await page.evaluate(`(() => {
        window.__lt = [];
        if (window.__po) window.__po.disconnect();
        window.__po = new PerformanceObserver((l) => { for (const e of l.getEntries()) window.__lt.push(Math.round(e.duration)); });
        window.__po.observe({ entryTypes: ["longtask"] });
      })()`);
      /*
       * P1-3 直接量: 统计"强制重渲染期间 getBoundingClientRect 被调用了多少次"。
       * 每次调用都是一次**强制同步布局**(行越多越贵); 改成 ResizeObserver + rAF 之后,
       * 渲染本身不该再触发它(只有元素被换掉的那一轮才会量一次)。(旧块原样移植)
       */
      await page.evaluate(`(() => {
        window.__gbr = 0;
        if (!window.__gbrPatched) {
          window.__gbrPatched = true;
          const orig = Element.prototype.getBoundingClientRect;
          Element.prototype.getBoundingClientRect = function () { window.__gbr++; return orig.apply(this, arguments); };
        }
        window.__gbr = 0;
      })()`);
      /*
       * A/B 放在同一次运行里: 先关窗口跑 N 轮(= 改动前的全量渲染), 再开窗口跑 N 轮。
       * 只看长任务不够 —— 网络两边一样大, 差的是 CPU 段; 故两个都记。
       * 直调 vm.rowWin/lastRid/refresh 属第2类时序探针: 被测对象就是渲染管线,
       * 走 UI 手势(切页签)量的是另一件事, 与旧块口径不一致。
       */
      const rounds = 3;
      const benchRun = async (winOn) => page.evaluate(`(async () => {
        const vm = ${INST};
        const saved = vm.rowWin;
        vm.rowWin = ${winOn};
        window.__lt = [];
        const ms = [];
        for (let i = 0; i < ${rounds}; i++) {
          vm.lastRid = null;                 // 强制服务端回全量 -> 前端整表替换
          const t = performance.now();
          await vm.refresh();
          await new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r)));
          ms.push(Math.round(performance.now() - t));
        }
        vm.rowWin = saved;
        return { ms, lt: window.__lt || [] };
      })()`);
      const off = await benchRun(false);
      const on = await benchRun(true);
      const sumLt = (lt) => lt.reduce((a, b) => a + b, 0);
      const avg = (a) => Math.round(a.reduce((x, y) => x + y, 0) / (a.length || 1));
      console.log(
        `      [A/B ${rounds} 轮] 全量: refresh ${off.ms.join('/')}ms, 长任务 ${off.lt.join('/') || '无'} | ` +
        `窗口化: refresh ${on.ms.join('/')}ms, 长任务 ${on.lt.join('/') || '无'}`);

      /* P1-2: 窗口化的长任务总和不得超过全量渲染 —— 收益方向断言(允许相等, 桩数据小时两边都近零)。 */
      expect(sumLt(on.lt), `P1-2 单轮主线程阻塞下降: 窗口化长任务 ${avg(on.lt)}ms/轮 vs 全量 ${avg(off.lt)}ms/轮; ` +
        `整轮 refresh ${avg(off.ms)} -> ${avg(on.ms)}ms`).toBeLessThanOrEqual(sumLt(off.lt));

      /*
       * P1-3: 唯一"按渲染次数"的布局读取是 P1-2 的**逐行测高**(行高不齐, 必须逐行记),
       * 量的是**窗口内**那几十行 —— 判据是"≤ 每轮渲染的行数 + 少量余量", 不是 0。
       * 预算公式逐字保留: tRows × (rounds + 2) + 20。
       */
      const gbr = await page.evaluate('window.__gbr');
      const gbrBudget = tRows * (rounds + 2) + 20;
      expect(gbr, `P1-3 重渲染不再按全表强制布局: ${rounds} 轮共 ${gbr} 次 ` +
        `(窗口内 ${tRows} 行/轮, 预算 ${gbrBudget}; 全表量法会是 ${tTotal * rounds} 次量级)`).toBeLessThanOrEqual(gbrBudget);
    });

    test('P1-2 行窗口化生效: DOM 行数远小于数据条数', async ({ page }) => {
      /* 旧块同条件门控(EXPECT_N && EXPECT_N > 500): 窗口 ~26 行, 种子数 ≤500 时
       * "DOM < 数据一半"没有判别力(全量渲染也过)。skip 消息带当前值(计划 §6 R2)。 */
      test.skip(TORRENTS <= 500, `行窗口化断言仅种子数 >500 有判别力; 当前 E2E_TORRENTS=${TORRENTS}(默认档 300, 旧脚本同条件跳过)`);
      await gotoTorrents(page, skin);

      const tRows = await page.locator('.torrent-row').count();
      const tTotal = await readInst(page, 'vm.filteredTorrents.length');
      /* 判据逐字保留: tRows < tTotal * 0.5(未窗口化时两者相等)。 */
      expect(tRows < tTotal * 0.5, `P1-2 行窗口化生效: DOM ${tRows} 行 << 数据 ${tTotal} 条`).toBe(true);
    });

    test('P1-2 首访路径指纹: 估算开窗档 gBR 远小于行数(防误退回精确冷启动)', async ({ page }) => {
      /* 只在估算开窗档跑: 低于阈值时窗口化本身关闭, 无"路径"可判(issue 26-11-02-0902 空档1)。 */
      test.skip(TORRENTS < ROW_WIN_EST_MIN, `路径指纹断言仅估算开窗档(>= ${ROW_WIN_EST_MIN})有判别力; 当前 E2E_TORRENTS=${TORRENTS}`);
      collectRuntimeErrors(page);
      /* gBR 计数必须先于 goto 注入, 且在**点击种子页签前**清零 —— 只量"种子视图首访"段,
       * 不把分组页首访的量齐计进来(A/B 用例的注入在 goto 之后, 量的是 refresh 轮次, 抓不到首访)。 */
      await page.addInitScript(() => {
        window.__gbr0 = 0;
        const orig = Element.prototype.getBoundingClientRect;
        Element.prototype.getBoundingClientRect = function () { window.__gbr0++; return orig.apply(this, arguments); };
      });
      await page.goto(`${baseUrl()}/${skin}/`, { waitUntil: 'domcontentloaded' });
      await expect(page.locator('.group-row').first()).toBeVisible({ timeout: 30_000 });
      await page.evaluate(() => { window.__gbr0 = 0; });
      await tab(page, 'torrents').click();
      await expect(page.locator('.torrent-row').first()).toBeVisible({ timeout: 15_000 });
      await awaitMainSettled(page);  // 旧 600ms 睡等「等 updated 量齐拍结束」→ poll 等行集/总高稳态, 计数稳定
      const gbr = await page.evaluate(() => window.__gbr0);
      const tTotal = await readInst(page, 'vm.filteredTorrents.length');
      /* 判别依据(2026-11-02 实测): 估算开窗首访只对窗口内 ~24 行量高, gbr≈55 且**与行数无关**
       * (1000/3000 档均 55); 误退回精确冷启动则对全表逐行量齐, gbr≈行数(200 档 228 / 300 档 325 /
       * 999 档 1051)。上界 150 居中 —— 对估算路径余量 2.7x, 对误切精确的最小档(200 行)余量 1.5x,
       * 两条路径都留判别余量; 占位总高粗界对"误切精确"(比值 1.0)无判别力, 全靠本条兜住。 */
      expect(gbr, `首访路径指纹(估算开窗): gBR ${gbr} 次 / 行数 ${tTotal} —— ` +
        '接近行数说明误退回精确冷启动(全量渲染+逐行量齐, 200 行即 334ms longtask)').toBeLessThan(150);
    });

    test('P1-2 占位总高 == 全量渲染(窗口化只少渲染 DOM, 不改布局高度)', async ({ page }) => {
      await gotoTorrents(page, skin);

      /*
       * 占位总高必须**等于全量渲染**的总高。!必须在**同一帧序列**里对照开关两侧: 早先只在
       * "滚动前后"各读一次 scrollHeight, 而那个读点发生在还原 rowWin 之后 ⇒ 两次量的都是
       * 窗口化高度, 恒等成立。正是这个读数时机让 prism 的行间距硬编码(6px vs 实际 5px)造成的
       * +2973px 偏差一路溜到提交(BUG-1 / TEST-2)。
       * rowWin 没有 UI 开关, 开/关两侧同一帧序列读数 —— 第1类注入/复原(旧块原样移植)。
       */
      const hCmp = await page.evaluate(`(async () => {
        const vm = ${INST};
        const saved = vm.rowWin;
        const settle = () => new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r)));
        const read = async () => { await settle(); return document.documentElement.scrollHeight; };
        vm.rowWin = true;  const win = await read();
        vm.rowWin = false; const full = await read();
        vm.rowWin = saved; await read();
        const el = document.querySelector(".group-table");
        return { win, full, gap: el ? parseFloat(getComputedStyle(el).rowGap) : null };
      })()`);
      /* 阈值: 估算开窗档(>= ROW_WIN_EST_MIN)首访按**已实测行全局均值**估算未量行, 占位总高
       * 随滚动单调收敛但与全量不是逐像素相等(3000 行实测偏差约 13%~14%, 方向取决于首屏采样
       * 到哪一档行高; issue 26-11-02-0902) —— 该档只做粗界守阵(防 ×2 / 接近 0 这类估算失真)。
       * else 分支(严格口径 |win-full|<50)只对 <200 的 off 档可达: 窗口化关闭, win==full 恒等
       * 平凡成立 —— 2026-11-02 二轮阈值 1000→200 后, 原精确冷启动档(200~999)已并入估算档。 */
      if (TORRENTS >= ROW_WIN_EST_MIN) {
        const ratio = hCmp.win / hCmp.full;
        expect(ratio, `占位总高粗界(估算开窗): 窗口化 ${hCmp.win} vs 全量 ${hCmp.full}px ` +
          `(比值 ${ratio.toFixed(3)}, 实测行间距 ${hCmp.gap}px)`).toBeGreaterThan(0.5);
        expect(ratio, '占位总高粗界(估算开窗): 不超过全量 1.5 倍').toBeLessThan(1.5);
      } else {
        expect(Math.abs(hCmp.win - hCmp.full), `窗口化 ${hCmp.win} vs 全量 ${hCmp.full}px ` +
          `(Δ ${hCmp.win - hCmp.full}, 实测行间距 ${hCmp.gap}px)`).toBeLessThan(50);
      }
    });

    test('滚动到底: 总高不塌陷(占位撑住) + 最后一屏有行且可见', async ({ page }) => {
      await gotoTorrents(page, skin);

      /* 滚到底: 总高度在滚动前后不塌陷, 且最后一行可见。
       * 400ms×2 不是装饰性等待: 行窗口化按滚动位置**异步补行**, 滚动后立刻读总高/末行
       * 会量到补行中间态 —— 两次滚动贴底 + settle 是测量程序的一部分(旧块同值同节奏)。 */
      const before = await page.evaluate('document.documentElement.scrollHeight');
      await page.evaluate('window.scrollTo(0, document.documentElement.scrollHeight)');
      await awaitMainSettled(page);  // 旧 400ms 睡等: 补行 settle 的显式化
      await page.evaluate('window.scrollTo(0, document.documentElement.scrollHeight)'); // 再滚一次(贴底)
      await awaitMainSettled(page);  // 旧 400ms 睡等: 贴底补行 settle 的显式化
      const after = await page.evaluate('document.documentElement.scrollHeight');
      const lastHash = await page.$$eval('.torrent-row', (ns) => (ns.length ? ns[ns.length - 1].getAttribute('data-hash') : null));
      /* 末行视口相交读数(getBoundingClientRect, 第2类): locator 的 isVisible 不含视口相交语义。 */
      const lastVisible = await page.evaluate(() => {
        const ns = document.querySelectorAll('.torrent-row');
        if (!ns.length) return false;
        const r = ns[ns.length - 1].getBoundingClientRect();
        return r.top < window.innerHeight && r.bottom > 0;
      });
      /* 阈值: 估算开窗档滚到底继续实测收敛, 方向**不定** —— 占位总高随滚动收敛, 但方向取决于
       * 首屏采样行高与全局均值的相对高低(3000 档实测 +13~14%, 300 档实测 -5.7% = -1296px;
       * 上轮"只会增长"的假设在 2026-11-02 阈值 200 后默认 300 档首次踩进本分支即证伪) ——
       * 故按**比例**禁塌陷: |Δ| < before×25%(对实测峰值 ~2x 余量; 窗口引擎塌陷/占位翻倍会是
       * 接近 ±100% 远超此线, 判别力保留)。issue 26-11-02-0902。
       * else 严格口径(|after-before|<200)只对 <200 的 off 档可达(win==full 平凡恒等, 同占位总高分档)。 */
      if (TORRENTS >= ROW_WIN_EST_MIN) {
        expect(Math.abs(after - before), `滚动到底不塌陷(占位撑住总高; 估算收敛按比例禁塌陷): ${before} -> ${after}px ` +
          `(|Δ| ${Math.abs(after - before)}, 上界 ${Math.round(before * 0.25)})`).toBeLessThan(before * 0.25);
      } else {
        expect(Math.abs(after - before), `滚动到底不塌陷(占位撑住总高): ${before} -> ${after}px`).toBeLessThan(200);
      }
      expect(lastVisible, `最后一屏有行且可见(末行 ${lastHash || '-'})`).toBe(true);
    });
  });

  /* ── W5 同屏交叉(计划 26-11-02-0351 §W5 改法要点 2): 千级种子主表 × 千文件抽屉同屏 ——
   * W3 引擎改动(窗口状态按源族分家: 主表=文档型 _winScrollY/_winViewH, 抽屉=容器型
   * _winCtnState)对主表的零回归端到端确认。量具分工: 抽屉侧窗口化/折叠/丢帧由
   * drawer-content-perf.spec.mjs(W4)与 dt-live-update #12(W3)把守; 本条只守「抽屉交互
   * 不扰动主表窗口」与「抽屉交互不放大主表轮询节拍」两个同屏面 —— 抽屉 content 无轮询,
   * 理论无耦合, 用数字确认(计划口径)。
   * 桩口径: page.route 拦 torrents files 端点(同 drawer-content-perf), 千文件树 =
   * 单层目录 D 下 1000 文件; E2E_TORRENTS>500 才有判别力(同上行窗口化门控)。 */
  function makeFilesK(n = 1000) {
    const out = [];
    for (let i = 0; i < n; i++) {
      out.push({
        name: `D/f${String(i).padStart(4, '0')} - file.mkv`,
        size: 1_000_000 + i * 999,
        progress: (i % 4) / 4,
        priority: 1,
        availability: 0.5,
      });
    }
    return out;
  }

  test.describe(`皮肤 ${skin}(W5: 主表×抽屉同屏交叉)`, () => {
    installRuntimeErrorGuard(test);

    test('W5 同屏交叉: 抽屉滚动/折叠不扰动主表窗口 + 不放大主表轮询节拍', async ({ page }) => {
      test.skip(TORRENTS <= 500, `同屏交叉断言仅种子数 >500 有判别力; 当前 E2E_TORRENTS=${TORRENTS}(默认档 300)`);
      test.setTimeout(90_000); // 5000 种子档多轮轮询量测, 30s 默认太紧(时间预算, 非睡等)
      collectRuntimeErrors(page);
      await page.route('**/api/torrents/*/files', (route) =>
        route.fulfill({ contentType: 'application/json', body: JSON.stringify(makeFilesK()) }));
      await page.addInitScript(() =>
        localStorage.setItem('autoqb.ui.drawerTpl', JSON.stringify({ content: '11' })));
      await gotoTorrents(page, skin);

      /* 开抽屉(首行; 滚到中段后补行窗口与 2s 轮询重渲会抢点击 —— 先开再滚, 同屏交叉量的是
       * 交互前后稳定态, 不量开合瞬间) → 内容页签(dt11 引擎桥) → 窗口化占位件点亮。 */
      await page.dblclick('.torrent-row >> nth=0', { force: true }); // force: 整表重渲染抢点击(smoke.md)
      const drawer = page.locator('.drawer-dock > .drawer');
      await expect(drawer).toBeVisible({ timeout: 5_000 });
      await drawer.locator('.drawer-tabs button', { hasText: '内容' }).click();
      const anchor = drawer.locator('[data-dt-table-anchor="drawerContentV11"]');
      await expect(anchor.locator('.group-row[data-table="drawerContentV11"]').first()).toBeVisible({ timeout: 10_000 });
      await expect(anchor.locator('.row-pad').first(), '抽屉窗口化占位件在场').toBeAttached({ timeout: 10_000 });
      await awaitMainSettled(page);  // 旧 600ms 睡等: 抽屉 dock 挤压视口后主表窗口重测 settle 的显式化

      /* 主表滚到中段(千级窗口居中态, 抽屉同屏在场), 等窗口化补行 settle(旧 600ms 睡等的显式化)。 */
      await page.evaluate('window.scrollTo(0, document.documentElement.scrollHeight * 0.5)');
      await awaitMainSettled(page);

      /* 快照 1: 主表窗口(滚动位 + 渲染窗首末行 + 常驻行数); 挂轮询 tick 与 longtask 探针。
       * vm.refresh 实例属性影子化计数(第1类注入; 节拍链 fn 走 this.refresh 命中影子)。 */
      await page.evaluate(`(() => {
        const vm = ${INST};
        if (!window.__refreshPatched) {
          window.__refreshPatched = true;
          const orig = vm.refresh;
          vm.refresh = function (...a) { window.__ticks.push(performance.now()); return orig.apply(this, a); };
        }
        window.__ticks = [];
        window.__lt = [];
        if (window.__po) window.__po.disconnect();
        window.__po = new PerformanceObserver((l) => { for (const e of l.getEntries()) window.__lt.push(Math.round(e.duration)); });
        window.__po.observe({ entryTypes: ['longtask'] });
      })()`);
      const snap = () => page.evaluate(() => {
        const rows = document.querySelectorAll('.torrent-row');
        return {
          sy: Math.round(window.scrollY),
          n: rows.length,
          first: rows.length ? rows[0].getAttribute('data-hash') : null,
          last: rows.length ? rows[rows.length - 1].getAttribute('data-hash') : null,
        };
      });
      const before = await snap();
      expect(before.n, '主表窗口常驻行数 >0(中段滚动态)').toBeGreaterThan(0);

      /* 抽屉交互: 40 步匀速滚到底(~3.2s, 窗口随滚动连续重算) + 回顶 + 折叠/展开一次(窗口重算最重路径;
       * 折叠目标 .dir 行在树顶 —— 滚到底后它已出窗卸载, 必须回顶再点)。 */
      const body = drawer.locator('.drawer-body');
      for (let step = 1; step <= 40; step++) {
        await body.evaluate((el, s) => { el.scrollTop = (el.scrollHeight * s) / 40; }, step);
        await measureWindow(80);  // 匀速滚动节拍(量具口径, 见 measureWindow 注)
      }
      await body.evaluate((el) => { el.scrollTop = 0; });
      await awaitDrawerSettled(page, anchor);  // 旧 400ms 睡等: 回顶后抽屉窗口重渲落定的显式化
      const tgl = anchor.locator('.group-row.dir [data-act="fold"]').first();
      await tgl.click();
      await awaitMainSettled(page);  // 旧 400ms 睡等: 折叠后主表窗口重算 settle 的显式化
      await tgl.click();
      await awaitMainSettled(page);  // 旧 400ms 睡等: 展开后主表窗口重算 settle 的显式化

      /* 快照 2: 主表窗口必须逐字段不变(抽屉滚动/折叠不漂移主表文档型窗口)。 */
      const after = await snap();
      expect(after.sy, `主表滚动位不漂移: ${before.sy} -> ${after.sy}`).toBe(before.sy);
      expect(after.n, `主表常驻行数不变: ${before.n} -> ${after.n}`).toBe(before.n);
      expect(after.first, `主表渲染窗首行不变: ${before.first} -> ${after.first}`).toBe(before.first);
      expect(after.last, `主表渲染窗末行不变: ${before.last} -> ${after.last}`).toBe(before.last);

      /* 轮询节拍: 交互窗(~4.4s)内主表 refresh 恰为节拍数(3000 种子档 2000ms → 2 拍, 余量 ±1) ——
       * >=1 证节拍不被抽屉交互拖累, <=3 证抽屉交互不放大轮询(计划: 「互不放大, 用数字确认」)。 */
      const ticks = await page.evaluate('window.__ticks');
      expect(ticks.length, `主表轮询节拍不被放大/拖累(交互窗实测 ${ticks.length} 拍; 2000ms 档期望 2±1)`).toBeLessThanOrEqual(3);
      expect(ticks.length, '主表轮询节拍在抽屉交互期间续跑(至少 1 拍)').toBeGreaterThanOrEqual(1);

      /* 主线程灾难冻结粗界(同 W4 K2 口径 500ms; 精细分布进档案不钉数)。 */
      const lt = await page.evaluate('window.__lt || []');
      expect(Math.max(0, ...lt), `同屏交互无灾难冻结帧(实测 longtask ${lt.join('/') || '无'})`).toBeLessThan(500);
      console.log(`      [W5 同屏 ${skin}] 主表窗口 ${before.n} 行(${(before.first || '').slice(0, 8)}…${(before.last || '').slice(0, 8)}…) 交互前后逐字段恒等 | ` +
        `轮询 ${ticks.length} 拍/4.4s | longtask ${lt.join('/') || '无'}`);
    });
  });
}
