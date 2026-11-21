/* auto-qb WEB UI · 迁移悬停浮窗(relPop; plan 26-11-07-2344 S3)
 *
 * app.js 按域拆分出的片段, 范式与 hr.js(hrPop*)同一套: 挂到 window.AQB_RELOCATE_POP,
 * 由 app.js 末尾 app.mixin(window.AQB_RELOCATE_POP) 注入同一个 Vue 实例 —— 方法体里的
 * this 仍是那个组件实例, 跨模块互调与拆分前完全等价。
 *
 * !参照 hr.js 逐条对齐参数(enter 120ms / leave 160ms 宽限 / 移入浮窗不关 / teleport body /
 *   上下翻转 / 指向箭头 / 滚动缩放即关 / 零矩形即收), **不抽公共基类**(语义独立, 防双实现
 *   被迫耦合; plan §07 风险表: 两处参数各自演化 = 漂移, 对齐靠本注释互指 + 守阵钉数值)。
 * !零请求契约: 浮窗**数据**全部来自行载荷(row.relocate 组行 g.relocate / 种子行 m.relocate)与
 *   relocateView(row)(decorate.js 单点), 组装/渲染**不发任何请求** —— /api/relocate_chain 深探测
 *   仍只在链浮窗按需触发(relChain), 渲染期零触盘零请求(P0 纪律)。唯一例外是 relPopClearHistory
 *   (S3 D3/D5 清空迁移历史): 显式点击才发的用户动作, 不破渲染期零请求(见方法注)。
 * !触发判据: relocateView(row) 非 null(即 state ∈ {moving, pending_finalize, failed, mixed,
 *   foreign} —— foreign 是 T5 外部旧路径种子通知态, 专属块见 assembleRelPop; 计划
 *   26-11-20-0434), 或终态窄放行谓词 _relPopTerminalGate(row) 通过(done / cancelled 且
 *   relocateResumeText 非空 —— 终态残留的恢复账余量行给浮窗入口, 判据与抽屉迁移段同一
 *   单点; issue 26-11-15-0345, plan 26-11-15-0914 S3 D5/D11)。无标注行悬停无响应;
 *   行内「不出已完成结论」的展示边界一条不动(RELOCATE_TONE / 行内着色零触碰,
 *   done/cancelled 行内仍单排正常色)。
 *
 * !本文件在 HTML 里必须排在 app.js **之前**(app.js 末尾要读 window.AQB_RELOCATE_POP);
 *   消费的 relocateView / relocateStateText / relocateOriginText / fmtRelTime 都经 this 调
 *   (mixin 注入后同一实例), 无需模块级依赖。
 */

/* 弹窗调度定时器(模块级, 不进响应式 —— hover 链路不为计时器付整树重渲染; 命名与 hr.js
 * 的 hrPopShowT/hrPopHideT 对仗, 顶层 let 撞名守阵(test_overlay_fit_single_point (5))零容忍) */
let relPopShowT = 0, relPopHideT = 0;
/* 全局一次性监听(滚动 / 缩放关弹窗)是否已挂。ESC 不在此挂 —— 走 lifecycle.js 的退栈链
 * (plan S3 拍板「ESC 接 lifecycle 退栈链」), 与 hrPop 的自带 keydown 监听是两条路。 */
let relPopGlobalsHooked = false;

/* 终态展示状态集(S3 清空历史按钮的可见性判据; 与后端派生单点 units.display_state_of_phase
 * 的输出词表同源 —— 词值进投影契约, 改值须两端同步; 跨端同值断言钉扎在
 * tests/test_webui_relocate_pop.py(REL_TERMINAL_STATES 字面量集 == units 展示词终态集),
 * 后端词表单点在 units.display_state_of_phase / DISPLAY_* 常量)。
 * 终态行(failed 常驻浮窗 / done/cancelled 经恢复账窄放行)是迁移历史唯一可见面, 「清空历史」
 * 入口就挂在这(计划 26-11-15-2340 §03.4 D3/D5: 失败记录永不自动清, 只能手动清空)。 */
const REL_TERMINAL_STATES = new Set(["done", "failed", "cancelled", "superseded"]);

