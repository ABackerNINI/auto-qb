# 26-11-04-test-webui-config-normalize-parity — 前端 cfgNormalize* 与后端 compat 规范化跨语言对拍守卫

**Status:** In Progress
**Added:** 2026-11-04
**Updated:** 2026-11-04
**Summary:** 前端 cfgNormalize* 与后端 compat 规范化跨语言对拍守卫
**Topics:** test-webui-config-normalize-parity
**Refs:** memory-bank/issues/26-11-03-1120-test-webui-config-normalize-parity-gap.html, memory-bank/issues/26-11-04-0504-test-webui-normalize-dom-battery-vacuous.html

## 原始请求

1. 「认领并修复 26-11-03-1120-test-webui-config-normalize-parity-gap.html」 —— 认领该 issue(状态 Open → 修复中)并落地其建议: 前端 `cfgNormalize*` 与后端 `compat` 规范化之间补自动对拍守卫。
2. 「继续 / 继续 / 继续」 —— 继续把手上这一步做完(不扩大范围)。

## 思考过程与决策

- **issue 给出的两条出路, 取第一条(加对拍),不回退第二条(删前端镜像)**: 镜像的存在是 D2 设计选择 —— 打开设置页**显示就已是归一形**、保存即写新形态, 后端 `normalize_legacy_rule` 再跑一遍是幂等兜底。若改成"只由后端下发规范形", 要重做 `cfgSetTree` 载入链和整套 DOM 电池, 改动面远大于本 issue(light 档)的定位, 且会动到 D2 验收口径。对拍守住语义等价, 镜像就可以安全留存。
- **期望值只写一份**: 对拍**不写**第三份手抄期望(那又会与两侧漂移)。`PARITY_CASES` 只放**输入**; 输出金标准 = **Python 侧 `normalize_legacy_rule` 真身输出**, JS 侧追平。这样任何一侧改语义对拍必红, 且红时能直接看到两边的实际 JSON 差异, 而不是"不匹配某个我手写的字面量"。
- **输入形态对齐真实载入链**: spec 全部用 YAML BaseLoader 载入后的形态(**所有标量是字符串**) —— 正好顺带钉住 `pitfalls/testing/config-validation-test-input.md` 里那条坑(用 python int/bool 写的测试输入过不了真实载入链)。这也是 `mixed_full_on_error` 里 `"retries": "5"` 写字符串而非 `5` 的原因。
- **覆盖清单按语义分桶,而不是按函数**: 扁平动作 / 混合形(全子键、缺子键、空 on_error)/ 规范形(带与不带 on_error)/ 退役伪动作(扁平与规范两形, 二者都应**不注入** on_error)/ choose(扁平 when、树形 when、未知键透传、非法分支形状、非 list 与缺失)/ 非法动作形状(标量、多键无 type、纯 on_error、数字)/ 条件(扁平、树形、叶子、非法、空表)/ 命名透传 / 无 conditions 无 actions / 空 spec。
- **`cfgRaw(["config"])` 的路径无关性**: `cfgNormalizeRulesDraft` 只读 `cfgRaw(["config"])` 下的所有 `*_rules` 分组, 与 schema/pluginIndex 无关, 所以 node 电池只需给 `cfg.tree.config.<某分组名>` 装 case 字典即可(bucket 直接放进 case 里, 每例独立 ctx, 互不污染), 不必重放真实分组名。
- 无 node 机器: 与 `test_webui_static_dom_page_layout.py` 的 node 探针同口径(**不引入 pytest skip**), 只跑 Python 侧基线 + 守"镜像在场/清单非空" —— 反恒真(禁把空清单/镜像被删伪装成绿)。
- 红验需**双向**: 只做单边(改 JS)只能证明"JS 不对齐时红", 证明不了"PY 变了也让 JS 判红"。本次实际做了 JS 侧 `backoff 60→99` 与 PY 侧 `backoff 60→45` 两次注入,均红并打印差异, 已还原。

## 实现计划

1. 新建 `tests/config_normalize_parity_support.py`: `PARITY_CASES`(输入清单) + `python_normalize`(金标准) + `cases_json()` + `_NODE_PARITY_PROBE`(node 电池, 跑 `cfgNormalizeRulesDraft` 后 dump)。
2. 新建 `tests/test_webui_config_normalize_parity.py`: 三个用例 —— Python 侧幂等 + 输入不被就地改写 / Python 侧金标准确有判别力(扁平确实被翻译、choose 键面确实保留、条件确实包 all)/ 跨语言逐例比对(无 node 只守进场)。
3. `commands run dev.fmt` 两个新文件 → 对拍用例单跑绿。
4. 红验(注入 JS 漂移 → 红 → 还原)+ 反向对照(注入 PY 漂移 → 红 → 还原)。
5. `commands run test.full` → 新建基线切片记实测数字。
6. issue HTML 置 Done + 状态变更日志追加; 档案补 `**Refs:**`; `kb.index` 重建。

## 子任务状态表

| 步 | 内容 | 状态 |
|---|---|---|
| 1 | 共享 fixtures + node 电池(`tests/config_normalize_parity_support.py`) | Done(2026-11-04) |
| 2 | 跨语言对拍守卫(`tests/test_webui_config_normalize_parity.py`) | Done(2026-11-04) |
| 3 | `dev.fmt` 格式化 + 单跑绿(3 passed) | Done(2026-11-04) |
| 4 | 红验 + 反向对照(两次注入均红, 已还原) | Done(2026-11-04) |
| 5 | `test.full` 全量绿 + 基线切片 | Done(2026-11-04) |
| 6 | issue 置 Done + 认领链回写 + `kb.index` | Done(2026-11-04) |

## 进度日志

### R0 · 立档 (2026-11-04)

- 2026-11-04: 认领 issue `26-11-03-1120-test-webui-config-normalize-parity-gap`(test/light) 并修复。
  - 新件: `tests/config_normalize_parity_support.py`(`PARITY_CASES` 共 24 例输入 + `python_normalize` 金标准 + `_NODE_PARITY_PROBE`)、`tests/test_webui_config_normalize_parity.py`(3 个用例)。
  - 口径: 期望只写一份 = **Python 侧真身输出**; JS 侧追平。谁改语义谁红, 红时逐例打印 `JS = ...` / `PY = ...`。
  - 红验: JS 缺省 `backoff` 60→99 → `test_js_python_parity` 红(多例差异); PY `ON_ERROR_DEFAULTS` 60→45 → `test_python_side_effective` + `test_js_python_parity` 双红。两次均已还原, 工作树只余两个新文件。
  - 全量: 见 `commands run kb.baseline`(最新切片)。
  - issue 状态 Open → Done, 状态变更日志留痕。

- 2026-11-04 05:07 跨语言对拍守卫落地(3用例/24例输入)+双向红验; 顺带入池 DOM 电池疑空转 26-11-04-0504
