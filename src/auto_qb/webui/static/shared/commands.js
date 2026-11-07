/* auto-qb WEB UI · 命令投递与乐观 UI(贴上/回执/撤下/真值对齐)
 *
 * app.js 按域拆分出的片段(2026-09-20)。约定与 config_editor.js / config_rules.js 同一范式:
 * 挂到 window.AQB_COMMANDS, 由 app.js 末尾 app.mixin(window.AQB_COMMANDS) 注入同一个 Vue 实例 ——
 * 方法体里的 this 仍是那个组件实例, 跨模块互调与拆分前完全等价。
 *
 * !本文件在 HTML 里必须排在 app.js **之前**(app.js 末尾要读 window.AQB_COMMANDS);
 *   用到的列模型常量(TABLE_COLUMNS / MIN_COL_PX / STATE_RANK …)仍单点定义在 app.js 顶部。
 */
/* 「值覆盖」的保持上限(ms) —— 必须与后端 TRUTH_PUSH_CAP_MS 一致(静态守阵钉住)。
 *
 * 2026-09-20 D2 定案后, 一次命令有**两个**时刻:
 *   1. 回执到达(命令已执行)  -> **结束压暗**(撤下, 10~20ms 级)
 *   2. 真值事件到达(已落地)  -> **结束值覆盖**(行上换成真值, 真机实测 ~1.25s)
 * 本常数管的是 2. 的兜底: 超时还没等到真值就回滚, 不留假状态。
 * !它不再进"端到端"宽限 —— 回执不再被扣住等真值, 端到端就是命令执行时间。 */
const TRUTH_HOLD_MS = 8000;

/* 站点 chip 图标槽(计划 26-10-19-2206 D1/D2/D3): token -> 图标 id 的**唯一映射**。
 * 图标通道**只服务命令结果**(前端本地态 alertIcons); 站点问题(缺配置 / tracker 报错)改走
 * chip 底色(颜色通道), 不再有图标 —— 于是"图标位置随状态跳"与"两类错误撞脸"同时消失。
 * 模板只做声明式绑定, 不在这里以外的地方写 `#i-xxx` 图标名, 也不按 state 猜原因
 * (口径与 error_reason 一致)。颜色走 CSS 类(sx-<token>), 三皮肤各自定义, 这里只管符号。 */
const ALERT_ICON = {
  pending: "#i-pulse", // 汇报进行中(蓝, 呼吸)
  ok: "#i-check",      // 成功(绿, 10s)
  warn: "#i-clock",    // 已受理·推迟 / 未确认(黄, 180s)
  error: "#i-x-circle", // 失败(红, 180s)
};
/* 命令结果图标寿命(ms, 计划 D7): 成功 10s / 推迟·未确认 180s / 失败 180s /
 * 进行中至回执(兜底 45s —— 回执最长等 40s, 留 5s 余量)。 */
const ALERT_ICON_MS = { ok: 10000, warn: 180000, error: 180000, pending: 45000 };

