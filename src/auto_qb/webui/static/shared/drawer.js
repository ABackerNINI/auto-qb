/* auto-qb WEB UI · 种子详情抽屉(通用/Tracker/文件/Peer 与就地编辑)
 *
 * app.js 按域拆分出的片段(2026-09-20)。约定与 config_editor.js / config_rules.js 同一范式:
 * 挂到 window.AQB_DRAWER, 由 app.js 末尾 app.mixin(window.AQB_DRAWER) 注入同一个 Vue 实例 ——
 * 方法体里的 this 仍是那个组件实例, 跨模块互调与拆分前完全等价。
 *
 * ❗本文件在 HTML 里必须排在 app.js **之前**(app.js 末尾要读 window.AQB_DRAWER);
 *   用到的列模型常量(TABLE_COLUMNS / MIN_COL_PX / STATE_RANK …)仍单点定义在 app.js 顶部。
 */
window.AQB_DRAWER = {
  methods: {
    /* 自动种子管理开关(种子页右键 R2 补遗): 复用 torrentCmd 回执链 */
    autoTmmToggle() {
      const m = this.menuTorrent();
      this.torrentCmd("auto-tmm", { enable: !m.auto_tmm }, m.auto_tmm ? "关闭自动种子管理" : "开启自动种子管理");
    },
    /* 右键菜单当前种子(SEED_ITEM 完整字段): 供菜单项动态文案/开关初值 */
    menuTorrent() {
      return this.memberByHash.get(this.menu.hash) || {};
    },
    /* 种子控制命令(R2): 带 body 的单种命令(校验/超级做种/强制开始/队列) —— 走既有回执链 */
    async torrentCmd(action, body = null, okText = "") {
      this.menu.visible = false;
      const hash = this.menu.hash;
      if (!hash) return;
      try {
        const resp = await this.api(`/api/torrents/${hash}/${action}`, {
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
    /* 抽屉内命令: 与 torrentCmd 同链路, 但 hash 取自抽屉(菜单未开时 menu.hash 为空) */
    drawerCmd(action, body = null, okText = "") {
      this.menu.hash = this.drawer.hash;
      this.torrentCmd(action, body, okText);
    },
    /* ---------------- 种子编辑对话框(D 轮): 限速/分享率限制/移动/重命名 ----------------
     * 统一形态: 多字段 .modal(modal.fields) + 回执 toast; 预填当前值, 空输入 = 不修改。
     * hash 约定: 菜单调用不传参取 menu.hash, 抽屉调用显式传 drawer.hash(与 drawerCmd 同约定)。 */
    _editTargetHash(h) {
      const hash = h || this.menu.hash;
      this.menu.visible = false;
      return hash || "";
    },
    /* 编辑类对话框取当前值: 抽屉已开且同一 hash 直接用 drawer.detail, 否则现拉一次详情 */
    async _editDetail(hash) {
      if (this.drawer.open && this.drawer.hash === hash && this.drawer.detail) return this.drawer.detail;
      try {
        const r = await this.api(`/api/torrents/${hash}`);
        return (r && r.torrent) || null;
      } catch (e) {
        if (!e.auth) this.toast("当前值获取失败: " + e.message, "error");
        return null;
      }
    },
    /* 编辑类命令统一投递: api + waitCmd 回执 + toast 三态; 成功后按动作刷新抽屉对应页签数据 */
    async _editPost(hash, action, body, okText) {
      try {
        const resp = await this.api(`/api/torrents/${hash}/${action}`, {
          method: "POST",
          body: JSON.stringify(body),
        });
        const r = await this.waitCmd(resp.cmd_id);
        if (r.ok) {
          this.toast(`已执行: ${okText}`, "ok", 2500);
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
    /* 限速…: 上传/下载两输入(KiB/s; 空=不改, 0=不限) → POST limits(×1024 转 bytes, 0 原样传) */
    async editLimits(h = "") {
      const hash = this._editTargetHash(h);
      if (!hash) return;
      const d = await this._editDetail(hash);
      const kiB = (bytes) => (bytes > 0 ? String(Math.round(bytes / 1024)) : "");  // 不限/未设(≤0)留空
      const res = await this._openModal({
        title: "限速",
        body: "设置该种子的上传/下载速度上限(KiB/s)。留空 = 保持不变, 填 0 = 不限速。",
        fields: [
          { key: "up", label: "上传上限(KiB/s)", value: d ? kiB(d.up_limit) : "", placeholder: "留空不修改, 0 = 不限" },
          { key: "dl", label: "下载上限(KiB/s)", value: d ? kiB(d.dl_limit) : "", placeholder: "留空不修改, 0 = 不限" },
        ],
        okText: "应用", cancelText: "取消",
      });
      if (!res) return;
      const body = {};
      for (const [k, key] of [["up", "up_limit"], ["dl", "dl_limit"]]) {
        if (res[k] === "") continue;  // 空 = 不修改
        const n = Number(res[k]);
        if (!Number.isFinite(n) || n < 0) {
          this.toast("限速需为非负数字(KiB/s)", "warn");
          return;
        }
        body[key] = Math.round(n * 1024);  // KiB/s → bytes/s; 0 原样传(后端语义 = 不限)
      }
      if (!Object.keys(body).length) {
        this.toast("未作修改", "ok", 2000);
        return;
      }
      await this._editPost(hash, "limits", body, "限速已更新");
    },
    /* 分享率限制…: 分享率/做种时长(h)/不活跃做种时长(h) → POST share-limits(-1 = 恢复全局默认) */
    async editShareLimits(h = "") {
      const hash = this._editTargetHash(h);
      if (!hash) return;
      const d = await this._editDetail(hash);
      const hrs = (sec) => (sec > 0 ? String(Math.round((sec / 3600) * 100) / 100) : "");  // -1/0(未设)留空
      const res = await this._openModal({
        title: "分享率限制",
        body: "达到任一限制后该种子将停止做种。留空 = 保持不变, 填 -1 = 恢复全局默认。",
        fields: [
          { key: "ratio", label: "分享率上限", value: d && d.max_ratio >= 0 ? String(d.max_ratio) : "", placeholder: "留空不修改, -1 = 全局" },
          { key: "time", label: "做种时长上限(小时)", value: d ? hrs(d.max_seeding_time) : "", placeholder: "留空不修改, -1 = 全局" },
          { key: "inactive", label: "不活跃做种上限(小时)", value: d ? hrs(d.max_inactive_seeding_time) : "", placeholder: "留空不修改, -1 = 全局" },
        ],
        okText: "应用", cancelText: "取消",
      });
      if (!res) return;
      const body = {};
      if (res.ratio !== "") {
        const n = Number(res.ratio);
        if (!Number.isFinite(n) || (n < 0 && n !== -1)) {
          this.toast("分享率需为非负数字(或 -1)", "warn");
          return;
        }
        body.ratio_limit = n;
      }
      for (const [k, key] of [["time", "seeding_time_limit"], ["inactive", "inactive_seeding_time_limit"]]) {
        if (res[k] === "") continue;  // 空 = 不修改
        const n = Number(res[k]);
        if (!Number.isFinite(n) || (n < 0 && n !== -1)) {
          this.toast("时长需为非负小时数(或 -1)", "warn");
          return;
        }
        body[key] = n === -1 ? -1 : Math.round(n * 3600);  // 小时 → 秒; -1 原样(未设/全局)
      }
      if (!Object.keys(body).length) {
        this.toast("未作修改", "ok", 2000);
        return;
      }
      await this._editPost(hash, "share-limits", body, "分享率限制已更新");
    },
    /* 移动…: 新保存路径输入(确认文案注明离开辅种组) → POST location */
    async editMove(h = "") {
      const hash = this._editTargetHash(h);
      if (!hash) return;
      const d = await this._editDetail(hash);
      const res = await this._openModal({
        title: "移动种子",
        body: "将种子文件移动到新路径。注意: 移动后该种子将离开当前辅种组。",
        fields: [{ key: "location", label: "新保存路径", value: d ? d.save_path || "" : "", placeholder: "D:\\downloads\\target" }],
        okText: "移动", cancelText: "取消",
      });
      if (!res) return;
      if (!res.location) {
        this.toast("路径不能为空", "warn");
        return;
      }
      await this._editPost(hash, "location", { location: res.location }, "已移动");
    },
    /* 重命名…: 种子显示名(不改磁盘文件名) → POST rename */
    async editRename(h = "") {
      const hash = this._editTargetHash(h);
      if (!hash) return;
      const d = await this._editDetail(hash);
      const res = await this._openModal({
        title: "重命名种子",
        body: "修改种子显示名(不影响磁盘上的文件/目录名)。",
        fields: [{ key: "name", label: "新名称", value: d ? d.name || "" : "", placeholder: "新种子名" }],
        okText: "重命名", cancelText: "取消",
      });
      if (!res) return;
      if (!res.name) {
        this.toast("名称不能为空", "warn");
        return;
      }
      await this._editPost(hash, "rename", { name: res.name }, "已重命名");
    },
    /* ---------------- 抽屉 Tracker 页签编辑(D 轮): 添加/编辑/删除 ---------------- */
    async trackerAdd() {
      const hash = this.drawer.hash;
      if (!hash) return;
      const raw = await this.promptDialog("添加 Tracker", "", {
        placeholder: "announce URL(多条用换行/逗号分隔)", okText: "添加",
      });
      if (raw === null) return;
      const urls = raw.split(/[\s,]+/).map((s) => s.trim()).filter(Boolean);
      if (!urls.length) {
        this.toast("请输入至少一条 tracker URL", "warn");
        return;
      }
      await this._editPost(hash, "trackers/add", { urls }, urls.length > 1 ? `已添加 ${urls.length} 条 tracker` : "tracker 已添加");
    },
    async trackerEdit(url) {
      const hash = this.drawer.hash;
      if (!hash) return;
      const nu = await this.promptDialog("编辑 Tracker", url, { placeholder: "新的 announce URL", okText: "保存" });
      if (nu === null) return;
      const newUrl = String(nu || "").trim();
      if (!newUrl) {
        this.toast("URL 不能为空", "warn");
        return;
      }
      if (newUrl === url) {
        this.toast("未作修改", "ok", 2000);
        return;
      }
      await this._editPost(hash, "trackers/edit", { orig_url: url, new_url: newUrl }, "tracker 已更新");
    },
    async trackerRemove(url) {
      const hash = this.drawer.hash;
      if (!hash) return;
      const ok = await this.confirmDialog("删除 Tracker", `将删除该 tracker: ${url}`, { okText: "删除", danger: true });
      if (!ok) return;
      await this._editPost(hash, "trackers/remove", { url }, "tracker 已删除");
    },
    /* ---------------- 抽屉内容页签编辑(D 轮): 行选中/优先级/文件重命名 ---------------- */
    /* 行点击选中(文件/目录均可): 再点同一行取消 —— 顶部"重命名…"的作用对象 */
    fileRowSelect(r) {
      this.drawerSelPath = this.drawerSelPath === r.path ? "" : r.path;
    },
    /* 文件优先级小菜单: 锚定单元格下方, 视口吸附(@click.stop 防止开菜单的点击立即被窗口关闭) */
    openFilePrio(ev, index) {
      this._markCtxSource(ev);
      const rect = ev.currentTarget.getBoundingClientRect();
      const w = 150, h = 176;
      this.filePrio = {
        visible: true, index,
        x: Math.min(Math.max(8, rect.left), Math.max(8, window.innerWidth - w - 8)),
        y: Math.min(rect.bottom + 4, Math.max(8, window.innerHeight - h - 8)),
      };
    },
    /* 优先级 4 档(0=跳过 1=普通 6=高 7=最高) → POST files/priority(单文件) */
    async setFilePriority(p) {
      this.filePrio.visible = false;
      const index = this.filePrio.index;
      const hash = this.drawer.hash;
      if (!hash || index < 0) return;
      const label = { 0: "跳过", 1: "普通", 6: "高", 7: "最高" }[p] || String(p);
      await this._editPost(hash, "files/priority", { indices: [index], priority: p }, `优先级已设为「${label}」`);
    },
    /* 文件/目录重命名(选中行; 单文件种子免选): POST rename-fs, new_path = 原目录前缀 + 新名 */
    async renameFileRow() {
      const hash = this.drawer.hash;
      if (!hash) return;
      const rows = this.drawerFileRows();
      let row = rows.find((r) => r.path === this.drawerSelPath);
      if (!row && rows.length === 1) row = rows[0];  // 单文件种子: 免选中直接改
      if (!row) {
        this.toast("请先点击选中要重命名的文件或目录", "warn");
        return;
      }
      const res = await this.promptDialog(row.dir ? "重命名目录" : "重命名文件", row.name, {
        body: `当前路径: ${row.path}`,
        okText: "重命名",
      });
      if (res === null) return;
      const nn = String(res || "").trim();
      if (!nn) {
        this.toast("名称不能为空", "warn");
        return;
      }
      if (nn === row.name) {
        this.toast("未作修改", "ok", 2000);
        return;
      }
      const parent = row.path.includes("/") ? row.path.slice(0, row.path.lastIndexOf("/") + 1) : "";
      await this._editPost(hash, "rename-fs", {
        old_path: row.path, new_path: parent + nn, is_folder: !!row.dir,
      }, row.dir ? "目录已重命名" : "文件已重命名");
    },
    async copyTorrentInfo(field) {
      this.menu.visible = false;
      const hash = this.menu.hash;
      const m = this.memberByHash.get(hash);
      if (!m) return;
      let value = field === "name" ? m.name
        : field === "hash" ? (m.infohash_v1 || m.hash)
          : (m.magnet_uri || "");
      /* magnet_uri **不在成员索引里**: 只有种子页的平铺 SEED_ITEM 数组带它(见 memberByHash
       * 注释), 而索引优先取分组/未归组条目 —— 那两份都出自后端 _member_view, 没有该字段
       * ⇒ 索引条目恒为 undefined, "复制磁力"曾 100% 落到"该种子没有 magnet 链接"(BUG-9)。
       * 改成**点的时候按需取一次详情**(复用 _editDetail: 抽屉已开则连请求都不发),
       * 而不是给每 1.5~3s 一轮的响应体加一个几十字节的字段(3000 种子 ≈ +0.6MB/轮)。 */
      if (!value && field === "magnet") {
        const d = await this._editDetail(hash);
        value = (d && d.magnet_uri) || "";
      }
      if (!value) {
        this.toast("该种子没有 magnet 链接", "warn");
        return;
      }
      const label = field === "name" ? "种子名" : field === "hash" ? "信息哈希" : "magnet 链接";
      this._copyText(value, label);
    },
    /* ---------------- 种子详情抽屉(R1B: WEB UI 替代 qB 界面的详情面板) ----------------
     * 数据: /api/torrents/{hash} 全字段详情; /trackers /files /peers 按需拉取。
     * trackers/peers 在对应 tab 激活期间 3s 轮询(页面隐藏时暂停), 关闭抽屉即停 —— 不进主循环 tick;
     * General 分组行在 drawerGeneralSections 预格式化(qB 哨兵 -1/-2/8640000 在此统一翻译)。 */
    async openTorrentDrawer(hash) {
      this.menu.visible = false;
      this._stopDrawerPoll();
      this.drawer = {
        open: true, hash, tab: "general", loading: true, error: "",
        detail: null, trackers: [], files: [], peers: { peers: [] },
        trackersLoading: false, filesLoading: false, peersLoading: false,
      };
      await this._fetchDrawerDetail();
    },
    closeDrawer() {
      this.drawer.open = false;
      this.filePrio.visible = false;
      this.drawerSelPath = "";
      this._stopDrawerPoll();
    },
    _stopDrawerPoll() {
      if (this._drawerTimer) {
        clearInterval(this._drawerTimer);
        this._drawerTimer = null;
      }
    },
    _startDrawerPoll() {
      this._stopDrawerPoll();
      // P1-4: 3s → 5s。抽屉是观察用途, peers/trackers 秒级变化对操作没有意义;
      // 而每次轮询都要 Web 线程直连 qB(peers 走 sync/torrentPeers, 响应体随 peer 数增长),
      // 在主循环之外额外占用 qB。5s 仍远快于人工观察节奏。
      this._drawerTimer = setInterval(() => {
        if (!this.drawer.open || document.hidden) return;
        if (this.drawer.tab === "trackers") this._fetchDrawerTrackers(true);
        else if (this.drawer.tab === "peers") this._fetchDrawerPeers(true);
      }, 5000);
    },
    async _fetchDrawerDetail() {
      this.drawer.loading = true;
      this.drawer.error = "";
      try {
        const r = await this.api(`/api/torrents/${this.drawer.hash}`);
        this.drawer.detail = (r && r.torrent) || null;
        if (!this.drawer.detail) this.drawer.error = "种子不存在或已被删除";
      } catch (e) {
        if (!e.auth) this.drawer.error = e.message || "详情获取失败";
      } finally {
        this.drawer.loading = false;
      }
    },
    async _fetchDrawerTrackers(silent = false) {
      if (!silent) this.drawer.trackersLoading = true;
      try {
        const r = await this.api(`/api/torrents/${this.drawer.hash}/trackers`);
        this.drawer.trackers = Array.isArray(r) ? r : [];
      } catch (e) {
        if (!silent && !e.auth) this.toast("tracker 列表获取失败: " + e.message, "error");
      } finally {
        this.drawer.trackersLoading = false;
      }
    },
    async _fetchDrawerFiles(silent = false) {
      if (!silent) this.drawer.filesLoading = true;
      try {
        const r = await this.api(`/api/torrents/${this.drawer.hash}/files`);
        this.drawer.files = Array.isArray(r) ? r : [];
      } catch (e) {
        if (!silent && !e.auth) this.toast("文件列表获取失败: " + e.message, "error");
      } finally {
        this.drawer.filesLoading = false;
      }
    },
    async _fetchDrawerPeers(silent = false) {
      if (!silent) this.drawer.peersLoading = true;
      try {
        const r = await this.api(`/api/torrents/${this.drawer.hash}/peers`);
        this.drawer.peers = r || { peers: [] };
      } catch (e) {
        if (!silent && !e.auth) this.toast("peer 列表获取失败: " + e.message, "error");
      } finally {
        this.drawer.peersLoading = false;
      }
    },
    /* tab 切换: general 重新拉详情(反映最新状态); trackers/peers 拉一次并启动轮询; content 拉一次 */
    drawerTab(tab) {
      if (this.drawer.tab === tab) return;
      this.drawer.tab = tab;
      this.filePrio.visible = false;  // 换页签时收起文件优先级小菜单(内容页签专属)
      this._stopDrawerPoll();
      if (tab === "general") this._fetchDrawerDetail();
      else if (tab === "trackers") {
        this._fetchDrawerTrackers();
        this._startDrawerPoll();
      } else if (tab === "peers") {
        this._fetchDrawerPeers();
        this._startDrawerPoll();
      } else if (tab === "content") this._fetchDrawerFiles();
    },
    /* 抽屉头部动作: 复用 actTorrent(它读 menu.hash 并自带回执/toast) */
    drawerAct(action) {
      this.menu.hash = this.drawer.hash;
      this.actTorrent(action);
    },
    /* 抽屉删除: 复用 delTorrent(确认框流程一致); 删除成功(成员消失)后自动收起抽屉 */
    drawerDel() {
      this.menu.hash = this.drawer.hash;
      this._drawerDeletePending = true;
      Promise.resolve(this.delTorrent()).then(() => {
        if (this._drawerDeletePending && !this.memberByHash.get(this.drawer.hash)) this.closeDrawer();
        this._drawerDeletePending = false;
      });
    },
    /* General tab 分组行(预格式化): qB 哨兵在此统一翻译 —— -1=从未/未设, 8640000=无 ETA。
     * W5-RFB-01 展示重构: 分组重组为 基础/传输/时间/路径, 每行带 sprite 图标(icon)供字段行渲染(f-row) */
    drawerGeneralSections() {
      const d = this.drawer.detail;
      if (!d) return [];
      const dur = (v, dash) => (v === null || v === undefined || v < 0) ? (dash || "未设") : this.fmtDuration(v);
      const ts = (v) => this.fmtTs(v) || "—";  // 抽屉保留"—"(TBL-01 只改主页面表格)
      const size = (v) => this.fmtSizeOrDash(v) || "—";
      const yn = (v) => (v ? "是" : "否");
      const lim = (v) => (v === null || v === undefined || v < 0) ? "未设" : (v === 0 ? "不限" : this.fmtDuration(v));
      return [
        {
          title: "基础",
          sum: `容量 ${size(d.size)} · 分享率 ${(d.ratio ?? 0).toFixed(2)}`,
          rows: [
            { icon: "#i-percent", label: "进度", text: `${((d.progress || 0) * 100).toFixed(1)}%` },
            { icon: "#i-hdd", label: "大小", text: size(d.size) },
            { icon: "#i-layers", label: "总大小", text: size(d.total_size) },
            { icon: "#i-download", label: "剩余量", text: size(d.amount_left) },
            { icon: "#i-pulse", label: "可用性", text: (d.availability ?? 0).toFixed(2) },
            { icon: "#i-percent", label: "分享率", text: (d.ratio ?? 0).toFixed(3) },
            { icon: "#i-lock", label: "私有", text: yn(d.private) },
            // FX-22: 哈希/备注可能极长 -> 块行 + 右侧"复制"(不再只能悬停看 title)
            { icon: "#i-hash", label: "信息哈希 v1", text: d.infohash_v1 || "—", mono: true, wide: true, act: "copy" },
            { icon: "#i-hash", label: "信息哈希 v2", text: d.infohash_v2 || "—", mono: true, wide: true, act: "copy" },
            { icon: "#i-columns", label: "分块", text: d.piece_size ? `${d.pieces_have ?? 0} / ${d.pieces_num ?? 0} × ${this.fmtSize(d.piece_size)}` : "—" },
            { icon: "#i-info", label: "已含元数据", text: yn(d.has_metadata) },
            { icon: "#i-calendar", label: "创建于", text: ts(d.creation_date) },
            { icon: "#i-settings", label: "创建工具", text: d.created_by || "—" },
            { icon: "#i-list", label: "备注", text: d.comment || "—", wide: true },
          ],
        },
        {
          title: "传输",
          sum: `实时 ↓${this.fmtSpeedOrDash(d.dlspeed) || "—"} ↑${this.fmtSpeedOrDash(d.upspeed) || "—"}`,
          rows: [
            { icon: "#i-download", label: "下载速度", text: this.fmtSpeedOrDash(d.dlspeed) || "—" },
            { icon: "#i-upload", label: "上传速度", text: this.fmtSpeedOrDash(d.upspeed) || "—" },
            { icon: "#i-hourglass", label: "ETA", text: this.fmtEta(d.eta) || "—" },
            { icon: "#i-download", label: "已下载", text: size(d.downloaded) },
            { icon: "#i-upload", label: "已上传", text: size(d.uploaded) },
            { icon: "#i-download", label: "本次会话下载", text: size(d.downloaded_session) },
            { icon: "#i-upload", label: "本次会话上传", text: size(d.uploaded_session) },
            { icon: "#i-warn", label: "浪费", text: size(d.total_wasted) },
            { icon: "#i-arrow-up", label: "做种", text: String(d.num_seeds ?? 0) },
            { icon: "#i-arrow-down", label: "用户(下载)", text: String(d.num_leechs ?? 0) },
            { icon: "#i-globe", label: "完整/下载中", text: `${d.num_complete ?? 0} / ${d.num_incomplete ?? 0}` },
            { icon: "#i-globe", label: "tracker 数", text: String(d.trackers_count ?? 0) },
            { icon: "#i-link", label: "连接数", text: `${d.connections_count ?? 0} / ${d.connections_limit ?? 0}` },
            { icon: "#i-refresh", label: "下次汇报", text: dur(d.reannounce_in || d.reannounce, "—") },
            { icon: "#i-x-circle", label: "tracker 错误", text: yn(d.has_tracker_error) },
            { icon: "#i-warn", label: "tracker 警告", text: yn(d.has_tracker_warning) },
            { icon: "#i-percent", label: "分享率限制", text: (d.max_ratio ?? -1) < 0 ? "未设" : d.max_ratio.toFixed(2) },
            { icon: "#i-timer", label: "做种时长限制", text: lim(d.max_seeding_time) },
            { icon: "#i-timer", label: "不活跃做种限制", text: lim(d.max_inactive_seeding_time) },
            { icon: "#i-bolt", label: "限制动作", text: d.share_limit_action || "—" },
          ],
        },
        {
          title: "时间",
          sum: `添加 ${ts(d.added_on)}`,
          rows: [
            { icon: "#i-calendar", label: "添加于", text: ts(d.added_on) },
            { icon: "#i-check-circle", label: "完成于", text: ts(d.completion_on) },
            { icon: "#i-eye", label: "见到完整副本", text: ts(d.seen_complete) },
            { icon: "#i-clock", label: "最近活动", text: ts(d.last_activity) },
            { icon: "#i-timer", label: "活跃时间", text: dur(d.time_active, "—") },
            { icon: "#i-timer", label: "做种时间", text: dur(d.seeding_time, "—") },
          ],
        },
        {
          title: "路径",
          sum: `自动种子管理 ${yn(d.auto_tmm)}`,
          // FX-22: 路径行一律块行 + 右侧"打开目录"(走后端 /api/open-path) —— 路径是本页最长、
          // 最常需要"去磁盘上看一眼"的一类值
          rows: [
            { icon: "#i-folder-open", label: "保存路径", text: d.save_path || "—", wide: true, act: "open" },
            { icon: "#i-folder", label: "内容路径", text: d.content_path || "—", wide: true, act: "open" },
            { icon: "#i-folder-open", label: "下载路径", text: d.download_path || "—", wide: true, act: "open" },
            { icon: "#i-folder", label: "根路径", text: d.root_path || "—", wide: true, act: "open" },
            { icon: "#i-sliders", label: "自动种子管理", text: yn(d.auto_tmm) },
            { icon: "#i-play", label: "强制开始", text: yn(d.force_start) },
            { icon: "#i-upload", label: "超级做种", text: yn(d.super_seeding) },
            { icon: "#i-sort", label: "顺序下载", text: yn(d.seq_dl) },
            { icon: "#i-bolt", label: "首末块优先", text: yn(d.f_l_piece_prio) },
          ],
        },
      ];
    },
    /* FX-22: 字段行图标着色 —— 由**图标名派生**色调类, 而不是给 48 行逐个加 tone 字段:
     * 图标本身已隐含语义(下载/上传/日历/文件夹/哈希...), 派生表是单点, 新增行自动生效。
     * 色值全在 views.css 的 .ico-t-* 族里走主题令牌。 */
    icoTone(icon) {
      const map = {
        "#i-download": "ico-t-io", "#i-upload": "ico-t-io", "#i-arrow-up": "ico-t-io", "#i-arrow-down": "ico-t-io",
        "#i-hdd": "ico-t-cap", "#i-layers": "ico-t-cap", "#i-columns": "ico-t-cap",
        "#i-calendar": "ico-t-time", "#i-clock": "ico-t-time", "#i-timer": "ico-t-time",
        "#i-hourglass": "ico-t-time", "#i-eye": "ico-t-time",
        "#i-globe": "ico-t-site", "#i-link": "ico-t-site",
        "#i-lock": "ico-t-sw", "#i-sliders": "ico-t-sw", "#i-play": "ico-t-sw", "#i-sort": "ico-t-sw",
        "#i-bolt": "ico-t-sw", "#i-settings": "ico-t-sw", "#i-refresh": "ico-t-sw",
        "#i-hash": "ico-t-id", "#i-info": "ico-t-id", "#i-tag": "ico-t-id", "#i-list": "ico-t-id",
        "#i-folder": "ico-t-path", "#i-folder-open": "ico-t-path",
        "#i-percent": "ico-t-state", "#i-pulse": "ico-t-state", "#i-check-circle": "ico-t-state",
        "#i-x-circle": "ico-t-state", "#i-warn": "ico-t-state",
      };
      return map[icon] || "";
    },
    /* Content tab: qB files[].name 为 '/' 分隔相对路径 -> 构树后扁平化(缩进渲染);
     * 目录行聚合大小; 文件行展示 进度/优先级(0=跳过 1=普通 4|6=高 7=最高), 优先级可点改(小菜单);
     * 每行带 index(种子内原始下标, files/priority 用)与 path(完整相对路径, 选中/rename-fs 用) */
    drawerFileRows() {
      const files = this.drawer.files || [];
      const root = { dirs: new Map(), files: [], size: 0, path: "" };
      for (let fi = 0; fi < files.length; fi++) {
        const f = files[fi];
        const parts = String(f.name || "").split("/").filter(Boolean);
        let node = root;
        for (let i = 0; i < parts.length - 1; i++) {
          if (!node.dirs.has(parts[i])) {
            node.dirs.set(parts[i], { dirs: new Map(), files: [], size: 0, path: node.path ? node.path + "/" + parts[i] : parts[i] });
          }
          node = node.dirs.get(parts[i]);
          node.size += f.size || 0;
        }
        node.files.push({ ...f, index: fi });
      }
      const prio = (p) => ({ 0: "跳过", 1: "普通", 4: "高", 6: "高", 7: "最高" }[p] ?? "普通");
      const rows = [];
      const walk = (node, name, depth) => {
        if (name !== null) rows.push({ depth, dir: true, name, path: node.path, text: this.fmtSize(node.size) });
        for (const [dn, d] of node.dirs) walk(d, dn, name === null ? 0 : depth + 1);
        for (const f of node.files) {
          const last = String(f.name || "").split("/").pop();
          rows.push({
            depth: name === null ? 0 : depth + 1, dir: false,
            name: last,
            path: node.path ? node.path + "/" + last : last,
            index: f.index,
            text: this.fmtSize(f.size), progress: Math.round((f.progress || 0) * 100),
            prio: prio(f.priority), skipped: f.priority === 0,
          });
        }
      };
      walk(root, null, -1);
      return rows;
    },
    /* Peers tab: qB 响应 peers 可能为 dict(以 ip:port 为键)或数组 —— 双形态归一 */
    drawerPeerRows() {
      const p = this.drawer.peers || {};
      const list = Array.isArray(p.peers) ? p.peers : Object.values(p.peers || {});
      return list.map((x) => ({
        addr: `${x.ip || "?"}${x.port ? ":" + x.port : ""}`,
        client: x.client || "—",
        flags: x.flags || "—",
        progress: Math.round((x.progress || 0) * 100),
        dlspeed: this.fmtSpeedOrDash(x.dlspeed || 0) || "—",  // 抽屉 peers 表保留"—"
        upspeed: this.fmtSpeedOrDash(x.upspeed || 0) || "—",
        downloaded: this.fmtSizeOrDash(x.downloaded || 0) || "—",
        uploaded: this.fmtSizeOrDash(x.uploaded || 0) || "—",
        relevance: `${Math.round((x.relevance || 0) * 100)}%`,
      }));
    },
    drawerTrackerStatus(s) {
      return { 0: "未启用", 1: "未连接", 2: "正常", 3: "更新中", 4: "未连接" }[s] ?? "—";
    },
    drawerTrackerVirtual(url) {
      const u = String(url || "");
      return u.startsWith("**") || ["[DHT]", "[PeX]", "[LSD]"].some((p) => u.startsWith(p));
    },
  },
};
