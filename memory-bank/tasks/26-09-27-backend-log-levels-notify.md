# 26-09-27-backend-log-levels-notify — 日志等级整改: 危险情况归 ERROR, 通知默认只推 ERROR

**Status:** Done
**Added:** 2026-09-27
**Updated:** 2026-09-27
**Summary:** 等级语义收窄定案(WARNING=纯排障/ERROR=真正危险), 表 A 升 20 处 ERROR、表 B 降 13 处 INFO、表 D 反向 1 处, notify.min_level 默认 WARNING→ERROR; test.full 1685 passed(2 failed 为既有 docs 守阵, 已入池)。
**Topics:** log-level-notify-error

## 原始请求

「将真正的危险情况的 log 等级调为 ERROR, 桌面通知默认 ERROR 级, WARNING 级仅排障, 先写一个计划, 列出详细的表」→ 计划批准后「开工」。

## 思考过程与决策

- 计划单点: [plans/26-09-27-1126-plan-log-level-notify-error.html](../plans/26-09-27-1126-plan-log-level-notify-error.html)(表 0 等级口径 / 表 A–D 全量 88 处 WARNING + 16 处 ERROR 逐条定级 / 表 1 配置改动 / 表 2 守阵影响 / 表 4 风险)。
- 根因: 通知链路 100% 依赖日志等级(NotifyHandler 拦截 `auto_qb` logger), 原口径「WARNING=回退/风险/数据异常」过宽 + min_level 默认 WARNING ⇒ 设计内动作/操作审计全部弹窗, 真危险被淹没。
- 约定先行(P1): 先改 `conventions/code-style.md`「日志规范」等级语义与 `pitfalls/ops/alert-levels.md` 判据①, 再动代码 —— 代码与守阵才有裁决依据。
- 两个「危险感」但不升级的决定: `skip_checking.py:102`(设计内高风险动作, 每种子触发, 升 ERROR 会高频刷屏)与 `webui/server/auth.py:68`(浏览器错配常见)留 WARNING; `hr/server.py:206` 鉴权失败因白名单内低频升 ERROR。
- A6(`rules/base.py:252`)实施前核对了 `result.is_failed` 分支: skip 走 DEBUG、pending 走等待路径, failed 是真失败 ⇒ 升级成立。

## 实现计划

P1 约定先行 → P2 通知默认值(models/groups/notify 三处) → P3 表 A 20 处升级 + 表 B 13 处降级 + 表 D 1 处反向 → P4 守阵同步 + 新增 2 个默认值用例 → P5 回写 + test.full 基线。

## 子任务状态表

| 子任务 | 状态 |
|---|---|
| P1 等级语义约定改写(code-style.md + alert-levels.md) | ✅ |
| P2 notify.min_level 默认 ERROR(models.py:217 / groups.py / notify.py:213) | ✅ |
| P3 表 A 升级 ERROR 20 处 | ✅ |
| P3 表 B 降级 INFO 13 处 | ✅ |
| P3 表 D tracker.py:32 ERROR→WARNING | ✅ |
| P4 守阵同步(test_checking/test_rule_engine/test_tracker) + 新增用例(test_notify/test_config) | ✅ |
| P5 回写 keys.md / productContext.md / README | ✅ |
| P5 test.full 基线切片 | ✅ |
| 既有缺陷入池(docs_forms 守阵红) | ✅ |

## 进度日志

- **2026-09-27 会话**(plan 1126 → 实施完成):
  - P2: `NotifyConfig.min_level` 默认 `"WARNING"`→`"ERROR"` + docstring 同步; WebUI schema 默认与 help 文案同步; NotifyHandler fallback 常量对齐; `webui/server/common.py:60` 过时注释更新。`NOTIFY_LEVELS` 与 urgent 判据(`>=ERROR`)不变。
  - P3: 34 处改级全部按计划表 A/B/D 执行, 只换等级常量不动消息文本; 另发现 `common.py` 注释漂移一并修正(计划内)。
  - P4: 三个 caplog 守阵按新等级翻转(`test_checking_full_checking_send_error` patch warning→error; `test_load_state_corrupt_without_backup_warns` 拆 warning/error 双断言; `test_match_tracker_conf_multi_match_error_log` 改名 `_warning_log` 并翻转断言); 新增 `test_notify_default_min_level_is_error` 与 `test_notify_min_level_default_is_error`; 两文件头部「## 测试计划」同步。
  - P5: README 桌面通知节 / `config-reference/keys.md` / `productContext.md` 回写; 基线切片 `testing/baselines/26-09-27-1152-log-level-notify-error.md`。
  - 实测: test.full **1685 passed + 1 skipped / 2 failed**, 覆盖率 91%(11206 语句 / 815 未覆盖 / 3720 分支 / 330 partial), 19.3s。2 failed 均为**既有**失败(`26-09-26-2345` 旧计划缺 doc-status/doc-topic/doc-added/doc-updated → `test_docs_forms` 两条守阵红; 已在 HEAD 上复验与本轮无关), 入池 issue。
  - ⚠ 遗留: 用户生产 `config.yml` 的 `notify.min_level: WARNING` 是红线, AI 不动 —— **需用户手改成 ERROR**, 否则默认值改动在该环境不生效。
- **2026-09-27 同步远端**(用户指令): ff 合并远端 `6fd1331`(前端模板拆分 / web 日志采集自足化 / **26-09-26-2345 旧计划 meta 修复**)。入池 issue 26-09-27-1153 随之失效 → 置 **Done**(本地复验 test_docs_forms 34 passed 全绿)。合并后新基线 **1688 passed + 1 skipped / 0 failed**(91%, 切片 26-09-27-1208)。流程: 备份 `.git` → stash 移出改动 → `--ff-only` → stash pop(仅两个生成物 `_doc-map`/`plans/_index` 冲突, 取远端版重跑 `kb.index` 解决)。
