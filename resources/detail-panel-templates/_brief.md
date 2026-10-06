# detail-panel-templates 设计简报(供后续设计智能体使用)

> 产线: auto-qb WEBUI 种子详情面板(下方面板, 带页签)逐页重设计。
> 本文件是唯一输入简报; 每份产出 = 一个自包含单文件 HTML 模板, 与本简报同目录。
> 本目录模板一律 **dark 主题**(模拟真实产品 UI, 不适用 webui.md 对 `resources/` 参考素材的浅色豁免)。

---

## 1. 任务背景与用户三点不满

种子详情面板已从「右侧抽屉」改为「底部停靠面板」(sticky 吸底、占文档流、无遮罩), 头部带页签。
用户对现状的三点不满(转述):

1. **常规页右边空一大块**: 常规页沿用旧竖向排版(分组卡片 + 单列 label/value 行), 面板改到下方后
   宽度拉满整幅列表宽, 行高堆叠导致右侧大量留白, 信息密度极低。
2. **Tracker/用户/内容三页没有设计感**: 几乎是裸 `<table>` 平铺(等宽字体表头 + 边框行), 无分组、
   无层级、无状态可视化, 与主列表的设计水准脱节。
3. **收起状态似乎没有实际作用**: 需要代码级论证(见 §3, 结论: 有作用但反馈极弱, 且持久化是死数据)。

设计目标: 按页签逐页出可交互 HTML 模板, 解决「宽面板下的横向空间利用 + 表格设计感 + 收起态价值」。

## 2. 现状实现地图(只读背景, 模板不引用产品代码)

