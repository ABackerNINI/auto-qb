/* auto-qb WEB UI · 种子转移交互流(计划 26-10-31-0306 W4 前半/T6)
 *
 * 分工:
 *   本文件              转移交互的**触发单点**: 菜单读侧(启用目标列表) + 触发钩子 transferOpen
 *   ctx_menu.js         「转移到」父项注册(kind:"submenu" + subName:"transfer", 四支各一项,
 *                       布局可经 web.ctx_menu 定制 —— 与其它菜单项同一套注册/合并/渲染体系)
 *   tpl/ctx-menus.html  submenu 骨架(父项/子项骨架各一份, 四支与「更多操作」共用)
 *   transfer_targets.js 设置页目标编辑器(T5, 写侧) —— 本文件只读配置, 不写树
 *
 * 读侧数据(菜单子项 = config.web.transfer.targets 中 enabled=true 的目标, D5):
 *   GET /api/config 现拉, 缓存进 trTargets(state.js, 整表替换) —— 菜单渲染只读缓存:
 *     ① 登录后预拉一次(lifecycle.js / auth.js 的 loadWebFlags 调用点旁边);
 *     ② 设置页保存成功后重拉(config_editor.js cfgSave, 与 loadWebFlags 同节奏);
 *     ③ 展开「转移到」子面板时重拉(menu.js openSub 钩子, 收窄外部改配置的陈旧窗)。
 *   三处都只**刷新缓存**, 渲染永远读 trTargets; 拉取失败保持上次缓存(菜单是瞬态浮层,
 *   不 toast 不打断, 下次展开再试)。目标按 name 寻址(与 POST /api/transfer/run 的
 *   target_id 同口径, 也与 ttTest 一致) —— 无名/未启用的目标不进菜单。
 *
 * 触发钩子(T7 接口, 本任务只留占位):
 *   transferOpen(targetId, hashes) —— 确认弹窗四段式(预检 -> 明细 -> 执行 -> 结算, 参照
 *   delete_flow.js)由 T7 在本方法内实现; 菜单与未来入口一律只把 (target_id, hashes) 交到
 *   这里, 不自带任何弹窗/预检/执行逻辑(范围守恒: T6 只做菜单, 弹窗是 T7)。
 *
 * !装载序: 三份 index.html 清单里本文件排在 transfer_targets.js 之后、app.js 之前(app.js
 *   末尾 app.mixin 注入, 启动时要读 window.AQB_*)。
 * !与其它 mixin 同款: 方法名是全局命名空间(跨 mixin 重名会被静默合并盖掉且不报错,
 *   _scan_mixin_wiring 钉这种形态) —— 本文件方法全走 transfer 与 ctxTransfer 前缀。
 */
window.AQB_TRANSFER_FLOW = {
  methods: {
    /* ---------------------------------------------------------- 读侧缓存 */
    /* GET /api/config -> web.transfer.targets 缓存进 trTargets(整表替换, 失败保持旧缓存)。
     * 走配置树而非 /api/webui/flags: targets 是完整配置结构且会随设置页保存变化, 与
     * transfer_targets.js::ttList 同一份真值(磁盘树), 不另造下发通道。 */
    async transferTargetsReload() {
      try {
        const conf = await this.api("/api/config");
        const config = conf && conf.tree && conf.tree.config ? conf.tree.config : {};
        const web = config.web && typeof config.web === "object" ? config.web : {};
        const transfer = web.transfer && typeof web.transfer === "object" ? web.transfer : {};
        this.trTargets = Array.isArray(transfer.targets) ? transfer.targets : [];
      } catch (e) {
        /* 保持上次缓存: 不打断菜单(下次展开再试) */
      }
    },
    /* 「转移到」子面板的子项(注册表 ctxRenderLayer 经 vm 调用; **恒返回 >= 1 项** ——
     * 无启用目标时给空态灰项「未配置目标, 去设置」, 子面板永不空)。子项形状与注册表
     * 渲染项同构(id/kind/label/note/icon/cls/gated/title/act/level), 走同一条子项骨架。 */
    ctxTransferMenuItems() {
      const hashes = this.ctxTransferHashes();
      const items = [];
      for (const t of this.trTargets || []) {
        const name = String((t && t.name) || "").trim();
        if (!name || !this.cfgTruthy(t && t.enabled)) continue;
        items.push({
          id: "transfer:" + name,
          kind: "item",
          label: name,
          note: "",
          icon: { cls: "", use: "#i-hdd" },
          cls: "",
          gated: false,
          title: "",
          act: (vm) => vm.transferOpen(name, hashes),
          level: 1,
        });
      }
      if (!items.length) {
        items.push({
          id: "transfer-empty",
          kind: "item",
          label: "未配置目标, 去设置",
          note: "",
          icon: { cls: "", use: "#i-settings" },
          cls: "",
          gated: true,  // is-gated 灰态(样式诉求), 但仍可点: 点击跳设置卡
          title: "",
          act: (vm) => vm.ctxTransferGoSettings(),
          level: 1,
        });
      }
      return items;
    },
    /* 当前菜单作用对象的 hash 全集 —— 四支统一走作用域单点 selection.js::_ctxScope:
     * multi = 选中集(组 key 按成员闭包展开) / episode = menu.episode.hashes /
     * member = menu.hash / group = 该组成员闭包; D5「选中集优先, 否则整组成员」的语义
     * 由 _scopeResolve 承担, 这里不做第二套判据。菜单渲染时求值 = 开层快照(D5)。
     * !closure 是去重后的 hash 全集(组 key 的成员已展开), 正是 /api/transfer/run 的
     *   hashes[] 口径 —— 不送组 key(后端只认 hash)。 */
    ctxTransferHashes() {
      const d = this._ctxScope();
      return d && d.closure ? Array.from(d.closure) : [];
    },
    /* 空态灰项: 收菜单 -> 进设置页 -> 落「WebUI」卡(现有导航机制 openSettings + hubGo) */
    ctxTransferGoSettings() {
      this.menu.visible = false;
      this.openSettings().then(() => this.hubGo("webui"));
    },

    /* ---------------------------------------------------------- 触发钩子(T7) */
    transferOpen(targetId, hashes) {
      /* T7 占位(计划 26-10-31-0306 W4 后半): 确认弹窗四段式(预检 -> 明细 -> 执行 ->
       * 结算, 参照 shared/delete_flow.js)在这里实现。入口只交 (target_id, hashes),
       * 弹窗/预检/执行逻辑一律不进菜单代码。本任务(T6)是明确的空实现: 静默占位。 */
      void targetId;
      void hashes;
    },
  },
};
