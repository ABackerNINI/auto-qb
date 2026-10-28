/* auto-qb WEB UI · 添加种子弹窗(分类标签联动/目录浏览/文件与链接提交/全局拖拽进料 DND-01)
 *
 * app.js 按域拆分出的片段(2026-09-20)。约定与 config_editor.js / config_rules.js 同一范式:
 * 挂到 window.AQB_ADD, 由 app.js 末尾 app.mixin(window.AQB_ADD) 注入同一个 Vue 实例 ——
 * 方法体里的 this 仍是那个组件实例, 跨模块互调与拆分前完全等价。
 *
 * !本文件在 HTML 里必须排在 app.js **之前**(app.js 末尾要读 window.AQB_ADD);
 *   用到的列模型常量(TABLE_COLUMNS / MIN_COL_PX / STATE_RANK …)仍单点定义在 app.js 顶部。
 */

/* ---- 添加种子三候选「最近使用」排序的单点(2026-10-09) ----
 * 需求: 保存路径/分类/标签三个候选下拉按「最近使用」排序 —— 最近用过的排前面, 省得每次翻找。
 * 口径(定案 = 由种子记录派生, 不新增存储): 「最近使用」= 该值下最近一次被种子使用的时间,
 * 即**取数行**(跨视图自取数, 见 _addRecencyRows)里属该值的种子 added_on 的最大值(见 _addRecencyMaps)。
 * 取舍: 与候选集同源(候选集本就派生自 store/qB), 故零后端改动、零新请求、零新增持久化,
 * 多端天然一致且不受「清站点数据」影响; 代价是程序按规则自动赋的分类/标签也会计入「使用」。
 * 排序规则: 时间降序 -> 从未使用过(时间 0)落末尾 -> 同时间按字母序(localeCompare)。
 * 表为空/值缺失一律落字母序, 与旧行为逐字一致 ⇒ 候选未到位时零观感差异。
 * 纯函数(不改入参): 与 _addNormPath 同在模块顶层, 供 node 单测探针直接调用。 */
function _addOrderByRecent(options, recency) {
  return (options || []).slice().sort((a, b) => {
    const tb = (recency && recency.get(b)) || 0;
    const ta = (recency && recency.get(a)) || 0;
    if (ta !== tb) return tb - ta;
    return a.localeCompare(b);
  });
}

/* 路径归一(与后端 infra/utils.path_normalize 同口径): 反斜杠转正斜杠 + 压缩重复斜杠, 首尾斜杠保留。
 * 必要性: /api/paths 返回的是**已归一**路径, 而 SEED_ITEM 的 save_path 是 qB **原文** ——
 * 两侧不同径则时间表恒不命中, 功能静默退化成纯字母序(不报错、不白屏, 只是"排序没生效")。 */
function _addNormPath(p) {
  return String(p == null ? "" : p).replace(/\\/g, "/").replace(/\/{2,}/g, "/");
}

/* combobox 失焦收层的合帧窗(毫秒): 焦点离开与 label 转发回焦之间隔着整段按住时长
 * (人手 80~150ms), 同步收层必被回焦打断 = 下拉闪烁; 挂一个合帧定时器等"焦点真离开"。
 * 单点常量 —— 收敛前 addPopBlurClose/metaCatBlurClose/movePathBlurClose 三处各写
 * 一个 40(issue 26-10-20-2230 R21-A-05), 改策略要三处同改。 */
const COMBO_BLUR_CLOSE_MS = 40;

