/* auto-qb WEB UI 图形化配置编辑器(Vue 3 全局 mixin, 无构建链)
 *
 * 设计要点(与 ai/06 约定一致):
 * - 前端持有**与磁盘同构的 YAML 树**(标量全为字符串), 编辑即就地增删改, 不做任何格式转换 → 零漂移
 * - `schema`(来自 /api/config/schema)只决定"怎么渲染 + 怎么提示", 不承载正确性规则;
 *   合法性唯一入口仍是后端 load_config —— 保存失败时 400 返回可读错误并原样展示
 * - 脏检测用 JSON 快照对比; 保存成功后重新拉取树(后端会把 R 级字段回退为旧值)
 * - 字段渲染采用"扁平化"列表(嵌套 object 展开为带缩进的多行), 模板只需一套分支
 */
/* 数值 + 单位下拉的单位表(与后端 schema.UNIT_KINDS 对应)
 *
 * 只按 **kind** 决定可用单位, 不把单位表写进 schema: 这样插件 spec(spec_kind=speed)
 * 与配置字段共用同一套控件, 无需给 Plugin 也加一份单位字段。
 * UNIT_FALLBACK 仅在"当前值无法解析出单位"时使用(如字段为空); 一般情况下直接沿用
 * 当前值里已有的单位(如 30M -> M), 不打扰用户。
 */
const UNIT_OPTIONS = {
  time: ["S", "M", "H", "D"],
  size: ["B", "KiB", "MiB", "GiB", "TiB"],
  speed: ["B/s", "KiB/s", "MiB/s", "GiB/s"],
};
const UNIT_FALLBACK = { time: "S", size: "MiB", speed: "KiB/s" };
/* 时间单位下拉的中文显示文案(仅改显示, value 仍是 S/M/H/D 与后端解析一致) */
const UNIT_LABELS = { time: { S: "秒", M: "分", H: "时", D: "天" } };

/* 站点→全局 回退链 map(report 26-10-03-0504 方案 B 阶段2)
 *
 * 语义单点在后端 loaders.py: remove_similar_tags 走 load_tracker_config(站点未设回退全局),
 * hr 输出字段走 load_tracker_hr 的 out/out_bool(站点 spec -> 全局 hr 段 -> 字段默认)。
 * 键 = 站点段叶子键, 值 = 全局对应键在 config 根下的中间段(叶子键同名, 空数组 = config 顶层)。
 * 站点绝对路径形如 ["config","trackers",<站点名>,...中间段,叶子键], 全局对应路径 =
 * ["config",...中间段,叶子键] —— 以路径上的站点名动态展开, 不穷举静态路径。
 * 仅这 7 个键做「站点值→全局对应键→schema 默认」生效值回填与来源徽标;
 * hr.exclude_tags / hr.exclude_categories 是并集语义(全局∪站点, loaders out_union, 设计注
 * 防「站点段写了就静默丢全局排除」), 不进本表 —— 不做回填与徽标(阶段3 只补 help 文案)。
 */
const SITE_FALLBACK_GLOBAL = {
  remove_similar_tags: [],
  add_tag: ["hr"],
  add_category: ["hr"],
  overwrite_category: ["hr"],
  add_tag_for_satisfied: ["hr"],
  add_category_for_satisfied: ["hr"],
  overwrite_category_for_satisfied: ["hr"],
};

