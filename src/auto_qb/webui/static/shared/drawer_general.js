/* drawer_general.js — R4 大文件拆分(计划 26-11-02-2342 §07)
 * 详情抽屉 · 开关 / 页签 / 跟随滚动 / 面板几何与动画钩子。
 * 只搬方法定义, 实现逐行未改; 根文件已定义该域, 本片段在其后原地扩充(Object.assign)。
 * 加载序 = 四套皮肤 index.html 清单里紧跟根文件之后(与拆分前同一迭代替换序)。
 */
Object.assign(window.AQB_DRAWER.methods, {
    /* ---------------- 种子详情面板(R1B -> 方案A 底部停靠, 计划 26-10-03-0917 W1/W2) ----------------
     * 数据: /api/torrents/{hash} 全字段详情; /trackers /files /peers 按需拉取。
     * trackers/peers 在对应 tab 激活期间主节拍轮询(2026-10-14 改, =currentPollMs; 页面隐藏时暂停), 关闭面板即停 —— 不进主循环 tick;
     * General 分组行在 drawerGeneralSections 预格式化(qB 哨兵 -1/-2/8640000 在此统一翻译)。
     * 形态: 右缘浮层改为底部停靠面板(2026-10-04 起落点为 app 级 .drawer-dock, 可见性由 drawerVisible
     * 按形态把守) —— 无遮罩, open 只负责挂状态与拉数据; close 只收面板。
     * W2 键盘跟随: 光标移动经 shortcuts.js::_kbApplyCursor 尾部进 _kbFollowDrawer 单点(防抖 200ms
     * + 请求代际 seq + hash 短路, §2.3), 停稳后经 _switchDrawerTarget 换目标; 显式打开/关闭在此
     * 两处作废在途跟随定时器, 显式操作优先于跟随。 */
    async openTorrentDrawer(hash) {
      // 防御分支: 面板落点只存在于主内容页 —— 设置页没有 .drawer-dock。
      // 2026-10-08(计划 26-10-08-1217): 视图守卫解除 —— 种子页/辅种页/追剧页三视图共用面板,
      // 成员行(辅种页明细/追剧集明细)的右键「详细信息」与双击均落此入口。
      if (this.page !== "groups") return;
      this.menu.visible = false;
      // 惰性补拉(issue 26-11-11-0633): flags 未取到时补一发, 流量页签(页签按钮 v-if=qbTrafficOn
      // 门控)补拉成功后按响应式亮起; fire-and-forget 不阻塞开面板, 已取到/在途时零副作用
      this.ensureWebFlags();
      /* FX-29 家族纪律(2026-10-07 报障「切换种子时用户页闪'暂无已连接用户'」): 面板已开着(种子
       * 形态)不得再走下面的整体重建 —— 重建把 peers/trackers/files 清成空列表且 loading=false,
       * 详情在途的整个等待期被渲染成一帧空态(空态 -> 加载态 -> 数据三连闪; pitfalls/web-ui/
       * drawer-switch-flicker「拉新数据前先清空旧数据」—— 其中"高度自适应面板还会塌一下"那半,
       * 面板高度已于 2026-10-18 起恒锁(见 drawerPanelStyle), 不再随内容塌陷, 但内容三连闪仍在)。
       * 已开 = 有旧数据可保留, 归软切换语义: 换目标交棒 _switchDrawerTarget(保留旧数据 + 160ms
       * 延迟遮罩, 与键盘跟随同链路); 同目标重入零副作用(重建把旧数据连 loading 各闪一遍 —— 同坑档
       * 「打开入口的重入语义」, 与 openDrawerTraffic 同目标短路同口径)。 */
      if (this.drawer.open && this.drawerIsSeed) {
        if (this.drawer.hash === hash) return;  // 同目标重入: 短路(重建 = 对同一目标再闪一遍)
        this._switchDrawerTarget(hash);
        return;
      }
      this._stopDrawerPoll();
      this._stopDrawerFollow();  // 显式打开优先于在途跟随(双击换目标 vs 防抖中的跟随, 不得互相打架)
      this._drawerSwitchEnd();   // FX-29: 面板整体重建 -> 无"旧内容可保留", 待到集合与遮罩一并作废
      // 流量页签(S5b, plan 26-10-03-0946 §07 表2)受 qb_traffic_enabled 门控: 上次停在流量页签
      // 而功能后来关闭时落回常规页(页签按钮 v-if=qbTrafficOn 不渲染, 初值也不能落在隐形页签上)
      const last = this.drawerLastTab;
      const initialTab = last === "traffic" && !this.qbTrafficOn ? "general" : (last || "general");
      this._qbTeardown();  // 若上一形态是流量图(全局/分组), 换到种子详情时收轮询与图
      this.drawer = {
        open: true, hash, tab: initialTab, loading: true, error: "",
        detail: null, trackers: [], files: [], peers: { peers: [] },
        // 初值页签的 loading 与空列表同帧置位(26-10-07 报障的冷启动半边): 面板关着/流量形态换形
        // 才走重建, 无旧数据可保留 —— 详情在途窗口期非常规页签的空列表若以 loading=false 裸奔,
        // 会先渲染一帧空态(暂无已连接用户/暂无 tracker/无文件列表), 详情落袋后
        // _loadDrawerTab 才翻成加载态 -> 三连闪。翻转仍归 fetcher 落袋单点, 这里只保证
        // 等待期不落空态(W5 起无变体, 正文由 Vue 组件按 loading 态自渲染)。
        trackersLoading: initialTab === "trackers", filesLoading: initialTab === "content",
        peersLoading: initialTab === "peers",
        // P3-5(报告 26-10-07-0542): 三个列表 fetcher 的失败标记 —— 变体据此区分「失败」与
        // 「真没有」(失败只 toast 时变体把空列表当空态显示, 用户误以为数据真的为空)
        trackersError: "", filesError: "", peersError: "",
        switching: false,  // FX-29: 打开路径不存在"保留旧数据", 遮罩恒不亮(显式建字段见 vue-reactivity)
        kind: "seed", scope: "",
      };
      // 开场落定信号(FX-29 待到集合同机制): 登记详情 + 初值页签的数据源, 全到手 = 面板几何落定,
      // 届时补一发让位(挂单 _drawerOpenReveal 在 _drawerDone 兑现) —— 开场那次量的是 loading 态
      // 几何(面板随后长到 42vh), 文档底打开时 scrollBy 还会被钳制成 0(下滚余量是停靠槽位长高才
      // 创造的; 2026-10-04 回归取证)。流量页签高度恒定(drawerPanelStyle 定高), 不进集合。
      this._drawerWait = new Set(initialTab === "traffic" ? ["detail"] : this._drawerWaitSources(initialTab));
      this._drawerOpenReveal = hash;
      this.persistDrawerOpen();  // W3 开合态记录(D1: 只写不回读, 首屏恒默认关闭)
      this._kbRevealRow(hash);   // 显式打开也让位: 停靠面板一开就压住列表底部, 被点行(双击/右键/Enter)要露出来(2026-10-03 报障)
      await this._fetchDrawerDetail();  // 详情恒拉(头部标题/常规页都依赖); 非常规 tab 再补拉对应数据
      if (initialTab !== "general") this._loadDrawerTab(initialTab);
      // R2 S5: 合并 gc 对 + 初值常规页 —— _loadDrawerTab 不走(常规页只有详情), 文件列表在此补
      // 一发(无 seq 只走 hash 戳守卫, _drawerWait 里的 "files" 由其 _drawerDone 登记)
      else if (this.dtSplitOn && this._dtPairOf(initialTab) === "gc") this._fetchDrawerFiles();
    },
    /* 收面板: 无遮罩可关, 只做面板自身收尾(文件优先级小菜单/行选中; 轮询/软切换收口在数据层
     * drawer_store.js 的 _stopDrawerPoll/_drawerSwitchEnd —— W1 已把取数/竞态/等待集合剥出本文件);
     * drawer.open 跨页不清 —— 切页再回种子页面板状态保持(方案A W1 验收项) */
    closeDrawer() {
      // 槽位冻结 + 落定顶缘登记: leave 期面板转 absolute 出流, dock 会瞬间塌 0 —— 把用户可见高
      // 立即写回 dock 内联(同帧无跳变帧), 钩子(drawerLeaveHook)再从该高度收拢到 0; _drawerAnimTop
      // 供 _kbViewBottom 在收场动画期读落定值(此处 dock 还在全高帧, 是唯一可信测量点)
      const dock = document.querySelector(".drawer-dock");
      if (dock && !dock.classList.contains("drawer-anim")
          && !window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
        const h = Math.round(dock.getBoundingClientRect().height);
        if (h) {
          this._drawerAnimTop = this._drawerFinalTop(dock);
          dock.classList.add("drawer-anim");
          dock.style.height = h + "px";
        }
      }
      this.drawer.open = false;
      this.filePrio.visible = false;
      this.drawerMenu.visible = false;  // 抽屉右键菜单(R2 S3)随面板收
      this._stopDrawerPoll();
      this._stopDrawerFollow();
      this._dtUnmountAll();     // 插件实例逐个 destroy + 清宿主(W7 恢复; 本体 drawer_templates.js)
      this._drawerSwitchEnd();  // FX-29: 收面板即撤切换态(未完成的等待不得挂到下次打开)
      this._qbTeardown();       // 流量形态(全局/分组/单种)轮询与图一并收(2026-10-04 三挂点并入抽屉)
      this.persistDrawerOpen();  // W3 开合态记录(D1: 只写不回读)
    },
    /* tab 切换: general 重新拉详情(反映最新状态); trackers/peers 拉一次并启动轮询; content 拉一次。
     * 切换即记住该 tab(drawerLastTab + localStorage), 使下一个种子默认停在相同页签。 */
    drawerTab(tab) {
      if (this.drawer.tab === tab) return;
      this.drawer.tab = tab;
      this.drawerLastTab = tab;
      this.persistDrawerTab();
      this.filePrio.visible = false;  // 换页签时收起文件优先级小菜单(内容页签专属)
      this._drawerSwitchEnd();  // FX-29: 切页签使在途的那一组响应全部过期(stale 不落袋), 若不撤等待
      this._stopDrawerPoll();   //     遮罩会挂死 —— 显式操作视作结束上一次切换
      this._loadDrawerTab(tab);
    },
    /* ---------------- W2 详情跟随光标(计划 §2.3 四条纪律, 全部收口在此单点) ----------------
     * 触发入口: shortcuts.js::_kbApplyCursor 尾部(鼠标路径将来接同一入口, §1.3 相邻预留)。
     *   1) 触发单点+守卫 —— 面板开 + 主内容页 + 光标是种子行(kind=torrent); 辅种/追剧的
     *      组行/剧行/集行光标(kind=group/show/ep)不跟随(2026-10-08 起成员行光标 kind=torrent
     *      在辅种页/追剧页同样命中, 三视图一体化: 计划 26-10-08-1217);
     *   2) 防抖 200ms —— 连发上下键不逐行拉详情, 停稳才发;
     *   3) 在途请求代际 seq —— _loadDrawerTab 每次 bump, 换 hash 后旧响应一律丢弃(见上);
     *   4) hash 未变短路 —— 光标落回同一行不重拉; 页签内主节拍轮询(_startDrawerPoll)照旧, 互不打架。 */
    _kbFollowDrawer() {
      if (!this.drawer.open) return;
      if (this.page !== "groups") return;  // 主内容页守卫(面板停靠落点; 三视图共用)
      const c = this.kbCursor;
      if (!c || c.kind !== "torrent") return;  // kind 守卫(组行/剧/集单元不跟随)
      if (this.drawer.hash === c.id) return;   // 纪律4: hash 未变短路(含防抖在途的重复触发)
      if (this._followDrawerTimer) clearTimeout(this._followDrawerTimer);
      this._followDrawerTimer = setTimeout(() => {
        this._followDrawerTimer = null;
        // 停稳复核: 面板已关 / 切页走了 / 目标已换(显式打开优先) / 光标又落回原行 -> 放弃本次跟随
        if (!this.drawer.open || this.page !== "groups") return;
        const cur = this.kbCursor;
        if (!cur || cur.kind !== "torrent" || cur.id === this.drawer.hash) return;
        this._switchDrawerTarget(cur.id);
      }, 200);
    },
    _stopDrawerFollow() {
      if (this._followDrawerTimer) {
        clearTimeout(this._followDrawerTimer);
        this._followDrawerTimer = null;
      }
    },
    /* 头部标题: 优先主表成员名(memberByHash 每 1.5~3s 一轮已在本地, 切换瞬间即得) ——
     * 旧实现等详情到位, 中间一帧把标题显示成 40 字符 hash 再跳回种子名, 是肉眼最刺眼的一跳。 */
    drawerTitle() {
      const m = this.memberByHash.get(this.drawer.hash);
      if (m && m.name) return m.name;
      return this.drawer.detail ? this.drawer.detail.name : this.drawer.hash;
    },
    /* 持久化抽屉 tab 偏好(与 persistUiPage 同纪律): 只落"停在哪页"这个意图, 不落派生值;
     * 写入失败(隐私模式/配额满)只影响刷新后落点, 不该打断切页 —— 故吞掉异常。 */
    persistDrawerTab() {
      try {
        localStorage.setItem("autoqb.ui.drawerTab", this.drawerLastTab);
      } catch { /* 写入失败: 本轮仍生效, 刷新后回落默认 */ }
    },
    /* ---------------- W3 高度治理(计划 26-10-03-0917 §2.1/§3.5/D1) ----------------
     * 拖拽调高: 面板顶缘 .drawer-grip 的 pointer 事件(pointer capture, move 实时改高),
     * 夹取 [240px, 70vh]; 持久化: 高度与开合态进
     * localStorage(autoqb.ui.drawerHeight / autoqb.ui.drawerOpen, 与 drawerTab 同族口径)。
     * D1 拍板 = 首屏默认关闭 + 高度记忆仍生效: drawer.open 初值恒 false(state.js),
     * drawerOpen 键只作记录(写入不回读) —— 与「开合态记忆」字面有出入, 首屏满高优先(硬约束)。 */
    /* 夹取函数(纯逻辑, 守阵可锚): px 夹进 [240, 0.7*viewportH]。极小视口下 70vh<240 时
     * 取 70vh 为上界、下界随之取 min(240, 上界) —— 区间保持合法, 面板不越过 70vh 红线。 */
    _drawerClampHeight(px, viewportH) {
      const max = Math.round((viewportH || 0) * 0.7);
      const min = Math.min(240, max);
      return Math.round(Math.min(Math.max(px, min), Math.max(max, min)));  // 取整, 落盘值不带亚像素尾数
    },
    /* 面板内联样式: **展开即锁死高度**, height 与 max-height 同锁一个 px。
     * !2026-10-18(用户报障根治 · 硬约束): 面板高度**绝不随内容自行调整** —— 旧口径未拖拽过时
     * 返回 {} 走 CSS 内容自适应(无 height, max-height:42vh 只兜底), 详情正文里任何元素的
     * 进出场都会改变面板实高: 五区分组「握手中」组随握手连接消失/出现(每 5s 轮询都可能翻动)、
     * 组头计数涨落、摘要行显隐…… 用户所见即「详情面板高度自己跳」。用户裁定: 高度是用户调整的
     * 固定值(拖拽值 autoqb.ui.drawerHeight, 跨会话记忆), 未拖拽过也恒锁默认档 42vh(与 CSS
     * 默认上限同值, 视口跨刷新变同步夹取); 内容超高一律由 .drawer-body(overflow:auto)
     * 内部滚动消化, 面板几何全程不动。与种子详情共用同一 drawerHeightPx(高度复用);
     * 关闭态交给 CSS(面板不渲染); 窄屏全屏态 D3 由 CSS !important 压过(高度记忆失效)。 */
    drawerPanelStyle() {
      if (!this.drawer.open) return {};
      const px = this.drawerHeightPx || Math.round(window.innerHeight * 0.42);
      const h = this._drawerClampHeight(px, window.innerHeight);
      return { height: h + "px", maxHeight: h + "px" };
    },
    /* 顶缘拖拽(pointer capture 挂在 grip 元素上, move/up 都派发给它, 出窗不丢事件)。
     * !命名约束: 模板内联处理器不得用 `_` 前缀 —— Vue 3.5 运行时编译的模板解析不了
     * 下划线开头的裸标识符(ReferenceError), 本文件其余 `_` 方法只经 this.xx 调用故无恙。 */
    drawerGripDown(e) {
      if (!this.drawer.open) return;
      if (e.button !== undefined && e.button !== 0) return;    // 只认主键
      e.preventDefault();  // 防拖拽起手选中文本/触发滚动
      const panel = e.currentTarget.parentElement;  // grip 是 .drawer 的首子节点
      this._drawerDrag = { startY: e.clientY, startH: panel.getBoundingClientRect().height, pid: e.pointerId };
      e.currentTarget.setPointerCapture(e.pointerId);
      document.body.classList.add("drawer-resizing");
    },
    drawerGripMove(e) {
      const d = this._drawerDrag;
      if (!d || e.pointerId !== d.pid) return;
      if (!this.drawer.open) { this.drawerDragStop(); return; }  // 拖拽中面板被关(键盘路径)
      this.drawerHeightPx = this._drawerClampHeight(d.startH + (d.startY - e.clientY), window.innerHeight);
    },
    drawerGripUp(e) {
      const d = this._drawerDrag;
      if (!d || e.pointerId !== d.pid) return;
      this.drawerDragStop();
      this.persistDrawerHeight();  // 松手才落盘(拖拽过程不写 localStorage)
    },
    drawerDragStop() {
      this._drawerDrag = null;
      document.body.classList.remove("drawer-resizing");
    },
    persistDrawerHeight() {
      try {
        localStorage.setItem("autoqb.ui.drawerHeight", String(this.drawerHeightPx));
      } catch { /* 写入失败: 本轮仍生效, 刷新后回落默认 */ }
    },
    /* 开合态记录(D1): 展开=1, 关闭=0。只写不回读 —— 首屏恒默认关闭(硬约束), 键按计划创建 */
    persistDrawerOpen() {
      try {
        localStorage.setItem("autoqb.ui.drawerOpen", this.drawer.open ? "1" : "0");
      } catch { /* 写入失败: 不影响本轮 */ }
    },
    /* ---------------- 出入过渡(Vue <transition> JS 钩子, drawer.html 接线; 用户报"出现/消失很生硬") ----------------
     * 生硬根源: 停靠面板占据文档流, open 翻转时列表底部一帧被面板撑开/收回 —— 面板本体的
     * transform/opacity 滑淡(CSS .drawer-enter/leave-*)治不了布局跳变。修法 = 槽位插值:
     * enter 用 rAF 追赶循环把 .drawer-dock 高度 0 -> 面板实时高(每帧重量, 详情中途到达长高也跟),
     * leave 反向把面板自身高度收拢到 0, 而槽位(dock)整段冻结、末帧一次性收拢 —— W2(计划
     * 26-11-12-1048): 旧实现 dock 逐帧跟缴 = 文档逐帧变矮 = scrollY 逐帧钳制, 背景列表逐帧回弹。
     * enter 侧每帧写 height/margin, 不碰面板 :style 绑定, Vue 重渲染即便回写绑定值下一帧也被
     * 循环覆盖(自愈)。动画期 .drawer-anim 裁掉溢出,
     * 面板从底缘升起/收回; prefers-reduced-motion 与窄屏全屏态(D3, 面板 fixed 出流)不插值。
     * 几何登记: 插值期间 dock 顶缘是中间值, 让位量测(_kbRevealRow)不许读 —— enter 起拍把
     * "自然高时的 dock 顶缘"(即落定顶缘, sticky 钉底)登记进 _drawerAnimTop, _kbViewBottom
     * 单点优先消费; 收敛/超时/被打断一律清零。seq 代际闸: 快速开关往返时旧循环立即让位新拍。 */
    _drawerFinalTop(dock) {
      return Math.round(dock.getBoundingClientRect().top);
    },
    _drawerAnimStop() {
      if (this._drawerAnimRaf) {
        cancelAnimationFrame(this._drawerAnimRaf);
        this._drawerAnimRaf = 0;
      }
      const dock = document.querySelector(".drawer-dock.drawer-anim");
      if (dock) {
        dock.classList.remove("drawer-anim");
        dock.style.height = "";
        dock.style.marginTop = "";
      }
    },
    drawerEnterHook(el) {
      const dock = el.parentElement;  // 面板落点 = .drawer-dock(tpl-manifest 注入), aside 的父节点
      this._drawerAnimStop();
      this._drawerAnimSeq = (this._drawerAnimSeq || 0) + 1;
      if (!dock || window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
      const seq = this._drawerAnimSeq;
      // 重开打断收场: 被打断的 leave 已把内联高写在面板上, 清掉再量自然高(压成 0 会把自然高量成 0,
      // 整段动画失效); 槽位残局由 _drawerAnimStop 清理, 面板淡出中的视觉由 CSS enter 接管
      for (const old of dock.querySelectorAll(".drawer.drawer-leave-active")) old.style.height = "";
      dock.style.height = "";  // 量自然高(清残留内联)
      const h0 = dock.getBoundingClientRect().height;
      this._drawerAnimTop = h0 ? this._drawerFinalTop(dock) : 0;  // 自然高帧的顶缘 = 落定顶缘(sticky 钉底)
      if (!h0) return;  // 窄屏全屏态(D3, 面板 fixed 不占布局)或空内容: 无槽位可插值, 交回纯 CSS 滑淡
      const m0 = parseFloat(getComputedStyle(dock).marginTop) || 0;
      dock.classList.add("drawer-anim");
      dock.style.height = "0px";
      dock.style.marginTop = "0px";
      const t0 = performance.now();
      const step = () => {
        if (seq !== this._drawerAnimSeq) return;  // 被新开合打断: 新拍已接管 dock
        const target = el.getBoundingClientRect().height;  // 每帧追面板实时高(详情中途长高也跟)
        const cur = parseFloat(dock.style.height) || 0;
        const next = cur + (target - cur) * 0.45;
        if (Math.abs(target - next) < 1 || performance.now() - t0 > 400) {
          dock.style.height = "";  // 收敛: 回交自然高, 内容后续涨落不再经动画
          dock.style.marginTop = "";
          dock.classList.remove("drawer-anim");
          this._drawerAnimTop = 0;
          this._drawerAnimRaf = 0;
          return;
        }
        dock.style.height = next + "px";
        dock.style.marginTop = Math.min(m0, next * (m0 / h0)) + "px";  // 呼吸距随槽位同步长出
        // 落定顶缘逐帧重登记: 详情中途长高后, enter 起拍登记的 loading 态顶缘不再是落定值,
        // 让位量测(_kbRevealRow/键盘跟随)会按旧几何漏让(2026-10-04 回归取证)。dock sticky
        // 吸底期底缘恒定(margin-top 不参与吸底定位), 落定顶缘 = dock 底缘 - 面板自然高
        // (面板自身布局高不受 dock 槽位 overflow 裁剪, 即当前内容的落定高)。
        this._drawerAnimTop = Math.round(dock.getBoundingClientRect().bottom - target);
        this._drawerAnimRaf = requestAnimationFrame(step);
      };
      this._drawerAnimRaf = requestAnimationFrame(step);
    },
    drawerAfterEnterHook() {
      if (!this.drawer.open) return;  // 入场被快速关闭打断: 迟到的钩子不得杀掉 leave 拍的动画循环
      this._drawerAnimStop();  // 兜底: 追赶循环若仍在途(慢收敛)强制收场回自然高
      this._drawerAnimTop = 0;
      // 槽位落定后补一发让位: 文档底打开时开场让位被钳制成 0(下滚余量是停靠槽位长高才创造的,
      // 2026-10-04 取证), 此刻槽位已回自然高、余量足额, 且收场兜底强制回自然高后几何是实量值。
      // 流量形态无种子行可让, 不发。
      if (this.drawerIsSeed) this._kbRevealRow(this.drawer.hash);
    },
    drawerLeaveHook(el) {
      // closeDrawer 已冻结槽位(drawer-anim + 捕获高)时先取值再清理 —— 面板马上转 absolute 出流,
      // 之后 dock 的自然高就塌了, 量不回用户看到的最后一帧
      const frozenDock = document.querySelector(".drawer-dock.drawer-anim");
      const frozenH = frozenDock ? Math.round(frozenDock.getBoundingClientRect().height) : 0;
      this._drawerAnimStop();
      this._drawerAnimSeq = (this._drawerAnimSeq || 0) + 1;
      if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) { this._drawerAnimTop = 0; return; }
      if (getComputedStyle(el).position === "fixed") { this._drawerAnimTop = 0; return; }  // D3 窄屏全屏态: 面板出流, 无布局可插值
      const dock = el.parentElement;
      if (!dock) { this._drawerAnimTop = 0; return; }
      const seq = this._drawerAnimSeq;
      // 优先用 closeDrawer 捕获的用户可见高; 未捕获(入场中被打断, enter 已登记顶缘)退面板实高
      const h0 = frozenH || Math.round(el.getBoundingClientRect().height);
      if (!h0) { this._drawerAnimTop = 0; return; }  // 空内容: 无高度可收
      if (!frozenH && !this._drawerAnimTop) this._drawerAnimTop = this._drawerFinalTop(dock);
      const m0 = parseFloat(getComputedStyle(dock).marginTop) || 0;
      dock.classList.add("drawer-anim");
      /* W2(计划 26-11-12-1048 §02/D9): 槽位整段冻结 —— 高度与呼吸距各写一次, 收场动画期逐帧
       * 不动。dock 是流内 sticky 元素, 逐帧缩它 = 文档逐帧变矮 = 浏览器逐帧钳制 scrollY, 背景
       * 列表逐帧回弹(修复前真机逐帧取证: 收场位移事件 8~11 次, D11 判据 <=1)。高度插值只作用
       * 于已出流的面板(leave-active absolute 底缘锚定, 四皮肤成对、守阵钉住), 文档高全程恒定
       * —— 列表这才真正「只看到面板沉下去」。槽位在末帧一次性收拢(见 step 末尾): 文档底至多
       * 一次钳制, 属「结果变短后的一次性钳制」预期口径(dock-panel.md:118), 非文档底零钳制。 */
      dock.style.height = h0 + "px";     // 槽位冻结(closeDrawer 已写同值, 自捕获帧起整段保持)
      dock.style.marginTop = m0 + "px";  // 呼吸距一并冻结(它同样进文档高, 逐帧收回一样逐帧钳制)
      const t0 = performance.now();
      const step = () => {
        if (seq !== this._drawerAnimSeq) return;  // 重开接管: enter 拍清冻结残局后自起动画, 本循环自弃
        const t = Math.min(1, (performance.now() - t0) / 160);  // 收场 160ms = CSS 退场(.drawer-leave-active)同拍
        const k = t * t;  // easeInQuad: 收场加速(与退场滑淡 ease-in 同感)
        // 只收面板自身高度(面板已转 absolute 底缘锚定, 底边钉死向下收) —— 槽位冻结, 文档高与列表全程不动
        el.style.height = Math.max(0, Math.round(h0 * (1 - k))) + "px";
        if (t < 1) {
          this._drawerAnimRaf = requestAnimationFrame(step);
          return;
        }
        // 末帧一次性收拢槽位: 面板已收到 0(不可见), 文档此刻一次性变矮 —— scrollY 至多一次
        // 钳制(D11 位移事件 <=1)。height 回自然(面板出流, 自然高 0), 呼吸距一并缴 0 —— 二者
        // 是槽位文档占用的一体两面, 必须同帧 surrender(只缴高留 8px 边距, 重开时 enter 起拍
        // 清边距会在贴文档底时多钳一次)。afterLeave 清内联回 CSS 自然 8px = 文档长回 8px,
        // 恰好是重开 enter 起拍清边距要消费的余量(与逐帧缴旧机制同一稳态, 重开零位移)
        dock.style.height = "";
        dock.style.marginTop = "0px";
        this._drawerAnimRaf = 0;  // 面板节点随后被 Vue 摘除; dock 残留内联由 afterLeave 兜底清
      };
      this._drawerAnimRaf = requestAnimationFrame(step);
      this._drawerAnimDock = dock;  // afterLeave 时面板已出 DOM(parentElement 为 null), 提前留手
    },
    drawerAfterLeaveHook() {
      if (this.drawer.open) return;  // 收场被快速重开打断: 迟到的钩子不得杀掉 enter 拍的动画循环
      this._drawerAnimStop();  // 面板已出 DOM, 兜底清 dock 内联与在途循环
      const dock = this._drawerAnimDock;
      if (dock) {
        dock.classList.remove("drawer-anim");
        dock.style.height = "";
        dock.style.marginTop = "";
        this._drawerAnimDock = null;
      }
      this._drawerAnimTop = 0;
    },
});
