# 文案排查的清点面: 必须覆盖全部渲染出口

> 摘要: 「全量文案排查/统一」若只清点主数据链(列模型 + 经典详情行), 会漏掉抽屉变体(drawer_tpl 15 个)、页插件(drawer_pages 4 个)与模板分片(tpl/)里的同词 —— 用户复查实证(26-10-10-2237 报告 §11): 一轮改了 ~470 处仍被指出「种子详情面板/用户页多数没对齐」。**「全量」的定义 = grep 全部渲染出口, 不是 grep 主链**; 且变体常按**行 label 字符串**过滤消费 drawer.js 的行(label 改名必须连过滤表一起改, 「分块→区块」即再犯例)。
> 触发: 文案统一, 术语对齐, 排查报告, 全量替换, 清点面, 变体, 页插件, drawer_tpl, drawer_pages, label 过滤, 报告遗漏, 用户复查

### 文案统一/全量排查的清点面纪律

- **触发**: 文案统一 / 术语对齐 / 全量文案排查报告 / 批量替换旧词(「全量」类任务)。
- **判别**: 清点面若只覆盖主数据链(列模型 + 经典详情行)即违规 —— 抽屉变体(drawer_tpl 15 个)、页插件(drawer_pages 4 个)、模板分片(tpl/)、设计稿母本(resources/detail-panel-templates)里的同词会整批漏掉; 变体还常按**行 label 字符串**过滤消费 drawer.js 的行(label 改名必须连过滤表一起改, 「分块→区块」即再犯例)。实证: 一轮改 ~470 处仍被用户复查指出「种子详情面板/用户页多数没对齐」(26-10-10-2237 报告 §11)。
- **处置**: ①开工先列清点面清单: `shared/*.js` + `shared/tpl/*.html` + `drawer_tpl/` + `drawer_pages/` + `resources/detail-panel-templates/` + 守阵断言串 + e2e 选择器; ②基准词不靠记忆, 逐条按 qB `.ts` 的 `<source>` 抽取(qB WebUI/GUI 两版不一致的词先请用户拍板); ③替换用「精确串 + 命中数断言」脚本(少命中即报, 防误伤防漏改); ④改 label 前 grep 旧词全库, 同步 `r.label === "…"` 等过滤表; ⑤守阵/e2e 钉的文案串是替换面的一部分, 首跑 `test.quick` 让守阵说话(本轮守阵断言「tracker 列表加载失败」3 处首跑红), 别抢在守阵前手工全改。
- **复发**: 1 —— 2026-10-11 GitHub Action 全量 e2e **34 failed / 168**: 文案统一提交 `1d7c864b`(开始/暂停→启动/停止、限速…→速度限制…、移动…→设定位置…、跳检…→跳过哈希校验…)只同步了 `menus.spec.mjs` / `delta-sync.spec.mjs` 两个 spec, 另三个(`trigger-scope` / `optimistic` / `multiselect-shows`)整套旧选择器 + `menus.spec` 内两条数组式断言(主路径「四项齐」、W5-off 多选)+ **toast 文案**「已执行: 批量限速(N 个目标)」(源侧是 `drawer.js::editLimitsMulti` 传给 `_bulkEditPost` 的 okText `"批量速度限制"`, **不是菜单显示名**)全部漏掉。为什么没命中: 本条 ①⑤ 虽已把 e2e 选择器写进清点面, 但执行时是「改到哪个 test 文件就顺手改哪里」, 不是**按旧词 grep `e2e/` 全目录逐个收口**(同批只同步了 delta-sync、漏了另三个, 是典型的只扫眼前文件); 且 e2e 侧**没有提交闸门** —— `test.quick` 守阵钉的是模板/JS 的**源头串**, 钉不到 e2e 的选择器与断言串, 全量 e2e 只有 CI 在 push 之后才跑。新增判据: **改了任何 UI 文案串, 收尾必须跑全量 e2e(`commands run dev.e2e`), 只跑 `--grep @fast` 子集兜不住**(34 条红里 menus 主路径组与 optimistic 全组都不在 @fast 内)。
