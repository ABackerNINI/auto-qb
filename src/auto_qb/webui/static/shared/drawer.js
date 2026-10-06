/* auto-qb WEB UI · 种子详情抽屉(通用/Tracker/文件/Peer 与就地编辑)
 *
 * app.js 按域拆分出的片段(2026-09-20)。约定与 config_editor.js / config_rules.js 同一范式:
 * 挂到 window.AQB_DRAWER, 由 app.js 末尾 app.mixin(window.AQB_DRAWER) 注入同一个 Vue 实例 ——
 * 方法体里的 this 仍是那个组件实例, 跨模块互调与拆分前完全等价。
 *
 * !本文件在 HTML 里必须排在 app.js **之前**(app.js 末尾要读 window.AQB_DRAWER);
 *   用到的列模型常量(TABLE_COLUMNS / MIN_COL_PX / STATE_RANK …)仍单点定义在 app.js 顶部。
 */
/* 跳检预检 gate id -> 分组行短标签(S4, 计划 26-10-05-0314): 取值与 ops_mod.GateVerdict 的
 * gate 对齐(G3-G8 / partial / dedup / filelist + gone); 漂移只影响分组行可读性, 不影响分流判定。 */
const SKIP_GATE_LABELS = {
  G3: "已完成", G4: "活跃中", G5: "校验在途", G6: "组内正在下载",
  G7: "组内校验在途", G8: "组内校验失败", partial: "部分下载", dedup: "今日已跳检",
  filelist: "文件缺失", gone: "已不在客户端",
};