| 文件 | 职责 |
|---|---|
| `src/auto_qb/webui/static/shared/tpl/drawer.html`(286 行) | 面板 DOM 单点: 头部(标题+页签+收起/关闭钮) + 五页签正文, 三皮肤共用 |
| `src/auto_qb/webui/static/shared/tpl/dock.html` | 落点 `<div class="drawer-dock">`(#app 直下, sticky 吸底) |
| `src/auto_qb/webui/static/shared/drawer.js`(1320 行) | 开合/页签切换/收起/拖拽调高/5s 轮询/跟随光标/各页数据组装 |
| `src/auto_qb/webui/static/shared/state.js:102-115` | drawer 状态初值(open=false, collapsed=false) |
| `src/auto_qb/webui/static/shared/app.js:429-441` | localStorage 恢复 drawerTab / drawerHeight |
| `src/auto_qb/webui/static/shared/format.js` / `hr.js:310-331` | 数值口径与 HR 文案单点 |
| `src/auto_qb/webui/static/atlas/css/dialogs.css:12-130` | 星图抽屉 CSS(`.drawer*` 段) |
| `src/auto_qb/webui/static/prism/css/views.css:540-700+` | 棱镜抽屉 CSS(基调皮肤, 见 §5) |
| `src/auto_qb/webui/static/console/css/dialogs.css:6-` | 控制台抽屉 CSS |
| `src/auto_qb/webui/server/routes/torrent_detail.py:27-86` | `/api/torrents/{hash}` 全字段详情 + `/trackers` `/files` `/peers` `/api/traffic/qb/torrent/{hash}` |

**三皮肤共用同一 DOM 与 JS**(shared/tpl/drawer.html + drawer.js, boot.js 按 tpl-manifest 注入),
差异只在各皮肤 CSS。常规页排版 = `.drawer-sec` 卡片 + `.f-row`(grid: 16px 图标 / 112px 标签 / 1fr 值 / auto 动作钮)
单列堆叠 —— 这就是"右边空一大块"的直接原因。三页表格 = `.drawer-table`(朴素 border-collapse 表)。

## 3. 收起状态代码级实证(结论: 有作用, 但反馈弱 + 持久化是死数据)

**收起改变了什么**:
- `toggleDrawerCollapse()` `drawer.js:989-998`: 翻转 `drawer.collapsed` → `aside.drawer` 挂 `collapsed` 类
  (`tpl/drawer.html:16`) → **唯一**生效规则是三皮肤各一条 `.drawer.collapsed .drawer-body { display:none }`
  (atlas `dialogs.css:23` / prism `views.css:552` / console `dialogs.css:17`) → 正文隐藏, 面板高度回落到
  头部一行(min-height 44px, `dialogs.css:52`); 同时 `drawerPanelStyle()` 收起态返回 `{}` 丢弃内联 height
  (`drawer.js:953-958`)。面板在文档流(sticky dock)里, 收起后列表区**确实回收空间**。
- 收起期副作用: 键盘跟随暂停(`drawer.js:834`)、流量图不重建/展开补建(`drawer.js:994-996`)、
  页签 5s 轮询可见性门跳过拉取(`drawer.js:718-723`)。

**用户感觉"没作用"的四个代码级依据**:
1. **持久化是单向死数据**: `persistDrawerOpen()` 写 `localStorage["autoqb.ui.drawerOpen"]`
   (`drawer.js:1005-1009`), 但**全库无任何读取**; 注释自认「只作记录(写入不回读)」(`drawer.js:940`),
   D1 拍板首屏恒默认收起(`state.js:115`, `drawer.open` 初值 false)。→ 收起状态从不被恢复。
2. **与"关闭"高度重叠**: 每次打开面板都重置 `collapsed:false`(`drawer.js:659`), Esc/关闭钮整个收起面板。
   收起相对关闭仅多保住: 页签/数据/滚动位置 + 免重拉 —— 无独立视觉身份。
3. **收起态页签仍可点但不展开**: `drawerTab()`(`drawer.js:794-803`)**不清除 collapsed**, 数据被拉进
   display:none 的正文里 —— 点了像"没反应"。
4. **注释漂移**: `tpl/drawer.html:19` 声称 grip「收起态隐藏」, 但三皮肤均无 `.drawer.collapsed .drawer-grip`
   规则, 8px 拖拽热区仍叠在头部上。

→ 模板设计要求: 给收起态一个**有信息量的最小形态**(如头部内嵌关键指标摘要条), 并让页签点击在收起态
有明确反馈(展开或提示)。

## 4. 页签清单与逐页数据字典

页签按钮 `tpl/drawer.html:49-56`, 取值 = `general / trackers / peers / content / traffic`
(流量页签受 `qbTrafficOn` 门控, 关闭时不渲染)。

### 4.1 常规 general — `GET /api/torrents/{hash}`
响应 `{torrent: TorrentRecord.to_dict() + site + hr_view_fields()}`; 70 个快照字段
(`torrents/compat.py:19-110`) + `site`(站点名) + ~20 个 `hr_*` 字段(`webui/views.py:237`) + `_raw` 前向兼容。

**当前展示**(4 组卡片共 49 行, `drawer.js:1151-1237`):
- HR 块(条件渲染): `hr_excluded` / `hr_triggered`+`hr_satisfied` / `hr_state`(+`hr_reason`→`hrStateLine` 拼
  `hr_safety_text||hr_state_text`) / `hr_site_lane` 门 + `hrSiteLine`(还需做种 `hr_site_need` / 剩余达标
  `hr_site_remain` / 分享率 `hr_site_ratio` / 站点下载 `hr_site_dl`) / `hr_tag` / `hr_tag_done` /
  `hr_req_time` / `hr_req_ratio`
- 基础(14): progress, size, total_size, amount_left, availability, ratio, private, infohash_v1,
  infohash_v2, piece_size+pieces_have+pieces_num, has_metadata, creation_date, created_by, comment
- 传输(20): dlspeed, upspeed, eta, downloaded, uploaded, downloaded_session, uploaded_session,
  total_wasted, num_seeds, num_leechs, num_complete/num_incomplete, trackers_count,
  connections_count/connections_limit, reannounce_in|reannounce, has_tracker_error,
  has_tracker_warning, max_ratio, max_seeding_time, max_inactive_seeding_time, share_limit_action
- 时间(6): added_on, completion_on, seen_complete, last_activity, time_active, seeding_time
- 路径(9): save_path, content_path, download_path, root_path, auto_tmm, force_start, super_seeding,
  seq_dl, f_l_piece_prio(路径行带"打开目录"钮, 哈希行带"复制"钮)
- 折叠区 `<details class="drawer-raw">`: 全部原始键值

**有但没展示**(设计素材): `hash` / `name`(仅在标题) / `tags` / `category` / `state` / `completed` /
`dl_limit` / `up_limit`(限速) / `magnet_uri` / `tracker`(首个可用 tracker) / `priority` / `popularity` /
`has_other_announce_error` / `site`(主列表有, 面板没有) / `hr_excluded_by` / `hr_safety` / `hr_safety_src`
(安全档位与来源) —— HR 安全档位(`hr_safety_text`)其实已拼进三态行, 但未做成可视化徽章。

### 4.2 Tracker trackers — `GET /api/torrents/{hash}/trackers`(qB 透传, 5s 轮询)
- 展示 5 列 + 行内动作: url(虚拟条目 `**`/`[DHT]`/`[PeX]`/`[LSD]` 弱化) / status(0 未启用 1 未连接
  2 正常 3 更新中 4 未连接) / 做种 `num_seeds`(swarm 总数 `num_complete` 括号) / 用户 `num_leeches`
  (+`num_incomplete`) / msg; 添加/编辑/删除钮(`drawer.js:519-556`)
- 有但没展示: `tier`(层级, 可做排序/分组依据), `num_peers`, `num_downloaded`(该 tracker 累计下载)
- 状态仅一行文字, 无色义 —— 设计空间: 状态徽章/色点。

### 4.3 用户 peers — `GET /api/torrents/{hash}/peers`(qB `sync/torrentPeers` 透传整包, 5s 轮询;
  前端对 `peers` 做 dict/数组双形态归一, `drawer.js:1296-1311`)
