/* config_editor_form.js — R4 大文件拆分(计划 26-11-02-2342 §07)
 * 配置编辑器 · 实体新增/重命名/删除(站点·Tracker·规则组·规则)。
 * 只搬方法定义, 实现逐行未改; 根文件已定义该域, 本片段在其后原地扩充(Object.assign)。
 * 加载序 = 四套皮肤 index.html 清单里紧跟根文件之后(与拆分前同一迭代替换序)。
 */
Object.assign(window.CONFIG_EDITOR.methods, {

    /* ---------------------------------------------------------- 命名实体增/改/删(单点骨架)
     *
     * 报告 26-10-20-2231(R20-C-01~04): 「新增有名实体 / 重命名 / 删除」这三个语义, 在站点
     * (config.trackers.<名>)、规则集(config.<组>_rules)、规则(config.<组>.<规则名>)上各抄过
     * 一遍 —— 骨架逐字相同(trim -> 空判 -> 查重 -> 写树 -> 同步选中键), 差异只有路径 / 文案 /
     * 初始值 / 选中键。这里收成三个参数化方法, 实体差异用 def 声明: 新口径(名称长度校验、
     * 保留字、删除前备份)只改这一处, 不再按实体各补一遍。
     *
     * def = {
     *   path:    实体容器(父层)的绝对路径; name 缺省 = 直接对 path 本身动手(如限速曲线整段)
     *   name:    实体键名(增 / 改 / 删的目标)
     *   label:   查重提示里的实体名(如 "站点")
     *   initial: 新增时的初始值(站点 spec / 规则集 {} / 规则 {conditions,actions})
     *   normalize: (name) => name, 新增前的键名规范化(规则集补 _rules 后缀; 缺省不改)
     *   select:  (name, oldName) => void, 增 / 改后把编辑器停在新实体上
     *   after:   () => void, 删除后的收尾(选中键回落到剩余首项 / 收走空父段)
     *   title / body / okText: 重命名与删除对话框的文案
     * }
     *
     * 入口分工: 增的命名交互在 config_hub.js 的 hubAddEntity(唯一调用方); 改 / 删的入口留在
     * 本文件(模板直接调 cfg*Rename / cfg*Remove)。两侧都只把 def 交给这三个骨架, 骨架只有一份。
     */
    cfgEntityAdd(def) {
      let name = String(def.name || "").trim();
      if (def.normalize) name = def.normalize(name);
      if (!name) return false;
      const path = [...def.path, name];
      if (this.cfgExists(path)) {
        this.toast(`名称冲突: ${def.label}「${name}」已存在`, "error");
        return false;
      }
      this.cfgSetPath(path, def.initial);
      if (def.select) def.select(name, null);
      return true;
    },
    async cfgEntityRename(def) {
      const input = await this.promptDialog(def.title, def.name, { okText: def.okText || "重命名" });
      if (input === null || input === undefined) return false;
      const name = String(input).trim();
      if (!name || name === def.name) return false;
      const container = this.cfgRaw(def.path);
      if (!container || typeof container !== "object") return false;
      if (container[name]) {
        this.toast(`名称冲突: ${def.label}「${name}」已存在`, "error");
        return false;
      }
      // 换键靠重建对象: 直接把值搬到新键会挪到末尾, 而列表顺序就是用户看到的实体顺序
      const rebuilt = {};
      for (const [k, v] of Object.entries(container)) rebuilt[k === def.name ? name : k] = v;
      this.cfgSetPath(def.path, rebuilt);
      if (def.select) def.select(name, def.name);
      return true;
    },
    async cfgEntityRemove(def) {
      const ok = await this.confirmDialog(def.title, def.body, { okText: def.okText || "删除", danger: true });
      if (!ok) return false;
      this.cfgDelPath(def.name === undefined ? def.path : [...def.path, def.name]);
      if (def.after) def.after();
      return true;
    },

    /* ---------------------------------------------------------- 站点编辑器 */

    cfgTrackerNames() {
      return Object.keys(this.cfgConfig().trackers || {});
    },
    cfgConfigPath() {
      return ["config"];
    },
    /* 站点实体差异清单(骨架见上方 cfgEntity*): 集合在 config.trackers 下, 选中键 trackerKey */
    cfgTrackerDef(name) {
      return {
        path: [...this.cfgConfigPath(), "trackers"],
        name,
        label: "站点",
        initial: this.cfgTrackerInitial(),
        select: (n) => { this.cfg.trackerKey = n; },
      };
    },
    /* 新站点的初始值: schema 声明为 str_list 的字段先给空数组, 其余键留空由后端走默认 */
    cfgTrackerInitial() {
      const spec = {};
      for (const f of (this.cfg.schema && this.cfg.schema.tracker_fields) || []) {
        if (f.kind === "str_list") spec[f.key] = [];
      }
      return spec;
    },
    async cfgTrackerRename(oldName) {
      return this.cfgEntityRename({ ...this.cfgTrackerDef(oldName), title: "重命名站点配置" });
    },
    async cfgTrackerRemove(name) {
      return this.cfgEntityRemove({
        ...this.cfgTrackerDef(name),
        title: `删除站点 ${name} 的配置`,
        body: "仅从配置文件中移除该站点段(不影响 qB 中的种子), 保存后生效。",
        okText: "删除",
        after: () => {
          // 最后一个站点删掉后连 trackers 段一起收走(留个空段在 YAML 里没有意义)
          const names = this.cfgTrackerNames();
          if (!names.length) this.cfgDelPath([...this.cfgConfigPath(), "trackers"]);
          this.cfg.trackerKey = names.length ? names[0] : null;
        },
      });
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
    /* 规则集实体差异清单: 集合在 config 根下, 选中键 ruleGroupKey; _rules 后缀是识别口径 */
    cfgRuleGroupDef(name) {
      return {
        path: this.cfgConfigPath(),
        name,
        label: "规则集",
        initial: {},
        // 后缀规范化放在骨架调用点(新增时才知道用户输入), 不预改 def.name —— 删除走的是既有键
        normalize: (n) => (n && !n.endsWith("_rules") ? n + "_rules" : n),
        select: (x) => { this.cfg.ruleGroupKey = x; },
      };
    },
    async cfgRuleRemoveGroup(name) {
      return this.cfgEntityRemove({
        ...this.cfgRuleGroupDef(name),
        title: `删除规则集 ${name}`,
        body: "该规则集下的全部规则将一并移除。",
        okText: "删除规则集",
        after: () => {
          const names = this.cfgRuleGroupNames();
          this.cfg.ruleGroupKey = names.length ? names[0] : null;
        },
      });
    },
    cfgRuleNames(groupKey) {
      const group = this.cfgRuleGroups()[groupKey] || {};
      return Object.keys(group);
    },
    /* 规则实体差异清单: 集合是所属规则集段; 规则没有独立选中键(选中由规则集决定) */
    cfgRuleDef(groupKey, name) {
      return {
        path: [...this.cfgConfigPath(), groupKey],
        name,
        label: "规则",
        // 新规则仅给 conditions/actions 两个空列表, 其余键留空由后端走默认值(保持 YAML 简洁)
        initial: { conditions: [], actions: [] },
      };
    },
    async cfgRuleRemove(groupKey, ruleName) {
      return this.cfgEntityRemove({
        ...this.cfgRuleDef(groupKey, ruleName),
        title: `删除规则 ${ruleName}`,
        body: "该规则的条件与动作配置将一并移除。",
        okText: "删除规则",
      });
    },
    async cfgRuleRename(groupKey, ruleName) {
      return this.cfgEntityRename({ ...this.cfgRuleDef(groupKey, ruleName), title: "重命名规则" });
    },
    cfgRulePath(groupKey, ruleName) {
      return [...this.cfgConfigPath(), groupKey, ruleName];
    },
});
