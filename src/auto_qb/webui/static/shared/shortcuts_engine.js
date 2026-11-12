/* shortcuts_engine.js — R4 大文件拆分(计划 26-11-02-2342 §07)
 * 键盘快捷键 · 分发引擎 / 光标移动 / 行内命令。
 * 只搬方法定义, 实现逐行未改; 根文件已定义该域, 本片段在其后原地扩充(Object.assign)。
 * 加载序 = 四套皮肤 index.html 清单里紧跟根文件之后(与拆分前同一迭代替换序)。
 */
Object.assign(window.AQB_SHORTCUTS.methods, {
    /* ---------------- 引擎: 匹配与屏蔽 ---------------- */
    /* 生效键表(模板基准 ⊕ overrides): 序列 -> 注册表条目。fixed(Esc)不进匹配表;
     * 黑名单串/空串(显式禁用)跳过 —— 后端脏数据在引擎层也不生效(守阵另断言默认键全干净)。 */
    _kbTable() {
      if (this._kbTableCache) return this._kbTableCache;
      const cfg = window.AQB_KEYS.load();
      const overrides = (cfg && cfg.overrides) || {};
      const map = new Map();
      for (const item of AQB_SHORTCUT_DEFS) {
        if (item.fixed || !item.run) continue;
        const serial = Object.prototype.hasOwnProperty.call(overrides, item.id) ? overrides[item.id] : item.def;
        if (!serial || kbInBlacklist(serial) || map.has(serial)) continue;
        map.set(serial, item);
      }
      this._kbTableCache = map;
      return map;
    },
    /* 当前作用域(五值之三取二; modal 在派发处单独分流):
     * 方案A W2(计划 26-10-03-0917 §3.2): 停靠面板**不再是键盘作用域** —— 它是种子列表的附属
     * 面板而非浮层, 面板开着时列表键位保持存活(§2.2 矩阵), scope 落 "list"(Delete 直连同样依赖
     * 此判定)。W1 曾临时让 drawer.open 判成 "drawer" 保逐键零回归, 随 _kbOverlayBusy 摘名单
     * 一并取消; "drawer" 值与下方浮层放行分支的 scope==="drawer" 判定机制保留(条目清空, 引擎留位)。 */
    _kbScope() {
      if (this.page === "settings") return "settings";
      return "list";
    },
    /* 模态层名单: 与 dialogs.js escBusy 的**浮层名单**同形, 但不含选择/展开兜底段
     * (有选中时快捷键必须照常可用 —— 目标解析走选中集合; escBusy 是 Esc 退栈专用, 不能混用)。
     * 方案A W2: 名单摘除 drawer.open —— 停靠面板不是浮层, Delete 等注册表外绑定与列表键在面板
     * 开着时保持可用; escBusy(退栈链)仍含 drawer.open(Esc 关面板), 两名单自此职责分叉。 */
    _kbOverlayBusy() {
      return !!(this.modal.visible || this.addOpen || this.statsOpen || this.speedOpen || this.mgrOpen ||
        this.metaOpen || this.relChain.open || this.filePrio.visible || this.historyOpen || this.headMenu.visible ||
        this.colMenuOpen || this.uiMenuOpen || this.searchHelpOpen || this.filterMenu || this.menu.visible ||
        this.kbHelpOpen || this.kbFullOpen);
    },
    /* 引擎入口(lifecycle.js mounted 注册在 Esc 退栈链之后; unmounted 撤除) */
    _kbOnKeyDown(e) {
      if (e.key === "Escape") return;                  // 固定键归退栈链, 引擎永不接(§08 C5)
      if (e.defaultPrevented) return;                  // 多 handler 礼仪: 先到先得
      if (e.isComposing || e.keyCode === 229) return;  // IME 组合期双保险(§3.4)
      if (KB_MODIFIER_CODES.has(e.code)) return;       // 纯修饰键不判定
      if (!this.authOk) return;                        // 登录遮罩期不响应
      const item = this._kbTable().get(kbSerializeEvent(e));
      if (e.repeat && !(item && item.repeat)) return;  // 长按自动重复默认丢弃; repeat 条目(上下键族)放行连发
      const t = e.target;
      const inInput = !!(t && t.closest && t.closest("input, textarea, select, [contenteditable]"));
      if (!item) {
        // Delete 键是注册表**外**的"额外删除操作"(§08 决策 v4): 直连删除链(_kbDelete 内部走
        // _deleteFlow 的确认框 + HR 风险点名, 与批量删除同链), 不占键表槽位、不进面板改键列表。
        // 上游 qB WebUI 习惯对齐(Delete 删除所选); Shift+Delete 同走确认框, 无"永久删"分支。
        if (!inInput && e.code === "Delete" && !e.ctrlKey && !e.altKey && !e.metaKey &&
            !this._kbOverlayBusy() && this._kbScope() === "list") {
          e.preventDefault();
          this._kbDelete();
        }
        return;
      }
      if (inInput && !item.inputSafe) return;          // 输入元素内只放行显式标记 inputSafe 的绑定
      const scope = this._kbScope();
      if (item.scope === "modal") {
        if (!this.modal.visible) return;               // 模态键位仅在模态层内响应(§5.1 三段之三)
      } else if (this.modal.visible) {
        return;                                        // 模态层打开: 只响应模态键位, 其余一律失效
      } else if (!inInput && this._kbOverlayBusy()) {
        // 浮层打开: 只放行焦点局部(设置页 Ctrl+S)自身的键位 —— 列表键位在浮层下仍然失效(同 W1-W4)。
        // 方案A W2: drawer.open 已摘出浮层名单 —— 停靠面板是列表附属不是浮层, 面板开着列表键位
        // 全部存活(§2.2 矩阵); scope==="drawer" 判定随名单摘除不再可达, 机制保留(条目清空)。
        // 自切换白名单(2026-10-09 切换语义, 报告 26-10-09-1731 §07.1): 若打开着的正是**本键自己
        // 控制的浮层**(统计/历史/帮助/列选择器), 本键仍消费 —— 否则第二次按键被本闸门吞掉,
        // 「再按一下关」永远到不了 run。名单外浮层开着时本键仍失效(原口径不变)。
        const own = KB_SELF_TOGGLE_OVERLAY[item.id];
        if (!(own && this[own])) {
          if (item.scope !== scope || (scope !== "drawer" && scope !== "settings")) return;
        }
      } else if (item.scope !== "global" && item.scope !== scope) {
        return;                                        // 非焦点页不串扰
      }
      // 条件绑定(表头 when, 见注册表条目形状注): 条件不成立即**不消费**本次按键 ——
      // 不 preventDefault, 键位留给浏览器/其它 handler(流量图窗口键 [ / ] 无图时不该被吞)
      if (item.when && !item.when(this)) return;
      e.preventDefault();
      item.run(this);
    },
    /* ---------------- W2: 光标模型(按身份不按下标) ---------------- */
    /* 光标线性链: 辅种页=组行(+展开组的成员行); 种子页=平铺行; 追剧页=剧/集单元(+展开集的成员行)。
     * 每次移动时现取现定位 —— 轮询整表替换/排序/筛选后身份重定位天然成立, 不需刷新钩子。
     * !成员行入链(2026-10-08 计划 26-10-08-1217, 原注释的「成员行 vNext」在此兑现): 面板三视图
     *   共用后, 辅种页/追剧页的成员行也要能 up/down 走到 —— 光标 kind=torrent 是 Alt+1~5 双态入口与
     *   面板跟随(_kbFollowDrawer)的目标解析依据, 成员行不在链上则这两条路径在两页都走不通。
     *   序 = 父行紧邻其子行(组 -> 其成员 / 集 -> 其版本), 与视觉顺序一致; 成员行 kind=torrent
     *   天然不参与展开语义(_kbExpandRow 对 torrent 无分支), Enter 落在 openTorrentDrawer。 */
    _kbRows() {
      if (this.page !== "groups") return [];
      if (this.viewMode === "torrents") return this.filteredTorrents.map((m) => ({ kind: "torrent", id: m.hash }));
      if (this.viewMode === "shows") {
        const out = [];
        for (const s of this.decoratedShows) {
          out.push({ kind: "show", id: s.key });
          if (this.expandedShows.includes(s.key)) {
            for (const sn of s.seasons) {
              for (const e of sn.episodes) {
                const eid = this.showEpRowId(s.key, sn.season, e.epKeyStr);
                out.push({ kind: "ep", id: eid });
                if (this.expandedShowEp === eid) {
                  // 版本行序走 sortedMembers(与集明细表同源, 光标上下即屏幕上下), hash 一律经
                  // memberHashesOf 单点取(集成员在前端已换成对象, 裸传会字符串化成 [object Object])
                  const hs = this.memberHashesOf(this.sortedMembers(e.members));
                  for (const h of hs) out.push({ kind: "torrent", id: h });
                }
              }
            }
          }
        }
        return out;
      }
      const out = [];
      for (const g of this.filteredGroups) {
        out.push({ kind: "group", id: g.key });
        if (this.expandedKey === g.key) {
          const hs = this.memberHashesOf(this.sortedMembers(g.members));
          for (const h of hs) out.push({ kind: "torrent", id: h });
        }
      }
      return out;
    },
    isKbCursor(kind, id) {
      const c = this.kbCursor;
      return !!c && c.kind === kind && c.id === id;
    },
    _kbApplyCursor(rows, idx) {
      this.kbCursor = rows[idx];
      this._kbScrollRowIntoView(rows, idx);
      this._kbFollowDrawer();  // 方案A W2 跟随单点(§2.3; page+kind 守卫在方法内, 相邻视图零开销返回)
    },
    _kbMove(delta) {
      const rows = this._kbRows();
      if (!rows.length) {
        this.kbCursor = null;
        return;
      }
      const cur = this.kbCursor ? rows.findIndex((r) => r.kind === this.kbCursor.kind && r.id === this.kbCursor.id) : -1;
      // 光标失效(无光标/刷新换人/切视图/点击的明细行不在链上): 回落**视口就近行**(26-09-30-1806
      // 方案 B) —— 下移落视口内首行, 上移落视口内末行, 一次按键落在眼前, 不再跳极值行(大库上
      // 即「鼠标在顶部按一下 up 视口跳到底」); 解析不出视口信息才退回旧口径(下移首行/上移末行)。
      // 找得到光标则裁剪夹取(就近步进口径)。
      const idx = cur < 0
        ? this._kbViewportRow(rows, delta)
        : Math.max(0, Math.min(rows.length - 1, cur + delta));
      if (idx === cur) return;
      this._kbApplyCursor(rows, idx);
    },
    /* 无光标回落: 视口就近行(报告 26-09-30-1806 方案 B)。down(delta>0) 落视口内首行, up 落视口内
     * 末行。两条解析路: (1)窗口化视图(group/torrent)用 _rowPre 前缀和换算文档 y(与
     * _kbScrollRowIntoView 同源, 长度不符视为失效, 沿用 P1-2 退避口径); (2)其余情形(追剧页全量
     * 渲染 / 小列表不开窗 / 前缀和失效)扫渲染行可见性 —— 视图切换是 v-if, DOM 里只有当前视图。
     * **两路坐标系不同**(前缀和 = 文档坐标, 渲染行 rect = 视口坐标), 见函数内首段注释: 混用会
     * 在滚动后把渲染行全判「出视口」, 退化成跳极值行。
     * 都解析不出 -> 退回旧口径: down 首行 / up 末行(保守, 不猜错)。只读几何, 滚动仍归 _kbApplyCursor。 */
    _kbViewportRow(rows, delta) {
      /* 坐标系口径(2026-10-09 修坐标错位): 单点 _kbViewTop / _kbViewBottom 返回**视口坐标**
       * (与 getBoundingClientRect 同源) —— 渲染行 rect 直接比它; 而窗口化的**前缀和 y 是文档
       * 坐标**, 比较时必须显式加回 sy(下面单取的滚动量)。旧实现把滚动量一并加进 vTop/vBot
       * 再拿去比 rect —— 只在未滚动时成立, 一旦滚过一屏, 所有渲染行都被判「出视口」,
       * 无光标回落就退化成「跳极值行」(down 回顶 / up 落底; 实测 scrollY=1500 时期望首可见行 ->
       * 实落 row 0)。两套坐标别混用。 */
      const vTop = this._kbViewTop();     // 视口坐标(顶栏 + 吸顶列头)
      const vBot = this._kbViewBottom();  // 视口坐标(状态栏 / 面板开着时让位面板顶缘)
      const sy = window.scrollY;          // 前缀和 y 是文档坐标, 比较时加回
      const kind = rows[0].kind === "torrent" || rows[0].kind === "group" ? rows[0].kind : null;
      const pre = kind && this._rowPre && this._rowPre[kind];
      if (pre && pre.length === rows.length + 1) {
        const top = this._winTop[kind] || 0;
        if (delta > 0) {
          for (let i = 0; i < rows.length; i++) {
            if (pre[i + 1] + top > sy + vTop + 4) return i;  // 首个底边伸进视口的行
          }
        } else {
          for (let i = rows.length - 1; i >= 0; i--) {
            if (pre[i] + top < sy + vBot - 4) return i;  // 末个顶边伸进视口的行
          }
        }
        return delta > 0 ? 0 : rows.length - 1;
      }
      const byId = new Map(rows.map((r, i) => [r.id, i]));
      let first = -1;
      let last = -1;
      const vTopM = vTop + 4;
      const vBotM = vBot - 4;
      for (const el of document.querySelectorAll("[data-key], [data-hash]")) {
        const dk = el.getAttribute("data-key");
        const i = byId.get(dk !== null ? dk : el.getAttribute("data-hash"));
        if (i === undefined) continue;
        const rect = el.getBoundingClientRect();
        if (rect.bottom <= vTopM || rect.top >= vBotM) continue;  // 完全出视口(display:none 恒 0 也被挡)
        if (first < 0 || i < first) first = i;
        if (i > last) last = i;
      }
      if (delta > 0) return first >= 0 ? first : 0;
      return last >= 0 ? last : rows.length - 1;
    },
    _kbMoveTo(idx) {
      const rows = this._kbRows();
      if (!rows.length) return;
      this._kbApplyCursor(rows, idx < 0 ? rows.length - 1 : Math.max(0, Math.min(rows.length - 1, idx)));
    },
    _kbMovePage(dir) {
      const rows = this._kbRows();
      if (!rows.length) return;
      const kind = this.kbCursor ? this.kbCursor.kind : rows[0].kind;
      const est = this._rowH[kind === "torrent" ? "torrent" : kind === "group" ? "group" : "member"] ||
        ROW_WIN_EST_H[kind === "torrent" ? "torrent" : "group"] || 44;
      /* PageUp / PageDown「一屏」= **可见带**内的行数(2026-10-09 收口): 可见带 = _kbViewTop 到
       * _kbViewBottom(顶栏+吸顶列头 … 固定状态栏, 面板开着再让位面板顶缘), **不是**整窗高 ——
       * 停靠面板一开可见带只剩一半(实测 739 -> 353px, 屏内只剩 6 行), 而按整窗高算的一屏会前进
       * 12 行 => 每翻一屏**静默跳过 6 行**(不开面板时行高 71px 也每屏跳 1 行)。
       * 行高取 _rowH 实测均值(行窗口化维护)-> ROW_WIN_EST_H -> 44 兜底, 与窗口化同一口径。 */
      const band = Math.max(0, this._kbViewBottom() - this._kbViewTop());
      const per = Math.max(1, Math.floor(band / est));
      this._kbMove(dir * per);
    },
    /* 列表行可见下界(W4 几何走查产出, 计划 26-10-03-0917): 停靠面板开着时它 sticky 吸在视口底,
     * 底部一段列表行被面板盖住 —— 行可见下界不再是 window.innerHeight,
     * 而是面板顶缘(getBoundingClientRect().top 实测, 滚到文档底面板落回文档流时该值自然上移)
     * 减去 dock 的 8px 呼吸距。关闭(面板不在 DOM)或窄屏全屏态(D3, position:fixed —— 列表整幅被
     * 覆盖, 没有"部分可见"可言, 也避免 top 内插出退化区间)回落整窗高; fixed 判定走计算样式,
     * 断点单点在各皮肤 CSS 的 @media(max-width:900px), JS 不复制断点数。 */
    _kbViewBottom() {
      let bot = window.innerHeight;
      /* 底部固定状态栏(--statusbar-h, 34px)同样盖住列表末行(2026-10-09 用户报「键盘移到最后一个
       * 种子只显示一半」)。内容区底部的等高内边距治不了它: 那只在**滚到文档底**时把最后一行托到
       * 状态栏之上, 而滚动跟随的落点是「视口底 - 8px」—— 文档余量足够滚到那里, 于是末行停进状态栏
       * 背后(实测遮 26px / 行高 50px)。下界 = 状态栏顶缘, 与停靠面板取更紧的那个。 */
      const sb = document.querySelector(".statusbar");
      if (sb && getComputedStyle(sb).position === "fixed") {
        const sbr = sb.getBoundingClientRect();
        if (sbr.height > 0) bot = Math.min(bot, sbr.top);
      }
      if (this.drawer.open) {
        const panel = document.querySelector(".drawer-dock > .drawer");
        // 出入过渡在途: 面板顶缘的 DOM 实量是高度插值中间值, 读登记的落定顶缘(drawer.js 钩子写入);
        // 入场动画中切走视图时面板随视图卸载、leave 钩子不点火, 登记值悬空 —— 面板已不在 DOM 即作废
        if (this._drawerAnimTop) {
          if (panel) return Math.min(bot, this._drawerAnimTop - 8);
          this._drawerAnimTop = 0;
          return bot;
        }
        if (panel && getComputedStyle(panel).position !== "fixed") {
          bot = Math.min(bot, panel.getBoundingClientRect().top - 8);
        }
      }
      return bot;
    },
    /* 列表行可见**上界**单点(与 _kbViewBottom 对称, 2026-10-09 用户报「键盘移到第一个种子只显示
     * 一半」): 顶栏之下还压着**吸顶列头** `.group-head`(三皮肤一律 position:sticky, top =
     * calc(--head-h - 1px), 实测 32px 高) —— 行被它盖住时几何上「在视口内」但其实看不见, 只按
     * _headH 当上界的滚动跟随会把落点停在列头背后(实测遮 23px / 行高 71px; 行矮时过半)。
     * 列头不在 DOM(成员明细 .detail-head 非 sticky / 无表头的列表)或未吸顶时回落顶栏高。
     * 返回**视口坐标**(消费方自行加 window.scrollY), 与 _kbViewBottom 同口径。 */
    _kbViewTop() {
      const headH = this._headH || 0;
      const hd = document.querySelector(".group-head");
      if (!hd || getComputedStyle(hd).position !== "sticky") return headH;
      // 用列头自身高度而不是当前 rect.bottom: 吸顶前后 rect 在两态间跳(自然位还多一段 .layout
      // 上内边距), 高度恒定才可复算; 吸顶落位是 top = --head-h - 1(那 1px 是防透缝重叠), 多算 1px
      // 只是让行多让 1px, 不影响可见性。
      return headH + hd.getBoundingClientRect().height;
    },
    /* 滚动进视口: 目标已可见则不动(避免每次按键都跳)。渲染行用 getBoundingClientRect 差值;
     * 窗口化未渲染行用 _rowWindow 前缀和换算 y(计划 W2; 禁 scrollIntoView, 见文件头)。
     * 上下边界走 _kbViewTop / _kbViewBottom 两个单点(顶栏+吸顶列头 / 固定状态栏+停靠面板)。 */
    _kbScrollRowIntoView(rows, idx) {
      this.$nextTick(() => {
        const r = rows[idx];
        if (!r) return;
        const sel = r.kind === "group" || r.kind === "show" || r.kind === "ep"
          ? `[data-key="${CSS.escape(r.id)}"]`
          : `[data-hash="${CSS.escape(r.id)}"]`;
        const vTop = this._kbViewTop();     // 顶栏 + 吸顶列头(列头盖住列表首行, 2026-10-09 报障)
        const vBot = this._kbViewBottom();  // 状态栏 + 面板开着时让位面板顶缘(W4 几何走查)
        /* 用真实 DOM 矩形校正落点。抽成局部函数是为了在下一帧复用: 共享 runner 上
         * $nextTick 可能早于窗口化重渲(目标行还没进 DOM), 或前缀和用的是估算行高而实测
         * 行高随字体/平台变化 —— 两种情形都会让首次落点停在状态栏背后。下一帧用真实
         * 矩形再校正一次即可, 不靠猜(P1-2 退避口径: 不确定时不滚, 但不能就此不补)。
         * 边界沿用本次单点落值, 不二次读 _kbViewTop/_kbViewBottom(单点纪律)。 */
        const reveal = () => {
          const el = document.querySelector(sel);
          if (!el) return false;
          const rect = el.getBoundingClientRect();
          if (rect.top < vTop + 4) window.scrollBy(0, rect.top - vTop - 8);
          else if (rect.bottom > vBot - 4) window.scrollBy(0, rect.bottom - vBot + 8);
          return true;
        };
        /* 跨帧重试: 窗口化重渲未必一帧落定(共享 runner 上尤其慢), 单次 rAF 仍可能扑空,
         * 那就等于旧码被换掉的「静默放弃」。在 1s 时间窗内持续等到目标行进 DOM 再校正;
         * 到点仍不出现按 P1-2 退避放弃, 不无限排队, 也不猜位置。 */
        const revealWhenRendered = (deadline) => {
          if (reveal()) return;
          if (performance.now() < deadline) requestAnimationFrame(() => revealWhenRendered(deadline));
        };
        const revealNext = () => {
          const deadline = performance.now() + 1000;
          requestAnimationFrame(() => revealWhenRendered(deadline));
        };
        if (document.querySelector(sel)) {
          reveal();
          return;
        }
        // 窗口化把该行折叠了: 用前缀和算它的文档 y。前缀和与当前列表不同源(长度不符)时
        // 不滚到错位处(P1-2 退避), 但下一帧重渲落定后要用真实 DOM 补一次, 否则末行会
        // 一直压在固定状态栏背后(2026-11-09 GitHub CI 双皮肤稳定复现 25~31px 遮挡)。
        const kind = r.kind === "torrent" ? "torrent" : r.kind === "group" ? "group" : null;
        const pre = kind && this._rowPre && this._rowPre[kind];
        if (!pre || pre.length !== rows.length + 1) {
          revealNext();
          return;
        }
        const y = pre[idx] + (this._winTop[kind] || 0);
        const h = pre[idx + 1] - pre[idx];
        if (y < window.scrollY + vTop + 4) window.scrollTo(0, y - vTop - 8);
        else if (y + h > window.scrollY + vBot - 4) window.scrollTo(0, y + h - vBot + 8);
        revealNext();  // 估算行高与实测行高的偏差由后续帧补正
      });
    },
    /* 显式打开路径的行让位(2026-10-03 报障: 双击列表最后几行, 停靠面板一开把被点行盖住) ——
     * W4 下界单点只接了键盘跟随, drawer.js openTorrentDrawer(双击/右键/Enter/Alt+数字 共用
     * 的显式打开)挂上状态后调本方法一次补让位。面板 DOM 随 open 状态 v-if 挂载, 同帧还量不到
     * 面板 —— nextTick 后再测; 目标行下缘低于可视下界才 scrollBy, 本来可见就不动(不抢用户的
     * 滚轮位置); 行不在 DOM(窗口化折叠)静默放弃, 滚动位置宁可不动也不猜(P1-2 退避口径)。 */
    _kbRevealRow(hash) {
      this.$nextTick(() => {
        if (!this.drawer.open) return;
        const el = document.querySelector(`[data-hash="${CSS.escape(hash)}"]`);
        if (!el) return;
        const rect = el.getBoundingClientRect();
        const vBot = this._kbViewBottom();  // 面板开着时下界 = 面板顶缘(W4 单点); 关闭/窄屏全屏态回落整窗高
        if (rect.bottom > vBot - 4) window.scrollBy(0, rect.bottom - vBot + 8);
      });
    },
    /* ---------------- W2: 展开面板与定位页签 ---------------- */
    _kbParseEpId(id) {
      const parts = String(id).split("|");
      if (parts.length < 3) return null;
      return { showKey: parts[0], season: parts[1] === "~" ? null : Number(parts[1]), epKeyStr: parts.slice(2).join("|") };
    },
    _kbExpandRow() {
      const c = this.kbCursor;
      if (!c) return;
      if (c.kind === "group") {
        if (this.expandedKey !== c.id) {
          this.expandedKey = c.id;
          this.selAnchorGroup = c.id;  // 展开的组作为 Shift 多选默认起点(与 toggleExpand 同口径)
        }
        return;
      }
      if (c.kind === "show") {
        if (!this.expandedShows.includes(c.id)) this.expandedShows.push(c.id);
        return;
      }
      if (c.kind === "ep") {
        const p = this._kbParseEpId(c.id);
        if (p && this.expandedShowEp !== c.id) this.expandedShowEp = c.id;
      }
    },
    /* 成员行(torrent)的所属行解析(<- 收起所属单元用): 辅种页 = 展开的组行; 追剧页 = 展开的集行;
     * 种子页平铺行无父行(返回 null)。判据 = 成员落在**当前展开单元**的成员链上 —— 复用
     * selection.js::_memberRangeList 单点(与 _kbRows 渲染同源: memberHashesOf(sortedMembers)),
     * 保证"屏幕上的成员行"与"收起目标"不错位; 不在链上即无父行, 保守不动。
     * 只可能有一个单元处于展开态(expandedKey / expandedShowEp 单值), 故父行身份直接取它。 */
    _kbParentRow(c) {
      if (!c || c.kind !== "torrent" || this.viewMode === "torrents") return null;
      if (!this._memberRangeList().includes(c.id)) return null;
      if (this.viewMode === "shows") return this.expandedShowEp ? { kind: "ep", id: this.expandedShowEp } : null;
      return this.expandedKey ? { kind: "group", id: this.expandedKey } : null;
    },
    /* <- 收起当前行(注册表 row-collapse)。组/剧/集行 = 收起自身展开态(反向于 _kbExpandRow);
     * **成员行(torrent)** 无自身展开语义 —— 原实现只认 group/show/ep 三种 kind, 光标按 down 进组后
     * <- 静默无反应(用户 2026-10-09 报)。改为收起**所属单元**并把光标带回其行: 成员行随收起消失,
     * 不把光标留在链外(否则下一次移动要落视口就近回落, 观感是"光标丢了")。 */
    _kbCollapseRow() {
      const c = this.kbCursor;
      if (!c) return;
      if (c.kind === "group") {
        if (this.expandedKey === c.id) this.expandedKey = null;
        return;
      }
      if (c.kind === "show") {
        const i = this.expandedShows.indexOf(c.id);
        if (i >= 0) this.expandedShows.splice(i, 1);
        return;
      }
      if (c.kind === "ep" && this.expandedShowEp === c.id) this.expandedShowEp = null;
      if (c.kind !== "torrent") return;
      const p = this._kbParentRow(c);
      if (!p) return;
      if (p.kind === "group") this.expandedKey = null;
      else if (p.kind === "ep") this.expandedShowEp = null;
      const rows = this._kbRows();
      const idx = rows.findIndex((r) => r.kind === p.kind && r.id === p.id);
      if (idx >= 0) this._kbApplyCursor(rows, idx);
      else this.kbCursor = p;  // 理论不可达(父行恒在收起后的链上); 保守落光标, 不留悬空引用
    },
    _kbOpenRow() {
      const c = this.kbCursor;
      if (!c) {
        this._kbHint();
        return;
      }
      if (c.kind === "group" || c.kind === "show" || c.kind === "ep") {
        // 组行/剧行/集行: 展开明细(与鼠标左键同语义, 0822 B9); 已展开则收起
        const open = c.kind === "group" ? this.expandedKey === c.id
          : c.kind === "show" ? this.expandedShows.includes(c.id)
            : this.expandedShowEp === c.id;
        if (open) this._kbCollapseRow();
        else this._kbExpandRow();
        return;
      }
      // 种子行: 详情面板。D2 拍板(计划 26-10-03-0917 §05): 面板已开时 Enter 仅跟随不关面板 ——
      // openTorrentDrawer 即换目标打开(不走 close), 关面板只走 Esc 与关闭钮
      this.openTorrentDrawer(c.id);
    },
    /* Alt+1~5 双态(方案A W2, §2.2): 面板关 = 开面板并定位该页签; 面板开 = 切页签(现行为)。
     * "开态"只对种子形态(kind=seed)成立: 流量形态(全局/分组流量图, 26-10-05 三挂点并入抽屉)
     * 的抽屉 hash 恒空 —— 直接走切页签会把空 hash 打进 /api/torrents//trackers 等端点(404,
     * toast "tracker/peer 列表获取失败"), Alt+1 又因流量形态 tab 恒为 general 早退(按了没反应)。
     * 流量形态视同关态: 解析目标后 openTorrentDrawer 整体重建为种子形态并落在该页签。
     * 目标解析: 光标行(kind=torrent)优先, 其次单选种子(_kbSingleHash, 选中恰一个 hash);
     * 非主内容页(停靠落点 .drawer-dock 只存在于主内容页)或解析不出目标时 toast 提示后忽略 —— 不猜目标。
     * 2026-10-08(计划 26-10-08-1217): 视图守卫解除 —— 三视图共用面板, 辅种页/追剧页的成员行
     *   (光标 kind=torrent)直接命中目标解析, Alt+1~5 在三视图同样可用。
     * drawer 作用域条目已清空(§3.2), 四条改 list 作用域由此单点分流双态。 */
    async _kbDrawerTab(tab) {
      if (this.page !== "groups") {
        this.toast("页签不可用: 详情面板只在种子/辅种/追剧页可用", "info", 2500);
        return;
      }
      /* 合并页签态位次重排(2026-10-10 用户报「标签合并后没有同步修改快捷键」): 合并成功
       * (dtMergeTabsOn: 开关开 + 宽度门内, 页签栏只剩三张可见页签)时把注册表五档按位次重排到
       * 可见页签(1=常规&内容 / 2=Tracker&用户 / 3=流量, 4/5 停用); 未合并五档原样。必须先于流量
       * 门控 —— 第 3 档重排成 traffic 后仍要过 qbTrafficOn 门(未启用提示后忽略, 不切到隐形页签)。 */
      if (this._kbMergeTabsOn()) {
        const remapped = KB_MERGE_TAB_REMAP[tab];
        if (!remapped) return;  // 合并态无对应页签: 静默(键已消费, 无浏览器默认动作)
        tab = remapped;
      }
      // 流量页签受功能门控: 页签按钮 v-if=qbTrafficOn 不渲染, 切到隐形页签 = 卡在一个没有
      // 按钮可切回的页(与 openTorrentDrawer 的 initialTab 归一同一口径), 未启用时提示后忽略
      // issue 26-11-11-0633: flags 未取到先补拉一次再判(与 openQbHistory 同款"没取到≠没启用"
      // 口径); 方法改 async(调用方 shortcuts.js 全部 fire-and-forget, 返回值无人消费)
      if (tab === "traffic") {
        if (!this.qbTrafficOn && !this.flagsLoaded) await this.ensureWebFlags();
        if (!this.qbTrafficOn) {
          this.toast("功能未启用: qB 口径流量图, 请先在设置里打开", "info", 2500);
          return;
        }
      }
      if (this.drawer.open && this.drawerIsSeed) {
        this.drawerTab(tab);  // 开态: 切页签(现行为)
        return;
      }
      // 面板关着或开着流量形态: 都走"开面板并定位该页签"(流量形态由 openTorrentDrawer 换形)
      const c = this.kbCursor;
      const hash = c && c.kind === "torrent" ? c.id : this._kbSingleHash();
      if (!hash) {
        this._kbHint();
        return;
      }
      this.drawerLastTab = tab;      // openTorrentDrawer 以 drawerLastTab 为初始页签
      this.persistDrawerTab();       // 与 drawerTab 切页同口径(下一个种子默认停在相同页签)
      this.openTorrentDrawer(hash);
    },
    /* 合并页签态判据(2026-10-10): 直接消费详情面板模板核心层的 dtMergeTabsOn computed(开关开 +
     * 宽度门内, 与抽屉页签栏 v-if 同一判据), 未接线/无该 computed 时回落 false —— 不重排即回五档。 */
    _kbMergeTabsOn() {
      return !!this.dtMergeTabsOn;
    },
    /* ---------------- W2/W3: 选择与目标解析 ---------------- */
    _kbHint() {
      this.toast("先点选一行, 或用 上下方向键 / Home / End 定位目标(空列表无动作)", "info", 2500);
    },
    /* 追剧页与 _kbRows 同序的单元链(剧单元 + 展开的集单元), 供 _toggleUnit/_extendUnit */
    _kbShowUnits() {
      const out = [];
      for (const s of this.decoratedShows) {
        out.push({ id: "show|" + s.key, hashes: this._showHashes(s) });
        if (this.expandedShows.includes(s.key)) {
          for (const sn of s.seasons) {
            for (const e of sn.episodes) {
              out.push({ id: this.showEpRowId(s.key, sn.season, e.epKeyStr), hashes: this.memberHashesOf(e.members) });
            }
          }
        }
      }
      return out;
    },
    _kbUnitOf(c) {
      if (c.kind !== "show" && c.kind !== "ep") return null;
      const want = c.kind === "show" ? "show|" + c.id : c.id;
      return this._kbShowUnits().find((u) => u.id === want) || null;
    },
    _kbToggleSelect() {
      const c = this.kbCursor;
      if (!c) {
        this._kbHint();
        return;
      }
      if (c.kind === "group") {
        const g = this._findGroup(c.id);
        if (g) this.toggleGroupSel(g);
        return;
      }
      if (c.kind === "torrent") {
        this.toggleMemberSel({ hash: c.id });
        return;
      }
      this._toggleUnit(this._kbUnitOf(c));  // 剧/集单元: 整单元切换(与鼠标 Ctrl+点击同语义)
    },
    /* Shift 手势原点(计划 26-10-02-0608 W3; 2026-10-19 收编鼠标路径): 首次 Shift 扩展前, 若当前
     * 上下文没有有效起点, 以当前光标落起点。逐个 kind(group/member/unit)试落 —— 光标能解析成
     * 该 kind 的有效 id 且该 kind 起点缺失才落; 已有有效起点(点击 / Ctrl 点击 / 上次手势落定)
     * 一律不动 —— 保证"同一起点多次 Shift 扩展"(法则 2)。光标为 null 时不落, 由 _selAnchor
     * 最后兜底列表首行。
     * !辅种页成员行的光标只解析得出 member kind(_selContext 只回当前视图主 kind, 辅种页恒为
     *  group), 单 kind 落点覆盖不到它 —— 成员行 Shift 手势曾因此取不到原点(同根: 区间塌成单行)。
     * !调用方必须先调本方法、再动光标: 键盘 _kbExtend(在 _kbMove 之前)与鼠标五入口(在改写
     *  kbCursor 之前, selection.js)都是这个顺序 —— 先落光标再解析, _selAnchor 兜底链的
     *  「当前光标」一环读到的是新位置, 区间塌成单行(2026-10-19 报障: Shift 连选后 Esc 清选择,
     *  再次 Shift 连选不以光标为起点; 坑档 pitfalls/web-ui/overlays.md §起点)。 */
    _selSeedAnchorFromCursor() {
      if (this.page !== "groups") return;  // 仅数据页有选择上下文(设置页无列表)
      const ctxs = [
        { kind: "group", ids: this.filteredGroups.map((g) => g.key) },
        { kind: "member", ids: this._memberRangeList() },
        { kind: "unit", ids: this._kbShowUnits().map((u) => u.id) },
      ];
      for (const ctx of ctxs) {
        const field = this._selAnchorField(ctx.kind);
        if (ctx.ids.includes(this[field])) continue;              // 已有有效起点不动(法则 2)
        const fromCursor = this._selCursorId(ctx.kind);
        if (fromCursor !== null && ctx.ids.includes(fromCursor)) this[field] = fromCursor;  // 无有效起点 -> 落手势原点
      }
    },
    _kbExtend(delta) {
      this._selSeedAnchorFromCursor();  // 先落起点(手势原点), 再移动光标 —— 顺序不可换(否则区间塌成单行)
      this._kbMove(delta);  // 移动光标, 再把锚点到新光标整段并入选择(锚点语义沿用既有实现)
      const c = this.kbCursor;
      if (!c) return;
      if (c.kind === "group") {
        this.shiftGroupSel({ key: c.id });
        return;
      }
      if (c.kind === "torrent") {
        // 成员行的范围**随视图**取(单点 _memberRangeList): 种子页平铺 / 辅种页展开组 /
        // 追剧页展开集。此前一律 shiftTorrentSel(种子页平铺列表) —— 辅种/追剧页上该列表为空
        // 或与之无关, 于是成员行 Shift+up/down 选不中任何东西(2026-10-09 修)。
        this.shiftMemberSel({ hash: c.id });
        return;
      }
      const units = this._kbShowUnits();
      this._extendUnit(units.find((u) => u.id === (c.kind === "show" ? "show|" + c.id : c.id)), units);
    },
    _kbSelectAll() {
      if (this.viewMode === "torrents") {
        this.selGroups = [];
        this.selAnchorGroup = null;
        this.selMembers = this.filteredTorrents.map((m) => m.hash);
        this._selSyncGroups();  // 双向联动: 凑齐的辅种组随之入选(种子页无组数据 -> no-op)
        return;
      }
      if (this.viewMode === "shows") {
        const hashes = [];
        for (const u of this._kbShowUnits()) hashes.push(...u.hashes);
        this.selGroups = [];
        this.selAnchorGroup = null;
        this.selMembers = [...new Set(hashes)];
        this._selSyncGroups();  // 双向联动: 同上(追剧页无组数据 -> no-op)
        return;
      }
      // 辅种页: 全选所有组 —— 组入选 + 各组成员全选, 经同一写入口 _selAddGroup(双向联动)
      this.selMembers = [];
      this.selAnchorMember = null;
      this.selGroups = [];
      for (const g of this.filteredGroups) this._selAddGroup(g.key);
    },
    /* 目标解析: **薄投影**到作用域单点(计划 26-10-10-2001 S3, 契约 C1)。口径 = 有选中走选中
     * 集合, 无选中走光标行; 虚拟组行(未归组命中)无真实组 key, 转单种子命令。保留
     * `{groupKeys, memberHashes}` 形状是因为它是键盘族与 _actCore/_deleteFlow 的既有载荷形状,
     * 不是第二套口径 —— 语义与委托前逐位一致。 */
    _kbTargets() {
      const d = this._scopeResolve("sel-first-cursor");
      return { groupKeys: d.keys, memberHashes: d.hashes };
    },
    _kbTargetText(t) {
      const n = t.groupKeys.length + t.memberHashes.length;
      if (t.groupKeys.length === 1 && !t.memberHashes.length) return "整组";
      if (t.memberHashes.length === 1 && !t.groupKeys.length) return "该种子";
      return `${n} 个目标`;
    },
    /* ---------------- W4: 一级动作(危险档先确认; S3 起鼠标路径同文案确认, 计划 26-10-05-0314) ---------------- */
    async _kbAct(action) {
      const t = this._kbTargets();
      if (!t.groupKeys.length && !t.memberHashes.length) {
        this._kbHint();
        return;
      }
      const what = this._kbTargetText(t);
      if (action === "recheck") {
        /* 确认框文案与调用形态单点在 commands.js _recheckConfirm(S3 抽出共用), 本路径的
         * what 文案/时序/取消语义与抽出前逐位一致。 */
        const ok = await this._recheckConfirm(what);
        if (!ok) return;
      } else if (action === "reannounce") {
        /* 非活跃目标先拦(与右键/详情面板同一闸门): 早于确认框 —— 先问"确定?"再回"不行"是坏体感。
         * _actCore 里还有同一道兜底(键盘不是唯一入口), 这里前置只为省掉无谓的一问。 */
        if (!this._guardReannounce({ keys: t.groupKeys, hashes: t.memberHashes })) return;
        const ok = await this.confirmDialog("强制重新汇报",
          `将向 tracker 强制重新汇报${what}。频繁误触可能触发站点限流或警告。`, { okText: "确定" });
        if (!ok) return;
      }
      return this._actCore(action, { keys: t.groupKeys, hashes: t.memberHashes });
    },
    /* 删除: 与批量删除(bulkDelete)同一条 _deleteFlow 链(确认框 + HR 风险点名 + 汇报前置),
     * 键盘双入口之二(D8 默认键 Shift+D 与本 Delete 直连, 注册表外, §08 决策 v4)。 */
    async _kbDelete() {
      const t = this._kbTargets();
      if (!t.groupKeys.length && !t.memberHashes.length) {
        this._kbHint();
        return;
      }
      const parts = [];
      if (t.groupKeys.length) parts.push(`${t.groupKeys.length} 个${this.l10nGroup}`);
      if (t.memberHashes.length) parts.push(`${t.memberHashes.length} 个种子`);
      const countText = parts.join("、");
      const seen = new Set();  // 种子数(组展开去重)与批量删除同口径
      for (const k of t.groupKeys) {
        const g = this._findGroup(k);
        if (!g) continue;
        if (g.virtual) {
          if (g.members[0]) seen.add(g.members[0].hash);
        } else {
          for (const m of g.members || []) seen.add(m.hash);
        }
      }
      for (const h of t.memberHashes) seen.add(h);
      await this._deleteFlow({
        keys: t.groupKeys,
        hashes: t.memberHashes,
        title: `删除 ${countText}`,
        body: `将删除选中目标内的全部种子, 共 ${seen.size} 个。建议删除前先向 tracker 汇报, 避免留下未汇报的 H&R 记录。`,
        countText,
        label: countText,
      });
    },
    /* 详情面板 I(切换语义, 报告 26-10-09-1731 §04.2): 目标解析同旧(torrent 光标优先, group 光标取
     * 首成员); 已开着**同一目标**的种子详情形态 => closeDrawer(再按一下关); 换目标 / 面板关着 /
     * 开着流量形态 => 照旧 openTorrentDrawer 打开。与 Alt+1~5(有条件, 待定)分工: I 管面板整体开关,
     * Alt+N 管定位页签。 */
    _kbOpenDrawer() {
      if (!this.kbCursor) {
        this._kbHint();
        return;
      }
      /* 目标走作用域单点(S3/C1): 光标行 -> 单目标 hash(组光标取闭包首元, 与既有同口径;
       * 剧/集单元与多目标无单目标 -> 空串, 静默不动作) */
      const hash = this._scopeFirstHash(this._scopeResolve("cursor"));
      if (!hash) return;  // 无目标(组无成员 / 剧集单元等)静默不动作(与原实现同口径)
      if (this.drawer.open && this.drawerIsSeed && this.drawer.hash === hash) {
        this.closeDrawer();  // 已开同目标 => 关(切换语义; 换目标仍走下方打开)
        return;
      }
      this.openTorrentDrawer(hash);
    },
    /* ---------------- 2026-10-09: 切换语义(报告 26-10-09-1731 §03/§04) ----------------
     * 6 条「适合」条目由「只打开」升级为「开/关双态」: 再按一次同一键关掉自己打开的东西。
     * 关闭一律复用既有 closeX / closeDrawer(不新造状态); Esc 仍是唯一固定关闭出口, 两者不冲突。
     * **只改键盘 run 路径** —— 鼠标入口(状态栏按钮 / 右键菜单 / 双击)保持原语义(范围守恒)。 */
    /* 统计面板 \: 已开 => closeStats */
    _kbToggleStats() {
      if (this.statsOpen) {
        this.closeStats();
        return;
      }
      return this.openStats();
    },
    /* 历史流量 Shift+\: 已开 => closeHistory */
    _kbToggleHistory() {
      if (this.historyOpen) {
        this.closeHistory();
        return;
      }
      return this.openHistory();
    },
    /* 快捷键帮助 Shift+/: 已开 => closeKbHelp */
    _kbToggleKbHelp() {
      if (this.kbHelpOpen) {
        this.closeKbHelp();
        return;
      }
      this.kbOpenHelp();
    },
    /* qB 口径流量图 Ctrl+\: 已开着全局流量形态 => closeDrawer; 否则走 openQbHistory(含 qbTrafficOn
     * 门 + 未启用提示)。同目标 = 关, 未开/换形态仍走原打开语义。 */
    _kbToggleQbTraffic() {
      if (this.qbTrafficOn && this.drawer.open && this.drawerIsTraffic && this.drawer.scope === "global") {
        this.closeDrawer();
        return;
      }
      return this.openQbHistory();
    },
    /* 标签/分类(键盘): 目标走作用域单点(S3/C1) —— 有选中传 null = 整个选中集合(与批量动作同口径);
     * 无选中用光标行。虚拟行(未归组命中种子)没有真实组 key, 与原实现同口径**静默不动作**。 */
    _kbMeta() {
      if (this.selGroups.length || this.selMembers.length) {
        this.openMetaDialog(null);
        return;
      }
      const c = this.kbCursor;
      if (!c) {
        this._kbHint();
        return;
      }
      if (c.kind === "group") {
        const g = this._findGroup(c.id);
        if (!g || g.virtual) return;
      }
      const d = this._scopeResolve("cursor");
      if (d.keys.length === 1 && !d.hashes.length) {
        this.openMetaDialog({ groupKeys: d.keys, memberHashes: [] });
        return;
      }
      if (d.hashes.length) this.openMetaDialog({ groupKeys: [], memberHashes: d.hashes });
    },
    _kbOpenFolder() {
      const c = this.kbCursor;
      if (!c) {
        this._kbHint();
        return;
      }
      if (c.kind === "group") {
        const g = this._findGroup(c.id);
        if (g && !g.virtual) this.openTargetPath("group", c.id);
        return;
      }
      if (c.kind === "torrent") this.openTargetPath("torrent", c.id);
    },
    _kbFocusSearch() {
      const el = this.$refs.searchInput;
      if (el) {
        el.focus();
        el.select();
      }
    },
    /* ---------------- W5: 单目标动作的键盘目标解析 ----------------
     * E/F/I 组的编辑/复制/导出/队列族都是**单种子**动作(右键菜单只在单目标上提供):
     * 目标解析要求恰有一个 hash —— 多选/整组/剧集单元一律提示, 不猜第一个(静默错目标
     * 比不动作更糟)。选中集合走 _kbTargets 同一口径, 无选中用光标行。 */
    _kbSingleHash() {
      const d = this._scopeResolve("sel-first-cursor");
      if (d.keys.length || d.hashes.length !== 1) return "";
      return d.hashes[0];
    },
    /* 单目标编辑/复制族: 目标由作用域单点解析后**显式传参**。
     * !2026-10-10(S3/M3): 此前是 `this.menu.hash = h; this[fn]()` —— 把目标"塞进"菜单状态再让
     *   下游去读(机制 3, 见 conventions/webui-scope.md §3)。现改为显式传参, 被调方法一律以
     *   `(hash)` 或 `(arg, hash)` 收目标: editMove/editLimits/editShareLimits/editRename 收 (h),
     *   copyTorrentInfo 收 (field, h), exportTorrent 收 (h)。 */
    _kbEditAct(fn, arg) {
      const h = this._kbSingleHash();
      if (!h) {
        this._kbHint();
        return;
      }
      return arg === undefined ? this[fn](h) : this[fn](arg, h);
    },
    /* 单目标种子命令族(队列/TMM/强制启动/超级做种): 复用 torrentCmd 回执链(与右键菜单同链),
     * 目标显式传参(S3/M3, 同上)。 */
    _kbTorrentCmd(action, makeBody, okText) {
      const h = this._kbSingleHash();
      if (!h) {
        this._kbHint();
        return;
      }
      return this.torrentCmd(action, makeBody(), okText, h);
    },
    _kbTorrentToggle(action, field, label) {
      const h = this._kbSingleHash();
      if (!h) {
        this._kbHint();
        return;
      }
      const m = this.memberByHash.get(h) || {};
      return this.torrentCmd(action, { enable: !m[field] }, `${m[field] ? "关闭" : "开启"}${label}`, h);
    },
    /* 反选当前视图(空位动作, 默认不绑键): 三视图各自的全集做差; 组/成员双向联动(2026-10-09) */
    _kbInvertSel() {
      if (this.viewMode === "torrents") {
        const sel = new Set(this.selMembers);
        this.selGroups = [];
        this.selAnchorGroup = null;
        this.selMembers = this.filteredTorrents.map((m) => m.hash).filter((h) => !sel.has(h));
        this._selSyncGroups();  // 双向联动: 凑齐的辅种组随之入选(种子页无组数据 -> no-op)
        return;
      }
      if (this.viewMode === "shows") {
        const sel = new Set(this.selMembers);
        const all = new Set();
        for (const u of this._kbShowUnits()) for (const h of u.hashes) all.add(h);
        this.selGroups = [];
        this.selAnchorGroup = null;
        this.selMembers = [...all].filter((h) => !sel.has(h));
        this._selSyncGroups();  // 双向联动: 同上(追剧页无组数据 -> no-op)
        return;
      }
      const sel = new Set(this.selGroups);
      this.selMembers = [];
      this.selAnchorMember = null;
      this.selGroups = [];
      for (const g of this.filteredGroups) if (!sel.has(g.key)) this._selAddGroup(g.key);
    },
    /* ---------------- W6: 服务端键位装载 ----------------
     * startPolling 是两条鉴权放行路径(密钥验证/本机免鉴权)的唯一汇合点, 键位真值在那里拉;
     * 失败不阻塞主流程(默认表可用), 只提示。拉完/换稿后必须失效 _kbTableCache(引擎缓存)。 */
    async _kbReloadKeys(quiet = false) {
      const ok = await window.AQB_KEYS.reload(this.token);
      this._kbTableCache = null;
      this.kbKeysRev++;  // 键帽面重渲染通知(计划 26-11-12-0344 S3/S4, state.js kbKeysRev)
      if (!ok && !quiet) this.toast("快捷键配置加载失败, 已用默认键位", "warn");
      return ok;
    },
});