- 展示 9 列: addr(ip:port) / client / flags / progress% / 下行 dlspeed / 上行 upspeed / 已下载
  downloaded / 已上传 uploaded / relevance%(关联度)
- qB 典型响应里还有但没展示(透传即有, 随 qB 版本浮动): `country`/`country_code`(国旗/地区),
  `connection`(加密/协议), `peer_id_client`, `files`(对端正在取的文件), `flags_desc`(flags 人话) ——
  设计空间: 方向/加密可视化、进度条、按 flags 筛选。

### 4.4 内容 content — `GET /api/torrents/{hash}/files`(qB 透传, 拉一次)
- 展示 4 列: 文件(树形缩进, 目录聚合大小、目录/文件分色, `drawer.js:1257-1295`) / 大小 / 进度% /
  优先级(0 跳过 1 普通 4|6 高 7 最高, 点改小菜单); 行点选供重命名
- 有但没展示: 每文件 `availability`(可用性), 树纯缩进无引导线/折叠 —— 设计空间: 折叠树、进度条内嵌、
  目录聚合进度。

### 4.5 流量 traffic — `GET /api/traffic/qb/torrent/{hash}?window=<档>`
响应 `{points:[{t,up,dl}], totals:[...], meta:{window, interval_s, source, stale}}`
(`server/traffic_qb.py:96-136`); 13 档窗口 1m/5m/30m/3h/6h/12h/24h/3d/7d/30d/6mo/1y/all
(`shared/qb_traffic_chart.js QB_WINDOW_NAMES`)。
- 展示: 窗口切换器 / uPlot 双系列图(上行/下行) / 悬停 tooltip(上行/下行/合计/空闲 0 桶/缺口无采样) /
  图例 / 汇总(桶数、上传累计、下载累计) / stale 横幅 / 三种空态
- 设计空间: 图表配色必须走 `--today-up/--today-down` 令牌; 面板高度与图高的比例关系。

## 5. 基调皮肤: prism(棱镜) + 默认暗色主题 ocean(深海机房)

**判定依据**: ①`server/static_ui.py:20` 官方注释「atlas=星图(旧) / prism=棱镜(新)」—— prism 是新旗舰;
②三皮肤对详情面板的 CSS 改动是逐提交锁步的(git log: 659eada8/3c7df550/4978a717/54d8b6fc 均三处同改),
无单皮肤独占迭代 → 取结构最完整的 prism; ③prism 有正式令牌契约(`tokens.css` + `themes/*.css` 五主题,
最近改动 2026-10-04)且往届模板(main-ui-templates)即以 ocean 令牌为内联基线; ④`theme.js:21`
`DARK_DEFAULT = "ocean"`。

