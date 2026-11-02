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
      this.openSettings();
      this.hubGo("keys");
    },
    /* ---------------- W6: 自定义面板(设置页「快捷键」分区) ----------------
     * 面板语义(计划 §5.2): 改动先本地生效(即时试用) → 「保存」PUT 落盘; 离开未保存 → 提示。
     * 草稿 = kbDraft(工作副本), 基准 = kbSaved(最近保存的服务端真值); 每次改稿同步进
     * AQB_KEYS(引擎即时生效)并失效 _kbTableCache。 */
    kbPanelEnter() {
      this.kbRecId = "";
      this.kbConflict = null;
      this.kbKeysLoading = true;
      return this._kbReloadKeys(true).then(() => {
        this.kbSaved = JSON.parse(JSON.stringify(window.AQB_KEYS.load()));
        this.kbDraft = JSON.parse(JSON.stringify(this.kbSaved));
        this.kbKeysLoading = false;
      });
    },
    /* 面板离开守卫(config_hub hubGo/hubBack 调): 未保存先确认; 确认后回滚再继续导航 */
    kbGuardLeave(target) {
      if (this.hub.view !== "keys" || target === "keys" || !this.kbDirty()) return false;
      this.confirmDialog("快捷键改动还未保存",
        "离开将放弃本次试用的改动; 点「保存」才会写入服务端(所有浏览器共享)。",
        { okText: "放弃并离开", cancelText: "留在此页" }).then((ok) => {
        if (!ok) return;
        this.kbDraftRevert();
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
    /* danger 条目的确认框标注: 三条确认框兜底动作标注"(有确认框)", 其余(超级做种)只标 ⚠(§08) */
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
