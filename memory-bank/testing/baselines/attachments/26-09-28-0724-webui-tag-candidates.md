# 1820 passed / 3 skipped —— WEBUI 标签候选剔除程序自动维护标签

> 摘要: /api/tags 增 exclude_auto 查询参数(添加种子窗口/「标签/分类…」弹窗候选源), 服务端按 utils.auto_managed_tag_rules 剔除站点+HR 精确集与集数模板形状标签; 事件标记(MISSING/zSkipChecked)与规则 add_tag 输出按拍板保留; 改标签弹窗把选中集合共同携带的标签并回候选保住摘除路径。新增 2 测试, 全默认配置行为不变。
> 基线时间: 2026-09-28 07:24
> 档案: tasks/26-09-28-webui-tag-candidates.md

- test.full 一次通过(无 throttle 假红): **1820 passed / 3 skipped**, 19.95s, TOTAL **91%**(12542 语句 / 915 未覆盖 / 4222 分支 / 389 partial); 与 26-09-28-0632(1818, 含 throttle 用例口径)同口径净增 2 = 本轮新测试(test_auto_managed_tag_rules + test_api_tags_exclude_auto)。
- test.quick 全绿 1820 passed(17.5s)。
