/* auto-qb WEB UI · 交互反馈原语(toast / 站内确认框 / 菜单定位)
 *
 * app.js 按域拆分出的片段(2026-09-20)。约定与 config_editor.js / config_rules.js 同一范式:
 * 挂到 window.AQB_FEEDBACK, 由 app.js 末尾 app.mixin(window.AQB_FEEDBACK) 注入同一个 Vue 实例 ——
 * 方法体里的 this 仍是那个组件实例, 跨模块互调与拆分前完全等价。
 *
 * !本文件在 HTML 里必须排在 app.js **之前**(app.js 末尾要读 window.AQB_FEEDBACK);
 *   用到的列模型常量(TABLE_COLUMNS / MIN_COL_PX / STATE_RANK …)仍单点定义在 app.js 顶部。
 */
/* toast 停留时长策略(单点) --------------------------------------------------
 * 用户报「右下角错误信息停留太短」(2026-10-05): 此前 error / timeout 缺省只有 4000ms
 * (少数调用点自填 8000ms) —— 报错文案常带原因段, 4s 根本读不完。
 * 口径 = 按 kind 设**下限**: 调用点缺省 ms 取下限, 显式传更短的 ms 一律抬到下限
 * (传更长照旧, 不封顶)。这样全量 error / timeout 调用点(约 30 处, 散在 8 个片段文件)
 * 无需逐个改, 以后新写的调用点也不会再退回短停留。想再调长只动这一个常量。
 * sticky 常驻条不经此处(early return), info / ok 行为不变(缺省 4000)。
 */
const TOAST_MS_DEFAULT = 4000;
const TOAST_MS_FLOOR = { error: 12000, timeout: 12000, warn: 8000 };
const toastMs = (kind, ms) => {
  const floor = TOAST_MS_FLOOR[kind] || 0;
  return ms == null ? Math.max(TOAST_MS_DEFAULT, floor) : Math.max(ms, floor);
};

/* 错误历史环形缓冲(WEBUI 错误历史 S1 数据层) --------------------------------
 * 把 error / timeout 类 toast 在**发出瞬间**收进会话内环形缓冲(根组件 _errHistory,
 * 字段定义在 state.js), 供后续步骤的错误历史面板回看 —— toast 停留再长也会错过。
 * 收集时机 = emit 即收而非退场时收: auth.js 登录/重连走 this.toasts = [] 整表清空,
 * 绕过 _dropToast, 退场钩子会漏掉刚发出的条目。sticky「等待中」条 emit 时是 busy,
 * 不在 ERR_HISTORY_KINDS 里(busy 本身永不入历史), 只在 _finishToast 结算成 timeout /
 * error 终态时经 _recordErrorToast 首次入历史; emit 即收 + settle upsert 双钩子靠
 * 同 id 去重, 同一条错误只留一条。纯内存: 零 localStorage/sessionStorage、不进
 * state_file, 刷新即失(会话内回看); cap 50 环形, 超限挤掉最旧。
 */
const ERR_HISTORY_CAP = 50;
const ERR_HISTORY_KINDS = { error: 1, timeout: 1 };

