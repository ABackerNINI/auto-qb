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
    /* FX-28: 时间点列(见 TIME_FMT_KEYS)的显示口径切换 —— 挂在**该列表头**右键菜单里,
     * 因为"怎么显示"是这一列的属性而非全局设置。新增可切换列: 往 TIME_FMT_KEYS +
     * TIME_FMT_DEFAULT 各加一条即可, 菜单与单元格按 key 自动生效。 */
    headMenuTimeFmt(mode) {
      const m = this.headMenu;
      this.headMenu.visible = false;
      if (!this.headTimeFmtAble()) return;
      if (this.timeFmt[m.key] === mode) return;   // 点当前值: 静默关闭(不给"已切换"的假反馈)
      this.timeFmt[m.key] = mode;                 // 整键替换属性(Vue 3 的响应式能接到)
      try {
        localStorage.setItem(TIME_FMT_STORE_KEY, JSON.stringify(this.timeFmt));
      } catch (e) {
        /* 隐私模式/配额满: 本轮仍生效, 只是刷新后回落默认 —— 偏好类写入失败不该打断操作 */
      }
      this.toast(mode === "rel"
        ? `「${m.label}」改按相对时间显示(3天前)`
        : `「${m.label}」改按绝对时间显示(09-20 21:25)`);
    },
    /* 该列是否支持口径切换(模板 v-if 用; 常量在 app.js, 模板读不到顶层 const) */
    headTimeFmtAble() {
      return TIME_FMT_KEYS.indexOf(this.headMenu.key) >= 0;
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
    /* ---------------- CTX-03 多选右键: 目标升级为整个选中集合 ----------------
     * 症状: 选中 N 行后右键, 菜单动作只作用于**被点的那一行**(用户报"多选时右键菜单应该对
     * 所有选择的种子生效, 当前仅对鼠标指向的种子生效")。
     * 语义: 被点的这一行**属于当前选中集合**时, 菜单升级为批量菜单(动作走 bulkAct / bulkDelete,
     * 与批量浮条**同一条链路**); 不属于时保持原来的单种子/整组/整集菜单。
     *
     * ❗判据是"选中集合是否**等同于**这一行自身的范围", 不是"选中数 > 1":
     *   选中 1 个辅种 + 右键它自己       -> 等同   -> 普通组菜单("暂停整组"才是对的文案)
     *   选中 1 个辅种 + 右键它的成员行   -> 不等同 -> 批量菜单(否则文案说"该种子"、实际动整组)
     * 成员/集/剧行按 **some** 判"属于": 行可能只是**半选**(由组选择派生命中的, 见 selHashSet),
     * 那时它仍应被视为"在选中集合里", 否则用户右键自己刚选中的行却拿到单行菜单。
     */
    _ctxScopeKey(scope) {
      const g = [...(scope.groupKeys || [])].sort();
      const h = [...(scope.hashes || [])].sort();
      return g.join("\u0001") + "\u0002" + h.join("\u0001");
    },
    _ctxMulti(anchorScope) {
      const sel = this._bulkTargets();   // 选中集合拆解(组 key + 成员 hash; 与批量浮条同口径)
      if (!sel.groupKeys.length && !sel.memberHashes.length) return false;
      const gk = anchorScope.groupKeys || [];
      const hs = anchorScope.hashes || [];
      const inSel = gk.length
        ? gk.every((k) => this.selGroups.includes(k))
        : hs.some((h) => this.selHashSet.has(h));
      if (!inSel) return false;
      // 集合与该行范围一致 = 只选中了它自己 -> 仍是单目标菜单(文案/项目集不该变成批量)
      return this._ctxScopeKey({ groupKeys: sel.groupKeys, hashes: sel.memberHashes }) !==
        this._ctxScopeKey({ groupKeys: gk, hashes: hs });
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
      this.menu = {
        visible: true,
        ...this._menuPos(event),
        key: group.key,
        hash: null,
        multi: this._ctxMulti({ groupKeys: [group.key] }),
      };
    },
    openMemberMenu(event, member) {
      event.preventDefault();
      event.stopPropagation();
      this._markCtxSource(event);
      this.menu = {
        visible: true,
        ...this._menuPos(event),
        key: null,
        hash: member.hash,
        multi: this._ctxMulti({ hashes: [member.hash] }),
      };
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
