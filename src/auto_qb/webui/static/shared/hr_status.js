/* auto-qb WEB UI · HR 站点级状态(设置页「HR 在线核实」分区的页尾「站点状态」块)
 *
 * 数据来自只读端点 `/api/hr/status`, 字段口径单点在 `auto_qb/hr/status.py`(与 `--hr-status`
 * 同一层) —— 本文件**只做展示**: 不重算阈值、不重算新鲜度, 只把后端给的人话与数字摆出来
 * (前端重算 = 自定义阈值/周期一改就静默失效, 见 pitfalls: HR 判定前后端各写一遍)。
 *
 * ❗加载时机: 打开「HR 在线核实」分区时拉一次(config_hub.js hubGo), 之后手动刷新
 *   (不轮询: 站点数据的小时级节奏不需要前端高频拉, 而轮询会给 Web 线程添无谓负载)。
 * ❗入口只有一个(2026-09-25 合并): Console Hub「HR 在线核实」分区页尾 —— 曾经的经典设置页
 *   章节与独立首页卡片都已随旧版设置页移除, 别再加回第二套入口。
 * ❗本文件在 HTML 里必须排在 app.js **之前**(app.js 末尾 mixin window.AQB_HR_STATUS)。
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
      } catch (e) {
        if (!e.auth) this.hrs.error = e.message || "状态读取失败";
      } finally {
        this.hrs.loading = false;
      }
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
