# 2873 —— 通知渠道设置项暂不图形化(Field.hidden)基线

> 摘要: 用户报「通知渠道勾选 platform 后取消仍提示有改动未保存, 取消后保存报 config.notify.channels: 必须是非空列表」→ 根因是 keyed_list 的 toggleKey 清空时写空列表(与"键缺失"不同构 ⇒ 脏标记消不掉; 空列表又被校验层拒); 处置 = 加 schema Field.hidden(键留在配置契约里, 只不进 UI 渲染) + toggleKey 清空改删键(与 cfgItemRemove 同口径)。新增守阵 3 个测试函数。
> 基线时间: 2026-10-10 09:51
> 档案: memory-bank/tasks/26-10-10-webui-notify-channels-hidden.md

**Refs:** memory-bank/tasks/26-10-10-webui-notify-channels-hidden.md,memory-bank/activeContext/26-10-10-0951-webui-notify-channels-hidden.md

## test.full 实测

- 分支: `develop`(HEAD `4afd2f4b`; 工作树含本专题 6 文件改动 + 回写件时实测)
- 命令: `commands run test.full`(Windows, 单次采样 —— 耗时口径见 testing/baseline.md「必须带区间」)
- **实测 (Windows)**: **2873 passed + 4 skipped, 0 failed, 覆盖率 TOTAL 99%**
  (16568 语句 / 167 未覆盖 / 5716 分支 / 143 partial; 门槛 98% 达标; 23.8s)
- 与上基线的差值: `commands run kb.baseline -n 2` 现列(切片正文只写自己的 TOTAL, 不抄逐位对比)。
- 增量明细(本轮真正新增): `src/` 3 文件(`config/schema/fields.py` 加 hidden 声明位 / `config/schema/groups.py` notify.channels 打 hidden / `webui/static/shared/config_editor.js` cfgFlatten 跳过 hidden + toggleKey 清空改删键)、`tests/` 2 文件(新增守阵 3 个测试函数)、`docs/configuration.md` 一行说明。
- 冒烟门禁: `npm run test:e2e:fast` 本轮未跑(改动面为 schema 声明位 + 前端扁平化单点, 无 e2e 覆盖该字段; 设置页不再渲染该项, 现有 e2e 收集面无断言落在其上)。
