# 规则系统可行性实验: 禁止 IYUU辅种 分类种子开始下载(报告已落盘, 随本提交入库)

> 摘要: `想法.md` L298 的可行性实验。结论: **条件侧完全支持**(`category` 条件 / `expr` 的 `tor.category`), **动作侧只有 `stop`** —— 能表达「永远不处于下载方向状态」的**持续压制**, 不是「禁止开始下载」的预防保证(种子由 IYUU 直接加进 qB, 本程序只能在同步节拍 1.5s 后事后发现)。推荐形态 = `trigger: on_torrent_added` 立即压制 + 缺省 interval 每 tick 兜底, 条件必须带 `state: ["is_downloading"]`(只按分类会误伤做种; 但该状态集含 `checkingDL`/`metaDL`, 会挡住校验 ⇒ 只等校验做种的辅种有副作用), 且**不能**配 `execute_once: once/daily`(实测第二轮起漏过)。真正闭环需新动作(整种子文件优先级置 0 —— qB 层已有此手段, WEB UI 有手动入口, 规则动作集没有)或加入端暂停。报告 `reports/26-09-27-0047-report-rule-iyuu-stop-guard.html`; 档案 `tasks/26-09-27-rule-iyuu-stop-guard.md`。
> 最后活动: 2026-09-27 00:47

## 已完成

- 读码取判据(条件/动作全集/绑定/触发时机/spec 约束)+ 配置期校验实验(`interval: 0S` 与裸枚举 `state` 实测被拒)
- 行为级内存 Fake 实验: 状态矩阵 8×3(只按分类会误伤 uploading/stalledUP)+ 去重对照(never 每轮压制 / once 漏过)
- 报告落盘(26-09-27-0047, 单文件 dark, 含证据索引与附注); 档案立档; 切片新建
- 收尾: 蒸馏 `26-09-22-2221-backend-cross-group-file-conflict` 切片(活线索已在 Open issue 内)守 40 上限; 坑 `pitfalls/testing/tmpdir.md` 复发 +1

## 待办

- **随本提交入库**(报告 + 档案 + 切片 + 索引 + 基线切片)
- **待用户拍板**: ①要不要新增「阻断下载」动作插件(整种子文件优先级置 0)把语义真正闭环 ②`test_yamls/test_actions/*.yml` 五份样例的 `log_level` 漂移要不要修或入池(本轮按范围守恒未动)
- 真机走查(可选): 若采纳压制规则, 需真机确认「新增辅种种子在两轮内被暂停」与「做种中的同分类种子不被误停」