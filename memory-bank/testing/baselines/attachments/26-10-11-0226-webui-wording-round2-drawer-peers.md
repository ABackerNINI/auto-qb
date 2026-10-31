# 3112 —— WEBUI 文案二轮补漏(抽屉/用户页, 报告 §11)基线

> 摘要: 用户复查指出一轮实施漏了种子详情面板与用户页的大批文案。二轮清点面扩到抽屉全部 classic 页插件(`drawer_pages/` 4 文件)与全部 15 变体(`drawer_tpl/`), 基准仍逐词抽本机 qBittorrent zh_CN 译文。落地: 用户页表头族(对端→IP/地址、Flags→标志、正在取→文件、下载/上传→下载速度/上传速度、已发/已收→已下载/已上传、关联/关联度→文件关联、会话已发/收→会话已上传/下载); tracker 状态词(正常→工作、失败/未连接→未工作、警告→未联系、未启用→禁用、添加 tracker→添加 Tracker、下次汇报→下次重新汇报); 文件优先级(跳过→不下载、普通→正常 —— 一轮 §05 标「保持」系误判); general 残留(分块→区块、首末块优先→先下载首尾文件块、用户(下载)→用户、tracker→Tracker 大小写)。shared 17 文件 ~92 处 + `resources/detail-panel-templates/` 12 文件 72 处 + e2e `drawer-peers-columns.spec.mjs` 1 处 + 守阵错误态文案 3 处。刻意不动: 自有概念(吸血嫌疑/内网/闲置同伴/占用/汇报层级/跳过校验胶囊)、qB 未收录词(更新中/分配中)、变体头注释。报告 §11 有全表。
> 基线时间: 2026-10-11 02:26

**Refs:** memory-bank/tasks/26-10-10-webui-wording-unify.md,memory-bank/reports/26-10-10-2237-report-webui-wording-unify.html

## test.full 实测

- 分支: `develop`(会话开工 `my-commit-flow.sync` 已同步 `1d7c864b`; 工作树含二轮全部文案/守阵改动时实测)
- 命令: `commands run test.full`
- **实测 (Windows)**: **3112 passed + 4 skipped, 0 failed, 覆盖率 TOTAL 99%**
  (16586 语句 / 156 未覆盖 / 5724 分支 / 143 partial; 门槛 98% 达标; 本轮 26.9s)
- 前置机检: 改动 JS 全量 `node --check` 通过; `test.quick` 首跑抓出守阵钉的旧错误文案 3 处, 同步后绿。
- 改动面(摘要): `src/auto_qb/webui/static/shared/`(drawer.js + drawer_pages/ 4 + drawer_tpl/ 01-12 + tpl/ctx-menus.html + tpl/dialogs-mgr.html, 17 文件 ~92 处)、`resources/detail-panel-templates/` 12 文件 72 处、`tests/test_webui_static_dom_panel.py` 3 处、`e2e/drawer-peers-columns.spec.mjs` 1 处。
- 未纳入本轮(刻意不越界): 术语常量单点化、`config_hub.js` schema 字段标签(上传限速/下载限速, 配置域)、三皮肤 CSS 注释、变体头注释里的旧词。
