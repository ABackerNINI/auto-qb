/* auto-qb WEB UI · 统计 / 分类标签管理 / 日志 / 限速 / 流量历史 弹窗
 *
 * app.js 按域拆分出的片段(2026-09-20)。约定与 config_editor.js / config_rules.js 同一范式:
 * 挂到 window.AQB_DIALOGS, 由 app.js 末尾 app.mixin(window.AQB_DIALOGS) 注入同一个 Vue 实例 ——
 * 方法体里的 this 仍是那个组件实例, 跨模块互调与拆分前完全等价。
 * 另承载 busy+try+反馈+finally 骨架的三个单点(_mgrRun/_panelLoad/_postWaitCmd, issue 26-10-20-2231):
 * config_hub.js 的 tm 面板族经同一根实例混入调用, 单点不在那份文件里重写。
 *
 * !本文件在 HTML 里必须排在 app.js **之前**(app.js 末尾要读 window.AQB_DIALOGS);
 *   用到的列模型常量(TABLE_COLUMNS / MIN_COL_PX / STATE_RANK …)仍单点定义在 app.js 顶部。
 */

/* 历史流量粒度三档(26-10-20-2231 / R23-B-17): <aq-seg> 要的形状 [{v, label}]。
 * 此前这份清单**只以字面量映射活在模板里**(`['day','month','year']` + `{day:'天',…}`), 与
 * historyBuckets 的分档判据隔了一层 —— 加一档要同时改模板数组、模板文案表、聚合分支三处。
 * 现在合法值挂在这里, 聚合分支与之同域(同文件), 模板只消费。 */
const HIST_GRAN_ITEMS = [
  { v: "day", label: "天" },
  { v: "month", label: "月" },
  { v: "year", label: "年" },
];
/* 限速浮层(.speed-pop)贴边留白 12px: 比浮层默认 8px(overlay_fit.js::EDGE)多 4px ——
 * FX-08 改就近弹出时的历史值, 无注释也无佐证必须不同; issue 26-10-20-2231 复验时按
 * 行为零变化口径显式命名保留, 夹取走单点显式传参, 确要统一只改这一个常量。 */
const SPEED_PAD = 12;