window.CONFIG_EDITOR = {
  data() {
    return {
      cfg: {
        schema: null,  // /api/config/schema 元数据(分组/字段/插件/常量/热重载级别)
        tree: null,  // 完整 YAML 文档树(含 config 根段)
        baseline: "",  // 已保存树的 JSON 快照(脏检测)
        loading: false,
        saving: false,
        error: "",  // 加载/保存错误(加载失败时整页替换; 保存失败走 toast)
        trackerKey: null,  // 站点编辑器当前选中站点
        trackerQuery: "",  // 站点二级页搜索框(不持久化, 与首页 hub.query 互不影响; 逻辑在 config_hub.js)
        newTrackerName: "",
        ruleGroupKey: null,  // 规则集编辑器当前选中规则集
        newRuleGroupName: "",
        newRuleName: "",
        addOpen: "",  // 当前展开的"新增"表单: "" | tracker | ruleGroup | rule(同时只允许一个)
        collapsedRules: {},  // 规则卡折叠态 { "<规则集>::<规则名>": true }
        openSections: {},  // 可选段展开态 { "<路径>": true }; **缺省 = 折叠**(设置页字段多, 展开应是主动选择)
        openGroups: {},  // 普通 object 段(group)展开态 { "<路径 join>": true }; 缺省 = 折叠(同 section)
        openLists: {},  // pattern_list 字段 list 区展开态 { "<路径 join>": true }; 缺省 = 折叠
        openCurves: {},  // 限速曲线条目展开态 { "<序号>": true }; 缺省 = 折叠(2026-09-28 用户要求)
        picker: { open: false, groupKey: "", ruleName: "", list: "" },  // 条件/动作选择面板(单例)
        chartHover: null,  // 限速曲线鼠标取值: { chartKey, x, y, tLabel, sLabel } | null
      },
    };
  },
  provide() {
    // 字段渲染子组件通过 inject 拿到根实例, 从而复用同一套 cfg* 方法
    return { ce: this };
  },
  computed: {
    cfgDirty() {
      if (!this.cfg.tree) return false;
      return JSON.stringify(this.cfg.tree) !== this.cfg.baseline;
    },
    /* 插件名 -> 元数据(条件/动作共用一张索引, 名称无冲突) */
    cfgPluginIndex() {
      const schema = this.cfg.schema;
      if (!schema) return {};
      const idx = {};
      for (const p of schema.plugins.condition) idx[p.name] = p;
      for (const p of schema.plugins.action) idx[p.name] = p;
      return idx;
    },
    /* 限速曲线的阶梯图数据: key 为 "<曲线序号>:<方向>"
     *
     * 作计算属性而非方法: 模板中每张图要引用 line/area/note/axis 多处, 计算属性只算一次;
     * 纯展示数据(解析失败的点直接跳过), 合法性仍由后端 load_config 夹紧。
     */
    cfgCurveCharts() {
      const out = {};
      const list = this.cfgCurveList();
      for (let i = 0; i < list.length; i++) {
        for (const dir of ["upload_curve", "download_curve"]) {
          const chart = this._buildCurveChart(i, dir);
          if (chart) out[`${i}:${dir}`] = chart;
        }
      }
      return out;
    },
  },
  methods: {
    /* ---------------------------------------------------------- 数值 + 单位
     *
     * 配置里的时间/大小/速度均是"数字 + 单位"的复合串(30M / 10MiB / 6MiB/s),
     * 界面上拆成"数值框 + 单位下拉"。写回仍是**单个字符串**(与磁盘同构的 YAML 树不变),
     * 合法性仍由后端 load_config 夹紧 —— 前端只负责拆/拼显示。
     */
    cfgHasUnit(kind) {
      return !!UNIT_OPTIONS[kind];
    },
    cfgUnitOptions(kind) {
      return UNIT_OPTIONS[kind] || [];
    },
    /* 时间单位下拉显示中文(仅 time 类), size/speed 原样返回 —— value 不变, 配置无漂移。
     * 强制 String(unit): 若上游传入非字符串(对象/Proxy), 模板插值时 String(obj) 会抛
     * "Cannot convert object to primitive value"; 这里主动归一避免下游连锁报错。 */
    cfgUnitLabel(kind, unit) {
      const u = String(unit);
      return (UNIT_LABELS[kind] && UNIT_LABELS[kind][u]) || u;
    },
    /* 拆: "1.5D" -> {num:"1.5", unit:"D"}; 空/不可解析时 unit 取 unit_default 或 kind 回退值 */
    cfgUnitParts(kind, text, unitDefault) {
      const opts = this.cfgUnitOptions(kind);
      const m = String(text === undefined || text === null ? "" : text).trim().match(/^([\d.]*)\s*([A-Za-z/]*)$/);
      const num = m ? m[1] : "";
      let unit = m ? m[2] : "";
      if (!opts.includes(unit)) unit = unitDefault || UNIT_FALLBACK[kind] || opts[0] || "";
      return { num: num, unit: unit };
    },
    /* 拼: 数值为空则写空串(= 未配置, 走默认), 避免产生 "MiB" 这种无数字值 */
    cfgSetUnit(path, num, unit) {
      const n = String(num === undefined || num === null ? "" : num).trim();
      this.cfgSetPath(path, n ? n + (unit || "") : "");
    },

    /* ---------------------------------------------------------- 规则引用(站点 rules)
     *
     * 既要"下拉可选"(避免手写错规则集名), 也要"可直接粘贴修改"(故输入框始终可编辑,
     * 下拉仅作为追加一条引用的快捷入口)。
     * ceRefOptions 返回**未过滤**全集; 行组件的 refOptions computed 再按当前站点已引用值过滤。
     */
    ceRefOptions() {
      const out = [];
      for (const [gname, group] of Object.entries(this.cfgRuleGroups())) {
        const names = Object.keys(group || {});
        const items = [{ value: `@${gname}`, label: `全部规则(${names.length} 条)` }];
        for (const rn of names) items.push({ value: `@${gname}.${rn}`, label: rn });
        out.push({ group: gname, items: items });
      }
      return out;
    },

    /* ---------------------------------------------------------- 加载与保存 */

    cfgConfig() {
      if (!this.cfg.tree) return {};
      return this.cfg.tree.config || {};
    },
    async cfgLoad() {
      this.cfg.loading = true;
      this.cfg.error = "";
      try {
        const [schema, conf] = await Promise.all([this.api("/api/config/schema"), this.api("/api/config")]);
        this.cfg.schema = schema;
        this.cfgSetTree(conf.tree);
        if (!this.cfg.trackerKey) this.cfg.trackerKey = Object.keys(this.cfgConfig().trackers || {})[0] || null;
        if (!this.cfg.ruleGroupKey) this.cfg.ruleGroupKey = Object.keys(this.cfgRuleGroups())[0] || null;
        // schema 到手才认得出分区 key: 校验并恢复上次看的分区(刷新保持位置; 见 config_hub.hubRestore)
        this.hubRestore();
      } catch (e) {
        this.cfg.error = e.message || "配置加载失败";
      } finally {
        this.cfg.loading = false;
      }
    },
    cfgSetTree(tree) {
      if (!tree || typeof tree !== "object") tree = { config: {} };
      if (!tree.config || typeof tree.config !== "object") tree.config = {};
      this.cfg.tree = tree;
      this.cfg.baseline = JSON.stringify(tree);
    },
    /* 返回 Boolean: 保存是否成功 —— 「保存并刷新」那条路径要靠它决定刷不刷新
     * (保存失败却刷新 = 白丢改动; 既有按钮路径拿返回值不用, 零影响) */
    async cfgSave() {
      this.cfg.saving = true;
      try {
        const result = await this.api("/api/config", { method: "PUT", body: JSON.stringify({ tree: this.cfg.tree }) });
        // 后端会把 R 级字段回退为磁盘旧值 → 重新拉取树保证 UI 与磁盘一致
        const fresh = await this.api("/api/config");
        this.cfgSetTree(fresh.tree);
        const n = (result.changes || []).length;
        // 保存结果反馈走全局 toast(timeout 型 = 琥珀色时钟, 恰合「已保存但有未写入项」的中间态)。
        // 口径(issue 26-09-28-2135): R 级/readonly 字段在写盘前已回退为磁盘旧值 —— 值**没写进去**,
        // 重启也不会生效, 不能再说「需重启进程才生效」; 如实说「仅能在配置文件中修改, 本次未写入」
        if (result.restart_required && result.restart_required.length) {
          this.toast(`已保存并热重载(变更 ${n} 项); ${result.restart_required.join(", ")} 为程序托管字段, 仅能在配置文件中修改, 本次未写入`, "timeout", 9000);
        } else {
          this.toast(`已保存并热重载(变更 ${n} 项)`, "ok", 3500);
        }
        // R2(计划 26-10-02-1955 W1): 保存成功后刷新功能旗标(免重登)。reload_config 是入队等
        // 主循环应用, PUT 回执先于应用落地 —— 立即拉一次之外再短延时补拉一次收窄竞态窗口
        // (竞态只朝 fail-closed 方向: 菜单暂藏, 后端 gate 仍真值兜底)。
        this.loadWebFlags();
        setTimeout(() => this.loadWebFlags(), 2000);
        return true;
      } catch (e) {
        this.toast("保存失败: " + (e.message || "未知错误"), "error", 9000);
        return false;
      } finally {
        this.cfg.saving = false;
      }
    },
    async cfgDiscard() {
      if (this.cfgDirty) {
        const ok = await this.confirmDialog("放弃未保存的修改", "当前编辑内容将丢失, 配置保持磁盘原样。", {
          okText: "放弃修改", danger: true,
        });
        if (!ok) return;
      }
      await this.cfgLoad();
    },
    cfgReset() {
      // 登出时清空受保护内容(与分组数据同等对待)
      this.cfg.schema = null;
      this.cfg.tree = null;
      this.cfg.baseline = "";
      this.cfg.error = "";
      this.cfg.trackerKey = null;
      this.cfg.ruleGroupKey = null;
      this.cfg.addOpen = "";
      this.cfg.openGroups = {};
      this.cfg.openLists = {};
      this.cfg.chartHover = null;
      this.cfgPickerClose();
    },
    async openSettings() {
      this.searchHelpOpen = false;  // 离开辅种页顶栏: 语法浮卡收起, 不带残留进设置页
      this.page = "settings";
      if (!this.cfg.schema) await this.cfgLoad();
    },

    /* ---------------------------------------------------------- 未保存改动防护(U1-b)
     *
     * issue 26-09-25-1702 / 报告 26-10-02-0508: 「有改动时刷新弹确认框, 刷新后改动清零」。
     * 框的形态选了 **U1-b(自绘框 + 原生兜底)** —— 两条链各管一段, 缺一不可:
     *   · **键盘刷新**(F5 / Ctrl+R 族): keydown 里 preventDefault 拦住默认刷新, 弹**自绘**三选一框
     *     (可写中文、多出「保存并刷新」这一支)。监听在 lifecycle.js mounted 注册(快捷键引擎之后)。
     *   · **其余离开路径**(地址栏回车 / 关标签 / 后退 / 一切真实导航): JS **取消不了**导航,
     *     唯一能拦的是原生 beforeunload 框 —— 文案由浏览器给(防钓鱼)、只有「留下 / 离开」两选项。
     * 之所以不改成纯自绘: 自绘 modal 拦不住导航; 之所以不改成纯原生: 原生框写不出中文也说不清
     * "可以先保存"。两套框并存是 U1-b 明知的代价(报告 §6), 换来的是键盘路径上可定制。
     *
     * 「刷新后清零」= **不做草稿恢复**(报告 §4 决定二): 现状 cfgLoad() 就用服务端树整体替换并
     * 重置 baseline, 这里只是把它从"静默发生"变成"用户点了离开之后发生" —— 语义极简
     * (要么你保存了, 要么它没存在过), 且天然免疫"敏感字段进 Web Storage"与"陈旧草稿幽灵"。
     *
     * 判据沿用 cfgDirty(全树 JSON 对比 baseline, 与 actbar「有改动还没保存」同源单点), 零新增状态机。
     * 挂载范围 = **只要 dirty**, 不额外收窄到设置页: 配置树是内存常驻的, 在设置页改完没保存就
     * 切走, 那棵树仍是脏的 —— 按页收窄会在那条路径上留下一个静默丢失的洞。dirty 只可能在
     * 设置页被造出来(且保存/放弃/登出即清零), 判据本身已经足够窄: 既不弹框疲劳,
     * 也不会因常驻监听让 Firefox 放弃 bfcache(报告 §6)。
     */
    cfgGuardActive() {
      return this.cfgDirty;
    },
    /* 原生兜底的挂载 / 摘除(幂等): 只在 dirty 期存在 —— 脏态由 state.js 的 watcher 驱动 */
    cfgGuardSync(on) {
      const want = !!on && this.cfgGuardActive();
      if (want === !!this._cfgGuardOn) return;
      if (!this._cfgBeforeUnload) this._cfgBeforeUnload = (e) => this._cfgOnBeforeUnload(e);
      this._cfgGuardOn = want;
      if (want) window.addEventListener("beforeunload", this._cfgBeforeUnload);
      else window.removeEventListener("beforeunload", this._cfgBeforeUnload);
    },
    /* 主动刷新(自绘框里点了任一"刷新"分支)前必须摘掉兜底 —— 否则紧接着的 reload 会再弹一次
     * 原生框, 变成"自绘框答完又答一遍"的双框连击(报告 §6 的"去重") */
    cfgGuardRelease() {
      this.cfgGuardSync(false);
    },
    _cfgOnBeforeUnload(e) {
      if (!this.cfgGuardActive()) return undefined;
      e.preventDefault();
      e.returnValue = "";  // 旧浏览器要赋值才弹; 文案由浏览器给, 写了也不显示
      return "";
    },
    /* 键盘刷新拦截: 命中即取消默认刷新并弹自绘框; 不命中一律放行(不抢任何其它键) */
    _cfgOnReloadKey(e) {
      if (e.defaultPrevented) return;                  // 多 handler 礼仪: 先到先得
      if (e.isComposing || e.keyCode === 229) return;  // IME 组合期(与快捷键引擎同口径)
      if (!this.cfgGuardActive()) return;              // 无未保存改动: 刷新照旧, 一声不吭
      if (this.modal.visible) return;                  // 已有弹窗: 不叠框, 交给原生兜底
      // F5 族(含 Ctrl/Shift+F5 硬刷新) + Ctrl/Cmd+R 族(含 Ctrl+Shift+R); 用 e.code 物理键位
      // (与快捷键引擎同口径, 不受布局影响)。注意与 KB_BLACKLIST 的分工: 那条黑名单管的是
      // "业务动作不许绑到这些键", 本守卫管的是"拦掉浏览器默认刷新", 两者目标不同 ——
      // 桌面上 F5 / Ctrl+R 的 preventDefault 确实能取消默认刷新(移动端不可靠, 见报告 §6)。
      const reloadKey = e.code === "F5" || (e.code === "KeyR" && (e.ctrlKey || e.metaKey));
      if (!reloadKey) return;
      e.preventDefault();
      this.cfgReloadGuard();
    },
    /* 自绘三选一(报告 U1-b 多出来的就是「保存并刷新」这一支) */
    async cfgReloadGuard() {
      const choice = await this.confirmThreeDialog(
        "有改动还没保存",
        "刷新会丢弃当前编辑的配置(不做草稿恢复, 刷新后回到磁盘上的配置)。",
        { okText: "保存并刷新", extraText: "放弃改动并刷新", cancelText: "留在此页" }
      );
      if (choice === true) {
        const saved = await this.cfgSave();
        if (!saved) return;  // 保存失败: 留在页面看报错(toast 已给原因), 绝不能带着改动刷新
        this.cfgGuardRelease();
        location.reload();
        return;
      }
      if (choice === "extra") {
        this.cfgGuardRelease();
        location.reload();
      }
      // false = 留在此页(Esc / 点暗幕 / 取消): 什么都不做, 改动仍在
    },

    /* ---------------------------------------------------------- 路径读写 */

    cfgRaw(path) {
      let node = this.cfg.tree;
      for (const p of path) {
        if (node === null || typeof node !== "object" || !(p in node)) return undefined;
        node = node[p];
      }
      return node;
    },
    cfgExists(path) {
      return this.cfgRaw(path) !== undefined;
    },
    /* 标量一律以字符串回写(YAML BaseLoader 语义: 所有标量都是字符串) */
    cfgScalar(value) {
      if (value === null || value === undefined) return "";
      return typeof value === "string" ? value : String(value);
    },
    cfgVal(path, fallback) {
      const v = this.cfgRaw(path);
      if (v === undefined || v === null || v === "") return fallback;
      return v;
    },
    cfgText(path, fallback) {
      const v = this.cfgVal(path, fallback);
      return v === null || v === undefined ? "" : String(v);
    },
    cfgBool(path, fallback) {
      const v = this.cfgVal(path, fallback);
      if (typeof v === "boolean") return v;
      return ["true", "1", "yes", "on"].includes(String(v).trim().toLowerCase());
    },
    cfgSetPath(path, value) {
      let node = this.cfg.tree;
      for (const p of path.slice(0, -1)) {
        if (node[p] === null || typeof node[p] !== "object") node[p] = {};
        node = node[p];
      }
      node[path[path.length - 1]] = value;
    },
    cfgSetBool(path, checked) {
      this.cfgSetPath(path, checked ? "true" : "false");
    },
    cfgDelPath(path) {
      let node = this.cfg.tree;
      for (const p of path.slice(0, -1)) {
        if (node === null || typeof node !== "object" || !(p in node)) return;
        node = node[p];
      }
      if (node && typeof node === "object") delete node[path[path.length - 1]];
    },
    /* 恢复字段为默认(移除该键, 让后端走回退链/默认值)
     * 消费者: CE_FIELD_BASE.followGlobal(方案 B 阶段3「跟随全局」按钮) —— 阶段2 前是死代码, 至此接线 */
    cfgResetField(path) {
      this.cfgDelPath(path);
    },

    /* ---------------------------------------------------------- 站点回退链(生效值回填 + 来源徽标)
     *
     * report 26-10-03-0504 方案 B 阶段2: GET /api/config 给的是磁盘原始树(mask 过敏感值),
     * 前端持整棵 YAML 同构树, 「生效值」自行合并(报告 §5.1 D4 模式 —— VS Code 的
     * effective 值 + "Modified in" 来源徽标)。回退链语义单点在后端 loaders.py, 这里的
     * SITE_FALLBACK_GLOBAL 只是同一张链的渲染侧表达, 服务三件事: 回填 / 徽标 / 占位串。
     */
    /* 站点绝对路径 -> 全局对应路径; 不在回退链(全局页 / 非链上键 / 规则页插件 spec)返回 null。
     * 判据 = 路径形态(config.trackers.<站点名>...) + 叶子键在 SITE_FALLBACK_GLOBAL 表内;
     * 全局页同名字段(如 config.hr.add_tag)path[1] 不是 "trackers", 天然不命中。 */
    cfgSiteFallbackPath(path) {
      if (!Array.isArray(path) || path.length < 4 || path[0] !== "config" || path[1] !== "trackers") return null;
      const key = path[path.length - 1];
      const mid = SITE_FALLBACK_GLOBAL[key];
      if (!mid) return null;
      return ["config", ...mid, key];
    },
    /* 生效值回填(报告 §3.3 显示失真的修复; 铁律: 与来源徽标同批上, 缺一不可):
     * 站点值 → 全局对应键 → schema 默认。仅对回退链 7 键生效, 其余字段原样返回
     * schemaDefault, 行为不变。站点 tri_state 键的 '' 是真值(覆盖为空), 调用方(cfgInputValue)
     * 用 cfgRaw 先判存在性, '' 不会落进这里当缺失; 全局对应键的 '' 不存在(后端 _strip_none 照剥)。 */
    cfgFallbackValue(path, schemaDefault) {
      const gp = this.cfgSiteFallbackPath(path);
      if (!gp) return schemaDefault;
      const g = this.cfgRaw(gp);
      if (g === undefined || g === null || g === "") return schemaDefault;
      return g;
    },

    /* ---------------------------------------------------------- 列表编辑 */

    cfgList(path) {
      const v = this.cfgRaw(path);
      return Array.isArray(v) ? v : [];
    },
    cfgItemSet(path, index, value) {
      const list = this.cfgList(path);
      list[index] = value;
      this.cfgSetPath(path, list);
    },
    cfgItemAdd(path, value) {
      const list = [...this.cfgList(path), value === undefined ? "" : value];
      this.cfgSetPath(path, list);
    },
    cfgItemRemove(path, index) {
      const list = [...this.cfgList(path)];
      list.splice(index, 1);
      if (list.length) this.cfgSetPath(path, list);
      else this.cfgDelPath(path);
    },

    /* ---------------------------------------------------------- 渲染辅助 */

    /* 字段可见性: show_if 为 (同段字段 key, 触发值) */
    cfgVisible(field, basePath) {
      if (!field.show_if || !field.show_if.length) return true;
      const [key, expect] = field.show_if;
      const owner = basePath && basePath.length ? basePath : field.path.slice(0, -1);
      return this.cfgText([...owner, key], "") === expect;
    },
    /* 把字段(含嵌套 object)展开为扁平渲染项
     *
     * 项类型: group(object 段标题, **默认折叠**) / section(可选段: 默认折叠的整体容器) /
     *        field(叶子字段) / subcard(由 group_of 归入父字段的"相关设置"子卡)
     *
     * 两种从属项的呈现方式(2026-09-14 调整):
     *   · **布尔**型从属项(如 add_category 的"覆盖已有分类")→ 父字段的**内联开关**
     *     (挂到父项的 `inline` 上, 由 ce-field 渲染在标签右侧)。它本身只有一个开关,
     *     单独占一张子卡比父字段还显眼, 与"这是父字段的一个附加选项"的语义不符。
     *   · 其余(对象/字符串等)仍走 group_of **子卡**(缩进小卡)。
     *
     * 折叠策略(2026-09-14 第五轮):
     *   · 可选段(optional object) → section(已默认折叠, 保留开关与摘要)
     *   · 普通 object 段 → group(默认折叠, 仅显示标题 + 摘要, 点击展开才看到子字段)
     *   · pattern_list 字段(delete_tags 等) → 自身默认折叠 list 区
     *   · 设置页字段很多, "展开"应是用户主动选择; 折叠态仍可见标题与摘要(已配置数)
     *   · 子项以 item.items 嵌套, 渲染层用 v-show 控制 —— 与 section 同构
     * allowGrouping=false 用于子卡/section/group 内部: 那些字段已归属上层, 不能再参与一次分组判定
     * (否则它们会被再次收进 children, roots 为空 => 容器渲染成空壳且不报错)。
     */
    cfgFlatten(fields, basePath, depth, ownerPath, allowGrouping = true) {
      const children = new Map();
      const inlineChildren = new Map();
      const roots = [];
      for (const f of fields) {
        if (allowGrouping && f.group_of) {
          const bucket = f.kind === "bool" ? inlineChildren : children;
          if (!bucket.has(f.group_of)) bucket.set(f.group_of, []);
          bucket.get(f.group_of).push(f);
        } else {
          roots.push(f);
        }
      }
      const byKey = new Map(fields.map((f) => [f.key, f]));
      const items = [];
      // colorIndex 在同一组内顺序循环 0..5, 给 group 段标题配 6 色色条
      let colorIndex = 0;
      for (const f of roots) {
        const path = [...basePath, f.key];
        if (f.kind === "object") {
          if (f.optional) {
            // 可选段: 缩进一级 + 边框成块(缩进用来表达"这是上一字段的展开内容")
            const subs = this.cfgFlatten(f.fields, path, depth + 1, basePath);
            items.push({ type: "section", field: f, path: path, depth: depth, items: subs });
          } else if (f.open) {
            // 平铺段(schema 声明 open): **不渲染折叠头**, 子字段以同级 depth 直接并入。
            // 曾服务日志/WebUI/通知三短段(2026-09-15 用户要求平铺; 2026-09-28 三段并入「常规」
            // 后改回成块展示, 不再声明 open) —— 现仅 hr_check.optional 段经 section 分支用 open 定初值,
            // 本分支保留为 schema 的通用能力
            const subs = this.cfgFlatten(f.fields, path, depth, basePath);
            items.push(...subs);
          } else {
            // 普通 object 段: **默认折叠**, 仅渲染标题与摘要; 子项以 item.items 嵌套,
            // v-show 控制显隐 —— 设置页字段太多, 默认折叠让用户先看概览再决定展开哪段
            const subs = this.cfgFlatten(f.fields, path, depth + 1, basePath);
            items.push({
              type: "group", field: f, path: path, depth: depth, label: f.label, help: f.help,
              items: subs, colorIndex: colorIndex++ % 6,
            });
          }
          continue;
        }
        const inline = (inlineChildren.get(f.key) || []).map((cf) => ({
          field: cf,
          path: [...basePath, cf.key],
        }));
        items.push({ type: "field", field: f, path: path, depth: depth, owner: ownerPath || basePath, inline: inline });
        const kids = children.get(f.key);
        if (kids && kids.length) {
          // 相关设置子卡: 父字段之下缩进一级, 归属关系一目了然
          const sub = this.cfgFlatten(kids, basePath, depth + 1, ownerPath || basePath, false);
          items.push({
            type: "subcard",
            path: path,
            depth: depth + 1,
            label: `${f.label} · 相关设置`,
            ownerField: f,
            owner: ownerPath || basePath,
            items: this._attachGrey(sub, byKey),
          });
        }
      }
      return this._attachGrey(items, byKey);
    },
    /* 把同段字段表附到带 grey_if 的项上: 灰显判定需要父字段的 schema 默认值作 fallback */
    _attachGrey(items, byKey) {
      for (const it of items) {
        const f = it.field;
        // 仅当引用键在**本层**字段表内才覆写 greyBy: 平铺段(透明展开后 splice 进外层的子项)
        // 自带内层 greyBy, 外层查不到该键时不能把它清成 null —— grey_if 引用的是同段字段,
        // 内层字段表才是正确上下文(第七轮修复)
        if (f && f.grey_if && f.grey_if.length && byKey.has(f.grey_if[0])) {
          it.greyBy = byKey.get(f.grey_if[0]);
        }
      }
      return items;
    },
    /* 字段是否处于"所属功能未启用"状态(grey_if 不满足): 灰显但仍可编辑 */
    cfgGreyed(item) {
      const g = item.field && item.field.grey_if;
      if (!g || !g.length) return false;
      const [key, expect] = g;
      const parent = item.greyBy;
      const fallback = parent ? this.cfgScalar(parent.default) : "";
      return this.cfgText([...item.path.slice(0, -1), key], fallback) !== expect;
    },
    /* 可选段展开/折叠(默认折叠) */
    cfgSectionOpen(path) {
      return !!this.cfg.openSections[this.cfgPathKey(path)];
    },
    cfgSectionToggle(path) {
      const key = this.cfgPathKey(path);
      const next = { ...this.cfg.openSections };
      if (next[key]) delete next[key];
      else next[key] = true;
      this.cfg.openSections = next;
    },
    cfgPathKey(path) {
      return Array.isArray(path) ? path.join(".") : String(path);
    },
    /* 普通 object 段(group)展开/折叠: 三态 —— 用户点过以本地图为准; 未点过跟随 schema 声明
     * (Field.open), 两者都未定则缺省折叠 */
    cfgGroupOpen(path, field) {
      const key = this.cfgPathKey(path);
      if (key in this.cfg.openGroups) return !!this.cfg.openGroups[key];
      return !!(field && field.open);
    },
    cfgGroupToggle(path, field) {
      const key = this.cfgPathKey(path);
      const next = { ...this.cfg.openGroups };
      // 写"当前有效态的取反"而不是 true/删除 二态: 旧实现对缺省展开(open)的段永远写不出
      // 显式 false, 点击无法收起(第七轮修复; 平铺段已不渲染折叠头, 此修复兑底其余段)
      next[key] = !this.cfgGroupOpen(path, field);
      this.cfg.openGroups = next;
    },
    /* group 段折叠摘要: 已配置子字段数/总叶子数(折叠时也能看出规模) */
    cfgGroupSummary(item) {
      if (!item || !item.items) return "未配置";
      const kids = this._collectLeaves(item.items);
      const total = kids.length;
      if (!total) return item.help ? "无子项" : "未配置";
      const filled = kids.filter((k) => k.type === "field" && this.cfgExists(k.path)).length;
      return `已配置 ${filled}/${total} 项`;
    },
    /* 收集 item.items 树里全部叶子(group/section 嵌套也展开), 供摘要计数 */
    _collectLeaves(items, acc = []) {
      for (const it of items || []) {
        if (it.type === "group" || it.type === "section") {
          if (it.items) this._collectLeaves(it.items, acc);
        } else if (it.type === "field" || it.type === "subcard") {
          acc.push(it);
          if (it.items) this._collectLeaves(it.items, acc);
        } else {
          acc.push(it);
        }
      }
      return acc;
    },
    /* pattern_list 字段 list 区展开/折叠: 缺省 = 折叠(delete_tags / delete_tags_if_has_no_torrents 自动命中) */
    cfgListOpen(path) {
      return !!this.cfg.openLists[this.cfgPathKey(path)];
    },
    cfgListToggle(path) {
      const key = this.cfgPathKey(path);
      const next = { ...this.cfg.openLists };
      if (next[key]) delete next[key];
      else next[key] = true;
      this.cfg.openLists = next;
    },
    /* 内联开关(父字段的布尔从属项, 如"覆盖已有分类"): 路径由调用方给出 */
    cfgInlineBool(path, fallback) {
      return this.cfgBool(path, fallback);
    },

    /* 可选段开关: 开启时按 schema 构造初始值(必填子字段先填好, 让新段可直接通过校验) */
    cfgToggleSection(path, field, on) {
      if (!on) {
        this.cfgDelPath(path);
        return;
      }
      this.cfgSetPath(path, this.cfgDefaultForField(field));
    },
    cfgDefaultForField(field) {
      if (field.kind !== "object") return [];
      const spec = {};
      for (const f of field.fields || []) {
        if (!f.required) continue;
        if (f.kind === "enum") spec[f.key] = (f.options && f.options[0]) || "";
        else if (f.kind === "bool") spec[f.key] = "false";
        else spec[f.key] = f.placeholder || this.cfgScalar(f.default);
      }
      return spec;
    },
    cfgInputValue(field, path) {
      const v = this.cfgRaw(path);
      // 站点回退链键(方案 B 阶段2): 键缺失时回填「全局对应键 → schema 默认」的生效值;
      // 注意 tri_state 键的站点 '' 是真值(覆盖为空), cfgRaw 判存在性(非 undefined)即原样返回空串
      if (v === undefined || v === null) return this.cfgScalar(this.cfgFallbackValue(path, field.default));
      return this.cfgScalar(v);
    },
    /* 未配置的字段显示"默认"标记(仅当 schema 声明了非空默认值时提示, 空默认值不打扰)
     * 站点回退链 7 键除外(方案 B 阶段2): 站点页这两态由「站点/全局」来源徽标表达 ——
     * 键缺失时生效值是全局配置值(未必等于 schema 默认), 再标「默认」就是矛盾徽标 */
    cfgIsDefault(item) {
      const d = item.field.default;
      if (d === null || d === undefined || d === "") return false;
      if (Array.isArray(d) && !d.length) return false;
      if (this.cfgSiteFallbackPath(item.path)) return false;
      return !this.cfgExists(item.path);
    },

    /* ---------------------------------------------------------- 站点编辑器 */

    cfgTrackerNames() {
      return Object.keys(this.cfgConfig().trackers || {});
    },
    cfgTracker(name) {
      const trackers = this.cfgConfig().trackers || {};
      return trackers[name] || null;
    },
    cfgTrackerAdd() {
      const name = (this.cfg.newTrackerName || "").trim();
      if (!name) return;
      if (this.cfgTracker(name)) {
        this.toast(`站点 ${name} 已存在`, "error");
        return;
      }
      const spec = {};
      for (const f of this.cfg.schema.tracker_fields) {
        if (f.kind === "str_list") spec[f.key] = [];
      }
      this.cfgSetPath([...this.cfgConfigPath(), "trackers", name], spec);
      this.cfg.trackerKey = name;
      this.cfg.newTrackerName = "";
      this.cfgAddCancel();
    },
    async cfgTrackerRename(oldName) {
      const newName = await this.promptDialog("重命名站点配置", oldName, { okText: "重命名" });
      if (newName === null) return;
      const name = newName.trim();
      if (!name || name === oldName) return;
      const trackers = this.cfgConfig().trackers || {};
      if (trackers[name]) {
        this.toast(`站点 ${name} 已存在`, "error");
        return;
      }
      const rebuilt = {};
      for (const [k, v] of Object.entries(trackers)) rebuilt[k === oldName ? name : k] = v;
      this.cfgSetPath([...this.cfgConfigPath(), "trackers"], rebuilt);
      if (this.cfg.trackerKey === oldName) this.cfg.trackerKey = name;
    },
    async cfgTrackerRemove(name) {
      const ok = await this.confirmDialog(
        `删除站点 ${name} 的配置`,
        "仅从配置文件中移除该站点段(不影响 qB 中的种子), 保存后生效。",
        { okText: "删除", danger: true }
      );
      if (!ok) return;
      const trackers = { ...(this.cfgConfig().trackers || {}) };
      delete trackers[name];
      if (Object.keys(trackers).length) this.cfgSetPath([...this.cfgConfigPath(), "trackers"], trackers);
      else this.cfgDelPath([...this.cfgConfigPath(), "trackers"]);
      const names = Object.keys(trackers);
      this.cfg.trackerKey = names.length ? names[0] : null;
    },
    cfgConfigPath() {
      return ["config"];
    },
    cfgAddCancel() {
      this.cfg.addOpen = "";
    },
    /* 当前站点的渲染项(站点字段 + hr 子段) */
    cfgTrackerItems() {
      const name = this.cfg.trackerKey;
      if (!name || !this.cfg.schema) return [];
      const base = [...this.cfgConfigPath(), "trackers", name];
      return this.cfgFlatten(this.cfg.schema.tracker_fields, base, 0);
    },

    /* ---------------------------------------------------------- 规则集编辑器 */

    cfgRuleGroups() {
      const conf = this.cfgConfig();
      const out = {};
      for (const [k, v] of Object.entries(conf)) {
        if (k.endsWith("_rules") && v && typeof v === "object") out[k] = v;
      }
      return out;
    },
    cfgRuleGroupNames() {
      return Object.keys(this.cfgRuleGroups());
    },
    cfgRuleAddGroup() {
      let name = (this.cfg.newRuleGroupName || "").trim();
      if (!name) return;
      if (!name.endsWith("_rules")) name += "_rules";
      if (this.cfgRuleGroups()[name]) {
        this.toast(`规则集 ${name} 已存在`, "error");
        return;
      }
      this.cfgSetPath([...this.cfgConfigPath(), name], {});
      this.cfg.ruleGroupKey = name;
      this.cfg.newRuleGroupName = "";
      this.cfgAddCancel();
    },
    async cfgRuleRemoveGroup(name) {
      const ok = await this.confirmDialog(`删除规则集 ${name}`, "该规则集下的全部规则将一并移除。", {
        okText: "删除规则集", danger: true,
      });
      if (!ok) return;
      this.cfgDelPath([...this.cfgConfigPath(), name]);
      const names = this.cfgRuleGroupNames().filter((n) => n !== name);
      this.cfg.ruleGroupKey = names.length ? names[0] : null;
    },
    cfgRuleNames(groupKey) {
      const group = this.cfgRuleGroups()[groupKey] || {};
      return Object.keys(group);
    },
    cfgRuleAdd(groupKey) {
      const name = (this.cfg.newRuleName || "").trim();
      if (!name) return;
      const group = this.cfgRuleGroups()[groupKey] || {};
      if (group[name]) {
        this.toast(`规则 ${name} 已存在`, "error");
        return;
      }
      // 新规则仅给 conditions/actions 两个空列表, 其余键留空由后端走默认值(保持 YAML 简洁)
      this.cfgSetPath([...this.cfgConfigPath(), groupKey, name], { conditions: [], actions: [] });
      this.cfg.newRuleName = "";
      this.cfgAddCancel();
    },
    async cfgRuleRemove(groupKey, ruleName) {
      const ok = await this.confirmDialog(`删除规则 ${ruleName}`, "该规则的条件与动作配置将一并移除。", {
        okText: "删除规则", danger: true,
      });
      if (!ok) return;
      this.cfgDelPath([...this.cfgConfigPath(), groupKey, ruleName]);
    },
    async cfgRuleRename(groupKey, ruleName) {
      const input = await this.promptDialog("重命名规则", ruleName, { okText: "重命名" });
      if (input === null) return;
      const name = input.trim();
      if (!name || name === ruleName) return;
      const group = this.cfgRuleGroups()[groupKey] || {};
      if (group[name]) {
        this.toast(`规则 ${name} 已存在`, "error");
        return;
      }
      const rebuilt = {};
      for (const [k, v] of Object.entries(group)) rebuilt[k === ruleName ? name : k] = v;
      this.cfgSetPath([...this.cfgConfigPath(), groupKey], rebuilt);
    },
    cfgRulePath(groupKey, ruleName) {
      return [...this.cfgConfigPath(), groupKey, ruleName];
    },

    /* ---------------------------------------------------------- 限速曲线编辑器 */

    cfgCurvePath() {
      return [...this.cfgConfigPath(), "global_speed_limit_curve"];
    },
    cfgCurveEnabled() {
      return this.cfgExists(this.cfgCurvePath());
    },
    cfgCurveEnable() {
      this.cfgSetPath(this.cfgCurvePath(), { traffic_source: [{ traffic_monitor: { dat_path: "" } }], curves: [] });
    },
    async cfgCurveDisable() {
      const ok = await this.confirmDialog("关闭全局限速曲线", "当前曲线配置将从配置文件中移除。", {
        okText: "关闭并移除", danger: true,
      });
      if (!ok) return;
      this.cfgDelPath(this.cfgCurvePath());
    },
    cfgCurve() {
      return this.cfgRaw(this.cfgCurvePath()) || null;
    },
    cfgCurveItems() {
      const base = this.cfgCurvePath();
      return [
        // SPD-03 enabled 总开关: 勾 = 写 enabled:true, 取消勾 = 写 enabled:false(保留各档配置, 不删段);
        // 键缺省 = 后端默认 true, 开关按勾选显示并带"默认"角标
        { type: "field", field: { key: "enabled", label: "启用", kind: "bool", default: true, help: "关闭后曲线任务整体停用(不写 qB), 各档配置保留" }, path: [...base, "enabled"], depth: 0 },
        { type: "field", field: { key: "interval", label: "执行间隔", kind: "time", help: "曲线任务多久重算一次并套用全局限速: 读 dat、按各 period 曲线聚合查档、写 qB 全局速度限制。流量按日聚合, 不必太频繁(分钟级即可, 不必秒级)。留空 = 回退常规 → interval, 与维护 / 全局清理等内置任务同周期。", default: "" }, path: [...base, "interval"], depth: 0 },
        { type: "field", field: { key: "dat_path", label: "Traffic Monitor 数据文件", kind: "path", placeholder: ".../history_traffic.dat", default: "", help: "Traffic Monitor 的 history_traffic.dat 路径(每行 \"YYYY/MM/DD <上传KB>/<下载KB>\", 单位 KB=1024B); 曲线靠它累计流量自动分档限速。必须指向该文件实际位置 —— 留空或路径错则读不到数据, 该曲线整条不生效。", risk: "路径错 / 文件不存在时不会报错中断, 只是该曲线静默失效(本轮不套用限速、下轮重试), 容易误以为限速没起作用。" }, path: [...base, "traffic_source", 0, "traffic_monitor", "dat_path"], depth: 0 },
      ];
    },
    cfgCurveList() {
      const c = this.cfgCurve();
      return c && Array.isArray(c.curves) ? c.curves : [];
    },
    cfgCurvePeriod(i) {
      const item = this.cfgCurveList()[i];
      return item && item.curve ? item.curve : {};
    },
    cfgCurvePeriodPath(i) {
      return [...this.cfgCurvePath(), "curves", i, "curve"];
    },
    cfgCurveAddPeriod() {
      const list = [...this.cfgCurveList(), { curve: { period: "1D" } }];
      this.cfgSetPath([...this.cfgCurvePath(), "curves"], list);
      // 新曲线顺手展开(默认折叠是给已有条目的, 新加的下一步就是编辑它)
      this.cfg.openCurves = { ...this.cfg.openCurves, [list.length - 1]: true };
    },
    cfgCurveRemovePeriod(i) {
      const list = [...this.cfgCurveList()];
      list.splice(i, 1);
      if (list.length) this.cfgSetPath([...this.cfgCurvePath(), "curves"], list);
      else this.cfgDelPath([...this.cfgCurvePath(), "curves"]);
      // 展开态按序号记录: 删中间一条后其后各条序号前移, 同步搬移保住各条的展开态
      const open = {};
      for (const [k, v] of Object.entries(this.cfg.openCurves)) {
        const idx = Number(k);
        if (idx !== i) open[idx > i ? idx - 1 : idx] = v;
      }
      this.cfg.openCurves = open;
    },
    cfgCurveOpen(i) {
      return !!this.cfg.openCurves[i];
    },
    cfgCurveToggle(i) {
      this.cfg.openCurves = { ...this.cfg.openCurves, [i]: !this.cfg.openCurves[i] };
    },
    /* 档位列表: direction 为 "upload_curve" | "download_curve" */
    cfgCurvePoints(i, direction) {
      const period = this.cfgCurvePeriod(i);
      return Array.isArray(period[direction]) ? period[direction] : [];
    },
    cfgCurvePointsPath(i, direction) {
      return [...this.cfgCurvePeriodPath(i), direction];
    },
    cfgCurvePointAdd(i, direction) {
      const directionKey = direction === "upload_curve" ? "upload_speed_limit" : "download_speed_limit";
      const list = [...this.cfgCurvePoints(i, direction)];
      // 阈值键为动态字符串(如 10GiB); 新增档位给空阈值由用户填写
      list.push({ "": { [directionKey]: "0KiB/s" } });
      this.cfgSetPath(this.cfgCurvePointsPath(i, direction), list);
    },
    cfgCurvePointRemove(i, direction, j) {
      const list = [...this.cfgCurvePoints(i, direction)];
      list.splice(j, 1);
      if (list.length) this.cfgSetPath(this.cfgCurvePointsPath(i, direction), list);
      else this.cfgDelPath(this.cfgCurvePointsPath(i, direction));
    },
    cfgCurveDirectionKey(direction) {
      return direction === "upload_curve" ? "upload_speed_limit" : "download_speed_limit";
    },
    /* 档位阈值键(动态): 改写键即重建该档对象 */
    cfgCurveThreshold(i, direction, j) {
      const entry = this.cfgCurvePoints(i, direction)[j];
      return entry ? Object.keys(entry)[0] || "" : "";
    },
    cfgCurveSpeed(i, direction, j) {
      const entry = this.cfgCurvePoints(i, direction)[j];
      if (!entry) return "";
      const key = Object.keys(entry)[0];
      const speed = entry[key] || {};
      return this.cfgScalar(speed[this.cfgCurveDirectionKey(direction)] || "");
    },
    cfgCurvePointSet(i, direction, j, threshold, speed) {
      const t = threshold === undefined ? this.cfgCurveThreshold(i, direction, j) : threshold;
      const s = speed === undefined ? this.cfgCurveSpeed(i, direction, j) : speed;
      const list = [...this.cfgCurvePoints(i, direction)];
      list[j] = { [t]: { [this.cfgCurveDirectionKey(direction)]: s } };
      this.cfgSetPath(this.cfgCurvePointsPath(i, direction), list);
    },

    /* ---------------------------------------------------------- 曲线图表(SVG 阶梯折线预览)
     *
     * 纯展示: 前端只用它画图, 解析失败不阻断保存(合法性唯一入口仍是后端 load_config)。
     * 语义与 curves.curve_speed 一致 —— 阈值是区间**上限**, 末档之后一直沿用末档速度。
     */

    cfgCurveInvalid(i, direction) {
      // 无法解析的档位数(阈值需形如 10GiB, 限速需形如 6MiB/s)
      let bad = 0;
      const points = this.cfgCurvePoints(i, direction);
      for (let j = 0; j < points.length; j++) {
        if (this._parseSizeValue(this.cfgCurveThreshold(i, direction, j)) === null ||
          this._parseSpeedValue(this.cfgCurveSpeed(i, direction, j)) === null) bad++;
      }
      return bad;
    },
    cfgCurveChartOf(i, direction) {
      return this.cfgCurveCharts[`${i}:${direction}`] || null;
    },
    /* 阶梯折线数据(纯展示)
     *
     * 语义与 curves.curve_speed 一致: 阈值是区间**上限**, 末档之后一直沿用末档速度。
     * 输出包含: 曲线 path、面积 path、X/Y 轴刻度与档位边界参考线、∞ 区水印、悬停标记点几何 —— 全部由前端算,
     * 图尺寸足够大可读(PAD 留出轴标签空间)。合法性/解析失败仍只提示不阻断(后端把关)。
     * x 轴按各档**实际流量长度**比例分段(2026-09-27 重构, 取代旧"每档等宽"): t_1..t_{n-1} 把
     * [0, 末档下限] 切成 n-1 个有限区间按长度分摊 70% 宽度; 末档与后端语义一致(X ≥ 末档下限后
     * 一直沿用末档速度, 末档阈值不改变速度函数)显示为 ∞ 区、占宽不超过 30%(仅 1 档时整图即 ∞, 独占全宽)。
     */
    _buildCurveChart(i, direction) {
      const raw = this.cfgCurvePoints(i, direction);
      const points = [];
      for (let j = 0; j < raw.length; j++) {
        const t = this._parseSizeValue(this.cfgCurveThreshold(i, direction, j));
        const s = this._parseSpeedValue(this.cfgCurveSpeed(i, direction, j));
        if (t === null || s === null || t <= 0) continue;
        points.push({ t, s });
      }
      if (!points.length) return null;
      points.sort((a, b) => a.t - b.t);

      // 几何: 左侧留 Y 轴标签, 底部留 X 轴标签; 图体明显放大(旧版 320×96 太小)
      const W = 560, H = 210, PAD_L = 58, PAD_R = 14, PAD_T = 12, PAD_B = 30, TICK_GAP = 46;
      const usableW = W - PAD_L - PAD_R;
      const maxS = Math.max(...points.map((p) => p.s), 1);
      const y = (s) => H - PAD_B - (H - PAD_B - PAD_T) * (s / maxS);

      // 末档 ∞ 区占图体 ≤30%(封顶防其它档被挤没); 其余有限区间按流量长度比例分摊剩余宽度
      const n = points.length;
      const W_inf = n === 1 ? usableW : usableW * 0.3;
      const W_finite = usableW - W_inf;
      const span = n > 1 ? points[n - 2].t : 0;  // 最后一个有限断点(= 末档下限)
      const x = (t) => PAD_L + (span > 0 ? (t / span) * W_finite : 0);

      // 阶梯线: 断点 t_k 处速度 s_k -> s_{k+1}; 末档平线一直延伸到右缘(∞)
      let line = `M ${x(0).toFixed(1)} ${y(points[0].s).toFixed(1)}`;
      for (let k = 0; k < n - 1; k++) {
        line += ` L ${x(points[k].t).toFixed(1)} ${y(points[k].s).toFixed(1)}`;
        line += ` L ${x(points[k].t).toFixed(1)} ${y(points[k + 1].s).toFixed(1)}`;
      }
      line += ` L ${(PAD_L + usableW).toFixed(1)} ${y(points[n - 1].s).toFixed(1)}`;
      const area = `${line} L ${(PAD_L + usableW).toFixed(1)} ${y(0).toFixed(1)} L ${PAD_L.toFixed(1)} ${y(0).toFixed(1)} Z`;

      // 刻度: X 取 0 + 各有限断点 + 右缘 ∞(相邻标签过近时省略, 参考线仍画); Y 取 5 个等距限速
      const xTicksRaw = [{ pos: PAD_L, label: "0" }];
      for (let k = 0; k < n - 1; k++) xTicksRaw.push({ pos: x(points[k].t), label: this._fmtBytes(points[k].t) });
      xTicksRaw.push({ pos: PAD_L + usableW, label: "∞" });
      const xTicks = [xTicksRaw[0]];
      for (let k = 1; k < xTicksRaw.length - 1; k++) {
        if (xTicksRaw[k].pos - xTicks[xTicks.length - 1].pos >= TICK_GAP) xTicks.push(xTicksRaw[k]);
      }
      xTicks.push(xTicksRaw[xTicksRaw.length - 1]);
      const yTicks = [];
      for (let k = 0; k <= 4; k++) {
        const s = (maxS * k) / 4;
        yTicks.push({ pos: y(s), label: this._fmtSpeed(s) });
      }
      // 档位边界竖参考线: 只画真正改变速度的断点(末档阈值不改变速度函数, 不画)
      const tierLines = [];
      for (let k = 0; k < n - 1; k++) tierLines.push({ x: x(points[k].t) });
      return {
        viewBox: `0 0 ${W} ${H}`,
        w: W,
        h: H,
        padL: PAD_L,
        padR: PAD_R,
        padT: PAD_T,
        padB: PAD_B,
        line: line,
        area: area,
        xTicks: xTicks,
        yTicks: yTicks,
        tierLines: tierLines,
        baseY: y(0),
        // 悬停换算所需的数据域: 有限区宽/总跨度 + 各档边界/限速
        span: span,
        W_finite: W_finite,
        W_inf: W_inf,
        maxS: maxS,
        points: points,
        note: `${n} 档 · 纵轴上限 ${this._fmtSpeed(maxS)}`,
      };
    },
    /* 鼠标在图上移动: 把像素位置换算回 (累计流量, 限速) 并高亮该档(阶梯: 找所属区间)
     *
     * 按 SVG 实际渲染缩放换算(preserveAspectRatio 居中) —— 任凭 CSS 把图改宽改窄都不偏移,
     * 修掉旧版"假设 SVG 铺满容器"在高度被压扁时的映射错位; tooltip 位置同样用真实渲染像素
     * 还原成相对容器的百分比, 不再受容器 padding 影响。
     */
    cfgChartHover(event, i, direction) {
      const chart = this.cfgCurveChartOf(i, direction);
      if (!chart) return;
      const svg = event.currentTarget.querySelector("svg");
      const rect = svg.getBoundingClientRect();
      const box = event.currentTarget.getBoundingClientRect();
      const scale = Math.min(rect.width / chart.w, rect.height / chart.h);
      const offX = (rect.width - chart.w * scale) / 2;
      const offY = (rect.height - chart.h * scale) / 2;
      const px = (event.clientX - rect.left - offX) / scale;
      const rel = Math.max(0, Math.min(chart.w - chart.padR, px) - chart.padL);
      // 第 j 档: 有限区内按流量线性映射找区间(阈值为区间上限); ∞ 区整段归末档
      const n = chart.points.length;
      let j, tLabel;
      if (chart.span <= 0 || rel >= chart.W_finite) {
        j = n - 1;
        tLabel = "∞";
      } else {
        const t = (rel / chart.W_finite) * chart.span;
        j = 0;
        while (j < n - 1 && t >= chart.points[j].t) j++;
        tLabel = this._fmtBytes(t);
      }
      // 阶梯语义: 该累计流量落入哪一档 -> 用该档的限速
      const speed = chart.points[j].s;
      const hx = chart.padL + rel;
      const hy = chart.h - chart.padB - (chart.h - chart.padB - chart.padT) * (speed / chart.maxS);
      this.cfg.chartHover = {
        key: `${i}:${direction}`,
        x: hx,
        y: hy,
        tLabel: tLabel,
        sLabel: this._fmtSpeed(speed),
        index: j + 1,
        // tooltip 位置: SVG 内绘制坐标还原到屏幕像素, 再换算成相对容器的百分比
        leftPct: ((rect.left - box.left + offX + hx * scale) / box.width) * 100,
        topPct: ((rect.top - box.top + offY + hy * scale) / box.height) * 100,
      };
    },
    cfgChartLeave() {
      this.cfg.chartHover = null;
    },
    cfgChartHovered(i, direction) {
      const h = this.cfg.chartHover;
      return !!h && h.key === `${i}:${direction}`;
    },
    /* 单位倍数: KiB/MiB/GiB... 为 1024 进制, KB/MB/GB... 为 1000 进制; 仅 B 或空 = 1 */
    _sizeMultiplier(unit) {
      const u = String(unit || "").trim();
      if (!u || /^b$/i.test(u)) return 1;
      const idx = "KMGTP".indexOf(u[0].toUpperCase());
      if (idx < 0) return null;
      return (/(i)/i.test(u) ? 1024 : 1000) ** (idx + 1);
    },
    _parseSizeValue(text) {
      const m = String(text === undefined || text === null ? "" : text).trim().match(/^([\d.]+)\s*([A-Za-z]*)$/);
      if (!m) return null;
      const mult = this._sizeMultiplier(m[2]);
      if (mult === null) return null;
      const v = parseFloat(m[1]);
      return isNaN(v) ? null : v * mult;
    },
    _parseSpeedValue(text) {
      const t = String(text === undefined || text === null ? "" : text).trim();
      if (!t) return null;
      return this._parseSizeValue(t.replace(/\s*\/\s*s\s*$/i, ""));
    },
    _fmtBytes(v) {
      for (const [u, div] of [["TiB", 2 ** 40], ["GiB", 2 ** 30], ["MiB", 2 ** 20], ["KiB", 2 ** 10]]) {
        if (v >= div) return (v / div).toFixed(1) + " " + u;
      }
      return Math.round(v) + " B";
    },
    _fmtSpeed(v) {
      for (const [u, div] of [["GiB/s", 2 ** 30], ["MiB/s", 2 ** 20], ["KiB/s", 2 ** 10]]) {
        if (v >= div) return (v / div).toFixed(1) + " " + u;
      }
      return Math.round(v) + " B/s";
    },
  },
};

