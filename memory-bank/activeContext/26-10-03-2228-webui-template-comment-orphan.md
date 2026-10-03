# WEBUI 分片注释孤儿修复(设置页冒出注释文字)

> 摘要: 用户报 WEBUI 设置页出现一段中文注释文字 `... 卡内可手动刷新 -->`。根因 = W1 模板分片
> (commit `6fd133147`)切割时把「统计面板(FE-2C)」注释的**开头一行**丢了, 聚合里只剩孤儿 `-->`,
> boot.js 拼串注入后成文字节点, 任何视图都渲染。补回开头行即修。
> 最后活动: 2026-10-03 22:28

## 已完成 (2026-10-03)

- **修复**: [shared/tpl/dialogs.html](../../src/auto_qb/webui/static/shared/tpl/dialogs.html#L1-L2) 第 1-2 行补回开头
  `<!-- 统计面板(FE-2C): /api/stats server_state 直取(缺失显示 —); server 为 null 时空态。` ——
  原文从分片前 `git show 6fd133147^:src/auto_qb/webui/static/prism/index.html` 取回。src 仅此一行改动。
- **排查**: `dialogs-mgr.html:1` 的 `-->` **非孤儿**(其 `<!--` 在 dialogs.html 尾部, 添加种子对话框
  注释跨分片边界, 聚合后配平), 未动; 全静态目录仅此一处真孤儿。
- **守阵**: `tests/test_web.py` 272 passed + 1 skipped(单文件跑, 覆盖率闸门无意义); 全量
  test.full **2416 passed + 3 skipped / 99%**。
- **基线**: [baselines/26-10-03-2228-webui-template-comment-orphan.md](../testing/baselines/26-10-03-2228-webui-template-comment-orphan.md)。
- **新坑**: [pitfalls/web-ui/tpl-comment-split-orphan.md](../pitfalls/web-ui/tpl-comment-split-orphan.md)。
- 不满足立档阈值(单文件单行修复, 一条主线); issue 未入池(用户当轮直接报障)。

## 状态

修复与收尾完成, 待用户『提交』统一入库。