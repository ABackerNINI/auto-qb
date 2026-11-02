/* columns_computed.js — R4 大文件拆分(计划 26-11-02-2342 §07)
 * 列模型 · 派生列样式/宽度/成员窗(computed 段)。
 * 只搬 computed 定义, 实现逐行未改; 本片段在全部方法片段之后加载, 保 methods 先于 computed。
 * 加载序 = 四套皮肤 index.html 清单里紧跟 columns_drag.js 之后。
 */
Object.assign(window.AQB_COLUMNS, {
  computed: {
    /* 表注册表的**有序数组视图**(计划 26-10-11-1722 P4): 列选择器按它 v-for(四段硬编码收敛为一段),
     * 每项 { id, label, columns } —— label 即列选择器的分组标题, columns 即列定义单点。
     * 注册表是模块常量(非响应式), 故本 computed 只在首帧算一次, 引用稳定(不引起重渲染抖动)。
     * !W2 取舍(计划 26-10-11-2106): 取**全集**, 抽屉三表在列选择器里各占一个分组 —— 与计划 §07
     * 的括注("不进 TABLE_PAGES 否则列选择器多出分组")**有意偏差**, 理由: 抽屉表头的右键隐藏
     * (`headMenuHide` -> `toggleColumn`)是**不可逆**操作, 没有选择器这一档就没有恢复入口
     * (只剩改 localStorage)。用户 26-10-11 拍板「以与主视图一致为准则」(D 组 Q2), 故取全集。
     * 计划 §11 变更记录已登记本偏差。 */
    tableDefs() {
      /* 变体表格体(26-10-12-0527): 带 variantTab 的表只在**对应变体被选中**时进选择器
       * (dtBridgeTbl 是 drawer_templates.js mixin 的桥反查; 经典选中时该变体表不出现 ——
       * 八个变体表恒列出会把生产选择器撑爆, 且全部隐藏列无意义)。恢复入口不变式保持:
       * 变体选中期间右键隐藏的列仍可在选择器勾回。 */
      const out = [];
      for (const id of ALL_TABLE_PAGES) {
        const def = ALL_TABLE_DEFS[id];
        if (def.variantTab && this.dtBridgeTbl(def.variantTab) !== id) continue;
        out.push({ id, label: def.label, columns: def.columns });
      }
      return out;
    },
    /* 列模板: computed 缓存(列宽/列显隐变化才变), 行渲染只取同一引用, 不再每行拼字符串 */
    groupGrid() {
      return { gridTemplateColumns: this._gridTemplate("group") };
    },
    detailGrid() {
      return { gridTemplateColumns: this._gridTemplate("detail") };
    },
    torrentGrid() {
      return { gridTemplateColumns: this._gridTemplate("torrent") };
    },
    showGrid() {
      return { gridTemplateColumns: this._gridTemplate("show") };
    },
    /* 变体表格体(计划 26-10-12-0527 U1 stub): 与主视图同一条 _gridTemplate 路径 ——
     * 列宽/列序/隐藏任一变化即换引用; U2 起每变体表一行(声明式追加, 形态同此)。
     * (2026-10-14: 经典三表的 drawerTracker/Peer/FileGrid 随经典渲染链一并退役。) */
    drawerStubV0Grid() {
      return { gridTemplateColumns: this._gridTemplate("drawerStubV0") };
    },
    /* 列对齐规则(R10-08): align 定义在列模型里, 这里按**当前可见列**生成 :nth-child 规则注入 <head>。
     *
     * 为何生成而非在模板里逐格挂类: 值单元格共 67 个 × 4 视图 × 2 套 UI, 逐格挂类必然漏改;
     * 生成则"列模型改一处, 表头与值同源"(表头同样按可见列索引渲染, 顺序天然一致)。
     *
     * 选择器用 :where() 把特异性压到 0,1,0(只剩 :nth-child 那一位), 于是:
     *   - 胜过 .g-stat/.m-stat(0,1,0, 同权重靠源顺序: 注入的 <style> 在样式表之后) -> 非默认对齐生效;
     *   - 与 .h-cell .arrow(0,2,0) 同权, 靠同一套源顺序胜出(见下方箭头 order 规则)。
     * 同时写 text-align 与 justify-content: 值单元格有的是块级文本, 有的是 flex(进度条/
     * 分享率对/芯片组), 只写 text-align 会漏掉后者。
     * 右对齐列的排序箭头取 order:-1 排到标签**左侧**(表头 .h-cell 已是 flex): 否则箭头作为标签的
     * 同行兄弟会把标题整块左顶 11px —— 用户看到的就是"点一下排序, 标题跳一下"。值格没有 .arrow,
     * 不受此规则影响。2026-10-06 起 "0 值居中"(.g-stat.zero/.m-stat.zero) 已删, 0 值格回落本规则注入
     * 的 right, 与同列表头同缘。
     * WARN: **left 也必须生成**: 数值列的值格子带 .g-stat/.m-stat(right), 若因为"left 是默认值"就跳过,
     *    左对齐的口径会被这两条通用规则盖掉(实测: 添加于列表头左、值右)。
     */
    colAlignCss() {
      const out = [];
      // 遍历全集(含抽屉三表, 计划 26-10-11-2106 W2): 对齐规则靠 [data-table] 锚命中表头与值格,
      // 抽屉表头根带 data-table="drawer*"、行容器同挂, 故与主视图同一条注入路径。
      for (const page of ALL_TABLE_PAGES) {
        const cols = this._visibleCols(page);
        for (let i = 0; i < cols.length; i++) {
          const align = cols[i].align || "left";
          const just = align === "right" ? "flex-end" : align === "center" ? "center" : "flex-start";
          out.push(`:where([data-table="${page}"]) > :nth-child(${i + 1}) { text-align: ${align}; justify-content: ${just}; }`);
          if (align === "right") out.push(`:where([data-table="${page}"]) > :nth-child(${i + 1}) .arrow { order: -1; }`);
        }
      }
      return out.join("\n");
    },
    /* ---------------- P1-2 行窗口: 只决定"渲染哪一段", 不参与任何业务语义 ----------------
     * 三个窗口共用 _rowWindow(); 未启用时 win.active=false, 切片 = 全量、上下占位 = 0,
     * 模板与不开窗时完全等价(因此关掉开关就是老行为, 回退路径零成本)。 */
    torrentWin() {
      return this._rowWindow("torrent", this.filteredTorrents, TABLE_DEFS.torrent.tableRef);
    },
    visibleTorrents() {
      const w = this.torrentWin;
      return w.active ? this.filteredTorrents.slice(w.start, w.end) : this.filteredTorrents;
    },
    torrentPadTop() {
      return this.torrentWin.padTop;
    },
    torrentPadBottom() {
      return this.torrentWin.padBottom;
    },
    /* 分组页: **有展开面板时退避** —— .detail 高度不定(含明细表头 + N 行成员), 会让后续行的
     * 位置偏离"第 i 行在 i×step"的假设(硬约束 2.); 此时回退全量渲染, 宁可慢也不能错位。 */
    groupWin() {
      const n = this.filteredGroups.length;
      // !退避判据必须是"**当前真的有面板**", 不能只看 expandedKey 非空: 展开态现在会跨视图带回
      // (切回分组页时原组可能已被删/被筛掉, 见 app.js restoreExpandState), 为一个不存在的面板退避
      // = 大库上永久退化成全量渲染, 且用户完全看不出原因(界面一切正常, 只是滚动变卡)。
      if (this.expandedKey && this.filteredGroups.some((g) => g.key === this.expandedKey)) {
        return { active: false, start: 0, end: n, padTop: 0, padBottom: 0 };
      }
      return this._rowWindow("group", this.filteredGroups, TABLE_DEFS.group.tableRef);
    },
    visibleGroups() {
      const w = this.groupWin;
      return w.active ? this.filteredGroups.slice(w.start, w.end) : this.filteredGroups;
    },
    groupPadTop() {
      return this.groupWin.padTop;
    },
    groupPadBottom() {
      return this.groupWin.padBottom;
    },
    /* 可见列(列选择器只改 colHidden; 顺序取 colOrder(表头拖动重排 TBL-05), 无自定义序时按列定义序) —— 表头/行/grid 模板共用 */
    visibleGroupCols() {
      return this._visibleCols("group");
    },
    visibleDetailCols() {
      return this._visibleCols("detail");
    },
    visibleTorrentCols() {
      return this._visibleCols("torrent");
    },
    visibleShowCols() {
      return this._visibleCols("show");
    },
    /* 变体表格体(26-10-12-0527 U1 stub): 表壳 :cols 与渲染器 :cols 同引用(列序天然一致)
     * (2026-10-14: 经典三表的 visibleDrawerTracker/Peer/FileCols 随经典渲染链一并退役。) */
    visibleDrawerStubV0Cols() {
      return this._visibleCols("drawerStubV0");
    },
    /* 变体表格体(U2): 07/08/09 三表, 同一条 _gridTemplate / _visibleCols 路径(omitEmpty
     * 渐进列在 _visibleCols 尾部单点生效 —— 0621 注: cols computed 主要供经典链同名消费
     * 惯例与守阵对齐面, 桥模板实际取 visibleColsOf)。 */
    drawerPeerV07Grid() {
      return { gridTemplateColumns: this._gridTemplate("drawerPeerV07") };
    },
    drawerPeerV08Grid() {
      return { gridTemplateColumns: this._gridTemplate("drawerPeerV08") };
    },
    drawerPeerV09Grid() {
      return { gridTemplateColumns: this._gridTemplate("drawerPeerV09") };
    },
    visibleDrawerPeerV07Cols() {
      return this._visibleCols("drawerPeerV07");
    },
    visibleDrawerPeerV08Cols() {
      return this._visibleCols("drawerPeerV08");
    },
    visibleDrawerPeerV09Cols() {
      return this._visibleCols("drawerPeerV09");
    },
    /* 变体表格体(U3): Tracker 04/05/06 三表, 同一条 _gridTemplate / _visibleCols 路径 */
    drawerTrackerV04Grid() {
      return { gridTemplateColumns: this._gridTemplate("drawerTrackerV04") };
    },
    drawerTrackerV05Grid() {
      return { gridTemplateColumns: this._gridTemplate("drawerTrackerV05") };
    },
    drawerTrackerV06Grid() {
      return { gridTemplateColumns: this._gridTemplate("drawerTrackerV06") };
    },
    visibleDrawerTrackerV04Cols() {
      return this._visibleCols("drawerTrackerV04");
    },
    visibleDrawerTrackerV05Cols() {
      return this._visibleCols("drawerTrackerV05");
    },
    visibleDrawerTrackerV06Cols() {
      return this._visibleCols("drawerTrackerV06");
    },
    /* U4 内容树两变体(10/11): 同一条 _gridTemplate / _visibleCols 路径(11 可用性列
     * omitEmpty 渐进在 _colsOmitEmpty 单点生效 —— 原 hasav/noav 双 grid 手搓退役)。 */
    drawerContentV10Grid() {
      return { gridTemplateColumns: this._gridTemplate("drawerContentV10") };
    },
    drawerContentV11Grid() {
      return { gridTemplateColumns: this._gridTemplate("drawerContentV11") };
    },
    visibleDrawerContentV10Cols() {
      return this._visibleCols("drawerContentV10");
    },
    visibleDrawerContentV11Cols() {
      return this._visibleCols("drawerContentV11");
    },
  },
});
