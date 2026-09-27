# 基线 · 1796 passed + 3 skipped —— HR 在线核实 M5.1–M5.5 全部落地轮 (在线核实 v2 代码侧完成)

> 摘要: 用户令「实施计划 plans/26-09-27-1815, 拍板按推荐」⇒ M5.1 判据与观测 → M5.2 信号处置与停用
> (suspended + --hr-resume + 骤降保护 + 回填对账撤销 + 登录退避) → M5.3 配额拆分(激活门 + 双令牌桶 +
> 页面/下载分工) → M5.4 早停②③与豁免 A/B(轮转起点 + 单轮页面总量) → M5.5 收尾(端点纵深提示 +
> keys.md/configuration.md/扩展 README)。审计报告 26-09-26-1628 的 P1/P2/P3 全部修复;
> 主计划 §15 v3.6 + 计划 1815 v1.2 + activeContext/任务档案已回写。⚠ 公式勘误: P = (now − done) + remain
> (三份制品同源笔误)。每步一红验(翻页并集/骤降保护/激活门/早停②), 临时还原 ⇒ 守阵红 ⇒ 还原全绿。
> 基线时间: 2026-09-27 22:18 (develop @ 045ea27, 开工前 merge --ff-only 至 Gitee 主线)
> 制品: plans/26-09-27-1815 (doc-status Implemented)

TOTAL 1796 passed + 3 skipped / 91%(12261 语句 / 908 未覆盖, test.full 19.9s)
合并树重测(2026-09-27 22:40, 同步远端 5102080: HR 站点绑定映射制 + UI 下拉 + 曲线重构四笔; stash → ff → pop,
手工合流 loaders 旧键迁移段(取远端: 迁移归 config v1→v2)与 keys.md 两处(映射制表述 ∪ M5 新键清单)):
**1804 passed + 3 skipped / 91%**(12300 语句)—— 远端映射制 +8 守阵, M5 全部逻辑在新绑定方式下兼容。
对比前基线(26-09-27-1838: 1742 passed, 代码零改动): **+54 passed**(M5.1 +26 守阵 / M5.2 +22 / M5.3 +11 /
M5.4 +14 / M5.5 +2, 含既有测试按新语义改写: login 退避 ×2 / early_stop ×3 / 清零放行 ×2 / 观测改处置 ×1);
语句 11691 → 12261(+570), 覆盖率 91% 持平。
中途全量节点: M5.1 1763 / M5.2 1774 / M5.3 1787 / M5.4 1795 / 收尾 1796, 每步均全量绿后进下一步。
映射制 × M5 兼容性专项验证(2026-09-27 22:55, 四场景端到端): ① 存量旧键(带 hr_page_url)→ v1→v2
迁移 → 映射派生(tracker='bt' 回填)⇒ M5 六键全默认(legacy/关, 零静默变更); ② sites 新位置
quota_model=split + page/torrent_rate_per_hour 覆盖 ⇒ HrLimits.split 全链路(40/10/20/5 默认与
split 天顶 200 都生效); ③ 双域档案 CarPT(web=carpt.net)迁移 + 派生 adapter=carpt; ④ service
limits_for 消费派生配置。派生构造逐字段核对: M5 全部 8 个站点键都在(loaders.py 288-306);
迁移白名单 5 个既有微调项, M5 新键只在 sites 新位置 ⇒ 迁移器无需认识。
覆盖率口径见 [baseline.md](../../testing/baseline.md)。
