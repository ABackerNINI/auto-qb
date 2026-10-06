/**
 * WEB UI 浏览器冒烟(Playwright + 桩服务) —— dev-only, 不参与打包
 *
 * 为什么需要: `agent-browser` 不支持 Windows, 而本项目有一整类故障"pytest 全绿但界面废掉"
 * (乐观 UI 不回滚、切视图数组被抹空、表头错位、行窗口化后滚动跳动)。本脚本用真实浏览器
 * 跑真实前端 + `scripts/ui_harness.py` 的合成后端, 把这类故障挡在提交前。
 *
 * 运行:
 *   1) uv run python scripts/ui_harness.py --torrents 3000 --port 8099
 *   2) node scripts/ui_smoke.cjs --base http://127.0.0.1:8099 --torrents 3000
 *
 * 依赖从哪来(2026-10-06 起本 clone 装了依赖, 优先级见下):
 *   ① 仓库内 `node_modules/playwright-core` —— `require()` 从本文件向上解析会**先**命中它,
 *      正常情况什么都不用设;
 *   ② 没有 `node_modules` 的 clone(它已 gitignore, 新 clone / 别的工作区不会有)则退回
 *      `NODE_PATH=<仓库外一次性安装的 node_modules>`, 例:
 *      `NODE_PATH=$HOME/.aqb-smoke-deps/node_modules node scripts/ui_smoke.cjs --base …`
 *   ③ 两条都不行时脚本会退到 `chromium.launch({channel:"msedge"})`(Edge 恒可用)。
 *   ❗脚本必须保持 **CJS(.cjs)**: ESM 的 `import` 不认 `NODE_PATH`, 退路 ② 会直接失效。
 *
 * 参数:
 *   --base       桩服务地址(默认 http://127.0.0.1:8099)
 *   --ui         prism|atlas|both(默认 both)
 *   --shots      截图目录(默认 .workbuddy-ai/tmp/ui-smoke)
 *   --torrents   期望种子总数(用于校验"总数正确", 默认 0=不校验)
 *   --expect-cmd ok|error|hang  与桩服务 --cmd-result 对应(默认 ok)
 *   (--skip-check on|off 已随 W5-off 精简轮迁入 e2e/menus.spec.mjs, S4 批 —— 本脚本不再支持)
 *   --hr-scene on|empty|off  与桩服务 --hr-scene 对应(默认 on): 仅 on 跑 HR 表③
 *                拉取历史断言组(计划 26-10-04-0312 S5); empty/off 场景行数断言不成立, 跳过
 *
 * 依赖: playwright-core(与已装的 chromium 版本对齐; 见文件末尾"版本对齐"注释)。
 */
const fs = require("fs");
const path = require("path");

let chromium;
// 先试 playwright-core: 本 clone 的 node_modules 里就有它(1.63 ↔ 本机 chromium-1243, 已对齐),
// `require` 向上解析会先命中; 无 node_modules 的 clone 靠 NODE_PATH 退路(见文件头「依赖从哪来」);
// 顶层 `playwright` 包只作最后兜底。
try {
  chromium = require("playwright-core").chromium;
} catch (e) {
  chromium = require("playwright").chromium;
}

const argv = (k, d) => {
  const i = process.argv.indexOf("--" + k);
  return i >= 0 && process.argv[i + 1] ? process.argv[i + 1] : d;
};

const BASE = argv("base", "http://127.0.0.1:8099");
const UI = argv("ui", "both");
const SHOTS = path.resolve(argv("shots", ".workbuddy-ai/tmp/ui-smoke"));
const EXPECT_N = parseInt(argv("torrents", "0"), 10);
const EXPECT_CMD = argv("expect-cmd", "ok");
/* --skip-check 两态参数与 W5-off 精简轮已于 2026-10-06 迁入 e2e/menus.spec.mjs(S4 批,
 * requireMode skipCheck 门控), 本脚本不再支持该参数。 */
const HR_SCENE = argv("hr-scene", "on");

const results = [];
const add = (ui, name, ok, detail) => {
  results.push({ ui, name, ok, detail });
  console.log(`${ok ? "PASS" : "FAIL"}  [${ui}] ${name}${detail ? " — " + detail : ""}`);
};

/**
 * Vue 根实例(读 renderMs 等埋点; 取不到返回 null, 相关项降级为跳过)。
 * !不能用 `__vue_app__._instance.proxy`: 实测 Vue 3.5.13 下 `_instance` 恒为空(键在但没值),
 * 走容器上的 `_vnode.component.proxy` 才拿得到(踩过一次, 别改回去)。
 */
const INST = "document.querySelector('#app')._vnode.component.proxy";

/*
 * 乐观态时序探针三件(armPending/armClick/readPending, 原 L83-117)已于 2026-10-06 随
 * W2 限速段退役(S4 批, 计划 26-10-06-0708 §3.3): 单点在 e2e/lib/probes.mjs, W2 的
 * armClick 用法范本见 e2e/menus.spec.mjs(armPending 预置 window.__p 的依赖在 lib 内自洽)。
 */

