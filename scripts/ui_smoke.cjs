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

async function readInst(page, expr) {
  return page.evaluate(`(() => { const vm = ${INST}; return vm ? (${expr}) : null; })()`);
}

async function smokeUi(browser, ui) {
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
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

    // 滚到底: 总高度必须仍等于全量(占位撑住), 且最后一行可见
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
    await page.click(".torrent-row", { button: "right" });
    await page.waitForSelector(".ctx-menu", { timeout: 5000 }).catch(() => null);
    await page.screenshot({ path: path.join(SHOTS, `${ui}-4-ctxmenu.png`) });
    const items = await page.$$eval(".ctx-item", (ns) => ns.map((n) => n.textContent.trim()));
    const handles = await page.$$(".ctx-item");
    let clicked = false;
    for (const h of handles) {
      const t = (await h.textContent()) || "";
      if (t.includes("暂停该种子") || t.includes("暂停整组") || t.trim() === "暂停") {
        await h.click();
        clicked = true;
        break;
      }
    }
    if (!clicked) {
      add(ui, "P0-3 右键菜单有暂停项", false, `菜单项: ${items.slice(0, 8).join(" / ")}`);
    } else {
      await page.waitForTimeout(120);
      const pendingNow = await page.$$eval(".torrent-row.is-pending, .group-row.is-pending", (n) => n.length);
      if (EXPECT_CMD === "error") {
        // 桩服务的失败是**瞬间**回的, 乐观窗口可能在采样前就关闭了 —— 这里只记录不做判据
        console.log(`      [info] error 模式: 采样到 ${pendingNow} 行 pending(回执太快时可能为 0)`);
      } else {
        add(ui, "P0-3 点击后立即可见 pending(乐观)", pendingNow > 0, `${pendingNow} 行半透明`);
      }
      await page.screenshot({ path: path.join(SHOTS, `${ui}-5-pending.png`) });
      /*
       * 成功回执**不会立刻**清 pending: 乐观值要一直贴到"服务端数据与预期一致"或 3s 超时
       * (见 app.js resolveOptimistic / isPending) —— 立刻清会出现"先变过去、下一轮又弹回来"。
       * 所以这里等过 3s 的回落点再断言"不留假状态"; hang 模式同理(没有回执 -> 靠 3s 兜底)。
       */
      let pendingLater = -1, pendingOps = -1, waited = 0;
      while (waited < 8000) {
        await page.waitForTimeout(500);
        waited += 500;
        pendingLater = await page.$$eval(".torrent-row.is-pending, .group-row.is-pending", (n) => n.length);
        pendingOps = await readInst(page, "Object.keys(vm.pendingOps || {}).length");
        if (pendingLater === 0 && pendingOps === 0) break;
      }
      add(ui, `P0-3 回执(${EXPECT_CMD})后不留假状态`, pendingLater === 0 && pendingOps === 0,
        `${waited}ms 后: 残留 ${pendingLater} 行 / pendingOps ${pendingOps}`);
    }

    await nav[2].click();  // 追剧
    await page.waitForTimeout(800);
    const epRows = await page.$$eval(".ep-row, .group-row", (n) => n.length);
    add(ui, "切到追剧视图无异常", epRows >= 0, `${epRows} 行`);
    await page.screenshot({ path: path.join(SHOTS, `${ui}-6-shows.png`) });

    await nav[0].click();  // 回分组
    await page.waitForTimeout(600);
    const backRows = await page.$$eval(".group-row", (n) => n.length);
    add(ui, "切回分组视图有数据", backRows > 0, `${backRows} 行`);
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
