/* auto-qb WEB UI · 跨视图选择(单击/多选/Shift 区间/批量目标聚合) + 键鼠衔接(点击落光标)
 *
 * app.js 按域拆分出的片段(2026-09-20)。约定与 config_editor.js / config_rules.js 同一范式:
 * 挂到 window.AQB_SELECTION, 由 app.js 末尾 app.mixin(window.AQB_SELECTION) 注入同一个 Vue 实例 ——
 * 方法体里的 this 仍是那个组件实例, 跨模块互调与拆分前完全等价。
 *
 * !键鼠衔接(报告 26-09-30-1806 方案 B): 五个点击入口(onGroupClick / onMemberClick /
 *   onTorrentClick / onShowClick / onShowEpClick)一律按所在行回写 kbCursor —— 落光标 ≠ 选中
 *   (focus 语义, 与 2026-09-17「普通点击不选中」口径不冲突), 键盘 ↑↓ / 动作键从刚点击的行出发;
 *   Ctrl/Shift+点击在原有选中语义之外同样落光标。点击行必在视口内, 不触发滚动跟随。
 *
 * !起点统一(计划 26-10-02-0608 方案 B): 光标之外, 区间起点(anchor)也纳入键鼠统一模型 ——
 *   普通/Ctrl 点击与键盘 Shift 手势原点落起点(_selSetAnchor), 起点单点解析走 _selAnchor
 *   (兜底链: 显式锚点 -> 当前光标 -> 展开的组 -> 列表首行), 不再四处各写一遍 list[0]。
 *   落起点 ≠ 选中; Shift 不重置起点(扩展期间起点不动, 便于同一起点多次扩段)。
 *
 * !本文件在 HTML 里必须排在 app.js **之前**(app.js 末尾要读 window.AQB_SELECTION);
 *   用到的列模型常量(TABLE_COLUMNS / MIN_COL_PX / STATE_RANK …)仍单点定义在 app.js 顶部。
 */