window.AQB_DIALOGS = {
  methods: {
    /* ---------------- 统计面板(FE-2C): 全局状态(server_state, 缺失显示 —) ----------------
     * 数据源随 /api/state.status.server 每轮回传(见 refresh()), 状态栏常显统计直接取
     * `statsServer`; 打开面板 / 卡内"刷新"按钮才走 /api/stats 重取一次(统计是低频信息,
     * 且"刷新"按钮语义上就该真的发一次请求)。server 为 null(qB 未同步/降级全量不可用)
     * 时空态文案; 请求失败给重试。
     */
    async openStats() {
      this.statsOpen = true;
      await this.loadStats();
    },
    closeStats() {
      this.statsOpen = false;
    },
    async loadStats() {
      await this._panelLoad(this, async () => {
        const r = await this.api("/api/stats");
        this.statsServer = r.server || null;
        // FIX-04b: 失败不清空已有数据(骨架常驻防闪烁); 仅首次加载失败保持 null → 错误占位重试
      }, { loading: "statsLoading", err: "statsError", errFallback: "加载失败" });
    },
    /* 统计值兜底: 字段缺失(null/undefined)显示 —; 0 是合法值(如 DHT 0 节点)原样展示 */
    statVal(v, fmt) {
      if (v === null || v === undefined || v === "") return "—";
      return fmt ? fmt(v) : String(v);
    },
    /* qB connection_status 文案(原值兜底; 缺失显示 —) */
    connText(v) {
      if (v === null || v === undefined || v === "") return "—";
      return { connected: "已连接", firewalled: "已连接(防火墙限制)", disconnected: "未连接" }[v] || String(v);
    },
    /* ---------------- 遮罩关窗: 判据必须是"按下的那一点也在遮罩上"(2026-10-03 报障) ----------------
     * 旧写法 @click.self 判的是 click 事件的 target, 而 click 由 mousedown 与 mouseup 的
     * **公共祖先**派发(DOM 规范): 在输入框里按下左键拖选文字、鼠标终点落到遮罩上抬手 ——
     * 公共祖先就是遮罩本身, 于是"拖选文字"被判成"点空白关窗"(用户原话: 选个标签文字,
     * 抬手窗口没了)。修法 = mousedown 先记一笔「这一下是不是从遮罩起手」(_maskArmed),
     * mouseup.self 只在自遮罩起手时才关窗。任何落在对话框内部的 mousedown 都会把臂位清掉,
     * 不会累积到下一次点击; 遮罩上按下再抬起(真·点空白)行为不变。
     * 用法(模板成对挂): @mousedown="maskDownSelf" @mouseup.self="maskCloseIfArmed(closeX)" */
    maskDownSelf(e) {
      this._maskArmed = e.target === e.currentTarget;
    },
    maskCloseIfArmed(closeFn, ...args) {
      if (!this._maskArmed) return;  // 这一笔起手在对话框内(拖选文字/拖动), 不是"点空白"
      this._maskArmed = false;
      closeFn(...args);
    },
    /* 只有布尔开关、没有关闭方法的两处浮层(历史弹层 / 快捷键帮助): 给遮罩一个具名关闭方法,
     * 免得在模板里写内联箭头(编译产物难读, 且赋值表达式在模板里不受守卫测试保护)。 */
    closeHistory() {
      this.historyOpen = false;
    },
    closeKbHelp() {
      this.kbHelpOpen = false;
    },
    /* ---------------- busy 骨架单点(issue 26-10-20-2231: dialogs/config_hub 共 19 处收敛) ----------------
     * 「置 busy → try 请求 → 失败反馈 → finally 复位」这条骨架原先在 dialogs.js 与 config_hub.js
     * 手抄 19 遍; 漏 finally 的症状是面板永久转圈(见 pitfalls/web-ui/inflight-flag-no-timeout)。
     * 三个单点按反馈通道分家(反馈形态不同是族的真实边界, 不强并成一个万能 helper):
     *   _mgrRun      管理对话框写操作(R20-B-01): busy → fn → ok toast → 重拉列表 → 失败 toast(!auth) → 复位
     *   _panelLoad   面板加载/槽回执(R20-B-02 + R20-C-15): busy(可选) → 槽清空 → fn → 失败落槽或 toast → 复位
     *   _postWaitCmd POST+waitCmd 三态 toast(R20-B-03): busy → POST → waitCmd → ok / 命令失败 / 发送失败 → 复位
     * 各处差异(成功收尾 / 失败回滚 / 槽名 / 静默变体)作为参数或回调留在调用点。刻意不入
     * helper 的特例: tmShutdownTool(保存失败回滚内存态, 见 R20-C-15 台账)保持原样。 */
    /* 管理对话框写操作骨架: fn 抛错 = 失败(auth 拦截静默, 交给登录框); 成功先 toast 再重拉列表 */
    async _mgrRun(fn, okMsg, errMsg) {
      this.mgrBusy = true;
      try {
        await fn();
        this.toast(okMsg, "ok", 2500);
        await this.loadMgr();
        return true;
      } catch (e) {
        if (!e.auth) this.toast(`${errMsg}: ${e.message}`, "error", 8000);
        return false;
      } finally {
        this.mgrBusy = false;
      }
    },
    /* 面板加载/槽回执骨架: loading 置真期间预清旧错(重试可见); 失败落错误槽 —— authGated=false
     * 的 tm 族不看 auth(状态轮询/配置保存的失败都要上屏, 不能静默)。loading 不传 = 静默变体
     * (speedMode: 不动 busy 位、不预清旧错, 失败仍落槽); keepErr=true 只跳过预清(tmLoad 重拉
     * 不清自己的状态槽, 由响应/失败分支落值)。errToast = toast 通道(一键导入站点: 恒提示不看
     * auth)。onOk/onErr/onFinally 承接各处个性(成功收尾 / 失败装配与回滚 / 加载完成置位)。 */
    async _panelLoad(obj, fn, opts) {
      const o = opts || {};
      if (o.loading) {
        obj[o.loading] = true;
        if (o.err && !o.keepErr) obj[o.err] = "";
      }
      try {
        await fn();
      } catch (e) {
        if (o.errToast) {
          this.toast(`${o.errToast.prefix}: ${(e && e.message) || o.errToast.fallback}`, "error", o.errToast.ms);
        } else if (o.err && (o.authGated === false || !e.auth)) {
          obj[o.err] = (e && e.message) || o.errFallback;
        }
        if (o.onErr) o.onErr(e);
      } finally {
        if (o.loading) obj[o.loading] = false;
        if (o.onFinally) o.onFinally();
      }
    },
    /* POST+waitCmd 三态 toast 骨架(三态判据单点): ①ok 回执 → okMsg(okMs 缺省 2500; 传函数 =
     * 成功此刻才取值, 供「按切换前状态措辞」的场景) ②命令回执失败(已送达被拒) → cmdFail: r.error(8000)
     * ③请求本身失败(发送不出去) → sendFail: e.message(auth 拦截静默, 交给登录框)。onPost 在
     * POST 完成与 waitCmd 之间(命令遥测 _markCmdPost 的记账点), onOk 在成功 toast 后
     * (await 完才走 finally 复位)。 */
    async _postWaitCmd(busyObj, busyKey, url, body, opts) {
      busyObj[busyKey] = true;
      try {
        const resp = await this.api(url, { method: "POST", body: JSON.stringify(body) });
        if (opts.onPost) opts.onPost(resp);
        const r = await this.waitCmd(resp.cmd_id);
        if (r.ok) {
          this.toast(typeof opts.okMsg === "function" ? opts.okMsg() : opts.okMsg, "ok", opts.okMs || 2500);
          if (opts.onOk) await opts.onOk();
          return true;
        }
        this.toast(`${opts.cmdFail}: ${r.error}`, "error", 8000);
        return false;
      } catch (e) {
        if (!e.auth) this.toast(`${opts.sendFail}: ` + e.message, "error");
      } finally {
        busyObj[busyKey] = false;
      }
      return false;
    },
    /* ---------------- 分类/标签管理对话框(FE-2C2): qB 分类/标签的增删改 ----------------
     * 列表数据源 GET /api/categories|tags; 写操作走 POST /api/categories(/edit|/remove) 与 /api/tags(/remove)。
     * CRUD 成功后重拉列表刷新对话框; 对话框关闭后主列表随下一轮 rid 轮询自然更新(不强刷)。
     */
    openMgr(kind) {
      this.filterMenu = "";  // 从筛选弹层进入: 先收起弹层再开对话框
      this.mgrOpen = kind;
      this.mgrCategories = [];
      this.mgrTags = [];
      this.mgrNew.tags = "";
      this.mgrNew.catName = "";
      this.mgrNew.catPath = "";
      this.mgrError = "";
      this.loadMgr();
    },
    closeMgr() {
      if (this.mgrBusy) return;  // 写操作回执等待期不允许误关
      this.mgrOpen = "";
    },
    /* 新建行提交分派(issue 26-10-20-2231 管理对话框合并后单一入口): 添加钮与 Enter 两路共用,
     * 按 mgrOpen 分派到既有 submitMgrTags / submitMgrCategory —— 校验与投递单点不动。 */
    mgrSubmitNew() {
      if (this.mgrOpen === "tag") this.submitMgrTags();
      else if (this.mgrOpen === "category") this.submitMgrCategory();
    },
    async loadMgr() {
      await this._panelLoad(this, async () => {
        if (this.mgrOpen === "category") {
          // qB categories: {名字: {save_path, ...}} → 行数组(名字字典序)
          const r = await this.api("/api/categories");
          const cats = r.categories || {};
          this.mgrCategories = Object.keys(cats)
            .map((name) => ({ name, save_path: (cats[name] && cats[name].save_path) || "" }))
            .sort((a, b) => a.name.localeCompare(b.name));
        } else {
          const r = await this.api("/api/tags");
          this.mgrTags = (r.tags || []).slice().sort((a, b) => a.localeCompare(b));
        }
      }, { loading: "mgrLoading", err: "mgrError", errFallback: "加载失败" });
    },
    async submitMgrCategory() {
      if (this.mgrBusy) return;  // 回车提交与按钮同源: 防回执等待期重复投递
      const name = this.mgrNew.catName.trim();
      if (!name) { this.toast("分类名称不能为空", "warn"); return; }
      await this._mgrRun(async () => {
        const payload = { name };
        const savePath = this.mgrNew.catPath.trim();
        if (savePath) payload.save_path = savePath;  // 可空: 留空 = 仅建分类不带路径
        await this.api("/api/categories", { method: "POST", body: JSON.stringify(payload) });
        this.mgrNew.catName = "";
        this.mgrNew.catPath = "";
      }, `已创建分类: ${name}`, "创建分类失败");
    },
    async submitMgrTags() {
      if (this.mgrBusy) return;  // 回执等待期防重复投递
      // 支持中英文逗号分隔批量创建(空段剔除; 与添加种子对话框的标签口径一致)
      const tags = this.mgrNew.tags.split(/[,,]/).map((t) => t.trim()).filter(Boolean);
      if (!tags.length) { this.toast("请输入至少一个标签", "warn"); return; }
      await this._mgrRun(async () => {
        await this.api("/api/tags", { method: "POST", body: JSON.stringify({ tags }) });
        this.mgrNew.tags = "";
      }, `已创建 ${tags.length} 个标签`, "创建标签失败");
    },
    async mgrEditCatPath(name) {
      const cur = (this.mgrCategories.find((c) => c.name === name) || {}).save_path || "";
      const p = await this.promptDialog("修改分类保存路径", cur, {
        body: `分类: ${name}`, placeholder: "如 D:\\Torrents\\TV", okText: "保存",
      });
      if (p === null) return;  // 取消/遮罩/Esc 均不写
      const savePath = p.trim();
      if (!savePath) { this.toast("保存路径不能为空", "warn"); return; }
      if (savePath === cur) { this.toast("未作修改", "ok", 2000); return; }
      await this._mgrRun(
        () => this.api("/api/categories/edit", { method: "POST", body: JSON.stringify({ name, save_path: savePath }) }),
        `已更新分类路径: ${name}`, "修改分类路径失败",
      );
    },
    async mgrDeleteCategory(name) {
      const ok = await this.confirmDialog("删除分类", `将删除分类「${name}」(不删除种子与文件)`, { okText: "删除", danger: true });
      if (!ok) return;
      await this._mgrRun(
        () => this.api("/api/categories/remove", { method: "POST", body: JSON.stringify({ names: [name] }) }),
        `已删除分类: ${name}`, "删除分类失败",
      );
    },
    async mgrDeleteTag(tag) {
      const ok = await this.confirmDialog("删除标签", `将删除标签「${tag}」(自动规则可能重新打上)`, { okText: "删除", danger: true });
      if (!ok) return;
      await this._mgrRun(
        () => this.api("/api/tags/remove", { method: "POST", body: JSON.stringify({ tags: [tag] }) }),
        `已删除标签: ${tag}`, "删除标签失败",
      );
    },
    /* ---------------- 标签/分类编辑对话框: 对选中集合**即时**增删标签/改分类 ----------------
     * 与管理对话框(FE-2C2, 全局定义的增删)互补: 这里只改"种子上打了什么"。
     * 交互为即时模式(照 qB 官方 WebUI): 点胶囊即投递一条 bulk 命令(add_tags/remove_tags),
     * 每条命令独立回执, 不设"应用/取消" —— 对话框只是把候选摊开, 关闭即完。
     * 目标集合在打开时刻锁定(遮罩下选择不会变); 单种子右键传 hash, 批量(右键批量菜单)传空
     * = 整个选中集合(与批量动作同口径)。键盘路径(计划 26-09-28-0354 W4)可传目标对象
     * {groupKeys, memberHashes}(光标组行/剧集单元, 无选中集合时), 与 _bulkTargets 同形状。
     * 新分类/新标签走"先建后设": 创建命令与打标命令按 FIFO 在主循环顺序执行, 创建失败
     * (典型 = 已存在的 409)不影响后续设置 —— 真正决定成败的是 set/add 的回执。
     */
    openMetaDialog(singleHash) {
      this.menu.visible = false;
      const targets = typeof singleHash === "string"
        ? { groupKeys: [], memberHashes: [singleHash] }
        : (singleHash || this._bulkTargets());
      if (!targets.groupKeys.length && !targets.memberHashes.length) return;
      this.metaTargets = targets;
      this.metaOpen = true;
      this.metaCatMenu = false;
      this.metaCatHi = -1;
      this.metaNewTags = "";
      this.metaBusy = false;
      const members = this._metaExpandHashes(targets)
        .map((h) => this.memberByHash.get(h))
        .filter(Boolean);
      this.metaCount = this._metaExpandHashes(targets).length;
      this.metaCommonTags = this._metaCommonTags(members);
      const cat = this._metaCommonCategory(members);
      this.metaCat = cat.value;
      this.metaCatDiff = cat.diff;
      this.metaCatInput = cat.value;
      this.loadMetaOptions();
    },
    closeMeta() {
      if (this.metaBusy) return;  // 命令回执等待期不允许误关(与管理对话框同口径)
      this.metaOpen = false;
    },
    /* 目标展开(预览共同值用): 与后端 bulk 的 keys 展开同口径(组级联全部在册成员);
     * 投递仍整份传 keys + hashes, 展开去重的单一权威在后端, 前端这份只为算交集/计数 */
    _metaExpandHashes(targets) {
      const hashes = [...targets.memberHashes];
      for (const k of targets.groupKeys) {
        const g = this._findGroup(k);
        if (g) for (const m of g.members) hashes.push(m.hash);
      }
      return [...new Set(hashes)];
    },
    /* 共同标签(交集): 与 decorate._commonTags 同口径取交集, 但**不过滤站点同名标签** ——
     * 那条过滤是组级**展示**口径(站点列已有同名值, 展示纯冗余); 编辑场景必须能看到并
     * 移除这类标签, 不能复用 */
    _metaCommonTags(members) {
      const sets = members.map((m) => new Set(m.tags || []));
      if (!sets.length) return [];
      let common = [...sets[0]];
      for (const s of sets.slice(1)) common = common.filter((t) => s.has(t));
      return common.sort((a, b) => a.localeCompare(b));
    },
    _metaCommonCategory(members) {
      const vals = members.map((m) => m.category || "");
      const diff = vals.some((v) => v !== vals[0]);
      return { value: diff ? "" : vals[0], diff };
    },
    async loadMetaOptions() {
      // 并行拉分类/标签候选; 单端点失败静默降级为空(不阻塞对话框, 照 loadAddOptions 先例)
      const safe = async (url, pick) => {
        try {
          return pick(await this.api(url));
        } catch (e) {
          return [];
        }
      };
      const [cats, tags] = await Promise.all([
        safe("/api/categories", (r) => Object.keys(r.categories || {}).sort((a, b) => a.localeCompare(b))),
        // exclude_auto=1: 候选剔除程序自动维护的标签(站点名/HR/集数等, 判定在后端)
        safe("/api/tags?exclude_auto=1", (r) => (r.tags || []).slice().sort((a, b) => a.localeCompare(b))),
      ]);
      if (this.metaOpen) {  // 仅对话框仍开着时回填(慢响应不得污染下一次打开)
        this.metaCategories = cats;
        // 选中种子共同携带的标签必须并回候选: 胶囊是这类标签唯一的摘除入口, 藏了就摘不掉
        // (编辑场景可见性口径同 _metaCommonTags 注释); 其余程序标签只影响"新增候选"的干净度
        this.metaTags = [...new Set([...tags, ...this.metaCommonTags])].sort((a, b) => a.localeCompare(b));
      }
    },
    /* bulk 投递统一走这里: 与 bulkAct 同链路(api + waitCmd + toast 三态), 但目标集合用
     * 打开时刻锁定的 metaTargets, 且不做乐观贴片 —— 标签/分类由 bulk 的 RESYNC 补刷新落行 */
    async _metaBulk(action, extra, okText) {
      this._auditScope("meta:" + action, this.metaTargets);  // S4 运行时审计(默认关, 只记账)
      const { groupKeys, memberHashes } = this.metaTargets;
      const t0 = this._newCmdStats(action);
      this._markCmdPatch(t0);
      return this._postWaitCmd(this, "metaBusy", "/api/torrents/bulk",
        { action, keys: groupKeys, hashes: memberHashes, ...extra },
        {
          okMsg: `已执行: ${okText}`,
          cmdFail: `${okText}失败`,
          sendFail: "命令发送失败",
          onPost: () => this._markCmdPost(t0),  // 遥测记账点: POST 完成与 waitCmd 之间
        });
    },
    async metaToggleTag(tag) {
      if (this.metaBusy) return;
      const has = this.metaCommonTags.includes(tag);
      const ok = await this._metaBulk(
        has ? "remove_tags" : "add_tags", { tags: [tag] },
        (has ? "移除标签「" : "添加标签「") + tag + "」"
      );
      if (ok) {  // 对话框内的即时确认(行数据等 bulk 的 RESYNC 补刷新落下来)
        this.metaCommonTags = has
          ? this.metaCommonTags.filter((t) => t !== tag)
          : [...this.metaCommonTags, tag].sort((a, b) => a.localeCompare(b));
      }
    },
    async metaAddNewTags() {
      if (this.metaBusy) return;
      const tags = this.metaNewTags.split(/[,,]/).map((t) => t.trim()).filter(Boolean);
      if (!tags.length) { this.toast("请输入至少一个标签", "warn"); return; }
      const fresh = tags.filter((t) => !this.metaTags.includes(t));
      if (fresh.length) {
        // 新标签定义先入队创建(定义列表/管理对话框可见); 已存在时创建失败不影响后续打标
        try {
          await this.api("/api/tags", { method: "POST", body: JSON.stringify({ tags: fresh }) });
        } catch (e) {
          if (!e.auth) this.toast("创建标签失败(可能已存在), 继续尝试打标", "warn", 4000);
        }
        this.metaTags = [...new Set([...this.metaTags, ...fresh])].sort((a, b) => a.localeCompare(b));
      }
      const ok = await this._metaBulk("add_tags", { tags }, `添加标签「${tags.join(", ")}」`);
      if (ok) {
        this.metaCommonTags = [...new Set([...this.metaCommonTags, ...tags])].sort((a, b) => a.localeCompare(b));
        this.metaNewTags = "";
      }
    },
    async metaSetCategory(name) {
      name = (name || "").trim();
      this.metaCatMenu = false;
      this.metaCatHi = -1;
      if (name === this.metaCat && !this.metaCatDiff) return;  // 未变化: 静默返回(不给"已设置"的假反馈)
      if (name && !this.metaCategories.includes(name)) {
        try {
          await this.api("/api/categories", { method: "POST", body: JSON.stringify({ name }) });
        } catch (e) {
          if (!e.auth) this.toast(`创建分类「${name}」失败(可能已存在), 继续尝试设置`, "warn", 4000);
        }
        this.metaCategories = [...this.metaCategories, name].sort((a, b) => a.localeCompare(b));
      }
      const ok = await this._metaBulk("set_category", { category: name }, name ? `设置分类「${name}」` : "清除分类");
      if (ok) {
        this.metaCat = name;
        this.metaCatDiff = false;
        this.metaCatInput = name;
      }
    },
    /* 失焦收层(与添加种子三下拉同一套单点口径 _popBlurArm, 见 pitfalls/web-ui/combobox-focusout-close:
     * 40ms 合帧守卫是必需的 —— 点字段 label(for= 转发激活)时浏览器先 blur 再把焦点转回输入框,
     * 同步收层 = 关了又开(用户看到的"闪烁再现"); 焦点真回来由 openMetaCatMenu 撤销。
     * 改前这个下拉根本没有失焦收层(也没进 lifecycle 的 window click 兜底名单): 点了对话框里
     * 别的地方(标签胶囊 / 新标签输入框)下拉悬着不收, 只能 Esc 或选一项 —— 与三下拉同族缺陷。
     * 四轮加固(2026-10-04): _popBlurArm 收层前问 _popBlurShouldHold(单点在 add_torrent.js,
     * 记录器挂根实例 mounted) —— 模板 @mousedown.prevent 缺位时由 JS 守卫独立根除按住期收层闪烁。 */
    metaCatBlurClose() {
      this._popBlurArm("_metaPopBlurT", ["meta-category"], () => {
        this.metaCatMenu = false;
        this.metaCatHi = -1;
      });
    },
    openMetaCatMenu() {
      this._popBlurCancel("_metaPopBlurT");  // 焦点回到本输入框时撤销挂起的失焦收层, 菜单不闪
      this.metaCatMouseAt = null;  // 开层复位悬停门限坐标(同 addCatMouseAt)
      this.metaCatHi = this.metaCategories.indexOf(this.metaCatInput.trim());
      this.metaCatMenu = true;
      this._hiScroll("metaCatList");
    },
    metaCatFiltered() {
      const q = this.metaCatInput.trim().toLowerCase();
      if (!q) return this.metaCategories;
      return this.metaCategories.filter((c) => c.toLowerCase().includes(q));
    },
    onMetaCatKeydown(e) {
      // 下拉未开时不接管按键(回车走应用); 开启后: 上下循环高亮, 回车选高亮项, Esc 只收面板(阻断冒泡不关对话框)。
      // 键盘导航本体在 comboKeydown 单点(add_torrent.js, 收敛 R20-B-05 五处; 本处个性 = 回车回退提交输入框文本)
      this.comboKeydown({
        items: () => this.metaCatFiltered(),
        open: () => this.metaCatMenu,
        setOpen: (v) => { this.metaCatMenu = v; },
        hi: () => this.metaCatHi,
        setHi: (v) => { this.metaCatHi = v; },
        onPick: (name) => this.metaSetCategory(name),
        enterFallback: () => this.metaCatInput,  // 无高亮项时回车提交输入框文本(含清空 = 无分类)
        listRef: "metaCatList",
        openOnArrow: true,
      }, e);
    },
    /* ---------------- 日志 tail(FE-2C): /api/log 只读(等级过滤 + 行数选择 + 手动刷新, 不轮询);
         入口在 Console Hub「常规」分区页尾(2026-09-26 由独立「运行日志」分区并入), 顶层 page 只有 groups/settings ---------------- */
    async loadLogs() {
      await this._panelLoad(this.logs, async () => {
        const q = new URLSearchParams({ lines: String(this.logs.num || 300) });
        if (this.logs.level) q.set("level", this.logs.level);
        const r = await this.api(`/api/log?${q.toString()}`);
        this.logs.lines = r.lines || [];
        this.logs.file = r.file || "";
        this.logs.note = r.note || "";   // "筛不了"的说明(后端给): 空结果与筛选失效不再长得一样
        this.logs.loaded = true;
      }, { loading: "loading", err: "error", errFallback: "日志加载失败" });
    },
    /* ---------------- 限速托管状态与临时覆盖(FE-2C D2) ----------------
     * /api/speed/mode 只读快照; /api/speed/override 两方向都必填(0=不限),
     * 曲线启用时覆盖是临时的(下一档位切换即恢复), 停用时为常态设置。
     */
    async loadSpeedMode(force = false) {
      if (this.speedMode.loaded && !force) return;
      // 静默变体(无 loading 位): 不预清旧错, 失败仍落槽 —— 与四块面板加载同骨架不同反馈节奏
      await this._panelLoad(this.speedMode, async () => {
        const r = await this.api("/api/speed/mode");
        this.speedMode = {
          loaded: true,
          curveEnabled: !!r.curve_enabled,
          target: r.curve_target || null,
          current: r.current || null,
          altOn: !!r.alt_on,                 // ALT-01: 备用速度是否生效(浮层双组高亮)
          altCurrent: r.alt_current || null, // ALT-01: 备用限速当前值(KiB/s)
          error: "",
        };
      }, { err: "error", errFallback: "状态获取失败" });
    },
    async submitSpeedOverride() {
      if (!this.speedOvReady || this.speedOverride.busy) return false;
      const up = Math.max(0, Math.round(Number(this.speedOverride.up)));
      const down = Math.max(0, Math.round(Number(this.speedOverride.down)));
      const text = `上传 ${this.fmtLimit(up) || "不限速"} / 下载 ${this.fmtLimit(down) || "不限速"}`;  // toast 保留"不限速"字样(TBL-02)
      return this._postWaitCmd(this.speedOverride, "busy", "/api/speed/override",
        { upload_kib: up, download_kib: down },
        {
          okMsg: `已临时覆盖全局限速: ${text}`,
          okMs: 3000,
          cmdFail: "限速覆盖失败",
          sendFail: "限速覆盖发送失败",
          onOk: async () => {
            this.speedOverride = { up: "", down: "", busy: false };
            await this.loadSpeedMode(true);  // 覆盖后刷新托管状态(qB 当前值已变)
          },
        });  // 返回 true 供弹窗判断成功关窗(SPD-04)
    },
    /* ---------------- 限速修改浮层(SPD-04; FX-08 改为**就近弹出**) ----------------
     * FX-08: 不再居中 + 遮罩弹出, 而是锚在点击的"限制速度"按钮附近向上弹(该方向输入框预聚焦),
     * 位置夹取到视口内(左右各留 12px), 不会跑到屏幕外; 点空白/Esc 关闭(无遮罩, 页面其余部分仍可操作)。
     * 打开时取一次 /api/speed/mode 并回填 qB 当前生效值(KiB/s, 0 = 不限); 提交沿用 submitSpeedOverride,
     * 成功即关窗, 失败留在窗内看报错并重试。
     */
    async openSpeedAt(ev, dir) {
      const el = ev && ev.currentTarget;
      const rect = el && el.getBoundingClientRect ? el.getBoundingClientRect() : null;
      const W = 380;  // 与 .speed-pop 的 width 单点一致
      const left = rect ? rect.left - SPEED_PAD : window.innerWidth - W - SPEED_PAD;
      this.speedAt = { left, dir: dir === "down" ? "down" : "up" };
      this.speedOpen = true;
      await this.loadSpeedMode(true);  // 开窗取当前值(强制刷新, 不吃缓存)
      this._fillSpeedFields();
      this.$nextTick(() => {
        // 只在当前方向预聚焦(点击"限制速度"就是为改这一方向), 并全选便于直接覆写
        const inp = this.$refs.speedPop && this.$refs.speedPop.querySelector("#sp-" + this.speedAt.dir);
        if (inp) {
          inp.focus();
          inp.select();
        }
      });
    },
    /* ALT-01: 用 /api/speed/mode 快照回填主/备两组输入(KiB/s; null -> 空串 = 未加载) */
    _fillSpeedFields() {
      const c = this.speedMode.current || {};
      const a = this.speedMode.altCurrent || {};
      const pick = (v) => (v === undefined || v === null ? "" : String(v));
      this.speedOverride.up = pick(c.upload_limit);
      this.speedOverride.down = pick(c.download_limit);
      this.speedAlt.up = pick(a.upload_limit);
      this.speedAlt.down = pick(a.download_limit);
    },
    /* 浮层内联定位: 只写 left(纵向由 CSS 锚定状态栏上缘), 并夹取到视口内(12px 边距显式传参) */
    speedPopStyle() {
      const FIT = window.AQB_OVERLAY_FIT; /* 几何单点(issue 26-10-20-2231), 方法内取别名 */
      const W = 380;
      return { left: FIT.clampAxis(this.speedAt.left, W, window.innerWidth, SPEED_PAD) + "px" };
    },
    /* 旧入口(居中弹窗)保留为薄包装: 无点击坐标时锚在视口右侧(第三方链接/键盘触发路径) */
    openSpeedDialog() {
      return this.openSpeedAt(null, "up");
    },
    closeSpeedDialog() {
      this.speedOpen = false;
      this.speedAt = { left: 0, dir: "up" };
    },
    /* Esc 链是否被浮层占用: lifecycle.js mounted 里 Esc 关闭链的**同一名单**(顺序无关, 只看有无)。
     * config_hub.js::hubOnKey 的「Esc 返回设置首页」用它守门 —— 链上还有层要关时, 该 Esc 先归
     * 关闭链, 不顺带把设置页退回首页。WARN: 新增浮层时两处同步: 那条 else-if 链 + 本方法(搜「escBusy」)。
     * 抽屉一项两处都写 **drawerVisible**(不是 drawer.open): 面板 DOM 已随抽屉退场(不在主内容页)
     * 时那条 Esc 该留给当前页面, 不是去关一张不在屏幕上的面板 —— 2026-10-06 面板加页面守卫后的连带改。 */
    escBusy() {
      return !!(this.modal.visible || this.addOpen || this.statsOpen || this.speedOpen || this.mgrOpen ||
        this.metaOpen || this.moveOpen || this.hrsOpen || this.filePrio.visible || this.drawerMenu.visible || this.drawerVisible || this.historyOpen ||
        this.headMenu.visible ||
        this.colMenuOpen || this.uiMenuOpen || this.searchHelpOpen || this.kbHelpOpen || this.errPanelOpen ||
        this.filterMenu ||
        this.menu.visible || this.selGroups.length || this.selMembers.length || this.expandedKey ||
        this.expandedShowEp || this.expandedShows.length);
    },
    async submitSpeedDialog() {
      const okMain = await this.submitSpeedOverride();
      const okAlt = await this.submitAltLimits();
      if (okMain && okAlt) {
        this.speedOpen = false;
        return;
      }
      // 任一组失败: 留在窗内重试 —— 主速成功时 speedOverride 已被清空, 必须重取 qB 当前值回填
      await this.loadSpeedMode(true);
      this._fillSpeedFields();
    },
    /* ---------------- ALT-01(计划 26-09-28-0037): 备用速度 ----------------
     * 模式切换(乌龟按钮)与限速修改(弹窗)是两个独立动作; 备用限速走 /api/speed/alt
     * (app/setPreferences alt_*), 与主速覆盖通道互不触碰。
     */
    /* S2 速度切乐观预翻转(计划 26-10-30-0610 §04 S2 / D2/D8): 点击当帧翻转高亮(0ms 级),
     * 回执 ok 转 hold(值保持到轮询确认, 防弹回), 四路失败回滚, 绝不留永久假状态。
     * speed_alt_toggle 实测回执 ~11ms 但 server_state 随 sync 快照翻转, 可见延迟均匀 [0,1.5s]
     * 随相位, 且无 SSE cmd/ver/truth 事件 —— 轮询是唯一确认通道, 预翻转是唯一修法。
     * 四路回滚(决策 D8):
     *   1. 回执 error        -> _postWaitCmd 返回 false -> _altOverrideClear(回落 server 值)
     *   2. 发送失败(异常)    -> 同上(catch 也返回 false, 已有 cmdFail/sendFail toast)
     *   3. 3s 无回执         -> _altOverrideArm(3000,false) 兜底清除(显示回落 server 值)
     *   4. ok 后 8s 未确认   -> _altOverrideArm(8000,true) 兜底清除(借 TRUTH_HOLD_MS 同款语义)
     * 确认单点在 polling.js statsServer 赋值处调 _altOverrideReconcile: refresh 带回的
     * use_alt_speed_limits 与 override 一致即清除 —— 确认延迟 = 距下个 sync 节拍相位(<=1.5s)。 */
    async toggleAltSpeed() {
      if (this.altToggling) return;
      // 点击时刻的 server 值: 既是回滚目标(prev), 也是成功措辞的基准 ——
      // !预翻转后 sbAltOn 已是新值, okMsg 再读 this.sbAltOn 会按"切换后"措辞(方向反了)
      const serverOn = !!(this.statsServer && this.statsServer.use_alt_speed_limits);
      this.altOverride = { value: !serverOn, prev: serverOn, ts: Date.now(), hold: false };
      this._altOverrideArm(3000, false);  // 路3: 3s 无回执 -> 回滚
      const ok = await this._postWaitCmd(this, "altToggling", "/api/speed/alt/toggle", {}, {
        okMsg: () => (serverOn ? "已切回主速度" : "已切换到备用速度(乌龟)"),  // 成功此刻取值: 按 server 切换前状态措辞
        cmdFail: "速度模式切换失败",
        sendFail: "切换请求发送失败",
      });
      /* 路1/路2: 回执 error / 发送失败 -> 回滚到 server 值。
       * !waitCmd 等待超时(40s)也落这里返回 false, 但那之前 3s 兜底已清除, 幂等 no-op。 */
      if (!ok) { this._altOverrideClear(); return; }
      // 路4 兜底重排: 回执 ok -> 转 hold(值覆盖保持到轮询确认), 期限从回执到达重算
      if (this.altOverride && !this.altOverride.hold) {
        this.altOverride.hold = true;
        this.altOverride.ts = Date.now();
        this._altOverrideArm(8000, true);  // 8s 未确认 -> 清除(回落 server 值)
      }
    },
    /* 兜底定时器(句柄挂实例不进 data: 非响应式, 同 _polls/_cmdWaiters 先例)。
     * needHold = 触发时要求的覆盖状态(3s 兜底要求仍未收到回执, 8s 兜底要求仍在 hold) ——
     * 状态已推进(回执到/已清除)即作废, 防旧定时器把新状态提前摘掉。 */
    _altOverrideArm(ms, needHold) {
      if (this._altOverrideTimer) clearTimeout(this._altOverrideTimer);
      this._altOverrideTimer = setTimeout(() => {
        this._altOverrideTimer = null;
        const ov = this.altOverride;
        if (!ov || ov.hold !== needHold) return;
        this._altOverrideClear();  // 回滚 = 摘覆盖, sbAltOn 自动回落 server 值(最后已知真值)
      }, ms);
    },
    _altOverrideClear() {
      if (this._altOverrideTimer) { clearTimeout(this._altOverrideTimer); this._altOverrideTimer = null; }
      this.altOverride = null;
    },
    /* 对账单点(polling.js statsServer 赋值处每轮调用): server 真值与 override 一致 = 翻转已
     * 落地, 覆盖即可摘除(摘除前后显示同值, 零观感跳变); 不一致继续 hold 防弹回
     * (快照带回命令前的旧值时, 摘了就会闪一下旧态 —— 与 pendingOps 的 hold 同理)。 */
    _altOverrideReconcile() {
      const ov = this.altOverride;
      if (!ov) return;
      const serverOn = !!(this.statsServer && this.statsServer.use_alt_speed_limits);
      if (serverOn === ov.value) this._altOverrideClear();
    },
    async submitAltLimits() {
      // 非空闸(issue 26-10-30-0622): 与 speedOvReady 同形 —— 两框任一为空 = 该组未确认,
      // 整组跳过不下发(返回 true 不挡主速组)。/api/speed/mode 读失败窗口 altCurrent=null
      // 时 _fillSpeedFields 把两框回空, 放行会让 Number("")||0 = 0 把备用限速静默写成
      // 0/0(不限速), 打破「未改动的组不下发」; 显式设不限速须输入 0, 与主速组同口径。
      if (this.speedAlt.up === "" || this.speedAlt.down === "" ||
        !Number.isFinite(Number(this.speedAlt.up)) || !Number.isFinite(Number(this.speedAlt.down))) return true;
      const up = Math.max(0, Math.round(Number(this.speedAlt.up) || 0));
      const down = Math.max(0, Math.round(Number(this.speedAlt.down) || 0));
      const c = this.speedMode.altCurrent || {};
      if (up === (c.upload_limit ?? -1) && down === (c.download_limit ?? -1)) return true;  // 未改动不下发
      return this._postWaitCmd(this.speedAlt, "busy", "/api/speed/alt",
        { upload_kib: up, download_kib: down },
        {
          okMsg: `已更新备用限速: 上 ${this.fmtLimit(up) || "不限速"} / 下载 ${this.fmtLimit(down) || "不限速"}`,
          okMs: 3000,
          cmdFail: "备用限速设置失败",
          sendFail: "备用限速发送失败",
        });
    },
    /* ---------------- 历史流量弹层(今日流量面板入口; 天/月/年切换 + 悬停取值) ---------------- */
    async openHistory() {
      this.historyOpen = true;
      await this.loadHistory();
    },
    async loadHistory() {
      await this._panelLoad(this, async () => {
        const data = await this.api("/api/traffic/history");
        this.historyData = data.history || [];
        // 26-10-17-1737 S1: 快照态随响应带回(off = 来源总开关关闭), 空态文案据此指到总开关
        this.historyState = data.state || "disabled";
      }, { loading: "historyLoading", err: "historyError", errFallback: "加载失败" });
    },
    /* 悬停追踪: 事件挂在 .hist-chart容器(mousemove), 指针 x 折算进 viewBox 坐标再换算
     * 桶索引 —— 连续无空隙; 旧版逐桶 enter/leave + 命中区只盖单柱的闪烁根因即在此 */
    histMove(ev) {
      if (!this.historyBuckets.length) return;
      const rect = ev.currentTarget.getBoundingClientRect();
      const g = this.histGeom;
      const x = ((ev.clientX - rect.left) / rect.width) * g.w;
      const idx = Math.floor((x - g.padL) / g.bw);
      this.histHoverIdx = Math.max(0, Math.min(this.historyBuckets.length - 1, idx));
    },
    histLeave() {
      this.histHoverIdx = -1;
    },
    /* 面积填充路径(折线下方淡渐染; 带参辅助放 methods —— pitfalls: computed不能加括号调用) */
    _histArea(key) {
      const pts = this.histSeries[key];
      if (!pts.length) return "";
      const base = (this.histGeom.padT + this.histGeom.chartH).toFixed(1);
      return `${this.histPaths[key]} L ${pts[pts.length - 1].x.toFixed(1)} ${base} L ${pts[0].x.toFixed(1)} ${base} Z`;
    },
  },
  computed: {
    /* 底部状态栏左侧常显统计摘要(TBL-08 修订; **FX-07 精简**): "统计不应该藏到弹出框中" ——
     * 取 /api/stats 的 server_state(纯内存快照, 与主轮询同周期静默同步)。
     * FX-07: 退役 本次 / 累计 / DHT 三项(本次与累计与"今日流量"口径重叠, DHT 属低频诊断),
     * 只留 连接 与 剩余 两个运行态指标; 今日流量改由模板单独渲染(数据源不同, 见 todayTraffic)。
     * server_state 未同步时返回空数组 → 显示未同步提示 */
    sbStats() {
      const s = this.statsServer;
      if (!s) return [];
      const items = [
        {
          key: "peers",
          icon: "#i-link",
          cls: "ico-peers",
          label: "连接",
          value: this.statVal(s.total_peer_connections),
          title: "连接状态: " + this.connText(s.connection_status),
        },
        {
          key: "disk",
          icon: "#i-hdd",
          cls: "ico-disk",
          label: "剩余",
          value: this.statVal(s.free_space_on_disk, (v) => this.fmtSize(v)),
          title: "qB 保存目录所在磁盘剩余空间",
        },
      ];
      return items;
    },
    /* 状态分布(按当前视图聚合): 旧版只读 this.groups, 种子页(groups 不被后端回传)
     * 与首次进入种子页(localStorage 持久化 view=torrent, 首轮 groups=[])时统计全空,
     * 「做种10 错误1」这一行消失 ⇒ 必须按 viewMode 各自取数:
     *   groups  →  各组 members + singles(同一来源 _member_view, kind 字段一致)
     *   torrents→  平铺数组(kind 字段同样由 _member_view 透出)
     *   shows   →  剧集节点的聚合 state(后端 _build_show_view 已取 min kind)
     * 顺序表与 kind 口径与 decorate.kindText 一致, 计数为 0 的类别被 filter 掉
     * !这张表同时是**状态筛选器下拉的选项源**(tpl/topbar.html 按 distSegments 渲染 v-for),
     *   所以新 kind 不进来 = 既统计不到也筛不到(2026-10-29 moving 补齐时补此注) */
    distSegments() {
      const order = ["seeding", "downloading", "checking", "paused", "error", "moving", "other"];
      const count = {};
      const bump = (k) => { if (k) count[k] = (count[k] || 0) + 1; };
      if (this.viewMode === "torrents") {
        for (const t of this.torrents) bump(t.kind);
      } else if (this.viewMode === "shows") {
        for (const s of (this.shows && this.shows.list) || []) {
          for (const season of (s.seasons || [])) {
            for (const ep of (season.episodes || [])) bump(ep.state);
          }
        }
      } else {
        for (const g of this.groups) for (const m of (g.members || [])) bump(m.kind);
        for (const r of this.singles) bump(r.kind);
      }
      const total = order.reduce((n, k) => n + (count[k] || 0), 0);
      if (!total) return [];
      return order.filter((k) => count[k]).map((k) => ({
        kind: k, count: count[k], pct: (count[k] / total) * 100, text: this.kindText(k),
      }));
    },
    distTotal() {
      return this.distSegments.reduce((n, s) => n + s.count, 0);
    },
    /* ---------------- 限速/流量快照(后端 SpeedCurveMixin 发布, 随 status 恒回传) ----------------
     * state: disabled(未启用限速曲线) / off(数据来源总开关关闭, 26-10-17-1737 S1) /
     *        ok / dry_run / stale(数据源不可用)
     * periods[].up|down 为**字节**; limit.target|actual 为 **KiB/s**(0 = 不限速, null = 该方向不管理)
     */
    traffic() {
      return this.status.traffic || { state: "disabled", periods: [], limit: {} };
    },
    trafficOn() {
      // off 与 disabled 同罪: 都不渲染"今日流量" pill —— 但语义不同(off = 来源总开关关了,
      // 曲线功能可能仍启用; 文案在历史弹层里按 state 区分, 见 popovers.html 的空态分支)
      return this.traffic.state !== "disabled" && this.traffic.state !== "off";
    },
    todayTraffic() {
      return (this.traffic.periods || []).find((p) => p.period === "day") || null;
    },
    /* 全局限速取数单点(R10-04): qB server_state 的全局限速键是 **dl_rate_limit / up_rate_limit**
     * (bytes/s, 0 = 不限速), **不是 dl_limit/up_limit** —— 后者是**单种子**级字段(TorrentRecord,
     * 见 mixins/web_view.py 的种子限速列)。前端曾读 s.dl_limit/s.up_limit ⇒ 恒 undefined ⇒
     * 状态栏"限制速度"永远显示 "—", 同时作速度染色分母时也恒缺失 ⇒ 色阶从未生效(连带故障)。
     * 现在状态栏文案、速度染色分母两处全部引用本单点, 改口径只改这里。
     * 单位维持 bytes/s(与 fmtSpeed 同源); 浮层内的编辑仍走 /api/speed/mode 的 KiB/s 口径,
     * 两套单位各在自己的显示层换算, 不在同一函数里混用。
     * 语义: null = 未知(字段缺失), 0 = 不限速。 */
    speedLimitBytes() {
      const s = this.statsServer || {};
      const pick = (v) => (v === null || v === undefined || v === "" ? null : Number(v) || 0);
      return { down: pick(s.dl_rate_limit), up: pick(s.up_rate_limit) };
    },
    /* 状态栏"限制速度"文案(决策 D3 的收窄版: **只取 qB 当前生效值**)。
     * 0 = 不限速 -> "不限"; 字段缺失 -> "—"(区分"未知"与"不限")。
     * 刻意不从限速曲线快照的 limit.actual 取数: 状态栏并列两个口径会变成"限速对照面板"
     * (那是已退役的信息栏形态); 曲线的目标/命中信息在限速浮层内的 .speed-mode-line 展示。 */
    sbLimits() {
      const { down, up } = this.speedLimitBytes;
      const f = (v) => (v === null ? "—" : (v ? this.fmtSpeed(v) : "不限"));
      return { down: f(down), up: f(up) };
    },
    /* ALT-01: 备用速度是否生效 —— 显示单点。S2(计划 26-10-30-0610 §04 S2 / D8)起改为
     * 「override 优先, server 兜底」: 有预翻转覆盖时显示 override 值, 否则读
     * statsServer.use_alt_speed_limits(qB server_state 随主轮询逐轮下发, 与规则引擎
     * sys.alt_speed_on 同源同键)。状态栏乌龟按钮高亮/title 与限速浮层双组高亮都引这里,
     * 预翻转与确认清除后自动跟随, 无需各自接线。 */
    sbAltOn() {
      if (this.altOverride) return !!this.altOverride.value;
      return !!(this.statsServer && this.statsServer.use_alt_speed_limits);
    },
    sbAltTitle() {
      return this.sbAltOn
        ? "备用速度生效中 · 点击切回主速度"
        : "主速度生效中 · 点击切换到备用速度(qB 乌龟)";
    },
    /* 限速对照行: 每个受管方向一行(该方向无曲线则不显示该行);
     * mismatch = 实际值已知且与命中目标不同 -> 前端据此"显示两个 + 原因"
     * tip 在**这里**算好(按方向取原因), 避免每个 pill 都展示全部方向的原因
     */
    limitRows() {
      const lim = this.traffic.limit || {};
      const target = lim.target || {}, actual = lim.actual || {}, reasons = lim.reasons || [];
      // 无方向特定原因时的默认说明(按快照状态区分: 试运行/数据不可用/正常)。
      // 必须在此内联为局部量 —— 本区段是 computed, 任何"看似方法的辅助函数"都会变成属性,
      // 在 computed 内以 this.xxx() 调用会抛 TypeError 导致整块渲染失败(2026-09-14 实测)。
      const fallback = this.traffic.state === "dry_run"
        ? "试运行(dry_run): 只显示命中限速, 不读取/不写入 qB"
        : this.traffic.state === "stale"
          ? "流量数据暂不可用, 限速沿用上一轮生效值"
          : "命中 = 曲线目标值, 实际 = qB 当前生效值";
      const rows = [];
      for (const [dir, label] of [["up", "上传"], ["down", "下载"]]) {
        const tg = target[dir];
        if (tg === null || tg === undefined) continue;
        const ac = actual[dir];
        const reason = reasons.find((r) => r.dir === dir) || null;
        const known = ac !== null && ac !== undefined;
        rows.push({
          dir,
          label,
          target: tg,
          actual: ac,
          mismatch: known && ac !== tg,
          reason,
          tip: reason ? reason.text : fallback,
        });
      }
      return rows;
    },
    /* 限速托管状态一行文案(FE-2C D2): 曲线托管中显示目标值; 未托管显示 qB 当前生效值 */
    speedModeLine() {
      const sm = this.speedMode;
      if (!sm.loaded) return "";
      if (sm.curveEnabled) {
        const t = sm.target || {};
        return `曲线托管中 · 目标 上传${this.fmtLimit(t.upload_kib) || "不限速"} / 下载${this.fmtLimit(t.download_kib) || "不限速"}`;
      }
      const c = sm.current || {};
      if (c.upload_limit === undefined && c.download_limit === undefined) return "未托管 · qB 限速未知";
      return `未托管 · qB 当前 上传${this.fmtLimit(c.upload_limit) || "不限速"} / 下载${this.fmtLimit(c.download_limit) || "不限速"}`;
    },
    /* 覆盖表单可提交: 两方向都已有数字(空串/非数字不放行 —— 后端两方向都设置, 漏传会被当 0=不限) */
    speedOvReady() {
      const o = this.speedOverride;
      return o.up !== "" && o.down !== "" && Number.isFinite(Number(o.up)) && Number.isFinite(Number(o.down));
    },
    /* ---------------- 历史流量(弹层): 按日原始行 -> 天(最近30)/月(近12)/年(全部)聚合 ---------------- */
    /* 粒度钮的 items(供 <aq-seg>): 直接转上面的单点, 不在这里再排一遍 —— 档位与文案的
     * 唯一事实是 HIST_GRAN_ITEMS, 下面的 historyBuckets 同源消费 historyGran。 */
    histGranItems() {
      return HIST_GRAN_ITEMS;
    },
    historyBuckets() {
      const rows = this.historyData || [];
      if (this.historyGran === "month") {
        const m = new Map();
        for (const r of rows) {
          const k = r.date.slice(0, 7);
          const cur = m.get(k) || { up: 0, down: 0 };
          cur.up += r.up;
          cur.down += r.down;
          m.set(k, cur);
        }
        return [...m.entries()].slice(-12).map(([k, v]) => ({ label: k.slice(2), tip: k, up: v.up, down: v.down }));
      }
      if (this.historyGran === "year") {
        const y = new Map();
        for (const r of rows) {
          const k = r.date.slice(0, 4);
          const cur = y.get(k) || { up: 0, down: 0 };
          cur.up += r.up;
          cur.down += r.down;
          y.set(k, cur);
        }
        return [...y.entries()].map(([k, v]) => ({ label: k, tip: `${k} 年`, up: v.up, down: v.down }));
      }
      return rows.slice(-30).map((r) => ({ label: r.date.slice(5), tip: r.date, up: r.up, down: r.down }));
    },
    historyMax() {
      return Math.max(1, ...this.historyBuckets.map((b) => Math.max(b.up, b.down)));
    },
    historySummary() {
      const rows = this.historyBuckets;
      const up = rows.reduce((s, b) => s + b.up, 0);
      const down = rows.reduce((s, b) => s + b.down, 0);
      const peak = rows.reduce((m, b) => Math.max(m, b.up + b.down), 0);
      const avg = rows.length ? (up + down) / rows.length : 0;
      return { up, down, peak, avg };
    },
    /* 折线图几何(常量 + 桶数派生): 无参 computed, 模板以属性访问(不加括号);
     * 尺寸放大(第七轮用户要求"改大一点"): 弹层 860px, viewBox 920×380 */
    histGeom() {
      const n = Math.max(1, this.historyBuckets.length);
      const w = 920, h = 380, padL = 64, padR = 16, padT = 16, padB = 30;
      const chartH = h - padT - padB;
      const bw = (w - padL - padR) / n;
      return { w, h, padL, padR, padT, padB, chartH, n, bw };
    },
    histViewBox() {
      return `0 0 ${this.histGeom.w} ${this.histGeom.h}`;
    },
    histTicks() {
      // Y 轴 5 档网格线(含 0 与最大值), 标签用与柱色无冲突的暗色
      const g = this.histGeom;
      const out = [];
      for (let k = 0; k <= 4; k++) {
        out.push({ y: g.padT + g.chartH * (1 - k / 4), label: k === 0 ? "0" : this.fmtSize((this.historyMax * k) / 4) });
      }
      return out;
    },
    histXTicks() {
      // X 轴标签均匀采样(最多 8 个, 防止柱多时文字重叠)
      const g = this.histGeom;
      const n = this.historyBuckets.length;
      const step = Math.max(1, Math.ceil(n / 8));
      const out = [];
      for (let i = 0; i < n; i += step) {
        out.push({ x: g.padL + i * g.bw + g.bw / 2, label: this.historyBuckets[i].label });
      }
      return out;
    },
    /* 双系列折线点(上传/下载): x = 槽位中心, y 按桶值比例 */
    histSeries() {
      const g = this.histGeom;
      const max = this.historyMax;
      const mk = (key) => this.historyBuckets.map((b, i) => ({
        x: g.padL + i * g.bw + g.bw / 2,
        y: g.padT + g.chartH * (1 - Math.min(1, b[key] / max)),
        v: b[key],
      }));
      return { up: mk("up"), down: mk("down") };
    },
    histPaths() {
      const toPath = (pts) => pts.map((p, i) => `${i ? "L" : "M"} ${p.x.toFixed(1)} ${p.y.toFixed(1)}`).join(" ");
      return { up: toPath(this.histSeries.up), down: toPath(this.histSeries.down) };
    },
    histAreaUp() {
      return this._histArea("up");
    },
    histAreaDown() {
      return this._histArea("down");
    },
    /* 悬停态(容器级 mousemove 连续追踪, 修复旧逐桶 enter/leave 在桶间空隙的闪烁):
     * crosshair x / 两系列高亮点 / tooltip 定位 */
      histHover() {
      if (this.histHoverIdx < 0 || this.histHoverIdx >= this.historyBuckets.length) return null;
      const g = this.histGeom;
      const i = this.histHoverIdx;
      return {
        bucket: this.historyBuckets[i],
        x: this.histSeries.up[i].x,
        up: this.histSeries.up[i],
        down: this.histSeries.down[i],
        leftPct: (this.histSeries.up[i].x / g.w) * 100,
      };
    },
  },
  watch: {
    /* 历史流量弹层开着时, 数据源快照一变就重拉(计划 26-10-16-0541 S7 接收面):
     * `traffic.ts` 变化 = 主循环重读了 dat(TM / 监视器工具输出)并重发了快照 —— 通知链
     * (工具阈值事件 -> /api/traffic/monitor/notify -> 主循环命令 -> 快照)的终点就在这行。
     * !只在弹层开着时才拉: 关着时多打一个 GET 只为刷一块看不见的图, 而弹层打开本来就会
     * loadHistory(openHistory); 顶栏 pill 不吃这条(它读 /api/state 的 traffic.periods, 主轮询自会带上)。 */
    "status.traffic.ts"(v) {
      if (this.historyOpen && v) this.loadHistory();
    },
    /* 分类下拉限高: 与添加种子三下拉同口径(add_torrent.js::_fitAddPop 的注释), 只是锚点是
     * meta 对话框自己的输入行 —— 开层(watcher metaCatMenu)/候选到位/过滤词变化三处都要重限,
     * 少一处就会出现"删字后候选涨回全量把对话框撑变形"。 */
    metaCatMenu(v) {
      if (v) this._fitAddPop("metaCatList");
    },
    metaCatInput() {
      if (this.metaCatMenu) this._fitAddPop("metaCatList");
    },
    metaCategories() {
      if (this.metaCatMenu) this._fitAddPop("metaCatList");
    },
  },
};

