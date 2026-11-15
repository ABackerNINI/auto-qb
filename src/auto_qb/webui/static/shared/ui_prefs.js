/* auto-qb WEB UI · 配置备份(设置页「导出配置/导入配置」双钮 + 浏览器偏好 ui_prefs 段)
 *
 * 计划 26-11-14-0624 S3。bundle 四段里的三段(config_yaml/webui_keys/gtm)由后端
 * routes/backup.py 提供(GET /api/backup/export / POST /api/backup/import); 第四段
 * ui_prefs 是浏览器 localStorage 偏好 —— **只存浏览器**裁决(app.js 列状态注释, D3)的
 * 迁移面: 收集/写回全在本文件完成, bundle 文件经手但服务端零接触零持久化
 * (导出 = 前端把 ui_prefs 并进服务端响应再落盘; 导入 = 前端先摘走该段本地写回,
 * POST 只带勾选的服务端三段)。
 *
 * 约定与 ui_feedback.js 同一范式: 挂到 window.AQB_UI_PREFS, 由 app.js 末尾
 * app.mixin(window.AQB_UI_PREFS) 注入同一个 Vue 实例 —— 方法体里的 this 仍是那个
 * 组件实例(toast/confirmDialog/_openModal/api 跨模块互调与拆分前完全等价)。
 * !本文件在 HTML 里必须排在 app.js **之前**(app.js 末尾要读 window.AQB_UI_PREFS);
 *   aqbFetch(fetch_low.js)/aqbAuthHeaders(auth.js)是运行时调用, 无装载序依赖。
 *
 * 偏好键口径(D8/D11): 显式双清单(下方 PREF_KEYS / PREF_EXCLUDED), 新增浏览器存储键
 * 必须登记其一, 否则 S4 静态守阵(tests/test_webui_static_ui_prefs.py)红 —— 双清单是
 * localStorage/sessionStorage 键族的**完整对账面**(含排除面), 不是本功能用到的子集;
 * 对账范围 = autoqb.(点分)与 autoqb_/gtm.(存储键)两族字面量, **不含**: standalone 页
 * 自用键(fx/showcase.html 的 fxsc.* 族)、cookie autoqb_ui(boot.js 登录后皮肤, 一次成本
 * ≈0)、事件名 autoqb:* 冒号族(计划 §03 拍板)—— 与 S4 扫描口径同界。
 */
/* ---------------------------------------------------------------------------
 * 双清单单点(D8; 2026-11-14 grep static/ 实测, 每键标注读写点; 计划初版表 +
 * 实测新增 autoqb.ui.qbFx / autoqb.ui.kbdPersist 两键, 差异见计划回写)
 * ------------------------------------------------------------------------- */
/* PREF_KEYS: 进 bundle 的浏览器偏好(导出收集/导入写回)。值 = localStorage 原文字符串
 * (不做 JSON 二次解析: collect 原样读出、apply 原样写回, 解析失败面归零, round-trip 恒等)。 */
