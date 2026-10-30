/* auto-qb WEB UI · 种子转移交互流(计划 26-10-31-0306 W4 前半/T6)
 *
 * 分工:
 *   本文件              转移交互的**触发单点**: 菜单读侧(启用目标列表) + 触发钩子 transferOpen
 *   ctx_menu.js         「转移到」父项注册(kind:"submenu" + subName:"transfer", 四支各一项,
 *                       布局可经 web.ctx_menu 定制 —— 与其它菜单项同一套注册/合并/渲染体系)
 *   tpl/ctx-menus.html  submenu 骨架(父项/子项骨架各一份, 四支与「更多操作」共用)
 *   transfer_targets.js 设置页目标编辑器(T5, 写侧) —— 本文件只读配置, 不写树
 *
 * 读侧数据(菜单子项 = config.web.transfer.targets 中 enabled=true 的目标, D5):
 *   GET /api/config 现拉, 缓存进 trTargets(state.js, 整表替换) —— 菜单渲染只读缓存:
 *     ① 登录后预拉一次(lifecycle.js / auth.js 的 loadWebFlags 调用点旁边);
 *     ② 设置页保存成功后重拉(config_editor.js cfgSave, 与 loadWebFlags 同节奏);
 *     ③ 展开「转移到」子面板时重拉(menu.js openSub 钩子, 收窄外部改配置的陈旧窗)。
 *   三处都只**刷新缓存**, 渲染永远读 trTargets; 拉取失败保持上次缓存(菜单是瞬态浮层,
 *   不 toast 不打断, 下次展开再试)。目标按 name 寻址(与 POST /api/transfer/run 的
 *   target_id 同口径, 也与 ttTest 一致) —— 无名/未启用的目标不进菜单。
 *
 * 触发钩子(T7, 本任务实现):
 *   transferOpen(targetId, hashes) —— 确认弹窗四段式(预检 -> 明细 -> 执行 -> 结算, 参照
 *   delete_flow.js::_deleteFlow 范本); 菜单与未来入口一律只把 (target_id, hashes) 交到
 *   这里, 不自带任何弹窗/预检/执行逻辑(范围守恒: T6 只做菜单, 弹窗是本文件)。
 *
 * 四段式分工(T7 实测口径):
 *   预检(前端轻量, 后端无独立预检路由, 不新开): 目标存在+启用(trTargets 缓存) / 逐 hash
 *     在当前列表表态(memberByHash = groups ∪ singles ∪ torrents 全量) / 状态门预演(与
 *     orchestrator.gate_verdict 同口径: missingFiles / 下载管线态 / 白名单外未知态 -> 将跳过)。
 *     预检能拦的(目标失效 / hash 失效 / 状态门)给出「将跳过及原因」且**不投递**;
 *     export 可用性与目标连通性前端无轻量判据, 后置到执行段失败分类(EXPORT_FAILED /
 *     AUTH_FAILED / ADD_FAILED / VERIFY_*), 由回执逐项结算。
 *   明细(单弹窗, 复用 ui_feedback::_openModal 的 details/checks, 不新增 tpl 分片):
 *     目标名/类型 / 数量 / 将跳过及原因 / 字段清单(按 target.fields 开关) / 改写路径预览
 *     (trMapSavePath: 有序前缀替换、首条命中、只作用保存路径终值 —— 与 orchestrator.
 *     map_save_path 逐位同语义, 守阵 test_transfer_flow_confirm.py 用后端真函数对账) /
 *     跳检警示(skip_check 开时) / 「仅本次保留源种子」勾选(默认不勾, D1)。
 *   执行: 确认后 POST /api/transfer/run 走 waitCmd(超时随批量放大); _transferRunning
 *     单飞闸禁重复触发; 行内 pending 图标兜底随超时放大。
 *   结算(批量管线三件套: waitCmd 回执 + toast 三态 + setRowIcon 行内图标): 回执 truth.
 *     results 逐项落图标(成功/跳过/失败 -> ok/warn/error, 原因进图标 tooltip); toast 按
 *     失败>跳过>全成 三态给计数与首因; truth 缺失不谎称成功(统一 warn, reannounce 同口径)。
 *
 * !不变量文案: 转移只移任务不动数据 —— 弹窗 body 明示「目标添加并验证成功后才删源任务
 *   (仅任务, 不删文件)」; 任何不成功路径源保留由后端 orchestrator 保证。
 * !装载序: 三份 index.html 清单里本文件排在 transfer_targets.js 之后、app.js 之前(app.js
 *   末尾 app.mixin 注入, 启动时要读 window.AQB_*)。
 * !与其它 mixin 同款: 方法名是全局命名空间(跨 mixin 重名会被静默合并盖掉且不报错,
 *   _scan_mixin_wiring 钉这种形态) —— 本文件方法全走 transfer 与 ctxTransfer 前缀。
 * !顶层 const/function 全走 TR_ / trMap 前缀(classic script 顶层声明共享全局词法环境,
 *   跨文件撞名 = 整文件 SyntaxError, 见 pitfalls/web-ui/classic-script-top-level-const-collision)。
 */

