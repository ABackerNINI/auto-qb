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
      // 挑一个**未暂停**的行(上一段刚暂停过一行, 再点它菜单里就是"开始"了)
      const rows = await page.$$(".torrent-row");
      let target = null;
      for (const r of rows) {
        const cls = (await r.getAttribute("class")) || "";
        if (!cls.includes("s-paused")) { target = r; break; }
      }
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
      for (const b of btns) {
        const t = (await b.textContent()) || "";
        if (t.includes("暂停")) { await b.click(); bulkClicked = true; break; }
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
        add(ui, "P0-3 批量乐观覆盖全部目标", pend >= Math.min(picked, N) * 0.8,
          `pendingOps ${pend} / 目标 ${picked}`);
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
      const idx = await page.evaluate(`(() => {
        const rows = [...document.querySelectorAll('.group-row[data-table="group"]')];
        return rows.findIndex((r) => !r.className.includes('s-paused'));
      })()`);
      const gHandles = await page.$$('.group-row[data-table="group"]');
      if (idx < 0 || !gHandles[idx]) {
        add(ui, "P0-3 整组乐观(组行 is-pending)", false, "找不到可暂停的组行");
      } else {
        const key = await gHandles[idx].evaluate((el) => el.dataset.key);
        const before = await gHandles[idx].evaluate((el) => el.className);
        await gHandles[idx].click({ button: "right" });
        await page.waitForSelector(".ctx-menu", { timeout: 5000 }).catch(() => null);
        const gItems = await page.$$(".ctx-item");
        let gClicked = false;
        for (const h of gItems) {
          const t = (await h.textContent()) || "";
          if (t.includes("暂停整组") || t.trim() === "暂停") { await h.click(); gClicked = true; break; }
        }
        await page.waitForTimeout(150);
        const after = await page.evaluate(
          `(() => { const el = document.querySelector('.group-row[data-table="group"][data-key=${JSON.stringify(key)}]'); return el ? el.className : null; })()`);
        if (EXPECT_CMD === "error") {
          // error 模式: 回执是**瞬间**回的, 乐观窗口可能在采样前就关了 ⇒ 改断言"回滚干净"
          const pend = await readInst(page, "Object.keys(vm.pendingOps || {}).length");
          const sCls = (c) => ((c || "").split(" ").find((x) => x.startsWith("s-")) || "");
          add(ui, "P0-3 整组乐观失败后回滚(组行)",
            gClicked && !!after && !after.includes("is-pending") && pend === 0 && sCls(after) === sCls(before),
            `${before} -> ${after} / pendingOps ${pend}`);
        } else {
          add(ui, "P0-3 整组乐观(组行 is-pending)", gClicked && !!after && after.includes("is-pending"),
            `${before} -> ${after}`);
        }
        await page.waitForTimeout(3400);  // 等乐观回落(3s 兜底), 别把 pending 带进后面的断言
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
        for (const h of eItems) {
          const t = (await h.textContent()) || "";
          if (t.includes("暂停整集") || t.includes("暂停整剧") || t.trim() === "暂停") { await h.click(); eClicked = true; break; }
        }
        await page.waitForTimeout(150);
        const after = await page.$$eval(".group-row.ep-row", (ns) => (ns[0] ? ns[0].className : null));
        if (EXPECT_CMD === "error") {
          const pend = await readInst(page, "Object.keys(vm.pendingOps || {}).length");
          const sCls = (c) => ((c || "").split(" ").find((x) => x.startsWith("s-")) || "");
          add(ui, "P0-3 整集乐观失败后回滚(集行)",
            eClicked && !!after && !after.includes("is-pending") && pend === 0 && sCls(after) === sCls(before),
            `${before} -> ${after} / pendingOps ${pend}`);
        } else {
          add(ui, "P0-3 整集乐观(集行 is-pending)", eClicked && !!after && after.includes("is-pending"),
            `${before} -> ${after}`);
        }
        await page.waitForTimeout(3400);
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
