/* drawer_files.js — R4 大文件拆分(计划 26-11-02-2342 §07)
 * 详情抽屉 · tracker 增删 / 文件优先级 / 种子信息复制。
 * 只搬方法定义, 实现逐行未改; 根文件已定义该域, 本片段在其后原地扩充(Object.assign)。
 * 加载序 = 四套皮肤 index.html 清单里紧跟根文件之后(与拆分前同一迭代替换序)。
 */
Object.assign(window.AQB_DRAWER.methods, {
    /* ---------------- 抽屉 Tracker 页签编辑(D 轮): 添加/删除 ---------------- */
    async trackerAdd() {
      const hash = this.drawer.hash;
      if (!hash) return;
      const raw = await this.promptDialog("添加 Tracker", "", {
        placeholder: "announce URL(多条用换行/逗号分隔)", okText: "添加",
      });
      if (raw === null) return;
      const urls = raw.split(/[\s,]+/).map((s) => s.trim()).filter(Boolean);
      if (!urls.length) {
        this.toast("tracker 为空: 请至少输入一条 announce URL", "warn");
        return;
      }
      await this._editPost(hash, "trackers/add", { urls }, urls.length > 1 ? `已添加 ${urls.length} 条 tracker` : "tracker 已添加");
    },
    async trackerRemove(url) {
      // url 为 mask 值(详情 API 只回 mask), 后端当场重取原文比对后再删
      const hash = this.drawer.hash;
      if (!hash) return;
      const ok = await this.confirmDialog("删除 Tracker", `将删除该 tracker: ${url}`, { okText: "删除", danger: true });
      if (!ok) return;
      await this._editPost(hash, "trackers/remove", { url }, "tracker 已删除");
    },
    /* ---------------- 抽屉内容页签编辑(D 轮): 优先级小菜单 ----------------
     * 2026-10-14: 经典渲染链移除后, 行选中(fileRowSelect/drawerSelPath)与文件重命名
     * (renameFileRow)随之退役 —— 二者只由已删的 drawer-tabs.html 工具栏/名称格消费,
     * 内容页签变体(10/11/12)自管选中态且不含重命名(见 10 变体头注)。 */
    /* 文件优先级小菜单: 锚定单元格下方, 视口吸附(@click.stop 防止开菜单的点击立即被窗口关闭) */
    openFilePrio(ev, index) {
      this._markCtxSource(ev);
      const FIT = window.AQB_OVERLAY_FIT; /* 几何单点(issue 26-10-20-2231), 方法内取别名 */
      const rect = ev.currentTarget.getBoundingClientRect();
      const w = 150, h = 176;
      this.filePrio = {
        visible: true, index,
        x: FIT.clampAxis(rect.left, w, window.innerWidth),
        y: FIT.clampAxis(rect.bottom + 4, h, window.innerHeight),
      };
    },
    /* 文件优先级码 -> 中文文案(0=跳过 1=普通 4|6=高 7=最高; 4=qB legacy「高」档, 设置侧只发
     * 0/1/6/7, 现网旧种子仍会回读) -> POST files/priority。文案字面单点在模板核心层
     * reg.helpers::prioText(issue 26-10-29-1340, 与 :1425 注释同一键集)。
     * indices 可选(计划 26-10-06-0838 S5 内容变体批量通道): 传文件下标数组时一次提交整批
     * (后端 files/priority 本就收 indices 数组, 见 torrent_cmds.py); 缺省沿用 filePrio.index
     * 单文件语义 —— 经典小菜单(ctx-menus.html)与变体 10 的锚定小菜单(openFilePrio)零变化。 */
    async setFilePriority(p, indices = null) {
      this.filePrio.visible = false;
      const hash = this.drawer.hash;
      const idx = Array.isArray(indices) ? indices.slice() : [this.filePrio.index];
      if (!hash || !idx.length || idx.some((i) => !Number.isInteger(i) || i < 0)) return;
      const { prioText } = window.AQB_DRAWER_TPL_REG.helpers; /* 文案单点(issue 26-10-29-1340), 方法内取别名(FIT 先例) */
      const label = prioText(p, String(p));
      const okText = Array.isArray(indices)
        ? `已将 ${idx.length} 个文件设为「${label}」` : `优先级已设为「${label}」`;
      await this._drawerFilePriority(hash, idx, p, okText);
    },
    /* W6a(计划 26-11-02-0351 §06 拍板 = 实施): 抽屉文件优先级乐观写补丁。
     * drawer.files 是内容页签的独立响应式数组, 不在 commands.js::_forEachRow 覆盖的
     * torrents/singles/groups 三数组内 —— 既有 applyOptimisticPatch/pendingOps 管不到它,
     * 所以在这里单点补一条只写 priority 的通道。
     * 写入纪律: 先逐 index 采当前 priority 作 prev, 当帧写新值(徽章立变), 再发 POST;
     * 只写 priority 一个字段(值来自我们), 不碰其它行数据。
     * 回滚出口两条(回执失败 / 等待超时)都回 prev, 随后静默重拉 files —— 命令若其实已
     * 生效, 重拉带回服务端真值, 最终态与整表重拉一致, 不留假状态; 成功路径同样重拉收口。
     * 重叠点击: 每次点击递增该 hash 的序号; 只有最新一次的操作做重拉(旧操作不回滚已被
     * 覆盖的 index), 后一次操作自己收口 —— 不引入绕过单写线程的并发通道。
     * 幂等: 重复点同一优先级只重复同值 POST, 可见态无变化; 不加任何定时器。 */
    async _drawerFilePriority(hash, indices, priority, okText) {
      const files = (this.drawer.open && this.drawer.hash === hash) ? this.drawer.files : null;
      const snap = [];
      if (Array.isArray(files)) {
        for (const i of indices) {
          const row = files[i];
          if (!row) continue;
          snap.push({ i, prev: row.priority, next: priority });
          row.priority = priority;  /* 乐观写入: 徽章当帧可见, 不等回执 */
        }
      }
      if (!this._filePrioSeq) this._filePrioSeq = new Map();
      const seq = (this._filePrioSeq.get(hash) || 0) + 1;
      this._filePrioSeq.set(hash, seq);
      const latest = () => this._filePrioSeq.get(hash) === seq;
      const refresh = () => {
        if (!latest()) return;
        if (this.drawer.open && this.drawer.hash === hash) this._fetchDrawerFiles(true);
      };
      try {
        const resp = await this.api(`/api/torrents/${hash}/files/priority`, {
          method: "POST",
          body: JSON.stringify({ indices: indices.slice(), priority }),
        });
        /* 优先级是快命令, 10s 足够; 超时后走回滚出口, 不让徽章停在假值上 */
        const r = await this.waitCmd(resp.cmd_id, 10000);
        if (r.ok) {
          this.toast(`已执行: ${okText}`, "ok", 2500);
          if (this.drawer.open && this.drawer.hash === hash) this._fetchDrawerDetail();
          refresh();
          return true;
        }
        const timeout = /执行等待超时/.test(String(r.error || ""));
        this._drawerFileRollback(hash, snap);
        this.toast(`${okText}${timeout ? "超时, 已回滚: " : "失败: "}${r.error}`, "error", 8000);
      } catch (e) {
        this._drawerFileRollback(hash, snap);
        if (!e.auth) this.toast(`${okText}命令发送失败, 已回滚: ` + e.message, "error");
        if (!e.auth) refresh();
        return false;
      }
      refresh();
      return false;
    },
    /* 失败/超时回滚: 只回仍是我们写下的值(后一次点击已覆盖的 index 不回滚, 由那次操作负责)。 */
    _drawerFileRollback(hash, snap) {
      if (!this.drawer.open || this.drawer.hash !== hash || !Array.isArray(this.drawer.files)) return;
      for (const { i, prev, next } of snap) {
        const row = this.drawer.files[i];
        if (row && row.priority === next) row.priority = prev;
      }
    },
    /* 复制种子信息: 目标 hash 显式传入, 缺省回落 menu.hash(S3/M3: 键盘路径 _kbEditAct 传 (field, h),
     * 不再借道菜单状态)。只剩 name/hash 两用(复制 magnet 入口已退役, issue 26-11-09-0639:
     * magnet_uri 入库即掩码(26-11-08-0043), 复制出的是 tr= 已掩的废链接)。 */
    copyTorrentInfo(field, h = "") {
      this.menu.visible = false;
      const hash = h || this.menu.hash;
      const m = this.memberByHash.get(hash);
      if (!m) return;
      const value = field === "name" ? m.name
        : field === "hash" ? (m.infohash_v1 || m.hash)
          : "";
      if (!value) {
        this.toast("无法复制: 该字段为空", "warn");
        return;
      }
      const label = field === "name" ? "种子名" : "信息哈希";
      this._copyText(value, label);
    },
});
