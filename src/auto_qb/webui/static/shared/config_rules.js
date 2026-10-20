/* auto-qb WEB UI 配置编辑器 · 规则集专段(条件/动作全量图形化, 无 YAML 片段兜底)
 *
 * 与 config_editor.js 同为一个 Vue 全局 mixin(方法名统一 cfg* 前缀, 无重名冲突)。
 *
 * 结构映射(YAML 形状):
 *   <规则集>_rules:
 *       <规则名>:
 *           enabled/trigger/interval/execute_once/cooldown/stop_following_rules_if/watch_fields:
 *                       规则级字段(schema.rule_fields, 「触发与节奏」折叠段, hub-field 通用渲染)
 *           conditions: [{<插件名>: <spec>}, ...]
 *           actions:    [{<插件名>: <spec>}, ...]   # 或 {ignore_next_action_error: true} 伪动作
 *
 * spec 形态由 schema 的 Plugin.spec_kind 决定: str/enum/speed 单值, bool 开关, list 列表, object 子表单。
 * 动作可选集合按 trigger 过滤(与后端 validation 的删除触发白名单同源)。
 */

/* 插件 spec 的**单值形态**取值域(对应后端 schema/fields.py::Plugin 的 spec_kind 文档串)
 * —— 不在此列的形态按子表单(object)造初值(旧口径: 未知形态也走子表单)。新增单值形态
 *    只要往这列加一项, 默认值规则由 cfgDefaultScalar 统一给(issue 26-10-20-2231)。 */