window.AQB_RELOCATE_POP = {
  data() {
    /* 弹窗单例状态(唯一进响应式的部分; 位置/箭头直接写 style, 不付重渲染)—— 形态照 hrPop */
    return { relPop: { open: false, above: false, data: null } };
  },
  methods: {
    /* ---------------- 终态窄放行谓词(issue 26-11-15-0345; plan 26-11-15-0914 S3 D5/D11) ----------------
     * done / cancelled 终态行上残留的恢复确认账余量(relocateResumeText 非空)给浮窗入口 ——
     * 判据与抽屉迁移段走同一文案单点(relocateResumeText), 不另写第二份口径。组行同样过闸,
     * 但组级聚合无恢复账(group_relocate 载荷无 resume 字段), 经此谓词恒 false —— 账是
     * 种子/成员行的, 组行不弹。行内展示边界不动: RELOCATE_TONE / 行内着色零触碰,
     * done/cancelled 行内仍单排正常色(decorate.js 注释口径原样)。 */
    _relPopTerminalGate(row) {
      const rel = row && row.relocate;
      if (!rel || (rel.state !== "done" && rel.state !== "cancelled")) return false;
      return !!this.relocateResumeText(rel);
    },
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
      // 无标注行与终态无账行不触发(relocateView null 且终态窄放行不过), 且顺带取消前一行挂起的显示
      if (!this.relocateView(row) && !this._relPopTerminalGate(row)) return;
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
     * 箭头指向触发矩形中心并随翻转换向。行已被轮询重建(windowing/刷新)时矩形为零 ->
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
     * relocateView(row) 为 null 时: 终态窄放行行(_relPopTerminalGate 通过)用中性 tone 替身
     * view 组装(替身只在本文件内构造, 不回写 relocateView/共享面 —— D11), 其余返回 null
     * (与触发判据双保险); 字段来源:
     *   verdict <- relocateStateText(rel.state)(现状词表, mixed = 「迁移多任务」, 不新造文案;
     *             done/cancelled = 「已完成/已撤销」已在词表, 终态窄放行零改动复用);
     *   phase   <- rel.phase 原始相位串(小字 mono; 组级聚合无 phase -> 省略);
     *   tone    <- view.tone(进行中四态与行内两排/单排着色同一判定, 不重算; 终态窄放行 =
     *             中性替身 "neutral", 见下);
     *   paths   <- rel.src / rel.dst(组行 dst 是数组: mixed 逐行全标「目标位置」无当前位置行,
     *             非 mixed 回落同 pair 形态, 数据在就给);
     *   kv      <- 组行才有成员行(pending/total); 别名行仅种子行(member_relocate 有 alias_count,
     *             组级聚合没有 -> 组行省略); 待恢复行仅种子行且账非空(relocateResumeText 非空串,
     *             issue 26-11-14-1744 (3): 计数+在途/穷尽态, 组级聚合无该账 -> 省略); 来源 <-
     *             relocateOriginText(rel.origin)(组级无 origin 字段 -> 省略, 不落「未知来源」);
     *             更新 <- fmtRelTime 相对时间(format.js 现成);
     *   reason  <- 仅 rel.state==='failed' 且 rel.reason 非空, 前缀「原因: 」。
     */
    assembleRelPop(row) {
      let view = this.relocateView(row);
      if (!view) {
        /* 闸放行但 view 缺失 = 终态窄放行行(relocateView 对 done/cancelled 恒 null): 构造中性
         * tone 替身。实读字段仅 mode/tone(R4: 以实读为准) —— mode="one" 走单排回落(src/dst
         * 按数据在就给, 终态行给的是历史路径); a/b/label 补齐 relocateView 输出形状(当前无
         * 消费, 备形状一致)。替身只在本文件内用, 不回写共享面(D11)。 */
        if (!this._relPopTerminalGate(row)) return null;  // 与触发判据双保险
        view = { mode: "one", tone: "neutral", a: null, b: null, label: null };
      }
      const rel = row.relocate;
      const isGroup = !!row.members;
      /* foreign(T5, 计划 26-11-20-0434): 外部旧路径种子通知态 —— 专属路径块(旧路径 +
       * 数据现位置)与「首见」kv, 不出 job 机械面(相位/别名/待恢复/来源/更新都是收尾机器
       * 的行, 外部种子没有)。组行 dst 是数组(组级聚合): 非 null 成员逐项给「数据现位置」,
       * 与紧邻 one 回落分支同构 —— 全空/空数组才落已过期文案(评审 minor 5: [] || fallback
       * 恒真会把全过期组渲染成空值)。降级判据读后端投影 expired 位(评审 minor 6: 区分位
       * 只认后端, 不按 dst 空实重推, 与 resume_exhausted 先例同口径), 文案走
       * foreignExpiredText() 单点(评审 nit 9)。 */
      const isForeign = rel.state === "foreign";
      /* 路径块: pair = 当前位置/目标位置各一行; one = 按数据在就给(组行 dst 是数组) */
      const paths = [];
      if (isForeign) {
        if (rel.src) paths.push(["旧路径", rel.src]);
        const locs = (isGroup ? (rel.dst || []) : [rel.dst]).filter((d) => d);
        /* 降级判据(minor 6): 种子行只认后端 expired 位(真读该位, dst 空实不参与判定 ——
         * expired=false 且无现位置按「数据在就给」不出行, 不谎报已过期); 组行聚合无该位,
         * 按评审 minor 5 口径以空数组表达全员过期。文案单点 foreignExpiredText(nit 9)。 */
        const showExpired = !!rel.expired || (isGroup && !locs.length);
        if (showExpired) {
          paths.push(["数据现位置", this.foreignExpiredText()]);
        } else {
          for (const d of locs) paths.push(["数据现位置", d]);
        }
      } else if (view.mode === "pair") {
        paths.push(["当前位置", rel.src]);
        paths.push(["目标位置", isGroup ? rel.dst[0] : rel.dst]);
      } else if (rel.state === "mixed") {
        for (const d of rel.dst || []) if (d) paths.push(["目标位置", d]);
      } else {
        if (rel.src) paths.push(["当前位置", rel.src]);
        const dsts = isGroup ? (rel.dst || []) : [rel.dst];
        for (const d of dsts) if (d) paths.push(["目标位置", d]);
      }
      /* kv 行(次序: 成员 -> 别名 -> 待恢复 -> 来源 -> 更新; 值全部行载荷; foreign 只给首见) */
      const kv = [];
      if (isForeign) {
        kv.push(["首见", rel.first_seen ? this.fmtTs(rel.first_seen) : "—"]);
      } else {
        if (isGroup) {
          if (rel.total > 0) kv.push(["成员", `${rel.pending}/${rel.total} 个成员待收尾`]);
        } else {
          if (typeof rel.alias_count === "number") {
            kv.push(["别名", rel.alias_count > 0 ? `链接位 ×${rel.alias_count}` : "—"]);
          }
          const resume = this.relocateResumeText(rel);
          if (resume) kv.push(["待恢复成员", resume]);
        }
        if (rel.origin) kv.push(["来源", this.relocateOriginText(rel.origin)]);
        kv.push(["更新", rel.updated_at ? this.fmtRelTime(rel.updated_at) : "—"]);
      }
      /* reason 槽(B2, 计划 26-11-21-1600): failed 给原因; foreign mismatch 条目给准确语义
       * 说明行(文案单点 foreignMismatchText, 判据读后端投影 kind 位)—— 同挂 foreign 档
       * (verdict 词/tone 不扩面), 差异只在说明; 两分支互斥不可能同拍。 */
      const reason = rel.state === "failed" && rel.reason
        ? `原因: ${rel.reason}`
        : (isForeign && rel.kind === "mismatch" ? this.foreignMismatchText() : "");
      return {
        verdict: this.relocateStateText(rel.state),
        phase: isForeign ? "" : (rel.phase || ""),
        tone: view.tone,
        paths,
        kv,
        reason,
        /* 清空历史入口(S3 D3/D5): 终态行才给 —— 失败记录永不自动清, 手动清空是唯一出口;
         * 在途态不亮(在途账没有清空面, 撤销走行内菜单/抽屉的撤销语义); foreign 是通知态
         * 非终态, 不亮。 */
        clearable: REL_TERMINAL_STATES.has(rel.state),
      };
    },

    /* ---------------- 清空迁移历史(S3 D3/D5, 计划 26-11-15-2340 §03.4) ----------------
     * 唯一的手动清理入口(失败/取消记录永不自动清)。浮窗数据仍零请求 —— 本方法是**显式
     * 点击**才发的用户动作, 不破「渲染期零请求」契约。两步确认走与 relocate_cancel 同款
     * 协议: 第一步 POST 不带 confirm 只取路由层持有的现场说明(文案单点, 前端不硬编码
     * 第二份), confirmDialog 展示后才发 confirm:true; 执行回执经 cmd 通道异步落 truth
     * (deferred 回执族) —— 必须 waitCmd 等真值(cls/cleared/remaining/note), HTTP 层的
     * {queued, cmd_id} 不含结果, 直接判它会谎报(评审 blocker-1)。I1 缓行/挂账缓行的
     * 剩余账在真值 note 里说明。 */
    async relPopClearHistory() {
      if (this._relPopClearing) return;
      let face;
      try {
        face = await this.api("/api/relocate/history/clear", {
          method: "POST",
          body: JSON.stringify({}),
        });
      } catch (e) {
        this.toast("清空迁移历史不可用: " + ((e && e.message) || "网络或服务端错误"), "warn", 10000);
        return;
      }
      const ok = await this.confirmDialog("清空迁移历史", (face && face.note) || "", {
        okText: "清空",
        danger: true,
      });
      if (!ok) return;
      this._relPopClearing = true;
      try {
        const resp = await this.api("/api/relocate/history/clear", {
          method: "POST",
          body: JSON.stringify({ confirm: true }),
        });
        const r = await this.waitCmd(resp.cmd_id);
        this.relPopHideNow();
        const truth = (r && r.truth) || null;
        if (r.ok && truth && truth.cls === "ok") this.toast(truth.note || "迁移历史已清空", "ok", 10000);
        else this.toast((truth && truth.note) || (r && r.error) || "清空未执行, 结果以程序日志为准", "warn", 10000);
      } catch (e) {
        const msg = (e && e.message) || "网络或服务端错误";
        this.toast("清空迁移历史不可用: " + msg, "warn", 10000);
      } finally {
        this._relPopClearing = false;
      }
    },
  },
};
