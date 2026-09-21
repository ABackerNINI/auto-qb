/* auto-qb WEB UI · 命令投递与乐观 UI(贴上/回执/撤下/真值对齐)
 *
 * app.js 按域拆分出的片段(2026-09-20)。约定与 config_editor.js / config_rules.js 同一范式:
 * 挂到 window.AQB_COMMANDS, 由 app.js 末尾 app.mixin(window.AQB_COMMANDS) 注入同一个 Vue 实例 ——
 * 方法体里的 this 仍是那个组件实例, 跨模块互调与拆分前完全等价。
 *
 * ❗本文件在 HTML 里必须排在 app.js **之前**(app.js 末尾要读 window.AQB_COMMANDS);
 *   用到的列模型常量(TABLE_COLUMNS / MIN_COL_PX / STATE_RANK …)仍单点定义在 app.js 顶部。
 */
/* 「值覆盖」的保持上限(ms) —— 必须与后端 TRUTH_PUSH_CAP_MS 一致(静态守阵钉住)。
 *
 * 2026-09-20 D2 定案后, 一次命令有**两个**时刻:
 *   ① 回执到达(命令已执行)  -> **结束压暗**(撤下, 10~20ms 级)
 *   ② 真值事件到达(已落地)  -> **结束值覆盖**(行上换成真值, 真机实测 ~1.25s)
 * 本常数管的是 ② 的兜底: 超时还没等到真值就回滚, 不留假状态。
 * ❗它不再进"端到端"宽限 —— 回执不再被扣住等真值, 端到端就是命令执行时间。 */
const TRUTH_HOLD_MS = 8000;

