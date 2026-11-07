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
        /* 最近一次保存失败的后端报错原文(cfgSave 单点写入, 成功即清空)。后端 400 的聚合报错
         * 是多行文本(「共 N 处」+ 逐条), toast 渲染会折行丢失结构 —— 需要原样展开的消费方
         * (种子转移目标编辑器, 计划 26-10-31-0306 T5)在块内按 pre-wrap 显示它。 */
        saveError: "",
        trackerKey: null,  // 站点编辑器当前选中站点
        trackerQuery: "",  // 站点二级页搜索框(不持久化, 与首页 hub.query 互不影响; 逻辑在 config_hub.js)
        ruleGroupKey: null,  // 规则集编辑器当前选中规则集
        openRuleMeta: {},  // 规则卡「触发与节奏」段展开态 { "<规则集>.<规则名>": true }; 缺省 = 折叠
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
    /* 单位梯(下拉选项)**唯一来源**(收敛 issue 26-10-20-2231 / 台账 R23-B-04): hub-field 的
     * unitOptions/unitLabel 与 traffic-card 的单位下拉都转调这两个函数, 调用侧**禁止另抄
     * 一份阶梯** —— 双源会导致"配置页 30MiB、工具参数页 30GiB"这类同值不同单位。 */
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
        // 选中键存在性校验(R5#153): 只在为空时重选不兜住「键已消失」—— 重命名 A→B 未保存点
        // 「放弃改动」, 重拉的磁盘树上只有 A, trackerKey 仍是 B, 右栏渲染幽灵站点; 此时编辑任意
        // 字段经 cfgSetPath 会把 config.trackers.B 连键带值写回树, 静默复活已放弃的改名。
        // 不在重拉的树里即回落首项; 空容器回落 null(与原缺省语义一致)。
        if (!this.cfgTrackerNames().includes(this.cfg.trackerKey)) {
          this.cfg.trackerKey = this.cfgTrackerNames()[0] || null;
        }
        if (!this.cfgRuleGroupNames().includes(this.cfg.ruleGroupKey)) {
          this.cfg.ruleGroupKey = this.cfgRuleGroupNames()[0] || null;
        }
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
      if (!tree.config || typeof tree !== "object") tree.config = {};
      this.cfg.tree = tree;
      // 规则草稿就地规范化(plan 26-11-01-0106 D2/W3-A/W3-B): conditions 旧扁平列表包隐式 all
      // 树 + actions 旧扁平/混合形翻译规范形并注入缺省 on_error + choose 键面保留 —— 打开即
      // 显示归一形、保存即写新形态; 归一在基线快照之前, 打开不误报脏(后端 normalize 幂等同构)
      this.cfgNormalizeRulesDraft();
      this.cfg.baseline = JSON.stringify(tree);
    },
    /* 返回 Boolean: 保存是否成功 —— 「保存并刷新」那条路径要靠它决定刷不刷新
     * (保存失败却刷新 = 白丢改动; 既有按钮路径拿返回值不用, 零影响) */
    async cfgSave() {
      this.cfg.saving = true;
      this.cfg.saveError = "";
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
          this.toast(`已保存: 已热重载, 变更 ${n} 项; ${result.restart_required.join(", ")} 为程序托管字段, 仅能在配置文件中修改, 本次未写入`, "timeout", 9000);
        } else {
          this.toast(`已保存: 已热重载, 变更 ${n} 项`, "ok", 3500);
        }
        // R2(计划 26-10-02-1955 W1): 保存成功后刷新功能旗标(免重登)。reload_config 是入队等
        // 主循环应用, PUT 回执先于应用落地 —— 立即拉一次之外再短延时补拉一次收窄竞态窗口
        // (竞态只朝 fail-closed 方向: 菜单暂藏, 后端 gate 仍真值兜底)。
        this.loadWebFlags();
        this.transferTargetsReload();  // T6(计划 26-10-31-0306): 转移目标随保存刷新(菜单读侧缓存与磁盘树对齐)
        setTimeout(() => this.loadWebFlags(), 2000);
        return true;
      } catch (e) {
        this.cfg.saveError = e.message || "未知错误";  // 供消费方原样展开聚合报错(toast 会折行)
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
      this.cfg.saveError = "";
      this.cfg.trackerKey = null;
      this.cfg.ruleGroupKey = null;
      this.cfg.openGroups = {};
      this.cfg.openLists = {};
      this.cfg.openRuleMeta = {};
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
     * 判据 = **双脏源**(2026-11-03 扩): 配置树 cfgDirty(全树 JSON 对比 baseline, 与 actbar
     * 「有改动还没保存」同源单点) || 键位草稿 kbDirtyView(独立状态机, GET/PUT /api/keys,
     * 计算属性在 config_hub.js)—— 键位面板从独立分区并入 WebUI 卡后, 它的未保存改动同样
     * 会被刷新静默清零, 不扩就是复刻「刷新后清零」的洞。零新增状态机。
     * 挂载范围 = **只要 dirty**, 不额外收窄到设置页: 配置树是内存常驻的, 在设置页改完没保存就
     * 切走, 那棵树仍是脏的 —— 按页收窄会在那条路径上留下一个静默丢失的洞。dirty 只可能在
     * 设置页被造出来(且保存/放弃/登出即清零), 判据本身已经足够窄: 既不弹框疲劳,
     * 也不会因常驻监听让 Firefox 放弃 bfcache(报告 §6)。
     */
    cfgGuardActive() {
      return this.cfgDirty || this.kbDirtyView;  // kbDirtyView 是计算属性(属性访问, 不是方法)
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
        "刷新会丢弃当前编辑的配置与未保存的键位改动(不做草稿恢复, 刷新后回到磁盘上的配置)。",
        { okText: "保存并刷新", extraText: "放弃改动并刷新", cancelText: "留在此页" }
      );
      if (choice === true) {
        const saved = await this.cfgSave();
        if (!saved) return;  // 保存失败: 留在页面看报错(toast 已给原因), 绝不能带着改动刷新
        if (this.kbDirtyView) {
          // 键位草稿后存(双脏源的第二源): 失败内部已回滚草稿(kbDraftRevert + toast),
          // 无论成败此刻都不再有未保存键位改动, 同样可安全刷新
          await this.kbSaveKeys();
        }
        this.cfgGuardRelease();
        location.reload();
        return;
      }
      if (choice === "extra") {
        this.cfgGuardRelease();
        location.reload();  // 键位草稿只在内存(引擎试用态), 刷新自然清零, 无需显式回滚
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
    /* 真值判断单点(收敛 issue 26-10-20-2231 / 台账 R20-C-06): YAML BaseLoader 全字符串口径下
     * 的高频判断。加真值词(如 "y")只改这一处; 调用侧**禁止内联重写**这份列表。 */
    cfgTruthy(v) {
      if (typeof v === "boolean") return v;
      return ["true", "1", "yes", "on"].includes(String(v).trim().toLowerCase());
    },
    cfgBool(path, fallback) {
      return this.cfgTruthy(this.cfgVal(path, fallback));
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
  },
};

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
      /* 叶子字段 / object 段(group) / 可选段(section) 共用同一口径(计划 26-10-18-0813 B2/D16):
       * `show_if` 此前只对叶子生效, 非叶子恒 true —— 于是 schema 在 object 段上挂的 provider
       * 条件显隐形同虚设, 只能靠模板手写过滤(tmProviderItems)。段项的 owner 由调用点给,
       * 缺失时 cfgVisible 自己回落到 field.path 的父路径(与叶子同一条路)。 */
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
    /* 密码字段的写回(2026-10-20 报障「点进常规就显示有改动还没保存」)
     *
     * 现象: 进设置页「常规」分区, 没碰任何控件, actbar 已经是「有改动还没保存」, 放弃改动一轮
     * 回来照样复现。根因不在设置页自己的逻辑 —— 密码框被包成「用户名 + 密码」的表单形状
     * (见 xtpl.html 密码分支, 为消 Chrome 两条可访问性警告), 浏览器 / 密码管理器会把它当
     * **登录表单**, 把同源(登录页)保存的凭据**自动填**进来, 并在**未聚焦**时派发 input 事件;
     * 原实现 @input=set() 把自动填充的值原样写进配置树 ⇒ 脏标记凭空变真(实测: 一个未聚焦
     * input 事件即翻真), 而框里显示的是掩码, 用户看不出改的是哪一项。
     *
     * 判据 = 事件到达时该框**是不是焦点**: 自动填充发生在未聚焦时(页面加载 / 后台), 而真实
     * 键入、粘贴、密码管理器下拉选取都必然先聚焦 —— 未聚焦一律不写树, 并把显示拉回树里的值
     * (否则界面与树各说各话)。模板侧配 autocomplete="new-password" 从源头劝退凭据填充, 本
     * 守卫兜住忽略 autocomplete 的扩展类工具(Bitwarden / 1Password 等)。
     */
    setSecret(ev) {
      const el = ev.target;
      if (document.activeElement !== el) {
        el.value = this.textValue();
        return;
      }
      this.ce.cfgSetPath(this.path, el.value);
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
     *    (2026-09-21 实测修复; 静态守阵见 tests/test_webui_static_dom_page_layout.py
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
    /* 取消勾选**最后一项**时必须删键, 不能写空列表(2026-10-10 报障, 与 cfgItemRemove 同口径):
     * ① 空列表与"键缺失"不同构 —— 全树 JSON 对比的脏标记认它是改动, 「勾选再取消」后仍提示
     *    "有改动还没保存", 且这一改动在 UI 上没有任何可见痕迹;
     * ② 空列表过不了后端校验(notify.channels 要求非空), 保存必败且用户无法从界面自救。
     * 删键 = 回到"未配置"(后端走缺省), 勾选再取消因此是零副作用的可逆操作。 */
    toggleKey(name) {
      const v = this.ce.cfgRaw(this.path);
      const list = Array.isArray(v) ? [...v] : [];
      const idx = list.findIndex((it) => it && typeof it === "object" && name in it);
      if (idx >= 0) list.splice(idx, 1);
      else list.push({ [name]: {} });
      if (list.length) this.ce.cfgSetPath(this.path, list);
      else this.ce.cfgDelPath(this.path);
    },
  },
};
