# 基线 · 1832 passed + 3 skipped / 90% —— WEBUI 上下键长按连发

> 摘要: 用户需求"WEBUI 快捷键上下键改为按住不动可连续触发"落地 —— shortcuts.js 引擎原在
> 入口处无条件丢弃 e.repeat 自动重复事件, 改为**逐键查询后判定**: 注册表条目新增 `repeat`
> 标记位, 标记条目放行长按连发, 其余键位维持丢弃。放行四条 = cursor-up/down(ArrowUp/Down
> 移光标) + extend-up/down(Shift+ArrowUp/Down 扩展选择); Ctrl+ArrowUp/Down 队列移动这类
> 每按一次发一条后端命令的键位**不开**(防长按刷爆命令), Delete 与其余动作键不变。
> 守阵 tests/test_web_shortcuts.py 新增 test_arrow_repeat_continuous(解析器 +repeat 字段,
> 钉住引擎放行逻辑与标记恰为四条且 scope=list)。单轮直改, 无计划文档。
> 基线时间: 2026-09-30 09:32 (develop @ 4061d10f + 本轮提交) 制品: 无计划文档(单点小改)。

TOTAL **1832 passed + 3 skipped / 90%**(12731 语句 / 1042 未覆盖 / 4344 分支 / 432 partial,
test.full 26.03s, rc=0) —— 较上基线 26-09-30-0825-open-path(1833 passed + 3 skipped)净 -1 =
本轮 +1(test_web_shortcuts.test_arrow_repeat_continuous), 上基线与当前远端 HEAD 之间存量
-2(commands 守阵 6→4 改写的计数口径差异, 非本轮改动, 如实记录)。

## 本轮改动面

- src/auto_qb/webui/static/shared/shortcuts.js: 引擎 repeat 拦截移到键表查询之后
  (`e.repeat && !(item && item.repeat)`); 注册表 cursor-up/down + extend-up/down 加
  `repeat: true`; 条目形状注释与文件头拦截清单同步。
- tests/test_web_shortcuts.py: _registry() 解析器补 repeat 字段提取; 新增
  test_arrow_repeat_continuous; 头部测试计划清单同步。
- 无后端改动、无新配置键、无 state_file schema 变更。
