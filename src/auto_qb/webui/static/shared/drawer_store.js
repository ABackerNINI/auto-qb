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
 *   - 本层拥有: 四个 fetcher(_fetchDrawerDetail|Trackers|Files|Peers) · 请求代际序号
 *     (_drawerLoadSeq) 与竞态守卫(_drawerStale) · 软切换待到集合(_drawerWait/_drawerWaitSources/
 *     _drawerDone) · 遮罩延迟点亮(_drawerBusyArm/_drawerBusyDisarm/_drawerSwitchEnd) · 按页签取数
 *     单点(_loadDrawerTab) · 换目标软切换(_switchDrawerTarget) · 页签轮询(_startDrawerPoll/
 *     _stopDrawerPoll) · 合并双列数据补给(_drawerMergeSupply) · peers 键名适配(_drawerNormPeers) ·
 *     软切换空态宽限(_drawerGraceHold; 与 peers 判空 helper _drawerPeerCount, 2026-10-13 第九次闪烁复发)。
 *   - 本层不拥有(留在 drawer.js): 面板开合/几何/拖高/持久化(_drawerClampHeight, drawerGrip*,
 *     drawerPanelStyle, persistDrawer*) · 跟随挂点(_kbFollowDrawer/_stopDrawerFollow) · 出入手
 *     过渡钩子 · 派生列表(drawerFileRows/drawerPeerRows/drawerGeneralSections)。
 *
 * !跨模块登记成对纪律(本层存在的首要理由, R2 风险): 凡是进 _drawerWait 集合的源, 必须有人调
 *   _drawerDone 登记到手。四 fetcher 在各自 finally 里成对; 流量源是**跨模块**的(kb_traffic_chart.js
 *   的 _qbLoad 落袋处显式调 _drawerDone("traffic", hash, 0)), 与 _drawerWaitSources 的通用分支成对。
 *   拆掉任一边 = 软切换遮罩等一个永不到手的源, 永久挂死(2026-10-04 实测)。
 */
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
      // FX-29 软切换宽限(见 _drawerGraceHold)的收口: 页签切走/换目标/关面板即撤销三列表(peers/
      // trackers/files)的待重拉与宽限标记 —— 本方法正是这几条路径的共同收口(与下一句 _qbPollStop
      // 同理由)。_switchDrawerTarget 在调本方法**之后**才重新置标记, 故这里的清空不会误伤本次换
      // 目标; _loadDrawerTab 内的 _startDrawerPoll→本方法 亦然(执行时标记尚未置位)。
      if (this._drawerGraceRetry) {
        for (const src in this._drawerGraceRetry) {
          if (this._drawerGraceRetry[src]) clearTimeout(this._drawerGraceRetry[src]);
          this._drawerGraceRetry[src] = null;
        }
      }
      this._drawerGrace = null;
      // 流量页签(S5b)的低频轮询同收: 本方法是抽屉页签轮询的收口单点(closeDrawer/drawerTab/
      // _switchDrawerTarget/openTorrentDrawer 全走这里), 页签切走/换目标/关面板即停 —— 若新页签
      // 仍是流量, _loadDrawerTab 会重新起(_qbPollStart 自带先停后起)
      this._qbPollStop("torrent");
    },
    _startDrawerPoll() {
      this._stopDrawerPoll();
      // P1-4: 3s → 5s。抽屉是观察用途, peers/trackers 秒级变化对操作没有意义;
      // 而每次轮询都要 Web 线程直连 qB(peers 走 sync/torrentPeers, 响应体随 peer 数增长),
      // 在主循环之外额外占用 qB。5s 仍远快于人工观察节奏。
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
      }, 5000);
    },
    /* W2 请求代际纪律: 四个 fetcher 均带可选 seq(0 = 无代际约束, 走 hash 戳守卫) ——
     * 换 hash(跟随/显式打开)或换代际(切页签)后, 在途旧响应一律丢弃, 防止慢响应把新目标的
     * 详情/列表覆盖成旧的。hash 戳另兜一路: 5s 轮询(seq=0)发出后恰逢跟随换目标, 响应也不落袋。 */
    _drawerStale(hash, seq) {
      return this.drawer.hash !== hash || (!!seq && seq !== this._drawerLoadSeq);
    },
    async _fetchDrawerDetail(seq = 0) {
      const hash = this.drawer.hash;
      this.drawer.loading = true;
      this.drawer.error = "";
      try {
        const r = await this.api(`/api/torrents/${hash}`);
        if (this._drawerStale(hash, seq)) return;  // 旧响应丢弃(W2 代际纪律)
        this.drawer.detail = (r && r.torrent) || null;
        if (!this.drawer.detail) this.drawer.error = "种子不存在或已被删除";
        this._dtNotify("detail");  // 模板核心层(计划 26-10-06-0838 S1): 落袋即通知活动变体重渲染(W7 恢复)
      } catch (e) {
        if (this._drawerStale(hash, seq)) return;
        if (!e.auth) this.drawer.error = e.message || "详情获取失败";
      } finally {
        // 过期请求不动 loading 态(新在途请求持有它), 免得闪一帧"加载完"假象
        if (!this._drawerStale(hash, seq)) this.drawer.loading = false;
        this._drawerDone("detail", hash, seq);  // FX-29: 落定登记(该数据源已到手)
      }
    },
    async _fetchDrawerTrackers(silent = false, seq = 0) {
      const hash = this.drawer.hash;
      if (!silent) this.drawer.trackersLoading = true;
      let deferred = false;  // FX-29 宽限丢弃(见 _drawerGraceHold)
      try {
        const r = await this.api(`/api/torrents/${hash}/trackers`);
        if (this._drawerStale(hash, seq)) return;
        const rows = Array.isArray(r) ? r : [];
        if (!silent && this._drawerGraceHold("trackers", hash, rows.length, () => this._fetchDrawerTrackers(false, seq))) {
          deferred = true;
          return;
        }
        this.drawer.trackers = rows;
        this.drawer.trackersError = "";  // 成功落袋即清失败标记(上一次失败不影响本轮展示)
      } catch (e) {
        if (!silent && !e.auth) this.toast("tracker 列表获取失败: " + e.message, "error");
        // P3-5: 失败标记落 state(过期响应不动它, 属于在途的新目标); 5s 轮询期(silent)也落,
        // 否则静默失败变体永远停在空态
        if (!this._drawerStale(hash, seq)) this.drawer.trackersError = e.message || "tracker 列表获取失败";
      } finally {
        if (deferred) return;  // 宽限丢弃: 保持 trackersLoading(旧数据撑几何)与遮罩, 等重拉结果
        if (!this._drawerStale(hash, seq)) {
          this.drawer.trackersLoading = false;
          this._dtNotify("trackers");  // W7 恢复: 旧变体需通知才重渲染, 理由见 2026-10-07 报障
        }
        this._drawerDone("trackers", hash, seq);
      }
    },
    async _fetchDrawerFiles(silent = false, seq = 0) {
      const hash = this.drawer.hash;
      if (!silent) this.drawer.filesLoading = true;
      let deferred = false;  // FX-29 宽限丢弃(见 _drawerGraceHold)
      try {
        const r = await this.api(`/api/torrents/${hash}/files`);
        if (this._drawerStale(hash, seq)) return;
        const rows = Array.isArray(r) ? r : [];
        if (!silent && this._drawerGraceHold("files", hash, rows.length, () => this._fetchDrawerFiles(false, seq))) {
          deferred = true;
          return;
        }
        this.drawer.files = rows;
        this.drawer.filesError = "";  // 成功落袋即清失败标记(同 trackers)
      } catch (e) {
        if (!silent && !e.auth) this.toast("文件列表获取失败: " + e.message, "error");
        if (!this._drawerStale(hash, seq)) this.drawer.filesError = e.message || "文件列表获取失败";
      } finally {
        if (deferred) return;  // 宽限丢弃: 保持 filesLoading(旧数据撑几何)与遮罩, 等重拉结果
        if (!this._drawerStale(hash, seq)) {
          this.drawer.filesLoading = false;
          this._dtNotify("files");  // W7 恢复: 通知在 loading 清掉之后(理由同 trackers, 变体 dt10/11/12)
        }
        this._drawerDone("files", hash, seq);
      }
    },
    async _fetchDrawerPeers(silent = false, seq = 0) {
      const hash = this.drawer.hash;
      if (!silent) this.drawer.peersLoading = true;
      let deferred = false;  // FX-29 宽限丢弃(见 _drawerGraceHold): 未落袋/未掀罩/保持 loading
      try {
        const r = await this.api(`/api/torrents/${hash}/peers`);
        if (this._drawerStale(hash, seq)) return;
        const norm = this._drawerNormPeers(r);
        if (!silent && this._drawerGraceHold("peers", hash, this._drawerPeerCount(norm), () => this._fetchDrawerPeers(false, seq))) {
          deferred = true;
          return;
        }
        this.drawer.peers = norm;
        this.drawer.peersError = "";  // 成功落袋即清失败标记(同 trackers)
      } catch (e) {
        if (!silent && !e.auth) this.toast("peer 列表获取失败: " + e.message, "error");
        if (!this._drawerStale(hash, seq)) this.drawer.peersError = e.message || "peer 列表获取失败";
      } finally {
        if (deferred) return;  // 宽限丢弃: 保持 peersLoading(旧数据撑几何)与遮罩, 等重拉结果
        if (!this._drawerStale(hash, seq)) {
          this.drawer.peersLoading = false;
          this._dtNotify("peers");  // W7 恢复: 通知在 loading 清掉之后(理由同 trackers, 变体 dt07/08/09)
        }
        this._drawerDone("peers", hash, seq);
      }
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
      this.filePrio.visible = false;  // 内容页签小菜单与行选中跨种子失效(与 drawerTab/closeDrawer 同口径)
      this.drawerSelPath = "";
      this._loadDrawerTab(this.drawer.tab);
      // 详情恒拉(头部标题/常规页都依赖, 与 openTorrentDrawer 同口径): _loadDrawerTab 只在 general
      // 页签拉详情, 其余页签在此补一发 —— seq 归 _loadDrawerTab 先 bump(页签数据走代际守卫),
      // 详情这次不带 seq 只走 hash 戳守卫(同 hash 内晚到也是同资源, 无覆盖错目标风险)。
      if (this.drawer.tab !== "general") this._fetchDrawerDetail();
      /* FX-29 软切换宽限(第九次形态, 见 _drawerGraceHold): 换目标后首个**空**列表响应视为
       * 「未就绪」。置位必须在 _loadDrawerTab **之后** —— 其内 _startDrawerPoll→_stopDrawerPoll
       * 会清空标记(那是页签轮询的收口); 而本方法开头的 _stopDrawerPoll 已清掉上一次换目标的残留。
       * 三列表同置(本次实际只消费被拉的那张, 其余留到下次换目标/被打断时清)。 */
      this._drawerGrace = { peers: true, trackers: true, files: true };
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
    /* ---------------- FX-29 软切换宽限(peers / trackers / files 三列表共用单点) ----------------
     * 病根(2026-10-13 用户报障「种子详情用户页切换种子时『暂无已连接用户』闪烁」, 坑档
     * pitfalls/web-ui/drawer-switch-flicker.md 第九次形态): 软切换「保留旧数据撑几何 + 遮罩
     * 防串显, 数据**全部到手**才掀罩」的「到手」只判"响应回来了" —— **空响应同样算**: 落袋即
     * 覆盖旧数据、登记 _drawerDone 掀罩、渲染层判空 ⇒ 一帧空态; 而真机换目标后 qB 对新种子的
     * 首个列表响应常瞬时为空(连接/状态尚未就绪) ⇒ 「表格 → 空态 →(下一拍)表格」的闪。
     * 处置: 换目标窗口内(标记由 _switchDrawerTarget 置)某列表的**首个空响应**视为「未就绪」——
     * 不落袋(保留旧数据)/不掀罩(不 _drawerDone)/短延迟重拉一次; 重拉仍空才接受(真没有 —— 那时
     * 标记已消费, 走正常落袋)。仅换目标窗口生效: 轮询(silent)与常态空列表照常如实渲染。
     * 一次性语义: 首次非 silent 落袋即消费本 src 的标记(非空 → 正常落袋; 空 → 宽限重拉)。
     * 返回 true = 已接管 —— 调用方必须 `deferred` 短路 finally(不落袋/不通知/保持 loading)。 */
    _drawerGraceHold(src, hash, count, refetch) {
      const g = this._drawerGrace;
      if (!g || !g[src]) return false;
      g[src] = false;
      if (count) return false;
      if (!this._drawerGraceRetry) this._drawerGraceRetry = {};
      this._drawerGraceRetry[src] = setTimeout(() => {
        this._drawerGraceRetry[src] = null;
        // 重拉前复核: 面板仍开/仍是种子形态/目标未换(换目标时本 timer 已被 _stopDrawerPoll 撤销)
        if (this.drawer.open && this.drawerIsSeed && this.drawer.hash === hash) refetch();
      }, 1000);
      return true;
    },
    /* peers 响应的对端数(qB sync/torrentPeers 恒为 dict 以 "ip:port" 为键, 兼容数组形态, 同
     * _drawerNormPeers) —— FX-29 软切换宽限判「响应是否为空」用(真机对端数 >0, 空即"未就绪")。
     * trackers/files 响应恒为数组, 直接取 .length, 无需本 helper。 */
    _drawerPeerCount(resp) {
      const p = resp && resp.peers;
      if (!p) return 0;
      return Array.isArray(p) ? p.length : Object.keys(p).length;
    },
  },
};
