/* auto-qb WEB UI · 种子详情抽屉(通用/Tracker/文件/Peer 与就地编辑)
 *
 * app.js 按域拆分出的片段(2026-09-20)。约定与 config_editor.js / config_rules.js 同一范式:
 * 挂到 window.AQB_DRAWER, 由 app.js 末尾 app.mixin(window.AQB_DRAWER) 注入同一个 Vue 实例 ——
 * 方法体里的 this 仍是那个组件实例, 跨模块互调与拆分前完全等价。
 *
 * !本文件在 HTML 里必须排在 app.js **之前**(app.js 末尾要读 window.AQB_DRAWER);
 *   用到的列模型常量(TABLE_COLUMNS / MIN_COL_PX / STATE_RANK …)仍单点定义在 app.js 顶部。
 *
 * W1(计划 26-10-11-2106): 取数 / 竞态 / 等待集合 / 软切换序号已剥到 shared/drawer_store.js
 *   (window.AQB_DRAWER_STORE)。本文件只留「面板开合 / 几何 / 拖高 / 持久化 / 跟随挂点 / 过渡钩子 /
 *   派生列表」; 四 fetcher 与软切换协议的调用点仍写 `this._fetchDrawerXxx`, 由 mixin 合并解析 ——
 *   调用形态与拆分前逐字等价。
 */
/* 跳检预检 gate id -> 分组行短标签(S4, 计划 26-10-05-0314): 取值与 ops_mod.GateVerdict 的
 * gate 对齐(G3-G8 / partial / dedup / filelist + gone); 漂移只影响分组行可读性, 不影响分流判定。 */
const SKIP_GATE_LABELS = {
  G3: "已完成", G4: "活跃中", G5: "校验在途", G6: "组内正在下载",
  G7: "组内校验在途", G8: "组内校验失败", partial: "部分下载", dedup: "今日已跳检",
  filelist: "丢失文件", gone: "已不在客户端",
};

/* ---------------- 页签合并(W4, 计划 26-10-11-2106: 合并状态收进面板核心单点) ----------------
 * W3 前这套判据住在模板选择层(AQB_DRAWER_TPL mixin, 插件/变体层) —— 但合并是
 * **抽屉级布局状态**, 不是插件层概念; W4 把它收进本文件(渲染核心)。
 * W6(同计划)起模板选择层(drawer_templates.js)整体退役并收进本文件: 密度档单点/
 * 读侧白名单迁移/右键菜单与显隐判据全在(见下方「模板选择层」段), 变体设施零残留 ——
 * 「抽屉只剩一套渲染技术」终态。
 * !单一状态源(计划 W4 目标「不再 computed 与模板两处读法」): 合并对 MERGE_PAIRS 是**列表**
 *   (有序), 渲染列组(dtPairCols)/合并页签清单(dtMergeTabList)/命中判据(_dtPairOf)共此一份
 *   —— tpl/drawer.html 不再硬编码 gc/tp 两个 <template> 分支与两张合并页签按钮(删「渲染列组
 *   vs 命中」双份判据, 计划 W4 改动面)。
 * !R2→R3 历史(判据语义, 不得回退): R2 曾按标志值渲染固定一对 + 挂载按当前对找宿主 = 空列 bug
 *   (用户报「选择并排后 tracker/用户标签显示常规/内容且为空」); R3 起列组/挂载/命中统一读
 *   「当前页签所属对」(dtPair)。宽度门 1920 是**暂态遮蔽**(dtSplitOn/dtMergeTabsOn 判 false,
 *   drawerMerge 标志不动) —— 缩窗过门回落单栏, 拉宽自动恢复; 门常量与两列封顶 2400(W6 起
 *   在三皮肤 views.css 的合并布局段)都是 W4 停手点, 口径不变。 */
const MERGE_STORE_KEY = "autoqb.ui.drawerMerge";
const DT_MERGE_MIN_WIDTH = 1920;
const MERGE_PAIRS = [
  { id: "gc", label: "常规&内容", tabs: ["general", "content"] },
  { id: "tp", label: "Tracker&用户", tabs: ["trackers", "peers"] },
];
/* 合并列的列头小节标题(单栏页签按钮的文案在 tpl/drawer.html 硬编码, 属其自身呈现, 不在此列) */
const DT_TAB_LABELS = { general: "常规", trackers: "Tracker", peers: "用户", content: "内容" };
/* 跨文件单点: 合并对的**结构**只在本文件定义一次, 任何消费方不得自建第二份映射
 * (双份判据即 R2 空列 bug 的根)。
 * !赋值形态与 AQB_DRAWER_TPL_REG 同(先建局部量再赋 window): 它是普通单点对象不是 mixin,
 * 不走 app.mixin 注入, 也就不用 `window.X = {` 字面量(mixin 接线守阵只钉「定义了必须注入」的
 * mixin 面, 见 _scan_mixin_wiring)。 */
const AQB_DRAWER_MERGE_SINGLE = {
  PAIRS: MERGE_PAIRS,
  MIN_WIDTH: DT_MERGE_MIN_WIDTH,
  pairOf(tab) {
    for (let i = 0; i < MERGE_PAIRS.length; i++) {
      if (MERGE_PAIRS[i].tabs.indexOf(tab) >= 0) return MERGE_PAIRS[i];
    }
    return null;
  },
};
window.AQB_DRAWER_MERGE = AQB_DRAWER_MERGE_SINGLE;

/* ---------------- 模板选择层落点(恢复注, 计划 26-10-11-2106 W7) ----------------
 * 右键菜单 computed 组 / 读侧 readSel / 显隐判据 dtHostOn / 挂载机械(_dtMount 系列/_dtSync/
 * _dtNotify/_dtRender/dtHtml/KIT/HELPERS)的原家是 drawer_templates.js(W4 期形态)。W5/W6 曾
 * 把选择层收进本文件并退役变体层(声明式密度档) —— W7 用户裁定该退役**越权**(计划目标只是
 * 「表格与主表能力统一」, 从未授权动模板), 变体层原样恢复, 选择层随之归位 drawer_templates.js
 * (装载序: 本文件 < drawer_templates.js < 变体自注册 < state.js, 见其头注); 本文件只保留
 * 合并(W4 收口)与形态判据(W3)。 */

