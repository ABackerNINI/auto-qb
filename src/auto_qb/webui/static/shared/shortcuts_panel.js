/* shortcuts_panel.js — R4 大文件拆分(计划 26-11-02-2342 §07)
 * 键盘快捷键 · 自定义面板(改键/冲突/重置/帮助浮层)。
 * 只搬方法定义, 实现逐行未改; 根文件已定义该域, 本片段在其后原地扩充(Object.assign)。
 * 加载序 = 四套皮肤 index.html 清单里紧跟根文件之后(与拆分前同一迭代替换序)。
 */
Object.assign(window.AQB_SHORTCUTS.methods, {
    /* ---------------- W6: 帮助浮层(H 组, Shift+Slash) ---------------- */
    kbOpenHelp() {
      this.kbHelpOpen = true;
    },
    kbGoSettings() {
      this.kbHelpOpen = false;
      // 必须链在 openSettings 之后: 首次进设置页 cfgLoad 成功会 hubRestore -> hubGo(view),
      // 同步先设的展开态会被那条路径的「进分区回折叠」冲掉(transfer_flow.js 同款先例)
      this.openSettings().then(() => {
        this.hubGo("webui");
        this.kbFullOpenPanel();  // 跳转即展开键位编辑覆盖层(拍板: 帮助浮层入口直达编辑面, 不让用户再找一次)
      });
    },
    /* ---------------- 键位编辑全屏覆盖层(2026-11-03 改版: 面板从独立「keys」分区并入 WebUI 卡) ----------------
     * 折叠块头「展开」即全屏覆盖层(HR 站点状态同款, 两态之间没有内嵌展开态): 覆盖层盖住配置树
     * actbar, 任一时刻视野里只有一个保存按钮。展开态不持久化, 每次进 webui 分区回折叠(hubGo 复位)。
     * 键位草稿只可能存在于覆盖层展开期 —— 关闭(kbFullClose)未保存先确认, 确认后回滚; */
    kbFullOpenPanel() {
      this.kbFullOpen = true;
      return this.kbPanelEnter();  // 首次展开才拉服务端真值(运行日志/HR「首次展开才拉」先例)
    },
    kbFullClose() {
      if (this.kbDirty()) {
        this.confirmDialog("键位改动还未保存",
          "关闭将放弃本次试用的改动; 点「保存」才会写入服务端(所有浏览器共享)。",
          { okText: "放弃并关闭", cancelText: "留在面板" }).then((ok) => {
          if (!ok) return;
          this.kbDraftRevert();
          this.kbFullOpen = false;
        });
        return;
      }
      this.kbRecordCancel();  // 非脏关闭出口也要摘录制监听(R5#232): 录制态点关闭/Esc, 脏路径有 kbDraftRevert 代劳, 本路不摘则 document 捕获期 _kbRecHandler 残留, 下一次任意按键被吞并静默提交成键位绑定
      this.kbFullOpen = false;
    },
    /* 折叠块头/首页卡共用的键位读数: N 条已自定义 / 默认键位(AQB_KEYS 适配器同步快照,
     * 非响应式 —— 与旧首页卡读数同口径, 滞后一次重渲染可接受) */
    kbReadout() {
      const doc = window.AQB_KEYS ? window.AQB_KEYS.load() : null;
      const n = doc ? Object.keys(doc.overrides || {}).length : 0;
      return n ? `${n} 条已自定义` : "默认键位";
    },
    /* ---------------- W6: 自定义面板(设置页「快捷键」分区) ----------------
     * 面板语义(计划 §5.2): 改动先本地生效(即时试用) -> 「保存」PUT 落盘; 离开未保存 -> 提示。
     * 草稿 = kbDraft(工作副本), 基准 = kbSaved(最近保存的服务端真值); 每次改稿同步进
     * AQB_KEYS(引擎即时生效)并失效 _kbTableCache。 */
    kbPanelEnter() {
      this.kbRecId = "";
      this.kbConflict = null;
      this.kbKeysLoading = true;
      this.kbKeysLoadFailed = false;
      return this._kbReloadKeys(true).then((ok) => {
        /* 装载失败态(R5#235): quiet=true 拉取失败时 kbSaved/kbDraft 只能落在默认表上,
         * 此后 kbSaveKeys 的 PUT 会以「默认+本次改动」整份覆盖服务端, 静默丢掉其它浏览器
         * 已保存的 overrides —— 置失败位禁用保存钮直堵覆盖路径, 退出路径 = 「重新加载」
         * (kbPanelEnter 重入: 进门先复位, 成功即恢复保存)。 */
        if (!ok) this.kbKeysLoadFailed = true;
        this.kbSaved = JSON.parse(JSON.stringify(window.AQB_KEYS.load()));
        this.kbDraft = JSON.parse(JSON.stringify(this.kbSaved));
        this.kbKeysLoading = false;
      });
    },
    /* 面板离开守卫(config_hub hubGo/hubBack 调): 键位编辑覆盖层开着且未保存时, 离开 webui
     * 分区先确认; 确认后回滚再继续导航。覆盖层开着时正常导航路径都被盖住, 本守卫是漏网路径
     * (如程序化跳转)的安全网 —— 关闭覆盖层自身的守卫在 kbFullClose */
    kbGuardLeave(target) {
      if (this.hub.view !== "webui" || target === "webui" || !this.kbFullOpen) return false;
      if (!this.kbDirty()) {
        this.kbRecordCancel();  // 非脏离开 webui 分区同样摘录制监听(R5#232): 本早退不拦导航, 残留的捕获期 handler 会跟着新页面吞按键
        this.kbFullOpen = false;  // 非脏早退同样收覆盖层(issue 26-11-08-0229 #11): 展开态不持久化, 不能残留到下次 hubGo 进 webui 才复位
        return false;
      }
      this.confirmDialog("键位改动还未保存",
        "离开将放弃本次试用的改动; 点「保存」才会写入服务端(所有浏览器共享)。",
        { okText: "放弃并离开", cancelText: "留在此页" }).then((ok) => {
        if (!ok) return;
        this.kbDraftRevert();
        this.kbFullOpen = false;  // 脏路径离开同样收覆盖层(issue 26-11-08-1621, 与 :76 非脏早退同式): 展开态不持久化, 不能残留到下次 hubGo 进 webui 才复位
        if (target === "hub") this.hubBack();
        else {
          this.hubCloseHelp();
          this.hub.view = target;
          window.scrollTo({ top: 0 });
        }
      });
      return true;
    },
    kbDirty() {
      if (!this.kbDraft || !this.kbSaved) return false;
      return JSON.stringify(this.kbDraft) !== JSON.stringify(this.kbSaved);
    },
    /* 注册表按 group 分组(保持声明序, 面板与帮助浮层共用) */
    kbGroups() {
      const out = [];
      for (const it of AQB_SHORTCUT_DEFS) if (!out.includes(it.group)) out.push(it.group);
      return out;
    },
    kbEntriesOf(group) {
      return AQB_SHORTCUT_DEFS.filter((it) => it.group === group);
    },
    /* 条目显示名(帮助浮层 / 设置页快捷键分区共用): 合并页签态下「详情面板」组五档重排到三张
     * 可见页签, 静态 label 会与页签栏对不上, 故在此按态改写 —— 前 3 档点名对应可见页签, 后 2 档
     * 标「合并态停用」; 非本组条目 / 未合并一律回落注册表静态 label(注册表仍是 label 单一事实源)。 */
    kbLabel(item) {
      if (!item) return "";
      if (item.group !== "详情面板" || !this._kbMergeTabsOn()) return item.label;
      const merged = {
        "drawer-tab-general": "详情面板 · 打开/切到 常规&内容",
        "drawer-tab-trackers": "详情面板 · 打开/切到 Tracker&用户",
        "drawer-tab-peers": "详情面板 · 打开/切到 流量",
        "drawer-tab-content": "详情面板 · 打开/切到内容页(合并态停用)",
        "drawer-tab-traffic": "详情面板 · 打开/切到流量页(合并态停用)",
      };
      return merged[item.id] || item.label;
    },
    /* 条目当前生效键位(草稿 ⊕ 模板基准): 与引擎 _kbTable 同口径, 空串 = 显式禁用 */
    kbSerialOf(item) {
      return kbSerialWithDraft(item, this.kbDraft);
    },
    kbIsOverridden(item) {
      return !!(this.kbDraft && this.kbDraft.overrides && Object.prototype.hasOwnProperty.call(this.kbDraft.overrides, item.id));
    },
    /* danger 条目的确认框标注: 三条确认框兜底动作标注"(有确认框)", 其余(超级做种)只标 WARN:(§08) */
    kbHasConfirm(item) {
      return ["act-delete", "act-recheck", "act-reannounce"].includes(item.id);
    },
    _kbApplyOverrides(overrides) {
      this.kbDraft = {
        schema_version: 1,
        template: (this.kbDraft && this.kbDraft.template) || "aqb-default",
        overrides,
      };
      window.AQB_KEYS.apply(JSON.parse(JSON.stringify(this.kbDraft)));  // 即时试用(引擎可见)
      this._kbTableCache = null;
    },
    /* 落一条键位: 回到模板默认即删掉 override(草稿最小化, 重置语义与之合一);
     * danger 条目绑裸键提示但允许(§08 v4: 确认框兜底)。 */
    _kbCommitSerial(item, serial) {
      const ov = { ...((this.kbDraft && this.kbDraft.overrides) || {}) };
      if (serial === item.def) delete ov[item.id];
      else ov[item.id] = serial;
      this._kbApplyOverrides(ov);
      if (item.danger && serial && !serial.includes("+")) {
        this.toast(`裸键绑定: 「${item.label}」是危险操作, 触发时有确认框兜底`, "warn", 5000);
      }
    },
    /* ---------------- W6: 录制器(VS Code 按下即录模式, §3.3/§5.2) ----------------
     * 捕获段(capture)监听: 录制态按键 preventDefault + stopPropagation, 引擎/退栈链/hubOnKey
     * 都收不到(§5.2 "引擎屏蔽层保证录制态不触发其它动作")。纯修饰键拒收; Esc 取消;
     * 黑名单当场拒绑; 冲突进三选一(交换/覆盖对方置空/取消)。 */
    kbRecord(id) {
      if (this.kbRecId === id) {
        this.kbRecordCancel();
        return;
      }
      this.kbConflict = null;
      this.kbRecId = id;
      if (this._kbRecHandler) document.removeEventListener("keydown", this._kbRecHandler, true);
      this._kbRecHandler = (e) => this._kbOnRecordKey(e);
      document.addEventListener("keydown", this._kbRecHandler, true);
    },
    kbRecordCancel() {
      this.kbRecId = "";
      if (this._kbRecHandler) {
        document.removeEventListener("keydown", this._kbRecHandler, true);
        this._kbRecHandler = null;
      }
    },
    _kbOnRecordKey(e) {
      e.preventDefault();
      e.stopPropagation();
      if (e.isComposing || e.keyCode === 229) return;  // IME 组合期不判定(§3.4)
      if (KB_MODIFIER_CODES.has(e.code)) return;       // 纯修饰键拒收(§3.3)
      if (e.key === "Escape") {
        this.kbRecordCancel();
        return;
      }
      if (e.repeat) return;
      const serial = kbSerializeEvent(e);
      const item = AQB_SHORTCUT_DEFS.find((it) => it.id === this.kbRecId);
      this.kbRecordCancel();
      if (!item) return;
      if (kbInBlacklist(serial)) {
        this.toast(`无法绑定: 浏览器保留该组合键(Ctrl+W/T/N/Q 等), ${kbDisplayName(serial)}`, "error", 6000);
        return;
      }
      const other = AQB_SHORTCUT_DEFS.find((it) => it.id !== item.id && !it.fixed && kbSerialWithDraft(it, this.kbDraft) === serial);
      if (other) {
        this.kbConflict = { id: item.id, serial, other: other.id, otherLabel: other.label };
        return;
      }
      this._kbCommitSerial(item, serial);
    },
    /* 冲突三选一(§5.2): 交换 = 对方拿我原来的键位; 覆盖 = 对方置空(显式禁用); 取消 = 不动 */
    kbConflictResolve(mode) {
      const c = this.kbConflict;
      if (!c) return;
      const item = AQB_SHORTCUT_DEFS.find((it) => it.id === c.id);
      const other = AQB_SHORTCUT_DEFS.find((it) => it.id === c.other);
      this.kbConflict = null;
      if (!item || !other) return;
      const ov = { ...((this.kbDraft && this.kbDraft.overrides) || {}) };
      if (mode === "swap") {
        const mine = kbSerialWithDraft(item, this.kbDraft);
        ov[item.id] = c.serial;
        if (mine === other.def) delete ov[other.id];
        else ov[other.id] = mine;
      } else if (mode === "steal") {
        ov[item.id] = c.serial;
        ov[other.id] = "";  // 对方置空 = 显式禁用(语义保留, 不能当缺省丢)
      } else {
        return;
      }
      this._kbApplyOverrides(ov);
    },
    kbDisableRow(item) {
      this._kbCommitSerial(item, "");  // 空串 = 显式禁用该动作(计划 §5.2)
    },
    kbResetRow(item) {
      this._kbCommitSerial(item, item.def);
    },
    kbResetAll() {
      this.kbRecordCancel();
      this.kbConflict = null;
      this._kbApplyOverrides({});  // 全部重置 = 清空派生, 回到纯模板(§4.7)
    },
    async kbSaveKeys() {
      const doc = JSON.parse(JSON.stringify(this.kbDraft));
      const r = await window.AQB_KEYS.save(doc, this.token);
      if (!r.ok) {
        this.toast("快捷键保存失败: " + r.error + "(本地已回滚)", "error", 8000);
        this.kbDraftRevert();
        return;
      }
      this.kbSaved = JSON.parse(JSON.stringify(doc));
      window.AQB_KEYS.apply(JSON.parse(JSON.stringify(doc)));
      this._kbTableCache = null;
      this.toast("快捷键已保存: 其它浏览器/标签刷新后生效", "ok", 3500);
    },
    kbDraftRevert() {
      this.kbRecordCancel();
      this.kbConflict = null;
      const base = this.kbSaved || AQB_KEYS_DEFAULT();
      this.kbDraft = JSON.parse(JSON.stringify(base));
      window.AQB_KEYS.apply(JSON.parse(JSON.stringify(base)));  // 回滚到最近保存的服务端真值
      this._kbTableCache = null;
    },
    /* 键位显示名(物理 code -> 人类键名, §3.3): 录制/面板/帮助浮层共用 */
    kbDisplayName(serial) {
      return kbDisplayName(serial);
    },
});
