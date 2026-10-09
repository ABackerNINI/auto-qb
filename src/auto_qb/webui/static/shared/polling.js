/* polling.js — 轮询与推送域(startEvents/stopEvents/startPolling/stopPolling/scheduleNext/
 * basePollMs/currentPollMs/refresh): W2b 自 app.js 拆出, 全局 mixin 方法域。 */
/* SSE 断线沿判定(纯函数, 探针真跑, 同 lifecycle.js _errlogReseed 先例): prev 为已持
 * connected 位(undefined=本会话尚未连上过 / true=在连 / false=断线重试期), 返回是否
 * 处于「断线沿」—— 首次断线或 true→false 跳变。重试期内重复 onerror(prev=false)与
 * 恢复成功(prev=true)都不是沿, 不发 toast。 */
function _esDisconnectEdge(prev) {
  return prev !== false;
}

window.AQB_POLL = {
  methods: {
    /* ---------------- P2 事件驱动(SSE /api/events) ----------------
     * 目的: 把「命令回执」与「视图版本变更」从轮询改成推送 ——
     *   前者省掉回执轮询的退避粒度(0→150→300→500ms), 后者省掉 1.5/2/3s 的定时触发。
     * !轮询**保留**作为兜底: 断线 / 首帧 / 浏览器不支持 / 反代缓冲时自动退回, 语义不变。
     * WARN: EventSource 发不出 Authorization 头 ⇒ 先用带鉴权的 POST /api/events/ticket 换
     *   **一次性短时票据**再以 ?ticket= 连流(26-10-02 加固: 查询串不再放长期密钥 ——
     *   反代日志只会留下用完即弃的票据); 本机 skip_local_verify(默认)下换票免密钥。
     */
    async startEvents() {
      if (this._es || this._esBusy || typeof EventSource === "undefined") return;
      this._esBusy = true;  // 换票是异步的, 防重入(async 后 if(this._es) 挡不住并发进入)
      let ticket = "";
      try {
        const r = await this.api("/api/events/ticket", { method: "POST" });
        ticket = (r && r.ticket) || "";
      } catch (e) {
        this._esBusy = false;
        return;  // 换票失败(未鉴权/服务不可达): 不开推送, 轮询兜底照旧
      }
      this._esBusy = false;
      if (!ticket) return;
      let es = null;
      try {
        es = new EventSource(`/api/events?ticket=${encodeURIComponent(ticket)}`);
      } catch (e) {
        return;  // 不支持就用轮询, 不报错(推送是加速手段, 不是必需)
      }
      this._es = es;
      es.addEventListener("cmd", (e) => {
        // 命令回执: 兑现 commands.js 里等待这条命令的 Promise(省掉轮询粒度)
        try { this.onCmdEvent(JSON.parse((e && e.data) || "{}")); } catch (_) { /* 坏帧忽略 */ }
      });
      es.addEventListener("truth", (e) => {
        // 真值事件: 服务端确认命令已生效后推来; 前端据此把行换成真值并结束值覆盖
        // (见 commands.js onTruthEvent —— 服务端只在真值落地时才推, 所以可以放心采纳)
        try { this.onTruthEvent(JSON.parse((e && e.data) || "{}")); } catch (_) { /* 坏帧忽略 */ }
      });
      es.addEventListener("ver", (e) => {
        // 只带版本号、**不含数据** —— 收到后拉一次 /api/state。密集发布时去抖合并,
        // 免得一轮 sync 触发 N 次全量拉取(3000 种子一轮 63ms, 打满主线程的坑踩过)。
        if (this._verTimer) clearTimeout(this._verTimer);
        this._verTimer = setTimeout(() => { this._verTimer = null; this.refresh(); }, 60);
      });
      es.onopen = () => {
        // 恢复成功: 只回置状态位, 静默不广播(断线提示只在断线沿发, 不发"已恢复"噪音)
        this._esConnected = true;
      };
      es.onerror = () => {
        // 断线沿(WEBUI 通知 S6, D2 拍板): 以 _esConnected 取沿, 首次断线或
        // true→false 跳变时发一条 error toast —— 经 toast() 内的 _recordErrorToast
        // 钩子自动进通知(挂机型断线自此可追溯); 重试期内重复 onerror 不重复发。
        if (_esDisconnectEdge(this._esConnected)) {
          this._esConnected = false;
          this.toast("与服务的推送连接断开, 正在自动重连…", "error");
        }
        // 一次性票据在重连时必失效(服务端取即删) —— EventSource 自带重连会一直拿旧票
        // 撞 401, 必须关掉旧连接换新票重开(3s, 与 EventSource 默认重连同拍); 服务不可达时
        // 换票请求失败, startEvents 直接返回, 不会空转
        if (this._es) { this._es.close(); this._es = null; }
        if (this._esRetry) return;
        this._esRetry = setTimeout(() => {
          this._esRetry = null;
          if (this.authOk) this.startEvents();
        }, 3000);
      };
    },
    stopEvents() {
      if (this._esRetry) { clearTimeout(this._esRetry); this._esRetry = null; }
      if (this._verTimer) { clearTimeout(this._verTimer); this._verTimer = null; }
      if (this._es) { this._es.close(); this._es = null; }
      this._esConnected = undefined;  // 断线沿状态位随连接会话归置: 重登后首断仍算「首次断线」
    },
    startPolling() {
      this.stopPolling();
      this.startEvents();  // P2: 先接上推送通道(失败也无害, 轮询仍在)
      this.loadSpeedMode();  // 限速托管状态(非轮询: 登录/重连时取一次, 卡内可手动刷新)
      // 键盘快捷键服务端真值(W6, 计划 26-09-28-0354 §4.4): 同为两条登录路径的唯一汇合点,
      // 鉴权已放行请求必带得上凭证; 失败静默回默认表(不阻塞登录), 打开面板时会重拉一次
      this._kbReloadKeys(true);
      // 状态栏常显统计(server_state)已随 /api/state.status.server 每轮回传 —— 登录首轮的
      // refresh() 即可填上, 不再需要为"限制速度/连接/剩余"单独补一次 /api/stats(FX-08 旧做法)。
      this.refresh();
      /* 刷新后停在设置页(page 持久化, 见 initialPage): 配置树是**按需加载**的
       * (cfgLoad 只在 openSettings / 页内"重试"里调) —— 不在这里补一次, 首屏就停在
       * 「配置加载失败 + 重试」(cfg.schema 永远为 null)。
       * 放在 startPolling 里是因为它是两条登录路径(本机免鉴权 / 密钥验证通过)的**唯一汇合点**,
       * 到这儿鉴权已放行, 这次请求必定带得上凭证。 */
      if (this.page === "settings" && !this.cfg.schema && !this.cfg.loading) this.cfgLoad();
    },
    stopPolling() {
      if (this.pollTimer) clearTimeout(this.pollTimer);
      this.pollTimer = null;
    },
    scheduleNext() {
      // 用 setTimeout 链式续排(而非 setInterval): 保证上一轮请求结束后再计时, 不堆叠请求
      this.stopPolling();
      if (document.hidden || !this.authOk) return;  // R10-01: 按鉴权模式判断(本机免鉴权下 token 为空)
      this.pollTimer = setTimeout(() => this.refresh(), this.currentPollMs());
    },
    /* P1 落地后按种子量分档(2026-09-19)。档位是**实测**定的, 不是拍的 —— 用
     * scripts/ui_harness.py + e2e/perf.spec.mjs 的 A/B 量出"窗口化后单轮 refresh 的真实耗时":
     *   1000 种子 143ms | 3000 种子 309ms | 5000 种子 396~501ms
     * 再把每档的**主线程占用率**压到 ~15% 上下(单轮耗时 / 间隔; 分档断言见 e2e/views.spec.mjs), 于是:
     *   ≤1000 → 1.5s(≈10%)  1000~3000 → 2s(≈15%)  >3000 → 3s(≈17%)
     * 两个边界条件: 1.**下界 1.5s = 服务端 sync_interval** —— 后端每 1.5s 才刷一次数据,
     *   再快也只是多拿一次"版本未变"的空响应(此时响应体趋近于零, 但不产生新数据);
     * 2.**不是"无变化退避"** —— 那只按 rid 是否变化放慢, 会把行数据新鲜度直接卖掉(见下)。
     */
    basePollMs() {
      const n = this.status && this.status.torrents;
      if (typeof n !== "number") return 2000;  // 总量未知(首轮/异常): 取中间档, 不冒进
      if (n > 3000) return 3000;
      if (n > 1000) return 2000;
      return 1500;  // 与服务端 sync_interval 对齐; 大库才往上让
    },
    currentPollMs() {
      // 失败退避: 连续失败翻倍至上限 15s(减少服务不可达时的空转)
      if (this.pollFails) return Math.min(15000, this.basePollMs() * 2 ** this.pollFails);
      // 恒定间隔(按种子量分档), **不做"无变化退避"**: 曾按"视图版本未变"逐步放慢(2s→5s→10s),
      // 但状态栏的全局速度走 /api/stats(不受 rid 门控, 每轮都刷)⇒ 两个速度来源刷新频率被解耦,
      // 观感上变成"状态栏正常、种子行滞后"。版本未变时响应体已趋近于零(不回传 groups),
      // 退避省不下什么, 却直接牺牲行数据新鲜度 —— 收益与代价不对等, 故只保留失败退避。
      return this.basePollMs();
    },
    /* 单一合并入口(plan 26-10-07-0414 S4, R6): 全量/增量两分支共用, 供 refresh() 调用。
     * 顺序安全事实(起草人已核): 三视图渲染入口各自客户端排序(sort.js sortedGroups /
     * filters.js filteredTorrents / shows.js decoratedShows), 服务端数组顺序不承载语义,
     * delta 追加行不需保序; 明细表 sortedMembers 空键=后端原序, 但 members 随整行 upsert
     * 原样携带(R8), 不受影响 —— 镜子测试因此按「行键集合 + 行内容」比较, 不比数组顺序。 */
    applyStateRows(payload) {
      /* delta 分支(payload.full === false, S3 协商): 行级 upsert(整行替换/追加, R8)
       * + removed 剔除。行键: torrents/singles=hash, groups/shows=key; 未脏行对象引用
       * 原样保留(不新建, :159-160 既有纪律); 数组以新实例赋回(Vue 数据流不变)。
       * 桶键不存在 = 该视图不回传这份(同全量分支「键不存在必须保留原引用」的纪律)。
       * 服务端 R5 已保证 removed 与 upsert 不交; 万一同时出现以 upsert 为准(行仍在,
       * 行内容=服务端当前真值), 删不存在的行本就是幂等 no-op(见 S3 removed.singles 注)。 */
      if (payload.full === false) {
        const d = payload.delta || {};
        const r = payload.removed || {};
        // 行级 apply 子函数(两分支共用的落点: full 分支的整表替换在 R6 语义上等价于
        // 「清空重放」, 无需行级 apply; 此处只服务 delta 的 upsert/剔除):
        const applyRows = (cur, keyField, ups, rms) => {
          if (!ups.length && !rms.length) return cur;  // 恒在但本轮无变化: 原引用不动
          const upMap = new Map();
          for (const row of ups) upMap.set(row[keyField], row);
          const rmSet = new Set(rms);
          const out = [];
          const seen = new Set();
          for (const row of cur) {
            const k = row[keyField];
            seen.add(k);
            const up = upMap.get(k);
            if (up !== undefined) { out.push(up); continue; }  // 脏行: 整行替换为新实例
            if (rmSet.has(k)) continue;                        // 已删行: 剔除
            out.push(row);                                     // 未脏行: 引用原样保留
          }
          for (const row of ups) if (!seen.has(row[keyField])) out.push(row);  // 新行追加(顺序不承载语义, 见上)
          return out;
        };
        if (d.torrents || r.torrents) this.torrents = applyRows(this.torrents, "hash", d.torrents || [], r.torrents || []);
        if (d.singles || r.singles) this.singles = applyRows(this.singles, "hash", d.singles || [], r.singles || []);
        if (d.groups || r.groups) this.groups = applyRows(this.groups, "key", d.groups || [], r.groups || []);
        // shows 桶(S3 期 view=show 恒全量, 此处不可达; S8/S9 接线前的通用合并):
        // shows 是 {list, unrecognized} —— list 按剧键行级合并, unrecognized 不动。
        if (d.shows || r.shows) {
          this.shows = {
            list: applyRows(this.shows.list || [], "key", d.shows || [], r.shows || []),
            unrecognized: this.shows.unrecognized,
          };
        }
        // 真值快照行源: 把 delta 桶按 _snapshotTruth 迭代的**同名键**挂回本响应对象 ——
        // 快照的「只认这一轮 payload 真的带来的行」口径原样成立(增量轮只比脏行), 调用点
        // `this._snapshotTruth(state)` 字面量不动(tests/test_webui_static_skins.py::_scan_pending_settle 钉住)。
        // WARN: 此后本函数作用域内的 state.torrents/singles/groups 只代表**增量行**, 不代表
        // 全量 —— 下游不得再当全量读(现调用点之后无人读它们)。
        if (d.torrents) payload.torrents = d.torrents;
        if (d.singles) payload.singles = d.singles;
        if (d.groups) payload.groups = d.groups;
        return payload;
      }
      // full 分支(含未协商的旧服务端响应: 无 full 键 ⇒ 走这里, 行为与 S3 之前逐字节等价)
      // = 清空重放(R6)。P1-1: 服务端只回当前视图的数组 —— **键不存在时必须保留原引用**,
      // 绝不能 `|| []` 清空(否则每次轮询都把另外两个视图抹成空, 切回去要等一轮全量)。
      if (payload.groups !== undefined) this.groups = payload.groups;
      if (payload.singles !== undefined) this.singles = payload.singles;  // 未归组种子(搜索兜底/总数回退)
      if (payload.torrents !== undefined) this.torrents = payload.torrents;  // 种子页平铺数组(SEED_ITEM)
      if (payload.shows !== undefined) this.shows = payload.shows;  // 追剧视图(R10)
      return payload;
    },
    async refresh() {
      try {
        // rid 增量: 带上已持有的视图版本, 服务端版本未变时不回传数组(响应体趋近于零)。
        // P1-1: 同时带上当前视图名, 服务端只回该视图需要的数组(响应体 ≈1/4)。
        // 切视图时 goView 会把 lastRid 置空 ⇒ 强制取一次全量, 别的视图不会停在旧数据上。
        // delta=1(plan S4, P-05 定案: 默认开、不加配置键): 声明客户端懂增量协议 ——
        //   服务端 rid 落在时间线窗口内时回增量载荷(full=false), 本地由 applyStateRows
        //   行级合并; 窗外/降级/切视图后 lastRid 已置空 ⇒ 服务端恒回全量(full=true), 天然兼容。
        const qs = [];
        if (this.lastRid !== null) qs.push(`rid=${this.lastRid}`);
        if (this.viewMode === "torrents") qs.push("view=torrent");
        else if (this.viewMode === "shows") qs.push("view=show");
        else qs.push("view=group");
        qs.push("delta=1");
        const query = `?${qs.join("&")}`;
        const state = await this.api("/api/state" + query);
        this.status = state.status;
        // qB 全局状态(server_state)随 status **恒回传**(与 traffic 同口径: 不受 rid 门控) ——
        // 状态栏常显统计与"限制速度"取它, 不再单独打 /api/stats ⇒ 每轮只剩 1 条请求,
        // 且状态栏与行数据**同源同轮**(不再出现"状态栏新鲜 / 种子行滞后"的错位观测)。
        if (state.status && state.status.server !== undefined) this.statsServer = state.status.server || null;
        if (state.updated !== false) {
          // P0-0 埋点: 这段赋值 + 多选交集是"点了没反应"里唯一发生在前端的部分,
          // 超过 50ms 就在控制台留痕 —— 大库下这是 P1(行窗口化)要不要做的直接判据。
          const _t0 = performance.now();
          // 视图有变化: 记录新版本; 无变化时保留原数组, 不触发重渲染。
          // S4(R6): 数组合并收敛进单一入口 applyStateRows —— full 分支整表替换(清空重放,
          // 与历史行为逐字节等价) / delta 分支行级 upsert+removed 剔除; 之后的多选交集/
          // 展开态回验/乐观值重贴等保留机制两条路共用, 时序约束不变。
          this.applyStateRows(state);
          if (typeof state.rid === "number") this.lastRid = state.rid;  // lastRid 恒 = 最后收到的 rid
          // !必须在 reapplyPending **之前**: 快照要的是服务端原始值(delta 轮 state 的
          // torrents/singles/groups 已被 applyStateRows 换成 delta 桶 —— 快照同样只比
          // 这一轮 payload 真的带来的行, 见 _snapshotTruth 注)。
          this._snapshotTruth(state);
          // 增量替换后按现存 key/hash 交集保留多选(避免轮询把用户选择清空);
          // 虚拟行 key(u-<hash>)不做存在性校验(搜索视图由 filteredGroups 重建)
          if (this.selectedCount) {
            const keys = new Set(this.groups.map((g) => g.key));
            const hashes = new Set(this.groups.flatMap((g) => g.members.map((m) => m.hash)));
            for (const r of this.singles) hashes.add(r.hash);
            for (const r of this.torrents) hashes.add(r.hash);  // 平铺数组 = 全量种子(超集, 覆盖种子页多选)
            this.selGroups = this.selGroups.filter((k) => keys.has(k) || k.startsWith("u-"));
            this.selMembers = this.selMembers.filter((h) => hashes.has(h));
          }
          this.renderMs = Math.round((performance.now() - _t0) * 10) / 10;
          if (this.renderMs > 50) console.warn(`[perf] 单轮视图赋值 ${this.renderMs}ms(>50ms)` +
            ` —— 稳态应远低于此; 首次切视图要全量渲染一帧量行高, 那一帧超属预期(P1-2 已落地)`);
        }
        this._expirePending();    // !先回滚超时的(不回滚会留永久假状态, issue 26-09-19-2141)
        this.reapplyPending();    // P0-3: 整表替换后把仍 pending 的乐观值重新贴上
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
  },
};
