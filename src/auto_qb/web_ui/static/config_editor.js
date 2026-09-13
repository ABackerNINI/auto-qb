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
        addOpen: "",  // 当前展开的"新增"表单: "" | tracker | ruleGroup | rule(同时只允许一个)
        collapsedRules: {},  // 规则卡折叠态 { "<规则集>::<规则名>": true }
        picker: { open: false, groupKey: "", ruleName: "", list: "" },  // 条件/动作选择面板(单例)
      },
    };
  },
  provide() {
    // 字段渲染子组件通过 inject 拿到根实例, 从而复用同一套 cfg* 方法
    return { ce: this };
  },
  computed: {
    /* 左导航: 分组 + 图标 + 条目数徽标 */
    cfgGroups() {
      const schema = this.cfg.schema;
      if (!schema || !this.cfg.tree) return [];
      const conf = this.cfgConfig();
      return schema.groups.map((g) => {
        const badge = g.key === "trackers" ? Object.keys(conf.trackers || {}).length :
          g.key === "rules" ? Object.keys(this.cfgRuleGroups()).length : 0;
        return { key: g.key, label: g.label, help: g.help, badge: badge, icon: g.icon || "i-settings" };
      });
    },
    /* 当前分组的渲染项(嵌套字段已扁平化) */
    cfgActive() {
      const schema = this.cfg.schema;
      if (!schema) return { key: "", label: "", help: "", icon: "", items: [] };
      const g = schema.groups.find((x) => x.key === this.cfg.activeGroup) || schema.groups[0];
      if (!g) return { key: "", label: "", help: "", icon: "", items: [] };
      return {
        key: g.key, label: g.label, help: g.help, icon: g.icon || "i-settings",
        items: this.cfgFlatten(g.fields, ["config"], 0),
      };
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
      if (this.cfgDirty) {
        const ok = await this.confirmDialog("放弃未保存的修改", "当前编辑内容将丢失, 配置保持磁盘原样。", {
          okText: "放弃修改", danger: true,
        });
        if (!ok) return;
      }
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
      this.cfg.addOpen = "";
      this.cfg.collapsedRules = {};
      this.cfgPickerClose();
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
     * 项类型: group(object 段标题) / field(叶子字段) / toggle(可选 object 段的启用开关) /
     *        subcard(由 group_of 归入父字段的"相关设置"子卡)
     * 可选段(default 为 null)以开关控制该键的存在性, 其子字段标记 depends 以便"未启用时隐藏";
     * allowGrouping=false 用于子卡内部: 那些字段已归属父字段, 不能再参与一次分组判定
     * (否则它们会被再次收进 children, roots 为空 => 子卡渲染成空)。
     */
    cfgFlatten(fields, basePath, depth, ownerPath, allowGrouping = true) {
      const children = new Map();
      const roots = [];
      for (const f of fields) {
        if (allowGrouping && f.group_of) {
          if (!children.has(f.group_of)) children.set(f.group_of, []);
          children.get(f.group_of).push(f);
        } else {
          roots.push(f);
        }
      }
      const byKey = new Map(fields.map((f) => [f.key, f]));
      const items = [];
      for (const f of roots) {
        const path = [...basePath, f.key];
        if (f.kind === "object") {
          if (f.optional) items.push({ type: "toggle", field: f, path: path, depth: depth });
          else items.push({ type: "group", field: f, path: path, depth: depth, label: f.label, help: f.help });
          const subs = this.cfgFlatten(f.fields, path, depth + 1, basePath);
          for (const s of subs) {
            if (f.optional) s.depends = path;
            items.push(s);
          }
          continue;
        }
        items.push({ type: "field", field: f, path: path, depth: depth, owner: ownerPath || basePath });
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
        if (f && f.grey_if && f.grey_if.length) it.greyBy = byKey.get(f.grey_if[0]) || null;
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
      this.cfgAddCancel();
    },
    async cfgTrackerRename(oldName) {
      const newName = await this.promptDialog("重命名站点配置", oldName, { okText: "重命名" });
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
    /* ---------------------------------------------------------- "新增"按钮: 就地展开输入框 */

    cfgAddStart(kind) {
      this.cfg.addOpen = this.cfg.addOpen === kind ? "" : kind;
      this.cfg.newTrackerName = "";
      this.cfg.newRuleGroupName = "";
      this.cfg.newRuleName = "";
      if (this.cfg.addOpen) {
        this.$nextTick(() => {
          const el = this.$refs.addInput;
          if (el) el.focus();
        });
      }
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
        this.cfg.noticeKind = "error";
        this.cfg.notice = `规则集 ${name} 已存在`;
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
        this.cfg.noticeKind = "error";
        this.cfg.notice = `规则 ${name} 已存在`;
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

    /* ---------------------------------------------------------- 曲线图表(SVG 阶梯折线预览)
     *
     * 纯展示: 前端只用它画图, 解析失败不阻断保存(合法性唯一入口仍是后端 load_config)。
     * 语义与 curves.curve_speed 一致 —— 阈值是区间**上限**, 末档之后一直沿用末档速度。
     */

    cfgCurvePeriodHint(i) {
      const p = (this.cfgCurvePeriod(i).period || "").trim();
      if (!p) return "未填写周期(DAY / MONTH / 7D)";
      const known = { DAY: "按当天累计流量", MONTH: "按本月累计流量" };
      return known[p.toUpperCase()] || `按最近 ${p} 的累计流量`;
    },
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
    _curveChart(i, direction) {
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
      const W = 320, H = 96, PAD = 6, AXIS = 14;
      const maxT = points[points.length - 1].t;
      const maxS = Math.max(...points.map((p) => p.s), 1);
      const tail = maxT * 0.08;  // 末档向右延伸一段, 表示"此后一直沿用末档"
      const spanT = maxT + tail;
      const x = (t) => PAD + (W - PAD * 2) * (t / spanT);
      const y = (s) => H - AXIS - (H - AXIS - PAD) * (s / maxS);
      let line = `M ${x(0).toFixed(1)} ${y(points[0].s).toFixed(1)}`;
      for (let k = 1; k < points.length; k++) {
        line += ` L ${x(points[k - 1].t).toFixed(1)} ${y(points[k - 1].s).toFixed(1)}`;
        line += ` L ${x(points[k - 1].t).toFixed(1)} ${y(points[k].s).toFixed(1)}`;
      }
      const lastS = points[points.length - 1].s;
      line += ` L ${x(spanT).toFixed(1)} ${y(lastS).toFixed(1)}`;
      const area = `${line} L ${x(spanT).toFixed(1)} ${H - AXIS} L ${x(0).toFixed(1)} ${H - AXIS} Z`;
      return {
        viewBox: `0 0 ${W} ${H}`,
        line: line,
        area: area,
        maxLabel: this._fmtBytes(spanT),
        note: `${points.length} 档 · 最严 ${this._fmtSpeed(maxS)}`,
      };
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
      // 子卡随父字段的可见性一起显隐
      if (this.item.type === "subcard") return this.ce.cfgVisible(this.item.ownerField, this.item.owner);
      if (this.item.type !== "field") return true;
      return this.ce.cfgVisible(this.f, this.item.owner);
    },
    /* 所属功能未启用(grey_if 不满足)时灰显, 但仍可编辑(不阻断, 只提示) */
    greyed() {
      return this.item.type === "field" && this.ce.cfgGreyed(this.item);
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
