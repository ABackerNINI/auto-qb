/* auto-qb WEB UI 前端(Vue 3 CDN, 无构建链): rid 增量轮询 + 命令投递 + 列宽记忆 */
/* global Vue, localStorage, confirm, alert */  // 声明浏览器全局, 消除编辑器 no-undef 红线
const { createApp } = Vue;

const GROUP_DEFAULT_COLS = [
  "minmax(180px, 2fr)", "minmax(90px, 1fr)", "minmax(90px, 1fr)", "minmax(90px, 1fr)",
  "minmax(90px, 1fr)", "minmax(200px, 2fr)", "52px",
];
const DETAIL_DEFAULT_COLS = [
  "110px", "70px", "minmax(90px, 1fr)", "minmax(90px, 1fr)", "minmax(90px, 1fr)",
  "minmax(90px, 1fr)", "minmax(80px, 1fr)", "minmax(100px, 1fr)", "80px",
];
const COLS_STORE_KEY = "autoqb_colwidths_v1";

function loadColWidths() {
  try {
    return JSON.parse(localStorage.getItem(COLS_STORE_KEY)) || {};
  } catch {
    return {};
  }
}

const app = createApp({
  data() {
    return {
      token: "",  // 已验证通过的密钥(唯一可信身份); 仅 bootstrap 验证成功后提交
      pendingToken: "",  // 验证中的候选密钥(不参与渲染门控/请求头); 服务不可达时供"重试连接"复用
      tokenInput: "",
      authRequired: true,  // 遮罩唯一开关: 仅在密钥验证成功后置 false —— 与 token 赋值解耦, 防错误密钥瞬间主界面闪现
      authPending: false,  // 密钥验证中: 禁用提交、按钮显示"验证中…", 防重复提交
      authError: "",
      authErrorKind: "",   // "auth" = 密钥被拒(401); "unavailable" = 服务不可达(保留候选密钥供重试)
      page: "groups",
      groups: [],
      status: {},
      pollSec: 2,
      expandedKey: null,
      sortKey: "uploaded",
      sortDir: -1,
      groupColumns: [
        { key: "name", sortable: true },
        { key: "dlspeed", sortable: true },
        { key: "upspeed", sortable: true },
        { key: "uploaded", sortable: true },
        { key: "size", sortable: true },
        { key: "sites", sortable: false },
        { key: "count", sortable: true },
      ],
      detailColumns: ["站点", "状态", "下载", "上传", "总上传", "种子大小", "进度", "做种时长", "Hash"],
      colWidths: loadColWidths(),  // {group: [..px..], detail: [..px..]}, localStorage 记忆
      resizing: null,              // {page, idx, startX, startVal}
      menu: { visible: false, x: 0, y: 0, key: null, hash: null },
      serviceDown: false,  // 服务不可达(程序退出): 显示全局横幅, 轮询继续以便恢复后自动接上
      pollFails: 0,        // 连续失败次数(轮询退避: 2s→4s→8s→15s 上限)
      pollTimer: null,     // setTimeout 链式轮询句柄(上一轮结束后再计时, 不堆叠请求)
      lastRid: null,       // 已持有的分组视图版本(服务端 rid); null = 尚未取到(强制全量)
      idlePolls: 0,        // 连续无更新轮数(无变化退避: 2s→5s→10s; 有更新立即归零)
      searchQuery: "",       // 搜索关键字
      searchHits: new Set(),  // 命中种子 hash 集合(名称/文件匹配)
      searchUncovered: [],    // 未归组的命中种子(分组未启用/文件列表不可读), 以虚拟行兜底展示
      searchBuilding: false,  // 文件索引构建中(增量限流可能多轮, 需稍后重查)
      searchError: "",        // 搜索请求失败提示(不再静默)
      searchTimer: null,      // 防抖 + 索引构建自动重查定时器
      kindFilter: "",         // 状态筛选(seeding/downloading/... ; 空 = 不筛选)
      toasts: [],             // 站内提示条(替代 alert)
      modal: {                // 站内确认/输入框(替代 confirm/prompt); 结构见 _modalInit
        visible: false, title: "", body: "", okText: "", cancelText: "",
        danger: false, input: false, value: "", placeholder: "",
      },
      _toastSeq: 0,           // 提示条自增 id
      _modalResolve: null,    // 模态 Promise 的 resolve(单例, 关闭时结算)
    };
  },
  computed: {
    pollLabel() {
      // 顶栏展示当前轮询间隔(自适应: 无变化/服务不可达时放慢)
      return Math.round(this.currentPollMs() / 1000);
    },
    statusBadge() {
      if (this.status.paused) return { text: "已暂停", kind: "warn" };
      if (this.status.connected === false) return { text: "qB 断开", kind: "error" };
      if (this.status.connected === true) return { text: "运行中", kind: "ok" };
      return { text: "连接中…", kind: "warn" };
    },
    sortedGroups() {
      const key = this.sortKey, dir = this.sortDir;
      return [...this.groups].sort((a, b) => {
        const va = a[key], vb = b[key];
        if (typeof va === "string") return dir * va.localeCompare(vb || "");
        return dir * ((va || 0) - (vb || 0));
      });
    },
    // 搜索是辅种管理的筛选: 在真实辅种组上筛选——组内任一成员命中即保留整组(组行沿用真实 key,
    // 组级操作可用), 仅命中成员 search-hit 高亮; 未归组的命中种子(分组未启用/文件列表不可读等)
    // 以单种子虚拟行兜底展示(虚拟行无组级操作, 右键退化为该种子的单种子菜单)。
    // 状态筛选(kindFilter)与之叠加: 先按成员状态筛组(组内任一成员为该状态即保留), 再做搜索匹配。
    filteredGroups() {
      const q = (this.searchQuery || "").trim();
      let base = this.sortedGroups;
      if (this.kindFilter) base = base.filter((g) => g.members.some((m) => m.kind === this.kindFilter));
      if (!q) return base;
      const hits = this.searchHits;
      const kept = [];
      for (const g of base) {
        let hit = false;
        const members = g.members.map((m) => {
          const isHit = hits.has(m.hash);
          if (isHit) hit = true;
          return { ...m, hit: isHit };
        });
        if (hit) kept.push({ ...g, members: members, virtual: false });
      }
      for (const r of this.searchUncovered) {
        if (this.kindFilter && r.kind !== this.kindFilter) continue;
        kept.push({
          key: "u-" + r.hash, name: r.name, count: 1, virtual: true,
          dlspeed: r.dlspeed, upspeed: r.upspeed, uploaded: r.uploaded, size: r.size,
          members: [{ ...r, hit: true }],
        });
      }
      return kept;
    },
    expandedGroup() {
      return this.groups.find((g) => g.key === this.expandedKey) || null;
    },
    totalTorrents() {
      return this.groups.reduce((n, g) => n + g.count, 0);
    },
    totalDl() {
      return this.groups.reduce((n, g) => n + g.dlspeed, 0);
    },
    totalUl() {
      return this.groups.reduce((n, g) => n + g.upspeed, 0);
    },
    /* 状态分布(纯前端聚合 members[].kind): 供顶栏下方堆叠条与可点击图例使用 */
    distSegments() {
      const order = ["seeding", "downloading", "checking", "paused", "error", "other"];
      const count = {};
      for (const g of this.groups) for (const m of g.members) count[m.kind] = (count[m.kind] || 0) + 1;
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
  },
  async mounted() {
    window.addEventListener("click", () => (this.menu.visible = false));
    // Esc: 优先关闭确认框, 其次右键菜单(两者都是临时浮层)
    document.addEventListener("keydown", (e) => {
      if (e.key !== "Escape") return;
      if (this.modal.visible) this.resolveModal(false);
      else if (this.menu.visible) this.menu.visible = false;
    });
    // 页面可见性(与 qB 自带 WebUI 同策略): 后台标签停止轮询; 恢复可见立即刷新并续排
    document.addEventListener("visibilitychange", () => {
      if (document.hidden) this.stopPolling();
      else if (this.token) this.refresh();  // 登出态切回标签不发空 Bearer(由登录成功后自行启动轮询)
    });
    // 本地存储密钥必须重新验证后才放行遮罩; 密钥已轮换则由 401 收口清除
    const savedToken = localStorage.getItem("autoqb_token");
    if (savedToken) this.bootstrap(savedToken);
  },
  methods: {
    async api(path, options = {}) {
      if (!this.token) {
        // 无密钥不出网: 否则会发出 "Bearer " 空头(被 HTTP 层裁剪成裸 "Bearer"),
        // 后端白记一次 401。调用方按 401 同路径处理(回密钥输入界面/静默)。
        this._logout();
        const noAuth = new Error("unauthorized");
        noAuth.auth = true;
        throw noAuth;
      }
      return this._request(path, options, this.token);
    },
    async _request(path, options, token) {
      const resp = await fetch(path, {
        ...options,
        headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json", ...(options.headers || {}) },
      });
      if (resp.status === 401) {
        this._logout("密钥无效或已更换");
        const err = new Error("unauthorized");
        err.auth = true;
        throw err;
      }
      if (!resp.ok) {
        const detail = await resp.json().catch(() => ({}));
        throw new Error(detail.detail || `HTTP ${resp.status}`);
      }
      return resp.json();
    },
    _logout(message = "") {
      // 鉴权失败唯一收口: 遮罩、凭证、定时器与所有已加载的受保护数据一并清空——
      // 防错误密钥提交瞬间主界面(含上一会话残留的分组/设置)闪现, 也避免数据滞留内存视图
      this.authRequired = true;
      this.authPending = false;
      this.pendingToken = "";
      this.token = "";
      localStorage.removeItem("autoqb_token");
      this.stopPolling();
      if (this.searchTimer) clearTimeout(this.searchTimer);  // 登出后停掉搜索防抖/重试, 防空头竞态
      this.searchTimer = null;
      this.groups = [];
      this.status = {};
      this.lastRid = null;
      this.idlePolls = 0;
      this.pollFails = 0;
      this.serviceDown = false;
      this.expandedKey = null;
      this.kindFilter = "";
      this.toasts = [];
      this.modal = this._modalInit();
      this._modalResolve = null;
      this.cfgReset();  // 配置树同样是受保护内容, 一并清除(编辑器状态复位)
      this.page = "groups";
      this.searchQuery = "";
      this.resetSearch();
      if (message) {
        this.authError = message;
        this.authErrorKind = "auth";
      }
    },
    /* ---------------------------------------------------------- 站内提示条(toast) */
    toast(text, kind = "info", ms = 4000) {
      const id = ++this._toastSeq;
      this.toasts.push({ id, text, kind });
      setTimeout(() => this._dropToast(id), ms);
    },
    _dropToast(id) {
      this.toasts = this.toasts.filter((t) => t.id !== id);
    },
    /* ------------------------------------------- 站内确认/输入框(替代 confirm/prompt) */
    _modalInit() {
      return {
        visible: false, title: "", body: "", okText: "", cancelText: "",
        danger: false, input: false, value: "", placeholder: "",
      };
    },
    confirmDialog(title, body, opts = {}) {
      // 返回 Promise<boolean>; 取消/遮罩/Esc 均结算为 false(不做任何写操作)
      return this._openModal({
        title, body, input: false,
        okText: opts.okText || "确认", cancelText: opts.cancelText || "取消", danger: !!opts.danger,
      });
    },
    promptDialog(title, value, opts = {}) {
      // 返回 Promise<string|null>; 取消返回 null(与原生 prompt 语义一致)
      return this._openModal({
        title, body: opts.body || "", input: true, value: value || "", placeholder: opts.placeholder || "",
        okText: opts.okText || "确定", cancelText: opts.cancelText || "取消", danger: !!opts.danger,
      });
    },
    _openModal(cfg) {
      if (this.modal.visible) this.resolveModal(false);  // 单例: 上一个悬空 Promise 先结算为取消
      return new Promise((resolve) => {
        this._modalResolve = resolve;
        this.modal = { ...this._modalInit(), ...cfg, visible: true };
        this.$nextTick(() => {
          if (this.modal.input && this.$refs.modalInput) {
            this.$refs.modalInput.focus();
            this.$refs.modalInput.select();
          }
        });
      });
    },
    resolveModal(ok) {
      if (!this.modal.visible) return;
      const { input, value } = this.modal;
      const resolve = this._modalResolve;
      this._modalResolve = null;
      this.modal = this._modalInit();
      if (resolve) resolve(ok ? (input ? value : true) : (input ? null : false));
    },
    /* ------------------------------------------- 状态筛选与搜索清除 */
    toggleKindFilter(kind) {
      this.kindFilter = this.kindFilter === kind ? "" : kind;
      this.expandedKey = null;  // 筛选后组集合变化, 复位展开态
    },
    clearKindFilter() {
      this.kindFilter = "";
    },
    clearSearch() {
      if (this.searchTimer) clearTimeout(this.searchTimer);
      this.searchTimer = null;
      this.searchQuery = "";
      this.resetSearch();
    },
    /* 右键菜单定位: 视口边界吸附(菜单尺寸取常量估算, 避免先渲染再测量造成的抖动) */
    _menuPos(event, w = 214, h = 222) {
      const x = Math.min(event.clientX, Math.max(8, window.innerWidth - w - 8));
      const y = Math.min(event.clientY, Math.max(8, window.innerHeight - h - 8));
      return { x: Math.max(8, x), y: Math.max(8, y) };
    },
    async bootstrap(candidate) {
      if (this.authPending) return;  // 防重复提交(验证中按钮已禁用, 双保险)
      this.authPending = true;
      this.authError = "";
      this.authErrorKind = "";
      this.pendingToken = candidate;
      this.lastRid = null;  // 重新鉴权/换密钥: 强制全量取一次分组视图
      this.idlePolls = 0;
      try {
        // 用候选密钥直接验证: 成功前 this.token 不提交、authRequired 不解除, 主界面 DOM 绝不渲染
        const state = await this._request("/api/state", {}, candidate);
        this.status = state.status;
        this.groups = state.groups || [];
        if (typeof state.rid === "number") this.lastRid = state.rid;
        this.serviceDown = false;
        this.token = candidate;  // 验证通过才提交为当前身份
        this.authRequired = false;  // 唯一放行点
        localStorage.setItem("autoqb_token", candidate);
        this.pendingToken = "";
        this.tokenInput = "";
        this.startPolling();
      } catch (e) {
        if (!e.auth) {
          // 服务不可达 ≠ 密钥错误: 不否定候选密钥(本地存储亦保留), 给出重试入口, 防误清凭证
          this.authError = "服务不可用, 请确认 auto-qb 程序正在运行";
          this.authErrorKind = "unavailable";
        }
        // e.auth(401/无凭证): _request 已走 _logout() 完成遮罩/数据/文案收口
      } finally {
        this.authPending = false;
      }
    },
    saveToken() {
      const candidate = this.tokenInput.trim();
      if (!candidate || this.authPending) return;  // 空提交/验证中拦截: 不触发任何请求与界面切换
      this.bootstrap(candidate);
    },
    retryAuth() {
      // 仅"服务不可达"分支保留候选密钥; 401 已清空, 重试按钮不渲染
      if (this.pendingToken && !this.authPending) this.bootstrap(this.pendingToken);
    },
    startPolling() {
      this.stopPolling();
      this.refresh();
    },
    stopPolling() {
      if (this.pollTimer) clearTimeout(this.pollTimer);
      this.pollTimer = null;
    },
    scheduleNext() {
      // 用 setTimeout 链式续排(而非 setInterval): 保证上一轮请求结束后再计时, 不堆叠请求
      this.stopPolling();
      if (document.hidden || !this.token) return;
      this.pollTimer = setTimeout(() => this.refresh(), this.currentPollMs());
    },
    currentPollMs() {
      // 失败退避: 连续失败翻倍至上限 15s(减少服务不可达时的空转)
      if (this.pollFails) return Math.min(15000, this.pollSec * 1000 * 2 ** this.pollFails);
      // 无变化退避: 连续多轮无更新逐步放慢(2s→5s→10s); 一旦有更新立即回到 2s
      if (this.idlePolls >= 6) return 10000;
      if (this.idlePolls >= 2) return 5000;
      return this.pollSec * 1000;
    },
    async refresh() {
      try {
        // rid 增量: 带上已持有的视图版本, 服务端版本未变时不回传 groups(响应体趋近于零)
        const query = this.lastRid === null ? "" : `?rid=${this.lastRid}`;
        const state = await this.api("/api/state" + query);
        this.status = state.status;
        if (state.updated !== false) {
          // 视图有变化: 整表替换并记录新版本; 无变化时保留原数组, 不触发重渲染
          this.groups = state.groups || [];
          if (typeof state.rid === "number") this.lastRid = state.rid;
          this.idlePolls = 0;
        } else {
          this.idlePolls += 1;
        }
        this.serviceDown = false;
        this.pollFails = 0;
      } catch (e) {
        // 服务不可达(程序退出/网络失败): 置 serviceDown 显示横幅; 轮询继续, 服务恢复后自动消失。
        // 401(密钥无效): 停止轮询并回到密钥输入界面(防无谓空转)。
        if (e.auth) {
          this.stopPolling();
          return;
        }
        this.serviceDown = true;
        this.pollFails = Math.min(4, this.pollFails + 1);
      }
      this.scheduleNext();
    },
    onSearchInput(event) {
      // 输入防抖: 停止输入 400ms 后触发搜索; 清空则立即恢复辅种管理视图(不等防抖)
      if (this.searchTimer) clearTimeout(this.searchTimer);
      if (!(event.target.value || "").trim()) {
        this.resetSearch();
        return;
      }
      this.searchTimer = setTimeout(() => this.doSearch(), 400);
    },
    resetSearch() {
      // 清空搜索结果并复位展开态: 搜索结果与普通分组结构不同(含虚拟行), 展开状态不跨视图残留
      this.searchHits = new Set();
      this.searchUncovered = [];
      this.searchBuilding = false;
      this.searchError = "";
      this.expandedKey = null;
    },
    async doSearch() {
      const q = (this.searchQuery || "").trim();
      if (!q) {
        this.resetSearch();
        return;
      }
      try {
        const data = await this.api(`/api/search?q=${encodeURIComponent(q)}`);
        const results = data.results || [];
        this.searchHits = new Set(results.map((r) => r.hash));
        // 实际归组的种子由分组筛选展示; 未归组的命中(分组未启用/文件列表不可读)单独兜底
        const grouped = new Set();
        for (const g of this.groups) for (const m of g.members) grouped.add(m.hash);
        this.searchUncovered = results.filter((r) => !grouped.has(r.hash));
        this.searchBuilding = !!data.building;
        this.searchError = "";
        if (this.searchBuilding) {
          // 文件索引构建中(增量限流可能需多轮): 1s 后自动重查, 直至 building 消除
          if (this.searchTimer) clearTimeout(this.searchTimer);
          this.searchTimer = setTimeout(() => this.doSearch(), 1000);
        }
      } catch (e) {
        // 不再静默(否则与"无匹配结果"无法区分): 401 由 api() 回登录框, 其余在搜索框旁提示
        if (!e.auth) {
          const msg = e.message || "搜索失败";
          this.resetSearch();
          this.searchError = msg;
        }
      }
    },
    fmtSpeed(v) {
      if (!v) return "0 B/s";
      for (const [unit, div] of [["GiB/s", 1073741824], ["MiB/s", 1048576], ["KiB/s", 1024]]) {
        if (v >= div) return (v / div).toFixed(2) + " " + unit;
      }
      return v + " B/s";
    },
    fmtSize(v) {
      if (v === null || v === undefined) return "-";
      if (!v) return "0 B";
      for (const [unit, div] of [["PiB", 2 ** 50], ["TiB", 2 ** 40], ["GiB", 2 ** 30], ["MiB", 2 ** 20], ["KiB", 2 ** 10]]) {
        if (v >= div) return (v / div).toFixed(2) + " " + unit;
      }
      return v + " B";
    },
    fmtDuration(sec) {
      // 做种时长: 后端已按分钟取整(torrents._VIEW_QUANTUM), 故不展示秒位
      sec = Math.floor(sec || 0);
      if (sec < 3600) return `${Math.floor(sec / 60)}分钟`;
      if (sec < 86400) return `${Math.floor(sec / 3600)}时${String(Math.floor((sec % 3600) / 60)).padStart(2, "0")}分`;
      return `${Math.floor(sec / 86400)}天${String(Math.floor((sec % 86400) / 3600)).padStart(2, "0")}时`;
    },
    kindText(kind) {
      return { seeding: "做种", downloading: "下载", checking: "校验中", paused: "已暂停", error: "错误", other: "其他" }[kind] || kind;
    },
    sumField(members, key) {
      return members.reduce((n, m) => n + (m[key] || 0), 0);
    },
    sumDl(g) {
      return this.sumField(g.members, "dlspeed");
    },
    sumUl(g) {
      return this.sumField(g.members, "upspeed");
    },
    setSort(key) {
      if (this.sortKey === key) {
        this.sortDir = -this.sortDir;
      } else {
        this.sortKey = key;
        this.sortDir = -1;
      }
    },
    sortArrow(key) {
      if (this.sortKey !== key) return "";
      return this.sortDir === 1 ? "▲" : "▼";
    },
    toggleExpand(key) {
      this.expandedKey = this.expandedKey === key ? null : key;
      this.menu.visible = false;
    },
    openMenu(event, group) {
      event.preventDefault();
      if (group.virtual) {
        // 虚拟行(未归组命中种子): 无真实组 key(组级路由会解析失败), 退化为该种子的单种子菜单
        this.openMemberMenu(event, group.members[0]);
        return;
      }
      this.menu = { visible: true, ...this._menuPos(event), key: group.key, hash: null };
      this.expandedKey = group.key;
    },
    openMemberMenu(event, member) {
      event.preventDefault();
      event.stopPropagation();
      this.menu = { visible: true, ...this._menuPos(event), key: null, hash: member.hash };
    },
    // 命令 => 中文动作名(用于投递成功/失败的提示文案)
    _actionText(action) {
      return { pause: "暂停", resume: "开始", reannounce: "强制汇报", delete: "删除" }[action] || action;
    },
    async act(action) {
      this.menu.visible = false;
      if (!this.menu.key) return;
      try {
        await this.api(`/api/groups/${this.menu.key}/${action}`, { method: "POST" });
        this.toast(`已投递: ${this._actionText(action)}整组`, "ok", 2500);
      } catch (e) {
        if (!e.auth) this.toast("命令发送失败: " + e.message, "error");
      }
    },
    async delWithFiles(deleteFiles) {
      this.menu.visible = false;
      if (!this.menu.key) return;
      const ok = await this.confirmDialog(
        deleteFiles ? "删除整组(含磁盘文件)" : "删除整组",
        deleteFiles
          ? "将删除整组种子及其磁盘文件, 此操作不可恢复。"
          : "将删除整组种子, 保留磁盘文件。",
        { okText: deleteFiles ? "删除并移除文件" : "删除", danger: true }
      );
      if (!ok) return;
      try {
        await this.api(`/api/groups/${this.menu.key}/delete`, {
          method: "POST",
          body: JSON.stringify({ delete_files: deleteFiles }),
        });
        this.toast(`已投递: 删除整组${deleteFiles ? "(含文件)" : ""}`, "ok", 2500);
      } catch (e) {
        if (!e.auth) this.toast("删除命令发送失败: " + e.message, "error");
      }
    },
    async actTorrent(action) {
      this.menu.visible = false;
      if (!this.menu.hash) return;
      try {
        await this.api(`/api/torrents/${this.menu.hash}/${action}`, { method: "POST" });
        this.toast(`已投递: ${this._actionText(action)}该种子`, "ok", 2500);
      } catch (e) {
        if (!e.auth) this.toast("命令发送失败: " + e.message, "error");
      }
    },
    async delTorrent(deleteFiles) {
      this.menu.visible = false;
      if (!this.menu.hash) return;
      const ok = await this.confirmDialog(
        deleteFiles ? "删除该种子(含磁盘文件)" : "删除该种子",
        deleteFiles
          ? "将删除该种子及其磁盘文件, 此操作不可恢复。"
          : "将删除该种子, 保留磁盘文件。",
        { okText: deleteFiles ? "删除并移除文件" : "删除", danger: true }
      );
      if (!ok) return;
      try {
        await this.api(`/api/torrents/${this.menu.hash}/delete`, {
          method: "POST",
          body: JSON.stringify({ delete_files: deleteFiles }),
        });
        this.toast(`已投递: 删除该种子${deleteFiles ? "(含文件)" : ""}`, "ok", 2500);
      } catch (e) {
        if (!e.auth) this.toast("删除命令发送失败: " + e.message, "error");
      }
    },
    gridStyle(page) {
      const defaults = page === "group" ? GROUP_DEFAULT_COLS : DETAIL_DEFAULT_COLS;
      const cols = (this.colWidths[page] || []).filter((v) => /^\d+px$/.test(v));
      // 记忆列数与默认列数不一致(结构变更)时回退默认, 防非法模板破坏布局
      const template = cols.length === defaults.length ? cols.join(" ") : null;
      return { gridTemplateColumns: template || defaults.join(" ") };
    },
    startResize(event, page, idx) {
      // 列宽拖拽: 从列头行(真正的 grid 容器)读取渲染列宽固化为 px, 拖动更新并写入 localStorage(记忆)
      const headEl = event.target.closest(".group-head") || event.target.closest(".detail-head");
      if (!headEl) return;
      const rendered = (getComputedStyle(headEl).gridTemplateColumns || "")
        .split(" ")
        .map((v) => parseFloat(v))
        .filter((v) => !isNaN(v) && v > 0);
      if (!rendered.length || idx >= rendered.length) return;
      const startX = event.clientX;
      const cols = this.colWidths[page] && this.colWidths[page].length === rendered.length
        ? [...this.colWidths[page]]
        : rendered.map((v) => `${Math.round(v)}px`);
      const startVal = parseFloat(cols[idx]) || rendered[idx] || 100;
      this.resizing = { page, idx, startX, startVal };
      const move = (e) => {
        const width = Math.max(60, Math.round(this.resizing.startVal + e.clientX - this.resizing.startX));
        cols[this.resizing.idx] = `${width}px`;
        this.colWidths = { ...this.colWidths, [page]: [...cols] };
      };
      const up = () => {
        document.removeEventListener("mousemove", move);
        document.removeEventListener("mouseup", up);
        localStorage.setItem(COLS_STORE_KEY, JSON.stringify(this.colWidths));
      };
      document.addEventListener("mousemove", move);
      document.addEventListener("mouseup", up);
    },
  },
});

// 图形化配置编辑器以全局 mixin 注入(设置页控件/状态/接口全在其中)
app.mixin(window.CONFIG_EDITOR);
app.mixin(window.CONFIG_RULES);
app.component("ce-field", window.CE_FIELD_COMPONENT);
app.mount("#app");
