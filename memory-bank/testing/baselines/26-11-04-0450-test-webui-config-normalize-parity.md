# 5053 —— 前端 cfgNormalize* 与后端 compat 跨语言对拍守卫(issue 26-11-03-1120 test)

> 摘要: 前端 cfgNormalize* 与后端 compat 跨语言对拍守卫(issue 26-11-03-1120 test)
> 基线时间: 2026-11-04 04:50
**Refs:** memory-bank/tasks/26-11-04-test-webui-config-normalize-parity.md

## 验收数字

`commands run test.full`(2026-11-04 04:46 起跑, 175.1s):

```
TOTAL                                                23370    185   7980    159    99%
  5053 passed, 10 skipped in 172.46s (0:02:52)
```

口径注记:
- 本轮只新增测试文件(前端 JS 镜像未改), 语句覆盖分母 23370、覆盖数 185 未变。
- 新增对拍守卫 3 个用例(`tests/test_webui_config_normalize_parity.py`), 已计入 5053 passed。
- 单跑该守阵文件时覆盖率闸报 FAIL(Total 18.47%)属预期 —— 只跑一个测试文件, 无关本守阵。

## 本改动面

| 文件 | 改动 |
|---|---|
| `tests/config_normalize_parity_support.py` | 新建: `PARITY_CASES`(24 例同输入 spec) + `python_normalize`(金标准) + `cases_json()` + `_NODE_PARITY_PROBE`(node 电池) |
| `tests/test_webui_config_normalize_parity.py` | 新建: `test_python_side_idempotent` / `test_python_side_effective` / `test_js_python_parity` 三个用例 |

未改生产代码(`config/compat.py`、`shared/config_rules.js` 零 diff); 红验注入已全部还原。
