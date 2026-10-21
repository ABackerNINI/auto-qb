/* auto-qb WEB UI · 种子详情抽屉「数据/行为层」(计划 26-10-11-2106 W1)
 *
 * 本文件是抽屉**取数 / 竞态 / 等待集合 / 软切换序号**的唯一宿主 —— 与渲染无关的一层:
 * 不发 HTML、不碰 DOM、不知道变体或经典页的存在(渲染通知只经 this._dtNotify 钩子转交)。
 * 从 drawer.js 剥出(W1「数据层抽离, 零观感变化」), 方法体逐字未改 —— 只换了落点, 不换行为。
 *
 * !本文件在 HTML 里必须排在 drawer.js **之前**(同域阅读序: 数据层 -> 几何/交互 -> 模板核心)。
 *   与其它片段同范式挂 window.AQB_DRAWER_STORE, 由 app.js 末尾 app.mixin(...) 注入同一个 Vue
 *   实例 —— 方法体里的 this 仍是那个组件实例, 跨模块互调与拆分前完全等价。
 *
 * 归属契约(重建期不许越界):
 *   - 本层拥有: 四 fetcher 的具名入口(_fetchDrawerDetail|Trackers|Files|Peers)与其**唯一**取数
 *     骨架(_fetchDrawerSource)+ 差异项表(_DT_FETCH)(2026-10-21 R21-A-01 收敛: 落袋次序只此一份) ·
 *     请求代际序号
 *     (_drawerLoadSeq) 与竞态守卫(_drawerStale) · 软切换待到集合(_drawerWait/_drawerWaitSources/
 *     _drawerDone) · 遮罩延迟点亮(_drawerBusyArm/_drawerBusyDisarm/_drawerSwitchEnd) · 按页签取数
 *     单点(_loadDrawerTab) · 换目标软切换(_switchDrawerTarget) · 页签轮询(_startDrawerPoll/
 *     _stopDrawerPoll) · 合并双列数据补给(_drawerMergeSupply) · peers 键名适配(_drawerNormPeers) ·
 *     软切换窗口的列表 loading 门抑制(_drawerListLoadingOn, 2026-10-13 第九次闪烁复发)。
 *   - 本层不拥有(留在 drawer.js): 面板开合/几何/拖高/持久化(_drawerClampHeight, drawerGrip*,
 *     drawerPanelStyle, persistDrawer*) · 跟随挂点(_kbFollowDrawer/_stopDrawerFollow) · 出入手
 *     过渡钩子 · 派生列表(drawerFileRows/drawerPeerRows/drawerGeneralSections)。
 *
 * !跨模块登记成对纪律(本层存在的首要理由, R2 风险): 凡是进 _drawerWait 集合的源, 必须有人调
 *   _drawerDone 登记到手。四 fetcher 在各自 finally 里成对; 流量源是**跨模块**的(kb_traffic_chart.js
 *   的 _qbLoad 落袋处显式调 _drawerDone("traffic", hash, 0)), 与 _drawerWaitSources 的通用分支成对。
 *   拆掉任一边 = 软切换遮罩等一个永不到手的源, 永久挂死(2026-10-04 实测)。
 */
/* W5(计划 26-10-13-0811 L5「更新是写字段, 不是重建」): 三个列表数据源(trackers/files/peers)
 * 共用的引用稳定合并 —— 轮询/重拉到来时按行键对账: 旧行在 = **原对象写字段**(Object.assign,
 * Vue 3 同值不触发 → 未变行零重渲), 新行追加, 失踪行剔除; 数组恒按服务端序重建(顺序不承载
 * 语义, 与主循环 applyStateRows 同口径)。返回新数组实例(顶层引用变更保证 Vue 感知), 但行
 * 对象生命周期内引用稳定 → keyed 补丁下行 DOM 身份恒定(速度格原节点续用, 勾选不跳动)。
 * 行键单点: trackers=url / files=index(缺则 name) / peers=ip:port —— 与各表 rowKey 口径一致。 */