const PREF_KEYS = [
  /* 主题(prism/js/theme.js:13 键, :25 首帧同步读 / :70 写) */
  "autoqb.ui.theme",
  /* 顶栏页签位置(groups|settings; view.js:152 写, app.js:814 读) */
  "autoqb.ui.page",
  /* 主表视图形态(view.js:213 写, app.js:798 读) */
  "autoqb.ui.view",
  /* 站点/规则集 hub 子页(config_hub.js:203 写, :167 读) */
  "autoqb.ui.hub",
  /* 主表行语言(rowlang.js:28 首帧读 / :141 写) */
  "autoqb.ui.rowlang",
  /* 抽屉记忆: 上次页签(app.js:826 读, drawer_general.js:163 写) */
  "autoqb.ui.drawerTab",
  /* 抽屉记忆: 高度(app.js:840 读, drawer_general.js:224 写) */
  "autoqb.ui.drawerHeight",
  /* 抽屉记忆: 合并模式(app.js:865 读, drawer.js:44 键 / :246 写) */
  "autoqb.ui.drawerMerge",
  /* 抽屉记忆: 各页签模板选择(drawer_templates.js:80 键, :664 读 / :1103 写) */
  "autoqb.ui.drawerTpl",
  /* 流量图窗口档位(qb_traffic_chart.js:132-134 键单点, :142 读 / :1368 写) */
  "autoqb.ui.qbWinGlobal",
  "autoqb.ui.qbWinShared",
  /* 流量图纵轴三态(qb_traffic_chart.js:165-170 键单点, :178 读 / :1421 写) */
  "autoqb.ui.qbYAxisGlobal",
  "autoqb.ui.qbYAxisTorrent",
  "autoqb.ui.qbYAxisGroup",
  /* 流量图动效参数(qb_traffic_chart.js:204 键, :279 读 / :1668 写) */
  "autoqb.ui.qbFx",
  /* 键位提示常驻开关(lifecycle.js:18 键, :496 读 / :476 写; 计划 26-11-14-0041 W2) */
  "autoqb.ui.kbdPersist",
  /* 列状态意图存储(app.js:395 键, app.js:721-725 读 / columns_persist.js:78 唯一写漏斗;
   * v3/v4 遗留键经 LEGACY_COLS_KEYS 迁移, 不带走) */
  "autoqb_cols_v5",
  /* 时间列显示口径(app.js:406 键, app.js:412 读 / menu.js:71 写) */
  "autoqb_timefmt_v1",
];
/* PREF_EXCLUDED: 明确不进 bundle 的存储键(排除面, S4 对账闸的另一半)。 */
const PREF_EXCLUDED = [
  /* 登录凭据(auth.js:91,189 / lifecycle.js:314)—— 绝不带走(硬约束) */
  "autoqb_token",
  /* 列存储遗留迁移读键(app.js:396 LEGACY_COLS_KEYS; 只在本机缺 v5 时读一次) */
  "autoqb_cols_v4",
  "autoqb_cols_v3",
  /* origin 一次性提示(app.js:399; 换地址/端口各提示一次的状态, 非偏好) */
  "autoqb_cols_origin_hint_v1",
  /* 版本自愈 reload 节流戳(polling.js:31; sessionStorage, per-tab 预算状态) */
  "autoqb_version_reload_v1",
  /* 抽屉开合态记录(drawer_general.js:230; 只写不读, 非偏好) */
  "autoqb.ui.drawerOpen",
  /* gtm 尖峰 24h 消警时间戳(dialogs.js:29; 状态非偏好) */
  "gtm.spike.ack",
];
/* bundle 三段的服务端 section 名 -> 中文标签(确认勾选与结果报告共用一张表) */
const AQB_UP_SECTIONS = [
  { key: "config_yaml", label: "主配置(config.yml)" },
  { key: "webui_keys", label: "WebUI 快捷键" },
  { key: "gtm", label: "流量监控工具配置(gtm)" },
];
/* bundle format 字段闸值(与 routes/backup.py BUNDLE_FORMAT 逐字一致, 守阵钉) */
const AQB_UP_BUNDLE_FORMAT = "auto-qb-config-bundle";
/* 机器相关路径固定提示行(D10: 不做字段级回退, 提示行恒在) */
const AQB_UP_PATH_HINT =
  "bundle 含机器相关路径(gtm tool_dir/tool_exe、qB 保存路径、transfer targets 路径等), 导入后请核对";

/* collect: 读 PREF_KEYS 内 localStorage(bundle ui_prefs 段原文)。存储不可用(隐私模式
 * 访问即抛)逐键兜底为缺键 —— 收集失败不该打断导出, 最多少带几条偏好。 */
function aqbUiPrefsCollect() {
  const out = {};
  for (let i = 0; i < PREF_KEYS.length; i++) {
    const k = PREF_KEYS[i];
    let v = null;
    try {
      v = localStorage.getItem(k);
    } catch (e) {
      v = null;
    }
    if (v !== null) out[k] = v;
  }
  return out;
}
/* apply: bundle ui_prefs 段写回本机 localStorage。只覆盖 bundle 内出现的键(缺键保持
 * 本机值, R5); 未登记键忽略并进返回的警告数组(向前兼容, D8); 已登记但值非字符串
 * (手造/外来 bundle 的格式漂移)同样忽略 + 警告。null/undefined = 该键导出时无值, 按
 * 缺键语义静默跳过(保持本机值)。 */
