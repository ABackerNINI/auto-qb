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
 * 颜色只编码「能不能删」(复用既有 pending/reached 语义色), 来源用 2 字徽标编码。 */
const HR_SAFETY_CLASSES = { danger: "pending", safe: "reached", unknown: "hr-unk" };
const HR_SAFETY_BUCKETS = { danger: "不能删", safe: "可删", unknown: "未核实" };
const HR_SRC_BADGES = {
  site_scope: "在线", site_satisfied: "在线", site_unsatisfied: "在线", site_released: "在线",
  policy: "策略", local: "本地", local_exempt: "本地", unverified: "未核",
};
const HR_SRC_BUCKETS = {
  site_scope: "在线核实", site_satisfied: "在线核实", site_unsatisfied: "在线核实", site_released: "在线核实",
  policy: "策略", local: "本地兜底", local_exempt: "本地兜底", unverified: "",
};

window.AQB_HR = {
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
    /* 做种时长列悬停全文: 含来源的完整短语 + 依据原文 + 站点侧值对照(与详情抽屉同源) */
    hrDurTitle(m) {
      if (!m.hr_safety) return "";
      return [m.hr_safety_text, m.hr_reason, this.hrSiteLine(m)].filter(Boolean).join(" · ");
    },
    /* H&R 筛选档位(2026-09-25 起四档: 不能删/可删/未核实): 组级消费组内成员档位集合、
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
    /* 种子页客户端文本过滤(R1A): 名称/站点/分类/标签/保存路径任一命中即保留(不区分大小写) */
    _torrentTextMatch(m, q) {
      return (m.name || "").toLowerCase().includes(q)
        || (m.site || "").toLowerCase().includes(q)
        || (m.category || "").toLowerCase().includes(q)
        || (m.save_path || "").toLowerCase().includes(q)
        || (m.tags || []).some((t) => t.toLowerCase().includes(q));
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
    /* 站点侧值一行(与本地实时值对照): 空串 = 该字段站点没给; 0 要单独说"已达标"(未知 ≠ 0) */
    hrSiteLine(m) {
      if (!m.hr_site_lane) return "";
      const parts = [`档位 ${m.hr_site_lane}`];
      if (m.hr_site_need !== "") parts.push(`还需做种 ${fmtDuration(m.hr_site_need)}`);
      if (m.hr_site_remain !== "") {
        parts.push(m.hr_site_remain === 0 ? "已达标" : `剩余达标 ${fmtDuration(m.hr_site_remain)}`);
      }
      if (m.hr_site_ratio !== "") parts.push(`分享率 ${Number(m.hr_site_ratio).toFixed(2)}`);
      if (m.hr_site_dl !== "") parts.push(`站点下载 ${fmtSize(m.hr_site_dl)}`);
      return parts.join(" · ");
    },
  },
  computed: {
    /* H&R 四档计数(不能删/可删/未核实; 从未触发的行不属于任何档, 与旧两档口径一致):
     * 只消费后端算好的 hr_safety, 前端不重算判定; 组行 = 组内出现过的档位各计 1(计数 = 含该档的组数),
     * 种子行按自身。❗取数面走 `facetRows`(**单点**, 见 filters.js): 组视图按组计数、种子页按种子计数。
     * (原先一律遍历 decoratedGroups ⇒ 种子页(按视图分片不回 groups)恒得 0/0 —— issue 见 filters.js) */
    hrOptions() {
      const counts = { "不能删": 0, "可删": 0, "未核实": 0 };
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