模板内联以下令牌现值(ocean.css 全表 + tokens.css 结构令牌), **逐个抄用, 不要自造色值**:

```css
color-scheme: dark;                     /* ocean.css:7 硬规则 */
/* 背景分层 */
--bg:#0d1724; --bg-card:#15233a; --bg-row:#112034; --bg-hover:#1c3050;
--bg-sunken:rgba(5,12,24,.5); --bg-elev:#1b2d4b; --glass:#111e31; --statusbar-bg:#17273c;
/* 前景三级+次级 */
--fg:#e9eff7; --fg-muted:#9cadc6; --fg-dim:#6e84a3; --fg-soft:#bccadd;
/* 品牌 accent(鸭羽青) */
--accent:#3aa6a6; --accent-hi:#5cc3c3; --accent-soft:rgba(58,166,166,.15);
--accent-line:rgba(58,166,166,.45); --ring:rgba(92,195,195,.5);
--on-accent:#04282a; --on-accent-ink:#032325; --on-error:#2b0c0c;   /* 实心底上的前景 */
/* 状态色族(语义: 种子/行状态; 0 值与"—"占位不染色) */
--green:#3fd699; --green-soft:rgba(63,214,153,.15); --green-line:rgba(63,214,153,.42);
--blue:#4cc3f7;  --blue-soft:rgba(76,195,247,.15);  --blue-line:rgba(76,195,247,.42);
--warn:#f5bb42;  --warn-soft:rgba(245,187,66,.15);  --warn-line:rgba(245,187,66,.45);
--error:#f3766f; --error-soft:rgba(243,118,111,.15);--error-line:rgba(243,118,111,.45);
/* 暂停/其它 = 无色相: 不铺底 + 中性描边 */
--paused:var(--fg-muted); --paused-soft:transparent; --paused-line:var(--border-strong);
/* 选中态族(靛蓝, 与做种绿彻底分开; 不得引用 --accent) */
--sel-bg:rgba(139,147,248,.16); --sel-line:rgba(139,147,248,.45); --sel-bar:#8b93f8;
/* 流量方向色族(2026-10-04 拍板: 上行=紫 / 下行=蓝绿) */
--today-up:var(--indigo);   /* #8b93f8 */
--today-down:var(--teal);   /* #2fd4bf */
--today-ico:var(--lime);    /* #a8e63c */
/* 数据扩展六色(chip/图例/分类) */
--violet:#ab8ffa; --pink:#f477b3; --teal:#2fd4bf; --indigo:#8b93f8; --cyan:#2ad0e8; --lime:#a8e63c;
/* (soft 版: 各 16% 同色透明, 见 ocean.css:46-56) */
/* HR 标记族 */
--hr-pending:#ff8f45; --hr-pending-soft:rgba(255,143,69,.18); --hr-pending-line:rgba(255,143,69,.5);
--hr-done:#5eead4; --hr-done-soft:rgba(94,234,212,.14); --hr-done-line:rgba(94,234,212,.38);
--hr-hit:#ff8f45;
/* 限速对照 / 今日流量派生 */
--limit-hit:var(--violet); --limit-actual:var(--blue);
/* 描边与表面 */
--border:#23395a; --border-strong:#34507c; --border-soft:rgba(255,255,255,.07);
--surface-1:rgba(255,255,255,.03); --surface-2:rgba(255,255,255,.06); --hairline:rgba(255,255,255,.055);
/* 结构令牌(tokens.css) */
--font-ui:"Segoe UI","Microsoft YaHei",system-ui,sans-serif;
--font-display:"Bahnschrift","Segoe UI","Microsoft YaHei",sans-serif;
--font-mono:"Cascadia Code","Consolas",ui-monospace,monospace;
--radius-lg:8px; --radius:6px; --radius-sm:4px;
--statusbar-h:34px;
--shadow-1:0 1px 2px rgba(0,0,0,.16); --shadow-2:0 6px 18px rgba(0,0,0,.22); --shadow-3:0 14px 40px rgba(0,0,0,.3);
--ease:cubic-bezier(.2,.8,.3,1); --ease-out:cubic-bezier(.16,1,.3,1); --ease-spring:cubic-bezier(.34,1.4,.64,1);
--dur-fast:100ms; --dur:160ms; --dur-slow:280ms;
/* 弹窗宽度族(--modal-w-narrow 460/base 520/form 560/add 860/wide 920), 面板模板一般用不到 */
```

