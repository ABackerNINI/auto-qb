/* auto-qb WEB UI · 追剧视图(剧/季/集展开与集级命令)
 *
 * app.js 按域拆分出的片段(2026-09-20)。约定与 config_editor.js / config_rules.js 同一范式:
 * 挂到 window.AQB_SHOWS, 由 app.js 末尾 app.mixin(window.AQB_SHOWS) 注入同一个 Vue 实例 ——
 * 方法体里的 this 仍是那个组件实例, 跨模块互调与拆分前完全等价。
 *
 * ❗本文件在 HTML 里必须排在 app.js **之前**(app.js 末尾要读 window.AQB_SHOWS);
 *   用到的列模型常量(TABLE_COLUMNS / MIN_COL_PX / STATE_RANK …)仍单点定义在 app.js 顶部。
 */
window.AQB_SHOWS = {
  methods: {
    /* ---------------- 追剧视图(R10): 剧/集展开与整集操作 ---------------- */
    syncShowHeadScroll(ev) {
      const head = this.$refs.showHead;
      if (!head) return;
      head.style.transform = `translateX(${-ev.target.scrollLeft}px)`;
    },
    toggleShow(key) {
      const i = this.expandedShows.indexOf(key);
      if (i >= 0) this.expandedShows.splice(i, 1);
      else this.expandedShows.push(key);
    },
    isShowExpanded(key) {
      return this.expandedShows.includes(key);
    },
    showEpRowId(showKey, season, epKeyStr) {
      return `${showKey}|${season === null || season === undefined ? "~" : season}|${epKeyStr}`;
    },
    toggleShowEp(showKey, season, epKeyStr) {
      const id = this.showEpRowId(showKey, season, epKeyStr);
      this.expandedShowEp = this.expandedShowEp === id ? null : id;
      this.menu.visible = false;
    },
    /* 集键 -> 展示文本(与后端 tvshows.ParsedRelease.episode_key 三形态对应) */
    epLabel(key) {
      if (!key || !key.length) return "—";
      if (key[0] === "ep") return "E" + String(key[1]).padStart(2, "0");
      if (key[0] === "range") return `E${String(key[1]).padStart(2, "0")}-E${String(key[2]).padStart(2, "0")}`;
      if (key[0] === "date") return key[1];
      return "整季包";
    },
    seasonLabel(season) {
      return season === null || season === undefined ? "日播 / 特别篇" : `第 ${season} 季`;
    },
    /* 集成员 -> hash 列表: 后端 shows 视图的 members 是 **hash 数组**, 而 decoratedShows 会把它们
     * 换成**成员对象**(带 hit 标记, 供行内渲染/筛选)。菜单与命令只认 hash —— 两种形态都要能取到,
     * 否则对象被字符串化后变成 "[object Object]": 后端查不到该 hash ⇒ 404「种子不存在」,
     * 整集/整剧的 开始/暂停/强制汇报/打开目标文件夹/删除 全线哑火(单种子菜单传的是 member.hash,
     * 不受影响 —— 这正是"种子右键能打开、剧/集右键打不开"的差异来源)。 */
    memberHashesOf(list) {
      return (list || []).map((m) => (typeof m === "string" ? m : (m && m.hash) || "")).filter(Boolean);
    },
    /* 整集右键菜单: 目标 = 该集全部成员(多版本), 操作走单种子命令(与批量同语义) */
    openShowEpMenu(event, show, ep) {
      event.preventDefault();
      event.stopPropagation();
      this._markCtxSource(event);
      const hashes = this.memberHashesOf(ep.members);
      this.menu = {
        visible: true,
        ...this._menuPos(event),
        key: null,
        hash: null,
        episode: { hashes, label: `${show.name} ${this.epLabel(ep.key)}`, scope: "ep" },
        // CTX-03: 该集属于选中集合且集合更大时升级为批量菜单(见 menu.js _ctxMulti)
        multi: this._ctxMulti({ hashes }),
      };
    },
    /* FX-13: 整剧右键菜单。追剧页的"剧"这一层此前只有左键展开、没有 @contextmenu ——
     * 越级的整剧操作(开始/暂停/汇报/打开目录/删除)无处可做。目标 = 该剧全部集的全部成员(去重),
     * 与整集菜单共用同一分支与动作链, 仅用 scope 区分文案与确认框标题。 */
    openShowMenu(event, show) {
      event.preventDefault();
      event.stopPropagation();
      this._markCtxSource(event);
      const hashes = [];
      const seen = new Set();
      for (const sn of show.seasons || []) {
        for (const e of sn.episodes || []) {
          for (const h of this.memberHashesOf(e.members)) {
            if (!seen.has(h)) {
              seen.add(h);
              hashes.push(h);
            }
          }
        }
      }
      if (!hashes.length) return;
      this.menu = {
        visible: true,
        ...this._menuPos(event),
        key: null,
        hash: null,
        episode: { hashes, label: show.name, scope: "show" },
        // CTX-03: 该剧属于选中集合且集合更大时升级为批量菜单(见 menu.js _ctxMulti)
        multi: this._ctxMulti({ hashes }),
      };
    },
    async actEpisode(action) {
      this.menu.visible = false;
      const ep = this.menu.episode || {};
      const hashes = ep.hashes || [];
      if (!hashes.length) return;
      const what = ep.scope === "show" ? "整剧" : "整集";
      const label = this._actionText(action);
      const isRe = action === "reannounce";
      // P0-4: pause/resume 合单为一条 bulk 命令 —— 整剧动辄上百集, 逐条投递要发上百次请求
      if (!isRe) {
        const t0 = this._newCmdStats(action);
        // P0-3: 与整组/单种子同一条乐观链路(整集/整剧此前**完全没接**, 点了没有任何即时反馈)
        this.applyOptimistic(hashes, action);
        this._markCmdPatch(t0);
        try {
          const resp = await this.api("/api/torrents/bulk", {
            method: "POST",
            body: JSON.stringify({ action, hashes }),
          });
          this._markCmdPost(t0);
          const r = await this.waitCmd(resp.cmd_id);
          this.resolveOptimistic(hashes, r.ok);
          /* D2: 与 commands.js 三处保持一致 —— 真值由 `truth` 事件推送, 不再拉全量。
           * ❗这里原先漏改, 追剧页集行还在走 1500ms 拉取预算, 撤下比种子页慢一大截。
           * ❗只在成功时标 receipt: 失败那一路是回滚, 标它会把 [perf] 里的路径判据带偏。 */
          if (r.ok && this.cmdStats) this.cmdStats.settleVia = "receipt";
          if (r.ok) this.toast(`已执行: ${label}${what}(${hashes.length} 个种子)`, "ok", 2500);
          else this.toast(`${label}${what}失败: ${r.error}`, "error", 8000);
        } catch (e) {
          this.resolveOptimistic(hashes, false);  // 发送失败: 同样回滚, 不留假状态
          if (!e.auth) this.toast("命令发送失败: " + e.message, "error");
        }
        return;
      }
      const tid = this.toast(`强制汇报等待中…(${hashes.length} 个目标, tracker 确认最长 30s)`, "busy", 0, { sticky: true });
      const results = await Promise.allSettled(
        hashes.map((h) =>
          this.api(`/api/torrents/${h}/${action}`, { method: "POST" }).then((r) =>
            this.waitCmd(r.cmd_id, 40000, { firstMs: 500, capMs: 1000 })
          )
        )
      );
      const fails = results.filter((r) => r.status === "rejected" || !r.value.ok);
      if (!fails.length) {
        this._finishToast(tid, "ok", `强制汇报成功(tracker 已确认, ${hashes.length} 个目标)`, 3000);
        return;
      }
      const firstErr = fails[0].status === "rejected" ? fails[0].reason.message : fails[0].value.error;
      this._finishToast(
        tid,
        "timeout",
        `强制汇报: 成功 ${hashes.length - fails.length}, 失败 ${fails.length}${firstErr ? ` (${firstErr})` : ""}`,
        6000
      );
    },
    /* 删除整集/整剧(全部版本; FX-13 起两者共用): 目标名与种子数进 body, 详情行由 _deleteFlow 统一派生 */
    async delEpisode() {
      this.menu.visible = false;
      const ep = this.menu.episode;
      if (!ep || !ep.hashes.length) return;
      const members = ep.hashes.map((h) => this.memberByHash.get(h)).filter(Boolean);
      if (!members.length) return;
      const what = ep.scope === "show" ? "整剧" : "整集";
      // FX-16: 与右键/批量/该种子共用同一条删除链; R10-16: 详情行由 _deleteFlow 统一派生
      await this._deleteFlow({
        keys: [],
        hashes: ep.hashes.slice(),
        title: `删除${what}`,
        body: `将删除"${ep.label}"的全部 ${members.length} 个种子。建议删除前先向 tracker 汇报, 避免留下未汇报的 H&R 记录。`,
        countText: `${what}(${members.length} 个种子)`,
        label: ep.label,
      });
    },
  },
  computed: {
    /* 追剧视图(R10): 后端已按剧→季→集聚合并算好聚合层; 前端只做 筛选/搜索(任一成员命中
     * 保留整集) + 剧级搜索命中(剧名含关键字保留全剧) + 排序。showHit 与 epHit 分开:
     * 剧名命中高亮整剧行, 集命中高亮集行(与分组视图"组内任一命中保留整组"同语义) */
    decoratedShows() {
      const q = (this.searchQuery || "").trim().toLowerCase();
      const hits = this.searchHits;
      const out = [];
      for (const s of this.shows.list) {
        let showHit = !!(q && (s.name || "").toLowerCase().includes(q));
        let keptEps = 0;
        let keptMembers = 0;
        const seasons = [];
        for (const sn of s.seasons) {
          const eps = [];
          for (const e of sn.episodes) {
            const members = e.members
              .map((h) => {
                const m = this.memberByHash.get(h);
                return m ? { ...m, hit: hits.has(h) } : null;
              })
              .filter(Boolean);
            if (!members.length) continue;
            if (!members.some((m) => this._memberPass(m))) continue;
            const epHit = members.some((m) => m.hit);
            if (q && !showHit && !epHit) continue;
            keptEps += 1;
            keptMembers += members.length;
            eps.push({ ...e, members, hit: epHit, epKeyStr: e.key.join("-") });
          }
          if (eps.length) seasons.push({ ...sn, episodes: eps });
        }
        if (showHit || seasons.length) {
          if (showHit) keptEps = s.episode_count;
          out.push({ ...s, seasons, hit: showHit, keptEps, keptMembers });
        }
      }
      const key = this.showSortKey;
      const dir = this.showSortDir;
      out.sort((a, b) => {
        let r;
        if (key === "name") r = dir * (a.name || "").localeCompare(b.name || "");
        else if (key === "episode_count") r = dir * (a.episode_count - b.episode_count);
        else r = dir * ((a.latest || 0) - (b.latest || 0));
        // 平局兜底按名升序且不随方向翻转(否则降序时同 latest 的剧会倒序排, 难以预期)
        if (r === 0) r = (a.name || "").localeCompare(b.name || "");
        return r;
      });
      return out;
    },
    /* 追剧视图统计(状态条计数): 剧/集/成员三层 */
    showStats() {
      let eps = 0;
      let members = 0;
      for (const s of this.decoratedShows) {
        eps += s.keptEps;
        members += s.keptMembers;
      }
      return { shows: this.decoratedShows.length, eps, members, unrecognized: this.unrecognizedTorrents.length };
    },
  },
};
