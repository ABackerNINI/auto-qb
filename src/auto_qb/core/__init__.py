"""auto_qb 核心域包（core）

由根目录平铺文件归拢而来（plan 26-09-22-2112 · 方案 C · W4b）:
- qbmanager.py  QbManager 主协调者（8 mixin 组合 + self.web 门面; 主循环唯一写线程）
- taskqueue.py  单任务队列（add_task / run_due 两动词）
- qbapi.py      qB API Facade（写后同步快照）
- qbclient.py   qB 客户端构造（本地直连 trust_env 处理）
- curves.py     限速曲线纯逻辑（Traffic Monitor dat 解析/聚合/查档）
- episodes.py   集数解析（第x集 > S01E05 > EP05 > E05）
- tvshows.py    剧集识别（追剧视图聚合键）
- exporter.py   YAML 配置模板导出
- mixins/       QbManager 的 6 个核心域功能切片
  (rule_engine / tags / checking / grouping / tracker / speed_curve;
   表现层切片 web_view / web_commands 已于 W3 迁 webui/)

依赖方向: core → config / infra / torrents / rules（单向）;
表现层（webui/tray）→ core 经门面与 mixin 组合, core 不 import 表现层。
"""
