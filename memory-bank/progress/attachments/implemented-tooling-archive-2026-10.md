# 已实现 · 依赖 / 知识库 / CI · 2026-10 段 (外迁存档)

> 摘要: 2026-10-01 / 2026-10-04 段原文逐字外迁 —— 四工位导航页 / 台账置顶 pin / 全库文档漂移分段修复(3 条)。
> 触发: 已实现, kb.nav, 导航页, 文档漂移, 外迁存档

> 本文件是外迁存档: 主档 `memory-bank/progress/implemented-tooling.md` 的 2026-10-01 / 2026-10-04 段 原文逐字搬来(仅相对链接整体下移一层 —— 本文件在 `progress/attachments/`); 主档原位留指针。

- **memory-bank 四工位导航页 · 三视图可切换 (2026-10-04, 计划 26-10-04-0952 全段落地)**: issues / plans /
  reports / tasks 的状态与关联做成本地导航页, 主视图三套并存(台账 / 控制台 / 卡片墙)顶栏一键切换(选择记忆
  localStorage, file:// 降级)。数据层 `nav_data.collect_nav()` 复用 `gen_doc_map.collect()` 做**薄 enrich**
  (issue 补 issue-type / issue-tier / issue-summary, 全形态补 doc-updated 缺省回落 stamp; 派生 topics[](../live
  口径同 is_live)与各形态 x 状态 counts), **不改 collect() 本体**(闸门/守阵消费单点, 键集合由守阵钉死);
  stamp 取数据自带 doc-updated 最大值, 不生成依赖当前时钟的内容。服务层 `nav_server.py` 纯 stdlib
  http.server 绑 127.0.0.1:8765(allow_reuse_address 必须关 —— Windows 上 REUSEADDR 会让同端口双绑静默成功),
  但**浏览器打开的地址用 localhost:8765**(`OPEN_HOST`, 2026-10-04 起; 127.0.0.1 那个 origin 有历史遗留, 换
  localhost 拿干净 origin —— 监听仍只绑回环 IPv4, localhost 解析回落即达):
  `/` 页面壳 + `/api/data` 每请求现算(前端 30s 轮询准实时) + `/memory-bank/<path>` 静态映射(resolve 后必须
  严格落在 memory-bank/ 内, 越界一律 403, ../ %2e%2e ..%2f 反斜杠变体全拒)。壳 `nav_page.html` 入库
  scripts/(http 模式 fetch + 轮询; 静态模式 `--gen-static` 注入单文件, 默认 tmp-analysis/nav/ 已 gitignored);
  `color-scheme: dark` 零外链资源。挂点 `commands run kb.nav`(前台长跑 Ctrl-C 停)。守阵
  `tests/test_kb_nav_*.py` 9 条: 数据形状 / issue enrich / stamp 防时钟 / collect() 键集合不回归 / 壳三视图
  容器+dark+零外链 / 服务层三路由与防穿越, 全桩目录零网络外呼零子进程。基线 2471 passed + 4 skipped /
  覆盖率 99%(切片 26-10-04-1039)。计划
  [26-10-04-0952](../../plans/26-10-04-0952-plan-kb-nav-page.html)。

- **kb.nav 台账置顶 (pin) (2026-10-04, 专题 kb-nav-pin, 计划 26-10-04-1830 全段落地)**: 导航页台账新增人工置顶 ——
  行内图钉 (空心 = 未 pin / 实心 = 已 pin, 点它切换) + 「置顶 · PINNED」**增量专区** (被 pin 件**同时**留在原表格
  = 双向显示, 专区不受筛选/搜索影响) + 右键菜单 (置顶/取消置顶 · 打开原文 · 复制仓库路径)。pin 是**人的视线偏好**、
  非文档属性: 落 localStorage `mb-nav-pins`(与视图选择同款 try/catch 降级), **只在 boot 装载一次、derive() 绝不触碰**
  (同「状态筛选器自动重置」源风险, 坑档案 poll-reseed-filter.md), 不写进任何件 meta、**数据层/服务层零改动**。图钉
  内嵌 title-cell (零列序改动, 不新增 td), 内联 SVG 无外链图标库、无 emoji。守阵 `tests/test_kb_nav_*.py` +4(专区/菜单
  骨架 · derive 不碰 pins 且装载点唯一 · 双向渲染 · 内联 SVG 无 emoji)。基线 2515 passed + 4 skipped / 99%
  (切片 26-10-04-1849)。计划 [26-10-04-1830](../../plans/26-10-04-1830-plan-kb-nav-pin.html)。
  **2026-10-05 改版 (用户: 专区改为与主区同栏的详细列表, 只置顶 + 强调)**: 专区不再是紧凑 chip 列表, 而是与主表
  **逐栏一致**的七栏详细列表 —— 列定义**单点** = 主表 thead(专区渲染时克隆 `thead.outerHTML`), 行单元格**共用**
  `ledgerCells()`(主表与专区同一份栏序/栏宽), 从结构上排除两处漂移; 栏对齐靠 `table-layout: fixed`(列宽只认首行)
  + 两滚动容器 `scrollbar-gutter: stable`(预留等宽滚动条槽) + 专区容器横向 padding 归零、左 accent 用 `inset` 阴影
  而非 border(都不许改内容宽度); `#` 栏放实心图钉标记, 行加强调底色。守阵 +1(`test_pin_zone_reuses_ledger_columns`:
  全壳仅一处表头 + 主表行与专区都调 `ledgerCells` + 专区克隆主表 thead), 另 2 条既有守阵改指共用单点。踩坑与机检
  判据见 [pitfalls/web-ui/layout-css.md](../../pitfalls/web-ui/layout-css.md)「两个独立表格逐栏对齐」节; 数据层/服务层仍零改动。

- **全库文档漂移分段修复 (2026-10-01, 从 activeContext 切片 26-10-01-1809 迁出)**: 内核化重构+别名层处置后四波欠账式漂移(P1×9/P2×63/P3≈45, 25 份文件), 按 [plans/26-10-01-1728](../../plans/26-10-01-1728-plan-doc-drift-repair.html) 五段回写**全部完成** —— S1 P1 架构描述重写 5 份(提交 6f474098)/ S2 误导指路与机制反转单点修 9 份(0b422396)/ S3 modules 中度批 6 份(58a88928)/ S4 用户面文档 4 份(7f046ca0)/ S5 P3 计数清扫(projectbrief / roadmap / rules-and-deps 实测刷新)+ 顺手删 mixins/__pycache__ 未跟踪残留; 收尾 test.full **1909 passed + 3 skipped / 91%**(切片 testing/baselines/26-10-01-1930)。代码注释残留 3 处(state.py docstring / qbmanager.py:398 / runtime.py:237)待用户拍板, 未动。滚动档案 [tasks/26-10-01-docs-doc-drift-repair](../../tasks/26-10-01-docs-doc-drift-repair.md)。
