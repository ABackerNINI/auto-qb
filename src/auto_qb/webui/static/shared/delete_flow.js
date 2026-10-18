/* auto-qb WEB UI · 删除流程(详情统计/确认框/连带文件)
 *
 * app.js 按域拆分出的片段(2026-09-20)。约定与 config_editor.js / config_rules.js 同一范式:
 * 挂到 window.AQB_DELETE, 由 app.js 末尾 app.mixin(window.AQB_DELETE) 注入同一个 Vue 实例 ——
 * 方法体里的 this 仍是那个组件实例, 跨模块互调与拆分前完全等价。
 *
 * !本文件在 HTML 里必须排在 app.js **之前**(app.js 末尾要读 window.AQB_DELETE);
 *   用到的列模型常量(TABLE_COLUMNS / MIN_COL_PX / STATE_RANK …)仍单点定义在 app.js 顶部。
 */

/* 「不能删」档位集(2026-09-25): danger=考察中(进行中, 橙) —— 删除可能新增 H&R 惩罚, 点名拦截。
 * failed=考核未通过(终态红档)**不在**此集合: 考核期已过、结果已成立, 删除无新增惩罚,
 * 点名「不能删」不符合实际(2026-09-25 用户修正)。warning=疑似辅种(黄档, 2026-09-30 计划
 * hr-trigger-semantics)**不在**此集合: 黄档警示「注意」不禁止删除, 与语义一致。
 * token 由后端 hr.resolve.safety_display 单点派生, 前端只集合比对; 消费点 = 删除确认框的
 * HR 风险点名(_hrRiskOf) —— 与删除链同一目标集合派生。 */
const HR_NO_DELETE = new Set(["danger"]);

/* 非活跃类 warn 的识别(D6 竞态兜底, issue 26-10-17-1703): 后端第二道闸的回执文案两种形态 ——
 *   单种: "未确认: 种子非活跃(暂停/停止/排队/校验中/错误), qB 静默忽略强制汇报"
 *         (commands.py::REANNOUNCE_INACTIVE_SKIP)
 *   组:   "未确认: 组内 N 个种子均非活跃, 已跳过"
 * 二者都含「非活跃」二字。web 回执没有错误码, 这是**文本**判据 —— 后端常量与本函数关键词由
 * 静态守阵 test_frontend_reannounce_inactive_gate_wiring 双向钉住, 防悄悄漂移。 */
function _reannounceWarnInactive(err) {
  return typeof err === "string" && err.includes("非活跃");
}