window.AQB_DRAWER = {
  computed: {
    /* 抽屉可见性(2026-10-04 双形态; 2026-10-06 收页面守卫; 2026-10-08 三视图共用):
     * 两形态一律只在主内容页(page === "groups")渲染 —— 面板是 sticky 吸底的停靠面板, 在设置页
     * (整幅配置工作台, 自己的滚动容器铺满)会压住页面底部的内容块, 看着像设置页的一部分
     * (用户报「qB 全局流量图错误地出现在设置页」)。种子详情**三视图共用**(2026-10-08 计划
     * 26-10-08-1217): 种子页/辅种页/追剧页都是表行, 成员行 hash 三视图同源(selHashSet), 面板
     * 作为表行附属对三视图一视同仁; 不再限种子视图。
     * !状态位 drawer.open **不随切页翻**: 面板 DOM 退场但抽屉状态保持 —— 回主内容页面板连同
     *   数据/窗口选择原样回来(W1 验收项, 与原先「DOM 随种子视图 v-if 出入」同语义)。 */
    drawerVisible() {
      if (!this.drawer.open) return false;
      if (this.page !== "groups") return false;
      return true;  // 三视图共用(流量形态与种子详情都只限主内容页)
    },
    /* ---------------- 形态判据收口(W3, 计划 26-10-11-2106; W6 收全) ----------------
     * 面板两形态由一个字段裁决: kind === "seed"(种子详情, 五页签) / "traffic"(qB 口径流量图,
     * 三挂点)。此前的字面量比较散落在模板与四个片段里(drawer.html 三处 / 本文件二处 /
     * 模板选择层 / menu.js / shortcuts.js) —— 「同功能多形态各一份, 改一处漏一处」
     * (表 B 问题 4)正是从这种散点长出来的。现收成下面的派生单点。
     * !非根实例(全局 mixin 会注入 <transition> 的 BaseTransition 假实例)一律 false: 判据自带
     *   `this.drawer &&` 守卫, 调用方不必再抄一遍(旧写法每处都要写 `this.drawer &&` 或
     *   先判 `!this.drawer` 提前返回, 漏一处就是 BaseTransition 上求值抛错)。
     * W6: qb_traffic_chart.js 的 _QB_SCOPES.active/stale 与 qbCurScope 也已改吃本单点
     *   (W3 停手点「uPlot 与图表模块零改动」在 W6 兑现) —— 全仓 `drawer.kind` 字面量只余
     *   本文件两个定义处(守阵 test_frontend_drawer_form_judge_single_point 钉死)。 */
    drawerIsSeed() {
      return !!(this.drawer && this.drawer.kind === "seed");
    },
    drawerIsTraffic() {
      return !!(this.drawer && this.drawer.kind === "traffic");
    },
    /* 头部标题块的成员徽标口径(单点): 徽标色档(k-<kind>)/ 图标 / 悬浮状态语三处同源。此前那段
     * `(memberByHash.get(drawer.hash) || {}).kind || 'other'` 在头部模板里手抄三遍 —— 同一
     * 「改一处漏一处」的形态, 故一并收口(与上面两个形态判据同批, 都是「头部渲染的输入」)。
     * memberByHash 是根数据里的 Map(Vue 3 对集合做响应式代理), 缺失(换目标瞬间 / 成员不在当前
     * 视图)回落 { kind: "other" } —— 与旧模板逐字同义: 状态语走 stateText(它读 error_reason),
     * 故这里给的是**对象**而不是 kind 字符串, 不能退化成 stateText({ kind })。 */
    drawerMember() {
      const m = this.memberByHash && this.memberByHash.get(this.drawer && this.drawer.hash);
      return m || { kind: "other" };
    },
    drawerMemberKind() {
      return this.drawerMember.kind || "other";
    },
    /* ---------------- 页签合并(W4 收口, 计划 26-10-09-2219 R3 语义) ----------------
     * dtMergeOn/dtMergeTabsOn/dtPair/dtSplitOn 四个判据与 R3 逐字同义, 只换落点到面板核心;
     * dtMergeTabList/dtPairCols 是 W4 新增的**渲染单点** —— 合并页签按钮与双列列组改由
     * v-for 消费, 模板不再硬编码 gc/tp 分支(删「渲染列组 vs 命中」双份判据)。 */
    /* R3: 合并开关是否开启(off|on; 兼容 R2 旧值 gc/tp —— 初值读取已迁移, 这里再兜一道) */
    dtMergeOn() {
      return (this.drawerMerge || "off") !== "off";
    },
    /* R3: 页签栏是否呈现合并页签 —— 开关开 + 门内。页签栏只在种子详情头部渲染(流量形态另有
     * 头部), 故无需再排除流量形态。门外回落四页签(暂态遮蔽, 标志不动)。 */
    dtMergeTabsOn() {
      return this.dtMergeOn && this.dtMergeGateOk();
    },
    /* R3: 当前页签所属的合并对("gc"|"tp"|null) —— 合并双列「渲染哪两列」的单点判据,
     * 与数据供给(drawer_store.js)同源; 流量与对外页签返回 null。 */
    dtPair() {
      return this._dtPairOf(this.drawer && this.drawer.tab);
    },
    /* R2 S2(计划 26-10-09-2219)·R3 修正: 合并布局生效判据(模板 v-if 单点) —— 开关开启 +
     * 种子详情形态 + 当前页签属于某一对 + 门内。门是暂态遮蔽: dtWinW(state.js 显式建字段)由
     * 核心 resize 监听防抖回写, 标志本身不动; 关面板/流量形态自然 false。 */
    dtSplitOn() {
      if (!this.dtMergeOn) return false;
      if (this.qbTrafficActive) return false;
      if (!this.dtPair) return false;
      return this.dtMergeGateOk();
    },
    /* W4: 合并页签清单(页签栏单点) —— 注册表是 boot 期静态数据, 依赖 dtMergeTabsOn
     * 翻转即可; 高亮判据在模板内联 mt.id === dtPair(与列组同源, 无独立高亮态)。
     * 26-10-20-2231: 形状改为 <aq-seg> 契约 [{v, label}](只做投影, 结构事实仍是 MERGE_PAIRS
     * 一份; pairOf/dtPairCols 读的也还是它) —— 页签钮从此不在模板里手写。 */
    dtMergeTabList() {
      return window.AQB_DRAWER_MERGE.PAIRS.map((p) => ({ v: p.id, label: p.label }));
    },
    /* 非合并态的四页签清单(同 <aq-seg> 契约): 文案单点是 DT_TAB_LABELS(合并列的列头也读它),
     * 顺序取该表的插入序(general/trackers/peers/content) —— 模板此前四个 <button> 逐字写死,
     * 与 DT_TAB_LABELS 是同一批文案的两份拷贝。 */
    dtTabItems() {
      return Object.keys(DT_TAB_LABELS).map((t) => ({ v: t, label: DT_TAB_LABELS[t] }));
    },
    /* W4: 当前生效对的列定义(正文双列 v-for 单点)。general 列经 props 传详情(组件 prop 面
     * 与单栏一致), 其余列组件无 props(v-bind 空对象 = 无操作); label 即 .dt-col-head 文案。 */
    dtPairCols() {
      const p = window.AQB_DRAWER_MERGE.pairOf(this.drawer && this.drawer.tab);
      if (!p) return [];
      return p.tabs.map((tab) => ({
        tab,
        label: DT_TAB_LABELS[tab] || tab,
        props: tab === "general" ? { d: this.drawer.detail } : {},
      }));
    },
  },
  /* W4 收口的两条监听(语义逐字未改): ① resize 防抖回写 dtWinW +
   * 门跨越后重挂/补给; ② drawerMerge 换代(右键开关)后重挂 + 第二列数据补给。
   * !全局 mixin 会波及子组件与 <transition> 的 BaseTransition 假实例(其上无数据面), 必须
   * `if (!this.drawer) return;` 守卫 —— 与模板选择层的 traffic 通知同规避式(后者在
   * drawer_templates.js 的 mixin 里, 同为全局注入, 互不重复注册)。 */
  mounted() {
    if (!this.drawer) return;
    this._mergeOnResize = () => {
      clearTimeout(this._mergeResizeT);
      this._mergeResizeT = setTimeout(() => {
        this._mergeResizeT = null;
        /* 2026-10-14: 与 dtToggleMerge 同口径 —— 门跨越前先熄桥(单独一帧卸桥), 否则
         * dtSplitOn 同帧翻转时拆桥会撞上 Teleport 目标被移除, Vue 运行期崩溃。 */
        if (this.dtSplitOn) this._dtBridgesOff();
        this.dtWinW = window.innerWidth;
        this.$nextTick(() => {
          this._dtSync();  /* v-if 换代后旧宿主 isConnected 已假, 卸旧重挂(W7 恢复) */
          /* 门跨越恢复双列时第二列数据可能从未拉过(影子期零请求语义), 补给一次 */
          if (this.dtSplitOn && typeof this._drawerMergeSupply === "function") this._drawerMergeSupply();
        });
      }, 150);
    };
    window.addEventListener("resize", this._mergeOnResize);
    this._unwatchMerge = this.$watch("drawerMerge", () => {
      this.$nextTick(() => {
        this._dtSync();  /* 布局换代重挂(W7 恢复插件面) + 第二列数据补给 */
        if (this.dtSplitOn && typeof this._drawerMergeSupply === "function") this._drawerMergeSupply();
      });
    });
  },
  beforeUnmount() {
    if (this._unwatchMerge) {
      this._unwatchMerge();
      this._unwatchMerge = null;
    }
    if (this._mergeOnResize) {
      window.removeEventListener("resize", this._mergeOnResize);
      this._mergeOnResize = null;
    }
    if (this._mergeResizeT) {
      clearTimeout(this._mergeResizeT);
      this._mergeResizeT = null;
    }
  },
  methods: {
    /* ---------------- 页签合并(W4 收口) ----------------
     * 方法体与 R3 逐字同义, 只换落点; W5 起无插件挂载机械, 布局换代全靠 v-if 响应式。 */
    /* R2 S2·R3: 当前页签所属合并对("gc"|"tp"|null) —— 合并页签高亮(模板 mt.id === dtPair)、
     * 双列列组(dtPair)与数据供给(drawer_store.js)的单点判据;
     * 流量与对外页签返回 null。 */
    _dtPairOf(tab) {
      if (this.qbTrafficActive) return null;
      const p = window.AQB_DRAWER_MERGE.pairOf(tab);
      return p ? p.id : null;
    },
    /* R2 S3·R3: 合并开关宽度门(右键菜单置灰与挂载守卫共用同一判据, 常量单点 MIN_WIDTH) */
    dtMergeGateOk() {
      return (this.dtWinW || window.innerWidth || 0) >= window.AQB_DRAWER_MERGE.MIN_WIDTH;
    },
    /* R3: 右键菜单单开关落点 —— 门内才生效, 再点即关 + 落盘。
     * 布局换代靠 v-if 响应式自翻(W5 起无插件重挂); 第二列数据补给(_drawerMergeSupply,
     * 本体在 drawer_store.js)由 drawerMerge 的 $watch 单发统一触发(本文件 mounted 注册)。 */
    dtToggleMerge() {
      if (!this.dtMergeGateOk()) return; /* 置灰项双保险: class 拦显示, 这里拦行为 */
      const v = this.dtMergeOn ? "off" : "on";
      /* 2026-10-14: 先把所有变体表格体桥熄灯, **下一拍**再翻合并标志 ——
       * 桥的 v-if 与所属 DOM 分支(v-if="dtSplitOn")同帧翻转时, Vue 拆桥会撞上“Teleport
       * 目标正被同帧移除”, 报 `Cannot destructure property 'bum' of 'e' as it is null`
       * (运行期崩溃, 合并开关/视口门跨越必现 —— 经典渲染链移除后四内容页签默认带桥才暴露)。
       * 分两帧: 第一帧只卸桥(锚还在文档里), 第二帧才拆分支, 无桥可拆即无崩溃。 */
      this._dtBridgesOff();
      this.$nextTick(() => { this.drawerMerge = v; });
      try { localStorage.setItem(MERGE_STORE_KEY, JSON.stringify(v)); } catch (e) { /* 写失败本轮仍生效 */ }
      if (this.drawerMenu) this.drawerMenu.visible = false;
    },
    /* R3: 合并页签点击落点 —— 切到该对(已在其中则零副作用, 避免无谓重拉); 目标页签取对的首列
     * (列序按对固定; 双列两列都会被挂载, 对内的具体取值不影响呈现, 只决定"主列=当前页签"的
     * 挂载归属与头部模板切换器指向)。 */
    dtMergeTabPick(pairId) {
      const p = window.AQB_DRAWER_MERGE.PAIRS.find((x) => x.id === pairId);
      if (!p) return;
      if (p.tabs.indexOf(this.drawer && this.drawer.tab) >= 0) return;
      if (typeof this.drawerTab === "function") this.drawerTab(p.tabs[0]);
    },
    /* ---------------- 模板选择层(W7 归位 drawer_templates.js, 见其 mixin) ----------------
     * _dtCurTab/dtHostOn/dtMenuPick/dtPersistSel 已随选择层回原家; 本文件零残留(双份定义会被
     * mixin 静默覆盖, 守阵 _scan_mixin_wiring/成员重名钉会红)。 */
    /* 自动种子管理开关(种子页右键 R2 补遗): 复用 torrentCmd 回执链 */
    autoTmmToggle() {
      const m = this.menuTorrent();
      this.torrentCmd("auto-tmm", { enable: !m.auto_tmm }, m.auto_tmm ? "关闭自动种子管理" : "开启自动种子管理");
    },
    /* 右键菜单当前种子(SEED_ITEM 完整字段): 供菜单项动态文案/开关初值 */
    menuTorrent() {
      return this.memberByHash.get(this.menu.hash) || {};
    },
    /* 种子控制命令(R2): 带 body 的单种命令(校验/超级做种/强制启动/队列) —— 走既有回执链。
     * !目标解析(S3/M3, 2026-10-10): `hash` 显式传入, 缺省回落 `menu.hash`(右键菜单路径本就以被点
     *   行为目标)。此前抽屉路径靠**写 this.menu.hash** 把抽屉目标"塞"进来 —— menu 状态被当成了
     *   全局目标变量(机制 3, 见 conventions/webui-scope.md §3)。 */
    async torrentCmd(action, body = null, okText = "", hash = "") {
      this.menu.visible = false;
      const target = hash || this.menu.hash;
      if (!target) return;
      /* 强制重新汇报闸门(qB 口径): 非活跃种子(暂停/停止·排队·校验·错误)拒绝 —— 详情面板 tracker
       * 页签的重报钮已置灰(右键菜单项走 drawerReannounceGate; 旧变体 04/05/06 同款, W5 退役),
       * 这里是行为层兜底(与 ctx-menu 的"class 拦显示、行为层再拦一道"同款)。本方法两条入口共用:
       * 单选右键菜单的控制命令, 与详情面板 drawerCmd(目标 = 抽屉 hash)。 */
      if (action === "reannounce" && !this._guardReannounce({ keys: [], hashes: [target] })) return;
      /* 重新校验先确认(计划 26-10-05-0314 S3): 只拦 recheck, 其它命令通道行为不变 ——
       * 单选右键(ctx-menus.html)与抽屉内命令(drawerCmd)同走本方法, 一处接入两入口覆盖;
       * 取消 = 直接返回, 尚未发请求, 零副作用。helper 与文案单点在 commands.js。 */
      if (action === "recheck") {
        const ok = await this._recheckConfirm("该种子");
        if (!ok) return;
      }
      try {
        const resp = await this.api(`/api/torrents/${target}/${action}`, {
          method: "POST",
          body: body ? JSON.stringify(body) : undefined,
        });
        const r = await this.waitCmd(resp.cmd_id);
        if (r.ok) this.toast(`已执行: ${okText || action}`, "ok", 2500);
        else this.toast(`${okText || action}失败: ${r.error}`, "error", 8000);
      } catch (e) {
        if (!e.auth) this.toast("命令发送失败: " + e.message, "error");
      }
    },
    /* 抽屉内命令: 与 torrentCmd 同链路, 目标 = 抽屉当前 hash(显式传参, 不动 menu 状态) */
    drawerCmd(action, body = null, okText = "") {
      this.torrentCmd(action, body, okText, this.drawer.hash);
    },
    /* ---------------- 右键跳检(P2', plan 26-09-30-0109 §3.6; S4 预检对话框 26-10-05-0314) ----------------
     * 高风险操作: 删除并以跳过校验方式重加, 本地统计(上传/下载量、做种时间)被清零,
     * 数据未经哈希校验。S4 起确认框升级为预检对话框(_skipCheckDialog, 单发/批量两入口共用):
     * 进框即禁用确认, 预检(ops 同谓词 dry-run)回执后按三分流渲染原因与逃生通道;
     * 固定警示区(统计清零/未哈希校验/无参考高风险/HR 在管)始终显示。执行走 ops 层四阶段,
     * 阻塞主循环 ~6s, 期间其它命令排队 —— waitCmd 放宽到 60s(与批量同口径)。 */
    async skipCheckTorrent() {
      this.menu.visible = false;
      const hash = this.menu.hash;
      if (!hash) return;
      await this._skipCheckDialog([hash], { mode: "single", hash, groupKeys: [], memberHashes: [hash] });
    },
    /* 跳检预检对话框状态机(S4, 计划 26-10-05-0314 §04; 单发/批量两入口共用):
     * 进框(确认禁用 + busy + 固定警示区) -> 发预检(POST /api/torrents/skip-check/precheck,
     * 后端 ops 同谓词 dry-run) -> 回执后按三分流切换:
     *   全 ok        -> 启用确认「跳检 N 个」(送全量, 不带 force);
     *   ok+force 混合 -> 确认「跳检 N 个可跳检的」(只送 ok 子集, 不带 force) + 强制钮
     *                    (复用 extraText 第三钮, 模板本就是 danger-solid 破坏性分支)
     *                    「强制跳检全部 N」(送全量 + force=true);
     *   force-only    -> 确认保持禁用, 只有强制钮;
     *   含 blocked    -> 无可执行钮(blocked 硬闸, force 只豁瞬态闸门救不回), 按原因分组列出;
     *   预检失败      -> D10 降级: 启用普通确认(= 旧 danger 确认框行为: 确认后执行, 后端闸门
     *                    执行时照拦), 永不出强制钮 —— force 必须先见赌注才出现(plan §07)。
     * 执行路径闸门原样全跑, 预检与执行之间没有信任传递(plan §03 callout)。
     * exec: {mode:"single", hash} | {mode:"bulk", groupKeys, memberHashes} —— 提交端点与 toast
     * 形态两入口各异, 由 _skipExec 按 mode 分派; 本方法只管对话框与预检状态机。 */
    async _skipCheckDialog(hashes, exec) {
      const n = hashes.length;
      // 代际: 单例 modal 下再开新框会把旧 Promise 结算为取消 —— 旧框在途的预检回执
      // 不得污染新框, 落袋前一律按 seq 复核
      const seq = (this._skipCheckSeq = (this._skipCheckSeq || 0) + 1);
      // 固定警示区(plan §03 callout: case 3 不代表没有代价): 统计清零 / 未哈希校验 /
      // 无参考高风险 / HR 在管(D5) —— 进框即显示, 与分流结果并列不互斥
      // (旧 danger 确认框文案区里的警示迁入于此)
      // tone: "warn"(计划 26-10-19-2341): 这 4 行写的是 #i-warn(警告图标), 但此前被通用的
      // .modal-detail-row .ico{color:var(--fg-dim)} 一律压成灰 —— 「case 3 不代表没有代价」
      // 这句 design intent 在视觉上一直是缺席的, 行级标 tone 才把它找回
      const warnRows = [
        { icon: "#i-warn", tone: "warn", label: "统计清零", value: "本地统计(上传/下载量、做种时间)将被清空", wide: true },
        { icon: "#i-warn", tone: "warn", label: "未哈希校验", value: "数据未经哈希校验", wide: true },
        { icon: "#i-warn", tone: "warn", label: "无参考", value: "无参考对照的跳检属高风险操作", wide: true },
        { icon: "#i-warn", tone: "warn", label: "HR 在管", value: "未放行的 HR 种子: 做种时间锚点会倒退、超额线(3×)推迟", wide: true },
      ];
      const p = this._openModal({
        title: n > 1 ? "批量跳检(跳过校验重加)" : "跳检(跳过校验重加)",
        body: n > 1 ? `将删除选中的 ${n} 个种子并以跳过校验方式重加。` : "将删除该种子并以跳过校验方式重加。",
        okText: `跳检 ${n} 个`,
        cancelText: "取消",
        danger: true,
        icon: "#i-bolt",
        wide: true,          // 原因/名称行宽松可读(与删除确认框同形态)
        // 语义配色分级(计划 26-10-19-2341): 跳检有代价但可重来 → warn 档(与不可逆的删除拉开
        // 一档); 整框 tone 不随预检结果升级 —— 升级由 verdict 行级 is-error 表达。这样取舍
        // 一半是被 T24 逼的: _skipPrecheck 六分支被逐语句等值断言钉死, 加一行就红, 故派生
        // 只能落在构造参数里
        tone: "warn",
        strip: true,
        okDisabled: true,    // 进框即禁用: 预检回执前无任何可执行钮(强制必须先看到赌注)
        busy: true,
        verdict: warnRows,
      });
      this._skipPrecheck(seq, this.modal.mid, hashes, warnRows);  // 不 await: 对话框已开, 回执异步落框; mid = 本框身份戳
      const choice = await p;
      if (!choice) return;  // 取消/Esc/遮罩: 零副作用(此时未发任何执行请求)
      // 走到这说明点的是确认/强制钮 —— _skipVerdict 只在 seq 复核通过后写入, 故取值必属
      // 当前这框(新框会先把旧 Promise 结算成取消); 兜底按降级(全量不带 force)处理
      const v = this._skipVerdict || { degraded: true, okHashes: hashes };
      if (choice === "extra") return this._skipExec(exec, hashes, true);  // 强制: 全量 + force=true
      // 确认: 降级 = 全量不带 force(= 旧确认框行为); 正常 = ok 子集(全 ok 时即全量)
      return this._skipExec(exec, v.degraded ? hashes : v.okHashes, false);
    },
    /* 预检投递与落框(不 await 调用): 回执后把三分流结果接在固定警示区之后, 并按态切换
     * 确认/强制钮。非 ok 回执与请求异常一律走 D10 降级; 403(web.skip_check_menu 关)同形 ——
     * 文案自解释, 执行端点同样有 403 兜底(fail-closed, 前端降级不构成绕过)。 */
    async _skipPrecheck(seq, mid, hashes, warnRows) {
      let rows = [], okHashes = [], counts = null, degraded = false;
      try {
        const resp = await this.api("/api/torrents/skip-check/precheck", {
          method: "POST",
          body: JSON.stringify({ hashes }),
        });
        const r = await this.waitCmd(resp.cmd_id, 60000);
        if (r.ok && r.truth && Array.isArray(r.truth.results)) {
          const results = r.truth.results;
          counts = {
            ok: results.filter((x) => x.cls === "ok").length,
            force: results.filter((x) => x.cls === "force").length,
            blocked: results.filter((x) => x.cls === "blocked").length,
          };
          okHashes = results.filter((x) => x.cls === "ok").map((x) => x.hash);
          rows = this._skipVerdictRows(results);
        } else {
          degraded = true;
          rows = [{ icon: "#i-warn", tone: "warn", label: "预检失败", value: `${r.ok ? "回执缺少预检数据" : r.error}, 后端闸门仍会在执行时拦截`, wide: true }];
        }
      } catch (e) {
        if (e.auth) return;  // 401 已由 _logout 收口(modal 一并清空), 无需也不得再动
        degraded = true;
        rows = [{ icon: "#i-warn", tone: "warn", label: "预检失败", value: `${e.message}, 后端闸门仍会在执行时拦截`, wide: true }];
      }
      // 迟到回执 / 框已关 / 已被新框取代: 不落袋(防旧结果驱动新框的按钮)。seq 复核跳检
      // 代际, 身份戳复核弹窗本身(F1-01 守卫单点 ui_feedback._modalIsCurrent) —— 取消跳检框
      // 后 seq 不递增, 用户再开限速/重命名等无关 modal(共用单例)时只有身份戳拦得住
      if (seq !== this._skipCheckSeq || !this._modalIsCurrent(mid)) return;
      this.modal.busy = false;
      this.modal.verdict = [...warnRows, ...rows];
      this._skipVerdict = { degraded, okHashes };
      if (degraded) {
        // D10 降级: 启用普通确认(确认后执行, 后端闸门照拦); 强制钮永不出现
        this.modal.okDisabled = false;
        this.modal.extraText = "";
      } else if (counts.blocked) {
        // 含 blocked: 一律不可执行 —— 确认/强制双钮全收, 用户须先解决原因
        this.modal.okDisabled = true;
        this.modal.extraText = "";
      } else if (counts.ok && counts.force) {
        // ok+force 混合: 确认只送 ok 子集(不带 force); 强制钮送全量 + force=true
        this.modal.okDisabled = false;
        this.modal.okText = `跳检 ${counts.ok} 个可跳检的`;
        this.modal.extraText = `强制跳检全部 ${counts.ok + counts.force}`;
      } else if (counts.force) {
        // force-only: 确认保持禁用, 只有强制钮
        this.modal.okDisabled = true;
        this.modal.extraText = `强制跳检全部 ${counts.ok + counts.force}`;
      } else {
        // 全 ok: 启用确认(送全量, 不带 force), 无强制钮
        this.modal.okDisabled = false;
        this.modal.okText = `跳检 ${counts.ok} 个`;
        this.modal.extraText = "";
      }
    },
    /* 预检回执 -> verdict 行式明细(不含固定警示区): 批量 = 计数行 + 按原因分组行
     * (同 (cls, gate) 聚合, 「禁止 · 已完成 ×3: 名A, 名B, …」单行省略, 组内名称上限
     * 5 个 + 「等 X 个」); 单发 = 全量原因行(原因+后果+出路三段式原文, 无未过闸门时
     * 给一条「前置条件全部满足」正行)。gate 短标签表见文件头 SKIP_GATE_LABELS。 */
    _skipVerdictRows(results) {
      const rows = [];
      const ok = results.filter((x) => x.cls === "ok");
      const force = results.filter((x) => x.cls === "force");
      const blocked = results.filter((x) => x.cls === "blocked");
      if (results.length > 1) {
        rows.push({
          icon: "#i-select-all",
          // 计数行按最坏结果取档: 有禁止→error, 有需强制→warn, 全 ok→ok(计划 26-10-19-2341)
          tone: blocked.length ? "error" : force.length ? "warn" : "ok",
          label: "预检",
          value: `可跳检 ${ok.length} / 需强制 ${force.length} / 禁止 ${blocked.length}`,
        });
        const groups = new Map();
        for (const r of results) {
          for (const x of r.reasons || []) {
            const key = `${x.cls}|${x.gate}`;
            if (!groups.has(key)) groups.set(key, { cls: x.cls, gate: x.gate, names: [] });
            groups.get(key).names.push(r.name || r.hash.slice(0, 12));
          }
        }
        for (const g of groups.values()) {
          const shown = g.names.slice(0, 5);  // 组内名称展示上限 5 个
          rows.push({
            icon: g.cls === "blocked" ? "#i-x-circle" : "#i-hourglass",
            // 「禁止」此前与「需强制」共用同一个灰 —— 硬闸语义没在视觉上表达出来
            tone: g.cls === "blocked" ? "error" : "warn",
            label: `${g.cls === "blocked" ? "禁止" : "需强制"} · ${SKIP_GATE_LABELS[g.gate] || g.gate} ×${g.names.length}`,
            value: shown.join(", ") + (g.names.length > shown.length ? ` 等 ${g.names.length} 个` : ""),
            wide: true,
          });
        }
      } else {
        const reasons = (results[0] && results[0].reasons) || [];
        if (!reasons.length) {
          rows.push({ icon: "#i-check-circle", tone: "ok", label: "预检", value: "前置条件全部满足, 可跳检" });
        } else {
          for (const x of reasons) {
            rows.push({
              icon: x.cls === "blocked" ? "#i-x-circle" : "#i-hourglass",
              tone: x.cls === "blocked" ? "error" : "warn",
              label: x.cls === "blocked" ? "禁止" : "需强制",
              value: x.text,
              wide: true,
            });
          }
        }
      }
      return rows;
    },
    /* 跳检执行分派(确认/强制钮共落点): 单发 POST /api/torrents/{hash}/skip-check(body 仅在
     * force 时携带 force 键, 缺省载荷与历史一致); 批量 POST /api/torrents/bulk
     * (action=skip_check, ok 子集只走 hashes 通道, 强制按 keys+hashes 整份 + force=true)。
     * 执行路径后端重跑全部闸门 —— blocked 照旧硬拒, force 只豁瞬态; 拒绝文案经
     * error 回执 toast 展示。单枚跳检阻塞主循环 ~6s 级, waitCmd 放宽到 60s + SSE cmd
     * 事件赛跑兜底(waitCmd 实现), 回执未到前批量常驻 toast 停留「进行中」。 */
    async _skipExec(exec, hashes, force) {
      try {
        if (exec.mode === "single") {
          const hash = exec.hash;
          const m = this.memberByHash.get(hash) || {};
          const resp = await this.api(`/api/torrents/${hash}/skip-check`, {
            method: "POST",
            body: force ? JSON.stringify({ force: true }) : undefined,
          });
          const r = await this.waitCmd(resp.cmd_id, 60000);
          if (r.ok) this.toast(`已跳检: ${m.name || hash.slice(0, 12)}`, "ok", 3000);
          else this.toast(`跳检未执行: ${r.error}`, "error", 8000);
          return;
        }
        const n = force ? exec.groupKeys.length + exec.memberHashes.length : hashes.length;
        const resp = await this.api("/api/torrents/bulk", {
          method: "POST",
          body: JSON.stringify({
            action: "skip_check",
            keys: force ? exec.groupKeys : [],
            hashes: force ? exec.memberHashes : hashes,
            ...(force ? { force: true } : {}),
          }),
        });
        const tid = this.toast(`批量跳检进行中…(${n} 个目标, 每个约需数秒)`, "busy", 0, { sticky: true });
        const r = await this.waitCmd(resp.cmd_id, 60000);
        if (r.ok) this._finishToast(tid, "ok", `已执行: 批量跳检(${n} 个目标)`, 3000);
        else this._finishToast(tid, "error", `批量跳检未完成: ${r.error}`, 8000);
      } catch (e) {
        if (!e.auth) {
          this.toast((exec.mode === "single" ? "命令发送失败: " : "批量跳检命令发送失败: ") + e.message, "error");
        }
      }
    },
    /* ---------------- 种子编辑对话框(D 轮): 限速/分享率限制/移动/重命名 ----------------
     * 统一形态: 多字段 .modal(modal.fields) + 回执 toast; 预填当前值, 空输入 = 不修改。
     * hash 约定: 菜单调用不传参取 menu.hash, 抽屉调用显式传 drawer.hash(与 drawerCmd 同约定)。 */
    _editTargetHash(h) {
      const hash = h || this.menu.hash;
      this.menu.visible = false;
      return hash || "";
    },
    /* 编辑类对话框取当前值: 抽屉已开且同一 hash 直接用 drawer.detail(免一次请求) */
    async _editDetail(hash) {
      if (this.drawer.open && this.drawer.hash === hash && this.drawer.detail) {
        return this.drawer.detail;
      }
      try {
        const r = await this.api(`/api/torrents/${hash}`);
        return (r && r.torrent) || null;
      } catch (e) {
        if (!e.auth) this.toast("当前值获取失败: " + e.message, "error");
        return null;
      }
    },
    /* 编辑类命令统一投递: api + waitCmd 回执 + toast 三态; 成功后按动作刷新抽屉对应页签数据 */
    async _editPost(hash, action, body, okText) {
      try {
        const resp = await this.api(`/api/torrents/${hash}/${action}`, {
          method: "POST",
          body: JSON.stringify(body),
        });
        const r = await this.waitCmd(resp.cmd_id);
        if (r.ok) {
          this.toast(`已执行: ${okText}`, "ok", 2500);
          if (this.drawer.open && this.drawer.hash === hash) {
            this._fetchDrawerDetail();
            if (action.startsWith("trackers/")) this._fetchDrawerTrackers(true);
            else if (action === "files/priority" || action === "rename-fs") this._fetchDrawerFiles(true);
          }
          return true;
        }
        this.toast(`${okText}失败: ${r.error}`, "error", 8000);
      } catch (e) {
        if (!e.auth) this.toast(`${okText}命令发送失败: ` + e.message, "error");
      }
      return false;
    },
    /* 速度限制…: 上传/下载两输入(KiB/s; 空=不改, 0=不限) → POST limits(×1024 转 bytes, 0 原样传) */
    async editLimits(h = "") {
      const hash = this._editTargetHash(h);
      if (!hash) return;
      const d = await this._editDetail(hash);
      const kiB = (bytes) => (bytes > 0 ? String(Math.round(this.bytesToKib(bytes))) : "");  // 不限/未设(≤0)留空
      const res = await this._openModal({
        title: "速度限制",
        body: "设置该种子的上传/下载速度上限(KiB/s)。留空 = 保持不变, 填 0 = 不限速。",
        fields: [
          { key: "up", label: "上传限制(KiB/s)", value: d ? kiB(d.up_limit) : "", placeholder: "留空不修改, 0 = 不限" },
          { key: "dl", label: "下载限制(KiB/s)", value: d ? kiB(d.dl_limit) : "", placeholder: "留空不修改, 0 = 不限" },
        ],
        okText: "应用", cancelText: "取消",
      });
      if (!res) return;
      const body = {};
      for (const [k, key] of [["up", "up_limit"], ["dl", "dl_limit"]]) {
        if (res[k] === "") continue;  // 空 = 不修改
        const n = Number(res[k]);
        if (!Number.isFinite(n) || n < 0) {
          this.toast("限速需为非负数字(KiB/s)", "warn");
          return;
        }
        body[key] = Math.round(this.kibToBytes(n));  // KiB/s → bytes/s; 0 原样传(后端语义 = 不限)
      }
      if (!Object.keys(body).length) {
        this.toast("未作修改", "ok", 2000);
        return;
      }
      await this._editPost(hash, "limits", body, "限速已更新");
    },
    /* 分享率限制…: 分享率/做种时间(h)/不活跃做种时间(h) → POST share-limits(-1 = 恢复全局默认) */
    async editShareLimits(h = "") {
      const hash = this._editTargetHash(h);
      if (!hash) return;
      const d = await this._editDetail(hash);
      const hrs = (sec) => (sec > 0 ? String(Math.round((sec / 3600) * 100) / 100) : "");  // -1/0(未设)留空
      const res = await this._openModal({
        title: "分享率限制",
        body: "达到任一限制后该种子将停止做种。留空 = 保持不变, 填 -1 = 恢复全局默认。",
        fields: [
          { key: "ratio", label: "分享率上限", value: d && d.max_ratio >= 0 ? String(d.max_ratio) : "", placeholder: "留空不修改, -1 = 全局" },
          { key: "time", label: "做种时间上限(小时)", value: d ? hrs(d.max_seeding_time) : "", placeholder: "留空不修改, -1 = 全局" },
          { key: "inactive", label: "不活跃做种上限(小时)", value: d ? hrs(d.max_inactive_seeding_time) : "", placeholder: "留空不修改, -1 = 全局" },
        ],
        okText: "应用", cancelText: "取消",
      });
      if (!res) return;
      const body = {};
      if (res.ratio !== "") {
        const n = Number(res.ratio);
        if (!Number.isFinite(n) || (n < 0 && n !== -1)) {
          this.toast("分享率需为非负数字(或 -1)", "warn");
          return;
        }
        body.ratio_limit = n;
      }
      for (const [k, key] of [["time", "seeding_time_limit"], ["inactive", "inactive_seeding_time_limit"]]) {
        if (res[k] === "") continue;  // 空 = 不修改
        const n = Number(res[k]);
        if (!Number.isFinite(n) || (n < 0 && n !== -1)) {
          this.toast("时长需为非负小时数(或 -1)", "warn");
          return;
        }
        body[key] = n === -1 ? -1 : Math.round(n * 3600);  // 小时 → 秒; -1 原样(未设/全局)
      }
      if (!Object.keys(body).length) {
        this.toast("未作修改", "ok", 2000);
        return;
      }
      await this._editPost(hash, "share-limits", body, "分享率限制已更新");
    },
    /* 设定位置…(2026-10-13): 单种子/单组/多选批量三入口统一改, 保存路径下拉候选按「最近使用」
     * 排序(与添加种子保存路径同口径, 复用 add_torrent.js 的 _addRecencyMaps/_addOrderByRecent/_addNormPath
     * 单点 —— 全局 mixin 合并, 跨模块互调与拆分前逐字等价)。下拉候选 = /api/paths 已知保存路径;
     * 单种子预填当前 save_path, 批量/单组无预填(各值不同, 预填误导)。目标集合打开时刻锁定(与 meta 同口径)。
     * combobox 收层/限高/悬停与添加种子三下拉 + meta 分类同套口径(见 pitfalls/web-ui/combobox-focusout-close)。
     * 三入口名/签名(editMove/editMoveMulti/editMoveGroup)与下游投递(editMove→_editPost,
     * editMoveMulti/editMoveGroup→_bulkEditPost)不变 —— 守阵 + 触发登记表钉这些。 */
    async editMove(h = "") {
      const hash = this._editTargetHash(h);
      if (!hash) return;
      const d = await this._editDetail(hash);
      return this.openMoveDialog({ groupKeys: [], memberHashes: [hash] }, "", hash, d ? d.save_path || "" : "");
    },
    /* ---------------- 设定位置对话框状态机(单种子/单组/多选批量共用) ---------------- */
    openMoveDialog(targets, scope, singleHash, prefill) {
      this.moveTargets = targets;
      this.moveOpen = true;
      this.moveSingleHash = singleHash;
      this.moveScope = scope;
      this.moveCount = targets.groupKeys.length + targets.memberHashes.length;
      this.movePathMenu = false;
      this.movePathHi = -1;
      this.movePathMouseAt = null;
      this.moveBusy = false;
      this.movePathInput = prefill || "";
      this.loadMoveOptions();
      // 开对话框即聚焦输入框(与 _openModal 原行为): 键盘路径 Enter 即确认, 鼠标路径下拉候选展开
      this.$nextTick(() => {
        const el = this.$refs.movePathInputEl;
        if (el) el.focus();
      });
    },
    closeMove() {
      if (this.moveBusy) return;  // 命令回执等待期不允许误关(与 meta 同口径)
      this.moveOpen = false;
    },
    async loadMoveOptions() {
      // 路径候选拉(与添加种子保存路径同端点); 单端点失败静默降级为空(不阻塞对话框, 照 loadAddOptions 先例)
      let paths = [];
      try {
        paths = (await this.api("/api/paths")).paths || [];
      } catch (e) {
        paths = [];
      }
      if (this.moveOpen) {  // 仅对话框仍开着时回填(慢响应不得污染下一次打开)
        // 「最近使用」排序单点复用(与添加种子保存路径同口径): 跨视图取数 _addRecencyMaps 现算
        const recent = this._addRecencyMaps();
        this.movePathOptions = _addOrderByRecent(paths, recent.path);
      }
    },
    openMovePathMenu() {
      this._popBlurCancel("_movePopBlurT");  // 焦点回到本输入框时撤销挂起的失焦收层, 菜单不闪
      this.movePathMouseAt = null;  // 开层复位悬停门限坐标(同 addCatMouseAt)
      this.movePathHi = this.movePathOptions.indexOf(this.movePathInput.trim());
      this.movePathMenu = true;
      this._hiScroll("movePathList");
    },
    moveApplyPath(p) {
      // 候选点击即回填 + 提交(对话框提交直接, 与添加种子回填态不同: 这里无后续"添加"步)
      this.movePathInput = p;
      this.movePathMenu = false;
      this.movePathHi = -1;
      this.submitMoveDialog();
    },
    onMovePathKeydown(e) {
      // 与 meta 分类下拉同套单点(comboKeydown, add_torrent.js): 上下循环高亮(开层即展开),
      // 回车即回填+提交(菜单未开时提交当前输入), Esc 只收面板(阻断冒泡不关对话框)。
      // 本处个性 = ①回车回退提交修剪后的输入框文本 ②IME 组词守卫随单点恒开(收敛前缺, R21-A-04 ③)
      this.comboKeydown({
        items: () => this.movePathOptions,
        open: () => this.movePathMenu,
        setOpen: (v) => { this.movePathMenu = v; },
        hi: () => this.movePathHi,
        setHi: (v) => { this.movePathHi = v; },
        onPick: (p) => this.moveApplyPath(p),
        enterFallback: () => { const p = (this.movePathInput || "").trim(); return p || null; },
        listRef: "movePathList",
        openOnArrow: true,
      }, e);
    },
    /* 失焦收层(与添加种子三下拉 + meta 分类同套单点 _popBlurArm, 见 pitfalls/web-ui/combobox-focusout-close:
     * 40ms 合帧守卫是必需的 —— 点字段 label(for= 转发激活)时浏览器先 blur 再把焦点转回输入框,
     * 同步收层 = 关了又开; 焦点真回来由 openMovePathMenu 撤销。收层前问 _popBlurShouldHold(add_torrent.js 单点)。 */
    movePathBlurClose() {
      this._popBlurArm("_movePopBlurT", ["move-path"], () => {
        this.movePathMenu = false;
        this.movePathHi = -1;
      });
    },
    async submitMoveDialog() {
      if (this.moveBusy) return;
      const location = String(this.movePathInput || "").trim();
      if (!location) {
        this.toast("路径不能为空", "warn");
        return;
      }
      this.moveBusy = true;
      let ok = false;
      try {
        if (this.moveSingleHash) ok = await this._editPost(this.moveSingleHash, "location", { location }, "已移动");
        else ok = await this._bulkEditPost(this.moveTargets, "location", { location }, "批量移动");
      } finally {
        this.moveBusy = false;
      }
      if (ok) this.moveOpen = false;  // 成功即关(与添加种子同口径); 失败留对话框开着让用户改路径
    },
    /* ---------------- 批量编辑(多选右键, 计划 26-10-02-1955 W2): 批量限速 / 批量移动 ----------------
     * 与单选编辑同一家族, 但三处不同: 目标集合是整个选中集合(_bulkTargets 口径, 组键 + 成员 hash
     * 整份交给后端, 展开去重的单一权威在后端); 无当前值可预填(多选各值不同, 预填必然误导);
     * 提交走 /api/torrents/bulk 合单通道(一次 POST + 一个聚合回执), 不做乐观贴片 —— 限速/移动
     * 的行值由 QbApi 写方法同步 store 快照 + bulk_torrents 的 RESYNC 补刷新落行(与标签/分类
     * 的 _metaBulk 同一观感)。 */
    /* 批量速度限制…: 双输入各自独立, 留空 = 该方向不提交(D3 拍板), KiB/s ×1024 与单选同口径。
     * targets / scope 可覆盖: 单组右键(editLimitsGroup)传该组成员 + scope="该组的";
     * 缺省 = 多选右键(选中集合 + "选中的")。 */
    async editLimitsMulti(targets = null, scope = "选中的") {
      this.menu.visible = false;
      targets = targets || this._bulkTargets();
      if (!targets.groupKeys.length && !targets.memberHashes.length) return;
      const res = await this._openModal({
        title: "批量速度限制",
        body: `为${scope} ${targets.groupKeys.length + targets.memberHashes.length} 个目标设置上传/下载速度上限(KiB/s)。留空 = 该项保持不变, 填 0 = 不限速。`,
        fields: [
          { key: "up", label: "上传限制(KiB/s)", value: "", placeholder: "留空不修改, 0 = 不限" },
          { key: "dl", label: "下载限制(KiB/s)", value: "", placeholder: "留空不修改, 0 = 不限" },
        ],
        okText: "应用", cancelText: "取消",
      });
      if (!res) return;
      const body = {};
      for (const [k, key] of [["up", "up_limit"], ["dl", "dl_limit"]]) {
        if (res[k] === "") continue;  // 空 = 不修改该项(只提交有值方向)
        const n = Number(res[k]);
        if (!Number.isFinite(n) || n < 0) {
          this.toast("限速需为非负数字(KiB/s)", "warn");
          return;
        }
        body[key] = Math.round(this.kibToBytes(n));  // KiB/s 转 bytes/s; 0 原样传(qB 语义 = 不限)
      }
      if (!Object.keys(body).length) {
        this.toast("未作修改", "ok", 2000);
        return;
      }
      await this._bulkEditPost(targets, "limits", body, "批量速度限制");
    },
    /* 批量设定位置…: 与单种子同对话框状态机(openMoveDialog), 多选无预填(各值不同, 预填误导)。
     * targets / scope 可覆盖: 单组右键(editMoveGroup)传该组成员 + scope="该组的"; 缺省 = 多选右键。
     * 提交走 _bulkEditPost(与单种子 _editPost 同链路, 由 submitMoveDialog 按 moveSingleHash 分). */
    async editMoveMulti(targets = null, scope = "选中的") {
      this.menu.visible = false;
      targets = targets || this._bulkTargets();
      const n = targets.groupKeys.length + targets.memberHashes.length;
      if (!n) return;
      return this.openMoveDialog(targets, scope, "", "");
    },
    /* 批量跳检…(计划 26-10-02-1955 W3; S4 起确认框升级为预检对话框 26-10-05-0314):
     * 目标集合缺省 = _bulkTargets(多选右键), 单组右键(skipCheckGroup)传该组成员;
     * 组键就地展开成成员 hash 后交 _skipCheckDialog(预检展示与
     * ok 子集的单一口径); 强制路径仍按 keys+hashes 双通道整份提交(与历史载荷同形 + force 键)。
     * 菜单显隐由 flags.skip_check_menu 门控(W1), 后端 bulk 分派处同样 fail-closed。 */
    async skipCheckMulti(targets = null) {
      this.menu.visible = false;
      targets = targets || this._bulkTargets();
      const n = targets.groupKeys.length + targets.memberHashes.length;
      if (!n) return;
      const hashes = [...targets.memberHashes];
      for (const k of targets.groupKeys) {
        const g = this._findGroup(k);
        for (const m of (g && g.members) || []) {
          if (!hashes.includes(m.hash)) hashes.push(m.hash);
        }
      }
      await this._skipCheckDialog(hashes, { mode: "bulk", groupKeys: targets.groupKeys, memberHashes: targets.memberHashes });
    },
    /* 批量编辑统一投递: 与 _metaBulk 同链路(api + waitCmd + toast 三态), 目标集合用打开
     * 对话框时刻锁定的 targets; 不做乐观贴片(见本节头注释)。 */
    async _bulkEditPost(targets, action, extra, okText) {
      const { groupKeys, memberHashes } = targets;
      try {
        const resp = await this.api("/api/torrents/bulk", {
          method: "POST",
          body: JSON.stringify({ action, keys: groupKeys, hashes: memberHashes, ...extra }),
        });
        const r = await this.waitCmd(resp.cmd_id);
        if (r.ok) this.toast(`已执行: ${okText}(${groupKeys.length + memberHashes.length} 个目标)`, "ok", 2500);
        else this.toast(`${okText}失败: ${r.error}`, "error", 8000);
        return r.ok;
      } catch (e) {
        if (!e.auth) this.toast(`${okText}命令发送失败: ` + e.message, "error");
        return false;
      }
    },
    /* 重命名…: 种子显示名(不改磁盘文件名) → POST rename */
    async editRename(h = "") {
      const hash = this._editTargetHash(h);
      if (!hash) return;
      const d = await this._editDetail(hash);
      const res = await this._openModal({
        title: "重命名种子",
        body: "修改种子显示名(不影响磁盘上的文件/目录名)。",
        fields: [{ key: "name", label: "新名称", value: d ? d.name || "" : "", placeholder: "新种子名" }],
        okText: "重命名", cancelText: "取消",
        // 宽档(2026-10-19, 用户报「弹窗太小」): 字段值 = 完整种子显示名, 真实名称 routinely
        // 80~120 字符 —— 通用 modal 基档 520(为确认/提示一句话设计)下输入框仅 474px,
        // 实测 97 字符长名裁掉 223px。走 --modal-w-add(与设定位置/添加种子同档, ctx 菜单
        // 相邻两编辑框同宽也顺眼); cls 经 popovers.html 类绑定并入根元素。
        cls: "rename-dialog",
      });
      if (!res) return;
      if (!res.name) {
        this.toast("名称不能为空", "warn");
        return;
      }
      await this._editPost(hash, "rename", { name: res.name }, "已重命名");
    },
    /* ---------------- 抽屉 Tracker 页签编辑(D 轮): 添加/删除 ---------------- */
    async trackerAdd() {
      const hash = this.drawer.hash;
      if (!hash) return;
      const raw = await this.promptDialog("添加 Tracker", "", {
        placeholder: "announce URL(多条用换行/逗号分隔)", okText: "添加",
      });
      if (raw === null) return;
      const urls = raw.split(/[\s,]+/).map((s) => s.trim()).filter(Boolean);
      if (!urls.length) {
        this.toast("请输入至少一条 tracker URL", "warn");
        return;
      }
      await this._editPost(hash, "trackers/add", { urls }, urls.length > 1 ? `已添加 ${urls.length} 条 tracker` : "tracker 已添加");
    },
    async trackerRemove(url) {
      // url 为 mask 值(详情 API 只回 mask), 后端当场重取原文比对后再删
      const hash = this.drawer.hash;
      if (!hash) return;
      const ok = await this.confirmDialog("删除 Tracker", `将删除该 tracker: ${url}`, { okText: "删除", danger: true });
      if (!ok) return;
      await this._editPost(hash, "trackers/remove", { url }, "tracker 已删除");
    },
    /* ---------------- 抽屉内容页签编辑(D 轮): 优先级小菜单 ----------------
     * 2026-10-14: 经典渲染链移除后, 行选中(fileRowSelect/drawerSelPath)与文件重命名
     * (renameFileRow)随之退役 —— 二者只由已删的 drawer-tabs.html 工具栏/名称格消费,
     * 内容页签变体(10/11/12)自管选中态且不含重命名(见 10 变体头注)。 */
    /* 文件优先级小菜单: 锚定单元格下方, 视口吸附(@click.stop 防止开菜单的点击立即被窗口关闭) */
    openFilePrio(ev, index) {
      this._markCtxSource(ev);
      const rect = ev.currentTarget.getBoundingClientRect();
      const w = 150, h = 176;
      this.filePrio = {
        visible: true, index,
        x: Math.min(Math.max(8, rect.left), Math.max(8, window.innerWidth - w - 8)),
        y: Math.min(rect.bottom + 4, Math.max(8, window.innerHeight - h - 8)),
      };
    },
    /* 优先级 4 档(0=跳过 1=普通 6=高 7=最高) → POST files/priority。
     * indices 可选(计划 26-10-06-0838 S5 内容变体批量通道): 传文件下标数组时一次提交整批
     * (后端 files/priority 本就收 indices 数组, 见 torrent_cmds.py); 缺省沿用 filePrio.index
     * 单文件语义 —— 经典小菜单(ctx-menus.html)与变体 10 的锚定小菜单(openFilePrio)零变化。 */
    async setFilePriority(p, indices = null) {
      this.filePrio.visible = false;
      const hash = this.drawer.hash;
      const idx = Array.isArray(indices) ? indices.slice() : [this.filePrio.index];
      if (!hash || !idx.length || idx.some((i) => !Number.isInteger(i) || i < 0)) return;
      const label = { 0: "不下载", 1: "正常", 6: "高", 7: "最高" }[p] || String(p);
      const okText = Array.isArray(indices)
        ? `已将 ${idx.length} 个文件设为「${label}」` : `优先级已设为「${label}」`;
      await this._editPost(hash, "files/priority", { indices: idx, priority: p }, okText);
    },
    /* 复制种子信息: 目标 hash 显式传入, 缺省回落 menu.hash(S3/M3: 键盘路径 _kbEditAct 传 (field, h),
     * 不再借道菜单状态) */
    async copyTorrentInfo(field, h = "") {
      this.menu.visible = false;
      const hash = h || this.menu.hash;
      const m = this.memberByHash.get(hash);
      if (!m) return;
      let value = field === "name" ? m.name
        : field === "hash" ? (m.infohash_v1 || m.hash)
          : "";
      /* magnet_uri **不在任何轮询载荷里**(issue E-04, P-06 拍板: 后端 _seed_view 已去掉;
       * 契约口径 = 只在用户显式动作时才需要的字段不进每 1.5~3s 一轮的响应体 —— magnet
       * 添加型库为 MB 级增量): "复制磁力"点的时候**按需取一次详情**(复用 _editDetail:
       * 抽屉已开则连请求都不发)。曾因索引条目没有该字段 100% 落到"该种子没有 magnet
       * 链接"(BUG-9), 按需详情即当时的修法。 */
      if (field === "magnet") {
        const d = await this._editDetail(hash);
        value = (d && d.magnet_uri) || "";
      }
      if (!value) {
        this.toast("该种子没有 magnet 链接", "warn");
        return;
      }
      const label = field === "name" ? "种子名" : field === "hash" ? "信息哈希" : "magnet 链接";
      this._copyText(value, label);
    },
    /* ---------------- 种子详情面板(R1B → 方案A 底部停靠, 计划 26-10-03-0917 W1/W2) ----------------
     * 数据: /api/torrents/{hash} 全字段详情; /trackers /files /peers 按需拉取。
     * trackers/peers 在对应 tab 激活期间主节拍轮询(2026-10-14 改, =currentPollMs; 页面隐藏时暂停), 关闭面板即停 —— 不进主循环 tick;
     * General 分组行在 drawerGeneralSections 预格式化(qB 哨兵 -1/-2/8640000 在此统一翻译)。
     * 形态: 右缘浮层改为底部停靠面板(2026-10-04 起落点为 app 级 .drawer-dock, 可见性由 drawerVisible
     * 按形态把守) —— 无遮罩, open 只负责挂状态与拉数据; close 只收面板。
     * W2 键盘跟随: 光标移动经 shortcuts.js::_kbApplyCursor 尾部进 _kbFollowDrawer 单点(防抖 200ms
     * + 请求代际 seq + hash 短路, §2.3), 停稳后经 _switchDrawerTarget 换目标; 显式打开/关闭在此
     * 两处作废在途跟随定时器, 显式操作优先于跟随。 */
    async openTorrentDrawer(hash) {
      // 防御分支: 面板落点只存在于主内容页 —— 设置页没有 .drawer-dock。
      // 2026-10-08(计划 26-10-08-1217): 视图守卫解除 —— 种子页/辅种页/追剧页三视图共用面板,
      // 成员行(辅种页明细/追剧集明细)的右键「详细信息」与双击均落此入口。
      if (this.page !== "groups") return;
      this.menu.visible = false;
      /* FX-29 家族纪律(2026-10-07 报障「切换种子时用户页闪'暂无已连接用户'」): 面板已开着(种子
       * 形态)不得再走下面的整体重建 —— 重建把 peers/trackers/files 清成空列表且 loading=false,
       * 详情在途的整个等待期被渲染成一帧空态(空态 -> 加载态 -> 数据三连闪; pitfalls/web-ui/
       * drawer-switch-flicker「拉新数据前先清空旧数据」—— 其中"高度自适应面板还会塌一下"那半,
       * 面板高度已于 2026-10-18 起恒锁(见 drawerPanelStyle), 不再随内容塌陷, 但内容三连闪仍在)。
       * 已开 = 有旧数据可保留, 归软切换语义: 换目标交棒 _switchDrawerTarget(保留旧数据 + 160ms
       * 延迟遮罩, 与键盘跟随同链路); 同目标重入零副作用(重建把旧数据连 loading 各闪一遍 —— 同坑档
       * 「打开入口的重入语义」, 与 openDrawerTraffic 同目标短路同口径)。 */
      if (this.drawer.open && this.drawerIsSeed) {
        if (this.drawer.hash === hash) return;  // 同目标重入: 短路(重建 = 对同一目标再闪一遍)
        this._switchDrawerTarget(hash);
        return;
      }
      this._stopDrawerPoll();
      this._stopDrawerFollow();  // 显式打开优先于在途跟随(双击换目标 vs 防抖中的跟随, 不得互相打架)
      this._drawerSwitchEnd();   // FX-29: 面板整体重建 -> 无"旧内容可保留", 待到集合与遮罩一并作废
      // 流量页签(S5b, plan 26-10-03-0946 §07 表②)受 qb_traffic_enabled 门控: 上次停在流量页签
      // 而功能后来关闭时落回常规页(页签按钮 v-if=qbTrafficOn 不渲染, 初值也不能落在隐形页签上)
      const last = this.drawerLastTab;
      const initialTab = last === "traffic" && !this.qbTrafficOn ? "general" : (last || "general");
      this._qbTeardown();  // 若上一形态是流量图(全局/分组), 换到种子详情时收轮询与图
      this.drawer = {
        open: true, hash, tab: initialTab, loading: true, error: "",
        detail: null, trackers: [], files: [], peers: { peers: [] },
        // 初值页签的 loading 与空列表同帧置位(26-10-07 报障的冷启动半边): 面板关着/流量形态换形
        // 才走重建, 无旧数据可保留 —— 详情在途窗口期非常规页签的空列表若以 loading=false 裸奔,
        // 会先渲染一帧空态(暂无已连接用户/暂无 tracker/无文件列表), 详情落袋后
        // _loadDrawerTab 才翻成加载态 -> 三连闪。翻转仍归 fetcher 落袋单点, 这里只保证
        // 等待期不落空态(W5 起无变体, 正文由 Vue 组件按 loading 态自渲染)。
        trackersLoading: initialTab === "trackers", filesLoading: initialTab === "content",
        peersLoading: initialTab === "peers",
        // P3-5(报告 26-10-07-0542): 三个列表 fetcher 的失败标记 —— 变体据此区分「失败」与
        // 「真没有」(失败只 toast 时变体把空列表当空态显示, 用户误以为数据真的为空)
        trackersError: "", filesError: "", peersError: "",
        switching: false,  // FX-29: 打开路径不存在"保留旧数据", 遮罩恒不亮(显式建字段见 vue-reactivity)
        kind: "seed", scope: "",
      };
      // 开场落定信号(FX-29 待到集合同机制): 登记详情 + 初值页签的数据源, 全到手 = 面板几何落定,
      // 届时补一发让位(挂单 _drawerOpenReveal 在 _drawerDone 兑现) —— 开场那次量的是 loading 态
      // 几何(面板随后长到 42vh), 文档底打开时 scrollBy 还会被钳制成 0(下滚余量是停靠槽位长高才
      // 创造的; 2026-10-04 回归取证)。流量页签高度恒定(drawerPanelStyle 定高), 不进集合。
      this._drawerWait = new Set(initialTab === "traffic" ? ["detail"] : this._drawerWaitSources(initialTab));
      this._drawerOpenReveal = hash;
      this.persistDrawerOpen();  // W3 开合态记录(D1: 只写不回读, 首屏恒默认关闭)
      this._kbRevealRow(hash);   // 显式打开也让位: 停靠面板一开就压住列表底部, 被点行(双击/右键/Enter)要露出来(2026-10-03 报障)
      await this._fetchDrawerDetail();  // 详情恒拉(头部标题/常规页都依赖); 非常规 tab 再补拉对应数据
      if (initialTab !== "general") this._loadDrawerTab(initialTab);
      // R2 S5: 合并 gc 对 + 初值常规页 —— _loadDrawerTab 不走(常规页只有详情), 文件列表在此补
      // 一发(无 seq 只走 hash 戳守卫, _drawerWait 里的 "files" 由其 _drawerDone 登记)
      else if (this.dtSplitOn && this._dtPairOf(initialTab) === "gc") this._fetchDrawerFiles();
    },
    /* 收面板: 无遮罩可关, 只做面板自身收尾(文件优先级小菜单/行选中; 轮询/软切换收口在数据层
     * drawer_store.js 的 _stopDrawerPoll/_drawerSwitchEnd —— W1 已把取数/竞态/等待集合剥出本文件);
     * drawer.open 跨页不清 —— 切页再回种子页面板状态保持(方案A W1 验收项) */
    closeDrawer() {
      // 槽位冻结 + 落定顶缘登记: leave 期面板转 absolute 出流, dock 会瞬间塌 0 —— 把用户可见高
      // 立即写回 dock 内联(同帧无跳变帧), 钩子(drawerLeaveHook)再从该高度收拢到 0; _drawerAnimTop
      // 供 _kbViewBottom 在收场动画期读落定值(此处 dock 还在全高帧, 是唯一可信测量点)
      const dock = document.querySelector(".drawer-dock");
      if (dock && !dock.classList.contains("drawer-anim")
          && !window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
        const h = Math.round(dock.getBoundingClientRect().height);
        if (h) {
          this._drawerAnimTop = this._drawerFinalTop(dock);
          dock.classList.add("drawer-anim");
          dock.style.height = h + "px";
        }
      }
      this.drawer.open = false;
      this.filePrio.visible = false;
      this.drawerMenu.visible = false;  // 抽屉右键菜单(R2 S3)随面板收
      this._stopDrawerPoll();
      this._stopDrawerFollow();
      this._dtUnmountAll();     // 插件实例逐个 destroy + 清宿主(W7 恢复; 本体 drawer_templates.js)
      this._drawerSwitchEnd();  // FX-29: 收面板即撤切换态(未完成的等待不得挂到下次打开)
      this._qbTeardown();       // 流量形态(全局/分组/单种)轮询与图一并收(2026-10-04 三挂点并入抽屉)
      this.persistDrawerOpen();  // W3 开合态记录(D1: 只写不回读)
    },
    /* tab 切换: general 重新拉详情(反映最新状态); trackers/peers 拉一次并启动轮询; content 拉一次。
     * 切换即记住该 tab(drawerLastTab + localStorage), 使下一个种子默认停在相同页签。 */
    drawerTab(tab) {
      if (this.drawer.tab === tab) return;
      this.drawer.tab = tab;
      this.drawerLastTab = tab;
      this.persistDrawerTab();
      this.filePrio.visible = false;  // 换页签时收起文件优先级小菜单(内容页签专属)
      this._drawerSwitchEnd();  // FX-29: 切页签使在途的那一组响应全部过期(stale 不落袋), 若不撤等待
      this._stopDrawerPoll();   //     遮罩会挂死 —— 显式操作视作结束上一次切换
      this._loadDrawerTab(tab);
    },
    /* ---------------- W2 详情跟随光标(计划 §2.3 四条纪律, 全部收口在此单点) ----------------
     * 触发入口: shortcuts.js::_kbApplyCursor 尾部(鼠标路径将来接同一入口, §1.3 相邻预留)。
     *   1) 触发单点+守卫 —— 面板开 + 主内容页 + 光标是种子行(kind=torrent); 辅种/追剧的
     *      组行/剧行/集行光标(kind=group/show/ep)不跟随(2026-10-08 起成员行光标 kind=torrent
     *      在辅种页/追剧页同样命中, 三视图一体化: 计划 26-10-08-1217);
     *   2) 防抖 200ms —— 连发上下键不逐行拉详情, 停稳才发;
     *   3) 在途请求代际 seq —— _loadDrawerTab 每次 bump, 换 hash 后旧响应一律丢弃(见上);
     *   4) hash 未变短路 —— 光标落回同一行不重拉; 页签内主节拍轮询(_startDrawerPoll)照旧, 互不打架。 */
    _kbFollowDrawer() {
      if (!this.drawer.open) return;
      if (this.page !== "groups") return;  // 主内容页守卫(面板停靠落点; 三视图共用)
      const c = this.kbCursor;
      if (!c || c.kind !== "torrent") return;  // kind 守卫(组行/剧/集单元不跟随)
      if (this.drawer.hash === c.id) return;   // 纪律4: hash 未变短路(含防抖在途的重复触发)
      if (this._followDrawerTimer) clearTimeout(this._followDrawerTimer);
      this._followDrawerTimer = setTimeout(() => {
        this._followDrawerTimer = null;
        // 停稳复核: 面板已关 / 切页走了 / 目标已换(显式打开优先) / 光标又落回原行 -> 放弃本次跟随
        if (!this.drawer.open || this.page !== "groups") return;
        const cur = this.kbCursor;
        if (!cur || cur.kind !== "torrent" || cur.id === this.drawer.hash) return;
        this._switchDrawerTarget(cur.id);
      }, 200);
    },
    _stopDrawerFollow() {
      if (this._followDrawerTimer) {
        clearTimeout(this._followDrawerTimer);
        this._followDrawerTimer = null;
      }
    },
    /* 头部标题: 优先主表成员名(memberByHash 每 1.5~3s 一轮已在本地, 切换瞬间即得) ——
     * 旧实现等详情到位, 中间一帧把标题显示成 40 字符 hash 再跳回种子名, 是肉眼最刺眼的一跳。 */
    drawerTitle() {
      const m = this.memberByHash.get(this.drawer.hash);
      if (m && m.name) return m.name;
      return this.drawer.detail ? this.drawer.detail.name : this.drawer.hash;
    },
    /* 持久化抽屉 tab 偏好(与 persistUiPage 同纪律): 只落"停在哪页"这个意图, 不落派生值;
     * 写入失败(隐私模式/配额满)只影响刷新后落点, 不该打断切页 —— 故吞掉异常。 */
    persistDrawerTab() {
      try {
        localStorage.setItem("autoqb.ui.drawerTab", this.drawerLastTab);
      } catch { /* 写入失败: 本轮仍生效, 刷新后回落默认 */ }
    },
    /* ---------------- W3 高度治理(计划 26-10-03-0917 §2.1/§3.5/D1) ----------------
     * 拖拽调高: 面板顶缘 .drawer-grip 的 pointer 事件(pointer capture, move 实时改高),
     * 夹取 [240px, 70vh]; 持久化: 高度与开合态进
     * localStorage(autoqb.ui.drawerHeight / autoqb.ui.drawerOpen, 与 drawerTab 同族口径)。
     * D1 拍板 = 首屏默认关闭 + 高度记忆仍生效: drawer.open 初值恒 false(state.js),
     * drawerOpen 键只作记录(写入不回读) —— 与「开合态记忆」字面有出入, 首屏满高优先(硬约束)。 */
    /* 夹取函数(纯逻辑, 守阵可锚): px 夹进 [240, 0.7*viewportH]。极小视口下 70vh<240 时
     * 取 70vh 为上界、下界随之取 min(240, 上界) —— 区间保持合法, 面板不越过 70vh 红线。 */
    _drawerClampHeight(px, viewportH) {
      const max = Math.round((viewportH || 0) * 0.7);
      const min = Math.min(240, max);
      return Math.round(Math.min(Math.max(px, min), Math.max(max, min)));  // 取整, 落盘值不带亚像素尾数
    },
    /* 面板内联样式: **展开即锁死高度**, height 与 max-height 同锁一个 px。
     * !2026-10-18(用户报障根治 · 硬约束): 面板高度**绝不随内容自行调整** —— 旧口径未拖拽过时
     * 返回 {} 走 CSS 内容自适应(无 height, max-height:42vh 只兜底), 详情正文里任何元素的
     * 进出场都会改变面板实高: 五区分组「握手中」组随握手连接消失/出现(每 5s 轮询都可能翻动)、
     * 组头计数涨落、摘要行显隐…… 用户所见即「详情面板高度自己跳」。用户裁定: 高度是用户调整的
     * 固定值(拖拽值 autoqb.ui.drawerHeight, 跨会话记忆), 未拖拽过也恒锁默认档 42vh(与 CSS
     * 默认上限同值, 视口跨刷新变同步夹取); 内容超高一律由 .drawer-body(overflow:auto)
     * 内部滚动消化, 面板几何全程不动。与种子详情共用同一 drawerHeightPx(高度复用);
     * 关闭态交给 CSS(面板不渲染); 窄屏全屏态 D3 由 CSS !important 压过(高度记忆失效)。 */
    drawerPanelStyle() {
      if (!this.drawer.open) return {};
      const px = this.drawerHeightPx || Math.round(window.innerHeight * 0.42);
      const h = this._drawerClampHeight(px, window.innerHeight);
      return { height: h + "px", maxHeight: h + "px" };
    },
    /* 顶缘拖拽(pointer capture 挂在 grip 元素上, move/up 都派发给它, 出窗不丢事件)。
     * !命名约束: 模板内联处理器不得用 `_` 前缀 —— Vue 3.5 运行时编译的模板解析不了
     * 下划线开头的裸标识符(ReferenceError), 本文件其余 `_` 方法只经 this.xx 调用故无恙。 */
    drawerGripDown(e) {
      if (!this.drawer.open) return;
      if (e.button !== undefined && e.button !== 0) return;    // 只认主键
      e.preventDefault();  // 防拖拽起手选中文本/触发滚动
      const panel = e.currentTarget.parentElement;  // grip 是 .drawer 的首子节点
      this._drawerDrag = { startY: e.clientY, startH: panel.getBoundingClientRect().height, pid: e.pointerId };
      e.currentTarget.setPointerCapture(e.pointerId);
      document.body.classList.add("drawer-resizing");
    },
    drawerGripMove(e) {
      const d = this._drawerDrag;
      if (!d || e.pointerId !== d.pid) return;
      if (!this.drawer.open) { this.drawerDragStop(); return; }  // 拖拽中面板被关(键盘路径)
      this.drawerHeightPx = this._drawerClampHeight(d.startH + (d.startY - e.clientY), window.innerHeight);
    },
    drawerGripUp(e) {
      const d = this._drawerDrag;
      if (!d || e.pointerId !== d.pid) return;
      this.drawerDragStop();
      this.persistDrawerHeight();  // 松手才落盘(拖拽过程不写 localStorage)
    },
    drawerDragStop() {
      this._drawerDrag = null;
      document.body.classList.remove("drawer-resizing");
    },
    persistDrawerHeight() {
      try {
        localStorage.setItem("autoqb.ui.drawerHeight", String(this.drawerHeightPx));
      } catch { /* 写入失败: 本轮仍生效, 刷新后回落默认 */ }
    },
    /* 开合态记录(D1): 展开=1, 关闭=0。只写不回读 —— 首屏恒默认关闭(硬约束), 键按计划创建 */
    persistDrawerOpen() {
      try {
        localStorage.setItem("autoqb.ui.drawerOpen", this.drawer.open ? "1" : "0");
      } catch { /* 写入失败: 不影响本轮 */ }
    },
    /* ---------------- 出入过渡(Vue <transition> JS 钩子, drawer.html 接线; 用户报"出现/消失很生硬") ----------------
     * 生硬根源: 停靠面板占据文档流, open 翻转时列表底部一帧被面板撑开/收回 —— 面板本体的
     * transform/opacity 滑淡(CSS .drawer-enter/leave-*)治不了布局跳变。修法 = 槽位插值:
     * enter 用 rAF 追赶循环把 .drawer-dock 高度 0 -> 面板实时高(每帧重量, 详情中途到达长高也跟),
     * leave 反向把面板自身高度收拢到 0(dock auto 跟随); 全程只写 height/margin, 不碰面板 :style
     * 绑定, Vue 重渲染即便回写绑定值下一帧也被循环覆盖(自愈)。动画期 .drawer-anim 裁掉溢出,
     * 面板从底缘升起/收回; prefers-reduced-motion 与窄屏全屏态(D3, 面板 fixed 出流)不插值。
     * 几何登记: 插值期间 dock 顶缘是中间值, 让位量测(_kbRevealRow)不许读 —— enter 起拍把
     * "自然高时的 dock 顶缘"(即落定顶缘, sticky 钉底)登记进 _drawerAnimTop, _kbViewBottom
     * 单点优先消费; 收敛/超时/被打断一律清零。seq 代际闸: 快速开关往返时旧循环立即让位新拍。 */
    _drawerFinalTop(dock) {
      return Math.round(dock.getBoundingClientRect().top);
    },
    _drawerAnimStop() {
      if (this._drawerAnimRaf) {
        cancelAnimationFrame(this._drawerAnimRaf);
        this._drawerAnimRaf = 0;
      }
      const dock = document.querySelector(".drawer-dock.drawer-anim");
      if (dock) {
        dock.classList.remove("drawer-anim");
        dock.style.height = "";
        dock.style.marginTop = "";
      }
    },
    drawerEnterHook(el) {
      const dock = el.parentElement;  // 面板落点 = .drawer-dock(tpl-manifest 注入), aside 的父节点
      this._drawerAnimStop();
      this._drawerAnimSeq = (this._drawerAnimSeq || 0) + 1;
      if (!dock || window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
      const seq = this._drawerAnimSeq;
      // 重开打断收场: 被打断的 leave 已把内联高写在面板上, 清掉再量自然高(压成 0 会把自然高量成 0,
      // 整段动画失效); 槽位残局由 _drawerAnimStop 清理, 面板淡出中的视觉由 CSS enter 接管
      for (const old of dock.querySelectorAll(".drawer.drawer-leave-active")) old.style.height = "";
      dock.style.height = "";  // 量自然高(清残留内联)
      const h0 = dock.getBoundingClientRect().height;
      this._drawerAnimTop = h0 ? this._drawerFinalTop(dock) : 0;  // 自然高帧的顶缘 = 落定顶缘(sticky 钉底)
      if (!h0) return;  // 窄屏全屏态(D3, 面板 fixed 不占布局)或空内容: 无槽位可插值, 交回纯 CSS 滑淡
      const m0 = parseFloat(getComputedStyle(dock).marginTop) || 0;
      dock.classList.add("drawer-anim");
      dock.style.height = "0px";
      dock.style.marginTop = "0px";
      const t0 = performance.now();
      const step = () => {
        if (seq !== this._drawerAnimSeq) return;  // 被新开合打断: 新拍已接管 dock
        const target = el.getBoundingClientRect().height;  // 每帧追面板实时高(详情中途长高也跟)
        const cur = parseFloat(dock.style.height) || 0;
        const next = cur + (target - cur) * 0.45;
        if (Math.abs(target - next) < 1 || performance.now() - t0 > 400) {
          dock.style.height = "";  // 收敛: 回交自然高, 内容后续涨落不再经动画
          dock.style.marginTop = "";
          dock.classList.remove("drawer-anim");
          this._drawerAnimTop = 0;
          this._drawerAnimRaf = 0;
          return;
        }
        dock.style.height = next + "px";
        dock.style.marginTop = Math.min(m0, next * (m0 / h0)) + "px";  // 呼吸距随槽位同步长出
        // 落定顶缘逐帧重登记: 详情中途长高后, enter 起拍登记的 loading 态顶缘不再是落定值,
        // 让位量测(_kbRevealRow/键盘跟随)会按旧几何漏让(2026-10-04 回归取证)。dock sticky
        // 吸底期底缘恒定(margin-top 不参与吸底定位), 落定顶缘 = dock 底缘 - 面板自然高
        // (面板自身布局高不受 dock 槽位 overflow 裁剪, 即当前内容的落定高)。
        this._drawerAnimTop = Math.round(dock.getBoundingClientRect().bottom - target);
        this._drawerAnimRaf = requestAnimationFrame(step);
      };
      this._drawerAnimRaf = requestAnimationFrame(step);
    },
    drawerAfterEnterHook() {
      if (!this.drawer.open) return;  // 入场被快速关闭打断: 迟到的钩子不得杀掉 leave 拍的动画循环
      this._drawerAnimStop();  // 兜底: 追赶循环若仍在途(慢收敛)强制收场回自然高
      this._drawerAnimTop = 0;
      // 槽位落定后补一发让位: 文档底打开时开场让位被钳制成 0(下滚余量是停靠槽位长高才创造的,
      // 2026-10-04 取证), 此刻槽位已回自然高、余量足额, 且收场兜底强制回自然高后几何是实量值。
      // 流量形态无种子行可让, 不发。
      if (this.drawerIsSeed) this._kbRevealRow(this.drawer.hash);
    },
    drawerLeaveHook(el) {
      // closeDrawer 已冻结槽位(drawer-anim + 捕获高)时先取值再清理 —— 面板马上转 absolute 出流,
      // 之后 dock 的自然高就塌了, 量不回用户看到的最后一帧
      const frozenDock = document.querySelector(".drawer-dock.drawer-anim");
      const frozenH = frozenDock ? Math.round(frozenDock.getBoundingClientRect().height) : 0;
      this._drawerAnimStop();
      this._drawerAnimSeq = (this._drawerAnimSeq || 0) + 1;
      if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) { this._drawerAnimTop = 0; return; }
      if (getComputedStyle(el).position === "fixed") { this._drawerAnimTop = 0; return; }  // D3 窄屏全屏态: 面板出流, 无布局可插值
      const dock = el.parentElement;
      if (!dock) { this._drawerAnimTop = 0; return; }
      const seq = this._drawerAnimSeq;
      // 优先用 closeDrawer 捕获的用户可见高; 未捕获(入场中被打断, enter 已登记顶缘)退面板实高
      const h0 = frozenH || Math.round(el.getBoundingClientRect().height);
      if (!h0) { this._drawerAnimTop = 0; return; }  // 空内容: 无高度可收
      if (!frozenH && !this._drawerAnimTop) this._drawerAnimTop = this._drawerFinalTop(dock);
      const m0 = parseFloat(getComputedStyle(dock).marginTop) || 0;
      dock.classList.add("drawer-anim");
      dock.style.height = h0 + "px";  // 从捕获帧起步, 面板同步收拢 —— 两边同一曲线永不脱节
      const t0 = performance.now();
      const step = () => {
        if (seq !== this._drawerAnimSeq) return;  // 重开接管: enter 拍已接管 dock 与面板
        const t = Math.min(1, (performance.now() - t0) / 160);  // 收场 160ms = CSS 退场(.drawer-leave-active)同拍
        const k = t * t;  // easeInQuad: 收场加速(与退场滑淡 ease-in 同感)
        // 收面板自身高度(面板已转 absolute 底缘锚定, 底边钉死向下收), dock 冻结高同步跟缴 —— 列表全程只看到面板沉下去
        el.style.height = Math.max(0, Math.round(h0 * (1 - k))) + "px";
        dock.style.height = el.style.height;
        dock.style.marginTop = Math.round(m0 * (1 - k)) + "px";  // 呼吸距同步收回, 免得尾部刺 8px
        if (t < 1) {
          this._drawerAnimRaf = requestAnimationFrame(step);
          return;
        }
        this._drawerAnimRaf = 0;  // 面板节点随后被 Vue 摘除; dock 残留内联由 afterLeave 兜底清
      };
      this._drawerAnimRaf = requestAnimationFrame(step);
      this._drawerAnimDock = dock;  // afterLeave 时面板已出 DOM(parentElement 为 null), 提前留手
    },
    drawerAfterLeaveHook() {
      if (this.drawer.open) return;  // 收场被快速重开打断: 迟到的钩子不得杀掉 enter 拍的动画循环
      this._drawerAnimStop();  // 面板已出 DOM, 兜底清 dock 内联与在途循环
      const dock = this._drawerAnimDock;
      if (dock) {
        dock.classList.remove("drawer-anim");
        dock.style.height = "";
        dock.style.marginTop = "";
        this._drawerAnimDock = null;
      }
      this._drawerAnimTop = 0;
    },
    /* 抽屉头部动作: 复用 actTorrent(自带回执/toast), 目标 = 抽屉 hash(显式传参, 不动 menu 状态) */
    drawerAct(action) {
      this.actTorrent(action, this.drawer.hash);
    },
    /* 抽屉删除: 复用 delTorrent(确认框流程一致); 删除成功(成员消失)后自动收起抽屉 */
    drawerDel() {
      this._drawerDeletePending = true;
      Promise.resolve(this.delTorrent(this.drawer.hash)).then(() => {
        if (this._drawerDeletePending && !this.memberByHash.get(this.drawer.hash)) this.closeDrawer();
        this._drawerDeletePending = false;
      });
    },
    /* General tab 分组行(预格式化): qB 哨兵在此统一翻译 —— -1=从未/未设, 8640000=无 ETA。
     * W5-RFB-01 展示重构: 分组重组为 基础/传输/时间/路径, 每行带 sprite 图标(icon)供字段行渲染(f-row) */
    drawerGeneralSections() {
      const d = this.drawer.detail;
      if (!d) return [];
      const dur = (v, dash) => (v === null || v === undefined || v < 0) ? (dash || "未设") : this.fmtDuration(v);
      const ts = (v) => this.fmtTs(v) || "—";  // 抽屉保留"—"(TBL-01 只改主页面表格)
      const size = (v) => this.fmtSizeOrDash(v) || "—";
      const yn = (v) => (v ? "是" : "否");
      const lim = (v) => (v === null || v === undefined || v < 0) ? "未设" : (v === 0 ? "不限" : this.fmtDuration(v));
      return [
        {
          title: "基础",
          sum: `容量 ${size(d.size)} · 分享率 ${(d.ratio ?? 0).toFixed(2)}`,
          rows: [
            { icon: "#i-percent", label: "进度", text: `${((d.progress || 0) * 100).toFixed(1)}%` },
            { icon: "#i-hdd", label: "大小", text: size(d.size) },
            { icon: "#i-layers", label: "总大小", text: size(d.total_size) },
            { icon: "#i-download", label: "剩余", text: size(d.amount_left) },
            { icon: "#i-pulse", label: "可用性", text: (d.availability ?? 0).toFixed(2) },
            { icon: "#i-percent", label: "分享率", text: (d.ratio ?? 0).toFixed(3) },
            { icon: "#i-lock", label: "私有", text: yn(d.private) },
            // FX-22: 哈希/备注可能极长 -> 块行 + 右侧"复制"(不再只能悬停看 title)
            { icon: "#i-hash", label: "信息哈希值 v1", text: d.infohash_v1 || "—", mono: true, wide: true, act: "copy" },
            { icon: "#i-hash", label: "信息哈希值 v2", text: d.infohash_v2 || "—", mono: true, wide: true, act: "copy" },
            { icon: "#i-columns", label: "区块", text: d.piece_size ? `${d.pieces_have ?? 0} / ${d.pieces_num ?? 0} × ${this.fmtSize(d.piece_size)}` : "—" },
            { icon: "#i-info", label: "已含元数据", text: yn(d.has_metadata) },
            { icon: "#i-calendar", label: "创建于", text: ts(d.creation_date) },
            { icon: "#i-settings", label: "创建工具", text: d.created_by || "—" },
            { icon: "#i-list", label: "备注", text: d.comment || "—", wide: true },
          ],
        },
        {
          title: "传输",
          sum: `实时 ↓${this.fmtSpeedOrDash(d.dlspeed) || "—"} ↑${this.fmtSpeedOrDash(d.upspeed) || "—"}`,
          rows: [
            { icon: "#i-download", label: "下载速度", text: this.fmtSpeedOrDash(d.dlspeed) || "—" },
            { icon: "#i-upload", label: "上传速度", text: this.fmtSpeedOrDash(d.upspeed) || "—" },
            { icon: "#i-hourglass", label: "ETA", text: this.fmtEta(d.eta) || "—" },
            { icon: "#i-download", label: "已下载", text: size(d.downloaded) },
            { icon: "#i-upload", label: "已上传", text: size(d.uploaded) },
            { icon: "#i-download", label: "会话已下载", text: size(d.downloaded_session) },
            { icon: "#i-upload", label: "会话已上传", text: size(d.uploaded_session) },
            { icon: "#i-warn", label: "已丢弃", text: size(d.total_wasted) },
            { icon: "#i-arrow-up", label: "做种数", text: String(d.num_seeds ?? 0) },
            { icon: "#i-arrow-down", label: "用户", text: String(d.num_leechs ?? 0) },
            { icon: "#i-globe", label: "完整/下载中", text: `${d.num_complete ?? 0} / ${d.num_incomplete ?? 0}` },
            { icon: "#i-globe", label: "Tracker 数", text: String(d.trackers_count ?? 0) },
            { icon: "#i-link", label: "连接", text: `${d.connections_count ?? 0} / ${d.connections_limit ?? 0}` },
            { icon: "#i-refresh", label: "下次重新汇报", text: dur(d.reannounce_in || d.reannounce, "—") },
            { icon: "#i-x-circle", label: "Tracker 错误", text: yn(d.has_tracker_error) },
            { icon: "#i-warn", label: "Tracker 警告", text: yn(d.has_tracker_warning) },
            { icon: "#i-percent", label: "分享率限制", text: (d.max_ratio ?? -1) < 0 ? "未设" : d.max_ratio.toFixed(2) },
            { icon: "#i-timer", label: "做种时间限制", text: lim(d.max_seeding_time) },
            { icon: "#i-timer", label: "不活跃做种限制", text: lim(d.max_inactive_seeding_time) },
            { icon: "#i-bolt", label: "限制动作", text: d.share_limit_action || "—" },
          ],
        },
        {
          title: "时间",
          sum: `添加 ${ts(d.added_on)}`,
          rows: [
            { icon: "#i-calendar", label: "添加于", text: ts(d.added_on) },
            { icon: "#i-check-circle", label: "完成于", text: ts(d.completion_on) },
            { icon: "#i-eye", label: "最后完整可见", text: ts(d.seen_complete) },
            { icon: "#i-clock", label: "最近活动", text: ts(d.last_activity) },
            { icon: "#i-timer", label: "活动时间", text: dur(d.time_active, "—") },
            { icon: "#i-timer", label: "做种时间", text: dur(d.seeding_time, "—") },
          ],
        },
        {
          title: "路径",
          sum: `自动种子管理 ${yn(d.auto_tmm)}`,
          // FX-22: 路径行一律块行 + 右侧"打开目录"(走后端 /api/open-path) —— 路径是本页最长、
          // 最常需要"去磁盘上看一眼"的一类值
          rows: [
            { icon: "#i-folder-open", label: "保存路径", text: d.save_path || "—", wide: true, act: "open" },
            { icon: "#i-folder", label: "内容路径", text: d.content_path || "—", wide: true, act: "open" },
            { icon: "#i-folder-open", label: "下载路径", text: d.download_path || "—", wide: true, act: "open" },
            { icon: "#i-folder", label: "根路径", text: d.root_path || "—", wide: true, act: "open" },
            { icon: "#i-sliders", label: "自动种子管理", text: yn(d.auto_tmm) },
            { icon: "#i-play", label: "强制启动", text: yn(d.force_start) },
            { icon: "#i-upload", label: "超级做种", text: yn(d.super_seeding) },
            { icon: "#i-sort", label: "按顺序下载", text: yn(d.seq_dl) },
            { icon: "#i-bolt", label: "先下载首尾文件块", text: yn(d.f_l_piece_prio) },
          ],
        },
      ];
    },
    /* FX-22: 字段行图标着色 —— 由**图标名派生**色调类, 而不是给 48 行逐个加 tone 字段:
     * 图标本身已隐含语义(下载/上传/日历/文件夹/哈希...), 派生表是单点, 新增行自动生效。
     * 色值全在 views.css 的 .ico-t-* 族里走主题令牌。 */
    icoTone(icon) {
      const map = {
        "#i-download": "ico-t-io", "#i-upload": "ico-t-io", "#i-arrow-up": "ico-t-io", "#i-arrow-down": "ico-t-io",
        "#i-hdd": "ico-t-cap", "#i-layers": "ico-t-cap", "#i-columns": "ico-t-cap",
        "#i-calendar": "ico-t-time", "#i-clock": "ico-t-time", "#i-timer": "ico-t-time",
        "#i-hourglass": "ico-t-time", "#i-eye": "ico-t-time",
        "#i-globe": "ico-t-site", "#i-link": "ico-t-site",
        "#i-lock": "ico-t-sw", "#i-sliders": "ico-t-sw", "#i-play": "ico-t-sw", "#i-sort": "ico-t-sw",
        "#i-bolt": "ico-t-sw", "#i-settings": "ico-t-sw", "#i-refresh": "ico-t-sw",
        "#i-hash": "ico-t-id", "#i-info": "ico-t-id", "#i-tag": "ico-t-id", "#i-list": "ico-t-id",
        "#i-folder": "ico-t-path", "#i-folder-open": "ico-t-path",
        "#i-percent": "ico-t-state", "#i-pulse": "ico-t-state", "#i-check-circle": "ico-t-state",
        "#i-x-circle": "ico-t-state", "#i-warn": "ico-t-state",
      };
      return map[icon] || "";
    },
    /* Content tab: qB files[].name 为 '/' 分隔相对路径 -> 构树后扁平化(缩进渲染);
     * 目录行聚合大小; 文件行展示 进度/优先级(0=跳过 1=普通 4|6=高 7=最高), 优先级可点改(小菜单);
     * 每行带 index(种子内原始下标, files/priority 用)与 path(完整相对路径, 选中/rename-fs 用) */
    drawerFileRows() {
      const files = this.drawer.files || [];
      const root = { dirs: new Map(), files: [], size: 0, path: "" };
      for (let fi = 0; fi < files.length; fi++) {
        const f = files[fi];
        const parts = String(f.name || "").split("/").filter(Boolean);
        let node = root;
        for (let i = 0; i < parts.length - 1; i++) {
          if (!node.dirs.has(parts[i])) {
            node.dirs.set(parts[i], { dirs: new Map(), files: [], size: 0, path: node.path ? node.path + "/" + parts[i] : parts[i] });
          }
          node = node.dirs.get(parts[i]);
          node.size += f.size || 0;
        }
        node.files.push({ ...f, index: fi });
      }
      const prio = (p) => ({ 0: "不下载", 1: "正常", 4: "高", 6: "高", 7: "最高" }[p] ?? "正常");
      const rows = [];
      const walk = (node, name, depth) => {
        if (name !== null) rows.push({
          depth, dir: true, name, path: node.path, text: this.fmtSize(node.size),
          _raw: { name, size: node.size, progress: 0 },
        });
        for (const [dn, d] of node.dirs) walk(d, dn, name === null ? 0 : depth + 1);
        for (const f of node.files) {
          const last = String(f.name || "").split("/").pop();
          rows.push({
            depth: name === null ? 0 : depth + 1, dir: false,
            name: last,
            path: node.path ? node.path + "/" + last : last,
            index: f.index,
            text: this.fmtSize(f.size), progress: Math.round((f.progress || 0) * 100),
            prio: prio(f.priority), skipped: f.priority === 0,
            // W2: 排序取原始值(大小/进度) —— 显示值 text 是 "1.2 MiB" 这类格式化字符串, 见 _sortVal
            _raw: { name: last, size: f.size || 0, progress: f.progress || 0, prio: f.priority },
          });
        }
      };
      walk(root, null, -1);
      return rows;
    },
    /* Peers tab: qB 响应 peers 可能为 dict(以 ip:port 为键)或数组 —— 双形态归一。
     * W2(计划 26-10-11-2106): 每行附 `_raw`(原始数值) —— 接壳后列头可排序, 而显示值 dlspeed 等
     * 是 `fmtSpeedOrDash` 出的字符串("1.2 MiB"), 按显示值比就是字典序错排; 排序取值见
     * sort.js `_sortVal`(优先 `_raw`)。显示字段一个未动 —— 15 个变体与其它消费方零影响。 */
    drawerPeerRows() {
      const p = this.drawer.peers || {};
      const list = Array.isArray(p.peers) ? p.peers : Object.values(p.peers || {});
      return list.map((x) => ({
        addr: `${x.ip || "?"}${x.port ? ":" + x.port : ""}`,
        client: x.client || "—",
        flags: x.flags || "—",
        progress: Math.round((x.progress || 0) * 100),
        dlspeed: this.fmtSpeedOrDash(x.dlspeed || 0) || "—",  // 抽屉 peers 表保留"—"
        upspeed: this.fmtSpeedOrDash(x.upspeed || 0) || "—",
        downloaded: this.fmtSizeOrDash(x.downloaded || 0) || "—",
        uploaded: this.fmtSizeOrDash(x.uploaded || 0) || "—",
        relevance: `${Math.round((x.relevance || 0) * 100)}%`,
        _raw: {
          addr: `${x.ip || "?"}${x.port ? ":" + x.port : ""}`,
          client: x.client || "", flags: x.flags || "",
          progress: x.progress || 0,
          dlspeed: x.dlspeed || 0, upspeed: x.upspeed || 0,
          downloaded: x.downloaded || 0, uploaded: x.uploaded || 0,
          relevance: x.relevance || 0,
        },
      }));
    },
    /* 2026-10-14: drawerTrackerRows() 随经典 Tracker 表退役(变体 04/05/06 的行装配在各自
     * rowsFn 里, 不再经根方法)。下面两条仍是变体消费的公共判定/翻译单点。 */
    drawerTrackerStatus(s) {
      return { 0: "禁用", 1: "未联系", 2: "工作", 3: "更新中", 4: "未工作" }[s] ?? "—";
    },
    drawerTrackerVirtual(url) {
      const u = String(url || "");
      return u.startsWith("**") || ["[DHT]", "[PeX]", "[LSD]"].some((p) => u.startsWith(p));
    },
  },
  watch: {
    /* 设定位置下拉限高(与添加种子三下拉 + meta 分类同口径, add_torrent.js::_fitAddPop 注释):
     * 开层(watcher movePathMenu)/候选到位(loadMoveOptions)/过滤词变化(movePathInput)三处都要重限,
     * 少一处出现"删字后候选涨回全量把对话框撑变形"。 */
    movePathMenu(v) {
      if (v) this._fitAddPop("movePathList");
    },
    movePathInput() {
      if (this.movePathMenu) this._fitAddPop("movePathList");
    },
    movePathOptions() {
      if (this.movePathMenu) this._fitAddPop("movePathList");
    },
  },
};
