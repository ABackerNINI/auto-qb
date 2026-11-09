# 5877 passed, 2 skipped (177.37s), 覆盖率 99% (26152 stmts / 41 miss) —— quotePath 引号路径漏检修复批全量绿

> 摘要: quotePath 引号路径漏检修复批全量绿
> 基线时间: 2026-11-10 00:51
**Refs:** memory-bank/issues/26-11-07-1216-bug-check-context-caps-porcelain-quote.html

## 验收数字

```text
TOTAL                                                26152     41   9102     53    99%
5877 passed, 2 skipped in 177.37s (0:02:57)
```

(实测时点: HEAD f905b7b7 + 本批工作树改动, `commands run test.full` 2026-11-10 00:48)

## 本改动面

- **修 issue 26-11-07-1216**: `scripts/check_context_caps.py` `changed_files()` 单点改调 `git -c core.quotePath=false status --porcelain`(全脚本唯一 status 调用面)——非 ASCII rename 路径在 git 默认 quotePath=true 下按 C 风格八进制转义输出, 转义串对不上真实路径, 「改动命中」判定静默漏检。`porcelain_paths` 解析逻辑不动(不 unquote), docstring 局限段改写为「调用方统一关 quotePath + 残余边界」(路径本身含引号/反斜杠/控制字符时 git 仍会加引号, 现仓无此类路径)。
- **新守卫用例** `tests/test_legacy_review4_scripts.py::test_changed_files_disables_quote_path`: wire 面 monkeypatched subprocess 钉死命令行逐字形态; 机制红验用默认 quotePath=true 下 git 真实输出的转义 rename 行穿过解析面, 断言两侧真实路径不在集合(sidefx 台账禁 POPEN, 不真弹 git)。测试文件头部「测试计划」清单同步登记。
- **issue 回写**: 翻 In Progress → Done(徽标+meta 两处), 补复验行(head f905b7b7 锚点仍在)与「修复后补充」(实际修法/验证方式/测试数字)。
- 评审 2 轮(首轮 1 条 minor: 夹具旧侧漏 docs/ 前缀致断言空转, 当场修; 复评轮零 actionable)。
