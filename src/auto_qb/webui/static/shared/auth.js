/* auth.js — HTTP 与鉴权域(api/_request/_logout/bootstrap/saveToken/retryAuth):
 * W2b 自 app.js 拆出, 全局 mixin 方法域(与既有 AQB_* 同范式, this 同一实例)。 */
/* 请求级超时(2026-10-16, issue 26-10-16-0954-bug-webui-chart-fetch-no-timeout):
 * 裸 `fetch()` **没有超时** —— 连接静默失效(服务端不响应 / TCP 半开 / 中间设备丢包)时 await
 * 永不返回, 调用方的 finally 整条失效: 流量图的 loading 恒真 ⇒ 轮询守卫把自己挡死(图表永久停在
 * 旧帧、无提示); polling.js 的 refresh 更彻底 —— 它 await 之后才 scheduleNext(), 悬挂即永久停表。
 * 给每次请求挂 AbortController + 上限, 把「悬挂」变成一次**可报的失败**, finally / 错误态路径照常走。
 * 取值 15s: 本机 WEBUI 直连(127.0.0.1)正常响应亚秒级, 后端路由另有自身超时与降级返回(meta.stale),
 * 全仓最重的 /api/state 全量轮也是秒级 —— 15s 只兜「连接层静默失效」这一类, 不误杀慢查询。
 * !不做 per-call 覆盖: 重活都走 waitCmd 的异步命令回执(POST 立即返回 cmd_id, 40s 是**前端等待
 * 上限**而非单次请求时长), 60 余个 api() 调用点无一需要更长预算。
 * 顶层只声明常量, 不碰 DOM/BOM(本文件会被测试的 node 探针 eval)。 */
const AQB_FETCH_TIMEOUT_S = 15;  // 秒; 定时器与超时文案同源(改一处两处生效, 不手抄两份)
const AQB_FETCH_TIMEOUT_MS = AQB_FETCH_TIMEOUT_S * 1000;
/* Authorization 头单点(收敛 issue 26-10-20-2231 / 台账 R20-F-04): 鉴权头形态(前缀大小写 /
 * 双头 / 凭据来源)只此一处。无 token 不发头(R10-01 本机免鉴权, 见 _request 注释)。
 * !顶层函数而非 mixin 方法: 快捷键密钥适配器(shortcuts.js 的 AQB_KEYS_ADAPTER)不是 Vue
 *   mixin 单例, 拿不到 this —— 与 aqbFetch(fetch_low.js)同款裸调形态。
 *   调用侧**禁止内联** `Bearer ${token}`。 */
function aqbAuthHeaders(token) {
  return token ? { Authorization: `Bearer ${token}` } : {};
}
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
      const headers = { "Content-Type": "application/json", ...aqbAuthHeaders(token), ...(options.headers || {}) };
      // 请求级超时(见 AQB_FETCH_TIMEOUT_MS): 超时与外部 signal 都收敛到同一个 controller;
      // 定时器无论成功/失败都在 finally 清掉(不留悬挂定时器)。外部 signal 用**链接**而不是覆盖 ——
      // 今天全仓无人传 signal, 这层是防「将来加取消时被本函数的 signal 静默顶掉」。
      const ctl = new AbortController();
      let timedOut = false;
      const timer = setTimeout(() => {
        timedOut = true;
        ctl.abort();
      }, AQB_FETCH_TIMEOUT_MS);
      const ext = options.signal;
      if (ext) {
        if (ext.aborted) ctl.abort();
        else ext.addEventListener("abort", () => ctl.abort(), { once: true });
      }
      try {
        const resp = await fetch(path, { ...options, headers, signal: ctl.signal });
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
        return await resp.json();
      } catch (e) {
        // AbortError 的原始文案("The operation was aborted")对用户没有信息量, 也分不出超时与取消:
        // 统一翻译成中文短句(超时带秒数)并打标记 —— 调用方的错误态直接显示它, 零新增 UI 就有提示。
        // fetch 与 body 读取都可能被中止, 两类都在这一处判定。
        if (e && e.name === "AbortError") {
          const err = new Error(timedOut ? "请求超时(" + AQB_FETCH_TIMEOUT_S + "s)" : "请求已取消");
          err.timeout = timedOut;
          throw err;
        }
        throw e;
      } finally {
        clearTimeout(timer);
      }
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
      // qB 口径流量图三挂点(2026-10-04 并入底部详情抽屉): 受保护内容与轮询定时器一并清
      // (轮询只挂打开期间, 登出必须拆干净 —— 不留对 /api/traffic/qb/* 的后台请求);
      // 抽屉若停在流量形态也一并收起 —— _qbTeardown 单点停三挂点轮询 + 销毁三挂点图
      this.qbHistHoverIdx = -1;
      this.qbHistData = null;
      this.qbGroupHoverIdx = -1;
      this.qbGroupData = null;
      this.qbTorrentHoverIdx = -1;
      this.qbTorrentData = null;
      this.drawer.open = false;
      this._qbTeardown();
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
        this.transferTargetsReload();  // T6(计划 26-10-31-0306): 预拉转移目标缓存(右键菜单「转移到」读侧; 方法在 transfer_flow.js)
        this._pullErrlogBoot();  // 通知 S3: 密钥路径的开页全量合并(方法在 lifecycle.js; 本机免鉴权路径在 lifecycle mounted)
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
