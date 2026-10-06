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
 *   --skip-check on|off  与桩服务 --skip-check-menu 对应(默认 on): off 走精简轮,
 *                只验 fail-closed 门控(单选/多选菜单都不渲染「跳检…」, 其余项照常)
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
/* 跳检菜单旗标两态(W5 汇总, 计划 26-10-02-1955): 与桩服务 --skip-check-menu 必须一致 ——
 * on(默认)跑全套(多选四项齐/单选跳检项/确认链); off 走精简轮只验 fail-closed 门控。 */
const SKIP_CHECK = argv("skip-check", "on");
/* HR 在线核实桩场景(计划 26-10-04-0312 S5): 与桩服务 --hr-scene 必须一致 ——
 * on(默认)跑表③拉取历史断言组; empty/off 场景下表③行集为空/未启用, 断言组跳过。 */
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

/**
 * 乐观态"生灭记录器"(2026-09-19 加, issue 26-09-19-2024 之后**必须**用它):
 * 真值对齐修好之前, pending 要挂满 3s 兜底 ⇒ "等 120ms 再数一次 .is-pending"这种采样稳过;
 * 修好之后 pending 只活 100~300ms, 事后再采样恒为 0 ⇒ 那些断言会**集体恒红**(不是回归, 是度量方式失效)。
 * 故统一改为: 点击前装记录器 → 点击 → 事后问"它**曾经**出现过吗 / 什么时候消失的"。
 */
async function armPending(page, sel = ".is-pending") {
  await page.evaluate(`(() => {
    const vm = ${INST};
    const SEL = ${JSON.stringify(sel)};
    window.__p = { t0: null, appear: null, gone: null, peak: 0, peakT: null, sel: SEL };
    const bump = () => {
      const p = window.__p;
      const n = Object.keys(vm.pendingOps || {}).length;
      if (n > p.peak) { p.peak = n; p.peakT = p.t0 ? Math.round(performance.now() - p.t0) : null; }
    };
    if (window.__pmo) window.__pmo.disconnect();
    window.__pmo = new MutationObserver(() => {
      const p = window.__p;
      const has = !!document.querySelector(p.sel);
      if (p.appear === null && has) p.appear = performance.now();
      if (p.appear !== null && p.gone === null && !has) p.gone = performance.now();
      bump();
    });
    window.__pmo.observe(document.body, { subtree: true, attributes: true, attributeFilter: ["class"], childList: true });
    clearInterval(window.__ptimer);
    window.__ptimer = setInterval(bump, 10);
  })()`);
}
/** 时刻基准取菜单项的 click 事件(捕获阶段), 不用 Playwright 的 click 时刻(含鼠标开销) */
async function armClick(page, handle) {
  await handle.evaluate((el) => el.addEventListener("click", () => { window.__p.t0 = performance.now(); }, { capture: true, once: true }));
}
async function readPending(page) {
  return page.evaluate(`(() => {
    clearInterval(window.__ptimer);
    const p = window.__p;
    const r = (x) => ((p.t0 && x) ? Math.round(x - p.t0) : null);
    return { appear: r(p.appear), gone: r(p.gone), peak: p.peak, peakT: p.peakT };
  })()`);
}
/** 找一个"可暂停"的行(未被暂停过的)。找不到就把第一行**恢复**一次再用 ——
 *  一轮冒烟会连续暂停几十个目标(批量 60 个), 后面的块很容易撞上"全是已暂停"。 */
async function pausableRow(page, rowSel, resumeText) {
  const pick = async () => {
    for (const r of await page.$$(rowSel)) {
      const cls = (await r.getAttribute("class")) || "";
      if (!cls.includes("s-paused")) return r;
    }
    return null;
  };
  let row = await pick();
  if (row || !resumeText) return row;
  const first = (await page.$$(rowSel))[0];
  if (!first) return null;
  await first.click({ button: "right" });
  await page.waitForSelector(".ctx-menu", { timeout: 5000 }).catch(() => null);
  for (const h of await page.$$(".ctx-item")) {
    const t = ((await h.textContent()) || "").trim();
    if (t.includes(resumeText)) { await h.click(); break; }
  }
  await page.waitForTimeout(1200);  // 等"恢复"的真值落回来
  return pick();
}

/** 命令投递端点(给 P0-3「补丁先于 POST」那一条注入人为延迟用)。
 *  !Playwright 新版的路由谓词收到的是 URL 对象而不是字符串, 别直接当 string 用。 */
const CMD_URL = (u) => {
  const s = typeof u === "string" ? u : String(u);
  return /\/api\/(torrents|groups)\/[^/?]+\/(pause|resume)(\?|$)/.test(s) || s.includes("/api/torrents/bulk");
};

async function readInst(page, expr) {
  return page.evaluate(`(() => { const vm = ${INST}; return vm ? (${expr}) : null; })()`);
}

/*
 * hang 模式(命令永不回执)的**常驻守阵** —— 只在 `--expect-cmd hang` 时跑, 且**独占**一轮
 * (不与其他断言混跑): hang 下前端 waitCmd 超时是 40s, 混进主轮会把一轮拖到十分钟。
 * 判的是「失败/未知绝不留永久假状态」这条红线在无回执场景下还成不成立:
 *   1. pending 立即出现(乐观) 2. 约 3s 后消失(兜底) 3. 消失后**状态色回到点击前**
 * 3. 是这条守阵的全部意义: 2026-09-19 之前兜底只 delete pendingOps 不回滚字段值, 而 rid 未变时
 *   服务端不回传数组、行对象不被替换 ⇒ 补丁值(kind:"paused")永久留在行上, 命令根本没执行
 *   界面却一直显示已暂停。ok / error 两轮都碰不到这条路径, 缺陷才躺到了现在(issue 26-09-19-2141)。
 */
async function hangChecks(page, ui) {
  const nav = await page.$$("nav.tabs button");
  if (nav.length >= 3) await nav[1].click();  // 种子视图
  await page.waitForFunction("document.querySelectorAll('.torrent-row').length > 0", null, { timeout: 15000 });
  await page.waitForTimeout(900);
  const row = await pausableRow(page, ".torrent-row", "开始该种子");
  if (!row) {
    add(ui, "P0-3 hang: 3s 兜底落回原状态", false, "找不到未暂停的行(且恢复失败)");
    return;
  }
  const hash = await row.evaluate((el) => el.getAttribute("data-hash"));
  const sCls = (c) => ((c || "").split(" ").find((x) => x.startsWith("s-")) || "");
  const before = sCls(await row.evaluate((el) => el.className));

  await page.evaluate(`(() => {
    const H = ${JSON.stringify(hash)};
    window.__h = { t0: null, rows: [] };
    window.__hi = setInterval(() => {
      const s = window.__h;
      if (s.t0 === null) return;
      const el = document.querySelector('.torrent-row[data-hash="' + H + '"]');
      s.rows.push({
        t: Math.round(performance.now() - s.t0),
        pend: el ? el.className.includes('is-pending') : null,
        cls: el ? ((el.className.split(' ').find((x) => x.startsWith('s-')) || '')) : null,
      });
    }, 10);
  })()`);
  await row.click({ button: "right" });
  await page.waitForSelector(".ctx-menu", { timeout: 5000 }).catch(() => null);
  for (const h of await page.$$(".ctx-item")) {
    const t = ((await h.textContent()) || "").trim();
    if (t.includes("暂停该种子") || t === "暂停") {
      await h.evaluate((el) => el.addEventListener("click", () => { window.__h.t0 = performance.now(); }, { capture: true, once: true }));
      await h.click();
      break;
    }
  }
  /* 兜底 3s + 轮询周期(1500 种子 → 2s) ⇒ 最长约 5s; 留到 6.5s 保证采到"消失"那一帧。 */
  await page.waitForTimeout(6500);
  const rows = await page.evaluate(`(() => { clearInterval(window.__hi); return window.__h.rows; })()`);
  const i0 = rows.findIndex((r) => r.pend);
  const appear = i0 >= 0 ? rows[i0].t : null;
  let gone = null;
  if (i0 >= 0) for (let j = i0; j < rows.length; j++) if (!rows[j].pend) { gone = rows[j].t; break; }
  const after = rows.length ? rows[rows.length - 1].cls : null;

  add(ui, "P0-3 hang: 无回执时立刻可见 pending(乐观)", appear !== null && appear < 500,
    `点击 → 出现 ${appear === null ? "从未出现" : appear + "ms"}`);
  add(ui, "P0-3 hang: 3s 兜底清除 pending", gone !== null && gone >= 2500 && gone <= 6000,
    `点击 → 消失 ${gone === null ? "始终未消失" : gone + "ms"}(须 2500~6000ms)`);
  /* 光"消失"不够 —— 回滚也会让它消失。**必须落回点击前的状态色**, 证明兜底真的把补丁撤了。 */
  add(ui, "P0-3 hang: 兜底后落回原状态(不留假状态)", after !== null && after === before,
    `${before} -> ${after}`);
}

