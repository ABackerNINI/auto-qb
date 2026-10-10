/* auto-qb WEB UI · 触发点登记表(声明式单点)
 *
 * 口径出处 = memory-bank/conventions/webui-scope.md(专题 webui-selection-trigger-parity,
 * 计划 26-10-10-2001 S2)。本文件是那张表在代码里的**唯一落点**, 有两个消费者:
 *   · 静态守阵 tests/test_webui_trigger_registry.py(从本文件文本里提取 TRIGGER_DEFS 解析);
 *   · e2e 矩阵(计划 S5, 经 window.AQB_TRIGGERS.triggerDefs() 取)。
 * 运行时的业务代码**不消费**它 —— 它描述「谁在触发、作用在谁身上」, 不是运行期数据。
 *
 * 新增触发点 / 新增投递点的唯一动作 = 在这里加一行。
 *   漏加: calls 少一行 → 守阵 T1 的「检测到的 POST 调用点」有表外项, 判红;
 *   加错: ui 行的 entry 不是真方法名 → 守阵 T5 判红。
 *
 * 字段:
 *   ui[]    id        唯一标识
 *           ui        ctx-menu | kbd | drawer
 *           variant   仅 ctx-menu 有, 与 tpl/ctx-menus.html 的四支一一对应
 *                     (multi / episode / member / group); 守阵 T3 拿它对账模板分支
 *           entry     入口方法名(可含多个, 用 | 分隔 —— 同一作用域的同族入口)
 *           scope     sel | anchor | cursor | sel-first-cursor | panel(可含 | 表示两种口径并存)
 *           dispatch  action | edit | delete | export | folder | panel | none
 *   calls[] file+fn   投递调用点(**每一个** `method: "POST"` 出现点都要在册)
 *           ep        端点形态(仅供人读)
 *           scope     该调用点承载的作用域
 *           why       scope 含 none 时必填: 为什么与选中/锚点无关
 *
 * !scope 的三种「目标」含义与 C5 锚点资格见 conventions/webui-scope.md §1/§2, 此处不复述。
 * !本文件在 HTML 里排在 selection.js 之后、app.js 之前; app.js 末尾 app.mixin(window.AQB_TRIGGERS)。
 */
