/* auto-qb WEB UI · HR 站点级状态(设置页「HR 在线核实」分区的页尾「站点状态」块)
 *
 * 数据来自只读端点 `/api/hr/status`, 字段口径单点在 `auto_qb/hr/status.py`(与 `--hr-status`
 * 同一层) —— 本文件**只做展示**: 不重算阈值、不重算新鲜度, 只把后端给的人话与数字摆出来
 * (前端重算 = 自定义阈值/周期一改就静默失效, 见 pitfalls: HR 判定前后端各写一遍)。
 *
 * !加载时机: 打开「HR 在线核实」分区时拉一次(config_hub.js hubGo), 之后手动刷新
 *   (不轮询: 站点数据的小时级节奏不需要前端高频拉, 而轮询会给 Web 线程添无谓负载)。
 * !种子明细(表①, 计划 26-10-01-2216 阶段2): /api/hr/sites/<site>/entries 按站点**按需**
 *   拉一次(打开分区/手动刷新时随 loadHrStatus 触发, 拍板②b), 不进 /api/hr/status 全量
 *   响应也不进 /api/state 轮询载荷(pitfalls/web-ui/contract-api.md: 只在用户显式动作时才
 *   需要的字段不塞轮询载荷); 单站点失败只置该站错误态(.empty 错误行), 不阻塞分区其余内容;
 *   无新增定时器。
 * !入口只有一个(2026-09-25 合并): Console Hub「HR 在线核实」分区页尾 —— 曾经的经典设置页
 *   章节与独立首页卡片都已随旧版设置页移除, 别再加回第二套入口。
 * !本文件在 HTML 里必须排在 app.js **之前**(app.js 末尾 mixin window.AQB_HR_STATUS)。
 */