window.AQB_COMMANDS = {
  methods: {
    // 命令 => 中文动作名(用于投递成功/失败的提示文案)
    _actionText(action) {
      return { pause: "暂停", resume: "开始", reannounce: "强制汇报", delete: "删除" }[action] || action;
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
         * ❗为什么必须单独埋这一段: 「贴上」早就修好了(受控 4~8ms), 而同一现象用户报了三次
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
     * ❗注意 reapplyPending 里的 _optimisticSettled 也删 pendingOps, 但那时压暗早已结束、
     *   settleMs 已记过, 所以不需要再调这里。 */
    _markCmdSettle() {
      const c = this.cmdStats;
      if (!c || c.settleMs != null || !c.t0) return;
      /* ❗判据是"**没有行还在压暗**", 不是"pendingOps 清空": D2 之后回执到了就结束压暗,
       * 但值覆盖会继续保留到真值事件到达, 那时 pendingOps 仍非空。
       * 撤下 = 用户不再看到"在飞"态, 就该在这一刻记账。 */
      for (const _h of Object.keys(this.pendingOps)) {
        const _op = this.pendingOps[_h];
        if (_op && _op.grey !== false) return;
      }
      c.settleMs = Math.round(performance.now() - c.t0);
      /* 阈值按目标数分档: 单目标/小批量 800ms; >100 目标 2500ms —— 整剧 800 个种子的**补丁本身**
       * 就要 ~160ms, 按单目标阈值报会变成常驻噪音, 而常驻的报警没人看。
       * ❗无回执(hang / 命令在途)时只记不报: 那时走的是 3s 兜底, 慢是设计如此, 报出来是噪音。 */
      /* ❗**无条件打印一行**: 真机上"点完再切到控制台敲命令取 cmdStats"根本做不到(没有那个空档),
       * 而这正是**用户感知的那一半**, 每次都该看得见。超阈值才升级成 WARNING —— 常驻的报警没人看,
       * 但"没有报警"不等于"能看见数字"。
       * ❗无回执(hang / 命令在途)时**不打印**: 那时走 3s 兜底, 慢是设计如此, 报出来是噪音。 */
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
    _markCmdPatch(t0) {
      if (this.cmdStats && t0) this.cmdStats.patchMs = Math.round(performance.now() - t0);
    },
    _markCmdPost(t0) {
      if (this.cmdStats && t0) this.cmdStats.postMs = Math.round(performance.now() - t0);
    },
    /* ---------------- 命令回执(轮询 /api/cmd/{id}): 主循环执行完/确认完才出结果 ----------------
     * pause/resume 等命令几乎即时; reannounce 的回执由后端 tracker 确认跟踪器在
     * "status 变 working / next_announce 被重置"或超时后写入(窗口 30s, 前端多留余量)。
     */
    async waitCmd(cmdId, timeoutMs = 40000, opts = {}) {
      /* 首查后退避(原实现第一查也要先睡 500ms —— 快命令平白多 500ms):
       * 快命令曲线 0 → 150 → 300 → 500 封顶; reannounce 走宽松曲线 500 → 1000 封顶
       * (tracker 确认本来就要几秒, 密轮询只增请求数不减延迟)。
       * 多发的请求只落在"命令在途"的极短窗口内, 空闲时没有任何额外轮询。
       * P0-0 埋点: 后端回执带 wait_ms/exec_ms 时记入 this.cmdStats, 并在超阈值时打一条
       * [perf](见下方 —— 埋点没有消费者就是死字段)。 */
      const start = Date.now();
      const firstMs = opts.firstMs || 0;
      const capMs = opts.capMs || 500;
      /* P2 事件驱动: SSE 连着时回执由 `cmd` 事件**推**过来, 不必等轮询退避的粒度
       * (0→150→300→500ms)—— 那段粒度本身就是撤下延迟的一部分。
       * ❗与轮询**赛跑**而不是替换: SSE 不可用/断了就自动退回原路径, 语义不变。 */
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
    /* 原轮询路径, 抽出来供 waitCmd 与事件路径赛跑(SSE 不可用时的兜底) */
    async _pollCmd(cmdId, timeoutMs, firstMs, capMs, start, stop) {
      let delay = firstMs;
      while (!stop.v && Date.now() - start < timeoutMs) {
        if (delay > 0) await new Promise((r) => setTimeout(r, delay));
        try {
          const r = await this.api(`/api/cmd/${cmdId}`);
          if (r.status === "ok" || r.status === "error") {
            return r;  // 埋点与结果转换统一在 _cmdRecToResult 做(事件路径与轮询路径共用)
          }
        } catch (e) {
          if (e.auth) throw e;  // 401 由统一收口处理(回登录)
          // 网络抖动: 继续轮询(服务恢复后回执仍可取到)
        }
        delay = delay === 0 ? 150 : Math.min(capMs, delay * 2);
      }
      return null;
    },
    /* 回执 -> {ok, truth|error}, 并落埋点/[perf](事件路径与轮询路径共用, 保证两边观感一致) */
    _cmdRecToResult(r, start, cmdId) {
      if (typeof r.wait_ms === "number") {
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
              /* ❗端到端阈值**不再**加"等真值"的宽限 —— D2 之后回执不再被扣住等真值,
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
      return r.status === "ok"
        ? { ok: true, truth: r.truth || null }
        : { ok: false, error: r.error || "执行失败" };
    },
    /* ---------------- P2 事件驱动: 订阅式等回执 ----------------
     * 由 app.js 的 EventSource(/api/events)收 `cmd` 事件后回调这里兑现。
     * ❗挂在实例上而不是 data 里: Map 不需要响应式, 放进 data 只是白白付代理开销。 */
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
      if (this.cmdStats && this.cmdStats.t0 && this.cmdStats.eventMs == null) {
        this.cmdStats.eventMs = Math.round(performance.now() - this.cmdStats.t0);
      }
      const w = this._cmdWaiters && this._cmdWaiters.get(rec && rec.cmd_id);
      if (w) w(rec);
    },
    /* D2: 真值事件 —— 服务端确认"命令已生效"后推来(见 WebUIRuntime.flush_truths)。
     * 到这里把真值落到行上, 但**不结束值覆盖** —— 覆盖的终点是"服务端**快照**同意"
     * (_optimisticSettled) 或 hold 超时兜底, 不是"真值到达"。
     *
     * ❗为什么不能在这里 `delete pendingOps[h]`(2026-09-21 用户报「整组暂停后 灰→绿→灰」):
     *   真值走 `torrents/info` **直查**, 比我们自己的 `/sync/maindata` **快照**新 —— 快照要等主循环
     *   下一次 sync(≤ sync_interval = 1.5s)才带上同一个状态。此刻把覆盖撤掉, 这 1.5s 内任何一次
     *   **视图发布**(任何种子任何字段变化都会让 rid 前进、整表重发)都会带着"命令前"的 kind 覆盖行
     *   对象 ⇒ 行被打回命令前的颜色(整组暂停闪回做种绿), 直到快照追上才再变灰。
     *   覆盖留着, 那一轮只会被 reapplyPending 用真值重新贴回去(观感: 一直是灰的)。
     * ❗真值**同时改 patch 与 prev**: patch 的值 = 已落地的真值(resume 的"落地态 6 种 vs 预测 2 种"
     *   由此收敛, 不再依赖"预测 == 真值"这种严格相等), prev 的值 = **最后已知真值** ——
     *   兜底回滚必须回这里: 回命令前的旧值等于把一个已暂停的种子显示成做种中。
     */
    onTruthEvent(rec) {
      const truth = rec && rec.truth;
      if (!truth) return;
      const now = Date.now();
      for (const h of Object.keys(truth)) {
        const t = truth[h];
        if (!t || !t.kind) continue;
        const op = this.pendingOps[h];
        if (op) {
          op.patch = { ...op.patch, kind: t.kind };
          op.prev = { ...op.prev, kind: t.kind };
          op.hold = true;   // 覆盖保持到"快照同意"(见上; 压暗早已由回执结束)
          op.ts = now;      // 兜底期限从真值落地起算(D2: 压暗已结束, 晚释放没有观感代价)
        }
        // 真值直接落到行上(不等下一轮 refresh)
        this._forEachRow(h, (row) => { row.kind = t.kind; });
      }
      if (this.cmdStats) this.cmdStats.settleVia = "push";
      this._markCmdSettle();
    },
    /* ---------------- P0-3 乐观 UI: 点击即变 ----------------
     * 只对"结果可预测"的动作做乐观(白名单: pause/resume); 强制汇报/重新校验/添加种子这类
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
      /* ❗超时**只判 false、不在这里 delete**: 模板每帧都会调 isPending, 在渲染函数里改响应式
       * 数据(回滚字段)有递归更新风险; 真正的回滚交给 _expirePending()(每轮 refresh 一次)。
       * 另注: 光 delete 不叫"回落真值" —— 见 _expirePending 的注释(issue 26-09-19-2141)。 */
      if (Date.now() - op.ts > 3000) return false;
      return true;
    },
    /* 3s 兜底: 超时未确认的补丁**显式回滚到补丁前的值**, 与失败回滚同一写法。
     * ❗旧写法"不再贴补丁、下轮以服务端为准"在 rid 门控下**不成立**: 服务端版本未变时不回传
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
        this._forEachRow(h, (row) => Object.assign(row, op.prev));
        delete this.pendingOps[h];
      }
    },
    _optimisticPatch(action, row) {
      if (action === "pause") return { kind: "paused" };
      if (action === "resume") return { kind: row && row.progress >= 1 ? "seeding" : "downloading" };
      return null;  // 不在白名单 -> 不做乐观
    },
    _forEachRow(hash, fn) {
      for (const r of this.torrents || []) if (r.hash === hash) fn(r);
      for (const r of this.singles || []) if (r.hash === hash) fn(r);
      for (const g of this.groups || []) for (const m of g.members || []) if (m.hash === hash) fn(m);
    },
    applyOptimistic(hashes, action) {
      const now = Date.now();
      for (const h of hashes || []) {
        if (!h) continue;
        this._forEachRow(h, (row) => {
          const patch = this._optimisticPatch(action, row);
          if (!patch) return;
          const prev = {};
          for (const k of Object.keys(patch)) prev[k] = row[k];
          Object.assign(row, patch);
          // grey = 压暗(回执到即结束) / hold = 值覆盖保持到真值事件(防弹回)
          this.pendingOps[h] = { patch, prev, ts: now, action, grey: true, hold: false };
        });
      }
      // 目标数供 settleMs 的 [perf] 阈值分档(见 _markCmdSettle)
      if (this.cmdStats) this.cmdStats.targets = (hashes || []).length;
    },
    resolveOptimistic(hashes, ok) {
      for (const h of hashes || []) {
        const op = this.pendingOps[h];
        if (!op) continue;
        if (ok) {
          /* D2 成功: **压暗立即结束**(撤下 —— 用户感知的那一半), 值覆盖转入 hold 继续保留
           * 到真值事件到达(onTruthEvent)。qB 翻状态真机实测要 ~1.25s, 等它就没有"点击即变"了;
           * 不弹回由 hold 保证(真值到达前一直盖住行上的值), 不靠等真值。
           * ❗兜底期限**从回执到达重算**且放宽到 TRUTH_HOLD_MS: 压暗已结束, 晚释放没有观感
           * 代价。**无回执(hang)时不会走到这里** —— 那种情况仍按 3s 回滚, "失败/未知绝不
           * 留永久假状态"这条不变。 */
          op.grey = false;
          op.hold = true;
          op.ts = Date.now();
          /* 诊断: 撤下这一步是"回执到达"促成的(真值随后由 truth 事件送到, 会再标 push) */
          if (this.cmdStats) this.cmdStats.settleVia = "receipt";
          continue;
        }
        this._forEachRow(h, (row) => Object.assign(row, op.prev));  // 失败: 回滚
        delete this.pendingOps[h];
      }
      this._markCmdSettle();  // pendingOps 的出口之一(失败回滚)
    },
    reapplyPending() {
      /* 每轮 refresh 整表替换会盖掉乐观值, 这里把仍 pending 的补丁重新贴上。
       * ❗**真值已到就收工**(issue 26-09-19-2024-webui-truth-convergence): 原先这里只管贴,
       * pendingOps 唯一的出口是 3s 兜底 ⇒ 真值早就到了、行还半透明挂着, 用户看到的就是
       * "点了之后 2-4s 才恢复正常"。现在逐个比对**服务端真值快照** ⇒ 对齐就立即清掉。 */
      for (const h of Object.keys(this.pendingOps)) {
        /* ❗不再跳过"已结束压暗"的 op: hold 期间必须继续盖住行上的值, 否则轮询带回的
         * 命令**前**旧值会把行打回去(弹回)。压暗只是视觉, 与值覆盖无关(见 isPending)。 */
        const op = this.pendingOps[h];
        if (!op) { delete this.pendingOps[h]; continue; }
        if (this._optimisticSettled(h, op)) {
          // 真值已对齐: 不再贴补丁(贴上去也是同样的值, 但 is-pending 会一直挂着)
          delete this.pendingOps[h];
          continue;
        }
        this._forEachRow(h, (row) => Object.assign(row, op.patch));
      }
      this._markCmdSettle();  // pendingOps 的出口之二(真值对齐后由上面 delete)
    },
    /* 本轮 /api/state 的真值快照(只记仍 pending 的 hash)。
     * ❗**必须比服务端原始值, 不能比行上的当前值**: 行在上一轮已经被贴过补丁了, 拿行上的值
     *   跟补丁比 = 跟自己比 ⇒ 首轮必"匹配"、pending 立刻消失(2026-09-19 实测 28ms 就清了,
     *   而桩服务真值 +120ms 才到 —— 断言全绿却什么都没测到)。
     * ❗**拷值不拷引用**: 赋值后 `this.torrents` 与 payload 是同一批对象, 补丁随后就改到它们,
     *   存引用等于没存。
     * ❗只认 payload 里**真的带了**的 hash: 当前视图的 payload 可能不含它(如追剧视图只回
     *   shows), 那时返回 false ⇒ 继续贴、交给 3s 兜底 —— 宁可慢收, 不可误判。 */
    _snapshotTruth(state) {
      const keys = Object.keys(this.pendingOps);
      if (!keys.length) { this.truthSnapshot = null; return; }
      const want = new Set(keys);
      const m = new Map();
      const take = (r) => {
        if (!r || !want.has(r.hash) || m.has(r.hash)) return;
        const op = this.pendingOps[r.hash];
        if (!op) return;
        const v = {};
        for (const k of Object.keys(op.patch)) v[k] = r[k];
        m.set(r.hash, v);
      };
      for (const r of state.torrents || []) take(r);
      for (const r of state.singles || []) take(r);
      for (const g of state.groups || []) for (const mm of g.members || []) take(mm);
      this.truthSnapshot = m;
    },
    /* 乐观补丁是否已落回真值: 只比**补丁改过的那几个键**, 且只比服务端这一轮给的值。 */
    _optimisticSettled(hash, op) {
      const t = this.truthSnapshot && this.truthSnapshot.get(hash);
      if (!t) return false;  // 本轮 payload 没带它的真值 -> 不算对齐(继续贴, 3s 兜底收尾)
      for (const k of Object.keys(op.patch)) {
        if (t[k] !== op.patch[k]) return false;
      }
      return true;
    },
    /* 组行是否有成员在飞(模板绑 is-pending)。**组行的颜色本身不需要额外补丁** ——
     * 组行状态色取自 decoratedGroups 的 status.primary, 而它是 _aggStatus(成员 kind) 算出来的
     * computed, 成员 kind 被 applyOptimistic 改过之后会自动重算(2026-09-19 实测:
     * 整组暂停后组行 class 由 s-checking 变 s-paused)。缺的只是"在飞"这个视觉标记。 */
    isGroupPending(g) {
      if (!this.pendingAny) return false;   // 常见路径 O(1)
      return (g.members || []).some((m) => this.isPending(m.hash));
    },
    /* 集行是否有成员在飞(同 isGroupPending, 但集的成员是 memberByHash 的**拷贝**)。
     * 取 hash 走 memberHashesOf(项目约定: 集成员在前端已是对象, 直接取 .hash 会被静态守阵拦下 ——
     * 那个守阵防的是"把对象当 hash 发给后端", 这里虽是本地查表, 但统一走归一函数没有代价)。 */
    isEpPending(e) {
      if (!this.pendingAny) return false;
      return this.memberHashesOf(e.members).some((h) => this.isPending(h));
    },
    /* 剧行(show 级)是否有种子在飞 —— 与 isGroupPending / isEpPending 同一族, 是 BUG-3 当年
     * 漏掉的第三层(issues/26-09-19-1959-webui-show-row-no-pending)。
     * 语义: 该剧**任何一集**有成员在飞即在飞(整剧操作会把该剧全部成员一起补丁)。
     * 剧行默认折叠(集行不渲染), 所以这一层是折叠态下**唯一**能显示"在飞"的元素。
     * 复用 isEpPending 逐集查(hash 归一仍走 memberHashesOf), 命中即返回 —— 不为它单开一套
     * hash 收集逻辑, 免得再长出一份与守阵不一致的写法。 */
    isShowPending(s) {
      if (!this.pendingAny) return false;   // 常见路径 O(1)
      for (const sn of s.seasons || []) {
        for (const e of sn.episodes || []) {
          if (this.isEpPending(e)) return true;
        }
      }
      return false;
    },
    /* 集行状态色。真值 `e.state` 是后端按 _SHOW_STATE_RANK 聚合后**当标量拷贝**进来的 ——
     * decoratedShows 每轮重建 {...e}, 但 e.state 只在下一次 /api/state 回包时才更新,
     * 所以成员 kind 被乐观补丁改掉后集行颜色不动(BUG-3: 整集暂停后仍是 s-seeding)。
     * 有成员在飞时按**同一张 STATE_RANK 表**现算; 没有在飞时一律用后端真值 ——
     * 不碰"筛选后成员子集"与后端全量成员口径不一致的语义(那是另一件事)。 */
    epState(e) {
      if (!this.isEpPending(e)) return e.state;
      return this._aggKind(e.members) || e.state;
    },
    async act(action) {
      this.menu.visible = false;
      if (!this.menu.key) return;
      const label = this._actionText(action);
      const isRe = action === "reannounce";
      /* P0-3「点击即变」: 补丁必须**先于** POST 贴上(与 actEpisode / bulk 同一顺序)。
       * 放在 await 之后 = 把即时反馈押在网络往返上 —— 真机大库下 POST 可达秒级, 用户看到的就是
       * "点了 2-4s 才变"(issue 26-09-19-1939-webui-optimistic-latency; 受控测量: 注入 2000ms
       * POST 延迟时补丁 2012ms 才贴, 改顺序后恒 ~0ms)。reannounce 结果在远端, 不做乐观。 */
      const g = isRe ? null : this._findGroup(this.menu.key);
      const hashes = isRe ? [] : (g && g.members ? g.members : []).map((m) => m.hash);
      const t0 = isRe ? 0 : this._newCmdStats(action);
      if (!isRe) {
        this.applyOptimistic(hashes, action);
        this._markCmdPatch(t0);
      }
      try {
        const resp = await this.api(`/api/groups/${this.menu.key}/${action}`, { method: "POST" });
        if (isRe) {
          // 强反馈状态机: 常驻"等待中" -> 原位换成 成功(绿) / 超时失败(琥珀), 不再用红色警告样式
          const tid = this.toast("强制汇报等待中…(已投递, tracker 确认最长 30s)", "busy", 0, { sticky: true });
          const r = await this.waitCmd(resp.cmd_id, 40000, { firstMs: 500, capMs: 1000 });
          if (r.ok) this._finishToast(tid, "ok", "强制汇报成功(tracker 已确认)", 3000);
          else this._finishToast(tid, "timeout", `强制汇报超时失败: ${r.error}`, 6000);
        } else {
          this._markCmdPost(t0);
          const r = await this.waitCmd(resp.cmd_id);
          this.resolveOptimistic(hashes, r.ok);
          // 回执已带真值 ⇒ 就地撤下(与库大小解耦); 没对上才补拉一次(旧服务端 / 取不到真值)
          /* D2: 真值不再走"回执里带 + 拉全量补"。回执**不带 truth**(带上未落地的真值 =
           * 让前端采纳命令前的旧值 ⇒ 弹回), 真值由 `truth` 事件推送(见 onTruthEvent)。
           * 这里删掉的 1500ms 拉取预算, 真机实测是撤下 2947ms 中的 1688ms 大头。 */
          if (r.ok) this.toast(`已执行: ${label}整组`, "ok", 2500);
          else this.toast(`${label}整组失败: ${r.error}`, "error", 8000);
        }
      } catch (e) {
        if (!isRe) this.resolveOptimistic(hashes, false);  // 发送失败: 同样回滚, 不留假状态
        if (!e.auth) this.toast("命令发送失败: " + e.message, "error");
      }
    },
    /* 选中集合拆解: 虚拟行(未归组命中种子)无真实组 key, 转为单种子命令; 已消失的目标跳过 */
    _bulkTargets() {
      const groupKeys = [];
      const memberHashes = [...this.selMembers];
      for (const k of this.selGroups) {
        const g = this._findGroup(k);
        if (!g) continue;
        if (g.virtual) memberHashes.push(g.members[0].hash);
        else groupKeys.push(k);
      }
      return { groupKeys, memberHashes };
    },
    /* 批量动作: pause/resume/recheck **合单**为一条 bulk 命令(一次 POST + 一个聚合回执);
     * reannounce 仍逐目标投递(后端 _BULK_ACTIONS 不含它 —— tracker 确认要逐个跟踪)。
     * 合单前 100 个目标 = 100 次 POST + 100 条回执轮询, 后端还要串行跑 100 次 qB 调用
     * (在主循环线程上, 期间界面"卡住"); 合单后是 1 + 1。 */
    async bulkAct(action) {
      const { groupKeys, memberHashes } = this._bulkTargets();
      const label = action === "recheck" ? "重新校验" : this._actionText(action);
      if (action !== "reannounce") {
        // 后端 bulk 会自己展开 keys 的组成员并与 hashes 合并去重, 组级端点不支持的
        // recheck 也因此不必在前端展开 —— 只有组没有成员时后端计一个"缺失组"。
        if (!groupKeys.length && !memberHashes.length) return;
        const hashes = [...memberHashes];
        for (const k of groupKeys) {
          const g = this._findGroup(k);
          if (g) for (const m of g.members) hashes.push(m.hash);
        }
        const t0 = this._newCmdStats(action);
        this.applyOptimistic(hashes, action);  // P0-3: 点击即变(失败会回滚)
        this._markCmdPatch(t0);
        try {
          const resp = await this.api("/api/torrents/bulk", {
            method: "POST",
            body: JSON.stringify({ action, keys: groupKeys, hashes: memberHashes }),
          });
          this._markCmdPost(t0);
          const r = await this.waitCmd(resp.cmd_id);
          this.resolveOptimistic(hashes, r.ok);
          /* D2: 真值不再走"回执里带 + 拉全量补"。回执**不带 truth**(带上未落地的真值 =
           * 让前端采纳命令前的旧值 ⇒ 弹回), 真值由 `truth` 事件推送(见 onTruthEvent)。
           * 这里删掉的 1500ms 拉取预算, 真机实测是撤下 2947ms 中的 1688ms 大头。 */
          const n = groupKeys.length + memberHashes.length;
          if (r.ok) this.toast(`已执行: ${label}(${n} 个目标)`, "ok", 2500);
          else this.toast(`${label}失败: ${r.error}`, "error", 8000);
        } catch (e) {
          this.resolveOptimistic(hashes, false);  // 发送失败: 同样回滚, 不留假状态
          if (!e.auth) this.toast("命令发送失败: " + e.message, "error");
        }
        return;
      }
      const jobs = [
        ...groupKeys.map((k) => `/api/groups/${k}/${action}`),
        ...memberHashes.map((h) => `/api/torrents/${h}/${action}`),
      ];
      if (!jobs.length) return;
      // 批量汇报: 常驻"等待中"(含目标数), 回执齐后原位换汇总终态(成功/超时, 琥珀不用红警告)
      const tid = this.toast(`强制汇报等待中…(${jobs.length} 个目标, tracker 确认最长 30s)`, "busy", 0, { sticky: true });
      const results = await Promise.allSettled(
        jobs.map((p) =>
          this.api(p, { method: "POST" }).then((r) => this.waitCmd(r.cmd_id, 40000, { firstMs: 500, capMs: 1000 }))
        )
      );
      const fails = results.filter((r) => r.status === "rejected" || !r.value.ok);
      if (!fails.length) {
        this._finishToast(tid, "ok", `强制汇报成功(tracker 已确认, ${jobs.length} 个目标)`, 3000);
        return;
      }
      const firstErr = fails[0].status === "rejected" ? fails[0].reason.message : fails[0].value.error;
      this._finishToast(
        tid,
        "timeout",
        `强制汇报: 成功 ${jobs.length - fails.length}, 失败 ${fails.length}${firstErr ? ` (${firstErr})` : ""}`,
        6000
      );
    },
    async actTorrent(action) {
      this.menu.visible = false;
      if (!this.menu.hash) return;
      const label = this._actionText(action);
      const isRe = action === "reannounce";
      // 同 act(): 补丁先于 POST(见那里的注释与 issue 26-09-19-1939-webui-optimistic-latency)
      const hashes = isRe ? [] : [this.menu.hash];
      const t0 = isRe ? 0 : this._newCmdStats(action);
      if (!isRe) {
        this.applyOptimistic(hashes, action);
        this._markCmdPatch(t0);
      }
      try {
        const resp = await this.api(`/api/torrents/${this.menu.hash}/${action}`, { method: "POST" });
        if (isRe) {
          const tid = this.toast("强制汇报等待中…(已投递, tracker 确认最长 30s)", "busy", 0, { sticky: true });
          const r = await this.waitCmd(resp.cmd_id, 40000, { firstMs: 500, capMs: 1000 });
          if (r.ok) this._finishToast(tid, "ok", "强制汇报成功(tracker 已确认)", 3000);
          else this._finishToast(tid, "timeout", `强制汇报超时失败: ${r.error}`, 6000);
        } else {
          this._markCmdPost(t0);
          const r = await this.waitCmd(resp.cmd_id);
          this.resolveOptimistic(hashes, r.ok);
          /* D2: 真值不再走"回执里带 + 拉全量补"。回执**不带 truth**(带上未落地的真值 =
           * 让前端采纳命令前的旧值 ⇒ 弹回), 真值由 `truth` 事件推送(见 onTruthEvent)。
           * 这里删掉的 1500ms 拉取预算, 真机实测是撤下 2947ms 中的 1688ms 大头。 */
          if (r.ok) this.toast(`已执行: ${label}该种子`, "ok", 2500);
          else this.toast(`${label}该种子失败: ${r.error}`, "error", 8000);
        }
      } catch (e) {
        if (!isRe) this.resolveOptimistic(hashes, false);  // 发送失败: 同样回滚, 不留假状态
        if (!e.auth) this.toast("命令发送失败: " + e.message, "error");
      }
    },
    /* 复制种子信息(种子页右键 R1A): clipboard API 优先, execCommand 降级(非安全上下文/权限拒绝);
     * 无论成功失败都给 toast 反馈 */
    async _copyText(text, label) {
      let ok = false;
      try {
        if (navigator.clipboard && window.isSecureContext) {
          await navigator.clipboard.writeText(text);
          ok = true;
        }
      } catch { ok = false; }
      if (!ok) {
        // 降级: 离屏 textarea + execCommand(旧浏览器 / file:// 等 clipboard API 不可用场景)
        const ta = document.createElement("textarea");
        ta.value = text;
        ta.style.position = "fixed";
        ta.style.opacity = "0";
        document.body.appendChild(ta);
        ta.select();
        try { ok = document.execCommand("copy"); } catch { ok = false; }
        document.body.removeChild(ta);
      }
      if (ok) this.toast(`已复制${label}`, "ok", 2000);
      else this.toast("复制失败: 浏览器未授权剪贴板访问", "error");
    },
    /* 右键菜单复制项: field = name | hash | magnet(数据取 memberByHash 的 SEED_ITEM 完整字段) */
    /* 导出 .torrent(种子页右键 R2 补遗): fetch 字节 → blob 下载(Bearer 走 header, 不能用 a href 直链;
     * 不能用 this.api —— 它固定 resp.json(), 而这里是二进制流) */
    async exportTorrent() {
      this.menu.visible = false;
      const hash = this.menu.hash;
      if (!hash) return;
      try {
        const resp = await fetch(`/api/torrents/${hash}/export`, { headers: { Authorization: `Bearer ${this.token}` } });
        if (resp.status === 401) {
          this._logout("密钥无效或已更换");
          return;
        }
        if (!resp.ok) {
          const detail = await resp.json().catch(() => ({}));
          throw new Error(detail.detail || `HTTP ${resp.status}`);
        }
        const buf = await resp.arrayBuffer();
        const m = this.memberByHash.get(hash) || {};
        const name = String(m.name || hash).replace(/["\\/]/g, "_") + ".torrent";
        const url = URL.createObjectURL(new Blob([buf], { type: "application/x-bittorrent" }));
        const a = document.createElement("a");
        a.href = url;
        a.download = name;
        document.body.appendChild(a);
        a.click();
        a.remove();
        setTimeout(() => URL.revokeObjectURL(url), 4000);
        this.toast("已导出 .torrent", "ok", 2500);
      } catch (e) {
        if (!e.auth) this.toast("导出失败: " + e.message, "error", 8000);
      }
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
