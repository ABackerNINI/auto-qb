# 2960 —— WEBUI Tracker 状态卡片栅格卡片等高(虚拟合并卡去描述)基线

> 摘要: 用户报「种子详情面板『状态卡片栅格』的虚拟条目卡片高度与其它的不一致, 需改为一致; 加守卫强制要求; 移除『私有 tracker 种子: DHT / PeX / LSD 已由 qB 禁用, 状态恒为『未启用』, 不参与汇报』的描述」—— 根因 = 变体 04 栅格写死 `align-items:start`(同排卡片各按内容高度, 不等高), 虚拟合并卡又比实体卡多一段设计稿 footer 长描述(真浏览器实测: 未启用实体卡 69px vs 虚拟卡 100px)。口径(用户拍板「同排等高」)= 栅格改 `align-items:stretch`(同排卡片自动齐平, 虚拟卡与其同排实体卡恒等高)+ 虚拟合并卡移除描述行只留 head + chips。1 个源文件 + 1 个测试文件(新增守阵 1 个测试函数), 不命中立档阈值, 切片沿用 26-10-06-0751(同专题追加)。
> 基线时间: 2026-10-10 19:19

**Refs:** memory-bank/activeContext/26-10-06-0751-webui-detail-panel-design.md

## test.full 实测

- 分支: `develop`(会话开工 `my-commit-flow.sync` 核验 `d1957be5`; 工作树含本轮改动 + 回写件时实测)
- 命令: `commands run test.full`(Windows, 单次采样 —— 耗时口径见 [../baseline.md](../baseline.md)「必须带区间」)
- **实测 (Windows)**: **2960 passed + 4 skipped, 0 failed, 覆盖率 TOTAL 99%**
  (16568 语句 / 165 未覆盖 / 5716 分支 / 142 partial; 门槛 98% 达标; 29.18s)
- 增量明细(本轮真正新增): `src/auto_qb/webui/static/shared/drawer_tpl/04-trackers-status-cards-tall.js` 为原文件修改(栅格 `align-items:start`→`stretch` + `virtualCardHtml` 删描述行); `tests/test_webui_static_dom_panel.py` 新增守阵 `test_drawer_tpl_trackers_card_uniform_height`(收集面 +1); 回写件 `progress/implemented-webui.md` 新条目、切片 26-10-06-0751 追加; 本基线切片。
- 静态守阵红验: 把来源文件的 `align-items:stretch` 改回 `start` 时, 新守阵报 `AssertionError: .dt04-grid 必须 align-items:stretch`(RC=1), 改回即绿 ⇒ 守卫有效。
- 真浏览器实测(prism, 1440x900, 桩 3 real + 3 virtual; 临时 e2e 探针跑后已删, 非入库制品): 修复前 未启用实体卡 **69px** / 虚拟合并卡 **100px**(不同高); 修复后同排两卡均 **75px**(等高), 且虚拟卡文本不再含描述文案。
