# 6543 passed + 6 skipped(根) —— transfer 验证异步化 S5 守阵收口全量基线

> 摘要: transfer 验证异步化 S5 守阵收口全量基线
> 基线时间: 2026-11-20 06:38

## 验收数字

TOTAL                                                29231     62  10424     72    99%
6543 passed, 6 skipped, 7 warnings in 162.83s (0:02:42)

`commands run test.full` 实测(2026-11-20 06:38, Windows 本机, 覆盖率 99% 达标)。较上批 6542 passed 差值 +1 = S5 新守阵用例 test_web_stop_sequence_with_inflight_verify_does_not_block; 红验在案: stop 面临时变异成 join worker 当场红(10.7s 卡满闸超时), 摘除后复绿。

## 本改动面

- `tests/test_transfer_routes.py`: 新增守阵 test_web_stop_sequence_with_inflight_verify_does_not_block(S5 审计唯一缺口补面: web 停止序列整段(center.stop -> 订阅注销 -> 服务退出位)在慢目标在途验证钉住时秒级内完成; 在途结论照常回灌但回执不写、全程零删源)+ 文件头「## 测试计划」同步; 其余三面守阵(排队<500ms / 逐条回执 / 源不误删)经审计既有用例判别力成立, 零改动
