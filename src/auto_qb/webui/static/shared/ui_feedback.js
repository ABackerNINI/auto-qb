/* auto-qb WEB UI · 交互反馈原语(toast / 站内确认框 / 菜单定位)
 *
 * app.js 按域拆分出的片段(2026-09-20)。约定与 config_editor.js / config_rules.js 同一范式:
 * 挂到 window.AQB_FEEDBACK, 由 app.js 末尾 app.mixin(window.AQB_FEEDBACK) 注入同一个 Vue 实例 ——
 * 方法体里的 this 仍是那个组件实例, 跨模块互调与拆分前完全等价。
 *
 * ❗本文件在 HTML 里必须排在 app.js **之前**(app.js 末尾要读 window.AQB_FEEDBACK);
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
          // 多字段形态聚焦第一个输入框(fields), 单输入形态聚焦 modalInput
          const el = (this.modal.fields && this.$refs.modalFields)
            ? this.$refs.modalFields.querySelector("input")
            : this.$refs.modalInput;
          if (el) {
            el.focus();
            el.select();
          }
        });
      });
    },
    resolveModal(ok) {
      if (!this.modal.visible) return;
      const { input, value, checkbox, checked, checks, fields } = this.modal;
      const resolve = this._modalResolve;
      this._modalResolve = null;
      this.modal = this._modalInit();
      if (!resolve) return;
      const hasChecks = !!(checkbox || (checks && checks.length));
      const hasFields = !!(fields && fields.length);
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
        } else resolve(true);
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
