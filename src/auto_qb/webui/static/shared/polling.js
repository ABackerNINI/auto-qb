/* polling.js — 轮询与推送域(startEvents/stopEvents/startPolling/stopPolling/scheduleNext/
 * basePollMs/currentPollMs/refresh): W2b 自 app.js 拆出, 全局 mixin 方法域。 */
/* SSE 断线沿判定(纯函数, 探针真跑, 同 lifecycle.js _errlogReseed 先例): prev 为已持
 * connected 位(undefined=本会话尚未连上过 / true=在连 / false=断线重试期), 返回是否
 * 处于「断线沿」—— 首次断线或 true->false 跳变。重试期内重复 onerror(prev=false)与
 * 恢复成功(prev=true)都不是沿, 不发 toast。 */
function _esDisconnectEdge(prev) {
  return prev !== false;
}

/* 在途悬挂兜底阈值(2026-10-22 由 qb_traffic_chart.js 的 _QB_LOAD_STALL_MS 上提到轮询骨架 ——
 * 抽屉侧此前没有这一层, 同一类"loading 卡死即永久挡拍/冻结"缺陷只修了一边)。
 * 取值 30s = 请求级超时(auth.js AQB_FETCH_TIMEOUT_MS, 15s)的两倍余量: 正常在途请求(哪怕正好被
 * 请求级超时兜到)不会命中 —— 只有"连 abort 都没能让 finally 跑起来"才走这里, 是兜底的兜底。
 * 跨文件不变式: AQB_POLL_STALL_MS >= AQB_FETCH_TIMEOUT_MS(守阵 test_frontend_api_request_timeout)。 */
const AQB_POLL_STALL_MS = 30000;

/* P-02 二期 S2a ingestion 物化的缺项待补队列(计划 26-11-11-0630 §03): key(组行 key) ->
 * 组行裸对象。物化时某个成员 hash 在索引(singles ∪ torrents)查不到 => 该槽保留原 hash
 * 字符串(绝不产 undefined 进消费位)并把行登记在此, 后续 applyStateRows 轮次经
 * _rematDrain 索引齐后补物化。后端 drain 段不变式「成员脏 ⇒ 同代组行脏」(runtime_views.py
 * drain_delta)保证常规轮不可达 —— 纯兜底, 常态零成本(空 Map)。模块级非响应式:
 * 登记的是行对象引用, 不进 Vue 数据流。 */
const _rematQueue = new Map();

/* S3 version-reload 防抖(plan 26-11-11-0630 §04 S3): 自愈 reload 的限流窗口与记忆键。
 * 30s 与轮询失败退避首档同量级 —— 抖动场景最坏退化为 1 次/30s 的有界节流(见 _versionSelfHeal 注)。
 * 键名沿用 autoqb_*_v1 既有风格; sessionStorage(per-tab、reload 存活、随标签关闭失效)恰好对齐
 * 「每个标签页一份自愈预算」的语义 —— 新开标签页本就加载新 JS, 不欠一次 reload。 */
const AQB_VERSION_RELOAD_DEBOUNCE_MS = 30000;
const AQB_VERSION_RELOAD_STORE_KEY = "autoqb_version_reload_v1";
/* 存储层不可用(私隐模式访问即抛)时的内存兜底记忆: 只在本页 incarnation 内有效, reload 即失忆。
 * 0 = 无记录(epoch 时间戳永不与 0 相距 <30s, 天然不误拦首轮)。 */
let _versionReloadMemAt = 0;