window.AQB_FEEDBACK = {
  methods: {
    /* ---------------------------------------------------------- 站内提示条(toast) */
    /* 停留时长见文件头 TOAST_MS_FLOOR(ms 缺省 = 按 kind 取下限) */
    toast(text, kind = "info", ms = null, opts = {}) {
      const id = ++this._toastSeq;
      this.toasts.push({ id, text, kind });
      // 错误历史: emit 即收(上方注释; auth 整表清空绕过退场钩子, 所以不能等退场)
      if (ERR_HISTORY_KINDS[kind]) this._recordErrorToast(id, kind, text);
      // sticky = 常驻不自动消失(强制汇报"等待中"): 由 _finishToast 更新终态后退场
      if (opts.sticky) return id;
      setTimeout(() => this._dropToast(id), toastMs(kind, ms));
      return id;
    },
    /* 常驻提示条结算: 原位更新文案与样式(kind)后停留 ms 再退场 —— "等待中"->"成功/超时"的强反馈 */
    _finishToast(id, kind, text, ms = null) {
      this._updateToast(id, { kind, text });
      // 错误历史: 终态 upsert —— busy 链在此首次入历史, emit 即收过的条目在此覆盖(kind/text 以终态为准)
      if (ERR_HISTORY_KINDS[kind]) this._recordErrorToast(id, kind, text);
      setTimeout(() => this._dropToast(id), toastMs(kind, ms));
    },
    _updateToast(id, patch) {
      const t = this.toasts.find((x) => x.id === id);
      if (t) Object.assign(t, patch);
    },
    _dropToast(id) {
      this.toasts = this.toasts.filter((t) => t.id !== id);
    },
    /* --------------------------------------------- 错误历史(WEBUI 错误历史 S1 数据层) */
    /* 收集/更新单点: upsert by id —— emit 后又 settle 的条目同 id 覆盖(kind/text 以终态为准),
     * 不产生重复; 新条目 unshift(新在上), 超过 ERR_HISTORY_CAP 挤掉最旧(环形语义)。
     * 面板关闭期(errPanelOpen 为 false)计未读徽标 —— 后续面板 UI 直接绑 _errUnread。 */
    _recordErrorToast(id, kind, text) {
      const hit = this._errHistory.find((e) => e.id === id);
      if (hit) {
        hit.kind = kind;
        hit.text = text;
      } else {
        this._errHistory.unshift({ id, seq: ++this._errSeq, ts: Date.now(), kind, text, source: "toast" });
        if (this._errHistory.length > ERR_HISTORY_CAP) this._errHistory.pop();
      }
      if (!this.errPanelOpen) this._errUnread++;
    },
    /* 清空历史(面板「清空」动作入口): 历史/未读全归零; seq 不清 —— 保持单调,
     * 展示排序兜底不因清空而出现并列回退(后端条目用后端环的 seq, 同理不清)。 */
    _clearErrorHistory() {
      this._errHistory = [];
      this._errUnread = 0;
    },
    /* 模板别名: `_` 前缀方法对模板代理不可见(issue 26-10-03-1412), 面板「清空」经此中转。 */
    clearErrorHistory() {
      this._clearErrorHistory();
    },
    /* 时间展示口径单点(S5, 模板直接调用故为非下划线方法 —— 模板坑: 下划线方法模板调不到):
     * toast 条目 ts = Date.now()(毫秒数), backend 条目 ts = lifecycle 合并时已格式化好的
     * "HH:MM:SS" 字符串; 两种来源统一回 HH:MM:SS。 */
    fmtErrTs(ts) {
      if (typeof ts === "string") return ts;
      const d = new Date(ts);
      const p = (n) => String(n).padStart(2, "0");
      return `${p(d.getHours())}:${p(d.getMinutes())}:${p(d.getSeconds())}`;
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
        okDisabled: false, // 确认钮禁用(popovers.html :disabled 绑定; 跳检预检对话框 S4: 进框 true,
                           // 预检回执后按三分流解锁 —— 既有对话框缺省 false 零变化)
        busy: false,       // 「正在检查前置条件…」行(跳检预检对话框 S4: 预检在途, 回执后撤下)
        verdict: null,     // 三分流渲染区(跳检预检对话框 S4: 行式明细 [{icon,label,value,wide}],
                           // 复用 modal-details 范式; null = 不渲染)
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
        // 模态身份戳(issue 26-10-06-0028 F1-01 单点): 每开一框自增一次 mid, 随框存进
        // this.modal —— 「单例 modal + 异步落框」形态的落袋守卫统一走 _modalIsCurrent,
        // 防迟到异步回执把上一框的结果写进无关弹窗
        this.modal = { ...this._modalInit(), ...cfg, visible: true, mid: (this._modalSeq = (this._modalSeq || 0) + 1) };
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
    /* 异步落框守卫单点(issue 26-10-06-0028 F1-01): 「单例 modal + 异步回执回写 this.modal」
     * 形态在落袋前必经 —— 比对发起时刻的框身份戳与当前可见框是否同一框(关闭/被任何新框
     * 取代即失配)。单靠业务代际 seq 兜不住「取消后 seq 不递增、用户已开无关弹窗」分支,
     * 身份戳才拦得住; 后续同形对话框一律复用本方法, 不再各写各的守卫。 */
    _modalIsCurrent(mid) {
      return !!(mid && this.modal.visible && this.modal.mid === mid);
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
    /* 右键菜单定位**初值**: 视口边界吸附(菜单尺寸取常量估算, 避免先渲染再测量的抖动)。
     * ⚠ 常量只是初值 —— 菜单真实高度随分支差一倍以上(批量菜单实测 393px, 此处按 222 估算),
     *   开层后必须再走一跳 _menuFitRefit 按**实测**尺寸重钳位, 否则锚点落在视口下部时菜单底
     *   会越过下缘, 底部菜单项真实点击不可达(issue 26-10-06-1717: Playwright 报
     *   "element is outside of the viewport" 重试到超时)。 */
    _menuPos(event, w = 214, h = 222) {
      const x = Math.min(event.clientX, Math.max(8, window.innerWidth - w - 8));
      const y = Math.min(event.clientY, Math.max(8, window.innerHeight - h - 8));
      return { x: Math.max(8, x), y: Math.max(8, y) };
    },
    /* 开层后按**实测**尺寸把菜单盒整体收进视口(issue 26-10-06-1717 的修法主体)。
     * 只认 offsetWidth/offsetHeight —— 菜单内容随分支(单种子/批量/整集/表头/文件优先级)
     * 与 flags(跳检项)变化, 常量估算拦不住。极矮视口下菜单比视口还高时(top 顶到 8 仍放不下)
     * 兜底限高 + 可滚, 保证底部项仍够得着; 限高每次开层先复位, 否则本次量到的是上次压过的高度。 */
    _menuFit(el, x, y) {
      if (!el) return { x, y };
      const EDGE = 8;                // 视口边缘留白(与 _menuOverflowsRight 同口径)
      el.style.maxHeight = "";
      el.style.overflowY = "";
      const vw = window.innerWidth, vh = window.innerHeight;
      const w = el.offsetWidth, h = el.offsetHeight;
      const nx = Math.max(EDGE, Math.min(x, Math.max(EDGE, vw - w - EDGE)));
      let ny = Math.max(EDGE, Math.min(y, Math.max(EDGE, vh - h - EDGE)));
      if (h > vh - EDGE * 2) {
        /* 菜单高过视口: 顶到上缘并限高可滚(宁可滚动也要让底部项可达)。注: 此分支下
         * .ctx-sub 次级面板会随本盒一起被裁 —— 但菜单已占满视口, 子面板本也无处可展。 */
        el.style.maxHeight = (vh - EDGE * 2) + "px";
        el.style.overflowY = "auto";
        ny = EDGE;
      }
      return { x: nx, y: ny };
    },
    /* 开层 watcher 的单点出口(state.js 的 menu/headMenu/filePrio 三处调它)。
     * 现读 this[stateKey] 而不是闭包捕获: 量测在 $nextTick, 期间若又开了一次(换对象),
     * 这里拿到的已是新对象、新对象自己的 watcher 也已排队, 不会把旧位置写回新菜单。
     * $nextTick 回调在 Vue 补丁之后、浏览器绘制之前跑, 回写 x/y 触发的重渲染同帧完成 ——
     * 不产生"先弹错位置再跳一下"的可见抖动。 */
    _menuFitRefit(stateKey, refName) {
      const s = this[stateKey];
      if (!s || !s.visible) return;
      const p = this._menuFit(this.$refs[refName], s.x, s.y);
      s.x = p.x;
      s.y = p.y;
    },
  },
};

/* ==========================================================================
   全局悬浮提示(.aq-tip): 原生 title 的自绘替代 —— 视觉复刻设置页发光按钮配方
 * --------------------------------------------------------------------------
 * 触发面 = 一切带 title 的元素(模板里 130+ 处 title / :title 绑定零改动全量受益)。
 * 机制(原生 tooltip 断供式): title 属性在 DOM 层被**单向拦截** —— MutationObserver
 * 盯全文档, 任何时刻出现 title(模板渲染 / Vue :title 写回 / 新插入节点)即刻迁进
 * data-aq-tip 并删掉原属性, DOM 里从此不存在 title, 原生气泡无从弹出。
 * 前两轮的「hover 时摘 + 离开还原 + 悬浮期补摘」仍有缝: Vue 轮询把指针下的节点整个
 * 换掉时指针不动、mouseover 不触发, 新节点带着 title 直接还魂(用户报两 tooltip 交替),
 * 且原生气泡周期补摘存在定时器竞态。代价: title 不再还原 —— 原生悬浮语义由 .aq-tip
 * 承接; :title 绑定值变化时 Vue 仍会 setAttribute("title"), 被观察器再次截走, 数据流闭环。
 * 浮层触发 = document 级委托 mouseover / focusin 命中 [data-aq-tip], 350ms 后弹 .aq-tip;
 * 离开 / 失焦 / 点击 / 滚动 / 窗口失焦立即收起; 文案 show() 时现读最新值(轮询变值即显新值)。
 * 定位(2026-10-04 修): 上方优先 / 上方放不下转下方 / 两侧都放不下才允许溢出视口 —— **任何
 * 分支都不越过锚点**(旧版末尾无条件夹回视口内, 状态栏这类底缘锚点会被浮层压在身下)。
 * 另: 锚点在 350ms 窗口内被 Vue 整个换掉时已脱离文档(rect 全 0), 按记录的指针坐标
 * elementFromPoint 重解析当前锚点, 解析不到就收起 —— 否则浮层会落到视口左上角。
 * 浮层单例挂 body 级 —— 脱离列表容器的 overflow / clip-path(同 hr-pop 与 .speed-pop 的教训);
 * 样式单点在 shared/console_hub.css 的 .aq-tip 段(三套皮肤同载, 颜色走皮肤令牌)。
 * 本块是纯 DOM 行为层, 不进 Vue mixin(不占 methods 命名空间, 也无重名风险)。
 * ========================================================================== */
(function () {
  "use strict";
  const SHOW_DELAY_MS = 350; // 与原生 tooltip 的迟滞感对齐, 掠过不闪
  const GAP = 6;             // 浮层与锚点的间距
  const EDGE = 8;            // 视口边缘留白(同 _menuOverflowsRight 口径)
  let tip = null;            // 单例浮层(懒建: 登录页等无 title 场景零 DOM 成本)
  let cur = null;            // 当前悬浮的 [data-aq-tip] 元素(嵌套组取最内层)
  let curX = NaN, curY = NaN; // 最近一次鼠标命中的视口坐标(锚点被换掉时按它重解析, 见 show)
  let timer = 0;

  function tipEl() {
    if (!tip) {
      tip = document.createElement("div");
      tip.className = "aq-tip";
      tip.setAttribute("role", "tooltip");
      document.body.appendChild(tip);
    }
    return tip;
  }

  /* title -> data-aq-tip 单向迁移: 原属性即刻摘除, 原生气泡断供。
   * 自身 removeAttribute 也进观察器批次, 此时 getAttribute 为 null —— 幂等直返,
   * 不得误清刚写入的 data-aq-tip; 空串 title 视为清除提示, 连旧标记一并摘掉。 */
  function capture(el) {
    const v = el.getAttribute("title");
    if (v === null) return;
    el.removeAttribute("title");
    if (v) el.setAttribute("data-aq-tip", v);
    else el.removeAttribute("data-aq-tip");
  }

  /* 清场 sweep: 节点自身 + 子树里现存的 title 一次性迁走(启动清场 / 观察器新插入节点) */
  function sweep(root) {
    if (root.nodeType === 1 && root.hasAttribute("title")) capture(root);
    if (root.querySelectorAll) for (const el of root.querySelectorAll("[title]")) capture(el);
  }

  function hide() {
    if (timer) { clearTimeout(timer); timer = 0; }
    cur = null;
    if (tip) tip.classList.remove("on");
  }

  function show(anchor) {
    // 锚点在 350ms 延时窗口内被整个换掉时(Vue 轮询重渲染, 见 pitfalls/web-ui/aq-tip-nested-title-double),
    // 它已脱离文档 —— getBoundingClientRect() 返回全 0, 浮层会落到视口左上角(表现为"位置错误")。
    // 按指针位置重新解析当前真正的锚点; 解析不到就收起(宁可不弹, 也不弹到错误位置)。
    if (anchor && !anchor.isConnected) {
      const hit = Number.isFinite(curX) && document.elementFromPoint(curX, curY);
      const el = hit && hit.closest ? hit.closest("[data-aq-tip]") : null;
      if (!el) { hide(); return; }
      anchor = el;
      cur = el;
    }
    const text = anchor.getAttribute("data-aq-tip"); // show 时现读: 轮询变值即显最新文案
    if (!text || !text.trim()) { hide(); return; }
    const t = tipEl();
    t.textContent = text;      // title 一律按纯文本渲染, 不吃 HTML 注入
    t.classList.add("on");     // 先 display 再量测(display: none 量不到尺寸)
    const r = anchor.getBoundingClientRect();
    const w = t.offsetWidth, h = t.offsetHeight;
    const vw = window.innerWidth, vh = window.innerHeight;
    // 水平: 锚点居中, 夹取到视口内(留 EDGE); 浮层宽过视口时贴左(右段裁掉, 好过整块出屏)
    const x = Math.max(EDGE, Math.min(r.left + r.width / 2 - w / 2, Math.max(EDGE, vw - w - EDGE)));
    // 垂直: 首选上方(与锚点留 GAP) -> 上方放不下转下方 -> 两侧都放不下才允许溢出视口。
    // !末尾**不再无条件夹回视口内**: 状态栏锚点在视口底缘, 一旦走"转下方"分支, 旧版夹取会把
    //   浮层拉回状态栏上, 正好盖住它自己描述的元素(用户报的"挡住元素本身")。
    const above = r.top - h - GAP, below = r.bottom + GAP;
    let y;
    if (above >= EDGE) y = above;                                    // 上方放得下
    else if (below + h <= vh - EDGE) y = below;                      // 上方放不下, 下方放得下
    else y = r.top - EDGE >= vh - EDGE - r.bottom ? above : below;   // 两侧都放不下: 贴空间大的一侧
    t.style.left = Math.round(x) + "px";
    t.style.top = Math.round(y) + "px";
  }

  function enter(target, x, y) {
    if (target === cur) return; // 锚点内部子元素间移动: 不重置延迟
    hide();
    if (!target) return;
    cur = target;
    curX = x; curY = y;        // 记住指针位置: 锚点被换掉时按它重解析(见 show)
    timer = setTimeout(() => show(cur), SHOW_DELAY_MS);
  }

  document.addEventListener("mouseover", (ev) => {
    enter(ev.target instanceof Element ? ev.target.closest("[data-aq-tip]") : null, ev.clientX, ev.clientY);
  }, true);
  document.addEventListener("mouseout", (ev) => {
    // 只在真正离开当前锚点时收起; 锚点内部移动由 mouseover 判重兜住
    if (cur && (!(ev.relatedTarget instanceof Element) || !cur.contains(ev.relatedTarget))) hide();
  }, true);
  // 键盘可达性: Tab 聚焦到带提示的控件同样出提示, 移走即收(键盘路径无指针坐标, 传 NaN 不参与重解析)
  document.addEventListener("focusin", (ev) => {
    enter(ev.target instanceof Element ? ev.target.closest("[data-aq-tip]") : null, NaN, NaN);
  }, true);
  document.addEventListener("focusout", hide, true);
  // 点击(往往接着开菜单 / 弹窗)与滚动(锚点位移)时立即收起, 浮层不悬在旧位置
  document.addEventListener("mousedown", hide, true);
  window.addEventListener("scroll", hide, true);
  window.addEventListener("blur", hide);

  sweep(document);
  new MutationObserver((muts) => {
    for (const m of muts) {
      if (m.type === "attributes") capture(m.target);
      else for (const n of m.addedNodes) sweep(n);
    }
  }).observe(document, { childList: true, subtree: true, attributes: true, attributeFilter: ["title"] });
})();

/* ==========================================================================
   弹窗滚轮穿透兜底(仅老 Safari / iOS < 16 生效)
 * --------------------------------------------------------------------------
 * P1 CSS 主案(c485d492)已给 .modal-mask / .hr-full-mask 加 overscroll-behavior:
 * contain 截断滚动链, 但该属性 Safari / iOS 16 才支持 —— 本块用 CSS.supports
 * 门控: 支持则完全不注册监听(现代浏览器零开销), 不支持才挂 document 级捕获
 * wheel / touchmove, 遮罩开着时拦掉落点不在内滚区的滚动, 兜底穿透。
 * document 级 wheel 监听在部分浏览器默认 passive, 必须显式 {passive: false};
 * 每次事件现查遮罩状态, 弹窗叠加无需开/关计数, v-if 卸载自然失效。
 * ========================================================================== */
(function () {
  "use strict";
  if (window.CSS && CSS.supports && CSS.supports("overscroll-behavior", "contain")) return;
  // 放行名单: 7 类内滚区 + modal(通用壳自身, P1 加固后 overflow-y: auto 是滚动容器)
  const ALLOW = [
    "add-dialog-body", "add-pop-list", "db-list", "mgr-list", "meta-tags",
    "kb-help-body", "hr-full-modal-bd", "modal",
  ];
  const MASK_SEL = ".modal-mask, .hr-full-mask";

  // 老浏览器没有 composedPath 时回退 target 向上遍历
  function pathAllowed(e) {
    if (e.composedPath) {
      const path = e.composedPath();
      for (const el of path) {
        if (el && el.classList) {
          for (const name of ALLOW) if (el.classList.contains(name)) return true;
        }
      }
      return false;
    }
    let t = e.target;
    while (t && t.classList) {
      for (const name of ALLOW) if (t.classList.contains(name)) return true;
      t = t.parentElement;
    }
    return false;
  }

  function shouldBlock(e) {
    if (!document.querySelector(MASK_SEL)) return false;       // 遮罩没开: 不拦
    if (e.type === "wheel" && e.ctrlKey) return false;         // Ctrl+滚轮缩放手势放行
    return !pathAllowed(e);
  }

  const onScrollEvt = (e) => {
    if (shouldBlock(e)) e.preventDefault();
  };
  document.addEventListener("wheel", onScrollEvt, { capture: true, passive: false });
  document.addEventListener("touchmove", onScrollEvt, { capture: true, passive: false });
})();
