/* auth.js — HTTP 与鉴权域(api/_request/_logout/bootstrap/saveToken/retryAuth):
 * W2b 自 app.js 拆出, 全局 mixin 方法域(与既有 AQB_* 同范式, this 同一实例)。 */
window.AQB_AUTH = {
  methods: {
    async api(path, options = {}) {
      if (!this.authOk) {
        // 无凭证不出网: 否则会发出 "Bearer " 空头(被 HTTP 层裁剪成裸 "Bearer"),
        // 后端白记一次 401。调用方按 401 同路径处理(回密钥输入界面/静默)。
        // R10-01: 判据改为**鉴权模式**而非"密钥串非空" —— 本机免鉴权下 token 为空是合法状态。
        this._logout();
        const noAuth = new Error("unauthorized");
        noAuth.auth = true;
        throw noAuth;
      }
      return this._request(path, options, this.token);
    },
    async _request(path, options, token) {
      // R10-01: **无密钥就不带 Authorization 头**(本机免鉴权模式)。旧实现无条件拼
      // `Bearer ${token}`, token 为空时发出裸 "Bearer", 而后端的免鉴权分支会把它当"未带凭证"
      // 每次请求记一条 WARNING(噪音); 带上真实密钥时后端也是忽略, 两种都不如干脆不发。
      const headers = { "Content-Type": "application/json", ...(options.headers || {}) };
      if (token) headers.Authorization = `Bearer ${token}`;
      const resp = await fetch(path, { ...options, headers });
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
      this.bootstrapping = false;
      this.pendingToken = "";
      this.token = "";
      localStorage.removeItem("autoqb_token");
      this.stopPolling();
      if (this.searchTimer) clearTimeout(this.searchTimer);  // 登出后停掉搜索防抖/重试, 防空头竞态
      this.searchTimer = null;
      this.groups = [];
      this.status = {};
      this.lastRid = null;
      this.pollFails = 0;
      this.serviceDown = false;
      this.expandedKey = null;
      this.expandMemo = { groups: null, shows: null };  // 跨视图暂存同属受保护内容, 一并清(换账号不该带回来)
      this.kindFilter = "";
      this.pathFilter = [];
      this.tagFilter = [];
      this.categoryFilter = [];
      this.siteFilter = [];
      this.hrFilter = [];
      this.singles = [];
      this.torrents = [];
      this.shows = { list: [], unrecognized: [] };
      this.expandedShows = [];
      this.expandedShowEp = null;
      this.filterMenu = "";
      this.colMenuOpen = false;
      this.toasts = [];
      this.modal = this._modalInit();
      this._modalResolve = null;
      this.clearSelection();
      this.historyOpen = false;
      this.histHoverIdx = -1;
      this.qbHistOpen = false;  // qB 口径流量图弹层(P5a): 受保护内容一并清(组件实例随 _qbChartDestroy 收尾)
      this.qbHistHoverIdx = -1;
      this.qbHistData = null;
      // qB 口径流量图 S5b 两挂点(分组弹层/抽屉流量页签): 受保护内容与轮询定时器一并清
      // (轮询只挂打开期间, 登出必须拆干净 —— 不留对 /api/traffic/qb/* 的后台请求)
      this._qbPollStop("global");
      this._qbPollStop("torrent");
      this._qbPollStop("group");
      this.qbGroupOpen = false;
      this.qbGroupHoverIdx = -1;
      this.qbGroupData = null;
      this.qbTorrentHoverIdx = -1;
      this.qbTorrentData = null;
      this.statsOpen = false;
      this.statsServer = null;
      this.statsError = "";
      this.mgrOpen = "";
      this.mgrBusy = false;
      this.metaOpen = false;
      this.metaBusy = false;
      this.logs = { loading: false, error: "", loaded: false, lines: [], file: "", open: false, note: "", level: "", num: 300 };
      this.speedMode = { loaded: false, curveEnabled: false, target: null, current: null, error: "" };
      this.speedOverride = { up: "", down: "", busy: false };
      this.speedOpen = false;
      this.speedAt = { left: 0, dir: "up" };
      this.cfgReset();  // 配置树同样是受保护内容, 一并清除(编辑器状态复位)
      this.page = "groups";
      this.searchQuery = "";
      this.resetSearch();
      if (message) {
        this.authError = message;
        this.authErrorKind = "auth";
      }
    },
    async bootstrap(candidate) {
      if (this.authPending) return;  // 防重复提交(验证中按钮已禁用, 双保险)
      this.authPending = true;
      this.authError = "";
      this.authErrorKind = "";
      this.pendingToken = candidate;
      this.lastRid = null;  // 重新鉴权/换密钥: 强制全量取一次分组视图
      try {
        // 用候选密钥直接验证: 成功前 this.token 不提交、authRequired 不解除, 主界面 DOM 绝不渲染
        const state = await this._request("/api/state", {}, candidate);
        this.status = state.status;
        this.groups = state.groups || [];
        this.singles = state.singles || [];
        this.torrents = state.torrents || [];
        this.shows = state.shows || { list: [], unrecognized: [] };
        if (typeof state.rid === "number") this.lastRid = state.rid;
        this.serviceDown = false;
        this.token = candidate;  // 验证通过才提交为当前身份
        this.authMode = "token";  // R10-01: 显式声明身份来源(覆盖可能残留的 local 模式)
        this.authRequired = false;  // 唯一放行点
        localStorage.setItem("autoqb_token", candidate);
        this.pendingToken = "";
        this.tokenInput = "";
        this.startPolling();
        this.loadWebFlags();  // R2(计划 26-10-02-1955 W1): 登录成功取一次功能旗标(方法在 lifecycle.js); 失败保持 false = fail-closed
      } catch (e) {
        if (!e.auth) {
          // 服务不可达 ≠ 密钥错误: 不否定候选密钥(本地存储亦保留), 给出重试入口, 防误清凭证
          this.authError = "服务不可用, 请确认 auto-qb 程序正在运行";
          this.authErrorKind = "unavailable";
        }
        // e.auth(401/无凭证): _request 已走 _logout() 完成遮罩/数据/文案收口
      } finally {
        this.authPending = false;
        this.bootstrapping = false;  // 验证结束(成功进主界面/失败回表单), 卸载加载态
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
  },
};
