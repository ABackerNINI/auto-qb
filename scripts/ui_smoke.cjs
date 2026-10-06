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
 *   (--torrents 已随块A 总数校验(S1)/块B 行窗口化门控(S5)迁入 e2e/ —— 本脚本不再消费该参数)
 *   --expect-cmd ok|error|hang  与桩服务 --cmd-result 对应(默认 ok)
 *   (--skip-check on|off 已随 W5-off 精简轮迁入 e2e/menus.spec.mjs, S4 批 —— 本脚本不再支持)
 *   --hr-scene on|empty|off 已随 HR 表③断言组迁入 e2e/hr-history.spec.mjs, S5 批 —— 本脚本不再支持
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
/* --torrents 的消费方(块A 总数校验已于 S1、块B 行窗口化门控已于 S5 迁入 e2e/ —— 后者是
 * EXPECT_N 的最后一个调用方)已全部离开, EXPECT_N 常量随块B 一并退役; 单点在
 * e2e/harness.mjs 的 TORRENTS(env E2E_TORRENTS)。 */
const EXPECT_CMD = argv("expect-cmd", "ok");
/* --skip-check 两态参数与 W5-off 精简轮已于 2026-10-06 迁入 e2e/menus.spec.mjs(S4 批,
 * requireMode skipCheck 门控), 本脚本不再支持该参数。 */
/* --hr-scene 参数与 HR 表③断言组已于 2026-10-06 迁入 e2e/hr-history.spec.mjs(S5 批,
 * 计划 26-10-06-0708 §3.3; requireMode hrScene 门控), 本脚本不再支持该参数。 */

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

/*
 * readInst helper(原 L79-81)已于 2026-10-06 退役: 其最后一个调用方(块A 迁移时留下的
 * tRows/tTotal 脚手架)随块B 一并迁入 e2e/perf.spec.mjs(S5 批), 单点在 e2e/lib/vm.mjs。
 */

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
   * 计划 26-10-06-0708 §3.3; 对账映射表见该文件头)。
   */

  /*
   * 块B(性能埋点 P1-2 主线程阻塞/P1-3 强制布局/行窗口化生效/占位总高/滚动不塌陷+末行可见,
   * 原 L500–585)已于 2026-10-06 迁入 e2e/perf.spec.mjs(S5 批, 计划 26-10-06-0708 §3.3;
   * 对账映射表见该文件头)。其专属脚手架(nav 页签引用 + 种子视图就位 + tRows/tTotal 读数,
   * 只供块B 的 gbrBudget 与"行窗口化生效"当输入)随块一并移除; A/B 长任务埋点与
   * getBoundingClientRect 计数器随块搬进 perf.spec(阈值逐字保留)。
   */

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
   * HR 拉取历史表③(懒加载/五形态徽章/仅看异常/行展开明细, 原 L1725–1790)已于 2026-10-06
   * 迁入 e2e/hr-history.spec.mjs(S5 批, 计划 26-10-06-0708 §3.3; 对账映射表见该文件头):
   * requireMode hrScene 门控与旧 `if (HR_SCENE === "on")` 同构(empty/off 整组 skip,
   * 消息带当前 env 值); vm 直调(hubGo/hrsToggle/hrsCollapse/hubBack)全部换成真实手势
   * (hub 卡片/「展开」钮/summary 点击), 仅看异常复原改再点一次 chip。
   */

  /*
   * 块H(列设置守阵 ×5: 多标签同步/异视口双窗+F3/全自动页不落px/隐藏列宽度保留/v4→v5迁移,
   * 原 L235–399; 计划取证 L1795–1985)已于 2026-10-06 迁入 e2e/column-prefs.spec.mjs(S6 批,
   * 计划 26-10-06-0708 §3.3; 对账映射表见该文件头)。专属脚手架 colHide/dragCol/colState/
   * clearCols 随块一并退役(拖宽手势 mouse.move/down/up 逐字照搬; 守阵 3「隐藏前从 _visibleCols
   * 取 key」的时序坑注释随迁; 列菜单改真实手势分区+文案定位, F3 模拟与 v4 注入两处 evaluate 按
   * D4 保留)。
   */

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
