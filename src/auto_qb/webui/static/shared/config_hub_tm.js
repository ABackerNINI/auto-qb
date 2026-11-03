/* config_hub_tm.js — R4 大文件拆分(计划 26-11-02-2342 §07)
 * 设置首屏 · 流量与限速(Traffic Monitor 接入/曲线/目录选择)。
 * 只搬方法定义, 实现逐行未改; 根文件已定义该域, 本片段在其后原地扩充(Object.assign)。
 * 加载序 = 四套皮肤 index.html 清单里紧跟根文件之后(与拆分前同一迭代替换序)。
 */
Object.assign(window.CONFIG_HUB.methods, {

    /* ------------------------------------------------ 全局流量来源卡 (计划 26-10-17-0339 S17/D15)
     * 一张卡合并「来源单选 + 工具状态」: provider 二选一(选中面展开); 底部状态区按 §05 五态展示
     * (auto-qb 侧探测指针); 「立即拉起/重试」促订阅线程立刻重跑; 自启开关**不是配置键** —— 状态读
     * 指针 autostart_registered, 拨动走 POST /autostart(D13); 工具自身参数(采样/阈值/适配器)经
     * 工具控制面读写, 折叠在「工具参数(高级)」—— 工具 PUT /config 是全量覆盖(last-writer-wins),
     * 参数表单必须「读后写」(先取 /status 回显整体提交)。
     * 「关闭工具」(S4, 计划 26-10-17-1737): 确认框(受影响清单取自 schema affects 元数据) ->
     * 先保存 enabled=false -> 再 POST /shutdown; 不切 provider, 「启用」一键恢复。 */
    tmProvider() {
      return this.cfgText(["config", "traffic_source", "provider"], "traffic_monitor");
    },
    tmSetProvider(v) {
      if (v) this.cfgSetPath(["config", "traffic_source", "provider"], v);
    },
    /* 数据来源总开关(S1/D1, 计划 26-10-17-1737): 关 = 停一切取数(停订阅/停拉起), 曲线发 off
     * 快照; 不写盘改别的功能配置, 开回即自恢复。UI 按 D14 **灰显不隐藏**(残留键可见可改)。 */
    tmSourceOff() {
      return this.cfgBool(["config", "traffic_source", "enabled"], true) === false;
    },
    /* 来源段自己的标量行(供 <hub-field> 渲染): 总开关 + 刷新间隔 —— 两者都是"来源本身"的属性,
     * 不随 provider 变(provider 用按钮单独渲染, 两个来源子段走 tmProviderItems)。
     * refresh_interval 是 26-10-18-0813 A3 的新键: 与曲线「执行间隔」是两个独立节奏, 行文案
     * 由 schema help 表达(那里是措辞单点, 前端不另写一份)。 */
    tmSourceRows() {
      const root = this.tmSourceRoot();
      if (!root) return [];
      const base = ["config", "traffic_source"];
      return (root.fields || [])
        .filter((x) => x.key === "enabled" || x.key === "refresh_interval")
        .map((f) => ({ type: "field", field: f, path: [...base, f.key], depth: 0, owner: base, inline: [] }));
    },
    /* 选中来源的参数行(供 <hub-field> 渲染): 从 schema 取该来源子段的叶子字段, 路径指向 traffic_source.<来源>
     *
     * B2/D16: 判据从「模板手工过滤 provider」换成通用可见性口径 —— 两个来源子段在 schema 上各挂
     * show_if=provider, 这里是它唯一的消费点。手工挑 key 与 schema 声明是两套真相: 手工那份漏改了
     * 就会出现"选 A 也显示 B 的参数"(或反之), 而 show_if 是字段元数据自身的一部分, 不会漂。
     * 之所以取叶子而非段项: 卡里要的是"平铺的参数行"(dat_path 一行), 不是可折叠的 object 子段。 */
    tmSourceRoot() {
      const g = this.cfg.schema && this.cfg.schema.groups.find((x) => x.key === "traffic_limit");
      return (g && (g.fields || []).find((f) => f.key === "traffic_source")) || null;
    },
    tmProviderItems() {
      const root = this.tmSourceRoot();
      if (!root) return [];
      const base = ["config", "traffic_source"];
      const out = [];
      for (const sub of root.fields || []) {
        if (!sub.fields) continue;  // 非 object 段(enabled / refresh_interval / provider)不算来源参数
        if (!this.cfgVisible(sub, base)) continue;  // show_if 是唯一判据
        const box = this.cfgFlatten([sub], base, 0)[0];
        for (const row of (box && box.items) || []) {
          if (row.type === "field") out.push(row);
        }
      }
      return out;
    },
    /* 合并卡三区折叠(B4/D14): 缺省展开, 折叠态不持久化(只在 hub.sub 里)
     * 键: source(来源) / curve(限速曲线) / chart(流量图采样) */
    hubSubOpen(key) {
      return this.hub.sub[key] !== false;
    },
    hubSubToggle(key) {
      this.hub.sub[key] = this.hub.sub[key] === false;
    },
    /* 「流量图采样」区(QB_TRAFFIC 段项): 可选段(optional=True)自带开关 + 折叠, 通用 section 口径 ——
     * 与 hubBlocks 生成的块同形, 这里只是把它搬进合并卡, 不另写一套渲染。 */
    tmChartSection() {
      const g = this.cfg.schema && this.cfg.schema.groups.find((x) => x.key === "traffic_limit");
      const f = g && (g.fields || []).find((x) => x.key === "qb_traffic");
      if (!f) return null;
      return this.cfgFlatten([f], ["config"], 0)[0] || null;
    },
    /* 卡头一句现状(与首页读数同源语义, 但更短): 用来在卡内三区之上先给出"这套东西现在什么状态" */
    tmSummary() {
      if (this.tmSourceOff()) return "来源已关闭";
      const src = this.tmProvider() === "global_traffic_monitor" ? "整机流量监视器" : "Traffic Monitor 文件";
      if (!this.cfgCurveEnabled()) return `${src} · 限速未启用`;
      const n = this.cfgCurveList().length;
      return n ? `${src} · ${n} 条曲线` : `${src} · 未配置曲线`;
    },
    /* 状态区五态文案(§05): ready / launching / launch_failed / not_running / not_installed */
    tmStateText() {
      return {
        ready: "已就绪", launching: "拉起中", launch_failed: "拉起失败",
        not_running: "未运行", not_installed: "未安装",
      }[this.tm.state] || "未知";
    },
    /* LED 段落色: CSS 只定义 .hb-led.ok / .warn, 其余落基态灰。
     * S6/#4: ready 曾返回 "on"(无此样式类) -> 「已就绪」显示成灰条; 现归 "ok"(绿)。 */
    tmStateClass() {
      return { ready: "ok", launching: "warn", launch_failed: "warn", not_running: "off", not_installed: "off" }[this.tm.state] || "";
    },
    async tmLoad() {
      // 重拉即作废面板上残留的动作回执(保存/自启/关闭工具) —— _panelLoad 只预清自己的错误槽
      this.tm.saveMsg = "";
      this.tm.saveErr = "";
      this.tm.autoMsg = "";
      this.tm.autoErr = "";
      await this._panelLoad(this.tm, async () => {
        const r = await this.api("/api/traffic/monitor/status");
        this.tm.enabled = !!r.enabled;
        this.tm.state = r.state || "not_running";
        this.tm.reachable = !!r.reachable;
        this.tm.toolUrl = r.tool_url || "";
        this.tm.tokenPath = r.token_path || "";
        this.tm.version = r.version || "";
        this.tm.pid = r.pid || 0;
        this.tm.dataDir = r.data_dir || "";
        this.tm.autostartRegistered = !!r.autostart_registered;
        this.tm.autostartError = r.autostart_error || "";
        this.tm.error = r.error || "";
        this.tm.retryS = Number(r.retry_s) || 0;
        this.tm.claimNote = r.claim_note || null;
        this.tm.status = r.status || null;
        if (this.tm.reachable && r.status && r.status.config) {
          this.tm.form = this.tmNormalizeForm(r.status.config);
        }
      }, {
        loading: "loading", err: "error", errFallback: "读取失败",
        authGated: false,  // 状态轮询的失败(含 auth)都要落「不可达」上屏, 不静默
        keepErr: true,     // 不预清状态槽: tm.error 由响应/失败分支落值(与 dialogs 四块面板不同)
        onErr: () => {     // 失败态装配(轮询口径: 拿不到 = 未运行)
          this.tm.reachable = false;
          this.tm.state = "not_running";
          this.tm.status = null;
        },
        onFinally: () => { this.tm.loaded = true; },
      });
    },
    /* 「立即拉起/重试」: 促订阅线程立刻重跑并忽略失败退避; 之后短轮询 status 观察 launching -> ready/launch_failed */
    async tmRelaunch() {
      if (this.tm.relaunching) return;
      this.tm.relaunching = true;
      this.tm.error = "";
      try {
        await this.api("/api/traffic/monitor/relaunch", { method: "POST" });
        this.tm.state = "launching";
        this.tm.retryS = 0;
        this.tmPollSettle();
      } catch (e) {
        this.tm.error = (e && e.message) || "促拉起失败";
        this.tm.relaunching = false;
      }
    },
    /* 轮询收敛(有界): 每 2s 重读状态, 直到离开 launching 或到上限 —— 走轮询骨架的 awaitPoll
     * 单点(polling.js): 同名 key 自带先停后起, 代际守卫不必再手写(漏掉代际检查曾是
     * "两条轮询链叠加双请求"的隐患); 与 tmPollShutdown 共用 key ⇒ 两条链天然不叠加。 */
    tmPollSettle() {
      this.awaitPoll("tm", {
        ms: () => 2000,
        max: 16,  // 旧实现 n < 15 递归 ⇒ n = 0..15, 共 16 拍(拍数上限语义换成 max, 次数不变)
        fn: () => this.tmLoad(),
        until: () => this.tm.state !== "launching",
        onEnd: () => { this.tm.relaunching = false; },  // 收敛/耗尽都收摊(与旧实现同)
      });
    },
    /* 「关闭工具」(S4/D3/D4, 计划 26-10-17-1737): 确认框列出受影响功能(清单取自 schema
     * 字段 enabled 的 affects 元数据, 不另写一份) -> 先保存 enabled=false(热重载即停订阅 /
     * 停拉起, 关闭可逆) -> 再 POST /shutdown 停工具进程; 不切 provider。 */
    tmAffectLabels() {
      const root = this.tmSourceRoot();
      const f = root && (root.fields || []).find((x) => x.key === "enabled");
      return ((f && f.affects) || []).map((id) => TM_AFFECT_LABELS[id] || id);
    },
    async tmShutdownTool() {
      if (this.tm.shutting) return;
      const items = this.tmAffectLabels();
      let body = "将停止工具进程, 并关闭整个流量来源功能: " + (items.join("; ") || "取数将全部暂停") +
        "; 开机自启注册不受影响。";
      if (this.cfgDirty) body += "当前还有其它未保存改动, 也会一并保存。";
      body += "之后打开上方「启用」即可恢复。";
      const ok = await this.confirmDialog("关闭工具", body, { okText: "关闭工具", danger: true });
      if (!ok) return;
      this.tm.shutting = true;
      this.tm.shutdownMsg = "";
      this.tm.shutdownErr = "";
      try {
        // 次序(D3): 先落盘 enabled=false 并热重载(订阅线程随之停), 再停工具进程 ——
        // 反序会让停工具的瞬间又被订阅线程抢拉起来。
        this.cfgSetBool(["config", "traffic_source", "enabled"], false);
        const saved = await this.cfgSave();
        if (!saved) {
          // 保存失败: 内存态回滚成 true 与磁盘一致(工具继续跑, 用户可重试; 不留「内存关了
          // 盘没关」的错位——那会让下次普通保存把关闭静默写进去)。
          this.cfgSetBool(["config", "traffic_source", "enabled"], true);
          this.tm.shutdownErr = "保存失败, 未停止工具(可重试)";
          return;
        }
        try {
          await this.api("/api/traffic/monitor/shutdown", { method: "POST" });
          this.tm.shutdownMsg = "已关闭工具进程";
        } catch (e) {
          this.tm.shutdownErr = "来源已关闭并保存; 停止工具失败: " + ((e && e.message) || "未知错误");
        }
        await this.tmLoad();
        this.tmPollShutdown();
      } finally {
        this.tm.shutting = false;
      }
    },
    /* 停止后轮询收敛(有界): 每 1s 重读状态, 直到工具离开 ready(指针删除即 not_running)或到
     * 上限; 与 tmPollSettle 同 key ⇒ 先停后起, 两条链不叠加。 */
    tmPollShutdown() {
      this.awaitPoll("tm", {
        ms: () => 1000,
        max: 11,  // 旧实现 n < 10 递归 ⇒ n = 0..10, 共 11 拍
        fn: () => this.tmLoad(),
        until: () => this.tm.state !== "ready",
      });
    },
    /* 「以本安装重登记」(D4/D5, 计划 26-10-20-1316 §03): 二次确认 -> 有界前台跑安装内
     * claim 启动器(人工易主唯一通道)。工具正在跑/数据归属异会被工具侧拒绝(409), 其人话
     * 输出原样进 claimErr —— auto-qb 不解释只转述。成功后刷状态(注记被工具侧清除)。 */
    async tmClaim() {
      if (this.tm.claiming) return;
      const ok = await this.confirmDialog(
        "以本安装重登记",
        "将把本安装登记为整机正主(唯一写数据的安装), 并原子重写正主记录。" +
          "工具正在运行时会被拒绝(请先「关闭工具」); 数据目录属于其它安装时也会被拒绝。" +
          "确认继续?",
        { okText: "重登记" }
      );
      if (!ok) return;
      this.tm.claiming = true;
      this.tm.claimMsg = "";
      this.tm.claimErr = "";
      try {
        const r = await this.api("/api/traffic/monitor/claim", { method: "POST" });
        this.tm.claimMsg = (r && r.output) || "已重登记为正主";
        await this.tmLoad();
      } catch (e) {
        this.tm.claimErr = (e && e.message) || "重登记失败";
      } finally {
        this.tm.claiming = false;
      }
    },
    /* 工具配置 -> 表单: 列表字段折成逗号串(表单是纯文本输入), 其余原样
     * (时间/大小/速率是复合串 "30S"/"10MiB"/"1GiB/s", 原样留在表单里, 由单位控件拆成「数值 + 单位」显示) */
    tmNormalizeForm(cfg) {
      const out = {};
      for (const k of Object.keys(cfg || {})) {
        const v = cfg[k];
        out[k] = Array.isArray(v) ? v.join(", ") : v;
      }
      return out;
    },
    /* 表单 -> 工具配置载荷(全量覆盖, last-writer-wins): 列表字段逗号串转数组, 其余按 kind 归一。
     * S7/D13: 时间/大小/速率**不再 Number() 化**(数值化会丢掉单位), 复合串原样回传; 用户没动过的键
     * 也原样回传 —— 旧版工具回显的裸数值因此能无损往返, 迁移的语义平移由工具侧负责。 */
    tmBuildPayload() {
      const f = this.tm.form;
      const num = (x) => (x === "" || x === null || x === undefined ? 0 : Number(x));
      const list = (x) => String(x || "").split(",").map((s) => s.trim()).filter(Boolean);
      const out = {};
      for (const p of this.tmParams()) {
        const v = f[p.key];
        if (v === undefined) continue;  // 工具没回显该键: 不发明值(丢给工具侧默认)
        if (p.kind === "list") out[p.key] = list(v);
        else if (p.kind === "time" || p.kind === "size" || p.kind === "speed") out[p.key] = v;
        else if (p.kind === "text") out[p.key] = String(v || "");
        else out[p.key] = num(v);
      }
      return out;
    },
    /* 工具参数的单位拆/合(S7/D12/D13): 复用设置页同一套单位表(cfgUnitParts / cfgUnitOptions /
     * cfgUnitLabel) —— 前端只做显示层拆合("10MiB" -> 10 + MiB), 文法与取值权威在工具侧
     * (gtm/units.py)。空数值写空串(= 未配置) 而不是 "MiB" 这种无数字值。 */
    tmUnitParts(p) {
      return this.cfgUnitParts(p.kind, this.tm.form[p.key], p.unitDefault);
    },
    tmSetUnitPart(p, num, unit) {
      const n = String(num === undefined || num === null ? "" : num).trim();
      this.tm.form[p.key] = n ? n + (unit || "") : "";
    },
    /* 工具参数行的「?」: 复用设置页的就近说明浮窗(hubAsk / hub.helpKey)。工具参数不在配置树里,
     * 走不了 hub-field, 故用合成 item 承载「字段样」元数据(label/kind/help/default 四件)。 */
    tmAskKey(p) {
      return "tool." + p.key;
    },
    tmAskItem(p) {
      return {
        type: "field",
        path: ["tool", p.key],
        field: { label: p.label, kind: p.kind, help: p.help, default: p.def },
      };
    },
    async tmSave() {
      await this._panelLoad(this.tm, async () => {
        const r = await this.api("/api/traffic/monitor/config", {
          method: "PUT",
          body: JSON.stringify({ config: this.tmBuildPayload() }),
        });
        if (r && r.config) this.tm.form = this.tmNormalizeForm(r.config);
        this.tm.saveMsg = "已保存（工具侧已热重载）";
      }, { loading: "saving", err: "saveErr", errFallback: "保存失败", authGated: false });
    },
    /* 自启开关: 读指针 autostart_registered, 拨动只发 install/uninstall; 失败回滚勾选态 */
    async tmAutostart(action) {
      const desired = action === "install";
      await this._panelLoad(this.tm, async () => {
        const r = await this.api("/api/traffic/monitor/autostart", {
          method: "POST",
          body: JSON.stringify({ action: action }),
        });
        this.tm.autoMsg = (r && r.message) || "已处理";
        this.tm.autostartRegistered = desired;
      }, {
        loading: "autoBusy", err: "autoErr", errFallback: "操作失败", authGated: false,
        onErr: () => { this.tm.autostartRegistered = !desired; },  // 失败回滚勾选态(与指针一致)
      });
    },
    tmFmtBytes(n) {
      return this.fmtSize(n);
    },
    /* S7 次级可见面: 「最近异常」一行(设置页工具状态区)。数据源 = 工具 GET /status.last_spike
     * (S5 采样器落 state 的最近一轮越界记录), 前端只读不改。
     * 24h 外或旧工具无该键/无越界 -> null(整行不渲染); 展示口径与日志同字段(阈值/速率)。 */
    tmLastSpikeText() {
      const s = this.tm.status && this.tm.status.last_spike;
      if (!s || !Array.isArray(s.items) || !s.items.length) return null;
      const t = Date.parse(s.ts);
      if (!Number.isFinite(t) || Date.now() - t > 24 * 3600 * 1000) return null;
      const p = (n) => String(n).padStart(2, "0");
      const d = new Date(t);
      const at = `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}`;
      const dir = (x) => (x === "up" ? "上行" : "下行");
      const detail = s.items.map((it) => `${it.nic} ${dir(it.dir)} ${this.fmtSpeed(it.rate_bps)}`).join("；");
      const thr = s.threshold_bps ? `（阈值 ${this.fmtSpeed(s.threshold_bps)}，仅告警已照常入账）` : "（仅告警已照常入账）";
      return `${at} ${detail}${thr}`;
    },
    /* ---- 文件选择器(D10③): 找不到工具时, 目录导航 + 文件名输入写 tool_exe / tool_dir ----
     * 后端 /api/fs/dirs 只列目录、且限在允许的保存路径内 —— 工具安装目录若不在范围内, 走上方文本框
     * 手填绝对路径; 在范围内可直接导航并用文件名拼出绝对路径写 tool_exe。 */
    tmPickOpen() {
      this.tm.pick.open = true;
      this.tm.pick.name = "";
      this.tm.pick.error = "";
      this.tmPickLoad("");
    },
    async tmPickLoad(path) {
      await this._panelLoad(this.tm.pick, async () => {
        const r = await this.api("/api/fs/dirs?path=" + encodeURIComponent(path || ""));
        this.tm.pick.path = r.path || "";
        this.tm.pick.parent = r.parent || "";
        this.tm.pick.dirs = r.dirs || [];
      }, {
        loading: "loading", err: "error", errFallback: "目录读取失败", authGated: false,
        onErr: () => { this.tm.pick.dirs = []; },
      });
    },
    tmPickEnter(d) {
      this.tmPickLoad(d.path);
    },
    tmPickUp() {
      if (this.tm.pick.parent) this.tmPickLoad(this.tm.pick.parent);
    },
    tmPickApplyDir() {
      if (!this.tm.pick.path) return;
      this.cfgSetPath(["config", "traffic_source", "global_traffic_monitor", "tool_dir"], this.tm.pick.path);
      this.tm.pick.open = false;
    },
    tmPickApplyExe() {
      const name = String(this.tm.pick.name || "").trim();
      if (!this.tm.pick.path || !name) return;
      const sep = this.tm.pick.path.indexOf("\\") >= 0 ? "\\" : "/";
      this.cfgSetPath(["config", "traffic_source", "global_traffic_monitor", "tool_exe"],
        this.tm.pick.path.replace(/[\\/]+$/, "") + sep + name);
      this.tm.pick.open = false;
    },
    /* 工具参数表(§05 工具侧参数): 键/标签/控件形态/说明; 模板按此 v-for 渲染, 避免 11 行硬编码。
     * S7/D12/D13: kind=time/size/speed 走「数值框 + 单位下拉 + ?」——
     *   - 单位表与设置页同源(cfgUnitOptions / UNIT_OPTIONS), 默认单位由 unitDefault 给;
     *   - 盘上与契约只留复合串("30S"/"10MiB"), 这里只负责显示层拆合;
     *   - def 只作「?」浮窗的「默认值」展示, **真值以工具侧 gtm/config.py 为权威**(写错不会生效,
     *     校验权威与默认值都在工具那一侧, 前端不复制)。
     * kind=list 的 hint 是输入框占位(逗号分隔正则); kind=text/int 走普通输入框。 */
    tmParams() {
      return [
        {
          key: "sample_interval", label: "采样间隔", kind: "time", unitDefault: "S", def: "5S",
          help: "多久读一次网卡计数器。越小曲线越细、CPU 占用越高; 两次采样之间的峰值取不到。"
            + "改完立即生效(热重载), 不用重启工具。",
        },
        {
          key: "flush_delta_bytes", label: "落盘阈值", kind: "size", unitDefault: "MiB", def: "1MiB",
          help: "累计流量变化达到这个量就立刻把增量追加进 history_traffic.dat。"
            + "调大 = 写盘次数更少, 但工具崩溃时丢的增量更多。与「落盘间隔」是「谁先到算谁」的关系。",
        },
        {
          key: "flush_interval_s", label: "落盘间隔", kind: "time", unitDefault: "S", def: "30S",
          help: "即使没到「落盘阈值」, 也最多隔这么久落一次盘 —— 低速时的兜底节奏。"
            + "调小 = 历史图更新更勤, 写盘更频繁。",
        },
        {
          key: "notify_threshold_bytes", label: "通知阈值", kind: "size", unitDefault: "MiB",
          def: "100MiB",
          help: "当日累计流量每涨这么多, 工具就向 auto-qb 推一次事件, 让它立刻重读历史文件刷新图表。"
            + "auto-qb 侧还有一层刷新冷却, 两边都设才不会被频繁推送牵着跑。",
        },
        {
          key: "sample_rate_warn_bps", label: "单轮速率告警阈值", kind: "speed", unitDefault: "GiB/s",
          def: "1GiB/s",
          help: "单个网卡单方向的速率(本轮增量/有效间隔)超过这个值就告警。只告警、不拦截, 流量照常入账;"
            + "告警会出现在设置页「最近异常」与工具日志里。默认 1GiB/s 覆盖常见千兆/2.5G/万兆峰值,"
            + "线路能跑满万兆时可适当调高。",
        },
        {
          key: "http_host", label: "控制面监听地址", kind: "text", def: "127.0.0.1",
          help: "工具本机 HTTP 接口(控制面)绑哪个地址, auto-qb 就是从这里读状态、下配置的。"
            + "一般不用改; 改成 0.0.0.0 会暴露给局域网(控制面靠 Bearer 密钥鉴权)。"
            + "**改完要重启工具才生效**(改绑监听地址无法热切换)。",
        },
        {
          key: "http_port", label: "控制面端口", kind: "int", def: "0",
          help: "控制面端口。0 = 每次启动由系统分配随机空闲端口(推荐, 不会与别的程序抢端口);"
            + "填固定端口便于手工调试。auto-qb 靠工具的发现指针找端口, 不需要你填这里。"
            + "**改完要重启工具才生效**。",
        },
        {
          key: "lease_ttl_s", label: "订阅租约", kind: "time", unitDefault: "S", def: "3M",
          help: "订阅租约时长(默认 3 分钟 = 180 秒): 超过这么久没收到 auto-qb 的心跳, 工具就把这个订阅剔除、"
            + "不再向它推送。必须明显大于「心跳周期」, 否则 auto-qb 会被误判为掉线。",
        },
        {
          key: "heartbeat_interval_s", label: "心跳周期", kind: "time", unitDefault: "S", def: "1M",
          help: "auto-qb 每隔这么久续一次租约(默认 1 分钟 = 60 秒)。改这个值只影响之后的续租节奏, "
            + "auto-qb 在订阅响应里拿到新值后自动跟随。",
        },
        {
          key: "notify_timeout_s", label: "推送超时", kind: "time", unitDefault: "S", def: "3S",
          help: "向 auto-qb 推事件的单次超时。超时只记一条失败并等下一轮, 不影响落盘与采样。",
        },
        {
          key: "adapter_include", label: "适配器白名单", kind: "list", def: "",
          hint: "逗号分隔正则, 留空 = 全部",
          help: "只统计名称匹配这些正则的网卡(逗号分隔)。留空 = 不设白名单。"
            + "回环与已断开的网卡本来就默认排除, 不用在这里写。",
        },
        {
          key: "adapter_exclude", label: "适配器黑名单", kind: "list", def: "",
          hint: "逗号分隔正则, 留空 = 不排除",
          help: "排除名称匹配这些正则的网卡(逗号分隔)。虚拟机 / VPN / 蓝牙之类的虚拟网卡常被重复计数,"
            + "填它们的名字可避免把同一份流量算两遍。",
        },
      ];
    },
});
