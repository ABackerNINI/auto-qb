# WEBUI 详情面板用户页空列表停"正在加载…"修复 — fetcher 落袋通知移进 finally (Done)

> 摘要: 用户报「WEBUI 种子详情页用户页显示好几秒'正在加载…', 然后才显示'暂无已连接用户'」。排查: 后端 `/api/torrents/{hash}/peers` 实测 2~3ms 非瓶颈, 经典包裹层走 Vue 响应式也无此窗口 —— 根因在变体渲染机制: 变体(dt07/08/09)**只在 `_dtNotify` 时重渲染**, 而列表 fetcher 原把通知放 try 块(数据落袋处), `peersLoading = false` 在 finally —— 通知那一刻 loading 还挂着, 空列表变体渲染"正在加载…", 随后 loading 清掉但无通知 ⇒ 停在旧态到下一拍 5s 轮询才翻空态。修法 = trackers/files/peers 三 fetcher 的 `_dtNotify` 移进 finally、在 loading 清掉之后(stale 响应仍不通知); trackers(dt04/05/06)与 files(dt10/11/12)是同款缺陷一并修, detail 不在列(general 变体不渲染 loading 态)。守阵: `test_web.py::test_drawer_tpl_registry_wiring` §4a 加次序断言(loading 清除先于通知)。新坑记入坑档 template-render.md(变体通知驱动渲染), kb.index 重建。不满足立档阈值(单会话、2 处源文件小修, 无任务档案)。test.full **2690 passed + 4 skipped / 99% / 33.8s**(基线切片 26-10-07-0411)。
> 最后活动: 2026-10-07 04:11

**Refs:** memory-bank/pitfalls/web-ui/template-render.md

## 现状

- **修复完成, 待提交**。改动面: `src/auto_qb/webui/static/shared/drawer.js`(三 fetcher 通知挪 finally) · `tests/test_web.py`(§4a 次序守阵 + docstring 测试计划同步) · 坑档 template-render.md 新条目 + 摘要/触发词扩充 · 本切片 · 基线切片 · `kb.index` 重建生成物。
- 验证: `commands run test.quick` 2690 passed; `commands run test.full` 2690 passed + 4 skipped / 99% / 33.8s。守阵正则以改动后源码实文校验过(fm 正则匹配三 fetcher 全函数体, 失配即红)。
- 未验证面 / 残留风险: 未做真机浏览器冒烟(需变体皮肤 + 真实 qB; 本 clone 的修复未经 Gitee 同步前, 用户运行中的实例 38080 服务的是别的 clone 的旧 drawer.js, 刷新不会带上修复)。判据为机制推演 + 逻辑单点收口: 通知点只有 fetcher/`_dtSync`/collapse 四处, 三 fetcher 修后每条落定路径(成功/失败/静默轮询)都有"清 loading + 通知"成对出现。
