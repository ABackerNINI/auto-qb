/* auto-qb WEB UI · 分组派生装饰(状态聚合/共同标签分类/图标文案)
 *
 * app.js 按域拆分出的片段(2026-09-20)。约定与 config_editor.js / config_rules.js 同一范式:
 * 挂到 window.AQB_DECORATE, 由 app.js 末尾 app.mixin(window.AQB_DECORATE) 注入同一个 Vue 实例 ——
 * 方法体里的 this 仍是那个组件实例, 跨模块互调与拆分前完全等价。
 *
 * !本文件在 HTML 里必须排在 app.js **之前**(app.js 末尾要读 window.AQB_DECORATE);
 *   用到的列模型常量(TABLE_COLUMNS / MIN_COL_PX / STATE_RANK …)仍单点定义在 app.js 顶部。
 */
/* S7 装饰记忆化(plan 26-10-07-0414; S10 收尾回归修复 2026-10-07): WeakMap<组行对象, {fp, deco}>。
 *
 * 缓存键 = 行对象引用 + 缓存值带「输入指纹」(纯函数缓存的标准失效法)。输出**只**依赖:
 *   ①组行自身字段 —— 服务端承诺脏行恒新建 dict、跨版本引用稳定(S6 后 delta 合并原样保留),
 *     行对象引用不变 ⇒ 内容不变, 这一半由 WeakMap 键覆盖;
 *   ②g.members 的**成员字段值** —— 成员行会被**原地改**: P0-3 乐观补丁链(applyOptimistic /
 *     resolveOptimistic 回滚 / reapplyPending / onTruthEvent)沿 _forEachRow 对成员直接
 *     Object.assign kind, 成员对象引用不变。S7 初版"行对象引用即完整缓存键"漏了这一面:
 *     组行身份不变 => WeakMap 恒命中 => 装饰结果陈旧 => 乐观值不再传导到组行状态色
 *     (踩 S4/S7 零改动区与"装饰结果与无记忆化逐字段一致"的 S7 验收)。
 * 指纹 fp 记装饰实际消费的源值(members 引用 + 逐成员 kind/size/category/site/tags 引用 +
 * 首成员 save_path —— 恰好 = save_path/status/commonTags/commonCategory/sizeMismatch
 * 5 个派生字段的完整输入面; _rank/kindText/_filterSiteTags 是纯方法, 不在输入面内,
 * 筛选/多选态走 filters.js/state.js 独立 computed 同样不在): 命中前逐槽比对, 任一失配
 * 即重算并回填 —— 原地变更指纹失配自然失效, 引用稳定的未脏行指纹一致命中复用(S7 的
 * "未脏行装饰结果引用恒等"断言保住), 重算面仍收敛到脏行。弱引用不延长废弃行对象寿命。
 * 返回结构形状不变(键集/字段与无记忆化完全一致), 消费方 sort.js sortedGroups /
 * filters.js / selection.js 不感知 —— 记忆化若改形状即踩 computed 静默白屏坑
 * (pitfalls/web-ui/vue-reactivity.md)。
 */
const _decoCache = new WeakMap();

/* relocate 标注签名(plan 26-11-04-1042 P0-5; P1 补齐 src/armed_at; 26-11-07-2344 S2 组级签名补 src):
 * 后端每次重建会产出新的 relocate 对象, 直接把对象引用放进指纹会让所有组行恒失配 —— 必须压成
 * 值签名后再比较。P1 详情段消费 src/created_at/armed_at; 行内两排 A→B(relocateView)消费 src/dst,
 * 任一值推进必须让装饰缓存失效(漏槽 = 相位推进后两排停在旧值)。 */
function _relocateSig(r) {
  if (!r) return "";
  return [r.state, r.phase, r.job_id, r.mover ? 1 : 0, r.origin, r.alias_kind, r.alias_count, r.src, r.dst,
          r.created_at, r.armed_at, r.updated_at, r.reason].join("|");
}

