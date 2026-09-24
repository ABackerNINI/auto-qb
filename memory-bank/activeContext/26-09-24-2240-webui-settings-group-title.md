# 新版设置首页: 「连接 qBittorrent」→「常规」

> 摘要: 新版设置(Console Hub)首页第一张卡标题窄于内容 —— basic 组除 qB 连接还有主循环节奏 / 数据目录等常规项; 已改标题 + desc/lede + 一处交叉引用。
> 触发: 设置页分组标题, 连接 qBittorrent, 常规, HUB_GROUP_META, Console Hub, config_hub.js, 文案与内容不符
> 最后活动: 2026-09-24 22:40

## 状态

**Done**(2026-09-24, 文案级小修, 未立项 —— 低于立档阈值)。用户报「第一页是『连接 qBittorrent』, 实际包含了常规设置」。

**根因**: `src/auto_qb/webui/static/shared/config_hub.js` 的 `HUB_GROUP_META.basic.title` 是按 schema 里
`qbittorrent` 子段取的标题, 但 `basic` 组**还有** `main_tick` / `sync_interval` / `state_save_interval` /
`max_tasks_per_tick` / `interval` / `data_dir` / `state_file` 七项常规项
(见 `config/schema/groups.py:8-105`) ⇒ 标题窄于内容, 属于「文案与内容不符」这一老毛病(同 R10-14「高级能力」→「更多操作」)。

**改法**(只动共享层, 棱镜/图集两套 UI 同生效):
- `HUB_GROUP_META.basic.title`: 「连接 qBittorrent」→「**常规**」, 并加一行注释说明为什么不是「连接」。
- `desc` / `lede`: 原句只讲 qB 连接, 重写成「上半部分连 qB, 下半部分是运行节奏 / 一轮干多少活 / 数据放哪」,
  与新标题对齐(标题改了而描述不改, 是同一处毛病的另一半)。
- `HUB_HELP["qbittorrent.port"].rel` 里的「连接 → 主机」→「常规 → 主机」 —— 交叉引用按分区标题写, 不改会指空。
- schema 侧 `Group("basic", "基础", ...)` **不动**: 那是经典版左导航标签, 经典版没有这层改写。

**验证**: `node --check src/auto_qb/webui/static/shared/config_hub.js` 通过;
全量 `test.quick`(剥掉本 shell 注入的 `PYTHONUTF8=1` 等) **1376 passed + 1 skipped**,
与 [testing/baseline.md](../testing/baseline.md) 一致(只改文案, 未加用例, 基线不动)。
传播面: 首页卡片标题 / 二级页大标题 / 面包屑 / 风险清单 `groupLabel` 都取同一个 `meta.title`, 一处改全生效。

## 未做(等拍板)

- `resources/settings-page-templates/01..05` 五份**样张**仍写「连接 qBittorrent」(`05-console-hub` 是本页的复刻源)。
  样张是设计稿快照, 是否跟着实现改由用户定 —— 按范围守恒未动。

## 指针

- [文案口径(改名的理由)](../conventions/webui.md)
- [同类旧案: 子菜单名窄于内容](../plans/26-09-17-0901-webui-fix-plan-round10.html)
