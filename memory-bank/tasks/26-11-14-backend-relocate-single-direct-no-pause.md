# 26-11-14-backend-relocate-single-direct-no-pause — 单成员 direct 搬迁免暂停: grilling 拍板与计划立档

**Status:** In Progress
**Added:** 2026-11-14
**Updated:** 2026-11-14
**Summary:** 单成员 direct 搬迁免暂停: grilling 三轮取证拍板 D1-D6/D4a + 计划 26-11-14-1741 入库(S1-S4 待显式开工) + 邻接面两件与新想法一件入池(topic relocate-move-window); 零代码改动
**Topics:** backend-relocate-single-direct-no-pause

**Refs:** memory-bank/plans/26-11-14-1741-plan-relocate-single-direct-no-pause.html

## 本篇只回答

「整组移动单种子被暂停」这轮 grilling 从报障观察到设计拍板走了哪条路、拍板了什么 —— 执行与验证数字归计划 26-11-14-1741 的实施批。

## 原始请求

1. 「整组移动单种子被暂停，grilling 然后出一个修改方案」
2. 观察补充:「移动前在做种，移动时暂停，完成后自动恢复，猜测是单种子也走整组移动管线导致的，需要读原设计文档重新评估是否需要将其移出管线。重新 grilling」
3. 追问:「闸门(部署/形态预检)、停滞看护(move_stalled)、全量校验(_dst_ready)、失败回执+重试账、重启恢复(_recover)、搬迁中删除拦截(D16)、WebUI 面板可见性、搬后重归组 —— 这些中哪些是对单种子真正有用的？」
4. 拍板:「Q3 qB 自己搬运行中的种子可靠性很高，靠 qB 自己维持，不需要担心。其余按推荐。既然有用，能否可以武装到『未开启整组移动』的情景？如果值得做，加入 issue」

## 思考过程与决策

三轮取证链: ①机理面 —— `_start_job` 暂停/恢复契约(`resume_hashes` 四出口恢复)、恢复单发即弃、fuse 不让路、快照陈旧窗; ②设计面 —— 原计划 26-10-18-1604 §4.1 暂停是设计第一步, 单成员 direct 是一等场景(S1 真机测过「direct 直达 done」), 本次行为 = 管线按设计工作, 无故障; ③价值面 —— 管线 8 项对单种子逐项裁决: 真有用 = 失败回声链(停滞看护/校验/回执/重启恢复)+D16 拦截, 低价值 = 重归组(下轮自愈)/面板(随 job 附带), 负价值 = 部署闸(direct 不碰 fastresume 收尾链, 纯 D4 连坐), 零成本 = 形态预检(单成员恒 direct)。

拍板 D1-D6/D4a(详表见计划 §06): D1 单成员 direct 免暂停做; D2 豁免口径=仅单成员且完成态(下载中/error/checking 仍暂停); D3 免真机先行探测(用户判定 qB 自身可靠, 推翻 agent 推荐的 P1 真机门; 失败兜底=既有停滞看护+失败回执); D4 保留 job 账与闸门只免暂停, 不做纯透传薄路径; D4a 部署闸维持 26-11-05-0808 D4「整功能禁用」原样(独立口径不混车); D5 恢复契约加固与 fuse 让路入池不修; D6 qB 侧搬迁让路与回声入池 feat。

计划外发现(入池, topic `relocate-move-window`): 恢复契约单发即弃(26-11-14-1744-bug-resume-fire-once-no-verify) / fuse 不让路 relocating_hashes(26-11-14-1744-bug-fuse-no-relocating-yield) / qB 侧搬迁零感知(26-11-14-1744-feat-qb-side-move-echo, 用户提议「武装到未开启情景」评估成立)。

## 实现计划

计划 26-11-14-1741 §04: S1 完成态判定 helper + `_start_job` 豁免判据与回执分型; S2 测试电池(完成态免暂停/下载中/error/多成员/dry-run/文案分型逐态钉扎); S3 文档回写(原计划 26-10-18-1604 §4.1 反指注记 + 切片); S4 test.full + 基线切片。

## 子任务状态表

| 步 | 内容 | 状态 |
|---|---|---|
| G1 | grilling 三轮取证与拍板 D1-D6/D4a | Done(2026-11-14) |
| G2 | 计划 26-11-14-1741 立档(Open) | Done(2026-11-14) |
| G3 | 邻接面/新想法三件入池(topic relocate-move-window) | Done(2026-11-14) |
| S1-S4 | 计划实施(完成态 helper/豁免判据/电池/回写/基线) | Open(等显式开工) |

## 进度日志

### R0 · 立档 (2026-11-14)

grilling 三轮: 机理取证(relocate_exec/relocate_lifecycle/fuse_mod/设计文档 26-10-18-1604) → 设计比对(行为=设计内, 争议收敛到单成员暂停豁免) → 价值裁决(8 项逐项) → 拍板 D1-D6/D4a。产出: 计划入库(Open, S1-S4 待显式开工)、三件入池(两条 bug 一条 feat)、任务档案立档。零代码改动、零 commit/push。

评审: 派发 2(事实口径面 / 正确性可执行面)全量评 655 行 → 轮 1 十条发现(minor 5 + nit 5, 引文 10/10 过检)全修; 轮 2 修复轮 1 nit(checkingUP 唯一分歧态名落地, 顺手修未过检不计入 修/检); 轮 3 限定复评零发现, 11 条前轮发现未回退; trailer `基 d7268c690677`。
