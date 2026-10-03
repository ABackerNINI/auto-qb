/* auto-qb WEB UI · 交互反馈原语(toast / 站内确认框 / 菜单定位)
 *
 * app.js 按域拆分出的片段(2026-09-20)。约定与 config_editor.js / config_rules.js 同一范式:
 * 挂到 window.AQB_FEEDBACK, 由 app.js 末尾 app.mixin(window.AQB_FEEDBACK) 注入同一个 Vue 实例 ——
 * 方法体里的 this 仍是那个组件实例, 跨模块互调与拆分前完全等价。
 *
 * !本文件在 HTML 里必须排在 app.js **之前**(app.js 末尾要读 window.AQB_FEEDBACK);
 *   用到的列模型常量(TABLE_COLUMNS / MIN_COL_PX / STATE_RANK …)仍单点定义在 app.js 顶部。
 */
window.AQB_FEEDBACK = {
  methods: {
    /* ---------------------------------------------------------- 站内提示条(toast) */
    toast(text, kind = "info", ms = 4000, opts = {}) {
      const id = ++this._toastSeq;
      this.toasts.push({ id, text, kind });
      // sticky = 常驻不自动消失(强制汇报"等待中"): 由 _finishToast 更新终态后退场
      if (opts.sticky) return id;
      setTimeout(() => this._dropToast(id), ms);
      return id;
    },
    /* 常驻提示条结算: 原位更新文案与样式(kind)后停留 ms 再退场 —— "等待中"->"成功/超时"的强反馈 */
    _finishToast(id, kind, text, ms = 4000) {
      this._updateToast(id, { kind, text });
      setTimeout(() => this._dropToast(id), ms);
    },
    _updateToast(id, patch) {
      const t = this.toasts.find((x) => x.id === id);
      if (t) Object.assign(t, patch);
    },
    _dropToast(id) {
      this.toasts = this.toasts.filter((t) => t.id !== id);
    },
    /* ------------------------------------------- 站内确认/输入框(替代 confirm/prompt) */
    _modalInit() {
      return {
        visible: false, title: "", body: "", okText: "", cancelText: "",
        extraText: "",  // 第三个按钮文案(三选一框, 见 confirmThreeDialog); 空 = 不渲染该钮
        danger: false, input: false, value: "", placeholder: "",
        checkbox: "", checked: false,  // 额外选项勾选框(如删除时"同时删除磁盘文件")
        checks: null,   // 多选项 [{key,label,checked}](删除确认框: 强制汇报 + 删除文件并存)
        details: null,  // 目标信息区 [{icon,label,value}](删除确认框显示待删种子信息)
        fields: null,   // 多字段输入 [{key,label,value,placeholder}](编辑类对话框: 限速/分享率/移动/重命名)
        wide: false,    // 加宽形态(删除确认框: 摘要与选项宽松可读; DLG-01 成员明细区已移除)
        icon: "",       // 标题图标覆盖(如删除用 i-trash-x); 缺省按 danger 取 warn/info
      };
    },
    confirmDialog(title, body, opts = {}) {
      // 返回 Promise<boolean>; 取消/遮罩/Esc 均结算为 false(不做任何写操作)
      return this._openModal({
        title, body, input: false,
        okText: opts.okText || "确认", cancelText: opts.cancelText || "取消", danger: !!opts.danger,
      });
    },
    /* 三选一确认框: 返回 Promise<true|"extra"|false>(留在此类分支的语义由调用方给)
     *
     * 只有"刷新守卫"那类三分支才用得上 —— 两钮对话框表达不了「先保存再走 / 直接走 / 不走」
     * (报告 26-10-02-0508 U1-b: 键盘刷新弹自绘框, 之所以值得自绘就是因为多了「保存并刷新」这一支)。
     * 与 confirmDialog 的**布尔契约分开**, 互不影响: extraText 缺省为空 = 第三个钮不渲染,
     * 既有全部两钮对话框零变化。第三个钮一律按**破坏性分支**渲染(danger-solid): 它代表
     * "放弃这批改动"这类不可逆选择, 排在「取消」与「确认」之间。
     */
    confirmThreeDialog(title, body, opts = {}) {
      return this._openModal({
        title, body, input: false,
        okText: opts.okText || "确认", extraText: opts.extraText || "", cancelText: opts.cancelText || "取消",
        danger: !!opts.danger,
      });
    },
    /* 带"额外选项勾选框"的确认框: 返回 Promise<{checked:boolean}|null>(取消 = null)
     *
     * 与 confirmDialog 的**布尔契约分开**, 互不影响 —— 删除类操作需要"一个确认动作 + 一个可选附加项"
     * (是否连带磁盘文件), 拆成两个菜单项(保留文件/含文件)反而需要用户先判断自己点的是哪个。
     */
    confirmWithOption(title, body, opts = {}) {
      return this._openModal({
        title, body, checkbox: opts.checkbox || "", checked: !!opts.checked,
        okText: opts.okText || "确认", cancelText: opts.cancelText || "取消", danger: !!opts.danger,
      });
    },
    promptDialog(title, value, opts = {}) {
      // 返回 Promise<string|null>; 取消返回 null(与原生 prompt 语义一致)
      return this._openModal({
        title, body: opts.body || "", input: true, value: value || "", placeholder: opts.placeholder || "",
        okText: opts.okText || "确定", cancelText: opts.cancelText || "取消", danger: !!opts.danger,
      });
    },
    _openModal(cfg) {
      if (this.modal.visible) this.resolveModal(false);  // 单例: 上一个悬空 Promise 先结算为取消
      return new Promise((resolve) => {
        this._modalResolve = resolve;
        this.modal = { ...this._modalInit(), ...cfg, visible: true };
        this.$nextTick(() => {
          // 多字段形态聚焦第一个输入框(fields), 单输入形态聚焦 modalInput;
          // 确认类(计划 26-09-28-0354 §08): 默认焦点在「确定」钮 —— Enter 即确认(按钮原生行为),
          // Esc 取消走 lifecycle 退栈链。删除类确认框(危险钮)同此, 与计划"默认确定 / Enter 确认"一致。
          const el = (this.modal.fields && this.$refs.modalFields)
            ? this.$refs.modalFields.querySelector("input")
            : this.$refs.modalInput;
          if (el) {
            el.focus();
            el.select();
            return;
          }
          const ok = this.$refs.modalOk;
          if (ok) ok.focus();
        });
      });
    },
    /* choice: true(确认) | false(取消/Esc/点暗幕) | "extra"(第三个钮, 见 confirmThreeDialog)。
     * 既有调用点全走 true/false 两态, "extra" 只有三选一框会传, 老契约不变。 */
    resolveModal(choice) {
      if (!this.modal.visible) return;
      const { input, value, checkbox, checked, checks, fields } = this.modal;
      const resolve = this._modalResolve;
      this._modalResolve = null;
      this.modal = this._modalInit();
      if (!resolve) return;
      const hasChecks = !!(checkbox || (checks && checks.length));
      const hasFields = !!(fields && fields.length);
      const ok = choice === true || choice === "extra";
      if (ok) {
        if (input) resolve(value);
        else if (hasFields) {
          // 多字段编辑对话框: 返回 {key: value}(字符串, 调用方自行解析数字/判空)
          const vals = {};
          for (const f of fields) vals[f.key] = String(f.value ?? "").trim();
          resolve(vals);
        } else if (hasChecks) {
          // 勾选类确认返回 {checked, checks:{key:bool}}(向后兼容单 checkbox 的 checked 字段)
          const map = {};
          for (const c of checks || []) map[c.key] = c.checked;
          resolve({ checked, checks: map });
        } else resolve(choice === "extra" ? "extra" : true);
      } else resolve(input || hasChecks || hasFields ? null : false);
    },
    /* 锚点左缘 + 弹层宽度是否超出视口(留 8px 边距); ev.currentTarget 在同步代码内有效 */
    _menuOverflowsRight(anchor, menuW) {
      if (!anchor || !anchor.getBoundingClientRect) return false;
      return anchor.getBoundingClientRect().left + menuW > window.innerWidth - 8;
    },
    /* 右键菜单定位: 视口边界吸附(菜单尺寸取常量估算, 避免先渲染再测量造成的抖动) */
    _menuPos(event, w = 214, h = 222) {
      const x = Math.min(event.clientX, Math.max(8, window.innerWidth - w - 8));
      const y = Math.min(event.clientY, Math.max(8, window.innerHeight - h - 8));
      return { x: Math.max(8, x), y: Math.max(8, y) };
    },
  },
};

