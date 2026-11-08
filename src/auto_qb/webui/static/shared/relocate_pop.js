/* auto-qb WEB UI · 迁移悬停浮窗(relPop; plan 26-11-07-2344 S3)
 *
 * app.js 按域拆分出的片段, 范式与 hr.js(hrPop*)同一套: 挂到 window.AQB_RELOCATE_POP,
 * 由 app.js 末尾 app.mixin(window.AQB_RELOCATE_POP) 注入同一个 Vue 实例 —— 方法体里的
 * this 仍是那个组件实例, 跨模块互调与拆分前完全等价。
 *
 * !参照 hr.js 逐条对齐参数(enter 120ms / leave 160ms 宽限 / 移入浮窗不关 / teleport body /
 *   上下翻转 / 指向箭头 / 滚动缩放即关 / 零矩形即收), **不抽公共基类**(语义独立, 防双实现
 *   被迫耦合; plan §07 风险表: 两处参数各自演化 = 漂移, 对齐靠本注释互指 + 守阵钉数值)。
 * !零请求契约: 浮窗数据全部来自行载荷(row.relocate 组行 g.relocate / 种子行 m.relocate)与
 *   relocateView(row)(decorate.js 单点), **不发任何请求** —— /api/relocate_chain 深探测
 *   仍只在链浮窗按需触发(relChain), 渲染期零触盘零请求(P0 纪律)。
 * !触发判据: relocateView(row) 非 null 才弹(即 state ∈ {moving, pending_finalize, failed, mixed});
 *   done / cancelled / 无标注行悬停无响应 —— 不出「已完成」结论(relocateView 同口径)。
 *
 * !本文件在 HTML 里必须排在 app.js **之前**(app.js 末尾要读 window.AQB_RELOCATE_POP);
 *   消费的 relocateView / relocateStateText / relocateOriginText / fmtRelTime 都经 this 调
 *   (mixin 注入后同一实例), 无需模块级依赖。
 */

/* 弹窗调度定时器(模块级, 不进响应式 —— hover 链路不为计时器付整树重渲染; 命名与 hr.js
 * 的 hrPopShowT/hrPopHideT 对仗, 顶层 let 撞名守阵(test_overlay_fit_single_point ⑤)零容忍) */
let relPopShowT = 0, relPopHideT = 0;
/* 全局一次性监听(滚动 / 缩放关弹窗)是否已挂。ESC 不在此挂 —— 走 lifecycle.js 的退栈链
 * (plan S3 拍板「ESC 接 lifecycle 退栈链」), 与 hrPop 的自带 keydown 监听是两条路。 */
let relPopGlobalsHooked = false;