/*
 * 跳检菜单旗标「关」态精简轮(W5 汇总, 计划 26-10-02-1955): 桩 --skip-check-menu off 起盘,
 * 走真实 /api/webui/flags -> state.flags -> v-if 链, 验 fail-closed 门控 ——
 *   1. flags 取到**布尔 false**(不是"没取到"的 undefined 形态 —— v-if 对 undefined 也隐藏,
 *      那是另一档故障, 端点断链会被误判成门控生效);
 *   2. 单选菜单不渲染「跳检…」(限速… 仍在 ⇒ 菜单本身正常, 缺的只是被门控的高危项);
 *   3. 多选菜单同样不渲染「跳检…」(限速/移动/导出 三项照常 ⇒ 门控只藏高危项)。
 * 后端 gate 的 403 双态由 pytest 兜底(test_web.py), 这里只管前端渲染面。
 */
async function skipCheckOffChecks(page, ui) {
  await page.waitForFunction(
    `(() => { const vm = ${INST}; return !!vm.flags && typeof vm.flags.skip_check_menu === "boolean"; })()`,
    null, { timeout: 10000 }
  ).catch(() => null);
  const flag = await readInst(page, "vm.flags ? vm.flags.skip_check_menu : null");
  add(ui, "W5 off: flags 取到 skip_check_menu=false(fail-closed)", flag === false, `flags.skip_check_menu=${JSON.stringify(flag)}`);

  const nav = await page.$$("nav.tabs button");
  if (nav.length >= 3) await nav[1].click();  // 种子视图
  await page.waitForFunction("document.querySelectorAll('.torrent-row').length > 0", null, { timeout: 15000 });
  await page.waitForTimeout(500);
  const menuTexts = async () => {
    await page.waitForSelector(".ctx-menu", { timeout: 5000 }).catch(() => null);
    return page.$$eval(".ctx-item", (ns) => ns.map((n) => n.textContent.trim()));
  };
  const row0 = (await page.$$(".torrent-row"))[0];
  if (!row0) {
    add(ui, "W5 off: 单选/多选菜单无跳检项", false, "页面上没有 .torrent-row 可右键");
    return;
  }
  // 单选: 不选中任何行直接右键
  await row0.click({ button: "right" });
  const single = await menuTexts();
  add(ui, "W5 off: 单选菜单不渲染跳检项(限速仍在)",
    single.some((t) => t.includes("限速…")) && !single.some((t) => t.includes("跳检…")),
    `单选菜单: ${single.slice(0, 10).join(" / ") || "(未打开)"}`);
  // 多选: 选 3 行右键选中锚点
  const selHashes = await page.evaluate(`(() => {
    const vm = ${INST};
    vm.selGroups = [];
    vm.selMembers = vm.filteredTorrents.slice(0, 3).map((r) => r.hash);
    return vm.selMembers.slice();
  })()`);
  let anchor = null;
  for (const r of await page.$$(".torrent-row")) {
    const h = await r.evaluate((el) => el.getAttribute("data-hash"));
    if (selHashes.includes(h)) { anchor = r; break; }
  }
  let multi = [];
  if (anchor) {
    await anchor.click({ button: "right" });
    multi = await menuTexts();
  }
  add(ui, "W5 off: 多选菜单不渲染跳检项(限速/移动/导出照常)",
    multi.some((t) => t.includes("限速…")) && multi.some((t) => t.includes("移动…"))
      && multi.some((t) => t.includes("导出 .torrent")) && !multi.some((t) => t.includes("跳检…")),
    `多选菜单: ${multi.slice(0, 11).join(" / ") || "(未打开)"}`);
  await page.keyboard.press("Escape");
  await page.waitForTimeout(150);
}

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
  /* hang 模式独占一轮: 它只验 3s 兜底, 主轮那些断言在 40s 的命令超时下会拖到十分钟 */
  if (EXPECT_CMD === "hang") {
    await hangChecks(page, ui);
    add(ui, "无 console.error / pageerror", errors.length === 0, errors.slice(0, 3).join(" | ") || "干净");
    await ctx.close();
    return;
  }
  await page.screenshot({ path: path.join(SHOTS, `${ui}-1-groups.png`) });

  /* 跳检旗标「关」态精简轮(W5): 只验 fail-closed 门控 —— 主轮那些断言(四项齐/确认链等)都
   * 假定 flags 开, 在关态下会假红, 故独占一轮(与 hang 模式同款早退)。 */
  if (SKIP_CHECK === "off") {
    await skipCheckOffChecks(page, ui);
    add(ui, "无 console.error / pageerror", errors.length === 0, errors.slice(0, 3).join(" | ") || "干净");
    await ctx.close();
    return;
  }


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

    // P0-3 乐观 UI: 右键 → 暂停 → 立刻出现 pending, 且最终不留假状态
    const row0 = await pausableRow(page, ".torrent-row", "开始该种子");
    if (!row0) {
      add(ui, "P0-3 右键菜单有暂停项", false, "找不到可暂停的种子行(且恢复失败)");
    } else {
      await row0.click({ button: "right" });
      await page.waitForSelector(".ctx-menu", { timeout: 5000 }).catch(() => null);
      await page.screenshot({ path: path.join(SHOTS, `${ui}-4-ctxmenu.png`) });
      const items = await page.$$eval(".ctx-item", (ns) => ns.map((n) => n.textContent.trim()));
      const handles = await page.$$(".ctx-item");
      let clicked = false;
      for (const h of handles) {
        const t = (await h.textContent()) || "";
        if (t.includes("暂停该种子") || t.includes("暂停整组") || t.trim() === "暂停") {
          await armPending(page);   // 记录器必须在点击**之前**装好
          await armClick(page, h);
          await h.click();
          clicked = true;
          break;
        }
      }
      if (!clicked) {
        add(ui, "P0-3 右键菜单有暂停项", false, `菜单项: ${items.slice(0, 8).join(" / ")}`);
      } else {
        await page.waitForTimeout(400);
        const p = await readPending(page);
        await page.screenshot({ path: path.join(SHOTS, `${ui}-5-pending.png`) });
        if (EXPECT_CMD === "error") {
          console.log(`      [info] error 模式: pending 出现过 ${p.appear !== null ? p.appear + "ms" : "否"}`);
        } else {
          /* 判"曾经出现过"而不是"此刻还有" —— 真值对齐修好后 pending 只活 100~300ms,
           * 事后再数必然是 0(见 armPending 的注释)。 */
          add(ui, "P0-3 点击后立即可见 pending(乐观)", p.appear !== null,
            `点击 → 出现 ${p.appear === null ? "从未出现" : p.appear + "ms"}`);
        }
      }
    }
    {
      /*
       * 成功回执后 pending 会一直贴到"真值对齐"(或 3s 兜底) —— 立刻清会出现"先变过去、
       * 下一轮又弹回来"。这里等到彻底干净再断言"不留假状态"; hang 模式靠 3s 兜底。
       */
      let pendingLater = -1, pendingOps = -1, waited = 0;
      while (waited < 8000) {
        await page.waitForTimeout(250);
        waited += 250;
        pendingLater = await page.$$eval(".torrent-row.is-pending, .group-row.is-pending", (n) => n.length);
        pendingOps = await readInst(page, "Object.keys(vm.pendingOps || {}).length");
        if (pendingLater === 0 && pendingOps === 0) break;
      }
      add(ui, `P0-3 回执(${EXPECT_CMD})后不留假状态`, pendingLater === 0 && pendingOps === 0,
        `${waited}ms 后: 残留 ${pendingLater} 行 / pendingOps ${pendingOps}`);
    }

    /*
     * P0-3「点击即变」回归守阵(issue 26-09-19-1939-webui-optimistic-latency):
     * 人为把命令 POST 拖慢(route 注入 800ms), 行仍必须**在 POST 返回之前**就变灰 ——
     * 这判的就是"补丁贴在第几行", 不是"网络快不快"。
     * 背景: 修之前 `act()` / `actTorrent()` 把 applyOptimistic 放在 `await POST` **之后**,
     * 而桩服务回执是瞬时的 ⇒ 本地永远测不出来, 真机大库下 POST 慢到秒级才暴露
     * (用户报"点了 2-4s 才有反应")。受控注入 2000ms 实测: 修前补丁 2012ms, 修后 0ms。
     * 判据 400ms = 远小于注入的 800ms、又远高于本地正常的 ~10ms。
     */
    {
      const DELAY = 800;
      const BUDGET = 400;
      await page.unrouteAll({ behavior: "ignoreErrors" }).catch(() => {});
      await page.route(CMD_URL, async (route) => {
        await new Promise((r) => setTimeout(r, DELAY));
        await route.continue();
      });
      // 挑一个**未暂停**的行(pausableRow 会在全是已暂停时先"恢复"一个)
      const target = await pausableRow(page, ".torrent-row", "开始该种子");
      if (!target) {
        add(ui, "P0-3 补丁先于 POST(慢投递不挡反馈)", false, "找不到未暂停的行");
      } else {
        await target.click({ button: "right" });
        await page.waitForSelector(".ctx-menu", { timeout: 5000 }).catch(() => null);
        const handles = await page.$$(".ctx-item");
        let clicked = false;
        let lat = null;
        for (const h of handles) {
          const t = ((await h.textContent()) || "").trim();
          if (!t.includes("暂停该种子") && t.trim() !== "暂停" && !t.includes("暂停整组")) continue;
          await page.evaluate(`(() => {
            window.__m = { t0: null, dom: null };
            if (window.__mo2) window.__mo2.disconnect();
            window.__mo2 = new MutationObserver(() => {
              if (window.__m.dom === null && document.querySelector(".is-pending")) window.__m.dom = performance.now();
            });
            window.__mo2.observe(document.body, { subtree: true, attributes: true, attributeFilter: ["class"], childList: true });
          })()`);
          // 时刻取菜单项的 click 事件(捕获阶段) —— 不用 Playwright 的 click 时刻, 那含鼠标开销
          await h.evaluate((el) => el.addEventListener("click", () => { window.__m.t0 = performance.now(); }, { capture: true, once: true }));
          await h.click();
          clicked = true;
          const deadline = Date.now() + DELAY + 1500;
          while (Date.now() < deadline) {
            lat = await page.evaluate("(() => { const m = window.__m; return (m.t0 && m.dom) ? Math.round(m.dom - m.t0) : null; })()");
            if (lat !== null) break;
            await page.waitForTimeout(20);
          }
          break;
        }
        add(ui, `P0-3 补丁先于 POST(注入 ${DELAY}ms 仍即时)`, clicked && lat !== null && lat < BUDGET,
          `点击 → is-pending ${lat === null ? "未出现" : lat + "ms"}(阈值 ${BUDGET}ms)`);
      }
      await page.unrouteAll({ behavior: "ignoreErrors" }).catch(() => {});
      await page.waitForTimeout(1200);  // 让被拖慢的命令走完回执/回滚
      /* 补丁提前了, "发送失败"这条路径也跟着变了(原来补丁还没贴, 现在必须显式回滚) */
      const pend = await readInst(page, "Object.keys(vm.pendingOps || {}).length");
      if (EXPECT_CMD === "error") {
        const pendRows = await page.$$eval(".torrent-row.is-pending, .group-row.is-pending", (n) => n.length);
        add(ui, "P0-3 慢投递 + 失败回执后回滚干净", pend === 0 && pendRows === 0, `pendingOps ${pend} / 残留行 ${pendRows}`);
      } else {
        console.log(`      [info] ok 模式: 慢投递后 pendingOps ${pend}(真值对齐前不清, 属预期)`);
      }
      await page.waitForTimeout(2600);  // 等 3s 兜底窗口过, 免得污染后面的断言
    }

    /*
     * P0-3 真值对齐(issue 26-09-19-2024): 点击 → 乐观态**消失**必须够快。
     * 与上面「补丁先于 POST」是**两段**: 上面管"变灰快不快", 这里管"恢复正常快不快"。
     * 修之前: pendingOps 只有 3s 超时一个出口(真值到了也不清) + 回执后不刷新 ⇒ 实测 3.1~3.4s;
     * 修之后: 回执后立刻拉真值(带退避重试) + 真值匹配即清 ⇒ 应 < 1s。
     * WARN: 前提是桩服务**真的改状态**(ui_harness.py::_apply_truth) —— 否则真值永不到,
     *   这条断言只会测到"走满 3s 兜底", 跟没测一样(这正是本条缺陷当初溜过去的原因)。
     *
     * !**这里量的是两段, 不是一段**(2026-09-22 修订 —— 此前双 UI 各 1 条恒红, 根因是量错了对象):
     * D2(`0c18fcd`)之后乐观态拆成了两条独立的时间线, 而旧断言把两者混成一个:
     *   1. 压暗(`.is-pending`)—— 回执到达即结束, 设计值就是十几~几十 ms(真机实测撤下 85ms);
     *   2. 值覆盖(`pendingOps`)—— 压暗结束后继续盖住行值, 直到"服务端快照同意"才释放,
     *      这才是"等真值"的那一段(桩里真值 +120ms 落 ⇒ 再经 ver 去抖 + 一轮 refresh ⇒ 实测 350~400ms)。
     * 旧断言拿 DOM 上的 `.is-pending` 消失去卡"≥80ms 才证明等了真值" ⇒ 1. 只有 17~22ms,
     * **必然**低于下界 ⇒ 双 UI 恒红, 而代码一直是对的。
     * ⇒ 现在 1. 量 DOM、上界 250ms(回归形态: 压暗不随回执结束 ⇒ 挂到值覆盖释放才消失 ≈350ms;
     *    再坏一层撤下退化回 D2 前的 ~3s 也一样红);
     *    2. 量 `pendingOps` 归零、仍卡 80~1000ms(回归形态: 走满 3s 兜底, 或回执即释放 ⇒ <80ms)。
     */
    {
      const BUDGET = 1000;        // 2. 值覆盖释放的上界(3s 兜底是它的回归形态)
      /* 1. 的上界 —— !**不是**拍脑袋的 400: 压暗若没随回执结束, DOM 上的 `.is-pending` 会一直挂到
       * **值覆盖释放**(pendingOps 清空)才消失, 而桩里那一段实测 ~350ms(真值 120ms + ver 去抖 60ms
       * + 一轮 refresh ~140ms)。上界取 400 的话"压暗不结束"会**擦线过关**(实测 349/374ms),
       * 故压到 250: 正常路径 ~20ms(12 倍余量), 退化路径 ~350ms(必红)。
       * WARN: 该间隔随库规模浮动(refresh 越慢退化值越大), 小库下退化值会更靠近 250; --torrents 3000 是定阈值时的口径。 */
      const GREY_BUDGET = 250;
      /* 2. 的采样间隔: pendingOps 是**响应式对象、DOM 上看不见**, 没有 MutationObserver 可用,
       * 只能定时采样。4ms 远小于最短窗口(error 模式回滚 ~21ms), 不至于漏采整个起落。 */
      /*
       * !挑目标**之前**先与服务端真值对齐一次。否则会空过: 上面的块刚暂停过若干行, 桩服务
       * 真值已经改了, 但前端要等下一轮轮询(2s)才在 DOM 上反映 —— 此时按"class 没有 s-paused"
       * 挑出来的行其实**服务端已是 paused**, 点暂停后真值瞬间匹配 ⇒ pending 0~20ms 就清,
       * 断言恒绿却什么都没测到(2026-09-19 实测就是这样: 19ms)。
       */
      await page.evaluate(`(() => { const vm = ${INST}; return vm.refresh && vm.refresh(); })()`);
      await page.waitForTimeout(400);
      /* error 模式没有"等真值"这回事: 命令失败 ⇒ 立即回滚(实测 ~21ms)。给它套下界会恒红,
       * 而"某种模式下恒红的断言"和"恒真的断言"一样没用 —— 失败路径由上面的
       * 「失败后落回原状态 / 回滚干净」两条覆盖, 这里只要求"快"。 */
      const FLOOR = EXPECT_CMD === "error" ? 0 : 80;
      const target2 = await pausableRow(page, ".torrent-row", "开始该种子");
      if (!target2) {
        add(ui, `P0-3 值覆盖及时落回真值(${FLOOR}~${BUDGET}ms)`, false, "找不到未暂停的行");
        add(ui, `P0-3 压暗在回执后及时撤下(<${GREY_BUDGET}ms)`, false, "找不到未暂停的行");
      } else {
        const beforeKind = await target2.evaluate((el) => {
          const c = el.className.split(" ").find((x) => x.startsWith("s-"));
          return c || "(无)";
        });
        await target2.click({ button: "right" });
        await page.waitForSelector(".ctx-menu", { timeout: 5000 }).catch(() => null);
        const hs = await page.$$(".ctx-item");
        let clicked2 = false;
        let clear = null;
        for (const h of hs) {
          const t = ((await h.textContent()) || "").trim();
          if (!t.includes("暂停该种子") && t.trim() !== "暂停" && !t.includes("暂停整组")) continue;
          await page.evaluate(`(() => {
            const vm = ${INST};
            window.__t = { t0: null, dom0: null, clear: null, opsUp: null, opsDown: null };
            if (window.__mo3) window.__mo3.disconnect();
            window.__mo3 = new MutationObserver(() => {
              const m = window.__t;
              if (m.dom0 === null && document.querySelector(".is-pending")) m.dom0 = performance.now();
              if (m.dom0 !== null && m.clear === null && !document.querySelector(".is-pending")) m.clear = performance.now();
            });
            window.__mo3.observe(document.body, { subtree: true, attributes: true, attributeFilter: ["class"], childList: true });
            /* 2. 值覆盖的起落: 0 -> N 记 opsUp, N -> 0 记 opsDown。 */
            clearInterval(window.__ti3);
            window.__ti3 = setInterval(() => {
              const m = window.__t;
              const n = Object.keys(vm.pendingOps || {}).length;
              if (m.opsUp === null) { if (n > 0) m.opsUp = performance.now(); return; }
              if (m.opsDown === null && n === 0) m.opsDown = performance.now();
            }, 4);
          })()`);
          await h.evaluate((el) => el.addEventListener("click", () => { window.__t.t0 = performance.now(); }, { capture: true, once: true }));
          await h.click();
          clicked2 = true;
          const deadline = Date.now() + 8000;
          while (Date.now() < deadline) {
            clear = await page.evaluate("(() => { const m = window.__t; return (m.t0 && m.opsDown) ? Math.round(m.opsDown - m.t0) : null; })()");
            if (clear !== null) break;
            await page.waitForTimeout(25);
          }
          break;
        }
        const tm = await page.evaluate(`(() => {
          clearInterval(window.__ti3);
          const m = window.__t;
          const f = (x) => ((m.t0 && x !== null) ? Math.round(x - m.t0) : null);
          return { clear: f(m.clear), opsUp: f(m.opsUp), opsDown: f(m.opsDown) };
        })()`);
        /*
         * !**同时设下界**: 桩服务的真值是**回执后 +120ms** 才落的(_TRUTH_DELAY), 所以要等真值
         * 就必须 ≥ 100ms 量级。若代码又退回"拿自己贴的补丁当真值比对"(2026-09-19 实测的坑:
         * 28ms 就清, 断言全绿却什么都没测到), 下界会立刻把它打成红。
         */
        add(ui, `P0-3 值覆盖及时落回真值(${FLOOR}~${BUDGET}ms)`,
          clicked2 && tm.opsDown !== null && tm.opsDown >= FLOOR && tm.opsDown < BUDGET,
          `点击 → pendingOps 归零 ${tm.opsDown === null ? "始终未归零" : tm.opsDown + "ms"}(须 ${FLOOR}~${BUDGET}ms` +
          (FLOOR ? `, 早于 ${FLOOR}ms 说明没等真值、只是跟自己的补丁比上了)` : `, error 模式=失败立即回滚)`) +
          ` / 覆盖起于 ${tm.opsUp === null ? "未采到" : tm.opsUp + "ms"}`);
        /*
         * 1. 压暗(DOM `.is-pending`)单独成条: 它是**用户感知的那一半**(D2 前撤下 2947ms,
         * 修后真机 85ms / 桩里十几 ms)。上面那条改量 pendingOps 之后, 它就没人管了 ——
         * 不补一条等于把"撤下慢"这个真实回归形态放走。
         * !不下界: D2 之后压暗本来就由回执结束, 十几 ms 是设计使然(给它套下界就是上面那条恒红的翻版)。
         */
        add(ui, `P0-3 压暗在回执后及时撤下(<${GREY_BUDGET}ms)`,
          clicked2 && tm.clear !== null && tm.clear < GREY_BUDGET,
          `点击 → is-pending 消失 ${tm.clear === null ? "始终未消失" : tm.clear + "ms"}(须 <${GREY_BUDGET}ms)`);
        /*
         * 光"pending 消失"不够 —— 回滚也会让它消失。**必须落回真值本身**:
         * ok 模式行必须真的是暂停态(s-paused), 证明清 pending 的是"真值匹配"而不是"补丁撤了退回旧值"。
         */
        const cls2 = await target2.getAttribute("class");
        if (EXPECT_CMD === "error") {
          add(ui, "P0-3 失败后落回原状态(非假暂停)", !!cls2 && !cls2.includes("s-paused"),
            `行 class: ${cls2}`);
        } else {
          /* 前置自证: 点击前必须**不是**暂停态 —— 否则"真值对齐"是白捡的(本来就是 paused)。 */
          add(ui, "P0-3 落回的是真值(行确为 s-paused)",
            !!cls2 && cls2.includes("s-paused") && !beforeKind.includes("s-paused"),
            `${beforeKind} -> ${cls2}`);
        }
      }
      await page.waitForTimeout(500);
    }

    /*
     * P0-4 批量合单: 选 N 个目标点暂停 ⇒ 必须只有 **1** 条 POST /api/torrents/bulk,
     * 且**零**条逐目标 /api/torrents/{hash}/pause。合单前这是 N 次 POST + N 条回执轮询 +
     * 后端 N 次串行 qB 调用(在主循环线程上, 期间界面"卡住")—— 这是"点批量后界面卡住"的真因。
     * 单测覆盖不到(全是前端行为), 只能在真浏览器里数请求。
     * 2026-10-05 批量控制条退役: 入口改走**右键批量菜单**(被右键行属于选中集合时升级为
     * menu.multi 分支) —— 与 CTX-03 同一套链路, 这里只是把 N 放大到 60 验合单规模。
     */
    {
      const N = 60;
      await page.evaluate("window.scrollTo(0, 0)");
      await page.waitForTimeout(300);
      const picked = await page.evaluate(`(() => {
        const vm = ${INST};
        vm.selGroups = [];
        vm.selMembers = vm.filteredTorrents.slice(0, ${N}).map((r) => r.hash);
        return vm.selMembers.length;
      })()`);
      /* 行是窗口化的: 只在**已渲染**的行里挑一个属于选中集合的锚点(菜单才会升级为批量) */
      const selHashes = await readInst(page, "vm.selMembers.slice()");
      let selRow = null;
      for (const r of await page.$$(".torrent-row")) {
        const h = await r.evaluate((el) => el.getAttribute("data-hash"));
        if (selHashes.includes(h)) { selRow = r; break; }
      }
      const hits = { bulk: 0, single: 0 };
      const onReq = (r) => {
        const u = r.url();
        if (u.includes("/api/torrents/bulk")) hits.bulk++;
        else if (/\/api\/torrents\/[^/?]+\/pause(\?|$)/.test(u)) hits.single++;
      };
      page.on("request", onReq);
      let bulkClicked = false;
      if (selRow) {
        await armPending(page, ".torrent-row.is-pending, .group-row.is-pending");  // 点击**之前**装好
        await selRow.click({ button: "right" });
        await page.waitForSelector(".ctx-menu", { timeout: 5000 }).catch(() => null);
        for (const h of await page.$$(".ctx-item")) {
          const t = ((await h.textContent()) || "").trim();
          if (t.includes("批量暂停")) { await armClick(page, h); await h.click(); bulkClicked = true; break; }
        }
      }
      await page.waitForTimeout(1500);
      page.off("request", onReq);
      add(ui, "P0-4 批量动作合单为一条请求", bulkClicked && hits.bulk === 1 && hits.single === 0,
        `选中 ${picked} 个 → bulk ${hits.bulk} 次 / 逐目标 ${hits.single} 次`);
      /*
       * 顺带验 P0-3 的批量形态: 乐观值要一次性贴到**全部**目标上(不是只贴第一行)。
       * error 模式下回执是**瞬间**回的, 乐观窗口在采样前就关了(实测 pendingOps 恒 0) ——
       * 那不是缺陷, 是采样时机; 此时改断言"失败后回滚干净"(否则这条断言在 error 模式恒红,
       * 而"某种模式下恒红的断言"和"恒真的断言"一样没用)。
       */
      const pend = await readInst(page, "Object.keys(vm.pendingOps || {}).length");
      if (EXPECT_CMD === "error") {
        const pendRows = await page.$$eval(".torrent-row.is-pending, .group-row.is-pending", (n) => n.length);
        add(ui, "P0-3 批量失败后回滚干净", pend === 0 && pendRows === 0,
          `pendingOps ${pend} / 残留行 ${pendRows} / 目标 ${picked}`);
      } else {
        /* 用**峰值**而不是"此刻的数量": 真值对齐修好后 1500ms 早清干净了, 此刻必然是 0。 */
        const p = await readPending(page);
        add(ui, "P0-3 批量乐观覆盖全部目标", p.peak >= Math.min(picked, N) * 0.8,
          `峰值 pendingOps ${p.peak}(@${p.peakT === null ? "-" : p.peakT + "ms"}) / 目标 ${picked}`);
      }
      // 清掉选择, 免得影响后面的视图切换断言
      await page.evaluate(`(() => { const vm = ${INST}; vm.clearSelection && vm.clearSelection(); })()`);
      await page.waitForTimeout(300);
    }

    /*
     * CTX-03 多选段(选中/未选中/合单为一条 bulk/按模式分流的乐观覆盖与回滚干净, 原 L777–851)
     * 已于 2026-10-06 迁入 e2e/multiselect-shows.spec.mjs(S2 批, 计划 26-10-06-0708 §3.3;
     * 对账映射表见该文件头)。选中集合改走真实 Ctrl+click, 不再 vm 注入。
     */

    /*
     * W2 批量限速/移动(计划 26-10-02-1955): 多选菜单出现两项 + 限速提交载荷形状。
     * 判据:
     *   1. 选中行右键 -> 批量菜单含「限速…」「移动…」两项(重新校验之后; 排序从宽, 只要求同时出现)。
     *   2. 点「限速…」-> 弹双输入对话框; 上传填 1024 KiB/s、下载留空 -> 载荷 action=limits、
     *      up_limit=1024*1024、dl_limit 键不出现(D3: 留空方向不提交)、hashes 覆盖整个选中集合。
     */
    {
      const N = 3;
      await page.evaluate("window.scrollTo(0, 0)");
      await page.waitForTimeout(200);
      const picked = await page.evaluate(`(() => {
        const vm = ${INST};
        vm.selGroups = [];
        vm.selMembers = vm.filteredTorrents.slice(0, ${N}).map((r) => r.hash);
        return vm.selMembers.length;
      })()`);
      const selHashes = await readInst(page, "vm.selMembers.slice()");
      let anchor = null;
      for (const r of await page.$$(".torrent-row")) {   // 行是窗口化的: 从已渲染行里挑选中锚点
        const h = await r.evaluate((el) => el.getAttribute("data-hash"));
        if (selHashes.includes(h)) { anchor = r; break; }
      }
      let menuTexts = [];
      if (anchor) {
        await anchor.click({ button: "right" });
        await page.waitForSelector(".ctx-menu", { timeout: 5000 }).catch(() => null);
        menuTexts = await page.$$eval(".ctx-item", (ns) => ns.map((n) => n.textContent.trim()));
      }
      add(ui, "W2 批量菜单含限速/移动两项",
        picked === N && menuTexts.some((t) => t.includes("限速…")) && menuTexts.some((t) => t.includes("移动…")),
        `选中 ${picked} 行 / 菜单: ${menuTexts.slice(0, 8).join(" / ") || "(未打开)"}`);
      /* W5 汇总: 多选菜单**四项齐**(限速/移动/跳检/导出 同屏在) —— 单项存在性已由 W2/W3/W4
       * 各条分散兜底, 本条专抓"加了新项挤掉旧项"这类汇总遗漏(收录口径见 ctx-menus.html 注)。 */
      add(ui, "W5 多选菜单四项齐(限速/移动/跳检/导出)",
        picked === N && ["限速…", "移动…", "跳检…", "导出 .torrent"].every((k) => menuTexts.some((t) => t.includes(k))),
        `菜单: ${menuTexts.join(" / ") || "(未打开)"}`);

      // 2. 提交载荷形状: 拦截 bulk POST -> 弹对话框 -> 上传填 1024 / 下载留空 -> 提交
      let bulkBody = null;
      const onReq = (r) => {
        if (r.url().includes("/api/torrents/bulk")) bulkBody = r.postData();
      };
      page.on("request", onReq);
      let clicked = false;
      for (const h of await page.$$(".ctx-item")) {
        const t = ((await h.textContent()) || "").trim();
        if (t.includes("限速…")) { await armClick(page, h); await h.click(); clicked = true; break; }
      }
      if (clicked) {
        await page.waitForSelector(".modal", { timeout: 5000 }).catch(() => null);
        const inputs = await page.$$(".modal-fields input");
        if (inputs.length === 2) {
          await inputs[0].fill("1024");   // 上传 1024 KiB/s; 下载留空 = 不提交该项(D3)
          await page.click(".modal-actions .bt.primary");
          await page.waitForTimeout(500);
        } else {
          add(ui, "W2 批量限速载荷形状(留空方向不提交)", false, `对话框输入框 ${inputs.length} 个(期望 2)`);
        }
      }
      page.off("request", onReq);
      let posted = null;
      try { posted = bulkBody ? JSON.parse(bulkBody) : null; } catch { posted = null; }
      const okPayload = !!posted && posted.action === "limits"
        && posted.up_limit === 1024 * 1024
        && !("dl_limit" in posted)
        && Array.isArray(posted.hashes) && posted.hashes.length === N;
      add(ui, "W2 批量限速载荷形状(留空方向不提交)", clicked && okPayload,
        `载荷: ${bulkBody ? bulkBody.slice(0, 140) : "(未捕获)"}`);
      /* W5 汇总: 成功回执 toast —— _bulkEditPost 在 waitCmd ok 后弹「已执行: 批量限速(N 个目标)」。
       * 桩命令泵瞬时回执, 正常 1s 内出现; 轮询 5s 是给慢轮询的余量。 */
      let limitsToast = null;
      if (clicked && okPayload) {
        const deadline = Date.now() + 5000;
        while (Date.now() < deadline && !limitsToast) {
          await page.waitForTimeout(250);
          const texts = await readInst(page, "(vm.toasts || []).map((t) => t.kind + '|' + t.text)");
          limitsToast = (texts || []).find((s) => s === `ok|已执行: 批量限速(${N} 个目标)`) || null;
        }
      }
      add(ui, "W5 批量限速成功回执 toast", clicked && okPayload && !!limitsToast,
        `toast: ${limitsToast || "(未出现)"}`);
      // 收尾: 关掉可能残留的弹层并清选择
      await page.evaluate(`(() => {
        const vm = ${INST};
        if (vm.modal && vm.modal.visible) vm.resolveModal(false);
        vm.clearSelection && vm.clearSelection();
      })()`);
      await page.waitForTimeout(300);
    }

    /*
     * W3 批量跳检(计划 26-10-02-1955): flags 门控菜单项 + 危险确认框「取消 = 不提交」。
     * 判据(harness 开关开 skip_check_menu=true, 走真实 flags 端点 -> state.flags -> v-if 链):
     *   1. 单选菜单含「跳检…」项(右键未选中行) + 选中行右键 -> 批量菜单也含
     *      (重新校验之后、限速/移动之前, 从宽只要求出现); 关态两处都不渲染由
     *      桩 --skip-check-menu off + ui_smoke.cjs --skip-check off 的精简轮兜底。
     *   2. 点「跳检…」-> 弹 danger 确认框(标题含「批量跳检」) -> 点「取消」-> 不发 bulk POST;
     *      点「跳检」(确认) -> 恰好 1 条 bulk POST(action=skip_check, 目标 = 选中集合)。
     *      (后端 gate 双态由 pytest 兜底, 这里只测前端确认链。)
     */
    {
      const N = 3;
      await page.evaluate("window.scrollTo(0, 0)");
      await page.waitForTimeout(200);
      const picked = await page.evaluate(`(() => {
        const vm = ${INST};
        vm.selGroups = [];
        vm.selMembers = vm.filteredTorrents.slice(0, ${N}).map((r) => r.hash);
        return vm.selMembers.length;
      })()`);
      const selHashes = await readInst(page, "vm.selMembers.slice()");
      /* W5 汇总: flags 开时**单选**菜单也有跳检项 —— 右键未选中行(= 单目标菜单);
       * 先做这条, 多选锚点那次右键会整份替换菜单, 不会串台。 */
      let singleTexts = [];
      for (const r of await page.$$(".torrent-row")) {
        const h = await r.evaluate((el) => el.getAttribute("data-hash"));
        if (!selHashes.includes(h)) {
          await r.click({ button: "right" });
          await page.waitForSelector(".ctx-menu", { timeout: 5000 }).catch(() => null);
          singleTexts = await page.$$eval(".ctx-item", (ns) => ns.map((n) => n.textContent.trim()));
          break;
        }
      }
      add(ui, "W3 单选菜单含跳检项(flags 开)", singleTexts.some((t) => t.includes("跳检…")),
        `单选菜单: ${singleTexts.slice(0, 10).join(" / ") || "(未打开)"}`);
      let anchor = null;
      for (const r of await page.$$(".torrent-row")) {   // 行是窗口化的: 从已渲染行里挑选中锚点
        const h = await r.evaluate((el) => el.getAttribute("data-hash"));
        if (selHashes.includes(h)) { anchor = r; break; }
      }
      let menuTexts = [];
      if (anchor) {
        await anchor.click({ button: "right" });
        await page.waitForSelector(".ctx-menu", { timeout: 5000 }).catch(() => null);
        menuTexts = await page.$$eval(".ctx-item", (ns) => ns.map((n) => n.textContent.trim()));
      }
      add(ui, "W3 批量菜单含跳检项(flags 开)",
        picked === N && menuTexts.some((t) => t.includes("跳检…")),
        `选中 ${picked} 行 / 菜单: ${menuTexts.slice(0, 9).join(" / ") || "(未打开)"}`);

      // 2. 确认框取消不提交: 拦截 bulk POST -> 点「跳检…」-> 确认框出现 -> 点「取消」-> 零 POST
      let bulkBody = null;
      const onReq = (r) => {
        if (r.url().includes("/api/torrents/bulk")) bulkBody = r.postData();
      };
      page.on("request", onReq);
      let clicked = false;
      for (const h of await page.$$(".ctx-item")) {
        const t = ((await h.textContent()) || "").trim();
        if (t.includes("跳检…")) { await h.click(); clicked = true; break; }
      }
      let modalShown = false;
      let modalTitle = "";
      let cancelled = false;
      if (clicked) {
        modalShown = !!(await page.waitForSelector(".modal", { timeout: 5000 }).catch(() => null));
        if (modalShown) {
          modalTitle = ((await page.$eval(".modal-title", (n) => n.textContent)) || "").trim();
          const cancel = await page.$(".modal-actions .bt.ghost");
          if (cancel) { await cancel.click(); cancelled = true; }
          await page.waitForTimeout(400);
        }
      }
      page.off("request", onReq);
      add(ui, "W3 跳检确认框取消不提交", clicked && modalShown && cancelled && bulkBody === null,
        `弹框: ${modalTitle || "(未出现)"} / 取消 ${cancelled ? "是" : "否"} / POST: ${bulkBody ? bulkBody.slice(0, 120) : "(未捕获)"}`);

      // 3. 确认后提交(W5 汇总): 确认框按下「跳检」(danger 框确认钮是 .bt.danger-solid, 非 primary)
      //    -> 恰好 1 条 bulk POST, action=skip_check、hashes = 选中集合(选择仍是上面那 3 个)。
      let confirmed = false;
      let confirmBody = null;
      const onReq2 = (r) => {
        if (r.url().includes("/api/torrents/bulk")) confirmBody = r.postData();
      };
      page.on("request", onReq2);
      // 2s 整表重渲染会换掉行节点: 按 hash 现找选中锚点再右键(选择未清, selMembers 仍是 N 个)
      let a2 = null;
      const selNow = await readInst(page, "vm.selMembers.slice()");
      for (const r of await page.$$(".torrent-row")) {
        const h = await r.evaluate((el) => el.getAttribute("data-hash"));
        if (selNow.includes(h)) { a2 = r; break; }
      }
      let modal2Title = "";
      if (a2) {
        await a2.click({ button: "right" });
        await page.waitForSelector(".ctx-menu", { timeout: 5000 }).catch(() => null);
        for (const h of await page.$$(".ctx-item")) {
          const t = ((await h.textContent()) || "").trim();
          if (t.includes("跳检…")) { await h.click(); break; }
        }
        const modal2 = await page.waitForSelector(".modal", { timeout: 5000 }).catch(() => null);
        if (modal2) {
          modal2Title = ((await page.$eval(".modal-title", (n) => n.textContent)) || "").trim();
          const okBtn = await page.$(".modal-actions .bt.danger-solid");
          if (okBtn) { await okBtn.click(); confirmed = true; }
          await page.waitForTimeout(1200);   // 等 POST + 回执(桩瞬时, 富余给慢轮询)
        }
      }
      page.off("request", onReq2);
      let confirmPosted = null;
      try { confirmPosted = confirmBody ? JSON.parse(confirmBody) : null; } catch { confirmPosted = null; }
      add(ui, "W3 跳检确认后提交 bulk(action=skip_check)",
        confirmed && !!confirmPosted && confirmPosted.action === "skip_check"
          && Array.isArray(confirmPosted.hashes) && confirmPosted.hashes.length === N,
        `弹框: ${modal2Title || "(未出现)"} / POST: ${confirmBody ? confirmBody.slice(0, 140) : "(未捕获)"}`);
      // 收尾: 关掉可能残留的弹层并清选择
      await page.evaluate(`(() => {
        const vm = ${INST};
        if (vm.modal && vm.modal.visible) vm.resolveModal(false);
        vm.clearSelection && vm.clearSelection();
      })()`);
      await page.waitForTimeout(300);
    }

    /*
     * W4 多选导出(计划 26-10-02-1955, D1 拍板 = 前端循环逐个触发下载): 多选菜单出现「导出 .torrent」
     * 项, 点击后对**单 hash** 导出端点发起 N 个请求且 N == 选中展开数(串行逐个, 无 bulk 合单)。
     * 组选中单独验一条: 整组选中必须展开为成员 hash 闭包(selHashSet 全量), 若实现误用
     * _bulkTargets().memberHashes(组内成员留在 keys 通道)请求数就会小于成员数 —— 在此暴露。
     * 桩端点(FakeClient.torrents_export)真出字节, 请求真实发生; 只数 /export 的 URL, 不碰下载落盘
     * (headless 下浏览器可能拦"多文件下载", 但拦的是 a.click 的落盘, fetch 计数不受影响)。
     */
    {
      const N = 3;
      await page.evaluate("window.scrollTo(0, 0)");
      await page.waitForTimeout(200);
      const picked = await page.evaluate(`(() => {
        const vm = ${INST};
        vm.selGroups = [];
        vm.selMembers = vm.filteredTorrents.slice(0, ${N}).map((r) => r.hash);
        return vm.selMembers.length;
      })()`);
      const selHashes = await readInst(page, "vm.selMembers.slice()");
      let anchor = null;
      for (const r of await page.$$(".torrent-row")) {   // 行是窗口化的: 从已渲染行里挑选中锚点
        const h = await r.evaluate((el) => el.getAttribute("data-hash"));
        if (selHashes.includes(h)) { anchor = r; break; }
      }
      let menuTexts = [];
      if (anchor) {
        await anchor.click({ button: "right" });
        await page.waitForSelector(".ctx-menu", { timeout: 5000 }).catch(() => null);
        menuTexts = await page.$$eval(".ctx-item", (ns) => ns.map((n) => n.textContent.trim()));
      }
      add(ui, "W4 批量菜单含导出项",
        picked === N && menuTexts.some((t) => t.includes("导出 .torrent")),
        `选中 ${picked} 行 / 菜单: ${menuTexts.slice(0, 11).join(" / ") || "(未打开)"}`);

      // 2. 点击后导出请求数 == 选中展开数: 计数 /export 请求(串行也全都会发, 等 1.2s 足够)
      let exportHits = 0;
      const onReq = (r) => {
        if (/\/api\/torrents\/[^/?]+\/export(\?|$)/.test(r.url())) exportHits++;
      };
      page.on("request", onReq);
      let clicked = false;
      for (const h of await page.$$(".ctx-item")) {
        const t = ((await h.textContent()) || "").trim();
        if (t.includes("导出 .torrent")) { await h.click(); clicked = true; break; }
      }
      await page.waitForTimeout(1200);
      page.off("request", onReq);
      add(ui, "W4 多选导出逐个请求(数 == 选中展开数)", clicked && exportHits === N,
        `选中 ${picked} 个 -> 导出请求 ${exportHits} 个(期望 ${N})`);
      /* W5 汇总: 导出成功回执 toast —— exportMulti 常驻 busy 在原位结算成「已导出 N 个 .torrent」。
       * 导出循环是串行 fetch(每个都真出字节), 1.2s 的请求计数等待通常已覆盖, 轮询 5s 是余量。 */
      let exportToast = null;
      if (clicked) {
        const deadline = Date.now() + 5000;
        while (Date.now() < deadline && !exportToast) {
          await page.waitForTimeout(250);
          const texts = await readInst(page, "(vm.toasts || []).map((t) => t.kind + '|' + t.text)");
          exportToast = (texts || []).find((s) => s === `ok|已导出 ${N} 个 .torrent`) || null;
        }
      }
      add(ui, "W5 导出成功回执 toast", clicked && !!exportToast, `toast: ${exportToast || "(未出现)"}`);
      await page.evaluate(`(() => { const vm = ${INST}; vm.clearSelection && vm.clearSelection(); })()`);
      await page.waitForTimeout(300);
    }

    /* W4 组选中场景: 整组右键导出 -> 请求数 == 组成员数(selHashSet 全量展开, 见上块注释)。
     * !在**辅种页**做: 种子页按视图分片不回 groups(VIEW_ARRAYS), 组选中在种子页展开不出成员;
     *   选中**两个**组 —— 只选 1 组右键该组行时 _ctxMulti 的"范围一致"判定会降级单目标菜单。
     *   组从**已渲染行**反挑(行窗口化, 不假设排序把哪组排在前面)。 */
    {
      await nav[0].click();  // 回辅种页
      await page.waitForFunction("document.querySelectorAll('.group-row').length > 0", null, { timeout: 15000 });
      await page.waitForTimeout(400);
      const ginfo = await page.evaluate(`(() => {
        const vm = ${INST};
        const visible = new Set([...document.querySelectorAll('.group-row[data-table="group"]')].map((el) => el.getAttribute("data-key")));
        const gs = vm.decoratedGroups.filter((x) => !x.virtual && (x.members || []).length && visible.has(x.key)).slice(0, 2);
        if (gs.length < 2) return null;
        vm.selMembers = [];
        vm.selGroups = gs.map((g) => g.key);
        return { groups: gs.length, members: gs.reduce((n, g) => n + g.members.length, 0), expanded: vm.selHashSet.size };
      })()`);
      let anchor = null;
      if (ginfo) {
        const keys = await readInst(page, "vm.selGroups.slice()");
        for (const r of await page.$$('.group-row[data-table="group"]')) {
          const k = await r.evaluate((el) => el.getAttribute("data-key"));
          if (keys.includes(k)) { anchor = r; break; }
        }
      }
      let clicked = false;
      let exportHits = 0;
      if (anchor) {
        const onReq = (r) => {
          if (/\/api\/torrents\/[^/?]+\/export(\?|$)/.test(r.url())) exportHits++;
        };
        page.on("request", onReq);
        await anchor.click({ button: "right" });
        await page.waitForSelector(".ctx-menu", { timeout: 5000 }).catch(() => null);
        for (const h of await page.$$(".ctx-item")) {
          const t = ((await h.textContent()) || "").trim();
          if (t.includes("导出 .torrent")) { await h.click(); clicked = true; break; }
        }
        await page.waitForTimeout(1200);
        page.off("request", onReq);
      }
      add(ui, "W4 组选中导出展开为整组成员",
        !!ginfo && clicked && exportHits === ginfo.expanded && ginfo.expanded === ginfo.members,
        `选中 ${ginfo ? ginfo.groups : "-"} 组 / 成员 ${ginfo ? ginfo.members : "-"} 个 -> 导出请求 ${exportHits} 个`);
      await page.evaluate(`(() => { const vm = ${INST}; vm.clearSelection && vm.clearSelection(); })()`);
      await page.waitForTimeout(300);
      await nav[1].click();  // 回种子页(后续块在此视图)
      await page.waitForFunction("document.querySelectorAll('.torrent-row').length > 0", null, { timeout: 15000 });
      await page.waitForTimeout(300);
    }

    /*
     * CTX-04 / CTX-05 / CTX-06 —— 右键**次级菜单**的三条(2026-09-24 用户报, 都是"pytest 全绿、
     * node --check 全绿、界面废掉"那一类; 判据一律取**可测的事实**, 不靠截图):
     *   1. 图标 hover 变灰(CTX-04): `.ctx-item:hover .ico` 是**后代**选择器, 而 `.ctx-sub` 是父项的
     *      DOM 后代 ⇒ hover「更多操作」会把整个子面板的图标刷成 --fg-muted, 语义色全被抹平。
     *      判据: 悬停父项时读子面板首项图标的 computed color, 必须仍是语义色(队列族 --teal),
     *      且不等于 --fg-muted —— 修之前这里恒等于 --fg-muted。
     *   2. 移出不消失(CTX-05): 只有 mouseenter 展开、没有任何收起 ⇒ 鼠标移到别的菜单项上
     *      子面板一直挂在屏幕上。判据: hover 到另一个一级项 → 450ms 后 .ctx-sub 必须为 0。
     *   3. 一级两个"更多"入口(CTX-06): 复制族曾单列第二个子面板 ⇒ 用户得先选"该进哪个"。
     *      判据: 一级 has-sub 恰好 1 个且文案是「更多操作」, 复制三项在它展开的面板里。
     */
    {
      await page.evaluate("window.scrollTo(0, 0)");
      await page.waitForTimeout(200);
      const row0 = (await page.$$(".torrent-row"))[0];
      if (!row0) {
        add(ui, "CTX-04/05/06 次级菜单", false, "页面上没有 .torrent-row 可右键(前置条件变了?)");
      } else {
        await row0.click({ button: "right" });
        await page.waitForSelector(".ctx-menu", { timeout: 5000 }).catch(() => null);
        // 3. 一级只允许一个次级菜单入口
        const subs = await page.$$(".ctx-menu > .ctx-item.has-sub");
        const subTexts = [];
        for (const h of subs) subTexts.push(((await h.textContent()) || "").trim());
        add(ui, "CTX-06 一级只有一个次级菜单入口(更多操作)",
          subs.length === 1 && subTexts[0].includes("更多操作"),
          `入口 ${subs.length} 个: ${subTexts.join(" / ") || "(无)"}`);

        // 展开子面板(hover 父项 —— 与用户路径一致)
        await subs[0].hover();
        await page.waitForSelector(".ctx-sub", { timeout: 3000 }).catch(() => null);
        const panelText = await page.$eval(".ctx-sub", (n) => n.textContent).catch(() => "");
        const flat = panelText.replace(/\s+/g, " ");
        add(ui, "CTX-06 复制族并入「更多操作」",
          ["复制名称", "复制哈希", "复制 magnet"].every((t) => flat.includes(t)),
          `面板: ${flat.slice(0, 90) || "(未展开)"}`);

        // 1. 悬停父项时子面板图标必须仍是语义色(队列族 --teal), 不是 --fg-muted
        const probe = await page.evaluate(`(() => {
          const el = document.querySelector(".ctx-sub .ico-queue");
          if (!el) return null;
          const mk = (v) => { const s = document.createElement("span"); s.style.color = v; document.body.appendChild(s); return s; };
          const muted = mk("var(--fg-muted)"), teal = mk("var(--teal)");
          const out = {
            icon: getComputedStyle(el).color,
            muted: getComputedStyle(muted).color,
            teal: getComputedStyle(teal).color,
          };
          muted.remove(); teal.remove();
          return out;
        })()`);
        add(ui, "CTX-04 悬停父项时子面板图标仍是语义色(不变灰)",
          !!probe && probe.icon === probe.teal && probe.icon !== probe.muted,
          probe ? `图标 ${probe.icon} / 语义色(--teal) ${probe.teal} / 灰(--fg-muted) ${probe.muted}`
            : "(子面板没展开, 读不到图标)");

        // 2. 移到别的菜单项上 -> 子面板必须收起(延迟 ~180ms, 故等 450ms 再看)
        const firstItem = await page.$(".ctx-menu > .ctx-item");
        if (firstItem) await firstItem.hover();
        await page.waitForTimeout(450);
        const still = await page.$$eval(".ctx-sub", (ns) => ns.length);
        add(ui, "CTX-05 移出父项后子面板收起", still === 0, `残留 .ctx-sub ${still} 个`);

        await page.keyboard.press("Escape");   // 收尾关菜单, 免得影响后续断言
        await page.waitForTimeout(150);
      }
    }

    /*
     * P0-3 整组乐观(BUG-3): 整组暂停后**组行本身**必须立刻可见 —— 颜色随成员 kind 重算 + is-pending。
     * 只补成员 hash 不够: 组行的状态色取自 g.status.primary(不展开明细时看不到成员行),
     * 而组行此前也没有 is-pending 绑定 ⇒ 整组操作在感知层完全没有反馈。
     * 走真实右键菜单(与用户路径一致), 不用 vm.act() 直调。
     * !先切回分组视图: 上一段 P0-4 是在**种子页**做的, 此时 DOM 里没有任何组行。
     */
    await nav[0].click();  // 回分组
    await page.waitForTimeout(600);
    {
      /*
       * !走 pausableRow(带"全暂停了就先恢复一行"的兜底), 不要只按 DOM class 挑:
       * 行是**窗口化**的(只渲染 26 行), 而前面的块已经批量暂停 60 个种子 + 整剧暂停一整部剧,
       * 窗口里的组行很容易**全是 s-paused** ⇒ 直接报"找不到可暂停的组行"
       * (2026-09-19 与对方提交合流后实测: prism 过、atlas 挂 —— 只因两者窗口落点不同)。
       */
      const gTarget = await pausableRow(page, '.group-row[data-table="group"]', "开始整组");
      if (!gTarget) {
        add(ui, "P0-3 整组乐观(组行 is-pending)", false, "找不到可暂停的组行(且恢复失败)");
      } else {
        const key = await gTarget.evaluate((el) => el.dataset.key);
        const before = await gTarget.evaluate((el) => el.className);
        await gTarget.click({ button: "right" });
        await page.waitForSelector(".ctx-menu", { timeout: 5000 }).catch(() => null);
        const gItems = await page.$$(".ctx-item");
        let gClicked = false;
        await armPending(page, ".group-row.is-pending");   // 必须在点击**之前**装好
        for (const h of gItems) {
          const t = (await h.textContent()) || "";
          if (t.includes("暂停整组") || t.trim() === "暂停") { await armClick(page, h); await h.click(); gClicked = true; break; }
        }
        await page.waitForTimeout(900);
        const p = await readPending(page);
        const after = await page.evaluate(
          `(() => { const el = document.querySelector('.group-row[data-table="group"][data-key=${JSON.stringify(key)}]'); return el ? el.className : null; })()`);
        const pend = await readInst(page, "Object.keys(vm.pendingOps || {}).length");
        const sCls = (c) => ((c || "").split(" ").find((x) => x.startsWith("s-")) || "");
        if (EXPECT_CMD === "error") {
          add(ui, "P0-3 整组乐观失败后回滚(组行)",
            gClicked && !!after && !after.includes("is-pending") && pend === 0 && sCls(after) === sCls(before),
            `${before} -> ${after} / pendingOps ${pend}`);
        } else {
          /* 判"组行**曾经**出现过 pending" —— 真值对齐修好后组行 pending 只活 100~300ms,
           * 点完再数一次必然是 0(不是回归, 是度量方式失效)。 */
          add(ui, "P0-3 整组乐观(组行 is-pending)", gClicked && p.appear !== null,
            `点击 → 组行出现 pending ${p.appear === null ? "从未出现" : p.appear + "ms"} / 消失 ${p.gone === null ? "-" : p.gone + "ms"}`);
        }
        await page.waitForTimeout(600);  // 真值对齐后 pending 早清了, 留一点余量即可
      }
    }

    /*
     * 「真值到达」≠「值覆盖结束」(2026-09-21 用户报「整组暂停后 灰→绿→灰」):
     * 真值走 `torrents/info` **直查**, 比我们自己的 `/sync/maindata` **快照**新 —— 快照要等主循环
     * 下一次 sync(≤ sync_interval = 1.5s)才带上同一个状态。若真值事件一到这里就把 pendingOps 删掉,
     * 这 1.5s 内任何一次**视图发布**(任何种子任何字段变化都会让 rid 前进、整表重发)都会带着
     * **命令前**的 kind 覆盖行对象 ⇒ 行被打回命令前的颜色(暂停组闪回做种绿), 快照追上再变灰。
     * 判据: 造一次"陈旧快照"(成员 kind 改回命令前)喂给 refresh 的同一套内部调用 ——
     * 行色**必须不变**、覆盖**必须还在**; 随后"快照同意"的那一版必须收工(覆盖不能永久挂着,
     * 那是另一个 bug: 假状态永不消退)。刻意直调 vm.applyOptimistic/resolveOptimistic/onTruthEvent
     * (不经右键菜单): 本条测的是"时序", 菜单与点击时序已在上面 P0-3 块里覆盖过。
     */
    {
      const t = await page.evaluate(`(() => {
        const vm = ${INST};
        // 挑一个"成员状态一致且非暂停"的组(前面几块已暂停过大量行)
        const g = vm.decoratedGroups.find((x) => x.members.length && x.members.every((m) => m.kind !== "paused"));
        if (!g) return { err: "找不到可暂停的组" };
        const hashes = g.members.map((m) => m.hash);
        const key = g.key;
        const before = vm.decoratedGroups.find((x) => x.key === key).status.primary;
        vm.applyOptimistic(hashes, "pause");
        const afterPatch = vm.decoratedGroups.find((x) => x.key === key).status.primary;
        vm.resolveOptimistic(hashes, true);   // 回执到达(结束压暗, 转入值覆盖)
        const truth = {};
        for (const h of hashes) truth[h] = { kind: "paused" };
        vm.onTruthEvent({ cmd_id: "smoke", truth });   // 真值事件(服务端直查)
        const held = Object.keys(vm.pendingOps || {}).length;
        // 陈旧快照: 服务端这一版仍是命令前的 kind, 且 rid 前进(真机窗口最多 1.5s)
        for (const gg of vm.groups) for (const m of gg.members) if (hashes.includes(m.hash)) m.kind = before;
        vm._snapshotTruth({ groups: vm.groups, singles: [], torrents: [] });   // refresh() 的同一顺序
        vm.reapplyPending();
        const afterStale = vm.decoratedGroups.find((x) => x.key === key).status.primary;
        // 快照追上: 这一版真的带上了 paused -> 覆盖必须收工(不留假状态)
        for (const gg of vm.groups) for (const m of gg.members) if (hashes.includes(m.hash)) m.kind = "paused";
        vm._snapshotTruth({ groups: vm.groups, singles: [], torrents: [] });
        vm.reapplyPending();
        const released = Object.keys(vm.pendingOps || {}).length;
        // 复原: 本条没真发命令, 前后端都没变, 行上的补丁要撤干净(免污染后续断言)
        for (const h of hashes) { vm._forEachRow(h, (r) => { r.kind = before; }); delete vm.pendingOps[h]; }
        return { key, before, afterPatch, held, afterStale, released };
      })()`);
      add(ui, "真值事件后不被陈旧快照打回(值覆盖保持到快照同意)",
        !t.err && t.afterPatch === "paused" && t.afterStale === "paused" && t.held > 0 && t.released === 0,
        t.err || `${t.before} →补丁 ${t.afterPatch} →陈旧快照 ${t.afterStale} →快照同意后释放 ${t.released} ` +
        `(覆盖保持=${t.held} 条)`);
    }

    /*
     * BUG-9: "复制磁力"必须真拿到 magnet。magnet_uri **只**在种子页的平铺 SEED_ITEM 里,
     * 成员索引(groups/singles)不带该字段 ⇒ 修复前在辅种页恒提示"该种子没有 magnet 链接"
     * (100% 失败, 与种子是否真有磁力无关)。断言刻意避开剪贴板差异: 只要求
     * "不再出现'没有 magnet 链接'", 并把实际 toast 打出来; 同时断言索引里确实没有该字段
     * (否则这条断言会因为"索引恰好带 magnet"而空过)。
     */
    {
      const r = await page.evaluate(`(async () => {
        const vm = ${INST};
        const g = vm.groups.find((x) => (x.members || []).length);
        if (!g) return { err: "no group" };
        const h = g.members[0].hash;
        const idxHasMagnet = "magnet_uri" in (vm.memberByHash.get(h) || {});
        vm.menu = { visible: true, hash: h, key: null };
        await vm.copyTorrentInfo("magnet");
        await new Promise((res) => setTimeout(res, 500));
        const t = (vm.toasts || []).slice(-1)[0];
        return { idxHasMagnet, toast: t ? t.text : null, kind: t ? t.kind : null };
      })()`);
      add(ui, "BUG-9 辅种页复制磁力不再恒失败",
        !r.err && r.idxHasMagnet === false && r.toast !== "该种子没有 magnet 链接",
        `索引带 magnet=${r.idxHasMagnet} / toast=${r.toast}`);
    }

    /*
     * 块F(追剧视图: 前行/集行乐观 + CTX-03 追剧多集 + 切回分组有数据 + CTX-03 辅种多组 +
     * BUG-8 刷新不空白, 原 L1376–1545)已于 2026-10-06 迁入 e2e/multiselect-shows.spec.mjs
     * (S2 批, 计划 26-10-06-0708 §3.3; 对账映射表见该文件头)。存量 flaky(集行 Ctrl+click
     * 落点拦截)的 trace 归因与对冲 arrange 一并落在该 spec 的 clickRow()。
     */
    add(ui, "顶栏三视图按钮存在", false, `nav.tabs button = ${nav.length}`);
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
