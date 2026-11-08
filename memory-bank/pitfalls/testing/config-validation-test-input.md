# 配置校验类测试的输入构造：BaseLoader 标量全为字符串 + _strip_none 先剥空串

> 摘要: 给 config 校验器写测试时, 走 `load_config`/`_load_errors` 这条真实链路(而非直调校验函数)最省事, 但**输入必须先过两道加工**再进校验器: ①YAML 用 **BaseLoader** 读, **所有标量一律是字符串** —— `- 123` 读成 `"123"`、`enabled: true` 读成 `"true"`; ②`_strip_none` 在进 `validate_config` 之前**剥掉 `""` 与 `None`**(含**列表项**)。于是「`_check_str_list` 的第 N 项不是字符串」这类**类型分支**, 用标量(`123`)或空串(`''`)当列表项**根本进不去** —— 前者已是合法字符串, 后者被 `_strip_none` 提前删掉(列表还非空 → 不报错), 测试会「写对了断言却拿不到错误」。要打到该分支, 列表项必须是**嵌套容器**(如 `- [x]` / `- {}`), 它既不是字符串、也不会被 `_strip_none` 删。
> 触发: 写 config 校验测试, 校验器测试, _load_errors, load_config, BaseLoader, 标量全是字符串, 空串被剥, _strip_none, _check_str_list, 第 N 项必须是非空字符串, 类型分支进不去, 断言拿不到错误, YAML 输入构造, 列表项类型

**Refs:** memory-bank/tasks/26-10-08-test-mutation-audit.md, memory-bank/testing/baselines/26-10-09-1611-mutants-config-loop-guards.md

### 实证（2026-10-09, config loop-guards 轮）

- **触发**: 给 `_validate_tag_lists`(校验 `delete_tags` / `delete_tags_if_has_no_torrents` 是字符串列表)补多条目守阵, 想构造「列表项非法」让 `_check_str_list` 报 `第 [0] 项必须是非空字符串`。首版写 `delete_tags_if_has_no_torrents: [123]` → **无任何错误**; 二版写 `['']` → **仍无错误**; 三版 `- [x]`(嵌套列表项)才报出来。
- **判别**: 表现为「写对了断言却拿不到错误」。判据是看目标分支在进校验器**之前**要过的两道加工 —— ①BaseLoader 把所有标量读成字符串(`123` 读成 `"123"`); ②`_strip_none` 先剥 `""`/`None`(**含列表项**)。我造的列表项若被这两步改造过, 分支就永远进不去。两个原因具体是:
  - `123` 经 BaseLoader 读成字符串 `"123"`, `isinstance(v, str) and v.strip()` 全真 ⇒ 合法, 不是类型错误。
  - `''` 被 `_strip_none` 在**校验前**剥掉(`_strip_none({"a": [1, None, "", "x"]}) == {"a": [1, "x"]}`, 见 `test_strip_none_list_branch_and_key_case`); 列表变成 `[]`, 而 `_check_str_list` 认为空列表合法 ⇒ 不报错。
  - 与坑档 [unreached-branch-guard.md](unreached-branch-guard.md)(夹具让分支不可达)同源: 这里的「不可达」来自链路前置加工, 不看这两步就永远造不出目标输入。
- **处置**: 要打「列表项类型不对」的分支, 用**嵌套容器**做列表项(`- [x]` / `- {}`) —— 非字符串且不被 `_strip_none` 删。更一般地: 写 config 校验测试前先问「我要打的那一行分支, 我造的输入**真的进得去**吗」。
