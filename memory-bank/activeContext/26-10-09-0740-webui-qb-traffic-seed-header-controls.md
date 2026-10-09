# webui-qb-traffic-seed-header-controls — 种子流量图的档位/纵轴控件落点(第 2 轮: 改落图下统计栏)

> 摘要: 用户对上一轮的落点提出更正 —— 控件放**种子头部**「太挤, 小窗口下会变形」, 改放**图下统计栏**
> (`.hist-summary`, 排在「下载累计」之后)。落点容器由 `.qb-headctl`(种子头部末位, `flex:1 1 100%` 恒占
> 第二行)换成 `.qb-statctl`(统计栏内一个 flex 组); 统计栏本体的门**放宽一档**(`qbCurSummary ||
> qbCurScope === 'torrent'`), 否则首载/错误态没有汇总 ⇒ 连换档位都点不到。**全局/分组流量形态不动**
> (控件仍在流量形态头部)。零 JS 改动; 守阵只改写既有断言口径(零新增测试函数); 真浏览器三皮肤
> 1440x900 + 四档窄视口(1440/1180/980/820)实测不越界、零 pageerror。已闭环。
> 最后活动: 2026-10-09 11:14

**Refs:** memory-bank/tasks/26-10-09-webui-qb-traffic-seed-header-controls.md,memory-bank/testing/baselines/26-10-09-1114-webui-qb-traffic-seed-statbar-controls.md

- 任务档案: [26-10-09-webui-qb-traffic-seed-header-controls](../tasks/26-10-09-webui-qb-traffic-seed-header-controls.md) —— 两轮的根因/取舍/实测数字都在档案, 本切片只留指针。
- 落地(纯前端静态层 + 测试侧, Python 产品代码零改动): `shared/tpl/drawer.html` —— 删种子头部末位的
  `.qb-headctl` 控件组, 改在 `.hist-summary` 的「下载累计」之后插 `.qb-statctl`(内含与流量形态头部
  **逐字同源**的 `.qb-tabs` + `.qb-tools`, 门 `v-if="qbCurScope === 'torrent'"`); 三皮肤 `views.css` 各把
  原 5 行 `.qb-headctl` 规则换成 4 行 `.hist-summary > .qb-statctl` 规则(成组 + 内层不收缩 + 紧凑档)。
- 关键判据(易被后人改坏): ①控件仍是**两处挂点**(流量形态头部 / 统计栏), 改一处必须同步另一处 —— 守阵把
  两块内层(空白归一后)比对, 不同步即红; ②统计栏内那组的门必须是 `qbCurScope === 'torrent'`(单点派生:
  种子形态 + 流量页签 + 功能开启); ③统计栏本体必须门在 `qbCurSummary || qbCurScope === 'torrent'` 上
  (只写 `qbCurSummary` = 首载/错误态控件整组消失); ④落点次序 = 图例 → 窗口 N 桶 → 上传累计 → **下载累计**
  → 控件组 → 口径 hint(用户口径「即『下载累计』后」), 由守阵按下标单调钉住; ⑤种子头部**不得**再出现
  `.qb-statctl`/`.qb-headctl`(该头部回归单行 44px)。
- 版式实测(真浏览器, 三皮肤 1440x900): 头部 44px(单行, 回到 10-08 版式改的目标形态)/ 统计栏 54~57px
  (两行: 汇总 + 控件同行, 口径 hint 被 `margin-left:auto` 顶到第二行)/ 控件组 821px 起于「下载累计」右侧
  不越界 / 图 235~238px。窄视口 1180/980/820: 头部恒 44px、统计栏 58→81px、横向溢出 0。
- 代价(留给后续评估): 统计栏由 26px 变 54~57px ⇒ 图少约 31px(10-08 版式改「把高度还给图」的收益被吃掉
  一部分); 口径 hint 独占第二行。用户口径是「先放…看看效果」, 若嫌图矮, 下一步可考虑 hint 让位或控件组
  与汇总分行合并。
- 未验证面: ①15 个 `drawer_tpl/` 变体下统计栏的观感未逐变体走查(变体消费同一数据域, 本次未动变体);
  ②折叠态(`drawer.collapsed`)与统计栏同屏时的观感未走查。
