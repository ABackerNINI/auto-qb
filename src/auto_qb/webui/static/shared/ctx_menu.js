/* auto-qb WEB UI · 行右键菜单注册表 + 用户布局解析(计划 26-10-20-0024 W2)
 *
 * 背景: ctx-menus.html 四支菜单此前是**静态模板直写**(每支一项一行 HTML), 项集奇偶靠人肉
 * (pitfalls/web-ui/ctx-menu-branch-parity.md: 2026-10-09 用户报「辅种页单组右键菜单缺选项」——
 * 给批量支补项漏了单组支, 两条路径静默分叉)。本文件把四支项集收敛到**注册表单点**:
 *   - CTX_ITEM_DEFS / CTX_SUB_ITEM_DEFS: (分支, id) -> 静态描述 + 运行时钩子, 定义序 = 默认布局
 *   - DEFAULT_CTX_LAYOUT: 从定义序生成 —— 与静态模板逐位一致(守阵钉, 见 W2 node 电池)
 *   - ctxMergeLayout / ctxRenderLayer: 用户布局(web.ctx_menu, 经 /api/webui/flags 下发)与
 *     注册表的合并语义(补尾/显隐槽位/跨层/分隔线一等公民), 与列偏好 colOrder/colHidden 双轨同款
 * 消费面(模板 v-for + menu.js 适配)在 W3; 本文件先行落地, 无人消费时零行为变化。
 *
 * 挂载面(与 drawer_templates.js 同范式——数据/纯函数与 mixin 分离):
 *   window.AQB_CTX_MENU_REG —— 注册表 + 默认布局 + 纯函数(node 单测电池与定制块共用)
 *   window.AQB_CTX_MENU     —— Vue mixin(app.js 末尾 app.mixin(window.AQB_CTX_MENU))
 * !本文件在 HTML 里必须排在 app.js **之前**; 排在 menu.js 之后(子菜单展开交互
 *   openSub/keepSub/scheduleSubClose 与钳位仍在 menu.js, 本文件只产出数据与分派)。
 */
