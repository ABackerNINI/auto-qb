/* auto-qb WEB UI · 设置页「WebUI」卡的右键菜单定制块 —— 行为层(计划 26-10-20-0024 W4)
 *
 * 分工(与 ctx_menu.js 一致的分层):
 *   ctx_menu.js         注册表 + 默认布局 + 合并语义(纯函数), 行右键菜单运行时消费
 *   本文件              定制面板的**编辑面**: 读合并布局 -> 用户编辑(显隐/↑↓/拖拽/跨层/线) -> 写回
 *   tpl/settings-detail.html  <template v-else-if="hub.view === 'webui'"> 的表格 + tab
 *
 * 草稿不另存(重要):
 *   编辑直接落在 cfg.tree.config.web.ctx_menu 上 —— 面板显示的永远是"当前草稿"本身, 不存在
 *   「面板草稿」与「配置树」两份真值。脏标记由 cfgDirty(全树 JSON 对比 baseline)自动接管,
 *   保存走全局 cfgSave(无独立保存钮), 放弃走全局 cfgDiscard —— 与其它配置项一字不差的语义。
 *   写回一律**整对象替换**(this.cfg.tree.config.web = {...}): Vue 3 对新增键也能追踪, 但整对象
 *   替换是三处既有教训的共同结论(flags 下发 / ctx_menu 初值 / 本处) —— 不给"深层新增键没触发
 *   渲染"留任何理论缝隙。
 *
 * 布局读写口径(与运行时**同一份语义**, 不复制一份):
 *   - 读: REG.ctxMergeLayout(branch, cfg) —— 补尾 / 隐藏槽位 / 跨层认领全在 ctx_menu.js;
 *         面板显示 order ∪ hidden(隐藏项也在表里, 否则勾掉就再也勾不回来)
 *   - 写: 把面板上的两层数组 + 两层隐藏集合原样写回(不做"最小 diff 只写用户动过的那项" ——
 *         那需要第二套合并逻辑, 而两份逻辑必然漂移)
 *
 * !装载序: index.html 里必须排在 ctx_menu.js 之后、app.js 之前(app.js 末尾 app.mixin)。
 */
