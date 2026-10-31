# qB 多标签解析: 成员判断必须 strip, 裸 split(",") 对第二个标签失明

> 摘要: qBittorrent 的 tags 字段以「, 」(逗号+空格)连接多标签; `split(",")` 不 strip 会把第二个标签解析成带前导空格的串(`" real-fake"` != `"real-fake"`), 所有「按标签认领种子」的成员判断随即静默失明。单标签时无空白无感, 第二个标签(实测: 产品打的 MISSING)进场即中招。
> 触发: 按标签认领/过滤种子, 写 tags 成员判断, tests-real 基建, qB API tags 字段

- **触发**: 2026-10-31 RM04 真机实测轮: 产品给假种子打 MISSING 标签后 tags 变 `MISSING, real-fake`, `tests-real` 侧 `seed.py::_fakes` 与 `lib/guard.py::snapshot` 的裸 `split(",")` 成员判断全部失明 → `real.seed.list` 报「自造 0 个」、`rm --all` 删不掉、守卫把假种子误计入保护面, 残留被同 infohash 复跑收养成假 FAIL(issue 26-10-31-1215)。各片用例各自手写 `_tags_of` 时都对了, 恰好是共享的 lib/CLI 两处漏了 —— 说明这不是"忘了 strip", 是**没有单点**。
- **判别**: ①grep `(t.get("tags") or "").split(",")`: 旁边没有 `.strip()` 就是中招形态; ②现象特征: 种子明明在实例里、按标签过滤却报 0; ③打印 `repr(tags.split(","))` —— 看到带前导空格的成员即实锤。
- **处置**: 统一走集合解析单点 `{x.strip() for x in (t.get("tags") or "").split(",") if x.strip()}`; tests-real 里单点是 `lib/guard.py::tag_set`(2026-11-01 起 `seed.py::_fakes` 与 `guard.snapshot` 都走它), 新的按标签判断**禁止自带裸 split**。注意 qB API 写入侧(`add_torrent(tags=...)`)用逗号连接即可, 只有**读回解析**侧需要 strip。
- **守阵**: `lib/guard.py::tag_set` docstring 写明禁令; 复发时先看是否有第三处调用点绕过了单点。
- **复发**: 0
