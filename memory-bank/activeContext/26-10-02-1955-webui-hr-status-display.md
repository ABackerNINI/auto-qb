# WEBUI HR 在线核实信息展示改造

> 摘要: 任务完结(实施面)。计划 [plans/26-10-02-1936](../plans/26-10-02-1936-plan-webui-hr-status-display-rework.html) 四阶段全部实施并推送: `b50c2873` 后端(local_present 单点 mark_local_present + 「毕业」可见 4 处改「已达标」) / `888a0e29` 折叠+覆盖式全屏(拍板①用户改判「展开即覆盖式全屏, 不另设全屏钮」; atlas clip-path 裁 fixed 后代坑真浏览器目检发现, 见 pitfalls/web-ui/clip-path-clips-fixed.md) / `8cb2da59` 老旧过滤+三态排序+三列重组 / `ca77ff23` 收尾(守阵复核零缺口)。拍板②a③a④a⑤a 均按推荐。基线 [baselines/26-10-03-0440](../testing/baselines/26-10-03-0440-webui-hr-status-display-rework-done.md)(2309 passed + 3 skipped / 99%); 阶段 2/3 各做了三套 UI 真浏览器目检(桩数据)。已完成条目迁出 progress/implemented-webui.md。档案 tasks/26-10-02-webui-hr-status-display(Done)。
> 最后活动: 2026-10-03 23:35

## 已完成 (2026-10-03)

- **切换钮文案再修订: 「显示未做种/只看做种中」→「显示已删除种子/只看本地仍在列」**(二次驳回, 用户指令): 用户指出「未做种」误导(实际语义是本地已删除/从未下载), 且「做种中」不准确(反向态含暂停/异常等非做种状态)。改动: 用户可见文案 —— 默认态 `hrsOldBtnText`「显示未做种 (N)」→「显示已删除种子 (N)」, 反向态「只看做种中 (M)」→「只看本地仍在列 (M)」, 空态 `hrsEmptyText`「该站点没有未做种的种子」→「该站点没有已删除的种子」; 同层注释/守阵标签一并换词。判据来自 routes/hr.py:22-36 —— `local_present` = 本地 qB 库存在该种子(含暂停, 与做种状态无关), 键探测 infohash v1→v2。**保留**内部标识符 `oldOn`/`hrsOldOnOf`/`hrsToggleOld`/`hrsOldBtnText`。明细见档案进度日志 23:35 条。
- **切换钮文案「显示老旧种子」→「显示未做种」**(第一轮修订, 已被上条取代; 回应 HR 取证报告 [26-10-03-1505](../reports/26-10-03-1505-report-hr-fetch-verify-forensics.html) §8 缺陷 B1 —— 按钮名「只看做种中」与实际过滤「本地库存在」之间的误导空间, 该轮选了「未做种」, 用户判定仍不准确)。

## 正在进行

- **真机走查待用户执行**(唯一未验证面): 需真实 qB + 真实 HR 数据, 折叠/全屏/过滤/排序/文案五面各点一遍; 走查发现问题回本切片续。
- (实施条目已全部完结迁出, 其余无)