async function readInst(page, expr) {
  return page.evaluate(`(() => { const vm = ${INST}; return vm ? (${expr}) : null; })()`);
}

/*
 * 旧 hangChecks 常驻守阵三连(原 L153-216)与 pausableRow / CMD_URL 专属脚手架已于
 * 2026-10-06 迁入/并入 e2e/optimistic.spec.mjs(S3 批, 计划 26-10-06-0708 §3.3;
 * 对账映射表见该文件头)。armPending/armClick/readPending 探针三件已随 W2 限速段于
 * 同日 S4 批退役(单点在 e2e/lib/probes.mjs)。
 */

/*
 * 跳检旗标「关」态精简轮(skipCheckOffChecks, 原 L131-190)已于 2026-10-06 迁入
 * e2e/menus.spec.mjs 的「W5 off: fail-closed 门控精简组」(S4 批, 计划 26-10-06-0708
 * §3.3; 对账映射表见该文件头)。
 */

async function smokeUi(browser, ui) {
  // clipboard 权限: "复制磁力/种子名"类断言要真写剪贴板, headless 默认会拒
  const ctx = await browser.newContext({
    viewport: { width: 1440, height: 900 },
    permissions: ["clipboard-read", "clipboard-write"],
  });
  const page = await ctx.newPage();
  const errors = [];
  const warns = [];
  page.on("pageerror", (e) => errors.push("pageerror: " + e.message));
  page.on("console", (m) => {
    if (m.type() === "error") errors.push("console.error: " + m.text());
    if (m.type() === "warning") warns.push(m.text());
  });

  await page.goto(`${BASE}/${ui}/`, { waitUntil: "domcontentloaded" });
  // 首屏: 分组视图有行(种子数据经 /api/state 回来后渲染)
  await page.waitForFunction("document.querySelectorAll('.group-row').length > 0", null, { timeout: 30000 });
  /*
   * hang 模式独占轮(早退分支)已于 2026-10-06 迁入 e2e/optimistic.spec.mjs(S3 批) ——
   * 本脚本不再支持 --expect-cmd hang 专属轮, 该轮只应跑新轨。
   */
  await page.screenshot({ path: path.join(SHOTS, `${ui}-1-groups.png`) });

/* 跳检旗标「关」态早退分支已于 2026-10-06 随 skipCheckOffChecks 迁入 e2e/menus.spec.mjs(S4 批)。 */


  /*
   * 块A(渲染健康/分组视图/展开态跨视图/导航焦点/种子视图数据与总数/renderMs/状态栏速度/
   * 筛选器计数/轮询分档, 原 L288–470)已于 2026-10-06 迁入 e2e/views.spec.mjs(S1 批,
   * 计划 26-10-06-0708 §3.3; 对账映射表见该文件头)。此处只保留后续块(性能埋点/乐观 UI/
   * 菜单族/HR/列设置)依赖的脚手架: nav 页签引用 + 种子视图就位 + tRows/tTotal 读数
   * (块B 的 gbrBudget 与"行窗口化生效"断言要拿它们当输入)。
   */
  const nav = await page.$$("nav.tabs button");
  if (nav.length >= 3) {
    await nav[1].click();  // 种子
    await page.waitForFunction("document.querySelectorAll('.torrent-row').length > 0", null, { timeout: 15000 });
    const tRows = await page.$$eval(".torrent-row", (n) => n.length);
    const tTotal = await readInst(page, "vm.filteredTorrents.length");

    /*
     * 强制全量重渲染 N 轮, 用 PerformanceObserver(longtask) 量"主线程被占住多久" ——
     * 这才是"不跟手"的真身: renderMs 只测同步赋值, Vue 的 DOM patch 发生在之后的
     * 调度里, 埋点抓不到; longtask(>50ms 的任务)能把整表替换的真实阻塞量出来。
     * 行窗口化(P1-2)的收益就体现在这个数字上。
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
     * 渲染本身不该再触发它(只有元素被换掉的那一轮才会量一次)。
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
     * 只看长任务不够 —— 网络(4MB 载荷)两边一样大, 差的是 CPU 段; 故两个都记。
     */
    const rounds = 3;
    const bench = async (winOn) => page.evaluate(`(async () => {
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
    const off = await bench(false);
    const on = await bench(true);
    const lt = on.lt;
    const sum = lt.reduce((a, b) => a + b, 0);
    const avg = (a) => Math.round(a.reduce((x, y) => x + y, 0) / (a.length || 1));
    console.log(
      `      [A/B ${rounds} 轮] 全量: refresh ${off.ms.join("/")}ms, 长任务 ${off.lt.join("/") || "无"} | ` +
      `窗口化: refresh ${on.ms.join("/")}ms, 长任务 ${on.lt.join("/") || "无"}`
    );
    const gbr = await page.evaluate("window.__gbr");
    add(ui, "P1-2 单轮主线程阻塞下降", sum <= off.lt.reduce((a, b) => a + b, 0),
      `长任务 ${avg(off.lt)} -> ${avg(lt)} ms/轮; 整轮 refresh ${avg(off.ms)} -> ${avg(on.ms)} ms`);
    results[results.length - 1].longtaskAvgMs = avg(lt);
    /*
     * P1-3 之后唯一"按渲染次数"的布局读取是 P1-2 的**逐行测高**(行高不齐, 必须逐行记),
     * 量的是**窗口内**那几十行, 不是全表 —— 所以判据是"≤ 每轮渲染的行数 + 少量余量",
     * 而不是 0。全表量一次(首轮/改列)才是一次 O(N) 读取, 且只发生一次。
     */
    const gbrBudget = tRows * (rounds + 2) + 20;  // 上界按"窗口行数"给, 不是按全表行数
    add(ui, "P1-3 重渲染不再按全表强制布局", gbr <= gbrBudget,
      `${rounds} 轮共 ${gbr} 次(窗口内 ${tRows} 行/轮; 全表量法会是 ${tTotal * rounds} 次量级)`);
    await page.screenshot({ path: path.join(SHOTS, `${ui}-2-torrents.png`) });

    // P1-2 行窗口化: 数据远多于 DOM 行数 ⇒ 说明窗口生效(未窗口化时两者相等)
    if (EXPECT_N && EXPECT_N > 500) {
      add(ui, "P1-2 行窗口化生效", tRows < tTotal * 0.5, `DOM ${tRows} 行 << 数据 ${tTotal} 条`);
    }

    /*
     * P1-2 占位总高必须**等于全量渲染**的总高(窗口化只少渲染 DOM, 不改布局高度)。
     * !必须在**同一帧序列**里对照开关两侧: 早先只在"滚动前后"各读一次 scrollHeight,
     * 而那个读点发生在 bench(true) 把 rowWin 还原成 true **之后** ⇒ 两次量的都是窗口化
     * 高度, 恒等成立。正是这个读数时机让 prism 的行间距硬编码(6px vs 实际 5px)造成的
     * +2973px 偏差一路溜到提交(BUG-1 / TEST-2)。
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
    add(ui, "P1-2 占位总高 == 全量渲染", Math.abs(hCmp.win - hCmp.full) < 50,
      `窗口化 ${hCmp.win} vs 全量 ${hCmp.full}px (Δ ${hCmp.win - hCmp.full}, 实测行间距 ${hCmp.gap}px)`);
    results[results.length - 1].winHeight = hCmp.win;
    results[results.length - 1].fullHeight = hCmp.full;
    results[results.length - 1].rowGapPx = hCmp.gap;

    // 滚到底: 总高度在滚动前后不塌陷, 且最后一行可见
    const before = await page.evaluate("document.documentElement.scrollHeight");
    await page.evaluate("window.scrollTo(0, document.documentElement.scrollHeight)");
    await page.waitForTimeout(400);
    await page.evaluate("window.scrollTo(0, document.documentElement.scrollHeight)");  // 再滚一次(贴底)
    await page.waitForTimeout(400);
    const after = await page.evaluate("document.documentElement.scrollHeight");
    const lastHash = await page.$$eval(".torrent-row", (ns) => (ns.length ? ns[ns.length - 1].getAttribute("data-hash") : null));
    const lastVisible = await page.evaluate(() => {
      const ns = document.querySelectorAll(".torrent-row");
      if (!ns.length) return false;
      const r = ns[ns.length - 1].getBoundingClientRect();
      return r.top < window.innerHeight && r.bottom > 0;
    });
    add(ui, "滚动到底不塌陷(占位撑住总高)", Math.abs(after - before) < 200, `${before} -> ${after}px`);
    add(ui, "最后一屏有行且可见", lastVisible, `末行 ${lastHash || "-"}`);
    await page.screenshot({ path: path.join(SHOTS, `${ui}-3-torrents-bottom.png`) });
    await page.evaluate("window.scrollTo(0, 0)");
    await page.waitForTimeout(300);

    /*
    * 块C(单行暂停链/慢投递/值覆盖/批量合单, 原 L449-766)已于 2026-10-06 迁入
    * e2e/optimistic.spec.mjs(S3 批, 计划 26-10-06-0708 §3.3; 对账映射表见该文件头)。
    */

    /*
     * CTX-03 多选段(选中/未选中/合单为一条 bulk/按模式分流的乐观覆盖与回滚干净, 原 L777–851)
     * 已于 2026-10-06 迁入 e2e/multiselect-shows.spec.mjs(S2 批, 计划 26-10-06-0708 §3.3;
     * 对账映射表见该文件头)。选中集合改走真实 Ctrl+click, 不再 vm 注入。
     */

    /*
     * W2 批量限速/移动(原 L370-459)已于 2026-10-06 迁入 e2e/menus.spec.mjs(S4 批,
     * 计划 26-10-06-0708 §3.3; 对账映射表见该文件头): 批量菜单两项 + W5 四项齐 +
     * 限速载荷形状(留空方向不提交) + 成功回执 toast(仅 ok 模式; 旧 error 轮恒红系
     * 存量假红, 新轨修掉)。选中集合改走真实 Ctrl+click, 不再 vm 注入。
     */

    /*
     * W3 批量跳检(原 L461-583)已于 2026-10-06 迁入 e2e/menus.spec.mjs(S4 批): 单选/批量
     * 菜单跳检项(flags 开) + 危险确认链(取消不提交/确认恰好 1 条 bulk action=skip_check)。
     */

    /*
     * W4 多选导出(原 L585-648)已于 2026-10-06 迁入 e2e/menus.spec.mjs(S4 批): 菜单导出项
     * + 逐个请求(数 == 选中展开数, 无 bulk 合单) + W5 导出成功回执 toast。
     */

    /*
     * W4 组选中导出(原 L650-699)已于 2026-10-06 迁入 e2e/menus.spec.mjs(S4 批): 整组选中
     * 展开为成员 hash 闭包(selHashSet 全量), 请求数 == 组成员数; 误用 _bulkTargets 的
     * keys 通道会漏成员, 在此暴露。
     */

    /*
     * CTX-04/05/06 次级菜单(原 L701-768)已于 2026-10-06 迁入 e2e/menus.spec.mjs(S4 批):
     * 一级唯一入口(更多操作)/复制族并入/悬停父项子面板图标仍语义色(不变灰)/移出收起。
     */

    /*
    * 块E(整组暂停反馈/真值事件陈旧快照/复制磁力, 原 L1174-1295)已于 2026-10-06 迁入
    * e2e/optimistic.spec.mjs(S3 批, 计划 26-10-06-0708 §3.3; 对账映射表见该文件头)。
    */

    /*
     * 块F(追剧视图: 前行/集行乐观 + CTX-03 追剧多集 + 切回分组有数据 + CTX-03 辅种多组 +
     * BUG-8 刷新不空白, 原 L1376–1545)已于 2026-10-06 迁入 e2e/multiselect-shows.spec.mjs
     * (S2 批, 计划 26-10-06-0708 §3.3; 对账映射表见该文件头)。存量 flaky(集行 Ctrl+click
     * 落点拦截)的 trace 归因与对冲 arrange 一并落在该 spec 的 clickRow()。
     */
  }

  /*
   * 设置页位置持久化(2026-09-25 用户报"设置页刷新会回到种子页"): 顶层 page 与设置分区
   * (`hub.view`)原本都是**纯内存态** ⇒ F5 必掉回辅种页 + 设置首页, 编辑到一半的位置全丢。
   * 这里走真实手势(点设置 → 进分区 → 刷新)复现用户路径。
   * !断言里必须含 `cfg.schema` 非空 —— 只改初值不改启动路径的写法会让刷新停在
   * 「配置加载失败 + 重试」(设置页配置树是**按需加载**的), 而 page 值看着是对的。
   */
  {
    try {
      await page.click("nav.tabs-right button");   // 顶栏右侧「设置」
      await page.waitForSelector(".hb-grid .hb-card", { timeout: 20000 }).catch(() => null);
      const cards = await page.$$(".hb-grid .hb-card");
      if (cards.length) await cards[0].click();    // 进第一个分区(真实手势)
      await page.waitForTimeout(500);
      const read = `(() => { const vm = ${INST}; return {
        page: vm.page, hub: vm.hub.view, schema: !!vm.cfg.schema,
        crumb: (document.querySelector(".hb-crumb .cb-now") || {}).textContent || "",
        store: localStorage.getItem("autoqb.ui.page") + "|" + localStorage.getItem("autoqb.ui.hub"),
      }; })()`;
      const s1 = await page.evaluate(read);
      await page.reload({ waitUntil: "domcontentloaded" });
      await page.waitForTimeout(3500);   // 等鉴权 + 首轮轮询 + 补的那次 cfgLoad
      const s2 = await page.evaluate(read);
      add(ui, "设置页刷新保持位置(顶层页 + 分区 + 配置已加载)",
        cards.length > 0 && s1.page === "settings" && s1.schema && s1.hub !== "hub" && s1.crumb
        && s2.page === "settings" && s2.schema && s2.hub === s1.hub && s2.crumb === s1.crumb,
        `进入: ${JSON.stringify(s1)} 刷新后: ${JSON.stringify(s2)}`);
      // 收尾: 清掉位置偏好并回辅种页, 别把后续断言带到设置页
      await page.evaluate(`localStorage.removeItem("autoqb.ui.page"); localStorage.removeItem("autoqb.ui.hub");`);
      await page.click("nav.tabs button");
      await page.waitForTimeout(800);
    } catch (e) {
      add(ui, "设置页刷新保持位置(顶层页 + 分区 + 配置已加载)", false, e.message);
    }
  }

  /*
   * HR 拉取历史表③(计划 26-10-04-0312 S5): 桩 --hr-scene on(默认)起盘, 走真实手势
   * 设置页 → HR 分区 → 站点状态全屏弹层 → 表③ 首次展开(懒加载 fetch)→ 渲染。
   * 最小断言集 ×4, 只钉「真浏览器里这条链路活着」: 行 shape / 五形态徽章映射 / 过滤
   * 语义 / 展开态的穷举归 test_web.py 守阵(pytest 层), 这里不重复。empty/off 场景
   * (桩 --hr-scene empty/off)行集为空/未启用, 行数断言不成立 —— 配对参数下整组跳过。
   */
  if (HR_SCENE === "on") {
    try {
      await page.click("nav.tabs-right button");   // 顶栏右侧「设置」
      await page.waitForSelector(".hb-grid .hb-card", { timeout: 20000 }).catch(() => null);
      await page.evaluate(`${INST}.hubGo("hr_check")`);
      await page.evaluate(`${INST}.hrsToggle()`);  // 站点状态全屏弹层(块头部唯一展开钮)
      await page.waitForSelector(".hr-full-modal", { timeout: 10000 });
      await page.waitForFunction(`(() => { const vm = ${INST}; return vm.hrs.loaded; })()`, null, { timeout: 10000 });
      // 表③ = 弹层里 summary 带「拉取历史」的 details(表② 同类但文案不同); 真实点开,
      // @toggle -> hrsHistEnsureLoaded -> 首次 fetch /api/hr/history(limit=300)
      const hist = await page.evaluateHandle(`(() => {
        return [...document.querySelectorAll(".hr-full-modal details.hrs-diag")]
          .find((d) => ((d.querySelector("summary") || {}).textContent || "").includes("拉取历史")) || null;
      })()`);
      const histEl = hist.asElement();
      if (!histEl) throw new Error("表③ details(拉取历史)在全屏弹层里找不到");
      await histEl.click();
      await page.waitForSelector(".hr-full-modal .hr-hist-table .hr-hist-row", { timeout: 10000 });
      const nRows = await page.$$eval(".hr-full-modal .hr-hist-row", (ns) => ns.length);
      add(ui, "HR表③: 首次展开懒加载, 五形态行齐", nRows === 5, `${nRows} 行`);
      const tones = await page.evaluate(`(() => {
        const out = {};
        for (const el of document.querySelectorAll(".hr-full-modal .hr-hist-row .hr-hres")) {
          const t = [...el.classList].find((c) => c.startsWith("hr-hres-")) || "?";
          out[t] = (out[t] || 0) + 1;
        }
        return out;
      })()`);
      const okTones = ["ok", "warn", "dim", "err", "blue"].every((t) => tones["hr-hres-" + t] === 1);
      add(ui, "HR表③: 五档徽章各一且 result_tone 类落上", okTones, JSON.stringify(tones));
      await page.evaluate(`(() => {
        const hist = [...document.querySelectorAll(".hr-full-modal details.hrs-diag")]
          .find((d) => ((d.querySelector("summary") || {}).textContent || "").includes("拉取历史"));
        [...hist.querySelectorAll(".hr-chip")].find((c) => c.textContent.includes("仅看异常")).click();
      })()`);
      await page.waitForTimeout(250);
      const nBad = await page.$$eval(".hr-full-modal .hr-hist-row", (ns) => ns.length);
      add(ui, "HR表③: 仅看异常本地过滤生效(defer+通道不可用)", nBad === 2, `${nBad} 行`);
      await page.evaluate(`${INST}.hrsHist.badOnly = false`);   // 复原全量行集
      await page.waitForTimeout(200);
      const first = (await page.$$(".hr-full-modal .hr-hist-row"))[0];
      await first.click();                                       // 行点击 -> hrsHistToggleRow
      await page.waitForSelector(".hr-full-modal .hr-hist-sub", { timeout: 5000 });
      const sub = await page.$eval(".hr-full-modal .hr-hist-sub", (el) => (el.textContent || "").trim());
      add(ui, "HR表③: 行展开明细子行可见(完成行三档)",
        sub.includes("A 考察中") && sub.includes("3 页 / 96 行"), sub.slice(0, 70));
      // 收尾: 关弹层回种子页, 别把后续断言带到设置页(与上一块同一套清理)
      await page.evaluate(`${INST}.hrsCollapse()`);
      await page.evaluate(`${INST}.hubBack()`);
      await page.evaluate(`localStorage.removeItem("autoqb.ui.page"); localStorage.removeItem("autoqb.ui.hub");`);
      await page.click("nav.tabs button");
      await page.waitForTimeout(800);
    } catch (e) {
      add(ui, "HR表③: 桩走查断言组", false, e.message);
      await page.evaluate(`(() => { try { ${INST}.hrsCollapse(); ${INST}.hubBack();
        localStorage.removeItem("autoqb.ui.page"); localStorage.removeItem("autoqb.ui.hub"); } catch (err) {} })()`).catch(() => {});
      await page.click("nav.tabs button").catch(() => {});
      await page.waitForTimeout(500);
    }
  }

  /* 列设置多标签页同步(issue 26-09-20-1800): 两个标签各改一次列, 谁也不许吞掉谁。
   * 旧实现: 每个标签各持"页面加载时的快照" + saveColState 整份写回 ⇒ **last-writer-wins**,
   * 先改的那个标签的改动被静默吞掉 —— 用户在真机上的说法是"列设置经常被重置"。
   * 判据: 标签 2 必须在**标签 1 改动之前**就已加载(否则读到的是最新存储, 验不出问题)。 */
  try {
    const p2 = await ctx.newPage();
    await p2.goto(`${BASE}/${ui}/`, { waitUntil: "domcontentloaded" });
    await p2.waitForFunction("document.querySelectorAll('.group-row').length > 0", null, { timeout: 30000 });
    const hideCol = async (pg, idx) => {
      await pg.click(".col-picker button.table-tool");
      await pg.waitForSelector(".col-menu .col-menu-item", { timeout: 5000 });
      const items = await pg.$$(".col-menu .col-menu-item");
      await items[idx].click();
      await pg.waitForTimeout(400);
      await pg.keyboard.press("Escape");
      await pg.waitForTimeout(200);
    };
    await hideCol(page, 3);            // 标签 1 先改
    await page.waitForTimeout(600);    // 等 storage 事件把改动推给标签 2
    await hideCol(p2, 5);              // 标签 2(旧快照)再改
    await page.waitForTimeout(600);
    const got = await page.evaluate(`JSON.stringify(${INST}.colHidden.group || [])`);
    add(ui, "列设置多标签页互不覆盖", JSON.parse(got).length >= 2, `hidden.group = ${got}`);
    await p2.close();
  } catch (e) {
    add(ui, "列设置多标签页互不覆盖", false, e.message);
  }

  /* ---------- 双轨模型守阵(plan 26-09-21-1551 §7.2) ----------
   * 旧模型六轮修复各自封通道; 新模型把"意图/生效分轨 + 单一漏斗"钉在真浏览器手势上。 */
  const colHide = async (pg, idx) => {
    await pg.click(".col-picker button.table-tool");
    await pg.waitForSelector(".col-menu .col-menu-item", { timeout: 5000 });
    const items = await pg.$$(".col-menu .col-menu-item");
    await items[idx].click();
    await pg.waitForTimeout(400);
    await pg.keyboard.press("Escape");
    await pg.waitForTimeout(200);
  };
  const dragCol = async (pg) => {
    const h = await pg.$(".group-head .h-cell:nth-child(2) .resizer");
    const bb = await h.boundingBox();
    await pg.mouse.move(bb.x + 5, bb.y + bb.height / 2);
    await pg.mouse.down();
    await pg.mouse.move(bb.x + 65, bb.y + bb.height / 2, { steps: 6 });
    await pg.mouse.up();
    await pg.waitForTimeout(300);
  };
  const colState = (pg) => pg.evaluate(`(() => { const vm = ${INST}; return JSON.stringify({ w: vm.colW, h: vm.colHidden }); })()`);
  const clearCols = (pg) => pg.evaluate(() => { localStorage.removeItem("autoqb_cols_v5"); localStorage.removeItem("autoqb_cols_v4"); });

  // 守阵 1: 异视口双窗互不吞 + F3 冻结恢复 —— A(1600) 拖宽固化, B(1000) 隐藏列, 互相采纳;
  // 旧模型此处 B 窗口算出的 px 会写进存储, A 刷新即被改写(失败分析 R2~R4 真机实测)。
  try {
    const pa = await ctx.newPage();
    await pa.setViewportSize({ width: 1600, height: 900 });
    await pa.goto(`${BASE}/${ui}/`, { waitUntil: "domcontentloaded" });
    await clearCols(pa);
    await pa.reload({ waitUntil: "domcontentloaded" });
    await pa.waitForFunction("document.querySelectorAll('.group-row').length > 0", null, { timeout: 30000 });
    const pb = await ctx.newPage();
    await pb.setViewportSize({ width: 1000, height: 700 });
    await pb.goto(`${BASE}/${ui}/`, { waitUntil: "domcontentloaded" });
    await pb.waitForFunction("document.querySelectorAll('.group-row').length > 0", null, { timeout: 30000 });
    await dragCol(pa);            // A 拖宽 -> group 固化(colW 非空)
    await colHide(pb, 5);         // B(更窄窗口)隐藏一列
    await pa.waitForTimeout(600); // 等 storage 事件把 B 的改动推给 A
    const ra = JSON.parse(await colState(pa));
    const okMerge = Object.keys(ra.w.group || {}).length > 0 && (ra.h.group || []).length >= 1;
    await colHide(pa, 3);         // A 再改一次
    // F3 补漏: 模拟 B 被冻结后恢复可见(hidden -> visible 各派发一次)
    await pb.evaluate(`Object.defineProperty(document, "hidden", { value: true, configurable: true });
      document.dispatchEvent(new Event("visibilitychange"));
      Object.defineProperty(document, "hidden", { value: false, configurable: true });
      document.dispatchEvent(new Event("visibilitychange"));`);
    await pb.waitForTimeout(500);
    const rb = JSON.parse(await colState(pb));
    const okF3 = (rb.h.group || []).length >= 2;
    await pa.reload({ waitUntil: "domcontentloaded" });   // 刷新后两者都必须还在
    await pa.waitForFunction("document.querySelectorAll('.group-row').length > 0", null, { timeout: 30000 });
    const ra2 = JSON.parse(await colState(pa));
    const okReload = Object.keys(ra2.w.group || {}).length > 0 && (ra2.h.group || []).length >= 2;
    add(ui, "列设置·异视口双窗互不吞+F3", okMerge && okF3 && okReload,
      `A=${JSON.stringify(ra)} B=${JSON.stringify(rb)} 重载=${JSON.stringify(ra2)}`);
    await pa.close();
    await pb.close();
  } catch (e) {
    add(ui, "列设置·异视口双窗互不吞+F3", false, e.message);
  }

  // 守阵 2: 全自动页的派生 px 绝不落盘 —— 意图动作后存储里 w 必须是 null(铁律的行为面)
  try {
    const pt = await ctx.newPage();
    await pt.goto(`${BASE}/${ui}/`, { waitUntil: "domcontentloaded" });
    await pt.waitForFunction("document.querySelectorAll('.group-row').length > 0", null, { timeout: 30000 });
    await pt.evaluate(`${INST}.toggleColumn("torrent", "size")`);
    await pt.waitForTimeout(300);
    const blob = JSON.parse(await pt.evaluate(`localStorage.getItem("autoqb_cols_v5") || "{}"`));
    const tw = blob.pages && blob.pages.torrent ? blob.pages.torrent.w : undefined;
    const okNull = tw === null;
    await pt.evaluate(`${INST}.toggleColumn("torrent", "size")`);   // 还原显隐
    add(ui, "列设置·全自动页不落px", okNull, `pages.torrent.w = ${JSON.stringify(tw)}`);
    await pt.close();
  } catch (e) {
    add(ui, "列设置·全自动页不落px", false, e.message);
  }

  // 守阵 3: 隐藏列宽度保留 —— 固化页 隐藏一列 -> 再拖宽 -> 重新显示, 该列 px 必须原样回来
  // (旧模型 _renderedWidths 只含可见列却整段替换, 失败分析 S4 实测 11→10 键)
  // !被隐藏列的 key 必须在隐藏**前**从 _visibleCols 取 —— 2026-09-28 辅种扩列给列定义加了
  //   hide:true 默认隐藏列后, colHidden.group 里常驻 amount_left 等默认隐藏键, 隐藏后取
  //   colHidden[0] 拿到的是从未有过意图宽度的默认隐藏列(固化只固化**可见列**), 它"读不回 px"
  //   是双轨模型的正确行为(显示时由 toggleColumn 按 templateMinPx 合成), 不是回归 —— 用例
  //   26-09-30-0602 的 前=undefined 后=92px 即此。断言的对象应是"被本用例隐藏的那一列"。
  try {
    const ph = await ctx.newPage();
    await ph.goto(`${BASE}/${ui}/`, { waitUntil: "domcontentloaded" });
    await clearCols(ph);
    await ph.reload({ waitUntil: "domcontentloaded" });
    await ph.waitForFunction("document.querySelectorAll('.group-row').length > 0", null, { timeout: 30000 });
    await dragCol(ph);   // 固化 group
    const s1 = JSON.parse(await colState(ph));
    const k = await ph.evaluate(`${INST}._visibleCols("group")[2].key`);   // 被隐藏列(隐藏前取, 见上)
    await ph.evaluate(`${INST}.toggleColumn("group", ${JSON.stringify(k)})`);
    await ph.waitForTimeout(200);
    const s2 = JSON.parse(await colState(ph));
    await dragCol(ph);   // 再拖宽(旧模型此处抹掉隐藏列 px)
    await ph.evaluate(`(() => { ${INST}.toggleColumn("group", ${JSON.stringify(k)}); })()`);
    await ph.waitForTimeout(300);
    const s3 = JSON.parse(await colState(ph));
    const okKeep = !!(k && s2.h.group && s2.h.group.includes(k) && s1.w.group && s1.w.group[k] && s3.w.group && s3.w.group[k] === s1.w.group[k]);
    add(ui, "列设置·隐藏列宽度保留", okKeep, `key=${k} 前=${JSON.stringify(s1.w.group && s1.w.group[k])} 后=${JSON.stringify(s3.w.group && s3.w.group[k])}`);
    await ph.close();
  } catch (e) {
    add(ui, "列设置·隐藏列宽度保留", false, e.message);
  }

  // 守阵 4: v4→v5 迁移 —— 固化页宽度保留 / 非固化页污染 px 清零 / 隐序保留; 首次意图动作落 v5
  try {
    const pm = await ctx.newPage();
    await pm.goto(`${BASE}/${ui}/`, { waitUntil: "domcontentloaded" });
    await pm.evaluate(() => {
      localStorage.removeItem("autoqb_cols_v5");
      localStorage.setItem("autoqb_cols_v4", JSON.stringify({
        widths: { group: { uploaded: "300px" }, torrent: { name: "222px" } },
        hidden: { group: ["category"] },
        manual: { group: true, torrent: false },
        order: {},
      }));
    });
    await pm.reload({ waitUntil: "domcontentloaded" });
    await pm.waitForFunction("document.querySelectorAll('.group-row').length > 0", null, { timeout: 30000 });
    const m1 = JSON.parse(await pm.evaluate(`(() => { const vm = ${INST}; return JSON.stringify({ wg: vm.colW.group || null, hg: vm.colHidden.group || [], wt: vm.colW.torrent || null }); })()`));
    const okLoad = !!(m1.wg && m1.wg.uploaded === "300px" && (m1.hg || []).includes("category") && !m1.wt);
    await pm.evaluate(`${INST}.toggleColumn("group", "total_size")`);   // 一次意图动作 -> 落 v5
    await pm.waitForTimeout(300);
    const blob = JSON.parse(await pm.evaluate(`localStorage.getItem("autoqb_cols_v5") || "{}"`));
    const g = blob.pages && blob.pages.group;
    const okV5 = !!(blob.v === 5 && g && g.w && g.w.uploaded === "300px" && (g.hidden || []).includes("category")
      && (!blob.pages.torrent || blob.pages.torrent.w === null));
    add(ui, "列设置·v4→v5迁移", okLoad && okV5, `load=${JSON.stringify(m1)}`);
    await pm.close();
  } catch (e) {
    add(ui, "列设置·v4→v5迁移", false, e.message);
  }


  const perfWarns = warns.filter((w) => w.includes("[perf]"));
  if (perfWarns.length) console.log(`      [perf] ${perfWarns.length} 条: ${perfWarns.slice(0, 3).join(" | ")}`);
  add(ui, "无 console.error / pageerror", errors.length === 0, errors.slice(0, 3).join(" | ") || "干净");

  await ctx.close();
}

(async () => {
  fs.mkdirSync(SHOTS, { recursive: true });
  const browser = await chromium.launch();
  const uis = UI === "both" ? ["prism", "atlas"] : [UI];
  for (const ui of uis) {
    try {
      await smokeUi(browser, ui);
    } catch (e) {
      add(ui, "冒烟整体执行", false, e.message);
    }
  }
  await browser.close();
  const failed = results.filter((r) => !r.ok);
  console.log(`\n合计 ${results.length} 项, 失败 ${failed.length} 项; 截图目录: ${SHOTS}`);
  process.exit(failed.length ? 1 : 0);
})();

/*
 * 版本对齐(踩过的坑, 2026-10-06 复核更新): playwright 的版本必须与 `%LOCALAPPDATA%\ms-playwright`
 * 里已下载的 chromium **配对**, 否则报 "Executable doesn't exist"。
 *   当前配对(2026-10-06 实测可用): playwright-core **1.63.x ↔ chromium-1243**
 *   (`chromium-1243` / `chromium_headless_shell-1243` 在盘上; 旧的 chromium-1234 已不在)。
 *   历史配对: core 1.62 ↔ chromium-1234 —— 那段"装 1.62 绕开"的配方已过期, 别再照抄。
 * 现在本仓库 `package.json` 已把 `@playwright/test@1.63` 列为 devDependency, 所以 playwright-core
 * 就在仓库内 `node_modules/`, `require("playwright-core")` 直接命中, 无需 NODE_PATH。
 * 装了新包却没下对应浏览器时, 用 `npx playwright install chromium` 补(别指望它自己下)。
 * 运行时用 `require("playwright-core")` —— ESM 的 import 不认 NODE_PATH, 故本脚本用 CJS。
 */
