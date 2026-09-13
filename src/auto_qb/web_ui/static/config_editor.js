/* auto-qb WEB UI 图形化配置编辑器(Vue 3 全局 mixin, 无构建链)
 *
 * 设计要点(与 ai/06 约定一致):
 * - 前端持有**与磁盘同构的 YAML 树**(标量全为字符串), 编辑即就地增删改, 不做任何格式转换 → 零漂移
 * - `schema`(来自 /api/config/schema)只决定"怎么渲染 + 怎么提示", 不承载正确性规则;
 *   合法性唯一入口仍是后端 load_config —— 保存失败时 400 返回可读错误并原样展示
 * - 脏检测用 JSON 快照对比; 保存成功后重新拉取树(后端会把 R 级字段回退为旧值)
 * - 字段渲染采用"扁平化"列表(嵌套 object 展开为带缩进的多行), 模板只需一套分支
 */
window.CONFIG_EDITOR = {
  data() {
    return {
      cfg: {
        schema: null,  // /api/config/schema 元数据(分组/字段/插件/常量/热重载级别)
        tree: null,  // 完整 YAML 文档树(含 config 根段)
        baseline: "",  // 已保存树的 JSON 快照(脏检测)
        loading: false,
        saving: false,
        error: "",  // 加载/保存错误(加载失败时整页替换, 保存失败时顶部横幅)
        notice: "",  // 成功提示
        noticeKind: "",  // ok | warn | error
        activeGroup: "basic",
        previewOpen: false,
        previewText: "",
        previewError: "",
        previewBusy: false,
        trackerKey: null,  // 站点编辑器当前选中站点
        newTrackerName: "",
        ruleGroupKey: null,  // 规则集编辑器当前选中规则集
        newRuleGroupName: "",
        newRuleName: "",
      },
    };
  },
  provide() {
    // 字段渲染子组件通过 inject 拿到根实例, 从而复用同一套 cfg* 方法
    return { ce: this };
  },
  computed: {
    /* 左导航: 分组 + 条目数徽标 */
    cfgGroups() {
      const schema = this.cfg.schema;
      if (!schema || !this.cfg.tree) return [];
      const conf = this.cfgConfig();
      return schema.groups.map((g) => {
        const badge = g.key === "trackers" ? Object.keys(conf.trackers || {}).length :
          g.key === "rules" ? Object.keys(this.cfgRuleGroups()).length : 0;
        return { key: g.key, label: g.label, help: g.help, badge: badge };
      });
    },
    /* 当前分组的渲染项(嵌套字段已扁平化) */
    cfgActive() {
      const schema = this.cfg.schema;
      if (!schema) return { key: "", label: "", help: "", items: [] };
      const g = schema.groups.find((x) => x.key === this.cfg.activeGroup) || schema.groups[0];
      if (!g) return { key: "", label: "", help: "", items: [] };
      return { key: g.key, label: g.label, help: g.help, items: this.cfgFlatten(g.fields, ["config"], 0) };
    },
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
  },
  methods: {
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
      this.cfg.notice = "";
      try {
        const result = await this.api("/api/config", { method: "PUT", body: JSON.stringify({ tree: this.cfg.tree }) });
        // 后端会把 R 级字段回退为磁盘旧值 → 重新拉取树保证 UI 与磁盘一致
        const fresh = await this.api("/api/config");
        this.cfgSetTree(fresh.tree);
        const n = (result.changes || []).length;
        if (result.restart_required && result.restart_required.length) {
          this.cfg.noticeKind = "warn";
          this.cfg.notice = `已保存并热重载(变更 ${n} 项); 需重启进程才生效: ${result.restart_required.join(", ")}`;
        } else {
          this.cfg.noticeKind = "ok";
          this.cfg.notice = `已保存并热重载(变更 ${n} 项)`;
        }
        this.cfg.previewOpen = false;
      } catch (e) {
        this.cfg.noticeKind = "error";
        this.cfg.notice = "保存失败: " + (e.message || "未知错误");
      } finally {
        this.cfg.saving = false;
      }
    },
    async cfgDiscard() {
      if (this.cfgDirty && !confirm("放弃未保存的修改?")) return;
      await this.cfgLoad();
      this.cfg.notice = "";
      this.cfg.previewOpen = false;
    },
    cfgReset() {
      // 登出时清空受保护内容(与分组数据同等对待)
      this.cfg.schema = null;
      this.cfg.tree = null;
      this.cfg.baseline = "";
      this.cfg.error = "";
      this.cfg.notice = "";
      this.cfg.previewOpen = false;
      this.cfg.previewText = "";
      this.cfg.previewError = "";
      this.cfg.trackerKey = null;
      this.cfg.ruleGroupKey = null;
    },
    async openSettings() {
      this.page = "settings";
      if (!this.cfg.schema) await this.cfgLoad();
    },
    async cfgTogglePreview() {
      if (this.cfg.previewOpen) {
        this.cfg.previewOpen = false;
        return;
      }
      this.cfg.previewBusy = true;
      this.cfg.previewError = "";
      try {
        const data = await this.api("/api/config/preview", {
          method: "POST",
          body: JSON.stringify({ tree: this.cfg.tree }),
        });
        this.cfg.previewText = data.yaml;
        this.cfg.previewOpen = true;
      } catch (e) {
        this.cfg.previewError = e.message || "预览失败";
      } finally {
        this.cfg.previewBusy = false;
      }
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
     * 项类型: group(object 段标题) / field(叶子字段) / toggle(可选 object 段的启用开关)
     * 可选段(default 为 null)以开关控制该键的存在性, 其子字段标记 depends 以便"未启用时隐藏"
     */
    cfgFlatten(fields, basePath, depth, ownerPath) {
      const items = [];
      for (const f of fields) {
        const path = [...basePath, f.key];
        if (f.kind === "object") {
          if (f.optional) items.push({ type: "toggle", field: f, path: path, depth: depth });
          else items.push({ type: "group", field: f, path: path, depth: depth, label: f.label, help: f.help });
          const subs = this.cfgFlatten(f.fields, path, depth + 1, basePath);
          for (const s of subs) {
            if (f.optional) s.depends = path;
            items.push(s);
          }
        } else {
          items.push({ type: "field", field: f, path: path, depth: depth, owner: ownerPath || basePath });
        }
      }
      return items;
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
        this.cfg.noticeKind = "error";
        this.cfg.notice = `站点 ${name} 已存在`;
        return;
      }
      const spec = {};
      for (const f of this.cfg.schema.tracker_fields) {
        if (f.kind === "str_list") spec[f.key] = [];
      }
      this.cfgSetPath([...this.cfgConfigPath(), "trackers", name], spec);
      this.cfg.trackerKey = name;
      this.cfg.newTrackerName = "";
      this.cfg.notice = "";
    },
    cfgTrackerRename(oldName) {
      const newName = prompt("重命名站点配置", oldName);
      if (newName === null) return;
      const name = newName.trim();
      if (!name || name === oldName) return;
      const trackers = this.cfgConfig().trackers || {};
      if (trackers[name]) {
        this.cfg.noticeKind = "error";
        this.cfg.notice = `站点 ${name} 已存在`;
        return;
      }
      const rebuilt = {};
      for (const [k, v] of Object.entries(trackers)) rebuilt[k === oldName ? name : k] = v;
      this.cfgSetPath([...this.cfgConfigPath(), "trackers"], rebuilt);
      if (this.cfg.trackerKey === oldName) this.cfg.trackerKey = name;
    },
    cfgTrackerRemove(name) {
      if (!confirm(`删除站点 ${name} 的配置?(不影响 qB 中的种子)`)) return;
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
        this.cfg.noticeKind = "error";
        this.cfg.notice = `规则集 ${name} 已存在`;
        return;
      }
      this.cfgSetPath([...this.cfgConfigPath(), name], {});
      this.cfg.ruleGroupKey = name;
      this.cfg.newRuleGroupName = "";
    },
    cfgRuleRemoveGroup(name) {
      if (!confirm(`删除规则集 ${name} 及其全部规则?`)) return;
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
        this.cfg.noticeKind = "error";
        this.cfg.notice = `规则 ${name} 已存在`;
        return;
      }
      // 新规则仅给 conditions/actions 两个空列表, 其余键留空由后端走默认值(保持 YAML 简洁)
      this.cfgSetPath([...this.cfgConfigPath(), groupKey, name], { conditions: [], actions: [] });
      this.cfg.newRuleName = "";
    },
    cfgRuleRemove(groupKey, ruleName) {
      if (!confirm(`删除规则 ${ruleName}?`)) return;
      this.cfgDelPath([...this.cfgConfigPath(), groupKey, ruleName]);
    },
    cfgRuleRename(groupKey, ruleName) {
      const input = prompt("重命名规则", ruleName);
      if (input === null) return;
      const name = input.trim();
      if (!name || name === ruleName) return;
      const group = this.cfgRuleGroups()[groupKey] || {};
      if (group[name]) {
        this.cfg.noticeKind = "error";
        this.cfg.notice = `规则 ${name} 已存在`;
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
    cfgCurveDisable() {
      if (!confirm("关闭全局限速曲线?(当前曲线配置将从文件中移除)")) return;
      this.cfgDelPath(this.cfgCurvePath());
    },
    cfgCurve() {
      return this.cfgRaw(this.cfgCurvePath()) || null;
    },
    cfgCurveItems() {
      const base = this.cfgCurvePath();
      return [
        { type: "field", field: { key: "interval", label: "执行间隔", kind: "time", unit: "S/M/H/D", help: "留空 = 回退主 interval", default: "" }, path: [...base, "interval"], depth: 0 },
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
      return !["bool", "enum", "str_list", "pattern_list", "keyed_list"].includes(this.f.kind);
    },
    visible() {
      if (this.item.depends && !this.ce.cfgExists(this.item.depends)) return false;
      if (this.item.type !== "field") return true;
      return this.ce.cfgVisible(this.f, this.item.owner);
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
    toggleSection(on) {
      this.ce.cfgToggleSection(this.path, this.f, on);
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