window.AQB_POLL = {
  methods: {
    /* ---------------- P2 事件驱动(SSE /api/events) ----------------
     * 目的: 把「命令回执」与「视图版本变更」从轮询改成推送 ——
     *   前者省掉回执轮询的退避粒度(0->150->300->500ms), 后者省掉 1.5/2/3s 的定时触发。
     * !轮询**保留**作为兜底: 断线 / 首帧 / 浏览器不支持 / 反代缓冲时自动退回, 语义不变。
     * WARN: EventSource 发不出 Authorization 头 => 先用带鉴权的 POST /api/events/ticket 换
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
      // #7(issue 26-11-08-0229): 落票后复查鉴权态再开流 —— 换票 await 期间可能已登出
      // (skip_local_verify 下换票免密钥, 票据落下不等于会话仍活); 旧序直接开流, 首个 ver
      // 事件经 refresh 的 !authOk 门再走 _logout 收口拆流, 残留至多一轮空转(R5#2 的
      // stopEvents 收口只是收窄)。此处读 authOk(R10-01 鉴权判据单点, 与 onerror 重试守卫
      // :90 同判据), 只读比较不引入新可变态; 复查点落在 await 恢复之后、开流之前 = 竞态窗口的闭端。
      if (!this.authOk) return;
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
      es.addEventListener("skip_check", (e) => {
        // 跳检终态(相位机在终态结算时广播, 见 ops_mod._skip_settle): 只有失败需要提示 ——
        // 成功已由批量回执/行状态覆盖; 规则侧发起的跳检没有回执, 失败靠这条浮条兜底。
        try { this.onSkipCheckEvent(JSON.parse((e && e.data) || "{}")); } catch (_) { /* 坏帧忽略 */ }
      });
      es.addEventListener("ver", (e) => {
        // 只带版本号、**不含数据** —— 收到后拉一次 /api/state。密集发布时去抖合并,
        // 免得一轮 sync 触发 N 次全量拉取(3000 种子一轮 63ms, 打满主线程的坑踩过)。
        // R4 清池(row119): 落拍时 document.hidden 短路 —— 后台标签不吃 ver 驱动(否则
        // 绕过骨架「后台不拉数」恒等守卫, 每个发布版都真实请求一次 /api/state); 恢复
        // 可见由 visibilitychange 处理器(lifecycle.js)补拉一次, 不双份。
        if (this._verTimer) clearTimeout(this._verTimer);
        this._verTimer = setTimeout(() => { this._verTimer = null; if (!document.hidden) this.refresh(); }, 60);
      });
      es.onopen = () => {
        // 恢复成功: 只回置状态位, 静默不广播(断线提示只在断线沿发, 不发"已恢复"噪音)
        this._esConnected = true;
      };
      es.onerror = () => {
        // 断线沿(WEBUI 通知 S6, D2 拍板): 以 _esConnected 取沿, 首次断线或
        // true->false 跳变时发一条 error toast —— 经 toast() 内的 _recordErrorToast
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
    /* ---------------- 轮询骨架单点(R20-D-05 / R20-E-02 / R20-E-03, 2026-10-22 收敛) ----------------
     * 此前「启停 + 守卫 + 在途悬挂兜底 + 代际守卫」这份生命周期写了三份(主轮 setTimeout 链 /
     * 抽屉 setInterval / 流量图 setInterval), 停止条件五处手写, 且抽屉侧漏了悬挂兜底(loading 卡死
     * 即面板冻结到重开)—— 同一类缺陷只修了一边。收敛后各轮询只声明差异, 骨架认这些键:
     *
     *   startPoll(key, opts) —— 长驻心跳(无返回值):
     *     ms      () => number        间隔; **每拍重读**(间隔随种子量/采样间隔变化时自动重排,
     *                                 不再需要 qb 侧那个 resync 钩子)
     *     fn      () => any           每拍动作
     *     guard   () => bool          附加守卫(false = 跳过本拍, 定时器不拆 —— 回页/恢复后自动续)
     *     stall   () => bool          卡死判据(true = 上一拍没让出控制权, 复位路径永不到)
     *     mutex   bool                true = 卡死未超时前挡拍(流量图 loading 在途互斥);
     *                                 false = 照常走本拍(抽屉静默取数不置门, 不能挡)
     *     stallMs number              卡死阈值(ms), 默认 AQB_POLL_STALL_MS
     *     onStall () => void          超时后的补偿(默认只留一条警告痕)
     *     chain   bool                true = 等 fn 落定再排下一拍(不堆叠请求, 主轮用)
     *
     *   awaitPoll(key, opts) —— 有界等待(返回 Promise, 收敛即兑现, 耗尽/叫停兑现 null):
     *     ms      (n, prevMs) => number   节拍(定间隔返回常量; 退避曲线按 prevMs 翻倍)
     *     fn      () => any               每拍动作; 抛出即 reject(401 上抛给统一收口)
     *     until   (r) => bool             收敛判据(r = 本拍 fn 的返回值)
     *     max     number                  拍数上限
     *     deadline() => bool              时间上限(true = 到点收摊)
     *     stop    () => bool              外部叫停(赛跑落败方)
     *     onEnd   () => void              收摊回调(收敛/耗尽/到点都走; fn 抛出的 reject 路径
     *                                     不走 —— 清理归调用方: 现调用面要么 fn 全吞错
     *                                     (tmLoad 经 _panelLoad, fail 分支不可达), 要么
     *                                     刻意上抛 401 统一收口(commands.js _pollCmd),
     *                                     都无 onEnd 侧清理面。issue 26-11-08-1621)
     *   key 传 null = 不入表(并发命令回执轮询各走各的, 不能互相顶掉); 非空 key = 先停后起。
     *
     * 恒等守卫(写死在骨架里, 调用方一律不再手写): document.hidden —— 后台标签不拉数。
     * 代际守卫: 同名 startPoll/awaitPoll 自带先停后起(句柄表 _polls), 不再手写 ++pollGen。 */
    _polls: null,
    stopPoll(key) {
      const st = this._polls && this._polls[key];
      if (!st || !st.alive) return;
      st.alive = false;
      if (st.timer) { clearTimeout(st.timer); st.timer = null; }
      if (st.wake) { const w = st.wake; st.wake = null; w(); }  // 唤醒在途 sleep, 不留永不兑现的 Promise
      if (this._polls[key] === st) this._polls[key] = null;
      if (st.settle) {
        // R4 清池(row120): 外部叫停/顶掉也走收摊回调 —— 与 finish() 同序同口径(文件头契约
        // 「onEnd: 收摊回调(收敛/耗尽/到点都走)」含 stopPoll 收摊; 漏了会让 onEnd 侧的
        // loading 复位等清理被跳过, 同 key 有界等待被 startPoll/awaitPoll 顶掉即此形态)。
        // 幂等: alive 已置 false, 此后 finish() 的守卫挡住, 不会双调。
        // #8(issue 26-11-08-0229): onEnd 包 try/finally —— onEnd 在 settle 之前调用,
        // 它同步抛异常会吞掉 settle(调用方 Promise 永久悬挂); finally 保 settle 必达,
        // 异常语义不变照常上抛。finish() 路径同式, 两路保持同序同口径。
        try { if (st.onEnd) st.onEnd(); } finally {
          const s = st.settle; st.settle = null; s(null);  // awaitPoll: 收摊兑现 null
        }
      }
    },
    startPoll(key, opts) {
      this.stopPoll(key);
      if (!this._polls) this._polls = {};
      const st = { alive: true, timer: null, stallAt: 0, period: 0 };
      this._polls[key] = st;
      const arm = () => {
        if (!st.alive) return;
        st.period = opts.ms();
        st.timer = setTimeout(beat, st.period);
      };
      const beat = async () => {
        if (!st.alive) return;
        st.timer = null;
        // 恒等守卫: 后台标签不拉数(单点, 调用方不再手写 document.hidden); 附加守卫只跳本拍,
        // 定时器不拆 —— 回页/恢复/形态切回后下一拍自动续(抽屉切页与流量图切形态同口径)
        if (!document.hidden && !(opts.guard && !opts.guard())) {
          if (opts.stall && opts.stall()) {
            const thr = opts.stallMs || AQB_POLL_STALL_MS;
            if (!st.stallAt) st.stallAt = Date.now();
            if (Date.now() - st.stallAt > thr) {
              st.stallAt = 0;  // 补偿一次即重新计时 => 一段悬挂只留一条痕
              if (opts.onStall) opts.onStall(thr);
              else console.warn(`[poll] ${key}: 上一拍在途超过 ${Math.round(thr / 1000)}s, 视为悬挂, 强制续拉`);
            } else if (opts.mutex) { arm(); return; }
          } else {
            st.stallAt = 0;
          }
          if (opts.chain) await opts.fn();
          else opts.fn();
        }
        if (!st.alive) return;
        arm();
      };
      arm();
    },
    awaitPoll(key, opts) {
      if (key) this.stopPoll(key);
      const st = { alive: true, timer: null, settle: null, fail: null, wake: null, onEnd: opts.onEnd || null };
      if (key) {
        if (!this._polls) this._polls = {};
        this._polls[key] = st;
      }
      const out = new Promise((resolve, reject) => { st.settle = resolve; st.fail = reject; });
      const close = () => {
        if (st.timer) { clearTimeout(st.timer); st.timer = null; }
        if (key && this._polls && this._polls[key] === st) this._polls[key] = null;
      };
      const finish = (v) => {
        if (!st.alive) return;
        st.alive = false;
        close();
        // #8(issue 26-11-08-0229): 与 stopPoll 收摊路同式 —— onEnd 包 try/finally,
        // settle 不被 onEnd 的同步异常吞掉(异常照常上抛, 不额外吞不额外藏)。
        try { if (opts.onEnd) opts.onEnd(); } finally {
          const s = st.settle; st.settle = null;
          if (s) s(v);
        }
      };
      const fail = (e) => {
        if (!st.alive) return;
        st.alive = false;
        close();
        const f = st.fail; st.fail = null;
        if (f) f(e);
      };
      (async () => {
        let n = 0;
        let prev = NaN;
        while (st.alive) {
          if (opts.stop && opts.stop()) break;
          if (opts.max != null && n >= opts.max) break;
          if (opts.deadline && opts.deadline()) break;
          const ms = opts.ms(n, prev);
          prev = ms;
          if (ms > 0) {
            await new Promise((r) => {
              st.timer = setTimeout(() => { st.timer = null; r(); }, ms);
              st.wake = r;
            });
            st.wake = null;
          }
          if (!st.alive) return;  // 期间被 stopPoll 收摊(已兑现 null)
          if (opts.stop && opts.stop()) break;
          let r = null;
          try { r = await opts.fn(); } catch (e) { return fail(e); }
          if (opts.until && opts.until(r)) return finish(r);
          n += 1;
        }
        finish(null);
      })();
      return out;
    },
    stopPolling() {
      this.stopPoll("main");
    },
    scheduleNext() {
      // 主轮节拍走骨架 chain 形态: 上一轮落定后才排下一拍(不堆叠请求, 与旧 setTimeout 链同义);
      // document.hidden / !authOk 交给骨架的恒等守卫, 这里不再手写停止条件(R20-E-03)
      this.startPoll("main", {
        chain: true,
        ms: () => this.currentPollMs(),
        fn: () => this.refresh(),
        guard: () => this.authOk,
      });
    },
    /* P1 落地后按种子量分档(2026-09-19)。档位是**实测**定的, 不是拍的 —— 用
     * scripts/ui_harness.py + e2e/perf.spec.mjs 的 A/B 量出"窗口化后单轮 refresh 的真实耗时":
     *   1000 种子 143ms | 3000 种子 309ms | 5000 种子 396~501ms
     * 再把每档的**主线程占用率**压到 ~15% 上下(单轮耗时 / 间隔; 分档断言见 e2e/views.spec.mjs), 于是:
     *   ≤1000 -> 1.5s(≈10%)  1000~3000 -> 2s(≈15%)  >3000 -> 3s(≈17%)
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
      // 恒定间隔(按种子量分档), **不做"无变化退避"**: 曾按"视图版本未变"逐步放慢(2s->5s->10s),
      // 但状态栏的全局速度走 /api/stats(不受 rid 门控, 每轮都刷)=> 两个速度来源刷新频率被解耦,
      // 观感上变成"状态栏正常、种子行滞后"。版本未变时响应体已趋近于零(不回传 groups),
      // 退避省不下什么, 却直接牺牲行数据新鲜度 —— 收益与代价不对等, 故只保留失败退避。
      return this.basePollMs();
    },
    /* ---------------- P-02 二期 S2a ingestion 物化(plan 26-11-11-0630 §03) ----------------
     * 后端组行 members 已改 **hash 字符串数组**(views_group._build_group_row), 成员明细由
     * torrent 桶平铺行承载(VIEW_ARRAYS group/show 两视图连带 torrents, views_common.py)。
     * 三条 state 入口(refresh 全量轮 / delta 轮 / auth.js bootstrap 登录快照)统一在
     * **赋值给 this.groups 之前**就地解析成员, 全树成员消费位(decorate/筛选/乐观链/
     * 选中/模板)零改动 —— 它们看到的仍是成员行对象, 与 P-02 一期行内字典同构。
     *
     * spike 裁决(2026-11-12, 记录于任务档案):
     * - 物化产**成员行浅拷贝**而非 canonical 行引用: 乐观补丁链 _forEachRow 沿
     *   torrents/singles/groups 三数组逐行命中, prev 采集(applyOptimisticPatch/
     *   applyOptimistic)以后命中覆盖前命中 —— 隐含「同 hash 多命中各为独立对象」不变式;
     *   若组员与平铺行同一对象, 第二次命中读到的是**已打补丁**的值, op.prev 被污染,
     *   失败回滚静默失效。拷贝保持该不变式(与 S1 前服务端成员字典同构), 补丁链零改动。
     * - WeakMap 装饰指纹(decorate.js fp[0]=members 数组引用 + 逐成员字段值)不受影响:
     *   物化只发生在**新行实例**(脏行)上; 未脏行由 applyRows 原样保留引用与数组身份,
     *   不产生装饰缓存失效风暴。
     * - 索引源与后端 S1b 镜子 fuzz 同构: singles ∪ torrents; delta 轮 torrents/singles
     *   桶先于 groups 桶合并(下方桶序), 物化时索引恒含本轮最新成员行; 成员脏必同代组脏
     *   (runtime_views.py drain_delta: added/delta_fields 逐 hash 推导 member_to_key 进
     *   g_up), 组行引用的成员 hash 常规恒可解析。
     */
    /* 成员索引: hash -> 行对象, 源 = singles ∪ torrents(与 decorate.js memberByHash 同源;
     * groups 段不作为源 —— 组行 members 此刻还是 hash 串)。pt/ps = 本轮载荷的平铺/未归组
     * 数组(全量轮传载荷, 内容最新; 增量轮传 null 只吃合并后的本地数组), 载荷优先:
     * 同 hash 冲突时以载荷为准, 本地数组仅查缺兜底。 */
    _memberIndexBuild(pt, ps) {
      const idx = new Map();
      const put = (row) => { if (row && row.hash && !idx.has(row.hash)) idx.set(row.hash, row); };
      for (const row of pt || []) put(row);
      for (const row of ps || []) put(row);
      for (const row of this.torrents || []) put(row);
      for (const row of this.singles || []) put(row);
      return idx;
    },
    /* 组行物化: 就地替换 hash 形 members 为成员行**浅拷贝**数组(行内对象独立于平铺行,
     * 乐观链 prev 采集不变式见上)。形状判定: 首元素非字符串(旧服务端对象形/已物化形/
     * e2e 合成注入)原样跳过 —— full 分支「与 S3 之前逐字节等价」承诺不破。缺项槽保留原
     * hash 字符串并登记待补(_rematQueue), 不产 undefined 进消费位。 */
    _materializeGroupRows(rows, idx) {
      const misses = [];
      for (const g of rows || []) {
        const ms = g.members;
        if (!Array.isArray(ms) || !ms.length || typeof ms[0] !== "string") continue;
        const out = [];
        let miss = 0;
        for (const h of ms) {
          const src = idx.get(h);
          if (src) { out.push({ ...src }); continue; }
          out.push(h);  // 缺项: 原样保留 hash 字符串(消费位不会拿到 undefined)
          miss += 1;
        }
        g.members = out;
        if (miss) misses.push(g);
      }
      for (const g of misses) _rematQueue.set(g.key, g);  // 键去重: 同组新行覆盖旧登记
    },
    /* 待补清账(S2a 防御面): 仅在本轮已建索引的入口调用, 队列空零成本。行已不在当前视图
     * (被整行替换/剔除) => 丢弃; hash 齐了 => 补物化并以 this.groups 重赋值补响应式触发
     * (队列持有的是裸对象引用, 直接改字段旁路 Vue 代理)。后端不变式下常规不可达。 */
    _rematDrain(idx) {
      if (!_rematQueue.size) return;
      let healed = false;
      const cur = this.groups || [];
      for (const [key, row] of [..._rematQueue]) {
        _rematQueue.delete(key);  // 先出队: 按结果决定是否重登
        if (!cur.includes(row)) continue;  // 行已被替换/剔除(Vue includes 对裸对象有 toRaw 回退)
        const ms = row.members || [];
        let miss = 0;
        const out = ms.map((m) => {
          if (typeof m !== "string") return m;
          const src = idx.get(m);
          if (!src) { miss += 1; return m; }
          return { ...src };
        });
        if (miss === ms.length) { _rematQueue.set(key, row); continue; }  // 依旧全缺: 留待下轮
        row.members = out;
        healed = true;
        if (miss) _rematQueue.set(key, row);  // 部分补齐: 留队补剩余
      }
      if (healed && this.groups) this.groups = this.groups.slice();
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
        if (d.groups || r.groups) {
          // S2a ingestion 物化(delta 轮): torrents/singles 桶已先行合并 => 索引含本轮最新
          // 成员行; 组行引用的成员 hash 恒可解析(成员脏⇒同代组脏, 见 _memberIndexBuild 注)。
          // 物化先于 applyRows/赋值: 脏组行此刻还是裸对象, 改动不旁路响应式。
          let rematIdx = null;
          if (d.groups && d.groups.length) {
            rematIdx = this._memberIndexBuild(null, null);
            this._materializeGroupRows(d.groups, rematIdx);
          }
          this.groups = applyRows(this.groups, "key", d.groups || [], r.groups || []);
          // 待补清账必须在赋值之后: applyRows 对脏行整行替换并保留 upsert 新实例引用,
          // 同轮登记行此刻才进 this.groups; 先清则 cur.includes 恒 false, 队列当轮空转。
          if (rematIdx) this._rematDrain(rematIdx);
        }
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
        // `this._snapshotTruth(state)` 字面量不动(tests/webui_static_scan_js.py::_scan_pending_settle 钉住)。
        // WARN: 此后本函数作用域内的 state.torrents/singles/groups 只代表**增量行**, 不代表
        // 全量 —— 下游不得再当全量读(现调用点之后无人读它们)。
        if (d.torrents) payload.torrents = d.torrents;
        if (d.singles) payload.singles = d.singles;
        if (d.groups) payload.groups = d.groups;
        return payload;
      }
      // full 分支(含未协商的旧服务端响应: 无 full 键 => 走这里, 行为与 S3 之前逐字节等价)
      // = 清空重放(R6)。P1-1: 服务端只回当前视图的数组 —— **键不存在时必须保留原引用**,
      // 绝不能 `|| []` 清空(否则每次轮询都把另外两个视图抹成空, 切回去要等一轮全量)。
      if (payload.groups !== undefined) {
        // S2a ingestion 物化(全量轮): 索引直接吃载荷平铺数组(内容最新, 同 hash 覆盖本地
        // 旧值), 本地数组仅查缺兜底。行仍裸对象, 先物化后赋值。旧服务端对象形 members 由
        // _materializeGroupRows 形状判定跳过(full 分支「与 S3 之前逐字节等价」不破)。
        let rematIdx = null;
        if (Array.isArray(payload.groups) && payload.groups.length) {
          rematIdx = this._memberIndexBuild(payload.torrents, payload.singles);
          this._materializeGroupRows(payload.groups, rematIdx);
        }
        this.groups = payload.groups;
        // 待补清账在赋值之后(理由同 delta 分支: 登记行须先进 this.groups 才过 includes);
        // groups 键不存在的轮次(其它视图)零成本跳过。
        if (rematIdx) this._rematDrain(rematIdx);
      }
      if (payload.singles !== undefined) this.singles = payload.singles;  // 未归组种子(搜索兜底/总数回退)
      if (payload.torrents !== undefined) this.torrents = payload.torrents;  // 种子页平铺数组(SEED_ITEM)
      if (payload.shows !== undefined) this.shows = payload.shows;  // 追剧视图(R10)
      return payload;
    },
    /* 搜索自动刷新触发点(plan 26-11-03-0120 F3): 每轮 /api/state 成功后比对服务端
     * search_rev 与"手上结果的版本"。落后 => 冷却允许就静默重查一次(整集替换, 不闪全列表);
     * 无数据变化时版本相等, 零额外请求。跳过条件: 手动搜索在途(pending)/静默重查在途/
     * 仅负词(结果恒空)/无搜索词(非搜索态)/版本缺失(旧服务端)。
     * 冷却 SEARCH_REFRESH_MIN_MS 按 P0 闸门取 2000ms —— 轮询本身 >=1.5s, 二者叠加后
     * 实际最小刷新间隔约 2s, 高频变更风暴也不会把 Web 线程打满。 */
    _maybeSearchRefresh() {
      if (this.searchPending || this._searchRefreshBusy) return;
      if (this.searchNegativeOnly) return;
      if (!(this.searchQuery || "").trim()) return;
      const rev = this.status && this.status.search_rev;
      if (typeof rev !== "number" || rev === this.searchRevApplied) return;
      const now = Date.now();
      if (this._searchRefreshAt && now - this._searchRefreshAt < SEARCH_REFRESH_MIN_MS) return;
      this._searchRefreshAt = now;
      this.doSearch(true);
    },
    /* ---------------- S3 version-reload 自愈(plan 26-11-11-0630 §03 version-reload 行 / §04 S3 行) ----------------
     * 问题面: 同仓同进程发布(静态 no-cache+ETag 重校验)下, 升级后**已开的旧标签页**仍跑旧 JS,
     * 每轮轮询把新形状的 status payload 喂给旧消费位 —— 静默渲染破损, 用户无感也无从自愈。
     * 机制: 后端 _status_payload 恒回传包版本号(version = server/common.py app_version()), 前端在
     * 轮询数据处理入口(refresh —— 定时轮询与 SSE ver 驱动都汇于它)每轮比对:
     *   - 首轮(本页 incarnation)记基线 this._versionSeen;
     *   - 后续轮与基线不一致 = 服务端已换版本 => location.reload() 自愈一跳(reload 拿到新 JS +
     *     新形状), **中止本轮载荷应用**(不把跨版本载荷喂进旧 JS)但**照常续排下一拍** —— 防抖
     *     已把实际 reload 速率封顶 1 次/30s, 续排不造成循环; 导航真发生时定时器随页销毁, 导航
     *     被取消(下条守卫用户点「留下」)时轮询链继续活着, 窗口过后重试自愈。
     *   - 变更沿先问配置编辑器脏态守卫(cfgGuardActive, U1-b 双脏源判据单点): 活跃 = 本轮跳过
     *     自愈(不 reload、不记防抖时间戳, 基线不动, 轮询照常) —— 后台轮询不替脏态用户弹原生
     *     beforeunload 框, 守卫释放后的下一轮变更沿自然再触发。
     * 防重签发循环(§04 S3 验收): 循环唯一来源是 version 抖动(回滚/灰度期新旧进程交替应答)——
     *   1) 稳定版本(一切真实部署的稳态): reload 后新页重新记基线, 恰好一次 reload 零循环;
     *   2) 抖动场景: sessionStorage 记最近一次 reload 时间戳(per-tab), 30s 窗口内至多一次 ——
     *      最坏退化为 1 次/30s 的有界节流, 部署稳定后归零;
     *   3) sessionStorage 不可用(私隐模式访问即抛, columns_persist.js 先例)退内存层
     *      (_versionReloadMemAt): 同页内仍拦重复触发; 跨 reload 记忆丢失 —— 稳定版本路径不受
     *      影响(第 1 条不依赖存储), 唯「存储被禁 + 每请求翻转版本」组合可能循环, 接受该残留
     *      (环境级存储缺陷叠加病态部署才可达; 自愈主目标不为其让位, 内存层已是可用上限)。
     * 保守默认(黄金法则 2): version 缺失/非字符串的轮(老服务端/异常响应)不触发也不动基线 ——
     *   无从判定变更方向, 宁可不自愈; 首次见到 version(基线尚空)只记基线不当变更沿。 */
    /* 基线 _versionSeen 不声明在本 methods 对象: 初值落 state.js data()(_versionSeen: null)——
     * Vue3 生产构建对 methods 里的非函数条目静默跳过(applyOptions 只认函数), 声明在这里恒无效,
     * 且真机初值变 undefined 与电池替身(null)异臂; data() 下划线字段先例 _searchRefreshAt。
     * 本方法只读写 this._versionSeen, 语义同上注。 */
    _versionSelfHeal(status) {
      const v = status && status.version;
      if (typeof v !== "string") return false;  // 缺失/异常轮: 不触发、不动基线(保守默认)
      if (this._versionSeen === null) {  // 单臂: 初值由 state.js data() 声明保证为 null(见上注)——
        // undefined 臂随落位修正收紧: 真机 undefined 只可能来自声明错位(methods 非函数条目被
        // Vue3 跳过), 保留反而吸收该回归(替身/真机再次异臂); 收紧后错位在真机首轮即显形
        // (基线判不中直接落变更沿 → reload, 30s 防抖封顶), 不再静默降级。
        this._versionSeen = v;  // 首轮记基线; reload 后新页 incarnation 重新记(循环破除第 1 条)
        return false;
      }
      if (v === this._versionSeen) return false;  // 一致轮: 零成本直通, 不碰存储
      // 配置编辑器脏态守卫活跃(U1-b, cfgGuardActive 双脏源判据单点): 后台自愈 reload 会替脏态
      // 用户弹原生 beforeunload 框 —— 本轮跳过自愈(不 reload、不记防抖时间戳、基线不动), 轮询
      // 照常; 守卫释放(cfgGuardRelease / 保存或放弃清脏)后的下一轮变更沿自然再触发, 只让拍不让位。
      if (this.cfgGuardActive()) return false;
      const now = Date.now();
      let recent = false;
      try {
        recent = now - (Number(sessionStorage.getItem(AQB_VERSION_RELOAD_STORE_KEY)) || 0)
          < AQB_VERSION_RELOAD_DEBOUNCE_MS;
      } catch { /* 私隐模式等: 存储层缺席, 只剩内存层 */ }
      if (!recent && now - _versionReloadMemAt < AQB_VERSION_RELOAD_DEBOUNCE_MS) recent = true;
      if (recent) return false;  // 防抖窗口内: 不 reload, 本轮照常处理(有界节流, 不循环重签发)
      try {
        sessionStorage.setItem(AQB_VERSION_RELOAD_STORE_KEY, String(now));
      } catch { /* 写失败同读: 内存层兜底 */ }
      _versionReloadMemAt = now;  // 内存层恒与存储层同拍记账(存储不可用时它是唯一记忆)
      location.reload();
      return true;
    },
    async refresh() {
      try {
        // rid 增量: 带上已持有的视图版本, 服务端版本未变时不回传数组(响应体趋近于零)。
        // P1-1: 同时带上当前视图名, 服务端只回该视图需要的数组(响应体 ≈1/4)。
        // 切视图时 goView 会把 lastRid 置空 => 强制取一次全量, 别的视图不会停在旧数据上。
        // delta=1(plan S4, P-05 定案: 默认开、不加配置键): 声明客户端懂增量协议 ——
        //   服务端 rid 落在时间线窗口内时回增量载荷(full=false), 本地由 applyStateRows
        //   行级合并; 窗外/降级/切视图后 lastRid 已置空 => 服务端恒回全量(full=true), 天然兼容。
        const qs = [];
        if (this.lastRid !== null) qs.push(`rid=${this.lastRid}`);
        if (this.viewMode === "torrents") qs.push("view=torrent");
        else if (this.viewMode === "shows") qs.push("view=show");
        else qs.push("view=group");
        qs.push("delta=1");
        const query = `?${qs.join("&")}`;
        const state = await this.api("/api/state" + query);
        // S3 version-reload(计划 26-11-11-0630 §03/§04): 轮询数据处理入口的**单点**变更沿,
        // 放在一切赋值/应用之前 —— 服务端版本与本页基线不一致即 reload 自愈: 本轮载荷**不应用**
        // (version 已变的载荷可能新形状, 旧 JS 不吃)但**照常续排下一拍** —— 防抖已把实际 reload
        // 速率封顶 1 次/30s, 续排不造成循环; 导航真发生时定时器随页销毁, 导航被取消(脏态守卫
        // 用户点「留下」)时轮询链继续活着, 窗口过后重试自愈。比对/防抖/守卫共存/缺失轮保守默认
        // 等语义单点见 _versionSelfHeal 注。
        if (this._versionSelfHeal(state.status)) { this.scheduleNext(); return; }
        this.status = state.status;
        // qB 全局状态(server_state)随 status **恒回传**(与 traffic 同口径: 不受 rid 门控) ——
        // 状态栏常显统计与"限制速度"取它, 不再单独打 /api/stats => 每轮只剩 1 条请求,
        // 且状态栏与行数据**同源同轮**(不再出现"状态栏新鲜 / 种子行滞后"的错位观测)。
        // S2 速度切预翻转(计划 26-10-30-0610/D8)的对账点单点在这里: server_state 是
        // use_alt_speed_limits 唯一的确认通道(无 SSE cmd/ver/truth 事件), 赋值后立即问一次
        // 覆盖是否已与真值一致 —— 一致即清除 altOverride(摘除前后显示同值, 零观感跳变)。
        if (state.status && state.status.server !== undefined) {
          this.statsServer = state.status.server || null;
          this._altOverrideReconcile();
        }
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
            // 双向联动(2026-10-09): 行级增删后重扫组完整性 —— 组成员被移除后组不再是"全选",
            // 该 key 必须随之移出(否则批量目标会指向一个已经不全选、甚至已消失的组)。
            this._selSyncGroups();
          }
          this.renderMs = Math.round((performance.now() - _t0) * 10) / 10;
          if (this.renderMs > 50) console.warn(`[perf] 单轮视图赋值 ${this.renderMs}ms(>50ms)` +
            ` —— 稳态应远低于此; 首次切视图要全量渲染一帧量行高, 那一帧超属预期(P1-2 已落地)`);
        }
        this._expirePending();    // !先回滚超时的(不回滚会留永久假状态, issue 26-09-19-2141)
        this.reapplyPending();    // P0-3: 整表替换后把仍 pending 的乐观值重新贴上
        this.serviceDown = false;
        this.pollFails = 0;
        this._maybeSearchRefresh();  // 本轮 state 已落, 顺带裁决搜索是否需要静默重查(plan 26-11-03-0120)
      } catch (e) {
        // 服务不可达(程序退出/网络失败): 置 serviceDown 显示横幅; 轮询继续, 服务恢复后自动消失。
        // 401(密钥无效): 停止轮询并回到密钥输入界面(防无谓空转)。
        if (e.auth) {
          this.stopPolling();
          this.stopEvents();  // R4 清池(row35): 与 _logout 同口径 —— 推送通道一并拆, 残留流不再空转
          return;
        }
        this.serviceDown = true;
        this.pollFails = Math.min(4, this.pollFails + 1);
      }
      this.scheduleNext();
    },
  },
};
