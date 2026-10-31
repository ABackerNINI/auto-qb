# 2917 —— WEBUI 单种子"总上传"列表头改"已上传"基线

> 摘要: 用户要求「将单个种子的"总上传"字段改为"已上传", 组的不变」, 范围拍板 = 种子页 + 明细表 + 追剧视图(分组表保持"总上传")。实施 = `shared/app.js` 三处列模型(`DETAIL_COLUMNS`/`TORRENT_COLUMNS`/`SHOW_COLUMNS`)的 `uploaded` 列 label 由"总上传"改"已上传"; `GROUP_COLUMNS` 不动。列 key 与后端字段不变 ⇒ 无偏好迁移、无模板改动。
> 档案: memory-bank/activeContext/26-10-10-1436-webui-uploaded-column-label.md
> 基线时间: 2026-10-10 14:36

**Refs:** memory-bank/activeContext/26-10-10-1436-webui-uploaded-column-label.md

## test.full 实测

- 分支: `develop`(会话开工 `my-commit-flow.sync` 已同步 52af8c9a; 工作树含本轮改动 + 回写件时实测)
- 命令: `commands run test.full`(Windows, 单次采样 —— 耗时口径见 [../baseline.md](../baseline.md)「必须带区间」)
- **实测 (Windows)**: **2917 passed + 4 skipped, 0 failed, 覆盖率 TOTAL 99%**
  (16568 语句 / 167 未覆盖 / 5716 分支 / 142 partial; 门槛 98% 达标; 34.94s)
- 增量明细: 本轮只改前端静态 JS(`app.js` 列模型文案, 不进 `--cov=src`), 无新增/删除测试 ⇒ 守阵净变动 0。
- e2e 实测: `commands run dev.e2e` 全量集(桩服务自动起, 双皮肤 atlas/prism) —— **132 passed + 10 skipped, 0 failed**; 列文案相关用例(`column-prefs.spec.mjs` 的 `colToggle` 用分组表"总上传")未受影响。

## 本轮改动面

- `shared/app.js` —— `DETAIL_COLUMNS`/`TORRENT_COLUMNS`/`SHOW_COLUMNS` 的 `uploaded` 列 `label` 由"总上传"改"已上传"(各加一行口径注释); `GROUP_COLUMNS` 保持"总上传"。种子页列模型头部注释同步。
- `src/` 后端零改动; 模板值单元格分支 / 列选择器 / 右侧抽屉零改动(抽屉单种子字段本就叫"已上传")。
- 知识库回写: 本切片 + activeContext 切片。