/* 状态门预演集(与 transfer/orchestrator.py 的 gate 判据同口径; 守阵
 * test_transfer_flow_confirm.py 从后端真值逐位对账, 两处漂移当场红) */
const TR_GATE_MISSING_FILES = "missingFiles";
const TR_GATE_PIPELINE_STATES = [
  "metaDL", "downloading", "stalledDL", "queuedDL", "checkingDL", "allocating", "forcedDL",
];
const TR_GATE_ALLOWED_STATES = [
  "uploading", "stalledUP", "pausedUP", "stoppedUP", "queuedUP", "forcedUP", "checkingUP",
  "pausedDL", "stoppedDL", "error",
];

/* 保存路径改写(前端预览单点, 语义与 orchestrator.map_save_path 逐位一致):
 * 有序 from->to 前缀替换、首条命中生效、无命中原样; 只作用于保存路径终值(调用方保证)。
 * 入参 rules 是配置树形状([{from, to}, ...], 标量全字符串); 挂 window 供守阵探针
 * 用后端真函数对账, 不用正则剖 JS 源码。 */
function trMapSavePath(savePath, rules) {
  const sp = String(savePath == null ? "" : savePath);
  const list = Array.isArray(rules) ? rules : [];
  for (const rule of list) {
    const from = String((rule && rule.from != null) ? rule.from : "");
    if (from && sp.startsWith(from)) {
      return String((rule && rule.to != null) ? rule.to : "") + sp.slice(from.length);
    }
  }
  return sp;
}
window.AQB_TRANSFER_MAP_SAVE_PATH = trMapSavePath;
/* 状态门预演集同款挂载(守阵探针与后端 orchestrator 真值对账用)。
 * !先聚成常量再挂 window(不是 `window.X = {...}` 字面量形态) —— bundle 守阵把
 *   该形态识别为 mixin 待注入面, 而这是纯数据挂载点(AQB_TRANSFER_FIELDS 同款)。 */
const TR_GATE_STATES = {
  missing: TR_GATE_MISSING_FILES,
  pipeline: TR_GATE_PIPELINE_STATES,
  allowed: TR_GATE_ALLOWED_STATES,
};
window.AQB_TRANSFER_GATE_STATES = TR_GATE_STATES;

