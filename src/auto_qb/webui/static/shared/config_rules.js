/* auto-qb WEB UI 配置编辑器 · 规则集专段(条件/动作全量图形化, 无 YAML 片段兜底)
 *
 * 与 config_editor.js 同为一个 Vue 全局 mixin(方法名统一 cfg* 前缀, 无重名冲突)。
 *
 * 结构映射(YAML 形状):
 *   <规则集>_rules:
 *       <规则名>:
 *           enabled/trigger/interval/execute_once/cooldown/watch_fields:
 *                       规则级字段(schema.rule_fields, 「触发与节奏」折叠段, hub-field 通用渲染;
 *                       stop_following_rules_if 已退役, 键面保留识别, 见 cfgRuleRetiredKeys)
 *           conditions: [{<插件名>: <spec>}, ...]
 *           actions:    [{<插件名>: <spec>} | {<插件名>: <spec>, on_error: {...}}, ...]
 *                       on_error(W2-B/D8): 动作级失败策略控件(见 cfgOnError* 方法族),
 *                       读侧兼容规范形 {type, params, on_error}(cfgPluginName/cfgSpecPath)
 *
 * spec 形态由 schema 的 Plugin.spec_kind 决定: str/enum/speed 单值, bool 开关, list 列表, object 子表单。
 * 动作可选集合按 trigger 过滤(与后端 validation 的删除触发白名单同源)。
 */

/* 插件 spec 的**单值形态**取值域(对应后端 schema/fields.py::Plugin 的 spec_kind 文档串)
 * —— 不在此列的形态按子表单(object)造初值(旧口径: 未知形态也走子表单)。新增单值形态
 *    只要往这列加一项, 默认值规则由 cfgDefaultScalar 统一给(issue 26-10-20-2231)。 */
const SPEC_SCALAR_KINDS = ["str", "speed", "expr", "enum", "bool"];

/* 条件组合树 UI 嵌套软上限(W3-B): 后端硬上限 16 层(CONDITION_TREE_MAX_DEPTH), UI 到这里
 * 就不再给「添加组合」入口(防误操作嵌出不可维护的深树); 仍可手写 YAML 超出。 */
const CFG_COND_UI_MAX_DEPTH = 8;