const SPEC_SCALAR_KINDS = ["str", "speed", "expr", "enum", "bool"];

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
      list.push({ [pluginName]: this.cfgDefaultForPlugin(this.cfgPluginIndex[pluginName]) });
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
    /* 表达式「试算」(expr 条件的按钮): 调后端 /api/expr/eval
     *
     * 留空 hash = 只做编译 + 语义校验(语法/名字拼写错的即时反馈, 不用等保存);
     * 填 hash = 用该种子求值并显示**中间值**(看清每个名字到底取到了什么)。
     * 取消/关闭对话框一律不发请求(与项目其它确认/输入原语同口径)。 */
    async cfgExprTry(path) {
      const text = this.cfgText(path, "");
      const input = await this.promptDialog("表达式试算", "", {
        placeholder: "种子 hash(留空 = 只校验语法与取值名)",
        okText: "试算",
      });
      if (input === null || input === undefined) return;
      let data;
      try {
        data = await this.api("/api/expr/eval", {
          method: "POST",
          body: JSON.stringify({
            text: text,
            hash: String(input || "").trim()
          }),
        });
      } catch (e) {
        this.toast("试算失败: " + ((e && e.message) || e), "error");
        return;
      }
      const used = (data.used || []).join("、") || "无";
      if (!data.ok) {
        this.toast("表达式有误: " + data.error, "error");
        return;
      }
      if (data.value === null || data.value === undefined) {
        this.toast("校验通过(用到取值: " + used + ")", "ok");
        return;
      }
      const detail = (data.trace || []).map((t) => t.name + "=" + JSON.stringify(t.value)).join("; ");
      this.toast("试算结果: " + data.value + (detail ? " [" + detail + "]" : ""), data.value ? "ok" : "info");
    },

    /* 新增条目时的 spec 初始值: 必填字段用 schema 默认值/占位符填充, 让新条目可直接通过校验
     *
     * 阶梯本体在 config_editor.js(cfgDefaultScalar / cfgDefaultForFields) —— 本处只做**插件形态分派**:
     * spec_kind 决定取列表 / 子表单 / 叶子标量, 叶子那支连「插件 bool 初值 = "true"、字段 bool = "false"」
     * 这个分歧也一并交给 cfgDefaultScalar 的 boolOn 开关(此前是两份代码各自写死)。 */
    cfgDefaultForPlugin(meta) {
      if (!meta) return "";
      if (meta.spec_kind === "list") return [];
      // 非单值形态(含 object 与任何未知形态, 沿用旧口径)→ 按子字段造对象, 必填优先 + object 子段递归
      if (!SPEC_SCALAR_KINDS.includes(meta.spec_kind)) {
        return this.cfgDefaultForFields(meta.fields, { requiredOnly: true, recurse: true });
      }
      return this.cfgDefaultScalar(
        { kind: meta.spec_kind, options: meta.options, placeholder: meta.placeholder },
        { boolOn: meta.spec_kind === "bool" }
      );
    },

    /* ---------------------------------------------------------- 规则卡交互(启用/摘要) */

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
      return `${this.cfgTriggerLabel(this.cfgRuleTrigger(groupKey, ruleName))} · 条件 ${conds} · 动作 ${acts}`;
    },

    /* ---------------------------------------------------------- 规则级字段(触发与节奏)
     *
     * 规则卡除条件/动作外还有一排规则级字段(trigger/interval/execute_once/cooldown/
     * stop_following_rules_if/watch_fields) —— 全部来自 schema.rule_fields(后端已在
     * /api/config/schema 载荷里), 用 cfgFlatten 展开成通用字段项交给 hub-field 渲染,
     * 控件形态(枚举下拉/数值+单位/列表)与帮助、「?」、条件显隐(show_if)零特判复用。 */
    /* 触发时机的中文短标签(卡头摘要与「触发与节奏」摘要共用单点) */
    cfgTriggerLabel(trigger) {
      return (
        {
          interval: "周期检查",
          on_torrent_added: "种子新增时",
          on_torrent_deleted: "种子删除时",
          on_torrent_state_enum_changed: "状态变化时",
          on_torrent_field_changed: "字段变化时",
        }[trigger] || trigger || "周期检查"
      );
    },
    /* 规则级字段渲染项: 去掉 enabled(卡头已有启用开关, 不重复渲染);
     * enum 字段(trigger/execute_once/stop_following_rules_if)缺省走后端默认、空串非法 ——
     * 克隆标 required 摘掉「(未配置)」空选项, 防止写出保存必败的空值(默认值仍由
     * cfgInputValue 兜底显示, 未动过的键不会写进树, YAML 保持简洁) */
    cfgRuleMetaItems(groupKey, ruleName) {
      if (!this.cfg.schema || !this.cfg.schema.rule_fields) return [];
      const path = this.cfgRulePath(groupKey, ruleName);
      const fields = this.cfg.schema.rule_fields
        .filter((f) => f.key !== "enabled")
        .map((f) => (f.kind === "enum" ? { ...f, required: true } : f));
      return this.cfgFlatten(fields, path, 0, path);
    },
    /* 折叠态(缺省 = 折叠, 与设置页 group 段同口径): 摘要行常显当前值, 不展开也能看出节奏 */
    cfgRuleMetaOpen(groupKey, ruleName) {
      return !!this.cfg.openRuleMeta[this.cfgRulePath(groupKey, ruleName).join(".")];
    },
    cfgRuleMetaToggle(groupKey, ruleName) {
      const key = this.cfgRulePath(groupKey, ruleName).join(".");
      this.cfg.openRuleMeta = { ...this.cfg.openRuleMeta, [key]: !this.cfg.openRuleMeta[key] };
    },
    /* 「触发与节奏」折叠头摘要: 触发时机 + 非默认的间隔/去重/冷却(默认值不占摘要, 展开可见全部) */
    cfgRuleMetaSummary(groupKey, ruleName) {
      const path = this.cfgRulePath(groupKey, ruleName);
      const trigger = this.cfgRuleTrigger(groupKey, ruleName);
      const parts = [this.cfgTriggerLabel(trigger)];
      if (trigger === "interval") {
        const iv = String(this.cfgText([...path, "interval"], "") || "").trim();
        if (iv && iv !== "0" && iv !== "0S") parts.push(`间隔 ${iv}`);
      }
      const onceLabel = { once: "仅执行一次", daily: "每天一次", hourly: "每小时一次" }[
        this.cfgText([...path, "execute_once"], "never")
      ];
      if (onceLabel) parts.push(onceLabel);
      const cd = String(this.cfgText([...path, "cooldown"], "0S") || "").trim();
      if (cd && cd !== "0" && cd !== "0S") parts.push(`冷却 ${cd}`);
      return parts.join(" · ");
    },

    /* ---------------------------------------------------------- 条件/动作选择面板(单例) */

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