(function () {
  "use strict";

  /* 四支分支名(与 triggers.js variant 口径一致; 模板判据链 menu.multi / menu.episode /
   * menu.hash / v-else 原样保留, 静态守阵 T3 的比对面不动)。 */
  const CTX_BRANCHES = ["multi", "episode", "member", "group"];
  /* 次级菜单名(state.js subMenu: "" | "advanced"; 全库仅此一个次级, 四支共用) */
  const CTX_SUB_NAME = "advanced";
  /* 门控键 -> flags 真值(与模板 v-if 逐字同径):
   *   skip_check_menu = web.skip_check_menu(fail-closed, 后端端点同步拒单)
   *   qb_traffic      = flags.qb_traffic_enabled(流量图入口, 无入口即无请求) */
  const CTX_GATE_FLAG = { skip_check_menu: "skip_check_menu", qb_traffic: "qb_traffic_enabled" };

  /* ---------------- 一级(level 0)注册表 ----------------
   * 每项字段:
   *   id    支内唯一(分隔线 token 亦占 id); label = 串或 (vm) => 串(动态文案)
   *   icon  { cls, use } —— cls 为 "" 时渲染 class="ico ico-sm"(危险项原样); use 如 "#i-play"
   *   act   (vm) => void —— 点击分派, 原方法调用逐字平移(动作链一行不动, 只改"渲染哪些项")
   *   gate  flags 门控键: 关时**不渲染**(v-if 语义), 布局槽位保留(用户开开关即归位)
   *   dyn   "reannounce" —— 运行时置灰 + title 钩子(reannounceMenuGate, qB 口径; 判据单点
   *         decorate.js::REANNOUNCE_BLOCKED_STATES, 目标全部非活跃时置灰不可用)
   *   danger true —— .ctx-item.danger 样式
   *   kind  "item"(缺省) | "sep" | "submenu"; submenu = 「更多操作」父项(次级内容见 CTX_SUB_ITEM_DEFS)
   */
  const CTX_ITEM_DEFS = {
    /* 批量(多选升级, CTX-03): 目标 = 整个选中集合, 动作走 ctxAct/bulk 链 */
    multi: [
      { id: "resume", label: "批量启动", icon: { cls: "ico-play", use: "#i-play" }, act: (vm) => vm.ctxAct("resume") },
      { id: "pause", label: "批量停止", icon: { cls: "ico-pause", use: "#i-pause" }, act: (vm) => vm.ctxAct("pause") },
      { id: "reannounce", label: "强制重新汇报", icon: { cls: "ico-sync", use: "#i-refresh" }, dyn: "reannounce", act: (vm) => vm.ctxAct("reannounce") },
      { id: "sep:d1", kind: "sep" },
      { id: "recheck", label: "强制重新检查", icon: { cls: "ico-recheck", use: "#i-refresh" }, act: (vm) => vm.ctxAct("recheck") },
      { id: "skip_check", label: "跳过哈希校验…", icon: { cls: "ico-recheck", use: "#i-bolt" }, gate: "skip_check_menu", act: (vm) => vm.ctxAct("skip_check") },
      { id: "limits", label: "速度限制…", icon: { cls: "ico-gauge", use: "#i-gauge" }, act: (vm) => vm.ctxAct("limits") },
      { id: "move", label: "设定位置…", icon: { cls: "ico-move", use: "#i-folder-open" }, act: (vm) => vm.ctxAct("location") },
      { id: "meta", label: "标签/分类…", icon: { cls: "ico-tag", use: "#i-tag" }, act: (vm) => vm.ctxMeta() },
      { id: "export", label: "导出 .torrent", icon: { cls: "ico-export", use: "#i-download" }, act: (vm) => vm.ctxAct("export") },
      { id: "sep:d2", kind: "sep" },
      { id: "delete", label: "批量删除…", icon: { cls: "", use: "#i-trash" }, danger: true, act: (vm) => vm.ctxDelete() },
    ],
    /* 整集整剧(shows.js openShowEpMenu/openShowMenu): scope=ep/show 决定动态文案 */
    episode: [
      { id: "resume", label: (vm) => (vm.menu.episode.scope === "show" ? "启动整剧" : "启动整集"), icon: { cls: "ico-play", use: "#i-play" }, act: (vm) => vm.actEpisode("resume") },
      { id: "pause", label: (vm) => (vm.menu.episode.scope === "show" ? "停止整剧" : "停止整集"), icon: { cls: "ico-pause", use: "#i-pause" }, act: (vm) => vm.actEpisode("pause") },
      { id: "reannounce", label: "强制重新汇报", icon: { cls: "ico-sync", use: "#i-refresh" }, dyn: "reannounce", act: (vm) => vm.actEpisode("reannounce") },
      { id: "sep:d1", kind: "sep" },
      { id: "open-path", label: "打开目标文件夹", icon: { cls: "ico-folder", use: "#i-folder-open" }, act: (vm) => vm.openTargetPath("torrent", vm.menu.episode.hashes[0]) },
      { id: "sep:d2", kind: "sep" },
      { id: "delete", label: (vm) => (vm.menu.episode.scope === "show" ? "删除整剧…" : "删除整集…"), icon: { cls: "", use: "#i-trash" }, danger: true, act: (vm) => vm.delEpisode() },
    ],
    /* 单种子(menu.hash): 一级 14 项(含「更多操作」父项) + 5 线; 次级 11 项 + 2 线见 CTX_SUB_ITEM_DEFS */
    member: [
      { id: "resume", label: "启动该种子", icon: { cls: "ico-play", use: "#i-play" }, act: (vm) => vm.actTorrent("resume") },
      { id: "pause", label: "停止该种子", icon: { cls: "ico-pause", use: "#i-pause" }, act: (vm) => vm.actTorrent("pause") },
      { id: "reannounce", label: "强制重新汇报", icon: { cls: "ico-sync", use: "#i-refresh" }, dyn: "reannounce", act: (vm) => vm.actTorrent("reannounce") },
      { id: "sep:d1", kind: "sep" },
      { id: "info", label: "详细信息", icon: { cls: "ico-info", use: "#i-info" }, act: (vm) => vm.openTorrentDrawer(vm.menu.hash) },
      { id: "sep:d2", kind: "sep" },
      { id: "limits", label: "速度限制…", icon: { cls: "ico-gauge", use: "#i-gauge" }, act: (vm) => vm.editLimits() },
      { id: "move", label: "设定位置…", icon: { cls: "ico-move", use: "#i-folder-open" }, act: (vm) => vm.editMove() },
      { id: "rename", label: "重命名…", icon: { cls: "ico-rename", use: "#i-pencil" }, act: (vm) => vm.editRename() },
      { id: "meta", label: "标签/分类…", icon: { cls: "ico-tag", use: "#i-tag" }, act: (vm) => vm.openMetaDialog(vm.menu.hash) },
      { id: "sep:d3", kind: "sep" },
      { id: "recheck", label: "强制重新检查", icon: { cls: "ico-recheck", use: "#i-refresh" }, act: (vm) => vm.torrentCmd("recheck", null, "强制重新检查") },
      { id: "skip_check", label: "跳过哈希校验…", icon: { cls: "ico-recheck", use: "#i-bolt" }, gate: "skip_check_menu", act: (vm) => vm.skipCheckTorrent() },
      { id: "export", label: "导出 .torrent", icon: { cls: "ico-export", use: "#i-download" }, act: (vm) => vm.exportTorrent() },
      { id: "open-path", label: "打开目标文件夹", icon: { cls: "ico-folder", use: "#i-folder-open" }, act: (vm) => vm.openTargetPath("torrent", vm.menu.hash) },
      { id: "sep:d4", kind: "sep" },
      /* 「更多操作」父项: 次级内容 = CTX_SUB_ITEM_DEFS.member; D7 次级无可见项时不渲染父项 */
      { id: "sub-more", label: "更多操作", icon: { cls: "ico-tune", use: "#i-sliders" }, kind: "submenu" },
      { id: "sep:d5", kind: "sep" },
      { id: "delete", label: "删除该种子…", icon: { cls: "", use: "#i-trash" }, danger: true, act: (vm) => vm.delTorrent() },
    ],
    /* 单组(v-else): 目标 = 该组全部成员(组级六入口复用批量链, commands.js) */
    group: [
      { id: "resume", label: "启动整组", icon: { cls: "ico-play", use: "#i-play" }, act: (vm) => vm.act("resume") },
      { id: "pause", label: "停止整组", icon: { cls: "ico-pause", use: "#i-pause" }, act: (vm) => vm.act("pause") },
      { id: "reannounce", label: "强制重新汇报", icon: { cls: "ico-sync", use: "#i-refresh" }, dyn: "reannounce", act: (vm) => vm.act("reannounce") },
      { id: "sep:d1", kind: "sep" },
      { id: "recheck", label: "强制重新检查", icon: { cls: "ico-recheck", use: "#i-refresh" }, act: (vm) => vm.recheckGroup() },
      { id: "skip_check", label: "跳过哈希校验…", icon: { cls: "ico-recheck", use: "#i-bolt" }, gate: "skip_check_menu", act: (vm) => vm.skipCheckGroup() },
      { id: "limits", label: "速度限制…", icon: { cls: "ico-gauge", use: "#i-gauge" }, act: (vm) => vm.editLimitsGroup() },
      { id: "move", label: "设定位置…", icon: { cls: "ico-move", use: "#i-folder-open" }, act: (vm) => vm.editMoveGroup() },
      { id: "meta", label: "标签/分类…", icon: { cls: "ico-tag", use: "#i-tag" }, act: (vm) => vm.metaGroup() },
      { id: "export", label: "导出 .torrent", icon: { cls: "ico-export", use: "#i-download" }, act: (vm) => vm.exportGroup() },
      { id: "sep:d2", kind: "sep" },
      { id: "open-path", label: "打开目标文件夹", icon: { cls: "ico-folder", use: "#i-folder-open" }, act: (vm) => vm.openTargetPath("group", vm.menu.key) },
      { id: "qb-traffic", label: "qB 口径流量图", icon: { cls: "", use: "#i-chart" }, gate: "qb_traffic", act: (vm) => vm.openQbGroup(vm.menu.key) },
      { id: "sep:d3", kind: "sep" },
      { id: "delete", label: (vm) => `删除该${vm.l10nGroup}…`, icon: { cls: "", use: "#i-trash" }, danger: true, act: (vm) => vm.delGroup() },
    ],
  };

  /* ---------------- 次级(level 1, 「更多操作」)注册表 ----------------
   * 现状仅 member 支有默认内容(FX-15 分层: qB 通用低频项); D7 四支统一次级 —— 其余三支次级
   * 默认为空, 用户可把任意支的项移入(移入即创建入口, 为空不显示)。 */
  const CTX_SUB_ITEM_DEFS = {
    member: [
      { id: "queue-top", label: "队列顶部", icon: { cls: "ico-queue", use: "#i-sort" }, act: (vm) => vm.torrentCmd("queue", { action: "top" }, "队列顶部") },
      { id: "queue-up", label: "向上移动队列", icon: { cls: "ico-queue", use: "#i-sort" }, act: (vm) => vm.torrentCmd("queue", { action: "up" }, "向上移动队列") },
      { id: "queue-down", label: "向下移动队列", icon: { cls: "ico-queue", use: "#i-sort" }, act: (vm) => vm.torrentCmd("queue", { action: "down" }, "向下移动队列") },
      { id: "queue-bottom", label: "队列底部", icon: { cls: "ico-queue", use: "#i-sort" }, act: (vm) => vm.torrentCmd("queue", { action: "bottom" }, "队列底部") },
      /* 次级默认线 token 用 s 前缀(sep:s1/s2): 与一级 d 前缀错开 —— 同支两层 token 恒唯一,
       * 跨层拖分隔线才不会被「目标层已有同名 token」的去重规则吞掉 */
      { id: "sep:s1", kind: "sep" },
      { id: "super-seeding", label: (vm) => (vm.menuTorrent().super_seeding ? "关闭超级做种" : "开启超级做种"), icon: { cls: "ico-super", use: "#i-shield" }, act: (vm) => vm.torrentCmd("super-seeding", { enable: !vm.menuTorrent().super_seeding }, vm.menuTorrent().super_seeding ? "关闭超级做种" : "开启超级做种") },
      { id: "force-start", label: (vm) => (vm.menuTorrent().force_start ? "取消强制启动" : "强制启动"), icon: { cls: "ico-force", use: "#i-bolt" }, act: (vm) => vm.torrentCmd("force-start", { enable: !vm.menuTorrent().force_start }, vm.menuTorrent().force_start ? "取消强制启动" : "强制启动") },
      { id: "auto-tmm", label: (vm) => (vm.menuTorrent().auto_tmm ? "关闭自动种子管理" : "开启自动种子管理"), icon: { cls: "ico-tmm", use: "#i-shield" }, act: (vm) => vm.autoTmmToggle() },
      { id: "share-limits", label: "分享率限制…", icon: { cls: "ico-percent", use: "#i-percent" }, act: (vm) => vm.editShareLimits() },
      { id: "sep:s2", kind: "sep" },
      { id: "copy-name", label: "复制名称", icon: { cls: "ico-copy", use: "#i-copy" }, act: (vm) => vm.copyTorrentInfo("name") },
      { id: "copy-hash", label: "复制哈希", icon: { cls: "ico-copy", use: "#i-copy" }, act: (vm) => vm.copyTorrentInfo("hash") },
      { id: "copy-magnet", label: "复制 magnet", icon: { cls: "ico-copy", use: "#i-copy" }, act: (vm) => vm.copyTorrentInfo("magnet") },
    ],
  };

  /* 默认布局: 从定义序生成 —— 不写 web.ctx_menu 时四支与静态模板逐位一致(零漂移验收) */
  const DEFAULT_CTX_LAYOUT = {};
  for (const branch of CTX_BRANCHES) {
    DEFAULT_CTX_LAYOUT[branch] = {
      order: (CTX_ITEM_DEFS[branch] || []).map((d) => d.id),
      hidden: [],
      sub: { order: (CTX_SUB_ITEM_DEFS[branch] || []).map((d) => d.id), hidden: [] },
    };
  }

  /* ---------------- 纯函数面(注册表查询 / 布局合并 / 渲染解析) ----------------
   * 全部不碰 DOM 与 Vue —— node 单测电池(W2 守阵钉)与 W4 定制块共用同一份语义。 */

  function ctxIsSepToken(token) {
    return typeof token === "string" && token.indexOf("sep:") === 0;
  }

  function ctxDefsOf(branch, level) {
    return (level === 1 ? CTX_SUB_ITEM_DEFS[branch] : CTX_ITEM_DEFS[branch]) || [];
  }

  /* (分支, token) -> 定义; 两层合查(跨层移动后项的"家"在另一层, 同支两层 token 恒唯一) */
  function ctxDefById(branch, id) {
    const defs = (CTX_ITEM_DEFS[branch] || []).concat(CTX_SUB_ITEM_DEFS[branch] || []);
    for (const d of defs) if (d.id === id) return d;
    return null;
  }

  /* 一层布局合并(支级或次级): 用户序优先, 未入序项按定义序补尾, 隐藏集独立。
   *   - 接受 token = 本层定义 | 对层定义(跨层移动的落点) | sep token(用户添加的线)
   *   - 用户序里的未知 id(注册表没有/已退役)忽略 —— 换版本不丢布局(列偏好同款韧性)
   *   - 补尾跳过 claimedElsewhere(对层用户序已认领的 id): 跨层移走 ≠ 缺省补回原层
   *   - 隐藏项(含 sep token)仍在 order 占位: 勾选恢复即归位(与 colHidden 同款)
   */
  function ctxMergeLayer(branch, level, layerCfg, claimedElsewhere) {
    const defs = ctxDefsOf(branch, level);
    const hidden = new Set(
      layerCfg && Array.isArray(layerCfg.hidden) ? layerCfg.hidden.filter((t) => typeof t === "string") : []
    );
    const byId = new Map();
    for (const d of defs) byId.set(d.id, d);
    const order = [];
    const seen = new Set();
    const userOrder = layerCfg && Array.isArray(layerCfg.order) ? layerCfg.order : null;
    if (userOrder) {
      for (const token of userOrder) {
        if (typeof token !== "string" || !token || seen.has(token)) continue;
        if (byId.has(token) || ctxDefById(branch, token) || ctxIsSepToken(token)) {
          order.push(token);
          seen.add(token);
        }
      }
    }
    for (const d of defs) {
      if (!seen.has(d.id) && !(claimedElsewhere && claimedElsewhere.has(d.id))) {
        order.push(d.id);
        seen.add(d.id);
      }
    }
    return { order, hidden };
  }

  /* 一支的完整合并布局: { order, hidden, sub: { order, hidden } }; cfg 缺省/畸形 = 默认布局。
   * 两层必须一起合: 补尾的"claimedElsewhere"取自对层用户序, 否则跨层移走的项会被补回原层。 */
  function ctxMergeLayout(branch, cfg) {
    const branchCfg = cfg && typeof cfg === "object" && !Array.isArray(cfg) ? cfg[branch] : null;
    const subCfg = branchCfg && typeof branchCfg === "object" && !Array.isArray(branchCfg) ? branchCfg.sub : null;
    const topUser = branchCfg && Array.isArray(branchCfg.order) ? branchCfg.order : null;
    const subUser = subCfg && Array.isArray(subCfg.order) ? subCfg.order : null;
    const topClaimed = new Set((subUser || []).filter((t) => typeof t === "string"));
    const subClaimed = new Set((topUser || []).filter((t) => typeof t === "string"));
    const top = ctxMergeLayer(branch, 0, branchCfg, topClaimed);
    const sub = ctxMergeLayer(branch, 1, subCfg, subClaimed);
    return { branch, order: top.order, hidden: top.hidden, sub: { order: sub.order, hidden: sub.hidden } };
  }

  /* 一层可执行项数(隐藏 + 门控之后; 供 D7「次级为空不显示入口」判定)。
   * 分隔线(默认线/用户线)与结构项都不占数: 只剩线的次级 = 空次级 —— 空面板拖两条线比
   * 单选项更残(D7 初衷), 不渲染「更多操作」父项; 线在配置里休眠, W4 定制块可见可恢复。 */
  function ctxLayerVisibleCount(branch, level, layer, flags) {
    let n = 0;
    for (const token of layer.order) {
      if (layer.hidden.has(token)) continue;
      if (ctxIsSepToken(token)) continue; // 线是结构不是项(默认线 id 亦以 sep: 开头, 先行滤)
      const def = ctxDefById(branch, token);
      if (!def) continue; // 未知 token: 渲染层容忍(照常渲染线), 计数层不计
      if (def.kind === "submenu") continue; // 结构项不占可见数
      if (def.gate && !ctxGateOk(def.gate, flags)) continue;
      n += 1;
    }
    return n;
  }

  function ctxGateOk(gate, flags) {
    const key = CTX_GATE_FLAG[gate];
    return key ? !!(flags && flags[key]) : true;
  }

  /* 渲染解析: 合并布局 -> 可见渲染项数组(顺序即渲染序)。
   *   - hidden 滤除(槽位在 order 里保留, 不重排)
   *   - gate 滤除(flags 关 = v-if 不渲染; 与模板 v-if 语义逐字同径)
   *   - submenu 父项: 次级无可见项时不渲染(D7, 单选项菜单 = 半残 UI); 次级层 itself 不渲染
   *     submenu(结构项不可嵌套, 定制块亦不提供它的跨层移动)
   *   - 动态 label / 置灰 title 在此就地求值(vm = Vue 实例, 响应式依赖随渲染收集)
   */
  function ctxRenderLayer(branch, level, flags, vm) {
    const merged = ctxMergeLayout(branch, flags && flags.ctx_menu);
    const layer = level === 1 ? merged.sub : merged;
    const out = [];
    for (const token of layer.order) {
      if (layer.hidden.has(token)) continue;
      const def = ctxDefById(branch, token);
      if (!def) {
        if (ctxIsSepToken(token)) out.push({ id: token, kind: "sep", label: "", icon: null, cls: "", gated: false, title: "", act: null, level });
        continue;
      }
      if (def.kind === "submenu") {
        if (level === 1) continue; // 次级里不渲染「更多操作」父项(不可嵌套)
        if (ctxLayerVisibleCount(branch, 1, merged.sub, flags) === 0) continue; // D7
      }
      if (def.gate && !ctxGateOk(def.gate, flags)) continue;
      out.push(ctxRenderItem(def, vm, level));
    }
    return out;
  }

  function ctxRenderItem(def, vm, level) {
    const item = {
      id: def.id,
      kind: def.kind || "item",
      label: typeof def.label === "function" ? def.label(vm) : def.label,
      icon: def.icon || null,
      cls: def.danger ? "danger" : "",
      gated: false,
      title: "",
      act: def.act || null,
      level,
    };
    if (def.dyn === "reannounce" && vm && typeof vm.reannounceMenuGate === "function") {
      const gate = vm.reannounceMenuGate();
      item.gated = !gate.ok;
      item.title = gate.title || ""; // 恒绑字符串: 可用时空串(ui_feedback 空串 title = 清除提示通道)
    }
    return item;
  }

  /* 下一个用户分隔线 token(sep:uN, N = 当前层最大 + 1, 不复用已删 id) —— W4 定制块「+ 添加分隔线」 */
  function ctxNextSepToken(tokens) {
    let max = 0;
    for (const t of tokens || []) {
      const m = /^sep:u(\d+)$/.exec(t || "");
      if (m) max = Math.max(max, parseInt(m[1], 10));
    }
    return "sep:u" + (max + 1);
  }

  window.AQB_CTX_MENU_REG = {
    CTX_BRANCHES,
    CTX_SUB_NAME,
    CTX_ITEM_DEFS,
    CTX_SUB_ITEM_DEFS,
    DEFAULT_CTX_LAYOUT,
    ctxIsSepToken,
    ctxDefsOf,
    ctxDefById,
    ctxMergeLayer,
    ctxMergeLayout,
    ctxLayerVisibleCount,
    ctxRenderLayer,
    ctxNextSepToken,
  };

  /* ---------------- Vue mixin(app.js 末尾 app.mixin(window.AQB_CTX_MENU)) ----------------
   * 模板(W3)消费: ctxItems(branch) / ctxSubItems(branch) / ctxRun(it)。
   * 方法而非 computed: 带分支参数; 列表 ≤15 项, 无缓存必要, 响应式依赖(flags/menu)随渲染收集。 */
  window.AQB_CTX_MENU = {
    methods: {
      /* 一级可见项(含 sep 与「更多操作」父项); 分支判据链仍在模板 v-if, 这里只按支取名 */
      ctxItems(branch) {
        return window.AQB_CTX_MENU_REG.ctxRenderLayer(branch, 0, this.flags, this);
      },
      /* 次级可见项(「更多操作」子面板); 空数组时模板不渲染父项(D7) */
      ctxSubItems(branch) {
        return window.AQB_CTX_MENU_REG.ctxRenderLayer(branch, 1, this.flags, this);
      },
      /* 点击分派: 原方法调用逐字平移(act 闭包捕获 vm), 关闭菜单等行为仍在各原方法内 */
      ctxRun(it) {
        if (it && typeof it.act === "function") it.act(this);
      },
    },
  };
})();
