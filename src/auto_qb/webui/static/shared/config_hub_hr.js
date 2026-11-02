/* config_hub_hr.js — R4 大文件拆分(计划 26-11-02-2342 §07)
 * 设置首屏 · HR 在线核实站点接入/调参。
 * 只搬方法定义, 实现逐行未改; 根文件已定义该域, 本片段在其后原地扩充(Object.assign)。
 * 加载序 = 四套皮肤 index.html 清单里紧跟根文件之后(与拆分前同一迭代替换序)。
 */
Object.assign(window.CONFIG_HUB.methods, {

    /* ---------------------------------------------------------- 站点接入卡片(计划 26-09-27-1318) */
    /* HR 在线核实分区的唯一启用入口: 卡片键集合来自 schema.constants.hr_check_site_presets
     * (内置站点档案, 与配置里已存在的键无关), 勾选启用即写 hr_check.sites.<id>.enabled(v3 布尔口径)。
     * 绑定状态由前端按映射制口径先行提示(计划 26-09-27-1930 §6: 显式 tracker 直取 > 档案已知
     * announce 域默认映射查表, 与后端同口径), fail-fast 仍由后端校验兜底 */
    hrSitePresets() {
      const c = this.cfg.schema && this.cfg.schema.constants;
      return (c && c.hr_check_site_presets) || [];
    },
    hrSiteEntries() {
      const v = this.cfgRaw(["config", "hr_check", "sites"]);
      return v && typeof v === "object" && !Array.isArray(v) ? v : {};
    },
    hrSiteEnabled(id) {
      const entry = this.hrSiteEntries()[id];
      if (!entry) return false;
      return this.cfgTruthy(entry.enabled);
    },
    hrSiteSetEnabled(id, on) {
      if (!on && !this.cfgExists(["config", "hr_check", "sites", id])) return; // 未配置 = 本就关闭, 不写垃圾键
      this.cfgSetBool(["config", "hr_check", "sites", id, "enabled"], on);
    },
    /* 绑定状态(映射制, 计划 26-09-27-1930 §6): 返回 {text, cls}; cls = "warn" 表示保存后校验会报错。
     * web 域与 tracker 域永不互相比对 —— 自动绑定只在 announce 命名空间内查表(双向子域容错,
     * 与 site_presets.match_trackers 同口径); 显式 tracker 按条目名直取 */
    hrSiteBinding(preset) {
      const trackerDomain = String(preset.tracker_domain || "").trim().toLowerCase();
      const entry = this.hrSiteEntries()[preset.id];
      const explicit =
        entry && entry.tracker !== undefined && entry.tracker !== null ? String(entry.tracker).trim() : "";
      const names = this.cfgTrackerNames();
      if (explicit) {
        if (!names.includes(explicit)) {
          return { cls: "warn", text: `映射目标 ${explicit} 不存在 —— 保存后校验会报错` };
        }
        return { cls: "", text: `已映射: ${explicit}` };
      }
      const hits = names.filter((n) => {
        const ds = this.cfgRaw(["config", "trackers", n, "domains"]);
        return Array.isArray(ds) &&
          ds.some((d) => {
            const t = String(d).trim().toLowerCase();
            return t && (t === trackerDomain || t.endsWith("." + trackerDomain) || trackerDomain.endsWith("." + t));
          });
      });
      if (hits.length === 1) return { cls: "", text: `已自动绑定: ${hits[0]}（档案默认映射）` };
      if (hits.length > 1) return { cls: "warn", text: `默认映射歧义: ${hits.join("、")} 都命中 —— 请显式指定 tracker` };
      return {
        cls: "warn",
        text: `未绑定: 档案已知 announce 域(${trackerDomain})未命中任何站点配置 —— 请补域名或显式指定 tracker`,
      };
    },
    /* 微调字段表: 从 schema 里 hr_check -> sites 字段的子字段表取(数据驱动), enabled 已由卡片勾选承担 */
    hrSiteTuningFields() {
      const g = this.cfg.schema && this.cfg.schema.groups.find((x) => x.key === "hr_check");
      const root = g && (g.fields || []).find((f) => f.key === "hr_check");
      const sites = root && (root.fields || []).find((f) => f.key === "sites");
      return ((sites && sites.fields) || []).filter((f) => f.key !== "enabled");
    },
    /* 组装成 hub-field 组件可渲染的 item(路径指向具体档案条目) */
    hrSiteTuningItems(id) {
      return this.hrSiteTuningFields().map((f) => ({
        type: "field",
        field: f,
        path: ["config", "hr_check", "sites", id, f.key],
        depth: 1,
        owner: ["config", "hr_check", "sites", id],
        inline: [],
      }));
    },

    /* ---------------------------------------------------------- 就近说明浮窗 */
    /* 内容: 富文案优先, 否则由 schema 的 help / risk / default 拼出五段 */
    hubHelpOf(item) {
      const f = item.field || {};
      const bare = this.hubBare(item.path);
      const rich = HUB_HELP[bare];
      const tags = [];
      if (f.required) tags.push("必填");
      if (f.kind) tags.push(f.kind);
      if (rich && rich.tags && rich.tags.length) tags.length = 0;
      return {
        t: f.label || "说明",
        k: bare,
        tags: (rich && rich.tags) || tags,
        what: (rich && rich.what) || f.help || "这一项还没有说明。",
        def: (rich && rich.def) || this.hubDefaultText(f),
        when: (rich && rich.when) || [],
        risk: (rich && rich.risk) || f.risk || "",
        rel: (rich && rich.rel) || [],
      };
    },
    /* WARN: 对象/数组型默认值(如 trackers / rules 的 default={}、channels 的 default=["platform"])不能
       直接进 cfgScalar —— String({}) 是 "[object Object]", 会在「?」说明浮窗的「默认值」一栏里
       原样显示给读者。空的一律归「（空）」, 非空对象按条目数给一句人话。 */
    hubDefaultText(field) {
      const d = field.default;
      if (d === null || d === undefined || d === "") return "（空）";
      if (Array.isArray(d)) return d.length ? d.join("、") : "（空）";
      if (typeof d === "object") {
        const n = Object.keys(d).length;
        return n ? `（对象: ${n} 项, 由子项决定）` : "（空）";
      }
      return this.cfgScalar(d);
    },
    hubAsk(item, ev) {
      const key = this.hubKey(item.path);
      if (this.hub.helpKey === key) {
        this.hubCloseHelp();
        return;
      }
      const btn = ev.currentTarget;
      const b = btn.getBoundingClientRect();
      const FIT = window.AQB_OVERLAY_FIT; /* 几何单点(issue 26-10-20-2231), 方法内取别名 */
      this.hub.help = this.hubHelpOf(item);
      this.hub.helpKey = key;
      /* 说明浮窗贴边留白 12px: 比浮层默认 8px(overlay_fit.js::EDGE)多 4px —— 入池审计
       * (issue 26-10-20-2231)时此处无注释、也无佐证必须不同; 按行为零变化口径显式传参
       * 保留现值, 确要统一只改这一个常量。 */
      const EDGE = 12, gap = 10;
      this.$nextTick(() => {
        const pop = this.$refs.hubPop;
        if (!pop) return;
        const pw = pop.offsetWidth;
        const ph = pop.offsetHeight;
        let left = b.right + gap;
        let place = "left";
        if (FIT.probeRight(b.right, pw, gap, EDGE)) {
          left = b.left - gap - pw;
          place = "right";
          if (FIT.probeLeft(b.left, pw, gap, EDGE)) {
            left = FIT.clampAxis(window.innerWidth - pw, pw, window.innerWidth, EDGE);
            place = "left";
          }
        }
        const top = FIT.clampAxis(b.top - 6, ph, window.innerHeight, EDGE);
        this.hub.pop = { left: left, top: top };
        this.hub.arrow = {
          place: place,
          left: place === "left" ? left - 5 : left + pw - 4,
          top: Math.min(Math.max(b.top + b.height / 2 - 4, top + 10), top + ph - 18),
        };
      });
    },
    hubCloseHelp() {
      if (!this.hub.help) return;
      this.hub.help = null;
      this.hub.helpKey = "";
    },
    hubOnDocClick(e) {
      if (this.hub.help && !(e.target && e.target.closest && e.target.closest(".hb-pop"))) {
        this.hubCloseHelp();
      }
      /* 聚焦搜索层「点外即收」(方案C 2026-09-29): 收层一律清词 —— 层开着时列表/详情都在暗幕底下,
       * 留词只会让下次点击又盖回来; stage 内点击(搜索行 / 面板 / 暗幕自身除外)不算点外 */
      if (this.hub.view === "trackers" && this.hubTrackerStageOpen &&
          !(e.target && e.target.closest && e.target.closest(".hb-tr-stage"))) {
        this.hubTrackerStageClose(true);
      }
    },
    hubOnKey(e) {
      /* IME 组词中的 Esc/Enter 属于输入法(取消候选 / 确认上屏), 不劫持 —— 中文输入状态按 Esc
       * 只该取消组词, 不该顺带关浮层/清搜索词/退首页 */
      if (e.isComposing || e.keyCode === 229) return;
      if (e.key !== "Escape") return;
      if (this.hub.help) {
        this.hubCloseHelp();
        return;
      }
      /* 站点搜索的退出路径: Esc = 清词收层退聚焦层(跳转器拍板延续 + 方案C) */
      if (this.hub.view === "trackers" && this.hubTrackerStageOpen) {
        this.hubTrackerStageClose(true);
        return;
      }
      /* 设置二级页 Esc 返回首页(方案三 2026-09-28): 排在说明浮窗/站点搜索之后, 不抢既有职责;
       * lifecycle 的 Esc 关闭链还有层要关(escBusy, 名单在 dialogs.js)时本键归它 ——
       * 否则用户按 Esc 关弹窗会顺带把页面退回首页 */
      if (this.page === "settings" && this.hub.view !== "hub" && !this.escBusy()) this.hubBack();
    },
});