window.AQB_DELETE = {
  methods: {
    /* DLG-02: 批量删除文案按选择构成计数(仅辅种=N 个辅种 / 仅种子=N 个种子)。
     * 用 _bulkTargets 的有效口径 —— 虚拟行(未归组命中)无真实组 key、按种子投递, 计入"种子"
     * 而非"辅种", 保证确认框标题/提交体/回执三处一致; 空串 = 选中项均已失效。
     * 消费点 = bulkDelete(右键批量删除菜单项)的确认框标题; 计数随**权威选择**而非当前视图漂移
     * (在种子页看"N 个辅种"不变, 这正是"三视图打通"的直观体现)。
     * WARN: 方法名不得以 `_` 开头: Vue 模板编译器不解析下划线前缀标识符
     *   (会报 "_xxx is not defined" 且整块渲染失败 —— 2026-09-17 浏览器冒烟实测)。
     */
    bulkCountText() {
      const { groupKeys, memberHashes } = this._bulkTargets();
      const parts = [];
      if (groupKeys.length) parts.push(`${groupKeys.length} 个${L10N_GROUP}`);
      if (memberHashes.length) parts.push(`${memberHashes.length} 个种子`);
      return parts.join("、");
    },
    async bulkDelete() {
      const { groupKeys, memberHashes } = this._bulkTargets();
      if (!groupKeys.length && !memberHashes.length) return;
      const countText = this.bulkCountText();
      // 摘要计数(DLG-01 收缩: 确认框不再列逐条成员明细, 只保留目标摘要+计数):
      // 组展开到成员级, 与选中的种子并集去重 —— 与后端 bulk 组键展开(级联在册成员,
      // 与 hashes 合并去重)同口径; 成员大小经 memberByHash 解析(groups ∪ singles ∪ torrents 全量)。
      // R10-16: 确认框的详情行改由 _deleteFlow 统一派生, 这里只算 body 要用的**种子数**(seen.size)。
      const seen = new Set();
      const countMember = (m) => {
        if (!m || seen.has(m.hash)) return;
        seen.add(m.hash);
      };
      for (const k of groupKeys) {
        const g = this._findGroup(k);
        if (!g) continue;
        if (g.virtual) countMember(g.members[0]);
        else for (const m of g.members || []) countMember(m);
      }
      for (const h of memberHashes) countMember(this.memberByHash.get(h));
      // FX-16: 统一走 _deleteFlow(与右键同一套: 目标明细 + 汇报前置 + 等聚合回执 + 收尾清选择)
      // R10-16: 不再自传 details(由 _deleteFlow 从目标集合派生), 四个入口的窗口结构由此完全一致
      await this._deleteFlow({
        keys: groupKeys,
        hashes: memberHashes,
        title: `删除 ${countText}`,
        body: `将删除选中目标内的全部种子, 共 ${seen.size} 个。建议删除前先向 tracker 汇报, 避免留下未汇报的 H&R 记录。`,
        countText,
        label: countText,
      });
    },
    /* ---------------- FX-16 删除链统一 ----------------
     * 旧实现是**两条链**: 右键(逐目标专用端点, 不等回执)与 批量(bulk 单命令, 等聚合回执),
     * 确认框内容也分叉(逐目标详情 vs 纯计数)。统一成一条链, **以右键的行为为准**
     * (目标明细 + 汇报前置 + 汇报失败即中止保留), 并保留批量侧更稳的两点(单命令聚合回执、
     * 收尾清选择)。四个入口(delGroup / delTorrent / delEpisode / bulkDelete)只负责组织 targets。
     *
     * targets = { keys[], hashes[], title, body, details[], countText, label }
     * 注: /api/groups/{k}/delete 与 /api/torrents/{h}/delete 端点**保留不动**(旧 UI 与第三方脚本仍可用)。
     */
    /* R10-16 删除详情行统一派生: 四个入口(右键组/右键种子/批量/整集整剧)过去各自拼 details,
     * 结果"同壳不同构"(右键 5 行含站点/保存路径, 批量只有 2 行摘要) —— 用户看到的就是
     * "不是同一个删除窗口"。现在入口只交目标集合, 明细行一律由本函数算: 目标 -> 计数 ->
     * 站点集合 -> 保存路径集合 -> 总大小; 单目标自然退化成逐项明细(站点/路径回到单体值)。
     * 多目标走集合摘要(决策 D8-A): 避免几十个目标把弹窗撑爆。 */
    /* 目标 -> 成员集合(组展开到成员级, 与选中的种子并集去重): _deleteDetails 与 HR 风险统计
     * 共用这一份收集 —— "删除链与风险点名看到的必须是同一批种子" */
    _deleteMembers(keys, hashes) {
      const seen = new Map();  // hash -> member(组展开与 hashes 去重)
      const collect = (m) => {
        if (m && m.hash && !seen.has(m.hash)) seen.set(m.hash, m);
      };
      for (const k of keys || []) {
        const g = this._findGroup(k);
        if (!g) continue;
        if (g.virtual) collect(g.members[0]);
        else for (const m of g.members || []) collect(m);
      }
      for (const h of hashes || []) collect(this.memberByHash.get(h));
      return [...seen.values()];
    },
    /* HR 风险点名(P2, 2026-09-25): 目标里「不能删」(HR_NO_DELETE: danger)的种子 ——
     * 按来源短语去重, 名字最多列 3 个; count=0 返回 null(确认框不加风险行) */
    _hrRiskOf(members) {
      const risky = members.filter((m) => HR_NO_DELETE.has(m.hr_safety));
      if (!risky.length) return null;
      const srcs = [...new Set(risky.map((m) => m.hr_safety_text).filter(Boolean))].join(" / ");
      const names = risky.slice(0, 3).map((m) => m.name || m.hash.slice(0, 12)).join("、");
      return { count: risky.length, srcs, names, more: risky.length > 3 ? ` 等 ${risky.length} 个` : "" };
    },
    _deleteDetails(keys, hashes) {
      const members = this._deleteMembers(keys, hashes);
      const sites = [...new Set(members.map((m) => m.site).filter(Boolean))];
      const paths = [...new Set(members.map((m) => m.save_path).filter(Boolean))];
      // 总大小 = X(Σ 成员 size); 实际占用 = Y(occ_key 内容单元去重, 单元取 max) ——
      // 与筛选行选中摘要**同一函数同一口径**(selection.js::selSizeSummaryOf, 计划
      // 26-10-18-2013 D12): 删除同辅种组多站点副本时, 磁盘只释放一份。"实际占用"行仅
      // Y<X 时追加(常态单目标/未归组种子不出现, 不扰动既有五行结构)。
      const sizeSum = this.selSizeSummaryOf(members);
      const single = (keys || []).length + (hashes || []).length <= 1 && members.length <= 1;
      // 目标: 单目标退化为**它的名字**(单辅种 = 辅种名, 单种子 = 种子名), 多目标走集合摘要
      const target = single && members.length === 1 ? (members[0].name || members[0].hash.slice(0, 12))
        : `${(keys || []).length} 个${L10N_GROUP} · ${members.length} 个种子`;
      const rows = [
        { icon: "#i-cards", label: "目标", value: target, wide: true },
        { icon: "#i-layers", label: "成员", value: `${members.length} 个种子` },
        { icon: "#i-globe", label: "站点", value: sites.join(", ") || "—" },
        { icon: "#i-folder-open", label: "保存路径", value: paths.join(" · ") || "—", wide: true },
        { icon: "#i-hdd", label: "总大小", value: this.fmtSize(sizeSum.total) },
      ];
      if (sizeSum.occupy < sizeSum.total) {
        rows.push({
          icon: "#i-hdd", label: "实际占用", value: this.fmtSize(sizeSum.occupy),
          hint: "辅种组内多站点副本只计一份(取最完整副本)",
        });
      }
      return rows;
    },
    async _deleteFlow(targets) {
      this._auditScope("delete", targets);  // S4 运行时审计(默认关, 只记账)
      const keys = targets.keys || [];
      const hashes = targets.hashes || [];
      if (!keys.length && !hashes.length) return;
      const members = this._deleteMembers(keys, hashes);
      const details = this._deleteDetails(keys, hashes);
      // P2 HR 风险点名(2026-09-25): 目标含「不能删」(HR_NO_DELETE: danger)种子时, 确认框点名
      // 数量 + 来源档位 + 前几个名字 —— 最后一道防误删闸门(来源短语由后端算好, 前端只拼)
      const risk = this._hrRiskOf(members);
      if (risk) {
        details.push({
          icon: "#i-warn", label: "HR 风险", wide: true,
          value: `${risk.count} 个仍在 HR 管束(${risk.srcs}): ${risk.names}${risk.more}，删除可能导致站点 H&R 惩罚`,
        });
      }
      /* reannounce-inactive-gate 闸门层(issue 26-10-17-1703): 删除链是「非活跃禁强制汇报」
       * 专题(坑档 pitfalls/web-ui/reannounce-inactive-gate.md)入口清单中唯一漏接的入口 ——
       * 目标全非活跃时「删除前强制汇报」不可能有回执(后端第二道闸必回 warn「种子非活跃」),
       * 旧实现请求照发 -> _reannounceAll 的 warn 不放行 -> 删除被整体中止, 用户须手动取消
       * 勾选才能删。这里在开框前先把复选框禁用+取消勾选(D3); 混选的投递收敛见下方
       * reannouncePlan(两层分工: 闸门判"允不允许", 计划判"发给谁")。 */
      const reannounceGate = this._deleteReannounceGate(members);
      const res = await this._confirmDelete({
        title: targets.title,
        body: targets.body,
        // R10-16: 入口不再传 details(传了也忽略) —— 四入口看到的窗口结构完全一致
        details,
        reannounceGate,
      });
      if (!res) return;
      const deleteFiles = res.checks.delete_files;
      if (res.checks.reannounce) {
        /* 投递层(与右链同源单点 decorate.js::reannouncePlan, D1): 非活跃目标收敛掉再投 ——
         * 照发只会命中后端第二道闸回 warn, 而 warn 不放行删除 ⇒ 删除被中止(本 issue 的现象)。
         * 解析不出(组行已消失)的目标原样走组端点, 由后端给显式回执。 */
        const plan = this.reannouncePlan({ keys, hashes });
        const jobs = [
          ...plan.keys.map((k) => `/api/groups/${k}/reannounce`),
          ...plan.hashes.map((h) => `/api/torrents/${h}/reannounce`),
        ];
        if (!jobs.length) {
          /* 闸门放行但计划为空(渲染到点击之间全转为非活跃的竞态, D6): 无可投递目标 ——
           * 汇报整体跳过, 不挡删除(D4: 非活跃 warn 降级为 skip 的同一口径; 空计划且零跳过
           * 时不打扰用户, 删除自身的回执会说明结果)。 */
          if (plan.skipped) this.toast(`目标均非活跃, 跳过强制重新汇报, 直接删除`, "ok", 3000);
        } else {
          const ok = await this._reannounceAll(jobs, targets.label, plan.skipped);
          if (!ok) return;  // 活跃目标汇报失败/未确认: 已提示且保留未删除(保守口径不放宽)
        }
      }
      // 投递删除: 统一走 bulk 单命令并等聚合回执(比旧右键的"已投递"更可信: 失败可见)
      try {
        const resp = await this.api("/api/torrents/bulk", {
          method: "POST",
          body: JSON.stringify({ action: "delete", keys, hashes, delete_files: deleteFiles }),
        });
        const r = await this.waitCmd(resp.cmd_id);
        if (r.ok) this.toast(`已删除: ${targets.countText}${deleteFiles ? "(含文件)" : ""}`, "ok", 3000);
        else this.toast(`删除未完全成功: ${r.error}`, "error", 8000);
      } catch (e) {
        if (!e.auth) this.toast("删除命令发送失败: " + e.message, "error");
      }
      this.clearSelection();  // 列表交下一轮 rid 轮询自然刷新(不主动 refresh)
    },
    /* 汇报前置: 逐目标投递并**全部等回执**; 全部确认成功(ok)或跳过(非活跃)才返回 true。
     * 回执按 status 分流(计划 26-10-05-0923 D4=warn; issue 26-10-17-1703 增 skip 桶):
     *   ok    = tracker 已确认;
     *   skip  = 非活跃 warn(「种子非活跃…」/「组内均非活跃…」) —— libtorrent 对非活跃种子
     *           直接空转, 永远等不到回执, 既不算失败**也不挡删除**; 正常路径已被
     *           reannouncePlan 收敛, 走到这里=渲染到点击之间状态变化的竞态兜底(D6);
     *   warn  = 已受理·推迟/未确认·停止/超时 —— 不是失败但**仍不放行删除**(推迟中的汇报
     *           要等最小间隔过期才真正发出, 立即删除会随种子一并丢失, 正是汇报前置要避免的
     *           H&R 风险; 未确认则没有任何「tracker 已接受」的正证据; 删除不可逆, 按保守
     *           口径处理, 不借修 bug 之机放宽);
     *   error = tracker 明确拒绝(含投递失败/等待超时)。
     * 文案诚实区分「失败/未确认/跳过」; skipped = 投递前收敛掉的非活跃数(等待态就报, D5)。 */
    async _reannounceAll(jobs, label, skipped = 0) {
      if (!jobs.length) return true;
      const skipTxt = skipped ? `(跳过 ${skipped} 个非活跃)` : "";
      const tid = this.toast(`正在向 tracker 汇报 ${jobs.length} 个目标${skipTxt}, 等待确认…`, "busy", 0, { sticky: true });
      const results = await Promise.allSettled(
        jobs.map((p) => this.api(p, { method: "POST" }).then((r) => this.waitCmd(r.cmd_id)))
      );
      const errs = [];
      const warns = [];
      let inactive = 0;  // 回执侧的非活跃 warn(D6 竞态): 与 skipped 同属"跳过", 末态合并计数
      for (const r of results) {
        if (r.status === "rejected") errs.push((r.reason && r.reason.message) || "投递失败");
        else if (!r.value.ok && r.value.status === "warn" && _reannounceWarnInactive(r.value.error)) inactive += 1;
        else if (!r.value.ok) (r.value.status === "warn" ? warns : errs).push(r.value.error || "执行失败");
      }
      if (errs.length || warns.length) {
        const head = errs.length
          ? `${errs.length}/${jobs.length} 个目标汇报失败`
          : `${warns.length}/${jobs.length} 个目标汇报未确认`;
        const first = errs[0] || warns[0];
        this._finishToast(tid, errs.length ? "error" : "timeout",
          `${head}${label ? `(${label})` : ""}: ${first}, 已保留未删除`, 8000);
        return false;
      }
      const skipN = skipped + inactive;
      this._finishToast(tid, "ok",
        `汇报确认成功${skipN ? `(跳过 ${skipN} 个非活跃)` : ""}, 开始删除…`, 2000);
      return true;
    },
    /* 删除确认框「删除前强制重新汇报」的可用性(闸门层, issue 26-10-17-1703; 判据与右链
     * 同源 = decorate.js::reannounceBlocked, 全族 paused/stopped/queued/checking/error/
     * missingFiles 覆盖, 不新造「仅 paused」特例): 目标**全部**非活跃时该项不可能有回执
     * (后端第二道闸必回 warn, 而 _reannounceAll 保守口径 warn 不放行 ⇒ 删除被中止, 用户
     * 须手动取消勾选才能删), 故禁用并取消勾选(D3); 混选(任一活跃)放行, 只在 pill 上报
     * 将跳过的非活跃数(D5, 投递收敛由 _deleteFlow 内 reannouncePlan 执行); 解析不出
     * (成员为空)不误拦 —— 与 decorate.js::_reannounceVerdict「解析出不拦」同口径。 */
    _deleteReannounceGate(members) {
      const rows = members || [];
      if (!rows.length) return { disabled: false, title: "", note: "" };
      const blocked = rows.filter((m) => this.reannounceBlocked(m));
      if (blocked.length === rows.length) {
        return { disabled: true, title: "目标均非活跃(暂停/停止/排队/校验中/错误), 无法强制重新汇报", note: "" };
      }
      if (blocked.length) {
        return { disabled: false, title: "", note: `${blocked.length} 个非活跃目标将跳过` };
      }
      return { disabled: false, title: "", note: "" };
    },
    /* ---------------- 删除确认框: 目标信息 + 强制重新汇报(默认勾选)/删除文件两选项 ---------------- */
    _confirmDelete(opts) {
      /* reannounce-inactive-gate 闸门(issue 26-10-17-1703): 全非活跃目标时汇报项禁用 +
       * 取消勾选(模板 tpl/popovers.html 的 opt-pill.is-gated 样式层真禁点击), 混选时
       * 勾选状态不变, 只在标签上带跳过说明。 */
      const gate = opts.reannounceGate || {};
      const reLabel = "删除前先强制重新汇报(等待 tracker 确认, 失败或未确认则不删除)";
      return this._openModal({
        title: opts.title,
        body: opts.body,
        details: opts.details || null,
        wide: true,  // 删除类确认框一律加宽: 摘要与选项宽松可读(DLG-01 成员明细已移除, 宽度见 --modal-wide-w)
        checks: [
          {
            key: "reannounce",
            label: gate.note ? `${reLabel}; ${gate.note}` : reLabel,
            checked: !gate.disabled,
            disabled: !!gate.disabled,
            title: gate.title || "",
          },
          { key: "delete_files", label: "同时删除磁盘文件(不可恢复)", checked: false },
        ],
        okText: "删除",
        cancelText: "取消",
        danger: true,
        icon: "#i-trash-x",
      });
    },
    /* 删除前汇报编排已被 _reannounceAll 取代(FX-16: 右键/批量/整集/整剧 四条入口统一走
     * _deleteFlow -> _reannounceAll 一套链), 旧单目标版本删除 —— 不再保留两条链。 */
    /* 删除该辅种(DLG-02: 旧"整组"叫法退役, 组删除一律计数语义): 单一菜单项 + 确认框显示目标信息
     * (辅种名/成员/站点/路径/总大小)与两个选项; FX-16 起删除动作本身交由 _deleteFlow 统一驱壳。 */
    async delGroup() {
      this.menu.visible = false;
      const key = this.menu.key;
      if (!key) return;
      const g = this._findGroup(key);
      if (!g) return;
      // R10-16: 详情行(辅种名/成员/站点/保存路径/总大小)改由 _deleteFlow 统一派生 ——
      // 单目标时自然退化成逐项明细, 与批量/整集入口结构一致
      await this._deleteFlow({
        keys: [key],
        hashes: [],
        title: `删除该${L10N_GROUP}`,
        body: `将删除"${g.name}"的全部 ${g.count} 个种子。建议删除前先向 tracker 汇报, 避免留下未汇报的 H&R 记录。`,
        countText: `该${L10N_GROUP}(${g.count} 个种子)`,
        label: `"${g.name}"`,
      });
    },
    /* 删除单个种子: 确认框显示种子名/站点/状态/路径/大小 + 两个选项。
     * !目标 hash 显式传入, 缺省回落 menu.hash(S3/M3, 2026-10-10): 抽屉路径 drawerDel 此前靠
     *   写 this.menu.hash 把目标"塞"进来, 现改为显式传参 —— menu 状态不再被当全局目标变量。 */
    async delTorrent(hash = "") {
      this.menu.visible = false;
      const target = hash || this.menu.hash;
      if (!target) return;
      let m = null;
      for (const g of this.filteredGroups) {
        const hit = (g.members || []).find((x) => x.hash === target);
        if (hit) {
          m = hit;
          break;
        }
      }
      if (!m) m = this.singles.find((x) => x.hash === target) || null;  // 单种子视图里的未归组种子
      if (!m) m = this.torrents.find((x) => x.hash === target) || null;  // 种子页平铺数组(全量兑底)
      if (!m) return;
      // FX-16: 删除链统一 —— 走 _deleteFlow(目标明细 + 汇报前置 + 等聚合回执 + 收尾清选择)
      // R10-16: 不再自传 details(条目与右键/批量/整集同构)
      await this._deleteFlow({
        keys: [],
        hashes: [target],
        title: "删除该种子",
        body: "将删除该种子。建议删除前先向 tracker 汇报, 避免留下未汇报的 H&R 记录。",
        countText: "该种子",
        label: m.name || hash.slice(0, 12),
      });
    },
  },
};
