# tracker URL 源头脱敏(计划, 未开工)
> 摘要: 把凭据脱敏从"日志出口"提到 **qbapi 拉取即脱敏**。**计划已产出并两轮更新, 未开工, 未提交**。三条关键结论: ① 没有代码依赖 `passkey` 值本身, 但有**两处依赖完整 URL**(移除 tracker 的定位键 · 汇报基线当 dict key); ② 顺带查出**第二个泄露面** `GET /api/torrents/{hash}/trackers` 是 qB 透传、完整 URL 直发浏览器(不在 `/api/log`, 上轮守阵扫不到); ③ 用户定了 **W3 收窄为「只保留添加 / 删除」**(编辑下线) + **mask 形态**(保形状 + 值全 hash) + **删除改为「传 hash + mask URL, 当场重取、用完即弃」** —— 原文**不再常驻内存**。
> 触发: tracker URL, passkey, 凭据, 脱敏, 泄露, 源头脱敏, mask, 编辑下线, 汇报基线, reannounce, 仓库体检, 工作区文件消失
> 最后活动: 2026-09-23 19:30

## 状态

**计划**: [../plans/26-09-22-1801-tracker-url-source-sanitize-plan.html](../plans/26-09-22-1801-tracker-url-source-sanitize-plan.html)
(基树 `00c61f8`; 行号已按包结构重构后的 `core/` · `infra/` · `webui/` 重取)。

**已定的口径**(两轮讨论得出):
- **形态 = mask**: 保留 scheme / host / path 与**参数名**, query 里**所有值**一律 hash(`https://site/announce?passkey=9f2c…`)。
  取代「只留主地址」—— 唯一性天然保持、诊断信息更全。**铁律: 不按参数名挑**(只 hash `passkey` 就是退回黑名单);
  hash 必须确定性、不加盐, 长度 ≥16 位。
- **W3 收窄**: 编辑功能整个下线(前端删 `trackerEdit` 与入口; 后端移除 `trackers/edit` 路由、
  `_cmd_edit_tracker`、命令表 `edit_tracker`)。改 passkey 退化为「移除旧的 + 添加新的」两步。
  连带好处: 「弹窗预填原文」这个最敏感的点自动消失。
- **删除的写路径 = 「当场重取 + 用完即弃」**(2026-09-23 19:25 用户方案, 取代序号 + 列表指纹):
  前端只传 `hash` + 待删的 **mask URL**; 后端当场重拉完整列表、逐条 mask 比对, 命中即取该条原文调 qB,
  **原文随局部变量立即丢弃**; 命中 0 条或多条 ⇒ error 回执不猜。
  **方案 B 因此从「双轨」变成「单轨 + 瞬时原文」** —— mask 保住唯一性 ⇒ 脱敏值本身就是可用的**内容标识**,
  于是序号 / 指纹 / 映射表全都不必要了, 且内容标识天然不怕列表重排。原文暴露窗口从
  「整个进程生命周期」缩到「一次调用的毫秒级」。
- **W4 已删除**(上一轮复核撤回「基线改 key」): 基线全程在进程内、不越界, 切到脱敏值反而会因
  同 host 多 tracker 撞 key 而静默漏判。现波次 = W1 归一化 → W2 收口详情 API → W3 收窄 → W4 守阵。
- **W1 覆盖面**: 读取**不是单一入口** —— 除 Facade(`core/qbapi.py:322`)外有 4 处直读原始 `client`
  (`webui/commands.py:161` · `webui/runtime.py:269` · `webui/server/routes/torrent_detail.py:37` · `webui/views.py:119`),
  **只改 Facade 会漏掉后四处**。

**本轮另做的两件事**:
1. **仓库体检**(用户要求): 结论**健康** —— fsck 0 问题 · ref 三处一致 · 1629 跟踪文件零缺失 ·
   全量 **1191 passed + 1 skipped**(= 当时基线)。
2. **踩坑并记账**: 快进后 **19 个文件从工作区消失**(HEAD 与索引都在, 与被改动的 208 文件交集为 **0**),
   已 `git restore --worktree` 还原并复查稳定。确认为 [../pitfalls/git/history-integration.md](../pitfalls/git/history-integration.md)
   那条坑的**复发**, 且**证明了快进也会触发**(原记录只写"非快进")—— 已放宽该条适用范围 + 补 `复发: 1` + 写明没命中的原因。

## 待办(下一步从这里接)

1. **决策点 4**(唯一剩下的): 是否先做 **W1 + W2** 止血 —— 不碰写路径、不改操作习惯, 零行为风险,
   先把裸奔的详情 API 堵上。我建议先批这两个。
2. **提交**: 计划文档(未跟踪)+ pitfalls 复发记账 + 本切片,**用户尚未说「提交」**。
3. **环境待用户处置**: 机器上有一批**跨 clone 的僵死进程**(`auto-qb-clone1` / `clone2` / `long-seeding` 的
   `ui_harness.py` / `serve.py` / `uv run`, 最久 18h+), 一度让 `uv` 构建报 `0xc0000043`。
   **按跨仓库红线我没有杀任何进程**, 交由用户决定。

## 单点指针

- 计划全文(含可行性分析 · 三方案对比 · 波次 · 风险 · 决策点) → [../plans/26-09-22-1801-tracker-url-source-sanitize-plan.html](../plans/26-09-22-1801-tracker-url-source-sanitize-plan.html)
- 已修的日志端脱敏(issue) → [../issues/26-09-21-1408-bug-web-tracker-url-passkey-log.html](../issues/26-09-21-1408-bug-web-tracker-url-passkey-log.html)
- 凭据脱敏长效约定 → [../conventions/code-style.md](../conventions/code-style.md)「日志规范」
- 合并后工作区文件消失(含快进) → [../pitfalls/git/history-integration.md](../pitfalls/git/history-integration.md)
