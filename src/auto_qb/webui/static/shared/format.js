/* auto-qb WEB UI · 展示格式化(速度/体积/时间/时长/分享率/限速)
 *
 * app.js 按域拆分出的片段(2026-09-20)。约定与 config_editor.js / config_rules.js 同一范式:
 * 挂到 window.AQB_FORMAT, 由 app.js 末尾 app.mixin(window.AQB_FORMAT) 注入同一个 Vue 实例 ——
 * 方法体里的 this 仍是那个组件实例, 跨模块互调与拆分前完全等价。
 *
 * !本文件在 HTML 里必须排在 app.js **之前**(app.js 末尾要读 window.AQB_FORMAT);
 *   用到的列模型常量(TABLE_COLUMNS / MIN_COL_PX / STATE_RANK …)仍单点定义在 app.js 顶部。
 */
/* 单位梯数据单点(收敛 issue 26-10-20-2231 / 台账 R20-C-09 + R20-F-05): 字节/速度两族的
 * 档位与 1024 进制只此一张表。加/删档(如补 PiB 速度档)只改这里; 曲线图专用梯顶截断见
 * _fmtLadder 的 top 参数 —— 调用侧**禁止另抄一份梯子**。 */
const AQB_UNIT_LADDER = {
  bytes: [["PiB", 2 ** 50], ["TiB", 2 ** 40], ["GiB", 2 ** 30], ["MiB", 2 ** 20], ["KiB", 2 ** 10]],
  speed: [["GiB/s", 2 ** 30], ["MiB/s", 2 ** 20], ["KiB/s", 2 ** 10]],
};
window.AQB_FORMAT = {
  methods: {
    /* 单位梯消费单点(S5 拆分形态, 计划 26-11-20-0009/D11): 参数与字符串形态 _fmtLadder 完全
     * 一致(digits = 小数位, roundFallback = 梯下原值是否取整, top = 梯顶档位名 —— 曲线图轴标
     * 要短, 只到 TiB; 缺省用整张梯), 返回拆分对象 {v, u, c} —— v = 数值串(toFixed/取整口径与
     * 串形态同), u = 单位串(**前导空格归属单位**: 拼接 v+u 与串形态逐字一致, 拆分后文本总宽
     * 不变), c = 单位档类 csu-族(大小族 csu-B/csu-KiB..csu-PiB、速度族 csu-Bs/csu-KiBs..
     * csu-GiBs —— 类名 's' 尾即速度族标记, 分族双色与按档组都靠它区分, 不另设族标记类; 颜色
     * 由 CSS 按 html[data-cs-units] 派生映射, JS 永不产颜色值, R4)。字符串形态 _fmtLadder 改为
     * 本函数的拼接消费面 —— 拆分与否结构性同源, 不会有第二份梯子走样; 表格(toFixed(2)+原样
     * 兜底)与图轴(toFixed(1)+取整兜底)的精度分歧是设计而非疏漏, 由参数各自表达。 */
    _fmtLadderParts(v, kind, digits, roundFallback, top) {
      const floor = kind === "speed" ? "B/s" : "B";
      const ladder = AQB_UNIT_LADDER[kind];
      let i = 0;
      if (top) {
        const at = ladder.findIndex((rung) => rung[0] === top);
        if (at >= 0) i = at;  // 档位名写错(改表忘了改调用)时回落整张梯, 不静默错值
      }
      for (; i < ladder.length; i++) {
        if (v >= ladder[i][1]) return { v: (v / ladder[i][1]).toFixed(digits), u: " " + ladder[i][0], c: "csu-" + ladder[i][0].replace("/", "") };
      }
      return { v: String(roundFallback ? Math.round(v) : v), u: " " + floor, c: "csu-" + floor.replace("/", "") };
    },
    /* 单位梯字符串形态(曲线轴标/抽屉行/状态栏等单文本节点消费面): 拆分形态的拼接投影 */
    _fmtLadder(v, kind, digits, roundFallback, top) {
      const p = this._fmtLadderParts(v, kind, digits, roundFallback, top);
      return p.v + p.u;
    },
    fmtSpeed(v) {
      if (!v) return "0 B/s";
      return this._fmtLadder(v, "speed", 2, false);
    },
    fmtSize(v) {
      if (v === null || v === undefined) return "-";
      if (!v) return "0 B";
      return this._fmtLadder(v, "bytes", 2, false);
    },
    /* 0 值不显示 "0 B/s"/"0 B"(满屏零值噪声): 只留极淡占位符, 列对齐不受影响 */
    fmtSpeedOrDash(v) {
      return v ? this.fmtSpeed(v) : "";  // TBL-01: 主页面表格空值空白(抽屉调用方自行兜回"—")
    },
    fmtSizeOrDash(v) {
      return v ? this.fmtSize(v) : "";  // 同上(TBL-01)
    },
    /* ---------------- 列风格 S5: 单位拆分 parts 家族(计划 26-11-20-0009 S5/D11) ----------------
     * fmtSize/fmtSpeed 的拆分形态: 返回 {v, u, c} 或 null —— null = 零值 dash 形态不拆, 与
     * fmtSizeOrDash/fmtSpeedOrDash 的空串口径同源(0/null/undefined/NaN 一律 null; 刻意与串
     * 形态哨兵 fmtSpeed(0)="0 B/s"/fmtSize(null)="-" 不同: parts 只服务表格双 span 消费面,
     * 零值走 dash 空白)。模板形态 <span class="cs-v">v</span><span class="cs-u" :class="c">u</span>
     * (u 携带前导空格, 拼串与 fmt 输出逐字一致, 文本总宽不变); 拆分**恒产**(「统一」组也拆,
     * 同色 = 视觉与现状无差, 单一代码路径不分支); c = 单位档类(含义见 _fmtLadderParts)。
     * 消费面 = xtpl-cells.html 四行模型的大小/速度族格(member 行 D5 排除、抽屉变体预装配串
     * 与状态栏不纳入, 上下限列同走本族 —— fmtLimitBytes 的空串口径与真值门逐值等价)。
     * 一致性由 node 电池钉死: 非 null 时 v+u == fmtSize/fmtSpeed 全单位梯逐字。 */
    fmtSizeParts(v) {
      return v ? this._fmtLadderParts(v, "bytes", 2, false) : null;  // 零值 dash 形态不拆
    },
    fmtSpeedParts(v) {
      return v ? this._fmtLadderParts(v, "speed", 2, false) : null;  // 同上(TBL-01 空值口径)
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
      // 做种时间: 后端已按分钟取整(torrents._VIEW_QUANTUM), 故不展示秒位
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
     * 哨兵与 fmtTs 同口径: -1/0 = 从未传输 -> 空白(TBL-01)。
     * WARN: 时基必须读 this.nowSec(响应式秒计数, app.js 每 30s 一跳)而不是现取 Date.now():
     *   后端 last_activity 按分钟量化且只在活动发生时才变 => 行对象不变时 Vue 不重渲染,
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
    /* 进度百分比单点(收敛 issue 26-10-20-2231 / 台账 R23-B-07): group / torrent / ep / member
     * 四个行模型的进度单元格此前各手写 Math.min(100, X*100)(条宽) 与 (X*100).toFixed(1)(文本)
     * —— 口径要改得四处同改, 必漏。钳上界 100: 条宽不得溢出单元格; 文本同取钳后值(progress>1
     * 时旧文本显示 >100% 而条已满格, 本就不一致, 顺带收口)。 */
    progPct(v) {
      return Math.min(100, v * 100);
    },
    /* 进度分档(计划 26-11-20-0009 S3/D7/D9): 输入进度百分比(progPct 口径, 0-100), 输出档位号
     * 0..6 —— 0 = 空端点(0%, 类 csb-0) / 1..5 = 五档(**左开右闭**: (0,20]→1 … (80,100)→5) /
     * 6 = 终点(100%, 类 csb-t)。边界: 20% 等整点归当档右端(左开右闭, 20 归 1 不归 2 —— Math.ceil
     * 正好给出该语义); >=100 一律终点档(>100 超界同归终点: progPct 已钳 100, 对端变体的预装
     * 百分比直入时也兜住); <=0(含负值/NaN/undefined)一律空端点档。类名装配走 progBandClass
     * (渲染器消费面, 条填充与百分比文字同挂): 类只表档位, 颜色由 CSS 按 html[data-cs-barramp]
     * 派生映射 —— JS 永不产颜色值(R4); 「跟随状态」档档位类照挂但无任何映射规则, 现状 --st
     * 链与状态着色一字不动(D7)。 */
    progBand(p) {
      if (!(p > 0)) return 0;
      if (p >= 100) return 6;
      return Math.ceil(p / 20);
    },
    progBandClass(p) {
      const band = this.progBand(p);
      return band === 6 ? "csb-t" : "csb-" + band;
    },
    /* ---------------- 列风格 S4: 速度色阶与数值列色阶(计划 26-11-20-0009 S4/D8/D9/D10) ----------------
     * 判定纯函数(speedBand / numScale 三件)与渲染器消费面(cellSpeedTone / cellNumScaleRatio /
     * cellNumScaleAvail)只产**档位/语义类名**, 颜色全部由 console_hub.css 按 html[data-cs-speedramp]
     * / html[data-cs-numeric] 属性派生映射 —— JS 永不产颜色值(R4)。csp- 与 cst- 是独立命名空间
     * (R6): 不碰 tone- 链与 HR 伴值链(.m-pair), 不与 S2 菜单色样 cs-* / S3 进度档 csb-* 重叠。 */
    /* 速度分档(S4/D8/D9): 输入行速度 bytes 与该方向全局限速 limit(bytes/s)——分母由调用方从
     * 行模型传入, 读数路径与既有 numTone 的 dlspeed/upspeed 挂点一致($root.speedLimitBytes,
     * dialogs.js 单点: null=未知/0=不限), 输出档位号 0..6 —— 0 = 无档(不产类: 速度 0 本就空白
     * fmtSpeedOrDash、分母 0=不限/null=未知恒不着色)/1..5 = 五档(**左开右闭**: (0,20%]→1 …
     * (80,100%]→5, 与 progBand 同构)/6 = over(>100% 超限; 恰 100% 仍第 5 档 —— over 是严格
     * 大于)。与 numTone 的 0.75 旧档互不干扰: 两套类链由 cellSpeedTone 按 speedramp 维互斥
     * 派发, 从不同时在链上。 */
    speedBand(bytes, limit) {
      if (!bytes || bytes <= 0 || !limit || limit <= 0) return 0;
      const ratio = bytes / limit;
      return ratio > 1 ? 6 : Math.ceil(ratio * 5);
    },
    /* 速度档类装配: 0 -> ""(无类) / 1..5 -> csp-1..csp-5 / 6 -> csp-over(类只表档位) */
    speedBandClass(bytes, limit) {
      const band = this.speedBand(bytes, limit);
      return band === 0 ? "" : band === 6 ? "csp-over" : "csp-" + band;
    },
    /* 速度格着色消费面(dlspeed/upspeed 两格挂点, 分母同既有 numTone 读数路径): speedramp 三态
     * 互斥派发 —— current(跟随现状, 默认) -> numTone 两档类链**原样返回**(tone-* 链与现状逐值
     * 等价); off(关) -> 空串(仅速度两列回落级联基线; up_limit/dl_limit 的 numTone 挂点在各自
     * 模板分支不受扰 —— D8: 分母不同不混); 选谱 -> speedBandClass(csp-*, 颜色由 CSS 派生)。
     * 关闭机制走 JS 类链源头而非 CSS 复位: 单元格 DOM 无列标识(行是 grid 且列可隐藏重排,
     * nth-child 不可依赖), tone-* 的 CSS 复位规则必然波及 uploaded/downloaded 等其它消费列
     * (R6) —— 三态互斥在类链源头一处收口。 */
    cellSpeedTone(bytes, limit) {
      const ramp = this.colStyle.speedramp;
      if (ramp === "current") return this.numTone(bytes, limit);
      if (ramp === "off") return "";
      return this.speedBandClass(bytes, limit);
    },
    /* 数值列色阶判定三件(S4/D10, 纯函数只认值本身): ratio <1 -> cst-warn(未回本) / >=1 ->
     * cst-good; availability <1 -> cst-warn / >=1 不产类(不着色; 负数 = qB 未知哨兵 -1、缺失
     * 同 cellAvailability 口径不产); eta <60s -> cst-soon(即将完成; <=0 = 未知/缺失、8640000
     * 哨兵同 fmtEta 口径不产)。三个时间列(last_activity/seeding_time/time_active)刻意不做
     * (D10 原文: 方向语义弱, 防圣诞树)。 */
    numScaleRatio(v) {
      if (v === null || v === undefined || isNaN(v)) return "";
      return v < 1 ? "cst-warn" : "cst-good";
    },
    numScaleAvail(v) {
      if (v === null || v === undefined || isNaN(v) || v < 0) return "";
      return v < 1 ? "cst-warn" : "";
    },
    numScaleEta(sec) {
      if (!sec || sec <= 0 || sec >= 8640000) return "";  // 哨兵/非正口径与 fmtEta 逐字同
      return sec < 60 ? "cst-soon" : "";
    },
    /* 数值列消费面: cellNumScaleRatio 吃行模型 —— HR 伴值共存(D10 拍板): ratio 格已有
     * hrRatioClass 伴值类(hr.js 单点产, .m-pair pending/reached), 同格共存时 **HR 伴值优先**,
     * 有伴值即不产 cst-*(JS 侧让位, 不靠 CSS 特异度搏斗, 杜绝串色); 无伴值且格有值(cellRatio
     * 非空 = progress>0, 空白格不染)才走 numScaleRatio。组行无 HR 伴值字段 -> hrRatioClass 恒
     * 空串 -> 自然落数值判定(种子行+组行同口径; member 行 D5 排除不挂, 判定单点对任意行模型
     * 成立, 日后纳入只差模板一行)。cellNumScaleAvail 吃原始值 —— numeric 开 -> numScaleAvail
     * (D10 完整语义: 0.75~1.0 归 warn、>=1 不着色, numTone 的 0.75 档让位); 关(默认) -> 既有
     * numTone(v,1) **原样**(tone-* 链与现状逐值等价)。开关在类链源头互斥收口, 不靠 CSS 比
     * 特异度(会波及 tone-* 其它消费列, R6)。组行 availability 无既有着色, 直接挂 numScaleAvail
     * 纯判定(关 = 无映射规则 = 现状)。eta 格直接挂 numScaleEta(自身哨兵口径已兜空白)。 */
    cellNumScaleRatio(m) {
      if (this.hrRatioClass(m)) return "";
      if (!this.cellRatio(m)) return "";
      return this.numScaleRatio(m.ratio || 0);
    },
    cellNumScaleAvail(v) {
      return this.colStyle.numeric === "on" ? this.numScaleAvail(v) : this.numTone(v, 1);
    },
    /* 可用性(FX-26): 两个"没有有效值"的来源都不显示 ——
     * 1. 负数: qB 拿不到 distributed_copies 时给 -1(未连上 tracker / 无 peer 数据), 旧版直接
     *    toFixed 出 "-1.00" 看着像真数值; 2. 暂停中的种子: 没连接就谈不上分布式副本数(与
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
     * WARN: 统一走 fmtTs(而非 fmtTime): 它挡住了 -1 哨兵(直接 fmtTime(-1) 会渲染出 1970 年的日期)。 */
    cellTime(ts, key) {
      return this.timeFmt[key] === "rel" ? this.fmtRelTime(ts) : this.fmtTs(ts);
    },
    cellTimeHint(ts, key) {
      return this.timeFmt[key] === "rel" ? this.fmtTs(ts) : this.fmtRelTime(ts);
    },
    /* FX-28 跨标签同步(F2/F3, 与列偏好 adoptColState 同一套机制): 别的标签改了口径 -> storage
     * 事件触发本方法**整份采用**存储值; 标签被冻结 / storage 事件丢失 -> 回到可见时补对齐一次。
     * 整份采用而非逐列合并: 同一列的后写赢, 半合并反而会让两个标签各留一半旧值(列偏好踩过)。 */
    adoptTimeFmt() {
      this.timeFmt = loadTimeFmt();
    },
    /* 数值色阶(TBL-03): value/denom 比值分两档底色 —— ratio<0.75 -> tone-low(偏弱), >=0.75 -> tone-high(接近满档);
     * value<=0 或分母缺失/<=0 返回空串(交给 zero/空白机制)。全局限速分母来自 /api/stats 的 statsServer
     * (懒加载, 未开过统计面板时为 null -> 速度列自动无色阶, 属预期降级, 规则内自然兜住) */
    numTone(value, denom) {
      if (!value || value <= 0 || !denom || denom <= 0) return "";
      return value / denom < 0.75 ? "tone-low" : "tone-high";
    },
    /* KiB/s <-> bytes/s 换算单点(收敛 issue 26-10-20-2231 / 台账 R20-F-05): 后端限速口径是
     * KiB/s, qB 与显示口径是 bytes/s(后端半已登记 R06-A02)。全前端乘除 1024 只此两个函数;
     * 调用侧**禁止内联** `* 1024` / `/ 1024` —— 后端改限速单位口径时要能一处收口。 */
    kibToBytes(kib) {
      return kib * 1024;
    },
    bytesToKib(bytes) {
      return bytes / 1024;
    },
    /* 限速显示: 后端单位 KiB/s(0 = 不限速, null = 该方向不管理) */
    fmtLimit(kib) {
      if (kib === null || kib === undefined) return "—";
      if (!kib) return "";  // 0 = 不限速: 不再显示字样(TBL-02); 提示/toast 文案处调用方用 || "不限速" 兜回
      return this.fmtSpeed(this.kibToBytes(kib));
    },
  },
};
