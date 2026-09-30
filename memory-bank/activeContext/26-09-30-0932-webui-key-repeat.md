# WEBUI 上下键长按连发

> 摘要: 用户需求"快捷键上下键按住不动可连续触发"已实现, 随本轮提交。shortcuts.js 引擎
> repeat 拦截改逐键查询后判定, 注册表 `repeat: true` 标记条目放行长按连发; 放行面 =
> 光标上/下移 + Shift+上/下扩展选择四条, 队列移动(Ctrl+上下)等每按发一条后端命令的键位
> 不放行。守阵 test_arrow_repeat_continuous 钉住放行逻辑与标记面。
> 档案: 基线 testing/baselines/26-09-30-0932-webui-key-repeat.md。
> 最后活动: 2026-09-30 09:32
