# WebUI qB 口径流量图 (全局/单种/分组三图) — 四轮拍板并入 (组不落盘读侧推算), 停在计划待实施

> 摘要: 可行性轮产出 [reports/26-10-03-0757](../reports/26-10-03-0757-report-qb-traffic-charts.html) (推荐 A, 先不实施); 用户拍板**总方案 C** (采样管线 + 逐系列 dat 文件落 `<data_dir>/qb-traffic/` 子目录, 推翻报告推荐 A) + **停机空洞 null 断线**。产出实施计划 [plans/26-10-03-0946-plan-qb-traffic-charts-c.html](../plans/26-10-03-0946-plan-qb-traffic-charts-c.html) (12 节 dark 单文件)。**二轮拍板 (26-10-03 10:41)**: 单种历史入盘 (infohash 天然稳定键) + 组 key 稳定化 (代理身份键 + 成员表决吸收, 指纹键否决)。**四轮拍板 (26-10-03 11:10, 计划内称三轮拍板)**: 组流量可由组内种子流量推算 (成员通常 ≤50) → **分组系列不落盘**, 组曲线 = 查询时刻成员集的单种 dat 读侧聚合 (借 global.dat 区分真空闲 0 线与停机断线); 全局含全部种子推算难 → **依旧落盘**。落盘范围收窄为 global + torrents/ 两类, groups/ 目录与 index 组注册表取消, **二轮引入的组身份代理键 + 成员表决吸收整体作废** (组不落盘则无键可断, 移动/增删换键后新键聚合同一批成员的历史, 曲线天然连续; 单种入盘升格为组推算数据基座)。存储: 行式 dat v1 (global.dat + torrents/&lt;infohash&gt;.dat, 头行只放不变身份) + index 单种注册表/reconcile + 删种冻结/重加解冻/按龄淘汰; 采样器 speed_curve_mod 同款自注册, 两系列 (全局恒采/单种活跃过滤); 组聚合移入 P4 API 层 (≤50 文件现算, 不做缓存); `qb_traffic` 配置键 4 键全链 (config_key_surface 键面冻结须同步); P1-P6 派发 ≈6-8 人日; 差分基线不落盘 → state 零改动免 v4。档案 [tasks/26-10-03-webui-qb-traffic-charts](../tasks/26-10-03-webui-qb-traffic-charts.md) (专题 torrent-traffic-stats)。主 issue 26-09-27-1248 保持 Open。

> 最后活动: 2026-10-03 11:10

**正在进行**: 无 —— 停在「计划已出 (含四轮拍板改版: 组不落盘读侧推算)、待实施启动」。

**待办**: ① 实施启动后按计划 P1-P6 逐段派发, 每段独立可提交; ② 「组别名」展示命名 (给曲线起人话名) 已判后置不阻塞, 用户重提再做。
