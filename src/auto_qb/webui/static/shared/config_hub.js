/* auto-qb WEB UI 设置页 · 新版(Console Hub)逻辑层
 *
 * 与 config_editor.js / config_rules.js 同一范式: 一个 Vue 全局 mixin, 方法名统一 `hub` 前缀。
 * **不复制任何编辑能力** —— 增删改全部复用既有的 cfg* 方法(同一棵 YAML 树、同一套保存/脏检测),
 * 本文件只负责:
 *   ① Hub & Spoke 的视图状态(首页 / 分区二级页 / 面包屑);
 *   ② 把 schema 字段拆成「块 → 行」两层(取代旧页五种折叠容器);
 *   ③ 就近说明浮窗的内容与定位(富文案优先, 否则回退 schema 的 help / risk / default)。
 *
 * 版式与控件外观见 shared/console_hub.css(样张 05-console-hub 的原样复刻)。
 * 分组文案取自样张第 9 节「文案改写对照」—— 说它做了什么, 不说它叫什么。
 */

/* 分区文案: 每条回答「它管什么 / 现在什么状态」; 缺省回退 schema 的 label / help */
const HUB_GROUP_META = {
  basic: {
    // 标题用「常规」而非「连接 qBittorrent」: 本组除 qB 连接外还有运行节奏 / 数据目录 / WebUI / 日志 / 通知等常规项
    title: "常规",
    desc: "连上 qBittorrent 的 Web UI，再定好 auto-qb 自己的运行节奏、界面、日志和通知。",
    lede: "上半部分是连接 qBittorrent：把地址和登录信息填对，auto-qb 就能接管种子管理。下面是 auto-qb 自己的常规设置：多久检查一次、一轮最多干多少活、运行状态和日志存在哪个目录，以及 WebUI 的开关与监听、日志落盘和系统通知。每行末尾的「?」可以看这一项的完整说明。",
  },
  maintenance: {
    title: "自动化",
    desc: "种子加进来之后自动做什么：打标签、把辅种归组、检查文件是否还在。",
    lede: "种子加入之后自动做什么：打标签、把辅种归成一组、检查文件是否还在、清理没用的标签。每一项都是可选的。",
  },
  speed: {
    title: "限速",
    desc: "按累计流量自动调整 qB 的全局速度上限，防止超额。",
    lede: "按累计流量自动调整 qB 的全局速度上限。比如当月上传超过 500 GiB 之后自动降到 2 MiB/s，到下个月自动恢复。多条曲线同时命中时取最严的那条。",
  },
  trackers: {
    title: "站点",
    desc: "按 tracker 域名识别站点，再套用这个站点的标签、限速和 HR 规则。",
    lede: "用 tracker 域名判断种子来自哪个站点，然后套用这个站点的标签、限速和 HR 规则。没配置的站点完全不做任何管理。HR 在线核实的启用不在这里 —— 去「HR 在线核实」分区的站点接入卡片点选。",
  },
  rules: {
    title: "规则",
    desc: "「当满足条件时执行动作」的自动化规则，按规则集分组管理。",
    lede: "一条规则就是「当满足条件时，执行这些动作」。条件要全部满足才会执行，动作按从上到下的顺序执行。",
  },
  hr_check: {
    title: "HR 在线核实",
    desc: "部分站点只有一部分种子受 H&R 约束，且站点不提供逐种标记 —— 逐种子在线核实；启用方式：本分区站点接入卡片点选；页面地址/解析器等由内置站点档案自动处理；分区页尾附各站点取数现状。",
    lede: "有些站点只有一部分种子受 H&R 约束，而且站点不告诉你哪些是 —— 只能上站查。开启总开关后在下方「站点接入」卡片点选启用站点（零 URL/路径/参数填写，页面地址、解析器、下载路径、翻页参数由内置站点档案自动处理，只需站点域名能对上）；取数由浏览器扩展完成，cookie 不离开浏览器。页尾的「站点状态」展示各站点取到哪一步、数据多新、现在为什么不放行。",
  },
};

/* 富说明(样张第 4 节的五段结构: 它是什么 / 默认值 / 什么时候需要改 / 注意 / 容易和它搞混的)
 *
 * 键 = 去掉 `config.` 前缀后的配置路径。没写在这里的项回退到 schema 的 help / risk / default,
 * 一样能弹出五段浮窗(只是「什么时候需要改」与「容易和它搞混的」两节为空)。 */