function _dtMergeRows(oldRows, newRows, keyOf) {
  if (!Array.isArray(newRows)) return [];
  if (!Array.isArray(oldRows) || !oldRows.length) return newRows;  // 首轮: 直接用新数组
  const oldByKey = new Map();
  for (const r of oldRows) oldByKey.set(keyOf(r), r);
  const out = [];
  const seen = new Set();
  for (const nw of newRows) {
    const k = keyOf(nw);
    seen.add(k);
    const old = oldByKey.get(k);
    if (old !== undefined) { Object.assign(old, nw); out.push(old); }
    else out.push(nw);
  }
  return out;
}

/* 四数据源差异项表 —— 全仓唯一一处(R21-A-01, 2026-10-21 收敛):
 *   端点 url(hash) · 归一 norm(vm, r) · 目标状态键 key · 空值形状 rows + pack
 * 外加三条结构性差异(loading 门字段 / 失败标记与提示 / 通知时机)。落袋与竞态的**次序**不在这里,
 * 只在 _fetchDrawerSource 一份 —— 任何地方再写第二份次序, stale/notify/done 的三步先后就会重新分裂,
 * 而这类颠倒不报错、只静默变成用户可见故障(见该骨架头注三条)。守阵
 * tests/test_webui_static_dom_panel.py::test_drawer_fetcher_skeleton_single_point 拦。
 *   url         端点(带 hash 拼装)
 *   key         drawer 上的目标状态键
 *   norm(vm,r)  归一: 取载荷 / 键名适配(peers) / 恒数组形; 返回值即本轮的行或值
 *   rowKey      行键(trackers=url / files=index(缺则 name) / peers=ip:port, 与各表 rowKey 同口径);
 *               null = 不合并, 整值落袋(详情)
 *   rows(old)   从目标状态键取旧行 —— 空值形状在此: 无旧值或形不对 => 空数组
 *   pack(rows)  行数组写回目标状态键 —— peers 多包一层 { peers }
 *   loadingKey  列表 loading 门字段; null = 详情(走 drawer.loading, 不经门抑制单点)
 *   errKey      失败标记字段; null = 详情(落 drawer.error)
 *   toastText   失败提示前缀; null = 不提示(详情失败由 error 态表达)
 *   failText    无 e.message 时的兜底文案
 *   absentText  载荷为空时的 error 文案(只有详情有: /api/torrents/{hash} 查无此种子)
 *   notifyAtLand true = 落袋即通知(详情: 变体不渲染 loading 态); false = 清 loading 之后通知 */
const _DT_FETCH = {
  detail: {
    url: (hash) => `/api/torrents/${hash}`,
    key: "detail",
    norm: (vm, r) => (r && r.torrent) || null,
    rowKey: null,
    loadingKey: null,
    errKey: null,
    toastText: null,
    failText: "详情获取失败",
    absentText: "种子不存在或已被删除",
    notifyAtLand: true,
  },
  trackers: {
    url: (hash) => `/api/torrents/${hash}/trackers`,
    key: "trackers",
    norm: (vm, r) => (Array.isArray(r) ? r : []),
    rowKey: (t) => String(t && t.url || ""),
    rows: (old) => (Array.isArray(old) ? old : []),
    pack: (rows) => rows,
    loadingKey: "trackersLoading",
    errKey: "trackersError",
    toastText: "tracker 列表获取失败: ",
    failText: "tracker 列表获取失败",
    notifyAtLand: false,
  },
  files: {
    url: (hash) => `/api/torrents/${hash}/files`,
    key: "files",
    norm: (vm, r) => (Array.isArray(r) ? r : []),
    rowKey: (f) => String(f && f.index !== undefined ? f.index : (f && f.name) || ""),
    rows: (old) => (Array.isArray(old) ? old : []),
    pack: (rows) => rows,
    loadingKey: "filesLoading",
    errKey: "filesError",
    toastText: "文件列表获取失败: ",
    failText: "文件列表获取失败",
    notifyAtLand: false,
  },
  peers: {
    url: (hash) => `/api/torrents/${hash}/peers`,
    key: "peers",
    /* 归一: 键名适配单点(vm._drawerNormPeers, 补 dlspeed / upspeed) + dict/数组恒归数组形 */
    norm: (vm, r) => {
      const norm = vm._drawerNormPeers(r);
      return Array.isArray(norm.peers) ? norm.peers : Object.values(norm.peers || {});
    },
    rowKey: (x) => String((x && x.ip || "?") + ":" + ((x && x.port) || "")),
    rows: (old) => (Array.isArray(old && old.peers) ? old.peers : []),
    pack: (rows) => ({ peers: rows }),
    loadingKey: "peersLoading",
    errKey: "peersError",
    toastText: "peer 列表获取失败: ",
    failText: "peer 列表获取失败",
    notifyAtLand: false,
  },
};

