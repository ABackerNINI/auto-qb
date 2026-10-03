# 基线切片 26-10-04-0150 — 添加种子三浮层互斥补双向(closeAddPopsExcept 单点)

> 摘要: issue 26-10-04-0130 认领, 按建议方向二实施。互斥矩阵原单向(openAddPathPop 收
> cat/tag, 反向不收), 路径面板与下拉可同悬且面板盖住相邻字段 label 的点击。修法 = 抽
> `closeAddPopsExcept(kind)` 单点, 三开层各调一次; 守阵补第 6 组互斥双向静态断言。

- 时间: 2026-10-04 01:50 (GMT+8); 合并远端 4805f5f5 后于新基线重测(会话起点 sync 至 594e247f)
- 分支: develop @ (本轮回写件, 随主提交一并入库)
- 命令: `commands run test.full`
- 实测: **2419 passed + 3 skipped, 32.46s, 覆盖率 99%** (134 miss / 105 partial; 合流前 2418,
  多 1 条为远端 20b13a66 的新守阵; 提交闸门前重测)
- 真浏览器走查(Playwright + scripts/ui_harness.py 桩后端, DOM 判浮层显隐, focus 模拟
  Tab 焦点迁移避开几何拦截): **6/6 通过** —— 路径开→focus 分类(path 收/cat 开)、分类开→
  focus 标签、标签开→focus 路径(修复前反向缺口: tag 不收)、分类开→点标签 label 转发、
  分类开→Tab 到标签, 终态全部单浮层; T1 前置确认路径面板可正常打开。
  走查中还实测复现了 issue 记录的拦截现象(修复路径下用 click 迁移焦点会被
  `pop-item ... subtree intercepts pointer events` 拦截直至超时 —— 与取证一致, 属面板
  几何覆盖, 焦点迁移路径不受影响)。
- 改动面:
  - `src/auto_qb/webui/static/shared/add_torrent.js` — 新增 `closeAddPopsExcept(kind)`
    三浮层互斥单点(收层带 Hi 复位), openAddCatMenu/openAddTagMenu/openAddPathPop 三处
    开层各调一次, 各自保留 Hi 复位与悬停门限坐标复位
  - `tests/test_web.py` — test_frontend_add_combo_blur_close_and_fit 补第 6 组「互斥双向」
    静态断言(单点存在 + 三分支覆盖 + 三开层各调一次) + 文件头测试计划同步
  - `memory-bank/issues/26-10-04-0130-bug-webui-add-pop-mutex.html` — 状态 Open→Done
    (复验仍复现 + 修复后补充 + 状态日志两行) + `issues/_index.md` 重建
- 未验证面: 真机(真实 qB + 真实数据)走查仍待用户执行