/* 迁移状态展示词表(plan 26-11-04-1042 P1): 筛选 / 详情段 / 单排回落语义共用一份, 禁止在模板里
 * 另写字面量三元。done / cancelled 不长期挂行内展示, 但仍算「有过迁移」。 */
const RELOCATE_STATE_TEXT = {
  moving: "迁移中", pending_finalize: "待收尾", failed: "迁移失败",
  mixed: "迁移多任务", done: "已完成", cancelled: "已撤销",
};
/* 状态 -> 色调映射(plan 26-11-07-2344 S2, 取代旧 RELOCATE_STATE_CLASS): 状态唯一载体 = 颜色
 * (.rel-tone-<tone>, row_lang.css 单点定义), 无底形无边框无药丸。done / cancelled 不在表内 ——
 * relocateView 对它们恒 null, 行内回落单排正常色。 */
const RELOCATE_TONE = { moving: "moving", pending_finalize: "pending", failed: "failed", mixed: "mixed" };
const RELOCATE_FILTER_ANY = "有过迁移";
const RELOCATE_ORIGIN_TEXT = { web: "WebUI", rule: "规则", unknown: "未知来源" };
/* 进行中三态(plan 26-11-07-2344 R3 D17): 位置集匹配(_pathPositions)与行内两排展示
 * (relocateView pair)共用同一 active 边界 —— 行内显示 B 排的行, 其 dst 才参与路径匹配。 */
const RELOCATE_ACTIVE_STATES = new Set(["moving", "pending_finalize", "failed"]);

function _groupRelocateSig(r) {
  if (!r) return "";
  return [r.state, r.pending, r.total, (r.job_ids || []).join(","), (r.dst || []).join(","), r.src,
          r.updated_at].join("|");
}

/* 指纹槽位(与 _decoFpBuild 逐字对应): [members 引用, (kind, size, category, site, tags 引用,
 * site_alert, site_alert_msg, relocate 签名)*n, 首成员 save_path, 组 relocate 签名]
 * !site_alert / site_alert_msg 必须进指纹(计划 26-10-19-2007 R3): 它们是站点 chip 左槽图标的
 *   唯一数据源, 而组行装饰是记忆化的 —— 不进指纹则"站点报错"出现/消失后组行仍命中旧缓存,
 *   图标永远陈旧(成员行是现渲染的, 只有组行会停在旧态, 这类不一致最难查)。
 * !成员/组的 relocate 签名同理必须进指纹(P0 迁移可见性): 相位推进只改 relocate 值,
 *   组行与成员对象引用不变, 漏槽会让进度徽标停在旧相位。 */
function _decoFpBuild(g) {
  const ms = g.members || [];
  const fp = [ms];
  for (const m of ms) {
    fp.push(m.kind, m.size, m.category, m.site, m.tags, m.site_alert, m.site_alert_msg, _relocateSig(m.relocate));
  }
  fp.push(ms.length ? ms[0].save_path : undefined, _groupRelocateSig(g.relocate));
  return fp;
}

function _decoFpHit(g, fp) {
  const ms = g.members || [];
  if (fp[0] !== ms || fp.length !== ms.length * 8 + 3) return false;
  let i = 1;
  for (const m of ms) {
    if (fp[i++] !== m.kind || fp[i++] !== m.size || fp[i++] !== m.category || fp[i++] !== m.site ||
        fp[i++] !== m.tags || fp[i++] !== m.site_alert || fp[i++] !== m.site_alert_msg ||
        fp[i++] !== _relocateSig(m.relocate)) {
      return false;
    }
  }
  return fp[i] === (ms.length ? ms[0].save_path : undefined) &&
    fp[i + 1] === _groupRelocateSig(g.relocate);
}