window.AQB_SELECTION = {
  methods: {
    /* ---------------- 起点(anchor)解析单点(计划 26-10-02-0608 方案 B) ----------------
     * 起点 = 最近一次"显式落位"的位置: 鼠标普通点击 / Ctrl(⌘)+点击某行, 或键盘 Shift 手势的
     * 原点(按下 Shift 前光标所在行)。起点与光标(focus)是**两件事** —— 扩展期间起点不动,
     * 便于多次 Shift 从同一起点扩段(法则 2); 落起点 != 选中, 只写 selAnchor*, 不碰
     * selGroups/selMembers(与 2026-09-17「普通点击不选中」及方案 B「落光标 != 选中」一致)。
     * 兜底链: 显式锚点(有效) -> 当前光标(有效) -> [group: 展开的组] -> 列表首行。
     * 此前四处消费者各写一遍 list[0] 兜底, 起点与光标脱节(点第 5 行 Shift 选却从表头起),
     * 收成这两个方法后口径只有一处。 */
    _selAnchorField(kind) {
      return kind === "group" ? "selAnchorGroup" : kind === "member" ? "selAnchorMember" : "selAnchorUnit";
    },
    /* 光标 -> 本 kind 的起点 id(kind 不匹配 / 无光标返回 null; 是否落在本列表由调用方校验) */
    _selCursorId(kind) {
      const c = this.kbCursor;
      if (!c) return null;
      if (kind === "group") return c.kind === "group" ? c.id : null;
      if (kind === "member") return c.kind === "torrent" ? c.id : null;
      if (c.kind === "show") return "show|" + c.id;
      if (c.kind === "ep") return c.id;
      return null;
    },
    /* 起点单点解析: list 传 id 串数组(group/member)或单元数组 {id,hashes}(unit) */
    _selAnchor(kind, list) {
      const ids = (list || []).map((x) => (kind === "unit" ? x.id : x));
      const field = this._selAnchorField(kind);
      if (ids.includes(this[field])) return this[field];
      const fromCursor = this._selCursorId(kind);
      if (fromCursor !== null && ids.includes(fromCursor)) return fromCursor;
      if (kind === "group" && ids.includes(this.expandedKey)) return this.expandedKey;
      return ids.length ? ids[0] : null;
    },
    /* 落起点(单点写入口): 按 kind 写对应 selAnchor* 字段 */
    _selSetAnchor(kind, id) {
      this[this._selAnchorField(kind)] = id;
    },
    /* 当前视图的起点上下文 {kind, ids}: 键盘手势原点据此判定"当前上下文有无有效起点" */
    _selContext() {
      if (this.page !== "groups") return null;
      if (this.viewMode === "torrents") return { kind: "member", ids: this.filteredTorrents.map((m) => m.hash) };
      if (this.viewMode === "shows") return { kind: "unit", ids: this._kbShowUnits().map((u) => u.id) };
      return { kind: "group", ids: this.filteredGroups.map((g) => g.key) };
    },
    /* ---------------- 多选与批量操作(Ctrl/⌘ 选中, Shift 范围; 普通点击行为不变) ---------------- */
    isGroupSelected(g) {
      return this.selGroups.includes(g.key);
    },
    onGroupClick(g, event) {
      this.kbCursor = { kind: "group", id: g.key };  // 点击落光标(≠ 选中, 方案 B 键鼠衔接)
      // 点击落起点(≠ 选中; 写在修饰键分支之前, 与展开/收起无关 —— 决策点③); Shift 不重置起点(法则 2)
      if (!event.shiftKey) this._selSetAnchor("group", g.key);
      this.menu.visible = false;
      if (event.ctrlKey || event.metaKey) {
        this.toggleGroupSel(g);
        return;
      }
      if (event.shiftKey) {
        this.shiftGroupSel(g);
        return;
      }
      this.toggleExpand(g.key, event);  // 普通点击保持"展开明细"原行为(不清除已有选择, 清除走 Esc)
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
      // 起点解析走单点 _selAnchor: 显式锚点 -> 当前光标 -> 当前展开的组(用户要求) -> 可见列表首行
      const list = this.filteredGroups.map((x) => x.key);
      const anchor = this._selAnchor("group", list);
      const from = list.indexOf(anchor);
      const to = list.indexOf(g.key);
      if (from < 0 || to < 0) return;
      const [a, b] = from <= to ? [from, to] : [to, from];
      this.selGroups = [...new Set([...this.selGroups, ...list.slice(a, b + 1)])];
    },
    onMemberClick(m, event) {
      // 普通点击**不再选中**(用户 2026-09-17 明确: 点击种子不触发选择); 仅修饰键选择:
      // Ctrl/⌘ 切换单行, Shift 从锚点整段范围
      this.kbCursor = { kind: "torrent", id: m.hash };  // 点击落光标(≠ 选中, 方案 B 键鼠衔接): 只写 focus 语义, 不动选择集合
      // 点击落起点(普通点击原为 no-op, 现补起点); Shift 不重置起点(法则 2)
      if (!event.shiftKey) this._selSetAnchor("member", m.hash);
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
      const anchor = this._selAnchor("member", list);
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
      const x = ev.target.scrollLeft;
      head.style.transform = `translateX(${-x}px)`;
      // 首列吸左(issue 26-10-06-1717): 首格反向位移抵消容器滚动, 与行内 sticky 同形(规则在 CSS)
      head.style.setProperty("--head-pin-x", `${x}px`);
    },
    /* 单种子行点击: 修饰键语义与明细行一致(Ctrl 切换 / Shift 平铺范围); 普通点击不选中。
     * 另接详情面板跟随(计划 26-10-03-0917 §1.3 相邻预留的鼠标路径): 普通单击与键盘共用
     * _kbFollowDrawer 同一个挂点, 面板开着点哪行面板就换到哪行 —— 此前只有键盘 ↑↓ 会跟随,
     * 鼠标点了半天面板纹丝不动(割裂感与报告 26-09-30-1806 同源: 两条输入没接同一行状态)。
     * 三条边界: ① 面板关着**不打开**(开面板仍归双击 / Enter / 右键「详情」, 点一下就弹出
     * 42vh 面板压掉列表, 与「用户硬约束: 列表当前行必须看得清」冲突) —— 挂点自己首行即守卫;
     * ② Ctrl / Shift 点击是**选择手势**不是「看这一行」, 不跟随(批量圈选 N 行不该让面板逐行翻);
     * ③ 面板**收起**时分流 _drawerPeekTarget(Q3, 报告 26-10-07-0542): 只换目标(头部标题 +
     * 摘要条立即反映新种子)**不展开** —— _kbFollowDrawer 首行「收起即返回」对键盘是有意设计
     * (drawer.js 收起态跟随暂停, 防连发键拉详情), 鼠标单击复用同一守卫曾致收起态点行「点了没反应」。 */
    onTorrentClick(m, event) {
      this.kbCursor = { kind: "torrent", id: m.hash };  // 点击落光标(≠ 选中, 方案 B 键鼠衔接)
      // 点击落起点(平铺种子行); Shift 不重置起点(法则 2)
      if (!event.shiftKey) this._selSetAnchor("member", m.hash);
      this.menu.visible = false;
      if (event.ctrlKey || event.metaKey) {
        this.toggleMemberSel(m);
        return;
      }
      if (event.shiftKey) {
        this.shiftTorrentSel(m);
        return;
      }
      // 普通单击: 面板开则跟随换目标(防抖 200ms / 守卫全在挂点内); 收起态走 peek 分流(边界③)
      if (this.drawer.collapsed) this._drawerPeekTarget(m.hash);
      else this._kbFollowDrawer();
    },
    shiftTorrentSel(m) {
      this.selGroups = [];  // FX-11: 同 toggleMemberSel
      this.selAnchorGroup = null;
      // 平铺列表内的连续范围选择(锚点不更新, 可从同一起点多次扩展); 起点走单点解析
      const list = this.filteredTorrents.map((x) => x.hash);
      const anchor = this._selAnchor("member", list);
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
      // 起点单点解析(计划 26-10-02-0608 W4): 起点缺失时以光标单元 / 首单元起算, 形成"起点->目标"
      // 区间, 不再退化为单单元切换(修 M7/M8 首拍只切换目标单元); 仅当目标也解析不出单元时才兜底切换
      const anchorIdx = units.findIndex((u) => u.id === this._selAnchor("unit", units));
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
      this.kbCursor = { kind: "show", id: s.key };  // 点击落光标(≠ 选中, 方案 B 键鼠衔接)
      // 点击落起点(单元 id 与 _showUnits 同构); Shift 不重置起点(法则 2)
      if (!event.shiftKey) this._selSetAnchor("unit", "show|" + s.key);
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
      this.kbCursor = { kind: "ep", id };  // 点击落光标(≠ 选中, 方案 B 键鼠衔接)
      // 点击落起点(集单元 id = showEpRowId); Shift 不重置起点(法则 2)
      if (!event.shiftKey) this._selSetAnchor("unit", id);
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
    /* 多选总数(组 + 独立成员): 供右键菜单升级为批量菜单(menu.multi)与快捷键目标解析 */
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