/* choose 编排块键面(W3-B, 与后端 compat.CHOOSE_KNOWN_KEYS / CHOOSE_BRANCH_KEYS 同源) */
const CFG_CHOOSE_KEYS = ["choose", "default"];
const CFG_CHOOSE_BRANCH_KEYS = ["when", "then"];
const CFG_COND_COMBO_KEYS = ["all", "any", "not"];

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
    /* 两键退役检测(D1, plan 26-11-01-0106 W1): stop_following_rules_if /
     * ignore_next_action_error 已退场 —— 载入层(rules_mod)把含键规则转未启用 + warning,
     * 但不回写 config.yml; webui 直接从规则 spec 检测键名出升级提示面(未启用徽标 + 卡脚
     * 提示), 判定口径与后端 retired_control_keys_in 同源(规则级键 + actions 域伪动作项)。 */
    cfgRuleRetiredKeys(groupKey, ruleName) {
      const spec = this.cfgRaw(this.cfgRulePath(groupKey, ruleName));
      if (!spec || typeof spec !== "object") return [];
      const keys = [];
      if ("stop_following_rules_if" in spec) keys.push("stop_following_rules_if");
      if (this.cfgActionsContainRetired(spec.actions)) {
        keys.push("ignore_next_action_error");
      }
      return keys;
    },
    /* actions 域退役伪动作判定(含 choose 分支 then/块级 default 的嵌套项, issue 26-11-03-1120):
     * 与后端 retired_control_keys_in 同口径递归 —— 只扫顶层时嵌套伪动作的升级提示面无声。 */
    cfgActionsContainRetired(actions) {
      return (actions || []).some((a) => {
        if (!a || typeof a !== "object") return false;
        if (this.cfgIsRetiredAction(a)) return true;
        if (Array.isArray(a.choose)
          && a.choose.some((br) => br && typeof br === "object" && this.cfgActionsContainRetired(br.then))) {
          return true;
        }
        return Array.isArray(a.default) && this.cfgActionsContainRetired(a.default);
      });
    },
    /* actions 域伪动作项识别(退役键自身): 不再当可渲染动作(hubPluginText 显示退役标记)
     * W2-B: 规范形 {type, params, on_error}(手写 YAML 经载入规范化的形态)同样识别。 */
    cfgIsRetiredAction(entry) {
      if (!entry || typeof entry !== "object") return false;
      if ("type" in entry) return entry.type === "ignore_next_action_error";
      return "ignore_next_action_error" in entry;
    },
    /* 卡脚升级提示(单点口径, 模板只引用; 话术与后端 _warn_retired_rule 对齐) */
    cfgRuleRetiredHint(groupKey, ruleName) {
      const keys = this.cfgRuleRetiredKeys(groupKey, ruleName);
      if (!keys.length) return "";
      let msg = "含已退役控制键(" + keys.join(", ") + "): 引擎载入时自动转为未启用(enabled=false), "
        + "规则内容原样保留, 请改写后重新启用";
      if (keys.includes("ignore_next_action_error")) {
        msg += "; ignore_next_action_error 的等价新写法: on_error: {policy: continue}";
      }
      return msg;
    },
    cfgPluginName(entry) {
      if (!entry || typeof entry !== "object") return "";
      if ("type" in entry) return String(entry.type); // 规范形(W2-B: {type, params, on_error})
      // 扁平形 / webui 混合形({动作键: 值, on_error: {...}}): on_error 不是插件名
      const keys = Object.keys(entry).filter((k) => k !== "on_error");
      return keys.length ? keys[0] : "";
    },
    cfgPluginMeta(entry) {
      return this.cfgPluginIndex[this.cfgPluginName(entry)] || null;
    },

    /* ---------------------------------------------------------- 增删与排序 */

    cfgPluginAdd(groupKey, ruleName, listName, pluginName) {
      const path = [...this.cfgRulePath(groupKey, ruleName), listName];
      const list = [...this.cfgPluginList(groupKey, ruleName, listName)];
      // W3-B(D2)起写规范形 {type, params, on_error}(载入链 normalize 幂等同构), 不再写旧扁平形
      list.push({
        type: pluginName,
        params: this.cfgDefaultForPlugin(this.cfgPluginIndex[pluginName]),
        on_error: { ...this.cfgOnErrorDefaults() },
      });
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

    cfgSpecPathAt(entryPath, extra) {
      /* 路径版 spec 定位(W3-B): entryPath = 动作/条件条目(单键 dict 或规范形)的路径 */
      const entry = this.cfgRaw(entryPath);
      const name = this.cfgPluginName(entry);
      // 规范形 {type, params, on_error}: spec 落在 params 键; 扁平/混合形: spec 落在动作名键
      const specKey = entry && typeof entry === "object" && "type" in entry ? "params" : name;
      return [...entryPath, specKey, ...(extra || [])];
    },
    cfgSpecPath(groupKey, ruleName, listName, index, extra) {
      return this.cfgSpecPathAt([...this.cfgRulePath(groupKey, ruleName), listName, index], extra);
    },
    /* spec 的渲染项: 统一映射为通用字段项, 从而复用同一套控件(无 YAML 片段兜底)
     * 路径版 cfgSpecItemsAt(W3-B)是本体 —— 供条件树叶节点(组合树路径)与动作卡共用 */
    cfgSpecItemsAt(entryPath) {
      const entry = this.cfgRaw(entryPath);
      const meta = this.cfgPluginMeta(entry);
      if (!meta) return [];
      const specPath = this.cfgSpecPathAt(entryPath);
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
    cfgSpecItems(groupKey, ruleName, listName, index) {
      return this.cfgSpecItemsAt([...this.cfgRulePath(groupKey, ruleName), listName, index]);
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
        this.toast("校验通过: 用到取值 " + used, "ok");
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
      // 非单值形态(含 object 与任何未知形态, 沿用旧口径)-> 按子字段造对象, 必填优先 + object 子段递归
      if (!SPEC_SCALAR_KINDS.includes(meta.spec_kind)) {
        return this.cfgDefaultForFields(meta.fields, { requiredOnly: true, recurse: true });
      }
      return this.cfgDefaultScalar(
        { kind: meta.spec_kind, options: meta.options, placeholder: meta.placeholder },
        { boolOn: meta.spec_kind === "bool" }
      );
    },

    /* ---------------------------------------------------------- 动作 on_error(W2-B, D8)
     * 动作卡「失败策略」控件: policy 三档(缺省 stop = 现行失败即止; continue 替代退役布尔;
     * retry = 任务级 requeue, 附 retries/backoff 数字输入)。默认值取后端 schema constants
     * (on_error_policies / on_error_defaults, 与载入链 normalize 注入的缺省同源)。
     * 写树口径: 全部为缺省值时不写(与 hub-field「未动过的键不写进树」一致), 改出非缺省组合
     * 才写 on_error —— 写出形态 = 动作键 + on_error 的混合形, 载入链 normalize 单点
     * (config/compat.py)翻译成 {type, params, on_error} 规范形。 */
    cfgOnErrorDefaults() {
      const c = this.cfg.schema && this.cfg.schema.constants;
      return (c && c.on_error_defaults) || { policy: "stop", retries: 3, backoff: 60 };
    },
    cfgOnErrorPolicies() {
      const c = this.cfg.schema && this.cfg.schema.constants;
      return (c && c.on_error_policies) || ["stop", "continue", "retry"];
    },
    cfgOnErrorPath(groupKey, ruleName, i, key) {
      return [...this.cfgRulePath(groupKey, ruleName), "actions", i, "on_error", key];
    },
    cfgOnErrorValue(groupKey, ruleName, i, key) {
      const def = this.cfgOnErrorDefaults()[key];
      return String(this.cfgVal(this.cfgOnErrorPath(groupKey, ruleName, i, key), def));
    },
    cfgOnErrorIsRetry(groupKey, ruleName, i) {
      return this.cfgOnErrorValue(groupKey, ruleName, i, "policy") === "retry";
    },
    cfgOnErrorSet(groupKey, ruleName, i, key, value) {
      this.cfgSetPath(this.cfgOnErrorPath(groupKey, ruleName, i, key), String(value));
      this.cfgOnErrorPruneIfDefault(groupKey, ruleName, i);
    },
    /* on_error 全部回缺省时整键摘除, YAML 保持简洁(后端 normalize 会注入同值缺省) */
    cfgOnErrorPruneIfDefault(groupKey, ruleName, i) {
      const def = this.cfgOnErrorDefaults();
      const base = [...this.cfgRulePath(groupKey, ruleName), "actions", i, "on_error"];
      const cur = this.cfgRaw(base);
      if (!cur || typeof cur !== "object") return;
      const clean = Object.keys(cur).every((k) => String(cur[k]) === String(def[k]));
      if (clean) this.cfgDelPath(base);
    },

    /* ---------------------------------------------------------- 规则卡交互(启用/摘要) */

    cfgRuleEnabled(groupKey, ruleName) {
      return this.cfgBool([...this.cfgRulePath(groupKey, ruleName), "enabled"], "true");
    },
    cfgRuleSetEnabled(groupKey, ruleName, on) {
      this.cfgSetBool([...this.cfgRulePath(groupKey, ruleName), "enabled"], on);
    },
    /* 卡头摘要(折叠时也能看出规则规模); 条件数 = 组合树叶子数(W3-A 树形, W3-B 起草稿已归一) */
    cfgRuleSummary(groupKey, ruleName) {
      const conds = this.cfgCondCount(this.cfgCondRootPath(groupKey, ruleName));
      const acts = this.cfgPluginList(groupKey, ruleName, "actions").length;
      return `${this.cfgTriggerLabel(this.cfgRuleTrigger(groupKey, ruleName))} · 条件 ${conds} · 动作 ${acts}`;
    },

    /* ---------------------------------------------------------- 规则级字段(触发与节奏)
     *
     * 规则卡除条件/动作外还有一排规则级字段(trigger/interval/execute_once/cooldown/
     * watch_fields; stop_following_rules_if 已退役但键面保留识别, 仍随 rule_fields 渲染
     * 并带「已退役」帮助文案) —— 全部来自 schema.rule_fields(后端已在
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
      return !!this.cfg.openRuleMeta[this.hubKey(this.cfgRulePath(groupKey, ruleName))];
    },
    cfgRuleMetaToggle(groupKey, ruleName) {
      const key = this.hubKey(this.cfgRulePath(groupKey, ruleName));
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

    /* ---------------------------------------------------------- 草稿规范化(D2, W3-A/W3-B)
     * cfgSetTree 载入链单点调用: 规则集草稿树**就地**规范化 ——
     *   - conditions: 旧扁平单键 dict 列表 -> 包隐式 `all:` 树(W3-A, 与后端
     *     compat.normalize_conditions 同构);
     *   - actions: 旧扁平/混合形 -> {type, params, on_error} 规范形 + 缺省 on_error 注入
     *     (W2-B 混合形写侧升级为全规范形写侧, plan D2); choose 编排块键面保留(W3-B),
     *     then/default 内动作项同样归一。
     * 效果: 打开设置页显示的即归一形(D2 验收前半), 保存即写新形态(验收后半) —— 后端
     * 载入链 normalize 幂等, 双侧同构零差异。基线快照在归一后建立, 打开不误报脏。 */
    cfgNormalizeRulesDraft() {
      const root = this.cfgRaw(["config"]);
      if (!root || typeof root !== "object") return;
      for (const [gk, group] of Object.entries(root)) {
        if (!gk.endsWith("_rules") || !group || typeof group !== "object") continue;
        for (const spec of Object.values(group)) {
          if (!spec || typeof spec !== "object" || Array.isArray(spec)) continue;
          if (Array.isArray(spec.conditions)) spec.conditions = { all: spec.conditions };
          if (Array.isArray(spec.actions)) spec.actions = spec.actions.map((a) => this.cfgNormalizeActionEntryDraft(a));
        }
      }
    },
    /* JS 镜像的单动作项漏斗(与后端 compat.normalize_action_entry 同构, 幂等): 只做形状
     * 翻译与缺省注入, 非法形状原样透传交后端校验器按扁平坐标报 */
    cfgNormalizeActionEntryDraft(entry) {
      if (!entry || typeof entry !== "object" || Array.isArray(entry)) return entry;
      if ("choose" in entry) {
        const out = { ...entry };
        if (Array.isArray(entry.choose)) {
          out.choose = entry.choose.map((br) => {
            if (!br || typeof br !== "object" || Array.isArray(br)) return br;
            if (!("when" in br) && !("then" in br)) return br;
            const nb = { ...br };
            if (Array.isArray(br.when)) nb.when = { all: br.when };
            if (Array.isArray(br.then)) nb.then = br.then.map((x) => this.cfgNormalizeActionEntryDraft(x));
            return nb;
          });
        }
        if (Array.isArray(entry.default)) out.default = entry.default.map((x) => this.cfgNormalizeActionEntryDraft(x));
        return out;
      }
      if (!("type" in entry)) {
        const keys = Object.keys(entry).filter((k) => k !== "on_error");
        if (keys.length === 1) {
          const name = keys[0];
          entry = {
            type: name,
            params: entry[name],
            ...Object.fromEntries(Object.entries(entry).filter(([k]) => k !== name)),
          };
        }
      }
      if ("type" in entry && entry.type !== "ignore_next_action_error") {
        const def = this.cfgOnErrorDefaults();
        if (!("on_error" in entry)) return { ...entry, on_error: { ...def } };
        const oe = entry.on_error;
        if (oe && typeof oe === "object" && !Array.isArray(oe)) {
          const missing = Object.keys(def).filter((k) => !(k in oe));
          if (missing.length) entry = { ...entry, on_error: { ...def, ...oe } };
        }
      }
      return entry;
    },

    /* ---------------------------------------------------------- 条件组合树编辑器(W3-A/W3-B, D2/D8)
     * conditions 规范化后是**一个节点**(组合 {all/any/not} 或叶子), 编辑器按树形递归渲染
     * (组件 aq-cond-node, 模板 tpl/rule-tree.html); 路径即树坐标(path 数组直达 cfg 树),
     * 增删改全部写树形 —— D2: 打开显示归一形, 保存写新形态。深径软上限
     * CFG_COND_UI_MAX_DEPTH(UI 不再给「添加组合」入口), 硬上限 16 在后端 fail-fast。 */
    cfgCondRootPath(groupKey, ruleName) {
      return [...this.cfgRulePath(groupKey, ruleName), "conditions"];
    },
    cfgCondHasTree(groupKey, ruleName) {
      return this.cfgExists(this.cfgCondRootPath(groupKey, ruleName));
    },
    cfgCondNodeRaw(path) {
      const node = this.cfgRaw(path);
      return node && typeof node === "object" && !Array.isArray(node) ? node : null;
    },
    cfgCondNodeKey(path) {
      const node = this.cfgCondNodeRaw(path);
      return node ? Object.keys(node)[0] || "" : "";
    },
    cfgCondComboLabel(key) {
      return { all: "全部满足", any: "任一满足", not: "不满足" }[key] || key;
    },
    /* 组合节点(all/any)的孩子列表路径; not 的孩子是单节点(路径 [..., "not"]) */
    cfgCondChildrenPath(path) {
      return [...path, this.cfgCondNodeKey(path)];
    },
    cfgCondChildren(path) {
      const v = this.cfgRaw(this.cfgCondChildrenPath(path));
      return Array.isArray(v) ? v : [];
    },
    cfgCondChildPath(path, i) {
      return [...this.cfgCondChildrenPath(path), i];
    },
    /* 组合键切换(all/any/not): 值随键搬 —— 切到 not 时列表收敛为第一个孩子(空列表给
     * {all: []} 占位, 树形恒合法), 切回 all/any 时单节点包成列表 */
    cfgCondSetCombo(path, key, newKey) {
      const node = this.cfgCondNodeRaw(path);
      if (!node || !CFG_COND_COMBO_KEYS.includes(newKey)) return;
      const value = node[key];
      let nv = value;
      if (newKey === "not") nv = Array.isArray(value) ? (value.length ? value[0] : { all: [] }) : value;
      else if (key === "not") nv = value === null || value === undefined ? [] : [value];
      this.cfgSetPath(path, { [newKey]: nv });
    },
    /* 在组合节点(path 处, all/any)添加孩子: 叶子条件或空组合节点 */
    cfgCondAddAt(path, kind, name) {
      if (!name) return;
      const item = kind === "group" ? { [name]: [] } : { [name]: this.cfgDefaultForPlugin(this.cfgPluginIndex[name]) };
      const list = [...this.cfgCondChildren(path), item];
      this.cfgSetPath(this.cfgCondChildrenPath(path), list);
    },
    /* 根级添加(设置页条件区下拉): 无树 -> 建隐式 all; 根是 all/any -> 追加孩子;
     * 根是叶子/not -> 包一层 all(合法树形, 语义 = all[原根, 新项]) */
    cfgCondRootAdd(groupKey, ruleName, kind, name) {
      const rp = this.cfgCondRootPath(groupKey, ruleName);
      const node = this.cfgCondNodeRaw(rp);
      if (!node) {
        this.cfgSetPath(rp, kind === "group" ? { [name]: [] } : { all: [{ [name]: this.cfgDefaultForPlugin(this.cfgPluginIndex[name]) }] });
        return;
      }
      const key = Object.keys(node)[0];
      if (key === "all" || key === "any") {
        this.cfgCondAddAt(rp, kind, name);
        return;
      }
      const first = kind === "group" ? { [name]: [] } : { [name]: this.cfgDefaultForPlugin(this.cfgPluginIndex[name]) };
      this.cfgSetPath(rp, { all: [node, first] });
    },
    /* 根是否为展开的 all/any 组合(决定设置页条件区是否渲染根级「添加」下拉) */
    cfgCondRootComboOpen(groupKey, ruleName) {
      const key = this.cfgCondNodeKey(this.cfgCondRootPath(groupKey, ruleName));
      return key === "all" || key === "any";
    },
    /* 删除 path 处的节点: 从父列表移除; 父列表因此变空则整节点向上收敛退场
     * (根节点退场 = 删 conditions 键 = 无条件直过, 与提示话术同语义) */
    cfgCondRemoveAt(path) {
      const listPath = path.slice(0, -1);
      const holder = this.cfgRaw(listPath);
      if (!Array.isArray(holder)) {
        this.cfgDelPath(listPath);  // 根节点: conditions 单键 dict 所在, 删 conditions 键
        return;
      }
      const list = [...holder];
      list.splice(path[path.length - 1], 1);
      if (list.length) {
        this.cfgSetPath(listPath, list);
        return;
      }
      const nodePath = listPath.slice(0, -1);  // 空组合节点自身路径(含组合键名, 如 [..., "conditions", "all"])
      const grand = this.cfgRaw(nodePath.slice(0, -1));
      if (Array.isArray(grand)) {
        this.cfgCondRemoveAt(nodePath);  // 祖父也是列表(嵌套组合): 递归向上收敛
      } else {
        this.cfgDelPath(nodePath);  // 祖父是规则 spec: 删组合键(根即 conditions 键) = 无条件直过
      }
    },
    /* 同层排序(父须为列表) */
    cfgCondMoveAt(path, delta) {
      const listPath = path.slice(0, -1);
      const list = this.cfgRaw(listPath);
      if (!Array.isArray(list)) return;
      const i = path[path.length - 1];
      const target = i + delta;
      if (target < 0 || target >= list.length) return;
      const nl = [...list];
      const [moved] = nl.splice(i, 1);
      nl.splice(target, 0, moved);
      this.cfgSetPath(listPath, nl);
    },
    cfgCondCanMove(path, delta) {
      const list = this.cfgRaw(path.slice(0, -1));
      if (!Array.isArray(list)) return false;
      const target = path[path.length - 1] + delta;
      return target >= 0 && target < list.length;
    },
    /* 条件树叶节点的 spec 渲染项(路径版; 与动作卡共用 cfgSpecItemsAt 的字段映射) */
    cfgCondSpecItems(path) {
      return this.cfgSpecItemsAt(path);
    },
    /* 组合树叶子计数(卡头摘要用): 组合节点递归, 叶子计 1 */
    cfgCondCount(path) {
      const node = this.cfgCondNodeRaw(path);
      if (!node) return 0;
      const key = Object.keys(node)[0];
      if (key === "all" || key === "any") {
        return (Array.isArray(node[key]) ? node[key] : []).reduce(
          (n, _c, i) => n + this.cfgCondCount([...path, key, i]), 0
        );
      }
      if (key === "not") return this.cfgCondCount([...path, "not"]);
      return 1;
    },
    cfgCondUiMaxDepth() {
      return CFG_COND_UI_MAX_DEPTH;
    },

    /* ---------------------------------------------------------- choose 编排块编辑器(W3-B, D8)
     * 动作列表项含 "choose" 键即编排块(草稿已归一, 键面 {choose, default}); 编辑器
     * (组件 aq-choose-block, 模板 tpl/rule-tree.html): 分支 = when 条件树(aq-cond-node)
     * + then 动作项列表, 外加可选 default; 块内动作项与顶层动作卡同语义(on_error 控件
     * 走路径版 cfgOnError*At 单点)。嵌套约束: choose 内不再给 choose 入口(后端 fail-fast)。 */
    cfgIsChooseEntry(entry) {
      return !!entry && typeof entry === "object" && !Array.isArray(entry) && "choose" in entry;
    },
    cfgChooseAdd(groupKey, ruleName) {
      const path = [...this.cfgRulePath(groupKey, ruleName), "actions"];
      const list = [...this.cfgPluginList(groupKey, ruleName, "actions")];
      list.push({ choose: [{ when: { all: [] }, then: [] }] });
      this.cfgSetPath(path, list);
    },
    cfgChooseBranches(groupKey, ruleName, i) {
      const v = this.cfgRaw([...this.cfgRulePath(groupKey, ruleName), "actions", i, "choose"]);
      return Array.isArray(v) ? v : [];
    },
    cfgChooseBranchPath(groupKey, ruleName, i, bi) {
      return [...this.cfgRulePath(groupKey, ruleName), "actions", i, "choose", bi];
    },
    cfgChooseBranchWhenPath(groupKey, ruleName, i, bi) {
      return [...this.cfgRulePath(groupKey, ruleName), "actions", i, "choose", bi, "when"];
    },
    cfgChooseBranchAdd(groupKey, ruleName, i) {
      const path = [...this.cfgRulePath(groupKey, ruleName), "actions", i, "choose"];
      this.cfgSetPath(path, [...this.cfgChooseBranches(groupKey, ruleName, i), { when: { all: [] }, then: [] }]);
    },
    cfgChooseBranchRemove(groupKey, ruleName, i, bi) {
      const path = [...this.cfgRulePath(groupKey, ruleName), "actions", i, "choose"];
      const list = [...this.cfgChooseBranches(groupKey, ruleName, i)];
      list.splice(bi, 1);
      if (list.length) this.cfgSetPath(path, list);
      else this.cfgListEntryRemove([...this.cfgRulePath(groupKey, ruleName), "actions", i]);  // 分支空了整块退场
    },
    cfgChooseHasDefault(groupKey, ruleName, i) {
      return this.cfgExists([...this.cfgRulePath(groupKey, ruleName), "actions", i, "default"]);
    },
    cfgChooseDefaultToggle(groupKey, ruleName, i, on) {
      const path = [...this.cfgRulePath(groupKey, ruleName), "actions", i, "default"];
      if (on) this.cfgSetPath(path, []);
      else this.cfgDelPath(path);
    },
    /* 通用列表条目移除(路径版): 列表空则整键摘除 */
    cfgListEntryRemove(entryPath) {
      const listPath = entryPath.slice(0, -1);
      const list = this.cfgRaw(listPath);
      if (!Array.isArray(list)) return;
      const nl = [...list];
      nl.splice(entryPath[entryPath.length - 1], 1);
      if (nl.length) this.cfgSetPath(listPath, nl);
      else this.cfgDelPath(listPath);
    },
    /* 动作项增删排(路径版): choose 的 then/default 与顶层动作列表共用 */
    cfgActionEntryAddAt(listPath, pluginName) {
      if (!pluginName) return;
      const list = Array.isArray(this.cfgRaw(listPath)) ? [...this.cfgRaw(listPath)] : [];
      list.push({
        type: pluginName,
        params: this.cfgDefaultForPlugin(this.cfgPluginIndex[pluginName]),
        on_error: { ...this.cfgOnErrorDefaults() },
      });
      this.cfgSetPath(listPath, list);
    },
    cfgActionEntryMoveAt(entryPath, delta) {
      const listPath = entryPath.slice(0, -1);
      const list = this.cfgRaw(listPath);
      if (!Array.isArray(list)) return;
      const i = entryPath[entryPath.length - 1];
      const target = i + delta;
      if (target < 0 || target >= list.length) return;
      const nl = [...list];
      const [moved] = nl.splice(i, 1);
      nl.splice(target, 0, moved);
      this.cfgSetPath(listPath, nl);
    },
    cfgActionEntryCanMove(entryPath, delta) {
      const list = this.cfgRaw(entryPath.slice(0, -1));
      if (!Array.isArray(list)) return false;
      const target = entryPath[entryPath.length - 1] + delta;
      return target >= 0 && target < list.length;
    },
    /* choose then/default 的动作项路径与列表(设置页模板坐标辅助) */
    cfgThenList(groupKey, ruleName, i, bi) {
      const v = this.cfgRaw([...this.cfgRulePath(groupKey, ruleName), "actions", i, "choose", bi, "then"]);
      return Array.isArray(v) ? v : [];
    },
    cfgThenEntryPath(groupKey, ruleName, i, bi, j) {
      return [...this.cfgRulePath(groupKey, ruleName), "actions", i, "choose", bi, "then", j];
    },
    cfgDefaultList(groupKey, ruleName, i) {
      const v = this.cfgRaw([...this.cfgRulePath(groupKey, ruleName), "actions", i, "default"]);
      return Array.isArray(v) ? v : [];
    },
    cfgDefaultEntryPath(groupKey, ruleName, i, j) {
      return [...this.cfgRulePath(groupKey, ruleName), "actions", i, "default", j];
    },
    cfgDefaultListPath(groupKey, ruleName, i) {
      return [...this.cfgRulePath(groupKey, ruleName), "actions", i, "default"];
    },
    cfgThenListPath(groupKey, ruleName, i, bi) {
      return [...this.cfgRulePath(groupKey, ruleName), "actions", i, "choose", bi, "then"];
    },

    /* on_error 控件的路径版(W3-B, choose 块内动作项用): 顶层动作卡仍用 (g, r, i) 签名族,
     * 两族同口径(缺省同源 / 非缺省才写树 / 全缺省整键摘除), 勿各改一套 */
    cfgOnErrorPathAt(entryPath, key) {
      return [...entryPath, "on_error", key];
    },
    cfgOnErrorValueAt(entryPath, key) {
      const def = this.cfgOnErrorDefaults()[key];
      return String(this.cfgVal(this.cfgOnErrorPathAt(entryPath, key), def));
    },
    cfgOnErrorIsRetryAt(entryPath) {
      return this.cfgOnErrorValueAt(entryPath, "policy") === "retry";
    },
    cfgOnErrorSetAt(entryPath, key, value) {
      this.cfgSetPath(this.cfgOnErrorPathAt(entryPath, key), String(value));
      const base = [...entryPath, "on_error"];
      const cur = this.cfgRaw(base);
      if (!cur || typeof cur !== "object") return;
      const def = this.cfgOnErrorDefaults();
      if (Object.keys(cur).every((k) => String(cur[k]) === String(def[k]))) this.cfgDelPath(base);
    },
  },
};

