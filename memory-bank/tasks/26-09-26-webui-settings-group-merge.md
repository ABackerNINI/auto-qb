# 26-09-26-webui-settings-group-merge — 设置页分组合并: 日志/界面(WebUI)/通知/运行日志 并入「常规」

**Status:** Done
**Added:** 2026-09-26
**Updated:** 2026-09-26
**Summary:** schema groups.py 把 log/web/notify 三段并进 basic 组删三个独立分组(首页 10 卡→6 卡), WebUI 界面卡改名 WebUI, 运行日志移入常规分区页尾; config_hub.js/atlas/prism 配套收口, test_config_schema_endpoint 守阵同步; 全量 1665 passed + 1 skipped, TOTAL 92%。

## 原始请求

> 将设置页中的日志/界面(改为WebUI)/通知/运行日志放到"常规"中

用户随后「继续」(收尾验证)与「提交」(走提交流程)。

## 思考过程与决策

- **「日志/界面」的解析**: 设置页(Consola Hub)首页卡片里实际是「日志」与「界面」两张卡(HUB_GROUP_META.web.title="界面"), 「(改为WebUI)」紧跟「界面」⇒ 解析为四项并入常规: 日志、界面(改名 WebUI)、通知、运行日志。日志落盘设置(等级/轮转/格式)语义上不属于 WebUI, 故不并成一张「WebUI」大段。
- **改动单点选 schema 而非前端 hack**: 坑库 search-views.md 定案「config/schema 是设置页表单唯一描述来源」, 首页卡片 = schema.groups 一对一映射 ⇒ 在 `groups.py` 合并分组后, 卡片/搜索直跳/风险清单/分组标签全部自动跟随; 前端只需处理 schema 之外的 `__logs` 特制卡。
- **CLI 无影响**: GROUPS 只经 `schema_payload()` 下发 WebUI, CLI 不消费; `validate_config` 键集合不变(test_config_schema 守卫确认)。
- **LED 语义**: basic 恒为核心分区, 不进 HUB_OFF_KEYS(web/notify 条目删除); web.host 非 127.0.0.1 的暴露警示从原「界面」卡挪到「常规」卡。
- **存量偏好兼容**: 浏览器 localStorage 里存过 `hub.view="__logs"` 的, hubRestore 先映射成 `basic` 再做 schema 校验(复用 hubGo, 守阵 1431 行钉住的四件事不受影响)。
- **并行会话协作**: 提交前发现同 clone 有并行会话 07:11–07:19 落了「按钮体系」提交(7b05c0c)并合并远端(079a587, 含 schema_version 字段进了 basic 组); 对方已按 hunk 过滤把本线改动排除在其提交外, 本线 7 文件未暂存 diff 纯净, 组合树重测 1665 passed 全绿后继续提交。

## 实现计划

1. `config/schema/groups.py`: basic 组 help 更新; state_file 之后并入 log/web/notify 三个 object 段(web 段 label「WEB UI」→「WebUI」及段内文案同步); 删除 logging/web/notify 三个 Group。
2. `config/schema/__init__.py`: 文档行「左导航 8 分组」→「6 分组」。
3. `config_hub.js`: HUB_GROUP_META.basic 文案重写、删 notify/web/logging 三条; HUB_HELP 三处 rel 引用「界面 →/通知 →」→「常规 →」; HUB_OFF_KEYS 删 web/notify; hubCards 删 `__logs` 特制卡; hubNow 删 `__logs` 分支; hubGo 懒加载挂到 basic; hubRestore 映射存量 `__logs`; hubLedOf web→basic; hubReadout 删 web/notify/logging 三 case(其中 logging case 原本就读不存在的 `config.logging.level`, 属死代码随合并消失)。
4. atlas/prism index.html 成对: 删 `__logs` v-else-if 分区模板, 运行日志块移入普通分区模板尾部 `<template v-if="hub.view === 'basic'">`; 顶栏注释「日志在设置"运行日志"章节」→「常规章节页尾」。
5. `dialogs.js` loadLogs 注释入口位置更新。
6. 守阵: `test_web.py::test_config_schema_endpoint` 分组表断言更新 + 加断言 basic 尾三段为 log/web/notify。

## 子任务状态表

| # | 子任务 | 状态 |
|---|---|---|
| 1 | schema 分组合并(groups.py + __init__.py 文档行) | ✅ |
| 2 | config_hub.js 收口(META/HELP/OFF_KEYS/卡/now/go/restore/LED/readout) | ✅ |
| 3 | atlas + prism 模板成对改(`__logs` → basic 页尾) | ✅ |
| 4 | 守阵同步 + test.quick/test.full 全绿 | ✅ |
| 5 | 事实回写(core-domain.md / progress / 基线切片) | ✅ |
| 6 | 提交 + 推送 Gitee | ✅ |

## 进度日志

- **2026-09-26 04:3x–07:1x**: 会话开始同步(c010afb → 2712804 ff); 定位分组单点在 schema; 完成 7 文件改动; test.quick 首轮红 1 条(test_config_schema_endpoint 断言旧分组表, 属计划内同步) → 修后 1640 passed; 组合树(含并行 versioning/button 测试)复跑 1665 passed + 1 skipped。
- **2026-09-26 07:5x**: 收尾回写踩两条守卫 —— ①坏链(档案未建时 progress 已引用, 建档即修); ②implemented-webui.md 超 evergreen cap(10,512 > 10,000), 按既定机制把 2026-09-15 三条外迁 `implemented-webui-history.md` 轮转解决。本会话另踩已记坑 TMPDIR 手工前缀一次(pitfalls/testing/tmpdir.md 复发 +1, 没命中原因: 写冒烟命令时凭习惯手拼 `TMPDIR=x pytest`, 没走 `commands run`, 路由到了 testing 类但没回读该条)。test.full 落基线切片 `26-09-26-0802-webui-settings-group-merge`(1665 passed + 1 skipped, TOTAL 92%)。
