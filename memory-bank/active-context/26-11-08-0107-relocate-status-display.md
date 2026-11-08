# relocate-status-display

> 摘要: 迁移状态展示 v2 计划 26-11-07-2344 实施完成: S1 组级聚合补 src(去重唯一值) / S2+S4 撤 rel-badge 药丸改着色 A→B 两排+右缘弧形箭头(relocateView 单点+指纹补 src+零点击) / S3 悬停浮窗 relocate_pop.js 照 hrPop 同参(120/160/零请求行载荷)+ --path-src 四皮肤令牌(D15 当前位置固定色) / S5 守阵红验转绿+chain:406 死断言改活断言 / test.full 5635+2 基线 26-11-08-0050; 视觉规格件 plans/attachments/relocate-status-display-v2-mockup.html
> 最后活动: 2026-11-08 08:25

**R0(2026-11-08 01:07):** 迁移状态展示 v2 计划 26-11-07-2344 实施完成: S1 组级聚合补 src(去重唯一值) / S2+S4 撤 rel-badge 药丸改着色 A→B 两排+右缘弧形箭头(relocateView 单点+指纹补 src+零点击) / S3 悬停浮窗 relocate_pop.js 照 hrPop 同参(120/160/零请求行载荷)+ --path-src 四皮肤令牌(D15 当前位置固定色) / S5 守阵红验转绿+chain:406 死断言改活断言 / test.full 5635+2 基线 26-11-08-0050; 视觉规格件 plans/attachments/relocate-status-display-v2-mockup.html

**R1(2026-11-08 08:25):** R3 批次: 用户报 pair 模式原 save_path 行漏删(实施缺口)+ 新拍板 D16/D17(路径 chip 点击筛选 + 位置集匹配, grilling 两轮定稿)。落地: ①xtpl-cells 两分支 pair 隐藏原单排路径行, A/B 排 +f-cell 可点 filterFromChip + 独立 f-on; ②decorate.js 新 _pathPositions 位置集单点(save_path 恒参与, 进行中三态 src/dst 并入, done/cancelled 历史位置不参与), filters.js 三消费点 + hr.js _memberPass 换用, 弹层 pathOptions 自动纳位置集; ③守阵红验先行(3 例对旧生产红)转绿; ④e2e 新 spec relocate-pair-filter 两皮肤全过(注入四粒桩在行窗口外, 需先点添加于切升序——踩坑已记计划 R3); ⑤批次评审全能档 4 发现全过检全修(注释漂移 D16/D17 口径); ⑥test.full 5753+2 基线 26-11-08-0825; e2e 全量 460 过/2 红为存量 move-note strict violation(入池 26-11-08-0820, 与本批无关); ⑦计划 R3 回写 + webui.md 口径段同步

**R2(2026-11-08 09:55):** 提交期撞闸门死锁(issue 26-11-08-0903: 锚点在合并拓扑下树差虚增 ~9600 行, 实算 9910 vs 真实 272), 用户授权修锚点算法: anchor_commit 加 --first-parent + _numstat 改「主线逐笔 + 侧分支无 trailer 连坐 + remerge 冲突解决面」(二轮评审 major 加固: 无 trailer 侧支被干净合并不得整类漏计), test_review_pkg 86 全过(新增合并拓扑回归 2 条); issue 0903 置 Done。批次实算 674 行(>400)走两轮派遣: 全能档 R3 评审(4 发现全修) + 工具/文档面二轮(major 1 + minor 2 + nit 1 全修)。

**Refs:** memory-bank/issues/26-11-08-0903-bug-review-anchor-merge-topology.html
