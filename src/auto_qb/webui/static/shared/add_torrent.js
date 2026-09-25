/* auto-qb WEB UI · 添加种子弹窗(分类标签联动/目录浏览/文件与链接提交/全局拖拽进料 DND-01)
 *
 * app.js 按域拆分出的片段(2026-09-20)。约定与 config_editor.js / config_rules.js 同一范式:
 * 挂到 window.AQB_ADD, 由 app.js 末尾 app.mixin(window.AQB_ADD) 注入同一个 Vue 实例 ——
 * 方法体里的 this 仍是那个组件实例, 跨模块互调与拆分前完全等价。
 *
 * ❗本文件在 HTML 里必须排在 app.js **之前**(app.js 末尾要读 window.AQB_ADD);
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
        safe("/api/tags", (r) => (r.tags || []).slice().sort((a, b) => a.localeCompare(b))),
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
      this.addTagMenu = false;
      this.addCatHi = -1;
      this.addCatMenu = true;
    },
    openAddTagMenu() {
      this.addCatMenu = false;
      this.addTagHi = -1;
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
      this.addCatMenu = false;
      this.addTagMenu = false;
      this.addPathHi = this.addPathOptions.indexOf(this.addSavePath.trim());
      this.addPathPop = true;
      this._hiScroll("addPathList");
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
};
