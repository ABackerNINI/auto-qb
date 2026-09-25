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
        newTrackerName: "",
        ruleGroupKey: null,  // 规则集编辑器当前选中规则集
        newRuleGroupName: "",
        newRuleName: "",
        addOpen: "",  // 当前展开的"新增"表单: "" | tracker | ruleGroup | rule(同时只允许一个)
        collapsedRules: {},  // 规则卡折叠态 { "<规则集>::<规则名>": true }
        openSections: {},  // 可选段展开态 { "<路径>": true }; **缺省 = 折叠**(设置页字段多, 展开应是主动选择)
        openGroups: {},  // 普通 object 段(group)展开态 { "<路径 join>": true }; 缺省 = 折叠(同 section)
        openLists: {},  // pattern_list 字段 list 区展开态 { "<路径 join>": true }; 缺省 = 折叠
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
          const chart = this._curveChart(i, dir);
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
    async cfgSave() {
      this.cfg.saving = true;
      try {
        const result = await this.api("/api/config", { method: "PUT", body: JSON.stringify({ tree: this.cfg.tree }) });
        // 后端会把 R 级字段回退为磁盘旧值 → 重新拉取树保证 UI 与磁盘一致
        const fresh = await this.api("/api/config");
        this.cfgSetTree(fresh.tree);
        const n = (result.changes || []).length;
        // 保存结果反馈走全局 toast(timeout 型 = 琥珀色时钟, 恰合「已保存但需重启才生效」的中间态)
        if (result.restart_required && result.restart_required.length) {
          this.toast(`已保存并热重载(变更 ${n} 项); 需重启进程才生效: ${result.restart_required.join(", ")}`, "timeout", 9000);
        } else {
          this.toast(`已保存并热重载(变更 ${n} 项)`, "ok", 3500);
        }
      } catch (e) {
        this.toast("保存失败: " + (e.message || "未知错误"), "error", 9000);
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
      this.page = "settings";
      if (!this.cfg.schema) await this.cfgLoad();
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
    /* 恢复字段为默认(移除该键, 让后端走默认值) */
    cfgResetField(path) {
      this.cfgDelPath(path);
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
            // 平铺段(schema 声明 open, 如 日志/WEB UI/通知 这类短段): **不渲染折叠头**,
            // 子字段以同级 depth 直接并入(2026-09-15 用户要求移除这三段的折叠;
            // 旧 cfgGroupToggle 对 open 段写不出显式 false 的三态 bug 也因此不再触达渲染层)
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
     * (Field.open, 如 日志/WEB UI/通知 短段声明平铺不折叠), 两者都未定则缺省折叠 */
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
      if (v === undefined || v === null) return field.default === null || field.default === undefined ? "" : this.cfgScalar(field.default);
      return this.cfgScalar(v);
    },
    /* 未配置的字段显示"默认"标记(仅当 schema 声明了非空默认值时提示, 空默认值不打扰) */
    cfgIsDefault(item) {
      const d = item.field.default;
      if (d === null || d === undefined || d === "") return false;
      if (Array.isArray(d) && !d.length) return false;
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
        { type: "field", field: { key: "interval", label: "执行间隔", kind: "time", help: "留空 = 回退主 interval", default: "" }, path: [...base, "interval"], depth: 0 },
        { type: "field", field: { key: "dat_path", label: "Traffic Monitor 数据文件", kind: "path", placeholder: ".../history_traffic.dat", default: "" }, path: [...base, "traffic_source", 0, "traffic_monitor", "dat_path"], depth: 0 },
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
    },
    cfgCurveRemovePeriod(i) {
      const list = [...this.cfgCurveList()];
      list.splice(i, 1);
      if (list.length) this.cfgSetPath([...this.cfgCurvePath(), "curves"], list);
      else this.cfgDelPath([...this.cfgCurvePath(), "curves"]);
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
     * 输出包含: 曲线 path、面积 path、X/Y 轴刻度与档位边界参考线、悬停标记点几何 —— 全部由前端算,
     * 图尺寸足够大可读(PAD 留出轴标签空间)。合法性/解析失败仍只提示不阻断(后端把关)。
     * SPD-02: x 轴改为**按档位边界分段等宽**(每档固定宽度, 末档边界后只留 ∞ 提示区),
     * 不再按流量线性映射 —— 否则末档区间远宽于前面档位时最后一档占位超 80%, 各档形状不可读。
     */
    _curveChart(i, direction) {
      return this._buildCurveChart(i, direction);
    },
    /* 可复用(图表 + 悬停共用同一几何), 故单独成型 */
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
      const W = 560, H = 210, PAD_L = 58, PAD_R = 14, PAD_T = 12, PAD_B = 30;
      const usableW = W - PAD_L - PAD_R;
      const maxS = Math.max(...points.map((p) => p.s), 1);
      const y = (s) => H - PAD_B - (H - PAD_B - PAD_T) * (s / maxS);

      // SPD-02: x 轴按档位边界分段等宽 —— 每档固定 segW 宽, 末档边界之后只留半档宽的"∞"提示区,
      // 不再按流量线性延伸(否则末档区间远宽于前面档位时, 最后一档占位超 80%)。
      const n = points.length;
      const segW = usableW / (n + 0.5);  // n 档 + 半档 ∞ 区
      // t -> px: t 落在 [b(j-1), b(j)](b(-1)=0)时在第 j 段内线性插值; 超出末档边界贴右缘
      const x = (t) => {
        if (t <= 0) return PAD_L;
        for (let j = 0; j < n; j++) {
          if (t <= points[j].t) {
            const lo = j === 0 ? 0 : points[j - 1].t;
            const f = points[j].t > lo ? (t - lo) / (points[j].t - lo) : 1;
            return PAD_L + segW * (j + f);
          }
        }
        return PAD_L + usableW;
      };

      let line = `M ${x(0).toFixed(1)} ${y(points[0].s).toFixed(1)}`;
      for (let k = 1; k < n; k++) {
        line += ` L ${x(points[k - 1].t).toFixed(1)} ${y(points[k - 1].s).toFixed(1)}`;
        line += ` L ${x(points[k - 1].t).toFixed(1)} ${y(points[k].s).toFixed(1)}`;
      }
      const lastS = points[n - 1].s;
      line += ` L ${(PAD_L + usableW).toFixed(1)} ${y(lastS).toFixed(1)}`;
      const area = `${line} L ${(PAD_L + usableW).toFixed(1)} ${y(0).toFixed(1)} L ${x(0).toFixed(1)} ${y(0).toFixed(1)} Z`;

      // 刻度: X 取档位边界(分段等宽后等距刻度不再对应整齐的流量值), 右缘标 ∞; Y 仍取 5 个等距限速
      const xTicks = [{ pos: PAD_L, label: "0" }];
      for (let j = 0; j < n; j++) xTicks.push({ pos: x(points[j].t), label: this._fmtBytes(points[j].t) });
      xTicks.push({ pos: PAD_L + usableW, label: "∞" });
      const yTicks = [];
      for (let k = 0; k <= 4; k++) {
        const s = (maxS * k) / 4;
        yTicks.push({ pos: y(s), label: this._fmtSpeed(s) });
      }
      // 档位边界竖参考线(预计算像素位置, 模板不再按线性比例折算)
      const tierLines = points.map((p) => ({ x: x(p.t) }));
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
        // 悬停换算所需的数据域: segW(每档宽) + points(各档边界/限速)
        segW: segW,
        maxS: maxS,
        points: points,
        note: `${n} 档 · 最严 ${this._fmtSpeed(maxS)}`,
      };
    },
    /* 鼠标在图上移动: 把像素位置换算回 (累计流量, 限速) 并高亮该档(阶梯: 找所属区间) */
    cfgChartHover(event, i, direction) {
      const chart = this.cfgCurveChartOf(i, direction);
      if (!chart) return;
      const svg = event.currentTarget.querySelector("svg");
      const rect = svg.getBoundingClientRect();
      const px = ((event.clientX - rect.left) / rect.width) * chart.w;
      const rel = Math.max(0, Math.min(chart.w - chart.padR, px) - chart.padL);
      // SPD-02 分段等宽: 第 j 段固定 segW 宽; 末档之后的 ∞ 提示区仍属末档(阈值为其上限)
      const n = chart.points.length;
      const j = Math.min(n - 1, Math.floor(rel / chart.segW));
      const f = Math.min(1, Math.max(0, (rel - chart.segW * j) / chart.segW));
      const lo = j === 0 ? 0 : chart.points[j - 1].t;
      const t = lo + (chart.points[j].t - lo) * f;
      // 阶梯语义: 该累计流量落入哪一档(阈值为区间上限) -> 用该档的限速
      const speed = chart.points[j].s;
      const hx = chart.padL + rel;
      const hy = chart.h - chart.padB - (chart.h - chart.padB - chart.padT) * (speed / chart.maxS);
      this.cfg.chartHover = {
        key: `${i}:${direction}`,
        x: hx,
        y: hy,
        tLabel: rel > chart.segW * n ? "∞" : this._fmtBytes(t),
        sLabel: this._fmtSpeed(speed),
        index: j + 1,
        // tooltip 位置(用百分比定位在容器内)
        leftPct: (hx / chart.w) * 100,
        topPct: (hy / chart.h) * 100,
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

/* 字段渲染组件: 单一模板适配全部 kind
 *
 * 通过 inject("ce") 调用根实例上的 cfg* 方法 —— 无构建链下这是复用控件、避免模板重复的最轻方案。
 * 模板见 index.html 的 <script type="text/x-template" id="tpl-ce-field">。
 */
window.CE_FIELD_COMPONENT = {
  name: "ce-field",
  template: "#tpl-ce-field",
  props: { item: { type: Object, required: true } },
  inject: ["ce"],
  /* 全局 mixin(app.mixin(CONFIG_EDITOR))给**每个**组件都挂了 provide(){ce:this},
   * 于是嵌套 ce-field 的 inject 会被中间层 ce-field 截获 —— 拿到的是该 ce-field 实例,
   * 它的 cfg 是 data() 新建的本地副本(嵌套字段只显默认值、编辑不进根树)。
   * 这里把自己**注入到的 ce 原样再 provide 下去**: 顶层 ce-field 注入的是根实例,
   * 任意深度的嵌套 ce-field 沿链拿到的都是同一个根(Vue 选项初始化 inject 先于 provide,
   * 此时 this.ce 已就绪)。group/section/subcard 三层嵌套都依赖此行为。 */
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
  },
  methods: {
    textValue() {
      return this.ce.cfgInputValue(this.f, this.path);
    },
    boolValue() {
      return this.ce.cfgBool(this.path, this.f.default);
    },
    sectionExists() {
      return this.ce.cfgExists(this.path);
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
      return this.ce.cfgBool(entry.path, entry.field.default);
    },
    setInline(entry, checked) {
      this.ce.cfgSetBool(entry.path, checked);
    },
    isDefault() {
      return this.ce.cfgIsDefault(this.item);
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
     * ⚠ `unitParts` 是 **computed**(无参 getter), 只能 `this.unitParts.unit` 取属性;
     *    写成 `this.unitParts()` 是把 getter 的**返回值**({num, unit} 对象)当函数调用
     *    ⇒ TypeError ⇒ 经典设置页一改"数值 + 单位"字段的数字就整页白屏
     *    (2026-09-21 实测修复; 静态守阵见 tests/test_web.py
     *     `test_frontend_computed_not_invoked_as_function`)。 */
    setUnitNum(value) {
      this.ce.cfgSetUnit(this.path, value, this.unitParts.unit);
    },
    setUnitName(unit) {
      this.ce.cfgSetUnit(this.path, this.unitParts.num, unit);
    },
    /* 规则引用: 从下拉选一条 => 追加一条引用, 并把下拉复位回占位项 */
    refPick(event) {
      const value = event.target.value;
      if (value) this.ce.cfgItemAdd(this.path, value);
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