/* ==========================================================================
   全局悬浮提示(.aq-tip): 原生 title 的自绘替代 —— 视觉复刻设置页发光按钮配方
 * --------------------------------------------------------------------------
 * 触发面 = 一切带 title 的元素(模板里 130+ 处 title / :title 绑定零改动全量受益)。
 * 机制: document 级委托 mouseover / focusin, 命中 [title] 即**摘除原属性(整条祖先链,
 * 嵌套带 title 的组借外层 title 还魂会叠出双 tooltip)**+ 350ms 后弹自绘浮层; 离开 /
 * 失焦即还原 title —— 还原前用 hasAttribute 探测: 悬浮期间若值已被重写则保留新值,
 * :title 绑定不受影响。悬浮期间另有周期补摘(状态栏 :title 随轮询逐轮变值, Vue patch
 * 会把 title 重写回去而 mouseover 不会再触发), 补摘捕获到的即最新值。
 * 浮层单例挂 body 级 —— 脱离列表容器的 overflow / clip-path(同 hr-pop 与 .speed-pop 的教训);
 * 样式单点在 shared/console_hub.css 的 .aq-tip 段(三套皮肤同载, 颜色走皮肤令牌)。
 * 本块是纯 DOM 行为层, 不进 Vue mixin(不占 methods 命名空间, 也无重名风险)。
 * ========================================================================== */
