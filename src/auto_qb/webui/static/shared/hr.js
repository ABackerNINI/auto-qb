/* auto-qb WEB UI · H&R 命中判定与配色
 *
 * app.js 按域拆分出的片段(2026-09-20)。约定与 config_editor.js / config_rules.js 同一范式:
 * 挂到 window.AQB_HR, 由 app.js 末尾 app.mixin(window.AQB_HR) 注入同一个 Vue 实例 ——
 * 方法体里的 this 仍是那个组件实例, 跨模块互调与拆分前完全等价。
 *
 * ❗本文件在 HTML 里必须排在 app.js **之前**(app.js 末尾要读 window.AQB_HR);
 *   用到的列模型常量(TABLE_COLUMNS / MIN_COL_PX / STATE_RANK …)仍单点定义在 app.js 顶部。
 */
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
    /* H&R 筛选档位(R07): 组级消费组级计数、成员级消费布尔, 标签一致;
     * 只比较后端算好的字段, 前端不重算模板/阈值(pitfalls: HR 判定前后端各写一遍 = 自定义标签立即失效) */
    /* 成员级筛选谓词: 单种子平铺/追剧集行/未识别桶共用同一套条件
     * (状态/路径/标签/分类/站点/H&R; 多选筛选器内为或, 筛选器之间为且) */
    _memberPass(m) {
      if (this.kindFilter && m.kind !== this.kindFilter) return false;
      if (this.pathFilter.length && !this.pathFilter.includes(m.save_path || "")) return false;
      if (this.tagFilter.length && !(m.tags || []).some((t) => this.tagFilter.includes(t))) return false;
      if (this.categoryFilter.length && !this.categoryFilter.includes(m.category || "")) return false;
      if (this.siteFilter.length && !this.siteFilter.includes(m.site)) return false;
      if (this.hrFilter.length && !this.hrFilter.includes(this._hrBucketMember(m))) return false;
      return true;
    },
    _hrBucket(g) {
      if (!g.hr_triggered) return "";
      return g.hr_pending > 0 ? "未达标" : "达标";
    },
    _hrBucketMember(m) {
      if (!m.hr_triggered) return "";
      return m.hr_satisfied ? "达标" : "未达标";
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
    /* 站点侧三态行(详情抽屉): 身份 + 达标依据来源 + 依据原文 —— 全由后端算好,
     * 前端只拼展示; 未接入 hr_check 的站点 hr_state 为空 ⇒ 返回空串(不显示这行) */
    hrStateLine(m) {
      if (!m.hr_state) return "";
      const src = m.hr_triggered ? (m.hr_satisfied_src === "site" ? " · 达标依据: 站点" : " · 达标依据: 本地兜底") : "";
      const why = m.hr_reason ? " · " + m.hr_reason : "";
      return `${m.hr_state_text}${src}${why}`;
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
    /* H&R 两档计数(只消费后端算好的组级/成员级布尔, 前端不重算模板/阈值, 见 pitfalls):
     * 达标 = 触发过 HR 且已全部满足; 未达标 = 仍有成员未满足; 无 HR 行不匹配任何档。
     * ❗取数面走 `facetRows`(**单点**, 见 filters.js): 组视图按组计数、种子页按种子计数 ——
     *   原先一律遍历 decoratedGroups ⇒ 种子页(按视图分片不回 groups)恒得 0/0(issue 见 filters.js)。 */
    hrOptions() {
      let done = 0;
      let pending = 0;
      for (const r of this.facetRows) {
        const bucket = r.members ? this._hrBucket(r) : this._hrBucketMember(r);
        if (!bucket) continue;
        if (bucket === "未达标") pending += 1;
        else done += 1;
      }
      return [{ value: "达标", count: done }, { value: "未达标", count: pending }];
    },
  },
};