/* 强制重新汇报"非活跃"状态集(qB 口径, 单点): qBittorrent commit aa189a7(关闭 issue #12080)
 * 起, 右键 "Force reannounce" 只在种子可汇报时可用 —— isPaused / isChecking / isQueued 时
 * `setEnabled(false)` 置灰, 其 tooltip 原文 "Can not force reannounce if torrent is
 * Paused/Queued/Errored/Checking"。根因在 libtorrent: force_tracker_request 对暂停种子
 * `if (is_paused()) return;` 直接空转, 排队种子同样发不出去(本项目调研报告
 * 26-10-05-0854 §3 附注「停止种子盲区」)。
 *
 * !判定必须读 qB **原始 state 串**而不是 kind: kind 现 7 档(2026-10-29 加 moving), 而
 *   queuedDL/queuedUP 被 qbittorrent-api 归进 is_downloading/is_uploading ⇒ 落成
 *   downloading/seeding, 单看 kind 会把排队种子当成活跃。state 缺失(老版本/异常行)时回落到
 *   kind 的 paused/checking/error 三档兜底(与 views.py::state_kind 的非活跃三档一一对应,
 *   宁可漏放不误拦)。
 *   moving 是反向的一例: 它自成第 7 档, **看 kind 判得出来**, 但它同样不在后端任何 state_enum
 *   谓词集合里 ⇒ 后端仍必须按 state 串判(见 commands.py 同名表)。 */
const REANNOUNCE_BLOCKED_STATES = {
  pausedDL: "种子暂停", pausedUP: "种子暂停",
  stoppedDL: "种子已停止", stoppedUP: "种子已停止",
  queuedDL: "种子排队", queuedUP: "种子排队",
  checkingDL: "种子校验", checkingUP: "种子校验", checkingResumeData: "种子校验",
  error: "种子错误", missingFiles: "丢失文件",
  // 搬迁中: qB 处在 moving 期间所有 peer 传输都会让位给磁盘搬运(libtorrent 行为), 汇报出去
  // 也换不回 peer; 且项目自己的搬迁模块把 moving 成员当禁区(relocate_units.py GATE_MOVING)。
  moving: "种子搬迁中",
};
const REANNOUNCE_BLOCKED_KINDS = { paused: "种子暂停", checking: "种子校验", error: "种子错误", moving: "种子搬迁中" };

