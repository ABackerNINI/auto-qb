/* auto-qb WEB UI · 展示格式化(速度/体积/时间/时长/分享率/限速)
 *
 * app.js 按域拆分出的片段(2026-09-20)。约定与 config_editor.js / config_rules.js 同一范式:
 * 挂到 window.AQB_FORMAT, 由 app.js 末尾 app.mixin(window.AQB_FORMAT) 注入同一个 Vue 实例 ——
 * 方法体里的 this 仍是那个组件实例, 跨模块互调与拆分前完全等价。
 *
 * ❗本文件在 HTML 里必须排在 app.js **之前**(app.js 末尾要读 window.AQB_FORMAT);
 *   用到的列模型常量(TABLE_COLUMNS / MIN_COL_PX / STATE_RANK …)仍单点定义在 app.js 顶部。
 */
window.AQB_FORMAT = {
  methods: {
    fmtSpeed(v) {
      if (!v) return "0 B/s";
      for (const [unit, div] of [["GiB/s", 1073741824], ["MiB/s", 1048576], ["KiB/s", 1024]]) {
        if (v >= div) return (v / div).toFixed(2) + " " + unit;
      }
      return v + " B/s";
    },
    fmtSize(v) {
      if (v === null || v === undefined) return "-";
      if (!v) return "0 B";
      for (const [unit, div] of [["PiB", 2 ** 50], ["TiB", 2 ** 40], ["GiB", 2 ** 30], ["MiB", 2 ** 20], ["KiB", 2 ** 10]]) {
        if (v >= div) return (v / div).toFixed(2) + " " + unit;
      }
      return v + " B";
    },
    /* 0 值不显示 "0 B/s"/"0 B"(满屏零值噪声): 只留极淡占位符, 列对齐不受影响 */
    fmtSpeedOrDash(v) {
      return v ? this.fmtSpeed(v) : "";  // TBL-01: 主页面表格空值空白(抽屉调用方自行兜回"—")
    },
    fmtSizeOrDash(v) {
      return v ? this.fmtSize(v) : "";  // 同上(TBL-01)
    },
    /* 时间点显示(追剧视图"最近动静"列): 今年省年份, 往年只到日 */
    fmtTime(ts) {
      if (!ts) return "";  // TBL-01: 表格空值空白
      const d = new Date(ts * 1000);
      const p = (n) => String(n).padStart(2, "0");
      if (d.getFullYear() !== new Date().getFullYear()) return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`;
      return `${p(d.getMonth() + 1)}-${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}`;
    },
    fmtDuration(sec) {
      // 做种时长: 后端已按分钟取整(torrents._VIEW_QUANTUM), 故不展示秒位
      sec = Math.floor(sec || 0);
      if (sec < 3600) return `${Math.floor(sec / 60)}分钟`;
      if (sec < 86400) return `${Math.floor(sec / 3600)}时${String(Math.floor((sec % 3600) / 60)).padStart(2, "0")}分`;
      return `${Math.floor(sec / 86400)}天${String(Math.floor((sec % 86400) / 3600)).padStart(2, "0")}时`;
    },
    /* ETA(秒): qB 哨兵 8640000 = 无 ETA, 非正数 = 未知/缺失 —— 均显示空白(TBL-01, 种子页 R1A) */
    fmtEta(sec) {
      if (!sec || sec <= 0 || sec >= 8640000) return "";
      return this.fmtDuration(sec);
    },
    /* 时间点(unix 秒): -1/0 = 从未(qB 哨兵) —— 空白(TBL-01); 其余与追剧"最近动静"同格式 */
    fmtTs(ts) {
      if (!ts || ts < 0) return "";
      return this.fmtTime(ts);
    },
    /* 相对时间(FX-27, "最近活动"列专用): 该列要回答的是"距今多久", 绝对时间点得读者自己做减法。
     * 档位: 刚刚 / 分钟 / 小时 / 天 / 月 / 年 —— **一律相对, 不回落绝对日期**: 同一列里"有的
     * 显示 3天前、有的显示 08-11 20:56"会让人以为没改干净(2026-09-20 用户实测反馈); 长跨度
     * 的可读性损失由 title 上的绝对时间点补回(调用方挂 :title="fmtTs(...)" )。
     * 哨兵与 fmtTs 同口径: -1/0 = 从未传输 → 空白(TBL-01)。
     * ⚠ 时基必须读 this.nowSec(响应式秒计数, app.js 每 30s 一跳)而不是现取 Date.now():
     *   后端 last_activity 按分钟量化且只在活动发生时才变 ⇒ 行对象不变时 Vue 不重渲染,
     *   现取时间会让"刚刚"之类的相对值**永久停在渲染那一刻**。 */
    fmtRelTime(ts) {
      if (!ts || ts < 0) return "";
      const sec = (this.nowSec || Math.floor(Date.now() / 1000)) - ts;
      if (sec < 60) return "刚刚";                          // 含时钟偏差导致的未来时间戳
      if (sec < 3600) return `${Math.floor(sec / 60)}分钟前`;
      if (sec < 86400) return `${Math.floor(sec / 3600)}小时前`;
      if (sec < 86400 * 30) return `${Math.floor(sec / 86400)}天前`;
      if (sec < 86400 * 365) return `${Math.floor(sec / (86400 * 30))}个月前`;
      return `${Math.floor(sec / (86400 * 365))}年前`;
    },
    /* 种子限速(qB 原始 bytes/s; 0 = 不限速/跟随全局): 与限速曲线的 KiB/s 口径区分开 */
    fmtLimitBytes(v) {
      if (v === null || v === undefined) return "";  // 缺失: 空白(TBL-01)
      if (!v) return "";  // 0 = 不限速: 不再显示字样(TBL-02)
      return this.fmtSpeed(v);
    },
    /* 做种/用户列(TBL-04): qB 口径 "已连接 (总数)" —— 总数缺失(-1/null)只显示已连接 */
    fmtPeersQb(connected, total) {
      if (connected === null || connected === undefined || connected < 0) return "";
      return total === null || total === undefined || total < 0 ? String(connected) : `${connected} (${total})`;
    },
    /* ---------------- 单元格口径单点化(FX-02/03/04) ----------------
     * 以下函数是这些列口径的**唯一来源**: 明细表 / 种子页 / 追剧集明细各自引用它们,
     * 不再把表达式写在模板里(上一版同一口径在模板里各写三份, 改口径必须三处同改, 必漏)。
     * 返回值语义 = 单元格显示文本, 空串即"该状态不显示"; 刻意用空串而非 v-if 摘除节点 ——
     * 单元格仍在 grid 中占位, 列宽与表头不会错位。 */
    cellSeedingTime(m) {
      const t = m.seeding_time || 0;
      // 0 分钟且无 HR 要求 -> 不显示; HR 已触发但尚未开始做种(0 分钟)的种子**必须保留**
      // (那正是最需要被看见的一类), 故隐藏判据带上 HR 条件豁免
      if (t <= 0 && !(m.hr_triggered && m.hr_req_time)) return "";
      return this.fmtDuration(t);
    },
    /* dir = "seeds"(做种/已连接) | "leechs"(用户/下载中) */
    cellPeers(m, dir) {
      if (m.kind === "paused") return "";  // FX-03: 暂停中的种子不显示 用户/做种
      return dir === "seeds"
        ? this.fmtPeersQb(m.num_seeds, m.num_complete)
        : this.fmtPeersQb(m.num_leechs, m.num_incomplete);
    },
    cellRatio(m) {
      if (!m.progress) return "";  // FX-04: 进度为 0(未开始/未下载)的种子不显示分享率
      return (m.ratio || 0).toFixed(2);
    },
    /* 可用性(FX-26): 两个"没有有效值"的来源都不显示 ——
     * ① 负数: qB 拿不到 distributed_copies 时给 -1(未连上 tracker / 无 peer 数据), 旧版直接
     *    toFixed 出 "-1.00" 看着像真数值; ② 暂停中的种子: 没连接就谈不上分布式副本数(与
     *    FX-03 的做种/用户列同口径)。0 仍是有效值(确实零副本), 保留显示 */
    cellAvailability(m) {
      if (m.kind === "paused") return "";
      const v = m.availability;
      if (v === null || v === undefined || v < 0) return "";
      return v.toFixed(2);
    },
    /* 时间点列(FX-28): 口径**按列**独立(见 data.timeFmt 与 TIME_FMT_KEYS), 由该列表头右键菜单切换;
     * 所有时间点列一律走这两个函数, 模板里不得再直接调 fmtTime/fmtTs(否则那列就没有开关)。
     * 两种口径互为悬停提示 —— 显示相对时 title 给绝对时间点, 显示绝对时 title 给"3天前",
     * 这样长跨度(1个月前/1年前)也能一眼核对, 不必为可核对性在列内混两种格式。
     * ⚠ 统一走 fmtTs(而非 fmtTime): 它挡住了 -1 哨兵(直接 fmtTime(-1) 会渲染出 1970 年的日期)。 */
    cellTime(ts, key) {
      return this.timeFmt[key] === "rel" ? this.fmtRelTime(ts) : this.fmtTs(ts);
    },
    cellTimeHint(ts, key) {
      return this.timeFmt[key] === "rel" ? this.fmtTs(ts) : this.fmtRelTime(ts);
    },
    /* FX-28 跨标签同步(F2/F3, 与列偏好 adoptColState 同一套机制): 别的标签改了口径 → storage
     * 事件触发本方法**整份采用**存储值; 标签被冻结 / storage 事件丢失 → 回到可见时补对齐一次。
     * 整份采用而非逐列合并: 同一列的后写赢, 半合并反而会让两个标签各留一半旧值(列偏好踩过)。 */
    adoptTimeFmt() {
      this.timeFmt = loadTimeFmt();
    },
    /* 数值色阶(TBL-03): value/denom 比值分两档底色 —— ratio<0.75 → tone-low(偏弱), >=0.75 → tone-high(接近满档);
     * value<=0 或分母缺失/<=0 返回空串(交给 zero/空白机制)。全局限速分母来自 /api/stats 的 statsServer
     * (懒加载, 未开过统计面板时为 null → 速度列自动无色阶, 属预期降级, 规则内自然兜住) */
    numTone(value, denom) {
      if (!value || value <= 0 || !denom || denom <= 0) return "";
      return value / denom < 0.75 ? "tone-low" : "tone-high";
    },
    /* 限速显示: 后端单位 KiB/s(0 = 不限速, null = 该方向不管理) */
    fmtLimit(kib) {
      if (kib === null || kib === undefined) return "—";
      if (!kib) return "";  // 0 = 不限速: 不再显示字样(TBL-02); 提示/toast 文案处调用方用 || "不限速" 兜回
      return this.fmtSpeed(kib * 1024);
    },
  },
};
