# 通用 CI 环境变量不能用来区分 GitHub Actions 与本地开发机

> 摘要: 通用 CI 变量在本仓库开发机入口常态为真, 拿它判「是否 CI」会让本地严格档永不生效(假绿)
> 触发: CI, GITHUB_ACTIONS, 环境变量判档, 阈值分档, dev.e2e, playwright, 严格档失效, 假绿, 回归检测力, 性能基准

## 本篇只回答

想按「CI / 本地」分档(阈值、重试、timeout、开关)时该用哪个环境变量判档, 以及判错档为什么是**假绿**而非假红。

### 用通用 `CI` 变量判档 → 开发机常态置真, 严格档永不生效

- **触发**: 测试或配置里写 `os.environ.get("CI") == "true"` / `!!process.env.CI` 之类, 想据此在 CI 上放宽断言、加 retries、抬 timeout, 本地保持严格。本仓库的**开发机入口本身就会置真**: `.commands/dev/config.toml` 的 `dev.e2e` note 明记「本机 CI=true 故失败重试 1 次」, `playwright.config.mjs` 也拿 `!!process.env.CI` 做 `forbidOnly` / `retries`。2026-11-07 性能基准分档初版正是这么写的。
- **判别**: ①本地开发机跑目标用例, 打印/日志显示落在「CI 档」而非「本地档」(本例 `[5000-seed benchmark] ... limits=ci_threshold:1.0/20.0ms`); ②严格档阈值从此再没有任何一次执行会用到 —— 把严格档阈值改成任意小值用例仍全绿 ⇒ 守阵空转, 是**假绿**(放走真回归)不是假红, 单看 CI 全绿发现不了; ③工具 shell 与开发 shell 的 `CI` 取值不同 ⇒ 同一份代码两侧结论不一致。
- **处置**: 判据只用**平台专属**变量 `GITHUB_ACTIONS`(GitHub Actions 的 ubuntu / windows job 均保证设置), 通用 `CI` 不参与; 用 truthy 判定(`os.environ.get("GITHUB_ACTIONS")`)而非 `== "true"`, 与 `playwright.config.mjs` 的 `!!process.env.CI` 同款。分档逻辑抽成可测函数(`tests/test_modules_p5.py::_perf_limit_key`), 并加**参数化守阵**: 显式设定/清除 `GITHUB_ACTIONS`、同时恒设 `CI=true`, 断言两档选择与阈值大小关系。其它 CI 平台各用其专属变量, 不要回退到通用 `CI`。
- **守阵**: `tests/test_modules_p5.py::test_rebuild_benchmark_limit_profile_selection`(2 条参数化; 红验: 判据改回 `CI` 即 1 failed)。相关计时口径坑见 [timing-tolerance.md](timing-tolerance.md)。
- **复发**: 0 (复踩时在此行追加「+N (日期): 为什么没命中」, 无复发可删本行)