const TRIGGER_DEFS = {
  "ui": [
    {
      "id": "ctx.multi.action", "ui": "ctx-menu", "variant": "multi", "entry": "ctxAct",
      "scope": "sel", "dispatch": "action"
    },
    {
      "id": "ctx.multi.meta", "ui": "ctx-menu", "variant": "multi", "entry": "ctxMeta",
      "scope": "sel", "dispatch": "edit"
    },
    {
      "id": "ctx.multi.delete", "ui": "ctx-menu", "variant": "multi", "entry": "ctxDelete",
      "scope": "sel", "dispatch": "delete"
    },
    {
      "id": "ctx.episode.action", "ui": "ctx-menu", "variant": "episode", "entry": "actEpisode",
      "scope": "anchor", "dispatch": "action"
    },
    {
      "id": "ctx.episode.folder", "ui": "ctx-menu", "variant": "episode", "entry": "openTargetPath",
      "scope": "anchor", "dispatch": "folder"
    },
    {
      "id": "ctx.episode.delete", "ui": "ctx-menu", "variant": "episode", "entry": "delEpisode",
      "scope": "anchor", "dispatch": "delete"
    },
    {
      "id": "ctx.member.action", "ui": "ctx-menu", "variant": "member", "entry": "actTorrent",
      "scope": "anchor", "dispatch": "action"
    },
    {
      "id": "ctx.member.drawer", "ui": "ctx-menu", "variant": "member", "entry": "openTorrentDrawer",
      "scope": "anchor", "dispatch": "panel"
    },
    {
      "id": "ctx.member.edit", "ui": "ctx-menu", "variant": "member",
      "entry": "editLimits|editMove|editRename|editShareLimits|openMetaDialog",
      "scope": "anchor", "dispatch": "edit"
    },
    {
      "id": "ctx.member.cmd", "ui": "ctx-menu", "variant": "member", "entry": "torrentCmd",
      "scope": "anchor", "dispatch": "panel"
    },
    {
      "id": "ctx.member.toggle", "ui": "ctx-menu", "variant": "member", "entry": "autoTmmToggle",
      "scope": "anchor", "dispatch": "panel"
    },
    {
      "id": "ctx.member.skip", "ui": "ctx-menu", "variant": "member", "entry": "skipCheckTorrent",
      "scope": "anchor", "dispatch": "edit"
    },
    {
      "id": "ctx.member.export", "ui": "ctx-menu", "variant": "member", "entry": "exportTorrent",
      "scope": "anchor", "dispatch": "export"
    },
    {
      "id": "ctx.member.folder", "ui": "ctx-menu", "variant": "member", "entry": "openTargetPath",
      "scope": "anchor", "dispatch": "folder"
    },
    {
      "id": "ctx.member.copy", "ui": "ctx-menu", "variant": "member", "entry": "copyTorrentInfo",
      "scope": "anchor", "dispatch": "none"
    },
    {
      "id": "ctx.member.delete", "ui": "ctx-menu", "variant": "member", "entry": "delTorrent",
      "scope": "anchor", "dispatch": "delete"
    },
    {
      "id": "ctx.group.action", "ui": "ctx-menu", "variant": "group", "entry": "act",
      "scope": "anchor", "dispatch": "action"
    },
    {
      "id": "ctx.group.recheck", "ui": "ctx-menu", "variant": "group", "entry": "recheckGroup",
      "scope": "anchor", "dispatch": "action"
    },
    {
      "id": "ctx.group.skip", "ui": "ctx-menu", "variant": "group", "entry": "skipCheckGroup",
      "scope": "anchor", "dispatch": "edit"
    },
    {
      "id": "ctx.group.edit", "ui": "ctx-menu", "variant": "group", "entry": "editLimitsGroup|editMoveGroup",
      "scope": "anchor", "dispatch": "edit"
    },
    {
      "id": "ctx.group.meta", "ui": "ctx-menu", "variant": "group", "entry": "metaGroup",
      "scope": "anchor", "dispatch": "edit"
    },
    {
      "id": "ctx.group.export", "ui": "ctx-menu", "variant": "group", "entry": "exportGroup",
      "scope": "anchor", "dispatch": "export"
    },
    {
      "id": "ctx.group.folder", "ui": "ctx-menu", "variant": "group", "entry": "openTargetPath",
      "scope": "anchor", "dispatch": "folder"
    },
    {
      "id": "ctx.group.traffic", "ui": "ctx-menu", "variant": "group", "entry": "openQbGroup",
      "scope": "anchor", "dispatch": "none"
    },
    {
      "id": "ctx.group.delete", "ui": "ctx-menu", "variant": "group", "entry": "delGroup",
      "scope": "anchor", "dispatch": "delete"
    },
    {
      "id": "kbd.action", "ui": "kbd", "entry": "_kbAct",
      "scope": "sel-first-cursor", "dispatch": "action"
    },
    {
      "id": "kbd.delete", "ui": "kbd", "entry": "_kbDelete",
      "scope": "sel-first-cursor", "dispatch": "delete"
    },
    {
      "id": "kbd.meta", "ui": "kbd", "entry": "_kbMeta",
      "scope": "sel-first-cursor", "dispatch": "edit"
    },
    {
      "id": "kbd.single", "ui": "kbd", "entry": "_kbEditAct|_kbTorrentCmd|_kbTorrentToggle",
      "scope": "sel-first-cursor", "dispatch": "panel"
    },
    {
      "id": "kbd.folder", "ui": "kbd", "entry": "_kbOpenFolder",
      "scope": "cursor", "dispatch": "folder"
    },
    {
      "id": "kbd.drawer", "ui": "kbd", "entry": "_kbOpenDrawer",
      "scope": "cursor", "dispatch": "panel"
    },
    {
      "id": "panel.cmd", "ui": "drawer", "entry": "torrentCmd",
      "scope": "panel", "dispatch": "panel"
    },
    {
      "id": "panel.drawer-cmd", "ui": "drawer", "entry": "drawerCmd",
      "scope": "panel", "dispatch": "panel"
    },
    {
      "id": "panel.skip", "ui": "drawer", "entry": "skipCheckMulti",
      "scope": "sel|anchor", "dispatch": "edit"
    },
    {
      "id": "panel.edit", "ui": "drawer", "entry": "editLimitsMulti|editMoveMulti",
      "scope": "sel|anchor", "dispatch": "edit"
    },
    {
      "id": "panel.tracker-remove", "ui": "drawer", "entry": "trackerRemove",
      "scope": "panel", "dispatch": "panel"
    }
  ],
  "calls": [
    {
      "file": "commands.js", "fn": "_actCore", "ep": "/api/groups/{key}/{action}",
      "scope": "sel|anchor", "why": ""
    },
    {
      "file": "commands.js", "fn": "_actCore", "ep": "/api/torrents/{hash}/{action}",
      "scope": "sel|anchor", "why": ""
    },
    {
      "file": "commands.js", "fn": "_actCore", "ep": "/api/torrents/bulk",
      "scope": "sel|anchor", "why": ""
    },
    {
      "file": "commands.js", "fn": "_actCore", "ep": "reannounce 逐目标(计划由 reannouncePlan 收敛)",
      "scope": "sel|anchor", "why": ""
    },
    {
      "file": "delete_flow.js", "fn": "_deleteFlow", "ep": "/api/torrents/bulk (delete)",
      "scope": "sel|anchor", "why": ""
    },
    {
      "file": "delete_flow.js", "fn": "_reannounceAll", "ep": "reannounce 逐目标",
      "scope": "sel|anchor", "why": ""
    },
    {
      "file": "dialogs.js", "fn": "_metaBulk", "ep": "/api/torrents/bulk (tags/category)",
      "scope": "sel|anchor", "why": ""
    },
    {
      "file": "drawer.js", "fn": "torrentCmd", "ep": "/api/torrents/{hash}/{action}",
      "scope": "panel", "why": ""
    },
    {
      "file": "drawer.js", "fn": "_editPost", "ep": "/api/torrents/{hash}/{action}",
      "scope": "panel", "why": ""
    },
    {
      "file": "drawer.js", "fn": "_bulkEditPost", "ep": "/api/torrents/bulk",
      "scope": "sel|anchor", "why": ""
    },
    {
      "file": "drawer.js", "fn": "_skipPrecheck", "ep": "/api/torrents/skip-check/precheck",
      "scope": "sel|anchor", "why": ""
    },
    {
      "file": "drawer.js", "fn": "_skipExec", "ep": "/api/torrents/{hash}/skip-check",
      "scope": "sel|anchor", "why": ""
    },
    {
      "file": "drawer.js", "fn": "_skipExec", "ep": "/api/torrents/bulk (skip-check)",
      "scope": "sel|anchor", "why": ""
    },
    {
      "file": "menu.js", "fn": "openTargetPath", "ep": "/api/open-path",
      "scope": "anchor", "why": ""
    },
    {
      "file": "add_torrent.js", "fn": "dirMkdir", "ep": "/api/fs/mkdir",
      "scope": "none", "why": "添加种子对话框建目录: 资源操作, 无选中/锚点语义"
    },
    {
      "file": "add_torrent.js", "fn": "submitAddTorrent", "ep": "/api/torrents/add",
      "scope": "none", "why": "新增种子: 新增对象不存在于任何选中集合"
    },
    {
      "file": "config_rules.js", "fn": "cfgExprTry", "ep": "/api/expr/eval",
      "scope": "none", "why": "规则表达式试算: 纯计算"
    },
    {
      "file": "dialogs.js", "fn": "submitMgrCategory", "ep": "/api/categories",
      "scope": "none", "why": "分类资源管理: 全局集合, 非种子级"
    },
    {
      "file": "dialogs.js", "fn": "submitMgrTags", "ep": "/api/tags",
      "scope": "none", "why": "标签资源管理: 全局集合, 非种子级"
    },
    {
      "file": "dialogs.js", "fn": "mgrEditCatPath", "ep": "/api/categories/edit",
      "scope": "none", "why": "分类资源管理"
    },
    {
      "file": "dialogs.js", "fn": "mgrDeleteCategory", "ep": "/api/categories/remove",
      "scope": "none", "why": "分类资源管理"
    },
    {
      "file": "dialogs.js", "fn": "mgrDeleteTag", "ep": "/api/tags/remove",
      "scope": "none", "why": "标签资源管理"
    },
    {
      "file": "dialogs.js", "fn": "metaAddNewTags", "ep": "/api/tags (先建后设)",
      "scope": "none", "why": "候选资源创建: 第二步 _metaBulk 才带目标"
    },
    {
      "file": "dialogs.js", "fn": "metaSetCategory", "ep": "/api/categories (先建后设)",
      "scope": "none", "why": "候选资源创建: 第二步 _metaBulk 才带目标"
    },
    {
      "file": "dialogs.js", "fn": "submitSpeedOverride", "ep": "/api/speed/override",
      "scope": "none", "why": "全局限速配置: 非目标级"
    },
    {
      "file": "dialogs.js", "fn": "toggleAltSpeed", "ep": "/api/speed/alt/toggle",
      "scope": "none", "why": "全局限速配置"
    },
    {
      "file": "dialogs.js", "fn": "submitAltLimits", "ep": "/api/speed/alt",
      "scope": "none", "why": "全局限速配置"
    },
    {
      "file": "hr_status.js", "fn": "hrsConfirmEmpty", "ep": "/api/hr/confirm-empty",
      "scope": "none", "why": "HR 站点级操作: 按 site 而非种子目标"
    },
    {
      "file": "hr_status.js", "fn": "hrsRefresh", "ep": "/api/hr/refresh",
      "scope": "none", "why": "HR 站点级刷新"
    },
    {
      "file": "polling.js", "fn": "startEvents", "ep": "/api/events/ticket",
      "scope": "none", "why": "SSE 订阅票据: 非动作"
    }
  ]
};

window.AQB_TRIGGERS = {
  methods: {
    /* 触发点登记表(只读)。e2e 经 readInst 取; 业务代码不消费 —— 见文件头。 */
    triggerDefs() {
      return TRIGGER_DEFS;
    },
  },
};
