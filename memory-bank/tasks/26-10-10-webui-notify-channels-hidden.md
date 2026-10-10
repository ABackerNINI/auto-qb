# 26-10-10-webui-notify-channels-hidden — 通知渠道设置项暂不图形化(Field.hidden)

**Status:** Done
**Added:** 2026-10-10
**Updated:** 2026-10-10
**Topics:** webui-notify-channels-hidden
**Summary:** 用户报「通知渠道勾选 platform 后取消仍提示有改动未保存, 取消后保存报 config.notify.channels: 必须是非空列表」; 用户拍板「暂时隐藏该设置项, 添加好注释」。实施 = 新增 schema `Field.hidden` 声明位(键留在配置契约里) + `cfgFlatten` 单点跳过 + `toggleKey` 清空改删键; 新增守阵 3 个测试函数。测试面见 `commands run kb.baseline`(基线 26-10-10-0951)。

**Refs:** memory-bank/activeContext/26-10-10-0951-webui-notify-channels-hidden.md,memory-bank/pitfalls/web-ui/config-field-unexpressable-in-ui.md,memory-bank/testing/baselines/26-10-10-0951-webui-notify-channels-hidden.md

## 原始请求

- 「修复问题: WEBUI常规设置中的"通知渠道"勾选"platform"后取消仍提示有改动未保存... 然后取消勾选保存报错: 保存失败: 配置校验失败, 共 1 处: [1] config.notify.channels: 必须是非空列表」
- 拍板(选项外自选): 「暂时隐藏"通知渠道"设置, 添加好注释」

## 思考过程与决策

- **根因(一处两症)**: `config_editor.js::toggleKey` 取消勾选最后一项时仍 `cfgSetPath(path, [])` 写空列表 —— ① 空列表与"键缺失"不同构, 脏标记是整树 `JSON.stringify` 对比 ⇒ 「勾选再取消」后仍提示有改动未保存; ② 空列表过不了校验(非空列表约束) ⇒ 保存必败。
- **语义盘查**: v1 渠道值域只有 platform 一档, 而 `load_notify_config` 缺省即 `["platform"]`, 且 `infra/notify.py` 目前**完全不读** channels —— 这个勾选框在语义上是空的(勾与不勾运行期等价)。故正确处置不是"修好这个控件", 而是先别把它摆出来。
- **为什么打 hidden 而不是摘字段(本轮最大的一次返工)**: 首版直接从 `groups.py` 摘掉 channels 字段, `test_config_key_surface` 当场红「消失的键(1): notify.channels」—— 键面守卫以 schema 为键面单点, 摘字段 = 破坏性变更流程(抬版本 + 注册迁移), 而配置契约根本没动(校验层仍接受、存量配置仍合法)。改为新增 `Field.hidden` 声明位, 键留契约、只不渲染。
- **为什么补 toggleKey**: 该字段将来(多渠道落地)一定会回来, 那时同症必复发; 且与同文件 `cfgItemRemove`「清空即删键」的既有口径不一致, 属于同源缺口, 一并归正(改动一行 + 注释)。

## 实现计划

1. `config/schema/fields.py`: 新增 `hidden: bool` 声明位 + docstring(用途与三个"别拿它干什么")
2. `config/schema/groups.py`: notify.channels 打 `hidden=True` + 注释(为什么隐藏 / 为什么不是摘字段 / 何时恢复)
3. `webui/static/shared/config_editor.js`: `cfgFlatten` 加 `if (f.hidden) continue`(两套 UI 同源于此); `toggleKey` 清空改 `cfgDelPath`
4. `tests/test_config_schema.py`: `test_notify_channels_hidden_from_ui_but_kept_in_contract`(四面: schema 保留 + hidden / hidden 声明面一处 / KNOWN_NOTIFY_KEYS 仍在 / 校验仍接受 platform 条目且仍拒空列表)
5. `tests/test_webui_static_dom_page.py`: `test_frontend_flatten_skips_hidden_fields` + `test_frontend_keyed_list_toggle_deletes_key_when_emptied`
6. `docs/configuration.md`: channels 行补「暂不在设置页显示」说明
7. 验证: `commands run test.one`(4 文件)→ `test.quick` → `test.full` → `dev.fmt` → 回写知识库 + `kb.index`

## 子任务状态表

| 子任务 | 状态 |
|---|---|
| schema `Field.hidden` 声明位 | Done |
| notify.channels 打 hidden + 注释 | Done |
| 前端 cfgFlatten 跳过 hidden | Done |
| 前端 toggleKey 清空改删键 | Done |
| 守阵测试(后端 1 + 前端 2) | Done |
| 文档与知识库回写(基线 / 坑档 / 切片 / 档案) | Done |

## 进度日志

- 2026-10-10 09:29 用户报障; 定位到 `toggleKey` 写空列表(一处两症)
- 2026-10-10 09:35 语义三选一提问 → 用户拍板「暂时隐藏 + 注释」
- 2026-10-10 09:44 首版(摘字段)被键面守卫判删键拦下 → 改 hidden 声明位方案
- 2026-10-10 09:50 test.full 绿: 2873 passed + 4 skipped / TOTAL 99% / 23.8s(基线 26-10-10-0951)
- 2026-10-10 09:51 回写坑档 / 基线切片 / 本档案, `kb.index` 重建索引
