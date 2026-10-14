# 3205 — notify↔tray icon 路径推导单点化(R19-A01)执行基线

**Refs:** memory-bank/activeContext/26-10-15-0412-notify-tray-icon-path-dup.md

> 摘要: 用户「认领并修复」`26-10-11-0352-refactor-notify-tray-icon-path-dup`(notify.ICON_ICO ↔ tray/app.ICON_ICO 两级 dirname 表达式逐字同)→ 按 issue 建议第二支落地: **infra/notify.py 的 ICON_ICO 成为包 assets 目录推导唯一处**, tray/app.py import 该常量、ICON_PNG 同目录派生; 表达式 3 处 → 1 处, 零行为变化。既有守阵 `test_notify_icon_ico_points_to_real_file` 继续生效。全量 3205 passed + 4 skipped / 98.64%。
> 基线时间: 2026-10-15 04:22

上一基线: memory-bank/testing/baselines/26-10-15-0321-test-delta-sync-full-round-flake.md

## 验收数字

- `test.full`: **3205 passed + 4 skipped, 0 failed** / 覆盖率 `TOTAL 16839 159 5728 142 99%`(98.64%, 过 98% 闸门)。
- 耗时: pytest 137.08s(单次采样, 全绿跑; 口径见 baseline.md)。
- 单文件前置跑: `test.one tests/test_notify.py` 27 passed(改完先跑守阵文件绿再收口)。
- Linux 侧未重测(改动为零行为变化收口, 无平台分支; 路径推导两侧同源 stdlib os.path)。

## 本波改动面

- **单点归属**: `src/auto_qb/infra/notify.py` ICON_ICO 注释升格为「包 assets 目录推导单点」说明(表达式字节不动)。
- **委托收口**: `src/auto_qb/tray/app.py` 删两行逐字同表达式, 改 `from ..infra.notify import ICON_ICO, WINDOWS_TOAST_APPID` + `ICON_PNG = os.path.join(os.path.dirname(ICON_ICO), "icon.png")`。
- **回写**: issue(Open → In Progress → Done, 两处徽标+meta, 状态日志含复验/实际修法/验证方式, doc-refs 认领链) + activeContext 切片新建(反向声明闭合) + 坑档 `pitfalls/kb/refs-rename.md` 复发 6(认领链创建顺序坑) + `kb.index` 重建 + 本基线切片。

## 已知偏差 / 移交

- 首轮 test.full 曾 1 failed(`test_docs_forms.py::test_claim_chain_is_bidirectional`): 认领时先回填 issue doc-refs、后建认领方切片, 悬空窗口被全量扫到; 切片落盘后单跑即绿、复跑全量全绿。教训已入坑档复发 6, 非本修复缺陷。
- 移交: dup-code-audit 池内其余 refactor issue 仍 Open 未动; 工作树另有一份先前会话遗留的未跟踪坑档(`pitfalls/git/rebase-continue-needs-clean-index.md`), 非本轮改动。