window.AQB_RELOCATE_POP = {
  data() {
    /* 弹窗单例状态(唯一进响应式的部分; 位置/箭头直接写 style, 不付重渲染)—— 形态照 hrPop */
    return { relPop: { open: false, above: false, data: null } };
  },
  methods: {
    /* ---------------- 触发调度(参数与 hr.js hrPopEnter/Leave/KeepOpen 逐条对齐) ----------------
     * 触发面 = 组行/种子行 save_path 单元格整体(xtpl-cells.html 两组分支; 浮窗只吃 hover,
     * chip 点击只筛路径不碰浮窗 —— R3 D16 零导航点击口径)。trg 必须在事件回调里同步捕获
     * (timer 里 currentTarget 已失效)。 */
    relPopEnter(ev, row) {
      const trg = ev && ev.currentTarget;
      if (!trg) return;
      this._relPopGlobals();
      clearTimeout(relPopHideT);
      clearTimeout(relPopShowT);
      if (!this.relocateView(row)) return;  // done/cancelled/无标注行不触发, 且顺带取消前一行挂起的显示
      relPopShowT = setTimeout(() => this._relPopShow(row, trg), 120);
    },
    relPopLeave() {
      clearTimeout(relPopShowT);
      clearTimeout(relPopHideT);
      relPopHideT = setTimeout(() => this.relPopHideNow(), 160);
    },
    /* 鼠标移入弹窗本身: 取消宽限隐藏(可悬停选中复制) */
    relPopKeepOpen() {
      clearTimeout(relPopHideT);
    },
    relPopHideNow() {
      clearTimeout(relPopShowT);
      clearTimeout(relPopHideT);
      if (this.relPop.open) this.relPop.open = false;
    },
    _relPopShow(row, trg) {
      const d = this.assembleRelPop(row);
      if (!d) return;
      this.relPop.data = d;
      this.relPop.open = true;
      this.$nextTick(() => {
        const el = this.$refs.relPop;
        if (!el || !this.relPop.open) return;
        this._relPopPlace(el, trg);
      });
    },
    /* position:fixed 锚定触发矩形: **below 优先**(下方空间不足才翻 above, 与 hrPop 的 above
     * 优先相反 —— 路径列在行内偏下, 下翻是常态), 横向夹取视口(8px 边距, 走 overlay_fit 单点),
     * 箭头指向触发矩形中心并随翻转换向。行已被轮询重建(windowing/刷新)时矩形为零 →
     * 视为悬停目标已消失, 直接收弹窗(否则会钉在视口左上角)。 */
    _relPopPlace(el, trg) {
      const FIT = window.AQB_OVERLAY_FIT; /* 几何单点(issue 26-10-20-2231), 方法内取别名 */
      const r = trg.getBoundingClientRect();
      if (!r.width && !r.height) {
        this.relPopHideNow();
        return;
      }
      const pw = el.offsetWidth, ph = el.offsetHeight;
      const gap = 10, margin = FIT.EDGE;
      const left = FIT.clampAxis(r.left + r.width / 2 - pw / 2, pw, window.innerWidth, margin);
      const below = r.bottom + gap + ph <= window.innerHeight - margin;
      let top = below ? r.bottom + gap : r.top - gap - ph;
      if (!below && top < margin) {
        top = FIT.clampAxis(margin, ph, window.innerHeight, margin);  // 上下都放不下: 贴上缘
      }
      el.style.left = Math.round(left) + "px";
      el.style.top = Math.round(top) + "px";
      this.relPop.above = !below;
      const arrow = el.querySelector(".rp-arrow");
      if (arrow) {
        arrow.style.left = Math.round(Math.max(14, Math.min(pw - 14, r.left + r.width / 2 - left)) - 5) + "px";
      }
    },
    _relPopGlobals() {
      if (relPopGlobalsHooked) return;
      relPopGlobalsHooked = true;
      window.addEventListener("scroll", () => this.relPopHideNow(), true);
      window.addEventListener("resize", () => this.relPopHideNow());
    },
    /* ---------------- 弹窗数据组装(全行载荷, 零请求) ----------------
     * relocateView(row) 为 null 时返回 null(与触发判据双保险); 字段来源:
     *   verdict ← relocateStateText(rel.state)(现状词表, mixed = 「迁移多任务」, 不新造文案);
     *   phase   ← rel.phase 原始相位串(小字 mono; 组级聚合无 phase → 省略);
     *   tone    ← relocateView(row).tone(与行内两排/单排着色同一判定, 不重算);
     *   paths   ← rel.src / rel.dst(组行 dst 是数组: mixed 逐行全标「目标位置」无当前位置行,
     *             非 mixed 回落同 pair 形态, 数据在就给);
     *   kv      ← 组行才有成员行(pending/total); 别名行仅种子行(member_relocate 有 alias_count,
     *             组级聚合没有 → 组行省略); 来源 ← relocateOriginText(rel.origin)(组级无 origin
     *             字段 → 省略, 不落「未知来源」); 更新 ← fmtRelTime 相对时间(format.js 现成);
     *   reason  ← 仅 rel.state==='failed' 且 rel.reason 非空, 前缀「原因: 」。
     */
    assembleRelPop(row) {
      const view = this.relocateView(row);
      if (!view) return null;
      const rel = row.relocate;
      const isGroup = !!row.members;
      /* 路径块: pair = 当前位置/目标位置各一行; one = 按数据在就给(组行 dst 是数组) */
      const paths = [];
      if (view.mode === "pair") {
        paths.push(["当前位置", rel.src]);
        paths.push(["目标位置", isGroup ? rel.dst[0] : rel.dst]);
      } else if (rel.state === "mixed") {
        for (const d of rel.dst || []) if (d) paths.push(["目标位置", d]);
      } else {
        if (rel.src) paths.push(["当前位置", rel.src]);
        const dsts = isGroup ? (rel.dst || []) : [rel.dst];
        for (const d of dsts) if (d) paths.push(["目标位置", d]);
      }
      /* kv 行(次序: 成员 → 别名 → 来源 → 更新; 值全部行载荷) */
      const kv = [];
      if (isGroup) {
        if (rel.total > 0) kv.push(["成员", `${rel.pending}/${rel.total} 个成员待收尾`]);
      } else {
        if (typeof rel.alias_count === "number") {
          kv.push(["别名", rel.alias_count > 0 ? `链接位 ×${rel.alias_count}` : "—"]);
        }
      }
      if (rel.origin) kv.push(["来源", this.relocateOriginText(rel.origin)]);
      kv.push(["更新", rel.updated_at ? this.fmtRelTime(rel.updated_at) : "—"]);
      const reason = rel.state === "failed" && rel.reason ? `原因: ${rel.reason}` : "";
      return {
        verdict: this.relocateStateText(rel.state),
        phase: rel.phase || "",
        tone: view.tone,
        paths,
        kv,
        reason,
      };
    },
  },
};