/* 字段渲染组件的**行为基座**(不是一个组件, 不要拿去 app.component 注册)
 *
 * 通过 inject("ce") 调用根实例上的 cfg* 方法 —— 无构建链下这是复用控件、避免模板重复的最轻方案。
 * 唯一消费者是 `config_hub.js` 的 `HUB_FIELD_COMPONENT`: 它 `Object.assign` 拷走这里全部读写方法,
 * 只换掉 `name` 与 `template`(即"同一套控件语义, 两套版式")。
 *
 * WARN: 2026-09-25: 经典设置页移除后, 原 `ce-field` 组件与 `tpl-ce-field` 模板已不可达, 一并删除;
 *   这里随之摘掉只服务那个组件的 `name` / `template` 两个键。**基座本身不能删** —— 删了 hub 侧
 *   会连带失去全部 cfg* 读写(inject/provide 链 + 方法都在这里)。守阵 `_scan_mixin_wiring` 的
 *   "定义即需接线" 规则已把 "被别的全局 Object.assign 消费" 也算作接线。
 */
window.CE_FIELD_BASE = {
  props: { item: { type: Object, required: true } },
  inject: ["ce"],
  /* 全局 mixin(app.mixin(CONFIG_EDITOR))给**每个**组件都挂了 provide(){ce:this},
   * 于是嵌套字段组件的 inject 会被中间层截获 —— 拿到的是该实例, 它的 cfg 是 data() 新建的
   * 本地副本(嵌套字段只显默认值、编辑不进根树)。这里把自己**注入到的 ce 原样再 provide 下去**:
   * 顶层注入的是根实例, 任意深度的嵌套组件沿链拿到的都是同一个根(Vue 选项初始化 inject 先于
   * provide, 此时 this.ce 已就绪)。group/section/subcard 三层嵌套都依赖此行为。 */
  provide() {
    return { ce: this.ce };
  },
  computed: {
    f() {
      return this.item.field;
    },
    path() {
      return this.item.path;
    },
    indent() {
      return { marginLeft: (this.item.depth || 0) * 16 + "px" };
    },
    isList() {
      return this.f.kind === "str_list" || this.f.kind === "pattern_list";
    },
    isBare() {
      // 无标签整行布局(插件 spec 的单值/列表项): 插件名与说明已在卡片头展示
      return !!this.item.bare;
    },
    isText() {
      return !["bool", "enum", "str_list", "pattern_list", "keyed_list", "rules_ref"].includes(this.f.kind);
    },
    /* 数值 + 单位下拉: 时间/大小/速度三类 kind 共用同一控件 */
    hasUnit() {
      return this.ce.cfgHasUnit(this.f.kind);
    },
    unitOptions() {
      return this.ce.cfgUnitOptions(this.f.kind);
    },
    unitParts() {
      return this.ce.cfgUnitParts(this.f.kind, this.textValue(), this.f.unit_default);
    },
    visible() {
      if (this.item.depends && !this.ce.cfgExists(this.item.depends)) return false;
      // 子卡随父字段的可见性一起显隐
      if (this.item.type === "subcard") return this.ce.cfgVisible(this.item.ownerField, this.item.owner);
      if (this.item.type !== "field") return true;
      return this.ce.cfgVisible(this.f, this.item.owner);
    },
    /* 所属功能未启用(grey_if 不满足)时灰显, 但仍可编辑(不阻断, 只提示) */
    greyed() {
      return this.item.type === "field" && this.ce.cfgGreyed(this.item);
    },
    /* 程序托管字段(schema Field.readonly, issue 26-09-28-2135): 渲染禁用控件 + 「程序维护」标记,
     * 值只能经 config.yml 修改 —— 后端写盘前还会按同一张 readonly 键面回退(防线与 UI 同一来源) */
    readonly() {
      return !!(this.f && this.f.readonly);
    },
    /* readonly 且当前值是列表/对象: 控件形态不适用(输入框 String 化出 "[object Object]"),
     * 渲染只读摘要(如 fs.path_map 的映射对) */
    readonlyComplex() {
      if (!this.readonly) return false;
      const v = this.ce.cfgRaw(this.path);
      return v !== null && v !== undefined && typeof v === "object";
    },
    /* 只读摘要行(readonlyComplex 分支): 列表逐项一行, 对象平铺为 "k: v" 对(嵌套值 JSON 化) */
    readonlySummary() {
      if (!this.readonlyComplex) return [];
      const v = this.ce.cfgRaw(this.path);
      const one = (val) => {
        if (val === null || val === undefined) return "";
        if (typeof val !== "object") return String(val);
        return Object.entries(val)
          .map(([k, x]) => `${k}: ${x !== null && typeof x === "object" ? JSON.stringify(x) : String(x)}`)
          .join(" · ");
      };
      if (Array.isArray(v)) return v.map(one);
      return Object.entries(v).map(([k, x]) => `${k}: ${one(x)}`);
    },
    /* 可选段(默认折叠): 折叠态仍显示开关与摘要 */
    sectionOpen() {
      return this.ce.cfgSectionOpen(this.path);
    },
    sectionSummary() {
      // 折叠时给一行摘要(已配置时列出已填字段数, 未配置时说明该段作用)
      if (!this.ce.cfgExists(this.path)) return this.f.help || "未配置";
      const kids = this.ce.cfgFlatten(this.f.fields || [], this.path, 1, this.path, false);
      const filled = kids.filter((k) => k.type === "field" && this.ce.cfgExists(k.path)).length;
      const total = kids.filter((k) => k.type === "field").length;
      return `已配置 ${filled}/${total} 项`;
    },
    /* 普通 object 段(group): 展开态三态解析(见 ce.cfgGroupOpen), 折叠态显示标题 + 摘要 */
    groupOpen() {
      return this.ce.cfgGroupOpen(this.path, this.f);
    },
    groupSummary() {
      return this.ce.cfgGroupSummary(this.item);
    },
    /* pattern_list 字段: list 区缺省折叠, 折叠态显示已配置条数 */
    listOpen() {
      return this.ce.cfgListOpen(this.path);
    },
    listSummary() {
      const n = (this.list() || []).length;
      return n ? `${n} 项` : "未配置";
    },
    /* rules_ref 下拉选项: 按当前站点已引用值过滤 —— 已引用的规则不再出现在下拉里, 误选入口消失;
     * 整组全被引用时该组整个隐藏(免渲染空 optgroup)。归一口径与后端判重一致(str().strip()):
     * 尾随空白的引用同样算已引用。无参 computed, 模板直接 `refOptions` 引用(不得 refOptions())。 */
    refOptions() {
      const used = new Set(this.list().map((it) => String(it === undefined || it === null ? "" : it).trim()));
      return this.ce
        .ceRefOptions()
        .map((g) => ({ group: g.group, items: g.items.filter((o) => !used.has(o.value)) }))
        .filter((g) => g.items.length);
    },
  },
  methods: {
    textValue() {
      return this.ce.cfgInputValue(this.f, this.path);
    },
    boolValue() {
      // 生效值回填(方案 B 阶段2): 站点回退链键缺失时按「全局对应键 → schema 默认」显示,
      // 不再拿 schema 默认冒充生效值(显示失真, report §3.3); 非链上键行为不变
      return this.ce.cfgBool(this.path, this.ce.cfgFallbackValue(this.path, this.f.default));
    },
    sectionExists() {
      return this.ce.cfgExists(this.path);
    },
    toggleSection(on) {
      this.ce.cfgToggleSection(this.path, this.f, on);
    },
    toggleGroup() {
      this.ce.cfgGroupToggle(this.path, this.f);
    },
    toggleList() {
      this.ce.cfgListToggle(this.path);
    },
    /* 单位显示文案(模板 v-for 内带参数调用, 必须是 method 不能是 computed —
       Vue computed getter 收到的参数是组件代理而非遍历项): time -> 秒/分/时/天, 其余原样 */
    unitLabel(u) {
      return this.ce.cfgUnitLabel(this.f.kind, u);
    },
    /* 内联开关(父字段的布尔从属项): 路径由 cfgFlatten 预先算好 */
    inlineValue(entry) {
      // 生效值回填同 boolValue: 站点 hr 段的内联开关(overwrite_category 族)按全局生效值回填
      return this.ce.cfgBool(entry.path, this.ce.cfgFallbackValue(entry.path, entry.field.default));
    },
    setInline(entry, checked) {
      this.ce.cfgSetBool(entry.path, checked);
    },
    isDefault() {
      return this.ce.cfgIsDefault(this.item);
    },
    /* 来源徽标(方案 B 阶段2, 与生效值回填同批上 —— report 风险注「徽标与回填必须一起」):
     * 站点页回退链 7 键, 站点键存在(tri_state 的 '' 也算存在, cfgExists 按树节点判)标「站点」,
     * 否则标「全局」= 该行生效值来自全局配置。返回 null = 不打徽标(全局页 / 非链上键)。
     * 内联开关在父行组件上渲染, 传 entry.path; 常规行不传用本行 path。 */
    siteBadge(path) {
      const p = path || this.path;
      if (!this.ce.cfgSiteFallbackPath(p)) return null;
      return this.ce.cfgExists(p) ? "站点" : "全局";
    },
    /* 文本框占位串: 站点回退链键显示全局生效值(VS Code「Modified in」语义) ——
     * 站点显式空(tri_state, 覆盖为空)时输入框是空串, 灰字占位正是用户该看到的继承值。
     * 仅当**显示值为空**(cfgInputValue 口径, 含回填)时才换成全局值; 有内容的占位串本不可见,
     * 原样返回 schema 的 placeholder, 不让派生逻辑漂出可见面。非链上键行为不变。 */
    sitePlaceholder() {
      const ph = this.f.placeholder || "";
      const gp = this.ce.cfgSiteFallbackPath(this.path);
      if (!gp) return ph;
      if (this.ce.cfgInputValue(this.f, this.path) !== "") return ph;
      return this.ce.cfgText(gp, "") || ph;
    },
    /* 「跟随全局」按钮可见性(方案 B 阶段3): 仅站点页回退链键且站点键**已存在**时显示 ——
     * 键不存在时本就跟随全局, 无事可做; 全局页 / 非链上键 / 规则页插件 spec
     * (cfgSiteFallbackPath 返回 null)一律 false。tri_state 键的 '' 也算存在(cfgExists 按树节点判)。 */
    canFollowGlobal(path) {
      const p = path || this.path;
      return !!(this.ce.cfgSiteFallbackPath(p) && this.ce.cfgExists(p));
    },
    /* 点「跟随全局」= 删站点覆盖键(report 26-10-03-0504 方案 B: 与 git --unset / VS Code Reset
     * 同构; cfgResetField/cfgDelPath 由此接线)。删键可逆性弱(保存后 str 值得重输 / bool 得重拨),
     * 按仓库破坏性动作惯例弹 confirmDialog(danger); 确认后删键 + toast 提醒「保存后生效」——
     * 删的只是内存树, 徽标与回填由响应式树实时翻成「全局」(阶段2 已保证), 无需额外交线。
     * WARN: 本方法跑在 hub-field 组件实例上, confirmDialog/toast/modal 都在**根实例** ——
     *   必须经 this.ce 调(直接 this.confirmDialog 会在 _openModal 读 this.modal 时炸,
     *   嵌套组件没有根的 data; config_hub.js 顶层模板里 this.confirmDialog 能用是因为那里 this=根)。 */
    async followGlobal(path, label) {
      const p = path || this.path;
      if (!this.canFollowGlobal(p)) return;
      const name = label || this.f.label;
      const ok = await this.ce.confirmDialog(
        `「${name}」恢复跟随全局`,
        "将删除本站点对这项的覆盖设置, 生效值回退为全局配置; 保存后写入磁盘。",
        { okText: "跟随全局", danger: true }
      );
      if (!ok) return;
      this.ce.cfgResetField(p);
      this.ce.toast(`已移除「${name}」的站点覆盖, 保存后跟随全局配置`, "ok", 3500);
    },
    set(value) {
      this.ce.cfgSetPath(this.path, value);
    },
    setBool(value) {
      this.ce.cfgSetBool(this.path, value);
    },
    list() {
      return this.ce.cfgList(this.path);
    },
    listSet(i, value) {
      this.ce.cfgItemSet(this.path, i, value);
    },
    listAdd() {
      this.ce.cfgItemAdd(this.path);
    },
    listRemove(i) {
      this.ce.cfgItemRemove(this.path, i);
    },
    /* 数值 + 单位: 只改其中一半时保留另一半的当前值(避免"改单位把数字清空")
     *
     * WARN: `unitParts` 是 **computed**(无参 getter), 只能 `this.unitParts.unit` 取属性;
     *    写成 `this.unitParts()` 是把 getter 的**返回值**({num, unit} 对象)当函数调用
     *    ⇒ TypeError ⇒ 经典设置页一改"数值 + 单位"字段的数字就整页白屏
     *    (2026-09-21 实测修复; 静态守阵见 tests/test_webui_static_dom_page.py
     *     `test_frontend_computed_not_invoked_as_function`)。 */
    setUnitNum(value) {
      this.ce.cfgSetUnit(this.path, value, this.unitParts.unit);
    },
    setUnitName(unit) {
      this.ce.cfgSetUnit(this.path, this.unitParts.num, unit);
    },
    /* 规则引用: 从下拉选一条 => 追加一条引用, 并把下拉复位回占位项。
     * 追加前查重(双保险): 下拉已按已引用值过滤(refOptions), 但过滤渲染前的连选竞态仍可能
     * 送来已引用值 —— 重复则 no-op(只复位)。归一与 refOptions/后端判重同口径(str().strip())。 */
    refPick(event) {
      const value = event.target.value;
      const used = new Set(this.list().map((it) => String(it === undefined || it === null ? "" : it).trim()));
      if (value && !used.has(value)) this.ce.cfgItemAdd(this.path, value);
      event.target.value = "";
    },
    checkedKey(name) {
      const v = this.ce.cfgRaw(this.path);
      return Array.isArray(v) && v.some((it) => it && typeof it === "object" && name in it);
    },
    toggleKey(name) {
      const v = this.ce.cfgRaw(this.path);
      const list = Array.isArray(v) ? [...v] : [];
      const idx = list.findIndex((it) => it && typeof it === "object" && name in it);
      if (idx >= 0) list.splice(idx, 1);
      else list.push({ [name]: {} });
      this.ce.cfgSetPath(this.path, list);
    },
  },
};
