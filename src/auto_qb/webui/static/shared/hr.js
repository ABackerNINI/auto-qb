/* auto-qb WEB UI · H&R 命中判定与配色
 *
 * app.js 按域拆分出的片段(2026-09-20)。约定与 config_editor.js / config_rules.js 同一范式:
 * 挂到 window.AQB_HR, 由 app.js 末尾 app.mixin(window.AQB_HR) 注入同一个 Vue 实例 ——
 * 方法体里的 this 仍是那个组件实例, 跨模块互调与拆分前完全等价。
 *
 * ❗本文件在 HTML 里必须排在 app.js **之前**(app.js 末尾要读 window.AQB_HR);
 *   用到的列模型常量(TABLE_COLUMNS / MIN_COL_PX / STATE_RANK …)仍单点定义在 app.js 顶部。
 */

/* 删除安全档位 × 来源档位的 token -> 展示映射(2026-09-25, 计划 webui-hr-safety-display §3):
 * token 由后端 hr.resolve.safety_display 单点派生, 前端只做映射与着色 —— 判定与来源不得在 JS 重算。
 * 颜色编码安全档位五档(2026-09-25 用户修正): danger 橙=考察中进行中 / failed 红=未达标终态
 * (考核期已过, 独立醒目色, 不与考察中混橙、更不是可删绿) / safe 绿 / unknown 灰;
 * danger 与 failed 同属「不能删」桶。来源用 2 字徽标编码。 */
const HR_SAFETY_CLASSES = { danger: "pending", failed: "hr-fail", safe: "reached", unknown: "hr-unk" };
/* 桶名(2026-09-25 用户修正): failed = 考核期已过仍未达标, 结果已成立的**终态** —— 删除不会新增
 * 惩罚, 叫「不能删」不符合实际, 独立成「考核未通过」桶(红), 不进 delete_flow 的删除点名集合 */
const HR_SAFETY_BUCKETS = { danger: "不能删", failed: "考核未通过", safe: "可删", unknown: "未核实" };
/* v3.4(2026-09-26 用户指令): site_exempt = D 档已免罪, 站点的明确终态结论 —— 与 site_released
 * (完整刷新未列出 = 缺席证据)分开编码, 同属「在线」徽标与「在线核实」来源桶 */
const HR_SRC_BADGES = {
  site_scope: "在线", site_satisfied: "在线", site_unsatisfied: "在线", site_released: "在线", site_exempt: "在线",
  policy: "策略", local: "本地", local_exempt: "本地", unverified: "未核",
};
const HR_SRC_BUCKETS = {
  site_scope: "在线核实", site_satisfied: "在线核实", site_unsatisfied: "在线核实", site_released: "在线核实", site_exempt: "在线核实",
  policy: "策略", local: "本地兜底", local_exempt: "本地兜底", unverified: "",
};

/* ---------------- HR 悬停弹窗(T3 进度仪表; 26-09-26-webui-hr-popup) ----------------
 * 做种时长单元格的原生 title(一大段文字)换成悬停小弹窗。渲染规则以
 * plans/26-09-25-2043-plan-webui-hr-popup-t3-progress-ledger.html 页脚「实现说明」为单点:
 * 结论短语已含来源与进行中状态 ⇒ 不出「来源章/考核中章」, 生命周期 chip 仅终态标「已结束」;
 * 双轨进度 = 本地粗轨(已做种/要求) + 站点细轨(还需/要求, 仅站点给出 need 端点时出现);
 * 角标只在结论没说时出现(还需 X / 已超出 X / 考核期已过); 数值条仅站点侧值(本地值表格行可见);
 * 无时长要求(身份层放行 / 未核实 / 未配时长)时轨道收起换状态徽记, 不留空轨。
 * 前端只做比例呈现与着色, 判定与阈值仍全部消费后端算好字段(hr.resolve / _hr_view_fields), 不重算。
 * 单例浮层 teleport 到 body 级(脱离列表容器, 同 .speed-pop 的 overflow/特异性教训);
 * prism 主题令牌挂在 html[data-theme], body 级自动继承, 弹窗无需拷贝主题。 */