const HUB_HELP = {
  "qbittorrent.port": {
    tags: ["必填", "整数 1–65535"],
    what: "qBittorrent 的 Web UI 监听在哪个端口。auto-qb 就是从这个端口去读种子、改种子的。",
    def: "8080",
    when: ["你在 qB 里把 Web UI 端口改过（以 qB 里显示的为准）。", "一台机器上跑多个 qB 实例，端口被占用。"],
    rel: [["常规 → 监听端口", "auto-qb 自己的界面端口，不是 qB 的"], ["常规 → 主机", "端口填对了但主机写错，一样连不上"]],
  },
  "web.host": {
    tags: ["字符串"],
    what: "auto-qb 的浏览器界面监听在哪个地址，决定「谁可以访问这个界面」。",
    def: "127.0.0.1",
    when: ["想从局域网里另一台设备（比如手机、NAS）打开这个界面。"],
    risk: "改成 0.0.0.0 会暴露给局域网。这个界面能暂停和删除种子，局域网里任何设备都能操作。",
    rel: [["常规 → 访问密钥", "对外暴露时密钥是唯一防线"], ["常规 → 跳过本地验证", "只对 127.0.0.1 生效，对外仍强制鉴权"]],
  },
  "main_tick": {
    tags: ["时间", "不能为 0"],
    what: "auto-qb 每隔多久把所有种子看一遍，并处理到期的任务。可以理解为「心跳」。",
    def: "2 秒",
    when: ["种子特别多、机器比较慢、感觉界面卡 —— 可以放宽到 5 秒。", "想让自动化更即时 —— 可以缩到 1 秒，但别填 0。"],
    rel: [["每轮最大任务数", "两者共同决定一轮的耗时"], ["内置任务间隔", "比心跳更慢的周期任务"]],
  },
  "global_speed_limit_curve": {
    tags: ["可选"],
    what: "让 auto-qb 盯着 Traffic Monitor 记录的累计流量，跨过一档阈值就把全局限速降到该档的数值。",
    def: "（未启用）",
    when: ["站点有流量考核、超额会被处罚。", "想在夜间或月末自动省带宽。"],
    rel: [["站点 → 上传限速", "只管单个站点的种子"], ["每轮最大任务数", "无关，别看混"]],
  },
  "hr_check.allow_window": {
    tags: ["时间窗", "可留空"],
    what: "只在设定的时段去站点取数；留空 = 全天都可以。",
    def: "（全天）",
    when: ["站点对夜间访问敏感，想避开高峰。", "自己常在白天用网，取数挑凌晨做。"],
    rel: [
      ["常规 → 免打扰时段", "❗语义正好相反：那个是「这段时间不要发通知」，本项是「只在这段时间取数」"],
      ["HR 在线核实 → 请求最小间隔", "两者一起决定对站点的访问频度"],
    ],
  },
  "hr_check.unknown_policy": {
    tags: ["枚举", "改动有风险"],
    what: "「还没核实过」的种子怎么算：按 H&R 管束（保守），还是按普通种子放行。",
    def: "hr（保守）",
    when: ["站点数据长期取不到，又不想让全站种子都被当成 H&R —— 改 not-hr 前先想清楚代价。"],
    risk: "改成 not-hr 等于自愿放弃一重保底：首刷未完成、刷新不完备、通道静默期间，真正欠 H&R 的种子会被当成普通种子放行。",
    rel: [["HR 在线核实 → 放行有效期", "另一个影响漏管窗口的旋钮"], ["站点 → HR 规则", "受管束的种子具体打什么标签、要求多久"]],
  },
};

/* 语义化语调(样张第 7 节): 重要 = 影响面大但可逆, 危险 = 破坏性 / 不可逆 / 有安全后果 */
const HUB_TONE = {
  "qbittorrent.password": "danger",
  "web.host": "danger",
  "web.token": "important",
  "data_dir": "important",
  "web.skip_local_verify": "important",
};

/* 分区「是否启用」判定: 未启用 -> LED 灰(不抢注意力), 由各处主开关决定
 * (web/notify 已并入 basic, 无独立卡片也就不再各自判 off —— basic 恒为核心分区) */
const HUB_OFF_KEYS = {
  maintenance: ["config", "grouping", "enabled"],
  hr_check: ["config", "hr_check", "enabled"],
};

/* 站点搜索(计划 26-09-27-1852): 键 -> 字段组(chip 上的中文标签), 不在表里的键不搜
 * (remove_similar_tags 是布尔无可读文本; hr_check 是旧键, 值以 HR 档案为准) */
const TRACKER_FIELD_GROUPS = {
  domains: "域名",
  tags: "标签",
  groups: "分组",
  remove_tags: "删标",
  rules: "规则",
  upload_speed_limit: "上传限速",
  download_speed_limit: "下载限速",
  hr: "HR",
};
/* 命中 chip 的展示顺序: 名称 -> 标签 -> 域名 -> 分组 -> 删标 / 规则 / 限速 / HR */
const TRACKER_CHIP_ORDER = { 名称: 0, 标签: 1, 域名: 2, 分组: 3, 删标: 4, 规则: 5, 上传限速: 6, 下载限速: 7, HR: 8 };
/* 掩码哨兵: R 级值在树里以 ******** 出现, 不能当可搜内容(防未来站点下新增敏感键) */
const TRACKER_MASK = "********";

/* 设置分区初值(持久化用户偏好): 刷新后回到上次看的分区, 而不是设置首页 ——
 * 只把顶层 page 持久化的话, 在「设置 → 站点」按 F5 会落到设置首页, 位置照样丢一半。
 * 这里只**取值**; 合法性等 schema 到手后由 hubRestore() 校验(分区 key 由 schema 定义,
 * 模块加载时读不到, 且升级后可能改名/删除)。 */
function initialHubView() {
  try {
    return localStorage.getItem("autoqb.ui.hub") || "hub";
  } catch {
    return "hub";
  }
}