window.AQB_ADD = {
  /* DND-01: 全局拖拽监听挂 window(照 config_hub 的钩子先例); _dragDepth 非响应式(只驱动
   * addDragOver 布尔, 不进 data 免依赖追踪)。remove 与 add 引用同一 method 实例, 严格对称。 */
  mounted() {
    this._dragDepth = 0;
    window.addEventListener("dragenter", this._addDragEnter);
    window.addEventListener("dragover", this._addDragOver);
    window.addEventListener("dragleave", this._addDragLeave);
    window.addEventListener("drop", this._addDragDrop);
    /* 四轮加固(2026-10-04): 失焦收层的 JS 侧单点守卫, 不依赖模板 @mousedown.prevent 是否到达浏览器。
     * capture 记录最近一次 mousedown 落点是不是「label[for]」(先于一切 stopPropagation) ——
     * addPopBlurClose / metaCatBlurClose 的 40ms 合帧定时器收层前先问 _popBlurShouldHold:
     * 本族 label 的转发 click 仍在途(人手按住 80~150ms > 40ms 窗)或焦点已回本族输入框 → 跳过收层,
     * 根除「按住期收层 → 松手转发回焦重开 = 闪烁」。模板修饰符正常时 mousedown 已被 prevent
     * (焦点不掉, 定时器根本不武装), 本记录器是纯兜底 —— 兜修饰符缺位的任何形态: 旧模板残留在
     * 长开页签(修复后不刷新页面就继续用)、未来模板回归、个别浏览器 label-blur 不可防。 */
    this._popLabelDownRecorder = (e) => {
      const el = e.target && e.target.closest ? e.target.closest("label[for]") : null;
      this._popLabelDown = el ? { t: performance.now(), forId: el.getAttribute("for") || "" } : null;
    };
    window.addEventListener("mousedown", this._popLabelDownRecorder, { capture: true });
  },
  unmounted() {
    window.removeEventListener("dragenter", this._addDragEnter);
    window.removeEventListener("dragover", this._addDragOver);
    window.removeEventListener("dragleave", this._addDragLeave);
    window.removeEventListener("drop", this._addDragDrop);
    if (this._popLabelDownRecorder) {
      window.removeEventListener("mousedown", this._popLabelDownRecorder, { capture: true });
      this._popLabelDownRecorder = null;
    }
  },
  methods: {
    /* ---------------- 添加种子对话框(R1B): 提交走 this.api() JSON —— .torrent 读取为 base64 随 files_b64 上送
     * (口径同 submitAddTorrent 内注释与 state.js addFiles; this.api() 恒置 application/json, 见 auth.js _request);
     * 回执仍复用 waitCmd 轮询 /api/cmd/{id} ---------------- */
    openAddTorrent() {
      this.addFiles = [];
      this.addUrls = "";
      this.addShowUrls = false;  // DLG-03: 链接输入框默认收起
      this.addSavePath = "";
      this.addCategory = "";
      this.addTags = "";
      this.addStart = false;  // 默认不勾 = paused 添加
      this.addSkipCheck = false;
      this.addSequential = false;
      this.addFirstLast = false;
      this.addTmm = false;
      this.addCatMenu = false;
      this.addTagMenu = false;
      this.addCatHi = -1;
      this.addTagHi = -1;
      this.addPathPop = false;
      this.addPathHi = -1;
      this.addOpen = true;
      this.loadAddOptions();  // DLG-03/04: 异步拉取分类/标签/历史路径候选, 不阻塞窗口打开
    },
    closeAddTorrent() {
      if (this.addSubmitting) return;  // 回执等待期不允许误关
      this.addOpen = false;
      this.dirBrowse.open = false;  // R10-11: 目录浏览器是添加窗口的子层, 一并关闭
    },
    async loadAddOptions() {
      // DLG-03/04: 并行拉取分类/标签/历史路径候选; 单个端点失败静默降级为空候选(不阻塞窗口)
      const safe = async (url, pick) => {
        try {
          return pick(await this.api(url));
        } catch (e) {
          return [];
        }
      };
      const [cats, tags, paths] = await Promise.all([
        safe("/api/categories", (r) => Object.keys(r.categories || {})),
        // exclude_auto=1: 剔除程序自动维护的标签(站点名/HR/集数等, 判定在后端), 候选只留用户可挑的
        safe("/api/tags?exclude_auto=1", (r) => r.tags || []),
        safe("/api/paths", (r) => r.paths || []),
      ]);
      if (this.addOpen) {  // 仅窗口仍开着时回填(慢响应不得污染下一次打开)
        // 「最近使用」排序(2026-10-09): 三候选一律按最近一次被种子使用的时间降序, 未用过按字母序。
        // 排序在落袋处单点做(端点只供候选集, 不承担展示序) —— 三个 pick 不再各自 .sort()。
        const recent = this._addRecencyMaps();
        this.addCatOptions = _addOrderByRecent(cats, recent.cat);
        this.addTagOptions = _addOrderByRecent(tags, recent.tag);
        this.addPathOptions = _addOrderByRecent(paths, recent.path);
      }
    },
    /* 三候选「最近使用」的取数行 —— **跨视图自取数**(与 filters.js::facetRows 同族):
     * 添加种子入口是顶栏常驻, 而 state 的阵列按 viewMode 裁剪(VIEW_ARRAYS: 辅种页只回
     * groups + singles、追剧页回 shows + groups + singles、种子页只回 torrents)⇒ 只读
     * this.torrents 时, 用户在**默认的辅种页**开窗会拿到空表, 排序**静默退化**成纯字母序
     * (不报错不白屏, 2026-10-09 e2e 首跑实测抓到)。判据同 pitfalls/web-ui/contract-api.md
     * 「跨视图的常驻消费者不能依赖按视图裁剪的阵列」。
     * 两分支各自完整: 种子页平铺 / 其余(groups∪singles, 追剧页 VIEW_ARRAYS 亦含 groups)。 */
    _addRecencyRows() {
      if (this.viewMode === "torrents" && this.torrents.length) return this.torrents;
      const rows = [...(this.singles || [])];
      for (const g of this.decoratedGroups || []) {
        for (const m of g.members || []) rows.push(m);
      }
      return rows;
    },
    /* 三候选的「最近使用」时间表: 遍历取数行现算 —— 分类/保存路径取单值, 标签取数组逐项,
     * 每值取所属种子 added_on 的最大值。纯读快照(不请求/不投命令/无副作用), 表为空时排序
     * 退化为纯字母序(见 _addOrderByRecent 兜底)。 */
    _addRecencyMaps() {
      const cat = new Map(), tag = new Map(), path = new Map();
      const bump = (m, k, ts) => {
        if (!k || !ts) return;  // 空值不构成候选; added_on 缺失(0)不参与
        if (ts > (m.get(k) || 0)) m.set(k, ts);
      };
      for (const r of this._addRecencyRows()) {
        if (!r) continue;
        const ts = r.added_on || 0;
        bump(cat, r.category, ts);
        bump(path, _addNormPath(r.save_path), ts);
        const tlist = Array.isArray(r.tags) ? r.tags : String(r.tags || "").split(",");
        for (const t of tlist) bump(tag, String(t).trim(), ts);
      }
      return { cat, tag, path };
    },
    escAddTorrent() {
      // Esc 逐层退栈(FIX-07)接入: 对话框内浮层(目录浏览器 → 分类/标签下拉 → 位置面板)先收起, 再关对话框
      if (this.dirBrowse.open) {
        this.closeDirBrowse();
      } else if (this.addCatMenu || this.addTagMenu) {
        this.addCatMenu = false;
        this.addTagMenu = false;
        this.addCatHi = -1;
        this.addTagHi = -1;
      } else if (this.addPathPop) {
        this.addPathPop = false;
        this.addPathHi = -1;
      } else {
        this.closeAddTorrent();
      }
    },
    toggleAddUrls() {
      this.addShowUrls = !this.addShowUrls;  // 收起不清空已输入链接, 再展开仍可继续编辑
    },
    /* 三浮层互斥单点(26-10-04-0130): 开任一浮层前收掉其余两个, 互斥必须双向 —— 单向写法
     * (只 openAddPathPop 收 cat/tag)会让路径面板与下拉同悬, 面板还盖住相邻字段 label 的点击。
     * kind 是要保留的那个; 收层带 Hi 复位, 与 Esc 退栈/失焦收层的收法一致。 */
    closeAddPopsExcept(kind) {
      if (kind !== "cat") {
        this.addCatMenu = false;
        this.addCatHi = -1;
      }
      if (kind !== "tag") {
        this.addTagMenu = false;
        this.addTagHi = -1;
      }
      if (kind !== "path") {
        this.addPathPop = false;
        this.addPathHi = -1;
      }
    },
    openAddCatMenu() {
      this._popBlurCancel("_addPopBlurT");  // 焦点回到本输入框(label 转发/重新点入)时撤销挂起的失焦收层, 菜单不闪
      this.closeAddPopsExcept("cat");
      this.addCatHi = -1;
      this.addCatMouseAt = null;  // 开层复位悬停门限坐标(下次打开首个动作不被旧坐标误挡)
      this.addCatMenu = true;
    },
    openAddTagMenu() {
      this._popBlurCancel("_addPopBlurT");
      this.closeAddPopsExcept("tag");
      this.addTagHi = -1;
      this.addTagMouseAt = null;  // 同上
      this.addTagMenu = true;
    },
    addCatFiltered() {
      const q = this.addCategory.trim().toLowerCase();
      if (!q) return this.addCatOptions;
      return this.addCatOptions.filter((c) => c.toLowerCase().includes(q));
    },
    addTagCurrent() {
      const m = this.addTags.match(/([^,]*)$/);  // 从简: 只按最后一个逗号后的片段过滤
      return (m ? m[1] : "").trim();
    },
    addTagFiltered() {
      const q = this.addTagCurrent().toLowerCase();
      const picked = new Set(this.addTags.split(",").map((t) => t.trim()).filter(Boolean));
      return this.addTagOptions.filter((t) => !picked.has(t) && (!q || t.toLowerCase().includes(q)));
    },
    pickAddCat(name) {
      this.addCategory = name;
      this.addCatMenu = false;
      this.addCatHi = -1;
    },
    /* 输入框内嵌清空(x, 2026-10-03 报障: 保存路径/分类/标签三个 combobox 没有清除入口,
     * 改一次值只能手动全选再删)。模板侧按钮必须 @mousedown.prevent —— 不拦默认动作按钮会抢走
     * 焦点, 输入框走 addPopBlurClose 把下拉收掉, 清完想接着挑候选就得多点一次; 拦掉后焦点
     * 留在输入框, 下拉保持展开(清空 = 空过滤词 = 全量候选, 由下面的 watcher 重限高)。 */
    clearAddField(kind) {
      if (kind === "path") {
        this.addSavePath = "";
        this.addPathHi = -1;
      } else if (kind === "cat") {
        this.addCategory = "";
        this.addCatHi = -1;
      } else if (kind === "tag") {
        this.addTags = "";
        this.addTagHi = -1;
      }
    },
    pickAddTag(tag) {
      const parts = this.addTags.split(",").map((t) => t.trim()).filter(Boolean);
      if (!parts.includes(tag)) parts.push(tag);
      this.addTags = parts.join(", ") + ", ";  // 尾随逗号: 便于继续挑选下一个
      this.addTagMenu = false;
      this.addTagHi = -1;
    },
    onAddCatKeydown(e) {
      this.comboKeydown({
        items: () => this.addCatFiltered(),
        open: () => this.addCatMenu,
        setOpen: (v) => { this.addCatMenu = v; },
        hi: () => this.addCatHi,
        setHi: (v) => { this.addCatHi = v; },
        onPick: (c) => this.pickAddCat(c),
        listRef: "addCatList",
        openOnArrow: true,  // 关层时方向键先开层(与 meta/move 同; 保存路径面板相反)
      }, e);
    },
    onAddTagKeydown(e) {
      this.comboKeydown({
        items: () => this.addTagFiltered(),
        open: () => this.addTagMenu,
        setOpen: (v) => { this.addTagMenu = v; },
        hi: () => this.addTagHi,
        setHi: (v) => { this.addTagHi = v; },
        onPick: (t) => this.pickAddTag(t),
        listRef: "addTagList",
        openOnArrow: true,
      }, e);
    },
    /* 悬停接管(治「上下键选中项闪烁/Enter 选错」2026-09-29, issue 26-09-29-2142; 同款: config_hub.hubTrackerHoverIdx):
     * 分类/标签/编辑分类三处下拉的悬停高亮原是 @mouseenter 直写键盘活动项 —— 光标静止停在列表上
     * 用 ↑↓ 选择时, 行滚动/DOM 变更后浏览器给静止光标补发合成 hover 事件, 活动项被拽回光标行
     * (改前真机实测: ↓×16 两次被拽回, Enter 选中光标行 cat-06 而非键盘到达的 cat-16 —— 不止闪烁, 实选错)。
     * 改为 @mousemove + 位移门限: 位移 <3px(静止 / 合成事件)不接管, 真实移动才把活动项交给光标;
     * 门限坐标按下拉分存(state.js *MouseAt), 开层单点复位(openAddCatMenu/openAddTagMenu/openMetaCatMenu) */
    comboHoverIdx(kind, i, ev) {
      const atKey = kind === "cat" ? "addCatMouseAt" : kind === "tag" ? "addTagMouseAt" : kind === "move" ? "movePathMouseAt" : "metaCatMouseAt";
      const hiKey = kind === "cat" ? "addCatHi" : kind === "tag" ? "addTagHi" : kind === "move" ? "movePathHi" : "metaCatHi";
      const x = ev.clientX, y = ev.clientY, at = this[atKey];
      if (at) {
        const dx = x - at.x, dy = y - at.y;
        if (dx * dx + dy * dy < 9) return; // <3px: 光标静止 / 合成事件, 不接管
      }
      this[atKey] = { x, y };
      this[hiKey] = i;
    },
    /* ---------------- combobox 键盘导航单点(收敛 issue 26-10-20-2230, R20-B-05/C-12 + R21-A-04) ----------------
     * 五个自绘下拉(添加窗口 保存路径/分类/标签 · 设定位置 movePath · 编辑弹窗 metaCat)的键盘
     * 导航原是五份同骨架实现(IME 守卫 -> ↑↓ 取模环绕 -> Enter 选中 -> Esc 只收面板), 分歧只在
     * 选项上; 且五份里只有站点搜索 hubTrackerKeydown(另一族, 第 6 变体)带 IME 组词守卫, 其余
     * 四份缺 —— 中文输入法组词期间方向键/回车会被劫持(路径输入多为 ASCII 而未暴露, R21-A-04 ③)。
     * 收敛为单点 + 守卫恒开; 第 6 变体(settings.html 站点搜索层)有自己的类族/滚动跟随/无 Esc
     * 语义且守阵独立钉着, 不并本单点。
     * ctx 由调用方注入, 全部经 getter 现读现取(不用闭包快照, 根数据随时在变):
     *   items()        候选数组(过滤产物; 路径/move 直传数组)
     *   open()/setOpen(v)   hi()/setHi(v)   面板开合与高亮索引(根数据读写)
     *   onPick(item)   选中候选(点选与回车共用同一个回调)
     *   enterFallback() Enter 无高亮项时的回退值(null = 不回退; meta = 输入框文本,
     *                   move = 修剪后的输入框文本)
     *   onEnter(item)  **可选**: 回退分支的落地回调(缺省 = onPick)。2026-10-29 设定位置点选改为
     *                   「只回填」后, 手输回车仍需直接提交 —— 只有 move 传本钩子, 其余四处不传。
     *   listRef         ↑↓ 后滚动跟随的 $refs 名(null = 不跟随)
     *   openOnArrow     关层时方向键是否先开层(false = 未开时不接管任何键, 保存路径面板) */
    comboKeydown(ctx, ev) {
      if (ev.isComposing || ev.keyCode === 229) return;  // IME 组词期不劫持(与 shortcuts/config_hub 同口径)
      const items = ctx.items() || [];
      const n = items.length;
      const down = ev.key === "ArrowDown", up = ev.key === "ArrowUp";
      if ((down || up) && n) {
        if (!ctx.open() && !ctx.openOnArrow) return;
        ev.preventDefault();
        if (!ctx.open()) {
          ctx.setOpen(true);
          ctx.setHi(down ? -1 : 0);
        }
        ctx.setHi((ctx.hi() + (down ? 1 : -1) + n) % n);
        if (ctx.listRef) this._hiScroll(ctx.listRef);
      } else if (ev.key === "Enter") {
        const hi = ctx.hi();
        if (ctx.open() && hi >= 0 && items[hi]) {
          ev.preventDefault();
          ctx.onPick(items[hi]);
        } else if (ctx.enterFallback) {
          ev.preventDefault();  // meta/move: 菜单未开或无高亮也吃掉回车(提交当前输入), 与收敛前逐字一致
          const v = ctx.enterFallback();
          if (v != null && v !== "") (ctx.onEnter || ctx.onPick)(v);
        }
      } else if (ev.key === "Escape" && ctx.open()) {
        ev.stopPropagation();  // 只收面板, 不关对话框(冒泡交 lifecycle 的 Esc 退栈链)
        ctx.setOpen(false);
        ctx.setHi(-1);
      }
    },
    /* ---------------- R10-11 路径选择器(服务端目录浏览) ----------------
     * “选择位置”不再只是自绘下拉: 由服务端给真实目录树(浏览器物理上拿不到绝对路径)。
     * 只列目录 + 可上溯到允许根 + 可新建文件夹; 选中后回填输入框(绝对路径)。
     * 安全边界全部在后端(GET /api/fs/dirs, POST /api/fs/mkdir)。 */
    async openDirBrowse() {
      this.addCatMenu = false;
      this.addTagMenu = false;
      this.addPathPop = false;
      this.dirBrowse = {
        open: true, path: "", parent: "", roots: [], dirs: [],
        loading: true, error: "", newName: "", busy: false,
      };
      await this.loadDir("");
    },
    closeDirBrowse() {
      this.dirBrowse.open = false;
    },
    async loadDir(path) {
      // 请求代际守卫(path 戳, 同 drawer.js _drawerStale 收口式): 发请求即记目标路径,
      // 落袋前比对 —— 快速连点目录 A→B 时 A 的慢响应后到不得把 B 的列表覆写回 A
      // (issue 26-10-06-0028 F2-03)
      const reqPath = path || "";
      this._dirReqPath = reqPath;
      this.dirBrowse.loading = true;
      this.dirBrowse.error = "";
      try {
        const r = await this.api("/api/fs/dirs?path=" + encodeURIComponent(reqPath));
        if (this._dirReqPath !== reqPath) return;  // 已有更新的目录请求: 旧响应丢弃
        this.dirBrowse.path = r.path || "";
        this.dirBrowse.parent = r.parent || "";
        this.dirBrowse.roots = r.roots || [];
        this.dirBrowse.dirs = r.dirs || [];
      } catch (e) {
        if (this._dirReqPath !== reqPath) return;
        if (!e.auth) this.dirBrowse.error = e.message || "读取目录失败";
      } finally {
        // 过期请求不动 loading 态(新在途请求持有它), 免得闪一帧"加载完"假象
        if (this._dirReqPath === reqPath) this.dirBrowse.loading = false;
      }
    },
    dirEnter(p) {
      this.loadDir(p);
    },
    dirUp() {
      if (this.dirBrowse.parent) this.loadDir(this.dirBrowse.parent);
    },
    async dirMkdir() {
      const name = (this.dirBrowse.newName || "").trim();
      if (!name || this.dirBrowse.busy) return;
      this.dirBrowse.busy = true;
      try {
        const r = await this.api("/api/fs/mkdir", {
          method: "POST",
          body: JSON.stringify({ path: this.dirBrowse.path, name }),
        });
        this.dirBrowse.newName = "";
        await this.loadDir(r.path || this.dirBrowse.path);
        this.toast(`已新建文件夹: ${r.created}`, "ok", 3000);
      } catch (e) {
        if (!e.auth) this.toast("新建文件夹失败: " + e.message, "error", 8000);
      } finally {
        this.dirBrowse.busy = false;
      }
    },
    /* 选定当前目录(首层/未进入具体目录时落到首个允许根) */
    dirPick() {
      const p = this.dirBrowse.path || (this.dirBrowse.dirs[0] && this.dirBrowse.dirs[0].path) || "";
      if (!p) {
        this.toast("请先选择一个目录", "warn");
        return;
      }
      this.addSavePath = p;
      this.dirBrowse.open = false;
    },
    /* FX-17: 输入框聚焦即展开候选面板。旧实现写在模板上的 @focus 是 `addPathPop = false`
     * —— 聚焦反而把面板关掉(为让位于原生 datalist 的建议浮层), 而那个浮层会自行超时消失,
     * 于是表现为"下拉 2 秒后不见了"。datalist 退役后聚焦 = 展开。 */
    openAddPathPop() {
      this._popBlurCancel("_addPopBlurT");
      this.closeAddPopsExcept("path");
      this.addPathHi = this.addPathOptions.indexOf(this.addSavePath.trim());
      this.addPathPop = true;
      this._hiScroll("addPathList");
    },
    /* ---------------- 失焦收层单点(收敛 R20-B-06 + R21-A-05: 三处 40ms 合帧各写一遍) ----------------
     * 收层主判据 = 输入框 @focusout(模板接线), window click(lifecycle.js)降级为兜底:
     * 点空白/点别的字段/Tab 走 focusout 必然触发; 点字段 label(for= 转发激活)不触发重开闪烁。
     * ⚠ 不能在 focusout 里同步收 —— 点 label 时 mousedown 默认动作先把已聚焦的输入框 blur 掉,
     * label 的 click 默认动作才把焦点转回, 这两步之间隔着**整段按住时长**(人手 80~150ms,
     * 必 > 合帧窗); 同步收层 = 关了又开, leave 过渡被打断 = 用户看到的"下拉闪烁再现"
     * (2026-10-03 报障, 三修才坐实, 完整判别见 pitfalls/web-ui/combobox-focusout-close)。
     * 挂合帧定时器: 焦点真离开(点空白/别的字段/Tab)下一拍收层; 焦点回来了(开层方法先跑
     * _popBlurCancel)则撤销, 菜单全程不闪。定时窗内 window click 兜底照常生效。
     * ⚠ label 一侧的 blur 由模板 @mousedown.prevent 根除(焦点不掉, 本定时器不武装) —— 合帧
     * 窗只兜点空白/Tab 这类瞬时焦点迁移, 不许把 label 的长按间隙算进来(2026-10-04 三修)。
     * ⚠ 四轮加固: 收层前问 _popBlurShouldHold(记录器见 mounted 注释) —— 焦点已回本族输入框
     * 或本族 label 转发 click 仍在途时跳过收层; 模板修饰符缺位(旧页签残留模板/未来回归)时
     * 由它独立根除闪烁, 不再依赖模板与 JS 同代到达浏览器。
     * ids = 本族输入框 id 名单; close = 收层动作(关面板 + 复位高亮)。 */
    /* 失焦收层前的守卫(记录器见 mounted 注释): 在合帧定时器**触发那刻**判定 ——
     * ①焦点已回本族输入框(转发 click 已落地 / 合成零延迟点击) → 不收, 开层方法会接手;
     * ②本族 label 的 mousedown 落在 350ms 内且焦点不在任何输入框上 = 转发 click 仍在途
     *   (人手按住中) → 不收, 等松手后 label 默认动作把焦点转回。350ms 上界防旧记录误挡
     *   后续无 mousedown 的失焦(如 Tab)。ids = 本族输入框 id(add 三字段 / meta 分类 / move)。 */
    _popBlurShouldHold(ids) {
      const ae = document.activeElement;
      if (ae && ae.id && ids.includes(ae.id)) return true;
      const rec = this._popLabelDown;
      return !!(rec && performance.now() - rec.t <= 350 && ids.includes(rec.forId));
    },
    _popBlurArm(timerKey, ids, close) {
      clearTimeout(this[timerKey]);
      this[timerKey] = setTimeout(() => {
        if (this._popBlurShouldHold(ids)) return;
        close();
      }, COMBO_BLUR_CLOSE_MS);
    },
    _popBlurCancel(timerKey) {
      clearTimeout(this[timerKey]);
    },
    addPopBlurClose() {
      this._popBlurArm("_addPopBlurT", ["ad-save-path", "ad-category", "ad-tags"], () => {
        this.addCatMenu = false;
        this.addTagMenu = false;
        this.addPathPop = false;
        this.addCatHi = -1;
        this.addTagHi = -1;
        this.addPathHi = -1;
      });
    },
    /* ---------------- 下拉限高(2026-10-03 报障: 选项过长把添加窗口撑变形) ----------------
     * .pop-menu 基础 max-height:330px 只保证菜单自身可滚, 但菜单锚在输入行下方, 输入行贴近
     * 窗口底沿时整条菜单伸出窗口外(滚动条也跟着出窗), 且绝对定位溢出会把 .add-dialog-body
     * 的 scrollHeight 撑大(窗口内容变形/多出滚动量)。开层后在同一帧量「输入行到滚动容器可见
     * 底沿」的净空, 把可滚内层(.add-pop-list 或菜单自身)限到净空内 —— 滚动条永远留在窗口里。
     * 只在开层/候选到位/过滤词变化时量一次: 菜单开着时用户再滚动窗口, 行随内容滚走, 净空只增
     * 不减会露头, 不做滚动跟随(收层重开即重新量, 复杂度不值)。meta 对话框的分类下拉同族,
     * 复用本方法(它的输入行与 .add-dialog-body 结构一致, watcher 挂在 dialogs.js)。 */
    _fitAddPop(refName) {
      this.$nextTick(() => {
        if (!this.addOpen && !this.metaOpen && !this.moveOpen) return;  // meta 对话框(标签与分类)/设定位置对话框复用同一套限高
        const inner = this.$refs[refName];
        if (!inner) return;
        const menu = inner.closest(".add-pop") || inner;
        const row = menu.closest(".add-input-row");
        const body = menu.closest(".add-dialog-body");
        if (!row || !body) return;
        const list = menu.querySelector(".add-pop-list") || menu;  // 可滚内层(路径面板=列表, 分类/标签=菜单自身)
        list.style.maxHeight = "";  // 先复位再量, 上一次的限高不许污染本次测量
        const chrome = menu.offsetHeight - list.offsetHeight;  // 面板头等固定件
        const avail = Math.floor(body.getBoundingClientRect().bottom - row.getBoundingClientRect().bottom - 10 - chrome);
        if (avail > 0 && list.offsetHeight > avail) list.style.maxHeight = `${Math.max(120, avail)}px`;
      });
    },
    pickAddPath(p) {
      this.addSavePath = p;  // 单选回填(覆盖自由输入框内容)
      this.addPathPop = false;
      this.addPathHi = -1;
    },
    onAddPathKeydown(e) {
      this.comboKeydown({
        items: () => this.addPathOptions,
        open: () => this.addPathPop,
        setOpen: (v) => { this.addPathPop = v; },
        hi: () => this.addPathHi,
        setHi: (v) => { this.addPathHi = v; },
        onPick: (p) => this.pickAddPath(p),
        listRef: "addPathList",
        openOnArrow: false,  // 保存路径面板: 未开时不接管任何键(收敛前首行早退), 与 cat/tag/meta/move 相反
      }, e);
    },
    _hiScroll(refName) {
      // 键盘高亮项滚动进可视区(block: nearest 不跳动)
      this.$nextTick(() => {
        const box = this.$refs[refName];
        if (!box) return;
        const el = box.querySelector('[data-hi="1"]');
        if (el && el.scrollIntoView) el.scrollIntoView({ block: "nearest" });
      });
    },
    onAddFilePick(event) {
      const picked = Array.from((event.target && event.target.files) || []);
      for (const f of picked) {
        // 同名同大小视为重复(同一文件二次误选); File 对象只存引用不读内容
        if (!this.addFiles.some((x) => x.name === f.name && x.size === f.size)) this.addFiles.push(f);
      }
      event.target.value = "";  // 重置原生 input, 允许再次选择同一文件补选
    },
    removeAddFile(i) {
      this.addFiles = this.addFiles.filter((_, idx) => idx !== i);
    },
    /* ---------------- DND-01 全局拖拽添加(文件 + magnet/URL 链接) ----------------
     * 监听绑在 window(两皮肤共用, 入口 = 页面任意位置); 只接管两类拖拽 ——
     * types 含 "Files"(拖文件)或 "text/uri-list"(从浏览器拖链接), 其余(页面内拖选中文本、
     * 拖纯文本进输入框)一律放行不 preventDefault, 原生行为不受影响。
     * depth 计数解决经典抖动: dragenter/leave 在子元素间交替成对触发, 归零才算真正离开。 */
    _addDragTakes(e) {
      const types = Array.from((e.dataTransfer && e.dataTransfer.types) || []);
      return types.includes("Files") || types.includes("text/uri-list");
    },
    _addDragEnter(e) {
      if (!this._addDragTakes(e)) return;
      e.preventDefault();
      this._dragDepth += 1;
      this.addDragOver = true;
    },
    _addDragOver(e) {
      if (!this._addDragTakes(e)) return;
      e.preventDefault();  // dragover 阶段也必须持续 preventDefault, drop 才被允许
      if (e.dataTransfer) e.dataTransfer.dropEffect = "copy";
    },
    _addDragLeave(e) {
      if (!this._addDragTakes(e)) return;
      this._dragDepth = Math.max(0, this._dragDepth - 1);
      if (!this._dragDepth) this.addDragOver = false;
    },
    _addDragDrop(e) {
      if (!this._addDragTakes(e)) return;
      e.preventDefault();  // 不拦 = 浏览器直接打开 .torrent / 跳转链接
      this._dragDepth = 0;
      this.addDragOver = false;
      const dt = e.dataTransfer;
      if (dt && dt.files && dt.files.length) this._addIngestFiles(dt.files);
      else this._addIngestLinks(dt);
    },
    _addIngestFiles(fileList) {
      const picks = [], ignored = [];
      for (const f of Array.from(fileList || [])) {
        if ((f.name || "").toLowerCase().endsWith(".torrent")) picks.push(f);
        else ignored.push(f);  // 含拖入的文件夹(目录条目 size=0 无扩展名), 不做递归遍历
      }
      if (!picks.length) {
        if (ignored.length) this.toast("拖入的不是 .torrent 文件, 已忽略", "warn");
        return;
      }
      if (!this.addOpen) this.openAddTorrent();  // 必须先开窗再填(openAddTorrent 会清空 addFiles)
      let added = 0;
      for (const f of picks) {
        // 与文件选择(onAddFilePick)同口径去重: 同名同大小视为重复
        if (!this.addFiles.some((x) => x.name === f.name && x.size === f.size)) {
          this.addFiles.push(f);
          added += 1;
        }
      }
      if (ignored.length) this.toast(`已忽略 ${ignored.length} 个非 .torrent 项`, "warn", 4000);
      else if (!added) this.toast("文件已在列表中", "warn", 3000);
    },
    _addIngestLinks(dt) {
      if (!dt) return;
      let text = "";
      try {
        text = dt.getData("text/uri-list") || dt.getData("text/plain") || "";
      } catch (err) {
        return;  // 受保护数据读不到就当没有
      }
      // uri-list 的标题行/注释行(# 开头)不匹配链接前缀, 按行过滤天然排除
      const lines = String(text).split(/\r?\n/).map((l) => l.trim())
        .filter((l) => /^(magnet:\?|https?:\/\/)/i.test(l));
      if (!lines.length) return;
      if (!this.addOpen) this.openAddTorrent();
      this.addShowUrls = true;  // 展开链接域让用户看见拖进来的内容; 追加不覆盖已输入
      this.addUrls = (this.addUrls.trimEnd() ? this.addUrls.trimEnd() + "\n" : "") + lines.join("\n");
    },
    addUrlCount() {
      return this.addUrls.split(/\r?\n/).filter((l) => l.trim()).length;
    },
    /* 添加落点预检(计划 26-10-18-1604 P5, 只读): 命中迁移别名作用域 / 收尾窗口时, 把
     * 「请求路径 -> 实际落点 -> 目标卷剩余」摊给用户二次确认 —— 取消 = 不提交(零副作用)。
     * 预检不可用(功能未启用 403 / 网络异常 / 判不出落点名)一律**放行**: 它只是把后果提前
     * 说清楚, 不构成闸门(执行侧闸门照旧), 不该因为预检故障挡住添加。 */
    async _relocateAddGate() {
      const savePath = this.addSavePath.trim();
      if (!savePath) return true;
      if (!this.addFiles.length && !this.addUrls.trim()) return true;
      // 落点名: 有 .torrent 时取第一个文件名去后缀; 只有链接/磁力时添加前无法预判, 跳过预检
      const name = this.addFiles.length ? String(this.addFiles[0].name || "").replace(/\.torrent$/i, "") : "";
      if (!name) return true;
      let r = null;
      try {
        const queued = await this.api("/api/relocate/precheck-add", {
          method: "POST",
          body: JSON.stringify({ save_path: savePath, name }),
        });
        const rec = await this.waitCmd(queued.cmd_id, 20000);
        r = rec.ok ? rec.truth : null;
      } catch (e) {
        if (e.auth) return false;  // 401 已由 _logout 收口
        return true;
      }
      if (!r || r.cls !== "confirm") return true;
      const rows = (r.reasons || []).map((x) => ({ icon: "#i-warn", label: "落点提示", value: x.text, wide: true }));
      rows.push({ icon: "#i-info", label: "请求路径", value: r.requested_path, wide: true });
      if (r.actual_path) rows.push({ icon: "#i-warn", label: "实际落点", value: r.actual_path, wide: true });
      if (r.volume_free != null) {
        rows.push({ icon: "#i-info", label: "目标卷剩余", value: `${Math.round(r.volume_free / (1024 ** 3))} GiB`, wide: true });
      }
      const choice = await this._openModal({
        title: "落点确认",
        body: `「${name}」的落点与请求路径不一致(该目录已在整组迁移中建了别名)。`,
        okText: "确认添加",
        cancelText: "取消",
        icon: "#i-warn",
        wide: true,
        verdict: rows,
      });
      return !!choice;
    },
    async submitAddTorrent() {
      if (!this.addCanSubmit) return;
      if (!(await this._relocateAddGate())) return;  // 落点预检: 取消则整个不提交
      // .torrent 读取为 base64 随 JSON 提交(后端解码后 bytes 内存直传 qB —— 零临时文件零新依赖)
      const filesB64 = [];
      for (const f of this.addFiles) {
        filesB64.push(
          await new Promise((resolve, reject) => {
            const reader = new FileReader();
            reader.onload = () => {
              const result = String(reader.result || "");
              resolve(result.includes(",") ? result.slice(result.indexOf(",") + 1) : result);
            };
            reader.onerror = () => reject(new Error(`无法读取文件: ${f.name}`));
            reader.readAsDataURL(f);
          })
        );
      }
      const payload = {
        files_b64: filesB64,
        urls: this.addUrls.split("\n").map((u) => u.trim()).filter(Boolean),
        save_path: this.addSavePath.trim(),
        category: this.addCategory.trim(),
        tags: this.addTags.split(",").map((t) => t.trim()).filter(Boolean),
        paused: !this.addStart,  // DLG-03: 「添加后开始」勾选 = 立即开始; 默认不勾 = paused 添加
        skip_checking: this.addSkipCheck,
        sequential: this.addSequential,
        first_last_piece_prio: this.addFirstLast,
        auto_tmm: this.addTmm,
      };
      this.addSubmitting = true;
      try {
        // JSON 提交(this.api() 恒置 Content-Type: application/json, 见 auth.js _request)
        const queued = await this.api("/api/torrents/add", { method: "POST", body: JSON.stringify(payload) });
        const r = await this.waitCmd(queued.cmd_id);
        if (r.ok) {
          this.toast("添加种子已受理, 列表稍后自动刷新", "ok", 4000);
          this.addOpen = false;
        } else if (r.status === "warn") {
          /* 部分受理(2026-10-18 报障「部分种子添加失败(已存在)时添加窗口不消失」):
           * qB 已把其中一部分加进去了(其余多为"已存在"被拒) —— 与"全部未接受"是两回事。
           * 窗口按已受理收口(关闭), 明细进 warn toast(后端文案已带"成功 N / 失败 M"计数,
           * 见 commands.py::_cmd_add_torrents 三态回执); 想补提剩下的再开窗即可。
           * 只有全拒(error)才保留窗口: 那一份文件/链接原样没进 qB, 留着改完能直接重提。 */
          this.toast(`${r.error}, 列表稍后自动刷新`, "warn", 8000);
          this.addOpen = false;
        } else {
          this.toast(`添加种子失败: ${r.error}`, "error", 8000);
        }
      } catch (e) {
        if (!e.auth) this.toast("添加种子失败: " + e.message, "error", 8000);
      } finally {
        this.addSubmitting = false;
      }
    },
  },
  computed: {
    /* 添加种子对话框: 保存路径前缀比对已有辅种组(输入变化时轻量计数, 不发请求)。
     * 双向前缀: 输入是某组路径的父目录、或子目录, 都算同一路径树(尾部斜杠/大小写归一后比对)。 */
    addPathGroupCount() {
      const norm = (p) => (p || "").trim().replace(/[\\/]+$/, "").toLowerCase();
      const input = norm(this.addSavePath);
      if (!input) return 0;
      let n = 0;
      for (const g of this.decoratedGroups) {
        const p = norm(g.save_path);
        if (!p) continue;
        if (p.startsWith(input) || input.startsWith(p)) n += 1;
      }
      return n;
    },
    /* 添加可提交条件: 有文件或有非空链接行, 且不在提交中 */
    addCanSubmit() {
      if (this.addSubmitting) return false;
      if (this.addFiles.length) return true;
      return this.addUrls.split(/\r?\n/).some((l) => l.trim());
    },
  },
  watch: {
    /* 下拉限高单点: 三个浮层的开层入口有四处(开层方法 / 输入 @input 直开 / 键盘 comboKeydown /
     * 目录浏览返回), 开层计时走 watcher 才不漏; 候选异步到位(loadAddOptions)会改变菜单高度,
     * 开着时也要重限。 */
    addCatMenu(v) {
      if (v) this._fitAddPop("addCatList");
    },
    addTagMenu(v) {
      if (v) this._fitAddPop("addTagList");
    },
    addPathPop(v) {
      if (v) this._fitAddPop("addPathList");
    },
    addCatOptions() {
      if (this.addCatMenu) this._fitAddPop("addCatList");
    },
    addTagOptions() {
      if (this.addTagMenu) this._fitAddPop("addTagList");
    },
    addPathOptions() {
      if (this.addPathPop) this._fitAddPop("addPathList");
    },
    /* 过滤词变化也要重限(2026-10-03 报障: 选中一个分类后逐字删除 -> 候选从 1 条涨回全量,
     * 下拉把窗口撑变形)。开层那一刻按**当时**的候选量算的限高不会自己更新 —— 菜单没关过,
     * addCatMenu watcher 不触发, @input 直开(菜单已是 true)也不触发。三个输入值各挂一个
     * watcher, 只在对应浮层开着时重量净空。 */
    addCategory() {
      if (this.addCatMenu) this._fitAddPop("addCatList");
    },
    addTags() {
      if (this.addTagMenu) this._fitAddPop("addTagList");
    },
    addSavePath() {
      if (this.addPathPop) this._fitAddPop("addPathList");
    },
  },
};