function aqbUiPrefsApply(prefs) {
  const ignored = [];
  if (!prefs || typeof prefs !== "object" || Array.isArray(prefs)) return ignored;
  const keys = Object.keys(prefs);
  for (let i = 0; i < keys.length; i++) {
    const k = keys[i];
    const v = prefs[k];
    if (PREF_KEYS.indexOf(k) < 0) {
      ignored.push(k);
      continue;
    }
    if (v === null || v === undefined) continue;
    if (typeof v !== "string") {
      ignored.push(k);
      continue;
    }
    try {
      localStorage.setItem(k, v);
    } catch (e) {
      /* 写回失败(隐私模式): 单键放弃, 不打断整份导入 */
    }
  }
  return ignored;
}
/* Content-Disposition 里取文件名(导出落盘沿用服务端戳): filename* 优先(RFC 6266 双段),
 * 回退 ASCII filename; 都没有回缺省名。 */
function aqbUiPrefsDlName(disposition) {
  const s = String(disposition || "");
  let m = s.match(/filename\*=(?:UTF-8''|utf-8'')?([^;]+)/i);
  if (m) {
    try {
      return decodeURIComponent(m[1].replace(/^"|"$/g, "").trim()) || null;
    } catch (e) {
      /* 编码异常回退 ASCII 段 */
    }
  }
  m = s.match(/filename="?([^";]+)"?/i);
  return m ? m[1].trim() : null;
}
/* 动态文件选择器(D6 闸1): promise 收口 change/cancel 两终态; cancel 事件 Chromium 113+
 * 支持, 老内核靠 focusout 兜底(选完/取消后焦点必然离开 input)。input 挂 body 上用完即删,
 * e2e 侧按 .aq-bk-file 定位 setInputFiles(隐藏元素可 setInputFiles, 不要求可见)。 */
function aqbUiPrefsPickFile() {
  return new Promise((resolve) => {
    const inp = document.createElement("input");
    inp.type = "file";
    inp.accept = "application/json,.json";
    inp.className = "aq-bk-file";
    inp.style.display = "none";
    document.body.appendChild(inp);
    let settled = false;
    const settle = (val) => {
      if (settled) return;
      settled = true;
      inp.remove();
      resolve(val || null);
    };
    inp.addEventListener("change", () => settle(inp.files && inp.files[0] ? inp.files[0] : null));
    inp.addEventListener("cancel", () => settle(null));
    inp.addEventListener("focusout", () => {
      setTimeout(() => {
        /* !inp.files 恒为 FileList 对象(truthy), 必须查 length —— 老内核无 cancel 事件时
         * 用户取消选择要靠这里兜底 settle(null), 否则 Promise 悬挂 + input 泄漏 */
        if (!settled && (!inp.files || !inp.files.length)) settle(null);
      }, 250);
    });
    inp.click();
  });
}
/* FileReader 读文本(先例 add_torrent.js:711 的 promise 包法) */
function aqbUiPrefsReadText(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result || ""));
    reader.onerror = () => reject(new Error("无法读取文件: " + (file && file.name ? file.name : "未知文件")));
    reader.readAsText(file);
  });
}