参考几何(现面板): dock 左右 padding 12px、`margin-top:8px`、默认 `max-height:42vh`、拖拽夹取
[240px, 70vh]、头部 min-height 44px、页签 = 文字钮 + active 底边线 `--accent`、正文 padding 14px 18px 20px。

## 6. dark 主题硬规则(webui.md 2026-09-20 用户指定)

- 深色底 + 浅色字, **禁止浅底黑字**; 模板模拟真实产品(本身即暗色), 无豁免。
- 底色亮度口径: 主背景 ≈ `#0f…`~`#18…` 一带(ocean `--bg:#0d1724`/`--bg-card:#15233a` 即合规基准,
  新造表面以这两个值插值, 不更暗不泛白); 正文字亮度 ≥ `#d8…`(ocean `--fg:#e9eff7` 合规)。
- 样式里**必须**写 `color-scheme: dark`(否则原生滚动条/表单控件不跟深)。
- 全站纪律 **PERF-01: 零 backdrop-filter**(毛玻璃已因性能全线移除) —— 模板禁用 blur/毛玻璃。

## 7. 语境框规范(全模板统一)

每份模板必须把被设计的面板放进**同一个假想主窗口框**, 让评审者判断下方面板的占幅与比例:

- 画布 = 固定 1280×800 视口(居中, 外围留深色衬底并标注尺寸); 内部自上而下:
  1. 顶栏占位条 ~48px(深色 + 少量假按钮/搜索框轮廓即可, 不抢戏);
  2. **简化种子列表占位区**: 表头 1 行 + 5-6 行种子(列: 状态点/名称/大小/进度/上下行速/比率), 用
     §9 样例数据包里的其余种子; 其中**一行高亮为当前行**(即面板正在展示的种子), 面板标题与其名称一致;
  3. **被设计的详情面板**(占满列表同宽, 左右 12px 内边距, 顶缘画 42px grip 微条);
  4. 底部状态栏条 34px(`--statusbar-bg`, 放速度/今日流量小字即可)。
- 面板高度档(变体 slug 必须标明): `collapsed`(收起条, 仅头部 ~44px, 可演示头部内嵌摘要) /
  `low`(矮档 240px) / `tall`(高档 ~560px ≈ 70vh); 未标注默认 `low`。
  同一页签的多变体应覆盖不同高度档, 至少一个变体演示 tall, general 至少一个演示 collapsed 改良形态。
- 列表区随面板高度**真实让位**(面板在文档流, 不是浮层) —— 用 flex column 让占位区收缩, 体现 dock-panel
  坑的几何语义。

## 8. 文件命名与页签 slug 约定

`<NN>-<tab-slug>-<variant-slug>.html`, NN 全局递增 01-15, 与本简报同目录:

| tab-slug | 页签 | NN 段 |
|---|---|---|
| `general` | 常规 | 01-03 |
| `trackers` | Tracker | 04-06 |
| `peers` | 用户 | 07-09 |
| `content` | 内容 | 10-12 |
| `traffic` | 流量 | 13-15 |

- variant-slug 自定(小写连字符), **必须以高度档结尾**: `-tall` / `-low` / `-collapsed`, 如
  `01-general-columns-tall.html`(双栏/三栏重排)、`07-peers-badge-low.html`。
- 同 tab-slug 内多变体只在设计手法上互斥(便于 A/B 评审), 不做同一文件的开关切换。

## 9. 模板技术要求

- **单文件自包含**: 内联全部 CSS/JS, **禁外链**(无 CDN/字体/图片/网络请求); 图标一律内联 SVG。
- 原生 JS(ES2020+), 禁框架; 交互(页签/展开/排序/悬停提示)只在模板内自洽。
- 界面文案**中文**; 数字/路径/哈希/域名用 `--font-mono`。
- 硬编码**真实感样例数据**(PT 语境: 站点域名打码形如 `tracker.example.org` / `pt.example.org`;
  上下行速度、分享率、做种/下载 peer 数、文件树、限速、HR 状态等)。
