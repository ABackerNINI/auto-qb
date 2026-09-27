/* boot.js — 模板分片注入胶水(两套 UI 共用, 见 plans/26-09-26-2233 §5)
 *
 * shell(index.html)只保留 sprite + #app 内联段(登录遮罩) + 分片清单(tpl-manifest) + 本脚本;
 * 页面区模板拆在 tpl/*.html, 由这里按清单顺序 fetch 后注入, 全部成功才按序放行逻辑脚本
 * (app.js 末尾 createApp().mount("#app") 执行时模板已完整)。任何一步失败: 显式错误占位 + 停止,
 * 不放行任何逻辑脚本 —— 与「配置加载失败 + 重试」同风格, 不留半挂状态。
 * 时序纪律: 动态插入的 <script> 默认 async=true, 必须 async=false + onload 链保序。
 */
(function () {
  "use strict";

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
  var partIdx = 0;

  function nextPart() {
    if (partIdx >= mf.parts.length) {
      injectParts();
      return;
    }
    var part = mf.parts[partIdx++];
    var into = part.into === "body" ? "body" : "app";
    fetch(part.src, { credentials: "same-origin" }).then(function (res) {
      if (!res.ok) throw new Error(part.src + " HTTP " + res.status);
      return res.text();
    }).then(function (text) {
      buckets[into] += text;
      nextPart();
    }).catch(function (err) {
      fail("分片加载失败: " + (err && err.message || err));
    });
  }

  function injectParts() {
    app.insertAdjacentHTML("beforeend", buckets.app);
    if (buckets.body) document.body.insertAdjacentHTML("beforeend", buckets.body);
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
