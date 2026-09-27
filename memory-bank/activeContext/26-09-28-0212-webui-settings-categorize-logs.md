# webui 设置页分类回归修复(「常规/日志」成块 + 运行日志折叠)实施

> 摘要: 用户实报 26-09-26 分组合并(1905d6d)丢分类 —— 日志等三段因 open=True 被 cfgFlatten 平铺进「常规/常规」。修复: 三段去 open=True 恢复成块(标题 日志/WebUI/通知 + 旧分组 help, 永远展开不折叠), 运行日志块默认折叠 + 首次展开才拉 /api/log(hubLogsToggle/hubLogsLoad), hubHits/hubFieldCount 递归适配; 守阵钉"尾三段不声明 open"; 三套 UI(atlas/prism/console)经 shared 模板+JS 一处生效(console 纯 CSS 换肤, manifest 守阵钉一致性)。test.full 1815 passed + 3 skipped, TOTAL 91.39%(基线 26-09-28-0212); 档案 tasks/26-09-28-webui-settings-categorize-logs.md。
> 最后活动: 2026-09-28 02:12

## 正在进行

- 等待用户说「提交」—— 收尾回写已全部落盘(档案/切片/基线/progress 条目/索引重建)。

## 关键决策

- 成块 ≠ 折叠: 去 open=True 后 hubBlocks 自动渲染成带标题且永远展开的块, 同时满足分类显性与 2026-09-15 平铺诉求。
- `open` 字段保留为 schema 通用能力(现仅 hr_check optional 段在用), 平铺分支注释改写防再误用。
- 运行日志懒加载取代"打开分区预取": 折叠态动等级/行数/刷新自动展开再拉。
