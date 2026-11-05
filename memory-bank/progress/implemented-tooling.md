# 已实现 · 依赖 / 知识库 / CI

> 摘要: 摘要: 依赖现代化与知识库机制本身的落地记录。
> 触发: 做过没有, 依赖, uv, 知识库, 立档, 索引, 瘦身, skill 瘦身, references, 上限

## 已实现 (✅, 有单测覆盖)

- **AGENTS.md 精简 + Copilot 入口收敛指针 (2026-10-06, 三笔 `376dda34`/`cba7c4f6`/`295bb226`)**: 7,896→6,533 字符(去链接/装饰/空格 950→163/日期标注), 判据一条没删; `.github/copilot-instructions.md` 2,159→83 纯指针。坑: 文档删不干净先查是不是机检 token 在吊着; 「」引文照抄原文(新坑 [pitfalls/docs/anchor-quote.md](../pitfalls/docs/anchor-quote.md))。
- **my-commit-flow 输出契约 v3.1 步骤行 (2026-10-06, 档案 [26-09-28-commands-shipflow-output-contract](../tasks/26-09-28-commands-shipflow-output-contract.md))**: 真改写 HEAD 的步骤在结果行上面各留一行 旧hash→新hash(链尾==结果行, 相邻两步首尾相接), 没发生不报; 结果行逐字不动。
- **COMMIT_MSG_AI 消费即删 + 残留收口 (2026-09-27 / 2026-10-07)**: 消息文件在 ref 核对通过后删除(失败出口保留现场); 恢复路径补「HEAD 消息与文件一致照常消费 + 入口残留扫描 + unlink 重试」。

> 已外迁: 2026-10-04 的 2 条 → [attachments/implemented-tooling-archive-2026-10.md](attachments/implemented-tooling-archive-2026-10.md)

- **kb.nav 顶栏「拉取」按钮 · 仅快进同步本仓库 (2026-10-05)**: 导航页顶栏新增拉取动作 —— 点一下让服务端
  `POST /api/pull` 同步当前 clone 到主线远端, **仅快进**: ls-remote 取远端真值(不读 refs/remotes, 该 ref 在
  本环境写入被静默丢弃, 见 [pitfalls/git/refs.md](../pitfalls/git/refs.md)) → fetch → `merge --ff-only`;
  **分叉 / 本地改动重叠 / 离线一律失败**并回一行原因(不 rebase / 不生成 merge commit), 前端弹提示浮层; 成功即
  重拉 `/api/data` 刷新页面。远端按 gitee → origin → github 挑(同 my-commit-flow 的 main_candidates)。安全: 只绑
  127.0.0.1 + 必须带自定义头 `X-Nav-Action`(跨站 fetch 带自定义头会先发 OPTIONS 预检, 本服务不答即被浏览器拦下)
  + Origin 回环校验 + `_PULL_LOCK` 串行化; 静态导出 / file:// 无服务端, 按钮隐藏。守阵 `tests/test_kb_nav_*.py`
  +11(壳按钮骨架 / 分类纯逻辑 / 非仓库·游离 HEAD·离线·分叉·本地领先·快进六场景 / 端点 403 护栏 + 404 +
  结果回传), **数据层 nav_data.py 零改动**, 服务层新增 POST 路由与 git 编排。基线 2553 passed + 4 skipped /
  99%(切片 [26-10-05-0324](../testing/baselines/attachments/26-10-05-0324-kb-nav-pull.md))。

