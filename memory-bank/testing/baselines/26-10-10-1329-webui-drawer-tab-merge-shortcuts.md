# 2887 —— 详情面板合并页签快捷键同步(Alt+1/2/3 三可见页签)基线

> 摘要: 用户报「标签合并后没有同步修改快捷键」—— 页签栏已收敛为 `[常规&内容][Tracker&用户](+流量)`, 而详情面板页签快捷键 Alt+1~5 仍是四页签映射(按下去不是预期那一页)。拍板「合并成功就 Alt+1/2/3, 未合并就 Alt+1/2/3/4/5」后修: 新增位次重排表 `KB_MERGE_TAB_REMAP` + 判据单点 `_kbMergeTabsOn`(读 `dtMergeTabsOn`, 与页签栏 `v-if` 同一 computed), `_kbDrawerTab` 内按位次重排(**先于**流量门控), 未合并五档原样; 帮助浮层/设置页文案经新增 `kbLabel` 随态改写。只改键盘 run 路径, 鼠标页签点击不受影响。
> 档案: memory-bank/activeContext/26-10-09-2226-webui-drawer-merge-tabs.md
> 基线时间: 2026-10-10 13:29

**Refs:** memory-bank/activeContext/26-10-09-2226-webui-drawer-merge-tabs.md,memory-bank/pitfalls/web-ui/kbd-tab-set-sync.md

## test.full 实测

- 分支: `develop`(会话开工 `my-commit-flow.sync` 快进 328ef158→f8952c6a; 工作树含本轮改动 + 回写件时实测)
- 命令: `commands run test.full`(Windows, 单次采样 —— 耗时口径见 [../baseline.md](../baseline.md)「必须带区间」)
- **实测 (Windows)**: **2887 passed + 4 skipped, 0 failed, 覆盖率 TOTAL 99%**
  (16568 语句 / 167 未覆盖 / 5716 分支 / 143 partial; 门槛 98% 达标; 26.86s)
- 与上基线的差值: `commands run kb.baseline -n 2` 现列(切片正文只写自己的 TOTAL)。
- 增量明细: passed +1 = 新增守阵 `test_web_shortcuts.py::test_drawer_tab_shortcuts_merge_remap`(既有抽屉页签/流量门控守阵为断言面**未变**, 逐条保持通过)。语句/分支数与上基线逐位持平 —— 本轮 `src/` 只改前端静态 JS(不进 `--cov=src` 统计)。
- e2e 实测: `drawer-merge.spec.mjs` **6 passed**(原 4 + 新增「合并态快捷键」用例, 双皮肤 atlas/prism; 真按键 Alt+1/2 切两合并页签对、Alt+4 停用零变化)。

## 本轮改动面

- `shared/shortcuts.js` —— 新增 `KB_MERGE_TAB_REMAP`(位次表) + 方法 `_kbMergeTabsOn` / `kbLabel`; `_kbDrawerTab` 顶部插合并态重排(先于流量门控); 头部注释同步。
- `shared/tpl/popovers.html` / `shared/tpl/settings-detail.html` —— 快捷键条目文案 `{{ it.label }}` → `{{ kbLabel(it) }}`。
- 守阵 `tests/test_web_shortcuts.py`(新增 `test_drawer_tab_shortcuts_merge_remap` + 头部测试计划清单同步); e2e `e2e/drawer-merge.spec.mjs`(新增合并态快捷键用例)。
- 知识库回写: `modules/webui-static-contract.md` + `progress/implemented-webui.md` + activeContext 切片 R4 段 + 坑档 `pitfalls/web-ui/kbd-tab-set-sync.md`(新增) + 本切片。
- `src/` 后端零改动。Linux(WSL 沙箱)侧未重测 —— 本轮只改平台无关的前端静态 JS 与断言面(口径见 baseline.md 常驻警告; 与近几轮切片同处理)。

## 守卫收口

- `kb.check` 全绿(主键 558 文档 · 290 专题 / 认领链闭环 / 回写措辞 / 日期) / `doc.caps` 无阻塞项无 cap 债务。
