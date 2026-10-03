/* auto-qb WEB UI · 添加种子弹窗(分类标签联动/目录浏览/文件与链接提交/全局拖拽进料 DND-01)
 *
 * app.js 按域拆分出的片段(2026-09-20)。约定与 config_editor.js / config_rules.js 同一范式:
 * 挂到 window.AQB_ADD, 由 app.js 末尾 app.mixin(window.AQB_ADD) 注入同一个 Vue 实例 ——
 * 方法体里的 this 仍是那个组件实例, 跨模块互调与拆分前完全等价。
 *
 * !本文件在 HTML 里必须排在 app.js **之前**(app.js 末尾要读 window.AQB_ADD);
 *   用到的列模型常量(TABLE_COLUMNS / MIN_COL_PX / STATE_RANK …)仍单点定义在 app.js 顶部。
 */
window.AQB_ADD = {
  /* DND-01: 全局拖拽监听挂 window(照 config_hub 的钩子先例); _dragDepth 非响应式(只驱动
   * addDragOver 布尔, 不进 data 免依赖追踪)。remove 与 add 引用同一 method 实例, 严格对称。 */
  mounted() {
    this._dragDepth = 0;
    window.addEventListener("dragenter", this._addDragEnter);
    window.addEventListener("dragover", this._addDragOver);
    window.addEventListener("dragleave", this._addDragLeave);
    window.addEventListener("drop", this._addDragDrop);
  },
  unmounted() {
    window.removeEventListener("dragenter", this._addDragEnter);
    window.removeEventListener("dragover", this._addDragOver);
    window.removeEventListener("dragleave", this._addDragLeave);
    window.removeEventListener("drop", this._addDragDrop);
  },
  methods: {
    /* ---------------- 添加种子对话框(R1B): multipart 提交不走 this.api()(它强制 application/json 会破坏 multipart boundary),
     * 用原生 fetch + Bearer(this.token); 回执仍复用 waitCmd 轮询 /api/cmd/{id} ---------------- */
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
        safe("/api/categories", (r) => Object.keys(r.categories || {}).sort((a, b) => a.localeCompare(b))),
        // exclude_auto=1: 剔除程序自动维护的标签(站点名/HR/集数等, 判定在后端), 候选只留用户可挑的
        safe("/api/tags?exclude_auto=1", (r) => (r.tags || []).slice().sort((a, b) => a.localeCompare(b))),
        safe("/api/paths", (r) => r.paths || []),
      ]);
      if (this.addOpen) {  // 仅窗口仍开着时回填(慢响应不得污染下一次打开)
        this.addCatOptions = cats;
        this.addTagOptions = tags;
        this.addPathOptions = paths;
      }
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
    openAddCatMenu() {
      this._addPopBlurCancel();  // 焦点回到本输入框(label 转发/重新点入)时撤销挂起的失焦收层, 菜单不闪
      this.addTagMenu = false;
      this.addCatHi = -1;
      this.addCatMouseAt = null;  // 开层复位悬停门限坐标(下次打开首个动作不被旧坐标误挡)
      this.addCatMenu = true;
    },
    openAddTagMenu() {
      this._addPopBlurCancel();
      this.addCatMenu = false;
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
    pickAddTag(tag) {
      const parts = this.addTags.split(",").map((t) => t.trim()).filter(Boolean);
      if (!parts.includes(tag)) parts.push(tag);
      this.addTags = parts.join(", ") + ", ";  // 尾随逗号: 便于继续挑选下一个
      this.addTagMenu = false;
      this.addTagHi = -1;
    },
    onAddCatKeydown(e) {
      this._comboKeydown(e, "cat");
    },
    onAddTagKeydown(e) {
      this._comboKeydown(e, "tag");
    },
    /* 悬停接管(治「上下键选中项闪烁/Enter 选错」2026-09-29, issue 26-09-29-2142; 同款: config_hub.hubTrackerHoverIdx):
     * 分类/标签/编辑分类三处下拉的悬停高亮原是 @mouseenter 直写键盘活动项 —— 光标静止停在列表上
     * 用 ↑↓ 选择时, 行滚动/DOM 变更后浏览器给静止光标补发合成 hover 事件, 活动项被拽回光标行
     * (改前真机实测: ↓×16 两次被拽回, Enter 选中光标行 cat-06 而非键盘到达的 cat-16 —— 不止闪烁, 实选错)。
     * 改为 @mousemove + 位移门限: 位移 <3px(静止 / 合成事件)不接管, 真实移动才把活动项交给光标;
     * 门限坐标按下拉分存(state.js *MouseAt), 开层单点复位(openAddCatMenu/openAddTagMenu/openMetaCatMenu) */
    comboHoverIdx(kind, i, ev) {
      const atKey = kind === "cat" ? "addCatMouseAt" : kind === "tag" ? "addTagMouseAt" : "metaCatMouseAt";
      const hiKey = kind === "cat" ? "addCatHi" : kind === "tag" ? "addTagHi" : "metaCatHi";
      const x = ev.clientX, y = ev.clientY, at = this[atKey];
      if (at) {
        const dx = x - at.x, dy = y - at.y;
        if (dx * dx + dy * dy < 9) return; // <3px: 光标静止 / 合成事件, 不接管
      }
      this[atKey] = { x, y };
      this[hiKey] = i;
    },
    _comboKeydown(e, kind) {
      // 分类/标签 combobox 共用键盘导航: 上下循环高亮, 回车选中, Esc 只收下拉(阻断冒泡, 不关对话框)
      const opts = kind === "cat" ? this.addCatFiltered() : this.addTagFiltered();
      const menuKey = kind === "cat" ? "addCatMenu" : "addTagMenu";
      const hiKey = kind === "cat" ? "addCatHi" : "addTagHi";
      const listRef = kind === "cat" ? "addCatList" : "addTagList";
      if ((e.key === "ArrowDown" || e.key === "ArrowUp") && opts.length) {
        e.preventDefault();
        if (!this[menuKey]) {
          this[menuKey] = true;
          this[hiKey] = e.key === "ArrowDown" ? -1 : 0;
        }
        this[hiKey] = (this[hiKey] + (e.key === "ArrowDown" ? 1 : -1) + opts.length) % opts.length;
        this._hiScroll(listRef);
      } else if (e.key === "Enter" && this[menuKey] && this[hiKey] >= 0 && opts[this[hiKey]]) {
        e.preventDefault();
        if (kind === "cat") this.pickAddCat(opts[this[hiKey]]);
        else this.pickAddTag(opts[this[hiKey]]);
      } else if (e.key === "Escape" && this[menuKey]) {
        e.stopPropagation();
        this[menuKey] = false;
        this[hiKey] = -1;
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
      this.dirBrowse.loading = true;
      this.dirBrowse.error = "";
      try {
        const r = await this.api("/api/fs/dirs?path=" + encodeURIComponent(path || ""));
        this.dirBrowse.path = r.path || "";
        this.dirBrowse.parent = r.parent || "";
        this.dirBrowse.roots = r.roots || [];
        this.dirBrowse.dirs = r.dirs || [];
      } catch (e) {
        if (!e.auth) this.dirBrowse.error = e.message || "读取目录失败";
      } finally {
        this.dirBrowse.loading = false;
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
      this._addPopBlurCancel();
      this.addCatMenu = false;
      this.addTagMenu = false;
      this.addPathHi = this.addPathOptions.indexOf(this.addSavePath.trim());
      this.addPathPop = true;
      this._hiScroll("addPathList");
    },
    /* ---------------- 失焦收层(2026-10-03 报障: 点窗口其它位置下拉不收/闪烁重现) ----------------
     * 收层主判据改成「输入框失焦」(模板 @focusout), window click(lifecycle.js)降级为兜底:
     * 点空白/点别的字段/Tab 走 focusout 必然触发; 点字段 label(for= 转发激活)不触发重开闪烁。
     * ⚠ 不能在 focusout 里同步收 —— 点 label 时浏览器先 blur 再由 label 默认动作把焦点转回输入框
     * (实测 focusout → ~2ms 后 focusin), 同步收层 = 关了又开, leave 过渡被打断 = 用户看到的
     * 「下拉闪烁再次出现」。挂 40ms 定时合帧: 焦点真离开(点空白/别的字段/Tab)下一拍收层;
     * 焦点回来了(开层方法先跑)则撤销, 菜单全程不闪。定时窗内收层前 window click 兜底照常生效。 */
    addPopBlurClose() {
      clearTimeout(this._addPopBlurT);
      this._addPopBlurT = setTimeout(() => {
        this.addCatMenu = false;
        this.addTagMenu = false;
        this.addPathPop = false;
        this.addCatHi = -1;
        this.addTagHi = -1;
        this.addPathHi = -1;
      }, 40);
    },
    _addPopBlurCancel() {
      clearTimeout(this._addPopBlurT);
    },
    /* ---------------- 下拉限高(2026-10-03 报障: 选项过长把添加窗口撑变形) ----------------
     * .pop-menu 基础 max-height:330px 只保证菜单自身可滚, 但菜单锚在输入行下方, 输入行贴近
     * 窗口底沿时整条菜单伸出窗口外(滚动条也跟着出窗), 且绝对定位溢出会把 .add-dialog-body
     * 的 scrollHeight 撑大(窗口内容变形/多出滚动量)。开层后在同一帧量「输入行到滚动容器可见
     * 底沿」的净空, 把可滚内层(.add-pop-list 或菜单自身)限到净空内 —— 滚动条永远留在窗口里。
     * 只在开层/候选到位时量一次: 菜单开着时用户再滚动窗口, 行随内容滚走, 净空只增不减会露头,
     * 不做滚动跟随(收层重开即重新量, 复杂度不值)。 */
    _fitAddPop(refName) {
      this.$nextTick(() => {
        if (!this.addOpen) return;
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
      // 面板未开时不接管按键(按钮默认行为); 开启后: 上下移动高亮, 回车回填, Esc 只收面板(阻断冒泡不关对话框)
      if (!this.addPathPop) return;
      const n = this.addPathOptions.length;
      if ((e.key === "ArrowDown" || e.key === "ArrowUp") && n) {
        e.preventDefault();
        if (this.addPathHi < 0) this.addPathHi = e.key === "ArrowDown" ? -1 : 0;
        this.addPathHi = (this.addPathHi + (e.key === "ArrowDown" ? 1 : -1) + n) % n;
        this._hiScroll("addPathList");
      } else if (e.key === "Enter") {
        e.preventDefault();
        const p = this.addPathOptions[this.addPathHi];
        if (p) this.pickAddPath(p);
      } else if (e.key === "Escape") {
        e.stopPropagation();
        this.addPathPop = false;
        this.addPathHi = -1;
      }
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
    async submitAddTorrent() {
      if (!this.addCanSubmit) return;
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
        // 不设 Content-Type, 浏览器自动生成 multipart boundary
        const queued = await this.api("/api/torrents/add", { method: "POST", body: JSON.stringify(payload) });
        const r = await this.waitCmd(queued.cmd_id);
        if (r.ok) {
          this.toast("添加种子已受理, 列表稍后自动刷新", "ok", 4000);
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
    /* 下拉限高单点: 三个浮层的开层入口有四处(开层方法 / 输入 @input 直开 / 键盘 _comboKeydown /
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
  },
};
