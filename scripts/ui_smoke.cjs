/**
 * WEB UI 浏览器冒烟(Playwright + 桩服务) —— dev-only, 不参与打包
 *
 * 为什么需要: `agent-browser` 不支持 Windows, 而本项目有一整类故障"pytest 全绿但界面废掉"
 * (乐观 UI 不回滚、切视图数组被抹空、表头错位、行窗口化后滚动跳动)。本脚本用真实浏览器
 * 跑真实前端 + `scripts/ui_harness.py` 的合成后端, 把这类故障挡在提交前。
 *
 * 运行:
 *   1) uv run python scripts/ui_harness.py --torrents 3000 --port 8099
 *   2) NODE_PATH=C:/Users/<你>/.workbuddy-ai/binaries/node/workspace/node_modules \
 *      node scripts/ui_smoke.cjs --base http://127.0.0.1:8099
 *
 * 参数:
 *   --base       桩服务地址(默认 http://127.0.0.1:8099)
 *   --ui         prism|atlas|both(默认 both)
 *   --shots      截图目录(默认 .workbuddy-ai/tmp/ui-smoke)
 *   --torrents   期望种子总数(用于校验"总数正确", 默认 0=不校验)
 *   --expect-cmd ok|error|hang  与桩服务 --cmd-result 对应(默认 ok)
 *
 * 依赖: playwright-core(与已装的 chromium 版本对齐; 见文件末尾"版本对齐"注释)。
 */
const fs = require("fs");
const path = require("path");

let chromium;
// 先试 playwright-core: 它的版本与**本机已下载的 chromium**对齐(1.62 ↔ chromium-1234);
// 顶层 `playwright` 包可能更新(1.63 要 chromium-1243)从而报 "Executable doesn't exist"。
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

const results = [];
const add = (ui, name, ok, detail) => {
  results.push({ ui, name, ok, detail });
  console.log(`${ok ? "PASS" : "FAIL"}  [${ui}] ${name}${detail ? " — " + detail : ""}`);
};

/**
 * Vue 根实例(读 renderMs 等埋点; 取不到返回 null, 相关项降级为跳过)。
 * ❗不能用 `__vue_app__._instance.proxy`: 实测 Vue 3.5.13 下 `_instance` 恒为空(键在但没值),
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
 *  ❗Playwright 新版的路由谓词收到的是 URL 对象而不是字符串, 别直接当 string 用。 */
const CMD_URL = (u) => {
  const s = typeof u === "string" ? u : String(u);
  return /\/api\/(torrents|groups)\/[^/?]+\/(pause|resume)(\?|$)/.test(s) || s.includes("/api/torrents/bulk");
};

