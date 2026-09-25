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
    // 标题用「常规」而非「连接 qBittorrent」: 本组除 qB 连接外还有主循环节奏 / 数据目录等常规项
    title: "常规",
    desc: "连上 qBittorrent 的 Web UI，再定好 auto-qb 自己的运行节奏和数据放在哪。",
    lede: "上半部分是连接 qBittorrent：把地址和登录信息填对，auto-qb 就能接管种子管理。下半部分是 auto-qb 自己的常规设置：多久检查一次、一轮最多干多少活、运行状态和日志存在哪个目录。每行末尾的「?」可以看这一项的完整说明。",
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
    desc: "按 tracker 域名识别站点，再套用这个站点的标签、限速和 HR 设置。",
    lede: "用 tracker 域名判断种子来自哪个站点，然后套用这个站点的标签、限速和 HR 设置。没配置的站点完全不做任何管理。",
  },
  rules: {
    title: "规则",
    desc: "「当满足条件时执行动作」的自动化规则，按规则集分组管理。",
    lede: "一条规则就是「当满足条件时，执行这些动作」。条件要全部满足才会执行，动作按从上到下的顺序执行。",
  },
  notify: {
    title: "通知",
    desc: "出错或有风险操作时，用电脑的系统通知提醒你。",
    lede: "出错或者做了有风险的操作时，用电脑的系统通知提醒你。走的是系统自己的通知中心，不用装插件、也不用配微信邮件之类。",
  },
  web: {
    title: "界面",
    desc: "这个浏览器界面怎么开、谁能访问。",
    lede: "你现在用的这个浏览器界面怎么开、谁能访问。改监听地址会让局域网里的其它设备也能操作种子。",
  },
  logging: {
    title: "日志",
    desc: "日志记在哪、留多久、记多细。",
    lede: "auto-qb 把运行日志记在哪、单个文件多大、留几个旧文件。日常用 INFO，排查问题时再开 DEBUG。",
  },
  hr_check: {
    title: "HR 在线核实",
    desc: "部分站点只有一部分种子受 H&R 约束，且站点不提供逐种标记 —— 逐种子在线核实；分区页尾附各站点取数现状。",
    lede: "有些站点只有一部分种子受 H&R 约束，而且站点不告诉你哪些是 —— 只能上站查。开启后 auto-qb 会定期取「我的 H&R」清单、逐种子对账；没接入的站点行为完全不变。取数由浏览器扩展完成，cookie 不离开浏览器。页尾的「站点状态」展示各站点取到哪一步、数据多新、现在为什么不放行。",
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
    rel: [["界面 → 端口", "auto-qb 自己的界面端口，不是 qB 的"], ["常规 → 主机", "端口填对了但主机写错，一样连不上"]],
  },
  "web.host": {
    tags: ["字符串"],
    what: "auto-qb 的浏览器界面监听在哪个地址，决定「谁可以访问这个界面」。",
    def: "127.0.0.1",
    when: ["想从局域网里另一台设备（比如手机、NAS）打开这个界面。"],
    risk: "改成 0.0.0.0 会暴露给局域网。这个界面能暂停和删除种子，局域网里任何设备都能操作。",
    rel: [["界面 → 访问密钥", "对外暴露时密钥是唯一防线"], ["界面 → 跳过本机验证", "只对 127.0.0.1 生效，对外仍强制鉴权"]],
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
    what: "让 auto-qb 盯着 qB 的累计流量，跨过一档阈值就把全局限速降到该档的数值。",
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
      ["通知 → 免打扰时段", "❗语义正好相反：那个是「这段时间不要发通知」，本项是「只在这段时间取数」"],
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
  "rules.overview": {
    tags: ["可选"],
    what: "一条规则就是「当满足条件时，执行这些动作」。规则按列表顺序逐条判断，不会命中一条就停。",
    def: "（无）",
    when: ["想让 auto-qb 自动删种、暂停、改分类等。"],
    risk: "带「风险」标记的动作（尤其是删除类）会真的动你的文件，启用前先确认条件写得够严。",
    rel: [["站点 → 要跑哪些规则", "决定是否对某个站点执行规则"], ["自动化", "不需要写规则也能做的常规管理"]],
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

/* 分区「是否启用」判定: 未启用 -> LED 灰(不抢注意力), 由各处主开关决定 */
const HUB_OFF_KEYS = {
  web: ["config", "web", "enabled"],
  notify: ["config", "notify", "enabled"],
  maintenance: ["config", "grouping", "enabled"],
  hr_check: ["config", "hr_check", "enabled"],
};

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
        view: initialHubView(),  // "hub" | 分组 key | "__logs"(持久化, 见 initialHubView)
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
      // 运行日志不在 schema 分组里(原顶栏日志页迁入), 单独补一张卡
      cards.push({
        key: "__logs",
        icon: "i-list",
        title: "运行日志",
        label: "运行日志",
        desc: "在这里直接看最新日志，不用去翻文件。",
        lede: "直接看 auto-qb 的运行日志，不用去翻文件。改了选项要手动刷新才会重新读取。",
        led: "ok",
        readout: this.logs && this.logs.file ? "已配置" : "日志文件未配置",
        badges: [],
      });
      // HR 站点状态不再单列一张卡(2026-09-25 合并): 它是只读现状不是配置项,
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
      if (this.hub.view === "__logs") {
        return {
          key: "__logs",
          label: "运行日志",
          icon: "i-list",
          title: "运行日志",
          lede: "直接看 auto-qb 的运行日志，不用去翻文件。改了选项要手动刷新才会重新读取。",
        };
      }
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
    /* 搜索: 按配置项名直跳(不用记它在哪个分区) */
    hubHits() {
      const q = (this.hub.query || "").trim().toLowerCase();
      if (!q || !this.cfg.schema || !this.cfg.tree) return [];
      const out = [];
      for (const g of this.cfg.schema.groups) {
        const meta = HUB_GROUP_META[g.key] || {};
        for (const it of this.cfgFlatten(g.fields, ["config"], 0)) {
          if (it.type !== "field") continue;
          const f = it.field;
          const hay = `${f.label} ${f.key} ${f.help || ""}`.toLowerCase();
          if (hay.indexOf(q) < 0) continue;
          out.push({ key: this.hubKey(it.path), label: f.label, group: g.key, groupLabel: meta.title || g.label });
          if (out.length >= 10) return out;
        }
      }
      return out;
    },
  },
  methods: {
    /* ---------------------------------------------------------- 视图跳转(首页 ↔ 二级页) */
    hubGo(key) {
      this.hubCloseHelp();
      this.hub.view = key;
      if (key === "trackers" && !this.cfgTrackerNames().includes(this.cfg.trackerKey)) {
        const names = this.cfgTrackerNames();
        this.cfg.trackerKey = names.length ? names[0] : null;
      }
      if (key === "rules" && !this.cfgRuleGroupNames().includes(this.cfg.ruleGroupKey)) {
        const names = this.cfgRuleGroupNames();
        this.cfg.ruleGroupKey = names.length ? names[0] : null;
      }
      if (key === "__logs" && !this.logs.loaded) this.loadLogs();
      // HR 站点状态已并入 hr_check 分区页尾: 打开分区时拉一次, 之后手动刷新(小时级节奏不轮询)
      if (key === "hr_check" && !this.hrs.loaded) this.loadHrStatus();
      window.scrollTo({ top: 0 });
    },
    hubBack() {
      this.hubCloseHelp();
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
    /* 从存储恢复的分区 key 必须**在 schema 里还认得出**才允许采用 —— schema 是模块级常量,
     * 版本升级后分区可能改名 / 删除, 不校验就会让刷新停在空白分区(且页面上没有任何提示)。
     * 采用时复用 hubGo: trackers / rules 的默认选中项与日志 / HR 的懒加载都在那条路径里,
     * 自己重写一遍就会漏掉其中一半。由 cfgLoad 成功后调用(那一刻 schema 才到手)。 */
    hubRestore() {
      const v = this.hub.view;
      if (!v || v === "hub") return;
      const known = v === "__logs" || !!(this.cfg.schema && this.cfg.schema.groups.some((g) => g.key === v));
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
      for (const g of this.cfg.schema.groups) {
        for (const it of this.cfgFlatten(g.fields, ["config"], 0)) if (it.type === "field") n += 1;
      }
      return n;
    },
    hubLedOf(key) {
      if (key === "speed" && !this.cfgCurveEnabled()) return "off";
      if (key === "trackers" && !this.cfgTrackerNames().length) return "off";
      if (key === "rules" && !this.cfgRuleGroupNames().length) return "off";
      const offPath = HUB_OFF_KEYS[key];
      if (offPath && !this.cfgBool(offPath, "true")) return "off";
      if (key === "web" && this.cfgText(["config", "web", "host"], "127.0.0.1") !== "127.0.0.1") return "warn";
      const risk = this.hubRiskList;
      if (risk.some((r) => r.group === key)) return "warn";
      return "ok";
    },
    hubReadout(key) {
      if (!this.cfg.tree) return "";
      switch (key) {
        case "basic":
          return `${this.cfgText(["config", "qbittorrent", "host"], "127.0.0.1")}:${this.cfgText(["config", "qbittorrent", "port"], "8080")}`;
        case "web":
          return this.cfgText(["config", "web", "host"], "127.0.0.1") === "127.0.0.1" ?
            `仅本机 · ${this.cfgText(["config", "web", "port"], "8080")}` :
            `对外暴露 · ${this.cfgText(["config", "web", "port"], "8080")}`;
        case "notify":
          return this.cfgText(["config", "notify", "quiet_hours"], "") || "全天都弹";
        case "logging":
          return this.cfgText(["config", "logging", "level"], "INFO");
        case "maintenance":
          return this.cfgBool(["config", "grouping", "enabled"], "true") ? "辅种分组已启用" : "辅种分组未启用";
        case "hr_check": {
          const names = this.cfgTrackerNames().filter(
            (n) => this.cfgText(["config", "trackers", n, "hr_check", "mode"], "off") !== "off"
          );
          return names.length ? `${names.length} 个站点在线核实` : "未配置站点";
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
    hubDefaultText(field) {
      const d = field.default;
      if (d === null || d === undefined || d === "") return "（空）";
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
      if (!this.hub.help) return;
      if (e.target && e.target.closest && e.target.closest(".hb-pop")) return;
      this.hubCloseHelp();
    },
    hubOnKey(e) {
      if (e.key === "Escape") this.hubCloseHelp();
    },

    /* ---------------------------------------------------------- 行 / 控件辅助 */
    hubToneOf(item) {
      return HUB_TONE[this.hubBare(item.path)] || "";
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
    hubCount(value) {
      return value && typeof value === "object" ? Object.keys(value).length : 0;
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
