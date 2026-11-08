# 桩上验证配置保存流: 版本章物化 / reload 不应用 / 按端口杀桩

> 摘要: ui_harness 桩的 /api/config GET 读**磁盘树**, PUT 过**版本闸门**(writer._reject_stale_version 对缺 config.schema_version 的提交树一律拒绝) —— 桩不物化配置文件时 GET 树缺章 ⇒ 「保存并应用」在桩上恒 400「提交的配置树缺少 schema_version」, 保存流完全测不到(2026-10-10 规则卡冒烟实证)。修法已落桩: boot 期物化带版本章的最小合法配置(scripts/ui_harness.py::_materialize_config, load_config 自校验, 模板漂移 = 桩拒绝启动)。另: exec kill 掉桩会话杀的是 uv 包装进程, python 子进程不死仍占端口。
> 触发: 桩/e2e 上测「保存并应用」; 桩 PUT 恒 400 缺 schema_version; 杀桩后端口仍被占

## 触发 / 判别 / 处置

- **触发**: ①桩上保存恒 400 且报缺 schema_version; ②kill 掉 exec 会话后 `Get-NetTCPConnection` 显示端口仍 Listen。
- **判别**: ①看 GET /api/config 的 tree 里有没有 `config.schema_version` —— 没有就是桩没物化(根因: 桩的运行期配置是内存 FakeConfig, manager.config_path 为空串, 磁盘上根本没有配置文件; 而真机配置在启动物化时必盖章, 故这个缺口只在桩上存在); ②按端口查到的 PID 名是 python(不是 uv)—— uv 只是包装进程。
- **处置**: ①桩已内建物化: `_materialize_config` 写最小合法配置并 boot 期自校验; `reload_config` 在桩上只回执不应用(`_apply_truth` 只认 pause/resume), FakeConfig 不会被真配置顶掉 ⇒ 桩上可以放心走完整 PUT→写盘→热重载回执链; ②杀桩用按端口找 PID 强杀的 task(`commands run dev.port-kill -- <端口>`), 别指望杀 exec 会话; e2e 轨由 playwright teardown 自己兜底强杀, 不用人工。
- **教训**: 桩文档读面要看「数据从哪来」—— create_app 是真的 ≠ 配置面是真的; 冒烟脚本先做**代码指纹**防陈旧桩(fetch /shared/<js> 断言新方法名), 再做数据面前提(GET 树形状)。

**Refs:** memory-bank/tasks/26-10-09-webui-rule-meta-fields.md