- **kb.nav 跟进轮九~十七 (2026-10-05~13, 专题 kb-nav-page, 切片 26-10-04-0952)**: 导航页壳 `nav_page.html` 单文件多轮改, 数据/服务层零改动 —— ⑨状态徽章三层底色口径 (台账 `.chip.st-*` 与控制台 `.rs.st-*` 共用透明度阶梯, 底/边/字三通道; 根因 `.chip{color:--dim}` 同特异性后盖状态文字色 + cyan/green 令牌明度几乎相同靠 alpha 拉开); ⑩顶栏专用令牌 `--chrome` (用户撤销后还原 `--paper`, 反向守阵 `test_topbar_surface_is_left_at_paper`); ⑪台账列标题行 `thead th` 改 `--chrome` (列头与数据行同 `--bg` 差 0 读不出表头; 相邻面逐面过, 克隆同款表头必须跟着改); ⑫置顶专区表头修 (`--chrome` 抬 #232e3b→#2b3947, 强调过的行挤明度空间, 合成色真算); ⑬隐藏功能 (独立键 `mb-nav-hidden`, 复用 pin 骨架, 隐藏区 `#hidZone` 同构, 四处退场单点); ⑭类型栏 (issue-type chip, 列序守阵扩); ⑮类型栏空值去占符 (`"·"`→`""`); ⑯Esc 退栈计划 26-10-13-0324 (拉取失败全屏锁 = doPull 失败弹 `#overlay` z-50 全屏遮罩, POLL_MS 30000 ⇒ ≤30s 不可点击); ⑰Esc 退栈实施 `escRetreat()` 单链 (退栈 order = visual z-order overlay→ctxMenu→drawer→sel, IME 组合期守卫, 判据用可见性, 遮罩退最上档即消锁; 守阵 +4 single_point/ime_guard/overlay_first/closes_drawer). 各轮基线切片见 kb.baseline; 判据单点 [pitfalls/web-ui/layout-css.md](../pitfalls/web-ui/layout-css.md) 状态徽章/顶栏/表头面同色条 + [pitfalls/web-ui/poll-reseed-filter.md](../pitfalls/web-ui/poll-reseed-filter.md)。

- **kb.nav 多选与批量右键菜单 (2026-10-31, 专题 kb-nav-multiselect, 计划 26-10-31-0143 全段落地)**: 台账加文件管理器式多选 —— Ctrl+click 切换 / Shift+click 锚点区间**并入** (auto-qb selection.js 口径: 锚点不动, 可从同一起点多次扩段), 主表 + 置顶专区双区同亮 (置顶件双向显示, link 为键), 普通单击 = 现行为且**不清多选** (拍板 D3, 用户明确拒绝「单击清多选」—— 容易误触); 右键批量升级照 auto-qb menu.js CTX-03 —— `ctxTargets` 单点解析 (集合>1 且行∈选区 → 整集合快照, openCtx 冻结 `dataset.links`, 右键不改选区), 批量文案带灰色 N (拍板 D12), 四项动作走批量链: pin/hide 幂等批量 (`every` 动态反向文案, 批量隐藏把隐藏件剪出选区), 复制每行一个 `memory-bank/<link>` 按主表可见序 (被筛掉的选中行按全量序追加), 打开 >5 先 `window.confirm`; 辅助件: 顶栏「已选 N」chip 点击清空, Esc 退栈链末档清多选 (drawer 档后、遗留 tr.sel 前), Ctrl+A 台账非输入态全选可见行, 切视图即清空。选区 `S.multi`/`S.multiAnchor` 纯会话态 (derive()/saveFilters() 均不碰, 同 pin 坑型)。守阵 `tests/test_kb_nav_*.py` +6 (会话态与手势 / 双区渲染 / 批量升级 / 幂等 / 辅助件 / 复制与打开); Playwright 无头真机冒烟全过 (脚本 tmp-analysis/nav/, gitignored)。
  计划 [26-10-31-0143](../plans/26-10-31-0143-plan-kb-nav-multiselect.html)。

- **kb.nav 搜索支持文件名/相对路径 (2026-11-03, 专题 kb-nav-searchbox)**: 用户复现「#gq 输入
  `memory-bank/reports/<文件>` 无匹配」—— 根因: 搜索 haystack 只拼 title/topic/issue-summary, `link` 未入索引,
  且匹配是对整串做 `includes`。修法: 壳内新增 `navSearchText()` / `navSearchQuery()` 单点, 索引加法式补
  `link` (basename 随之可搜) 与 `memory-bank/<link>` 仓库根相对形态; 台账 `aFiltered` / 控制台
  `renderChannels` / 卡片墙 `cVisibleItems` 三处统一消费, 正文不入索引 (体积口径), 大小写与反斜杠归一;
  排序/展示与原有标题·专题·摘要匹配行为不变, 数据层/服务层零改动。守阵 `tests/test_kb_nav_*.py` 新增一条
  (node 回放页内真实 JS 单点: basename / mb 内相对路径 / 仓库根相对路径 / 大小写 / 反斜杠 / 原字段 / 无关词),
  数字见 kb.baseline。合流后顺带修远端新守阵的环境依赖 (`tests/test_real_machine_safety.py` 受控桩分支
  原先默认 `tmp_path` 在非系统卷且祖先目录不带 hidden 属性, 本机 TMP=C:/AppData 下必然误红; 桩化
  `SystemDrive` 与非 `hid` 路径属性后与运行环境解耦), 详情见对应基线切片的「首跑红及处置」。

- **kb.nav 置顶区折叠 + 置顶条目单击对齐主区 (2026-11-03, 专题 kb-nav-pin-zone)**: 两处交互改动都在壳
  `nav_page.html`(数据层/服务层零改动)。①置顶专区标题行加**折叠按钮** `#pzToggle`: 原生 `button`
  (回车/空格即触发, 不另写键位), `aria-expanded` + `aria-controls="pzBody"` + `aria-label`, 折叠箭头
  靠 `.pinzone.collapsed` 旋转 -90° 反映状态; 收起只藏表格主体 `pzBody`, **标题行与展开入口始终可见**;
  折叠态落 `mb-nav-pin-collapsed`(与 PINS_KEY 同款 try/catch 降级, boot 唯一装载、derive 不碰, 同 pin 坑型)。
  应用单点 `applyPinCollapse()` 只动类 / aria / `[hidden]`, 不重建 innerHTML —— 重建会把焦点从按钮丢回 body。
  ②置顶条目单击原先 `window.open` 原文, 与主区(打开右侧抽屉)不一致; 收成共用单点 `openRowDetail(link)`
  (主表与置顶区的 click 委托都调它, 同一 `renderDrawer` / 同一 `sel` 高亮), 置顶件双向显示时两区同 link
  同亮; Esc 行选择退档改扫 `#v-ledger` 下全部 `tr.sel` 覆盖双区。图钉 / 多选 / 折叠早退分支仍留在各自
  click 委托里(不进单点)。守阵 `tests/test_kb_nav_interaction.py` +2(node 回放页内真实 JS: 折叠切换 +
  aria 状态 + localStorage, 以及置顶行单击走 `openRowDetail` 而非 `window.open`; 合流时随 R2 测试拆分
  从原 `tests/test_kb_nav.py` 迁入本桶), 数字见 kb.baseline;
  `kb.nav --gen-static` 生成静态页真机验证 5 项 PASS(折叠/展开/抽屉/选中态)。

> 已外迁: 2026-09-15~09-24 的 12 条 → [attachments/implemented-tooling-archive-2026-09.md](attachments/implemented-tooling-archive-2026-09.md)
> 已外迁: 2026-10-01 的 1 条 → [attachments/implemented-tooling-archive-2026-10.md](attachments/implemented-tooling-archive-2026-10.md)
