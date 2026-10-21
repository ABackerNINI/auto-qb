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
       * 保存/放弃全是配置树那一套, 不自建状态机。 */
      cards.push({
        key: "webui",
        icon: "i-sliders",
        title: "WebUI",
        label: "WebUI",
        desc: "右键菜单布局定制：重排、显隐、移进「更多操作」，以及跳检开关。",
        lede: "界面行为定制。四支行右键菜单（多选批量/整集整剧/单种子/单组）的项可以重排、隐藏、以及在一级与「更多操作」之间移动；" +
          "布局存在服务端配置里，保存后当前标签立即生效，其它标签/浏览器刷新后生效。跳检开关也搬到了这一张卡（键不变，仍是 config.yml 的 web.skip_check_menu）。",
        led: "on",
        readout: this.cmCardReadout ? this.cmCardReadout() : "默认布局",
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
        return {
          key: "webui", label: "WebUI", icon: "i-sliders", title: "WebUI",
          lede: "界面行为定制。四支行右键菜单（多选批量/整集整剧/单种子/单组）的项可以重排、隐藏、以及在一级与「更多操作」之间移动；布局存在服务端配置里，保存后当前标签立即生效，其它标签/浏览器刷新后生效。",
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
            const v = e.enabled;
            return typeof v === "boolean" ? v : ["true", "1", "yes", "on"].includes(String(v).trim().toLowerCase());
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
    /* WARN: 对象/数组型默认值(如 trackers / rules 的 default={}、channels 的 default=["platform"])不能
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
      /* 聚焦搜索层「点外即收」(方案C 2026-09-29): 收层一律清词 —— 层开着时列表/详情都在暗幕底下,
       * 留词只会让下次点击又盖回来; stage 内点击(搜索行 / 面板 / 暗幕自身除外)不算点外 */
      if (this.hub.view === "trackers" && this.hubTrackerStageOpen &&
          !(e.target && e.target.closest && e.target.closest(".hb-tr-stage"))) {
        this.hubTrackerStageClose(true);
      }
    },
    hubOnKey(e) {
      /* IME 组词中的 Esc/Enter 属于输入法(取消候选 / 确认上屏), 不劫持 —— 中文输入状态按 Esc
       * 只该取消组词, 不该顺带关浮层/清搜索词/退首页 */
      if (e.isComposing || e.keyCode === 229) return;
      if (e.key !== "Escape") return;
      if (this.hub.help) {
        this.hubCloseHelp();
        return;
      }
      /* 站点搜索的退出路径: Esc = 清词收层退聚焦层(跳转器拍板延续 + 方案C) */
      if (this.hub.view === "trackers" && this.hubTrackerStageOpen) {
        this.hubTrackerStageClose(true);
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
     * WARN: JS 必须用 [^\p{L}\p{N}](u 标志必带) —— ASCII \W 是 Unicode 语义的反面,
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
    /* 点命中行(跳转器交互 2026-09-28, 方案C 延续): 选中即清词收层直达详情 —— 层盖着列表,
     * 只选中不清词会把切站效果留在暗幕底下看不见; 焦点一并交还页面, 落到详情可直接编辑 */
    hubTrackerPick(name) {
      this.cfg.trackerKey = name;
      this.hubTrackerStageClose(true);
    },
    /* 聚焦层收层单点(方案C): 清词 + 聚焦态/键盘活动项复位; blurInput 时把焦点从搜索框还回去 */
    hubTrackerStageClose(blurInput) {
      this.cfg.trackerQuery = "";
      this.hub.trackerSearchFocus = false;
      this.hub.trackerHitIdx = -1;
      this.hub.trackerMouseAt = null;
      if (blurInput && this.$refs.trackerSearchInput) this.$refs.trackerSearchInput.blur();
    },
    /* × 清空钮: 配合模板 @mousedown.prevent —— 阻止按钮抢焦点, 输入框保持聚焦可继续输入
     * (清词后聚焦层仍开着, 回到空态引导, 再敲字即搜) */
    hubTrackerClear() {
      this.cfg.trackerQuery = "";
    },
    /* 悬停接管(治「上下键选中项闪烁」2026-09-29): 命中行不挂 @mouseenter + CSS 不写 :hover ——
     * 光标静止停在命中列表上时, 旧高亮(悬停)与键盘活动项两套同源高亮打架, 活动项会跳回光标行;
     * 行入场动画 / 滚动 / DOM 变更后浏览器还会给静止光标补发合成 hover 事件, 放大成交替闪烁。
     * 改为 @mousemove + 位移门限: 位移 <3px(静止 / 合成事件)不接管, 真实移动才把活动项交给光标 */
    hubTrackerHoverIdx(i, ev) {
      const x = ev.clientX, y = ev.clientY, at = this.hub.trackerMouseAt;
      if (at) {
        const dx = x - at.x, dy = y - at.y;
        if (dx * dx + dy * dy < 9) return; // <3px: 光标静止 / 合成事件, 不接管
      }
      this.hub.trackerMouseAt = { x, y };
      this.hub.trackerHitIdx = i;
    },
    /* 聚焦层键盘导航(方案C): ↑↓ 移动命中活动项, Enter 打开活动项(=点命中); IME 组词中不劫持。
     * Esc 不在这里处理 —— 归 hubOnKey 的既有 Esc 链(帮助浮窗优先级在前), 避免双路径清词 */
    hubTrackerKeydown(e) {
      if (e.isComposing || e.keyCode === 229) return;
      const hits = this.hubTrackerHits.hits;
      if (e.key === "ArrowDown" || e.key === "ArrowUp") {
        if (!hits.length) return;
        e.preventDefault();
        const n = hits.length, cur = this.hub.trackerHitIdx;
        this.hub.trackerHitIdx = e.key === "ArrowDown"
          ? (cur + 1) % n
          : (cur < 0 ? n - 1 : (cur - 1 + n) % n);
        this.$nextTick(() => this.hubTrackerScrollActIntoView()); // 滚动跟随(26-09-29-2142)
      } else if (e.key === "Enter") {
        if (this.hub.trackerHitIdx >= 0 && hits[this.hub.trackerHitIdx]) {
          e.preventDefault();
          this.hubTrackerPick(hits[this.hub.trackerHitIdx].name);
        }
      }
    },

    /* 键盘活动项滚动跟随(26-09-29-2142): 命中列表 max-height 300px 可滚, 但 ↑↓ 只改 idx 不推滚动条,
     * 长列表上高亮走出可视区 = 键盘选择不可用。↑↓ 改 idx 后把 .act 行滚进列表视野。
     * 手动差值调 scrollTop(block:"nearest" 语义: 行在视野内不动, 出视野才滚最小距离);
     * 不用 scrollIntoView —— 它会逐层滚动所有可滚祖先, 连带滚动暗幕后面的整页产生二次干扰。
     * $nextTick 等 Vue 把 .act 类挪到新行之后再量。程序滚动不产生光标位移,
     * 浏览器即便补发合成 mousemove 也被 hubTrackerHoverIdx 的 3px 门限挡掉(不复发闪烁)。 */
    hubTrackerScrollActIntoView() {
      const list = document.querySelector(".hb-tr-stage.on .hb-tr-drop-list");
      const row = list && list.querySelector(".hb-tr-hit.act");
      if (!list || !row) return;
      const lr = list.getBoundingClientRect(), rr = row.getBoundingClientRect();
      if (rr.top < lr.top) list.scrollTop += rr.top - lr.top; // 行在上方视野外 → 上滚
      else if (rr.bottom > lr.bottom) list.scrollTop += rr.bottom - lr.bottom; // 行在下方视野外 → 下滚
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
    /* 「新增实体」的命名交互单点(报告 26-10-20-2231 R20-C-02): 取消 / 空名 / 查重的判据只写一遍,
     * 三个入口只声明文案 —— 改命名交互(如加长度提示、二次确认)不必再改三处。
     * def 额外带 title / placeholder / prefill, 其余字段原样交给 cfgEntityAdd 的骨架。 */
    async hubAddEntity(def) {
      const { title, placeholder, prefill, ...entity } = def;
      const input = await this.promptDialog(title, prefill || "", { placeholder, okText: "添加" });
      if (input === null || input === undefined) return;
      const name = String(input).trim();
      if (!name) return;
      this.cfgEntityAdd({ ...entity, name });
    },
    async hubAddTracker(prefill) {
      /* prefill: 聚焦搜索层面板尾的「新增站点「词」」把当前搜索词带进命名框(方案C, 搜不到就当场建) */
      return this.hubAddEntity({
        ...this.cfgTrackerDef(""),
        title: "新增站点配置",
        placeholder: "站点名(如 HHan)",
        prefill,
      });
    },
    async hubImportSites() {
      /* 一键导入缺失站点(对齐 CLI --export-yaml --only-missing): 后端只读扫描,
       * 条目填入编辑器待审 —— 示例值不未经审阅生效, 保存走既有 cfgSave 路径。
       * busy 骨架走 dialogs.js::_panelLoad(toast 通道 errToast: 恒提示不看 auth)。 */
      if (this.hub.importing) return;
      await this._panelLoad(this.hub, async () => {
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
      }, { loading: "importing", errToast: { prefix: "导入失败", fallback: "未知错误", ms: 9000 } });
    },
    async hubAddRuleGroup() {
      return this.hubAddEntity({
        ...this.cfgRuleGroupDef(""),
        title: "新增规则集",
        placeholder: "规则集名(自动补 _rules)",
      });
    },
    async hubAddRule(groupKey) {
      return this.hubAddEntity({
        ...this.cfgRuleDef(groupKey, ""),
        title: "新增规则",
        placeholder: "规则名(如 auto-skip-checking)",
      });
    },
    hubPickPlugin(groupKey, ruleName, listName, ev) {
      const value = ev.target.value;
      if (value) this.cfgPluginAdd(groupKey, ruleName, listName, value);
      ev.target.value = "";
    },

    /* ------------------------------------------------ 全局流量来源卡 (计划 26-10-17-0339 S17/D15)
     * 一张卡合并「来源单选 + 工具状态」: provider 二选一(选中面展开); 底部状态区按 §05 五态展示
     * (auto-qb 侧探测指针); 「立即拉起/重试」促订阅线程立刻重跑; 自启开关**不是配置键** —— 状态读
     * 指针 autostart_registered, 拨动走 POST /autostart(D13); 工具自身参数(采样/阈值/适配器)经
     * 工具控制面读写, 折叠在「工具参数(高级)」—— 工具 PUT /config 是全量覆盖(last-writer-wins),
     * 参数表单必须「读后写」(先取 /status 回显整体提交)。
     * 「关闭工具」(S4, 计划 26-10-17-1737): 确认框(受影响清单取自 schema affects 元数据) ->
     * 先保存 enabled=false -> 再 POST /shutdown; 不切 provider, 「启用」一键恢复。 */
    tmProvider() {
      return this.cfgText(["config", "traffic_source", "provider"], "traffic_monitor");
    },
    tmSetProvider(v) {
      if (v) this.cfgSetPath(["config", "traffic_source", "provider"], v);
    },
    /* 数据来源总开关(S1/D1, 计划 26-10-17-1737): 关 = 停一切取数(停订阅/停拉起), 曲线发 off
     * 快照; 不写盘改别的功能配置, 开回即自恢复。UI 按 D14 **灰显不隐藏**(残留键可见可改)。 */
    tmSourceOff() {
      return this.cfgBool(["config", "traffic_source", "enabled"], true) === false;
    },
    /* 来源段自己的标量行(供 <hub-field> 渲染): 总开关 + 刷新间隔 —— 两者都是"来源本身"的属性,
     * 不随 provider 变(provider 用按钮单独渲染, 两个来源子段走 tmProviderItems)。
     * refresh_interval 是 26-10-18-0813 A3 的新键: 与曲线「执行间隔」是两个独立节奏, 行文案
     * 由 schema help 表达(那里是措辞单点, 前端不另写一份)。 */
    tmSourceRows() {
      const root = this.tmSourceRoot();
      if (!root) return [];
      const base = ["config", "traffic_source"];
      return (root.fields || [])
        .filter((x) => x.key === "enabled" || x.key === "refresh_interval")
        .map((f) => ({ type: "field", field: f, path: [...base, f.key], depth: 0, owner: base, inline: [] }));
    },
    /* 选中来源的参数行(供 <hub-field> 渲染): 从 schema 取该来源子段的叶子字段, 路径指向 traffic_source.<来源>
     *
     * B2/D16: 判据从「模板手工过滤 provider」换成通用可见性口径 —— 两个来源子段在 schema 上各挂
     * show_if=provider, 这里是它唯一的消费点。手工挑 key 与 schema 声明是两套真相: 手工那份漏改了
     * 就会出现"选 A 也显示 B 的参数"(或反之), 而 show_if 是字段元数据自身的一部分, 不会漂。
     * 之所以取叶子而非段项: 卡里要的是"平铺的参数行"(dat_path 一行), 不是可折叠的 object 子段。 */
    tmSourceRoot() {
      const g = this.cfg.schema && this.cfg.schema.groups.find((x) => x.key === "traffic_limit");
      return (g && (g.fields || []).find((f) => f.key === "traffic_source")) || null;
    },
    tmProviderItems() {
      const root = this.tmSourceRoot();
      if (!root) return [];
      const base = ["config", "traffic_source"];
      const out = [];
      for (const sub of root.fields || []) {
        if (!sub.fields) continue;  // 非 object 段(enabled / refresh_interval / provider)不算来源参数
        if (!this.cfgVisible(sub, base)) continue;  // show_if 是唯一判据
        const box = this.cfgFlatten([sub], base, 0)[0];
        for (const row of (box && box.items) || []) {
          if (row.type === "field") out.push(row);
        }
      }
      return out;
    },
    /* 合并卡三区折叠(B4/D14): 缺省展开, 折叠态不持久化(只在 hub.sub 里)
     * 键: source(来源) / curve(限速曲线) / chart(流量图采样) */
    hubSubOpen(key) {
      return this.hub.sub[key] !== false;
    },
    hubSubToggle(key) {
      this.hub.sub[key] = this.hub.sub[key] === false;
    },
    /* 「流量图采样」区(QB_TRAFFIC 段项): 可选段(optional=True)自带开关 + 折叠, 通用 section 口径 ——
     * 与 hubBlocks 生成的块同形, 这里只是把它搬进合并卡, 不另写一套渲染。 */
    tmChartSection() {
      const g = this.cfg.schema && this.cfg.schema.groups.find((x) => x.key === "traffic_limit");
      const f = g && (g.fields || []).find((x) => x.key === "qb_traffic");
      if (!f) return null;
      return this.cfgFlatten([f], ["config"], 0)[0] || null;
    },
    /* 卡头一句现状(与首页读数同源语义, 但更短): 用来在卡内三区之上先给出"这套东西现在什么状态" */
    tmSummary() {
      if (this.tmSourceOff()) return "来源已关闭";
      const src = this.tmProvider() === "global_traffic_monitor" ? "整机流量监视器" : "Traffic Monitor 文件";
      if (!this.cfgCurveEnabled()) return `${src} · 限速未启用`;
      const n = this.cfgCurveList().length;
      return n ? `${src} · ${n} 条曲线` : `${src} · 未配置曲线`;
    },
    /* 状态区五态文案(§05): ready / launching / launch_failed / not_running / not_installed */
    tmStateText() {
      return {
        ready: "已就绪", launching: "拉起中", launch_failed: "拉起失败",
        not_running: "未运行", not_installed: "未安装",
      }[this.tm.state] || "未知";
    },
    /* LED 段落色: CSS 只定义 .hb-led.ok / .warn, 其余落基态灰。
     * S6/#4: ready 曾返回 "on"(无此样式类) -> 「已就绪」显示成灰条; 现归 "ok"(绿)。 */
    tmStateClass() {
      return { ready: "ok", launching: "warn", launch_failed: "warn", not_running: "off", not_installed: "off" }[this.tm.state] || "";
    },
    async tmLoad() {
      // 重拉即作废面板上残留的动作回执(保存/自启/关闭工具) —— _panelLoad 只预清自己的错误槽
      this.tm.saveMsg = "";
      this.tm.saveErr = "";
      this.tm.autoMsg = "";
      this.tm.autoErr = "";
      await this._panelLoad(this.tm, async () => {
        const r = await this.api("/api/traffic/monitor/status");
        this.tm.enabled = !!r.enabled;
        this.tm.state = r.state || "not_running";
        this.tm.reachable = !!r.reachable;
        this.tm.toolUrl = r.tool_url || "";
        this.tm.tokenPath = r.token_path || "";
        this.tm.version = r.version || "";
        this.tm.pid = r.pid || 0;
        this.tm.dataDir = r.data_dir || "";
        this.tm.autostartRegistered = !!r.autostart_registered;
        this.tm.autostartError = r.autostart_error || "";
        this.tm.error = r.error || "";
        this.tm.retryS = Number(r.retry_s) || 0;
        this.tm.claimNote = r.claim_note || null;
        this.tm.status = r.status || null;
        if (this.tm.reachable && r.status && r.status.config) {
          this.tm.form = this.tmNormalizeForm(r.status.config);
        }
      }, {
        loading: "loading", err: "error", errFallback: "读取失败",
        authGated: false,  // 状态轮询的失败(含 auth)都要落「不可达」上屏, 不静默
        keepErr: true,     // 不预清状态槽: tm.error 由响应/失败分支落值(与 dialogs 四块面板不同)
        onErr: () => {     // 失败态装配(轮询口径: 拿不到 = 未运行)
          this.tm.reachable = false;
          this.tm.state = "not_running";
          this.tm.status = null;
        },
        onFinally: () => { this.tm.loaded = true; },
      });
    },
    /* 「立即拉起/重试」: 促订阅线程立刻重跑并忽略失败退避; 之后短轮询 status 观察 launching -> ready/launch_failed */
    async tmRelaunch() {
      if (this.tm.relaunching) return;
      this.tm.relaunching = true;
      this.tm.error = "";
      try {
        await this.api("/api/traffic/monitor/relaunch", { method: "POST" });
        this.tm.state = "launching";
        this.tm.retryS = 0;
        this.tmPollSettle(0);
      } catch (e) {
        this.tm.error = (e && e.message) || "促拉起失败";
        this.tm.relaunching = false;
      }
    },
    /* 轮询收敛(有界): 每 2s 重读状态, 直到离开 launching 或到上限; pollGen 代际守卫防重入叠加 */
    tmPollSettle(n) {
      const gen = ++this.tm.pollGen;
      setTimeout(async () => {
        if (gen !== this.tm.pollGen) return;
        await this.tmLoad();
        if (this.tm.state === "launching" && n < 15) {
          this.tmPollSettle(n + 1);
          return;
        }
        this.tm.relaunching = false;
      }, 2000);
    },
    /* 「关闭工具」(S4/D3/D4, 计划 26-10-17-1737): 确认框列出受影响功能(清单取自 schema
     * 字段 enabled 的 affects 元数据, 不另写一份) -> 先保存 enabled=false(热重载即停订阅 /
     * 停拉起, 关闭可逆) -> 再 POST /shutdown 停工具进程; 不切 provider。 */
    tmAffectLabels() {
      const root = this.tmSourceRoot();
      const f = root && (root.fields || []).find((x) => x.key === "enabled");
      return ((f && f.affects) || []).map((id) => TM_AFFECT_LABELS[id] || id);
    },
    async tmShutdownTool() {
      if (this.tm.shutting) return;
      const items = this.tmAffectLabels();
      let body = "将停止工具进程, 并关闭整个流量来源功能: " + (items.join("; ") || "取数将全部暂停") +
        "; 开机自启注册不受影响。";
      if (this.cfgDirty) body += "当前还有其它未保存改动, 也会一并保存。";
      body += "之后打开上方「启用」即可恢复。";
      const ok = await this.confirmDialog("关闭工具", body, { okText: "关闭工具", danger: true });
      if (!ok) return;
      this.tm.shutting = true;
      this.tm.shutdownMsg = "";
      this.tm.shutdownErr = "";
      try {
        // 次序(D3): 先落盘 enabled=false 并热重载(订阅线程随之停), 再停工具进程 ——
        // 反序会让停工具的瞬间又被订阅线程抢拉起来。
        this.cfgSetBool(["config", "traffic_source", "enabled"], false);
        const saved = await this.cfgSave();
        if (!saved) {
          // 保存失败: 内存态回滚成 true 与磁盘一致(工具继续跑, 用户可重试; 不留「内存关了
          // 盘没关」的错位——那会让下次普通保存把关闭静默写进去)。
          this.cfgSetBool(["config", "traffic_source", "enabled"], true);
          this.tm.shutdownErr = "保存失败, 未停止工具(可重试)";
          return;
        }
        try {
          await this.api("/api/traffic/monitor/shutdown", { method: "POST" });
          this.tm.shutdownMsg = "已关闭工具进程";
        } catch (e) {
          this.tm.shutdownErr = "来源已关闭并保存; 停止工具失败: " + ((e && e.message) || "未知错误");
        }
        await this.tmLoad();
        this.tmPollShutdown(0);
      } finally {
        this.tm.shutting = false;
      }
    },
    /* 停止后轮询收敛(有界): 每 1s 重读状态, 直到工具离开 ready(指针删除即 not_running)或到
     * 上限; pollGen 代际守卫与 tmPollSettle 共用(两条轮询链不叠加)。 */
    tmPollShutdown(n) {
      const gen = ++this.tm.pollGen;
      setTimeout(async () => {
        if (gen !== this.tm.pollGen) return;
        await this.tmLoad();
        if (this.tm.state === "ready" && n < 10) {
          this.tmPollShutdown(n + 1);
        }
      }, 1000);
    },
    /* 「以本安装重登记」(D4/D5, 计划 26-10-20-1316 §03): 二次确认 -> 有界前台跑安装内
     * claim 启动器(人工易主唯一通道)。工具正在跑/数据归属异会被工具侧拒绝(409), 其人话
     * 输出原样进 claimErr —— auto-qb 不解释只转述。成功后刷状态(注记被工具侧清除)。 */
    async tmClaim() {
      if (this.tm.claiming) return;
      const ok = await this.confirmDialog(
        "以本安装重登记",
        "将把本安装登记为整机正主(唯一写数据的安装), 并原子重写正主记录。" +
          "工具正在运行时会被拒绝(请先「关闭工具」); 数据目录属于其它安装时也会被拒绝。" +
          "确认继续?",
        { okText: "重登记" }
      );
      if (!ok) return;
      this.tm.claiming = true;
      this.tm.claimMsg = "";
      this.tm.claimErr = "";
      try {
        const r = await this.api("/api/traffic/monitor/claim", { method: "POST" });
        this.tm.claimMsg = (r && r.output) || "已重登记为正主";
        await this.tmLoad();
      } catch (e) {
        this.tm.claimErr = (e && e.message) || "重登记失败";
      } finally {
        this.tm.claiming = false;
      }
    },
    /* 工具配置 -> 表单: 列表字段折成逗号串(表单是纯文本输入), 其余原样
     * (时间/大小是复合串 "30S"/"10MiB", 原样留在表单里, 由单位控件拆成「数值 + 单位」显示) */
    tmNormalizeForm(cfg) {
      const out = {};
      for (const k of Object.keys(cfg || {})) {
        const v = cfg[k];
        out[k] = Array.isArray(v) ? v.join(", ") : v;
      }
      return out;
    },
    /* 表单 -> 工具配置载荷(全量覆盖, last-writer-wins): 列表字段逗号串转数组, 其余按 kind 归一。
     * S7/D13: 时间/大小**不再 Number() 化**(数值化会丢掉单位), 复合串原样回传; 用户没动过的键
     * 也原样回传 —— 旧版工具回显的裸数值因此能无损往返, 迁移的语义平移由工具侧负责。 */
    tmBuildPayload() {
      const f = this.tm.form;
      const num = (x) => (x === "" || x === null || x === undefined ? 0 : Number(x));
      const list = (x) => String(x || "").split(",").map((s) => s.trim()).filter(Boolean);
      const out = {};
      for (const p of this.tmParams()) {
        const v = f[p.key];
        if (v === undefined) continue;  // 工具没回显该键: 不发明值(丢给工具侧默认)
        if (p.kind === "list") out[p.key] = list(v);
        else if (p.kind === "time" || p.kind === "size") out[p.key] = v;
        else if (p.kind === "text") out[p.key] = String(v || "");
        else out[p.key] = num(v);
      }
      return out;
    },
    /* 工具参数的单位拆/合(S7/D12/D13): 复用设置页同一套单位表(cfgUnitParts / cfgUnitOptions /
     * cfgUnitLabel) —— 前端只做显示层拆合("10MiB" -> 10 + MiB), 文法与取值权威在工具侧
     * (gtm/units.py)。空数值写空串(= 未配置) 而不是 "MiB" 这种无数字值。 */
    tmUnitParts(p) {
      return this.cfgUnitParts(p.kind, this.tm.form[p.key], p.unitDefault);
    },
    tmSetUnitPart(p, num, unit) {
      const n = String(num === undefined || num === null ? "" : num).trim();
      this.tm.form[p.key] = n ? n + (unit || "") : "";
    },
    /* 工具参数行的「?」: 复用设置页的就近说明浮窗(hubAsk / hub.helpKey)。工具参数不在配置树里,
     * 走不了 hub-field, 故用合成 item 承载「字段样」元数据(label/kind/help/default 四件)。 */
    tmAskKey(p) {
      return "tool." + p.key;
    },
    tmAskItem(p) {
      return {
        type: "field",
        path: ["tool", p.key],
        field: { label: p.label, kind: p.kind, help: p.help, default: p.def },
      };
    },
    async tmSave() {
      await this._panelLoad(this.tm, async () => {
        const r = await this.api("/api/traffic/monitor/config", {
          method: "PUT",
          body: JSON.stringify({ config: this.tmBuildPayload() }),
        });
        if (r && r.config) this.tm.form = this.tmNormalizeForm(r.config);
        this.tm.saveMsg = "已保存（工具侧已热重载）";
      }, { loading: "saving", err: "saveErr", errFallback: "保存失败", authGated: false });
    },
    /* 自启开关: 读指针 autostart_registered, 拨动只发 install/uninstall; 失败回滚勾选态 */
    async tmAutostart(action) {
      const desired = action === "install";
      await this._panelLoad(this.tm, async () => {
        const r = await this.api("/api/traffic/monitor/autostart", {
          method: "POST",
          body: JSON.stringify({ action: action }),
        });
        this.tm.autoMsg = (r && r.message) || "已处理";
        this.tm.autostartRegistered = desired;
      }, {
        loading: "autoBusy", err: "autoErr", errFallback: "操作失败", authGated: false,
        onErr: () => { this.tm.autostartRegistered = !desired; },  // 失败回滚勾选态(与指针一致)
      });
    },
    tmFmtBytes(n) {
      return this.fmtSize(n);
    },
    /* ---- 文件选择器(D10③): 找不到工具时, 目录导航 + 文件名输入写 tool_exe / tool_dir ----
     * 后端 /api/fs/dirs 只列目录、且限在允许的保存路径内 —— 工具安装目录若不在范围内, 走上方文本框
     * 手填绝对路径; 在范围内可直接导航并用文件名拼出绝对路径写 tool_exe。 */
    tmPickOpen() {
      this.tm.pick.open = true;
      this.tm.pick.name = "";
      this.tm.pick.error = "";
      this.tmPickLoad("");
    },
    async tmPickLoad(path) {
      await this._panelLoad(this.tm.pick, async () => {
        const r = await this.api("/api/fs/dirs?path=" + encodeURIComponent(path || ""));
        this.tm.pick.path = r.path || "";
        this.tm.pick.parent = r.parent || "";
        this.tm.pick.dirs = r.dirs || [];
      }, {
        loading: "loading", err: "error", errFallback: "目录读取失败", authGated: false,
        onErr: () => { this.tm.pick.dirs = []; },
      });
    },
    tmPickEnter(d) {
      this.tmPickLoad(d.path);
    },
    tmPickUp() {
      if (this.tm.pick.parent) this.tmPickLoad(this.tm.pick.parent);
    },
    tmPickApplyDir() {
      if (!this.tm.pick.path) return;
      this.cfgSetPath(["config", "traffic_source", "global_traffic_monitor", "tool_dir"], this.tm.pick.path);
      this.tm.pick.open = false;
    },
    tmPickApplyExe() {
      const name = String(this.tm.pick.name || "").trim();
      if (!this.tm.pick.path || !name) return;
      const sep = this.tm.pick.path.indexOf("\\") >= 0 ? "\\" : "/";
      this.cfgSetPath(["config", "traffic_source", "global_traffic_monitor", "tool_exe"],
        this.tm.pick.path.replace(/[\\/]+$/, "") + sep + name);
      this.tm.pick.open = false;
    },
    /* 工具参数表(§05 工具侧参数): 键/标签/控件形态/说明; 模板按此 v-for 渲染, 避免 11 行硬编码。
     * S7/D12/D13: kind=time/size 走「数值框 + 单位下拉 + ?」——
     *   - 单位表与设置页同源(cfgUnitOptions / UNIT_OPTIONS), 默认单位由 unitDefault 给;
     *   - 盘上与契约只留复合串("30S"/"10MiB"), 这里只负责显示层拆合;
     *   - def 只作「?」浮窗的「默认值」展示, **真值以工具侧 gtm/config.py 为权威**(写错不会生效,
     *     校验权威与默认值都在工具那一侧, 前端不复制)。
     * kind=list 的 hint 是输入框占位(逗号分隔正则); kind=text/int 走普通输入框。 */
    tmParams() {
      return [
        {
          key: "sample_interval", label: "采样间隔", kind: "time", unitDefault: "S", def: "5S",
          help: "多久读一次网卡计数器。越小曲线越细、CPU 占用越高; 两次采样之间的峰值取不到。"
            + "改完立即生效(热重载), 不用重启工具。",
        },
        {
          key: "flush_delta_bytes", label: "落盘阈值", kind: "size", unitDefault: "MiB", def: "1MiB",
          help: "累计流量变化达到这个量就立刻把增量追加进 history_traffic.dat。"
            + "调大 = 写盘次数更少, 但工具崩溃时丢的增量更多。与「落盘间隔」是「谁先到算谁」的关系。",
        },
        {
          key: "flush_interval_s", label: "落盘间隔", kind: "time", unitDefault: "S", def: "30S",
          help: "即使没到「落盘阈值」, 也最多隔这么久落一次盘 —— 低速时的兜底节奏。"
            + "调小 = 历史图更新更勤, 写盘更频繁。",
        },
        {
          key: "notify_threshold_bytes", label: "通知阈值", kind: "size", unitDefault: "MiB",
          def: "100MiB",
          help: "当日累计流量每涨这么多, 工具就向 auto-qb 推一次事件, 让它立刻重读历史文件刷新图表。"
            + "auto-qb 侧还有一层刷新冷却, 两边都设才不会被频繁推送牵着跑。",
        },
        {
          key: "http_host", label: "控制面监听地址", kind: "text", def: "127.0.0.1",
          help: "工具本机 HTTP 接口(控制面)绑哪个地址, auto-qb 就是从这里读状态、下配置的。"
            + "一般不用改; 改成 0.0.0.0 会暴露给局域网(控制面靠 Bearer 密钥鉴权)。"
            + "**改完要重启工具才生效**(改绑监听地址无法热切换)。",
        },
        {
          key: "http_port", label: "控制面端口", kind: "int", def: "0",
          help: "控制面端口。0 = 每次启动由系统分配随机空闲端口(推荐, 不会与别的程序抢端口);"
            + "填固定端口便于手工调试。auto-qb 靠工具的发现指针找端口, 不需要你填这里。"
            + "**改完要重启工具才生效**。",
        },
        {
          key: "lease_ttl_s", label: "订阅租约", kind: "time", unitDefault: "S", def: "3M",
          help: "订阅租约时长(默认 3 分钟 = 180 秒): 超过这么久没收到 auto-qb 的心跳, 工具就把这个订阅剔除、"
            + "不再向它推送。必须明显大于「心跳周期」, 否则 auto-qb 会被误判为掉线。",
        },
        {
          key: "heartbeat_interval_s", label: "心跳周期", kind: "time", unitDefault: "S", def: "1M",
          help: "auto-qb 每隔这么久续一次租约(默认 1 分钟 = 60 秒)。改这个值只影响之后的续租节奏, "
            + "auto-qb 在订阅响应里拿到新值后自动跟随。",
        },
        {
          key: "notify_timeout_s", label: "推送超时", kind: "time", unitDefault: "S", def: "3S",
          help: "向 auto-qb 推事件的单次超时。超时只记一条失败并等下一轮, 不影响落盘与采样。",
        },
        {
          key: "adapter_include", label: "适配器白名单", kind: "list", def: "",
          hint: "逗号分隔正则, 留空 = 全部",
          help: "只统计名称匹配这些正则的网卡(逗号分隔)。留空 = 不设白名单。"
            + "回环与已断开的网卡本来就默认排除, 不用在这里写。",
        },
        {
          key: "adapter_exclude", label: "适配器黑名单", kind: "list", def: "",
          hint: "逗号分隔正则, 留空 = 不排除",
          help: "排除名称匹配这些正则的网卡(逗号分隔)。虚拟机 / VPN / 蓝牙之类的虚拟网卡常被重复计数,"
            + "填它们的名字可避免把同一份流量算两遍。",
        },
      ];
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