/* ---------------------------------------------------------- 组件定义(W3-A/W3-B, D2/D8)
 * 模板在 shared/tpl/rule-tree.html(x-template, tpl-manifest 注入 body); 本文件在 HTML 里
 * 排在 app.js 之前(app.js 末尾 app.component(...) 读 window.AQ_*), 与 ctl_bits.js 同范式
 * —— **组件只贡献模板与 props, 不持有任何业务状态**, 读写一律经 $root 回到 CONFIG_RULES
 * 方法族(aq-cond-node 递归渲染条件组合树; aq-choose-block 渲染 choose 编排块)。
 * 在组件里复写一份方法会触发 _scan_mixin_wiring 的重名守阵(被 Vue 合并策略盖掉的那份
 * 永不执行且不报错)。回调 prop 而非 emit: 与三件套同口径(见 ctl_bits.js 头注)。 */

/* 条件组合树节点 <aq-cond-node>(递归): path = 节点在 cfg 树中的坐标(数组), depth = 层深。
 * 组合节点(all/any/not)渲染键切换 + 孩子递归 + 添加/删除/排序; 叶子渲染与旧条件卡同款
 * (hub-field spec 控件走 cfgCondSpecItems 单点)。节点形状非法时给占位提示(保存会被
 * 后端校验拒绝, 前端不吞不装)。 */
