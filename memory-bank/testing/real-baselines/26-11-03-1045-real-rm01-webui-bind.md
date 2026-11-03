# 1 passed + 8 deselected —— RM01-06 端口被占: 启动期 fail-fast 干净退出

> 摘要: 真机实测轨 RM01 单条复测 —— 端口被占时 WebUI bind 失败无条件 fail-fast: 退出码 1、ERROR 行与诊断块含 web.port/web.enabled、state.lock 与 meta 已释放、占位 socket 仍持有端口
> 基线时间: 2026-11-03 10:45
> 基线 commit: 2f61ce98(实测时刻 HEAD; 判据改动在工作树)
**Refs:** memory-bank/testing/baselines/26-11-03-1112-webui-bind-fail-fast.md

## 01 验收数字

`commands run real.run --case RM01-06 --yes`(2026-11-03 10:44, Windows, `-n 0`):

```text
1 passed, 8 deselected in 14.67s
```

- 两条进程路径都覆盖: `app.start`(`p.wait(90)` 得 rc=1) + `app.run_cli`(收 stderr 单行)。
- 首跑前环境未设 `QBT_TEST_36595`, 片内 `environment` fixture 因 403 跳过整片(见 §03); 注入测试实例自身 APIKey 后复跑, token 未落盘。

| 判据 | 实测 |
|---|---|
| 退出码 | **1**(两条路径一致) |
| 日志 KEY 行 | `WEB UI 启动失败: localhost:7162 无法监听(端口被占用? 详见上方 uvicorn 错误)` |
| 诊断块 | `WEB UI 启动失败诊断 (web.enabled=true, web.host=127.0.0.1, web.port=7162)` · `原因: [WinError 10048] ...` · `处置: 改 web.port ... web.enabled: false` · `退出: 启动期 fail-fast, 退出码 1, 采集不会启动` |
| stderr | `WebUI 启动失败: 127.0.0.1:7162 无法监听 (web.enabled=true, ... web.port=7162); ... 退出码 1` |
| 锁 | `state.lock.meta.json` 不存在; 原位重取 `SingleInstanceLock` 成功(未被持有); 本次实测 `state.lock` 文件未残留 |
| 端口 | 占位 socket 仍可 `listen`; `app.port_free(7162)` 为 False(仍被占) |

## 02 本改动面

- `tests-real/rm01_startup/test_rm01_startup.py::test_rm01_06_port_taken_reports_failure_not_silent`: 场景不变(先占端口、`web.enabled=true`), 判据由「进程活着 = 绿」翻面为「rc=1 + 可操作诊断 + 锁释放」; docstring 失败判据同步改写。
- 未改 `src/`、`tests-real/lib/app.py`、`conftest.py`、覆盖率阈值; 未改写旧切片 `26-10-31-0831-real-RM01.md`。

## 03 排障与前提

- 当前环境(环境1/D盘机)两个 testing 实例在监听, 但 `QBT_TEST_36595` 未设 / `instances.local.json` 不存在 ⇒ 片内 `environment` fixture 对主实例 `/app/version` 收 403, 整片 `1 skipped`。本轮单条复测以测试实例自身 `WebUI\APIKey` 注入 `QBT_TEST_36595` 后复跑; token 未落盘、未写进仓库。
- 未误杀无关进程; 占位 socket 由用例自己创建、自己关闭。

## 04 结论

- RM01-06 判据反转后真机绿: A 路线(fail-fast、退出码 1、锁释放)在真实进程边界成立。
- 历史切片 `26-10-31-0831-real-RM01.md` 的「不退出不装死」记录是当时事实, 不改写; 新口径以本片为准。
