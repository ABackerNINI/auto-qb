# 同 clone 并行跑两条 uv 测试任务撞构建文件锁

> 摘要: 同 clone 并行跑两条 uv 测试任务(如 test.gtm + test.quick)时, 后到者 uv 构建子包失败 os error 32 —— 串行重跑即绿, 不是代码问题
> 触发: 并行跑测试, os error 32, 文件被占用, Failed to build, uv, test.gtm, test.quick, 另一个程序正在使用此文件
**Refs:** memory-bank/tasks/26-11-03-backend-gtm-day-total-inflation.md

### 同 clone 并行两条 uv 测试命令 → 后到者构建失败「os error 32」

- **触发**: 同一个 clone 里同时跑两条各自走 `uv run` 的测试任务(实例: 后台 `test.quick` 进行中又前台跑 `test.gtm`)—— 两条都要构建 `tools/global-traffic-monitor` 子包, uv 的构建临时目录/产物文件被先到进程持有。
- **判别**: `[FAIL] test.gtm` 且输出为 `error: Failed to build 'global-traffic-monitor @ file:///...'` + `cause: 另一个程序正在使用此文件, 进程无法访问。 (os error 32)` —— 报错形态像环境坏了, 实际与代码无关(2026-11-03 评审轮实测: 首跑即失败, 等另一条跑完重跑立即绿)。
- **处置**: 不要在同 clone 并行跑两条 uv 测试命令 —— 串行执行; 已经撞上就等另一条结束后原样重跑。评审/验证场景用后台任务跑一条时, 另一条等完成通知再发。