window.AQB_DRAWER = {
  computed: {
    /* 抽屉可见性(2026-10-04 双形态; 2026-10-06 收页面守卫):
     * 两形态一律只在主内容页(page === "groups")渲染 —— 面板是 sticky 吸底的停靠面板, 在设置页
     * (整幅配置工作台, 自己的滚动容器铺满)会压住页面底部的内容块, 看着像设置页的一部分
     * (用户报「qB 全局流量图错误地出现在设置页」)。种子详情另限种子视图(面板是表行的附属)。
     * !状态位 drawer.open **不随切页翻**: 面板 DOM 退场但抽屉状态保持 —— 回主内容页面板连同
     *   数据/窗口选择原样回来(W1 验收项, 与原先「DOM 随种子视图 v-if 出入」同语义)。 */
    drawerVisible() {
      if (!this.drawer.open) return false;
      if (this.page !== "groups") return false;
      if (this.drawer.kind === "traffic") return true;
      return this.viewMode === "torrents";
    },
  },
  methods: {
    /* 自动种子管理开关(种子页右键 R2 补遗): 复用 torrentCmd 回执链 */
    autoTmmToggle() {
      const m = this.menuTorrent();
      this.torrentCmd("auto-tmm", { enable: !m.auto_tmm }, m.auto_tmm ? "关闭自动种子管理" : "开启自动种子管理");
    },
    /* 右键菜单当前种子(SEED_ITEM 完整字段): 供菜单项动态文案/开关初值 */
    menuTorrent() {
      return this.memberByHash.get(this.menu.hash) || {};
    },
    /* 种子控制命令(R2): 带 body 的单种命令(校验/超级做种/强制开始/队列) —— 走既有回执链 */
    async torrentCmd(action, body = null, okText = "") {
      this.menu.visible = false;
      const hash = this.menu.hash;
      if (!hash) return;
      /* 重新校验先确认(计划 26-10-05-0314 S3): 只拦 recheck, 其它命令通道行为不变 ——
       * 单选右键(ctx-menus.html)与抽屉内命令(drawerCmd)同走本方法, 一处接入两入口覆盖;
       * 取消 = 直接返回, 尚未发请求, 零副作用。helper 与文案单点在 commands.js。 */
      if (action === "recheck") {
        const ok = await this._recheckConfirm("该种子");
        if (!ok) return;
      }
      try {
        const resp = await this.api(`/api/torrents/${hash}/${action}`, {
          method: "POST",
          body: body ? JSON.stringify(body) : undefined,
        });
        const r = await this.waitCmd(resp.cmd_id);
        if (r.ok) this.toast(`已执行: ${okText || action}`, "ok", 2500);
        else this.toast(`${okText || action}失败: ${r.error}`, "error", 8000);
      } catch (e) {
        if (!e.auth) this.toast("命令发送失败: " + e.message, "error");
      }
    },
    /* 抽屉内命令: 与 torrentCmd 同链路, 但 hash 取自抽屉(菜单未开时 menu.hash 为空) */
    drawerCmd(action, body = null, okText = "") {
      this.menu.hash = this.drawer.hash;
      this.torrentCmd(action, body, okText);
    },
    /* ---------------- 右键跳检(P2', plan 26-09-30-0109 §3.6; S4 预检对话框 26-10-05-0314) ----------------
     * 高风险操作: 删除并以跳过校验方式重加, 本地统计(上传/下载量、做种时间)被清零,
     * 数据未经哈希校验。S4 起确认框升级为预检对话框(_skipCheckDialog, 单发/批量两入口共用):
     * 进框即禁用确认, 预检(ops 同谓词 dry-run)回执后按三分流渲染原因与逃生通道;
     * 固定警示区(统计清零/未哈希校验/无参考高风险/HR 在管)始终显示。执行走 ops 层四阶段,
     * 阻塞主循环 ~6s, 期间其它命令排队 —— waitCmd 放宽到 60s(与批量同口径)。 */
    async skipCheckTorrent() {
      this.menu.visible = false;
      const hash = this.menu.hash;
      if (!hash) return;
      await this._skipCheckDialog([hash], { mode: "single", hash, groupKeys: [], memberHashes: [hash] });
    },
    /* 跳检预检对话框状态机(S4, 计划 26-10-05-0314 §04; 单发/批量两入口共用):
     * 进框(确认禁用 + busy + 固定警示区) -> 发预检(POST /api/torrents/skip-check/precheck,
     * 后端 ops 同谓词 dry-run) -> 回执后按三分流切换:
     *   全 ok        -> 启用确认「跳检 N 个」(送全量, 不带 force);
     *   ok+force 混合 -> 确认「跳检 N 个可跳检的」(只送 ok 子集, 不带 force) + 强制钮
     *                    (复用 extraText 第三钮, 模板本就是 danger-solid 破坏性分支)
     *                    「强制跳检全部 N」(送全量 + force=true);
     *   force-only    -> 确认保持禁用, 只有强制钮;
     *   含 blocked    -> 无可执行钮(blocked 硬闸, force 只豁瞬态闸门救不回), 按原因分组列出;
     *   预检失败      -> D10 降级: 启用普通确认(= 旧 danger 确认框行为: 确认后执行, 后端闸门
     *                    执行时照拦), 永不出强制钮 —— force 必须先见赌注才出现(plan §07)。
     * 执行路径闸门原样全跑, 预检与执行之间没有信任传递(plan §03 callout)。
     * exec: {mode:"single", hash} | {mode:"bulk", groupKeys, memberHashes} —— 提交端点与 toast
     * 形态两入口各异, 由 _skipExec 按 mode 分派; 本方法只管对话框与预检状态机。 */
    async _skipCheckDialog(hashes, exec) {
      const n = hashes.length;
      // 代际: 单例 modal 下再开新框会把旧 Promise 结算为取消 —— 旧框在途的预检回执
      // 不得污染新框, 落袋前一律按 seq 复核
      const seq = (this._skipCheckSeq = (this._skipCheckSeq || 0) + 1);
      // 固定警示区(plan §03 callout: case 3 不代表没有代价): 统计清零 / 未哈希校验 /
      // 无参考高风险 / HR 在管(D5) —— 进框即显示, 与分流结果并列不互斥
      // (旧 danger 确认框文案区里的警示迁入于此)
      const warnRows = [
        { icon: "#i-warn", label: "统计清零", value: "本地统计(上传/下载量、做种时间)将被清空", wide: true },
        { icon: "#i-warn", label: "未哈希校验", value: "数据未经哈希校验", wide: true },
        { icon: "#i-warn", label: "无参考", value: "无参考对照的跳检属高风险操作", wide: true },
        { icon: "#i-warn", label: "HR 在管", value: "未放行的 HR 种子: 做种时长锚点会倒退、超额线(3×)推迟", wide: true },
      ];
      const p = this._openModal({
        title: n > 1 ? "批量跳检(跳过校验重加)" : "跳检(跳过校验重加)",
        body: n > 1 ? `将删除选中的 ${n} 个种子并以跳过校验方式重加。` : "将删除该种子并以跳过校验方式重加。",
        okText: `跳检 ${n} 个`,
        cancelText: "取消",
        danger: true,
        icon: "#i-bolt",
        wide: true,          // 原因/名称行宽松可读(与删除确认框同形态)
        okDisabled: true,    // 进框即禁用: 预检回执前无任何可执行钮(强制必须先看到赌注)
        busy: true,
        verdict: warnRows,
      });
      this._skipPrecheck(seq, this.modal.mid, hashes, warnRows);  // 不 await: 对话框已开, 回执异步落框; mid = 本框身份戳
      const choice = await p;
      if (!choice) return;  // 取消/Esc/遮罩: 零副作用(此时未发任何执行请求)
      // 走到这说明点的是确认/强制钮 —— _skipVerdict 只在 seq 复核通过后写入, 故取值必属
      // 当前这框(新框会先把旧 Promise 结算成取消); 兜底按降级(全量不带 force)处理
      const v = this._skipVerdict || { degraded: true, okHashes: hashes };
      if (choice === "extra") return this._skipExec(exec, hashes, true);  // 强制: 全量 + force=true
      // 确认: 降级 = 全量不带 force(= 旧确认框行为); 正常 = ok 子集(全 ok 时即全量)
      return this._skipExec(exec, v.degraded ? hashes : v.okHashes, false);
    },
    /* 预检投递与落框(不 await 调用): 回执后把三分流结果接在固定警示区之后, 并按态切换
     * 确认/强制钮。非 ok 回执与请求异常一律走 D10 降级; 403(web.skip_check_menu 关)同形 ——
     * 文案自解释, 执行端点同样有 403 兜底(fail-closed, 前端降级不构成绕过)。 */
    async _skipPrecheck(seq, mid, hashes, warnRows) {
      let rows = [], okHashes = [], counts = null, degraded = false;
      try {
        const resp = await this.api("/api/torrents/skip-check/precheck", {
          method: "POST",
          body: JSON.stringify({ hashes }),
        });
        const r = await this.waitCmd(resp.cmd_id, 60000);
        if (r.ok && r.truth && Array.isArray(r.truth.results)) {
          const results = r.truth.results;
          counts = {
            ok: results.filter((x) => x.cls === "ok").length,
            force: results.filter((x) => x.cls === "force").length,
            blocked: results.filter((x) => x.cls === "blocked").length,
          };
          okHashes = results.filter((x) => x.cls === "ok").map((x) => x.hash);
          rows = this._skipVerdictRows(results);
        } else {
          degraded = true;
          rows = [{ icon: "#i-warn", label: "预检失败", value: `${r.ok ? "回执缺少预检数据" : r.error}, 后端闸门仍会在执行时拦截`, wide: true }];
        }
      } catch (e) {
        if (e.auth) return;  // 401 已由 _logout 收口(modal 一并清空), 无需也不得再动
        degraded = true;
        rows = [{ icon: "#i-warn", label: "预检失败", value: `${e.message}, 后端闸门仍会在执行时拦截`, wide: true }];
      }
      // 迟到回执 / 框已关 / 已被新框取代: 不落袋(防旧结果驱动新框的按钮)。seq 复核跳检
      // 代际, 身份戳复核弹窗本身(F1-01 守卫单点 ui_feedback._modalIsCurrent) —— 取消跳检框
      // 后 seq 不递增, 用户再开限速/重命名等无关 modal(共用单例)时只有身份戳拦得住
      if (seq !== this._skipCheckSeq || !this._modalIsCurrent(mid)) return;
      this.modal.busy = false;
      this.modal.verdict = [...warnRows, ...rows];
      this._skipVerdict = { degraded, okHashes };
      if (degraded) {
        // D10 降级: 启用普通确认(确认后执行, 后端闸门照拦); 强制钮永不出现
        this.modal.okDisabled = false;
        this.modal.extraText = "";
      } else if (counts.blocked) {
        // 含 blocked: 一律不可执行 —— 确认/强制双钮全收, 用户须先解决原因
        this.modal.okDisabled = true;
        this.modal.extraText = "";
      } else if (counts.ok && counts.force) {
        // ok+force 混合: 确认只送 ok 子集(不带 force); 强制钮送全量 + force=true
        this.modal.okDisabled = false;
        this.modal.okText = `跳检 ${counts.ok} 个可跳检的`;
        this.modal.extraText = `强制跳检全部 ${counts.ok + counts.force}`;
      } else if (counts.force) {
        // force-only: 确认保持禁用, 只有强制钮
        this.modal.okDisabled = true;
        this.modal.extraText = `强制跳检全部 ${counts.ok + counts.force}`;
      } else {
        // 全 ok: 启用确认(送全量, 不带 force), 无强制钮
        this.modal.okDisabled = false;
        this.modal.okText = `跳检 ${counts.ok} 个`;
        this.modal.extraText = "";
      }
    },
    /* 预检回执 -> verdict 行式明细(不含固定警示区): 批量 = 计数行 + 按原因分组行
     * (同 (cls, gate) 聚合, 「禁止 · 已完成 ×3: 名A, 名B, …」单行省略, 组内名称上限
     * 5 个 + 「等 X 个」); 单发 = 全量原因行(原因+后果+出路三段式原文, 无未过闸门时
     * 给一条「前置条件全部满足」正行)。gate 短标签表见文件头 SKIP_GATE_LABELS。 */
    _skipVerdictRows(results) {
      const rows = [];
      const ok = results.filter((x) => x.cls === "ok");
      const force = results.filter((x) => x.cls === "force");
      const blocked = results.filter((x) => x.cls === "blocked");
      if (results.length > 1) {
        rows.push({
          icon: "#i-select-all",
          label: "预检",
          value: `可跳检 ${ok.length} / 需强制 ${force.length} / 禁止 ${blocked.length}`,
        });
        const groups = new Map();
        for (const r of results) {
          for (const x of r.reasons || []) {
            const key = `${x.cls}|${x.gate}`;
            if (!groups.has(key)) groups.set(key, { cls: x.cls, gate: x.gate, names: [] });
            groups.get(key).names.push(r.name || r.hash.slice(0, 12));
          }
        }
        for (const g of groups.values()) {
          const shown = g.names.slice(0, 5);  // 组内名称展示上限 5 个
          rows.push({
            icon: g.cls === "blocked" ? "#i-x-circle" : "#i-hourglass",
            label: `${g.cls === "blocked" ? "禁止" : "需强制"} · ${SKIP_GATE_LABELS[g.gate] || g.gate} ×${g.names.length}`,
            value: shown.join(", ") + (g.names.length > shown.length ? ` 等 ${g.names.length} 个` : ""),
            wide: true,
          });
        }
      } else {
        const reasons = (results[0] && results[0].reasons) || [];
        if (!reasons.length) {
          rows.push({ icon: "#i-check-circle", label: "预检", value: "前置条件全部满足, 可跳检" });
        } else {
          for (const x of reasons) {
            rows.push({
              icon: x.cls === "blocked" ? "#i-x-circle" : "#i-hourglass",
              label: x.cls === "blocked" ? "禁止" : "需强制",
              value: x.text,
              wide: true,
            });
          }
        }
      }
      return rows;
    },
    /* 跳检执行分派(确认/强制钮共落点): 单发 POST /api/torrents/{hash}/skip-check(body 仅在
     * force 时携带 force 键, 缺省载荷与历史一致); 批量 POST /api/torrents/bulk
     * (action=skip_check, ok 子集只走 hashes 通道, 强制按 keys+hashes 整份 + force=true)。
     * 执行路径后端重跑全部闸门 —— blocked 照旧硬拒, force 只豁瞬态; 拒绝文案经
     * error 回执 toast 展示。单枚跳检阻塞主循环 ~6s 级, waitCmd 放宽到 60s + SSE cmd
     * 事件赛跑兜底(waitCmd 实现), 回执未到前批量常驻 toast 停留「进行中」。 */
    async _skipExec(exec, hashes, force) {
      try {
        if (exec.mode === "single") {
          const hash = exec.hash;
          const m = this.memberByHash.get(hash) || {};
          const resp = await this.api(`/api/torrents/${hash}/skip-check`, {
            method: "POST",
            body: force ? JSON.stringify({ force: true }) : undefined,
          });
          const r = await this.waitCmd(resp.cmd_id, 60000);
          if (r.ok) this.toast(`已跳检: ${m.name || hash.slice(0, 12)}`, "ok", 3000);
          else this.toast(`跳检未执行: ${r.error}`, "error", 8000);
          return;
        }
        const n = force ? exec.groupKeys.length + exec.memberHashes.length : hashes.length;
        const resp = await this.api("/api/torrents/bulk", {
          method: "POST",
          body: JSON.stringify({
            action: "skip_check",
            keys: force ? exec.groupKeys : [],
            hashes: force ? exec.memberHashes : hashes,
            ...(force ? { force: true } : {}),
          }),
        });
        const tid = this.toast(`批量跳检进行中…(${n} 个目标, 每个约需数秒)`, "busy", 0, { sticky: true });
        const r = await this.waitCmd(resp.cmd_id, 60000);
        if (r.ok) this._finishToast(tid, "ok", `已执行: 批量跳检(${n} 个目标)`, 3000);
        else this._finishToast(tid, "error", `批量跳检未完成: ${r.error}`, 8000);
      } catch (e) {
        if (!e.auth) {
          this.toast((exec.mode === "single" ? "命令发送失败: " : "批量跳检命令发送失败: ") + e.message, "error");
        }
      }
    },
    /* ---------------- 种子编辑对话框(D 轮): 限速/分享率限制/移动/重命名 ----------------
     * 统一形态: 多字段 .modal(modal.fields) + 回执 toast; 预填当前值, 空输入 = 不修改。
     * hash 约定: 菜单调用不传参取 menu.hash, 抽屉调用显式传 drawer.hash(与 drawerCmd 同约定)。 */
    _editTargetHash(h) {
      const hash = h || this.menu.hash;
      this.menu.visible = false;
      return hash || "";
    },
    /* 编辑类对话框取当前值: 抽屉已开且同一 hash 直接用 drawer.detail, 否则现拉一次详情 */
    async _editDetail(hash) {
      if (this.drawer.open && this.drawer.hash === hash && this.drawer.detail) return this.drawer.detail;
      try {
        const r = await this.api(`/api/torrents/${hash}`);
        return (r && r.torrent) || null;
      } catch (e) {
        if (!e.auth) this.toast("当前值获取失败: " + e.message, "error");
        return null;
      }
    },
    /* 编辑类命令统一投递: api + waitCmd 回执 + toast 三态; 成功后按动作刷新抽屉对应页签数据 */
    async _editPost(hash, action, body, okText) {
      try {
        const resp = await this.api(`/api/torrents/${hash}/${action}`, {
          method: "POST",
          body: JSON.stringify(body),
        });
        const r = await this.waitCmd(resp.cmd_id);
        if (r.ok) {
          this.toast(`已执行: ${okText}`, "ok", 2500);
          if (this.drawer.open && this.drawer.hash === hash) {
            this._fetchDrawerDetail();
            if (action.startsWith("trackers/")) this._fetchDrawerTrackers(true);
            else if (action === "files/priority" || action === "rename-fs") this._fetchDrawerFiles(true);
          }
          return true;
        }
        this.toast(`${okText}失败: ${r.error}`, "error", 8000);
      } catch (e) {
        if (!e.auth) this.toast(`${okText}命令发送失败: ` + e.message, "error");
      }
      return false;
    },
    /* 限速…: 上传/下载两输入(KiB/s; 空=不改, 0=不限) → POST limits(×1024 转 bytes, 0 原样传) */
    async editLimits(h = "") {
      const hash = this._editTargetHash(h);
      if (!hash) return;
      const d = await this._editDetail(hash);
      const kiB = (bytes) => (bytes > 0 ? String(Math.round(bytes / 1024)) : "");  // 不限/未设(≤0)留空
      const res = await this._openModal({
        title: "限速",
        body: "设置该种子的上传/下载速度上限(KiB/s)。留空 = 保持不变, 填 0 = 不限速。",
        fields: [
          { key: "up", label: "上传上限(KiB/s)", value: d ? kiB(d.up_limit) : "", placeholder: "留空不修改, 0 = 不限" },
          { key: "dl", label: "下载上限(KiB/s)", value: d ? kiB(d.dl_limit) : "", placeholder: "留空不修改, 0 = 不限" },
        ],
        okText: "应用", cancelText: "取消",
      });
      if (!res) return;
      const body = {};
      for (const [k, key] of [["up", "up_limit"], ["dl", "dl_limit"]]) {
        if (res[k] === "") continue;  // 空 = 不修改
        const n = Number(res[k]);
        if (!Number.isFinite(n) || n < 0) {
          this.toast("限速需为非负数字(KiB/s)", "warn");
          return;
        }
        body[key] = Math.round(n * 1024);  // KiB/s → bytes/s; 0 原样传(后端语义 = 不限)
      }
      if (!Object.keys(body).length) {
        this.toast("未作修改", "ok", 2000);
        return;
      }
      await this._editPost(hash, "limits", body, "限速已更新");
    },
    /* 分享率限制…: 分享率/做种时长(h)/不活跃做种时长(h) → POST share-limits(-1 = 恢复全局默认) */
    async editShareLimits(h = "") {
      const hash = this._editTargetHash(h);
      if (!hash) return;
      const d = await this._editDetail(hash);
      const hrs = (sec) => (sec > 0 ? String(Math.round((sec / 3600) * 100) / 100) : "");  // -1/0(未设)留空
      const res = await this._openModal({
        title: "分享率限制",
        body: "达到任一限制后该种子将停止做种。留空 = 保持不变, 填 -1 = 恢复全局默认。",
        fields: [
          { key: "ratio", label: "分享率上限", value: d && d.max_ratio >= 0 ? String(d.max_ratio) : "", placeholder: "留空不修改, -1 = 全局" },
          { key: "time", label: "做种时长上限(小时)", value: d ? hrs(d.max_seeding_time) : "", placeholder: "留空不修改, -1 = 全局" },
          { key: "inactive", label: "不活跃做种上限(小时)", value: d ? hrs(d.max_inactive_seeding_time) : "", placeholder: "留空不修改, -1 = 全局" },
        ],
        okText: "应用", cancelText: "取消",
      });
      if (!res) return;
      const body = {};
      if (res.ratio !== "") {
        const n = Number(res.ratio);
        if (!Number.isFinite(n) || (n < 0 && n !== -1)) {
          this.toast("分享率需为非负数字(或 -1)", "warn");
          return;
        }
        body.ratio_limit = n;
      }
      for (const [k, key] of [["time", "seeding_time_limit"], ["inactive", "inactive_seeding_time_limit"]]) {
        if (res[k] === "") continue;  // 空 = 不修改
        const n = Number(res[k]);
        if (!Number.isFinite(n) || (n < 0 && n !== -1)) {
          this.toast("时长需为非负小时数(或 -1)", "warn");
          return;
        }
        body[key] = n === -1 ? -1 : Math.round(n * 3600);  // 小时 → 秒; -1 原样(未设/全局)
      }
      if (!Object.keys(body).length) {
        this.toast("未作修改", "ok", 2000);
        return;
      }
      await this._editPost(hash, "share-limits", body, "分享率限制已更新");
    },
    /* 移动…: 新保存路径输入(确认文案注明离开辅种组) → POST location */
    async editMove(h = "") {
      const hash = this._editTargetHash(h);
      if (!hash) return;
      const d = await this._editDetail(hash);
      const res = await this._openModal({
        title: "移动种子",
        body: "将种子文件移动到新路径。注意: 移动后该种子将离开当前辅种组。",
        fields: [{ key: "location", label: "新保存路径", value: d ? d.save_path || "" : "", placeholder: "D:\\downloads\\target" }],
        okText: "移动", cancelText: "取消",
      });
      if (!res) return;
      if (!res.location) {
        this.toast("路径不能为空", "warn");
        return;
      }
      await this._editPost(hash, "location", { location: res.location }, "已移动");
    },
    /* ---------------- 批量编辑(多选右键, 计划 26-10-02-1955 W2): 批量限速 / 批量移动 ----------------
     * 与单选编辑同一家族, 但三处不同: 目标集合是整个选中集合(_bulkTargets 口径, 组键 + 成员 hash
     * 整份交给后端, 展开去重的单一权威在后端); 无当前值可预填(多选各值不同, 预填必然误导);
     * 提交走 /api/torrents/bulk 合单通道(一次 POST + 一个聚合回执), 不做乐观贴片 —— 限速/移动
     * 的行值由 QbApi 写方法同步 store 快照 + bulk_torrents 的 RESYNC 补刷新落行(与标签/分类
     * 的 _metaBulk 同一观感)。 */
    /* 批量限速…: 双输入各自独立, 留空 = 该方向不提交(D3 拍板), KiB/s ×1024 与单选同口径 */
    async editLimitsMulti() {
      this.menu.visible = false;
      const targets = this._bulkTargets();
      if (!targets.groupKeys.length && !targets.memberHashes.length) return;
      const res = await this._openModal({
        title: "批量限速",
        body: `为选中的 ${targets.groupKeys.length + targets.memberHashes.length} 个目标设置上传/下载速度上限(KiB/s)。留空 = 该项保持不变, 填 0 = 不限速。`,
        fields: [
          { key: "up", label: "上传上限(KiB/s)", value: "", placeholder: "留空不修改, 0 = 不限" },
          { key: "dl", label: "下载上限(KiB/s)", value: "", placeholder: "留空不修改, 0 = 不限" },
        ],
        okText: "应用", cancelText: "取消",
      });
      if (!res) return;
      const body = {};
      for (const [k, key] of [["up", "up_limit"], ["dl", "dl_limit"]]) {
        if (res[k] === "") continue;  // 空 = 不修改该项(只提交有值方向)
        const n = Number(res[k]);
        if (!Number.isFinite(n) || n < 0) {
          this.toast("限速需为非负数字(KiB/s)", "warn");
          return;
        }
        body[key] = Math.round(n * 1024);  // KiB/s 转 bytes/s; 0 原样传(qB 语义 = 不限)
      }
      if (!Object.keys(body).length) {
        this.toast("未作修改", "ok", 2000);
        return;
      }
      await this._bulkEditPost(targets, "limits", body, "批量限速");
    },
    /* 批量移动…: promptDialog 空 prefill(多选无当前值) -> confirm 确认框展示目标路径与 N */
    async editMoveMulti() {
      this.menu.visible = false;
      const targets = this._bulkTargets();
      const n = targets.groupKeys.length + targets.memberHashes.length;
      if (!n) return;
      const raw = await this.promptDialog("批量移动", "", {
        body: `将选中的 ${n} 个目标的文件移动到新路径。注意: 移动后相关种子将离开当前辅种组。`,
        placeholder: "D:\\downloads\\target", okText: "下一步",
      });
      if (raw === null) return;
      const location = String(raw || "").trim();
      if (!location) {
        this.toast("路径不能为空", "warn");
        return;
      }
      const ok = await this.confirmDialog("确认移动", `将把 ${n} 个目标的保存路径移动到: ${location}`, { okText: "移动" });
      if (!ok) return;
      await this._bulkEditPost(targets, "location", { location }, "批量移动");
    },
    /* 批量跳检…(计划 26-10-02-1955 W3; S4 起确认框升级为预检对话框 26-10-05-0314):
     * 目标集合 _bulkTargets, 组键就地展开成成员 hash 后交 _skipCheckDialog(预检展示与
     * ok 子集的单一口径); 强制路径仍按 keys+hashes 双通道整份提交(与历史载荷同形 + force 键)。
     * 菜单显隐由 flags.skip_check_menu 门控(W1), 后端 bulk 分派处同样 fail-closed。 */
    async skipCheckMulti() {
      this.menu.visible = false;
      const targets = this._bulkTargets();
      const n = targets.groupKeys.length + targets.memberHashes.length;
      if (!n) return;
      const hashes = [...targets.memberHashes];
      for (const k of targets.groupKeys) {
        const g = this._findGroup(k);
        for (const m of (g && g.members) || []) {
          if (!hashes.includes(m.hash)) hashes.push(m.hash);
        }
      }
      await this._skipCheckDialog(hashes, { mode: "bulk", groupKeys: targets.groupKeys, memberHashes: targets.memberHashes });
    },
    /* 批量编辑统一投递: 与 _metaBulk 同链路(api + waitCmd + toast 三态), 目标集合用打开
     * 对话框时刻锁定的 targets; 不做乐观贴片(见本节头注释)。 */
    async _bulkEditPost(targets, action, extra, okText) {
      const { groupKeys, memberHashes } = targets;
      try {
        const resp = await this.api("/api/torrents/bulk", {
          method: "POST",
          body: JSON.stringify({ action, keys: groupKeys, hashes: memberHashes, ...extra }),
        });
        const r = await this.waitCmd(resp.cmd_id);
        if (r.ok) this.toast(`已执行: ${okText}(${groupKeys.length + memberHashes.length} 个目标)`, "ok", 2500);
        else this.toast(`${okText}失败: ${r.error}`, "error", 8000);
      } catch (e) {
        if (!e.auth) this.toast(`${okText}命令发送失败: ` + e.message, "error");
      }
    },
    /* 重命名…: 种子显示名(不改磁盘文件名) → POST rename */
    async editRename(h = "") {
      const hash = this._editTargetHash(h);
      if (!hash) return;
      const d = await this._editDetail(hash);
      const res = await this._openModal({
        title: "重命名种子",
        body: "修改种子显示名(不影响磁盘上的文件/目录名)。",
        fields: [{ key: "name", label: "新名称", value: d ? d.name || "" : "", placeholder: "新种子名" }],
        okText: "重命名", cancelText: "取消",
      });
      if (!res) return;
      if (!res.name) {
        this.toast("名称不能为空", "warn");
        return;
      }
      await this._editPost(hash, "rename", { name: res.name }, "已重命名");
    },
    /* ---------------- 抽屉 Tracker 页签编辑(D 轮): 添加/编辑/删除 ---------------- */
    async trackerAdd() {
      const hash = this.drawer.hash;
      if (!hash) return;
      const raw = await this.promptDialog("添加 Tracker", "", {
        placeholder: "announce URL(多条用换行/逗号分隔)", okText: "添加",
      });
      if (raw === null) return;
      const urls = raw.split(/[\s,]+/).map((s) => s.trim()).filter(Boolean);
      if (!urls.length) {
        this.toast("请输入至少一条 tracker URL", "warn");
        return;
      }
      await this._editPost(hash, "trackers/add", { urls }, urls.length > 1 ? `已添加 ${urls.length} 条 tracker` : "tracker 已添加");
    },
    async trackerEdit(url) {
      const hash = this.drawer.hash;
      if (!hash) return;
      const nu = await this.promptDialog("编辑 Tracker", url, { placeholder: "新的 announce URL", okText: "保存" });
      if (nu === null) return;
      const newUrl = String(nu || "").trim();
      if (!newUrl) {
        this.toast("URL 不能为空", "warn");
        return;
      }
      if (newUrl === url) {
        this.toast("未作修改", "ok", 2000);
        return;
      }
      await this._editPost(hash, "trackers/edit", { orig_url: url, new_url: newUrl }, "tracker 已更新");
    },
    async trackerRemove(url) {
      const hash = this.drawer.hash;
      if (!hash) return;
      const ok = await this.confirmDialog("删除 Tracker", `将删除该 tracker: ${url}`, { okText: "删除", danger: true });
      if (!ok) return;
      await this._editPost(hash, "trackers/remove", { url }, "tracker 已删除");
    },
    /* ---------------- 抽屉内容页签编辑(D 轮): 行选中/优先级/文件重命名 ---------------- */
    /* 行点击选中(文件/目录均可): 再点同一行取消 —— 顶部"重命名…"的作用对象 */
    fileRowSelect(r) {
      this.drawerSelPath = this.drawerSelPath === r.path ? "" : r.path;
    },
    /* 文件优先级小菜单: 锚定单元格下方, 视口吸附(@click.stop 防止开菜单的点击立即被窗口关闭) */
    openFilePrio(ev, index) {
      this._markCtxSource(ev);
      const rect = ev.currentTarget.getBoundingClientRect();
      const w = 150, h = 176;
      this.filePrio = {
        visible: true, index,
        x: Math.min(Math.max(8, rect.left), Math.max(8, window.innerWidth - w - 8)),
        y: Math.min(rect.bottom + 4, Math.max(8, window.innerHeight - h - 8)),
      };
    },
    /* 优先级 4 档(0=跳过 1=普通 6=高 7=最高) → POST files/priority(单文件) */
    async setFilePriority(p) {
      this.filePrio.visible = false;
      const index = this.filePrio.index;
      const hash = this.drawer.hash;
      if (!hash || index < 0) return;
      const label = { 0: "跳过", 1: "普通", 6: "高", 7: "最高" }[p] || String(p);
      await this._editPost(hash, "files/priority", { indices: [index], priority: p }, `优先级已设为「${label}」`);
    },
    /* 文件/目录重命名(选中行; 单文件种子免选): POST rename-fs, new_path = 原目录前缀 + 新名 */
    async renameFileRow() {
      const hash = this.drawer.hash;
      if (!hash) return;
      const rows = this.drawerFileRows();
      let row = rows.find((r) => r.path === this.drawerSelPath);
      if (!row && rows.length === 1) row = rows[0];  // 单文件种子: 免选中直接改
      if (!row) {
        this.toast("请先点击选中要重命名的文件或目录", "warn");
        return;
      }
      const res = await this.promptDialog(row.dir ? "重命名目录" : "重命名文件", row.name, {
        body: `当前路径: ${row.path}`,
        okText: "重命名",
      });
      if (res === null) return;
      const nn = String(res || "").trim();
      if (!nn) {
        this.toast("名称不能为空", "warn");
        return;
      }
      if (nn === row.name) {
        this.toast("未作修改", "ok", 2000);
        return;
      }
      const parent = row.path.includes("/") ? row.path.slice(0, row.path.lastIndexOf("/") + 1) : "";
      await this._editPost(hash, "rename-fs", {
        old_path: row.path, new_path: parent + nn, is_folder: !!row.dir,
      }, row.dir ? "目录已重命名" : "文件已重命名");
    },
    async copyTorrentInfo(field) {
      this.menu.visible = false;
      const hash = this.menu.hash;
      const m = this.memberByHash.get(hash);
      if (!m) return;
      let value = field === "name" ? m.name
        : field === "hash" ? (m.infohash_v1 || m.hash)
          : "";
      /* magnet_uri **不在任何轮询载荷里**(issue E-04, P-06 拍板: 后端 _seed_view 已去掉;
       * 契约口径 = 只在用户显式动作时才需要的字段不进每 1.5~3s 一轮的响应体 —— magnet
       * 添加型库为 MB 级增量): "复制磁力"点的时候**按需取一次详情**(复用 _editDetail:
       * 抽屉已开则连请求都不发)。曾因索引条目没有该字段 100% 落到"该种子没有 magnet
       * 链接"(BUG-9), 按需详情即当时的修法。 */
      if (field === "magnet") {
        const d = await this._editDetail(hash);
        value = (d && d.magnet_uri) || "";
      }
      if (!value) {
        this.toast("该种子没有 magnet 链接", "warn");
        return;
      }
      const label = field === "name" ? "种子名" : field === "hash" ? "信息哈希" : "magnet 链接";
      this._copyText(value, label);
    },
    /* ---------------- 种子详情面板(R1B → 方案A 底部停靠, 计划 26-10-03-0917 W1/W2) ----------------
     * 数据: /api/torrents/{hash} 全字段详情; /trackers /files /peers 按需拉取。
     * trackers/peers 在对应 tab 激活期间 5s 轮询(页面隐藏时暂停), 关闭面板即停 —— 不进主循环 tick;
     * General 分组行在 drawerGeneralSections 预格式化(qB 哨兵 -1/-2/8640000 在此统一翻译)。
     * 形态: 右缘浮层改为底部停靠面板(2026-10-04 起落点为 app 级 .drawer-dock, 可见性由 drawerVisible
     * 按形态把守) —— 无遮罩, open 只负责挂状态与拉数据; close 只收面板。
     * W2 键盘跟随: 光标移动经 shortcuts.js::_kbApplyCursor 尾部进 _kbFollowDrawer 单点(防抖 200ms
     * + 请求代际 seq + hash 短路, §2.3), 停稳后经 _switchDrawerTarget 换目标; 显式打开/关闭在此
     * 两处作废在途跟随定时器, 显式操作优先于跟随。 */
    async openTorrentDrawer(hash) {
      // 防御分支(W1): 面板落点只存在于种子页(torrents 视图), 非种子页没有 .drawer-dock ——
      // 入口(双击/右键/Enter)本就只在种子页, 这里兜底防跨页调用把面板状态挂在不可见容器上
      if (this.page !== "groups" || this.viewMode !== "torrents") return;
      this.menu.visible = false;
      this._stopDrawerPoll();
      this._stopDrawerFollow();  // 显式打开优先于在途跟随(双击换目标 vs 防抖中的跟随, 不得互相打架)
      this._drawerSwitchEnd();   // FX-29: 面板整体重建 -> 无"旧内容可保留", 待到集合与遮罩一并作废
      // 流量页签(S5b, plan 26-10-03-0946 §07 表②)受 qb_traffic_enabled 门控: 上次停在流量页签
      // 而功能后来关闭时落回常规页(页签按钮 v-if=qbTrafficOn 不渲染, 初值也不能落在隐形页签上)
      const last = this.drawerLastTab;
      const initialTab = last === "traffic" && !this.qbTrafficOn ? "general" : (last || "general");
      this._qbTeardown();  // 若上一形态是流量图(全局/分组), 换到种子详情时收轮询与图
      this.drawer = {
        open: true, collapsed: false, hash, tab: initialTab, loading: true, error: "",
        detail: null, trackers: [], files: [], peers: { peers: [] },
        trackersLoading: false, filesLoading: false, peersLoading: false,
        switching: false,  // FX-29: 打开路径不存在"保留旧数据", 遮罩恒不亮(显式建字段见 vue-reactivity)
        kind: "seed", scope: "",
      };
      // 开场落定信号(FX-29 待到集合同机制): 登记详情 + 初值页签的数据源, 全到手 = 面板几何落定,
      // 届时补一发让位(挂单 _drawerOpenReveal 在 _drawerDone 兑现) —— 开场那次量的是 loading 态
      // 几何(面板随后长到 42vh), 文档底打开时 scrollBy 还会被钳制成 0(下滚余量是停靠槽位长高才
      // 创造的; 2026-10-04 回归取证)。流量页签高度恒定(drawerPanelStyle 定高), 不进集合。
      this._drawerWait = new Set(initialTab === "traffic" ? ["detail"] : this._drawerWaitSources(initialTab));
      this._drawerOpenReveal = hash;
      this.persistDrawerOpen();  // W3 开合态记录(D1: 只写不回读, 首屏恒默认收起)
      this._kbRevealRow(hash);   // 显式打开也让位: 停靠面板一开就压住列表底部, 被点行(双击/右键/Enter)要露出来(2026-10-03 报障)
      await this._fetchDrawerDetail();  // 详情恒拉(头部标题/常规页都依赖); 非常规 tab 再补拉对应数据
      if (initialTab !== "general") this._loadDrawerTab(initialTab);
    },
    /* 收面板: 无遮罩可关, 只做面板自身收尾(文件优先级小菜单/行选中/页签轮询);
     * drawer.open 跨页不清 —— 切页再回种子页面板状态保持(方案A W1 验收项) */
    closeDrawer() {
      // 槽位冻结 + 落定顶缘登记: leave 期面板转 absolute 出流, dock 会瞬间塌 0 —— 把用户可见高
      // 立即写回 dock 内联(同帧无跳变帧), 钩子(drawerLeaveHook)再从该高度收拢到 0; _drawerAnimTop
      // 供 _kbViewBottom 在收场动画期读落定值(此处 dock 还在全高帧, 是唯一可信测量点)
      const dock = document.querySelector(".drawer-dock");
      if (dock && !dock.classList.contains("drawer-anim")
          && !window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
        const h = Math.round(dock.getBoundingClientRect().height);
        if (h) {
          this._drawerAnimTop = this._drawerFinalTop(dock);
          dock.classList.add("drawer-anim");
          dock.style.height = h + "px";
        }
      }
      this.drawer.open = false;
      this.filePrio.visible = false;
      this.drawerSelPath = "";
      this._stopDrawerPoll();
      this._stopDrawerFollow();
      this._drawerSwitchEnd();  // FX-29: 收面板即撤切换态(未完成的等待不得挂到下次打开)
      this._qbTeardown();       // 流量形态(全局/分组/单种)轮询与图一并收(2026-10-04 三挂点并入抽屉)
      this._dtUnmountAll();     // 模板核心层(计划 26-10-06-0838 S1): 逐变体 destroy + 清空宿主子树
      this.persistDrawerOpen();  // W3 开合态记录(D1: 只写不回读)
    },
    _stopDrawerPoll() {
      if (this._drawerTimer) {
        clearInterval(this._drawerTimer);
        this._drawerTimer = null;
      }
      // 流量页签(S5b)的低频轮询同收: 本方法是抽屉页签轮询的收口单点(closeDrawer/drawerTab/
      // _switchDrawerTarget/openTorrentDrawer 全走这里), 页签切走/换目标/关面板即停 —— 若新页签
      // 仍是流量, _loadDrawerTab 会重新起(_qbPollStart 自带先停后起)
      this._qbPollStop("torrent");
    },
    _startDrawerPoll() {
      this._stopDrawerPoll();
      // P1-4: 3s → 5s。抽屉是观察用途, peers/trackers 秒级变化对操作没有意义;
      // 而每次轮询都要 Web 线程直连 qB(peers 走 sync/torrentPeers, 响应体随 peer 数增长),
      // 在主循环之外额外占用 qB。5s 仍远快于人工观察节奏。
      this._drawerTimer = setInterval(() => {
        if (!this.drawer.open || document.hidden) return;
        // W4 停靠化收口(计划 26-10-03-0917 前波移交观察项): 面板 DOM 随种子视图 v-if 出入,
        // 切走页面/视图后 drawer.open 仍为 true(回页状态保持语义), 旧浮层形态的轮询会继续对
        // 隐藏面板打 trackers/peers —— 不可见即跳过(定时器不拆, 回页下一拍自动恢复)。
        if (this.page !== "groups" || this.viewMode !== "torrents") return;
        if (this.drawer.tab === "trackers") this._fetchDrawerTrackers(true);
        else if (this.drawer.tab === "peers") this._fetchDrawerPeers(true);
      }, 5000);
    },
    /* W2 请求代际纪律: 四个 fetcher 均带可选 seq(0 = 无代际约束, 走 hash 戳守卫) ——
     * 换 hash(跟随/显式打开)或换代际(切页签)后, 在途旧响应一律丢弃, 防止慢响应把新目标的
     * 详情/列表覆盖成旧的。hash 戳另兜一路: 5s 轮询(seq=0)发出后恰逢跟随换目标, 响应也不落袋。 */
    _drawerStale(hash, seq) {
      return this.drawer.hash !== hash || (!!seq && seq !== this._drawerLoadSeq);
    },
    async _fetchDrawerDetail(seq = 0) {
      const hash = this.drawer.hash;
      this.drawer.loading = true;
      this.drawer.error = "";
      try {
        const r = await this.api(`/api/torrents/${hash}`);
        if (this._drawerStale(hash, seq)) return;  // 旧响应丢弃(W2 代际纪律)
        this.drawer.detail = (r && r.torrent) || null;
        if (!this.drawer.detail) this.drawer.error = "种子不存在或已被删除";
        this._dtNotify("detail");  // 模板核心层(计划 26-10-06-0838 S1): 落袋即通知活动变体重渲染
      } catch (e) {
        if (this._drawerStale(hash, seq)) return;
        if (!e.auth) this.drawer.error = e.message || "详情获取失败";
      } finally {
        // 过期请求不动 loading 态(新在途请求持有它), 免得闪一帧"加载完"假象
        if (!this._drawerStale(hash, seq)) this.drawer.loading = false;
        this._drawerDone("detail", hash, seq);  // FX-29: 落定登记(该数据源已到手)
      }
    },
    async _fetchDrawerTrackers(silent = false, seq = 0) {
      const hash = this.drawer.hash;
      if (!silent) this.drawer.trackersLoading = true;
      try {
        const r = await this.api(`/api/torrents/${hash}/trackers`);
        if (this._drawerStale(hash, seq)) return;
        this.drawer.trackers = Array.isArray(r) ? r : [];
        this._dtNotify("trackers");  // 模板核心层(计划 26-10-06-0838 S1): 落袋即通知
      } catch (e) {
        if (!silent && !e.auth) this.toast("tracker 列表获取失败: " + e.message, "error");
      } finally {
        if (!this._drawerStale(hash, seq)) this.drawer.trackersLoading = false;
        this._drawerDone("trackers", hash, seq);
      }
    },
    async _fetchDrawerFiles(silent = false, seq = 0) {
      const hash = this.drawer.hash;
      if (!silent) this.drawer.filesLoading = true;
      try {
        const r = await this.api(`/api/torrents/${hash}/files`);
        if (this._drawerStale(hash, seq)) return;
        this.drawer.files = Array.isArray(r) ? r : [];
        this._dtNotify("files");  // 模板核心层(计划 26-10-06-0838 S1): 落袋即通知
      } catch (e) {
        if (!silent && !e.auth) this.toast("文件列表获取失败: " + e.message, "error");
      } finally {
        if (!this._drawerStale(hash, seq)) this.drawer.filesLoading = false;
        this._drawerDone("files", hash, seq);
      }
    },
    async _fetchDrawerPeers(silent = false, seq = 0) {
      const hash = this.drawer.hash;
      if (!silent) this.drawer.peersLoading = true;
      try {
        const r = await this.api(`/api/torrents/${hash}/peers`);
        if (this._drawerStale(hash, seq)) return;
        this.drawer.peers = r || { peers: [] };
        this._dtNotify("peers");  // 模板核心层(计划 26-10-06-0838 S1): 落袋即通知
      } catch (e) {
        if (!silent && !e.auth) this.toast("peer 列表获取失败: " + e.message, "error");
      } finally {
        if (!this._drawerStale(hash, seq)) this.drawer.peersLoading = false;
        this._drawerDone("peers", hash, seq);
      }
    },
    /* tab 切换: general 重新拉详情(反映最新状态); trackers/peers 拉一次并启动轮询; content 拉一次。
     * 切换即记住该 tab(drawerLastTab + localStorage), 使下一个种子默认停在相同页签。 */
    drawerTab(tab) {
      // 补强二(计划 26-10-06-0838 S1, 报告 §5): 收起态点页签 = 先展开再切, 消灭"点了没反应"
      if (this.drawer.collapsed) this.toggleDrawerCollapse();
      if (this.drawer.tab === tab) return;
      this.drawer.tab = tab;
      this.drawerLastTab = tab;
      this.persistDrawerTab();
      this.filePrio.visible = false;  // 换页签时收起文件优先级小菜单(内容页签专属)
      this._drawerSwitchEnd();  // FX-29: 切页签使在途的那一组响应全部过期(stale 不落袋), 若不撤等待
      this._stopDrawerPoll();   //     遮罩会挂死 —— 显式操作视作结束上一次切换
      this._loadDrawerTab(tab);
    },
    /* 按 tab 拉取对应数据(开抽屉初值 / 切 tab / W2 跟随换目标共用, 单一加载逻辑):
     * 每次进入 bump 请求代际 seq —— 之后所有带 seq 的在途响应过期, 换目标/换页签竞态在此收口。 */
    _loadDrawerTab(tab) {
      const seq = (this._drawerLoadSeq = (this._drawerLoadSeq || 0) + 1);
      if (tab === "general") this._fetchDrawerDetail(seq);
      else if (tab === "trackers") {
        this._fetchDrawerTrackers(false, seq);
        this._startDrawerPoll();
      } else if (tab === "peers") {
        this._fetchDrawerPeers(false, seq);
        this._startDrawerPoll();
      } else if (tab === "content") this._fetchDrawerFiles(false, seq);
      // 流量页签(S5b, plan 26-10-03-0946 §07 表②): 数据源 /api/traffic/qb/torrent/{hash};
      // 打开时拉取一次 + 打开期间按采样间隔低频续拉(qb_traffic_chart.js _qbPollStart,
      // meta.interval_s 取间隔), 关抽屉/切页签/换目标由 _stopDrawerPoll 统一收 ——
      // hash 上下文竞态(换目标后旧响应)在 _qbLoad 的 stale 判定里丢弃
      else if (tab === "traffic" && this.qbTrafficOn) {
        this._qbLoad("torrent");
        this._qbPollStart("torrent");
      }
      this._dtSync();  // 模板核心层(计划 26-10-06-0838 S1): 换页签即卸旧变体、按选择挂当前页签变体
    },
    /* ---------------- W2 详情跟随光标(计划 §2.3 四条纪律, 全部收口在此单点) ----------------
     * 触发入口: shortcuts.js::_kbApplyCursor 尾部(鼠标路径将来接同一入口, §1.3 相邻预留)。
     *   1) 触发单点+守卫 —— 面板开 + 种子页 + 光标是种子行(kind=torrent); 追剧/辅种组行视图共用
     *      _kbApplyCursor, 守卫不满足即零开销返回, 不波及;
     *   2) 防抖 200ms —— 连发上下键不逐行拉详情, 停稳才发;
     *   3) 在途请求代际 seq —— _loadDrawerTab 每次 bump, 换 hash 后旧响应一律丢弃(见上);
     *   4) hash 未变短路 —— 光标落回同一行不重拉; 页签内 5s 轮询(_startDrawerPoll)照旧, 互不打架。 */
    _kbFollowDrawer() {
      if (!this.drawer.open) return;
      if (this.drawer.collapsed) return;  // W3 收起态跟随暂停(body 不可见, 拉了也看不见); 展开时补跟
      if (this.page !== "groups" || this.viewMode !== "torrents") return;  // 种子页守卫(面板停靠落点)
      const c = this.kbCursor;
      if (!c || c.kind !== "torrent") return;  // kind 守卫(组行/剧/集单元不跟随)
      if (this.drawer.hash === c.id) return;   // 纪律4: hash 未变短路(含防抖在途的重复触发)
      if (this._followDrawerTimer) clearTimeout(this._followDrawerTimer);
      this._followDrawerTimer = setTimeout(() => {
        this._followDrawerTimer = null;
        // 停稳复核: 面板已关/已收起 / 切页走了 / 目标已换(显式打开优先) / 光标又落回原行 -> 放弃本次跟随
        if (!this.drawer.open || this.drawer.collapsed || this.page !== "groups" || this.viewMode !== "torrents") return;
        const cur = this.kbCursor;
        if (!cur || cur.kind !== "torrent" || cur.id === this.drawer.hash) return;
        this._switchDrawerTarget(cur.id);
      }, 200);
    },
    _stopDrawerFollow() {
      if (this._followDrawerTimer) {
        clearTimeout(this._followDrawerTimer);
        this._followDrawerTimer = null;
      }
    },
    /* ---------------- FX-29 换目标: 软切换(治「上下键切换种子时抽屉闪烁」, 26-10-03) ----------------
     * 旧实现把 detail / trackers / files / peers 一把清空再重拉, 面板每一次光标移动都走一遍
     * 「整幅内容消失 -> 落到加载空态 -> 数据回来重建」, 连按上下键时就是持续闪烁; 且未拖过高的
     * 面板只有 CSS 42vh 上限(高度随内容), 空态把面板抽成一条再撑开, 列表与停靠面板连锁跳动。
     * 软切换 = 保留旧数据撑住几何, 用 **遮罩** 而不是清空来防串显: 内容此刻属于上个种子, 罩住
     * 即不可读(并屏蔽交互), 新数据全部到手才掀开 —— 「看着上个种子的值」不会成立, 但面板几何
     * 全程不动, 用户眼里只有内容换了一帧。落定按「数据源集合」而不是「任一请求」: 早到的单个请求
     * 不许提前掀罩(那时另一个源还是上个种子的值), 故按 tab 登记待到集合, 全部到手才算落定。 */
    _switchDrawerTarget(hash) {
      this._stopDrawerPoll();
      this._stopDrawerFollow();
      this.drawer.hash = hash;
      this.drawer.loading = true;
      this.drawer.error = "";
      this._drawerWait = new Set(this._drawerWaitSources(this.drawer.tab));
      this._drawerBusyArm();   // 延迟点亮遮罩(快响应时用户看不到任何中间态)
      this.filePrio.visible = false;  // 内容页签小菜单与行选中跨种子失效(与 drawerTab/closeDrawer 同口径)
      this.drawerSelPath = "";
      this._loadDrawerTab(this.drawer.tab);
      // 详情恒拉(头部标题/常规页都依赖, 与 openTorrentDrawer 同口径): _loadDrawerTab 只在 general
      // 页签拉详情, 其余页签在此补一发 —— seq 归 _loadDrawerTab 先 bump(页签数据走代际守卫),
      // 详情这次不带 seq 只走 hash 戳守卫(同 hash 内晚到也是同资源, 无覆盖错目标风险)。
      if (this.drawer.tab !== "general") this._fetchDrawerDetail();
    },
    /* 本次切换要等的数据源(tab -> 「详情 + 该 tab 列表」); 常规页签只有详情一项 */
    _drawerWaitSources(tab) {
      if (tab === "general") return ["detail"];
      if (tab === "content") return ["detail", "files"];
      return ["detail", tab];
    },
    /* 单个数据源到手(成功或失败都算到手 —— 失败要让 error 态显出来, 不能把遮罩挂死)。
     * 过期响应不登记: 它的数据没落袋, 状态仍属于在途的新目标。 */
    _drawerDone(src, hash, seq) {
      const w = this._drawerWait;
      if (!w || this._drawerStale(hash, seq)) return;
      w.delete(src);
      if (w.size) return;      // 还有兄弟源在飞 —— 不提前掀罩(防半新半旧)
      this._drawerSwitchEnd();
      if (this._drawerOpenReveal) {  // 开场路径的落定补让位(挂单见 openTorrentDrawer; 切换路径无挂单)
        const h = this._drawerOpenReveal;
        this._drawerOpenReveal = "";
        // 双守卫防迟到兑现: 挂单后被打断(关闭/换目标)时 drawer.open/hash 已易主, 那是别的种子几何
        if (this.drawer.open && this.drawer.hash === h) this._kbRevealRow(h);
      }
    },
    /* 遮罩延迟点亮: 局域网详情常在 100ms 内就到 —— 那一刻用户看到的是「内容直接换成新的」,
     * 中间没有任何一帧变淡; 只有真的慢下来(>160ms)才滑入加载胶囊并把旧值淡到不可读。 */
    _drawerBusyArm() {
      this._drawerBusyDisarm();
      this._busyArmTimer = setTimeout(() => {
        this._busyArmTimer = null;
        if (this.drawer.open && !this.drawer.collapsed) this.drawer.switching = true;
      }, 160);
    },
    _drawerBusyDisarm() {
      if (this._busyArmTimer) {
        clearTimeout(this._busyArmTimer);
        this._busyArmTimer = null;
      }
    },
    /* 切换期收尾: 撤待到集合 / 撤延迟 / 撤遮罩(closeDrawer 与中途打断同样走这里) */
    _drawerSwitchEnd() {
      this._drawerWait = null;
      this._drawerBusyDisarm();
      this.drawer.switching = false;
    },
    /* 头部标题: 优先主表成员名(memberByHash 每 1.5~3s 一轮已在本地, 切换瞬间即得) ——
     * 旧实现等详情到位, 中间一帧把标题显示成 40 字符 hash 再跳回种子名, 是肉眼最刺眼的一跳。 */
    drawerTitle() {
      const m = this.memberByHash.get(this.drawer.hash);
      if (m && m.name) return m.name;
      return this.drawer.detail ? this.drawer.detail.name : this.drawer.hash;
    },
    /* 持久化抽屉 tab 偏好(与 persistUiPage 同纪律): 只落"停在哪页"这个意图, 不落派生值;
     * 写入失败(隐私模式/配额满)只影响刷新后落点, 不该打断切页 —— 故吞掉异常。 */
    persistDrawerTab() {
      try {
        localStorage.setItem("autoqb.ui.drawerTab", this.drawerLastTab);
      } catch { /* 写入失败: 本轮仍生效, 刷新后回落默认 */ }
    },
    /* ---------------- W3 高度治理(计划 26-10-03-0917 §2.1/§3.5/D1) ----------------
     * 拖拽调高: 面板顶缘 .drawer-grip 的 pointer 事件(pointer capture, move 实时改高),
     * 夹取 [240px, 70vh]; 收起/展开钮: 收起态只留头部(~44px); 持久化: 高度与开合态进
     * localStorage(autoqb.ui.drawerHeight / autoqb.ui.drawerOpen, 与 drawerTab 同族口径)。
     * D1 拍板 = 首屏默认收起 + 高度记忆仍生效: drawer.open 初值恒 false(state.js),
     * drawerOpen 键只作记录(写入不回读) —— 与「开合态记忆」字面有出入, 首屏满高优先(硬约束)。 */
    /* 夹取函数(纯逻辑, 守阵可锚): px 夹进 [240, 0.7*viewportH]。极小视口下 70vh<240 时
     * 取 70vh 为上界、下界随之取 min(240, 上界) —— 区间保持合法, 面板不越过 70vh 红线。 */
    _drawerClampHeight(px, viewportH) {
      const max = Math.round((viewportH || 0) * 0.7);
      const min = Math.min(240, max);
      return Math.round(Math.min(Math.max(px, min), Math.max(max, min)));  // 取整, 落盘值不带亚像素尾数
    },
    /* 面板内联样式: 展开且有高度记忆/拖拽值时, height 与 max-height 同锁一个 px
     * (CSS 默认 max-height:42vh 只管未拖拽过的内容自适应态; 拖到 42vh 以上必须放开);
     * 流量形态必须给确定高度 —— 图高 = 宿主高(撑满抽屉可用高), 无确定高度时 flex 无解,
     * 故未拖拽过时回落 42vh(与 CSS 默认上限同值); 与种子详情共用同一 drawerHeightPx(高度复用);
     * 收起/关闭态交给 CSS(收起 = body 隐藏, 高度回落头部行高) */
    drawerPanelStyle() {
      if (!this.drawer.open || this.drawer.collapsed) return {};
      const px = this.drawerHeightPx || (this.qbTrafficActive ? Math.round(window.innerHeight * 0.42) : 0);
      if (!px) return {};
      const h = this._drawerClampHeight(px, window.innerHeight);
      return { height: h + "px", maxHeight: h + "px" };
    },
    /* 顶缘拖拽(pointer capture 挂在 grip 元素上, move/up 都派发给它, 出窗不丢事件)。
     * !命名约束: 模板内联处理器不得用 `_` 前缀 —— Vue 3.5 运行时编译的模板解析不了
     * 下划线开头的裸标识符(ReferenceError), 本文件其余 `_` 方法只经 this.xx 调用故无恙。 */
    drawerGripDown(e) {
      if (!this.drawer.open || this.drawer.collapsed) return;  // 收起态无 body 可调
      if (e.button !== undefined && e.button !== 0) return;    // 只认主键
      e.preventDefault();  // 防拖拽起手选中文本/触发滚动
      const panel = e.currentTarget.parentElement;  // grip 是 .drawer 的首子节点
      this._drawerDrag = { startY: e.clientY, startH: panel.getBoundingClientRect().height, pid: e.pointerId };
      e.currentTarget.setPointerCapture(e.pointerId);
      document.body.classList.add("drawer-resizing");
    },
    drawerGripMove(e) {
      const d = this._drawerDrag;
      if (!d || e.pointerId !== d.pid) return;
      if (!this.drawer.open || this.drawer.collapsed) { this.drawerDragStop(); return; }  // 拖拽中面板被关(键盘路径)
      this.drawerHeightPx = this._drawerClampHeight(d.startH + (d.startY - e.clientY), window.innerHeight);
    },
    drawerGripUp(e) {
      const d = this._drawerDrag;
      if (!d || e.pointerId !== d.pid) return;
      this.drawerDragStop();
      this.persistDrawerHeight();  // 松手才落盘(拖拽过程不写 localStorage)
    },
    drawerDragStop() {
      this._drawerDrag = null;
      document.body.classList.remove("drawer-resizing");
    },
    /* 收起/展开: 收起 = 只留头部(body 隐藏); 展开即向当前光标补跟(收起期跟随暂停, 见 _kbFollowDrawer) */
    toggleDrawerCollapse() {
      this.drawer.collapsed = !this.drawer.collapsed;
      this.persistDrawerOpen();
      this._dtNotify("collapse");  // 模板核心层(计划 26-10-06-0838 S1): 摘要条走模板响应式, 通知留给变体自身状态
      if (!this.drawer.collapsed) {
        this._kbFollowDrawer();
        // 流量形态: 收起期 body 不可见(图不重建), 展开后宿主重新有尺寸 -> 补一发建图
        const s = this.qbCurScope;
        if (s) this.$nextTick(() => this._qbChartBuild(s));
      }
    },
    persistDrawerHeight() {
      try {
        localStorage.setItem("autoqb.ui.drawerHeight", String(this.drawerHeightPx));
      } catch { /* 写入失败: 本轮仍生效, 刷新后回落默认 */ }
    },
    /* 开合态记录(D1): 展开=1, 收起/关闭=0。只写不回读 —— 首屏恒默认收起(硬约束), 键按计划创建 */
    persistDrawerOpen() {
      try {
        localStorage.setItem("autoqb.ui.drawerOpen", this.drawer.open && !this.drawer.collapsed ? "1" : "0");
      } catch { /* 写入失败: 不影响本轮 */ }
    },
    /* ---------------- 出入过渡(Vue <transition> JS 钩子, drawer.html 接线; 用户报"出现/消失很生硬") ----------------
     * 生硬根源: 停靠面板占据文档流, open 翻转时列表底部一帧被面板撑开/收回 —— 面板本体的
     * transform/opacity 滑淡(CSS .drawer-enter/leave-*)治不了布局跳变。修法 = 槽位插值:
     * enter 用 rAF 追赶循环把 .drawer-dock 高度 0 -> 面板实时高(每帧重量, 详情中途到达长高也跟),
     * leave 反向把面板自身高度收拢到 0(dock auto 跟随); 全程只写 height/margin, 不碰面板 :style
     * 绑定, Vue 重渲染即便回写绑定值下一帧也被循环覆盖(自愈)。动画期 .drawer-anim 裁掉溢出,
     * 面板从底缘升起/收回; prefers-reduced-motion 与窄屏全屏态(D3, 面板 fixed 出流)不插值。
     * 几何登记: 插值期间 dock 顶缘是中间值, 让位量测(_kbRevealRow)不许读 —— enter 起拍把
     * "自然高时的 dock 顶缘"(即落定顶缘, sticky 钉底)登记进 _drawerAnimTop, _kbViewBottom
     * 单点优先消费; 收敛/超时/被打断一律清零。seq 代际闸: 快速开关往返时旧循环立即让位新拍。 */
    _drawerFinalTop(dock) {
      return Math.round(dock.getBoundingClientRect().top);
    },
    _drawerAnimStop() {
      if (this._drawerAnimRaf) {
        cancelAnimationFrame(this._drawerAnimRaf);
        this._drawerAnimRaf = 0;
      }
      const dock = document.querySelector(".drawer-dock.drawer-anim");
      if (dock) {
        dock.classList.remove("drawer-anim");
        dock.style.height = "";
        dock.style.marginTop = "";
      }
    },
    drawerEnterHook(el) {
      const dock = el.parentElement;  // 面板落点 = .drawer-dock(tpl-manifest 注入), aside 的父节点
      this._drawerAnimStop();
      this._drawerAnimSeq = (this._drawerAnimSeq || 0) + 1;
      if (!dock || window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
      const seq = this._drawerAnimSeq;
      // 重开打断收场: 被打断的 leave 已把内联高写在面板上, 清掉再量自然高(压成 0 会把自然高量成 0,
      // 整段动画失效); 槽位残局由 _drawerAnimStop 清理, 面板淡出中的视觉由 CSS enter 接管
      for (const old of dock.querySelectorAll(".drawer.drawer-leave-active")) old.style.height = "";
      dock.style.height = "";  // 量自然高(清残留内联)
      const h0 = dock.getBoundingClientRect().height;
      this._drawerAnimTop = h0 ? this._drawerFinalTop(dock) : 0;  // 自然高帧的顶缘 = 落定顶缘(sticky 钉底)
      if (!h0) return;  // 窄屏全屏态(D3, 面板 fixed 不占布局)或空内容: 无槽位可插值, 交回纯 CSS 滑淡
      const m0 = parseFloat(getComputedStyle(dock).marginTop) || 0;
      dock.classList.add("drawer-anim");
      dock.style.height = "0px";
      dock.style.marginTop = "0px";
      const t0 = performance.now();
      const step = () => {
        if (seq !== this._drawerAnimSeq) return;  // 被新开合打断: 新拍已接管 dock
        const target = el.getBoundingClientRect().height;  // 每帧追面板实时高(详情中途长高也跟)
        const cur = parseFloat(dock.style.height) || 0;
        const next = cur + (target - cur) * 0.45;
        if (Math.abs(target - next) < 1 || performance.now() - t0 > 400) {
          dock.style.height = "";  // 收敛: 回交自然高, 内容后续涨落不再经动画
          dock.style.marginTop = "";
          dock.classList.remove("drawer-anim");
          this._drawerAnimTop = 0;
          this._drawerAnimRaf = 0;
          return;
        }
        dock.style.height = next + "px";
        dock.style.marginTop = Math.min(m0, next * (m0 / h0)) + "px";  // 呼吸距随槽位同步长出
        // 落定顶缘逐帧重登记: 详情中途长高后, enter 起拍登记的 loading 态顶缘不再是落定值,
        // 让位量测(_kbRevealRow/键盘跟随)会按旧几何漏让(2026-10-04 回归取证)。dock sticky
        // 吸底期底缘恒定(margin-top 不参与吸底定位), 落定顶缘 = dock 底缘 - 面板自然高
        // (面板自身布局高不受 dock 槽位 overflow 裁剪, 即当前内容的落定高)。
        this._drawerAnimTop = Math.round(dock.getBoundingClientRect().bottom - target);
        this._drawerAnimRaf = requestAnimationFrame(step);
      };
      this._drawerAnimRaf = requestAnimationFrame(step);
    },
    drawerAfterEnterHook() {
      if (!this.drawer.open) return;  // 入场被快速关闭打断: 迟到的钩子不得杀掉 leave 拍的动画循环
      this._drawerAnimStop();  // 兜底: 追赶循环若仍在途(慢收敛)强制收场回自然高
      this._drawerAnimTop = 0;
      // 槽位落定后补一发让位: 文档底打开时开场让位被钳制成 0(下滚余量是停靠槽位长高才创造的,
      // 2026-10-04 取证), 此刻槽位已回自然高、余量足额, 且收场兜底强制回自然高后几何是实量值。
      // 流量形态无种子行可让, 不发。
      if (this.drawer.kind === "seed") this._kbRevealRow(this.drawer.hash);
    },
    drawerLeaveHook(el) {
      // closeDrawer 已冻结槽位(drawer-anim + 捕获高)时先取值再清理 —— 面板马上转 absolute 出流,
      // 之后 dock 的自然高就塌了, 量不回用户看到的最后一帧
      const frozenDock = document.querySelector(".drawer-dock.drawer-anim");
      const frozenH = frozenDock ? Math.round(frozenDock.getBoundingClientRect().height) : 0;
      this._drawerAnimStop();
      this._drawerAnimSeq = (this._drawerAnimSeq || 0) + 1;
      if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) { this._drawerAnimTop = 0; return; }
      if (getComputedStyle(el).position === "fixed") { this._drawerAnimTop = 0; return; }  // D3 窄屏全屏态: 面板出流, 无布局可插值
      const dock = el.parentElement;
      if (!dock) { this._drawerAnimTop = 0; return; }
      const seq = this._drawerAnimSeq;
      // 优先用 closeDrawer 捕获的用户可见高; 未捕获(入场中被打断, enter 已登记顶缘)退面板实高
      const h0 = frozenH || Math.round(el.getBoundingClientRect().height);
      if (!h0) { this._drawerAnimTop = 0; return; }  // 空内容: 无高度可收
      if (!frozenH && !this._drawerAnimTop) this._drawerAnimTop = this._drawerFinalTop(dock);
      const m0 = parseFloat(getComputedStyle(dock).marginTop) || 0;
      dock.classList.add("drawer-anim");
      dock.style.height = h0 + "px";  // 从捕获帧起步, 面板同步收拢 —— 两边同一曲线永不脱节
      const t0 = performance.now();
      const step = () => {
        if (seq !== this._drawerAnimSeq) return;  // 重开接管: enter 拍已接管 dock 与面板
        const t = Math.min(1, (performance.now() - t0) / 160);  // 收场 160ms = CSS 退场(.drawer-leave-active)同拍
        const k = t * t;  // easeInQuad: 收场加速(与退场滑淡 ease-in 同感)
        // 收面板自身高度(面板已转 absolute 底缘锚定, 底边钉死向下收), dock 冻结高同步跟缴 —— 列表全程只看到面板沉下去
        el.style.height = Math.max(0, Math.round(h0 * (1 - k))) + "px";
        dock.style.height = el.style.height;
        dock.style.marginTop = Math.round(m0 * (1 - k)) + "px";  // 呼吸距同步收回, 免得尾部刺 8px
        if (t < 1) {
          this._drawerAnimRaf = requestAnimationFrame(step);
          return;
        }
        this._drawerAnimRaf = 0;  // 面板节点随后被 Vue 摘除; dock 残留内联由 afterLeave 兜底清
      };
      this._drawerAnimRaf = requestAnimationFrame(step);
      this._drawerAnimDock = dock;  // afterLeave 时面板已出 DOM(parentElement 为 null), 提前留手
    },
    drawerAfterLeaveHook() {
      if (this.drawer.open) return;  // 收场被快速重开打断: 迟到的钩子不得杀掉 enter 拍的动画循环
      this._drawerAnimStop();  // 面板已出 DOM, 兜底清 dock 内联与在途循环
      const dock = this._drawerAnimDock;
      if (dock) {
        dock.classList.remove("drawer-anim");
        dock.style.height = "";
        dock.style.marginTop = "";
        this._drawerAnimDock = null;
      }
      this._drawerAnimTop = 0;
    },
    /* 抽屉头部动作: 复用 actTorrent(它读 menu.hash 并自带回执/toast) */
    drawerAct(action) {
      this.menu.hash = this.drawer.hash;
      this.actTorrent(action);
    },
    /* 抽屉删除: 复用 delTorrent(确认框流程一致); 删除成功(成员消失)后自动收起抽屉 */
    drawerDel() {
      this.menu.hash = this.drawer.hash;
      this._drawerDeletePending = true;
      Promise.resolve(this.delTorrent()).then(() => {
        if (this._drawerDeletePending && !this.memberByHash.get(this.drawer.hash)) this.closeDrawer();
        this._drawerDeletePending = false;
      });
    },
    /* General tab 分组行(预格式化): qB 哨兵在此统一翻译 —— -1=从未/未设, 8640000=无 ETA。
     * W5-RFB-01 展示重构: 分组重组为 基础/传输/时间/路径, 每行带 sprite 图标(icon)供字段行渲染(f-row) */
    drawerGeneralSections() {
      const d = this.drawer.detail;
      if (!d) return [];
      const dur = (v, dash) => (v === null || v === undefined || v < 0) ? (dash || "未设") : this.fmtDuration(v);
      const ts = (v) => this.fmtTs(v) || "—";  // 抽屉保留"—"(TBL-01 只改主页面表格)
      const size = (v) => this.fmtSizeOrDash(v) || "—";
      const yn = (v) => (v ? "是" : "否");
      const lim = (v) => (v === null || v === undefined || v < 0) ? "未设" : (v === 0 ? "不限" : this.fmtDuration(v));
      return [
        {
          title: "基础",
          sum: `容量 ${size(d.size)} · 分享率 ${(d.ratio ?? 0).toFixed(2)}`,
          rows: [
            { icon: "#i-percent", label: "进度", text: `${((d.progress || 0) * 100).toFixed(1)}%` },
            { icon: "#i-hdd", label: "大小", text: size(d.size) },
            { icon: "#i-layers", label: "总大小", text: size(d.total_size) },
            { icon: "#i-download", label: "剩余量", text: size(d.amount_left) },
            { icon: "#i-pulse", label: "可用性", text: (d.availability ?? 0).toFixed(2) },
            { icon: "#i-percent", label: "分享率", text: (d.ratio ?? 0).toFixed(3) },
            { icon: "#i-lock", label: "私有", text: yn(d.private) },
            // FX-22: 哈希/备注可能极长 -> 块行 + 右侧"复制"(不再只能悬停看 title)
            { icon: "#i-hash", label: "信息哈希 v1", text: d.infohash_v1 || "—", mono: true, wide: true, act: "copy" },
            { icon: "#i-hash", label: "信息哈希 v2", text: d.infohash_v2 || "—", mono: true, wide: true, act: "copy" },
            { icon: "#i-columns", label: "分块", text: d.piece_size ? `${d.pieces_have ?? 0} / ${d.pieces_num ?? 0} × ${this.fmtSize(d.piece_size)}` : "—" },
            { icon: "#i-info", label: "已含元数据", text: yn(d.has_metadata) },
            { icon: "#i-calendar", label: "创建于", text: ts(d.creation_date) },
            { icon: "#i-settings", label: "创建工具", text: d.created_by || "—" },
            { icon: "#i-list", label: "备注", text: d.comment || "—", wide: true },
          ],
        },
        {
          title: "传输",
          sum: `实时 ↓${this.fmtSpeedOrDash(d.dlspeed) || "—"} ↑${this.fmtSpeedOrDash(d.upspeed) || "—"}`,
          rows: [
            { icon: "#i-download", label: "下载速度", text: this.fmtSpeedOrDash(d.dlspeed) || "—" },
            { icon: "#i-upload", label: "上传速度", text: this.fmtSpeedOrDash(d.upspeed) || "—" },
            { icon: "#i-hourglass", label: "ETA", text: this.fmtEta(d.eta) || "—" },
            { icon: "#i-download", label: "已下载", text: size(d.downloaded) },
            { icon: "#i-upload", label: "已上传", text: size(d.uploaded) },
            { icon: "#i-download", label: "本次会话下载", text: size(d.downloaded_session) },
            { icon: "#i-upload", label: "本次会话上传", text: size(d.uploaded_session) },
            { icon: "#i-warn", label: "浪费", text: size(d.total_wasted) },
            { icon: "#i-arrow-up", label: "做种", text: String(d.num_seeds ?? 0) },
            { icon: "#i-arrow-down", label: "用户(下载)", text: String(d.num_leechs ?? 0) },
            { icon: "#i-globe", label: "完整/下载中", text: `${d.num_complete ?? 0} / ${d.num_incomplete ?? 0}` },
            { icon: "#i-globe", label: "tracker 数", text: String(d.trackers_count ?? 0) },
            { icon: "#i-link", label: "连接数", text: `${d.connections_count ?? 0} / ${d.connections_limit ?? 0}` },
            { icon: "#i-refresh", label: "下次汇报", text: dur(d.reannounce_in || d.reannounce, "—") },
            { icon: "#i-x-circle", label: "tracker 错误", text: yn(d.has_tracker_error) },
            { icon: "#i-warn", label: "tracker 警告", text: yn(d.has_tracker_warning) },
            { icon: "#i-percent", label: "分享率限制", text: (d.max_ratio ?? -1) < 0 ? "未设" : d.max_ratio.toFixed(2) },
            { icon: "#i-timer", label: "做种时长限制", text: lim(d.max_seeding_time) },
            { icon: "#i-timer", label: "不活跃做种限制", text: lim(d.max_inactive_seeding_time) },
            { icon: "#i-bolt", label: "限制动作", text: d.share_limit_action || "—" },
          ],
        },
        {
          title: "时间",
          sum: `添加 ${ts(d.added_on)}`,
          rows: [
            { icon: "#i-calendar", label: "添加于", text: ts(d.added_on) },
            { icon: "#i-check-circle", label: "完成于", text: ts(d.completion_on) },
            { icon: "#i-eye", label: "见到完整副本", text: ts(d.seen_complete) },
            { icon: "#i-clock", label: "最近活动", text: ts(d.last_activity) },
            { icon: "#i-timer", label: "活跃时间", text: dur(d.time_active, "—") },
            { icon: "#i-timer", label: "做种时间", text: dur(d.seeding_time, "—") },
          ],
        },
        {
          title: "路径",
          sum: `自动种子管理 ${yn(d.auto_tmm)}`,
          // FX-22: 路径行一律块行 + 右侧"打开目录"(走后端 /api/open-path) —— 路径是本页最长、
          // 最常需要"去磁盘上看一眼"的一类值
          rows: [
            { icon: "#i-folder-open", label: "保存路径", text: d.save_path || "—", wide: true, act: "open" },
            { icon: "#i-folder", label: "内容路径", text: d.content_path || "—", wide: true, act: "open" },
            { icon: "#i-folder-open", label: "下载路径", text: d.download_path || "—", wide: true, act: "open" },
            { icon: "#i-folder", label: "根路径", text: d.root_path || "—", wide: true, act: "open" },
            { icon: "#i-sliders", label: "自动种子管理", text: yn(d.auto_tmm) },
            { icon: "#i-play", label: "强制开始", text: yn(d.force_start) },
            { icon: "#i-upload", label: "超级做种", text: yn(d.super_seeding) },
            { icon: "#i-sort", label: "顺序下载", text: yn(d.seq_dl) },
            { icon: "#i-bolt", label: "首末块优先", text: yn(d.f_l_piece_prio) },
          ],
        },
      ];
    },
    /* FX-22: 字段行图标着色 —— 由**图标名派生**色调类, 而不是给 48 行逐个加 tone 字段:
     * 图标本身已隐含语义(下载/上传/日历/文件夹/哈希...), 派生表是单点, 新增行自动生效。
     * 色值全在 views.css 的 .ico-t-* 族里走主题令牌。 */
    icoTone(icon) {
      const map = {
        "#i-download": "ico-t-io", "#i-upload": "ico-t-io", "#i-arrow-up": "ico-t-io", "#i-arrow-down": "ico-t-io",
        "#i-hdd": "ico-t-cap", "#i-layers": "ico-t-cap", "#i-columns": "ico-t-cap",
        "#i-calendar": "ico-t-time", "#i-clock": "ico-t-time", "#i-timer": "ico-t-time",
        "#i-hourglass": "ico-t-time", "#i-eye": "ico-t-time",
        "#i-globe": "ico-t-site", "#i-link": "ico-t-site",
        "#i-lock": "ico-t-sw", "#i-sliders": "ico-t-sw", "#i-play": "ico-t-sw", "#i-sort": "ico-t-sw",
        "#i-bolt": "ico-t-sw", "#i-settings": "ico-t-sw", "#i-refresh": "ico-t-sw",
        "#i-hash": "ico-t-id", "#i-info": "ico-t-id", "#i-tag": "ico-t-id", "#i-list": "ico-t-id",
        "#i-folder": "ico-t-path", "#i-folder-open": "ico-t-path",
        "#i-percent": "ico-t-state", "#i-pulse": "ico-t-state", "#i-check-circle": "ico-t-state",
        "#i-x-circle": "ico-t-state", "#i-warn": "ico-t-state",
      };
      return map[icon] || "";
    },
    /* Content tab: qB files[].name 为 '/' 分隔相对路径 -> 构树后扁平化(缩进渲染);
     * 目录行聚合大小; 文件行展示 进度/优先级(0=跳过 1=普通 4|6=高 7=最高), 优先级可点改(小菜单);
     * 每行带 index(种子内原始下标, files/priority 用)与 path(完整相对路径, 选中/rename-fs 用) */
    drawerFileRows() {
      const files = this.drawer.files || [];
      const root = { dirs: new Map(), files: [], size: 0, path: "" };
      for (let fi = 0; fi < files.length; fi++) {
        const f = files[fi];
        const parts = String(f.name || "").split("/").filter(Boolean);
        let node = root;
        for (let i = 0; i < parts.length - 1; i++) {
          if (!node.dirs.has(parts[i])) {
            node.dirs.set(parts[i], { dirs: new Map(), files: [], size: 0, path: node.path ? node.path + "/" + parts[i] : parts[i] });
          }
          node = node.dirs.get(parts[i]);
          node.size += f.size || 0;
        }
        node.files.push({ ...f, index: fi });
      }
      const prio = (p) => ({ 0: "跳过", 1: "普通", 4: "高", 6: "高", 7: "最高" }[p] ?? "普通");
      const rows = [];
      const walk = (node, name, depth) => {
        if (name !== null) rows.push({ depth, dir: true, name, path: node.path, text: this.fmtSize(node.size) });
        for (const [dn, d] of node.dirs) walk(d, dn, name === null ? 0 : depth + 1);
        for (const f of node.files) {
          const last = String(f.name || "").split("/").pop();
          rows.push({
            depth: name === null ? 0 : depth + 1, dir: false,
            name: last,
            path: node.path ? node.path + "/" + last : last,
            index: f.index,
            text: this.fmtSize(f.size), progress: Math.round((f.progress || 0) * 100),
            prio: prio(f.priority), skipped: f.priority === 0,
          });
        }
      };
      walk(root, null, -1);
      return rows;
    },
    /* Peers tab: qB 响应 peers 可能为 dict(以 ip:port 为键)或数组 —— 双形态归一 */
    drawerPeerRows() {
      const p = this.drawer.peers || {};
      const list = Array.isArray(p.peers) ? p.peers : Object.values(p.peers || {});
      return list.map((x) => ({
        addr: `${x.ip || "?"}${x.port ? ":" + x.port : ""}`,
        client: x.client || "—",
        flags: x.flags || "—",
        progress: Math.round((x.progress || 0) * 100),
        dlspeed: this.fmtSpeedOrDash(x.dlspeed || 0) || "—",  // 抽屉 peers 表保留"—"
        upspeed: this.fmtSpeedOrDash(x.upspeed || 0) || "—",
        downloaded: this.fmtSizeOrDash(x.downloaded || 0) || "—",
        uploaded: this.fmtSizeOrDash(x.uploaded || 0) || "—",
        relevance: `${Math.round((x.relevance || 0) * 100)}%`,
      }));
    },
    drawerTrackerStatus(s) {
      return { 0: "未启用", 1: "未连接", 2: "正常", 3: "更新中", 4: "未连接" }[s] ?? "—";
    },
    drawerTrackerVirtual(url) {
      const u = String(url || "");
      return u.startsWith("**") || ["[DHT]", "[PeX]", "[LSD]"].some((p) => u.startsWith(p));
    },
  },
};