window.AQB_HR_STATUS = {
  data() {
    return {
      hrs: {
        loaded: false,
        loading: false,
        error: "",
        enabled: false,
        note: "",
        sites: [],
        channel: {},
        fetchEnabled: false,
        workerRunning: false,
        pollInterval: 0,
        confirming: false,
        refreshing: false,
        refreshNote: "",
        /* 表① 逐站点明细(键 = 站点名): { loading, loaded, error, entries, readError, now }
         * laneSel(键 = 站点名): 档位筛选 chips 的本地选择("" = 全部), 前端过滤不回后端 */
        details: {},
        laneSel: {},
      },
    };
  },
  methods: {
    async loadHrStatus(force = false) {
      if (this.hrs.loading) return;
      if (this.hrs.loaded && !force) return;
      this.hrs.loading = true;
      this.hrs.error = "";
      try {
        const r = await this.api("/api/hr/status");
        this.hrs.loaded = true;
        this.hrs.enabled = !!r.enabled;
        this.hrs.note = r.note || "";
        this.hrs.sites = r.sites || [];
        this.hrs.channel = r.channel || {};
        this.hrs.fetchEnabled = !!r.fetch_enabled;
        this.hrs.workerRunning = !!r.worker_running;
        this.hrs.pollInterval = r.poll_interval || 0;
        /* 表① 明细随站点各拉一次: 打开分区(loadHrStatus())首拉, 手动刷新/立即拉取
         * (loadHrStatus(true))重拉 —— 每站点自有 loaded/loading 守卫, 失败不阻塞彼此 */
        for (const s of this.hrs.sites) this.loadHrSiteEntries(s.site, force);
      } catch (e) {
        if (!e.auth) this.hrs.error = e.message || "状态读取失败";
      } finally {
        this.hrs.loading = false;
      }
    },
    /* ---------------- 表① 种子明细(计划 26-10-01-2216 阶段2) ----------------
     * 端点校验: HR 未启用 400 / 站点未接入 404 / 取数线程未启动 409; 站点文件读坏不抛,
     * read_error 随响应带出(前端单独显示, 与「明细请求本身失败」分开)。行字段与人话
     * (lane_text/need_seed_text/verified_source_text)全部后端算好, 排序(档位·下载量)与
     * 行集(含失踪行)也是后端口径 —— 这里只存取与筛选, 不重算任何 HR 语义。 */
    async loadHrSiteEntries(site, force = false) {
      const prev = this.hrs.details[site];
      if (prev && prev.loading) return;
      if (prev && prev.loaded && !force) return;
      /* force 重拉(手动刷新/立即拉取)期间保留旧行(loaded 维持 true), 表格不闪回加载态;
       * 只有首拉才显示 loading 占位 —— 手动刷新的语义是「换数据」不是「清空重来」 */
      const keep = !!(force && prev && prev.loaded);
      this.hrs.details[site] = {
        loading: true,
        loaded: keep,
        error: "",
        entries: keep ? prev.entries : [],
        readError: "",
        now: keep ? prev.now : 0,
      };
      try {
        const r = await this.api(`/api/hr/sites/${encodeURIComponent(site)}/entries`);
        this.hrs.details[site] = {
          loading: false,
          loaded: true,
          error: "",
          entries: r.entries || [],
          readError: r.read_error || "",
          now: r.now || 0,
        };
      } catch (e) {
        /* auth 失败由全局登出兜底, 不留站点级错误行 */
        this.hrs.details[site] = {
          loading: false,
          loaded: false,
          error: e.auth ? "" : (e.message || "站点明细读取失败"),
          entries: [],
          readError: "",
          now: 0,
        };
      }
    },
    /* 明细状态读取(模板经 v-for 单元素别名取一次, 避免 undefined 链) */
    hrsDetailOf(site) {
      return this.hrs.details[site] || { loading: false, loaded: false, error: "", entries: [], readError: "", now: 0 };
    },
    /* 档位筛选 chips(全部/A 考察中/B 达标/C 未达标/D 免罪; 拍板只筛 lane 字母, 文案单点在这) */
    hrsLaneChips() {
      return [["", "全部"], ["A", "A 考察中"], ["B", "B 达标"], ["C", "C 未达标"], ["D", "D 免罪"]];
    },
    hrsLaneSelOf(site) {
      return this.hrs.laneSel[site] || "";
    },
    hrsSetLaneSel(site, lane) {
      this.hrs.laneSel[site] = lane;
    },
    /* 行集 = 后端排好序的 entries 前端本地过筛(不回后端、不重排序) */
    hrsDetailRows(site) {
      const d = this.hrs.details[site];
      if (!d || !d.entries) return [];
      const sel = this.hrsLaneSelOf(site);
      return sel ? d.entries.filter((e) => e.lane === sel) : d.entries;
    },
    /* 档位徽章色义(§5.4): A=warn(考察中) / B=green(达标) / C=error(未达标) / D=blue(免罪);
     * 失踪行由 CSS tr.missing 统一换 --paused 描边弱化, 这里不管 */
    hrsLaneCls(lane) {
      return `hr-lane-${String(lane || "").toLowerCase()}`;
    },
    /* 字节数复用共享 fmtSize(AQB_FORMAT 单点); null/undefined = 站点没给 → — (0 是真值, 照显) */
    hrsSize(v) {
      return v === null || v === undefined ? "—" : this.fmtSize(v);
    },
    hrsRatio(v) {
      return v === null || v === undefined ? "—" : Number(v).toFixed(2);
    },
    /* 还需做种人话由后端给; 它的缺失占位是 "-"(need_seed_text 单点), 表格里统一 — */
    hrsNeedSeed(t) {
      return !t || t === "-" ? "—" : t;
    },
    /* 完成时间: 站点 ISO 字符串取日期段; 缺失 → — */
    hrsDone(iso) {
      return iso ? String(iso).slice(0, 10) : "—";
    },
    /* 上次核实(放行判定): 0 = 无放行记录 → —(fmtTs 的 0 哨兵本就回空, 这里补 —);
     * last_seen 上游恒 0(issue 26-10-01-2335), 未知时不缀「最近被见到」—— 绝不显示 epoch */
    hrsVerifiedText(e) {
      return e.verified_ts ? this.fmtTs(e.verified_ts) : "—";
    },
    /* 来源小徽章: satisfied(B 毕业)=绿 / 其余有记录(absent 免罪, not-listed 未列出)=蓝 /
     * 无记录=默认中性(未核实)。token 是后端 SOURCE_* 契约值, 只映射不重算。
     * 类名 hr-vsrc(verified source): hr-src 是列表页已退役的文字 chip 族
     * (hr-tooltip-overlap, 守阵钉了 class="hr-src" 零残留), 新件不得复用该名字 */
    hrsSrcCls(e) {
      if (!e.verified_source) return "";
      return e.verified_source === "satisfied" ? "hr-vsrc-b" : "hr-vsrc-d";
    },
    /* 状态列: 在列(观察期 N) / 失踪 N 波; 「最近被见到」只在 last_seen 已知时缀 */
    hrsStatusText(e) {
      let t = e.active ? "在列" : `失踪 ${e.missing_streak} 波`;
      if (e.active && e.missing_streak > 0) t += ` · 观察期 ${e.missing_streak}`;
      const seen = this.fmtTs(e.last_seen);
      if (seen) t += ` · 最近被见到 ${seen}`;
      return t;
    },
    /* ---------------- 展示辅助(值全由后端算好, 这里只挑文案与配色) ---------------- */
    hrsStateText(s) {
      if (s.listing === "none") return "全站型(本地兜底)";
      return s.releases_enabled ? "放行签发开启" : "放行签发冻结";
    },
    hrsStateClass(s) {
      return s.listing === "none" || s.releases_enabled ? "ok" : "warn";
    },
    /* 档位计数(A 考察中 / B 已达标 / C 未达标 / D 已免罪) —— 顺序固定, 便于多站点横向对比 */
    hrsLaneText(s) {
      const l = s.lane_counts || {};
      return `A=${l.A || 0} B=${l.B || 0} C=${l.C || 0} D=${l.D || 0}`;
    },
    /* 档位波次徽章(计划 26-09-29-2036 M3): 数字全由后端 s.lanes 算好, 这里只拼文案与配色 */
    hrsLaneBadge(ls) {
      let t = `${ls.lane} ${ls.status_text}: ${ls.pages}页${ls.rows}行${ls.full_depth ? "(全)" : ""}`;
      if (ls.count_claim != null) t += ` · ${ls.rows}/声明${ls.count_claim}`;
      if (ls.count_match === false) t += " 对不平";
      return t;
    },
    hrsLaneClass(ls) {
      if (ls.count_match === false) return "warn";
      return ls.status === "failed" ? "error" : "";
    },
    /* 人工对账戳(§5.3): 零行波默认不签发放行, 确认账号清单确实为空后写一次性戳 */
    async hrsConfirmEmpty(site) {
      if (this.hrs.confirming) return;
      if (!confirm(`确认站点 ${site} 的 HR 清单确实为空?
确认后零行波可正常签发放行; 清单再现非零行时确认戳自动失效。
页头计数可自证空集的站点(各档声明全为 0)无需此人工确认。`)) return;
      this.hrs.confirming = true;
      try {
        await this.api("/api/hr/confirm-empty", { method: "POST", body: JSON.stringify({ site }) });
        await this.loadHrStatus(true);
      } catch (e) {
        if (!e.auth) alert(e.message || "确认写入失败");
      } finally {
        this.hrs.confirming = false;
      }
    },
    /* 立即拉取(计划 26-09-30-0240): 请求后端置一次性 force 旗标, 取数线程跳过复用窗与
     * 拉取间隔立即开波(账号频控 min_interval/日额/Retry-After/时间窗仍生效)。
     * site 缺省 = 全部启用站点。受理后立即刷新状态; 波启动后首任务数秒内入队,
     * 后续任务由取数线程/扩展的既有轮询接管 —— 本页不需要轮询, 刷一次看「上次取波」即可。 */
    async hrsRefresh(site = "") {
      if (this.hrs.refreshing) return;
      this.hrs.refreshing = true;
      try {
        const r = await this.api("/api/hr/refresh", { method: "POST", body: JSON.stringify(site ? { site } : {}) });
        const n = (r.requested || []).length;
        this.hrs.refreshNote = n
          ? `已受理 ${n} 个站点, 取数线程执行中(跳过复用窗与拉取间隔, 频控仍生效)`
          : "";
        await this.loadHrStatus(true);
      } catch (e) {
        if (!e.auth) alert(e.message || "立即拉取请求失败");
      } finally {
        this.hrs.refreshing = false;
      }
    },
    hrsPct(v) {
      return `${Math.round((v || 0) * 100)}%`;
    },
    /* 通道一行话: 端点通不通 + 本实例能不能主动抓(没有浏览器时只能读别人抓的) */
    hrsChannelText() {
      const c = this.hrs.channel || {};
      if (!c.enabled) return "取数通道未启用(只会读共享数据, 不会主动抓)";
      const where = c.listening ? `监听 127.0.0.1:${c.port}` : "端点未启动";
      const who = this.hrs.fetchEnabled ? "本实例可主动取数" : "本实例只读共享数据";
      const seen = c.last_contact_ts ? "" : " · 还没有任何扩展联系过";
      const pend = c.pending ? ` · 待取任务 ${c.pending}` : "";
      return `${where} · ${who}${seen}${pend}`;
    },
    hrsPollText() {
      return this.hrs.pollInterval ? `每 ${this.hrs.pollInterval}s 检查一次站点` : "";
    },
  },
};