window.AQB_COMMANDS = {
  methods: {
    // 命令 => 中文动作名(用于投递成功/失败的提示文案)
    _actionText(action) {
      return { pause: "停止", resume: "启动", reannounce: "强制重新汇报", recheck: "强制重新检查", delete: "删除" }[action] || action;
    },
    /* ---------------- 站点 chip: 站点问题走颜色, 命令结果走图标(计划 26-10-19-2206) ----------------
     * 缺配置 = 橙底 + 虚线底边(非颜色通道, D4), tracker 报错 = 红底; 图标只剩命令结果一种,
     * 固定放在站点名之后 —— 一列扫下去图标位置恒定。 */
    /* 站点问题 -> chip/明细行类名(返回 "" / "sa-no-conf" / "sa-tracker")。
     * 判定只读后端 token(site_alert), 不在前端按 state 猜原因; 缺配置优先于报错 ——
     * 与后端 _site_alert 的判定顺序一致(配置缺失时报错文本不可信)。
     * 类名与旧图标类(sa-no_site_conf / sa-tracker_error)刻意不同名: 旧类残留会被静态守阵拦下。 */
    siteAlertClass(m) {
      const t = m && m.site_alert;
      if (t === "no_site_conf") return "sa-no-conf";
      if (t === "tracker_error") return "sa-tracker";
      return "";
    },
    /* chip/明细行 tooltip(D8): 站点问题在前、命令结果在后, 并存时合并成两行(单条不加换行)。
     * 挂在整块 chip 上 —— 触发面从 11px 图标放大到整块, 图标本身不再各自挂 title。 */
    chipAlertTip(m) {
      const parts = [];
      if (m && m.site_alert && m.site_alert_msg) parts.push(m.site_alert_msg);
      const ic = m ? this.rowIcon(m.hash) : null;
      if (ic && ic.msg) parts.push(ic.msg);
      return parts.join("\n");
    },
    /* 读屏文案(D4): 站点问题不只有颜色一个通道 —— aria-label 带上站点名与原因。
     * 无站点问题时返回 ""(绑定侧用 `|| null` 摘属性, 空 aria-label 会顶掉 chip 里的可见文字)。 */
    siteAlertAria(m) {
      if (!m || !m.site_alert) return "";
      const msg = m.site_alert_msg || "";
      return msg ? `${m.site}: ${msg}` : m.site;
    },
    alertIconHref(token) {
      return ALERT_ICON[token] || "";
    },
    /* 命令结果读口(模板用): 返回该 hash 当前的命令结果图标, 无则 null。
     * until 到期的兜底在这里也判一次 —— 定时器被页面挂起(后台标签页节流)时不会留孤儿图标。 */
    rowIcon(hash) {
      const r = this.alertIcons && this.alertIcons[hash];
      if (!r) return null;
      if (r.until && Date.now() > r.until) return null;
      return r;
    },
    /* 命令结果写口单点: 给某行落一个结果图标(ms 缺省 = 不自动过期, 等回执改写)。
     * !每 hash 一个定时器, 覆盖时先清旧定时器 —— 否则"进行中(45s 兜底)"的旧定时器会把
     *   后到的成功/失败图标提前清掉(时序: 兜底 45s > 成功 10s, 用户会看到绿勾闪一下就没了)。 */
    setRowIcon(hash, kind, msg, ms) {
      if (!hash) return;
      if (!this._rowIconTimers) this._rowIconTimers = {};
      if (this._rowIconTimers[hash]) {
        clearTimeout(this._rowIconTimers[hash]);
        delete this._rowIconTimers[hash];
      }
      if (!kind || !ALERT_ICON[kind]) {
        delete this.alertIcons[hash];
        return;
      }
      const life = ms == null ? ALERT_ICON_MS[kind] || 0 : ms;
      this.alertIcons[hash] = { kind, msg: msg || "", until: life ? Date.now() + life : 0 };
      if (life) {
        this._rowIconTimers[hash] = setTimeout(() => {
          delete this.alertIcons[hash];
          delete this._rowIconTimers[hash];
        }, life);
      }
    },
    /* 组 key -> 成员 hash 列表(右槽按 hash 落图标: 组级 job 的结果也要落到成员行上)。
     * 组已不在视图(刚被解散)时返回空 —— 落不到图标也不谎报, toast 仍给聚合结论。 */
    _jobHashes(k) {
      const g = this._findGroup(k);
      return g ? (g.members || []).map((m) => m.hash) : [];
    },
    /* ---------------- P0-3 埋点(点击侧): 「点击 → 补丁」/「点击 → POST 返回」 ----------------
     * 原先 cmdStats 只量**回执段**(wait_ms / exec_ms / 端到端), 「点击 → 命令投递」这一段
     * 既没打点也没超时, 是**盲区**: 真机上 POST 慢到秒级时, 前端日志全绿、只有用户肉眼能看见
     * "点了 2-4s 才有反应"(issue 26-09-19-1939-webui-optimistic-latency 就是这么报上来的)。
     * 埋点没有消费者就是死字段 —— 这两段一并写进 cmdStats, 由 waitCmd 的 [perf] 统一消费。 */
    _newCmdStats(action) {
      const t0 = performance.now();
      this.cmdStats = {
        action: action || null,
        t0,               // 点击时刻(供 settleMs 用; 埋点没有消费者就是死字段 —— 见 _markCmdSettle)
        patchMs: null,    // 点击 -> 乐观补丁贴上(补丁先于 POST, 正常 ~0ms)
        postMs: null,     // 点击 -> 命令 POST 返回(真机大库可能秒级 —— 本埋点要的就是它)
        /* 点击 -> 补丁撤下、行恢复正常(**用户感知的那一半**)。
         * !为什么必须单独埋这一段: 「贴上」早就修好了(受控 4~8ms), 而同一现象用户报了三次
         * —— 前三次全都只埋了 patchMs/postMs, 于是"撤下慢"在日志里全绿、只能靠肉眼报。
         * 修前这一段恒 3~4.5s(3s 常量兜底 + 等到下一次轮询), 修后 ~200~350ms。 */
        settleMs: null,
        settleVia: null,  // 撤下走的哪条路: receipt(回执到达即撤) / push(真值事件到达)
        targets: null,    // 本次命令的目标数(供 [perf] 阈值分档, 见 _markCmdSettle)
        totalMs: null,
        waitMs: null,
        execMs: null,
        cmdId: null,
      };
      return t0;
    },
    /* 撤下埋点: pendingOps 归零的那一刻记 settleMs。
     * 调用点两处(覆盖"压暗结束"的全部出口): resolveOptimistic(回执到达 / 失败回滚)、
     * onTruthEvent(真值事件到达)。缺一处就会漏记。
     * !注意 reapplyPending 里的 _optimisticSettled 也删 pendingOps, 但那时压暗早已结束、
     *   settleMs 已记过, 所以不需要再调这里。 */
    _markCmdSettle() {
      const c = this.cmdStats;
      if (!c || c.settleMs != null || !c.t0) return;
      /* !判据是"**没有行还在压暗**", 不是"pendingOps 清空": D2 之后回执到了就结束压暗,
       * 但值覆盖会继续保留到真值事件到达, 那时 pendingOps 仍非空。
       * 撤下 = 用户不再看到"在飞"态, 就该在这一刻记账。 */
      for (const _h of Object.keys(this.pendingOps)) {
        const _op = this.pendingOps[_h];
        if (_op && _op.grey !== false) return;
      }
      c.settleMs = Math.round(performance.now() - c.t0);
      /* 阈值按目标数分档: 单目标/小批量 800ms; >100 目标 2500ms —— 整剧 800 个种子的**补丁本身**
       * 就要 ~160ms, 按单目标阈值报会变成常驻噪音, 而常驻的报警没人看。
       * !无回执(hang / 命令在途)时只记不报: 那时走的是 3s 兜底, 慢是设计如此, 报出来是噪音。 */
      /* !**无条件打印一行**: 真机上"点完再切到控制台敲命令取 cmdStats"根本做不到(没有那个空档),
       * 而这正是**用户感知的那一半**, 每次都该看得见。超阈值才升级成 WARNING —— 常驻的报警没人看,
       * 但"没有报警"不等于"能看见数字"。
       * !无回执(hang / 命令在途)时**不打印**: 那时走 3s 兜底, 慢是设计如此, 报出来是噪音。 */
      if (c.totalMs == null) return;
      /* `via` = 撤下走的是哪条路, 真机排查的第一判据(2026-09-21 简化为两档):
       *   receipt = 回执到达即结束压暗(正常路径, 真机实测撤下 85ms);
       *   push    = 真值事件到达(压暗早已结束, 这里只表示"值覆盖"也收工了)。
       * 旧版还有 truth / pull / stale 三档, 随着"回执不再带真值 + 不再拉全量"已全部消失。 */
      const budget = (c.targets || 0) > 100 ? 2500 : 800;
      /* 撤下这行要能**单独定位**慢在哪一段: 只给"回执/撤下"两个总数, 遇到本地 85ms 这种
       * 数字没法归因(执行明明只有 2.8ms)。故把服务端的 POST / 排队 / 执行三段都带上 ——
       * 一条命令一行, 不算刷屏。 */
      const head = `[perf] 命令 ${c.cmdId || "-"}${c.action ? "(" + c.action + ")" : ""}:` +
        ` 贴上 ${c.patchMs}ms / POST ${c.postMs}ms / 排队 ${c.waitMs}ms / 执行 ${c.execMs}ms` +
        ` / 回执 ${c.totalMs}ms / 事件 ${c.eventMs}ms / 撤下 ${c.settleMs}ms` +
        ` via=${c.settleVia || "?"} (${c.targets || "?"} 个目标)`;
      if (c.settleMs > budget) console.warn(head + ` —— 撤下 >${budget}ms 属异常`);
      else console.log(head);
    },
    /* !写入前比对 t0 归属(R5#233): t0 是 _newCmdStats 建槽那一刻的返回值 —— 槽被下一次
     *   点击整体重写后 slot.t0 已换人, 上一条命令迟到入账的 patch/post 两段若照旧写入,
     *   会把旧命令的耗时挂进新命令的 stats([perf] 数字错挂)。 */
    _markCmdPatch(t0) {
      if (this.cmdStats && this.cmdStats.t0 === t0) this.cmdStats.patchMs = Math.round(performance.now() - t0);
    },
    _markCmdPost(t0) {
      if (this.cmdStats && this.cmdStats.t0 === t0) this.cmdStats.postMs = Math.round(performance.now() - t0);
    },
    /* ---------------- 命令回执(轮询 /api/cmd/{id}): 主循环执行完/确认完才出结果 ----------------
     * pause/resume 等命令几乎即时; reannounce 的回执由后端 tracker 确认跟踪器在
     * "tracker 状态转 working / next_announce epoch 前跳(成功 = 前跳变大, 不是被重置)
     * /tracker 拒绝/超时"后写入, status 三值 ok/error/warn(计划 26-10-05-0923 D4=warn);
     * 受最小间隔推迟的目标立即回 warn「已受理」早回执, 不占确认窗口(窗口 30s, 前端多留余量)。
     */
    async waitCmd(cmdId, timeoutMs = 40000, opts = {}) {
      /* 首查后退避(原实现第一查也要先睡 500ms —— 快命令平白多 500ms):
       * 快命令曲线 0 → 150 → 300 → 500 封顶; reannounce 走宽松曲线 500 → 1000 封顶
       * (tracker 确认本来就要几秒, 密轮询只增请求数不减延迟)。
       * 多发的请求只落在"命令在途"的极短窗口内, 空闲时没有任何额外轮询。
       * P0-0 埋点: 后端回执带 wait_ms/exec_ms 时记入 this.cmdStats, 并在超阈值时打一条
       * [perf](见下方 —— 埋点没有消费者就是死字段)。 */
      const start = Date.now();
      /* 归属补记(R5#233): cmdStats 单槽在点击侧建槽时还不知道 cmdId(POST 未回), 等回执的
       * 漏斗在这里补记 —— _cmdRecToResult / onCmdEvent 写入前比对它, 不归属的回执只丢埋点
       * 不合并(上一条命令在途时再次点击, cmdStats 已被 _newCmdStats 整体重写, 旧命令的
       * 回执若照旧合并, totalMs/waitMs/execMs 就错挂进新命令的 stats)。 */
      if (this.cmdStats && this.cmdStats.cmdId == null) this.cmdStats.cmdId = cmdId;
      const firstMs = opts.firstMs || 0;
      const capMs = opts.capMs || 500;
      /* P2 事件驱动: SSE 连着时回执由 `cmd` 事件**推**过来, 不必等轮询退避的粒度
       * (0→150→300→500ms)—— 那段粒度本身就是撤下延迟的一部分。
       * !与轮询**赛跑**而不是替换: SSE 不可用/断了就自动退回原路径, 语义不变。 */
      const evP = this._awaitCmd(cmdId, timeoutMs);
      const stop = { v: false };
      const pollP = this._pollCmd(cmdId, timeoutMs, firstMs, capMs, start, stop);
      const got = await Promise.race([evP, pollP]);
      stop.v = true;  // 让落败的轮询路径尽快收摊(它下一次循环会退出)
      this._cancelCmdWait(cmdId);
      if (!got) {
        return { ok: false, error: `执行等待超时(${Math.round(timeoutMs / 1000)}s), 结果以程序日志为准` };
      }
      return this._cmdRecToResult(got, start, cmdId);
    },
    /* 原轮询路径, 抽出来供 waitCmd 与事件路径赛跑(SSE 不可用时的兜底)。
     * 有界等待走轮询骨架的 awaitPoll 单点(polling.js): 退避曲线由 ms(n, prev) 表达
     * (首拍 firstMs, 之后 0→150 起跳、逐拍翻倍夹到 capMs), 时间上限由 deadline 表达,
     * 叫停由 stop 表达 —— 三份有界等待(_pollCmd / tmPollSettle / tmPollShutdown)自此同骨架。
     * !key 传 null: 并发命令各等各的回执, 不能互相顶掉(传 key 会先停后起)。 */
    _pollCmd(cmdId, timeoutMs, firstMs, capMs, start, stop) {
      return this.awaitPoll(null, {
        ms: (n, prev) => (n === 0 ? firstMs : prev === 0 ? 150 : Math.min(capMs, prev * 2)),
        deadline: () => Date.now() - start >= timeoutMs,
        stop: () => stop.v,
        fn: async () => {
          try {
            const r = await this.api(`/api/cmd/${cmdId}`);
            // warn 也是终结态(reannounce 已受理·推迟/未确认, D4=warn): 不放行会一直挂到 40s 等待超时
            if (r.status === "ok" || r.status === "error" || r.status === "warn") {
              return r;  // 埋点与结果转换统一在 _cmdRecToResult 做(事件路径与轮询路径共用)
            }
          } catch (e) {
            if (e.auth) throw e;  // 401 由统一收口处理(回登录)
            // 网络抖动: 继续轮询(服务恢复后回执仍可取到)
          }
          return null;
        },
        until: (r) => !!r,
      });
    },
    /* 回执 -> {ok, truth|error}, 并落埋点/[perf](事件路径与轮询路径共用, 保证两边观感一致)
     * !归属校验(R5#233): 埋点合并只认「等的就是这条命令」—— cmdId 由 waitCmd 补记(见上),
     *   旧命令在途时再次点击, cmdStats 已整体重写且归属换了人, 旧回执到达这里整块跳过
     *   (只丢埋点, 结果转换不受影响)。 */
    _cmdRecToResult(r, start, cmdId) {
      if (typeof r.wait_ms === "number" && this.cmdStats && this.cmdStats.cmdId === cmdId) {
        // 合并而非替换: 点击侧的两段(_newCmdStats 写入)不能在这里被冲掉
        this.cmdStats = {
          ...(this.cmdStats || {}),
          totalMs: Date.now() - start,
          waitMs: r.wait_ms,
          execMs: r.exec_ms,
          cmdId,
        };
        /* 埋点必须有消费者, 否则就是死字段(2026-09-19 复核: 此前 cmdStats 只写不读,
         * 计划里那张"走查表"从未产出)。超阈值时打一条 [perf] —— 冒烟脚本会收集并打印。
         * patchMs 大 = 补丁没做到"点击即变"(被同步工作或 POST 挡住); postMs 大 = 命令投递慢
         * (真机大库长 tick / GIL 争用); waitMs 大 = 命令没被及时消费(P0-1 唤醒退化);
         * totalMs 大 = 轮询曲线或网络慢。 */
        const c = this.cmdStats;
        /* !端到端阈值**不再**加"等真值"的宽限 —— D2 之后回执不再被扣住等真值,
         * 它就是命令执行时间(真机实测 pause 端到端应远小于旧值 1259ms)。
         * 真值那一段现在由 `撤下` 之后的"值覆盖"独立负责, 不混进端到端。 */
        const e2eBudget = 400;
        if (c.waitMs > 100 || c.totalMs > e2eBudget || (c.postMs || 0) > 400 || (c.patchMs || 0) > 50) {
          console.warn(
            `[perf] 命令 ${cmdId}${c.action ? "(" + c.action + ")" : ""}: 补丁 ${c.patchMs}ms` +
            ` / POST ${c.postMs}ms / 排队 ${c.waitMs}ms / 执行 ${c.execMs}ms` +
            ` / 端到端 ${c.totalMs}ms(补丁>50 或 POST>400 或 排队>100 或 端到端>${e2eBudget}属异常)`
          );
        }
      }
      // `truth` = 回执里附带的真值({hash: {kind}})。带上它前端就不必再拉一次全量 /api/state。
      // 强制汇报的聚合回执例外: truth = {results: [{hash, status, reason}]}(逐目标结果,
      // 计划 26-10-19-2007 D6) —— 部分失败时它恰恰是 warn/error 回执, 故**三态都带出** truth,
      // 否则"哪几个失败了"在行上就永远落不下来(聚合文案只留前 3 条原因)。
      // `status` = 后端回执原值(ok/error/warn, D4=warn): reannounce 聚合分支按它三桶分流
      // (warn = 已受理·推迟/未确认, 不等于失败); 其余消费方只读 ok/error, 添字段零影响。
      // SSE 与轮询两路都经这里转换, 终结语义单点(改回执词汇只动这一处 + 后端契约测试)。
      const truth = r.truth || null;
      return r.status === "ok"
        ? { ok: true, truth, status: "ok" }
        : { ok: false, error: r.error || "执行失败", status: r.status || "", truth };
    },
    /* ---------------- P2 事件驱动: 订阅式等回执 ----------------
     * 由 app.js 的 EventSource(/api/events)收 `cmd` 事件后回调这里兑现。
     * !挂在实例上而不是 data 里: Map 不需要响应式, 放进 data 只是白白付代理开销。 */
    _cmdWaiters: null,
    _awaitCmd(cmdId, timeoutMs) {
      if (!this._cmdWaiters) this._cmdWaiters = new Map();
      return new Promise((resolve) => {
        const timer = setTimeout(() => {
          if (this._cmdWaiters) this._cmdWaiters.delete(cmdId);
          resolve(null);  // 超时 -> 交给轮询路径
        }, timeoutMs);
        this._cmdWaiters.set(cmdId, (rec) => {
          clearTimeout(timer);
          resolve(rec);
        });
      });
    },
    _cancelCmdWait(cmdId) {
      if (!this._cmdWaiters) return;
      const w = this._cmdWaiters.get(cmdId);
      if (w) { this._cmdWaiters.delete(cmdId); w(null); }
    },
    onCmdEvent(rec) {
      /* 埋点: 记下"事件**到达浏览器**"这一刻。
       * 用途是把回执耗时 split 成两半 —— 真机实测 68ms 里执行只占 2.8ms, 剩下 46ms
       * 到底是"服务端推得慢"还是"浏览器主线程忙、回调排队", 只看 totalMs 分不出来:
       *   事件 ≈ 25ms 而回执 68ms  => 事件早就到了, 是前端主线程被占(大库渲染/JSON 解析)
       *   事件 ≈ 65ms 而回执 68ms  => 是服务端推送链路慢(生成器唤醒 / uvicorn 写 socket) */
      if (this.cmdStats && this.cmdStats.t0 && this.cmdStats.eventMs == null
          && rec && rec.cmd_id === this.cmdStats.cmdId) {
        this.cmdStats.eventMs = Math.round(performance.now() - this.cmdStats.t0);
      }
      const w = this._cmdWaiters && this._cmdWaiters.get(rec && rec.cmd_id);
      if (w) w(rec);
    },
    /* D2: 真值事件 —— 服务端确认"命令已生效"后推来(见 WebUIRuntime.flush_truths)。
     * 到这里把真值落到行上, 但**不结束值覆盖** —— 覆盖的终点是"服务端**快照**同意"
     * (_optimisticSettled) 或 hold 超时兜底, 不是"真值到达"。
     *
     * !为什么不能在这里 `delete pendingOps[h]`(2026-09-21 用户报「整组暂停后 灰→绿→灰」):
     *   真值走 `torrents/info` **直查**, 比我们自己的 `/sync/maindata` **快照**新 —— 快照要等主循环
     *   下一次 sync(≤ sync_interval = 1.5s)才带上同一个状态。此刻把覆盖撤掉, 这 1.5s 内任何一次
     *   **视图发布**(任何种子任何字段变化都会让 rid 前进、整表重发)都会带着"命令前"的 kind 覆盖行
     *   对象 ⇒ 行被打回命令前的颜色(整组暂停闪回做种绿), 直到快照追上才再变灰。
     *   覆盖留着, 那一轮只会被 reapplyPending 用真值重新贴回去(观感: 一直是灰的)。
     * !真值**同时改 patch 与 prev**: patch 的值 = 已落地的真值(resume 的"落地态 6 种 vs 预测 2 种"
     *   由此收敛, 不再依赖"预测 == 真值"这种严格相等), prev 的值 = **最后已知真值** ——
     *   兜底回滚必须回这里: 回命令前的旧值等于把一个已暂停的种子显示成做种。
     */
    /* 跳检终态事件(计划 26-10-21-1857 S4): 失败才提示, 成功交给回执/行状态 */
    onSkipCheckEvent(ev) {
      const p = (ev && ev.payload) || {};
      if (p.ok) return;
      const name = p.name || (p.hash || "").slice(0, 12);
      this.toast(`跳检失败: ${name} —— ${p.message || "未知原因"}`, "error", 8000);
    },

    onTruthEvent(rec) {
      const truth = rec && rec.truth;
      if (!truth) return;
      const now = Date.now();
      for (const h of Object.keys(truth)) {
        const t = truth[h];
        if (!t || !t.kind) continue;
        const op = this.pendingOps[h];
        /* !kind 注入只对 pause/resume 的 op(计划 26-10-30-0610 S1.3 守卫): 它们的真值是 kind,
         *   注入后 resume/pause 各走 _optimisticSettled 的专用谓词, 不受多出的键影响。
         *   其余 action(如 rename)的 op 保持原 patch —— rename 的真值是 **name** 而非 kind,
         *   掺入 kind 会让 _optimisticSettled 的逐键比对永远差一个键(对账判据被污染,
         *   op 挂到 8s 兜底才回滚, 行名被错误弹回旧名)。静态守阵钉住本守卫, 防回归。 */
        if (op && (op.action === "pause" || op.action === "resume")) {
          op.patch = { ...op.patch, kind: t.kind };
          op.prev = { ...op.prev, kind: t.kind };
          op.hold = true;   // 覆盖保持到"快照同意"(见上; 压暗早已由回执结束)
          op.ts = now;      // 兜底期限从真值落地起算(D2: 压暗已结束, 晚释放没有观感代价)
        }
        // 真值直接落到行上(不等下一轮 refresh)—— kind 是服务端真值, 对 rename 也无害(kind 未变)
        this._forEachRow(h, (row) => { row.kind = t.kind; });
      }
      if (this.cmdStats) this.cmdStats.settleVia = "push";
      this._markCmdSettle();
    },
    /* ---------------- P0-3 乐观 UI: 点击即变 ----------------
     * 只对"结果可预测"的动作做乐观(白名单: pause/resume); 强制重新汇报/重新校验/添加种子这类
     * "结果在远端"的动作不做, 由"等待中"常驻 toast 承担。
     * pending 行的乐观字段每轮 refresh 后被重新贴上(整表替换会盖掉), 直到服务端数据与预期
     * 一致或 3s 超时 —— 避免"先变过去、下一轮又弹回来"的抖动; 回执 error 立即回滚原值,
     * 绝不留假状态(断网/qB 未启动时必须能看到失败)。 */
    isPending(hash) {
      const op = this.pendingOps[hash];
      if (!op) return false;
      /* D2: 回执一到(grey=false)就不再"在飞" —— 压暗到此结束(撤下)。
       * 但**值覆盖还要继续**(op.hold), 直到真值事件到达; 否则下一轮 refresh 会把
       * 命令**前**的旧值打回行上 ⇒ 弹回。这里只管压暗, 不要和值覆盖混在一起。 */
      if (op.grey === false) return false;
      /* !超时**只判 false、不在这里 delete**: 模板每帧都会调 isPending, 在渲染函数里改响应式
       * 数据(回滚字段)有递归更新风险; 真正的回滚交给 _expirePending()(每轮 refresh 一次)。
       * 另注: 光 delete 不叫"回落真值" —— 见 _expirePending 的注释(issue 26-09-19-2141)。 */
      if (Date.now() - op.ts > 3000) return false;
      return true;
    },
    /* 3s 兜底: 超时未确认的补丁**显式回滚到补丁前的值**, 与失败回滚同一写法。
     * !旧写法"不再贴补丁、下轮以服务端为准"在 rid 门控下**不成立**: 服务端版本未变时不回传
     * 数组、行对象不被替换 ⇒ 上一轮贴的 kind:"paused" 会一直留在行上 —— 命令根本没执行,
     * 界面却一直显示已暂停(hang 模式实测: 3.66s 清 pending 后行仍是 s-paused, 真值 s-downloading)。
     * 回滚用的是 op.prev(贴补丁那一刻的行值 = 最近一次已知的服务端真值); 之后若真值真的变了,
     * 下一轮 refresh 自然会把它换成真值, 不会互相打架。 */
    _expirePending() {
      const now = Date.now();
      for (const h of Object.keys(this.pendingOps)) {
        const op = this.pendingOps[h];
        if (!op) continue;
        /* 两种期限: hold(已收到回执, 在等真值事件)用 TRUTH_HOLD_MS —— 压暗早就结束了,
         * 值还盖着没有观感代价, 放宽容错; 非 hold(还没收到回执 / 未知)仍按 3s 回滚,
         * 保住"失败/未知绝不留假状态"这条。 */
        const cap = op.hold ? TRUTH_HOLD_MS : 3000;
        if (now - op.ts <= cap) continue;
        /* 回滚目标不得是"命令前的旧值"(report 26-10-11-2017 §4.4): 若本轮服务端快照已经
         * 离开命令前的状态, 说明命令其实已生效 —— 回 op.prev 等于把一个已改变的种子显示回
         * 旧态(本 bug 的直接成因: 批量路径没有真值事件 ⇒ prev 永远停在点击那一刻)。
         * 有服务端现值就用它(它才是"最后已知真值"), 没有才退回 prev。 */
        const t = this.truthSnapshot && this.truthSnapshot.get(h);
        this._forEachRow(h, (row) => Object.assign(row, t || op.prev));
        this._syncDrawerRollback(h, op.patch, t || op.prev);  // 抽屉 detail 对称还原(issue 26-10-30-0818)
        delete this.pendingOps[h];
      }
    },

    /* ---- 进行中 → 结果: 统一两段式("统一收", 2026-11-02 九轮) ----
     * 口径: 「进行中 / 已投递」与「结果」是**两个事件**, 队列里必须是两条 —— 进行中条归档成
     * 中性(info)留在队列, 结果**另起一条**推入; 新条推入时归档条被 flipStack 顶上一格,
     * 两条并存可见(D6-3 队列重排的可见前提)。
     * !此前各链路都是同一条 `_finishToast` 原位改字: 本地/桩服务回执快, 进行中条只活几百毫秒
     *   就被换了内容, 用户读作「第一个窗口被第二个顶掉, 仅显示不到 1 秒」。强制汇报先改(九轮),
     *   导出 / 批量跳检 / 转移 / 删除前置汇报本轮统一收进本原语。
     * 用法: const run = this._runningToast(`导出已开始: N 个 .torrent 文件`);
     *       await this._settleRunningToast(run, "ok", `已导出: N 个 .torrent 文件`, 3000);
     * minShow = 进行中条的最短可读时长(兜住本地 ~500ms 的回执; 慢回执完全不受影响)。
     * text 传空 = 只归档不出结果条(调用方自己接着发, 例如删除流后面还有「已删除」)。
     * 例外: 投递本身抛错(网络/400)时**不拆** —— 没有"已投递"这回事, 进行中条自身就是终态,
     *   直接 `_finishToast(id, "error", …)` 原位落失败, 免得屏幕上留一条假的「已投递」。 */
    _runningToast(text) {
      return { tid: this.toast(text, "busy", 0, { sticky: true }), text, at: Date.now() };
    },
    async _settleRunningToast(ref, kind, text, ms = null, minShow = 900) {
      if (!ref) return;
      const hold = Math.max(0, minShow - (Date.now() - ref.at));
      if (hold) await new Promise((r) => setTimeout(r, hold));
      this._finishToast(ref.tid, "info", ref.text, 4000);
      if (text) this.toast(text, kind, ms);
    },
  },
  computed: {
    /* 是否有任何乐观补丁在飞(computed 缓存)。给"逐成员问 isPending"的调用点做 O(1) 短路 ——
     * 集行动辄上百成员, 若无补丁还逐个查, 每次重渲染都是几百次无用查找(见 isEpPending)。 */
    pendingAny() {
      return Object.keys(this.pendingOps).length > 0;
    },
  },
};
