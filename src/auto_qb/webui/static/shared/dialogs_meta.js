/* dialogs_meta.js — R4 大文件拆分(计划 26-11-02-2342 §07)
 * 弹窗 · 元信息分类/标签 / 日志 / 限速浮层。
 * 只搬方法定义, 实现逐行未改; 根文件已定义该域, 本片段在其后原地扩充(Object.assign)。
 * 加载序 = 四套皮肤 index.html 清单里紧跟根文件之后(与拆分前同一迭代替换序)。
 */
Object.assign(window.AQB_DIALOGS.methods, {
    async metaSetCategory(name) {
      name = (name || "").trim();
      this.metaCatMenu = false;
      this.metaCatHi = -1;
      if (name === this.metaCat && !this.metaCatDiff) return;  // 未变化: 静默返回(不给"已设置"的假反馈)
      if (name && !this.metaCategories.includes(name)) {
        try {
          await this.api("/api/categories", { method: "POST", body: JSON.stringify({ name }) });
        } catch (e) {
          if (!e.auth) this.toast(`分类创建失败: 「${name}」可能已存在, 继续尝试设置`, "warn", 4000);
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
        this.metaOpen || this.moveOpen || this.hrsOpen || this.kbFullOpen || this.relChain.open || this.filePrio.visible || this.drawerMenu.visible || this.drawerVisible || this.historyOpen ||
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
});
