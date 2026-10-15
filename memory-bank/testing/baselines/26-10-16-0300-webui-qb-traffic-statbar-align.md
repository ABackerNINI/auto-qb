# 3405 —— 流量图统计栏三挂点对齐(统计栏子项垂直居中) 执行基线

> 摘要: 用户动议「流量图统计栏未对齐, 比如『上传/下载图例』与『窗口 xxx桶』后者更高; 还有后面的视图切换按钮与纵轴切换按钮; 所有流量图都对齐」。真浏览器量布局定位到根因: 流量图统计栏 `.hist-summary` 是 flex 而**未写** `align-items` ⇒ 默认 `stretch`, 纯文本读数(「窗口 N 桶」/上传累计/下载累计)被拉到与控件组同高、文字**贴顶**(实测墨迹 y=832), 而自带 `align-items: center` 的图例(`.hs-leg`, y=835.7)与控件组(`.qb-statctl` 内的档位/纵轴按钮, y=836)内容居中 ⇒ 三族文字落成两条线(错开 3.7~4px)。修法 = 三皮肤 `.hist-summary` 显式 `align-items: center`(一处规则, 三挂点全局/分组/单种共用同一段模板故一次全覆盖; 顺带让 popovers 今日流量弹层的统计栏同款对齐)。守阵 +1 条断言(三皮肤成对: `.hist-summary` 必含 `align-items: center`, 零新增测试函数)。实测: 三皮肤 × 三挂点 × 纵轴 auto/manual 共 18 组, 图例/窗口/累计三族文字 y 逐组同值、档位与纵轴按钮同线(prism/atlas 836 vs 835.7 = 0.3px 子像素, console 全等 838); manual 模式输入框出现后行高仍 33px 不串行。e2e fast 166 用例全绿。
> 基线时间: 2026-10-16 03:00

**Refs:** memory-bank/activeContext/26-10-09-0740-webui-qb-traffic-seed-header-controls.md

## test.full 实测

- 分支: `develop`(会话开工 `my-commit-flow.sync` -> 已同步 5f7c730a; 工作树含本轮改动时实测)
- 命令: `commands run test.full`(Windows)
- **实测 (Windows)**: **3405 passed + 4 skipped, 0 failed, 覆盖率 TOTAL 98%**

| 面 | 语句 | 未覆盖 | 分支 | partial | 覆盖率 |
|---|---|---|---|---|---|
| TOTAL | 17334 | 185 | 5842 | 159 | 98% |

- 耗时: 152.5s(单次采样, 区间口径见 `testing/baseline.md`)
- e2e: `E2E_PORT=8337 commands run dev.e2e -- --grep @fast` 166 passed
  (默认 8137 被**残留桩**占用 -> 按 `e2e/harness.mjs` 的排障口径换干净端口复跑, 不是复用旧服务)
- 本轮零新增测试函数; 守阵只加一条断言(三皮肤 CSS 成对锚 `align-items: center`,
  加在 `tests/test_webui_static_dom_panel.py` 既有的「CSS 三皮肤成对」段内)。
- Linux (WSL 沙箱) 本轮未重测 —— 改动全在纯静态前端层与静态守阵, 无平台分支。

## 包内脚本测试

- 本轮未触碰 `.commands/` 与 `.agents/skills/commands/`, 未跑 `test.pkg`; 提交闸门按 match 规则自判。
