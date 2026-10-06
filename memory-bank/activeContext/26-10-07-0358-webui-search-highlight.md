# WEBUI 移除冗余的搜索命中行级高亮 (Done)

> 摘要: 用户报「WEBUI 搜索后所有种子都是匹配的, 即所有种子都会高亮, 失去了意义」。根因 = 行级 `search-hit` 高亮挂在"保留即命中"的行上 —— 种子页 `filteredTorrents` 只留命中; 辅种组行 / 追剧集行 / 未识别行按成员命中整行保留 ⇒ 恒亮无区分。**用户拍板只去冗余的行级高亮**: 删种子页种子行 / 辅种页组行 / 追剧页集行 / 未识别行的类绑定, **保留**明细成员行与站点挂件的"仅命中成员才亮"(仍有区分)及追剧**剧行**(`hit` = 该剧全部集都保留, 非恒亮)。同批清死数据: `columns.js::isHit` 方法 + 组 / 集 / 未识别行的 `hit` 字段。CSS 三皮肤规则全保留(剧行 / 成员行 / 挂件仍在用)。test.full **2689 passed + 4 skipped / 99%**(基线切片 26-10-07-0358)。
> 最后活动: 2026-10-07 03:58

**Refs:** memory-bank/tasks/26-10-07-webui-search-highlight.md

## 现状

- **改动完成, 待提交**。改动面: `static/shared/tpl/torrents.html`(种子行) · `tpl/groups.html`(组行) · `tpl/shows.html`(集行 + 未识别行) · `shared/columns.js`(删 `isHit`) · `shared/filters.js`(组对象去 `hit` + 注释) · `shared/shows.js`(集对象去 `hit` + 注释) · `shared/decorate.js`(未识别行去 `hit`)。共 7 个源文件。
- 验证: `node --check` 4 个 JS 全绿; `commands run test.full` **2689 passed + 4 skipped / 0 failed / 99% / 59.24s**(与上一条基线 26-10-07-0251 逐位持平, 本轮无测试增删; 既有守阵 `test_web.py::test_frontend_search_syntax_wiring` 仍绿 —— `filteredTorrents` 的 `hits.has(r.hash)` 过滤逻辑未动)。
- 未验证面 / 残留风险: 未做真机 Playwright 冒烟(需真实 qB); 判据为模板静态读 + 类绑定消费者全量 grep —— 剩余 `search-hit` 绑定 = 组明细成员行 / 剧明细成员行 / 站点挂件 / 追剧剧行, 均有区分力。
- 判据沉淀: 「行级高亮只在'同一容器里同时存在命中与未命中行'时才有信息量 —— 若行的保留条件本身等于命中条件, 高亮恒亮, 无区分」。
