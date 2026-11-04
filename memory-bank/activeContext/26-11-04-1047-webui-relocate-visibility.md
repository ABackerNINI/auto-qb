# webui-relocate-visibility

> 摘要: 产出待收尾迁移种子的 WebUI 可见性与路径链展示计划(P0-P3 分期); 完成 8 条假设压测、三层路径语义、数据契约、链探测边界、测试与回滚设计
> 最后活动: 2026-11-04 15:24
**Refs:**
- [计划](../plans/26-11-04-1042-plan-webui-relocate-visibility.html)
**R0(2026-11-04 10:47):** 产出待收尾迁移种子的 WebUI 可见性与路径链展示计划(P0-P3 分期); 完成 8 条假设压测、三层路径语义、数据契约、链探测边界、测试与回滚设计

**R1(2026-11-04 11:51):** P0 完成: 主循环发布不可变 job 快照; 成员/组 relocate 标注(状态归并/origin 归属/后端聚合); origin 落账; decorate 指纹进新字段; 新增 8 项单测

**R2(2026-11-04 12:18):** P1 完成: 路径列迁移徽标(moving/待收尾/failed/mixed, button 键盘/触屏可达, 点击只开详情); 独立迁移状态筛选(路径筛仍按 save_path); 详情 General 新增迁移段(无 job 整段不渲染); decorate 指纹补 src/armed_at; 扩展 4 项测试; test.full 实测 5163 passed + 10 skipped

**R3(2026-11-04 13:09):** P2 完成: GET /api/relocate/chain 只收 hash、服务端派生起点、403 与允许根白名单; 逐跳 lstat/readlink(junction/symlink/硬链接/挂载点, 8 跳上限+环检测, 判不了给未确认); 每跳类型+job alias_paths 归属章; 20s TTL+refresh=1; 四皮肤 A→B→C 浮窗(键盘/Esc/焦点回退, 错误态分级); 新增 relocate_chain 13 例; test.full 实测 5176 passed + 10 skipped

**R4(2026-11-04 13:31):** P3 完成: opt-in qB 待收尾标签镜像(默认空=零 qB 写; 只写不读, zRelocate 保留命名空间); armed/收尾窗口加、终态摘, 失败降级+重启补写; 新增 8 例标签测试与配置键守卫; test.full 见 kb.baseline

**R5(2026-11-04 15:24):** 真机验收完成: 新增 tests-real RM04-15..18 并全过(四皮肤行高/浮窗翻转夹取与滚动关闭/Esc 退栈回焦/组行入口基准/A->B->C 与 UNC 15.1ms 未确认/pending_tag 加-手删不重加-重启补写-终态摘/关闭零写), RM04-14 confirm 回路回归通过; test.full 5185 passed + 10 skipped, 新基线 26-11-04-1519