window.CONFIG_HUB = {
  data() {
    return {
      hub: {
        view: initialHubView(),  // "hub" | 分组 key(持久化, 见 initialHubView; 旧版 "__logs" 由 hubRestore 映射进 basic)
        query: "",         // 首页搜索框
        help: null,        // 浮窗内容 { t, k, tags, what, def, when, risk, rel }
        helpKey: "",       // 当前打开的浮窗对应的字段路径(再点一次 = 关闭)
        pop: { left: 0, top: 0 },
        arrow: { left: 0, top: 0, place: "left" },
        focusKey: "",      // 搜索跳转后要高亮的行
      },
    };
  },
  watch: {
    /* 分区切换即用户意图, 落盘后才经得起 F5(与顶层 page 同口径, 见 app.js persistUiPage)。
     * 写入失败(隐私模式/配额满)只影响刷新后的落点, 不该打断导航 —— 故吞掉异常。 */
    "hub.view"(v) {
      try {
        localStorage.setItem("autoqb.ui.hub", v || "hub");
      } catch { /* 写入失败: 本轮仍生效, 刷新后回设置首页 */ }
    },
    /* 仅一个命中 -> 直接选中(计划 §05): 搜索结果唯一时右栏立即出该站详情, 省一次点击。
     * hits 不依赖 trackerKey, 此处回写不会成环 */
    "hubTrackerHits.hits"(hits) {
      if (hits && hits.length === 1) this.cfg.trackerKey = hits[0].name;
    },
  },
  computed: {
    /* 首页卡片: 图标 + 标题 + 一句人话描述 + LED 状态 + 读数徽标 */
    hubCards() {
      if (!this.cfg.schema || !this.cfg.tree) return [];
      const cards = this.cfg.schema.groups.map((g) => {
        const meta = HUB_GROUP_META[g.key] || {};
        return {
          key: g.key,
          icon: g.icon || "i-settings",
          title: meta.title || g.label,
          label: g.label,
          desc: meta.desc || g.help || "",
          lede: meta.lede || g.help || "",
          led: this.hubLedOf(g.key),
          readout: this.hubReadout(g.key),
          badges: this.hubBadges(g.key),
        };
      });
      // 运行日志不再单列首页卡(2026-09-26 并入「常规」分区页尾, 随分区模板渲染);
      // HR 站点状态同理(2026-09-25 合并): 它是只读现状不是配置项,
      // 并进「HR 在线核实」分区页尾, 打开分区时随 hubGo 拉一次 /api/hr/status。
      return cards;
    },
    /* 等宽读数: 「N 个分区 · 共 M 项 · K 项尚未保存」 */
    hubStats() {
      return { groups: this.hubCards.length, fields: this.hubFieldCount(), dirty: this.cfgDirty };
    },
    /* 建议先看一眼的: 已配置且带 risk 的项 + 含风险动作的规则 */
    hubRiskList() {
      if (!this.cfg.schema || !this.cfg.tree) return [];
      const out = [];
      for (const g of this.cfg.schema.groups) {
        this.hubCollectRisk(this.cfgFlatten(g.fields, ["config"], 0), g, out);
      }
      for (const gk of this.cfgRuleGroupNames()) {
        for (const rn of this.cfgRuleNames(gk)) {
          const risk = this.cfgRuleRisk(gk, rn);
          if (risk) out.push({ group: "rules", groupLabel: "规则", label: `${gk} / ${rn}`, risk: risk });
        }
      }
      return out.slice(0, 8);
    },
    /* 当前二级页的分区元信息 */
    hubNow() {
      const schema = this.cfg.schema;
      if (!schema) return { key: "", title: "", lede: "", icon: "i-settings" };
      const g = schema.groups.find((x) => x.key === this.hub.view);
      if (!g) return { key: "", title: "", lede: "", icon: "i-settings" };
      const meta = HUB_GROUP_META[g.key] || {};
      return { key: g.key, label: g.label, icon: g.icon || "i-settings", title: meta.title || g.label, lede: meta.lede || g.help || "" };
    },
    /* 当前分区的「块 → 行」(站点/规则/限速三个专段不走这里, 模板里单独渲染) */
    hubBlocks() {
      const schema = this.cfg.schema;
      if (!schema || !this.cfg.tree || this.hub.view === "hub") return [];
      const g = schema.groups.find((x) => x.key === this.hub.view);
      if (!g) return [];
      const blocks = [];
      const root = { key: "__root", label: "常规", help: "", rows: [], section: false };
      let rootUsed = false;
      const walk = (list, target) => {
        for (const it of list || []) {
          if (it.type === "field") {
            if (!rootUsed && target === root) rootUsed = true;
            target.rows.push(it);
            continue;
          }
          // hr_check.sites 不走通用分区块渲染: 它的键是内置站点档案 id(来自 constants 而非
          // 配置里已存在的键), 通用行组装写不出正确路径 —— 由 hr_check 模板分支的「站点接入」
          // 卡片单独渲染(计划 26-09-27-1318 §5)
          if (this.hubKey(it.path) === "config.hr_check.sites") continue;
          const b = {
            key: this.hubKey(it.path),
            label: it.label || (it.field && it.field.label) || "相关设置",
            help: (it.field && it.field.help) || "",
            risk: (it.field && it.field.risk) || "",
            section: it.type === "section",
            item: it,
            rows: [],
          };
          blocks.push(b);
          walk(it.items || [], b);
        }
      };
      walk(this.cfgFlatten(g.fields, ["config"], 0), root);
      return rootUsed ? [root].concat(blocks) : blocks;
    },
    /* 搜索: 按配置项名直跳(不用记它在哪个分区)。
     * 递归进 object 段(块)内部找叶子字段 —— 2026-09-28 起日志/WebUI/通知在「常规」页各自成块,
     * 其字段不再是 cfgFlatten 的顶层项 */
    hubHits() {
      const q = (this.hub.query || "").trim().toLowerCase();
      if (!q || !this.cfg.schema || !this.cfg.tree) return [];
      const out = [];
      const collect = (items, g, meta) => {
        for (const it of items || []) {
          if (it.type !== "field") {
            collect(it.items, g, meta);
            continue;
          }
          const f = it.field;
          const hay = `${f.label} ${f.key} ${f.help || ""}`.toLowerCase();
          if (hay.indexOf(q) < 0) continue;
          out.push({ key: this.hubKey(it.path), label: f.label, group: g.key, groupLabel: meta.title || g.label });
          if (out.length >= 10) return;
        }
      };
      for (const g of this.cfg.schema.groups) {
        const meta = HUB_GROUP_META[g.key] || {};
        collect(this.cfgFlatten(g.fields, ["config"], 0), g, meta);
        if (out.length >= 10) break;
      }
      return out;
    },
    /* 站点搜索: 每站一组归一化行(名称行在最前)。cfg.tree 是响应式代理 —— 本计算属性遍历了
     * 每个站点条目的键与值, 编辑 / 增删站点 / 保存重载都会让它重算, 无需在 cfgLoad 上另行挂钩 */
    hubTrackerIndex() {
      const trackers = (this.cfgConfig() && this.cfgConfig().trackers) || {};
      return Object.keys(trackers).map((name) => ({ name, rows: this.trackerRows(name, trackers[name]) }));
    },
    /* 站点搜索主入口: { active, kind, hits, total }。
     * 匹配语义与种子搜索(views.py::search_torrents)同构: 负词任一行命中即整站排除(优先),
     * 正词逐词跨行 AND; 命中行收集成 chip(去重 + 组序 + 上限 3, 见 §05) */
    hubTrackerHits() {
      const q = String(this.cfg.trackerQuery || "");
      if (!q.trim()) return { active: false, kind: "", hits: [], total: this.cfgTrackerNames().length };
      const p = this.trackerParseQuery(q);
      if (p.negOnly) return { active: true, kind: "negOnly", hits: [], total: this.cfgTrackerNames().length };
      const hits = [];
      for (const site of this.hubTrackerIndex) {
        const rows = site.rows;
        if (p.neg.some((w) => rows.some((r) => r.n.indexOf(w) !== -1))) continue;
        if (p.pos.length && !p.pos.every((w) => rows.some((r) => r.n.indexOf(w) !== -1))) continue;
        const nameHit = p.pos.some((w) => rows[0].n.indexOf(w) !== -1);
        const chips = [];
        const seen = {};
        for (const r of rows.slice(1)) {
          if (!p.pos.some((w) => r.n.indexOf(w) !== -1)) continue;
          const k = r.grp + "|" + r.raw;
          if (seen[k]) continue;
          seen[k] = 1;
          chips.push({ grp: r.grp, raw: r.raw });
        }
        chips.sort((a, b) => (TRACKER_CHIP_ORDER[a.grp] ?? 9) - (TRACKER_CHIP_ORDER[b.grp] ?? 9));
        hits.push({ name: site.name, nameHit, chips: chips.slice(0, 3), more: Math.max(0, chips.length - 3) });
      }
      return { active: true, kind: "hits", hits, total: this.cfgTrackerNames().length };
    },
    hubTrackerActive() {
      return this.hubTrackerHits.active;
    },
    /* 右栏联动(§06): 左栏正在显示的站点必须是命中之一, 否则右栏出引导提示 */
    hubTrackerSelIn() {
      return this.hubTrackerHits.hits.some((h) => h.name === this.cfg.trackerKey);
    },
    hubTrackerCountText() {
      const r = this.hubTrackerHits;
      if (!r.active) return ""; // 无查询时不显示计数(§06)
      if (r.kind === "negOnly") return "只有排除词";
      return `命中 ${r.hits.length} / ${r.total} 个站点`;
    },
  },
  methods: {
    /* ---------------------------------------------------------- 视图跳转(首页 ↔ 二级页) */
    hubGo(key) {
      this.hubCloseHelp();
      this.cfg.trackerQuery = ""; // 离开分区即清空站点搜索, 不带残留状态(计划 §06)
      this.hub.view = key;
      if (key === "trackers" && !this.cfgTrackerNames().includes(this.cfg.trackerKey)) {
        const names = this.cfgTrackerNames();
        this.cfg.trackerKey = names.length ? names[0] : null;
      }
      if (key === "rules" && !this.cfgRuleGroupNames().includes(this.cfg.ruleGroupKey)) {
        const names = this.cfgRuleGroupNames();
        this.cfg.ruleGroupKey = names.length ? names[0] : null;
      }
      // 运行日志已并入「常规」分区页尾且默认折叠(2026-09-28): 首次展开才拉一次,
      // 之后手动刷新(不自动轮询); 分区打开本身不再预取
      if (key === "hr_check" && !this.hrs.loaded) this.loadHrStatus();
      window.scrollTo({ top: 0 });
    },
    hubBack() {
      this.hubCloseHelp();
      this.cfg.trackerQuery = ""; // 同 hubGo: 返回首页不带站点搜索残留
      this.hub.view = "hub";
      window.scrollTo({ top: 0 });
    },
    hubJump(hit) {
      this.hub.query = "";
      this.hub.view = hit.group;
      this.hub.focusKey = hit.key;
      this.$nextTick(() => {
        const el = document.querySelector(`[data-hb-key="${hit.key}"]`);
        if (el) el.scrollIntoView({ block: "center", behavior: "smooth" });
      });
    },
    /* 运行日志块(「常规」页尾): 默认折叠(2026-09-28 用户要求), 首次展开才拉一次 /api/log,
     * 之后手动刷新不轮询 —— 折叠态不预取, 省掉打开分区就背一次最多 2000 行 tail 的请求 */
    hubLogsToggle() {
      this.logs.open = !this.logs.open;
      if (this.logs.open && !this.logs.loaded) this.loadLogs();
    },
    /* 折叠态下动等级 / 行数 / 刷新 = 明确想看日志: 顺手展开再拉 */
    hubLogsLoad() {
      this.logs.open = true;
      this.loadLogs();
    },
    /* 从存储恢复的分区 key 必须**在 schema 里还认得出**才允许采用 —— schema 是模块级常量,
     * 版本升级后分区可能改名 / 删除, 不校验就会让刷新停在空白分区(且页面上没有任何提示)。
     * 采用时复用 hubGo: trackers / rules 的默认选中项与 HR 的懒加载都在那条路径里,
     * 自己重写一遍就会漏掉其中一半。由 cfgLoad 成功后调用(那一刻 schema 才到手)。 */
    hubRestore() {
      let v = this.hub.view;
      if (v === "__logs") v = "basic"; // 旧版「运行日志」分区已并入常规(2026-09-26), 存量偏好映射过去
      if (!v || v === "hub") return;
      const known = !!(this.cfg.schema && this.cfg.schema.groups.some((g) => g.key === v));
      if (!known) {
        this.hub.view = "hub";
        return;
      }
      this.hubGo(v);
    },
    hubKey(path) {
      return Array.isArray(path) ? path.join(".") : String(path);
    },
    /* schema 路径去掉 `config.` 前缀(富说明表与语调表都按这个键查) */
    hubBare(path) {
      const k = this.hubKey(path);
      return k.indexOf("config.") === 0 ? k.slice(7) : k;
    },

    /* ---------------------------------------------------------- 首页读数 / 状态 */
    hubFieldCount() {
      if (!this.cfg.schema) return 0;
      let n = 0;
      // 递归进 object 段(块)内部: 同 hubHits, 块内叶子字段不再是 cfgFlatten 顶层项(2026-09-28)
      const count = (items) => {
        for (const it of items || []) {
          if (it.type !== "field") count(it.items);
          else n += 1;
        }
      };
      for (const g of this.cfg.schema.groups) count(this.cfgFlatten(g.fields, ["config"], 0));
      return n;
    },
    hubLedOf(key) {
      if (key === "speed" && !this.cfgCurveEnabled()) return "off";
      if (key === "trackers" && !this.cfgTrackerNames().length) return "off";
      if (key === "rules" && !this.cfgRuleGroupNames().length) return "off";
      const offPath = HUB_OFF_KEYS[key];
      if (offPath && !this.cfgBool(offPath, "true")) return "off";
      if (key === "basic" && this.cfgText(["config", "web", "host"], "127.0.0.1") !== "127.0.0.1") return "warn";
      const risk = this.hubRiskList;
      if (risk.some((r) => r.group === key)) return "warn";
      return "ok";
    },
    hubReadout(key) {
      if (!this.cfg.tree) return "";
      switch (key) {
        case "basic":
          return `${this.cfgText(["config", "qbittorrent", "host"], "127.0.0.1")}:${this.cfgText(["config", "qbittorrent", "port"], "8080")}`;
        case "maintenance":
          return this.cfgBool(["config", "grouping", "enabled"], "true") ? "辅种分组已启用" : "辅种分组未启用";
        case "hr_check": {
          // 站点接入卡片(hr_check.sites)的启用数(v3: 条目 enabled 布尔); 旧键 trackers.*.hr_check
          // 已随 schema v2 废除(迁移链自动改写), 不再计数
          const enabled = Object.entries(this.hrSiteEntries()).filter(([id, e]) => {
            if (!e) return false;
            const v = e.enabled;
            return typeof v === "boolean" ? v : ["true", "1", "yes", "on"].includes(String(v).trim().toLowerCase());
          }).length;
          return enabled ? `${enabled} 个站点在线核实` : "未配置站点";
        }
        case "speed": {
          if (!this.cfgCurveEnabled()) return "未启用";
          const list = this.cfgCurveList();
          return list.length ? `${list.length} 条 · ${this.cfgCurvePeriod(0).period || "—"}` : "未配置曲线";
        }
        case "trackers": {
          const names = this.cfgTrackerNames();
          return names.length ? names.slice(0, 3).join(" / ") : "未配置";
        }
        case "rules": {
          const gk = this.cfgRuleGroupNames();
          let n = 0;
          for (const k of gk) n += this.cfgRuleNames(k).length;
          return `${gk.length} 个规则集 · ${n} 条`;
        }
        default:
          return "";
      }
    },
    hubBadges(key) {
      const out = [];
      if (key === "trackers") out.push({ text: `${this.cfgTrackerNames().length} 个`, cls: "" });
      else if (key === "rules") {
        const risky = this.hubRiskList.filter((r) => r.group === "rules").length;
        out.push({ text: `${this.cfgRuleGroupNames().length} 个规则集`, cls: "" });
        if (risky) out.push({ text: `${risky} 条含风险`, cls: "risk" });
      } else if (key === "speed" && this.cfgCurveEnabled()) {
        out.push({ text: `${this.cfgCurvePoints(0, "upload_curve").length} 档`, cls: "" });
      } else if (key === "maintenance" && !this.cfgBool(["config", "add_episode_tags", "enabled"], "false")) {
        out.push({ text: "集数标签未开", cls: "" });
      }
      return out;
    },
    /* 递归收集带 risk 且**已配置**的字段(未配置的不打扰) */
    hubCollectRisk(items, group, out) {
      const meta = HUB_GROUP_META[group.key] || {};
      for (const it of items || []) {
        if (it.type === "field") {
          if (it.field && it.field.risk && this.cfgExists(it.path)) {
            out.push({
              group: group.key,
              groupLabel: meta.title || group.label,
              label: it.field.label,
              risk: it.field.risk,
            });
          }
          continue;
        }
        this.hubCollectRisk(it.items || [], group, out);
      }
    },

    /* ---------------------------------------------------------- 站点接入卡片(计划 26-09-27-1318) */
    /* HR 在线核实分区的唯一启用入口: 卡片键集合来自 schema.constants.hr_check_site_presets
     * (内置站点档案, 与配置里已存在的键无关), 勾选启用即写 hr_check.sites.<id>.enabled(v3 布尔口径)。
     * 绑定状态由前端按映射制口径先行提示(计划 26-09-27-1930 §6: 显式 tracker 直取 > 档案已知
     * announce 域默认映射查表, 与后端同口径), fail-fast 仍由后端校验兜底 */
    hrSitePresets() {
      const c = this.cfg.schema && this.cfg.schema.constants;
      return (c && c.hr_check_site_presets) || [];
    },
    hrSiteEntries() {
      const v = this.cfgRaw(["config", "hr_check", "sites"]);
      return v && typeof v === "object" && !Array.isArray(v) ? v : {};
    },
    hrSiteEnabled(id) {
      const entry = this.hrSiteEntries()[id];
      if (!entry) return false;
      const v = entry.enabled;
      return typeof v === "boolean" ? v : ["true", "1", "yes", "on"].includes(String(v).trim().toLowerCase());
    },
    hrSiteSetEnabled(id, on) {
      if (!on && !this.cfgExists(["config", "hr_check", "sites", id])) return; // 未配置 = 本就关闭, 不写垃圾键
      this.cfgSetBool(["config", "hr_check", "sites", id, "enabled"], on);
    },
    /* 绑定状态(映射制, 计划 26-09-27-1930 §6): 返回 {text, cls}; cls = "warn" 表示保存后校验会报错。
     * web 域与 tracker 域永不互相比对 —— 自动绑定只在 announce 命名空间内查表(双向子域容错,
     * 与 site_presets.match_trackers 同口径); 显式 tracker 按条目名直取 */
    hrSiteBinding(preset) {
      const trackerDomain = String(preset.tracker_domain || "").trim().toLowerCase();
      const entry = this.hrSiteEntries()[preset.id];
      const explicit =
        entry && entry.tracker !== undefined && entry.tracker !== null ? String(entry.tracker).trim() : "";
      const names = this.cfgTrackerNames();
      if (explicit) {
        if (!names.includes(explicit)) {
          return { cls: "warn", text: `映射目标 ${explicit} 不存在 —— 保存后校验会报错` };
        }
        return { cls: "", text: `已映射: ${explicit}` };
      }
      const hits = names.filter((n) => {
        const ds = this.cfgRaw(["config", "trackers", n, "domains"]);
        return Array.isArray(ds) &&
          ds.some((d) => {
            const t = String(d).trim().toLowerCase();
            return t && (t === trackerDomain || t.endsWith("." + trackerDomain) || trackerDomain.endsWith("." + t));
          });
      });
      if (hits.length === 1) return { cls: "", text: `已自动绑定: ${hits[0]}（档案默认映射）` };
      if (hits.length > 1) return { cls: "warn", text: `默认映射歧义: ${hits.join("、")} 都命中 —— 请显式指定 tracker` };
      return {
        cls: "warn",
        text: `未绑定: 档案已知 announce 域(${trackerDomain})未命中任何站点配置 —— 请补域名或显式指定 tracker`,
      };
    },
    /* 微调字段表: 从 schema 里 hr_check -> sites 字段的子字段表取(数据驱动), enabled 已由卡片勾选承担 */
    hrSiteTuningFields() {
      const g = this.cfg.schema && this.cfg.schema.groups.find((x) => x.key === "hr_check");
      const root = g && (g.fields || []).find((f) => f.key === "hr_check");
      const sites = root && (root.fields || []).find((f) => f.key === "sites");
      return ((sites && sites.fields) || []).filter((f) => f.key !== "enabled");
    },
    /* 组装成 hub-field 组件可渲染的 item(路径指向具体档案条目) */
    hrSiteTuningItems(id) {
      return this.hrSiteTuningFields().map((f) => ({
        type: "field",
        field: f,
        path: ["config", "hr_check", "sites", id, f.key],
        depth: 1,
        owner: ["config", "hr_check", "sites", id],
        inline: [],
      }));
    },

    /* ---------------------------------------------------------- 就近说明浮窗 */
    /* 内容: 富文案优先, 否则由 schema 的 help / risk / default 拼出五段 */
    hubHelpOf(item) {
      const f = item.field || {};
      const bare = this.hubBare(item.path);
      const rich = HUB_HELP[bare];
      const tags = [];
      if (f.required) tags.push("必填");
      if (f.kind) tags.push(f.kind);
      if (rich && rich.tags && rich.tags.length) tags.length = 0;
      return {
        t: f.label || "说明",
        k: bare,
        tags: (rich && rich.tags) || tags,
        what: (rich && rich.what) || f.help || "这一项还没有说明。",
        def: (rich && rich.def) || this.hubDefaultText(f),
        when: (rich && rich.when) || [],
        risk: (rich && rich.risk) || f.risk || "",
        rel: (rich && rich.rel) || [],
      };
    },
    /* ⚠ 对象/数组型默认值(如 trackers / rules 的 default={}、channels 的 default=["platform"])不能
       直接进 cfgScalar —— String({}) 是 "[object Object]", 会在「?」说明浮窗的「默认值」一栏里
       原样显示给读者。空的一律归「（空）」, 非空对象按条目数给一句人话。 */
    hubDefaultText(field) {
      const d = field.default;
      if (d === null || d === undefined || d === "") return "（空）";
      if (Array.isArray(d)) return d.length ? d.join("、") : "（空）";
      if (typeof d === "object") {
        const n = Object.keys(d).length;
        return n ? `（对象: ${n} 项, 由子项决定）` : "（空）";
      }
      return this.cfgScalar(d);
    },
    hubAsk(item, ev) {
      const key = this.hubKey(item.path);
      if (this.hub.helpKey === key) {
        this.hubCloseHelp();
        return;
      }
      const btn = ev.currentTarget;
      const b = btn.getBoundingClientRect();
      this.hub.help = this.hubHelpOf(item);
      this.hub.helpKey = key;
      this.$nextTick(() => {
        const pop = this.$refs.hubPop;
        if (!pop) return;
        const pw = pop.offsetWidth;
        const ph = pop.offsetHeight;
        const gap = 10;
        let left = b.right + gap;
        let place = "left";
        if (left + pw > window.innerWidth - 12) {
          left = b.left - gap - pw;
          place = "right";
          if (left < 12) {
            left = Math.max(12, window.innerWidth - pw - 12);
            place = "left";
          }
        }
        let top = b.top - 6;
        if (top + ph > window.innerHeight - 12) top = window.innerHeight - ph - 12;
        if (top < 12) top = 12;
        this.hub.pop = { left: left, top: top };
        this.hub.arrow = {
          place: place,
          left: place === "left" ? left - 5 : left + pw - 4,
          top: Math.min(Math.max(b.top + b.height / 2 - 4, top + 10), top + ph - 18),
        };
      });
    },
    hubCloseHelp() {
      if (!this.hub.help) return;
      this.hub.help = null;
      this.hub.helpKey = "";
    },
    hubOnDocClick(e) {
      if (this.hub.help && !(e.target && e.target.closest && e.target.closest(".hb-pop"))) {
        this.hubCloseHelp();
      }
      /* 站点搜索「点外即收」(跳转器交互 2026-09-28): 收层一律清词 —— 浮层盖着详情,
       * 留词只会让下次点击又盖回来; 搜索行内点击(改词 / × / 计数)不算点外, 不收 */
      if (this.hub.view === "trackers" && this.hubTrackerActive &&
          !(e.target && e.target.closest && e.target.closest(".hb-tr-search"))) {
        this.cfg.trackerQuery = "";
      }
    },
    hubOnKey(e) {
      if (e.key !== "Escape") return;
      if (this.hub.help) {
        this.hubCloseHelp();
        return;
      }
      /* 站点搜索的退出路径(计划 §06 Q5): Esc 等效清空, 恢复全量 pill 列表 */
      if (this.hub.view === "trackers" && String(this.cfg.trackerQuery || "").trim()) {
        this.cfg.trackerQuery = "";
        return;
      }
      /* 设置二级页 Esc 返回首页(方案三 2026-09-28): 排在说明浮窗/站点搜索之后, 不抢既有职责;
       * lifecycle 的 Esc 关闭链还有层要关(escBusy, 名单在 dialogs.js)时本键归它 ——
       * 否则用户按 Esc 关弹窗会顺带把页面退回首页 */
      if (this.page === "settings" && this.hub.view !== "hub" && !this.escBusy()) this.hubBack();
    },

    /* ---------------------------------------------------------- 站点搜索(计划 26-09-27-1852)
     * 匹配函数收敛为前端单点: 一处 norm / 一处 parse / 一处 rows, 模板不散写。 */
    /* 归一化: 与 views.py::_search_norm 同语义(分隔符折叠为单空格 + 小写)。
     * ⚠ JS 必须用 [^\p{L}\p{N}](u 标志必带) —— ASCII \W 是 Unicode 语义的反面,
     * 会把整个中文词折成空格, 中文搜索直接废掉(拟记 pitfalls/web-ui) */
    trackerNorm(s) {
      return String(s).replace(/[^\p{L}\p{N}]+/gu, " ").toLowerCase().trim();
    },
    /* 站点 -> 归一化行(名称行恒在最前, 供名称命中判定)。序列化兜底口径(§03):
     * 字符串原样 / 列表逐项 / 数字 String() / 布尔跳过(无可读文本) / dict 递归到叶子 /
     * 掩码哨兵跳过 / 空串跳过(不出空 chip) */
    trackerRows(name, entry) {
      const rows = [{ grp: "名称", raw: name, n: this.trackerNorm(name) }];
      const walk = (v, grp) => {
        if (v === TRACKER_MASK) return;
        if (typeof v === "boolean") return;
        if (typeof v === "number") {
          rows.push({ grp, raw: String(v), n: this.trackerNorm(v) });
          return;
        }
        if (Array.isArray(v)) {
          v.forEach((x) => walk(x, grp));
          return;
        }
        if (v && typeof v === "object") {
          Object.keys(v).forEach((k) => walk(v[k], grp));
          return;
        }
        const raw = String(v === undefined || v === null ? "" : v);
        if (!raw.trim()) return;
        rows.push({ grp, raw, n: this.trackerNorm(raw) });
      };
      for (const k of Object.keys(entry || {})) {
        const grp = TRACKER_FIELD_GROUPS[k];
        if (grp) walk(entry[k], grp);
      }
      return rows;
    },
    /* 查询解析(照搬种子搜索语法, 用户零学习成本): 空格分词 = 隐式 AND / -词 = 排除 /
     * "短语" = 连续子串 / -"短语" = 排除短语; 宽容容错: 孤立 - 忽略, 未闭合引号收到行尾 */
    trackerParseQuery(q) {
      const pos = [];
      const neg = [];
      const re = /(-?)(?:"([^"]*)"|(\S+))/g;
      let m;
      while ((m = re.exec(String(q)))) {
        const term = m[2] !== undefined ? m[2] : m[3];
        if (!term) continue;
        const n = this.trackerNorm(term);
        if (!n) continue;
        (m[1] ? neg : pos).push(n);
      }
      return { pos, neg, negOnly: !pos.length && neg.length > 0 };
    },
    /* 点命中行(跳转器交互 2026-09-28): 选中即清词收层直达详情 —— 下拉盖着详情,
     * 只选中不清词会把切站效果留在浮层底下看不见(原「保留搜索」是分栏语境的拍板, 随下拉退役) */
    hubTrackerPick(name) {
      this.cfg.trackerKey = name;
      this.cfg.trackerQuery = "";
    },
    /* × 清空钮: 配合模板 @mousedown.prevent —— 阻止按钮抢焦点, 输入框保持聚焦可继续输入 */
    hubTrackerClear() {
      this.cfg.trackerQuery = "";
    },

    /* ---------------------------------------------------------- 行 / 控件辅助 */
    /* 语调单点: schema 的 tone 字段(破坏性/重要字段显式声明, 如 删标/彻底删标)优先,
     * 回落 HUB_TONE 静态表(动态路径进不去表的老键, 如 qbittorrent.password);
     * 行条纹(hubRowClass)与行内「?」按钮同一来源, 危险行整组走红 */
    hubToneOf(item) {
      return (item.field && item.field.tone) || HUB_TONE[this.hubBare(item.path)] || "";
    },
    hubRowClass(item) {
      const out = [];
      if (item.field && item.field.risk) out.push(this.hubToneOf(item) === "danger" ? "danger" : "risk");
      if (this.hub.focusKey && this.hub.focusKey === this.hubKey(item.path)) out.push("flash");
      return out.join(" ");
    },
    /* 数值/时间/大小/速度一律等宽(样张: 读数用 mono, 标题用 display) */
    hubMonoOf(item) {
      return ["int", "time", "size", "speed", "expr"].indexOf((item.field && item.field.kind) || "") >= 0;
    },
    /* 窄宽给数字, 宽给路径/表达式 —— 值是 300GiB / 8MiB/s 这种短串, 拉满整行既浪费又难扫 */
    hubWidthOf(item) {
      const k = (item.field && item.field.kind) || "";
      if (["int", "time", "size", "speed"].indexOf(k) >= 0) return "hb-w-sm";
      if (k === "path") return "hb-w-lg";
      return "";
    },
    /* 条件 / 动作一行人话: 插件名 + 简短取值 */
    hubPluginText(entry) {
      const meta = this.cfgPluginMeta(entry);
      if (!meta) return this.cfgPluginName(entry) || "—";
      const name = meta.label || this.cfgPluginName(entry);
      if (this.isIgnoreNext(entry)) return "忽略下一个动作的错误";
      const kind = meta.spec_kind;
      if (kind === "bool") return `${name}（${String(entry[meta.name]) === "true" ? "是" : "否"}）`;
      const raw = entry[meta.name];
      if (raw === undefined || raw === null || raw === "") return name;
      if (typeof raw === "object" && !Array.isArray(raw)) {
        const parts = Object.keys(raw).filter((k) => String(raw[k]) !== "");
        return parts.length ? `${name} · ${parts.slice(0, 2).join("/")}` : name;
      }
      const text = Array.isArray(raw) ? raw.join(", ") : String(raw);
      return text ? `${name} · ${text}` : name;
    },
    hubStepClass(entry) {
      const meta = this.cfgPluginMeta(entry);
      return meta && meta.risk ? "danger" : "";
    },

    /* ---------------------------------------------------------- 站点 / 规则集 / 规则 增删 */
    async hubAddTracker() {
      const name = await this.promptDialog("新增站点配置", "", { placeholder: "站点名(如 HHan)", okText: "添加" });
      if (name === null || name === undefined) return;
      const n = String(name).trim();
      if (!n) return;
      if (this.cfgTracker(n)) {
        this.toast(`站点 ${n} 已存在`, "error");
        return;
      }
      this.cfg.newTrackerName = n;
      this.cfgTrackerAdd();
    },
    async hubImportSites() {
      /* 一键导入缺失站点(对齐 CLI --export-yaml --only-missing): 后端只读扫描,
       * 条目填入编辑器待审 —— 示例值不未经审阅生效, 保存走既有 cfgSave 路径 */
      if (this.hub.importing) return;
      this.hub.importing = true;
      try {
        const res = await this.api("/api/sites/missing");
        const sites = res.sites || [];
        if (!sites.length) {
          this.toast("没有发现未配置的站点", "ok");
          return;
        }
        const list = sites.map((s) => `${s.name}(${s.domain})`).join("、");
        const ok = await this.confirmDialog(
          `导入 ${sites.length} 个缺失站点`,
          `将按默认配置填入编辑器: ${list}。默认限速为不限、HR 为示例值 —— 保存前请在编辑器中核对。`,
          { okText: "导入" }
        );
        if (!ok) return;
        const trackers = { ...(this.cfgConfig().trackers || {}) };
        let added = 0;
        for (const s of sites) {
          if (trackers[s.name]) continue; // 已存在同名键(如待生效热重载)不覆盖
          trackers[s.name] = s.entry;
          if (!added) this.cfg.trackerKey = s.name;
          added++;
        }
        if (!added) {
          this.toast("站点已存在, 没有可导入项", "error");
          return;
        }
        this.cfgSetPath([...this.cfgConfigPath(), "trackers"], trackers);
        this.toast(`已填入 ${added} 个站点, 核对后点「保存」生效`, "ok", 6000);
      } catch (e) {
        this.toast("导入失败: " + (e.message || "未知错误"), "error", 9000);
      } finally {
        this.hub.importing = false;
      }
    },
    async hubAddRuleGroup() {
      const name = await this.promptDialog("新增规则集", "", { placeholder: "规则集名(自动补 _rules)", okText: "添加" });
      if (name === null || name === undefined) return;
      const n = String(name).trim();
      if (!n) return;
      this.cfg.newRuleGroupName = n;
      this.cfgRuleAddGroup();
    },
    async hubAddRule(groupKey) {
      const name = await this.promptDialog("新增规则", "", { placeholder: "规则名(如 auto-skip-checking)", okText: "添加" });
      if (name === null || name === undefined) return;
      const n = String(name).trim();
      if (!n) return;
      this.cfg.newRuleName = n;
      this.cfgRuleAdd(groupKey);
    },
    hubPickPlugin(groupKey, ruleName, listName, ev) {
      const value = ev.target.value;
      if (value) this.cfgPluginAdd(groupKey, ruleName, listName, value);
      ev.target.value = "";
    },
  },
  mounted() {
    document.addEventListener("click", this.hubOnDocClick);
    document.addEventListener("keydown", this.hubOnKey);
    window.addEventListener("resize", this.hubCloseHelp);
  },
  unmounted() {
    document.removeEventListener("click", this.hubOnDocClick);
    document.removeEventListener("keydown", this.hubOnKey);
    window.removeEventListener("resize", this.hubCloseHelp);
  },
};

/* 字段渲染组件: 复用 CE_FIELD_BASE 的全部读写逻辑(同一棵 YAML 树、同一套控件语义),
 * 只换成 console-hub 的行模板(标签 | 控件 | 「?」)。 */
window.HUB_FIELD_COMPONENT = Object.assign({}, window.CE_FIELD_BASE, {
  name: "hub-field",
  template: "#tpl-hub-field",
});
