/* columns_drag.js — R4 大文件拆分(计划 26-11-02-2342 §07)
 * 列模型 · 列顺序拖拽与落点。
 * 只搬方法定义, 实现逐行未改; 根文件已定义该域, 本片段在其后原地扩充(Object.assign)。
 * 加载序 = 四套皮肤 index.html 清单里紧跟根文件之后(与拆分前同一迭代替换序)。
 */
Object.assign(window.AQB_COLUMNS.methods, {

    /* ------------------------------------------------ 列序(表头拖动重排 TBL-05) */

    /* 当前生效的全列序(可见+隐藏): colOrder 优先, 未入序的列(新增/残留)按定义序补尾 */
    _orderedKeys(page) {
      const defs = TABLE_COLUMNS[page].map((c) => c.key);
      const order = this.colOrder[page];
      if (!order || !order.length) return [...defs];
      const head = order.filter((k) => defs.includes(k));
      return [...head, ...defs.filter((k) => !head.includes(k))];
    },

    /* 落点换算: dropIdx 是**可视列空间**的插入边界(表头只渲染可见列), 存储的 colOrder 是
     * **全序列**(含隐藏列) —— 移除自身后按"第 b 个可见列之前"折算插入点, 隐藏列的相对
     * 次序不动(之后取消隐藏时插回原相对位)。落库后下一帧 recomputeEffective 重算生效宽度。 */
    applyColOrder(page, key, dropIdx) {
      const full = this._orderedKeys(page);
      const vis = full.filter((k) => this.colVisible(page, k));
      const fromVis = vis.indexOf(key);
      if (fromVis < 0 || dropIdx < 0 || dropIdx > vis.length) return;
      const at = dropIdx > fromVis ? dropIdx - 1 : dropIdx;  // 移除自身后的插入边界(可视空间)
      full.splice(full.indexOf(key), 1);
      let inserted = false;
      for (let i = 0, seen = 0; i < full.length; i++) {
        if (!this.colVisible(page, full[i])) continue;
        if (seen++ === at) { full.splice(i, 0, key); inserted = true; break; }
      }
      if (!inserted) full.push(key);  // 边界在末个可见列之后
      this.colOrder = { ...this.colOrder, [page]: full };
      this.persistPage(page);
      this.$nextTick(() => this.recomputeEffective());
    },

    /* 表头拖动重排手势: mousedown 阈值方案(与列宽拖拽 startResize 同款) —— 不用 HTML5
     * draggable, 避免原生拖影/文本选择与"点击排序""列宽拖拽"互相干扰。resizer 的
     * mousedown 已 .stop(不会进到这里); 位移超阈值才进入重排, 释放时若真拖过用 capture
     * 阶段 swallow 拦掉冒泡 click(防误触排序, 同 startResize 手法)。
     * 指示线: head 容器内绝对定位 .col-drop-line(不占 grid 轨道), left 由 move 实时更新。 */
    startColDrag(event, page, key) {
      if (event.button !== 0) return;  // 仅左键; 右键 = openColMenuAt(contextmenu), 中键不劫持
      const headEl = event.target.closest(".group-head") || event.target.closest(".detail-head");
      if (!headEl) return;
      if (this._visibleCols(page).length < 2) return;  // 单列无从重排
      event.preventDefault();  // 抑制表头文本选择(拖拽手势的先决条件; 纯点击不受影响)
      const startX = event.clientX, startY = event.clientY;
      const TH = 6;  // 位移阈值(px): 之内视为普通点击(排序照旧), 超过才进入重排
      const label = (columnDef(page, key) || {}).label || key;  // FX-25 虚影文案
      let dragging = false;
      const cells = () => Array.from(headEl.children).filter((el) => el.classList.contains("h-cell"));
      const move = (e) => {
        if (!dragging) {
          if (Math.abs(e.clientX - startX) <= TH && Math.abs(e.clientY - startY) <= TH) return;
          dragging = true;
          headEl.classList.add("col-dragging");
          document.body.style.cursor = "col-resize";
        }
        const list = cells();
        const base = headEl.getBoundingClientRect();
        let idx = list.length;  // 默认插到末尾之后
        for (let i = 0; i < list.length; i++) {
          const cr = list[i].getBoundingClientRect();
          if (e.clientX < cr.left + cr.width / 2) { idx = i; break; }
        }
        // 指示线落在插入边界的列间隙中线(idx<len 取该列左缘-半间隙; 末尾取末列右缘+半间隙)
        const edge = idx < list.length ? list[idx].getBoundingClientRect().left : list[list.length - 1].getBoundingClientRect().right;
        this.colDrag = { page, key, idx, x: edge - base.left - headEl.clientLeft + (idx < list.length ? -5 : 5) };
        // FX-25: 虚影只更新 x/y(走 transform, 不触发重排); 无虚影时鼠标无处可依, 用户分不清"拖的是什么"
        this.colGhost = { label, x: e.clientX, y: e.clientY };
      };
      const up = () => {
        document.removeEventListener("mousemove", move);
        document.removeEventListener("mouseup", up);
        headEl.classList.remove("col-dragging");
        document.body.style.cursor = "";
        const drag = this.colDrag;
        this.colDrag = null;
        this.colGhost = null;   // FX-25: 松手即消失
        if (!dragging) return;  // 未过阈值 = 普通点击, click 正常冒泡(排序不受影响)
        if (drag && drag.page === page) this.applyColOrder(page, key, drag.idx);
        // 拖拽尾冒泡 click 会触发 setSort(同列释放时) —— capture 阶段拦掉即停(同 startResize)。
        // !自清兜底(R4 存量评审 R5#38): 真拖后 mouseup 可能落在窗口外/不产生 click 的位置
        // (拖出浏览器边界松手常见), 拦截层只等「下一次 click」注销就会常驻 capture 层,
        // 把用户页面任意位置的下次点击整个吞掉(菜单按钮/排序各哑一次)。click 若在本拍派发
        // 必先于定时器回调(同一输入任务内), 故下一拍自清不会漏拦。
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

    /* 落点指示线内联样式(仅本 page 的表头渲染; top/height 走 CSS 全高, left 相对 head 盒) */
    colDropLineStyle(page) {
      const d = this.colDrag;
      if (!d || d.page !== page) return {};
      return { left: d.x + "px" };
    },
    /* 成员行(展开明细)窗口: 与 group/torrent 不同, 三个成员窗口都要按"当前展开单元"
     * 的成员数组计算占位 —— 故**带参数**。Vue 3 computed 是无参 getter, 这里必须放
     * methods(否则模板里 memberPadTop(g.members) 触发 this.memberWin 当 getter 调用,
     * 拿到的是对象而不是函数 → "this.memberWin is not a function", 整表就地白屏)。
     * 该 bug 由拆分前的同一段代码继承而来, 之前未塌是因为它走的是追剧页的成员行(整表
     * 不白)还是其它原因未复现, 现在辅种页展开一行即 100% 触发, 必须正名。
     * !调用契约(R4 存量评审 R5#35): 传入的必须是**排序后**的数组 —— 前缀和/切片/占位
     * 与渲染数组同源同序, 调用点(winMembers / memberPadTop / memberPadBottom)各自先过
     * sortedMembers; 直接喂未排序的 g.members 会在明细排序激活时切片错位(见 winMembers 注)。 */
    memberWin(list) {
      return this._rowWindow("member", list || [], null);
    },
    memberPadTop(list) {
      return this.memberWin(this.sortedMembers(list)).padTop;
    },
    memberPadBottom(list) {
      return this.memberWin(this.sortedMembers(list)).padBottom;
    },
});