/* ---------------- <aq-combo-input>: combobox 输入行 + 候选面板组件(收敛 issue 26-10-20-2230 / R23-A-01) ----------------
 * 模板在 tpl/xtpl.html#tpl-combo-input(与 aq-table 同范式: body 注入的 x-template, 不随根模板
 * 编译, 也不多包 DOM)。五个调用点(添加窗口 保存路径/分类/标签 · 设定位置 movePath · 编辑弹窗
 * metaCat)此前各写一份逐字同骨架; 行为全部留在既有单点上(comboHoverIdx / comboKeydown /
 * _fitAddPop / _popBlurShouldHold / clearAddField), 本组件**只贡献模板与最小实例态**:
 *   · 数据一律 props(modelValue/menu/hi/options…), 写入一律 emit(update:modelValue/input/
 *     open/blur/keydown/clear) —— 组件实例没有根数据(根数据只在根实例, 见 table.js 头注同一
 *     教训; 模板里裸写 this.addCatMenu 会读到 undefined 且**不报错**)。
 *   · 悬停接管经 $root.comboHoverIdx(3px 位移门限在它里面); comboKey 空 = 不挂(保存路径)。
 *   · ref 落点 = **根** $refs(menuRef/listRef/inputRef), 经方法函数 ref 代写 —— 字符串 ref
 *     会注册到本组件实例上, 而 _fitAddPop/_hiScroll 是根方法、读的是根 $refs(实测 Vue
 *     3.5.13 语义, 见 pitfalls/web-ui 新增坑档); 名字为空 = 该处不需要 ref。
 * WARN: 组件方法名全局唯一(_scan_mixin_wiring 扫 methods 段跨文件重名) —— 方法名一律 comboOn / comboBind 前缀。
 * !本文件在 HTML 里必须排在 app.js 之前(app.js 末尾要 app.component 读 window.AQ_COMBO_INPUT_COMPONENT)。 */
