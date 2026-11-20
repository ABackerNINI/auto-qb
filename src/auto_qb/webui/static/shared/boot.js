/* boot.js — 模板分片注入胶水(四套 UI 共用, 见 plans/26-09-26-2233 §5 / 26-11-20-0727 §03)
 *
 * shell(index.html)只保留 sprite + #app 内联段(登录遮罩) + 分片清单(tpl-manifest) + 本脚本;
 * 页面区模板拆在 tpl/*.html, 由这里并发 fetch 后按清单序注入, 全部成功才按序放行逻辑脚本
 * (app.js 末尾 createApp().mount("#app") 执行时模板已完整)。任何一步失败(含请求悬挂被请求级
 * 超时兜住, issue 26-10-16-1303): 显式错误占位 + 停止, 不放行任何逻辑脚本 —— 与「配置加载失败
 * + 重试」同风格, 不留半挂状态。
 * 时序纪律(plan 26-11-20-0727 P1): 分片 Promise.all 并发 fetch, 结果按清单 index 归位后拼接;
 * 脚本用 link rel=preload as=script 并发预取(不 fetch —— P1 中间件仍全量 no-cache, fetch 预取
 * 后再插 script src 会二次 ETag 重验, 破坏「每脚本只 1 次网络请求」), 全部成功后按清单序批量
 * 插入 async=false 脚本, 执行序 = 清单序。fail-fast 不变: 任一失败即 fail(), 不注入半成品。
 */