window.AQ_COND_NODE_COMPONENT = {
  name: "aq-cond-node",
  /* inject/provide 不是可选项(traffic_card.js 头注同款判据): 全局 mixin(CONFIG_EDITOR) 给
   * **每个**组件都挂了 provide(){ce:this}, 本组件不显式透传的话, 叶子里的 <hub-field> 注入到的
   * ce 就是本组件实例(mixin data 新建的 cfg 副本, tree=null) —— 表现为叶子字段只显默认值、
   * 「＋ 添加」/「?」点着没反应(写入/弹层都落在坏副本上, 2026-11-11 用户报障复现实锤)。 */
  inject: ["ce"],
  provide() {
    return { ce: this.ce };
  },
  props: {
    path: { type: Array, required: true },
    depth: { type: Number, default: 1 },
  },
  computed: {
    node() {
      return this.$root.cfgCondNodeRaw(this.path);
    },
    comboKey() {
      return this.node ? this.$root.cfgCondNodeKey(this.path) : "";
    },
    isCombo() {
      return ["all", "any", "not"].includes(this.comboKey);
    },
    label() {
      return this.$root.cfgCondComboLabel(this.comboKey);
    },
    children() {
      return this.$root.cfgCondChildren(this.path);
    },
    notChildPath() {
      return [...this.path, "not"];
    },
    canMoveUp() {
      return this.$root.cfgCondCanMove(this.path, -1);
    },
    canMoveDown() {
      return this.$root.cfgCondCanMove(this.path, 1);
    },
    canAddGroup() {
      return this.depth < this.$root.cfgCondUiMaxDepth();
    },
  },
  methods: {
    childPath(i) {
      return [...this.path, this.comboKey, i];
    },
  },
  template: "#tpl-aq-cond-node",
};

/* choose 编排块 <aq-choose-block>(W3-B, D8): 分支(when 条件树 + then 动作项列表)按序 +
 * 可选 default。groupKey/ruleName/index 定位块在 cfg 树中的坐标; then/default 动作项渲染
 * 与顶层动作卡同构(spec 字段 + on_error 控件), 块内不再提供 choose 入口(编排块一层)。 */
window.AQ_CHOOSE_BLOCK_COMPONENT = {
  name: "aq-choose-block",
  /* ce 透传同 aq-cond-node(then/default 里也嵌 hub-field, 不透传同样坏副本) */
  inject: ["ce"],
  provide() {
    return { ce: this.ce };
  },
  props: {
    groupKey: { type: String, required: true },
    ruleName: { type: String, required: true },
    index: { type: Number, required: true },
  },
  computed: {
    branches() {
      return this.$root.cfgChooseBranches(this.groupKey, this.ruleName, this.index);
    },
    hasDefault() {
      return this.$root.cfgChooseHasDefault(this.groupKey, this.ruleName, this.index);
    },
  },
  template: "#tpl-aq-choose-block",
};
