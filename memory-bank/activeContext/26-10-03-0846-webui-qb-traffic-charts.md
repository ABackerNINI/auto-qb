# WebUI qB 口径流量图 (全局/单种/分组三图) — 方案C 拍板落地, 停在计划待实施

> 摘要: 可行性轮产出 [reports/26-10-03-0757](../reports/26-10-03-0757-report-qb-traffic-charts.html) (推荐 A, 先不实施); 本轮用户拍板**总方案 C** (采样管线 + 逐系列 dat 文件落 `<data_dir>/qb-traffic/` 子目录, 推翻报告推荐 A) + **停机空洞 null 断线**, 分组换 key 旧历史策略按要求给三选项详细对比 (待拍板默认「不保留」, P4 前可改判)。产出实施计划 [plans/26-10-03-0946-plan-qb-traffic-charts-c.html](../plans/26-10-03-0946-plan-qb-traffic-charts-c.html) (12 节 dark 单文件): 存储设计 (行式 dat v1 + index/reconcile + 单种不落盘)、采样器 (speed_curve_mod 同款自注册; 修正报告 §9.1 —— `_build_group_view` 系 web 层懒建, 采样器自算组级 sum)、`qb_traffic` 配置键 4 键全链 (新发现 config_key_surface 键面冻结须同步)、null 断线栅格语义、P1-P6 派发 ≈6-8.5 人日; C 下差分基线不落盘 → state 零改动免 v4。档案 [tasks/26-10-03-webui-qb-traffic-charts](../tasks/26-10-03-webui-qb-traffic-charts.md) (专题 torrent-traffic-stats)。主 issue 26-09-27-1248 保持 Open。

> 最后活动: 2026-10-03 09:46

**正在进行**: 无 —— 停在「计划已出、待实施启动」。

**待办**: ① 用户对计划 §04.3 分组换 key 旧历史策略拍板 (默认甲「不保留」, 不拍板即维持甲); ② 实施启动后按计划 P1-P6 逐段派发, 每段独立可提交; ③ P4 (分组查询端点) 前是分组 key 策略的改判窗口。