(function () {
  "use strict";

  /* 四支的展示名/说明(面板 tab 用; 与菜单内文案无关, 只解释"这支什么时候出现") */
  const CTX_BRANCH_LABEL = { multi: "多选批量", episode: "整集整剧", member: "单种子", group: "单组" };
  const CTX_BRANCH_HINT = {
    multi: "在列表里选中多行后右键 —— 动作作用于整个选中集合",
    episode: "追剧页选中整集或整剧后右键 —— 文案随「整集/整剧」变化",
    member: "明细表里单个种子右键 —— 最常用的一支, 也是唯一带默认次级菜单的",
    group: "分组表里某个组右键 —— 动作作用于该组全部成员",
  };

  function ctxReg() {
    return window.AQB_CTX_MENU_REG;
  }

  /* 深拷一层的布局(面板编辑用; Set 也要新的, 否则原地改会绕过写回) */
  function cloneLayer(layer) {
    return { order: layer.order.slice(), hidden: new Set(layer.hidden) };
  }

  window.AQB_CTX_CUSTOM = {
    computed: {
      /* 当前 tab 的支名(初值 member: 唯一有默认次级内容的一支, 一进来就有东西看) */
      cmBranch() {
        const b = this.ctxCust && this.ctxCust.branch;
        return ctxReg().CTX_BRANCHES.indexOf(b) >= 0 ? b : "member";
      },
      cmBranchLabel() {
        return CTX_BRANCH_LABEL[this.cmBranch] || this.cmBranch;
      },
      cmBranchHint() {
        return CTX_BRANCH_HINT[this.cmBranch] || "";
      },
      /* 两个固定区(D17)的标题/说明 —— 模板用同一张表渲染两次(一级 / 次级「更多操作」),
       * 两处各写一份 HTML 就是"改一边忘另一边"的复发形态 */
      cmSections() {
        return [
          { level: 0, title: "一级菜单", note: "右键菜单直接列出的部分" },
          { level: 1, title: "次级菜单「更多操作」", note: "悬停展开的子面板; 这里为空时, 菜单里不会出现入口" },
        ];
      },
      /* 四个 tab 的渲染数据(顺序 = 运行时判据链顺序, 与菜单优先级一致) */
      ctxBranchList() {
        return ctxReg().CTX_BRANCHES.map((b) => {
          const c = this.cmTabCount(b);
          return { key: b, label: CTX_BRANCH_LABEL[b] || b, top: c.top, sub: c.sub };
        });
      },
      /* 迁入的跳检开关(D6): 与 ctx_menu 同卡, 键仍是 config.web.skip_check_menu */
      cmSkipCheck() {
        const web = this.cmWebCfg();
        return !!web.skip_check_menu;
      },
      /* 当前支是否已被定制过(默认布局 = 无定制): tab 上打点 + 「恢复默认」按钮的 disabled */
      cmBranchCustomized() {
        return this.cmIsCustomized(this.cmBranch);
      },
    },
    methods: {
      /* ---------------------------------------------------------- 读写地基 */
      /* config.web 段(可能不存在; 定制块只碰这两个键, 不整段重建) */
      cmWebCfg() {
        const cfg = this.cfgConfig ? this.cfgConfig() : this.cfg.tree && this.cfg.tree.config;
        const web = cfg && cfg.web;
        return web && typeof web === "object" ? web : {};
      },
      /* config.web.ctx_menu 原样(未定制 = undefined) */
      cmCfg() {
        const v = this.cmWebCfg().ctx_menu;
        return v && typeof v === "object" && !Array.isArray(v) ? v : null;
      },
      cmCfgBranch(branch) {
        const c = this.cmCfg();
        const b = c && c[branch];
        return b && typeof b === "object" && !Array.isArray(b) ? b : null;
      },
      /* 一支是否偏离默认(顺序变了 / 有隐藏项 / 次级变了) —— 判据用**合并后**的布局与默认
       * 布局对齐, 而不是看配置里有几个键: 用户"改回原样"也算未定制, tab 上的点不会赖着不消 */
      cmIsCustomized(branch) {
        if (!this.cmCfgBranch(branch)) return false;
        const def = ctxReg().DEFAULT_CTX_LAYOUT[branch];
        if (!def) return false;
        const m = ctxReg().ctxMergeLayout(branch, this.cmCfg());
        const diff = (order, hidden, defOrder) => hidden.size > 0 || order.join("|") !== defOrder.join("|");
        return diff(m.order, m.hidden, def.order) || diff(m.sub.order, m.sub.hidden, def.sub.order);
      },
      /* 首页卡读数: N 支已定制 / 默认布局 */
      cmCardReadout() {
        const n = ctxReg().CTX_BRANCHES.filter((b) => this.cmIsCustomized(b)).length;
        return n ? `${n} 支菜单已定制` : "默认布局";
      },
      /* 整对象替换写回 config.web(响应式单点; 见文件头注释) */
      cmSetWeb(patch) {
        const next = Object.assign({}, this.cmWebCfg(), patch);
        this.cfg.tree.config.web = next;
      },
      /* 当前支的合并布局(与运行时同一个函数 —— 面板看到的就是菜单将渲染的) */
      cmLayout(branch) {
        return ctxReg().ctxMergeLayout(branch || this.cmBranch, this.cmCfg());
      },
      /* 布局写回: merged = {order, hidden, sub:{order, hidden}} */
      cmPersist(branch, merged) {
        const next = Object.assign({}, this.cmCfg() || {});
        next[branch] = {
          order: merged.order.slice(),
          hidden: Array.from(merged.hidden),
          sub: { order: merged.sub.order.slice(), hidden: Array.from(merged.sub.hidden) },
        };
        this.cmSetWeb({ ctx_menu: next });
      },
      /* 取一份可改的副本(两层一起) */
      cmDraft(branch) {
        const m = this.cmLayout(branch);
        return { order: m.order.slice(), hidden: new Set(m.hidden), sub: cloneLayer(m.sub) };
      },

      /* ---------------------------------------------------------- 面板渲染数据 */
      /* 表行: 隐藏项也在表里(勾掉还能勾回来), 分隔线单列一行 */
      cmRows(branch, level) {
        const m = this.cmLayout(branch);
        const layer = level === 1 ? m.sub : m;
        const rows = [];
        layer.order.forEach((token, idx) => {
          const isSep = ctxReg().ctxIsSepToken(token);
          const def = isSep ? null : ctxReg().ctxDefById(branch, token);
          const dynLabel = def && typeof def.label === "function" ? def.labelText || token : null;
          rows.push({
            id: token,
            idx,
            level,
            sep: isSep,
            userSep: isSep && token.indexOf("sep:u") === 0,
            hidden: layer.hidden.has(token),
            label: isSep ? (token.indexOf("sep:u") === 0 ? "自定义分隔线" : "分隔线") : def ? def.labelText || (typeof def.label === "string" ? def.label : dynLabel) || token : token,
            use: def && def.icon ? def.icon.use : "",
            danger: !!(def && def.danger),
            submenu: !!(def && def.kind === "submenu"),
            gate: def && def.gate ? def.gate : "",
            /* 结构项(「更多操作」父项)不可跨层 —— 它本身就是次级入口, 移进次级等于嵌套 */
            movable: !isSep && !(def && def.kind === "submenu"),
          });
        });
        return rows;
      },
      /* tab 上的角标: 该支一级可见项数 / 次级可见项数(隐藏与门控都不计, 与运行时同口径) */
      cmTabCount(branch) {
        const m = this.cmLayout(branch);
        const vc = (level, layer) => ctxReg().ctxLayerVisibleCount(branch, level, layer, this.flags);
        return { top: vc(0, m), sub: vc(1, m.sub) };
      },

      /* ---------------------------------------------------------- 显隐 */
      cmToggleHidden(branch, level, id) {
        const d = this.cmDraft(branch);
        const layer = level === 1 ? d.sub : d;
        if (layer.hidden.has(id)) layer.hidden.delete(id);
        else layer.hidden.add(id);
        this.cmPersist(branch, d);
      },

      /* ---------------------------------------------------------- ↑↓(D14: 键盘可达的那一半) */
      cmMoveStep(branch, level, id, delta) {
        const d = this.cmDraft(branch);
        const layer = level === 1 ? d.sub : d;
        const i = layer.order.indexOf(id);
        const j = i + delta;
        if (i < 0 || j < 0 || j >= layer.order.length) return;
        const t = layer.order[i];
        layer.order[i] = layer.order[j];
        layer.order[j] = t;
        this.cmPersist(branch, d);
      },

      /* ---------------------------------------------------------- 跨层(一级 ↔「更多操作」, D1) */
      cmMoveLevel(branch, level, id) {
        const d = this.cmDraft(branch);
        const src = level === 1 ? d.sub : d;
        const dst = level === 1 ? d : d.sub;
        const i = src.order.indexOf(id);
        if (i < 0) return;
        const def = ctxReg().ctxDefById(branch, id);
        if (def && def.kind === "submenu") return; // 结构项不可嵌套(与运行时渲染口径一致)
        src.order.splice(i, 1);
        src.hidden.delete(id);
        dst.hidden.delete(id); // 换层的项默认可见: 移过去就消失会像"丢了"
        dst.order.push(id);
        this.cmPersist(branch, d);
      },

      /* ---------------------------------------------------------- 分隔线(D10: 一等公民) */
      cmAddSep(branch, level) {
        const d = this.cmDraft(branch);
        const layer = level === 1 ? d.sub : d;
        const token = ctxReg().ctxNextSepToken(layer.order.concat(Array.from(layer.hidden)));
        layer.order.push(token);
        this.cmPersist(branch, d);
      },
      /* 只允许删用户线(sep:uN): 默认线是模板结构的锚点, 删了"恢复默认"才对得上 —— 用户想
       * 让默认线消失, 取消勾选(隐藏)即可, 槽位保留在配置里, 想恢复勾回来 */
      cmDelSep(branch, level, id) {
        const d = this.cmDraft(branch);
        const layer = level === 1 ? d.sub : d;
        const i = layer.order.indexOf(id);
        if (i < 0) return;
        layer.order.splice(i, 1);
        layer.hidden.delete(id);
        this.cmPersist(branch, d);
      },

      /* ---------------------------------------------------------- 恢复默认(D16: 直接写草稿, 无二次确认) */
      cmResetBranch(branch) {
        const def = ctxReg().DEFAULT_CTX_LAYOUT[branch];
        if (!def) return;
        this.cmPersist(branch, {
          order: def.order.slice(),
          hidden: new Set(),
          sub: { order: def.sub.order.slice(), hidden: new Set() },
        });
        this.toast(`「${CTX_BRANCH_LABEL[branch] || branch}」已恢复默认布局`, "ok", 3000);
      },

      /* ---------------------------------------------------------- 拖拽(D14: 鼠标直觉的那一半) */
      /* 同款交互照列选择器(columns.js colDrag): mousedown 起手 + 行上 dragover 记落点,
       * 但这里用原生 HTML5 DnD(表格行不是等宽格子, 无需自绘幽灵) */
      cmDragStart(row, ev) {
        this.ctxCust.drag = { branch: this.cmBranch, level: row.level, idx: row.idx, id: row.id };
        this.ctxCust.over = null;
        if (ev && ev.dataTransfer) {
          ev.dataTransfer.effectAllowed = "move";
          /* Firefox 必须 setData 才真正开始拖(否则 dragstart 后什么都不发生) */
          try {
            ev.dataTransfer.setData("text/plain", row.id);
          } catch { /* 某些浏览器在只读态拒写: 不影响拖拽本身 */ }
        }
      },
      cmDragOver(row, ev) {
        const d = this.ctxCust.drag;
        if (!d || d.branch !== this.cmBranch) return;
        /* 跨层: 目标行与**源**都必须可动 —— 结构项(「更多操作」父项)本身不参与跨层 */
        if (row.level !== d.level) {
          const srcDef = ctxReg().ctxDefById(d.branch, d.id);
          if (!row.movable || (srcDef && srcDef.kind === "submenu")) return;
        }
        if (ev && ev.preventDefault) ev.preventDefault(); // 允许落下(dragover 不 preventDefault = 禁投)
        this.ctxCust.over = { level: row.level, idx: row.idx };
      },
      /* 落到某一行 = 插到该行之前(同层且源在下 = 逻辑上"移到它前面") */
      cmDropAt(row) {
        const d = this.ctxCust.drag;
        this.ctxCust.drag = null;
        this.ctxCust.over = null;
        if (!d || d.branch !== this.cmBranch) return;
        const draft = this.cmDraft(d.branch);
        const src = d.level === 1 ? draft.sub : draft;
        const dst = row.level === 1 ? draft.sub : draft;
        const from = src.order.indexOf(d.id);
        if (from < 0) return;
        const def = ctxReg().ctxDefById(d.branch, d.id);
        if (def && def.kind === "submenu" && d.level !== row.level) return; // 结构项不跨层
        src.order.splice(from, 1);
        src.hidden.delete(d.id);
        dst.hidden.delete(d.id);
        let at = row.idx;
        if (d.level === row.level && from < row.idx) at = row.idx - 1;
        at = Math.max(0, Math.min(at, dst.order.length));
        dst.order.splice(at, 0, d.id);
        this.cmPersist(d.branch, draft);
      },
      cmDragEnd() {
        this.ctxCust.drag = null;
        this.ctxCust.over = null;
      },
      /* 拖到表尾空白处 = 追加到该层末尾 */
      cmDropTail(branch, level) {
        const d = this.ctxCust.drag;
        this.ctxCust.drag = null;
        this.ctxCust.over = null;
        if (!d || d.branch !== branch) return;
        const draft = this.cmDraft(branch);
        const src = d.level === 1 ? draft.sub : draft;
        const dst = level === 1 ? draft.sub : draft;
        const from = src.order.indexOf(d.id);
        if (from < 0) return;
        const def = ctxReg().ctxDefById(branch, d.id);
        if (def && def.kind === "submenu" && d.level !== level) return;
        src.order.splice(from, 1);
        src.hidden.delete(d.id);
        dst.hidden.delete(d.id);
        dst.order.push(d.id);
        this.cmPersist(branch, draft);
      },

      /* ---------------------------------------------------------- 跳检开关(D6: 与定制块同卡) */
      cmSetSkipCheck(v) {
        this.cmSetWeb({ skip_check_menu: !!v });
      },
      /* 进分区: 固定回单种子支(不记忆上次 tab —— 一次只看一支, 记忆会让人以为"卡住") */
      cmPanelEnter() {
        this.ctxCust.branch = "member";
        this.ctxCust.drag = null;
        this.ctxCust.over = null;
      },
    },
  };
})();
