# 26-11-11-webui-pinned-matrix-guard — 必显列悬停行为守阵全矩阵扩面 + search-hit 停靠点收紧 220px

**Status:** In Progress
**Added:** 2026-11-11
**Updated:** 2026-11-11
**Summary:** 必显列悬停行为守阵全矩阵扩面 + search-hit 停靠点收紧 220px
**Topics:** webui-pinned-matrix-guard

## 本篇只回答

「主表固定列(名称列)hover 背景与其它列不一致」这轮的取证结论、守阵扩面落地与 search-hit 停靠点定案; 领域判据单点在 pitfalls/web-ui/frozen-column.md(已回写), 本档案只记过程与决策。

## 原始请求

1. 「WEBUI主表下载状态种子固定列"名称"列在hover时背景与其它列不一致,其它状态可能也存在,该问题已出现过多次,这次要查清楚根因,彻底堵死」。
2. (拍板一)现场答: 最新版、flux、未开行语言; 堵死方案选「守阵扩面到全矩阵(推荐)」—— 新建 e2e spec。
3. (拍板二)search-hit 尾差修法选「收紧衰减段(推荐)」—— 行板与首格镜像停靠点改固定 220px, 不做行宽管线、不只钉守阵。

## 思考过程与决策

- **取证**(桩服务 ui_harness + Playwright, 五类量法): 四皮肤(prism/atlas/console/flux, flux 默认带 fx glass)× 行语言 flat/wave × prism ocean/frost × 行状态(下载/做种/校验/暂停/其它)× 组合态(选中/展开/search-hit)× 动态(悬停跨 poll 6s、30 次快速滑入滑出)—— 计算样式逐帧、可见底色逐层 alpha 合成、截图像素地面真值全部 Δ0。**当前 develop 树无法复现用户报障**; 排除陈旧 CSS(no-cache 全覆盖)、poll patch 打断(v-for 稳定 key)。
- **结构性根因**: 名称列(吸左首格)与行板是两个承载物, 「底色表达式逐字相同 + 过渡同源 --dur」不变量靠每个绘制面各自手写; 历史 ≥5 轮复发各因不同(坑档 frozen-column 06/07/08/09/10 各条 + row_lang 重构 + flux fx D4-1)。守阵盲区 = 行为面 e2e 只跑 prism+atlas × 默认 flat × 通用行。
- **守阵扩面**(决策 D-扩面): 新建 e2e/main-table-pinned-matrix.spec.mjs —— 四皮肤 flat + prism/flux wave × 状态行逐帧+稳态像素 × 组合态; **必须钉 colorScheme=dark**(否则 prism 落 frost, row_lang 被排除, wave 假覆盖——首跑后由评审抓出); wave 不做 computed 逐帧断言(行板/首格表示本就不同, 像素地面真值承担)。
- **search-hit 尾差**(守阵首跑抓到的真问题): 停靠点 46% 按各自宽度解析, 行/首格几何分家, 名称列尾部静态差 Δ20-28(atlas 28)。修法拍板 = 固定 220px(收紧衰减段), 拒绝「行宽 ResizeObserver 管线」(工程量大)与「只钉守阵」(残留已超可辨阈)。
- **评审批次**: 分面 2(正确性/测试缺口)→ 修 6(2 major: wave 非斑马 search-hit 零覆盖、colorScheme 未钉; 4 minor)→ 复评轮 1 轮(5 修复核验在位 + 1 minor zebra 标注改实测)→ 检 6/6 过, 零 actionable。

## 实现计划

总体思路: 先取证定性(不可复现 + 守阵盲区), 再以守阵扩面为「堵死」主体, 守阵首跑暴露的 search-hit 残留按拍板修复, 红绿双验后回写坑档。

## 子任务状态表

| 步 | 内容 | 状态 |
|---|---|---|
| 1 | 取证: 五类量法全矩阵测量(临时探针, 已删) | Done(2026-11-11) |
| 2 | 守阵扩面: e2e/main-table-pinned-matrix.spec.mjs(24 用例) | Done(2026-11-11) |
| 3 | search-hit 停靠点 220px(8 CSS 文件 + row_lang 6 处 + 注释) | Done(2026-11-11) |
| 4 | 静态守阵改钉(镜像+行板双侧 + row_lang 生效层 1b 段) | Done(2026-11-11) |
| 5 | 红绿双验(e2e 首跑红 6 → 绿 24; 静态红验 ×2) | Done(2026-11-11) |
| 6 | 分批评审 2 面 + 复评 1 轮, 修 6, 检 6/6 | Done(2026-11-11) |
| 7 | 回写坑档 frozen-column(⑦ 定案 + 量法教训 + 守阵清单) | Done(2026-11-11) |

## 进度日志

### R0 · 立档 (2026-11-11)

取证→守阵扩面→search-hit 收紧→评审两轮全修→全量绿(见 kb.baseline, 基线切片 26-11-11-0346; 行为守阵矩阵 spec 24 用例全绿)→坑档回写。未提交(待用户显式指令)。

- 2026-11-11 03:47 取证(五类量法全矩阵, 当前树不可复现)+守阵扩面 spec(24用例)+search-hit 停靠点收紧 220px(静态/行为双层红绿双验)+评审 2面1复评轮修6检6过6+全量绿(基线 26-11-11-0346)+坑档 frozen-column 07 定案回写
