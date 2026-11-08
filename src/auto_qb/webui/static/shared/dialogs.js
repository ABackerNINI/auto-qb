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
/* GTM 当日总量虚高告警(计划 26-11-03-1102 S7c / D5)的本机消警单点:
 * 只写 localStorage(不写服务端状态 —— 避免新增写路径), 键值 = 已确认的 gtm_anomaly.ts;
 * 展示窗口 24h(服务端只保留最近一轮, 前端按 ts 过滤防"陈年异常"长期占位)。 */
const GTM_ACK_KEY = "gtm.spike.ack";
const GTM_ALERT_TTL_MS = 24 * 3600 * 1000;

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
        // FIX-04b: 失败不清空已有数据(骨架常驻防闪烁); 仅首次加载失败保持 null -> 错误占位重试
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
    /* ---------------- GTM 告警横幅的两条交互(计划 26-11-03-1102 S7c) ----------------
     * 点击横幅 -> toast 完整文案(细节只在用户主动要看时才铺开, 状态栏保持一行);
     * × -> 本机消警: 键 = 当前 gtm_anomaly.ts, 同一 ts 不再显示、新 ts 自动重显。 */
    ackGtmAlert() {
      const a = this.gtmAnomaly;
      if (!a) return;
      try {
        localStorage.setItem(GTM_ACK_KEY, a.ts);
      } catch (e) {
        /* 隐私模式/存储被禁: 写失败就当本轮没消警(仍显示, 不静默假装已确认) */
        return;
      }
      /* ack 不在响应式数据里: 赋值同内容的新对象触发 gtmAlert 重算(与 refresh() 的整份
       * 替换同口径, 只多一次 patch), 否则横幅要等下一轮轮询才消失。 */
      this.status = { ...(this.status || {}) };
    },
    showGtmAlert() {
      const a = this.gtmAlert;
      if (a) this.toast(a.full, "warn", 8000);
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
     * 「置 busy -> try 请求 -> 失败反馈 -> finally 复位」这条骨架原先在 dialogs.js 与 config_hub.js
     * 手抄 19 遍; 漏 finally 的症状是面板永久转圈(见 pitfalls/web-ui/inflight-flag-no-timeout)。
     * 三个单点按反馈通道分家(反馈形态不同是族的真实边界, 不强并成一个万能 helper):
     *   _mgrRun      管理对话框写操作(R20-B-01): busy -> fn -> ok toast -> 重拉列表 -> 失败 toast(!auth) -> 复位
     *   _panelLoad   面板加载/槽回执(R20-B-02 + R20-C-15): busy(可选) -> 槽清空 -> fn -> 失败落槽或 toast -> 复位
     *   _postWaitCmd POST+waitCmd 三态 toast(R20-B-03): busy -> POST -> waitCmd -> ok / 命令失败 / 发送失败 -> 复位
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
    /* POST+waitCmd 三态 toast 骨架(三态判据单点): (1)ok 回执 -> okMsg(okMs 缺省 2500; 传函数 =
     * 成功此刻才取值, 供「按切换前状态措辞」的场景) (2)命令回执失败(已送达被拒) -> cmdFail: r.error(8000)
     * (3)请求本身失败(发送不出去) -> sendFail: e.message(auth 拦截静默, 交给登录框)。onPost 在
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
          // qB categories: {名字: {save_path, ...}} -> 行数组(名字字典序)
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
      if (!name) { this.toast("分类名称不能为空: 请输入名称后重试", "warn"); return; }
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
      // 支持中英文逗号分隔批量创建(空段剔除; 添加种子对话框的标签输入仍仅按半角逗号拆分, 口径未对齐)
      const tags = this.mgrNew.tags.split(/[,\uFF0C]/).map((t) => t.trim()).filter(Boolean);
      if (!tags.length) { this.toast("标签不能为空: 请至少输入一个标签", "warn"); return; }
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
      if (!savePath) { this.toast("保存路径不能为空: 请输入或选择一个目录", "warn"); return; }
      if (savePath === cur) { this.toast("未作修改: 输入与当前值一致", "ok", 2000); return; }
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
      // 入口闸 + 闸后同步占闸(与 metaSetCategory 同式, R4 终审增量): 新标签创建的 POST /api/tags
      // 在 _metaBulk 之前 await, 那段窗口 metaBusy 尚未由 _postWaitCmd 置真, 二次调用(双击/回车
      // 与点选竞态)漏闸并发 —— 过闸立即占闸; 空输入提前 return 就地复位, 成功路径的复位仍归
      // _metaBulk(_postWaitCmd) 既有收口。
      if (this.metaBusy) return;
      this.metaBusy = true;
      const tags = this.metaNewTags.split(/[,\uFF0C]/).map((t) => t.trim()).filter(Boolean);  // 中英文逗号, 与 submitMgrTags 同口径
      if (!tags.length) { this.toast("标签不能为空: 请至少输入一个标签", "warn"); this.metaBusy = false; return; }
      const fresh = tags.filter((t) => !this.metaTags.includes(t));
      if (fresh.length) {
        // 新标签定义先入队创建(定义列表/管理对话框可见); 已存在时创建失败不影响后续打标。
        // fresh 与下方 bulk 载荷均不去重(重复输入段原样投递): 后端链 _cmd_tags(torrent_detail.py)
        // -> create_tags 命令(commands_config.py) -> qB Web API createTags/addTags 对已存在与
        // 重复标签幂等(集合语义 no-op 不报错), 重复段无观感副作用, 故入口有意不去重
        try {
          await this.api("/api/tags", { method: "POST", body: JSON.stringify({ tags: fresh }) });
        } catch (e) {
          if (!e.auth) this.toast("标签创建失败: 可能已存在, 继续尝试打标", "warn", 4000);
        }
        this.metaTags = [...new Set([...this.metaTags, ...fresh])].sort((a, b) => a.localeCompare(b));
      }
      const ok = await this._metaBulk("add_tags", { tags }, `添加标签「${tags.join(", ")}」`);
      if (ok) {
        this.metaCommonTags = [...new Set([...this.metaCommonTags, ...tags])].sort((a, b) => a.localeCompare(b));
        this.metaNewTags = "";
      }
    },
  },
  computed: {
    /* 底部状态栏左侧常显统计摘要(TBL-08 修订; **FX-07 精简**): "统计不应该藏到弹出框中" ——
     * 取 /api/stats 的 server_state(纯内存快照, 与主轮询同周期静默同步)。
     * FX-07: 退役 本次 / 累计 / DHT 三项(本次与累计与"今日流量"口径重叠, DHT 属低频诊断),
     * 只留 连接 与 剩余 两个运行态指标; 今日流量改由模板单独渲染(数据源不同, 见 todayTraffic)。
     * server_state 未同步时返回空数组 -> 显示未同步提示 */
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
     * 「做种10 错误1」这一行消失 => 必须按 viewMode 各自取数:
     *   groups  ->  各组 members + singles(同一来源 _member_view, kind 字段一致)
     *   torrents->  平铺数组(kind 字段同样由 _member_view 透出)
     *   shows   ->  剧集节点的聚合 state(后端 _build_show_view 已取 min kind)
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
    /* ---------------- GTM 当日总量虚高告警(计划 26-11-03-1102 S7c / D5) ----------------
     * 数据源: traffic.gtm_anomaly(快照可选段, 来自 GTM /status.last_spike)。**判空矩阵**是
     * 版本兼容与失败降级的单点(旧后端根本没这个键, 旧 GTM 发 null):
     *   键缺失 / null / 非对象(含数组) / 缺 ts / ts 非字符串或不可解析 / items 为空或没有一条
     *   可用(需要 nic + up|down + 数值 rate_bps)-> null = 无异常 = 模板整组不渲染。
     * 只做形状与时间判定, 不读服务端状态、不发请求 => GTM 不可达时主界面完全不受影响(T30)。 */
    gtmAnomaly() {
      const raw = (this.traffic || {}).gtm_anomaly;
      if (!raw || typeof raw !== "object" || Array.isArray(raw)) return null;
      const ts = raw.ts;
      if (typeof ts !== "string" || !ts.trim()) return null;
      const t = Date.parse(ts);
      if (!Number.isFinite(t)) return null;
      const items = Array.isArray(raw.items)
        ? raw.items.filter((it) => it && typeof it === "object" && typeof it.nic === "string" && it.nic
          && (it.dir === "up" || it.dir === "down") && Number.isFinite(Number(it.rate_bps)))
        : [];
      if (!items.length) return null;
      return { ts, t, raw, items };
    },
    /* 横幅展示判定单点: 无异常 -> null; 本机已 ack 同一 ts -> null; 超过 24h -> null。
     * 未来 ts(本机时钟偏差)按新异常处理(不因负 age 静默丢掉真实告警)。
     * 短版只给 items[0], 多方向追加 +N; 完整版含 ts / delta+dt_s / threshold_bps, 点击横幅时看。 */
    gtmAlert() {
      const a = this.gtmAnomaly;
      if (!a) return null;
      let ack = null;
      try { ack = localStorage.getItem(GTM_ACK_KEY); } catch (e) { ack = null; }
      if (ack === a.ts) return null;  // 同一 ts 已消警; 新异常 ts 不同 => 自动重显
      const now = Number.isFinite(this.nowSec) ? this.nowSec * 1000 : Date.now();
      if (now - a.t > GTM_ALERT_TTL_MS) return null;  // 超过 24h: 不再占位(服务端只留最近一轮)
      // 本区段是 computed: 辅助函数一律内联为局部量(见 limitRows 的 2026-09-14 实测注)
      const num = (v) => (v === null || v === undefined || v === "" || !Number.isFinite(Number(v))
        ? null : Number(v));
      const dirText = (v) => (v === "down" ? "下行" : "上行");
      const d = new Date(a.t);
      const p = (n) => String(n).padStart(2, "0");
      const at = `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}`;
      const dtS = num(a.raw.dt_s);
      const rate = (v) => this.fmtSpeed(num(v) === null ? 0 : num(v));
      const rows = a.items.map((it) => {
        const delta = num(it.delta);
        return `${it.nic} ${dirText(it.dir)} ${delta === null ? "—" : this.fmtSize(delta)}`
          + `${dtS === null ? "" : "/" + dtS + "s"} ≈ ${rate(it.rate_bps)}`;
      });
      const thr = num(a.raw.threshold_bps);
      const first = a.items[0];
      const short = `${first.nic} ${dirText(first.dir)} ${rate(first.rate_bps)}`
        + (a.items.length > 1 ? ` +${a.items.length - 1}` : "");
      const full = `最近异常：${at} ${rows.join("；")}（阈值 ${thr === null ? "—" : this.fmtSpeed(thr)}），已照常入账`;
      return { ts: a.ts, short, full };
    },
    /* 全局限速取数单点(R10-04): qB server_state 的全局限速键是 **dl_rate_limit / up_rate_limit**
     * (bytes/s, 0 = 不限速), **不是 dl_limit/up_limit** —— 后者是**单种子**级字段(TorrentRecord,
     * 见 mixins/web_view.py 的种子限速列)。前端曾读 s.dl_limit/s.up_limit => 恒 undefined =>
     * 状态栏"限制速度"永远显示 "—", 同时作速度染色分母时也恒缺失 => 色阶从未生效(连带故障)。
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
    x: { type: Boolean, default: true },         // 关闭钮(通用确认框无 x)
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
    x: { type: Boolean, default: true },         // 关闭钮(通用确认框无 x)
  },
  template: "#tpl-aq-modal",
};
