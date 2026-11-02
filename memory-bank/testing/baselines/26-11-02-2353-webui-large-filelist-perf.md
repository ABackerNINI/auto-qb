# 4896 passed + 2 skipped(根) —— W6a 落地 + W6b Dropped + 真机 RM08-09 千文件

> 摘要: W6a 乐观优先级落地(失败/超时双回滚) + W6b 按拍板 Dropped + 真机 RM08-09 千文件 content 实测
> 基线时间: 2026-11-02 23:53
**Refs:** memory-bank/tasks/26-11-02-webui-large-filelist-perf.md, memory-bank/plans/26-11-02-0351-plan-webui-large-filelist-perf.html

## 验收数字

`commands run test.full` 实测(2026-11-02 23:53, 工作区未入库态, W6a 落地后):

- 汇总行: `4896 passed, 2 skipped, 3 warnings in 147.45s (0:02:27)`
- 覆盖率: TOTAL 22523 stmts / 134 miss, 分支 7728/128 miss, **99%**(门槛 99% 达标)
- 零 failed。首轮曾 3 failed: ①`test_index_is_regenerated`/②`test_gen_all_check_is_green`(改档后索引未重建, `kb.index` 后自愈) ③`test_trigger_registry_call_sites_exact`(新增 POST 调用点未登记, `triggers.js` 补 `_drawerFilePriority` 条目后自愈)
- 新增单测 `tests/test_webui_drawer_fileprio_optimistic.py`: 2 passed(静态顺序/双出口 + node 五态电池)

e2e(同一树, 千文件桩, 双皮肤):

- `commands run dev.e2e -- e2e/drawer-fileprio-optimistic.spec.mjs`: **6 passed**(成功/失败回滚/超时回滚 × prism/atlas)
- 可见延迟: 乐观 **15-17ms** vs 旧路径 **171-174ms**(回执延迟 100ms); 失败回滚 350-352ms; 超时回滚 10027-10036ms(10s 无回执)

真机(环境1 = D 盘 36595/36596; C 盘 56589/56590 目录不存在, 未使用):

- `commands run real.env` / `real.guard` 通过(端口+镜像路径+进程三方核对; 主实例 8 枚真实种子快照时 0 active, 全程非活跃; 副实例空库)
- `commands run real.run -- --case RM08-09 --yes`: **1 passed**(新用例; 假种子 1000 文件, paused/无数据/无 announce)
- 数据面(最后一跑): files 1000 行 / payload **156478B** / 冷 **30ms** / 热 **17ms** / detail **12ms** / `files/priority` HTTP 轮询回执 **425ms**(两跑区间: 冷 30-44 / 热 16-18 / detail 12-28 / 回执 423-440)
- 真产品前端(最后一跑): 首帧 **436ms** / 常驻 DOM **47 行**(折叠后 **1** / 展开后 **47**) / **rowsFn 1002 行 max 7.6ms / mean 5.28ms (n=20)** / longtask **0** / 可见延迟 乐观 **9ms** vs 旧路径 **64ms**(两跑区间: 首帧 436-486 / 乐观 9-14 / 旧路径 64-80)
- 收尾 `clean_fakes` 删净假种子; 产品进程 taskkill /F /T

## 本改动面

- `src/auto_qb/webui/static/shared/drawer.js` — `setFilePriority` 改走新增 `_drawerFilePriority`; 新增 `_drawerFileRollback`; 乐观写先于 POST, 失败/超时回 prev 后静默重拉; 重叠点击按 hash 序号只让最新一次收口
- `src/auto_qb/webui/static/shared/triggers.js` — TRIGGER_DEFS 登记 `drawer.js::_drawerFilePriority`(panel)
- `tests/test_webui_drawer_fileprio_optimistic.py` — 新增(2 条: 静态守阵 + node 五态电池)
- `e2e/drawer-fileprio-optimistic.spec.mjs` — 新增(3 条 × 双皮肤, 含可见延迟对照实测)
- `tests-real/rm08_webui_read/test_rm08_webui_read.py` — 新增 RM08-09(千文件假种子 + 数据面/真产品前端量具), 文件头补 RM08-09 说明
- `memory-bank/plans/26-11-02-0351-plan-webui-large-filelist-perf.html` — §06 D1 Dropped/D3 实施回填 + §06.1 落地后/真机数字 + R2 变更记录
- `memory-bank/tasks/26-11-02-webui-large-filelist-perf.md` — Summary/S9-S11/R1 进度日志
