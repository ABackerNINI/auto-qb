// @ts-check
import { expect, test } from '@playwright/test';
import { BASE_URL, SKINS, TORRENTS } from './harness.mjs';
import { collectRuntimeErrors, installRuntimeErrorGuard } from './lib/errors.mjs';
import { INST, readInst } from './lib/vm.mjs';

/**
 * 性能埋点(S5 批, 计划 26-10-06-0708 §3.3/§04 S5) —— 承接旧脚本 scripts/ui_smoke.cjs 的**块B**
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
 *  · 步骤2 旧脚本同参数轮: 桩 8235(--torrents 300 --hr-scene on 默认) + `node scripts/ui_smoke.cjs
 *    --base http://127.0.0.1:8235 --torrents 300 --ui both` = 32 项 0 FAIL(1m26s), 无存量失败;
 *    对账范围内块B 5 断言名 × 2 皮肤全 PASS(实测: prism 长任务 167→0 ms/轮, refresh 145→33ms,
 *    gbr 82 次(窗口 20 行/轮, 预算 120); atlas 161→0, 145→34ms, gbr 82; 占位总高 prism 18215
 *    /atlas 18520, Δ 均 0, 行间距 5/6px; 滚动前后高度均不变)。
 *  · 步骤3 对账映射: 见上表 —— 块B 5 旧名/皮肤 → 3 test/皮肤(+1 门控 test), 1:N(合并)成立,
 *    每个旧名有去向下落。
 *  · 步骤4 删旧块(与本 spec 同 commit): ui_smoke.cjs 删块B 段(含仅供块B 的 nav 页签/种子视图/
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
 *  · evaluate 保留处(均有注释, 全部属允许两类): ①longtask PerformanceObserver + gbr 计数器 +
 *    A/B bench 直调 vm.rowWin/lastRid/refresh —— 量的是"渲染管线占了主线程多久/强制布局几次",
 *    这些度量点只在页面内部, 且被测对象就是 vm 的渲染行为本身(第②类时序探针, 旧块原样移植);
 *    ②占位总高的 rowWin 开关对照 —— rowWin 没有 UI 开关, 开/关两侧必须同一帧序列读数(第①类
 *    注入/复原桩态, 旧块同款); ③末行视口可见性的 getBoundingClientRect 读数(第②类, 视口相交
 *    没有 locator 之外的取径)。
 *  · 阈值数字逐字保留(回归基准, 不是实现细节): rounds=3、gbrBudget = 窗口行数×(rounds+2)+20、
 *    占位总高 Δ<50px、滚动塌陷 Δ<200px、行窗口化判据 tRows < tTotal×0.5(EXPECT_N>500 才有判别力)。
 *  · 保留的 sleep 均有注释: 滚动后 400ms×2 —— 行窗口化按滚动位置异步补行, 读总高/末行前要让
 *    补行 settle, 旧块同值同节奏(量的是 settle 后的布局不变量, 等待即测量程序的一部分)。
 *  · 旧脚本单页流水里的跨块收尾(scrollTo(0,0) 等)不再需要 —— 每 test 独立 context。
 */

/** 导航页签定位器(tpl/topbar.html `nav.tabs [data-view]`)。 */
const tab = (page, view) => page.locator(`nav.tabs [data-view="${view}"]`);

/** 进种子视图并等行渲染(块B 所有用例的共同 arrange, 旧脚本 nav[1] 点击同口径)。 */
async function gotoTorrents(page, skin) {
  collectRuntimeErrors(page);
  await page.goto(`${BASE_URL}/${skin}/`, { waitUntil: 'domcontentloaded' });
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

      /* 窗口行数(窗口化默认开)与数据总数: P1-3 预算的输入。vm 内部字段读数(evaluate 第②类)。 */
      const tRows = await page.locator('.torrent-row').count();
      const tTotal = await readInst(page, 'vm.filteredTorrents.length');
      expect(tRows, '窗口行数 > 0(种子视图有数据)').toBeGreaterThan(0);

      /*
       * 强制全量重渲染 N 轮, 用 PerformanceObserver(longtask) 量"主线程被占住多久" ——
       * 这才是"不跟手"的真身: renderMs 只测同步赋值, Vue 的 DOM patch 发生在之后的
       * 调度里, 埋点抓不到; longtask(>50ms 的任务)能把整表替换的真实阻塞量出来。
       * 行窗口化(P1-2)的收益就体现在这个数字上。(旧块原样移植 —— 第②类时序探针)
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
       * 直调 vm.rowWin/lastRid/refresh 属第②类时序探针: 被测对象就是渲染管线,
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

    test('P1-2 占位总高 == 全量渲染(窗口化只少渲染 DOM, 不改布局高度)', async ({ page }) => {
      await gotoTorrents(page, skin);

      /*
       * 占位总高必须**等于全量渲染**的总高。!必须在**同一帧序列**里对照开关两侧: 早先只在
       * "滚动前后"各读一次 scrollHeight, 而那个读点发生在还原 rowWin 之后 ⇒ 两次量的都是
       * 窗口化高度, 恒等成立。正是这个读数时机让 prism 的行间距硬编码(6px vs 实际 5px)造成的
       * +2973px 偏差一路溜到提交(BUG-1 / TEST-2)。
       * rowWin 没有 UI 开关, 开/关两侧同一帧序列读数 —— 第①类注入/复原(旧块原样移植)。
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
      /* 阈值逐字保留: |win - full| < 50。 */
      expect(Math.abs(hCmp.win - hCmp.full), `窗口化 ${hCmp.win} vs 全量 ${hCmp.full}px ` +
        `(Δ ${hCmp.win - hCmp.full}, 实测行间距 ${hCmp.gap}px)`).toBeLessThan(50);
    });

    test('滚动到底: 总高不塌陷(占位撑住) + 最后一屏有行且可见', async ({ page }) => {
      await gotoTorrents(page, skin);

      /* 滚到底: 总高度在滚动前后不塌陷, 且最后一行可见。
       * 400ms×2 不是装饰性等待: 行窗口化按滚动位置**异步补行**, 滚动后立刻读总高/末行
       * 会量到补行中间态 —— 两次滚动贴底 + settle 是测量程序的一部分(旧块同值同节奏)。 */
      const before = await page.evaluate('document.documentElement.scrollHeight');
      await page.evaluate('window.scrollTo(0, document.documentElement.scrollHeight)');
      await page.waitForTimeout(400);
      await page.evaluate('window.scrollTo(0, document.documentElement.scrollHeight)'); // 再滚一次(贴底)
      await page.waitForTimeout(400);
      const after = await page.evaluate('document.documentElement.scrollHeight');
      const lastHash = await page.$$eval('.torrent-row', (ns) => (ns.length ? ns[ns.length - 1].getAttribute('data-hash') : null));
      /* 末行视口相交读数(getBoundingClientRect, 第②类): locator 的 isVisible 不含视口相交语义。 */
      const lastVisible = await page.evaluate(() => {
        const ns = document.querySelectorAll('.torrent-row');
        if (!ns.length) return false;
        const r = ns[ns.length - 1].getBoundingClientRect();
        return r.top < window.innerHeight && r.bottom > 0;
      });
      /* 阈值逐字保留: |after - before| < 200。 */
      expect(Math.abs(after - before), `滚动到底不塌陷(占位撑住总高): ${before} -> ${after}px`).toBeLessThan(200);
      expect(lastVisible, `最后一屏有行且可见(末行 ${lastHash || '-'})`).toBe(true);
    });
  });
}