/* ---------------- <aq-modal-head> / <aq-modal>: 对话框外壳组件(收敛 issue 26-10-20-2231 / R23-A-02·A-03·A-08) ----------------
 * 模板在 tpl/dialog-shell.html(与 aq-combo-input 同范式: body 注入的 x-template, 不随根模板
 * 编译, 也不多包 DOM)。11 处对话框此前各手抄一份三段式外壳(modal-title 头 11 / modal-actions
 * 栏 10 / 遮罩关窗手势对 10), 现外壳一份 + 中部插槽; 本组件只贡献模板与 props, **零方法**:
 *   · 遮罩手势是根方法(读根 _maskArmed) —— 组件内一律 $root 调用(见 pitfalls/web-ui/
 *     component-ref-ownership: 全局 mixin 的方法域会骗过 this, 根数据只在根实例上)。
 *   · 关窗一律 :close(Function) + 可选 :close-args(Array)(通用确认框 resolveModal + [false]),
 *     不在模板里写内联箭头(同 closeHistory 注释口径); 开合用 :open 或调用点 v-if 均可。
 *   · body-class 空 = 中部裸插槽(hist/确认框不包 .add-dialog-body); $slots.actions 空 = 不渲染
 *     动作栏(hist 无底部条, 空条会多出 16px margin-top)。
 * WARN: 组件方法名全局唯一(_scan_mixin_wiring 扫 methods 段跨文件重名) —— 本组件零方法, 无重名面。
 * !本文件在 HTML 里必须排在 app.js 之前(app.js 末尾要 app.component 读 window.AQ_*)。 */
