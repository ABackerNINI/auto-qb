/* 阶段2 浏览器冒烟(ad-hoc, dev-only, 不入仓库): 站点页生效值回填 + 来源徽标
 * 前置: uv run python scripts/ui_harness.py --torrents 30 --port 8123 --no-groups
 * 运行: node tmp-analysis/phase2_smoke.cjs
 */
const path = "C:/Program Files/nodejs/node_modules/@playwright/cli/node_modules/playwright-core";
const { chromium } = require(path);

const BASE = "http://127.0.0.1:8123";
const results = [];
const add = (name, ok, detail) => {
  results.push({ name, ok });
  console.log(`${ok ? "PASS" : "FAIL"}  ${name}${detail ? " — " + detail : ""}`);
};

const EXERCISE_TREE = {
  config: {
    schema_version: "4",
    remove_similar_tags: "true",
    hr: { add_tag: "GTag", overwrite_category: "true" },
    trackers: {
      HHan: {
        domains: ["hhanclub.net"],
        hr: { required_seeding_time: "3D", condition: "80%", add_tag: "" },
      },
      BBB: {
        domains: ["btschool.net"],
        remove_similar_tags: "false",
        hr: { required_seeding_time: "2D", condition: "80%" },
      },
    },
  },
};

(async () => {
  // 0. 桩服务无磁盘 config_path(make_manager 内存配置), PUT 落盘路径不可用 ——
  //    阶段2 是纯显示层, 直接以 cfgSetTree 灌演练树(与保存后前端持有的树同构), 不测写盘。
  const get = await (await fetch(BASE + "/api/config")).json();
  add("桩服务 /api/config 可达", !!(get && get.tree));

  const browser = await chromium.launch({
    // 本机已装的 chromium 是 1243, @playwright/cli 捆的 playwright-core 要 1247 —— 显式指路径
    executablePath: "C:/Users/11059/AppData/Local/ms-playwright/chromium-1243/chrome-win64/chrome.exe",
  });
  for (const ui of ["atlas", "prism", "console"]) {
    const page = await browser.newPage();
    const errors = [];
    page.on("pageerror", (e) => errors.push(String(e)));
    await page.goto(`${BASE}/${ui}/`);
    await page.waitForSelector("#app .topbar, #app [class*=topbar]", { timeout: 15000 });

    // Vue 根实例(ui_smoke 同款取法)
    const vm = await page.evaluate(() => {
      const app = document.querySelector("#app");
      let n = app && app._vnode;
      while (n && !n.component) n = n.child || n.suspense && n.suspense.activeBranch || null;
      return n && n.component ? true : false;
    });
    add(`[${ui}] Vue 根实例可达`, !!vm);

    // 打开设置页 → 灌演练树 → 站点分区选中 HHan + 展开 hr 段
    await page.evaluate(async (tree) => {
      const app = document.querySelector("#app");
      let n = app && app._vnode;
      while (n && !n.component) n = n.child || null;
      const root = n.component.proxy;
      await root.openSettings();
      root.cfgSetTree(tree);
      root.hub.view = "trackers";
      root.cfg.trackerKey = "HHan";
      root.cfg.openSections = { "config.trackers.HHan.hr": true };
    }, EXERCISE_TREE);
    await page.waitForTimeout(400);

    const rowInfo = (key) =>
      page.evaluate((k) => {
        const el = document.querySelector(`[data-hb-key="${k}"]`);
        if (!el) return null;
        const lb = el.querySelector(".hb-lb");
        const badges = lb ? [...lb.querySelectorAll(".hb-badge")].map((b) => b.textContent.trim()) : [];
        const input = el.querySelector(".hb-input");
        const sw = el.querySelector(".hb-switch");
        const inline = [...el.querySelectorAll(".hb-switch")].map((s) => ({
          text: (s.querySelector(".hb-sw-text") || {}).textContent,
          checked: s.querySelector("input") ? s.querySelector("input").checked : null,
          badges: [...s.querySelectorAll(".hb-badge")].map((b) => b.textContent.trim()),
        }));
        return {
          badges,
          value: input ? input.value : null,
          placeholder: input ? input.getAttribute("placeholder") : null,
          switchChecked: sw && sw.querySelector("input") ? sw.querySelector("input").checked : null,
          swText: sw ? (sw.querySelector(".hb-sw-text") || {}).textContent : null,
          inline,
        };
      }, key);

    // ---- HHan: hr 段 add_tag = ''(tri_state 覆盖为空)
    let r = await rowInfo("config.trackers.HHan.hr.add_tag");
    add(`[${ui}] HHan add_tag 徽标=站点(空串也算存在)`, !!r && r.badges.includes("站点"), JSON.stringify(r && r.badges));
    add(`[${ui}] HHan add_tag 输入框显示空串`, !!r && r.value === "", JSON.stringify(r && r.value));
    add(`[${ui}] HHan add_tag 占位串显示全局生效值 GTag`, !!r && r.placeholder === "GTag", JSON.stringify(r && r.placeholder));

    // ---- HHan: add_category 缺失 → 徽标全局 + 回填(全局也没有 → schema 默认空)
    r = await rowInfo("config.trackers.HHan.hr.add_category");
    add(`[${ui}] HHan add_category 徽标=全局`, !!r && r.badges.includes("全局") && !r.badges.includes("站点"), JSON.stringify(r && r.badges));
    add(`[${ui}] HHan add_category 行无「默认」矛盾徽标`, !!r && !r.badges.includes("默认"), JSON.stringify(r && r.badges));

    // ---- HHan: remove_similar_tags 缺失 → 徽标全局 + 开关显示全局 true
    r = await rowInfo("config.trackers.HHan.remove_similar_tags");
    add(`[${ui}] HHan remove_similar_tags 徽标=全局`, !!r && r.badges.includes("全局"), JSON.stringify(r && r.badges));
    add(`[${ui}] HHan remove_similar_tags 开关显示生效值 ON(全局 true)`, !!r && r.switchChecked === true, JSON.stringify(r));
    add(`[${ui}] HHan remove_similar_tags 行无「默认」矛盾徽标`, !!r && !r.badges.includes("默认"), JSON.stringify(r && r.badges));

    // ---- HHan: 内联开关 overwrite_category(站点缺失)→ 全局 true 回填 + 徽标全局
    r = await rowInfo("config.trackers.HHan.hr.add_category");
    const inl = r && r.inline.find((x) => (x.text || "").indexOf("覆盖已有分类") >= 0);
    add(`[${ui}] HHan 内联开关按全局生效值显示 ON`, !!inl && inl.checked === true, JSON.stringify(inl));
    add(`[${ui}] HHan 内联开关徽标=全局`, !!inl && inl.badges.includes("全局"), JSON.stringify(inl && inl.badges));

    // ---- 切到 BBB
    await page.evaluate(() => {
      const app = document.querySelector("#app");
      let n = app && app._vnode;
      while (n && !n.component) n = n.child || null;
      const root = n.component.proxy;
      root.cfg.trackerKey = "BBB";
      root.cfg.openSections = { "config.trackers.BBB.hr": true };
    });
    await page.waitForTimeout(300);

    r = await rowInfo("config.trackers.BBB.remove_similar_tags");
    add(`[${ui}] BBB remove_similar_tags 徽标=站点(显式 false)`, !!r && r.badges.includes("站点"), JSON.stringify(r && r.badges));
    add(`[${ui}] BBB remove_similar_tags 开关显示站点 false`, !!r && r.switchChecked === false, JSON.stringify(r));

    r = await rowInfo("config.trackers.BBB.hr.add_tag");
    add(`[${ui}] BBB add_tag 徽标=全局 + 回填 GTag`, !!r && r.badges.includes("全局") && r.value === "GTag", JSON.stringify(r));

    // ---- 全局页(自动化): remove_similar_tags 不打来源徽标, 行为不变
    await page.evaluate(() => {
      const app = document.querySelector("#app");
      let n = app && app._vnode;
      while (n && !n.component) n = n.child || null;
      n.component.proxy.hub.view = "maintenance";
    });
    await page.waitForTimeout(300);
    r = await rowInfo("config.remove_similar_tags");
    add(`[${ui}] 全局页 remove_similar_tags 无来源徽标`, !!r && !r.badges.includes("站点") && !r.badges.includes("全局"), JSON.stringify(r && r.badges));
    add(`[${ui}] 全局页 remove_similar_tags 值不变(ON)`, !!r && r.switchChecked === true, JSON.stringify(r));

    // ---- 交互: 点 BBB add_tag 输入框改动会进树(既有 set 链不受影响)
    await page.evaluate(() => {
      const app = document.querySelector("#app");
      let n = app && app._vnode;
      while (n && !n.component) n = n.child || null;
      const root = n.component.proxy;
      root.hub.view = "trackers";
      root.cfg.trackerKey = "BBB";
      root.cfg.openSections = { "config.trackers.BBB.hr": true };
    });
    await page.waitForTimeout(300);
    await page.evaluate(() => {
      const app = document.querySelector("#app");
      let n = app && app._vnode;
      while (n && !n.component) n = n.child || null;
      const root = n.component.proxy;
      root.cfgSetPath(["config", "trackers", "BBB", "hr", "add_tag"], "Edited");
    });
    await page.waitForTimeout(200);
    r = await rowInfo("config.trackers.BBB.hr.add_tag");
    const treeVal = await page.evaluate(() => {
      const app = document.querySelector("#app");
      let n = app && app._vnode;
      while (n && !n.component) n = n.child || null;
      return n.component.proxy.cfg.tree.config.trackers.BBB.hr.add_tag;
    });
    add(`[${ui}] 编辑写入树 + 行显示同步`, r && r.value === "Edited" && treeVal === "Edited", JSON.stringify({ dom: r && r.value, tree: treeVal }));

    add(`[${ui}] 无页面 JS 错误`, errors.length === 0, errors.join(" | "));
    await page.close();
  }
  await browser.close();
  const bad = results.filter((x) => !x.ok).length;
  console.log(`\n${results.length - bad}/${results.length} passed`);
  process.exit(bad ? 1 : 0);
})().catch((e) => {
  console.error("SMOKE ERROR:", e);
  process.exit(2);
});
