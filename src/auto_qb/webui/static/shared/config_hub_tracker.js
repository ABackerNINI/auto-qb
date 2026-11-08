/* config_hub_tracker.js — R4 大文件拆分(计划 26-11-02-2342 §07)
 * 设置首屏 · 站点 tracker 索引/命中/选择层。
 * 只搬方法定义, 实现逐行未改; 根文件已定义该域, 本片段在其后原地扩充(Object.assign)。
 * 加载序 = 四套皮肤 index.html 清单里紧跟根文件之后(与拆分前同一迭代替换序)。
 */
Object.assign(window.CONFIG_HUB.methods, {

    /* ---------------------------------------------------------- 站点搜索(计划 26-09-27-1852)
     * 匹配函数收敛为前端单点: 一处 norm / 一处 parse / 一处 rows, 模板不散写。 */
    /* 归一化: 与 views.py::_search_norm 同语义(分隔符折叠为单空格 + 小写)。
     * WARN: JS 必须用 [^\p{L}\p{N}](u 标志必带) —— ASCII \W 是 Unicode 语义的反面,
     * 会把整个中文词折成空格, 中文搜索直接废掉(拟记 pitfalls/web-ui) */
    trackerNorm(s) {
      return String(s).replace(/[^\p{L}\p{N}]+/gu, " ").toLowerCase().trim();
    },
    /* 站点 -> 归一化行(名称行恒在最前, 供名称命中判定)。序列化兜底口径(§03):
     * 字符串原样 / 列表逐项 / 数字 String() / 布尔跳过(无可读文本) / dict 递归到叶子 /
     * 掩码哨兵跳过 / 空串跳过(不出空 chip) */
    trackerRows(name, entry) {
      const rows = [{ grp: "名称", raw: name, n: this.trackerNorm(name) }];
      const walk = (v, grp) => {
        if (v === TRACKER_MASK) return;
        if (typeof v === "boolean") return;
        if (typeof v === "number") {
          rows.push({ grp, raw: String(v), n: this.trackerNorm(v) });
          return;
        }
        if (Array.isArray(v)) {
          v.forEach((x) => walk(x, grp));
          return;
        }
        if (v && typeof v === "object") {
          Object.keys(v).forEach((k) => walk(v[k], grp));
          return;
        }
        const raw = String(v === undefined || v === null ? "" : v);
        if (!raw.trim()) return;
        rows.push({ grp, raw, n: this.trackerNorm(raw) });
      };
      for (const k of Object.keys(entry || {})) {
        const grp = TRACKER_FIELD_GROUPS[k];
        if (grp) walk(entry[k], grp);
      }
      return rows;
    },
    /* 查询解析(照搬种子搜索语法, 用户零学习成本): 空格分词 = 隐式 AND / -词 = 排除 /
     * "短语" = 连续子串 / -"短语" = 排除短语; 宽容容错: 孤立 - 忽略, 未闭合引号收到行尾 */
    trackerParseQuery(q) {
      const pos = [];
      const neg = [];
      const re = /(-?)(?:"([^"]*)"|(\S+))/g;
      let m;
      while ((m = re.exec(String(q)))) {
        const term = m[2] !== undefined ? m[2] : m[3];
        if (!term) continue;
        const n = this.trackerNorm(term);
        if (!n) continue;
        (m[1] ? neg : pos).push(n);
      }
      return { pos, neg, negOnly: !pos.length && neg.length > 0 };
    },
    /* 点命中行(跳转器交互 2026-09-28, 方案C 延续): 选中即清词收层直达详情 —— 层盖着列表,
     * 只选中不清词会把切站效果留在暗幕底下看不见; 焦点一并交还页面, 落到详情可直接编辑 */
    hubTrackerPick(name) {
      this.cfg.trackerKey = name;
      this.hubTrackerStageClose(true);
    },
    /* 聚焦层收层单点(方案C): 清词 + 聚焦态/键盘活动项复位; blurInput 时把焦点从搜索框还回去 */
    hubTrackerStageClose(blurInput) {
      this.cfg.trackerQuery = "";
      this.hub.trackerSearchFocus = false;
      this.hub.trackerHitIdx = -1;
      this.hub.trackerMouseAt = null;
      if (blurInput && this.$refs.trackerSearchInput) this.$refs.trackerSearchInput.blur();
    },
    /* × 清空钮: 配合模板 @mousedown.prevent —— 阻止按钮抢焦点, 输入框保持聚焦可继续输入
     * (清词后聚焦层仍开着, 回到空态引导, 再敲字即搜) */
    hubTrackerClear() {
      this.cfg.trackerQuery = "";
    },
    /* 悬停接管(治「上下键选中项闪烁」2026-09-29): 命中行不挂 @mouseenter + CSS 不写 :hover ——
     * 光标静止停在命中列表上时, 旧高亮(悬停)与键盘活动项两套同源高亮打架, 活动项会跳回光标行;
     * 行入场动画 / 滚动 / DOM 变更后浏览器还会给静止光标补发合成 hover 事件, 放大成交替闪烁。
     * 改为 @mousemove + 位移门限: 位移 <3px(静止 / 合成事件)不接管, 真实移动才把活动项交给光标 */
    hubTrackerHoverIdx(i, ev) {
      const x = ev.clientX, y = ev.clientY, at = this.hub.trackerMouseAt;
      if (at) {
        const dx = x - at.x, dy = y - at.y;
        if (dx * dx + dy * dy < 9) return; // <3px: 光标静止 / 合成事件, 不接管
      }
      this.hub.trackerMouseAt = { x, y };
      this.hub.trackerHitIdx = i;
    },
    /* 聚焦层键盘导航(方案C): up/down 移动命中活动项, Enter 打开活动项(=点命中); IME 组词中不劫持。
     * Esc 不在这里处理 —— 归 hubOnKey 的既有 Esc 链(帮助浮窗优先级在前), 避免双路径清词 */
    hubTrackerKeydown(e) {
      if (e.isComposing || e.keyCode === 229) return;
      const hits = this.hubTrackerHits.hits;
      if (e.key === "ArrowDown" || e.key === "ArrowUp") {
        if (!hits.length) return;
        e.preventDefault();
        const n = hits.length, cur = this.hub.trackerHitIdx;
        this.hub.trackerHitIdx = e.key === "ArrowDown"
          ? (cur + 1) % n
          : (cur < 0 ? n - 1 : (cur - 1 + n) % n);
        this.$nextTick(() => this.hubTrackerScrollActIntoView()); // 滚动跟随(26-09-29-2142)
      } else if (e.key === "Enter") {
        if (this.hub.trackerHitIdx >= 0 && hits[this.hub.trackerHitIdx]) {
          e.preventDefault();
          this.hubTrackerPick(hits[this.hub.trackerHitIdx].name);
        }
      }
    },

    /* 键盘活动项滚动跟随(26-09-29-2142): 命中列表 max-height 300px 可滚, 但 up/down 只改 idx 不推滚动条,
     * 长列表上高亮走出可视区 = 键盘选择不可用。up/down 改 idx 后把 .act 行滚进列表视野。
     * 手动差值调 scrollTop(block:"nearest" 语义: 行在视野内不动, 出视野才滚最小距离);
     * 不用 scrollIntoView —— 它会逐层滚动所有可滚祖先, 连带滚动暗幕后面的整页产生二次干扰。
     * $nextTick 等 Vue 把 .act 类挪到新行之后再量。程序滚动不产生光标位移,
     * 浏览器即便补发合成 mousemove 也被 hubTrackerHoverIdx 的 3px 门限挡掉(不复发闪烁)。 */
    hubTrackerScrollActIntoView() {
      const list = document.querySelector(".hb-tr-stage.on .hb-tr-drop-list");
      const row = list && list.querySelector(".hb-tr-hit.act");
      if (!list || !row) return;
      const lr = list.getBoundingClientRect(), rr = row.getBoundingClientRect();
      if (rr.top < lr.top) list.scrollTop += rr.top - lr.top; // 行在上方视野外 -> 上滚
      else if (rr.bottom > lr.bottom) list.scrollTop += rr.bottom - lr.bottom; // 行在下方视野外 -> 下滚
    },

    /* ---------------------------------------------------------- 行 / 控件辅助 */
    /* 语调单点: schema 的 tone 字段(破坏性/重要字段显式声明, 如 删标/彻底删标)优先,
     * 回落 HUB_TONE 静态表(动态路径进不去表的老键, 如 qbittorrent.password);
     * 行条纹(hubRowClass)与行内「?」按钮同一来源, 危险行整组走红 */
    hubToneOf(item) {
      return (item.field && item.field.tone) || HUB_TONE[this.hubBare(item.path)] || "";
    },
    hubRowClass(item) {
      const out = [];
      if (item.field && item.field.risk) out.push(this.hubToneOf(item) === "danger" ? "danger" : "risk");
      if (this.hub.focusKey && this.hub.focusKey === this.hubKey(item.path)) out.push("flash");
      return out.join(" ");
    },
    /* 数值/时间/大小/速度一律等宽(样张: 读数用 mono, 标题用 display) */
    hubMonoOf(item) {
      return ["int", "time", "size", "speed", "expr"].indexOf((item.field && item.field.kind) || "") >= 0;
    },
    /* 窄宽给数字, 宽给路径/表达式 —— 值是 300GiB / 8MiB/s 这种短串, 拉满整行既浪费又难扫 */
    hubWidthOf(item) {
      const k = (item.field && item.field.kind) || "";
      if (["int", "time", "size", "speed"].indexOf(k) >= 0) return "hb-w-sm";
      if (k === "path") return "hb-w-lg";
      return "";
    },
    /* 条件 / 动作一行人话: 插件名 + 简短取值 */
    hubPluginText(entry) {
      /* 伪动作 ignore_next_action_error 已退役(D1, plan 26-11-01-0106 W1): 不再当动作显示,
       * 按退役键标记 —— 升级提示面(未启用徽标/卡脚提示)由 cfgRuleRetiredHint 单点承接。
       * 判定须在 meta 判空之前: 退役键不在插件索引里, meta 恒空。 */
      if (this.cfgIsRetiredAction(entry)) return "已退役: ignore_next_action_error";
      /* choose 编排块(W3-B): 不在插件索引里, meta 恒空 —— 须在 meta 判空之前给出行话 */
      if (this.cfgIsChooseEntry(entry)) return "动作分支(choose)";
      const meta = this.cfgPluginMeta(entry);
      if (!meta) return this.cfgPluginName(entry) || "—";
      const name = meta.label || this.cfgPluginName(entry);
      const kind = meta.spec_kind;
      if (kind === "bool") return `${name}（${String(entry[meta.name]) === "true" ? "是" : "否"}）`;
      const raw = entry[meta.name];
      if (raw === undefined || raw === null || raw === "") return name;
      if (typeof raw === "object" && !Array.isArray(raw)) {
        const parts = Object.keys(raw).filter((k) => String(raw[k]) !== "");
        return parts.length ? `${name} · ${parts.slice(0, 2).join("/")}` : name;
      }
      const text = Array.isArray(raw) ? raw.join(", ") : String(raw);
      return text ? `${name} · ${text}` : name;
    },
    hubStepClass(entry) {
      const meta = this.cfgPluginMeta(entry);
      return meta && meta.risk ? "danger" : "";
    },

    /* ---------------------------------------------------------- 站点 / 规则集 / 规则 增删 */
    /* 「新增实体」的命名交互单点(报告 26-10-20-2231 R20-C-02): 取消 / 空名 / 查重的判据只写一遍,
     * 三个入口只声明文案 —— 改命名交互(如加长度提示、二次确认)不必再改三处。
     * def 额外带 title / placeholder / prefill, 其余字段原样交给 cfgEntityAdd 的骨架。 */
    async hubAddEntity(def) {
      const { title, placeholder, prefill, ...entity } = def;
      const input = await this.promptDialog(title, prefill || "", { placeholder, okText: "添加" });
      if (input === null || input === undefined) return;
      const name = String(input).trim();
      if (!name) return;
      this.cfgEntityAdd({ ...entity, name });
    },
    async hubAddTracker(prefill) {
      /* prefill: 聚焦搜索层面板尾的「新增站点「词」」把当前搜索词带进命名框(方案C, 搜不到就当场建) */
      return this.hubAddEntity({
        ...this.cfgTrackerDef(""),
        title: "新增站点配置",
        placeholder: "站点名(如 HHan)",
        prefill,
      });
    },
    /* 逐域名导入(现状路径单点, 计划 26-11-03-2337 M4 抽出): confirmDialog 列清单 ->
     * 逐域名各填一条(键 = sites[i].name)。分支2(全单域名组/无 groups)与分支3的「拆分导入」
     * 同走这一份, 不留两份拷贝; 逻辑与拆分前 hubImportSites 逐行一致。 */
    async _hubImportPerDomain(sites) {
      const list = sites.map((s) => `${s.name}(${s.domain})`).join("、");
      const ok = await this.confirmDialog(
        `导入 ${sites.length} 个缺失站点`,
        `将按默认配置填入编辑器: ${list}。默认限速为不限、HR 为示例值 —— 保存前请在编辑器中核对。`,
        { okText: "导入" }
      );
      if (!ok) return;
      const trackers = { ...(this.cfgConfig().trackers || {}) };
      let added = 0;
      for (const s of sites) {
        if (Object.prototype.hasOwnProperty.call(trackers, s.name)) continue; // 已存在同名键(如待生效热重载)不覆盖
        trackers[s.name] = s.entry;
        if (!added) this.cfg.trackerKey = s.name;
        added++;
      }
      if (!added) {
        this.toast("站点已存在, 没有可导入项", "error");
        return;
      }
      this.cfgSetPath([...this.cfgConfigPath(), "trackers"], trackers);
      this.toast(`已填入 ${added} 个站点, 核对后点「保存」生效`, "ok", 6000);
    },
    async hubImportSites() {
      /* 一键导入缺失站点(对齐 CLI --export-yaml --only-missing): 后端只读扫描,
       * 条目填入编辑器待审 —— 示例值不未经审阅生效, 保存走既有 cfgSave 路径。
       * busy 骨架走 dialogs.js::_panelLoad(toast 通道 errToast: 恒提示不看 auth)。
       *
       * 三分支自适应引导(计划 26-11-03-2337 M4, 后端契约: sites 逐域名原形 + groups
       * 共现合并组, 组数可为 0; 全单元素组时 groups 的 domains/entry 与 sites 一一对应,
       * 组名在 sites 取名之后顺延(不按名字互查)):
       *   1. sites 空 -> 现状「无需导入」toast(不变);
       *   2. 不存在 >=2 域名的组(groups 缺省/为空/全单元素) -> 现状 confirmDialog
       *      逐域名导入(_hubImportPerDomain, 路径零变化);
       *   3. 存在 >=2 域名的组 -> 三钮 confirmThreeDialog 引导:
       *      ok=「合并导入」(Enter 默认, 推荐; 键 = groups[i].name, 值 = groups[i].entry,
       *      entry.domains 已含组内全域名, 后端单点产出)、extra=「拆分导入」(ghost 样式
       *      —— 拆分不是破坏性动作, 走现状逐域名路径)、cancel=「取消」(什么都不做)。
       *      两种导入都只填编辑器待审, 保存仍走既有 PUT /api/config。 */
      if (this.hub.importing) return;
      await this._panelLoad(this.hub, async () => {
        const res = await this.api("/api/sites/missing");
        const sites = res.sites || [];
        if (!sites.length) {
          this.toast("无需导入: 没有发现未配置的站点", "ok");
          return;
        }
        const groups = res.groups || [];
        const hasMulti = groups.some((g) => (g.domains || []).length >= 2);
        if (!hasMulti) {
          await this._hubImportPerDomain(sites);
          return;
        }
        /* 合并明细: 列前 10 组 Name(d1、d2), 超出折叠一行(单行文案, .modal-body 无
         * white-space 预处理, 不靠换行排版) */
        const DETAIL_MAX = 10;
        const detail = groups.slice(0, DETAIL_MAX)
          .map((g) => `${g.name}(${(g.domains || []).join("、")})`).join("、");
        const fold = groups.length > DETAIL_MAX ? `…另有 ${groups.length - DETAIL_MAX} 组` : "";
        const choice = await this.confirmThreeDialog(
          `导入 ${sites.length} 个缺失站点(含多域名站点)`,
          `同站多个 tracker 域名可合并为一个站点条目, 合并后共享标签/限速/HR 配置; 拆分则逐域名各一条(旧行为)。推荐合并。` +
          `合并明细: ${detail}${fold}。合并/拆分都只填入编辑器待审, 保存前请逐条核对。`,
          { okText: "合并导入", extraText: "拆分导入", extraStyle: "ghost" }
        );
        if (choice === true) {
          const trackers = { ...(this.cfgConfig().trackers || {}) };
          let added = 0, domains = 0;
          for (const g of groups) {
            if (Object.prototype.hasOwnProperty.call(trackers, g.name)) continue; // 同名键已存在不覆盖(与逐域名路径同一 skip 语义)
            trackers[g.name] = g.entry;
            if (!added) this.cfg.trackerKey = g.name;
            added++;
            domains += (g.domains || []).length;
          }
          if (!added) {
            this.toast("站点已存在, 没有可导入项", "error");
            return;
          }
          this.cfgSetPath([...this.cfgConfigPath(), "trackers"], trackers);
          // 文案形态受「主标题: 说明」守阵约束(_scan_toast_copy_two_part: 首个分隔符前 ≤14 字),
          // 组数/域名数都塞标题会超长 —— 数字进说明段
          this.toast(`已填入 ${added} 组: 共 ${domains} 个域名, 核对后点「保存」生效`, "ok", 6000);
        } else if (choice === "extra") {
          await this._hubImportPerDomain(sites);
        }
        // choice === false/null(取消/Esc/遮罩): 什么都不做
      }, { loading: "importing", errToast: { prefix: "导入失败", fallback: "未知错误", ms: 9000 } });
    },
    async hubAddRuleGroup() {
      return this.hubAddEntity({
        ...this.cfgRuleGroupDef(""),
        title: "新增规则集",
        placeholder: "规则集名(自动补 _rules)",
      });
    },
    async hubAddRule(groupKey) {
      return this.hubAddEntity({
        ...this.cfgRuleDef(groupKey, ""),
        title: "新增规则",
        placeholder: "规则名(如 auto-skip-checking)",
      });
    },
    hubPickPlugin(groupKey, ruleName, listName, ev) {
      const value = ev.target.value;
      if (value) this.cfgPluginAdd(groupKey, ruleName, listName, value);
      ev.target.value = "";
    },
});
