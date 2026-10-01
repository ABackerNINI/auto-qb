# 基线 · 2290 passed + 3 skipped / 99% —— 用户指派批 7 issue 清偿收官

> 摘要: 4 阶段 4 提交(2359a3d1 hr 三项 / 4a883385 flaky 时钟对齐 / f89ceada qbmanager StopIteration+pragma / 49d933b5 tray 读回删除)后的会话末基线; 7 条 issue 全部收口(5 Done + 1 Dropped 复验推翻 + 1 已消失)。收尾 sync 并入远端 fa79d526(WebUI Shift 连选起点, 带守阵 +1)后在本基线重测。档案: [tasks/26-10-02-backend-issues-clearance.md](../../tasks/26-10-02-backend-issues-clearance.md)。
> 基线时间: 2026-10-02 07:07, develop @ 032a6eec(收尾回写未提交工作树, test.full 实测)。
> Linux 侧: 待补(仅 Windows 侧重测, 见 baseline.md 常驻警告)。

TOTAL **2290 passed + 3 skipped / 99%**(13,251 语句 / 86 未覆盖 / 4,436 分支 / 81 partial,
test.full 28.41s, rc=0)。
相对本批开工前(26-10-02-0603: 2289 passed + 3 skipped / 99%)**+1 passed**(远端并入的 Shift
连选守阵 +1, 本批测试面净持平: hr 恢复告警改断言、flaky 改初始条件、qbmanager 守阵 +1 与
tray 删 1 用例互抵); 语句 13,251、分支 4,436 / partial 81 —— 本批净删面 = tray 读回块整删。
改动面: `hr/service.py` + `tests/test_hr_service.py`(阶段 1/2)、`core/qbmanager.py` +
`tests/test_qbmanager.py`(阶段 3, qbmanager.py 覆盖率 100%)、`tray/app.py` + `tests/test_tray.py`(阶段 4)。
