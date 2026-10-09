# webui-qb-traffic-seed-header-controls — 种子流量图的档位/纵轴控件落点 + 统计栏口径注解形态

> 摘要: 本专题三轮同日落定 —— ①上一轮: 控件补进种子头部(修「控件消失」); ②第 2 轮: 用户否决头部落点
> (「太挤、小窗口下会变形」)⇒ 改落**图下统计栏**(`.hist-summary` 内 `.qb-statctl`, 排在「下载累计」之后),
> 统计栏本体门放宽为 `qbCurSummary || qbCurScope === 'torrent'`; ③第 3 轮: 统计栏常驻口径注解
> 「累计为窗口内增量(断线期不计)」退场, 改为**上传累计 / 下载累计两个读数的悬浮提示**(`:title="qbCurSummaryHint"`,
> 走全局断供管道 → `data-aq-tip`)。第 3 轮顺带把统计栏从两行收回**单行**(33px), 图由 235px 回到 259px ——
> 第 2 轮「图少约 31px」的代价随之消失。**全局/分组流量形态全程零改动**; 零 JS 改动; 守阵只改写既有断言
> 口径(零新增测试函数); 真浏览器三皮肤 + 四档窄视口实测不越界、tooltip 正常、零 pageerror。已闭环。
> 最后活动: 2026-10-09 12:07

**Refs:** memory-bank/tasks/26-10-09-webui-qb-traffic-seed-header-controls.md,memory-bank/testing/baselines/26-10-09-1207-webui-qb-traffic-seed-hint-tooltip.md

- 任务档案: [26-10-09-webui-qb-traffic-seed-header-controls](../tasks/26-10-09-webui-qb-traffic-seed-header-controls.md) —— 三轮的根因/取舍/实测数字都在档案, 本切片只留指针。
- 落地(纯前端静态层 + 测试侧, Python 产品代码零改动): `shared/tpl/drawer.html` —— 种子头部不挂控件组;
  统计栏 `.hist-summary` 内「下载累计」之后挂 `.qb-statctl`(内含与流量形态头部**逐字同源**的 `.qb-tabs` +
  `.qb-tools`, 门 `v-if="qbCurScope === 'torrent'"`); 两个累计读数各挂 `:title="qbCurSummaryHint"`。
  三皮肤 `views.css` 只加了 4 行 `.hist-summary > .qb-statctl`(成组 / 内层不收缩 / 紧凑档) —— 第 3 轮**零 CSS 改动**。
- 关键判据(易被后人改坏): ①控件是**两处挂点**(流量形态头部 / 统计栏), 改一处必须同步另一处 —— 守阵把两块
  内层(空白归一后)比对, 不同步即红; ②统计栏内那组的门必须是 `qbCurScope === 'torrent'`; ③统计栏本体必须门在
  `qbCurSummary || qbCurScope === 'torrent'` 上(只写 `qbCurSummary` = 首载/错误态控件整组消失);
  ④落点次序 = 图例 → 窗口 N 桶 → 上传累计 → 下载累计 → 控件组, 由守阵按下标单调钉住; ⑤种子头部**不得**再出现
  `.qb-statctl`/`.qb-headctl`(该头部回归单行 44px); ⑥口径注解必须是**两个**累计读数上的 `:title`
  (守阵钉 `count(':title="qbCurSummaryHint"') == 2`)且抽屉里**不得**再有 `.hist-hint` span。
- ⚠ 别顺手删 `.hist-hint` 的 CSS: 抽屉里那处用法已退场, 但 `shared/tpl/popovers.html`(今日流量弹层
  「悬停查看详情」)仍在消费同一条规则 —— 三皮肤各一行, 删了那边就裸奔。
- 版式实测(真浏览器, 三皮肤 1440x900): 头部 44px(单行)/ 统计栏 31~33px(**第 3 轮起单行**, 第 2 轮为 54~57px
  两行)/ 控件组 821px 起于「下载累计」右侧不越界 / 图 259~261px(第 2 轮 235~238px)。窄视口 1180/980/820:
  头部恒 44px、横向溢出 0。tooltip: 悬停两个累计读数均弹「累计为窗口内增量(断线期不计)」, 分组作用域自动带
  「 · 组口径 = 当前成员集聚合」尾注。
- 未验证面: ①15 个 `drawer_tpl/` 变体下统计栏的观感未逐变体走查; ②折叠态(`drawer.collapsed`)与统计栏同屏时
  的观感未走查(2026-10-09 起**不再适用** —— 折叠状态已整体移除, 见档案 26-10-09-webui-drawer-collapse-removal); ③tooltip 在抽屉贴近屏幕底缘时的弹层避让未专项走查(全站 tooltip 共用同一避让实现)。
