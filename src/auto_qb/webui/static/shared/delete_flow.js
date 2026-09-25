/* auto-qb WEB UI · 删除流程(详情统计/确认框/连带文件)
 *
 * app.js 按域拆分出的片段(2026-09-20)。约定与 config_editor.js / config_rules.js 同一范式:
 * 挂到 window.AQB_DELETE, 由 app.js 末尾 app.mixin(window.AQB_DELETE) 注入同一个 Vue 实例 ——
 * 方法体里的 this 仍是那个组件实例, 跨模块互调与拆分前完全等价。
 *
 * ❗本文件在 HTML 里必须排在 app.js **之前**(app.js 末尾要读 window.AQB_DELETE);
 *   用到的列模型常量(TABLE_COLUMNS / MIN_COL_PX / STATE_RANK …)仍单点定义在 app.js 顶部。
 */
window.AQB_DELETE = {
  methods: {
    /* DLG-02: 批量删除文案按选择构成计数(仅辅种=N 个辅种 / 仅种子=N 个种子)。
     * 用 _bulkTargets 的有效口径 —— 虚拟行(未归组命中)无真实组 key、按种子投递, 计入"种子"
     * 而非"辅种", 保证批量条按钮/确认框标题/提交体三处一致; 空串 = 选中项均已失效。
     * FX-12: 批量条直接渲染它 —— 计数随**权威选择**而非当前视图漂移
     * (在种子页看"N 个辅种"不变, 这正是"三视图打通"的直观体现)。
     * ⚠ 方法名不得以 `_` 开头: Vue 模板编译器不解析下划线前缀标识符
     *   (会报 "_xxx is not defined" 且整块渲染失败 —— 2026-09-17 浏览器冒烟实测)。
     */
    bulkCountText() {
      const { groupKeys, memberHashes } = this._bulkTargets();
      const parts = [];
      if (groupKeys.length) parts.push(`${groupKeys.length} 个${L10N_GROUP}`);
      if (memberHashes.length) parts.push(`${memberHashes.length} 个种子`);
      return parts.join("、");
    },
    /* 批量条 HR 风险提示(P4, 2026-09-25): 选中目标里「不能删」(hr_safety=danger, 后端算好)的
     * 种子数 —— 与删除链同一目标集合派生, 不按视图阵列另算; 无风险返回空串(不渲染) */
    bulkHrWarnText() {
      const { groupKeys, memberHashes } = this._bulkTargets();
      if (!groupKeys.length && !memberHashes.length) return "";
      const n = this._deleteMembers(groupKeys, memberHashes)
        .filter((m) => m.hr_safety === "danger").length;
      return n ? `含 ${n} 个不能删` : "";
    },
    /* 批量条删除按钮文案: 计数文本前缀"删除", 空选中退化为纯"删除" */
    bulkDeleteLabel() {
      const t = this.bulkCountText();
      return t ? `删除 ${t}` : "删除";
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
    /* HR 风险点名(P2, 2026-09-25): 目标里 hr_safety=danger(不能删)的种子 —— 按来源短语去重,
     * 名字最多列 3 个; count=0 返回 null(确认框不加风险行) */
    _hrRiskOf(members) {
      const risky = members.filter((m) => m.hr_safety === "danger");
      if (!risky.length) return null;
      const srcs = [...new Set(risky.map((m) => m.hr_safety_text).filter(Boolean))].join(" / ");
      const names = risky.slice(0, 3).map((m) => m.name || m.hash.slice(0, 12)).join("、");
      return { count: risky.length, srcs, names, more: risky.length > 3 ? ` 等 ${risky.length} 个` : "" };
    },
    _deleteDetails(keys, hashes) {
      const members = this._deleteMembers(keys, hashes);
      const names = [];
      const sites = [...new Set(members.map((m) => m.site).filter(Boolean))];
      const paths = [...new Set(members.map((m) => m.save_path).filter(Boolean))];
      const totalSize = members.reduce((n, m) => n + (m.size || 0), 0);
      const single = (keys || []).length + (hashes || []).length <= 1 && members.length <= 1;
      // 目标: 单目标退化为**它的名字**(单辅种 = 辅种名, 单种子 = 种子名), 多目标走集合摘要
      const target = single && names.length === 1 ? names[0]
        : single && members.length === 1 ? (members[0].name || members[0].hash.slice(0, 12))
          : `${(keys || []).length} 个${L10N_GROUP} · ${members.length} 个种子`;
      return [
        { icon: "#i-cards", label: "目标", value: target, wide: true },
        { icon: "#i-layers", label: "成员", value: `${members.length} 个种子` },
        { icon: "#i-globe", label: "站点", value: sites.join(", ") || "—" },
        { icon: "#i-folder-open", label: "保存路径", value: paths.join(" · ") || "—", wide: true },
        { icon: "#i-hdd", label: "总大小", value: this.fmtSize(totalSize) },
      ];
    },
    async _deleteFlow(targets) {
      const keys = targets.keys || [];
      const hashes = targets.hashes || [];
      if (!keys.length && !hashes.length) return;
      const details = this._deleteDetails(keys, hashes);
      // P2 HR 风险点名(2026-09-25): 目标含「不能删」(hr_safety=danger)种子时, 确认框点名
      // 数量 + 来源档位 + 前几个名字 —— 最后一道防误删闸门(来源短语由后端算好, 前端只拼)
      const risk = this._hrRiskOf(this._deleteMembers(keys, hashes));
      if (risk) {
        details.push({
          icon: "#i-warn", label: "HR 风险", wide: true,
          value: `${risk.count} 个仍在 HR 管束(${risk.srcs}): ${risk.names}${risk.more}，删除可能导致站点 H&R 惩罚`,
        });
      }
      const res = await this._confirmDelete({
        title: targets.title,
        body: targets.body,
        // R10-16: 入口不再传 details(传了也忽略) —— 四入口看到的窗口结构完全一致
        details,
      });
      if (!res) return;
      const deleteFiles = res.checks.delete_files;
      if (res.checks.reannounce) {
        const jobs = [
          ...keys.map((k) => `/api/groups/${k}/reannounce`),
          ...hashes.map((h) => `/api/torrents/${h}/reannounce`),
        ];
        const ok = await this._reannounceAll(jobs, targets.label);
        if (!ok) return;  // 汇报失败: 已提示且保留未删除
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
    /* 汇报前置: 逐目标投递并**全部等回执**; 全部成功返回 true(任一失败 -> 已提示且保留未删除) */
    async _reannounceAll(jobs, label) {
      if (!jobs.length) return true;
      const tid = this.toast(`正在向 tracker 汇报 ${jobs.length} 个目标, 等待确认…`, "busy", 0, { sticky: true });
      const results = await Promise.allSettled(
        jobs.map((p) => this.api(p, { method: "POST" }).then((r) => this.waitCmd(r.cmd_id)))
      );
      const fails = results.filter((r) => r.status === "rejected" || !r.value.ok);
      if (fails.length) {
        this._finishToast(tid, "timeout", `${fails.length}/${jobs.length} 个目标汇报确认失败${label ? `(${label})` : ""}, 已保留未删除`, 6000);
        return false;
      }
      this._finishToast(tid, "ok", "汇报确认成功, 开始删除…", 2000);
      return true;
    },
    /* ---------------- 删除确认框: 目标信息 + 强制汇报(默认勾选)/删除文件两选项 ---------------- */
    _confirmDelete(opts) {
      return this._openModal({
        title: opts.title,
        body: opts.body,
        details: opts.details || null,
        wide: true,  // 删除类确认框一律加宽: 摘要与选项宽松可读(DLG-01 成员明细已移除, 宽度见 --modal-wide-w)
        checks: [
          { key: "reannounce", label: "删除前先强制汇报(等待 tracker 确认, 失败则不删除)", checked: true },
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
    /* 删除单个种子: 确认框显示种子名/站点/状态/路径/大小 + 两个选项 */
    async delTorrent() {
      this.menu.visible = false;
      const hash = this.menu.hash;
      if (!hash) return;
      let m = null;
      for (const g of this.filteredGroups) {
        const hit = (g.members || []).find((x) => x.hash === hash);
        if (hit) {
          m = hit;
          break;
        }
      }
      if (!m) m = this.singles.find((x) => x.hash === hash) || null;  // 单种子视图里的未归组种子
      if (!m) m = this.torrents.find((x) => x.hash === hash) || null;  // 种子页平铺数组(全量兑底)
      if (!m) return;
      // FX-16: 删除链统一 —— 走 _deleteFlow(目标明细 + 汇报前置 + 等聚合回执 + 收尾清选择)
      // R10-16: 不再自传 details(条目与右键/批量/整集同构)
      await this._deleteFlow({
        keys: [],
        hashes: [hash],
        title: "删除该种子",
        body: "将删除该种子。建议删除前先向 tracker 汇报, 避免留下未汇报的 H&R 记录。",
        countText: "该种子",
        label: m.name || hash.slice(0, 12),
      });
    },
  },
};
