/* config_editor_tree.js — R4 大文件拆分(计划 26-11-02-2342 §07)
 * 配置编辑器 · 字段树展开/可见/分组/列表开合。
 * 只搬方法定义, 实现逐行未改; 根文件已定义该域, 本片段在其后原地扩充(Object.assign)。
 * 加载序 = 四套皮肤 index.html 清单里紧跟根文件之后(与拆分前同一迭代替换序)。
 */
Object.assign(window.CONFIG_EDITOR.methods, {
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
        // 暂不图形化(schema Field.hidden): 键仍在配置契约里(校验接受 / loader 读 / 存量值保留),
        // 只是不进设置页 —— 在这里单点跳过, 两套 UI 的 hub 页与经典设置页同时生效
        if (f.hidden) continue;
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
    /* path→key 与 hubKey 是同一事实(收敛 issue 26-10-20-2231 / 台账 R20-C-18): 本文件历史上
     * 的第二份单点(比内联更隐蔽 —— 看着都像合法的单点)。现转调 hubKey, 判据只此一处。 */
    cfgPathKey(path) {
      return this.hubKey(path);
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
    /* schema → 默认值阶梯单点(issue 26-10-20-2231)
     *
     * "按 schema 形状造初值"这条阶梯曾有三份实现(可选段 cfgDefaultForField / 插件 spec /
     * 插件 section), 后两份还互相嵌套 —— 加一种 kind 的默认值规则要三处同改, 漏一处新条目
     * 就过不了后端校验或写出非法空值。现在只剩这一条下降链, 三处的差异退化成 opts 开关:
     *   cfgDefaultScalar(node, opts)      —— 叶子 → 标量(enum / bool / 其它)
     *   cfgDefaultForFields(fields, opts) —— 字段清单 → 对象(object 且 recurse 时再下一层)
     * opts: requiredOnly(只填必填子字段) / recurse(object 子段递归一层) / boolOn(bool 初值取 "true")
     * 插件形态的分派(spec_kind → list / object / 叶子)在 config_rules.js::cfgDefaultForPlugin。 */
    cfgDefaultScalar(node, opts) {
      const o = opts || {};
      if (node.kind === "enum") return (node.options && node.options[0]) || "";
      if (node.kind === "bool") return o.boolOn ? "true" : "false";
      return node.placeholder || this.cfgScalar(node.default);
    },
    cfgDefaultForFields(fields, opts) {
      const o = opts || {};
      const out = {};
      for (const f of fields || []) {
        if (o.requiredOnly && !f.required) continue;
        // object 子段再下一层: 子段口径 = 全字段、不再递归(原 section 级的行为, 现在只是少传 recurse)
        out[f.key] =
          f.kind === "object" && o.recurse ? this.cfgDefaultForFields(f.fields, {}) : this.cfgDefaultScalar(f, o);
      }
      return out;
    },
    /* 可选段初值: object 段按必填子字段造对象; 非 object(历史口径)→ 空列表 */
    cfgDefaultForField(field) {
      if (field.kind !== "object") return [];
      return this.cfgDefaultForFields(field.fields, { requiredOnly: true });
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
});
