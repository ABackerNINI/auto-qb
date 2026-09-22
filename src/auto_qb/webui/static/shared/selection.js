/* auto-qb WEB UI · 跨视图选择(单击/多选/Shift 区间/批量目标聚合)
 *
 * app.js 按域拆分出的片段(2026-09-20)。约定与 config_editor.js / config_rules.js 同一范式:
 * 挂到 window.AQB_SELECTION, 由 app.js 末尾 app.mixin(window.AQB_SELECTION) 注入同一个 Vue 实例 ——
 * 方法体里的 this 仍是那个组件实例, 跨模块互调与拆分前完全等价。
 *
 * ❗本文件在 HTML 里必须排在 app.js **之前**(app.js 末尾要读 window.AQB_SELECTION);
 *   用到的列模型常量(TABLE_COLUMNS / MIN_COL_PX / STATE_RANK …)仍单点定义在 app.js 顶部。
 */
window.AQB_SELECTION = {
  methods: {
    /* ---------------- 多选与批量操作(Ctrl/⌘ 选中, Shift 范围; 普通点击行为不变) ---------------- */
    isGroupSelected(g) {
      return this.selGroups.includes(g.key);
    },
    onGroupClick(g, event) {
      this.menu.visible = false;
      if (event.ctrlKey || event.metaKey) {
        this.toggleGroupSel(g);
        return;
      }
      if (event.shiftKey) {
        this.shiftGroupSel(g);
        return;
      }
      this.toggleExpand(g.key, event);  // 普通点击保持"展开明细"原行为(不清除已有选择, 清除走浮条)
    },
    toggleGroupSel(g) {
      // FX-11: 组选择与种子选择互斥(同一时刻只一种口径, 否则批量目标混发、计数含义不明)
      this.selMembers = [];
      this.selAnchorMember = null;
      this.selGroups = this.selGroups.includes(g.key)
        ? this.selGroups.filter((k) => k !== g.key)
        : [...this.selGroups, g.key];
      this.selAnchorGroup = g.key;
    },
    shiftGroupSel(g) {
      // FX-11: Shift 扩展同样属"组选择口径" -> 清掉另一侧
      this.selMembers = [];
      this.selAnchorMember = null;
      // 从锚点到当前行整段加入选择(锚点不更新: 多次 Shift 可从同一起点扩展)
      // 锚点解析: Ctrl+点击设置的锚点 -> 当前展开的组(用户要求) -> 可见列表首行
      const list = this.filteredGroups.map((x) => x.key);
      let anchor = this.selAnchorGroup;
      if (!list.includes(anchor) && list.includes(this.expandedKey)) anchor = this.expandedKey;
      if (!list.includes(anchor)) anchor = list[0];
      const from = list.indexOf(anchor);
      const to = list.indexOf(g.key);
      if (from < 0 || to < 0) return;
      const [a, b] = from <= to ? [from, to] : [to, from];
      this.selGroups = [...new Set([...this.selGroups, ...list.slice(a, b + 1)])];
    },
    onMemberClick(m, event) {
      // 普通点击**不再选中**(用户 2026-09-17 明确: 点击种子不触发选择); 仅修饰键选择:
      // Ctrl/⌘ 切换单行, Shift 从锚点整段范围
      if (event.ctrlKey || event.metaKey) {
        this.toggleMemberSel(m);
        return;
      }
      if (event.shiftKey) this.shiftMemberSel(m);
    },
    toggleMemberSel(m) {
      // FX-11: 选种子 -> 清空辅种组选择(两个口径不共存)
      this.selGroups = [];
      this.selAnchorGroup = null;
      this.selMembers = this.selMembers.includes(m.hash)
        ? this.selMembers.filter((h) => h !== m.hash)
        : [...this.selMembers, m.hash];
      this.selAnchorMember = m.hash;
    },
    shiftMemberSel(m) {
      this.selGroups = [];  // FX-11: 同 toggleMemberSel
      this.selAnchorGroup = null;
      // 当前展开明细的成员内连续选择(跨组范围由分组表的多选承担)
      const g = this.filteredGroups.find((x) => x.key === this.expandedKey);
      if (!g) return;
      const list = g.members.map((x) => x.hash);
      const anchor = list.includes(this.selAnchorMember) ? this.selAnchorMember : list[0];
      const from = list.indexOf(anchor);
      const to = list.indexOf(m.hash);
      if (from < 0 || to < 0) return;
      const [a, b] = from <= to ? [from, to] : [to, from];
      this.selMembers = [...new Set([...this.selMembers, ...list.slice(a, b + 1)])];
    },
    /* 单种子表横向滚动 -> 表头位移同步(与分组表同款 transform 桥接, 避免双向 scroll 回环) */
    syncTorrentHeadScroll(ev) {
      const head = this.$refs.torrentHead;
      if (!head) return;
      head.style.transform = `translateX(${-ev.target.scrollLeft}px)`;
    },
    /* 单种子行点击: 修饰键语义与明细行一致(Ctrl 切换 / Shift 平铺范围); 普通点击不选中 */
    onTorrentClick(m, event) {
      this.menu.visible = false;
      if (event.ctrlKey || event.metaKey) {
        this.toggleMemberSel(m);
        return;
      }
      if (event.shiftKey) this.shiftTorrentSel(m);
    },
    shiftTorrentSel(m) {
      this.selGroups = [];  // FX-11: 同 toggleMemberSel
      this.selAnchorGroup = null;
      // 平铺列表内的连续范围选择(锚点不更新, 可从同一起点多次扩展)
      const list = this.filteredTorrents.map((x) => x.hash);
      const anchor = list.includes(this.selAnchorMember) ? this.selAnchorMember : list[0];
      const from = list.indexOf(anchor);
      const to = list.indexOf(m.hash);
      if (from < 0 || to < 0) return;
      const [a, b] = from <= to ? [from, to] : [to, from];
      this.selMembers = [...new Set([...this.selMembers, ...list.slice(a, b + 1)])];
    },
    clearSelection() {
      this.selGroups = [];
      this.selMembers = [];
      this.selAnchorGroup = null;
      this.selAnchorMember = null;
      this.selAnchorUnit = null;
    },
    /* ---------------- FX-12: 追剧页选中态与修饰键选择 ----------------
     * 剧行/集行保留"点击 = 展开"的原行为; **修饰键才选中**(与表格一致):
     * Ctrl/⌘+点击 = 切换该剧/该集全部成员; Shift+点击 = 从锚点单元整段选择。
     * "全部成员被选" = selected, "命中但非全选" = partial(indeterminate 语义)。
     */
    _selState(hashes) {
      const list = hashes || [];
      if (!list.length) return { selected: false, partial: false };
      const set = this.selHashSet;
      let hit = 0;
      for (const h of list) if (set.has(h)) hit += 1;
      return { selected: hit === list.length, partial: hit > 0 && hit < list.length };
    },
    isMemberSelected(m) {
      return this.selHashSet.has(m.hash);
    },
    /* 组行选中态: 组本身被选 -> selected; 否则派生集合命中其**部分**成员 -> partial。
     * (典型场景: 在种子页选了某辅种组的几个种子, 切回辅种页该组应显示"半选"而非"没选") */
    groupSelState(g) {
      if (this.isGroupSelected(g)) return { selected: true, partial: false };
      const st = this._selState((g.members || []).map((m) => m.hash));
      return { selected: false, partial: st.partial };
    },
    _showHashes(s) {
      const out = [];
      for (const sn of s.seasons || []) {
        for (const e of sn.episodes || []) {
          out.push(...this.memberHashesOf(e.members));
        }
      }
      return [...new Set(out)];
    },
    _showUnits() {
      return this.decoratedShows.map((s) => ({ id: "show|" + s.key, hashes: this._showHashes(s) }));
    },
    _epUnits(s) {
      const out = [];
      for (const sn of s.seasons || []) {
        for (const e of sn.episodes || []) {
          out.push({ id: this.showEpRowId(s.key, sn.season, e.epKeyStr), hashes: this.memberHashesOf(e.members) });
        }
      }
      return out;
    },
    showSelState(s) {
      const u = this._showUnits().find((x) => x.id === "show|" + s.key);
      return this._selState(u ? u.hashes : []);
    },
    epSelState(e) {
      return this._selState(this.memberHashesOf(e.members));
    },
    /* 整单元切换: 全选中则整段取消, 否则整段加入(并清掉辅种组口径) */
    _toggleUnit(unit) {
      if (!unit || !unit.hashes.length) return;
      this.selGroups = [];
      this.selAnchorGroup = null;
      const all = unit.hashes;
      const cur = this.selMembers;
      const allIn = all.every((h) => cur.includes(h));
      this.selMembers = allIn ? cur.filter((h) => !all.includes(h)) : [...new Set([...cur, ...all])];
      this.selAnchorUnit = unit.id;
    },
    _extendUnit(unit, list) {
      if (!unit) return;
      const units = list || [];
      const anchorIdx = units.findIndex((u) => u.id === this.selAnchorUnit);
      const curIdx = units.findIndex((u) => u.id === unit.id);
      if (anchorIdx < 0 || curIdx < 0) {
        this._toggleUnit(unit);
        return;
      }
      this.selGroups = [];
      this.selAnchorGroup = null;
      const [a, b] = anchorIdx <= curIdx ? [anchorIdx, curIdx] : [curIdx, anchorIdx];
      const add = [];
      for (const u of units.slice(a, b + 1)) add.push(...u.hashes);
      this.selMembers = [...new Set([...this.selMembers, ...add])];
    },
    onShowClick(s, event) {
      if (event.ctrlKey || event.metaKey) {
        this._toggleUnit(this._showUnits().find((u) => u.id === "show|" + s.key));
        return;
      }
      if (event.shiftKey) {
        this._extendUnit(this._showUnits().find((u) => u.id === "show|" + s.key), this._showUnits());
        return;
      }
      this.toggleShow(s.key);
    },
    onShowEpClick(s, sn, e, event) {
      const id = this.showEpRowId(s.key, sn.season, e.epKeyStr);
      const units = this._epUnits(s);
      if (event.ctrlKey || event.metaKey) {
        this._toggleUnit(units.find((u) => u.id === id));
        return;
      }
      if (event.shiftKey) {
        this._extendUnit(units.find((u) => u.id === id), units);
        return;
      }
      this.toggleShowEp(s.key, sn.season, e.epKeyStr);
    },
    _findGroup(key) {
      // **必须先查 decoratedGroups**(groups 的前端派生超集, 同 key): 原始组字典没有 save_path
      // 等派生字段 —— 曾致删除确认框的保存路径恒为"—"(R03)。filteredGroups 兼容虚拟行(u-<hash>)
      return this.decoratedGroups.find((g) => g.key === key) || this.filteredGroups.find((g) => g.key === key) || null;
    },
  },
  computed: {
    /* 多选总数(组 + 独立成员), 供批量浮条显隐 */
    selectedCount() {
      return this.selGroups.length + this.selMembers.length;
    },
    /* FX-12: 选择权威 -> 派生集合。**唯一权威**仍是 selGroups(组 key) 与 selMembers(成员 hash)
     * (FX-11 起两者互斥, 同一时刻只有一侧非空); 所有视图的"已选"一律读这里 ——
     * 组选择展开为成员 hash 闭包, 于是"辅种页选了 1 组"在种子页/追剧页同样看得出选中。 */
    selHashSet() {
      const s = new Set(this.selMembers);
      for (const k of this.selGroups) {
        const g = this._findGroup(k);
        if (!g) continue;
        if (g.virtual) {
          if (g.members[0]) s.add(g.members[0].hash);
          continue;
        }
        for (const m of g.members || []) s.add(m.hash);
      }
      return s;
    },
  },
};
