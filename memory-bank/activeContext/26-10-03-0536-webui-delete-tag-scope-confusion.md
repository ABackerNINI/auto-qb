# 全局/站点双设置作用域混淆分析(26-10-01-2129) — 报告轮完成, 停在拍板

> 摘要: 用户指派分析 issue 26-10-01-2129(「删除类标签」全局/站点单设置混淆)出报告。取证结论: 缺陷三层 —— config 层 `_strip_none` 使 str/list「显式空=未定义」坍缩(bool 可区分, 文档化设计) / WebUI 层 bool 开关恒写值从不删键单向锁死(恢复入口死代码, 后端删键链路已在, 纯前端接线可修) / 回填显示用 schema 默认非生效全局值; 受影响面 9 个全局/站点双层键。方案 A(只修 WebUI, S)/C(WebUI 修齐, M, 推荐)/B(config+WebUI 完整三态, L, 挂触发条件待命); 「是否填 config 层」= 当前不填。产出: [reports/26-10-03-0504](../reports/26-10-03-0504-report-webui-site-scope-confusion.html)(专题 webui-delete-tag-scope-confusion)+ 档案 [tasks/26-10-03-webui-delete-tag-scope-confusion](../tasks/26-10-03-webui-delete-tag-scope-confusion.md) + 三方认领链。主会话只委派: 3 子智能体串行(取证/调研/报告)全部一次成功, 零代码改动, 基线 8cb2da59。**停在拍板: D1 选方案(推荐 C) / D2「站点覆盖为空」是否真实需求(是则直接 B)。**

> 最后活动: 2026-10-03 05:36