async function readInst(page, expr) {
  return page.evaluate(`(() => { const vm = ${INST}; return vm ? (${expr}) : null; })()`);
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
  const groupRows = await page.$$eval(".group-row", (n) => n.length);
  add(ui, "分组视图渲染", groupRows > 0, `${groupRows} 行`);
  await page.screenshot({ path: path.join(SHOTS, `${ui}-1-groups.png`) });

  // 三视图切换(P1-1: 只回传当前视图数组 ⇒ 切过去必须仍有数据, 不能被上一轮抹空)
  const nav = await page.$$("nav.tabs button");
  if (nav.length >= 3) {
    await nav[1].click();  // 种子
    await page.waitForFunction("document.querySelectorAll('.torrent-row').length > 0", null, { timeout: 15000 });
    const tRows = await page.$$eval(".torrent-row", (n) => n.length);
    const tTotal = await readInst(page, "vm.filteredTorrents.length");
    add(ui, "切到种子视图有数据", tRows > 0 && (!tTotal || tRows <= tTotal), `DOM ${tRows} 行 / 数据 ${tTotal} 条`);
    if (EXPECT_N) add(ui, "种子总数与桩服务一致", tTotal === EXPECT_N, `${tTotal} vs ${EXPECT_N}`);
    const renderMs = await readInst(page, "vm.renderMs");
    add(ui, "单轮 renderMs 埋点可读", typeof renderMs === "number", `${renderMs}ms`);
    /*
     * 轮询分档(P1 之后的收尾一步): 间隔必须**按种子量**落在实测档位上 ——
     *   ≤1000 → 1.5s | 1000~3000 → 2s | >3000 → 3s
     * 档位来自实测单轮 refresh 耗时(1000:143ms / 3000:309ms / 5000:~400ms),
     * 目的是把主线程占用率压在 ~15%。断言它, 免得"改了半天的渲染优化"被一个
     * 写死的 1s 轮询重新拖垮。
     */
    if (EXPECT_N) {
      const want = EXPECT_N > 3000 ? 3000 : EXPECT_N > 1000 ? 2000 : 1500;
      const got = await readInst(page, "vm.currentPollMs()");
      add(ui, "轮询间隔按种子量分档", got === want, `${EXPECT_N} 种子 → ${got}ms(期望 ${want}ms)`);
    }

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
     * ❗必须在**同一帧序列**里对照开关两侧: 早先只在"滚动前后"各读一次 scrollHeight,
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
     * ⚠ 前提是桩服务**真的改状态**(ui_harness.py::_apply_truth) —— 否则真值永不到,
     *   这条断言只会测到"走满 3s 兜底", 跟没测一样(这正是本条缺陷当初溜过去的原因)。
     */
    {
      const BUDGET = 1000;
      /*
       * ❗挑目标**之前**先与服务端真值对齐一次。否则会空过: 上面的块刚暂停过若干行, 桩服务
       * 真值已经改了, 但前端要等下一轮轮询(2s)才在 DOM 上反映 —— 此时按"class 没有 s-paused"
       * 挑出来的行其实**服务端已是 paused**, 点暂停后真值瞬间匹配 ⇒ pending 0~20ms 就清,
       * 断言恒绿却什么都没测到(2026-09-19 实测就是这样: 19ms)。
       */
      await page.evaluate(`(() => { const vm = ${INST}; return vm.refresh && vm.refresh(); })()`);
      await page.waitForTimeout(400);
      const target2 = await pausableRow(page, ".torrent-row", "开始该种子");
      if (!target2) {
        add(ui, "P0-3 乐观态及时落回真值", false, "找不到未暂停的行");
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
            window.__t = { t0: null, dom0: null, clear: null };
            if (window.__mo3) window.__mo3.disconnect();
            window.__mo3 = new MutationObserver(() => {
              const m = window.__t;
              if (m.dom0 === null && document.querySelector(".is-pending")) m.dom0 = performance.now();
              if (m.dom0 !== null && m.clear === null && !document.querySelector(".is-pending")) m.clear = performance.now();
            });
            window.__mo3.observe(document.body, { subtree: true, attributes: true, attributeFilter: ["class"], childList: true });
          })()`);
          await h.evaluate((el) => el.addEventListener("click", () => { window.__t.t0 = performance.now(); }, { capture: true, once: true }));
          await h.click();
          clicked2 = true;
          const deadline = Date.now() + 8000;
          while (Date.now() < deadline) {
            clear = await page.evaluate("(() => { const m = window.__t; return (m.t0 && m.clear) ? Math.round(m.clear - m.t0) : null; })()");
            if (clear !== null) break;
            await page.waitForTimeout(25);
          }
          break;
        }
        /*
         * ❗**同时设下界**: 桩服务的真值是**回执后 +120ms** 才落的(_TRUTH_DELAY), 所以要等真值
         * 就必须 ≥ 100ms 量级。若代码又退回"拿自己贴的补丁当真值比对"(2026-09-19 实测的坑:
         * 28ms 就清, 断言全绿却什么都没测到), 下界会立刻把它打成红。
         */
        /* error 模式没有"等真值"这回事: 命令失败 ⇒ 立即回滚(实测 ~21ms)。给它套下界会恒红,
         * 而"某种模式下恒红的断言"和"恒真的断言"一样没用 —— 失败路径由上面的
         * 「失败后落回原状态 / 回滚干净」两条覆盖, 这里只要求"快"。 */
        const FLOOR = EXPECT_CMD === "error" ? 0 : 80;
        add(ui, `P0-3 乐观态及时落回真值(${FLOOR}~${BUDGET}ms)`,
          clicked2 && clear !== null && clear >= FLOOR && clear < BUDGET,
          `点击 → pending 消失 ${clear === null ? "始终未消失" : clear + "ms"}(须 ${FLOOR}~${BUDGET}ms` +
          (FLOOR ? `: 早于 ${FLOOR}ms 说明没等真值、只是跟自己的补丁比上了)` : `, error 模式=失败立即回滚)`));
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
     */
    {
      const N = 60;
      const picked = await page.evaluate(`(() => {
        const vm = ${INST};
        vm.selGroups = [];
        vm.selMembers = vm.filteredTorrents.slice(0, ${N}).map((r) => r.hash);
        return vm.selMembers.length;
      })()`);
      await page.waitForSelector(".bulk-inline", { timeout: 5000 }).catch(() => null);
      const hits = { bulk: 0, single: 0 };
      const onReq = (r) => {
        const u = r.url();
        if (u.includes("/api/torrents/bulk")) hits.bulk++;
        else if (/\/api\/torrents\/[^/?]+\/pause(\?|$)/.test(u)) hits.single++;
      };
      page.on("request", onReq);
      const btns = await page.$$(".bulk-inline .bulk-btn");
      let bulkClicked = false;
      await armPending(page, ".torrent-row.is-pending, .group-row.is-pending");  // 点击**之前**装好
      for (const b of btns) {
        const t = (await b.textContent()) || "";
        if (t.includes("暂停")) { await armClick(page, b); await b.click(); bulkClicked = true; break; }
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
     * P0-3 整组乐观(BUG-3): 整组暂停后**组行本身**必须立刻可见 —— 颜色随成员 kind 重算 + is-pending。
     * 只补成员 hash 不够: 组行的状态色取自 g.status.primary(不展开明细时看不到成员行),
     * 而组行此前也没有 is-pending 绑定 ⇒ 整组操作在感知层完全没有反馈。
     * 走真实右键菜单(与用户路径一致), 不用 vm.act() 直调。
     * ❗先切回分组视图: 上一段 P0-4 是在**种子页**做的, 此时 DOM 里没有任何组行。
     */
    await nav[0].click();  // 回分组
    await page.waitForTimeout(600);
    {
      /*
       * ❗走 pausableRow(带"全暂停了就先恢复一行"的兜底), 不要只按 DOM class 挑:
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

    await nav[2].click();  // 追剧
    await page.waitForTimeout(900);
    // 原来是 `epRows >= 0`(恒真, 等于没断言) —— BUG-8 正是"追剧页 0 行"却照样 PASS 的那类故障
    const showRowCount = await page.$$eval(".show-row", (n) => n.length);
    add(ui, "切到追剧视图有剧行", showRowCount > 0, `${showRowCount} 行`);
    await page.screenshot({ path: path.join(SHOTS, `${ui}-6-shows.png`) });

    /*
     * P0-3 剧行乐观(issues/26-09-19-1959): 剧行默认**折叠**, 集行根本不渲染 ⇒
     * 剧行是折叠态下**唯一**能显示"在飞"的元素。BUG-3 当年只补了组行(辅种页)与集行(追剧页),
     * 剧行这一级漏了 —— 整剧暂停的补丁 0ms 就贴上, 但折叠态下没有任何可见元素把它显示出来。
     * 故必须在**折叠态**下断言(下面展开剧的那一节测的是集行, 覆盖不到这里)。
     */
    if (showRowCount > 0) {
      const sRow = (await page.$$(".show-row"))[0];
      const before = await sRow.evaluate((el) => el.className);
      await sRow.click({ button: "right" });
      await page.waitForSelector(".ctx-menu", { timeout: 5000 }).catch(() => null);
      const sItems = await page.$$(".ctx-item");
      let sClicked = false;
      for (const h of sItems) {
        const t = (await h.textContent()) || "";
        if (t.includes("暂停整剧")) { await h.click(); sClicked = true; break; }
      }
      /*
       * 不能用「固定睡 150ms 再采一次」:
       * ① 成功路径 —— 整剧操作会把该剧**全部**成员一起补丁(桩里这一"剧"就有 1500 个种子),
       *    applyOptimistic 逐 hash 扫表, 补丁贴完前 pendingOps 还没填齐 ⇒ 150ms 采样会假失败;
       * ② 失败路径 —— 补丁贴在 POST **之前**(issue 26-09-19-1939 的修法), 失败要等回执回来才回滚,
       *    150ms 采样会看到"还没回滚"的假阳性(实测 atlas 就抓到过)。
       * 故两条路径都等条件成立再断言: 成功等 is-pending 出现, 失败等 pendingOps 归零。
       * 真机上单剧通常几十个种子, 会比桩里快得多 —— 轮询把两种规模都覆盖到。
       */
      let after = null;
      if (sClicked && EXPECT_CMD === "error") {
        await page.waitForFunction(`Object.keys(${INST}.pendingOps || {}).length === 0`,
          null, { timeout: 4000 }).catch(() => null);   // 等回滚
        after = await page.$$eval(".show-row", (ns) => (ns[0] ? ns[0].className : null));
        add(ui, "P0-3 剧行乐观(失败不留假状态)", !!after && !after.includes("is-pending"),
          `${before} -> ${after}`);
      } else {
        const appeared = sClicked ? await page.waitForFunction(
          "!!document.querySelector('.show-row') && document.querySelector('.show-row').className.includes('is-pending')",
          null, { timeout: 1500 }
        ).then(() => true).catch(() => false) : false;
        after = await page.$$eval(".show-row", (ns) => (ns[0] ? ns[0].className : null));
        add(ui, "P0-3 剧行乐观(剧行 is-pending)", sClicked && appeared,
          `${before} -> ${after}(轮询 1.5s ${appeared ? "内出现" : "内未出现"})`);
      }
      await page.waitForTimeout(3400);  // 等乐观回落, 别把 pending 带进后面的集行断言
    }

    /*
     * P0-3 整集乐观(BUG-3): 集行状态色来自后端回传的 e.state(**标量拷贝**), 成员 kind 被补丁
     * 改过也不会变 ⇒ 整集/整剧此前点了没有任何即时反馈。这里断言集行在回执前就带上 is-pending
     * 且 s- 状态色已换(epState() 按与后端同一张 STATE_RANK 表现算)。
     */
    if (showRowCount > 0) {
      const sHandles = await page.$$(".show-row");
      await sHandles[0].click();  // 展开剧 -> 出集行
      await page.waitForSelector(".group-row.ep-row", { timeout: 8000 }).catch(() => null);
      const epHandles = await page.$$(".group-row.ep-row");
      add(ui, "展开剧后有集行", epHandles.length > 0, `${epHandles.length} 集`);
      if (epHandles.length) {
        const before = await epHandles[0].evaluate((el) => el.className);
        await epHandles[0].click({ button: "right" });
        await page.waitForSelector(".ctx-menu", { timeout: 5000 }).catch(() => null);
        const eItems = await page.$$(".ctx-item");
        let eClicked = false;
        await armPending(page, ".group-row.ep-row.is-pending");   // 点击**之前**装好
        for (const h of eItems) {
          const t = (await h.textContent()) || "";
          if (t.includes("暂停整集") || t.includes("暂停整剧") || t.trim() === "暂停") { await armClick(page, h); await h.click(); eClicked = true; break; }
        }
        await page.waitForTimeout(900);
        const p = await readPending(page);
        const after = await page.$$eval(".group-row.ep-row", (ns) => (ns[0] ? ns[0].className : null));
        if (EXPECT_CMD === "error") {
          const pend = await readInst(page, "Object.keys(vm.pendingOps || {}).length");
          const sCls = (c) => ((c || "").split(" ").find((x) => x.startsWith("s-")) || "");
          add(ui, "P0-3 整集乐观失败后回滚(集行)",
            eClicked && !!after && !after.includes("is-pending") && pend === 0 && sCls(after) === sCls(before),
            `${before} -> ${after} / pendingOps ${pend}`);
        } else {
          add(ui, "P0-3 整集乐观(集行 is-pending)", eClicked && p.appear !== null,
            `点击 → 集行出现 pending ${p.appear === null ? "从未出现" : p.appear + "ms"} / 消失 ${p.gone === null ? "-" : p.gone + "ms"}`);
        }
        await page.waitForTimeout(600);
      }
    }

    await nav[0].click();  // 回分组
    await page.waitForTimeout(600);
    const backRows = await page.$$eval(".group-row", (n) => n.length);
    add(ui, "切回分组视图有数据", backRows > 0, `${backRows} 行`);

    /*
     * BUG-8: 刷新后停在追剧页**不能空白**。视图偏好是持久化的(localStorage), 而 P1-1 的
     * "按视图回传"若只回 shows, 前端的成员索引(memberByHash)就是空的 ⇒ 每个集的成员都被
     * filter(Boolean) 丢掉 ⇒ 0 行; 且 rid 已记住 ⇒ 之后每轮都是"版本未变不回传", 自己不会恢复,
     * 必须手动切一次视图才回来。放最后做(要 reload, 会重置页面状态)。
     */
    {
      await page.evaluate(`localStorage.setItem("autoqb.ui.view", "shows")`);
      await page.reload({ waitUntil: "domcontentloaded" });
      await page.waitForTimeout(3500);
      const d = await page.evaluate(`(() => {
        const vm = ${INST};
        return { viewMode: vm.viewMode, idx: vm.memberByHash.size, shows: vm.decoratedShows.length,
                 rows: document.querySelectorAll(".show-row").length };
      })()`);
      add(ui, "BUG-8 刷新后追剧页不空白", d.viewMode === "shows" && d.rows > 0,
        `索引 ${d.idx} / 剧 ${d.shows} / 行 ${d.rows}`);
      await page.evaluate(`localStorage.removeItem("autoqb.ui.view")`);
    }
  } else {
    add(ui, "顶栏三视图按钮存在", false, `nav.tabs button = ${nav.length}`);
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
 * 版本对齐(踩过的坑): playwright 1.63 要 chromium-1243, 本机已装的是 chromium-1234 ⇒
 * 报 "Executable doesn't exist"。解法: 装与之匹配的 playwright-core@1.62(不用下浏览器):
 *   cd <node workspace> && PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1 npm i --no-audit --no-fund playwright-core@1.62.0
 * 运行时用 `require("playwright-core")` —— ESM 的 import 不认 NODE_PATH, 故本脚本用 CJS。
 */
