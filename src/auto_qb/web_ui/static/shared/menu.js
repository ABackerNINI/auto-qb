/* auto-qb WEB UI · 表头菜单 / 行右键菜单 / 展开收起
 *
 * app.js 按域拆分出的片段(2026-09-20)。约定与 config_editor.js / config_rules.js 同一范式:
 * 挂到 window.AQB_MENU, 由 app.js 末尾 app.mixin(window.AQB_MENU) 注入同一个 Vue 实例 ——
 * 方法体里的 this 仍是那个组件实例, 跨模块互调与拆分前完全等价。
 *
 * ❗本文件在 HTML 里必须排在 app.js **之前**(app.js 末尾要读 window.AQB_MENU);
 *   用到的列模型常量(TABLE_COLUMNS / MIN_COL_PX / STATE_RANK …)仍单点定义在 app.js 顶部。
 */
window.AQB_MENU = {
  methods: {
    /* ---------------- 表头右键菜单(TBL-05): 按列操作 ----------------
     * 用户明确该菜单指的是"隐藏xxx"(隐藏**这一列**), 而不是笼统的列选择器;
     * 排序项直接从表头一键指定方向(与表头左键的三态循环互补)。
     */
    openHeadMenu(event, page, col) {
      event.preventDefault();
      this._markCtxSource(event);
      const pos = this._menuPos(event);
      this.headMenu = {
        visible: true,
        x: pos.x,
        y: pos.y,
        page,
        key: col.key,
        label: col.label,
        sortable: !!col.sortable,
        locked: !!col.locked,
      };
    },
    headMenuHide() {
      const m = this.headMenu;
      this.headMenu.visible = false;
      if (!m.page || !m.key) return;
      if (m.locked) {
        this.toast(`「${m.label}」是必显列(承载展开/标识), 不可隐藏`, "info");
        return;
      }
      this.toggleColumn(m.page, m.key);
      this.toast(`已隐藏「${m.label}」列(右键表头或"列"按钮可恢复)`);
    },
    headMenuSort(dir) {
      const m = this.headMenu;
      this.headMenu.visible = false;
      if (!m.sortable) return;
      // 明细表头右键的排序项也走明细表自己的键(m.page 已是列所属的表名)
      const { gk, gd } = this._sortKeys(m.page === "detail" ? "detail" : undefined);
      this[gk] = m.key;
      this[gd] = dir;
    },
    headMenuPicker() {
      const m = this.headMenu;
      this.headMenu.visible = false;
      // 在右键处就地展开完整列选择器(复用 openColMenuAt 的视口钳位)
      this.openColMenuAt({ clientX: m.x, clientY: m.y }, m.page);
    },
    /* 排序箭头已图标化(i-arrow-up/down sprite), 直接在模板按 sortKey/sortDir 渲染 */
    /* 分组表横向滚动时同步表头位移(表头已脱离 .group-table 容器做纵向 sticky,
       横向滚动靠 JS 桥接避免列头与列体错位)。用 transform 而非 scrollLeft,
       避免反向触发自身 scroll 事件形成回环; 不带 transition 跟手不滞后 */
    syncGroupHeadScroll(ev) {
      const head = this.$refs.groupHead;
      if (!head) return;
      head.style.transform = `translateX(${-ev.target.scrollLeft}px)`;
    },
    toggleExpand(key, event) {
      // 仅左键触发展开: 右键菜单不应连带展开明细(旧实现在 openMenu 里主动展开, 已移除)
      if (event && event.button !== 0) return;
      const next = this.expandedKey === key ? null : key;
      this.expandedKey = next;
      // 展开的组作为 Shift 多选默认起点(用户要求); 收起不改锚点(保留上一次起点)
      if (next) this.selAnchorGroup = next;
      this.menu.visible = false;
    },
    /* ---------------- CTX-02 触发源强调 ----------------
     * 右键菜单弹出期间把"是在操作谁"标出来(被点的行/按钮挂 .ctx-src)。
     * 用 DOM 标记而不是状态字段: 触发点分布在 组行/种子行/整集行/文件优先级单元格 以及
     * 若干按钮, 逐个加模板绑定既啰嗦又容易漏; 直接标记事件目标所在的行, 双 UI 模板零改动即生效。
     * 清理走 watch(menu.visible/filePrio.visible), 覆盖 Esc/点空白/执行动作全部关闭路径。
     */
    _markCtxSource(event) {
      this._clearCtxSource();
      const t = event && event.target;
      if (!t || typeof t.closest !== "function") return;
      const el = t.closest(".group-row, .member-row, .ep-row, .show-row, .tb-row, .ctx-anchor") || t;
      if (el && el.classList) el.classList.add("ctx-src");
    },
    _clearCtxSource() {
      document.querySelectorAll(".ctx-src").forEach((el) => el.classList.remove("ctx-src"));
    },
    openMenu(event, group) {
      event.preventDefault();
      this._markCtxSource(event);
      if (group.virtual) {
        // 虚拟行(未归组命中种子): 无真实组 key(组级路由会解析失败), 退化为该种子的单种子菜单
        this.openMemberMenu(event, group.members[0]);
        return;
      }
      // 仅弹菜单, **不展开明细**(用户需要看明细时自己左键点行)
      this.menu = { visible: true, ...this._menuPos(event), key: group.key, hash: null };
    },
    openMemberMenu(event, member) {
      event.preventDefault();
      event.stopPropagation();
      this._markCtxSource(event);
      this.menu = { visible: true, ...this._menuPos(event), key: null, hash: member.hash };
    },
    /* ---------------- FX-15 次级菜单(flyout) ----------------
     * 入口按"PT 日常高频"与"qB 通用能力"分层: 一级只放高频动作, 队列/TMM/超级做种/
     * 强制开始/分享率限制/复制族 一律进次级菜单(原则已写入 memory-bank conventions.md)。
     * hover 与点击都能展开(键盘走 Enter/Space); 子面板按父项右缘判定是否需要向左翻。
     */
    openSub(name, ev) {
      this.subMenu = name;
      this.subFlip = this._menuOverflowsRight(ev && ev.currentTarget, 200);
    },
    toggleSub(name, ev) {
      if (this.subMenu === name) {
        this.subMenu = "";
        return;
      }
      this.openSub(name, ev);
    },
    /* FX-14: 打开目标文件夹 —— 路径由**服务端**从自己的快照派生(web.py /api/open-path),
     * 前端只传 kind + 标识: 后端绝不接受客户端传路径(防"任意文件执行"), 且只允许目录/单文件种子的文件。
     * R10-10: 单文件种子返回 `select: true`(打开所在目录并**定位选中**该文件) —— 文案随之区分,
     * 否则用户会以为"只是打开了文件夹"。 */
    async openTargetPath(kind, id) {
      this.menu.visible = false;
      if (!id) return;
      try {
        const r = await this.api("/api/open-path", {
          method: "POST",
          body: JSON.stringify(kind === "group" ? { kind: "group", key: id } : { kind: "torrent", hash: id }),
        });
        const how = r.select ? "已在文件夹中选中该文件" : "已打开目标文件夹";
        this.toast(`${how}: ${r.opened}`, "ok", 3000);
      } catch (e) {
        if (!e.auth) this.toast("打开目标文件夹失败: " + e.message, "error", 8000);
      }
    },
  },
};
