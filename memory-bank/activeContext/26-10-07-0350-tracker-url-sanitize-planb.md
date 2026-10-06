# tracker URL 源头脱敏 方案 B — S1–S4 实施完成

> 摘要: 分步计划 [26-10-07-0055](../plans/26-10-07-0055-plan-tracker-url-sanitize-planb.html) 的 **S1–S4 已全部落码**(分支 feat/tracker-url-sanitize-planb 六提交 589c91ff→e229c658→88a21ca4→a46c1df7→ff97e7cf, S4a/S4b 两笔), 收尾回写已完成(档案 Done / 计划 doc-status Done / 旧切片 26-09-23-1915 迁出 progress)。S1 源头归一化: `mask_tracker_url`/`mask_tracker_entry` R1–R9 规格 + qbapi 槽/Facade 拉取即 mask + 6 组单测; S2 编辑下线: 前端/路由/命令表/处理器/QbApi 包装/测试全链路删除, 端点清单 77→76; S3 收口切换(原子批): 详情 API mask 前置于缓存 + `_cmd_remove_tracker` 改道 mask 比对/原文传 qB/0·2+ 命中报错; S4: 守阵 5 组落码并逐组红验(全红→还原复绿, 源码零残留) + code-style「凭据脱敏」条升级越界即脱敏。test.full 实测: **2698 passed + 4 skipped + 2 failed(存量 KB 守卫, 收尾已修回绿)/ 覆盖率 98.54% / 39~41s**(基线 [26-10-07-0337](../testing/baselines/26-10-07-0337-tracker-url-sanitize-planb-s4b.md)), 新增测试 +14。
> 触发: tracker URL, mask, 脱敏, passkey, 编辑下线, 移除 tracker, S1-S4, 守阵, 红验
> 最后活动: 2026-10-07 03:50

**Refs:** memory-bank/tasks/26-10-07-webui-tracker-url-sanitize.md,memory-bank/plans/26-10-07-0055-plan-tracker-url-sanitize-planb.html,memory-bank/testing/baselines/26-10-07-0337-tracker-url-sanitize-planb-s4b.md

## 已完成

- S1–S4 六提交全部落码(明细见任务档案进度日志 2026-10-07 03:50 条), 守阵 5 组红验全过。
- 存量 2 红(基线 26-10-07-0337 记录的 KB 守卫)已修复: 切片 26-10-06-0751「最后活动」坏时间戳改为规范 `YYYY-MM-DD HH:MM`; 定向 `test_memory_bank.py` 37 passed 全绿。
- 档案 `tasks/26-10-07-webui-tracker-url-sanitize.md` Status→Done; 计划 HTML doc-status→Done(基树 20bd2157 → 完成于 ff97e7cf); 旧切片 26-09-23-1915 已完结迁出 [progress/implemented-webui.md](../progress/implemented-webui.md)。

## 遗留事项

- **真机走查未做**(S4 计划含此项, 本环境无 qB 未执行): 详情面板 mask 显示(站点/端点/状态可辨)、移除一条、添加一条、「编辑」入口消失且路由 404, 待真机验证。
- **计划外发现(未修, 范围守恒)**: ①`webui/commands.py:257` 仍有虚拟前缀字面量第三处(计划只收敛 views.py 一处); ②`static_ui.py:46` StaticFiles 挂根使 POST 未匹配恒 405(守阵③按 404/405 双断言适配)。需要处置时走 issue 入池。
- 分支 feat/tracker-url-sanitize-planb 待并回 develop(6 提交, 交付以 Gitee 为准)。
- 基线切片 [26-10-07-0113](../testing/baselines/26-10-07-0113-planb-steps-docs-round.md) 的 Refs 仍指向已迁出的旧切片 26-09-23-1915(一次性快照不回写, 事实已由本切片与 progress 承接)。