window.AQB_TRANSFER_FLOW = {
  methods: {
    /* ---------------------------------------------------------- 读侧缓存 */
    /* GET /api/config -> web.transfer.targets 缓存进 trTargets(整表替换, 失败保持旧缓存)。
     * 走配置树而非 /api/webui/flags: targets 是完整配置结构且会随设置页保存变化, 与
     * transfer_targets.js::ttList 同一份真值(磁盘树), 不另造下发通道。 */
    async transferTargetsReload() {
      try {
        const conf = await this.api("/api/config");
        const config = conf && conf.tree && conf.tree.config ? conf.tree.config : {};
        const web = config.web && typeof config.web === "object" ? config.web : {};
        const transfer = web.transfer && typeof web.transfer === "object" ? web.transfer : {};
        this.trTargets = Array.isArray(transfer.targets) ? transfer.targets : [];
      } catch (e) {
        /* 保持上次缓存: 不打断菜单(下次展开再试) */
      }
    },
    /* 「转移到」子面板的子项(注册表 ctxRenderLayer 经 vm 调用; **恒返回 >= 1 项** ——
     * 无启用目标时给空态灰项「未配置目标, 去设置」, 子面板永不空)。子项形状与注册表
     * 渲染项同构(id/kind/label/note/icon/cls/gated/title/act/level), 走同一条子项骨架。 */
    ctxTransferMenuItems() {
      const hashes = this.ctxTransferHashes();
      const items = [];
      for (const t of this.trTargets || []) {
        const name = String((t && t.name) || "").trim();
        if (!name || !this.cfgTruthy(t && t.enabled)) continue;
        items.push({
          id: "transfer:" + name,
          kind: "item",
          label: name,
          note: "",
          icon: { cls: "", use: "#i-hdd" },
          cls: "",
          gated: false,
          title: "",
          act: (vm) => vm.transferOpen(name, hashes),
          level: 1,
        });
      }
      if (!items.length) {
        items.push({
          id: "transfer-empty",
          kind: "item",
          label: "未配置目标, 去设置",
          note: "",
          icon: { cls: "", use: "#i-settings" },
          cls: "",
          gated: true,  // is-gated 灰态(样式诉求), 但仍可点: 点击跳设置卡
          title: "",
          act: (vm) => vm.ctxTransferGoSettings(),
          level: 1,
        });
      }
      return items;
    },
    /* 当前菜单作用对象的 hash 全集 —— 四支统一走作用域单点 selection.js::_ctxScope:
     * multi = 选中集(组 key 按成员闭包展开) / episode = menu.episode.hashes /
     * member = menu.hash / group = 该组成员闭包; D5「选中集优先, 否则整组成员」的语义
     * 由 _scopeResolve 承担, 这里不做第二套判据。菜单渲染时求值 = 开层快照(D5)。
     * !closure 是去重后的 hash 全集(组 key 的成员已展开), 正是 /api/transfer/run 的
     *   hashes[] 口径 —— 不送组 key(后端只认 hash)。 */
    ctxTransferHashes() {
      const d = this._ctxScope();
      return d && d.closure ? Array.from(d.closure) : [];
    },
    /* 空态灰项: 收菜单 -> 进设置页 -> 落「WebUI」卡(现有导航机制 openSettings + hubGo) */
    ctxTransferGoSettings() {
      this.menu.visible = false;
      this.openSettings().then(() => this.hubGo("webui"));
    },

    /* ---------------------------------------------------------- 触发钩子(T7 四段式) */
    /* 预检段(前端轻量): 目标存在+启用 / 逐 hash 在当前列表态 / 状态门预演。
     * 返回 {err} = 开不了弹窗(目标侧问题, toast 后返回); 否则 {target, send, skips}:
     * send = 预检放行、确认后真正投递的 hashes; skips = [{hash, reason}] 预检拦截项
     * (确认弹窗明示「将跳过及原因」, 执行时不投递 —— 与后端 gate_verdict 的跳过同口径,
     * 源任务与数据文件都不动)。export 可用性/目标连通性不在预检面(见文件头四段式分工)。 */
    _transferPrecheck(targetId, hashes) {
      const targets = Array.isArray(this.trTargets) ? this.trTargets : [];
      const want = String(targetId || "").trim();
      const target = targets.find((t) => String((t && t.name) || "").trim() === want);
      if (!target) return { err: `转移目标不存在或已改名: ${want}(见设置页「种子转移」)` };
      if (!this.cfgTruthy(target.enabled)) {
        return { err: `转移目标未启用: ${want}(在设置页「种子转移」里打开启用开关)` };
      }
      const seen = new Set();
      const send = [];
      const skips = [];
      for (const raw of Array.isArray(hashes) ? hashes : []) {
        const hash = String(raw || "");
        if (!hash || seen.has(hash)) continue;
        seen.add(hash);
        const m = this.memberByHash ? this.memberByHash.get(hash) : null;
        if (!m) {
          skips.push({ hash: hash, reason: "当前列表里找不到该种子(可能已被删除)" });
          continue;
        }
        const gate = this._transferGateText(String(m.state || ""));
        if (gate) {
          skips.push({ hash: hash, reason: gate });
          continue;
        }
        send.push(hash);
      }
      return { target: target, send: send, skips: skips };
    },
    /* 状态门预演单点: 拦截返回原因文案, 放行返回 ""。三档判据与文案同
     * orchestrator.gate_verdict 逐位一致(守阵用后端真值对账), 差别只在结果消费方向:
     * 后端落「跳过」回执, 前端在弹窗里先给「将跳过及原因」且不投递。 */
    _transferGateText(state) {
      if (state === TR_GATE_MISSING_FILES) return "源数据文件已丢失(missingFiles), 不可转移";
      if (TR_GATE_PIPELINE_STATES.includes(state)) return `下载管线态(${state}), 不可转移`;
      if (!TR_GATE_ALLOWED_STATES.includes(state)) return `未知状态(${state || "空"}), 保守拦截`;
      return "";
    },
    /* 字段清单文案: 按 target.fields 开关(window.AQB_TRANSFER_FIELDS 单点, 键序=展示序;
     * 缺键回退模板默认 = ttFieldOn 同口径)。保存路径锁死必开, 单独注记不进开关列表。 */
    _transferFieldList(target) {
      const fields = target && target.fields && typeof target.fields === "object" ? target.fields : {};
      const defs = window.AQB_TRANSFER_FIELDS || [];
      const on = [];
      for (const f of defs) {
        if (f.key === "save_path") continue;
        const v = fields[f.key];
        if (v === undefined ? !f.defOff : this.cfgTruthy(v)) on.push(f.label);
      }
      return on.length ? on.join("、") + "(保存路径恒转移)" : "仅保存路径(其余字段不跟随)";
    },
    /* 改写路径预览(计划 §07 风险 1 的肉眼可查防线): 对涉及源种子的保存路径终值逐条
     * 走 trMapSavePath, 唯一 (源 -> 改写后) 对逐行展示 + 命中种子数; 未命中/空路径单独
     * 注记。展示上限 6 组, 超出给汇总行(同一规则命中的改写口径相同, 不损失审查面)。 */
    _transferPathRows(target, send) {
      const rules = Array.isArray(target.path_map) ? target.path_map : [];
      if (!rules.length) {
        return [{ icon: "#i-folder-open", label: "路径映射", wide: true, value: "未配置映射, 保存路径原样转移" }];
      }
      const ruleTxt = rules
        .map((r) => `${String((r && r.from) || "")} -> ${String((r && r.to) || "")}`)
        .join("; ");
      const rows = [{
        icon: "#i-folder-open", label: "路径映射", wide: true,
        value: `${rules.length} 条规则(有序前缀替换, 首条命中生效): ${ruleTxt}`,
      }];
      const pairs = new Map();  // "src\ndst" -> 种子数
      let unchanged = 0;
      let noPath = 0;
      for (const h of send) {
        const m = this.memberByHash ? this.memberByHash.get(h) : null;
        const sp = String((m && m.save_path) || "");
        if (!sp) { noPath += 1; continue; }
        const dst = trMapSavePath(sp, rules);
        if (dst === sp) { unchanged += 1; continue; }
        const k = sp + "\n" + dst;
        pairs.set(k, (pairs.get(k) || 0) + 1);
      }
      const entries = [...pairs.entries()];
      const CAP = 6;
      for (const [k, n] of entries.slice(0, CAP)) {
        const sep = k.indexOf("\n");
        rows.push({
          icon: "#i-folder-open", label: "改写预览", wide: true,
          value: `${k.slice(0, sep)} -> ${k.slice(sep + 1)}`,
          hint: `${n} 个种子的保存路径将被改写为箭头后的值`,
        });
      }
      if (entries.length > CAP) {
        rows.push({
          icon: "#i-folder-open", label: "改写预览", wide: true,
          value: `其余 ${entries.length - CAP} 组未逐条列出(同一规则命中, 改写口径相同)`,
        });
      }
      if (unchanged) {
        rows.push({
          icon: "#i-folder-open", label: "未命中映射", wide: true,
          value: `${unchanged} 个种子保存路径原样(无规则命中其前缀)`,
        });
      }
      if (noPath) {
        rows.push({ icon: "#i-folder-open", label: "无保存路径", wide: true, value: `${noPath} 个种子当前未上报保存路径(执行时按 qB 实值为准)` });
      }
      return rows;
    },
    /* 明细段: 四段式的确认弹窗(复用 _openModal, 不新增 tpl 分片)。details 行表 +
     * 「仅本次保留源种子」单选项(D1 默认不勾); tone=warn + strip = 后果类操作警示条
     * (非删除级 danger: 默认路径删的也只是任务, 数据文件全程不动)。 */
    async _transferConfirm(target, send, skips) {
      const name = String(target.name || "").trim();
      const type = String(target.type || "qb");
      const typeLabels = window.AQB_TRANSFER_TYPE_LABELS || {};
      const rows = [
        { icon: "#i-hdd", label: "目标", value: `${name}(${typeLabels[type] || type})`, wide: true },
        { icon: "#i-cards", label: "数量", value: `将转移 ${send.length} 个种子` },
      ];
      if (skips.length) {
        const reasons = [...new Set(skips.map((s) => s.reason))];
        rows.push({
          icon: "#i-warn", label: "将跳过", tone: "warn", wide: true,
          value: `${skips.length} 个(执行时不投递, 源保留): ${reasons.slice(0, 3).join("; ")}${reasons.length > 3 ? " 等" : ""}`,
        });
      }
      rows.push({ icon: "#i-layers", label: "转移字段", value: this._transferFieldList(target) });
      rows.push(...this._transferPathRows(target, send));
      if (this.cfgTruthy(target.skip_check)) {
        rows.push({
          icon: "#i-warn", label: "跳检警示", tone: "warn", wide: true,
          value: "目标已开启「跳过校验」: 未完成种子将在执行时自动降级为校验添加, 绝不以跳检形式添加",
        });
      }
      return this._openModal({
        title: `转移到「${name}」`,
        body: "转移只移动下载任务, 不动任何数据文件; 目标添加并验证成功后才会删除源任务(仅删任务, 不删文件)。",
        details: rows,
        wide: true,
        checks: [{
          key: "keep_source",
          label: "仅本次保留源种子(转移成功后也不删除源任务)",
          checked: false,
        }],
        okText: "开始转移",
        cancelText: "取消",
        icon: "#i-hdd",
        tone: "warn",
        strip: true,
      });
    },
    /* 执行段 + 结算段: 确认后 POST /api/transfer/run 走 waitCmd, 回执逐项结算。
     * _transferRunning 单飞闸: 执行中重复触发直接返回(删除流"确认后不可再改主意"同纪律);
     * waitCmd 超时随批量放大(串行逐种子, 单条最坏 = export+添加+验证 10s, 见 §07 风险 3),
     * 行内 pending 图标兜底同步放大。结算三件套: 回执 truth.results 逐项 setRowIcon
     * (成功/跳过/失败 -> ok/warn/error, 原因进 tooltip) + toast 三态(失败>跳过>全成) +
     * 完成后刷新目标缓存(列表态交 rid 轮询自然对齐, 与删除流同口径)。 */
    async _transferExec(targetId, name, send, skips, keepSource) {
      if (this._transferRunning) return;
      this._transferRunning = true;
      const timeoutMs = Math.max(40000, send.length * 20000 + 20000);
      const tid = this.toast(
        `正在转移 ${send.length} 个种子到「${name}」…(串行执行, 数据文件不动)`, "busy", 0, { sticky: true }
      );
      for (const h of send) this.setRowIcon(h, "pending", "转移中…", timeoutMs + 5000);
      let r = null;
      try {
        const body = { target_id: targetId, hashes: send };
        if (keepSource) body.keep_source = true;  // 「提供才透传」, 与路由口径一致(缺省 = 默认删源)
        const resp = await this.api("/api/transfer/run", { method: "POST", body: JSON.stringify(body) });
        r = await this.waitCmd(resp.cmd_id, timeoutMs);
      } catch (e) {
        /* 投递失败(网络/400): 一批全未执行 —— 撤 pending 图标(不落 error: 种子没被碰过,
         * 落红图标反而谎报), 只 toast。 */
        for (const h of send) this.setRowIcon(h, "", "");
        this._finishToast(tid, "error", "转移命令发送失败: " + ((e && e.message) || e), 8000);
        this._transferRunning = false;
        return;
      }
      /* 结算: 回执 truth = {results: [{hash, 状态(成功/跳过/失败), 原因}], summary, target}。
       * 中文三态 -> 行内图标三色; summary 缺失时按 results 现算; 两个兜底都「不谎称成功」:
       *   !r.ok(命令级失败, 如目标在投递-执行之间被删/停用) -> 全批 error + 原因;
       *    r.ok 但 results 缺失(等待超时/旧后端) -> 全批 warn(reannounce truth 缺失同口径)。 */
      const truth = (r && r.truth) || {};
      const results = Array.isArray(truth.results) ? truth.results : null;
      let okN = 0, skipN = 0, failN = 0, firstFail = "", firstSkip = "";
      if (results) {
        for (const it of results) {
          const hash = String((it && it.hash) || "");
          const label = String((it && it["状态"]) || (it && it.status) || "");
          const reason = String((it && it["原因"]) || (it && it.reason) || "");
          let kind = "warn";
          if (label === "成功" || label === "success" || label === "ok") { kind = "ok"; okN += 1; }
          else if (label === "失败" || label === "failed" || label === "error") {
            kind = "error"; failN += 1;
            if (!firstFail) firstFail = reason;
          } else {
            skipN += 1;
            if (!firstSkip) firstSkip = reason;
          }
          this.setRowIcon(hash, kind, reason);
        }
      } else if (!r.ok) {
        failN = send.length;
        firstFail = String(r.error || "执行失败");
        for (const h of send) this.setRowIcon(h, "error", firstFail);
      } else {
        skipN = send.length;
        firstSkip = "未收到逐项结果(以程序日志为准)";
        for (const h of send) this.setRowIcon(h, "warn", firstSkip);
      }
      const allSkip = skipN + skips.length;
      const head = `转移结算(目标 ${name}): 成功 ${okN}, 跳过 ${allSkip}, 失败 ${failN}`;
      if (failN) {
        this._finishToast(tid, "error", `${head}; ${firstFail || "部分种子失败, 源已保留"}`, 8000);
      } else if (allSkip) {
        this._finishToast(tid, "timeout", `${head}; ${firstSkip || "部分种子被跳过, 源保留"}`, 6000);
      } else {
        this._finishToast(tid, "ok",
          `${head}${keepSource ? "(按勾选保留源任务)" : "(源任务已删除, 数据文件未动)"}`, 3000);
      }
      this.transferTargetsReload();  // 目标缓存对齐热重载后的配置; 列表态交 rid 轮询自然刷新
      if (!keepSource && okN > 0) this.clearSelection();  // 源任务已删的行不再留在选中集(删除流同口径)
      this._transferRunning = false;
    },
    /* 四段式入口: 菜单与未来入口只交 (target_id, hashes), 预检/明细/执行/结算全在本文件 */
    async transferOpen(targetId, hashes) {
      if (this._transferRunning) return;  // 执行中禁止重复触发(单飞闸, 与 _transferExec 同闸)
      const pre = this._transferPrecheck(targetId, hashes);
      if (pre.err) {
        this.toast(pre.err, "error", 8000);
        return;
      }
      this._auditScope("transfer", { keys: [], hashes: pre.send });  // S4 运行时审计(默认关, 只记账)
      if (!pre.send.length) {
        const reasons = [...new Set(pre.skips.map((s) => s.reason))].join("; ");
        this.toast(`没有可转移的种子: ${pre.skips.length} 个全部被预检排除(${reasons})`, "error", 8000);
        return;
      }
      const res = await this._transferConfirm(pre.target, pre.send, pre.skips);
      if (!res) return;  // 取消/Esc/遮罩 = 零副作用
      const keepSource = !!(res.checks && res.checks.keep_source);
      await this._transferExec(String(targetId || "").trim(), String(pre.target.name || "").trim(),
        pre.send, pre.skips, keepSource);
    },
  },
};