window.AQ_MODAL_HEAD_COMPONENT = {
  name: "aq-modal-head",
  props: {
    icon: { type: String, required: true },      // 标题图标(sprite href, 如 "#i-plus")
    iconClass: { type: String, default: "" },    // 图标附加类(stats ico-chart / hist ico-history)
    title: { type: String, default: "" },        // 标题文本(#title 插槽缺省时的回退)
    close: { type: Function, required: true },   // 关闭动作(遮罩/关闭钮共用一份)
    x: { type: Boolean, default: true },         // 关闭钮(通用确认框无 ✕)
  },
  template: "#tpl-aq-modal-head",
};
window.AQ_MODAL_COMPONENT = {
  name: "aq-modal",
  props: {
    open: { type: Boolean, default: true },      // 开合(调用点也可直接 v-if 在组件标签上)
    close: { type: Function, required: true },   // 关闭动作(maskCloseIfArmed(close, ...closeArgs))
    closeArgs: { type: Array, default: () => [] }, // 关闭动作实参(确认框 resolveModal + [false])
    icon: { type: String, default: "" },         // 标题图标(sprite href)
    iconClass: { type: String, default: "" },    // 图标附加类
    title: { type: String, default: "" },        // 标题文本
    label: { type: String, default: "" },        // aria-label; 空 = 不挂(hist/确认框同原状)
    widthClass: { default: "" },                 // .modal 附加类(字符串/数组/对象透传; move 的 pop-open 走数组)
    bodyClass: { type: String, default: "" },    // 中部包裹类; 空 = 裸插槽(不加空 wrapper)
    maskClass: { type: String, default: "modal-mask" }, // 遮罩附加类(add-dialog-mask / dir-browse-mask)
    x: { type: Boolean, default: true },         // 关闭钮(通用确认框无 ✕)
  },
  template: "#tpl-aq-modal",
};
