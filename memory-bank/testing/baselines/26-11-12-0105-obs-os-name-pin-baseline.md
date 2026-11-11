# 6060 passed, 2 skipped —— recycle 观测一致性测试双平台钉桩后全量基线

> 摘要: recycle 观测一致性测试双平台钉桩后全量基线
> 基线时间: 2026-11-12 01:05

## 验收数字

```text
TOTAL                                                27073     65   9460     68    99%
6060 passed, 2 skipped in 147.80s (0:02:27)
```

(实测时点: 2026-11-12 第 4 轮评审零 actionable 后 `commands run test.full`, 覆盖率 99%(门槛 99%); 较上片 6008: +52 = 中途入库的 recycle daemon W1a/W1b/W2a/W2b 观测面及其它批次净增用例, 2 skipped 为存量 skip 不变; 本切片为本批组合树的测试数字权威, 其余处一律引用不手抄。)

## 本改动面

- `tests/test_recycle_daemon.py`: `test_observe_owner_injected_map_matches_self_fetch` 自取路径两平台分派支在任一平台都跑 —— nt 支补 `monkeypatch.setattr(rd.os, "name", "nt")` 钉住(原只桩 netstat 输出, Linux CI 上经真实 os.name 走 proc 分派真读 /proc 必挂, 即 GitHub CI 连续 4 笔红的根因), proc 支钉 `os.name="posix"` + `_stub_proc_open` 造 `/proc/net/tcp`(8081 LISTENING, inode 111)+ `/proc/100/fd/3 -> socket:[111]`, 两支各断言同一 owner 记录; proc 支回毒 `subprocess.run` 钉不起子进程; 测试 docstring 与文件头「测试计划」清单同步「两支各 os.name 桩钉住」。
- `memory-bank/issues/26-11-12-0053-chore-linux-ci-timeout-py-download.html`: 新入池(计划外发现, Open)—— test.linux 包装超时 900s 不足 + 3.12 镜像 uv 补下载托管 CPython 走 github 容器内不通; 临时绕法与正修方向已记录。
- 附带验证(不入基线口径): Linux 容器复现(3.13 镜像直跑 linux_ci.py) recycle_daemon 面全过, 全量 5978 passed / 61 failed —— 61 失败全为 `test_webui_static_r4_*` node 电池在无 node 容器里的既有环境缺口(GitHub runner 预装 node 不红), 与本批无关。

