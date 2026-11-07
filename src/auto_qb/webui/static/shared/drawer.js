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

/* 设定位置对话框: 下拉开层后「限高重测」的延时(2026-10-29)。开层时 body 的 padding-bottom 走
 * 200ms 过渡(三皮肤 dialogs.css `.modal.move-dialog .add-dialog-body`), 过渡**进行中**量到的净空
 * 只有一半 -> _fitAddPop 会把列表误限到 120px 且不再自恢复; 过渡结束(+余量)后复位重测一次。
 * !本常量必须 > CSS 过渡时长 —— 改任一边必须同步另一边(守阵查两处都在)。 */
const MOVE_POP_SETTLE_MS = 240;

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
 * !R2->R3 历史(判据语义, 不得回退): R2 曾按标志值渲染固定一对 + 挂载按当前对找宿主 = 空列 bug
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
  /* W4 收口的两条监听(语义逐字未改): (1) resize 防抖回写 dtWinW +
   * 门跨越后重挂/补给; (2) drawerMerge 换代(右键开关)后重挂 + 第二列数据补给。
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
        // 语义配色分级(计划 26-10-19-2341): 跳检有代价但可重来 -> warn 档(与不可逆的删除拉开
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
          // 计数行按最坏结果取档: 有禁止->error, 有需强制->warn, 全 ok->ok(计划 26-10-19-2341)
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
        const run = this._runningToast(`批量跳检已提交: ${n} 个目标, 每个约需数秒`);
        const r = await this.waitCmd(resp.cmd_id, 60000);
        if (r.ok) await this._settleRunningToast(run, "ok", `已执行: 批量跳检(${n} 个目标)`, 3000);
        else await this._settleRunningToast(run, "error", `批量跳检未完成: ${r.error}`, 8000);
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
    /* ---------------- 整组迁移 confirm 回路(issue 26-11-04-0734 / 计划 26-10-18-1604 P5) ----------------
     * 后端按设计「未确认零副作用」: relocate_exec 对 cls=confirm 直接 continue, 回执仍 status=ok,
     * 只在 truth.summary.confirm 里计数 —— 前端必须在 r.ok 之上再读 summary, 否则会把「等确认」
     * 误报成「已执行」。下列方法供 _editPost / _bulkEditPost 两条投递路径共用。 */
    _relocateConfirmCount(r) {
      return Number((r && r.truth && r.truth.summary && r.truth.summary.confirm) || 0);
    },
    /* 确认框行表: 形态/来源/目标/未来种子/原因/提示; 目录别名把「以后新增也落新位置」讲透。
     * 多项时加 #n 前缀(verdict 行 key 按序号生成, 同 label 不会撞键)。 */
    _relocateConfirmRows(r) {
      const FORMS = { dir_alias: "目录别名(在目标路径建目录/符号链接)", file_links: "逐文件链接", direct: "直接搬移" };
      const items = ((r && r.truth && r.truth.results) || []).filter((it) => it && it.cls === "confirm");
      const multi = items.length > 1;
      const rows = [];
      items.forEach((it, i) => {
        const p = multi ? `#${i + 1} ` : "";
        const alias = it.form === "dir_alias";
        rows.push({ icon: "#i-folder-open", label: p + "迁移形态", value: FORMS[it.form] || String(it.form || "未知") });
        rows.push({ icon: "#i-folder", label: p + "来源", value: String(it.save_path || "") });
        rows.push({ icon: "#i-folder", label: p + "目标", value: String(it.target || ""), wide: true });
        rows.push({
          icon: alias ? "#i-warn" : "#i-info",
          label: p + "未来种子",
          value: alias
            ? "受影响: 目录别名指向新位置, 该目录以后新增/写入的文件也会落到新目标路径"
            : "不受影响: 只链接本组现有文件, 以后新增的种子仍按各自保存路径落盘",
          wide: true,
        });
        const reason = (it.reasons || []).map((x) => x && x.text).filter(Boolean).join("; ");
        if (reason) rows.push({ icon: "#i-warn", label: p + "原因", value: reason, wide: true });
        const note = (it.notes || []).filter(Boolean)[0];
        if (note) rows.push({ icon: "#i-info", label: p + "提示", value: note, wide: true });
      });
      return rows;
    },
    /* 二次确认框(返回 Promise<boolean>); 取消 = 不重发、零副作用 */
    async _relocateConfirmGate(r) {
      const items = ((r && r.truth && r.truth.results) || []).filter((it) => it && it.cls === "confirm");
      if (!items.length) {  // 回执只有计数没有明细: 不猜、不弹无信息框
        this.toast("迁移未发起: 回执缺少确认明细, 请稍后重试", "warn", 8000);
        return false;
      }
      const hasAlias = items.some((it) => it.form === "dir_alias");
      const body = `后端已拦截 ${items.length} 个目标, 确认前不做任何改动(不建任务、不动 qB)。`
        + (hasAlias
          ? " 其中含目录别名: 确认后该目录会指向新位置, 目录里以后新增/写入的文件也会落到新目标路径。"
          : " 确认后仅链接本组现有文件, 不影响未来新增。");
      return (await this._openModal({
        title: "需确认: 迁移方式",
        body,
        icon: "#i-warn",
        verdict: this._relocateConfirmRows(r),
        okText: "确认迁移",
        cancelText: "取消",
        tone: "warn",
        wide: true,
      })) === true;
    },
    /* 成功 toast 按真实回执计数(整组迁移回执带 truth.summary; 其余动作无 summary 走原文案) */
    _relocateDoneText(r, okText) {
      const s = (r && r.truth && r.truth.summary) || null;
      if (!s) return `已执行: ${okText}`;
      const parts = [`已发起 ${s.started || 0} 项`];
      if (s.skip) parts.push(`跳过 ${s.skip} 项`);
      if (s.blocked) parts.push(`拒绝 ${s.blocked} 项`);
      if (s.confirm) parts.push(`待确认 ${s.confirm} 项`);
      return `已执行: ${okText} — ${parts.join(" / ")}`;
    },
    /* 编辑类命令统一投递: api + waitCmd 回执 + toast 三态; 成功后按动作刷新抽屉对应页签数据。
     * 返回 true/false; 整组迁移命中 confirm 时返回 "confirm"(零副作用等确认, 交 submitMoveDialog
     * 开二次确认框后带 confirm=true 重发), 不弹成功。 */
    async _editPost(hash, action, body, okText) {
      try {
        const resp = await this.api(`/api/torrents/${hash}/${action}`, {
          method: "POST",
          body: JSON.stringify(body),
        });
        const r = await this.waitCmd(resp.cmd_id);
        /* 整组迁移命中 confirm(目录别名/长路径校正): 后端零副作用等确认, 回执仍 ok —— 不报成功 */
        if (r.ok && action === "location" && this._relocateConfirmCount(r) > 0) {
          this._pendingRelocateConfirm = r;
          return "confirm";
        }
        if (r.ok) {
          this.toast(this._relocateDoneText(r, okText), "ok", 2500);
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
    /* 速度限制…: 上传/下载两输入(KiB/s; 空=不改, 0=不限) -> POST limits(×1024 转 bytes, 0 原样传) */
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
          this.toast("限速值无效: 需为非负数字(KiB/s)", "warn");
          return;
        }
        body[key] = Math.round(this.kibToBytes(n));  // KiB/s -> bytes/s; 0 原样传(后端语义 = 不限)
      }
      if (!Object.keys(body).length) {
        this.toast("未作修改: 输入与当前值一致", "ok", 2000);
        return;
      }
      await this._editPost(hash, "limits", body, "限速已更新");
    },
    /* 分享率限制…: 分享率/做种时间(h)/不活跃做种时间(h) -> POST share-limits(-2 = 恢复全局默认)
     * 哨兵语义与后端 commands_limit.py::_cmd_set_share_limits 对齐: -2 = 用全局, -1 = 不限制(R5#60)。 */
    async editShareLimits(h = "") {
      const hash = this._editTargetHash(h);
      if (!hash) return;
      const d = await this._editDetail(hash);
      const hrs = (sec) => (sec > 0 ? String(Math.round((sec / 3600) * 100) / 100) : "");  // -2/-1/0(全局/不限制/未设)留空
      const res = await this._openModal({
        title: "分享率限制",
        body: "达到任一限制后该种子将停止做种。留空 = 保持不变, 输 -2 = 恢复全局默认。",
        fields: [
          { key: "ratio", label: "分享率上限", value: d && d.max_ratio >= 0 ? String(d.max_ratio) : "", placeholder: "留空不修改, -2 = 全局" },
          { key: "time", label: "做种时间上限(小时)", value: d ? hrs(d.max_seeding_time) : "", placeholder: "留空不修改, -2 = 全局" },
          { key: "inactive", label: "不活跃做种上限(小时)", value: d ? hrs(d.max_inactive_seeding_time) : "", placeholder: "留空不修改, -2 = 全局" },
        ],
        okText: "应用", cancelText: "取消",
      });
      if (!res) return;
      const body = {};
      if (res.ratio !== "") {
        const n = Number(res.ratio);
        if (!Number.isFinite(n) || (n < 0 && n !== -2)) {
          this.toast("分享率无效: 需为非负数字或 -2", "warn");
          return;
        }
        body.ratio_limit = n;
      }
      for (const [k, key] of [["time", "seeding_time_limit"], ["inactive", "inactive_seeding_time_limit"]]) {
        if (res[k] === "") continue;  // 空 = 不修改
        const n = Number(res[k]);
        if (!Number.isFinite(n) || (n < 0 && n !== -2)) {
          this.toast("时长无效: 需为非负小时数或 -2", "warn");
          return;
        }
        body[key] = n === -2 ? -2 : Math.round(n * 3600);  // 小时 -> 秒; -2 原样(用全局)
      }
      if (!Object.keys(body).length) {
        this.toast("未作修改: 输入与当前值一致", "ok", 2000);
        return;
      }
      await this._editPost(hash, "share-limits", body, "分享率限制已更新");
    },
    /* 设定位置…(2026-10-13): 单种子/单组/多选批量三入口统一改, 保存路径下拉候选按「最近使用」
     * 排序(与添加种子保存路径同口径, 复用 add_torrent.js 的 _addRecencyMaps/_addOrderByRecent/_addNormPath
     * 单点 —— 全局 mixin 合并, 跨模块互调与拆分前逐字等价)。下拉候选 = /api/paths 已知保存路径;
     * 单种子预填当前 save_path, 批量/单组无预填(各值不同, 预填误导)。目标集合打开时刻锁定(与 meta 同口径)。
     * combobox 收层/限高/悬停与添加种子三下拉 + meta 分类同套口径(见 pitfalls/web-ui/combobox-focusout-close)。
     * 三入口名/签名(editMove/editMoveMulti/editMoveGroup)与下游投递(editMove->_editPost,
     * editMoveMulti/editMoveGroup->_bulkEditPost)不变 —— 守阵 + 触发登记表钉这些。 */
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
      // 开对话框即聚焦输入框(键盘路径可直接打字/回车), 但**不展开下拉**(2026-10-29 用户拍板):
      // 打开就弹面板会让「第一眼」是开层态, 收层时窗口高度骤变 = 跳变。抑制标志只消费一次,
      // 之后点输入框 / 按方向键照常展开(见 openMovePathMenu 首行)。
      this.moveSuppressOpen = true;
      clearTimeout(this._movePopSettleT);
      this.$nextTick(() => {
        const el = this.$refs.movePathInputEl;
        if (el) el.focus();
      });
    },
    closeMove() {
      if (this.moveBusy) return;  // 命令回执等待期不允许误关(与 meta 同口径)
      clearTimeout(this._movePopSettleT);
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
      // 打开即聚焦的那一次不展开(2026-10-29): 抑制标志只消费一次, 之后点输入框/方向键照常展开
      if (this.moveSuppressOpen) { this.moveSuppressOpen = false; return; }
      this._popBlurCancel("_movePopBlurT");  // 焦点回到本输入框时撤销挂起的失焦收层, 菜单不闪
      this.movePathMouseAt = null;  // 开层复位悬停门限坐标(同 addCatMouseAt)
      this.movePathHi = this.movePathOptions.indexOf(this.movePathInput.trim());
      this.movePathMenu = true;
      this._hiScroll("movePathList");
      this._movePopSettle();  // 高度过渡结束后复位重测限高(过渡中量到的净空只有一半)
    },
    /* 高度过渡后的限高重测(2026-10-29): 开层时 body 的 padding-bottom 走 200ms 过渡, 过渡中量到的
     * 净空偏小会把列表误限到 120px 且不再自恢复 -> 过渡结束(+余量)后 _fitAddPop 复位重测一次。
     * 时长单点见文件头 MOVE_POP_SETTLE_MS(必须 > CSS 过渡时长, 改任一边同步另一边)。 */
    _movePopSettle() {
      clearTimeout(this._movePopSettleT);
      this._movePopSettleT = setTimeout(() => {
        if (this.movePathMenu) this._fitAddPop("movePathList");
      }, MOVE_POP_SETTLE_MS);
    },
    moveApplyPath(p) {
      // 点选候选 = 只回填 + 收面板, **不提交**(2026-10-29 用户报障「点选项就移动」): 真正移动只由
      // 「设定位置」按钮或手输回车发起, 与添加种子 pickAddPath 同口径(那边点选也只回填)。
      this.movePathInput = p;
      this.movePathMenu = false;
      this.movePathHi = -1;
      clearTimeout(this._movePopSettleT);
    },
    onMovePathKeydown(e) {
      // 与 meta 分类下拉同套单点(comboKeydown, add_torrent.js): 上下循环高亮(开层即展开)。
      // 2026-10-29 起语义分两条: 有高亮项回车 = 只回填(经 moveApplyPath, 再按一次才提交);
      // 无高亮/手输回车 = 直接提交(走 onEnter 钩子, 其余四个下拉不传该钩子)。Esc 只收面板。
      this.comboKeydown({
        items: () => this.movePathOptions,
        open: () => this.movePathMenu,
        setOpen: (v) => { this.movePathMenu = v; },
        hi: () => this.movePathHi,
        setHi: (v) => { this.movePathHi = v; },
        onPick: (p) => this.moveApplyPath(p),
        enterFallback: () => { const p = (this.movePathInput || "").trim(); return p || null; },
        // 回车直接提交: 回车是明确的确认手势(不是误点), 手输路径后不该逼用户再挪鼠标
        onEnter: (p) => { this.movePathInput = p; this.movePathMenu = false; this.movePathHi = -1; this.submitMoveDialog(); },
        listRef: "movePathList",
        openOnArrow: true,
      }, e);
    },
    /* 失焦收层(与添加种子三下拉 + meta 分类同套单点 _popBlurArm, 见 pitfalls/web-ui/combobox-focusout-close:
     * 40ms 合帧守卫是必需的 —— 点字段 label(for= 转发激活)时浏览器先 blur 再把焦点转回输入框,
     * 同步收层 = 关了又开; 焦点真回来由 openMovePathMenu 撤销。收层前问 _popBlurShouldHold(add_torrent.js 单点)。 */
    movePathBlurClose() {
      this._popBlurArm("_movePopBlurT", ["move-path"], () => {
        clearTimeout(this._movePopSettleT);
        this.movePathMenu = false;
        this.movePathHi = -1;
      });
    },
    async submitMoveDialog() {
      if (this.moveBusy) return;
      const location = String(this.movePathInput || "").trim();
      if (!location) {
        this.toast("路径不能为空: 请填写新的保存位置", "warn");
        return;
      }
      const post = (confirm) => {
        const body = confirm ? { location, confirm: true } : { location };
        return this.moveSingleHash
          ? this._editPost(this.moveSingleHash, "location", body, "移动")
          : this._bulkEditPost(this.moveTargets, "location", body, "批量移动");
      };
      this.moveBusy = true;
      let ok = false;
      try {
        ok = await post(false);
      } finally {
        this.moveBusy = false;
      }
      /* confirm 回路(issue 26-11-04-0734): 后端零副作用等确认 -> 先收设定位置框再开确认框。
       * 两层全屏遮罩同 z-index 且 move-dialog 在 DOM 靠后, 留着会被确认框盖住; 取消/失败则带
       * 原路径重开(可改路径再试), 确认则带 confirm=true 重发同一命令。 */
      if (ok === "confirm") {
        const receipt = this._pendingRelocateConfirm;
        this._pendingRelocateConfirm = null;
        this.moveOpen = false;
        const reopen = () => this.openMoveDialog(this.moveTargets, this.moveScope, this.moveSingleHash, location);
        if (!(await this._relocateConfirmGate(receipt))) {
          reopen();
          return;
        }
        this.moveBusy = true;
        let final = false;
        try {
          final = await post(true);
        } finally {
          this.moveBusy = false;
        }
        if (final === true) return;  // 成功: 框已收, 成功 toast 由投递点按真实回执给
        if (final === "confirm") this.toast("迁移未发起: 后端仍在等确认(未执行任何改动)", "warn", 8000);
        reopen();
        return;
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
          this.toast("限速值无效: 需为非负数字(KiB/s)", "warn");
          return;
        }
        body[key] = Math.round(this.kibToBytes(n));  // KiB/s 转 bytes/s; 0 原样传(qB 语义 = 不限)
      }
      if (!Object.keys(body).length) {
        this.toast("未作修改: 输入与当前值一致", "ok", 2000);
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
        /* 整组迁移命中 confirm: 同 _editPost, 返回 "confirm" 交 submitMoveDialog 二次确认后重发 */
        if (r.ok && action === "location" && this._relocateConfirmCount(r) > 0) {
          this._pendingRelocateConfirm = r;
          return "confirm";
        }
        if (r.ok) this.toast(this._relocateDoneText(r, `${okText}(${groupKeys.length + memberHashes.length} 个目标)`), "ok", 2500);
        else this.toast(`${okText}失败: ${r.error}`, "error", 8000);
        return r.ok;
      } catch (e) {
        if (!e.auth) this.toast(`${okText}命令发送失败: ` + e.message, "error");
        return false;
      }
    },
    /* 重命名…: 种子显示名(不改磁盘文件名) -> POST rename */
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
        this.toast("名称不能为空: 请输入新的显示名", "warn");
        return;
      }
      /* S1 重命名乐观补丁(计划 26-10-30-0610): 对话框确认后、POST 之前把新名贴上行与抽屉。
       * 覆盖面(决策 D3): _forEachRow 三数组(torrents/singles/组成员)+ 抽屉 detail;
       * 头部标题(drawerTitle)经 memberByHash 自动跟随 —— memberByHash 的值与三数组是
       * **同一批对象引用**, 补丁落行即落索引, 无需(也不得)另写一份。
       * 回执链沿用 _editPost: ok 转 hold(值覆盖保持到快照 name 同意, 不弹回),
       * error / 发送异常 / 等待超时都返回 false -> resolveOptimistic(false) 回滚原名;
       * 3s 无回执由 _expirePending 兜底回滚, 不留假状态。
       * 回滚面对称覆盖抽屉 detail(_syncDrawerRollback, issue 26-10-30-0818): 贴补丁时写了
       * detail.name, 失败/超时两条回滚出口都必须把它还原, 否则抽屉标题回落分支停留新名直到重开。 */
      const prevDetailName = (this.drawer.open && this.drawer.hash === hash && this.drawer.detail)
        ? this.drawer.detail.name : null;
      this.applyOptimisticPatch([hash], "rename", { name: res.name });
      if (prevDetailName !== null) {
        this.drawer.detail.name = res.name;
        /* hash 不在当前视图三数组时 applyOptimisticPatch 采不到 prev, detail 是该 hash 唯一的
         * 旧名落点 —— 回填进 op.prev 让失败/超时回滚仍有原名可退(issue 26-10-30-0818);
         * 行在视图时 prev.name 已采到真值, 不覆盖。 */
        const op = this.pendingOps[hash];
        if (op && op.prev.name === undefined) op.prev.name = prevDetailName;
      }
      const ok = await this._editPost(hash, "rename", { name: res.name }, "已重命名");
      this.resolveOptimistic([hash], ok);
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
