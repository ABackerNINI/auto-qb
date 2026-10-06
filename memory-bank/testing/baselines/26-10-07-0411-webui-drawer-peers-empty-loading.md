# 2690 —— WEBUI 详情面板用户页空列表停"正在加载…"修复收尾 (develop, 源码小修轮)

> 摘要: 修复「种子详情面板用户页显示好几秒'正在加载…'才翻到'暂无已连接用户'」—— 列表
> fetcher 在 try 块 `_dtNotify`(变体只认通知重渲染), 此时 `finally` 尚未清 loading, 空列表
> 变体(dt07/08/09)停"正在加载…"到下一拍 5s 轮询; 经典层走 Vue 响应式无此窗口, 后端接口实测
> 2~3ms 非瓶颈。修法 = trackers/files/peers 三 fetcher 的落袋通知移进 finally、在 loading
> 清掉之后。改动: drawer.js + test_web.py(守阵加次序断言)。
> 基线时间: 2026-10-07 04:11

- 分支: develop @ **dbde451a**(开工 sync 即在此 hash, 本轮尚无本地提交)
- 命令: `commands run test.full`(Windows)
- **实测 (Windows)**: **2690 passed + 4 skipped, 覆盖率 TOTAL 99%(16021 语句 / 163 未覆盖 /
  5472 分支 / 143 partial)**; pytest 自报 **33.13s**(commands 包脚本计时 33.8s 含开销)。
- 相对上一条 [26-10-07-0346](26-10-07-0346-webui-drawer-search-jump.md)
  (2690 + 4 / 16021 / 163 / 5472 / 143): passed 与覆盖四指标逐位相同 —— 本次守阵是既有
  `test_drawer_tpl_registry_wiring` 内加断言, 不新增测试函数; 前端 JS 不进 `--cov=src` 统计。
