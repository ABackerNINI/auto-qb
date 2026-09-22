/* auto-qb WEB UI · 统计 / 分类标签管理 / 日志 / 限速 / 流量历史 弹窗
 *
 * app.js 按域拆分出的片段(2026-09-20)。约定与 config_editor.js / config_rules.js 同一范式:
 * 挂到 window.AQB_DIALOGS, 由 app.js 末尾 app.mixin(window.AQB_DIALOGS) 注入同一个 Vue 实例 ——
 * 方法体里的 this 仍是那个组件实例, 跨模块互调与拆分前完全等价。
 *
 * ❗本文件在 HTML 里必须排在 app.js **之前**(app.js 末尾要读 window.AQB_DIALOGS);
 *   用到的列模型常量(TABLE_COLUMNS / MIN_COL_PX / STATE_RANK …)仍单点定义在 app.js 顶部。
 */
window.AQB_DIALOGS = {
  methods: {
    /* ---------------- 统计面板(FE-2C): 全局状态(server_state, 缺失显示 —) ----------------
     * 数据源随 /api/state.status.server 每轮回传(见 refresh()), 状态栏常显统计直接取
     * `statsServer`; 打开面板 / 卡内"刷新"按钮才走 /api/stats 重取一次(统计是低频信息,
     * 且"刷新"按钮语义上就该真的发一次请求)。server 为 null(qB 未同步/降级全量不可用)
     * 时空态文案; 请求失败给重试。
     */
    async openStats() {
      this.statsOpen = true;
      await this.loadStats();
    },
    closeStats() {
      this.statsOpen = false;
    },
    async loadStats() {
      this.statsLoading = true;
      this.statsError = "";
      try {
        const r = await this.api("/api/stats");
        this.statsServer = r.server || null;
      } catch (e) {
        if (!e.auth) this.statsError = e.message || "加载失败";
        // FIX-04b: 失败不清空已有数据(骨架常驻防闪烁); 仅首次加载失败保持 null → 错误占位重试
      } finally {
        this.statsLoading = false;
      }
    },
    /* 统计值兜底: 字段缺失(null/undefined)显示 —; 0 是合法值(如 DHT 0 节点)原样展示 */
    statVal(v, fmt) {
      if (v === null || v === undefined || v === "") return "—";
      return fmt ? fmt(v) : String(v);
    },
    /* qB connection_status 文案(原值兜底; 缺失显示 —) */
    connText(v) {
      if (v === null || v === undefined || v === "") return "—";
      return { connected: "已连接", firewalled: "已连接(防火墙限制)", disconnected: "未连接" }[v] || String(v);
    },
    /* ---------------- 分类/标签管理对话框(FE-2C2): qB 分类/标签的增删改 ----------------
     * 列表数据源 GET /api/categories|tags; 写操作走 POST /api/categories(/edit|/remove) 与 /api/tags(/remove)。
     * CRUD 成功后重拉列表刷新对话框; 对话框关闭后主列表随下一轮 rid 轮询自然更新(不强刷)。
     */
    openMgr(kind) {
      this.filterMenu = "";  // 从筛选弹层进入: 先收起弹层再开对话框
      this.mgrOpen = kind;
      this.mgrCategories = [];
      this.mgrTags = [];
      this.mgrNewCatName = "";
      this.mgrNewCatPath = "";
      this.mgrNewTags = "";
      this.mgrError = "";
      this.loadMgr();
    },
    closeMgr() {
      if (this.mgrBusy) return;  // 写操作回执等待期不允许误关
      this.mgrOpen = "";
    },
    async loadMgr() {
      this.mgrLoading = true;
      this.mgrError = "";
      try {
        if (this.mgrOpen === "category") {
          // qB categories: {名字: {save_path, ...}} → 行数组(名字字典序)
          const r = await this.api("/api/categories");
          const cats = r.categories || {};
          this.mgrCategories = Object.keys(cats)
            .map((name) => ({ name, save_path: (cats[name] && cats[name].save_path) || "" }))
            .sort((a, b) => a.name.localeCompare(b.name));
        } else {
          const r = await this.api("/api/tags");
          this.mgrTags = (r.tags || []).slice().sort((a, b) => a.localeCompare(b));
        }
      } catch (e) {
        if (!e.auth) this.mgrError = e.message || "加载失败";
      } finally {
        this.mgrLoading = false;
      }
    },
    async submitMgrCategory() {
      if (this.mgrBusy) return;  // 回车提交与按钮同源: 防回执等待期重复投递
      const name = this.mgrNewCatName.trim();
      if (!name) { this.toast("分类名称不能为空", "warn"); return; }
      this.mgrBusy = true;
      try {
        const payload = { name };
        const savePath = this.mgrNewCatPath.trim();
        if (savePath) payload.save_path = savePath;  // 可空: 留空 = 仅建分类不带路径
        await this.api("/api/categories", { method: "POST", body: JSON.stringify(payload) });
        this.toast(`已创建分类: ${name}`, "ok", 2500);
        this.mgrNewCatName = "";
        this.mgrNewCatPath = "";
        await this.loadMgr();
      } catch (e) {
        if (!e.auth) this.toast(`创建分类失败: ${e.message}`, "error", 8000);
      } finally {
        this.mgrBusy = false;
      }
    },
    async submitMgrTags() {
      if (this.mgrBusy) return;  // 回执等待期防重复投递
      // 支持中英文逗号分隔批量创建(空段剔除; 与添加种子对话框的标签口径一致)
      const tags = this.mgrNewTags.split(/[,,]/).map((t) => t.trim()).filter(Boolean);
      if (!tags.length) { this.toast("请输入至少一个标签", "warn"); return; }
      this.mgrBusy = true;
      try {
        await this.api("/api/tags", { method: "POST", body: JSON.stringify({ tags }) });
        this.toast(`已创建 ${tags.length} 个标签`, "ok", 2500);
        this.mgrNewTags = "";
        await this.loadMgr();
      } catch (e) {
        if (!e.auth) this.toast(`创建标签失败: ${e.message}`, "error", 8000);
      } finally {
        this.mgrBusy = false;
      }
    },
    async mgrEditCatPath(name) {
      const cur = (this.mgrCategories.find((c) => c.name === name) || {}).save_path || "";
      const p = await this.promptDialog("修改分类保存路径", cur, {
        body: `分类: ${name}`, placeholder: "如 D:\\Torrents\\TV", okText: "保存",
      });
      if (p === null) return;  // 取消/遮罩/Esc 均不写
      const savePath = p.trim();
      if (!savePath) { this.toast("保存路径不能为空", "warn"); return; }
      if (savePath === cur) { this.toast("未作修改", "ok", 2000); return; }
      this.mgrBusy = true;
      try {
        await this.api("/api/categories/edit", { method: "POST", body: JSON.stringify({ name, save_path: savePath }) });
        this.toast(`已更新分类路径: ${name}`, "ok", 2500);
        await this.loadMgr();
      } catch (e) {
        if (!e.auth) this.toast(`修改分类路径失败: ${e.message}`, "error", 8000);
      } finally {
        this.mgrBusy = false;
      }
    },
    async mgrDeleteCategory(name) {
      const ok = await this.confirmDialog("删除分类", `将删除分类「${name}」(不删除种子与文件)`, { okText: "删除", danger: true });
      if (!ok) return;
      this.mgrBusy = true;
      try {
        await this.api("/api/categories/remove", { method: "POST", body: JSON.stringify({ names: [name] }) });
        this.toast(`已删除分类: ${name}`, "ok", 2500);
        await this.loadMgr();
      } catch (e) {
        if (!e.auth) this.toast(`删除分类失败: ${e.message}`, "error", 8000);
      } finally {
        this.mgrBusy = false;
      }
    },
    async mgrDeleteTag(tag) {
      const ok = await this.confirmDialog("删除标签", `将删除标签「${tag}」(自动规则可能重新打上)`, { okText: "删除", danger: true });
      if (!ok) return;
      this.mgrBusy = true;
      try {
        await this.api("/api/tags/remove", { method: "POST", body: JSON.stringify({ tags: [tag] }) });
        this.toast(`已删除标签: ${tag}`, "ok", 2500);
        await this.loadMgr();
      } catch (e) {
        if (!e.auth) this.toast(`删除标签失败: ${e.message}`, "error", 8000);
      } finally {
        this.mgrBusy = false;
      }
    },
    /* ---------------- 日志页(FE-2C): /api/log 只读 tail(等级过滤 + 行数选择 + 手动刷新, 不轮询) ---------------- */
    async openLogs() {
      // W4: 日志迁入设置页"运行日志"章节; 顶层 page 收敛为 groups/settings, 不再有 'logs'
      await this.openSettings();
      this.cfg.activeGroup = "__logs";
      if (!this.logs.loaded) await this.loadLogs();
    },
    async loadLogs() {
      this.logs.loading = true;
      this.logs.error = "";
      try {
        const q = new URLSearchParams({ lines: String(this.logs.num || 300) });
        if (this.logs.level) q.set("level", this.logs.level);
        const r = await this.api(`/api/log?${q.toString()}`);
        this.logs.lines = r.lines || [];
        this.logs.file = r.file || "";
        this.logs.loaded = true;
      } catch (e) {
        if (!e.auth) this.logs.error = e.message || "日志加载失败";
      } finally {
        this.logs.loading = false;
      }
    },
    /* ---------------- 限速托管状态与临时覆盖(FE-2C D2) ----------------
     * /api/speed/mode 只读快照; /api/speed/override 两方向都必填(0=不限),
     * 曲线启用时覆盖是临时的(下一档位切换即恢复), 停用时为常态设置。
     */
    async loadSpeedMode(force = false) {
      if (this.speedMode.loaded && !force) return;
      try {
        const r = await this.api("/api/speed/mode");
        this.speedMode = {
          loaded: true,
          curveEnabled: !!r.curve_enabled,
          target: r.curve_target || null,
          current: r.current || null,
          error: "",
        };
      } catch (e) {
        if (!e.auth) this.speedMode.error = e.message || "状态获取失败";
      }
    },
    async submitSpeedOverride() {
      if (!this.speedOvReady || this.speedOverride.busy) return false;
      const up = Math.max(0, Math.round(Number(this.speedOverride.up)));
      const down = Math.max(0, Math.round(Number(this.speedOverride.down)));
      const text = `上 ${this.fmtLimit(up) || "不限速"} / 下 ${this.fmtLimit(down) || "不限速"}`;  // toast 保留"不限速"字样(TBL-02)
      this.speedOverride.busy = true;
      try {
        const resp = await this.api("/api/speed/override", {
          method: "POST",
          body: JSON.stringify({ upload_kib: up, download_kib: down }),
        });
        const r = await this.waitCmd(resp.cmd_id);
        if (r.ok) {
          this.toast(`已临时覆盖全局限速: ${text}`, "ok", 3000);
          this.speedOverride = { up: "", down: "", busy: false };
          await this.loadSpeedMode(true);  // 覆盖后刷新托管状态(qB 当前值已变)
          return true;  // SPD-04: 供弹窗判断成功关窗
        } else {
          this.toast(`限速覆盖失败: ${r.error}`, "error", 8000);
        }
      } catch (e) {
        if (!e.auth) this.toast("限速覆盖发送失败: " + e.message, "error");
      } finally {
        this.speedOverride.busy = false;
      }
      return false;
    },
    /* ---------------- 限速修改浮层(SPD-04; FX-08 改为**就近弹出**) ----------------
     * FX-08: 不再居中 + 遮罩弹出, 而是锚在点击的"限制速度"按钮附近向上弹(该方向输入框预聚焦),
     * 位置夹取到视口内(左右各留 12px), 不会跑到屏幕外; 点空白/Esc 关闭(无遮罩, 页面其余部分仍可操作)。
     * 打开时取一次 /api/speed/mode 并回填 qB 当前生效值(KiB/s, 0 = 不限); 提交沿用 submitSpeedOverride,
     * 成功即关窗, 失败留在窗内看报错并重试。
     */
    async openSpeedAt(ev, dir) {
      const el = ev && ev.currentTarget;
      const rect = el && el.getBoundingClientRect ? el.getBoundingClientRect() : null;
      const W = 380;  // 与 .speed-pop 的 width 单点一致
      const left = rect ? rect.left - 12 : window.innerWidth - W - 12;
      this.speedAt = { left, dir: dir === "down" ? "down" : "up" };
      this.speedOpen = true;
      await this.loadSpeedMode(true);  // 开窗取当前值(强制刷新, 不吃缓存)
      const c = this.speedMode.current || {};
      const pick = (v) => (v === undefined || v === null ? "" : String(v));
      this.speedOverride.up = pick(c.upload_limit);
      this.speedOverride.down = pick(c.download_limit);
      this.$nextTick(() => {
        // 只在当前方向预聚焦(点击"限制速度"就是为改这一方向), 并全选便于直接覆写
        const inp = this.$refs.speedPop && this.$refs.speedPop.querySelector("#sp-" + this.speedAt.dir);
        if (inp) {
          inp.focus();
          inp.select();
        }
      });
    },
    /* 浮层内联定位: 只写 left(纵向由 CSS 锚定状态栏上缘), 并夹取到视口内 */
    speedPopStyle() {
      const W = 380, PAD = 12;
      return { left: Math.max(PAD, Math.min(this.speedAt.left, window.innerWidth - W - PAD)) + "px" };
    },
    /* 旧入口(居中弹窗)保留为薄包装: 无点击坐标时锚在视口右侧(第三方链接/键盘触发路径) */
    openSpeedDialog() {
      return this.openSpeedAt(null, "up");
    },
    closeSpeedDialog() {
      this.speedOpen = false;
      this.speedAt = { left: 0, dir: "up" };
    },
    async submitSpeedDialog() {
      const ok = await this.submitSpeedOverride();
      if (ok) this.speedOpen = false;
    },
    /* ---------------- 历史流量弹层(今日流量面板入口; 天/月/年切换 + 悬停取值) ---------------- */
    async openHistory() {
      this.historyOpen = true;
      await this.loadHistory();
    },
    async loadHistory() {
      this.historyLoading = true;
      this.historyError = "";
      try {
        const data = await this.api("/api/traffic/history");
        this.historyData = data.history || [];
      } catch (e) {
        if (!e.auth) this.historyError = e.message || "加载失败";
      } finally {
        this.historyLoading = false;
      }
    },
    /* 悬停追踪: 事件挂在 .hist-chart容器(mousemove), 指针 x 折算进 viewBox 坐标再换算
     * 桶索引 —— 连续无空隙; 旧版逐桶 enter/leave + 命中区只盖单柱的闪烁根因即在此 */
    histMove(ev) {
      if (!this.historyBuckets.length) return;
      const rect = ev.currentTarget.getBoundingClientRect();
      const g = this.histGeom;
      const x = ((ev.clientX - rect.left) / rect.width) * g.w;
      const idx = Math.floor((x - g.padL) / g.bw);
      this.histHoverIdx = Math.max(0, Math.min(this.historyBuckets.length - 1, idx));
    },
    histLeave() {
      this.histHoverIdx = -1;
    },
    /* 面积填充路径(折线下方淡渐染; 带参辅助放 methods —— pitfalls: computed不能加括号调用) */
    _histArea(key) {
      const pts = this.histSeries[key];
      if (!pts.length) return "";
      const base = (this.histGeom.padT + this.histGeom.chartH).toFixed(1);
      return `${this.histPaths[key]} L ${pts[pts.length - 1].x.toFixed(1)} ${base} L ${pts[0].x.toFixed(1)} ${base} Z`;
    },
  },
  computed: {
    /* 底部状态栏左侧常显统计摘要(TBL-08 修订; **FX-07 精简**): "统计不应该藏到弹出框中" ——
     * 取 /api/stats 的 server_state(纯内存快照, 与主轮询同周期静默同步)。
     * FX-07: 退役 本次 / 累计 / DHT 三项(本次与累计与"今日流量"口径重叠, DHT 属低频诊断),
     * 只留 连接 与 剩余 两个运行态指标; 今日流量改由模板单独渲染(数据源不同, 见 todayTraffic)。
     * server_state 未同步时返回空数组 → 显示未同步提示 */
    sbStats() {
      const s = this.statsServer;
      if (!s) return [];
      const items = [
        {
          key: "peers",
          icon: "#i-link",
          cls: "ico-peers",
          label: "连接",
          value: this.statVal(s.total_peer_connections),
          title: "当前 peer 连接总数 · 连接状态: " + this.connText(s.connection_status),
        },
        {
          key: "disk",
          icon: "#i-hdd",
          cls: "ico-disk",
          label: "剩余",
          value: this.statVal(s.free_space_on_disk, (v) => this.fmtSize(v)),
          title: "qB 保存目录所在磁盘剩余空间",
        },
      ];
      return items;
    },
    /* 状态分布(按当前视图聚合): 旧版只读 this.groups, 种子页(groups 不被后端回传)
     * 与首次进入种子页(localStorage 持久化 view=torrent, 首轮 groups=[])时统计全空,
     * 「做种10 错误1」这一行消失 ⇒ 必须按 viewMode 各自取数:
     *   groups  →  各组 members + singles(同一来源 _member_view, kind 字段一致)
     *   torrents→  平铺数组(kind 字段同样由 _member_view 透出)
     *   shows   →  剧集节点的聚合 state(后端 _build_show_view 已取 min kind)
     * 顺序表与 kind 口径与 decorate.kindText 一致, 计数为 0 的类别被 filter 掉 */
    distSegments() {
      const order = ["seeding", "downloading", "checking", "paused", "error", "other"];
      const count = {};
      const bump = (k) => { if (k) count[k] = (count[k] || 0) + 1; };
      if (this.viewMode === "torrents") {
        for (const t of this.torrents) bump(t.kind);
      } else if (this.viewMode === "shows") {
        for (const s of (this.shows && this.shows.list) || []) {
          for (const season of (s.seasons || [])) {
            for (const ep of (season.episodes || [])) bump(ep.state);
          }
        }
      } else {
        for (const g of this.groups) for (const m of (g.members || [])) bump(m.kind);
        for (const r of this.singles) bump(r.kind);
      }
      const total = order.reduce((n, k) => n + (count[k] || 0), 0);
      if (!total) return [];
      return order.filter((k) => count[k]).map((k) => ({
        kind: k, count: count[k], pct: (count[k] / total) * 100, text: this.kindText(k),
      }));
    },
    distTotal() {
      return this.distSegments.reduce((n, s) => n + s.count, 0);
    },
    distTitle() {
      return this.distSegments.map((s) => `${s.text} ${s.count}`).join(" · ");
    },
    /* ---------------- 限速/流量快照(后端 SpeedCurveMixin 发布, 随 status 恒回传) ----------------
     * state: disabled(未启用限速曲线) / ok / dry_run / stale(数据源不可用)
     * periods[].up|down 为**字节**; limit.target|actual 为 **KiB/s**(0 = 不限速, null = 该方向不管理)
     */
    traffic() {
      return this.status.traffic || { state: "disabled", periods: [], limit: {} };
    },
    trafficOn() {
      return this.traffic.state !== "disabled";
    },
    todayTraffic() {
      return (this.traffic.periods || []).find((p) => p.period === "day") || null;
    },
    /* 今日流量悬浮说明: 把口径写清楚(数据源 = Traffic Monitor dat 的按日行, 单位字节) */
    todayTrafficTitle() {
      const t = this.todayTraffic;
      if (!t) return "";
      return `今日流量(Traffic Monitor 按日口径): 下载 ${this.fmtSize(t.down)} / 上传 ${this.fmtSize(t.up)}`
        + ` · 数据状态: ${this.traffic.state}`;
    },
    /* 全局限速取数单点(R10-04): qB server_state 的全局限速键是 **dl_rate_limit / up_rate_limit**
     * (bytes/s, 0 = 不限速), **不是 dl_limit/up_limit** —— 后者是**单种子**级字段(TorrentRecord,
     * 见 mixins/web_view.py 的种子限速列)。前端曾读 s.dl_limit/s.up_limit ⇒ 恒 undefined ⇒
     * 状态栏"限制速度"永远显示 "—", 同时作速度染色分母时也恒缺失 ⇒ 色阶从未生效(连带故障)。
     * 现在状态栏文案、速度染色分母两处全部引用本单点, 改口径只改这里。
     * 单位维持 bytes/s(与 fmtSpeed 同源); 浮层内的编辑仍走 /api/speed/mode 的 KiB/s 口径,
     * 两套单位各在自己的显示层换算, 不在同一函数里混用。
     * 语义: null = 未知(字段缺失), 0 = 不限速。 */
    speedLimitBytes() {
      const s = this.statsServer || {};
      const pick = (v) => (v === null || v === undefined || v === "" ? null : Number(v) || 0);
      return { down: pick(s.dl_rate_limit), up: pick(s.up_rate_limit) };
    },
    /* 状态栏"限制速度"文案(决策 D3 的收窄版: **只取 qB 当前生效值**)。
     * 0 = 不限速 -> "不限"; 字段缺失 -> "—"(区分"未知"与"不限")。
     * 刻意不从限速曲线快照的 limit.actual 取数: 状态栏并列两个口径会变成"限速对照面板"
     * (那是已退役的信息栏形态); 曲线的目标/命中信息在限速浮层内的 .speed-mode-line 展示。 */
    sbLimits() {
      const { down, up } = this.speedLimitBytes;
      const f = (v) => (v === null ? "—" : (v ? this.fmtSpeed(v) : "不限"));
      return { down: f(down), up: f(up) };
    },
    /* 限速对照行: 每个受管方向一行(该方向无曲线则不显示该行);
     * mismatch = 实际值已知且与命中目标不同 -> 前端据此"显示两个 + 原因"
     * tip 在**这里**算好(按方向取原因), 避免每个 pill 都展示全部方向的原因
     */
    limitRows() {
      const lim = this.traffic.limit || {};
      const target = lim.target || {}, actual = lim.actual || {}, reasons = lim.reasons || [];
      // 无方向特定原因时的默认说明(按快照状态区分: 试运行/数据不可用/正常)。
      // 必须在此内联为局部量 —— 本区段是 computed, 任何"看似方法的辅助函数"都会变成属性,
      // 在 computed 内以 this.xxx() 调用会抛 TypeError 导致整块渲染失败(2026-09-14 实测)。
      const fallback = this.traffic.state === "dry_run"
        ? "试运行(dry_run): 只显示命中限速, 不读取/不写入 qB"
        : this.traffic.state === "stale"
          ? "流量数据暂不可用, 限速沿用上一轮生效值"
          : "命中 = 曲线目标值, 实际 = qB 当前生效值";
      const rows = [];
      for (const [dir, label] of [["up", "上传"], ["down", "下载"]]) {
        const tg = target[dir];
        if (tg === null || tg === undefined) continue;
        const ac = actual[dir];
        const reason = reasons.find((r) => r.dir === dir) || null;
        const known = ac !== null && ac !== undefined;
        rows.push({
          dir,
          label,
          target: tg,
          actual: ac,
          mismatch: known && ac !== tg,
          reason,
          tip: reason ? reason.text : fallback,
        });
      }
      return rows;
    },
    /* 限速托管状态一行文案(FE-2C D2): 曲线托管中显示目标值; 未托管显示 qB 当前生效值 */
    speedModeLine() {
      const sm = this.speedMode;
      if (!sm.loaded) return "";
      if (sm.curveEnabled) {
        const t = sm.target || {};
        return `曲线托管中 · 目标 上${this.fmtLimit(t.upload_kib) || "不限速"} / 下${this.fmtLimit(t.download_kib) || "不限速"}`;
      }
      const c = sm.current || {};
      if (c.upload_limit === undefined && c.download_limit === undefined) return "未托管 · qB 限速未知";
      return `未托管 · qB 当前 上${this.fmtLimit(c.upload_limit) || "不限速"} / 下${this.fmtLimit(c.download_limit) || "不限速"}`;
    },
    /* 覆盖表单可提交: 两方向都已有数字(空串/非数字不放行 —— 后端两方向都设置, 漏传会被当 0=不限) */
    speedOvReady() {
      const o = this.speedOverride;
      return o.up !== "" && o.down !== "" && Number.isFinite(Number(o.up)) && Number.isFinite(Number(o.down));
    },
    /* ---------------- 历史流量(弹层): 按日原始行 -> 天(最近30)/月(近12)/年(全部)聚合 ---------------- */
    historyBuckets() {
      const rows = this.historyData || [];
      if (this.historyGran === "month") {
        const m = new Map();
        for (const r of rows) {
          const k = r.date.slice(0, 7);
          const cur = m.get(k) || { up: 0, down: 0 };
          cur.up += r.up;
          cur.down += r.down;
          m.set(k, cur);
        }
        return [...m.entries()].slice(-12).map(([k, v]) => ({ label: k.slice(2), tip: k, up: v.up, down: v.down }));
      }
      if (this.historyGran === "year") {
        const y = new Map();
        for (const r of rows) {
          const k = r.date.slice(0, 4);
          const cur = y.get(k) || { up: 0, down: 0 };
          cur.up += r.up;
          cur.down += r.down;
          y.set(k, cur);
        }
        return [...y.entries()].map(([k, v]) => ({ label: k, tip: `${k} 年`, up: v.up, down: v.down }));
      }
      return rows.slice(-30).map((r) => ({ label: r.date.slice(5), tip: r.date, up: r.up, down: r.down }));
    },
    historyMax() {
      return Math.max(1, ...this.historyBuckets.map((b) => Math.max(b.up, b.down)));
    },
    historySummary() {
      const rows = this.historyBuckets;
      const up = rows.reduce((s, b) => s + b.up, 0);
      const down = rows.reduce((s, b) => s + b.down, 0);
      const peak = rows.reduce((m, b) => Math.max(m, b.up + b.down), 0);
      const avg = rows.length ? (up + down) / rows.length : 0;
      return { up, down, peak, avg };
    },
    /* 折线图几何(常量 + 桶数派生): 无参 computed, 模板以属性访问(不加括号);
     * 尺寸放大(第七轮用户要求"改大一点"): 弹层 860px, viewBox 920×380 */
    histGeom() {
      const n = Math.max(1, this.historyBuckets.length);
      const w = 920, h = 380, padL = 64, padR = 16, padT = 16, padB = 30;
      const chartH = h - padT - padB;
      const bw = (w - padL - padR) / n;
      return { w, h, padL, padR, padT, padB, chartH, n, bw };
    },
    histViewBox() {
      return `0 0 ${this.histGeom.w} ${this.histGeom.h}`;
    },
    histTicks() {
      // Y 轴 5 档网格线(含 0 与最大值), 标签用与柱色无冲突的暗色
      const g = this.histGeom;
      const out = [];
      for (let k = 0; k <= 4; k++) {
        out.push({ y: g.padT + g.chartH * (1 - k / 4), label: k === 0 ? "0" : this.fmtSize((this.historyMax * k) / 4) });
      }
      return out;
    },
    histXTicks() {
      // X 轴标签均匀采样(最多 8 个, 防止柱多时文字重叠)
      const g = this.histGeom;
      const n = this.historyBuckets.length;
      const step = Math.max(1, Math.ceil(n / 8));
      const out = [];
      for (let i = 0; i < n; i += step) {
        out.push({ x: g.padL + i * g.bw + g.bw / 2, label: this.historyBuckets[i].label });
      }
      return out;
    },
    /* 双系列折线点(上传/下载): x = 槽位中心, y 按桶值比例 */
    histSeries() {
      const g = this.histGeom;
      const max = this.historyMax;
      const mk = (key) => this.historyBuckets.map((b, i) => ({
        x: g.padL + i * g.bw + g.bw / 2,
        y: g.padT + g.chartH * (1 - Math.min(1, b[key] / max)),
        v: b[key],
      }));
      return { up: mk("up"), down: mk("down") };
    },
    histPaths() {
      const toPath = (pts) => pts.map((p, i) => `${i ? "L" : "M"} ${p.x.toFixed(1)} ${p.y.toFixed(1)}`).join(" ");
      return { up: toPath(this.histSeries.up), down: toPath(this.histSeries.down) };
    },
    histAreaUp() {
      return this._histArea("up");
    },
    histAreaDown() {
      return this._histArea("down");
    },
    /* 悬停态(容器级 mousemove 连续追踪, 修复旧逐桶 enter/leave 在桶间空隙的闪烁):
     * crosshair x / 两系列高亮点 / tooltip 定位 */
    histHover() {
      if (this.histHoverIdx < 0 || this.histHoverIdx >= this.historyBuckets.length) return null;
      const g = this.histGeom;
      const i = this.histHoverIdx;
      return {
        bucket: this.historyBuckets[i],
        x: this.histSeries.up[i].x,
        up: this.histSeries.up[i],
        down: this.histSeries.down[i],
        leftPct: (this.histSeries.up[i].x / g.w) * 100,
      };
    },
  },
};
