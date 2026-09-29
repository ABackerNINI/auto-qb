# WEBUI 键盘快捷键 · W1-W7 全波已实施(W5-W7 第二波完成) → W5-W7 待提交

> 摘要: 计划 plans/26-09-28-0354 全波落地。**W1-W4 第一波已入库 `38ffec5`**(基线
> 26-09-30-0555); **W5-W7 第二波 2026-09-30 07:02 完成, 未提交**(基线
> [26-09-30-0702](../testing/baselines/26-09-30-0702-webui-keyboard-w5w7.md), test.full
> 1813 passed + 3 skipped / 91%)。**W5 绑定+局部作用域**: E/F/I 组 run 全量接线(单目标
> 动作目标解析要求恰一 hash `_kbSingleHash`, 多选/整组提示不猜第一个; 复用 editMove/
> copyTorrentInfo/torrentCmd 等既有单种链), `_kbScope` 三档(settings/drawer/list)全量生效,
> 抽屉 Alt+1-4 / 设置页 Ctrl+S inputSafe / 模态白名单分流(modal 条目本期无, 引擎预留分支
> 静态守阵钉住), 浮层打开只放行焦点局部键位。**W6 后端持久化+面板**: routes/keys.py
> GET/PUT /api/keys(webui-keys.json 与 web.token 同寻址, 读时兜底链 主→.bak→默认表, PUT
> 校验 422, 金清单+2); 适配器 AQB_KEYS.reload/save(load 保持同步快照, startPolling 拉真值);
> 设置页「快捷键」分区(按下即录录制器捕获段监听/纯修饰键拒收/黑名单拒绑/冲突三选一/单条
> 全部重置/空串=禁用/保存失败本地回滚/离开未保存先确认 hubGo+hubBack 双挂守卫) + 帮助浮层
> Shift+Slash(Esc 归退栈链, 名单三处同步)。**W7**: 守阵 +11(前端 6 后端 5), 探针 28 项全过,
> dev.harness 无新增失败。新坑: pitfalls/web-ui/js-comment-terminator.md(块注释 `*/` 提前
> 终止, node --check 仍绿运行时才炸, 实测踩中)。
> 最后活动: 2026-09-30 07:10 (W5-W7 完成收尾, 未提交)

## 正在进行

- **W5-W7 已完成待提交**(改动面 14 文件: 新增 routes/keys.py; 引擎 shortcuts.js; 接线
  routes/__init__ + polling/state/lifecycle/dialogs/config_hub; 模板/CSS settings-detail/
  popovers/console_hub.css; 守阵 test_web.py + test_web_shortcuts.py)。下一步: 用户「提交」
  指令走 ship.commit(提交信息素材在任务档案进度日志 07:02 条)。
- 已完成条目已迁出至 [progress/implemented-webui.md](../progress/implemented-webui.md)
  「键盘快捷键全量落地」条; 计划 doc-status 已置 Done; 档案子任务表已全 Done。

## 关键决策

- 决策点① v4 终版 (2026-09-30 用户五轮拍板收敛): **无修饰单键为主, 单手操作优先**; 危险操作
  **一律二键组合** (一个修饰键+字母), 确认框兜底 (默认按钮「确定」, Enter 即确认): 删除
  Shift+D + Delete 额外入口, 重新校验 Shift+Y, 强制汇报 Shift+A; 裸键 D/C/F 释放空位;
  面板 danger 条目「⚠ 危险操作 (有确认框)」, 自绑裸键提示但允许(实施: `_kbCommitSerial`
  内 toast 提示)。
- 决策点⑤: 分两波 (W1-W4 默认键位 / W5-W7 局部作用域+面板+收尾), 均独立可验收。
- 决策点⑥: 后端独立文件 webui-keys.json + GET/PUT /api/keys; 适配器单点保反悔路径(计划 §4.6)。
- 实施期定口径: 单目标动作(E/F/I 组)目标解析**要求恰一 hash** —— 多选/整组/剧集单元一律
  toast 提示不猜第一个(静默错目标比不动作更糟); 列选择器 K 开/Esc 关(键盘再按被浮层屏蔽,
  注册表注释已注明)。
- load 同步快照语义保留: 引擎 keydown 内现取, 服务端真值由 reload() 异步拉入后失效
  `_kbTableCache` —— 适配器换介质(反悔路径)引擎零改动。
