# WEBUI 通知渠道设置项暂不图形化

> 摘要: 用户报「通知渠道勾选 platform 后取消仍提示有改动未保存; 取消后保存报 config.notify.channels: 必须是非空列表」。用户拍板「暂时隐藏该设置项, 添加好注释」—— 实施 = 新增 schema `Field.hidden`(键留在配置契约里, 只不进渲染) + `cfgFlatten` 单点跳过 + `toggleKey` 清空改删键(与 cfgItemRemove 同口径)。根因与判据入坑档 `pitfalls/web-ui/config-field-unexpressable-in-ui.md`; 基线 `26-10-10-0951`(见 kb.baseline)。
> 最后活动: 2026-10-10 09:51

**Refs:** memory-bank/tasks/26-10-10-webui-notify-channels-hidden.md,memory-bank/pitfalls/web-ui/config-field-unexpressable-in-ui.md

## 正在进行

- 无 —— 本轮修复已完成并收口(test.full 绿, 守阵 3 个测试函数已加)。

## 关键结论(供后续恢复该字段时读)

- **为什么是 hidden 而不是摘字段**: 键面守卫(`tests/test_config_key_surface.py`)以 schema 为键面单点 —— 直接从 `groups.py` 摘掉 channels 会被判成「消失的键」(破坏性变更, 要抬 `CURRENT_VERSIONS["config"]` + 注册迁移), 而本次根本没改配置契约(校验层与 loader 照旧接受该键, 存量 config.yml 里已写的 channels 仍然合法)。实测第一版就是这个红(`消失的键(1): notify.channels`)。
- **恢复条件**: 多渠道(webhook/邮件/Telegram, 见 `想法.md`)落地后, 去掉 `hidden=True` 即可; 那时空列表才有「一个都不选」的语义, 需同步放开校验层的非空约束与 loader 的显式空分支(现在 `raw_channels` 为空即走缺省)。
- **未做的语义变更**(用户未授权): 放开 `channels: []` 并让它真的静默 —— 那要改校验 + loader + notify 侧按 channels 分派(`infra/notify.py` 目前完全不读 channels)。
