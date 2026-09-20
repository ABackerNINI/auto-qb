/* auto-qb WEB UI 配置编辑器 · 规则集专段(条件/动作全量图形化, 无 YAML 片段兜底)
 *
 * 与 config_editor.js 同为一个 Vue 全局 mixin(方法名统一 cfg* 前缀, 无重名冲突)。
 *
 * 结构映射(YAML 形状):
 *   <规则集>_rules:
 *       <规则名>:
 *           conditions: [{<插件名>: <spec>}, ...]
 *           actions:    [{<插件名>: <spec>}, ...]   # 或 {ignore_next_action_error: true} 伪动作
 *
 * spec 形态由 schema 的 Plugin.spec_kind 决定: str/enum/speed 单值, bool 开关, list 列表, object 子表单。
 * 动作可选集合按 trigger 过滤(与后端 validation 的删除触发白名单同源)。
 */
window.CONFIG_RULES = {
  methods: {
    /* ---------------------------------------------------------- 列表与条目 */

    cfgPluginList(groupKey, ruleName, listName) {
      const v = this.cfgRaw([...this.cfgRulePath(groupKey, ruleName), listName]);
      return Array.isArray(v) ? v : [];
    },
    cfgPluginEntry(groupKey, ruleName, listName, index) {
      return this.cfgPluginList(groupKey, ruleName, listName)[index] || null;
    },
    isIgnoreNext(entry) {
      return !!(entry && typeof entry === "object" && "ignore_next_action_error" in entry);
    },
    cfgPluginName(entry) {
      if (!entry || typeof entry !== "object") return "";
      const keys = Object.keys(entry);
      return keys.length ? keys[0] : "";
    },
    cfgPluginMeta(entry) {
      return this.cfgPluginIndex[this.cfgPluginName(entry)] || null;
    },

    /* ---------------------------------------------------------- 增删与排序 */

    cfgPluginAdd(groupKey, ruleName, listName, pluginName) {
      const path = [...this.cfgRulePath(groupKey, ruleName), listName];
      const list = [...this.cfgPluginList(groupKey, ruleName, listName)];
      list.push({ [pluginName]: this.cfgPluginDefaultSpec(pluginName) });
      this.cfgSetPath(path, list);
    },
    cfgIgnoreNextAdd(groupKey, ruleName) {
      const path = [...this.cfgRulePath(groupKey, ruleName), "actions"];
      const list = [...this.cfgPluginList(groupKey, ruleName, "actions")];
      list.push({ ignore_next_action_error: "true" });
      this.cfgSetPath(path, list);
    },
    cfgPluginRemove(groupKey, ruleName, listName, index) {
      const path = [...this.cfgRulePath(groupKey, ruleName), listName];
      const list = [...this.cfgPluginList(groupKey, ruleName, listName)];
      list.splice(index, 1);
      if (list.length) this.cfgSetPath(path, list);
      else this.cfgDelPath(path);
    },
    cfgPluginMove(groupKey, ruleName, listName, index, delta) {
      const path = [...this.cfgRulePath(groupKey, ruleName), listName];
      const list = [...this.cfgPluginList(groupKey, ruleName, listName)];
      const target = index + delta;
      if (target < 0 || target >= list.length) return;
      const [moved] = list.splice(index, 1);
      list.splice(target, 0, moved);
      this.cfgSetPath(path, list);
    },

    /* ---------------------------------------------------------- spec 读写 */

    cfgSpecPath(groupKey, ruleName, listName, index, extra) {
      const entry = this.cfgPluginEntry(groupKey, ruleName, listName, index);
      const name = this.cfgPluginName(entry);
      return [...this.cfgRulePath(groupKey, ruleName), listName, index, name, ...(extra || [])];
    },
    cfgSpecRaw(groupKey, ruleName, listName, index) {
      const entry = this.cfgPluginEntry(groupKey, ruleName, listName, index);
      return entry ? entry[this.cfgPluginName(entry)] : undefined;
    },
    cfgSpecSet(groupKey, ruleName, listName, index, value) {
      const entry = this.cfgPluginEntry(groupKey, ruleName, listName, index);
      const name = this.cfgPluginName(entry);
      if (!name) return;
      this.cfgSetPath([...this.cfgRulePath(groupKey, ruleName), listName, index, name], value);
    },
    /* 列表形态 spec: 值为数组(YAML 单值亦归一为数组, 与插件解析一致) */
    cfgSpecList(groupKey, ruleName, listName, index) {
      const v = this.cfgSpecRaw(groupKey, ruleName, listName, index);
      if (Array.isArray(v)) return v;
      return v === undefined || v === null || v === "" ? [] : [v];
    },
    cfgSpecListItemSet(groupKey, ruleName, listName, index, i, value) {
      const list = [...this.cfgSpecList(groupKey, ruleName, listName, index)];
      list[i] = value;
      this.cfgSpecSet(groupKey, ruleName, listName, index, list);
    },
    cfgSpecListItemAdd(groupKey, ruleName, listName, index, meta) {
      const list = [...this.cfgSpecList(groupKey, ruleName, listName, index)];
      list.push(meta && meta.placeholder ? meta.placeholder : "");
      this.cfgSpecSet(groupKey, ruleName, listName, index, list);
    },
    cfgSpecListItemRemove(groupKey, ruleName, listName, index, i) {
      const list = [...this.cfgSpecList(groupKey, ruleName, listName, index)];
      list.splice(i, 1);
      if (list.length) this.cfgSpecSet(groupKey, ruleName, listName, index, list);
      else this.cfgSpecSet(groupKey, ruleName, listName, index, []);
    },
    /* 单值形态 spec: 直接读写成字符串 */
    cfgSpecText(groupKey, ruleName, listName, index) {
      const v = this.cfgSpecRaw(groupKey, ruleName, listName, index);
      return v === undefined || v === null ? "" : String(v);
    },
    cfgSpecBool(groupKey, ruleName, listName, index) {
      const v = this.cfgSpecRaw(groupKey, ruleName, listName, index);
      if (typeof v === "boolean") return v;
      return ["true", "1", "yes", "on"].includes(String(v === undefined ? "false" : v).trim().toLowerCase());
    },
    /* spec 的渲染项: 统一映射为通用字段项, 从而复用同一套控件(无 YAML 片段兜底) */
    cfgSpecItems(groupKey, ruleName, listName, index) {
      const entry = this.cfgPluginEntry(groupKey, ruleName, listName, index);
      const meta = this.cfgPluginMeta(entry);
      if (!meta) return [];
      const specPath = this.cfgSpecPath(groupKey, ruleName, listName, index);
      if (meta.spec_kind === "object") return this.cfgFlatten(meta.fields, specPath, 1, specPath);
      const raw = meta.spec_kind === "list" ? (meta.item_kind === "pattern" ? "pattern_list" : "str_list") : meta.spec_kind;
      // expr = 表达式: 用多行文本框(单行放不下), 校验交给后端配置期解析
      const kind = raw === "expr" ? "text" : raw;
      return [
        {
          type: "field",
          bare: true,  // 无标签整行布局: 插件名与说明已由卡片头提供, 避免重复
          field: {
            key: meta.name,
            label: meta.label,
            kind: kind,
            default: null,
            options: meta.options || [],
            placeholder: meta.placeholder || "",
            help: "",
          },
          path: specPath,
          depth: 0,
          owner: [],
        }
      ];
    },
    /* 切换条目使用的插件(重置为该插件的默认 spec) */
    cfgPluginReplace(groupKey, ruleName, listName, index, pluginName) {
      const entry = this.cfgPluginEntry(groupKey, ruleName, listName, index);
      if (!pluginName || pluginName === this.cfgPluginName(entry)) return;
      this.cfgSetPath([...this.cfgRulePath(groupKey, ruleName), listName, index], {
        [pluginName]: this.cfgPluginDefaultSpec(pluginName),
      });
    },
    /* 新增条目时的 spec 初始值: 必填字段用 schema 默认值/占位符填充, 让新条目可直接通过校验 */
    cfgPluginDefaultSpec(pluginName) {
      const meta = this.cfgPluginIndex[pluginName];
      if (!meta) return "";
      if (meta.spec_kind === "list") return [];
      if (meta.spec_kind === "bool") return "true";
      if (meta.spec_kind === "enum") return (meta.options && meta.options[0]) || "";
      // expr = 单行表达式: 初值用占位示例(让新条目可直接通过后端校验)
      if (meta.spec_kind === "str" || meta.spec_kind === "speed" || meta.spec_kind === "expr") {
        return meta.placeholder || "";
      }
      const spec = {};
      for (const f of meta.fields || []) {
        if (!f.required) continue;
        if (f.kind === "bool") spec[f.key] = "false";
        else if (f.kind === "enum") spec[f.key] = (f.options && f.options[0]) || "";
        else if (f.kind === "object") spec[f.key] = this.cfgPluginDefaultSection(f);
        else spec[f.key] = f.placeholder || (f.default === null || f.default === undefined ? "" : String(f.default));
      }
      return spec;
    },
    cfgPluginDefaultSection(field) {
      const section = {};
      for (const f of field.fields || []) {
        if (f.kind === "enum") section[f.key] = (f.options && f.options[0]) || "";
        else section[f.key] = f.kind === "bool" ? "false" : f.placeholder || String(f.default === null || f.default === undefined ? "" : f.default);
      }
      return section;
    },

    /* ---------------------------------------------------------- 规则级字段与动作可用性 */

    cfgRuleItems(groupKey, ruleName) {
      if (!this.cfg.schema) return [];
      return this.cfgFlatten(this.cfg.schema.rule_fields, this.cfgRulePath(groupKey, ruleName), 0);
    },

    /* ---------------------------------------------------------- 规则卡交互(折叠/启用/摘要) */

    cfgRuleKey(groupKey, ruleName) {
      return `${groupKey}::${ruleName}`;
    },
    /* 规则卡缺省折叠(用户要求): 只显示摘要行(触发器 · 条件数 · 动作数)与风险提示, 展开是主动选择 */
    cfgRuleCollapsed(groupKey, ruleName) {
      return !this.cfg.openRules[this.cfgRuleKey(groupKey, ruleName)];
    },
    cfgRuleToggle(groupKey, ruleName) {
      const k = this.cfgRuleKey(groupKey, ruleName);
      this.cfg.openRules = { ...this.cfg.openRules, [k]: !this.cfg.openRules[k] };
    },
    cfgRuleEnabled(groupKey, ruleName) {
      return this.cfgBool([...this.cfgRulePath(groupKey, ruleName), "enabled"], "true");
    },
    cfgRuleSetEnabled(groupKey, ruleName, on) {
      this.cfgSetBool([...this.cfgRulePath(groupKey, ruleName), "enabled"], on);
    },
    /* 卡头摘要(折叠时也能看出规则规模) */
    cfgRuleSummary(groupKey, ruleName) {
      const conds = this.cfgPluginList(groupKey, ruleName, "conditions").length;
      const acts = this.cfgPluginList(groupKey, ruleName, "actions").length;
      return `${this.cfgRuleTrigger(groupKey, ruleName)} · 条件 ${conds} · 动作 ${acts}`;
    },

    /* ---------------------------------------------------------- 条件/动作选择面板(单例) */

    cfgPickerIsOpen(groupKey, ruleName, listName) {
      const p = this.cfg.picker;
      return !!p.open && p.groupKey === groupKey && p.ruleName === ruleName && p.list === listName;
    },
    cfgPickerOpen(groupKey, ruleName, listName) {
      this.cfg.picker = this.cfgPickerIsOpen(groupKey, ruleName, listName) ?
        { open: false, groupKey: "", ruleName: "", list: "" } :
        { open: true, groupKey: groupKey, ruleName: ruleName, list: listName };
    },
    cfgPickerClose() {
      this.cfg.picker = { open: false, groupKey: "", ruleName: "", list: "" };
    },
    cfgRuleTrigger(groupKey, ruleName) {
      return this.cfgText([...this.cfgRulePath(groupKey, ruleName), "trigger"], "interval");
    },
    /* 动作可选集合按 trigger 过滤(与后端 validation.DELETED_TRIGGER_ALLOWED_ACTIONS 同源) */
    cfgActionOptions(groupKey, ruleName) {
      if (!this.cfg.schema) return [];
      const trigger = this.cfgRuleTrigger(groupKey, ruleName);
      const allowed = (this.cfg.schema.constants && this.cfg.schema.constants.deleted_allowed_actions) || [];
      return this.cfg.schema.plugins.action.filter((p) => trigger !== "on_torrent_deleted" || allowed.includes(p.name));
    },
    cfgConditionOptions() {
      return this.cfg.schema ? this.cfg.schema.plugins.condition : [];
    },
    /* 高风险提示汇总: 高风险动作清单 + 去重缺失(汇报/校验类反复执行有风险) */
    cfgRuleRisk(groupKey, ruleName) {
      const path = this.cfgRulePath(groupKey, ruleName);
      const names = this.cfgPluginList(groupKey, ruleName, "actions").map((e) => this.cfgPluginName(e));
      const risky = names.filter((n) => this.cfgPluginIndex[n] && this.cfgPluginIndex[n].risk);
      const once = this.cfgText([...path, "execute_once"], "never");
      const cooldown = this.cfgText([...path, "cooldown"], "0S");
      const noDedup = once === "never" && (cooldown === "0S" || cooldown === "0" || cooldown === "");
      const notes = [];
      if (risky.length) notes.push(`含高风险动作: ${risky.join(", ")}`);
      if (noDedup && (risky.includes("reannounce") || risky.includes("checking"))) {
        notes.push("未配置去重(执行一次/冷却), 高频触发有风险");
      }
      return notes.join("; ");
    },
  },
};
