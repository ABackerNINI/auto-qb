# 5459 passed + 10 skipped —— qbclient._session 注解对齐与 override 豁免摘除全量基线

> 摘要: qbclient._session 注解对齐与 override 豁免摘除全量基线
> 基线时间: 2026-11-06 06:14

## 验收数字

- 汇总行: **5459 passed + 10 skipped** in 139.99s(0:02:19, xdist 并行, TMPDIR 由 tests/_tmp_bootstrap.py 自举); 命令整体 142.2s, 1 warning。
- 覆盖率 TOTAL 表末行: **TOTAL 24538 stmts / 74 miss / 8396 branch / 41 partial / 99%**(Windows 侧覆盖闸 99.0, PASS)。
- 口径注记: 本轮零新增用例、产品运行期行为零改动; 数字为当前树实测(开工快进 2 笔后的远端合流面), 与上基线的差值对比走 `commands run kb.baseline -n 2`。
- 静态类型面: `commands run dev.typecheck` 全库 `Success: no issues found in 195 source files`(退出码 0), 独立于 pytest 闸门(D3)。

## 本改动面

- issue 26-11-06-0247 清偿: `src/auto_qb/core/qbclient.py` 的 `_session` 返回注解 `requests.Session` → `QbittorrentSession`(`from qbittorrentapi.request import QbittorrentSession`), 删 `import requests`, 补 3 行 why 注释; 覆盖体与 `trust_env=False` 运行期语义零改动。
- `pyproject.toml` ⑤ `[[tool.mypy.overrides]] module = ["auto_qb.core.qbclient"] / disable_error_code = ["override"]` 整块摘除, 原位留一行递减说明; `tests/test_mypy_allowlist_guard.py` 冻结清单保留 ⑤ 作为 2026-11-06 S4 基线(守阵语义「新增红/递减不红」), 守阵零改动。
- 复验与红绿: 摘豁免后 `dev.typecheck -- src/auto_qb/core/qbclient.py` 仍报 `[override]`(Superclass QbittorrentSession / Subclass Session); 改注解后全库零错; `dev.fmt` 通过。
- 收尾件: issue 报告两处状态 Open→In Progress→Done + 复验/实际修法留痕; 各生成物索引由 `kb.index` 重建; activeContext 切片走 `kb.wrap`; 主题文档(`core-runtime.md` / `techContext.md`)记录的是模块职责与行为, 本次仅注解变化, 未漂移, 故零回写。
- 真机自检不命中: 纯类型注解修复, 运行期行为零变化, 不落入真机轨两类准入(qB 真执行 / 真文件系统·进程·注册表); mypy 全库零错 + 全量桩测试全绿即可判定, 桩保真度足以支撑结论。
- 收口评审不触发(立档阈值不命中: 单会话、1 轮指令、2 个文件); 未立任务档案; 本轮无提交动作。
