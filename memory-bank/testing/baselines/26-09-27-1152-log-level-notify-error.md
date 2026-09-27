# 1685 passed + 1 skipped / 2 failed(既有) —— 日志等级整改: 危险归 ERROR, 通知默认只推 ERROR

> 摘要: 等级语义收窄定案(计划 26-09-27-1126 表 0): WARNING=纯排障(可自愈降级/重试中/保护性动作),
> ERROR=真正危险(数据丢失/写盘失败/停摆需人工/认证失败/未预期); `notify.min_level` 默认
> WARNING→ERROR(models.py/groups.py/notify.py fallback 三处), 弹窗测试判别口诀进 code-style.md。
> 表 A 升 20 处、表 B 降 13 处、表 D 反向 1 处; 三个 caplog 守阵翻转 + 新增 2 个默认值用例。
> 2 failed 为**既有** docs 守阵红(旧计划缺 meta, HEAD 上复验同红), 与本轮无关, 已入池。
> 基线时间: 2026-09-27 11:52
> 档案: 26-09-27-backend-log-levels-notify

- **测试增量**: 总数 1685→1685+2 新增 = `test_notify_default_min_level_is_error`(默认配置下
  INFO/WARNING 不通知、ERROR 派发)与 `test_notify_min_level_default_is_error`(未配置时默认
  ERROR); 守阵翻转: `test_checking_full_checking_send_error`(patch logger.warning→error)、
  `test_load_state_corrupt_without_backup_warns`(「备份也不可用」断言 WARNING→ERROR)、
  `test_match_tracker_conf_multi_match_error_log`→`_warning_log`(表 D1 反向, 断言翻转)。

TOTAL 91%(11206 语句 / 815 未覆盖 / 3720 分支 / 330 partial; test.full 19.3s, 1 采样;
覆盖率口径见 [../baseline.md](../baseline.md))。