(function () {
  "use strict";
  const SHOW_DELAY_MS = 350; // 与原生 tooltip 的迟滞感对齐, 掠过不闪
  const REARM_MS = 250;      // 悬浮期间补摘周期(短于原生气泡起跳延迟, Vue 重写的 title 撑不到 1s)
  const GAP = 6;             // 浮层与锚点的间距
  const EDGE = 8;            // 视口边缘留白(同 _menuOverflowsRight 口径)
  let tip = null;            // 单例浮层(懒建: 登录页等无 title 场景零 DOM 成本)
  let cur = null;            // 当前悬浮的 [title] 元素(链最内层)
  let chain = [];            // 本次悬浮被摘掉 title 的整条祖先链(含 cur): 还原单点
  let timer = 0;
  let rearm = 0;             // 悬浮期间周期补摘定时器(见 enter)

  function tipEl() {
    if (!tip) {
      tip = document.createElement("div");
      tip.className = "aq-tip";
      tip.setAttribute("role", "tooltip");
      document.body.appendChild(tip);
    }
    return tip;
  }

  function strip(el) {
    el.__aqTitle = el.getAttribute("title");
    el.removeAttribute("title"); // 原属性在手上, 原生气泡就无从弹出
  }

  function restore(el) {
    if (el.__aqTitle === null || el.__aqTitle === undefined) return;
    if (!el.hasAttribute("title")) el.setAttribute("title", el.__aqTitle);
    el.__aqTitle = null;
  }

  function hide() {
    if (timer) { clearTimeout(timer); timer = 0; }
    if (rearm) { clearInterval(rearm); rearm = 0; }
    for (const el of chain) restore(el);
    chain = [];
    cur = null;
    if (tip) tip.classList.remove("on");
  }

  function show(anchor) {
    const text = anchor.__aqTitle;
    if (!text || !text.trim()) { hide(); return; }
    const t = tipEl();
    t.textContent = text;      // title 一律按纯文本渲染, 不吃 HTML 注入
    t.classList.add("on");     // 先 display 再量测(display: none 量不到尺寸)
    const r = anchor.getBoundingClientRect();
    const w = t.offsetWidth, h = t.offsetHeight;
    let x = Math.min(Math.max(EDGE, r.left + r.width / 2 - w / 2), window.innerWidth - w - EDGE);
    let y = r.top - h - GAP;   // 默认上方居中
    if (y < EDGE) y = r.bottom + GAP; // 上方放不下转下方
    if (y + h > window.innerHeight - EDGE) y = Math.max(EDGE, window.innerHeight - h - EDGE);
    t.style.left = Math.round(x) + "px";
    t.style.top = Math.round(y) + "px";
  }

  function enter(target) {
    if (target === cur) return; // 锚点内部子元素间移动: 不重置延迟
    hide();
    if (!target) return;
    cur = target;
    // 整条祖先链都要摘(不止最内层): 状态栏是嵌套带 title 的组(.sb-today > .sb-hist /
    // .sb-stats > .sb-item / .sb-speed > .sb-spd), 只摘最内层时原生气泡会借外层祖先的
    // title 还魂 —— 自绘浮层 + 原生气泡同时出现(双 tooltip)。
    for (let el = target; el; el = el.parentElement) {
      if (el.hasAttribute("title")) { strip(el); chain.push(el); }
    }
    timer = setTimeout(() => show(cur), SHOW_DELAY_MS);
    // 状态栏速度/今日流量等 :title 绑定随轮询逐轮变值, Vue patch 会在悬浮期间把 title
    // 重写回去(mouseover 不会再触发, 没人摘) —— 周期补摘, 补摘时捕获到的即最新值,
    // 还原自然还原新值; 周期短于原生气泡起跳延迟, 重写的 title 撑不到弹出。
    rearm = setInterval(() => {
      for (const el of chain) if (el.hasAttribute("title")) strip(el);
    }, REARM_MS);
  }

  document.addEventListener("mouseover", (ev) => {
    enter(ev.target instanceof Element ? ev.target.closest("[title]") : null);
  }, true);
  document.addEventListener("mouseout", (ev) => {
    // 只在真正离开当前锚点时收起; 锚点内部移动由 mouseover 判重兜住
    if (cur && (!(ev.relatedTarget instanceof Element) || !cur.contains(ev.relatedTarget))) hide();
  }, true);
  // 键盘可达性: Tab 聚焦到带 title 的控件同样出提示, 移走即收
  document.addEventListener("focusin", (ev) => {
    enter(ev.target instanceof Element ? ev.target.closest("[title]") : null);
  }, true);
  document.addEventListener("focusout", hide, true);
  // 点击(往往接着开菜单 / 弹窗)与滚动(锚点位移)时立即收起, 浮层不悬在旧位置
  document.addEventListener("mousedown", hide, true);
  window.addEventListener("scroll", hide, true);
  window.addEventListener("blur", hide);
})();
