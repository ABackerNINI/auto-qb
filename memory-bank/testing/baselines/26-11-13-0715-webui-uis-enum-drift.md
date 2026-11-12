# 6084 —— 6084 passed + 19 skipped —— test.full 基线: UIS 枚举收编 _UI_ALL 单点批(测试面仅改名, 零新增用例)

> 摘要: 6084 passed + 19 skipped —— test.full 基线: UIS 枚举收编 _UI_ALL 单点批(测试面仅改名, 零新增用例)
> 基线时间: 2026-11-13 07:15

## 验收数字

实测(2026-11-13, clone2 本机, develop@36f030b1 + 未提交批(UIS 收编单点), `PATH=$HOME/.local/node/bin:$PATH` 前置、无 TZ 前置):

```text
TOTAL                                                27113     219   9480     89    99%
6084 passed, 19 skipped in 122.13s (0:02:02)
```

差值口径: 较上条基线(26-11-13-0629: 6081+19, clone1 实测) +3 passed。本批测试面**零新增用例**(仅 `test_mount_pairing_three_shells` 改名 `test_mount_pairing_all_shells` + 断言消息文案), 其中 +1 = 36f030b1(TZ 批)新守阵用例 `test_dst_free_tz_pinned_for_wallclock_asserts` 在 0629 快照时点尚未入库; 余 +2 与跨 clone 环境差异相关(clone1 vs clone2, 0629 注记的 flaky 守阵扩面收集面差异带内), 零回归。

## 本改动面

- **`tests/web_shortcuts_support.py`**: 删除旧三皮肤枚举 `UIS = ("atlas", "prism", "console")`, 原位留注记指向 `webui_helpers._UI_ALL` 单点(issue 26-11-13-0443)。
- **`tests/test_web_shortcuts_registry.py` / `tests/test_web_shortcuts_cursor.py` / `tests/test_web_shortcuts_drawer.py` 三消费方接线**: `from webui_helpers import _UI_ALL` 直连; 三处 `for ui in UIS` → `for ui in _UI_ALL`(flux 第四皮肤自此进守阵循环)。
- **测试改名与文案如实更新**: `test_mount_pairing_three_shells` → `test_mount_pairing_all_shells`(registry 头部测试计划条目同步); registry/cursor/drawer 头部导语「三份 tpl-manifest」→「全部皮肤(webui_helpers._UI_ALL)的 tpl-manifest」; cursor/drawer 受影响循环周边「三皮肤」→「四皮肤」(含 drawer:859 断言消息)。
- **文档面**: issue 26-11-13-0443 翻 Done(kb.status 两处一致 + 正文补实际修法/验证); 立档 `memory-bank/tasks/26-11-13-webui-uis-enum-drift.md`(阈值命中: 改动 ≥3 源文件)双向补链; 坑档 `pitfalls/testing/env3-test-run-prereqs.md` 复发+1(闸门预跑裸跑踩 node PATH 前置) + `kb.index` 再生; 本基线切片 + 会话切片(kb.wrap)随批入库。
