/* commands_send.js — R4 大文件拆分(计划 26-11-02-2342 §07)
 * 命令 · 下发核心 / 批量与右键 / 导出。
 * 只搬方法定义, 实现逐行未改; 根文件已定义该域, 本片段在其后原地扩充(Object.assign)。
 * 加载序 = 四套皮肤 index.html 清单里紧跟根文件之后(与拆分前同一迭代替换序)。
 */
Object.assign(window.AQB_COMMANDS.methods, {
    /* ---------------- 动作统一出口(计划 26-09-28-0354 W3 的唯一重构点) ----------------
     * 右键批量菜单 / 键盘快捷键两个入口共用同一条动作链。端点按目标形态路由:
     *   单组(仅 1 个组 key 且动作在组级端点支持面内 pause/resume) -> /api/groups/{k}/{action};
     *   单种子(仅 1 个 hash)                                      -> /api/torrents/{h}/{action};
     *   其余(多目标 / 组级端点不支持的 recheck 等)                 -> /api/torrents/bulk 合单;
     *   reannounce 恒逐目标投递(后端 _BULK_ACTIONS 不含它, tracker 确认要逐个跟踪);
     *   reannounce 的投递集合先经 reannouncePlan 收敛为**活跃子集**(非活跃的发出去也是
     *   qB 引擎空转, 只会给确认层添假结论) —— 组目标因此展开为逐成员 hash(仅活跃的在列)。
     * 回执文案只管一件事(计划 26-10-20-0145 D2/D11): `已执行: {动作}({N} 个种子)` /
     *   `{动作}失败: {原因}` —— N = 实际受作用的种子总数(selection.js::_seedCountOf), 与菜单
     *   灰色后缀、删除确认框同一口径。此前四个入口各传 what/countSuffix("整组"/"该种子"/
     *   "整剧"+"(N 个种子)"/"批量"+"(N 个目标)"), 同一件事四种叫法 + 两种计数单位。
     * !别再引入 what/countSuffix 参数: 目标形态已经从 keys/hashes 拿得到, 让调用方描述一遍
     *   就是给「同动作不同叫法」留门(这正是本轮退役的东西)。
     * 乐观补丁: pause/resume 白名单(§P0-3), 目标 = 组成员展开 ∪ hashes 去重 —— 与原三条链一致。 */
    async _actCore(action, { keys = [], hashes = [] } = {}) {
      this._auditScope("actCore:" + action, { keys, hashes });  // S4 运行时审计(默认关, 只记账)
      const n = keys.length + hashes.length;
      if (!n) return;
      /* 强制重新汇报闸门(qB 口径): 目标全为非活跃时拒绝, 早于乐观补丁与 POST(零副作用)。
       * 本出口覆盖 组菜单 act / 单种子 actTorrent / 整集整剧 actEpisode / 批量 bulkAct /
       * 键盘 _kbAct —— 与右键菜单的置灰(ctx-menus.html)同一判据, 互为"显示层 / 行为层"两道。 */
      if (action === "reannounce" && !this._guardReannounce({ keys, hashes })) return;
      const seedN = this._seedCountOf(keys, hashes);  // 种子数单点(组按成员展开), N 不取 n
      const countSuffix = `(${seedN} 个种子)`;
      const label = this._actionText(action);
      const isRe = action === "reannounce";
      const optHashes = [];
      if (!isRe) {
        const seen = new Set();
        for (const k of keys) {
          const g = this._findGroup(k);
          if (!g) continue;
          for (const m of g.members || []) {
            if (!seen.has(m.hash)) {
              seen.add(m.hash);
              optHashes.push(m.hash);
            }
          }
        }
        for (const h of hashes) {
          if (!seen.has(h)) {
            seen.add(h);
            optHashes.push(h);
          }
        }
      }
      const t0 = isRe ? 0 : this._newCmdStats(action);
      /* 强制汇报投递条的句柄(九轮: 投递与回执是**两条**消息, 见 reannounce 分支注解)。
       * 提到 try 外是为了 catch 里也能把它收掉 —— sticky 条不结账会永远挂在屏上。 */
      let reToast = null;
      if (!isRe) {
        this.applyOptimistic(optHashes, action);  // P0-3: 补丁先于 POST(失败会回滚), 见 26-09-19-1939
        this._markCmdPatch(t0);
      }
      try {
        if (isRe) {
          /* 投递集合收敛(单点 = decorate.js::reannouncePlan): 上面的闸门给的是"允不允许",
           * 这里给的是"发给谁"。混选(1 活跃 + N 非活跃)按 qB 口径放行, 但非活跃的发出去
           * 也是 libtorrent 空转 —— qB 的 GUI 没有 per-target 回执所以无所谓, 我们有确认层:
           * 白等到 item deadline(最长 600s)后落「未确认」, 把干净的成功报成部分失败。 */
          const plan = this.reannouncePlan({ keys, hashes });
          /* job 从"纯 URL"改成"URL + 目标标识"(计划 26-10-19-2007 S6): 逐目标结果要落到
           * 站点 chip 右槽, 而回执里的 truth.results 是**按 hash** 给的 —— 组级 job 必须知道
           * 自己覆盖哪些成员, 才能在 truth 缺失时兜底落 warn。 */
          const jobs = [
            ...plan.keys.map((k) => ({ url: `/api/groups/${k}/reannounce`, hashes: this._jobHashes(k) })),
            ...plan.hashes.map((h) => ({ url: `/api/torrents/${h}/reannounce`, hashes: [h] })),
          ];
          if (!jobs.length) {
            /* 闸门放行(目标解析不出时不误拦)但计划为空(组行成员被清空的罕见态): 必须显式
             * 收口 —— 落进下面的成功分支会报「成功 0 个目标」, 那是把没做事说成做成了。 */
            this.toast(plan.skipped ? `汇报已跳过: 全部 ${plan.skipped} 个目标均非活跃` : "无可汇报目标: 没有可强制重新汇报的种子", "error", 6000);
            return;
          }
          const cnt = jobs.length;
          /* 跳过数在投递前就已知, 故投递条就报出来 —— 否则用户要盯到 tracker 确认落定(最长 40s)
           * 才知道"我选了 2 个为什么只汇报了 1 个"。
           * !2026-11-02 九轮(用户实测「第一个消息窗口会被第二个顶掉, 仅显示不到 1 秒, 没有做到
           *   队列重排」): 八轮把回执做成**同一条**原位换字(emit 一条 sticky, 回执 _finishToast
           *   改 kind/text) —— 桩服务回执 ~500ms 就回, 投递条只活半秒就被改了内容, 看着就是
           *   "两个窗口互相顶掉"; 队列里从头到尾只有一条, 自然也没有重排可言。
           *   今按 D6-3 队列语义拆成**两条事件消息**: 投递条归档成中性「已投递」并留在队列里
           *   (带 TTL), 回执**另起一条** —— 新条推入时投递条被 flipStack 顶上一格, 两条并存。
           *   因此投递条文案必须**归档后仍成立**: 不写「等待中」(它结算后就不再是"等待"了),
           *   统一写「已投递」; "tracker 确认中" 也只作投递瞬间的状态词。 */
          const deliveredText = `强制重新汇报已投递: ${cnt} 个目标`
            + (plan.skipped ? `, 跳过 ${plan.skipped} 个非活跃` : "");
          reToast = this._runningToast(deliveredText);
          /* 投递即给目标落"进行中"(右槽蓝呼吸, 兜底 45s): 多目标时用户能在**行上**看到
           * 哪几个在飞, 而不是只有一条聚合 toast。 */
          for (const j of jobs) for (const h of j.hashes) this.setRowIcon(h, "pending", "强制重新汇报中…");
          const results = await Promise.allSettled(
            jobs.map((j) =>
              this.api(j.url, { method: "POST" }).then((r) => this.waitCmd(r.cmd_id, 40000, { firstMs: 500, capMs: 1000 }))
            )
          );
          /* 三桶按回执 status 分流(计划 26-10-05-0923 D4=warn, 机器依据 = status 不看前缀):
           * ok = tracker 已确认; error = tracker 拒绝(含投递失败/等待超时); warn = 已受理·推迟
           * 与未确认·停止/超时。前缀(已受理/未确认/失败)只作文案, 不参与分流。 */
          let okN = 0, errN = 0, warnN = 0, firstMsg = "";
          results.forEach((r, i) => {
            let status = "error", msg = "";
            if (r.status === "rejected") {
              errN += 1;
              msg = (r.reason && r.reason.message) || "投递失败";
            } else if (r.value.ok) {
              okN += 1;
              status = "ok";
            } else if (r.value.status === "warn") {
              warnN += 1;
              status = "warn";
              msg = r.value.error || "";
            } else {
              errN += 1;
              msg = r.value.error || "";
            }
            if (!firstMsg) firstMsg = msg;
            /* 逐目标结果(计划 D6): truth.results 是后端 items[hash] 的原样带出, 不新增端点。
             * !truth 缺失(旧版后端 / 等待超时)时该批目标统一落 warn —— **不谎称成功**;
             *   组级 job 的目标 hash 取自 _jobHashes(视图当前成员)。 */
            const per = r.status === "fulfilled" && r.value.truth && r.value.truth.results;
            if (Array.isArray(per) && per.length) {
              for (const it of per) this.setRowIcon(it.hash, it.status, it.reason || "");
            } else {
              for (const h of jobs[i].hashes) this.setRowIcon(h, status === "ok" ? "warn" : status, msg || "未收到逐目标结果");
            }
          });
          if (!errN && !warnN) {
            /* 回执条只报"结果": 目标数/跳过数投递条已经报过, 这里再报会把说明挤成两行,
             * 也与投递条不同高(八轮报障的成因之一)。 */
            await this._settleRunningToast(reToast, "ok", `强制重新汇报成功: tracker 已确认 ${cnt} 个目标`, 3000);
            return;
          }
          /* toast 类型映射(计划 §3.4): 含 error -> error / 仅 warn -> timeout(复用现有类型, 不新增)。 */
          const kind = errN ? "error" : "timeout";
          /* head 不带跳过数: 投递条已报过, 重复会把说明挤成两行(与投递条不同高) */
          const head = `强制重新汇报: 成功 ${okN}, 失败 ${errN}, 未确认 ${warnN}`;
          /* 后端聚合 msg 头部「成功 X, 失败 Y, 未确认 Z: 」与前端三桶计数重复(格式被契约测试
           * 钉住), 剥头只留原因段; 投递失败/等待超时无头部, 原样保留。 */
          const detail = firstMsg.replace(/^成功 [0-9]+, 失败 [0-9]+, 未确认 [0-9]+: /, "");
          await this._settleRunningToast(reToast, kind, detail ? `${head} (${detail})` : head, 6000);
          return;
        }
        let resp;
        if (keys.length === 1 && !hashes.length && (action === "pause" || action === "resume")) {
          resp = await this.api(`/api/groups/${keys[0]}/${action}`, { method: "POST" });
        } else if (hashes.length === 1 && !keys.length) {
          resp = await this.api(`/api/torrents/${hashes[0]}/${action}`, { method: "POST" });
        } else {
          resp = await this.api("/api/torrents/bulk", {
            method: "POST",
            body: JSON.stringify({ action, keys, hashes }),
          });
        }
        this._markCmdPost(t0);
        const r = await this.waitCmd(resp.cmd_id);
        this.resolveOptimistic(optHashes, r.ok);
        /* D2: 真值由 `truth` 事件推送(onTruthEvent), 回执不带 truth —— 各入口原注释合并于此 */
        if (r.ok) this.toast(`已执行: ${label}${countSuffix}`, "ok", 2500);
        else this.toast(`${label}失败: ${r.error}`, "error", 8000);
      } catch (e) {
        if (!isRe) this.resolveOptimistic(optHashes, false);  // 发送失败: 回滚, 不留假状态
        /* 投递条必须收口: sticky 条不结账会永远挂在屏上(发送抛错时尤其明显)。
         * auth 失效不弹 —— 会话断了, 屏幕上留条"命令未能送达"毫无用处。 */
        if (reToast && !e.auth) this._finishToast(reToast.tid, "error", "强制重新汇报失败: 命令未能送达", 6000);
        if (!e.auth) this.toast("命令发送失败: " + e.message, "error");
      }
    },
    async act(action) {
      this.menu.visible = false;
      if (!this.menu.key) return;
      return this._actCore(action, { keys: [this.menu.key], hashes: [] });
    },
    /* 选中集合拆解 -> {groupKeys, memberHashes}。
     * !2026-10-10(计划 26-10-10-2001 S3): 展开逻辑收进 selection.js::_scopeResolve("sel") 单点,
     *   本方法退化为它的**形状投影** —— 保留 `{groupKeys, memberHashes}` 是因为这是多个退出入口与
     *   批量对话框的既有载荷形状, 不是第二套口径。语义逐位不变: 虚拟行(未归组命中种子)无真实组
     *   key 转单种子命令; 已消失的目标跳过; 双向联动下已被真实组覆盖的成员 hash 必须剔除, 否则
     *   同一目标既发组命令又发成员命令(重复投递)。 */
    _bulkTargets() {
      const d = this._scopeResolve("sel");
      return { groupKeys: d.keys, memberHashes: d.hashes };
    },
    /* 重新校验确认框(共用 helper, 计划 26-10-05-0314 S3): 文案与调用形态**逐字**抽自
     * shortcuts.js _kbAct 键盘路径原状, 各入口共用一份 —— 批量(本文件 bulkAct)/单选右键
     * 与抽屉(drawer.js torrentCmd)/键盘(shortcuts.js _kbAct 改调本 helper)。
     * 返回 Promise<boolean>: false = 取消/Esc/点遮罩, 调用方零副作用直接返回。
     * 文案字符串全仓只此一份(静态守阵 T13 钉死, 防多入口漂移); 不放 _actCore —— 那里是
     * 键盘与批量共同出口, 会造成键盘路径双重确认, 且 torrentCmd 不走 _actCore 覆盖不全。 */
    async _recheckConfirm(what) {
      return this.confirmDialog("重新校验",
        `将对${what}重新校验: 全量重读磁盘并校验完整性, 大库上耗时长且不可中断。`, { okText: "确定" });
    },
    /* 批量动作(右键批量菜单入口): 目标集合 = _bulkTargets, 动作链交 _actCore 统一出口。
     * pause/resume/recheck 合单语义由 _actCore 的 bulk 路由承担(一次 POST + 一个聚合回执);
     * reannounce 逐目标投递 + tracker 确认聚合回执, 文案与原实现逐字一致。 */
    async bulkAct(action) {
      const { groupKeys, memberHashes } = this._bulkTargets();
      if (!groupKeys.length && !memberHashes.length) return;
      /* 重新校验先确认(计划 26-10-05-0314 S3): 与键盘路径同 helper 同文案, what 取批量形态
       * (N 个目标, 与下方 countSuffix 同口径); 取消 = 直接返回, 此时未发请求未打乐观补丁,
       * 零副作用。批量浮条已退役(2026-10-05, topbar.html), 守卫放 bulkAct 单点 —— 批量右键
       * (ctxAct)与未来任何复用本通道的批量入口同时覆盖, ctxAct 不必各接一遍。 */
      if (action === "recheck") {
        const ok = await this._recheckConfirm(`${groupKeys.length + memberHashes.length} 个目标`);
        if (!ok) return;
      }
      return this._actCore(action, {
        keys: groupKeys,
        hashes: memberHashes,
      });
    },
    /* ---------------- CTX-03 批量右键菜单的动作入口 ----------------
     * 多选右键时菜单升级为批量菜单(见 menu.js `_ctxMulti`), 动作**直接复用批量动作链路** ——
     * 目标集合的权威仍是 selGroups / selMembers, 这里不再自己拆一遍, 免得两处口径漂移。
     * 只多一件事: 先收起菜单 —— 菜单根节点是 `@click.stop`(见 index.html), 全局"点空白关闭"
     * 接不到, 而 bulkAct/bulkDelete 本身不管菜单开合, 没有关闭菜单的责任。
     */
    ctxAct(action) {
      this.menu.visible = false;
      /* 批量限速/移动(计划 26-10-02-1955 W2): 先弹对话框再走 bulk 合单, 载荷(留空方向
       * 不提交 / 目标路径)由对话框方法组装 —— 与 ctxMeta 同为"先收菜单 + 对话框持有目标
       * 集合"的形态, 不进 _actCore(那里没有对话框前置, 且限速/移动不在乐观白名单)。 */
      if (action === "limits") return this.editLimitsMulti();
      if (action === "location") return this.editMoveMulti();
      /* 批量跳检(计划 26-10-02-1955 W3): 与限速/移动同为"先收菜单 + 对话框持有目标集合"
       * 形态 —— danger 确认框前置 + 60s waitCmd, 不进 _actCore(那里没有对话框前置,
       * 且跳检不在乐观白名单, 行状态由跳检重加后的 RESYNC 自然刷新)。 */
      if (action === "skip_check") return this.skipCheckMulti();
      /* 多选导出(计划 26-10-02-1955 W4): 前端本地循环逐个触发下载(复用单 hash 导出端点),
       * **不进 bulk 合单** —— 它不是后端命令, 也没有对话框前置; 目标集合不取 _bulkTargets,
       * 直接用 selHashSet 全量展开(见 exportMulti 注释, 组选中必须含整组成员)。 */
      if (action === "export") return this.exportMulti();
      return this.bulkAct(action);
    },
    ctxDelete() {
      this.menu.visible = false;
      return this.bulkDelete();
    },
    /* 批量右键菜单的"标签/分类…"入口: 目标集合的权威在对话框(openMetaDialog 传空 =
     * 整个选中集合, 与批量动作同口径), 这里只负责先收起菜单(菜单根 @click.stop,
     * 全局"点空白关闭"接不到) */
    ctxMeta() {
      this.menu.visible = false;
      return this.openMetaDialog(null);
    },
    /* ---------------- CTX-03 单组右键菜单: 组级入口(与多选批量菜单同项集) ----------------
     * 症状(2026-10-09 用户报「单组右键菜单缺选项」): 单组菜单只有 开始/暂停/汇报 + 打开文件夹/
     * 流量图/删除, 而多选批量菜单还有 重新校验/跳检/限速/移动/标签分类/导出 —— 同一批动作在
     * 「右键 1 组」与「选 2 组」两条路径上项集不一致。这里补齐单组路径: 目标 = **该组全部成员**
     * (_groupTargets, 与 _bulkTargets 同形状的 {groupKeys, memberHashes}), 下游整份复用多选链路
     * (bulk 合单 / _skipCheckDialog / _exportHashes / openMetaDialog), 不为组级另开旁路 ——
     * 与 CTX-03「多选升级为批量菜单」同一"目标集合单点"口径。
     * 虚拟行(未归组命中种子)无真实组 key, 组级动作对其无意义 -> 返回 null(调用方直接收菜单返回)。
     * 注: 目标取成员 hash 而非组 key, 是为了让各对话框/回执里的目标数直接等于**种子数**
     * (组键在 _bulkTargets 口径里算 1 个目标, 单组场景下会显示成"1 个目标"而误导)。 */
    _groupTargets() {
      const k = this.menu.key;
      if (!k) return null;
      const g = this._findGroup(k);
      if (!g || g.virtual) return null;
      /* 展开走同一单点(selection.js::_scopeResolve), 只是取其 closure: 组闭包 = 该组全部成员 hash。
       * 这里**刻意**不带组 key(与 _bulkTargets 的 keys 通道不同)—— 见上方注释: 组键在批量口径里
       * 算 1 个目标, 单组场景下会显示成"1 个目标"而误导。 */
      const d = this._scopeResolve("anchor", { kind: "group", id: k });
      return { groupKeys: [], memberHashes: [...d.closure] };
    },
    /* 组级重新校验: 与批量菜单「重新校验」同 helper 同确认文案(what=整组), 走 _actCore 统一出口 */
    async recheckGroup() {
      const t = this._groupTargets();
      this.menu.visible = false;
      if (!t || !t.memberHashes.length) return;
      const ok = await this._recheckConfirm("整组");
      if (!ok) return;
      return this._actCore("recheck", { keys: [], hashes: t.memberHashes });
    },
    /* 组级限速/移动/跳检: 直接交多选同款对话框(scope="该组的" 让文案落到组语义), 目标锁定该组 */
    editLimitsGroup() {
      const t = this._groupTargets();
      if (!t) { this.menu.visible = false; return; }
      return this.editLimitsMulti(t, "该组的");
    },
    editMoveGroup() {
      const t = this._groupTargets();
      if (!t) { this.menu.visible = false; return; }
      return this.editMoveMulti(t, "该组的");
    },
    skipCheckGroup() {
      const t = this._groupTargets();
      if (!t) { this.menu.visible = false; return; }
      return this.skipCheckMulti(t);
    },
    /* 组级标签/分类: 目标 = 该组(openMetaDialog 收 {groupKeys, memberHashes} 形状, 与键盘路径同款) */
    metaGroup() {
      const t = this._groupTargets();
      this.menu.visible = false;
      if (!t) return;
      return this.openMetaDialog(t);
    },
    /* 组级导出: 展开成员 hash 后走与多选导出同一套逐个下载(_exportHashes), 不进 bulk 合单 */
    async exportGroup() {
      const t = this._groupTargets();
      this.menu.visible = false;
      if (!t || !t.memberHashes.length) return;
      return this._exportHashes(t.memberHashes);
    },
    /* 单种子动作(右键单种子菜单 / 抽屉头部动作 drawerAct)。目标 = hash 显式传入, 缺省回落
     * menu.hash(菜单路径本就以被点行为目标, 无需再传)。
     * !2026-10-10(S3/M3): 抽屉与键盘路径此前靠**写 this.menu.hash** 把目标"塞"进来, 现改为
     *   显式传参 —— menu 状态不再被当全局目标变量(见 conventions/webui-scope.md §3 机制 3)。 */
    async actTorrent(action, hash = "") {
      this.menu.visible = false;
      const h = hash || this.menu.hash;
      if (!h) return;
      return this._actCore(action, { keys: [], hashes: [h] });
    },
    /* 复制种子信息(种子页右键 R1A): clipboard API 优先, execCommand 降级(非安全上下文/权限拒绝);
     * 无论成功失败都给 toast 反馈 */
    async _copyText(text, label) {
      let ok = false;
      try {
        if (navigator.clipboard && window.isSecureContext) {
          await navigator.clipboard.writeText(text);
          ok = true;
        }
      } catch { ok = false; }
      if (!ok) {
        // 降级: 离屏 textarea + execCommand(旧浏览器 / file:// 等 clipboard API 不可用场景)
        const ta = document.createElement("textarea");
        ta.value = text;
        ta.style.position = "fixed";
        ta.style.opacity = "0";
        document.body.appendChild(ta);
        ta.select();
        try { ok = document.execCommand("copy"); } catch { ok = false; }
        document.body.removeChild(ta);
      }
      if (ok) this.toast(`已复制: ${label}已写入剪贴板`, "ok", 2000);
      else this.toast("复制失败: 浏览器未授权剪贴板访问", "error");
    },
    /* 模板入口别名(issue 26-10-03-1412): Vue 模板解析不到 `_` 前缀成员(保留内部域, 点复制钮
     * 恒抛 ReferenceError 且整块渲染失败), 模板可触达的处理器必须无下划线 —— drawer.html /
     * popovers.html 的复制钮走这里; JS 内部调用(drawer.js 复制菜单项)仍走 this._copyText */
    copyText(text, label) {
      return this._copyText(text, label);
    },
    /* 右键菜单复制项: field = name | hash | magnet(数据取 memberByHash 的 SEED_ITEM 完整字段) */
    /* 导出 .torrent(种子页右键 R2 补遗): fetch 字节 -> blob 下载(Bearer 走 header, 不能用 a href 直链;
     * 不能用 this.api —— 它固定 resp.json(), 而这里是二进制流; 下载核心抽在 _exportDownload,
     * 多选导出(W4)共用同一套, 本方法只补单选的 toast 语义) */
    async exportTorrent(hash = "") {
      this.menu.visible = false;
      const target = hash || this.menu.hash;
      if (!target) return;
      try {
        await this._exportDownload(target);
        this.toast("已导出: .torrent 文件已保存", "ok", 2500);
      } catch (e) {
        if (!e.auth) this.toast("导出失败: " + e.message, "error", 8000);
      }
    },
    /* 导出下载核心(单选/多选共用, W4 抽取): 裸 fetch 字节 -> Blob 触发浏览器下载(Bearer 走 header,
     * 不能用 a href 直链; 不能用 this.api —— 它固定 resp.json(), 而这里是二进制流)。
     * 401 走 _logout 收口后抛 e.auth 错(调用方 catch 静默, 与 api() 的 401 契约同形);
     * 其余非 2xx 抛 Error(detail) —— 成功/失败的 toast 由调用方按各自语义给。
     * !走低层带超时单点 aqbFetch(issue 26-10-16-1303): 裸 fetch 悬挂时 await 永不返回 =>
     *   回执永远停在"进行中"、失败 toast 也永不出现; 挂上限后悬挂变一次可报的失败(超时文案)。 */
    async _exportDownload(hash) {
      const resp = await aqbFetch(`/api/torrents/${hash}/export`, { headers: aqbAuthHeaders(this.token) });
      if (resp.status === 401) {
        this._logout("密钥无效或已更换");
        const err = new Error("unauthorized");
        err.auth = true;
        throw err;
      }
      if (!resp.ok) {
        const detail = await resp.json().catch(() => ({}));
        throw new Error(detail.detail || `HTTP ${resp.status}`);
      }
      const buf = await resp.arrayBuffer();
      const m = this.memberByHash.get(hash) || {};
      const name = String(m.name || hash).replace(/["\\/]/g, "_") + ".torrent";
      const url = URL.createObjectURL(new Blob([buf], { type: "application/x-bittorrent" }));
      const a = document.createElement("a");
      a.href = url;
      a.download = name;
      document.body.appendChild(a);
      a.click();
      a.remove();
      setTimeout(() => URL.revokeObjectURL(url), 4000);
    },
    /* 多选导出(计划 26-10-02-1955 W4, 决策点 D1 拍板 = 前端循环逐个触发下载, 零后端改动):
     * hashes 取 selHashSet 全量展开(组选中展开为成员 hash 闭包) —— 不用 _bulkTargets().memberHashes,
     * 后者把真实组的成员留在 keys 通道, 导出会漏掉整组成员(selHashSet 是选中集合的权威派生, 见
     * selection.js)。逐 hash 串行下载核心抽在 _exportHashes(单组导出 exportGroup 共用)。 */
    async exportMulti() {
      const hashes = [...this.selHashSet];
      if (!hashes.length) return;
      return this._exportHashes(hashes);
    },
    /* 导出下载批处理核心(多选 exportMulti / 单组 exportGroup 共用): 逐 hash **串行**走单选同一套
     * 裸 fetch + Blob 口径(禁并发扇出; 文件名沿用单 hash 端点的 Content-Disposition 现状);
     * 单个失败不中断整体, 结束 toast 汇总 成功 N / 失败 K。401 中途整段终止: _logout 已清会话与
     * toast, 继续循环只会再发空头。 */
    async _exportHashes(hashes) {
      const run = this._runningToast(`导出已开始: ${hashes.length} 个 .torrent 文件`);
      const failed = [];
      let ok = 0;
      for (const h of hashes) {
        try {
          await this._exportDownload(h);
          ok += 1;
        } catch (e) {
          if (e.auth) return;
          failed.push(h);
        }
      }
      if (!failed.length) {
        await this._settleRunningToast(run, "ok", `已导出: ${ok} 个 .torrent 文件`, 3000);
        return;
      }
      const heads = failed.slice(0, 3).map((h) => h.slice(0, 8)).join(", ") + (failed.length > 3 ? " …" : "");
      await this._settleRunningToast(run, "timeout", `导出: 成功 ${ok} / 失败 ${failed.length} (${heads})`, 6000);
    },
});
