# 3967 passed + 10 skipped —— 前端 schema→默认值梯单点(issue 26-10-20-2231)

> 摘要: 前端 schema→默认值梯单点(issue 26-10-20-2231)
> 基线时间: 2026-10-21 03:23
**Refs:** memory-bank/issues/26-10-20-2231-refactor-fe-config-default-ladder-dup.html

## 验收数字

`commands run test.full`(本机 Windows, 仓库自带 TMPDIR 前缀), 实测输出:

```text
TOTAL                                                20467     93   7012     93    99%
3967 passed, 10 skipped in 39.35s
```

**合流后复跑**(远端 `64f20d86` 配置实体 CRUD 收敛 + `be302a02` combobox 族收敛两笔 rebase 进来之后,
同一改动面重跑一次):

```text
TOTAL                                                20467     95   7012     94    99%
3967 passed, 10 skipped in 42.63s
```

缺口 93→95(语句) / 93→94(分支) 是远端两笔各自带入的, 与本轮改动无关; 覆盖率仍 99%, 闸照过。

口径注记:

- 0 failed / 0 error; 覆盖率闸(`--cov-fail-under 99`)照过(99%)。
- 合流解冲突面: 全部落在 `memory-bank/`(7 份 tasks 台账 + `issues/_index.md` +
  `attachments/_archive.md` + `activeContext` 各为「两边各自追加收尾日志」型并集冲突);
  `src/` 与 `tests/` 零冲突 —— `config_editor.js` 与远端那笔 232 行收敛自动合并成功,
  合流后本轮阶梯单点(`cfgDefaultScalar` / `cfgDefaultForFields` / `cfgDefaultForPlugin`)仍在位,
  守阵单跑 1 passed。
- 本轮新增 1 条用例: `tests/test_webui_static_dom_page.py::test_frontend_config_default_ladder_single_point`
  (issue 26-10-20-2231: 静态单点断言 + node 语义电池 11 项); 单跑 1 passed。
- **行为等价性实证**(改动前后各跑一遍同一批输入, 输出逐字节一致):
  ① 合成 schema 电池 10 项输出全等(插件 bool/list/enum/str/object/未知形态 + 可选段两类 + 字段级三类);
  ② **真实 schema 全量对照** —— 从后端 `schema_payload()` 导出真 schema, 对全部 **25 个插件**(13 条件 + 12 动作)
  的 spec 初值与全部 **18 个 object 段**的可选段初值各算一遍, 改动前后两份 JSON `diff` 为空。
- 红验(守阵活性, 三类突变全部符合预期, 均以精确反向编辑还原):
  ① `cfgDefaultScalar` 的 bool 分支改成一律 `"false"`(把插件/字段的口径"顺手统一")
  ⇒ 红, 报「行为漂移: 插件 bool spec 初值 = "true"(与字段级 "false" 的分歧点)」;
  ② `config_rules.js` 里重新手搓一个字段循环 ⇒ 红, 报「又出现了手搓的字段循环」;
  ③ `cfgToggleSection` 不再调 `cfgDefaultForField` ⇒ 红, 报「可选段初值入口断了」(恒久活性探针)。
  还原后 `git diff -- src/` 只剩本轮有意的收敛改动。

## 本改动面

| 文件 | 改动 |
|---|---|
| `src/auto_qb/webui/static/shared/config_editor.js` | 新增阶梯单点 `cfgDefaultScalar` / `cfgDefaultForFields`(opts: requiredOnly / recurse / boolOn); `cfgDefaultForField` 退化为薄壳 |
| `src/auto_qb/webui/static/shared/config_rules.js` | 两份手搓循环(`cfgPluginDefaultSpec` / `cfgPluginDefaultSection`)删除, 换为插件形态分派 `cfgDefaultForPlugin`(spec_kind → list / 子表单 / 叶子阶梯) + 模块级 `SPEC_SCALAR_KINDS` |
| `tests/test_webui_static_dom_page.py` | 新增守阵 `test_frontend_config_default_ladder_single_point`(形态六查 + 恒久活性探针 + node 语义电池 11 项) + 文件头「测试计划」清单一行 + 导入 `json/shutil/subprocess` |
| `memory-bank/issues/26-10-20-2231-refactor-fe-config-default-ladder-dup.html` | 状态 Open → In Progress → Done; §04 改「修复与验证」(复验/实际修法/等价性实证/红验/测试数字), 状态变更日志下沉为 §05 |
| `memory-bank/pitfalls/web-ui/frontend-split.md` | 新增「schema→默认值梯单点」节(触发/判别/处置/守阵登记) |
| `memory-bank/issues/_index.md` · `memory-bank/issues/attachments/_archive.md` | 索引重建生成物(`commands run kb.index`) |
| `memory-bank/testing/baselines/26-10-21-0323-dup-code-audit.md` | 本切片 |

未触及: 三份 `index.html` 与 `shared/` 其它片段(仅 config_editor/config_rules 两个文件)、全部后端代码与 `config.yml`。
上一轮(三 shell sprite/login 段守阵)的改动与数字见 `memory-bank/testing/baselines/26-10-21-0225-dup-code-audit.md`。
