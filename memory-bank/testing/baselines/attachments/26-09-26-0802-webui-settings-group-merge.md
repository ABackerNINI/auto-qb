# 1666 collected / 1665 passed + 1 skipped —— webui 设置页分组合并(日志/界面(WebUI)/通知/运行日志 并入常规)

> 摘要: schema groups.py 把 log/web/notify 三段并进 basic 组、删三个独立分组(首页 10 卡 → 6 卡), WebUI 界面卡改名 WebUI, 运行日志移入常规分区页尾; 数字为合并工作树重测(含并行入库的 versioning/button 测试, 该两线亦在本树先行验证)。
> 基线时间: 2026-09-26 08:02
> 档案: 26-09-26-webui-settings-group-merge

- **本线守阵改写 1 条**(test_web.py): `test_config_schema_endpoint` 分组表断言更新为 6 组
  (basic/maintenance/hr_check/speed/trackers/rules) + 新增断言 basic 尾三段 = log/web/notify。
  收尾踩两条 KB 守卫(坏链/cap 超)已按机制修复(立档 + 2026-09-15 三条外迁 history 轮转)。
- **对比上一条基线(1641+1, 按钮体系) +24**: 并行线 test_versioning.py 新文件 + test_web.py 按钮/版本接线用例;
  本线自身零新增用例(分组表断言就地更新)。

TOTAL **92%**(11112 语句 / 783 未覆盖 / 3692 分支 / 331 partial), 耗时 18.65s(单次采样)。
