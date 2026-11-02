/* auto-qb WEB UI 设置页 · 新版(Console Hub)逻辑层
 *
 * 与 config_editor.js / config_rules.js 同一范式: 一个 Vue 全局 mixin, 方法名统一 `hub` 前缀。
 * **不复制任何编辑能力** —— 增删改全部复用既有的 cfg* 方法(同一棵 YAML 树、同一套保存/脏检测),
 * 本文件只负责:
 *   1. Hub & Spoke 的视图状态(首页 / 分区二级页 / 面包屑);
 *   2. 把 schema 字段拆成「块 → 行」两层(取代旧页五种折叠容器);
 *   3. 就近说明浮窗的内容与定位(富文案优先, 否则回退 schema 的 help / risk / default)。
 *
 * 版式与控件外观见 shared/console_hub.css(样张 05-console-hub 的原样复刻)。
 * 分组文案取自样张第 9 节「文案改写对照」—— 说它做了什么, 不说它叫什么。
 * busy+try+反馈+finally 骨架不走本文件: tm 面板族与一键导入改接 dialogs.js 的
 * _panelLoad 单点(issue 26-10-20-2231), 经同一根实例混入调用。
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
  traffic_limit: {
    title: "流量与限速",
    desc: "数据来源、按累计流量自动调限速、qB 流量采样记录 —— 三者共用一份流量口径。",
    lede: "这一页管三件事, 它们共用一份流量口径: 上面的「数据来源」决定「读谁的累计流量」(Traffic Monitor 的 dat 文件, 或整机流量监视器工具, 二选一); 中间的「限速曲线」按这份累计流量跨档改 qB 的全局速度上限; 最下面的「流量图采样」把 qB 自己报的速率定期记下来, 供 WEB UI 的流量图使用 —— 那份记录与来源文件的累计流量不是同一份数据。右上「打开历史图表」看全局历史流量。",
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
      ["常规 → 免打扰时段", "!语义正好相反：那个是「这段时间不要发通知」，本项是「只在这段时间取数」"],
      ["HR 在线核实 → 请求最小间隔", "两者一起决定对站点的访问频度"],
    ],
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

/* 「不走通用分区块渲染」的配置路径(计划 26-10-18-0813 B2/D16): hubBlocks 的 walk 只查这张表 ——
 * 此前是 walk 里一行硬编码 if, 合并卡要再排除两块就会变成三处散落判断(改一处漏一处 = 同一块
 * 被渲染两次或一次都不渲染)。三条各自的理由:
 *   config.hr_check.sites          —— 键是内置站点档案 id(来自 constants, 不是配置里已存在的键),
 *                                     通用行组装写不出正确路径; 由 hr_check 分支的「站点接入」卡片渲染;
 *   config.traffic_source          —— 「流量与限速」合并卡的来源区专段渲染(aq-traffic-card);
 *   config.global_speed_limit_curve—— 同上, 曲线区专段渲染(曲线编辑器不是通用控件形态)。 */
const HUB_SKIP_PATHS = ["config.hr_check.sites", "config.traffic_source", "config.global_speed_limit_curve"];

/* 旧 hub.view 持久值 -> 新视图 key(计划 26-10-18-0813 D13): 「流量图」「全局流量来源」「限速曲线」
 * 三组已合并为 traffic_limit。只映射不清 localStorage —— 用户手调的其它偏好不必陪葬, 而且
 * 映射过期后旧键自然失效(落回设置首页), 无副作用。 */
const HUB_VIEW_ALIAS = {
  traffic_source: "traffic_limit",
  speed: "traffic_limit",
  traffic: "traffic_limit",
};

/* 「关闭工具」确认框的受影响功能文案(D4, 计划 26-10-17-1737 S1/S4): schema 字段
 * affects 元数据(功能 id) -> 该功能被连带的后果。id 集合的单一事实源在 schema
 * (config/schema/fields.py 的 Field.affects), 本表只补人话; 漏一个 id 就原样退回
 * id 本身, 由 test_web_traffic_monitor 的接线守阵盯着不丢。 */