window.AQB_DRAWER_STORE = {
  methods: {
    /* R2 S5: 合并开启/门跨越后的第二列数据补给(核心层 drawerMerge $watch 与 resize 回调共用;
     * 插件禁触碰取数/轮询纪律不破)。按生效对把缺失的数据源补齐: 已有数据/在途不重发(避免
     * 开关抽屉反复打请求), fetcher 自带静默/loading/stale 丢弃。seq 只 bump 一次走代际守卫。 */
    _drawerMergeSupply() {
      if (!this.drawer.open || !this.dtSplitOn) return;
      const pair = this._dtPairOf(this.drawer.tab);
      if (!pair) return;
      const seq = (this._drawerLoadSeq = (this._drawerLoadSeq || 0) + 1);
      if (pair === "gc") {
        if (!this.drawer.files.length && !this.drawer.filesLoading) this._fetchDrawerFiles(false, seq);
        if (!this.drawer.detail && !this.drawer.loading) this._fetchDrawerDetail();
      } else if (pair === "tp") {
        if (!this.drawer.trackers.length && !this.drawer.trackersLoading) this._fetchDrawerTrackers(false, seq);
        if (!this.drawerPeerRows().length && !this.drawer.peersLoading) this._fetchDrawerPeers(false, seq);
        this._startDrawerPoll();
      }
    },
    _stopDrawerPoll() {
      if (this._drawerTimer) {
        clearInterval(this._drawerTimer);
        this._drawerTimer = null;
      }
      // !本方法**不清** _drawerSoftSwitch: 它会在 _switchDrawerTarget→_loadDrawerTab→_startDrawerPoll
      // 途中被调用, 而列表 loading 门抑制必须在同一次 _loadDrawerTab 的 fetcher 里已生效(见
      // _drawerListLoadingOn); 该标记只在 _drawerSwitchEnd 落定/被打断时清。
      // 流量页签(S5b)的低频轮询同收: 本方法是抽屉页签轮询的收口单点(closeDrawer/drawerTab/
      // _switchDrawerTarget/openTorrentDrawer 全走这里), 页签切走/换目标/关面板即停 —— 若新页签
      // 仍是流量, _loadDrawerTab 会重新起(_qbPollStart 自带先停后起)
      this._qbPollStop("torrent");
    },
    _startDrawerPoll() {
      this._stopDrawerPoll();
      // 2026-10-14(用户报「详情面板用户页实时速度刷新率太低」): 5s 固定 → 主节拍 currentPollMs()
      // (种子页刷新间隔, 按种子量分档 1.5/2/3s) —— 实时速度与行数据同频观。旧 P1-4 把 5s 省 qB
      // 直连成本但把速度滞后直接卖掉, 用户口径是同频; 服务端 peers 短缓存(1s)窗口仍窗口外,
      // trackers 默认 2s 缓存把 1.5s 档里的白拉吸收。失败退背随 currentPollMs 同主轮退背。
      this._drawerTimer = setInterval(() => {
        if (!this.drawer.open || document.hidden) return;
        // W4 停靠化收口(计划 26-10-03-0917 前波移交观察项): 面板 DOM 随主内容页 v-if 出入,
        // 切走页面(设置页)后 drawer.open 仍为 true(回页状态保持语义), 旧浮层形态的轮询会继续对
        // 隐藏面板打 trackers/peers —— 不可见即跳过(定时器不拆, 回主内容页下一拍自动恢复)。
        // 2026-10-08(计划 26-10-08-1217): 视图守卫解除 —— 三视图(种子/辅种/追剧)共用面板,
        // 在辅种页/追剧页展开的面板同样要续拉; 只挡非主内容页。
        if (this.page !== "groups") return;
        // R2 S5: 合并 tp 对生效时双源同频(负载 = 用户页签单用时, 无新增频次)
        if (this.dtSplitOn && this._dtPairOf(this.drawer.tab) === "tp") {
          this._fetchDrawerTrackers(true);
          this._fetchDrawerPeers(true);
          return;
        }
        if (this.drawer.tab === "trackers") this._fetchDrawerTrackers(true);
        else if (this.drawer.tab === "peers") this._fetchDrawerPeers(true);
      }, this.currentPollMs());
    },
    /* W2 请求代际纪律: 四个 fetcher 均带可选 seq(0 = 无代际约束, 走 hash 戳守卫) ——
     * 换 hash(跟随/显式打开)或换代际(切页签)后, 在途旧响应一律丢弃, 防止慢响应把新目标的
     * 详情/列表覆盖成旧的。hash 戳另兜一路: 抽屉轮询(seq=0)发出后恰逢跟随换目标, 响应也不落袋。 */
    _drawerStale(hash, seq) {
      return this.drawer.hash !== hash || (!!seq && seq !== this._drawerLoadSeq);
    },
    /* ---------------- 四 fetcher 的唯一取数骨架(R21-A-01, 2026-10-21 收敛) ----------------
     * 落袋次序是有心之作, 原先在 detail/trackers/files/peers 里各写一遍(每份 ~22 行, 全层 13 个
     * _drawerStale 判点): hash 快照 -> ① 前置门 -> try{api} -> ② stale 守卫 -> ③ 归一 + 引用稳定
     * 合并 -> 清失败标记 -> catch{失败提示 / stale 守卫 / 落失败标记} -> finally{stale 守卫
     * -> 清 loading -> _dtNotify -> _drawerDone}。
     * 次序颠倒不报错, 只静默变成用户可见故障, 所以只留这一份:
     *   - ③ 之前不判 stale = 旧响应覆盖新目标(W2);
     *   - 列表源 _dtNotify 早于清 loading = 空列表停「正在加载…」一拍轮询(2026-10-07 报障);
     *   - 漏 _drawerDone = FX-29 遮罩等一个永不到手的源, 永久挂死(2026-10-04 实测)。
     * 差异项全部外置在 _DT_FETCH 表, 本方法不认识任何具体数据源。 */
    async _fetchDrawerSource(src, silent = false, seq = 0) {
      const cfg = _DT_FETCH[src];
      const hash = this.drawer.hash;
      // ① 前置门: 列表源走门抑制单点(软切换窗口内不置门, 见 _drawerListLoadingOn); 详情源没有
      //    「上一目标留下的空态」要保, 恒置 loading 并清 error(它不参与轮询, 无静默路径)。
      if (cfg.loadingKey) {
        if (this._drawerListLoadingOn(silent)) this.drawer[cfg.loadingKey] = true;
      } else {
        this.drawer.loading = true;
        this.drawer.error = "";
      }
      try {
        const r = await this.api(cfg.url(hash));
        if (this._drawerStale(hash, seq)) return;  // ② 旧响应丢弃(W2 代际纪律)
        /* ③ 落袋三步: 归一(qB 键名适配 / 恒数组形) -> 按行键引用稳定合并(W5: 写字段不重建, 行
         * DOM 身份恒定) -> 写目标状态键。详情源 rowKey 为 null, 整值落袋。 */
        const v = cfg.norm(this, r);
        this.drawer[cfg.key] = cfg.rowKey
          ? cfg.pack(_dtMergeRows(cfg.rows(this.drawer[cfg.key]), v, cfg.rowKey))
          : v;
        if (cfg.errKey) this.drawer[cfg.errKey] = "";  // 成功落袋即清失败标记(上一次失败不影响本轮展示)
        else if (!v) this.drawer.error = cfg.absentText;  // 详情 404 语义: 载荷为空不是"没拉到"
        // 详情落袋即通知(W7 恢复, 模板核心层计划 26-10-06-0838 S1); 列表源见 finally
        if (cfg.notifyAtLand) this._dtNotify(src);
      } catch (e) {
        // 失败提示不看 stale: 用户发起的请求失败就该说一声(详情源 toastText 为 null, 由 error 态表达)
        if (cfg.toastText && !silent && !e.auth) this.toast(cfg.toastText + e.message, "error");
        // P3-5: 失败标记落 state(过期响应不动它, 属于在途的新目标); 抽屉轮询期(silent)也落,
        // 否则静默失败变体永远停在空态
        if (this._drawerStale(hash, seq)) return;
        if (cfg.errKey) this.drawer[cfg.errKey] = e.message || cfg.failText;
        else if (!e.auth) this.drawer.error = e.message || cfg.failText;
      } finally {
        // 过期请求不动 loading 态(新在途请求持有它), 免得闪一帧"加载完"假象
        if (!this._drawerStale(hash, seq)) {
          if (cfg.loadingKey) {
            this.drawer[cfg.loadingKey] = false;
            // W7 恢复: 列表源的通知必须在 loading 清掉之后 —— 变体只在 _dtNotify 时重渲染,
            // 通知先于清门 = 空列表停在「正在加载…」到下一拍轮询(2026-10-07 用户页报障)
            if (!cfg.notifyAtLand) this._dtNotify(src);
          } else {
            this.drawer.loading = false;
          }
        }
        this._drawerDone(src, hash, seq);  // FX-29: 落定登记(该数据源已到手)
      }
    },
    /* 四个具名入口 = 骨架的薄壳: 名字是调用点/守阵/跨模块登记认的接口, 差异全在 _DT_FETCH 表。
     * 这里(以及任何新数据源)都不许再写第二份落地次序 —— 见 _fetchDrawerSource 头注。 */
    async _fetchDrawerDetail(seq = 0) {
      return this._fetchDrawerSource("detail", false, seq);
    },
    async _fetchDrawerTrackers(silent = false, seq = 0) {
      return this._fetchDrawerSource("trackers", silent, seq);
    },
    async _fetchDrawerFiles(silent = false, seq = 0) {
      return this._fetchDrawerSource("files", silent, seq);
    },
    async _fetchDrawerPeers(silent = false, seq = 0) {
      return this._fetchDrawerSource("peers", silent, seq);
    },
    /* 按 tab 拉取对应数据(开抽屉初值 / 切 tab / W2 跟随换目标共用, 单一加载逻辑):
     * 每次进入 bump 请求代际 seq —— 之后所有带 seq 的在途响应过期, 换目标/换页签竞态在此收口。 */
    _loadDrawerTab(tab) {
      const seq = (this._drawerLoadSeq = (this._drawerLoadSeq || 0) + 1);
      if (tab === "general") this._fetchDrawerDetail(seq);
      else if (tab === "trackers") {
        this._fetchDrawerTrackers(false, seq);
        this._startDrawerPoll();
      } else if (tab === "peers") {
        this._fetchDrawerPeers(false, seq);
        this._startDrawerPoll();
      } else if (tab === "content") this._fetchDrawerFiles(false, seq);
      // 流量页签(S5b, plan 26-10-03-0946 §07 表②): 数据源 /api/traffic/qb/torrent/{hash};
      // 打开时拉取一次 + 打开期间按采样间隔低频续拉(qb_traffic_chart.js _qbPollStart,
      // meta.interval_s 取间隔), 关抽屉/切页签/换目标由 _stopDrawerPoll 统一收 ——
      // hash 上下文竞态(换目标后旧响应)在 _qbLoad 的 stale 判定里丢弃
      else if (tab === "traffic" && this.qbTrafficOn) {
        this._qbLoad("torrent");
        this._qbPollStart("torrent");
      }
      // R2 S5(计划 26-10-09-2219): 合并生效时第二列的数据供给也在此收口(插件禁触碰取数/轮询
      // 纪律不破) —— gc 对补 detail+files, tp 对补 trackers+peers(带 seq 走代际守卫, 详情走
      // hash 戳守卫, 与 _switchDrawerTarget 同式)。门内才供给: 影子期零额外请求。
      if (this.dtSplitOn) {
        const pair = this._dtPairOf(tab);
        if (pair === "gc") {
          if (tab !== "general") this._fetchDrawerDetail();
          if (tab !== "content") this._fetchDrawerFiles(false, seq);
        } else if (pair === "tp") {
          if (tab !== "trackers") this._fetchDrawerTrackers(false, seq);
          if (tab !== "peers") this._fetchDrawerPeers(false, seq);
          if (tab !== "trackers" && tab !== "peers") this._startDrawerPoll();
        }
      }
      this._dtSync();  // 换页签重挂(W7 恢复): 卸旧全部实例, 挂当前页签主列 + 合并次列
    },
    /* ---------------- FX-29 换目标: 软切换(治「上下键切换种子时抽屉闪烁」, 26-10-03) ----------------
     * 旧实现把 detail / trackers / files / peers 一把清空再重拉, 面板每一次光标移动都走一遍
     * 「整幅内容消失 -> 落到加载空态 -> 数据回来重建」, 连按上下键时就是持续闪烁; 且未拖过高的
     * 面板只有 CSS 42vh 上限(高度随内容), 空态把面板抽成一条再撑开, 列表与停靠面板连锁跳动。
     * 软切换 = 保留旧数据撑住几何, 用 **遮罩** 而不是清空来防串显: 内容此刻属于上个种子, 罩住
     * 即不可读(并屏蔽交互), 新数据全部到手才掀开 —— 「看着上个种子的值」不会成立, 但面板几何
     * 全程不动, 用户眼里只有内容换了一帧。落定按「数据源集合」而不是「任一请求」: 早到的单个请求
     * 不许提前掀罩(那时另一个源还是上个种子的值), 故按 tab 登记待到集合, 全部到手才算落定。 */
    _switchDrawerTarget(hash) {
      this._stopDrawerPoll();
      this._stopDrawerFollow();
      this.drawer.hash = hash;
      this.drawer.loading = true;
      this.drawer.error = "";
      // P3-5: 三个列表失败标记同 error 口径作废(属于上一个目标, 新目标由 fetcher 重新落)
      this.drawer.trackersError = this.drawer.filesError = this.drawer.peersError = "";
      this._drawerWait = new Set(this._drawerWaitSources(this.drawer.tab));
      this._drawerBusyArm();   // 延迟点亮遮罩(快响应时用户看不到任何中间态)
      this.filePrio.visible = false;  // 内容页签小菜单跨种子失效(与 drawerTab/closeDrawer 同口径)
      /* FX-29 软切换标记(第九次形态, 见 _drawerListLoadingOn): 本次换目标保留**上一个目标的已落袋
       * 结果**(其中"空列表"= 没有对端/没有 tracker, 是种子的**常态**) ⇒ 期间三个列表 fetcher
       * 不置 loading 门 —— 否则模板门 `loading && 无行` 会把这份常态空态顶掉一帧换成「正在加载…」,
       * 数据回来再换回 = 用户所报「切换种子时『暂无已连接用户』闪烁」(逐帧实测 `E→L→E`)。
       * !必须在 _loadDrawerTab **之前**置位: 三 fetcher 在 _loadDrawerTab 内、await 之前**同步**读它;
       *   而本方法开头的 _stopDrawerPoll **不清**本标记(见其注释), 故置位不会被其内的
       *   _startDrawerPoll→_stopDrawerPoll 抹掉(这一点与旧宽限标记相反)。落定/被打断由
       *   _drawerSwitchEnd 清。 */
      this._drawerSoftSwitch = true;
      this._loadDrawerTab(this.drawer.tab);
      // 详情恒拉(头部标题/常规页都依赖, 与 openTorrentDrawer 同口径): _loadDrawerTab 只在 general
      // 页签拉详情, 其余页签在此补一发 —— seq 归 _loadDrawerTab 先 bump(页签数据走代际守卫),
      // 详情这次不带 seq 只走 hash 戳守卫(同 hash 内晚到也是同资源, 无覆盖错目标风险)。
      if (this.drawer.tab !== "general") this._fetchDrawerDetail();
    },
    /* 本次切换要等的数据源(tab -> 「详情 + 该 tab 列表」); 常规页签只有详情一项。
     * R2 S5(计划 26-10-09-2219): 合并生效时按**生效对**扩展 —— gc 对等 detail+files,
     * tp 对等 detail+trackers+peers(遮罩等全对数据源齐再掀, 不掀半新半旧)。
     * 通用分支 `["detail", tab]` 覆盖 traffic: 流量源由 qb_traffic_chart.js _qbLoad 落袋处
     * 显式 _drawerDone("traffic") 登记 —— 跨模块成对, 拆任一边遮罩挂死(本层头注)。 */
    _drawerWaitSources(tab) {
      if (this.dtSplitOn) {
        const pair = this._dtPairOf(tab);
        if (pair === "gc") return ["detail", "files"];
        if (pair === "tp") return ["detail", "trackers", "peers"];
      }
      if (tab === "general") return ["detail"];
      if (tab === "content") return ["detail", "files"];
      return ["detail", tab];
    },
    /* 单个数据源到手(成功或失败都算到手 —— 失败要让 error 态显出来, 不能把遮罩挂死)。
     * 过期响应不登记: 它的数据没落袋, 状态仍属于在途的新目标。 */
    _drawerDone(src, hash, seq) {
      const w = this._drawerWait;
      if (!w || this._drawerStale(hash, seq)) return;
      w.delete(src);
      if (w.size) return;      // 还有兄弟源在飞 —— 不提前掀罩(防半新半旧)
      this._drawerSwitchEnd();
      if (this._drawerOpenReveal) {  // 开场路径的落定补让位(挂单见 openTorrentDrawer; 切换路径无挂单)
        const h = this._drawerOpenReveal;
        this._drawerOpenReveal = "";
        // 双守卫防迟到兑现: 挂单后被打断(关闭/换目标)时 drawer.open/hash 已易主, 那是别的种子几何
        if (this.drawer.open && this.drawer.hash === h) this._kbRevealRow(h);
      }
    },
    /* 遮罩延迟点亮: 局域网详情常在 100ms 内就到 —— 那一刻用户看到的是「内容直接换成新的」,
     * 中间没有任何一帧变淡; 只有真的慢下来(>160ms)才滑入加载胶囊并把旧值淡到不可读。 */
    _drawerBusyArm() {
      this._drawerBusyDisarm();
      this._busyArmTimer = setTimeout(() => {
        this._busyArmTimer = null;
        if (this.drawer.open) this.drawer.switching = true;
      }, 160);
    },
    _drawerBusyDisarm() {
      if (this._busyArmTimer) {
        clearTimeout(this._busyArmTimer);
        this._busyArmTimer = null;
      }
    },
    /* 切换期收尾: 撤待到集合 / 撤延迟 / 撤遮罩(closeDrawer 与中途打断同样走这里) */
    _drawerSwitchEnd() {
      this._drawerWait = null;
      this._drawerSoftSwitch = false;  // 软切换结束 ⇒ 列表 loading 门恢复(见 _drawerListLoadingOn)
      this._drawerBusyDisarm();
      this.drawer.switching = false;
    },
    /* qB sync/torrentPeers 的对端速度字段是 dl_speed / up_speed(qB 原始命名), 与列表侧
     * torrents/info 的 dlspeed / upspeed **不同名** —— 抽屉 peers 的全部消费点(经典表经
     * drawerPeerRows, 变体 07/08/09 的 peerList 直读原始对端对象)统一按 dlspeed / upspeed
     * 取名, 故在落袋单点(_fetchDrawerPeers)做一次键名适配: 补 dlspeed / upspeed(保留原键,
     * 其余字段 dl_speed 系的 downloaded/uploaded/flags/progress/relevance 本就同名无需动)。
     * 漏这一步的症状 = 用户页上下载恒 0(取不到值 → 0), 而桩服务若也按错名造数据则测不出来。 */
    _drawerNormPeers(resp) {
      const r = resp && typeof resp === "object" ? resp : { peers: [] };
      const fix = (x) => {
        if (!x || typeof x !== "object") return x;
        if (x.dlspeed === undefined && x.dl_speed !== undefined) x.dlspeed = x.dl_speed;
        if (x.upspeed === undefined && x.up_speed !== undefined) x.upspeed = x.up_speed;
        return x;
      };
      if (Array.isArray(r.peers)) r.peers = r.peers.map(fix);
      else if (r.peers && typeof r.peers === "object")
        r.peers = Object.fromEntries(Object.entries(r.peers).map(([k, v]) => [k, fix(v)]));
      return r;
    },
    /* ---------------- FX-29 软切换: 列表 loading 门抑制(治「切换种子时用户页闪『暂无已连接用户』」) -------
     * 病根(2026-10-13 用户报障, 坑档 pitfalls/web-ui/drawer-switch-flicker.md 第九次形态): 软切换
     * 「保留旧数据撑几何 + 遮罩防串显」保留的是**上一个目标的已落袋结果** —— 而**空列表(没有对端/
     * 没有 tracker)是种子的常态**, 这份"已落袋的空"同样在屏上。但三个列表 fetcher 一律 `loading = true`,
     * 模板门 `loading && !行数` 就把这份既有的空态顶掉一帧换成「正在加载…」, 数据(空)回来再换回 ——
     * 用户看到的就是「『暂无已连接用户』闪烁」。逐帧实测(临时探针, 已删): 全空桩下软切换序列 = `E→L→E`
     * (E=空态 / L=加载门), 即本坑。
     * 修法: 换目标窗口(`_drawerSoftSwitch`, 由 _switchDrawerTarget 于 _loadDrawerTab **之前**置位)内
     * **不置**列表 loading 门 —— 屏上那份旧结果(含空)是归属上一目标的**已确认**状态, 在被新结果取代
     * 之前不该被 loading 覆盖; 「还没到新的」由 FX-29 遮罩(160ms 延迟点亮)表达。
     * !两条硬约束(本轮踩过):
     *   ①**不得**改成「空响应视为『未就绪』→ 延迟渲染/重拉」—— 那会把常态的空推迟(首版固定 1s 重拉,
     *     被用户否掉: 「种子的常态就是没有对端」; 何况后端对空响应还有 1s 短缓存, 重拉只会拿回空包)。
     *   ②标记必须**在 _loadDrawerTab 之前**置位(三 fetcher 在其内 await 前同步读), 且
     *     _stopDrawerPoll **不得**清它(_loadDrawerTab→_startDrawerPoll 会调它)。
     * 冷启动(openTorrentDrawer)不走本方法: 那时无旧结果可保留, loading 由该方法按 initialTab 同帧置位。 */
    _drawerListLoadingOn(silent) {
      return !silent && !this._drawerSoftSwitch;
    },
  },
};