(function () {
  "use strict";

  /* 分片装载的请求级超时(issue 26-10-16-1303): 裸 fetch 没有超时 —— 连接静默失效(服务端不响应 /
   * TCP 半开 / 中间设备丢包)时 await 永不返回, 装载链停在当前片、后续 then/catch 一个都不执行,
   * 应用永久停在白屏(v-cloak 前)且无提示。挂上限后悬挂变成一次**可报的失败**: catch -> fail()
   * 给可读占位 + 重新加载按钮(与分片 404 同一路径)。
   * !值比低层单点 aqbFetch(shared/fetch_low.js, 15s)短: 本链阻塞整个首屏, 早失败更重要。
   * !本文件在清单脚本之前执行(装载链本身是放行它们的前提), 用不了那个单点(定义还没跑到),
   *   故内联一份等价逻辑; 两处文案同款, 值各自守阵钉住。
   * 并发化后(P1-1)每片仍各带一个 AbortController + 10s 定时器, 悬挂只拖垮该片 -> Promise.all
   * 整体 reject -> fail(), 不会留下半挂等待。 */
  var BOOT_PART_TIMEOUT_MS = 10000;

  /* AbortError 的原始文案("The operation was aborted")对用户没有信息量 —— 与低层单点同款翻译 */
  function partErrText(err) {
    if (err && err.name === "AbortError") return "请求超时(" + (BOOT_PART_TIMEOUT_MS / 1000) + "s)";
    return (err && err.message || err);
  }

  /* UI 皮肤 cookie(autoqb_ui): 四套 UI 共用本脚本 = 唯一写入口 —— 打开任一 UI 就把它的
   * 目录段记进 cookie(1 年), 之后从根路径 / 进入时服务端读 cookie 直达上次用的 UI
   * (修复"关窗口重开总回星图")。载体必须是 cookie 而非 localStorage: 307 在服务端裁决,
   * 服务端读不到 localStorage。这里只做形状校验, 目录是否真实存在由服务端把关
   * (static_ui.py::_remembered_ui), 改名/删除后的旧 cookie 会自动回落星图。 */
  var skin = location.pathname.split("/")[1];
  if (skin && /^[A-Za-z][A-Za-z0-9_-]{0,31}$/.test(skin)) {
    document.cookie = "autoqb_ui=" + skin + "; Path=/; Max-Age=31536000; SameSite=Lax";
  }

  var app = document.getElementById("app");

  function fail(msg) {
    /* 错误占位复用登录遮罩的类名拿一致样式; 此时 Vue 尚未启动, 纯 DOM 写入 */
    if (!app) { document.body.textContent = "auto-qb: " + msg; return; }
    app.innerHTML = '<div class="login-mask"><div class="login-card">'
      + '<div class="brand"><span class="brand-mark"><img class="brand-img" src="/shared/icon.png" alt=""></span>'
      + '<span>auto-qb</span></div>'
      + '<p class="error">界面资源加载失败: ' + msg + "</p>"
      + '<button type="button" class="bt primary">重新加载</button></div></div>';
    var btn = app.querySelector("button");
    if (btn) btn.addEventListener("click", function () { location.reload(); });
  }

  var mfEl = document.getElementById("tpl-manifest");
  if (!app || !mfEl) { fail("页面骨架不完整(缺 #app 或 tpl-manifest)"); return; }

  var mf;
  try {
    mf = JSON.parse(mfEl.textContent);
  } catch (e) {
    fail("tpl-manifest 不是合法 JSON: " + e.message);
    return;
  }
  if (!mf || !Array.isArray(mf.parts) || !mf.parts.length
    || !Array.isArray(mf.scripts) || !mf.scripts.length) {
    fail("tpl-manifest 清单为空或缺 parts/scripts");
    return;
  }

  /* P2-2(plan 26-11-20-0727 D4/D6): 版本查询参数单点 —— 分片 fetch URL / 脚本 preload href /
   * 最终 script src 三处都经它追加同一个 V。preload href 与 script src 必须逐字同形, 否则
   * preload 的缓存复用失效、脚本二次请求(D4)。V 来自 index.html head 注入的 window.AQB_V
   * (P2-a 已注入令牌, 服务端响应时替换为真实 V); 缺失(异常/直接开文件/诊断桩/node 探针)时
   * 优雅退化: 不加 v、不崩 —— 退化后 URL 仍是清单字面量。 */
  function withV(url) {
    var v = (typeof window !== "undefined" && window.AQB_V) ? String(window.AQB_V) : "";
    if (!v || !url) return url;
    return url + (url.indexOf("?") >= 0 ? "&v=" : "?v=") + v;
  }

  var buckets = { app: "", body: "" };
  var slots = [];  /* 自定义选择器落点(方案A 停靠面板): { sel, text } —— app 桶插入后按选择器定位注入 */
  var parts = mf.parts;

  /* P1-1(plan 26-11-20-0727): 并发 fetch 全部分片。每片独立 AbortController + 10s 定时器,
   * 各片 finally 清自己的定时器。Promise.all 的结果按入参 index 排列(与完成先后无关), 全部
   * 成功才在下面按清单序拼接注入 —— 顺序、全有或全无、10s 超时三条不变量都不变(D8);
   * 任一片 reject(404 / 网络错误 / 悬挂 abort) -> Promise.all reject -> fail(), 一片都不注入。 */
  var jobs = parts.map(function (part) {
    var ctl = new AbortController();
    var timer = setTimeout(function () { ctl.abort(); }, BOOT_PART_TIMEOUT_MS);
    return fetch(withV(part.src), { credentials: "same-origin", signal: ctl.signal }).then(function (res) {
      if (!res.ok) throw new Error(part.src + " HTTP " + res.status);
      return res.text();
    }).finally(function () {
      clearTimeout(timer);  // 成功/失败/悬挂都清掉(不留悬挂定时器)
    });
  });

  function findSlot(sel, root) {
    /* 递归下钻 template.content 找落点容器(见 injectParts 内注释) */
    var hit = root.querySelector(sel);
    if (hit) return hit;
    var tmpls = root.querySelectorAll("template");
    for (var i = 0; i < tmpls.length; i++) {
      hit = findSlot(sel, tmpls[i].content);
      if (hit) return hit;
    }
    return null;
  }

  function injectParts() {
    app.insertAdjacentHTML("beforeend", buckets.app);
    if (buckets.body) document.body.insertAdjacentHTML("beforeend", buckets.body);
    /* 自定义落点: 目标容器可在 <template v-if> 片段内部(如种子视图的 .drawer-dock, 面板随视图
     * 出入) —— querySelector 够不到 template.content, 且模板存在浏览器解析出的**嵌套**
     * (querySelectorAll 不会下钻 content 片段), 须逐层递归; 找不到即 fail-fast,
     * 与分片加载失败同一处置(不留半挂状态)。必须在 Vue 挂载前完成(本函数先于脚本链执行)。 */
    for (var si = 0; si < slots.length; si++) {
      var target = findSlot(slots[si].sel, app);
      if (!target) { fail("分片落点不存在: " + slots[si].sel); return; }
      target.insertAdjacentHTML("beforeend", slots[si].text);
    }
    injectScripts();
  }

  /* P1-2(plan 26-11-20-0727): 脚本从「逐个插入 + onload 递归」改为「并发预取 + 批量插入」。
   * 预取只用 link rel=preload as=script, 不 fetch —— P1 阶段中间件仍全量 no-cache, fetch 预取
   * 后再插 script src 会二次 ETag 重验, 破坏「每脚本只 1 次网络请求」; preload 结果可被后续
   * script 复用缓存。全部预取成功(onload 计数到齐)才按清单序批量插入 async=false 脚本 ——
   * 执行序 = 清单序(顶层 const 与依赖顺序依赖它, 不用 type=module 改作用域); 任一预取 onerror
   * -> fail(), 且发生在插入**任何**脚本之前(D8 fail-fast, 404 专门注入验证的点)。P2-b 起三处
   * URL(分片 fetch / 本 preload href / 最终 script src)统一经 withV 追加同一个 V —— preload
   * 与 script src 逐字同形才能复用预取缓存, 不给脚本制造二次请求。 */
  function injectScripts() {
    var scripts = mf.scripts;
    var remaining = scripts.length;
    var failed = false;

    function preloadFail(src) {
      if (failed) return;  /* 多个预取同时失败只报一次 */
      failed = true;
      fail("脚本加载失败: " + src);
    }

    function insertAll() {
      for (var j = 0; j < scripts.length; j++) {
        var s = document.createElement("script");
        s.src = withV(scripts[j]);
        s.async = false; /* 批量按清单序插入 + async=false -> 执行序 = 清单序 0..N-1 */
        s.onerror = (function (src) {
          return function () { fail("脚本加载失败: " + src); };
        })(scripts[j]);
        document.head.appendChild(s);
      }
    }

    for (var i = 0; i < scripts.length; i++) {
      /* 用 IIFE 锁住每轮的 src(ES5 var 无块级作用域), 否则 onload/onerror 全指向最后一轮 */
      (function (src) {
        var link = document.createElement("link");
        link.rel = "preload";
        link.as = "script";
        link.href = withV(src);
        link.onload = function () {
          remaining -= 1;
          if (remaining === 0 && !failed) insertAll();
        };
        link.onerror = function () { preloadFail(src); };
        document.head.appendChild(link);
      })(scripts[i]);
    }
  }

  Promise.all(jobs).then(function (texts) {
    /* texts[i] 对应 parts[i] —— Promise.all 保序, 与并发完成先后无关 */
    for (var i = 0; i < texts.length; i++) {
      var part = parts[i];
      var into = part.into === "body" || part.into === "app" ? part.into : "";  // 其余值 = 自定义选择器
      if (into) buckets[into] += texts[i];
      else slots.push({ sel: part.into, text: texts[i] });
    }
    injectParts();
  }).catch(function (err) {
    fail("分片加载失败: " + partErrText(err));
  });
})();
