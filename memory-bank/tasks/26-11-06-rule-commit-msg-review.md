# 26-11-06-rule-commit-msg-review — 提交信息自动审查: ship.commit 内联三态机检落地

**Status:** In Progress
**Added:** 2026-11-06
**Updated:** 2026-11-06
**Summary:** ship.commit 在 git commit -F 前内联提交消息三态机检(硬拦/自动修/警告): 编码损伤、gitmoji 骨架、正文标签与 AI 写作残骸全走纯函数模块 msg_check.py; 逃生走 msg_check_allow 配置白名单; 正文零代改。
**Topics:** rule-commit-msg-review
**Refs:** memory-bank/plans/26-11-06-0124-plan-commit-msg-review.html

## 原始请求

1. 「提交信息自动审查: 在my-commit-flow提交脚本中自动查BOM/常见乱码/全英文/骨架格式/常见错误等等, 先补齐其它可能错误条目再分析」
2. 「要不要自动处理需要分条讨论, 要不要给逃生通道也要讨论, grilling」
3. 「Q4 标点暂时不改. 空格归一仅骨架承接处, 不改动正文. 其余按推荐」
4. 「开工」

## 思考过程与决策

- grilling 六问全拍板(D1-D6), 结论表见计划 §06: 三态框架 + 定稿矩阵 + 正文标签口径(a) + 标点不代改/空格归一仅骨架承接处 + 配置白名单逃生 + 接线七条。
- 关键实测(BOM 过 -F 不剥 / CRLF 自剥 / `#` 行保留 / 反引号语料 21/200 在用)改写了清单: 前两条决定 BOM 必查、CRLF 不查;后两条避免了两个会批量误伤的检查项。
- 计划: memory-bank/plans/26-11-06-0124-plan-commit-msg-review.html(D1-D6 拍板表、三态矩阵、拒收存档、S1-S4 步骤)。

## 实现计划

S1 msg_check.py 纯函数模块(gitmoji 全集 75 个去 VS16 归一 + review_text/check_message_file) → S2 KEY_DEFAULTS 加 msg_check_allow + config_problems 白名单 id 校验(未知 id = STOP) → S3 commit.py 接线(存在性检查后、闸门前;自动修写回留痕;失败行自带逃生提示) → S4 test_commit.py 用例(纯函数面 + 接线面)。

## 子任务状态表

| 步 | 内容 | 状态 |
|---|---|---|
| S1 | msg_check.py 模块(检测+自动修+白名单过滤) | Done(2026-11-06) |
| S2 | msg_check_allow 进 KEY_DEFAULTS + 白名单校验 | Done(2026-11-06) |
| S3 | commit.py 接线(检查点/写回/失败行) | Done(2026-11-06) |
| S4 | 测试(纯函数面+接线面+docstring 测试计划同步) | Done(2026-11-06) |

## 进度日志

### R0 · 立档 (2026-11-06)

- grilling 六问拍板后出计划、实现 S1-S4 一次走完: 包测试与 test.quick 全绿(见 kb.baseline)。
- 环境插曲: 本 clone 的 pytest/yapf console-script trampoline 全坏(坑档 venv-trampoline-clone-copy), 坑档路由命中, `uv sync --reinstall-package <pkg>` 定点重装两包即愈。
- 实现细节修正: c5 实测段数字检测剥掉标签本体再查(标签自带日期, 整段扫会永远命中)——已落代码注释与单测。

### R1 · 收口评审 (2026-11-06)

- review: blocker 清零, 修 16+留痕 1, 入池 0, 分面(3 子代理串行: 正确性/安全/测试缺口; 17 条发现全过 review.check 引文校验, 零 refute)。
- 关键修复: c2 依 200 笔语料回测降警告(初拍 D3a 前提「语料 100% 合规」系抽查 3 笔的错误断言, 用户改拍); B3 收敛到已知 gitmoji 集(旗类 RI 对曾被拆坏写回, major); SLOT 行首锚定+hash 尖括号形态移出强表; 读写两侧补瞬时锁重试; 叉号打印前缀换 ASCII; 测试 +6 例与「机检先于闸门」金丝雀。修复后语料终测硬拦 4/200(全为真违反), 自动修零触发。
- 计划文档 kb.bump 至 R1(§03 矩阵/§06 D3 修正/变更记录同步)。
- 范围说明: 本轮触碰过无关任务切片 26-11-04-1047-webui-relocate-visibility 的 R3 行一处(裸数字改「见 kb.baseline」)——非计划内清扫, 是措辞守卫判红挡住提交后的最小解锁修复(7d603fb1 先例同款), 已随 771b8d8e 入库并在提交信息与收尾报告披露。