window.AQ_COMBO_INPUT_COMPONENT = {
  name: "aq-combo-input",
  props: {
    modelValue: { type: String, default: "" },    // 输入框值(父模板 v-model 绑根数据)
    inputId: { type: String, default: "" },       // 输入框 id(_popBlurShouldHold 家族名单锚)
    inputRef: { type: String, default: "" },      // 输入框 $refs 名(开对话框自动聚焦用)
    placeholder: { type: String, default: "" },
    menu: { type: Boolean, default: false },      // 候选面板开合(根数据)
    hi: { type: Number, default: -1 },            // 键盘/悬停高亮索引(根数据)
    options: { type: Array, default: () => [] },  // 候选(字符串数组; 过滤产物由调用方传入)
    onPick: { type: Function, required: true },   // 点选/回车选中(o)
    comboKey: { type: String, default: "" },      // 悬停接管 kind(comboHoverIdx); 空 = 不挂
    icon: { type: String, default: "" },          // 候选行图标(sprite href); 空 = 无图标
    emptyText: { type: String, default: "" },
    headText: { type: String, default: "" },      // 计数头; 空 = 无头(R23-A-10 口径见模板头注)
    clearKind: { type: String, default: "" },     // 清空钮 clearAddField(kind); 空 = 无清空钮
    presetLabel: { type: String, default: "" },   // 预置行文案(meta 的"(无分类)"); 空 = 无
    presetValue: { type: String, default: "" },   // 预置行的 onPick 实参
    innerList: { type: Boolean, default: false }, // 候选是否包 .add-pop-list 可滚内层
    menuRef: { type: String, default: "" },       // 面板 $refs 名(限高/滚动跟随)
    listRef: { type: String, default: "" },       // 可滚内层 $refs 名(限高)
  },
  emits: ["update:modelValue", "input", "open", "blur", "keydown", "clear"],
  methods: {
    /* 原生 input 一个事件两件事: 回写模型(父模板 v-model) + 调用方侧输入逻辑
     * (如 addCatHi = -1; addCatMenu = true) —— 与收敛前 v-model/@input 两绑同序 */
    comboOnInput(e) {
      this.$emit("update:modelValue", e.target.value);
      this.$emit("input", e);
    },
    /* 悬停接管(治上下键选中项闪烁, hover-keynav-fight): 门限判据在 comboHoverIdx 单点里,
     * 这里只按 comboKey 转发; 空 = 该下拉没有悬停/键盘互斥面(保存路径候选) */
    comboOnHover(i, ev) {
      if (this.comboKey) this.$root.comboHoverIdx(this.comboKey, i, ev);
    },
    comboBindMenu(el) { if (this.menuRef) this.$root.$refs[this.menuRef] = el; },
    comboBindList(el) { if (this.listRef) this.$root.$refs[this.listRef] = el; },
    comboBindInput(el) { if (this.inputRef) this.$root.$refs[this.inputRef] = el; },
  },
  template: "#tpl-combo-input",
};
