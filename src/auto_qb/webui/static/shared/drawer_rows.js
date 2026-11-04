/* drawer_rows.js — R4 大文件拆分(计划 26-11-02-2342 §07)
 * 详情抽屉 · 常规行派生 / 文件行 / 用户行 / tracker 状态。
 * 只搬方法定义, 实现逐行未改; 根文件已定义该域, 本片段在其后原地扩充(Object.assign)。
 * 加载序 = 四套皮肤 index.html 清单里紧跟根文件之后(与拆分前同一迭代替换序)。
 */
Object.assign(window.AQB_DRAWER.methods, {
    /* 抽屉头部动作: 复用 actTorrent(自带回执/toast), 目标 = 抽屉 hash(显式传参, 不动 menu 状态) */
    drawerAct(action) {
      this.actTorrent(action, this.drawer.hash);
    },
    /* 抽屉删除: 复用 delTorrent(确认框流程一致); 删除成功(成员消失)后自动收起抽屉 */
    drawerDel() {
      this._drawerDeletePending = true;
      Promise.resolve(this.delTorrent(this.drawer.hash)).then(() => {
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
      const out = [
        {
          title: "基础",
          sum: `容量 ${size(d.size)} · 分享率 ${(d.ratio ?? 0).toFixed(2)}`,
          rows: [
            { icon: "#i-percent", label: "进度", text: `${((d.progress || 0) * 100).toFixed(1)}%` },
            { icon: "#i-hdd", label: "大小", text: size(d.size) },
            { icon: "#i-layers", label: "总大小", text: size(d.total_size) },
            { icon: "#i-download", label: "剩余", text: size(d.amount_left) },
            { icon: "#i-pulse", label: "可用性", text: (d.availability ?? 0).toFixed(2) },
            { icon: "#i-percent", label: "分享率", text: (d.ratio ?? 0).toFixed(3) },
            { icon: "#i-lock", label: "私有", text: yn(d.private) },
            // FX-22: 哈希/备注可能极长 -> 块行 + 右侧"复制"(不再只能悬停看 title)
            { icon: "#i-hash", label: "信息哈希值 v1", text: d.infohash_v1 || "—", mono: true, wide: true, act: "copy" },
            { icon: "#i-hash", label: "信息哈希值 v2", text: d.infohash_v2 || "—", mono: true, wide: true, act: "copy" },
            { icon: "#i-columns", label: "区块", text: d.piece_size ? `${d.pieces_have ?? 0} / ${d.pieces_num ?? 0} × ${this.fmtSize(d.piece_size)}` : "—" },
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
            { icon: "#i-download", label: "会话已下载", text: size(d.downloaded_session) },
            { icon: "#i-upload", label: "会话已上传", text: size(d.uploaded_session) },
            { icon: "#i-warn", label: "已丢弃", text: size(d.total_wasted) },
            { icon: "#i-arrow-up", label: "做种数", text: String(d.num_seeds ?? 0) },
            { icon: "#i-arrow-down", label: "用户", text: String(d.num_leechs ?? 0) },
            { icon: "#i-globe", label: "完整/下载中", text: `${d.num_complete ?? 0} / ${d.num_incomplete ?? 0}` },
            { icon: "#i-globe", label: "Tracker 数", text: String(d.trackers_count ?? 0) },
            { icon: "#i-link", label: "连接", text: `${d.connections_count ?? 0} / ${d.connections_limit ?? 0}` },
            { icon: "#i-refresh", label: "下次重新汇报", text: dur(d.reannounce_in || d.reannounce, "—") },
            { icon: "#i-x-circle", label: "Tracker 错误", text: yn(d.has_tracker_error) },
            { icon: "#i-warn", label: "Tracker 警告", text: yn(d.has_tracker_warning) },
            { icon: "#i-percent", label: "分享率限制", text: (d.max_ratio ?? -1) < 0 ? "未设" : d.max_ratio.toFixed(2) },
            { icon: "#i-timer", label: "做种时间限制", text: lim(d.max_seeding_time) },
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
            { icon: "#i-eye", label: "最后完整可见", text: ts(d.seen_complete) },
            { icon: "#i-clock", label: "最近活动", text: ts(d.last_activity) },
            { icon: "#i-timer", label: "活动时间", text: dur(d.time_active, "—") },
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
            { icon: "#i-play", label: "强制启动", text: yn(d.force_start) },
            { icon: "#i-upload", label: "超级做种", text: yn(d.super_seeding) },
            { icon: "#i-sort", label: "按顺序下载", text: yn(d.seq_dl) },
            { icon: "#i-bolt", label: "先下载首尾文件块", text: yn(d.f_l_piece_prio) },
          ],
        },
      ];
      /* P1 迁移段(plan 26-11-04-1042): 数据源 = /api/torrents/{hash} 新增的 relocate 投影。
       * 无 job 时**整段不渲染** —— 旧 state / 未迁移种子不得出现「已完成」之类误导结论。 */
      const rel = d.relocate;
      if (rel) {
        out.push({
          title: "迁移",
          sum: `${this.relocateStateText(rel.state)}${rel.mover ? " · 搬移成员" : " · 受影响成员"}`,
          rows: [
            { icon: "#i-refresh", label: "迁移状态", text: this.relocateStateText(rel.state) },
            { icon: "#i-info", label: "设置来源", text: this.relocateOriginText(rel.origin) },
            { icon: "#i-check-circle", label: "auto-qb 设置", text: "是" },
            { icon: "#i-hash", label: "任务标识", text: rel.job_id || "—", mono: true, wide: true, act: "copy" },
            { icon: "#i-folder", label: "源路径", text: rel.src || "—", wide: true, act: "open" },
            { icon: "#i-folder-open", label: "目标路径", text: rel.dst || "—", wide: true, act: "open" },
            { icon: "#i-layers", label: "关联别名", text: rel.alias_count ? `${rel.alias_count} 个（${rel.alias_kind || "未知类型"}）` : "无" },
            { icon: "#i-timer", label: "收尾武装", text: rel.armed_at ? ts(rel.armed_at) : "未武装" },
            { icon: "#i-clock", label: "最近更新", text: ts(rel.updated_at) },
          ].concat(rel.state === "failed" && rel.reason
            ? [{ icon: "#i-warn", label: "失败原因", text: rel.reason, wide: true }] : []),
        });
      }
      return out;
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
      const prio = (p) => window.AQB_DRAWER_TPL_REG.helpers.prioText(p, "正常"); /* 文案单点(issue 26-10-29-1340), 方法内取 */
      const rows = [];
      const walk = (node, name, depth) => {
        if (name !== null) rows.push({
          depth, dir: true, name, path: node.path, text: this.fmtSize(node.size),
          _raw: { name, size: node.size, progress: 0 },
        });
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
            // W2: 排序取原始值(大小/进度) —— 显示值 text 是 "1.2 MiB" 这类格式化字符串, 见 _sortVal
            _raw: { name: last, size: f.size || 0, progress: f.progress || 0, prio: f.priority },
          });
        }
      };
      walk(root, null, -1);
      return rows;
    },
    /* Peers tab: qB 响应 peers 可能为 dict(以 ip:port 为键)或数组 —— 双形态归一。
     * W2(计划 26-10-11-2106): 每行附 `_raw`(原始数值) —— 接壳后列头可排序, 而显示值 dlspeed 等
     * 是 `fmtSpeedOrDash` 出的字符串("1.2 MiB"), 按显示值比就是字典序错排; 排序取值见
     * sort.js `_sortVal`(优先 `_raw`)。显示字段一个未动 —— 15 个变体与其它消费方零影响。 */
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
        _raw: {
          addr: `${x.ip || "?"}${x.port ? ":" + x.port : ""}`,
          client: x.client || "", flags: x.flags || "",
          progress: x.progress || 0,
          dlspeed: x.dlspeed || 0, upspeed: x.upspeed || 0,
          downloaded: x.downloaded || 0, uploaded: x.uploaded || 0,
          relevance: x.relevance || 0,
        },
      }));
    },
    /* 2026-10-14: drawerTrackerRows() 随经典 Tracker 表退役(变体 04/05/06 的行装配在各自
     * rowsFn 里, 不再经根方法)。下面两条仍是变体消费的公共判定/翻译单点。 */
    drawerTrackerStatus(s) {
      return { 0: "禁用", 1: "未联系", 2: "工作", 3: "更新中", 4: "未工作" }[s] ?? "—";
    },
    drawerTrackerVirtual(url) {
      const u = String(url || "");
      return u.startsWith("**") || ["[DHT]", "[PeX]", "[LSD]"].some((p) => u.startsWith(p));
    },
});
