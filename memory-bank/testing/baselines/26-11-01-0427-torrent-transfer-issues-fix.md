# 4365 passed + 2 skipped —— 转移三连修复回归: 409 探针查重兜底 / 目标 api_key 鉴权 / path_map 分隔符归一化

> 摘要: 计划 26-10-31-0306 真机验收入池的转移 issue 三连修复后全量回归快照 —— 409 无文案重复改判跳过、目标支持 api_key 鉴权(后端+前端)、path_map 分隔符归一化
> 基线时间: 2026-11-01 04:27
**Refs:**

## 验收数字

`commands run test.full` (187.16s, 2026-11-01 实测):

```text
4365 passed, 2 skipped (共 4367 条) in 187.16s
coverage: 99% (21840 stmts / 144 miss)
```

口径: 全量 pytest 含覆盖率报表; 相对上基线逐位对比不写, 看差值 `commands run kb.baseline -n 2`。
skipped 为环境口径跳过(本轮 2 条, 与近期切片同环境)。

## 本改动面

- `src/auto_qb/transfer/adapters/qb.py` + `tests/test_transfer_adapters.py`（issue 26-11-01-0334-bug, commit f556b11f）: 409 无文案重复添加补探针查重兜底 —— 抽共享 helper `_probe_duplicate`, Mapping 分支 `_interpret_result` 与异常分支 `_result_from_exception` 都改走它; 409 且文案命中 needle → skipped, 无文案(qB 5.2 形态 body 仅 b'Conflict')→ 探针 `_hash_exists` 查得同 hash → skipped「目标已存在」, 查不到才 failed; 模块 docstring「已存在判定」补第 3 条路; 新增 2 用例(无文案 409 + 查得/查无), 全 mock 不联网。
- `src/auto_qb/config/{models,loaders,validation/sections,schema/groups}.py` + `src/auto_qb/config/writer.py` + `src/auto_qb/transfer/adapters/qb.py`（issue 26-11-01-0335-feat 后端, commit 26cdbe48）: `TransferTargetConfig` 加 `api_key` 字段, 装载/校验键集 `KNOWN_TRANSFER_TARGET_KEYS`/schema help 同步; `_build_client` 照 `qbclient.new_client` 口径透传 `api_key=... or None`(空串=未配置); `writer.py` 目标掩码/还原扩为 `TARGET_SECRET_KEYS=(password, api_key)`, 还原逐键只回填仍为哨兵的键(防新键经 GET /api/config 明文泄漏); 新增单测 4 条(配置装载/adapter 透传/空串映射/掩码还原双向)。
- `src/auto_qb/webui/static/shared/tpl/transfer-targets.html` + `shared/transfer_targets.js`（issue 26-11-01-0335-feat 前端, commit 88a6aceb）: 目标编辑器密码字段后新增 API Key 输入框(隐藏 username 形状 + autocomplete=new-password + 非焦点不写树, 复用密码哨兵遮显机制); `ttSecret`/`ttHasSecret`/`ttSecretPlaceholder` 泛化为按键参(缺省 password); 守阵 `test_transfer_targets_editor.py` 补 3 处对账(非焦点不写树/显式指键/禁回显)。
- `src/auto_qb/transfer/orchestrator.py` + `src/auto_qb/webui/static/shared/transfer_flow.js`（issue 26-11-01-0334-feat, commit f731de07, 已随修复自行落 Done）: path_map 比对加分隔符归一化 —— 后端 `_path_sep_norm`/前端 `trSepNorm` 在反斜杠→正斜杠保长归一空间做前缀比对, 命中后对原串替换; 后端纯函数直测 6 条 + 前端守阵用例 8→10 组。