/* 弹窗调度定时器(模块级, 不进响应式 —— hover 链路不为计时器付整树重渲染) */
let hrPopShowT = 0, hrPopHideT = 0;
/* 全局一次性监听(ESC / 滚动 / 缩放关弹窗)是否已挂 */
let hrPopGlobalsHooked = false;

window.AQB_HR = {
  data() {
    /* 弹窗单例状态(唯一进响应式的部分; 位置/箭头直接写 style, 不付重渲染) */
    return { hrPop: { open: false, above: false, data: null } };
  },
  methods: {
    /* ---------------- HR 展示辅助(布尔/阈值均由后端算好, 前端只做比较与着色) ----------------
     * hr_triggered / hr_satisfied: 是否触发 HR / 是否已达成要求
     * hr_req_time: 要求做种时长(秒); hr_req_ratio: 要求分享率(0 = 不要求)
     * 绝不在前端重算模板或阈值(自定义标签格式与要求值会立即失效), 见 ai/08-pitfalls。
     */
    hrTimeReached(m) {
      return m.hr_req_time > 0 && m.seeding_time >= m.hr_req_time;
    },
    hrRatioReached(m) {
      return m.hr_req_ratio > 0 && (m.ratio || 0) >= m.hr_req_ratio;
    },
    /* 对照列配色: **按列各自的要求**判定 —— 未配要求的列(如只要求时长不要求分享率)必须
     * 保持中性色, 否则会给一个"本来就没要求的数值"染上警示色, 反而是误读。
     */
    hrTimeClass(m) {
      if (!m.hr_triggered || !(m.hr_req_time > 0)) return "";
      return this.hrTimeReached(m) ? "reached" : "pending";
    },
    hrRatioClass(m) {
      if (!m.hr_triggered || !(m.hr_req_ratio > 0)) return "";
      return this.hrRatioReached(m) ? "reached" : "pending";
    },
    hrGroupClass(g) {
      if (!g.hr_triggered) return "";
      return g.hr_pending ? "pending" : "done";
    },
    /* 做种时长列的档位配色(2026-09-25): 站点已接入(hr_safety 非空)按**删除安全档位**着色 ——
     * 站点结论优先于本地(v3.0 档位即结论: 站点说已达标, 本地时长没够线也是 reached;
     * 站点考察中, 本地够线也仍 pending)。未接入回落既有本地配色, 行为与历史逐字一致。 */
    hrDurClass(m) {
      if (!m.hr_safety) return this.hrTimeClass(m);
      return HR_SAFETY_CLASSES[m.hr_safety] || "";
    },
    /* 来源徽标(2 字芯片): 当前结论来自 v3.0 优先级链哪一档 —— 在线 / 本地 / 策略 / 未核 */
    hrSrcBadge(m) {
      return m.hr_safety ? (HR_SRC_BADGES[m.hr_safety_src] || "") : "";
    },
    /* ---------------- HR 悬停弹窗: 触发调度 + 数据组装(渲染规则单点见文件头) ---------------- */

    /* 触发面 = 做种时长单元格整体(来源徽标在其内, 不单独绑): enter 120ms 后显示,
     * leave 160ms 宽限后隐藏, 移入弹窗不隐藏(可选中复制); ESC/页面滚动/窗口缩放即时关闭。
     * trg 必须在事件回调里同步捕获(timer 里 currentTarget 已失效)。 */
    hrPopEnter(ev, m) {
      const trg = ev && ev.currentTarget;
      if (!trg) return;
      this._hrPopGlobals();
      clearTimeout(hrPopHideT);
      clearTimeout(hrPopShowT);
      const d = this.hrPopData(m);
      if (!d) return;  // 无档位行(未触发/未接入)不触发, 且顺带取消前一行挂起的显示
      hrPopShowT = setTimeout(() => this._hrPopShow(d, trg), 120);
    },
    hrPopLeave() {
      clearTimeout(hrPopShowT);
      clearTimeout(hrPopHideT);
      hrPopHideT = setTimeout(() => this.hrPopHideNow(), 160);
    },
    /* 鼠标移入弹窗本身: 取消宽限隐藏(可悬停选中复制) */
    hrPopKeepOpen() {
      clearTimeout(hrPopHideT);
    },
    hrPopHideNow() {
      clearTimeout(hrPopShowT);
      clearTimeout(hrPopHideT);
      if (this.hrPop.open) this.hrPop.open = false;
    },
    _hrPopShow(d, trg) {
      this.hrPop.data = d;
      this.hrPop.open = true;
      this.$nextTick(() => {
        const el = this.$refs.hrPop;
        if (!el || !this.hrPop.open) return;
        this._hrPopPlace(el, trg);
      });
    },
    /* position:fixed 锚定触发矩形: 优先上方(间距 10px), 上方空间不足翻下方, 横向夹取视口(8px 边距),
     * 下方也放不下则贴底; 箭头指向触发矩形中心并随翻转换向。行已被轮询重建(windowing/刷新)时矩形
     * 为零 → 视为悬停目标已消失, 直接收弹窗(否则会钉在视口左上角)。 */
    _hrPopPlace(el, trg) {
      const r = trg.getBoundingClientRect();
      if (!r.width && !r.height) {
        this.hrPopHideNow();
        return;
      }
      const pw = el.offsetWidth, ph = el.offsetHeight;
      const vw = window.innerWidth, vh = window.innerHeight, gap = 10, margin = 8;
      const left = Math.max(margin, Math.min(vw - pw - margin, r.left + r.width / 2 - pw / 2));
      const below = r.top - gap - ph < margin;
      let top = below ? r.bottom + gap : r.top - gap - ph;
      if (below && top + ph > vh - margin) top = Math.max(margin, vh - margin - ph);
      el.style.left = Math.round(left) + "px";
      el.style.top = Math.round(top) + "px";
      this.hrPop.above = !below;
      const arrow = el.querySelector(".hp-arrow");
      if (arrow) {
        arrow.style.left = Math.round(Math.max(14, Math.min(pw - 14, r.left + r.width / 2 - left)) - 5) + "px";
      }
    },
    _hrPopGlobals() {
      if (hrPopGlobalsHooked) return;
      hrPopGlobalsHooked = true;
      document.addEventListener("keydown", (e) => {
        if (e.key === "Escape") this.hrPopHideNow();
      });
      window.addEventListener("scroll", () => this.hrPopHideNow(), true);
      window.addEventListener("resize", () => this.hrPopHideNow());
    },
    /* 弹窗数据组装(全为后端算好字段的展示映射; null = 不弹):
     * lane ← hr_safety(danger 橙=考察中 / failed 红=考核未通过终态 / safe 绿 / unknown 灰),
     * verdict ← hr_safety_text, 依据 ← hr_reason, 站点侧值 ← hr_site_*(与详情抽屉 hrSiteLine 同源),
     * 本地值 ← seeding_time / hr_req_time(与表格列同口径)。
     * "none" = 不适用(站点未接入且未触发), 与无字段行同等不弹。 */
    hrPopData(m) {
      if (!m.hr_safety || m.hr_safety === "none") return null;
      const lane = m.hr_safety;
      const src = m.hr_safety_src;
      const need = m.hr_site_need, remain = m.hr_site_remain;
      const seeded = m.seeding_time || 0, req = m.hr_req_time || 0;
      /* 生命周期 chip: 仅考核期已过的终态标「已结束」(考察中的短语已含进行中, 不重复) */
      const ended = ["site_satisfied", "site_unsatisfied", "site_released", "site_exempt", "local_exempt"].includes(src);
      /* 数值条 = 站点侧值专用(站点分享率/站点下载; 格式化与 hrSiteLine 同口径); 无站点侧值整条不渲染 */
      const kv = [];
      if (m.hr_site_ratio !== "") kv.push(["站点分享率", Number(m.hr_site_ratio).toFixed(2)]);
      if (m.hr_site_dl !== "") kv.push(["站点下载", this.fmtSize(m.hr_site_dl)]);
      let gauge = null, badge = "";
      if (["site_released", "site_exempt", "local_exempt", "unverified"].includes(src) || !(req > 0)) {
        /* 无时长要求(身份层放行/超龄豁免/未核实/未配时长): 轨道收起换状态徽记; 未核实用虚线盾 */
        badge = lane === "unknown" ? "dash" : "check";
      } else {
        /* 角标只在结论短语没说时出现: 考察中 = 还需 X(站点 need 优先, 缺了回落本地差值) /
         * 本地兜底 = 已超出 X 或还需 X / 终态未达标 = 考核期已过; 已达标不重复出角标(站点轨满格自明) */
        let tag = null;
        if (src === "site_unsatisfied") {
          tag = { tone: "failed", text: "考核期已过" };
        } else if (src === "site_scope") {
          if (need !== "" && need > 0) tag = { tone: "danger", text: `还需 ${this.fmtDuration(need)}` };
          else if (need === "" && remain !== 0 && req - seeded > 0) {
            tag = { tone: "danger", text: `还需 ${this.fmtDuration(req - seeded)}` };
          }
        } else if (src === "local") {
          if (seeded - req > 0) tag = { tone: "safe", text: `已超出 ${this.fmtDuration(seeded - req)}` };
          else if (req - seeded > 0) tag = { tone: "danger", text: `还需 ${this.fmtDuration(req - seeded)}` };
        } else if (src === "policy" && req - seeded > 0) {
          tag = { tone: "danger", text: `还需 ${this.fmtDuration(req - seeded)}` };
        }
        /* 站点细轨(半透明填充区分): 仅站点给出数值端点时出现 —— 考察中按 还需/要求 画剩余占比
         * (与本地已做种占比互补, 两轨并排可见分歧); 已达标满格自明; 终态未达标不画(倒计时已随考核期结束) */
        let site = null;
        if (src === "site_satisfied") {
          site = { tone: "safe", pct: 100 };
        } else if (src === "site_scope" && req > 0) {
          if (need !== "") site = { tone: "danger", pct: Math.max(0, Math.min(100, (need / req) * 100)) };
          else if (remain === 0) site = { tone: "danger", pct: 100 };
        }
        gauge = {
          tag,
          seeded: this.fmtDuration(seeded),
          req: this.fmtDuration(req),
          pct: Math.max(0, Math.min(100, (seeded / req) * 100)),
          site,
        };
      }
      return {
        lane,
        verdict: m.hr_safety_text || m.hr_safety,
        ended,
        gauge,
        badge,
        kv,
        reason: m.hr_reason || "",
        /* 站点值滞后一个刷新周期: 有站点侧数据(数值条/站点轨)才提示 */
        lag: kv.length > 0 || !!(gauge && gauge.site),
      };
    },
    /* H&R 筛选档位(2026-09-25 起四桶: 不能删/考核未通过/可删/未核实): 组级消费组内成员档位集合、
     * 成员级消费 hr_safety; 旧服务端(无 hr_safety 字段)回落本地布尔, 词汇映射进新档位。
     * 只比较后端算好的字段, 前端不重算模板/阈值(pitfalls: HR 判定前后端各写一遍 = 自定义标签立即失效) */
    /* 成员级筛选谓词: 单种子平铺/追剧集行/未识别桶共用同一套条件
     * (状态/路径/标签/分类/站点/H&R/HR来源; 多选筛选器内为或, 筛选器之间为且) */
    _memberPass(m) {
      if (this.kindFilter && m.kind !== this.kindFilter) return false;
      if (this.pathFilter.length && !this.pathFilter.includes(m.save_path || "")) return false;
      if (this.tagFilter.length && !(m.tags || []).some((t) => this.tagFilter.includes(t))) return false;
      if (this.categoryFilter.length && !this.categoryFilter.includes(m.category || "")) return false;
      if (this.siteFilter.length && !this.siteFilter.includes(m.site)) return false;
      if (this.hrFilter.length && !this.hrFilter.includes(this._hrBucketMember(m))) return false;
      if (this.hrSrcFilter.length && !this.hrSrcFilter.includes(this._hrSrcBucketMember(m))) return false;
      return true;
    },
    _hrBucketMember(m) {
      if (m.hr_safety) return HR_SAFETY_BUCKETS[m.hr_safety] || "";
      if (!m.hr_triggered) return "";
      return m.hr_satisfied ? "可删" : "不能删";
    },
    /* 组级档位集合: 组内出现过的档位各算一档(混合组同时进"不能删"与"可删") */
    _hrBuckets(g) {
      const out = [];
      for (const m of g.members || []) {
        const b = this._hrBucketMember(m);
        if (b && !out.includes(b)) out.push(b);
      }
      return out;
    },
    _hrSrcBucketMember(m) {
      return m.hr_safety ? (HR_SRC_BUCKETS[m.hr_safety_src] || "") : "";
    },
    _hrSrcBuckets(g) {
      const out = [];
      for (const m of g.members || []) {
        const b = this._hrSrcBucketMember(m);
        if (b && !out.includes(b)) out.push(b);
      }
      return out;
    },
    hrGroupTitle(g) {
      if (!g.hr_triggered) return `该${L10N_GROUP}没有成员触发 HR 条件`;
      if (!g.hr_pending) return `已触发 HR 的 ${g.hr_triggered} 个成员均已满足做种时长/分享率要求`;
      return `已触发 HR ${g.hr_triggered} 个, 其中 ${g.hr_pending} 个尚未满足做种时长/分享率要求`;
    },
    /* 站点侧三态行(详情抽屉): 结论(含来源档位) + 依据原文 —— 全由后端算好,
     * 前端只拼展示; 未接入 hr_check 的站点 hr_state 为空 ⇒ 返回空串(不显示这行) */
    hrStateLine(m) {
      if (!m.hr_state) return "";
      const why = m.hr_reason ? " · " + m.hr_reason : "";
      return `${m.hr_safety_text || m.hr_state_text}${why}`;
    },
    /* 站点侧值一行(与本地实时值对照): 空串 = 该字段站点没给; 0 要单独说"已达标"(未知 ≠ 0)
     * ❗fmtDuration/fmtSize 是 methods(format.js), 必须经 this 调 —— 裸调用在渲染函数里
     *   ReferenceError, Vue 3 会卸掉整棵组件树(白屏); 站点未接入(hr_site_lane 空)时本方法
     *   提前返回, 裸调用永远不被求值 ⇒ 雷埋着不响, 站点接入后每行 title 都踩中。
     * 档位前缀已撤(2026-09-25 用户修正): A/B/C 是站点内部档位词, 界面不展示。 */
    hrSiteLine(m) {
      if (!m.hr_site_lane) return "";
      const parts = [];
      if (m.hr_site_need !== "") parts.push(`还需做种 ${this.fmtDuration(m.hr_site_need)}`);
      if (m.hr_site_remain !== "") {
        parts.push(m.hr_site_remain === 0 ? "已达标" : `剩余达标 ${this.fmtDuration(m.hr_site_remain)}`);
      }
      if (m.hr_site_ratio !== "") parts.push(`分享率 ${Number(m.hr_site_ratio).toFixed(2)}`);
      if (m.hr_site_dl !== "") parts.push(`站点下载 ${this.fmtSize(m.hr_site_dl)}`);
      return parts.join(" · ");
    },
  },
  computed: {
    /* H&R 四桶计数(不能删/考核未通过/可删/未核实; 从未触发的行不属于任何桶):
     * 只消费后端算好的 hr_safety, 前端不重算判定; 组行 = 组内出现过的档位各计 1(计数 = 含该档的组数),
     * 种子行按自身。❗取数面走 `facetRows`(**单点**, 见 filters.js): 组视图按组计数、种子页按种子计数。
     * (原先一律遍历 decoratedGroups ⇒ 种子页(按视图分片不回 groups)恒得 0/0 —— issue 见 filters.js) */
    hrOptions() {
      const counts = { "不能删": 0, "考核未通过": 0, "可删": 0, "未核实": 0 };
      for (const r of this.facetRows) {
        const buckets = r.members ? this._hrBuckets(r) : [this._hrBucketMember(r)].filter(Boolean);
        for (const b of buckets) if (b in counts) counts[b] += 1;
      }
      return Object.entries(counts).map(([value, count]) => ({ value, count }));
    },
    /* HR 来源三档计数(在线核实/本地兜底/策略): 与 hrOptions 同一取数面 ——
     * "只看本地兜底"正是最需要等在线核实结果的一批种子 */
    hrSrcOptions() {
      const counts = { "在线核实": 0, "本地兜底": 0, "策略": 0 };
      for (const r of this.facetRows) {
        const buckets = r.members ? this._hrSrcBuckets(r) : [this._hrSrcBucketMember(r)].filter(Boolean);
        for (const b of buckets) if (b in counts) counts[b] += 1;
      }
      return Object.entries(counts).map(([value, count]) => ({ value, count }));
    },
  },
};
