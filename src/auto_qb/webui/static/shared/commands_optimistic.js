/* commands_optimistic.js — R4 大文件拆分(计划 26-11-02-2342 §07)
 * 命令 · 乐观补丁 / 真值快照 / 撤下判据。
 * 只搬方法定义, 实现逐行未改; 根文件已定义该域, 本片段在其后原地扩充(Object.assign)。
 * 加载序 = 四套皮肤 index.html 清单里紧跟根文件之后(与拆分前同一迭代替换序)。
 */
Object.assign(window.AQB_COMMANDS.methods, {
    _optimisticPatch(action, row) {
      if (action === "pause") return { kind: "paused" };
      if (action === "resume") return { kind: row && row.progress >= 1 ? "seeding" : "downloading" };
      return null;  // 不在白名单 -> 不做乐观
    },
    /* 显式补丁注册口(计划 26-10-30-0610 S1): 补丁由调用方给出, 不查 _optimisticPatch 白名单。
     * 首个消费者 = 种子重命名(patch = {name}, drawer.js::editRename): 实测回执 ~5.6ms 但新名
     * 进 sync 快照要 ~1.7s(扑空 5/5), 不贴补丁行名就白等一个 sync 周期。回执/真值/兜底全走
     * 既有四件套, 对它们零改动: resolveOptimistic(ok -> hold) / _expirePending(3s/8s 兜底) /
     * reapplyPending(整表替换后重贴) / _snapshotTruth + _optimisticSettled(通用分支逐键比对,
     * 天然支持 {name})。
     * !与 applyOptimistic 的两点差异:
     *   1. 行不在当前视图(hash 不在 _forEachRow 三数组)时**也照常注册 op** —— 否则该 hash 没有
     *      回执入口, hold/回滚语义整体断链; 对空 prev 的回滚 Object.assign 是 no-op, 无害。
     *   2. 不做白名单判定 —— 调用方必须只传"值来自我们"的字段(§01 不变量: 值覆盖只盖
     *      「值来自我们」的字段; name 是我们下发的值, 符合)。
     * !真值语义: pause/resume 的真值是 kind, rename 的真值是 **name**(由 _optimisticSettled
     *   对快照逐键比对); onTruthEvent 的 kind 注入必须带 action 守卫 —— 见该方法内注释。 */
    applyOptimisticPatch(hashes, action, patch) {
      if (!patch || !Object.keys(patch).length) return;
      const now = Date.now();
      for (const h of hashes || []) {
        if (!h) continue;
        const prev = {};
        this._forEachRow(h, (row) => {
          for (const k of Object.keys(patch)) prev[k] = row[k];
          Object.assign(row, patch);
        });
        // grey = 压暗(回执到即结束) / hold = 值覆盖保持到真值对齐(防弹回), 与 applyOptimistic 同语义
        this.pendingOps[h] = { patch, prev, ts: now, action, grey: true, hold: false };
      }
      // 目标数供 settleMs 的 [perf] 阈值分档(见 _markCmdSettle)
      if (this.cmdStats) this.cmdStats.targets = (hashes || []).length;
    },
    _forEachRow(hash, fn) {
      for (const r of this.torrents || []) if (r.hash === hash) fn(r);
      for (const r of this.singles || []) if (r.hash === hash) fn(r);
      for (const g of this.groups || []) for (const m of g.members || []) if (m.hash === hash) fn(m);
    },
    /* 回滚的抽屉对称面(issue 26-10-30-0818): editRename 贴补丁时把 drawer.detail.name 一并改成
     * 新名(D3 覆盖面), 但 detail 是独立拉取的对象、不在 _forEachRow 三数组里 —— 失败/超时回滚
     * 只还原行的话, 抽屉标题回落分支(drawerTitle 在 hash 不在视图时读 detail.name)会停留新名,
     * 直到重开抽屉/下次拉详情才纠正。两个回滚出口(resolveOptimistic 失败分支 / _expirePending
     * 兜底)都经这里把**行同款回滚值**(op.prev, 兜底时 t || op.prev)对称写回 detail; 抽屉没开着
     * 或已切到别的 hash 就跳过 —— 重开时自然重新拉取。只写 patch 出现过的键且值取自 rolled,
     * rolled 缺键(undefined)跳过, 不写垃圾。 */
    _syncDrawerRollback(hash, patch, rolled) {
      const d = this.drawer;
      if (!d || !d.open || d.hash !== hash || !d.detail || !rolled) return;
      for (const k of Object.keys(patch || {})) {
        if (rolled[k] !== undefined) d.detail[k] = rolled[k];
      }
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
           * !兜底期限**从回执到达重算**且放宽到 TRUTH_HOLD_MS: 压暗已结束, 晚释放没有观感
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
        this._syncDrawerRollback(h, op.patch, op.prev);  // 抽屉 detail 对称还原(issue 26-10-30-0818)
        delete this.pendingOps[h];
      }
      this._markCmdSettle();  // pendingOps 的出口之一(失败回滚)
    },
    reapplyPending() {
      /* 每轮 refresh 整表替换会盖掉乐观值, 这里把仍 pending 的补丁重新贴上。
       * !**真值已到就收工**(issue 26-09-19-2024-webui-truth-convergence): 原先这里只管贴,
       * pendingOps 唯一的出口是 3s 兜底 => 真值早就到了、行还半透明挂着, 用户看到的就是
       * "点了之后 2-4s 才恢复正常"。现在逐个比对**服务端真值快照** => 对齐就立即清掉。 */
      for (const h of Object.keys(this.pendingOps)) {
        /* !不再跳过"已结束压暗"的 op: hold 期间必须继续盖住行上的值, 否则轮询带回的
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
     * !**必须比服务端原始值, 不能比行上的当前值**: 行在上一轮已经被贴过补丁了, 拿行上的值
     *   跟补丁比 = 跟自己比 => 首轮必"匹配"、pending 立刻消失(2026-09-19 实测 28ms 就清了,
     *   而桩服务真值 +120ms 才到 —— 断言全绿却什么都没测到)。
     * !**拷值不拷引用**: 赋值后 `this.torrents` 与 payload 是同一批对象, 补丁随后就改到它们,
     *   存引用等于没存。
     * !只认 payload 里**真的带了**的 hash: 当前视图的 payload 可能不含它(如追剧视图只回
     *   shows), 那时返回 false => 继续贴、交给 3s 兜底 —— 宁可慢收, 不可误判。 */
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
        /* 顺手让 op.prev 保鲜(report 26-10-11-2017 §6.3): prev 的语义是"最后已知服务端真值",
         * 兜底回滚要回这里(onTruthEvent 在真值到达时就是这么刷的)。批量路径没有真值事件,
         * 就在这里用服务端快照补上 —— 否则 prev 永远停在点击那一刻, 超时必打回旧值。 */
        op.prev = { ...op.prev, ...v };
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
      /* 判据与服务端 _truth_landed 同谓词(report 26-10-11-2017 §4.4): 不要求"服务端 kind 严格
       * 等于预测值" —— resume 的落地态有 downloading/seeding/checking 等多种, 前端预测只猜得出
       * 两种, 严格相等会让预测偏一格的动作永远收敛不了, 补丁一直挂到兜底超时。 */
      if (op.action === "resume") return t.kind !== "paused";
      if (op.action === "pause") return t.kind === "paused";
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
    /* ---------------- 强制重新汇报闸门(qB 口径, 单一行为出口) ----------------
     * 非活跃目标(暂停/停止·排队·校验·错误/文件缺失)不允许强制重新汇报 —— 与 qB 的
     * `actionForceReannounce->setEnabled(false)` 同语义(commit aa189a7, issue #12080);
     * 判据单点 = decorate.js::reannounceTargetsGate(任一目标活跃即可用, 与 qB
     * oneCanForceReannounce 同口径)。
     * 前端两层: 入口处"置灰可见 + title 提示原因"(ctx-menus.html / drawer_tpl 04-06),
     * 行为层由本方法兜底 —— 菜单项仍可被点(置灰只改样式, 见 .ctx-item.is-gated 口径),
     * 键盘与详情面板又是另外两条入口, 不接一层就绕得过去。
     * 返回 false = 已给 toast, 调用方直接 return(尚未发请求, 零副作用)。
     *
     * !本闸门只判"允不允许"(集合级全有全无, 与 qB 的 oneCanForceReannounce 一致),
     *   **不等**于"发给谁" —— 混选(1 活跃 + N 非活跃)按 qB 口径是**放行**的, 若照集合全量
     *   投递, qB 引擎会对非活跃的静默空转而我们的确认层仍会为它们白等窗口, 最终把一次
     *   干净的成功报成「未确认 N」。故放行后的投递集合由 decorate.js::reannouncePlan
     *   再收敛一次(只投活跃), 两道是"闸门 / 计划"的分工, 不可互相替代。 */
    _guardReannounce(t) {
      const g = this.reannounceTargetsGate(t);
      if (g.ok) return true;
      this.toast(g.title, "error", 7000);
      return false;
    },
});