const TM_AFFECT_LABELS = {
  global_speed_limit_curve: "全局限速曲线将暂停取数",
  rules: "expr 流量条件(规则)将显式报错",
  history_chart: "历史流量图将关闭",
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
  let v = "hub";
  try {
    v = localStorage.getItem("autoqb.ui.hub") || "hub";
  } catch {
    v = "hub"; // 隐私模式/存储被禁: 本轮从设置首页开始
  }
  /* 合并视图的旧值映射(D13): 三组并一组后, 存量偏好 traffic_source / speed / traffic 一律落到
   * traffic_limit。映射放在**取值处**这个单点 —— 之后 hubRestore 拿到的就是新 key,
   * 不必在恢复路径里再认一遍旧名(旧名进 schema 校验会被判"未知分区"并清回首页)。 */
  return HUB_VIEW_ALIAS[v] || v;
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
        trackerSearchFocus: false,  // 聚焦搜索层(方案C, plans/26-09-29-0323): 搜索框聚焦即开层
        trackerHitIdx: -1,          // 命中面板键盘活动项(↑↓ 移动), -1 = 无
        trackerMouseAt: null,       // 悬停接管的最后一次接管坐标 {x,y}(hubTrackerHoverIdx); null = 无
        /* 「流量与限速」合并卡三个子区的折叠态(计划 26-10-18-0813 B4/D14): 键 = source|curve|chart;
         * 缺省 = 展开。**不持久化**(与站点状态块/运行日志同口径) —— 折叠是浏览时的临时动作,
         * 记进 localStorage 只会让下次进来先看到三个标题。 */
        sub: {},
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
      /* 命中集合随查询词变化重建, 活动项重置回第一项(Enter 即开第一命中, 对齐拍板样机) */
      this.hub.trackerHitIdx = hits && hits.length ? 0 : -1;
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
      // 并进「HR 在线核实」分区页尾; 打开分区只复位折叠态不发请求(阶段2 决策点⑤a,
      // 见 hubGo), 首次展开(hrsToggle)才拉 /api/hr/status。
      // 键盘快捷键(W6, 计划 26-09-28-0354 §5.2): 同为客户端块(不进配置 schema),
      // 数据走 GET/PUT /api/keys; 读数 = 当前派生条数(overrides)。
      const keysDoc = window.AQB_KEYS ? window.AQB_KEYS.load() : null;
      const nKeys = keysDoc ? Object.keys(keysDoc.overrides || {}).length : 0;
      cards.push({
        key: "keys",
        icon: "i-select-all",
        title: "快捷键",
        label: "快捷键",
        desc: "查看与自定义键盘快捷键：录制新键位、冲突交换、恢复默认。",
        lede: "键盘快捷键的查看与自定义。每条动作可重新录制键位（按下即录），冲突时可交换或覆盖并置空对方，浏览器保留键当场拒绑；键位存于服务端，所有浏览器共享，保存后其它标签刷新生效。",
        led: "on",
        readout: nKeys ? `${nKeys} 条已自定义` : "默认键位",
        badges: [],
      });
      /* 「WebUI」卡(计划 26-10-20-0024 W4, D6): 右键菜单布局定制 + 跳检开关(从「常规」的
       * WebUI 配置块迁入)。与「快捷键」同属客户端块 —— 但注意它**不是**纯客户端:
       * 布局落在 config.web.ctx_menu, 走全局 cfgSave 与 /api/webui/flags 下发, 所以脏标记/
       * 保存/放弃全是配置树那一套, 不自建状态机。
       * 26-10-31(计划 26-10-31-0306 W1/T5): 种子转移目标编辑器并入本卡(配置树 web.transfer),
       * 同款「编辑直接落配置树」范式; 读数 = 菜单定制 + 目标数两段拼接。 */
      const cmReadout = this.cmCardReadout ? this.cmCardReadout() : "";
      const trReadout = this.ttCardReadout ? this.ttCardReadout() : "";
      cards.push({
        key: "webui",
        icon: "i-sliders",
        title: "WebUI",
        label: "WebUI",
        desc: "右键菜单布局定制：重排、显隐、移进「更多操作」；跳检开关；种子转移目标管理。",
        lede: "界面行为定制。四支行右键菜单（多选批量/整集整剧/单种子/单组）的项可以重排、隐藏、以及在一级与「更多操作」之间移动；" +
          "布局存在服务端配置里，保存后当前标签立即生效，其它标签/浏览器刷新后生效。跳检开关也搬到了这一张卡（键不变，仍是 config.yml 的 web.skip_check_menu）。" +
          "「种子转移目标」也在这里配置：把种子任务原样转移到其它下载器（移动任务、不动数据），保留哪些字段按目标各配一套。",
        led: "on",
        readout: [cmReadout, trReadout].filter(Boolean).join(" · ") || "默认布局",
        badges: [],
      });
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
      if (this.hub.view === "keys") {
        // 键盘快捷键分区(W6): 客户端块不进 schema, 元信息在此补齐(首页卡/面包屑/页头共用)
        return {
          key: "keys", label: "快捷键", icon: "i-select-all", title: "快捷键",
          lede: "键盘快捷键的查看与自定义。每条动作可重新录制键位（按下即录），冲突时可交换或覆盖并置空对方，浏览器保留键当场拒绑；键位存于服务端，所有浏览器共享，保存后其它标签刷新生效。",
        };
      }
      if (this.hub.view === "webui") {
        // 「WebUI」卡(计划 26-10-20-0024 W4): 同款客户端块(布局键在 config 里, 但分区本身不进 schema)
        // 26-10-31 起本卡还带种子转移目标编辑器(计划 26-10-31-0306 W1/T5), 页头说明一并交代
        return {
          key: "webui", label: "WebUI", icon: "i-sliders", title: "WebUI",
          lede: "界面行为定制。四支行右键菜单（多选批量/整集整剧/单种子/单组）的项可以重排、隐藏、以及在一级与「更多操作」之间移动；布局存在服务端配置里，保存后当前标签立即生效，其它标签/浏览器刷新后生效。「种子转移目标」在下方：把种子任务原样转移到其它下载器（移动任务、不动数据），目标可以增删改配、逐目标测连通。",
        };
      }
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
          // 专段渲染的路径不进通用分区块(B2/D16: 排除表是单点常量, 这里只查表, 不再逐条 if)
          if (HUB_SKIP_PATHS.indexOf(this.hubKey(it.path)) >= 0) continue;
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
    /* 聚焦搜索层开合(方案C, 2026-09-29 拍板): 聚焦或有词即开层。收层路径全部清词
     * (跳转器拍板 2026-09-28 延续), 故「有词但层收着」不存在, 开与 hubTrackerActive 同域 */
    hubTrackerStageOpen() {
      return this.hub.trackerSearchFocus || this.hubTrackerActive;
    },
  },
  methods: {
    /* ---------------------------------------------------------- 视图跳转(首页 ↔ 二级页) */
    hubGo(key) {
      if (this.kbGuardLeave(key)) return;  // 离开快捷键分区且有未保存改动: 先确认(W6, §5.2)
      this.hubCloseHelp();
      this.hubTrackerStageClose(false); // 离开分区即清空站点搜索并复位聚焦层, 不带残留状态(计划 §06 + 方案C)
      this.hub.view = key;
      if (key === "trackers" && !this.cfgTrackerNames().includes(this.cfg.trackerKey)) {
        const names = this.cfgTrackerNames();
        this.cfg.trackerKey = names.length ? names[0] : null;
      }
      if (key === "rules" && !this.cfgRuleGroupNames().includes(this.cfg.ruleGroupKey)) {
        const names = this.cfgRuleGroupNames();
        this.cfg.ruleGroupKey = names.length ? names[0] : null;
      }
      // 站点状态块(计划 26-10-02-1936 阶段2): 默认折叠, 打开分区不再自动拉数(决策点⑤a,
      // 首次展开才拉, 取数时机在 hr_status.js hrsToggle) —— 展开态不持久化, 每次进分区
      // (含刷新后 hubRestore 恢复到本分区)都回到折叠态
      if (key === "hr_check") this.hrsOpen = false;
      // 键盘快捷键分区(W6): 每次进入都重拉服务端真值对齐草稿(他处保存后刷新可见)
      if (key === "keys") this.kbPanelEnter();
      // 「WebUI」定制卡(W4): 进入即回单种子支, 并清掉上次的拖拽残留(拖到一半按 Esc/切走会留源)
      if (key === "webui") this.cmPanelEnter();
      // 同卡的目标编辑器(W1/T5, 计划 26-10-31-0306): 收起展开中的编辑器与测试回执, 不带残留进分区
      if (key === "webui" && this.ttPanelEnter) this.ttPanelEnter();
      // 「流量与限速」合并卡(B1/D13): 每次进入都拉工具控制面真值(工具是外部进程, 状态随时变)
      if (key === "traffic_limit") this.tmLoad();
      window.scrollTo({ top: 0 });
    },
    hubBack() {
      if (this.kbGuardLeave("hub")) return;  // 同 hubGo: 未保存先确认(W6)
      this.hubCloseHelp();
      this.hubTrackerStageClose(false); // 同 hubGo: 返回首页不带站点搜索残留
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
      // "keys" / "webui" 是客户端块(分区本身不进 schema), 与 schema 分区一样允许从存储恢复
      const known = v === "keys" || v === "webui" || !!(this.cfg.schema && this.cfg.schema.groups.some((g) => g.key === v));
      if (!known) {
        this.hub.view = "hub";
        return;
      }
      this.hubGo(v);
    },
    /* 路径数组→点分键单点(收敛 issue 26-10-20-2231 / 台账 R20-C-18): 改键格式(如加前缀防碰撞)
     * 只改这一处; 调用侧**禁止内联** `path.join(".")`。 */
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
      /* 合并卡(D13): 来源关 = off(停一切取数, 比"曲线没启用"更硬); 否则曲线未启用 = warn
       * (来源在取数但没有任何东西消费它 —— 不是坏状态, 只是没配完); 都就绪再落下面统一的
       * risk 判定(= ok)。三档与原「限速」卡的 LED 语义逐格一致。 */
      if (key === "traffic_limit") {
        if (this.tmSourceOff()) return "off";
        if (!this.cfgCurveEnabled()) return "warn";
      }
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
            return this.cfgTruthy(e.enabled);
          }).length;
          return enabled ? `${enabled} 个站点在线核实` : "未配置站点";
        }
        case "traffic_limit": {
          /* 读数 = 「来源名 · N 条曲线」(D13)。两个节奏(来源刷新间隔 / 曲线执行间隔)都在卡里,
           * 读数只报"谁的数 + 配了几条", 不塞节奏 —— 那一格一行放不下, 且会与徽标的「N 档」重复。 */
          const src = this.tmProvider() === "global_traffic_monitor" ? "整机流量监视器" : "Traffic Monitor 文件";
          if (!this.cfgCurveEnabled()) return `${src} · 限速未启用`;
          const list = this.cfgCurveList();
          return list.length ? `${src} · ${list.length} 条曲线` : `${src} · 未配置曲线`;
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
      } else if (key === "traffic_limit" && this.cfgCurveEnabled()) {
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

window.HUB_FIELD_COMPONENT = Object.assign({}, window.CE_FIELD_BASE, {
  name: "hub-field",
  template: "#tpl-hub-field",
});
