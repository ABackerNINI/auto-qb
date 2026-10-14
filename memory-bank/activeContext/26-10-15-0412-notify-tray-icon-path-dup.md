# 认领并修复 notify↔tray icon 路径推导重复(R19-A01)

> 摘要: 用户指令「认领并修复 memory-bank/issues/26-10-11-0352-refactor-notify-tray-icon-path-dup.html」。复验仍复现(源码随包迁移到 src/auto_qb/ 后行号未变, notify:48 与 tray/app:31-32 两级 dirname 表达式逐字同)→ 按 issue 建议的第二支「notify 导出 ICON_ICO、tray 引用」落地: **infra/notify.py 的 ICON_ICO 成为包 assets 目录推导唯一处**, tray/app.py 改为 import 该常量(ICON_PNG 由同目录派生), 全仓两级 dirname 表达式 3 处 → 1 处, **零行为变化**(运行期探针: 两模块 ICON_ICO 字节同、指向真实文件)。改动 2 个源文件(notify / tray-app), 未新增测试——既有守阵 test_notify_icon_ico_points_to_real_file 继续钉「路径指向真实文件」, 且低于立档阈值(3 源文件)故未建任务档案。issue 状态流水 Open → In Progress → Done; 全量测试数字见基线切片 `memory-bank/testing/baselines/26-10-15-0423-notify-tray-icon-path-dup.md`。
> 最后活动: 2026-10-15 04:23

**Refs:** memory-bank/issues/26-10-11-0352-refactor-notify-tray-icon-path-dup.html,memory-bank/testing/baselines/26-10-15-0423-notify-tray-icon-path-dup.md

## 正在进行

- **修复已落地并收口**: issue 两处徽标 + meta 已置 Done, 状态日志含复验 / 实际修法 / 与建议改道原因 / 验证方式四段; 认领链双向闭合(issue.doc-refs → 本切片, 本切片 Refs → issue + 基线, 基线 Refs → 本切片)。

## 关键结论(供后续执行参考)

- **修法取舍**: issue 建议的两支(①infra.assets_dir() 新单点函数 ②notify 导出 ICON_ICO、tray 引用)选 **②** —— 少改一个源文件(不动 infra/utils.py), 表达式净收敛(3→1), 且 tray 本就已从 notify import(WINDOWS_TOAST_APPID), 依赖方向不变; 包目录移动时仍只需改 notify 一处。
- **ICON_PNG 的派生口径**: `os.path.dirname(ICON_ICO) + "icon.png"` —— 与 tray 原 ICON_PNG 字节同(运行期探针实证), 不引入第二个 dirname 口径。
- **零行为变化验证**: 运行期断言 `tray.ICON_ICO == notify.ICON_ICO` 且 `os.path.isfile` 为真; notify 测试文件全量先跑绿; 全量见基线切片。
- **退回成本**: 若将来 assets 目录需要参数化(如打包路径可配), 再升级为 `infra.assets_dir()` 函数单点(现无常驻配置入口, 提前抽函数属过度设计)。
- **流程教训(已入坑档 `pitfalls/kb/refs-rename.md` 复发 6)**: 认领链必须**先建认领方件、后回填 doc-refs** —— 本轮先填 issue doc-refs 后写切片, 悬空窗口被同期 test.full 扫红 1 条, 复跑才绿。
