# 热重载路径测试选「活配置段」会触发该段模块 apply 的真实副作用(notify 段会泄漏真 handler)

> 摘要: 驱动 apply_new_config 的测试(段认领兜底/回执/级别语义类)如果改的是 notify 这类「apply 有
> 全局动作」的段 —— NotifyModule.apply 对段变会 `_mount(force=True)`, **配置未启用也真挂载**
> NotifyHandler 到 "auto_qb" 根 logger 且测试不摘 —— 全局状态泄漏进后续测试
> (实测: test_notify::test_setup_notify_disabled 的「不挂载」断言被它打红, 单跑恒绿、全量才炸)。
> 触发: 写热重载/兜底类测试选驱动段时; 见「单跑绿全量红」且红在 logging 全局面断言

- **触发**: apply_new_config / host.apply_all 的测试需要挑一个「变更段」来驱动; 选段时只想着
  diff 好构造, 没查该段所属模块的 apply 是否有全局动作。
- **判别**: 全量红单跑绿的失败点在**无关的日志/通知测试**; 或某测试后 `logging.getLogger("auto_qb").handlers`
  里多了 NotifyHandler。对照: 被改段名 → `host.get(认领模块).apply` 是否会 mount/start/remount。
- **处置**: 选段三判据 —— ①该段**独占**认领(多认领段裁一个 claimer 仍是认领面, 兜底测试不红);
  ②认领模块的 apply 是 BaseModule 默认无动作(或恒短路); ③该段不在 rules 重建判据里(delete_tags/
  trackers 变了会触发 L2 重建, 搅浑断言)。合规先例: add_episode_tags(maintenance 独占 + 无动作)。
  必须用有副作用的段时, finally 里摘干净(notify: `host.get("notify")._unmount()`); 参考实现
  tests/test_modules_p6.py::test_unclaimed_section_change_warns_and_rebuilds 的选段注释。
- **守阵**: test_modules_p6 选段注释(段选择判据三条件); conftest 的通知拦截只拦**外部命令**,
  拦不住 handler 挂载本身 —— 别指望 conftest 兜底。
- **复发**: 1(2026-10-01 P6 兜底守阵初版; 全量红指向 test_notify 才定位, 选段注释已把判据固化)。
