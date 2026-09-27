# 1816 passed / 3 skipped —— 搜索框语法帮助入口(框内幽灵「?」+ 锚定浮卡, 方案A)

> 摘要: 顶栏搜索框加「高级用法」帮助入口 —— 3 版交互式提案(计划 26-09-28-0201)用户拍板方案A; 「?」幽灵钮恒显于输入框内清空钮左侧, 浮卡列 词 AND/`-词`/`"短语"`/`-"短语"` 四行语法 + 容错提示, 示例行点击回填即搜; 占位符同步简化为「搜索种子或文件名...」。
> 基线时间: 2026-09-28 03:00
> 档案: 26-09-26-webui-search-query-syntax

- **本线新增守阵 1 条**(test_web.py): `test_frontend_search_help_wiring` —— 模板(帮助钮/浮卡/
  示例回填/简化占位符)+ state 声明 + view.js 方法(回填即搜/焦点还输入框)+ 三条收起路径
  (点空白/Esc/导航)+ 挂件类在共用层 console_hub.css 成对定义 + 三皮肤 input 右内边距 52px 留位。
  用例总数较上条基线(1815+3)的 +1 即本条。
- 挂件样式落点: 三 UI 共用层 `shared/console_hub.css`(不计各皮肤 700 行单文件 cap —— atlas
  components.css 已贴顶); 星图无 `--font-mono` 令牌, mono 一律 `var(--font-mono, 内联栈)` longhand
  (shorthand 遇未定义令牌整条失效连 font-size 一起丢)。
- 实机验证(dev.harness 桩 + Playwright, 非本基线数字来源): atlas/prism/console 三套 UI 开合/
  回填/Esc/点空白/清空共存全通过, 示例 `"web dl"` 经真实后端 `search_torrents` 命中 35/60 辅种,
  页面零 JS 错误。
- 附带收口: 新计划文档使 `_doc-map.md` 撞 index-auto cap(12,284>12,200) → 按
  pitfalls/kb/cap-counting.md「两个出口」①改渲染口径(gen_doc_map 计划/报告展示戳截到日期精度,
  `--date_stamp`, 全表省 ~245 字符, 零信息损失), 本线后余量 161 字符; 该坑档本体仅剩 47 字符
  余量, 下轮收尾回写前先量。

TOTAL **91%**(12504 语句 / 914 未覆盖 / 4204 分支 / 388 partial), 耗时 19.18s(单次采样)。
