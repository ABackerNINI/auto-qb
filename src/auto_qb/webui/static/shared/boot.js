/* boot.js — 模板分片注入胶水(两套 UI 共用, 见 plans/26-09-26-2233 §5)
 *
 * shell(index.html)只保留 sprite + #app 内联段(登录遮罩) + 分片清单(tpl-manifest) + 本脚本;
 * 页面区模板拆在 tpl/*.html, 由这里按清单顺序 fetch 后注入, 全部成功才按序放行逻辑脚本
 * (app.js 末尾 createApp().mount("#app") 执行时模板已完整)。任何一步失败(含请求悬挂被请求级
 * 超时兜住, issue 26-10-16-1303): 显式错误占位 + 停止, 不放行任何逻辑脚本 —— 与「配置加载失败
 * + 重试」同风格, 不留半挂状态。
 * 时序纪律: 动态插入的 <script> 默认 async=true, 必须 async=false + onload 链保序。
 */
(function () {
  "use strict";

  /* 分片装载的请求级超时(issue 26-10-16-1303): 裸 fetch 没有超时 —— 连接静默失效(服务端不响应 /
   * TCP 半开 / 中间设备丢包)时 await 永不返回, 装载链停在当前片、后续 then/catch 一个都不执行,
   * 应用永久停在白屏(v-cloak 前)且无提示。挂上限后悬挂变成一次**可报的失败**: catch -> fail()
   * 给可读占位 + 重新加载按钮(与分片 404 同一路径)。
   * !值比低层单点 aqbFetch(shared/fetch_low.js, 15s)短: 本链阻塞整个首屏, 早失败更重要。
   * !本文件在清单脚本之前执行(装载链本身是放行它们的前提), 用不了那个单点(定义还没跑到),
   *   故内联一份等价逻辑; 两处文案同款, 值各自守阵钉住。 */
  var BOOT_PART_TIMEOUT_MS = 10000;

  /* AbortError 的原始文案("The operation was aborted")对用户没有信息量 —— 与低层单点同款翻译 */
  function partErrText(err) {
    if (err && err.name === "AbortError") return "请求超时(" + (BOOT_PART_TIMEOUT_MS / 1000) + "s)";
    return (err && err.message || err);
  }

  /* UI 皮肤 cookie(autoqb_ui): 三套 UI 共用本脚本 = 唯一写入口 —— 打开任一 UI 就把它的
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

  var buckets = { app: "", body: "" };
  var slots = [];  /* 自定义选择器落点(方案A 停靠面板): { sel, text } —— app 桶插入后按选择器定位注入 */
  var partIdx = 0;

  function nextPart() {
    if (partIdx >= mf.parts.length) {
      injectParts();
      return;
    }
    var part = mf.parts[partIdx++];
    var into = part.into === "body" || part.into === "app" ? part.into : "";  // 其余值 = 自定义选择器
    var ctl = new AbortController();
    var timer = setTimeout(function () { ctl.abort(); }, BOOT_PART_TIMEOUT_MS);
    fetch(part.src, { credentials: "same-origin", signal: ctl.signal }).then(function (res) {
      if (!res.ok) throw new Error(part.src + " HTTP " + res.status);
      return res.text();
    }).then(function (text) {
      if (into) buckets[into] += text;
      else slots.push({ sel: part.into, text: text });
      nextPart();
    }).catch(function (err) {
      fail("分片加载失败: " + partErrText(err));
    }).finally(function () {
      clearTimeout(timer);  // 成功/失败/悬挂都清掉(不留悬挂定时器)
    });
  }

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
    var scriptIdx = 0;
    (function nextScript() {
      if (scriptIdx >= mf.scripts.length) return;
      var src = mf.scripts[scriptIdx++];
      var el = document.createElement("script");
      el.src = src;
      el.async = false; /* onload 链已串行, 此处再钉死插入序 -> 执行序 */
      el.onload = nextScript;
      el.onerror = function () { fail("脚本加载失败: " + src); };
      document.head.appendChild(el);
    })();
  }

  nextPart();
})();
