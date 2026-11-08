/* columns_persist.js — R4 大文件拆分(计划 26-11-02-2342 §07)
 * 列模型 · 列宽持久化 / 列显隐 / 自适应 / 拖宽。
 * 只搬方法定义, 实现逐行未改; 根文件已定义该域, 本片段在其后原地扩充(Object.assign)。
 * 加载序 = 四套皮肤 index.html 清单里紧跟根文件之后(与拆分前同一迭代替换序)。
 */
Object.assign(window.AQB_COLUMNS.methods, {
    /* 生效宽度现算(双轨模型的"生效轨", plan 26-09-21-1551 §3.1):
     * - 全自动页(colW 为空) -> 每次窗口变化后按当前渲染实测(保留"填满容器 + 自适应"的观感)
     * - 固化页(colW 非空)   -> 用意图值(冻结, 拖一列不再动其它列)
     * !只写易变态 colWidths, **绝不落盘** —— persistPage 只收意图(colHidden/colOrder/colW),
     *   "派生值没有资格落盘"是双轨模型唯一铁律(守阵 test_frontend_persist_page_takes_intent_only)。
     */
    recomputeEffective() {
      for (const page of ALL_TABLE_PAGES) {
        if (this.colW[page]) {
          this.colWidths = { ...this.colWidths, [page]: { ...this.colW[page] } };
          continue;
        }
        const headEl = this._headEl(page);
        if (!headEl) continue;
        const widths = this._renderedWidths(headEl, page);
        if (widths) this.colWidths = { ...this.colWidths, [page]: widths };
      }
    },

    /* 空存储提示(W4 origin 隔离 + W5 浏览器"关闭时清除站点数据"): 本 origin 没有列偏好记录时
     * 记一次 —— 进**通知面板**(状态栏铃铛, 未读徽标)而不是页面浮层。
     * !出口口径(2026-10-09 用户实报): 早期版本运行时往 body 里插一条 fixed 横幅, 它压在页面内容上,
     *   且**每次自动化测试都触发**(测试用全新浏览器上下文 => 没有"已提示"去重标记), 把每张截图都
     *   盖掉一截。改为只进通知面板(ui_feedback.js::_recordNotice): 面板默认收起, 不占版面、
     *   不进截图, 入口徽标提示"有话要说"。文案本身一字不改 —— 陈述事实与排查路径的价值不变。
     *
     * !为什么只陈述"本地址没有偏好记录"、不做精确判定(2026-09-24 取证): 站点级"关闭窗口时清除
     * Cookie 和站点数据"(Chromium cookie 例外 setting=4 = SESSION_ONLY)会在关浏览器时把该 host 的
     * Cookie 与 localStorage **一起**清掉 => "被清过"与"首次访问"在客户端**完全同形**: 任何能当跨会话
     * 记忆用的东西(包括本函数的"已提示"标记)都躺在被清掉的那份数据里, 没有服务端就无法区分。
     * 故这里给"事实 + 两种成因 + 自查路径", 不下结论(取证: Edge/Chrome 的 cookie 例外里都有
     * `127.0.0.1,*` setting=4, 于是"浏览器重启后偏好全回默认"被当成应用 bug 追了多轮)。 */
    _showColsOriginHint() {
      if (this._colsOriginHintShown) return;
      this._colsOriginHintShown = true;
      // 同一次标签会话只记一次: 清站点数据的环境下 localStorage 里的"已提示"标记也一起没了,
      // 只靠它会在每次关浏览器重开后又记一条; sessionStorage 随标签关闭失效, 正好只兜"同一次会话"。
      try {
        if (sessionStorage.getItem(COLS_ORIGIN_HINT_KEY)) return;
        sessionStorage.setItem(COLS_ORIGIN_HINT_KEY, "1");
      } catch { /* 私隐模式等: 退回下面 localStorage 那层标记 */ }
      try {
        if (localStorage.getItem(COLS_ORIGIN_HINT_KEY)) return;
        localStorage.setItem(COLS_ORIGIN_HINT_KEY, "1");
      } catch { /* 私隐模式: 写失败也继续记, 本会话内由 _colsOriginHintShown 挡住 */ }
      this._recordNotice(
        "本地址还没有列偏好记录。常见成因: 1. 偏好按站点隔离存储, 换地址/端口"
        + "(127.0.0.1 ↔ localhost、38080 ↔ 38081)各存一份; 2. 浏览器在本地址上开了"
        + "「关闭窗口时清除 Cookie 和站点数据」→ 每次关掉浏览器偏好都会回默认"
        + "(Edge 可在 edge://settings/content/all 里查该地址)。可固定用同一地址, "
        + "或改用 http://localhost:<端口> 打开。"
      );
    },

    /* 唯一持久化漏斗(plan 26-09-21-1551 §3.4): 全仓对 COLS_STORE_KEY 的 setItem **只允许这一处**
     * (静态守阵钉住)。写 v5 按页子树: 以存储为底(RMW, 防"同一毫秒两边写"), 只覆盖本次涉及的
     * page, 其余 page 取存储最新值。!只收意图态(colHidden/colOrder/colW) —— 生效宽度 colWidths
     * 是按窗口现算的派生值, 到不了这里; 旧模型"先存后算/先算后存"的顺序约束在本模型下不存在
     * (派生根本不在持久化路径上)。 */
    persistPage(page) {
      const prev = readColStateRaw();
      const base = prev && prev.pages && typeof prev.pages === "object"
        ? { v: 5, origin: location.origin, pages: { ...prev.pages } }
        : { v: 5, origin: location.origin, pages: {} };
      base.pages[page] = {
        hidden: this.colHidden[page] || [],
        order: this.colOrder[page] || [],
        w: this.colW[page] || null,
      };
      // 写失败(私隐模式/配额满)不得影响功能: 本次会话内的调整仍在内存里生效
      try {
        localStorage.setItem(COLS_STORE_KEY, JSON.stringify(base));
      } catch { /* 忽略: 仅失去跨会话记忆 */ }
    },
    /* 跨标签同步(F2): 别的标签改了列 -> 本标签**整份采用**存储里的意图(与"刷新一次"等价)。
     * 双轨模型下采纳永远安全: 采纳的是纯意图, 生效宽度随后由 recomputeEffective 按本窗口现算,
     * 不存在"采纳了别的窗口算出的 px"这回事。不做逐列合并 —— 那需要给每段加"谁更新"的时间戳
     * 语义, 代价远大于收益(同页同秒并发仍最后写赢, 固有且可接受)。
     * !调用方只能是 storage 事件(它**只在其它标签**触发, 写入方自己收不到, 故无需去重)
     *   与 visibilitychange 的"回到可见"分支(补漏: 标签被冻结 / 事件丢失)。 */
    adoptColState() {
      const next = loadColState();
      this.colHidden = next.hidden;
      this.colOrder = next.order;
      this.colW = next.w;
      this.$nextTick(() => this.recomputeEffective());
    },
    colVisible(page, key) {
      return !(this.colHidden[page] || []).includes(key);
    },
    toggleColumn(page, key) {
      const col = columnDef(page, key);
      if (!col || col.locked) return;  // locked 列不可隐藏(模板中不渲染其勾选框, 这里是双保险)
      const cur = this.colHidden[page] || [];
      const hidden = cur.includes(key) ? cur.filter((k) => k !== key) : [...cur, key];
      this.colHidden = { ...this.colHidden, [page]: hidden };
      // 固化页: 新显示的列需要一个 px 宽度才能维持"只改一列"的策略(全自动页交给现算)
      if (this.colW[page] && !hidden.includes(key)) {
        const w = { ...(this.colW[page] || {}) };
        if (!w[key]) {
          w[key] = templateMinPx(col.tpl) + "px";
          this.colW = { ...this.colW, [page]: w };
        }
      }
      this.persistPage(page);
      this.$nextTick(() => this.recomputeEffective());
    },
    resetAllColumnWidths(page) {
      // 恢复默认列宽: 清空意图宽度(w=null) -> 回全自动, 该页重新随窗口自适应
      this.colW = { ...this.colW, [page]: null };
      this.colWidths = { ...this.colWidths, [page]: {} };  // 立即回弹性模板, 下一帧按新渲染实测
      this.persistPage(page);
      this.$nextTick(() => this.recomputeEffective());
    },
    fitColumnsToWindow(page) {
      // 适应窗口宽度(2026-09-21 D2 拍板): 回**全自动** —— 清空意图宽度与生效覆盖, 让默认弹性
      // 模板重新填满容器, 且此后继续随窗口自适应。旧实现把"当前窗口算出的快照"固化为偏好,
      // 正是"派生值当意图"的残留(换窗口即过拟合); 想固定某一列 -> 拖它(见 startResize)。
      this.colW = { ...this.colW, [page]: null };
      this.colWidths = { ...this.colWidths, [page]: {} };
      this.persistPage(page);
      this.$nextTick(() => this.recomputeEffective());
    },
    /* 列选择器底部两个动作的"全表"入口(计划 26-10-11-1722 P4): 遍历注册表, 取代模板里逐页手写的
     * 四条调用(加一张表不用再改模板)。W2 起取**全集** —— 列选择器既然列出抽屉三表的列, 两个
     * "全表"动作就必须覆盖它们, 否则会出现"能勾选但恢复不了"的半截能力(见 computed `tableDefs`)。 */
    resetAllColumnWidthsAll() {
      for (const page of ALL_TABLE_PAGES) this.resetAllColumnWidths(page);
    },
    fitColumnsToWindowAll() {
      for (const page of ALL_TABLE_PAGES) this.fitColumnsToWindow(page);
    },

    /* 列宽拖拽: 拖某列**只改该列**
     *
     * 关键在于起始时把**全部可见列**固化为当前渲染 px —— 它们原本可能是 minmax/fr 弹性值,
     * 不固化的话被拖列会把余量从邻居那儿抢走(表现为"调一列, 其它列跟着变")。
     * 按住 Shift 拖拽 = 与相邻列互相挤占(总宽不变), 对应主流表格的 shift-resize。
     *
     * 拖拽抑制误触排序: resizer 与 .h-cell 共父级, mouseup 后浏览器仍派发 click 冒泡到
     * .h-cell 触发 setSort(用户感知为"调列宽顺手把排序变了")。这里累计位移超过阈值时,
     * 在 capture 阶段拦截下一次 click(stopPropagation+preventDefault), 拦完即注销;
     * 且 mouseup 后下一拍自清 —— mouseup 落在窗口外(不产生 click)时拦截层若只等"下一次
     * click"注销, 会常驻吞掉页面任意位置的下次点击(R4 存量评审 R5#38)。
     * 未拖动(纯点击 resizer)不升格意图也不拦截, 保持原行为(R4 存量评审 R5#37):
     * 升格会把起始渲染快照 merge 进 colW 落盘, 该页自此从「全自动」静默转「固化」。
     */
    startResize(event, page, key) {
      const headEl = event.target.closest(".group-head") || event.target.closest(".detail-head");
      if (!headEl) return;
      const widths = this._renderedWidths(headEl, page);
      if (!widths) return;
      const vis = this._visibleCols(page);
      const idx = vis.findIndex((c) => c.key === key);
      if (idx < 0) return;
      const startX = event.clientX;
      const startVal = parseFloat(widths[key]);
      const neighbor = event.shiftKey ? vis[idx + 1] : null;
      const startNeighbor = neighbor ? parseFloat(widths[neighbor.key]) : 0;
      let dragged = false;  // 位移超过 RESIZE_DRAG_THRESHOLD 即置真, up 时用于决定是否拦 click
      let lastWidths = null;  // 拖拽中的最新整页 px(up 时升格为意图)
      const move = (e) => {
        if (!dragged && Math.abs(e.clientX - startX) > RESIZE_DRAG_THRESHOLD) dragged = true;
        if (!dragged) return;  // 未过阈值不写生效轨: 位移 <=3px 时写入的只是起始快照, 会覆盖微动
                               // (内存态, 下次窗口变化自愈, 但纯观感上列宽"被定住") —— 过阈值才生效
        const w = Math.max(MIN_COL_PX, Math.round(startVal + e.clientX - startX));
        const next = { ...widths, [key]: `${w}px` };
        if (neighbor) {
          next[neighbor.key] = `${Math.max(MIN_COL_PX, Math.round(startNeighbor - (w - startVal)))}px`;
        }
        this.colWidths = { ...this.colWidths, [page]: next };  // 只动生效态, 意图在 up 时一次性升格
        lastWidths = next;
      };
      const up = () => {
        document.removeEventListener("mousemove", move);
        document.removeEventListener("mouseup", up);
        // 未拖动 = 纯点击 resizer: 先 return, 不升格意图也不拦 click(保持原行为) ——
        // 零位移也把起始渲染快照 merge 进 colW 落盘, 该页会静默从「全自动」转「固化」
        // (R4 存量评审 R5#37; dragged 在本函数只覆盖本门槛与 click 拦截两件事)
        if (!dragged) return;
        // 意图升格: 以既有 colW 为底 merge(!隐藏列的 px 在这里保住 —— 渲染快照只含可见列,
        // 旧实现整段替换正是"隐藏列宽度被抹"的根因), 再叠本次拖拽终值; 整页自此固化
        const intent = { ...(this.colW[page] || {}), ...widths, ...(lastWidths || {}) };
        this.colW = { ...this.colW, [page]: intent };
        this.persistPage(page);
        this.$nextTick(() => this.recomputeEffective());
        // 拖拽尾处浏览器会冒泡一次 click 到 .h-cell 触发 setSort —— capture 阶段拦掉即停;
        // 下一拍自清兜底(mouseup 落窗口外不产生 click 时拦截层不得常驻, R4 存量评审 R5#38)
        const swallow = (ev) => {
          ev.stopPropagation();
          ev.preventDefault();
          document.removeEventListener("click", swallow, true);
        };
        document.addEventListener("click", swallow, true);
        setTimeout(() => document.removeEventListener("click", swallow, true), 0);
      };
      document.addEventListener("mousemove", move);
      document.addEventListener("mouseup", up);
    },
    /* 双击分隔线 = 按内容自适应宽度(表头 + 当前已渲染行), 夹在 [最小宽, MAX_FIT_PX] */
    autoFitColumn(event, page, key) {
      const headEl = event.target.closest(".group-head") || event.target.closest(".detail-head");
      if (!headEl) return;
      const vis = this._visibleCols(page);
      const idx = vis.findIndex((c) => c.key === key);
      if (idx < 0) return;
      const container = headEl.parentElement;
      const rowSel = page === "detail" ? ".member-row" : ".group-row";
      let max = headEl.children[idx] ? headEl.children[idx].scrollWidth : MIN_COL_PX;
      for (const row of container.querySelectorAll(rowSel)) {
        const cell = row.children[idx];
        if (cell) max = Math.max(max, cell.scrollWidth);
      }
      const width = Math.min(MAX_FIT_PX, Math.max(MIN_COL_PX, Math.ceil(max) + 18));
      const widths = this._renderedWidths(headEl, page) || {};
      // 意图升格: 以既有 colW 为底 merge(隐藏列 px 保住, 同 startResize), 再叠可见列冻结 + 本列适配备
      const intent = { ...(this.colW[page] || {}), ...widths, [key]: `${width}px` };
      this.colW = { ...this.colW, [page]: intent };
      this.colWidths = { ...this.colWidths, [page]: { ...intent } };  // 同步生效态, 免一帧跳变
      this.persistPage(page);
    },
});