- 必须写 `color-scheme: dark`; 禁 backdrop-filter; 令牌按 §5 逐值内联(可增补新令牌, 但不得与既有族重名)。

### 统一样例数据包(全模板同一"主角"种子, 保证跨模板评审一致性)

```
主种子: [Nekomoe Kissaten] Some Anime S02 - 05 [1080p][AVC][JPN].mkv
  hash v1: 9f1c3a7d2e5b8a04c6d1e9f2a3b4c5d6e7f80912   私有: 是   分类: 动漫   标签: HR候选, 首页推荐
  站点: tracker.example.org   保存路径: D:/pt/_inbox/[Nekomoe] Some Anime S02
  大小 4.38 GiB(总 4.41 GiB, 分块 4 MiB × 1130 已有 1129)   进度 99.8%   可用性 21.37
  分享率 3.412   已上传 14.9 GiB   已下载 4.38 GiB   浪费 128.4 MiB
  速度 ↑ 2.11 MiB/s  ↓ 0(做种中)   做种 12( swarm 38 )  用户 0(3)   连接 12/∞   tracker 数 2
  HR: 已触发未达标, 要求做种 96h / 要求分享率 2.00, 站点侧: 还需做种 41h12m(安全档 warning)
  添加 2026-09-28 12:31, 完成 2026-09-28 19:02, 活跃 6d4h, 做种 6d18h, 下次汇报 21m
  限速: 上行 8 MiB/s(站点规则), 下行不限   分享率限制 5.00(达标后停止)
文件树(节选): Season 02/(3 目录 7 文件) · 第 05 集 mkv 1.2 GiB 100% 普通 · NCOP&ED mp4 180 MiB 100% 跳过 · 扫图 pdf 42 MiB 86% 普通
Tracker 表样例: https://tracker.example.org/announce.php?passkey=****(正常, 做种 12(38), 用户 0(3))
                https://backup.example.org/announce(更新中) + 虚拟条目 [DHT]/[PeX]/[LSD]
Peers 样例(做种视角 5-8 行): 客户端 qBittorrent 5.1.2 / Transmission 4.0.6 / aria2 1.37, flags 含 D U E H, 进度 0-100% 分布
其余列表种子(占位区): 3-5 条不同状态(做种中/下载中/暂停/HR未达标), 名称自拟 PT 风
```

## 10. 相关 pitfalls 硬约束摘要(memory-bank/pitfalls/web-ui/)

1. **dock-panel.md**: 底部停靠面板占文档流 —— 面板高度变化即列表视口变化, 模板必须演示"让位"而非浮层
   遮挡; 当前光标行不得被面板永久遮死(设计需保留可见性兜底)。
2. **drawer-switch-flicker.md**: 换种子/换页签走软切换(旧数据撑几何 + switching 遮罩), **不许**设计
   "整面板塌成一条再撑开"的加载形态; 加载空态不得接管已有数据的正文。
3. **layout-css.md**(含 progress-bar.md): 表格两态必须有足够明度差; 按钮显式 color; 数值列右对齐且
   数值盒定宽(`min-width` + right), 进度条长度与百分比文本解耦, 防逐行漂移。
4. **css-perf-parity.md**: 零 backdrop-filter; 毛玻璃观感只能用不透明分层底色 + 1px hairline 模拟。
5. **template-render.md / frontend-split.md**: 类名与结构改动将来要三皮肤成对落地(模板即评审基准),
   设计稿使用的类名/层级请贴近现 DOM 语义(`.drawer-head/.drawer-tabs/.drawer-body/.drawer-sec`),
   避免评审通过后无法平移。
6. **aq-tip-nested-title-double.md**: 悬浮提示一律走原生 `title` 属性(全局自绘 .aq-tip 承接),
   不在模板里自造 hover 浮层。
7. (实现期) **css/js-comment-terminator**: 注释里不得出现 `*/`(会静默吞掉后续规则/引发白屏)。