window.AQB_UI_PREFS = {
  methods: {
    /* ---------------------------------------------------------- 导出(D12) */
    /* cfgDirty 时提示不阻断(导出恒读磁盘, 未保存改动不含在内); GET -> 前端并入 ui_prefs
     * 段 -> Blob <a download> 落盘(先例 commands_send.js:_exportDownload; 401 走 _logout
     * 收口后静默, 与 api() 的 401 契约同形)。 */
    async cfgBackupExport() {
      if (this.cfgDirty) this.toast("导出的是已保存配置, 未保存改动不含在内", "warn");
      try {
        const resp = await aqbFetch("/api/backup/export", { headers: aqbAuthHeaders(this.token) });
        if (resp.status === 401) {
          this._logout("密钥无效或已更换");
          const err = new Error("unauthorized");
          err.auth = true;
          throw err;
        }
        if (!resp.ok) {
          const detail = await resp.json().catch(() => ({}));
          throw new Error((detail && detail.detail) || "HTTP " + resp.status);
        }
        const bundle = await resp.json();
        /* ui_prefs 并进服务端 bundle(D3: 服务端响应不含该段, 前端补齐再落盘);
         * created_at 服务端已带, 老后端缺戳时以本机时间兜底 */
        bundle.ui_prefs = aqbUiPrefsCollect();
        if (!bundle.created_at) bundle.created_at = new Date().toISOString();
        const name = aqbUiPrefsDlName(resp.headers.get("Content-Disposition")) || "auto-qb-backup.json";
        const url = URL.createObjectURL(
          new Blob([JSON.stringify(bundle, null, 2)], { type: "application/json" })
        );
        const a = document.createElement("a");
        a.href = url;
        a.download = name;
        document.body.appendChild(a);
        a.click();
        a.remove();
        setTimeout(() => URL.revokeObjectURL(url), 4000);
        this.toast("已导出: 配置备份已保存(" + name + ")", "ok", 6000);
      } catch (e) {
        if (!e || !e.auth) this.toast("导出失败: " + ((e && e.message) || e), "error");
      }
    },
    /* ---------------------------------------------------------- 导入(D6 三闸) */
    /* 闸1 选文件 + shape 检查 -> 脏态闸(D12) -> 闸2 confirm 勾选+摘要 -> POST(只带勾选的
     * 服务端三段)-> ui_prefs 本地写回(**POST 成功之后**才 apply: 失败/取消路径本机零改动,
     * 与失败 dialog「一字未改」文案保真) -> 闸3 结果 dialog -> reload。 */
    async cfgBackupImport() {
      /* ---- 闸1: 选文件 + JSON shape 检查(format 字段不符直接报错) ---- */
      const file = await aqbUiPrefsPickFile();
      if (!file) return;
      let bundle = null;
      try {
        const text = await aqbUiPrefsReadText(file);
        bundle = JSON.parse(text);
      } catch (e) {
        this.toast("无法读取备份文件: " + ((e && e.message) || e), "error");
        return;
      }
      if (!bundle || typeof bundle !== "object" || Array.isArray(bundle) || bundle.format !== AQB_UP_BUNDLE_FORMAT) {
        this.toast("不是配置备份: format 字段不符 - " + ((file && file.name) || ""), "error");
        return;
      }
      /* ---- 脏态闸(D12): cfgDirty 先确认「未保存改动将丢失」再继续。确认过就不走
       * cfgDiscard()(它内部还有一道「放弃未保存的修改」confirm, 双重弹窗)—— 直接
       * cfgLoad() 重拉磁盘树, 与 cfgDiscard 确认后的落地动作相同。 */
      if (this.cfgDirty) {
        const go = await this.confirmDialog(
          "有未保存的配置改动",
          "导入会覆盖本机已保存配置, 当前未保存的改动将丢失。",
          { okText: "放弃改动并继续", danger: true }
        );
        if (!go) return;
        await this.cfgLoad();
      }
      /* ---- 闸2: confirm 分 section 勾选(bundle 含该段才可勾, 缺段灰显)+ 摘要 + 提示行 ---- */
      const avail = {
        config_yaml: typeof bundle.config_yaml === "string" && !!bundle.config_yaml.trim(),
        webui_keys: !!bundle.webui_keys && typeof bundle.webui_keys === "object" && !Array.isArray(bundle.webui_keys),
        gtm: !!bundle.gtm && typeof bundle.gtm === "object" && !Array.isArray(bundle.gtm),
      };
      const checks = AQB_UP_SECTIONS.map((s) => ({
        key: s.key,
        label: s.label + "(整份替换, 覆盖本机现有值)",
        checked: avail[s.key],
        disabled: !avail[s.key],
        title: avail[s.key] ? "" : "bundle 不含该段(导出时该面缺失), 无法导入",
      }));
      /* config schema 版本: config_yaml 文本里 config.schema_version 行的廉价正则提取
       * (前端不背 YAML 解析器; 提不出按「未标注」展示, 后端闸照常兜底) */
      const sm = typeof bundle.config_yaml === "string"
        ? bundle.config_yaml.match(/^\s+schema_version:\s*(\d+)\s*$/m)
        : null;
      const gtm = bundle.gtm && typeof bundle.gtm === "object" && !Array.isArray(bundle.gtm) ? bundle.gtm : null;
      const verdict = [
        { icon: "#i-info", label: "bundle 版本", value: bundle.bundle_version == null ? "未标注" : "v" + bundle.bundle_version },
        { icon: "#i-info", label: "创建时间", value: bundle.created_at || "未标注" },
        { icon: "#i-info", label: "来源程序", value: bundle.app_version || "未标注" },
        { icon: "#i-info", label: "config schema", value: sm ? "v" + sm[1] : "未标注" },
        { icon: "#i-info", label: "gtm 工具", value: gtm ? (gtm.tool_version || "未标注") : "离线导出(无 gtm 段)" },
        { icon: "#i-warn", label: "注意", wide: true, value: AQB_UP_PATH_HINT },
      ];
      const choice = await this._openModal({
        title: "导入配置备份",
        body: "勾选要应用的段; 浏览器偏好(ui_prefs)不经服务端, 确认后直接在本机写回。",
        verdict: verdict,
        checks: checks,
        wide: true,
        okText: "导入",
        cancelText: "取消",
      });
      if (!choice || !choice.checks) return;
      const sections = {};
      for (let i = 0; i < AQB_UP_SECTIONS.length; i++) {
        const s = AQB_UP_SECTIONS[i];
        if (choice.checks[s.key]) sections[s.key] = bundle[s.key];
      }
      if (!Object.keys(sections).length) {
        this.toast("未勾选任何要应用的段, 导入取消", "warn");
        return;
      }
      /* ---- 闸3: POST -> ui_prefs 本地写回(D3, 只在 POST 成功后; 评审拍板二选一取移位 ——
       * 失败路径连本机偏好都一字未动, 「配置一字未改」文案对服务端与本机双侧保真) ---- */
      try {
        const res = await this.api("/api/backup/import", {
          method: "POST",
          body: JSON.stringify({ bundle_version: bundle.bundle_version, sections: sections }),
        });
        const ignored = aqbUiPrefsApply(bundle.ui_prefs);
        if (ignored.length) {
          this.toast("偏好部分未导入: 未登记或格式不符键已忽略 - " + ignored.join(", "), "warn", 8000);
        }
        const rows = [];
        const applied = (res && res.applied) || [];
        for (let i = 0; i < applied.length; i++) {
          const s = AQB_UP_SECTIONS.filter(function (x) { return x.key === applied[i]; })[0];
          rows.push({ icon: "#i-check", label: s ? s.label : applied[i], value: "已应用" });
        }
        const skipped = (res && res.skipped) || [];
        for (let i = 0; i < skipped.length; i++) {
          const sk = skipped[i] || {};
          const s = AQB_UP_SECTIONS.filter(function (x) { return x.key === sk.section; })[0];
          rows.push({ icon: "#i-warn", label: s ? s.label : (sk.section || "?"), value: sk.reason || "", wide: true });
        }
        const warnings = (res && res.warnings) || [];
        for (let i = 0; i < warnings.length; i++) {
          rows.push({ icon: "#i-warn", label: "提示", value: warnings[i], wide: true });
        }
        await this._openModal({
          title: "导入完成",
          body: rows.length
            ? "应用结果如下, 确认后刷新页面使全部设置生效。"
            : "没有可应用的段, 确认后刷新页面。",
          verdict: rows,
          okText: "刷新页面",
        });
        location.reload();
      } catch (e) {
        if (e && e.auth) return;
        /* 422 = 聚合多行文本, 整段展示(逐行明细行; 500/400 同收口) */
        const lines = String((e && e.message) || e).split("\n").filter(function (s) { return s.trim(); });
        const rows = lines.map(function (line, i) {
          return { icon: "#i-warn", label: i === 0 ? "原因" : "", value: line, wide: true };
        });
        await this._openModal({
          title: "导入失败",
          body: "配置一字未改(整体拒绝, 不半应用)。",
          verdict: rows,
          danger: true,
          okText: "知道了",
        });
      }
    },
  },
};