window.AQB_DECORATE = {
  methods: {
    /* ------------------------------------------- 迁移可见性 P1(plan 26-11-04-1042)
     * 行内展示(relocateView)/ 筛选桶 / 详情段的**唯一**展示口径。数据一律来自后端 P0 投影:
     * 组行读 g.relocate(后端聚合, 不取首成员推断), 种子行读 m.relocate。 */
    relocateStateText(state) {
      return RELOCATE_STATE_TEXT[state] || "未知状态";
    },
    relocateOriginText(origin) {
      return RELOCATE_ORIGIN_TEXT[origin] || (origin ? origin : "未知来源");
    },
    /* 行内迁移展示单点(plan 26-11-07-2344 S2): 路径列两排 A→B / 单排着色的**唯一**判定与口径,
     * 模板与后续悬停浮窗(relocate_pop.js)都只从这里取。输出 {mode, tone, a, b, label} 或 null:
     *   mode='pair' -> 两排(a=当前位置 src, b=目标位置 dst), tone 类挂 .rel-pair 整块着色;
     *   mode='one'  -> 单排回落(a/b 置空), label 挂状态词, tone 类只给路径文字着色 —— 不渲染
     *                  任何文字徽章(状态唯一载体 = 颜色);
     *   null        -> 无 relocate / done / cancelled —— 纯单排正常色, 不出「已完成」结论。
     * 组行(有 members)读 g.relocate(后端聚合, 不取首成员推断 —— P0 纪律); 种子行读 m.relocate。
     * 两排判定: 组级 src 非空且 dst 恰 1 个 -> pair(a=src, b=dst[0]); mixed 恒单排(组内多任务
     * 状态不一致, 一对路径表达不了); 种子行 src/dst 均非空 -> pair, 任一缺失 -> one。
     * 零导航点击(plan D9, R3 D16 修订): A/B 排路径 chip 可点 = 切换路径筛选(显示值即筛选值),
     * 仍不开抽屉/链浮窗; 本方法本身不携带任何行为, 点击行为在模板层。 */
    relocateView(row) {
      const rel = row && row.relocate;
      if (!rel) return null;
      const tone = RELOCATE_TONE[rel.state];
      if (!tone) return null;
      const isGroup = !!row.members;
      let pair;
      if (isGroup) {
        pair = rel.state !== "mixed" && !!rel.src && Array.isArray(rel.dst) && rel.dst.length === 1;
      } else {
        pair = !!(rel.src && rel.dst);
      }
      if (!pair) {
        return { mode: "one", tone, a: null, b: null, label: RELOCATE_STATE_TEXT[rel.state] || null };
      }
      return { mode: "pair", tone, a: rel.src, b: isGroup ? rel.dst[0] : rel.dst, label: null };
    },
    /* 迁移筛选桶(成员级): 进行中三态 + 「有过迁移」(done/cancelled 也计入历史, 行内不着色) */
    _relocatePick(r) {
      const rel = r && r.relocate;
      if (!rel) return [];
      const out = [];
      if (rel.state !== "done" && rel.state !== "cancelled" && rel.state !== "mixed") {
        const label = RELOCATE_STATE_TEXT[rel.state];
        if (label) out.push(label);
      }
      out.push(RELOCATE_FILTER_ANY);
      return out;
    },
    /* 组级筛选桶: 组内任一成员落某档即保留整组(与 _hrBuckets 同语义) */
    _relocateBuckets(row) {
      const out = [];
      for (const r of row.members || [row]) {
        for (const b of this._relocatePick(r)) if (!out.includes(b)) out.push(b);
      }
      return out;
    },
    /* 路径筛选位置集(plan 26-11-07-2344 R3 D17): 路径筛选的匹配与选项计数的**同一单点** ——
     * save_path 恒参与; 进行中三态(moving/pending_finalize/failed)的迁移标注把 src/dst 并入
     * 「保存位置」(D16: 行内 A/B 排路径 chip 点击筛的就是这个口径, 不新增筛选维度);
     * done/cancelled 的历史 src/dst 不参与 —— 迁移完成即回落纯 save_path(该行不再命中
     * 迁移期点出的 src/dst 值, 是 D17 active 边界的既定推论)。消费点四四处: filters.js
     * _facetPick(选项计数)/组级谓词/虚拟行谓词 + hr.js _memberPass, 全部走本方法, 禁止
     * 各自再写 save_path 判断(漂移 = 计数里存在的值筛不出来, R5#36 同源教训)。 */
    _pathPositions(r) {
      const out = [(r && r.save_path) || ""];
      const rel = r && r.relocate;
      if (rel && RELOCATE_ACTIVE_STATES.has(rel.state)) {
        if (rel.src && !out.includes(rel.src)) out.push(rel.src);
        for (const d of Array.isArray(rel.dst) ? rel.dst : [rel.dst]) {
          if (d && !out.includes(d)) out.push(d);
        }
      }
      return out;
    },
    /* ------------------------------------------- 组级"共同值"计算(组级标签/分类列)
     *
     * 后端只透出成员原始值, 共同值(交集/一致值)在**前端**计算: 这类派生展示数据不参与
     * 后端视图重建判定, 且 computed 缓存后可复用, 无需让后端每轮做集合运算。
     */
    /* 组状态聚合口径(**单点**): 按 STATE_RANK 取"最该被看到"的成员状态 + 计数文案。
     *
     * `decoratedGroups` 与组行乐观补丁共用这一份 —— 两处各写一套必然漂移, 那就会出现
     * "点了暂停, 乐观算出的颜色和真值算出来的不一样"的抖动(见 STATE_RANK 注释)。
     */
    _aggStatus(members) {
      const counts = {};
      for (const m of members || []) counts[m.kind] = (counts[m.kind] || 0) + 1;
      const present = Object.keys(counts).sort((a, b) => this._rank(a) - this._rank(b));
      return {
        primary: present[0] || "other",
        // 计数文案按同一优先级排(与主色同序, 避免"颜色说 A、文案先说 B")
        text: present.map((k) => `${this.kindText(k)} ${counts[k]}`).join(" · "),
      };
    },
    /* kind -> 优先级数值(表里没有的 kind 排最后, 与后端 `_SHOW_STATE_RANK.get(k, 9)` 同口径) */
    _rank(kind) {
      return STATE_RANK[kind] === undefined ? STATE_RANK_LAST : STATE_RANK[kind];
    },
    /* 一组种子按同一张表聚合出的状态(供集行乐观补丁用: 与后端 e.state 同口径) */
    _aggKind(members) {
      let best = null;
      for (const m of members || []) {
        if (!m) continue;
        if (best === null || this._rank(m.kind) < this._rank(best)) best = m.kind;
      }
      return best;
    },
    _commonTags(members) {
      const sets = members.map((m) => new Set(m.tags || []));
      if (!sets.length) return { list: [], diff: false };
      const first = sets[0];
      let common = [...first];
      for (const s of sets.slice(1)) common = common.filter((t) => s.has(t));
      // 与站点名一致的标签(忽略大小写, 多为辅种工具自动打的"站点身份"标签)不展示: 站点列已有同名值, 纯冗余
      common = this._filterSiteTags(common, members);
      common.sort();
      // ± = 成员标签集合不完全相同(组级只显示共同标签, 差异提示避免误读为"全组一致")
      const diff = sets.some((s) => s.size !== first.size || [...s].some((t) => !first.has(t)));
      return { list: common, diff };
    },
    /* 过滤与成员站点名一致(忽略大小写)的标签 —— 组级共同标签与明细行共用 */
    _filterSiteTags(tags, members) {
      const names = new Set((members || []).map((m) => (m.site || "").toLowerCase()).filter(Boolean));
      return (tags || []).filter((t) => !names.has(t.toLowerCase()));
    },
    /* 明细行标签: 先滤掉与站点名一致的标签再展示(折叠计数/悬浮 title 口径一致) */
    mTags(m) {
      return this._filterSiteTags(m.tags, [m]);
    },
    /* 站点配色已改回状态色(2026-09-15, 字体与背景都表示种子状态): 原 siteHue djb2 函数与 .sc-0..7 一起删除, 站点身份由 chip 文字表达 */
    /* 站点专属配色已移除(2026-09-15 用户要求回退): 字体与背景都用状态色, 原 siteHue djb2
     * 哈希机制与 .sc-0..7 一起删除, 站点身份由 chip 文字表达(见 memory-bank/pitfalls.md 回写) */
    _commonCategory(members) {
      const vals = members.map((m) => m.category || "");
      if (!vals.length) return { value: "", diff: false };
      const diff = vals.some((v) => v !== vals[0]);
      return { value: diff ? "" : vals[0], diff };
    },
    kindText(kind) {
      // moving = 搬迁中(qB 原始 state "moving"); allocating 与它合流见 views.py::state_kind
      return {
        seeding: "做种", downloading: "下载", checking: "校验", paused: "暂停",
        error: "错误", moving: "移动中", other: "其他",
      }[kind] || kind;
    },
    /* 单种子状态文案: 错误状态优先显示**后端算好的具体原因**(error_reason: "文件丢失" /
     * tracker 报错原文), 其余状态回落 kindText。原因文本一律由后端给出(取数单点), 前端不得
     * 按 state 猜原因。kindText 仍用于状态图例/筛选器/组级与集级聚合文案 —— 那里没有
     * "某一种子的原因"可言。 */
    stateText(m) {
      if (!m || !m.kind) return "";
      if (m.kind === "error" && m.error_reason) return m.error_reason;
      return this.kindText(m.kind);
    },
    kindIcon(kind) {
      // 状态图标(与 sprite symbol 一一对应): 校验用 i-pulse(配合 CSS 呼吸动画, 语义=进行中);
      // moving 复用 i-pulse —— 同为"进行中"语义, 且不新增 symbol(三份 index.html 的 sprite
      // 必须逐字相等, 由 tests 静态守阵机械比对)
      return {
        seeding: "#i-upload", downloading: "#i-download", checking: "#i-pulse",
        paused: "#i-pause", error: "#i-warn", moving: "#i-pulse", other: "#i-info",
      }[kind] || "#i-info";
    },
    /* HR 标签分类色(与后端 WebviewMixin._hr_view_tags 对应)
     *
     * pending = 已触发 HR 条件但尚未满足做种时间/分享率(需关注, 用最鲜亮的颜色);
     * done    = 已满足(可以放宽, 用另一组镇静的颜色)。判定依据是后端解析后的标签文本
     * (已展开 ${required_seeding_time} 变量), 因此与真正写入 qB 的标签逐字相等。
     * 组级列展示的是"共同标签"——若某标签全组共有, 则组内 HR 状态必然一致, 故用代表成员即可。
     */
    tagClass(tag, member) {
      if (!member) return "";
      if (member.hr_tag && tag === member.hr_tag) return "hr-pending";
      if (member.hr_tag_done && tag === member.hr_tag_done) return "hr-done";
      return "";
    },
    /* ---------------- 强制重新汇报可用性(qB 口径, 单点判定) ----------------
     * 判据表见文件顶部 REANNOUNCE_BLOCKED_STATES。四个消费面共用这一份:
     *   右键菜单(ctx-menus.html 四支)/ 键盘 shortcuts.js _kbAct / 动作层 commands.js _actCore /
     *   详情面板 tracker 页签的重报钮(drawer_tpl 04/05/06 + drawer.js torrentCmd)。
     * 多目标与 qB 的 `oneCanForceReannounce` 同口径: **任一目标活跃即可用**(不是"全部活跃")。
     */
    reannounceBlocked(m) {
      const st = m && m.state;
      if (st && REANNOUNCE_BLOCKED_STATES[st]) return true;
      return !!(m && REANNOUNCE_BLOCKED_KINDS[m.kind]);  // state 缺失兜底(见顶部注释)
    },
    reannounceBlockText(m) {
      const st = m && m.state;
      return (st && REANNOUNCE_BLOCKED_STATES[st]) || (m && REANNOUNCE_BLOCKED_KINDS[m.kind]) || "非活跃";
    },
    /* 目标解析: {keys(组 key), hashes} -> 去重后的种子行(判定只读 state/kind 两字段) */
    _reannounceRows(t) {
      const rows = [];
      const seen = new Set();
      const push = (r) => { if (r && r.hash && !seen.has(r.hash)) { seen.add(r.hash); rows.push(r); } };
      for (const k of (t && t.keys) || []) {
        const g = this._findGroup(k);
        for (const m of (g && g.members) || []) push(m);
      }
      for (const h of (t && t.hashes) || []) push(this.memberByHash.get(h));
      return rows;
    },
    /* 行集合 -> {ok, title}(title 仅在 !ok 时非空, 供置灰项/钮的 title 提示原因) */
    _reannounceVerdict(rows) {
      /* 目标解析不出(行已消失/虚拟行): 不误拦 —— 与判定上线前行为一致(命令照发, 后端自有回执) */
      if (!rows.length || rows.some((r) => !this.reannounceBlocked(r))) return { ok: true, title: "" };
      return {
        ok: false,
        title: rows.length === 1
          ? `${this.reannounceBlockText(rows[0])}，无法强制重新汇报`
          : `全部 ${rows.length} 个目标均非活跃(暂停/停止/排队/校验/错误)，无法强制重新汇报`,
      };
    },
    reannounceTargetsGate(t) {
      return this._reannounceVerdict(this._reannounceRows(t));
    },
    /* 目标集合 -> **投递计划**(放行后的活跃子集, 单点): 与 qB 的"真实效果"对齐。
     *
     * qB 的 GUI 把整个选中集合交给引擎, 引擎(libtorrent)对暂停/排队种子空转 —— 于是"真正
     * 被汇报的"只有活跃的那几个。本项目把这一步**前移成投递收敛**: 非活跃目标既不发请求,
     * 也不进 tracker 确认跟踪。不收的代价是实打实的 —— 确认层会为这些"投递了但引擎空转"
     * 的目标白等到 item deadline(最长 600s), 最后落「未确认」, 把一次干净的成功报成部分失败。
     *
     * 解析面与闸门**同源**(_findGroup / memberByHash), 保证"判过的集合"与"发的集合"恒一致:
     *   组 key 解析不出 -> 原样交回组端点(后端有显式回执, 置灰与命令照发不冲突);
     *   hash 解析不出   -> 照发(与 _reannounceVerdict 的「不误拦」同口径, 由 qB 回执定论)。
     * 返回 {keys, hashes, skipped}: keys/hashes = 实际投递目标; skipped = 收敛掉的非活跃数。 */
    reannouncePlan(t) {
      const keys = [];
      const hashes = [];
      const seen = new Set();
      let skipped = 0;
      for (const k of (t && t.keys) || []) {
        const g = this._findGroup(k);
        if (!g) { keys.push(k); continue; }
        for (const m of g.members || []) {
          if (!m || !m.hash || seen.has(m.hash)) continue;
          seen.add(m.hash);
          if (this.reannounceBlocked(m)) { skipped += 1; continue; }
          hashes.push(m.hash);
        }
      }
      for (const h of (t && t.hashes) || []) {
        if (!h || seen.has(h)) continue;
        seen.add(h);
        const row = this.memberByHash.get(h);
        if (row && this.reannounceBlocked(row)) { skipped += 1; continue; }
        hashes.push(h);
      }
      return { keys, hashes, skipped };
    },
    /* 右键菜单当前目标的可用性(模板 :class / :title 用)。分支判据与 menu.js::ctxMenuKind()
     * **同序** —— menu.multi 优先级最高(menu.js _ctxMulti 与 shows.js 两个入口都会
     * 同时置 multi 与 episode/hash, ctxMenuKind() 先判 multi, 故这里也必须先判 multi)。 */
    reannounceMenuGate() {
      const m = this.menu || {};
      let t = null;
      if (m.multi) { const b = this._bulkTargets(); t = { keys: b.groupKeys, hashes: b.memberHashes }; }
      else if (m.episode) t = { keys: [], hashes: m.episode.hashes || [] };
      else if (m.hash) t = { keys: [], hashes: [m.hash] };
      else if (m.key) t = { keys: [m.key], hashes: [] };
      return t ? this.reannounceTargetsGate(t) : { ok: true, title: "" };
    },
    /* 详情面板(抽屉)当前种子的可用性(tracker 页签重报钮用): 目标 = drawer.hash。
     * !软切换(FX-29)期间 drawer.detail 仍是**上一个**目标的数据, 只在 detail.hash 与当前
     *   hash 一致时才采信它; 否则回落视图行(memberByHash 随视图刷新, 恒对当前目标)。 */
    drawerReannounceGate() {
      const d = this.drawer || {};
      if (!d.hash) return { ok: true, title: "" };
      const det = d.detail && d.detail.hash === d.hash ? d.detail : null;
      const row = det || this.memberByHash.get(d.hash);
      return this._reannounceVerdict(row ? [row] : []);
    },
  },
  computed: {
    /* 组级派生展示数据(依赖 groups, 仅在分组数据变化时算一次; 渲染多帧不重算):
     * 保存路径(筛选器)、状态摘要(图标+配色+计数)、共同标签/分类(含差异标记)、大小一致性
     *
     * 交集/共同值在**前端**计算: 后端只透出成员原始值, 避免每次视图重建做集合运算。
     */
    decoratedGroups() {
      return this.groups.map((g) => {
        // S7: 未脏行(引用稳定 + 指纹一致)复用已装饰结果; 脏行/原地变更(指纹失配)重算
        // (键=行对象, 失效=输入指纹, 见文件头 _decoCache 注)。返回结构形状逐一不变
        // (键集/字段与无记忆化完全一致), 消费方 sort.js sortedGroups / filters.js /
        // selection.js 不感知 —— 记忆化若改形状即踩 computed 静默白屏坑
        // (pitfalls/web-ui/vue-reactivity.md)。
        const hit = _decoCache.get(g);
        if (hit && _decoFpHit(g, hit.fp)) return hit.deco;
        const deco = {
          ...g,
          save_path: (g.members[0] && g.members[0].save_path) || "",
          status: this._aggStatus(g.members),
          commonTags: this._commonTags(g.members),
          commonCategory: this._commonCategory(g.members),
          sizeMismatch: new Set(g.members.map((m) => m.size)).size > 1,
        };
        _decoCache.set(g, { fp: _decoFpBuild(g), deco });
        return deco;
      });
    },
    totalTorrents() {
      // 种子页数据源到位后直接取平铺数组长度(权威口径); 旧响应缺 torrents 时回退 分组+未归组 合计
      if (this.torrents.length) return this.torrents.length;
      return this.groups.reduce((n, g) => n + g.count, 0) + this.singles.length;
    },
    /* 状态栏速度合计: 只读服务端算好的标量(status.totals 随 status **恒回传**, 不参与
     * 视图分片与 rid 门控)。
     * !**不要改回对 groups 求和** —— groups 是按视图回传的(VIEW_ARRAYS: 种子页不回它),
     * 而状态栏是跨视图的常驻显示: 求和会让种子页恒显示 0(首屏即种子页, groups 一直是 [])
     * 或停在**冻结的旧值**(先开过辅种页再切过来), 且漏掉未归组单种子(singles, 实测
     * 少算 88.7%)。见 issue 26-09-20-1646。 */
    totalDl() {
      const t = this.status && this.status.totals;
      return t ? t.dlspeed : 0;
    },
    totalUl() {
      const t = this.status && this.status.totals;
      return t ? t.upspeed : 0;
    },
    /* 成员索引: groups ∪ singles = 全量种子(shows 明细只带 hash, 从这里取完整成员视图,
     * 避免响应体重复成员数据; bulkDelete 摘要计数同源于此) */
    memberByHash() {
      const map = new Map();
      for (const g of this.groups) for (const m of g.members) map.set(m.hash, m);
      for (const r of this.singles) if (!map.has(r.hash)) map.set(r.hash, r);
      for (const r of this.torrents) if (!map.has(r.hash)) map.set(r.hash, r);  // SEED_ITEM 全量(扩展展示字段在这份; magnet_uri 刻意不在 —— 按需取详情, 见 drawer.js copyTorrentInfo)
      return map;
    },
    /* 未识别折叠区: hash → 成员解析, 过同一套筛选/搜索, 按种子名排序 */
    unrecognizedTorrents() {
      const q = (this.searchQuery || "").trim().toLowerCase();
      const hits = this.searchHits;
      const out = [];
      for (const h of this.shows.unrecognized) {
        const m = this.memberByHash.get(h);
        if (!m) continue;
        if (!this._memberPass(m)) continue;
        if (q && !hits.has(h)) continue;
        out.push(m);
      }
      out.sort((a, b) => (a.name || "").localeCompare(b.name || ""));
      return out;
    },
  },
};
