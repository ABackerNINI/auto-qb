# 非活跃种子禁强制汇报(qB 口径 · 四入口接线 + 混选投递收敛)

> 摘要: 用户要求「WEBUI 非活跃状态的种子不允许强制汇报, 包括右键/详情面板, 按钮变灰不可点击, 与 qb 的行为保持一致」。口径 = qB 原样(commit `aa189a7` / issue #12080: 暂停/停止 · 排队 · 校验中 · 错误/文件丢失 均不许, 多选按"任一活跃即可用"), 三问已由用户拍板。落点四处: 判定单点 `decorate.js`、显示层 `ctx-menus.html` 四支 + `drawer_tpl/04|05|06` 重报钮置灰、行为层 `_actCore` / `_kbAct` / `torrentCmd` 各一道闸。**后续轮(20:32)**: 用户追问「混选会不会导致汇报非活跃种子」→ 成立, 且危害不在"汇报"(qB 引擎本就空转)而在**我们自己的确认层**(非活跃目标白等 item deadline 后落假「未确认」, 把干净的成功报成部分失败; qB 无 per-target 回执故不显此症)。用户三项拍板后补**第二层: 投递收敛** —— 前端单点 `decorate.js::reannouncePlan`(解析面与闸门同源, 组目标展开为活跃成员 hash; 解析不出的原样交回不静默丢)+ `_actCore` 按计划投递与跳过数文案 + 后端 `commands.py` 判据表与两个 `_cmd_reannounce_*` 过滤(第二道闸)。两轮全绿; 机理入坑档 `pitfalls/web-ui/reannounce-inactive-gate.md`。
> 最后活动: 2026-10-10 20:32

**Refs:** memory-bank/tasks/26-10-10-webui-reannounce-inactive-gate.md

## 正在进行

- 无 —— 两轮均已完成并收口(数字见 `commands run kb.baseline`)。

## 关键结论(供后续「状态相关动作门控」参考)

- **判定读 qB 原始 `state`, 不读派生 `kind`**: `kind` 只 6 档, `queuedDL`/`queuedUP` 被 qbittorrent-api 归进 downloading/seeding ⇒ **排队种子单看 kind 判不出来**。判据单点 `decorate.js::REANNOUNCE_BLOCKED_STATES`(`state` 缺失才回落 kind 的 paused/checking/error); 后端同表在 `commands.py::REANNOUNCE_BLOCKED_STATES`, 守阵钉两侧逐项一致。
- **后端判据也不能用 `state_enum` 谓词**(2026-10-10 实测真值表): `queuedDL`/`queuedUP` → `is_downloading`/`is_uploading` 为 True, 只有 `paused*`/`stopped*` 是 `is_stopped`、`error`/`missingFiles` 是 `is_errored`。想用谓词判"活跃"会把排队/校验中当活跃放过去。
- **qB 多目标口径是"任一活跃即可用"**(`oneCanForceReannounce`, 不是"全部活跃")—— 混合组不该置灰。**但 OR 语义的判据必然导致混选放行, 因此放行之后必须再做一次投递收敛**(判据层判"允不允许", 投递层判"发给谁", 两者不可合并): 否则不可执行的目标也被投递, 在有确认层的实现上会白等窗口并报假失败。
- **qB 的置灰 gate 只在 GUI**: commit `aa189a7` 只改 `src/gui/transferlistwidget.cpp`, HTTP 端点侧无门; `TorrentImpl::forceReannounce()` 是裸透传 `m_nativeHandle.force_reannounce(0, index)`, 真拦截在 libtorrent(issue #12080 维护者原话 "Force reannounce does nothing even for Queued torrents")。⇒ **"与 qB 一致"要分清是"与 GUI 一致"还是"与引擎一致"**, 二者在混选时不是一回事。
- **强制汇报有四条入口, 少接一条即形同虚设**: 右键四支 → `_actCore`; 键盘 `Shift+A` → `_kbAct` → `_actCore`; 详情面板 tracker 重报钮 → `drawerCmd` → `torrentCmd`(**不经 `_actCore`**, 必须单独接); 直调。显示层管"变灰 + 原因", 行为层设总闸。
- **置灰不用 `disabled`/`pointer-events:none`**: 二者会让全局自绘 tooltip 的 `mouseover` 委托命中不到, "为什么变灰"的 title 说明反而丢失。改用项目既有的 `is-gated` 口径(样式灰 + `cursor:default` + title + 行为层再拦), 菜单项 title 恒绑字符串(可用时空串, 走 ui_feedback「空串 title = 清除提示」通道)。
- **e2e 断言多目标动作要按 hash 落, 不要数请求条数**: 选中行可能同属一组而被展开为整组成员(本项目桩 300 种子 / 150 组, 两行必同组), 条数随分组形态变, 只有 hash 级断言在任何分组下都成立。
- **收窄动作后要重新审视注册层的前置直判**: 投递面收敛后 `_register_reannounce_pending` 的"停止种子立即 warn"支从常规路径降级为**竞态兜底**, 保留不删(删了等于把竞态推回"白等窗口后报未确认"); 其契约改为直接调注册面钉住。
