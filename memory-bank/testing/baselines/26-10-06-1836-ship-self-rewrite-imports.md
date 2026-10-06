# 2678 —— ship.commit 包脚本自我改写: 延迟 import 热刷新

> 摘要: 修 `ship.commit` 的一条自伤 —— 提交已落盘却在推送步抛
> `ImportError: cannot import name 'retry_note' from '_pipeline'`(退出码被误置 1)。根因 = **包脚本住在仓库里**,
> 本次内部同步把远端新版包脚本(`aaff8b3a`)rebase 进工作区, 而 `commit.py` 进程启动时已缓存旧 `_pipeline`;
> 延迟导入的**新** `push.py` 按缓存解析新名字 ⇒ 找不到。修法 = 新增 `_pipeline.refresh_package_modules()`
> (内容摘要门控 + `importlib.reload` 保身份), `commit.py` 推送步前调用。零 `src/` 改动 —— 改动全在
> `.commands/my-commit-flow/` 与 `memory-bank/`(两者都不在 `testpaths`), 故 `test.full` 数字与上一条**逐位相同**。
> 基线时间: 2026-10-06 18:36

**Refs:** memory-bank/tasks/26-10-06-ship-self-rewrite-imports.md, memory-bank/activeContext/26-10-06-1836-ship-self-rewrite-imports.md

- 分支: develop @ **9e0b35fc**(工作树含本轮改动未提交)
- 命令: `commands run test.full`(Windows —— 耗时口径见 [../baseline.md](../baseline.md)「必须带区间」)
- **实测 (Windows)**: **2678 passed + 4 skipped, 覆盖率 TOTAL 99%**
  - 语句 **16021** / 未覆盖 **163** / 分支 **5472** / partial **143**。
  - 耗时: 两次采样 **51.92s** / **44.21s** ⇒ 区间约 **44~52s**。
  - 注: 首采样那次有 **1 failed** —— `tests/test_docs_forms.py::test_claim_chain_is_bidirectional`, 即「档案引用的
    基线切片尚未落盘」这一环(它等的就是**本切片**); 本切片落盘 + `kb.index` 后该条转绿 ⇒ 2678。
    更早一次 6 failed 全是索引未重建的老签名(`test_index_is_regenerated` 等), 由 `kb.index` 消掉。
- 相对上一条基线 [26-10-06-1830](26-10-06-1830-webui-ctx-menu-viewport.md)(2678 + 4 / 16021 / 163 / 5472 / 143):
  **逐位相同** —— 本轮只动包脚本与知识库, 二者都收不进 `testpaths = tests`。
- **包自测**(不在 `testpaths`, 由 `commands run test.pkg` 跑): **131 passed / 108.15s**(上一条 126, **+5**)。
  本包单独: `test_pipeline.py` **54 OK**(+3, `PackageRefreshTest`) · `test_commit.py` **27 passed**(+2, 接线守阵)。
- **红验**: ①注掉 `commit.py` 的 `refresh_package_modules()` ⇒ `test_push_path_refreshes_package_modules` FAIL
  (顺序实收 `['sync','push']`, 缺 `refresh`); ②把摘要门控去掉(改成"有摘要就重载") ⇒
  `test_unchanged_source_never_touches_module` FAIL(替身 `VALUE 999` 被冲回 `1`)。两处均已还原。
- **端到端复现**(真实包代码 → 临时目录, 非提交物): 进程先 import rev A `_pipeline`(删掉 `retry_note`) →
  磁盘换成 rev B ⇒ `import push` 抛 `cannot import name 'retry_note' from '_pipeline'`(**与真事故一字不差**);
  调 `refresh_package_modules()` → `REFRESH: ['_pipeline']` → 再 `import push` 成功。
- 守卫: `kb.check` 绿(465 文档 · 253 专题, 主键 + 认领链 OK) · `doc.links` 绿 · `doc.caps` **无债务** ·
  `kb.index` 20 生成物重建。
- 改动面:
  - `.commands/my-commit-flow/scripts/_pipeline.py` —— 新增 `_PACKAGE_MODULES` / `_PACKAGE_DIR` / `_source_digest` /
    `_PACKAGE_DIGESTS` / `refresh_package_modules()`; imports 补 `hashlib` / `importlib`; 模块 docstring 补一行。
  - `.commands/my-commit-flow/scripts/commit.py` —— 推送步前 `refresh_package_modules()`; import 补该名;
    docstring 流程第 8 步补说明。
  - `.commands/my-commit-flow/scripts/test_pipeline.py` / `test_commit.py` —— 新守阵 5 条 + 头部「测试计划」补登。
  - `.commands/my-commit-flow/references/pipeline.md` —— 「ship.commit 编排」节补一条判据指针。
  - `memory-bank/` —— 新任务档案 · `pitfalls/git/self-rewrite-imports.md` 新条目 · 本切片 · activeContext 切片。
  - 生成物 `_index.md` / `_doc-map.md` 族(20 个重建)。
- 行尾: 本切片与改动面全为 **LF**(仓库 2026-10-02 起 `text=auto eol=lf`)。
- **未入库**: 等用户显式「提交」。
